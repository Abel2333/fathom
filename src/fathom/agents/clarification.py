"""User clarification module for the research agent.

This module handles analyzing user requests and determining if clarification
is needed before proceeding with research.
"""

from typing import Literal, cast

from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langgraph.graph import END
from langgraph.types import Command

from fathom.config.loader import ConfigLoader
from fathom.config.logging import get_logger
from fathom.models.schema import AgentState, ClarifyWithUser, ResearchQuestion
from fathom.prompts import (
    clarify_with_user_instructions,
    transform_messages_into_research_topic_prompt,
)
from fathom.tools.search import build_model
from fathom.tools.utils import get_today_str

settings = ConfigLoader()
logger = get_logger(__name__)


async def clarify_with_user(
    state: AgentState,
) -> Command[Literal["write_research_brief", "__end__"]]:
    """
    Analyze user messages and ask clarifying questions if the research scope is unclear.

    This function determines the user's request needs clarification before proceeding
    with research. If clarification is disabled or not needed, it proceeds directly to research.

    Args:
        state: Current agent state containing user messages

    Returns:
        Command to  either end with a clarifying question or proceed to research brief
    """
    logger.info("=" * 60)
    logger.info("CLARIFICATION PHASE: Starting")
    logger.info("=" * 60)

    # Check allow clarifying
    if not settings.config["research"]["allow_clarification"]:
        logger.info("Clarification disabled in config, proceeding directly to research brief")
        logger.info("→ Routing to: write_research_brief")
        return Command(goto="write_research_brief")

    # Prepare the model
    messages = state["messages"]
    logger.info(f"Analyzing {len(messages)} user messages for clarification needs")
    logger.debug(f"Message preview: {get_buffer_string(messages)[:200]}...")

    clarify_model = build_model(settings.summary_model).with_structured_output(
        ClarifyWithUser
    )
    logger.debug(f"Using model: {settings.summary_model}")

    # Prompt
    logger.debug("Invoking clarification model...")
    prompt_content = clarify_with_user_instructions.format(
        messages=get_buffer_string(messages), date=get_today_str()
    )
    response = cast(
        ClarifyWithUser,
        await clarify_model.ainvoke([HumanMessage(content=prompt_content)]),
    )
    logger.debug(f"Model response received: need_clarification={response.need_clarification}")

    # Route based on clarification analysis
    if response.need_clarification:
        # End with clarifying question for user
        # End here denote the end of AI messages in this turn
        logger.info("✋ Clarification needed - asking user for more information")
        logger.info(f"Question: {response.question[:150]}...")
        logger.info("→ Routing to: END (waiting for user response)")
        return Command(
            goto=cast(Literal["__end__"], END),
            update={"messages": [AIMessage(content=response.question)]},
        )
    else:
        # Proceed to research with verification message
        logger.info("✓ No clarification needed - scope is clear")
        logger.debug(f"Verification message: {response.verification[:100]}...")
        logger.info("→ Routing to: write_research_brief")
        return Command(
            goto="write_research_brief",
            update={"messages": [AIMessage(content=response.verification)]},
        )


async def write_research_brief(
    state: AgentState,
) -> Command[Literal["research_supervisor"]]:
    """
    Transform user messages into a structured research brief and initialize supervisor.

    This function analyzes the user's messages and generates a focused research brief
    that will guide the research supervisor. It also sets up the initial supervisor
    context with appropriate prompts and instructions.

    Args:
        state: Current agent state containing user messages

    Returns:
        Command to proceed to research supervisor with initialized context
    """
    logger.info("=" * 60)
    logger.info("RESEARCH BRIEF GENERATION: Starting")
    logger.info("=" * 60)

    # Set up the research model for structured output
    research_model = build_model(settings.research_model).with_structured_output(
        ResearchQuestion
    )
    logger.debug(f"Using model: {settings.research_model}")

    # Prompt
    messages_str = get_buffer_string(state.get("messages", []))
    logger.info(f"Transforming {len(state.get('messages', []))} messages into research brief")
    logger.debug(f"Message content preview: {messages_str[:200]}...")

    prompt_content = transform_messages_into_research_topic_prompt.format(
        messages=messages_str,
        date=get_today_str(),
    )

    logger.debug("Invoking research brief generation model...")
    response = cast(
        ResearchQuestion,
        await research_model.ainvoke([HumanMessage(content=prompt_content)]),
    )

    logger.info("✓ Research brief generated successfully")
    logger.info(f"Brief preview: {response.research_brief[:150]}...")
    logger.debug(f"Full research brief: {response.research_brief}")

    # Import here to avoid circular dependency
    from fathom.prompts import lead_researcher_prompt

    # Initiallize supervisor with research brief and instructions
    supervisor_system_prompt = lead_researcher_prompt.format(
        date=get_today_str(),
        max_concurrent_research_units=settings.config["research"]["concurrency"],
        max_researcher_iterations=settings.config["research"]["max_depth"],
    )

    logger.info("Initializing supervisor with research brief and configuration")
    logger.debug(f"Supervisor config: concurrency={settings.config['research']['concurrency']}, "
                f"max_depth={settings.config['research']['max_depth']}")
    logger.info("→ Routing to: research_supervisor")

    from langchain_core.messages import SystemMessage

    return Command(
        goto="research_supervisor",
        update={
            "research_brief": response.research_brief,
            "supervisor_messages": {
                "type": "override",
                "value": [
                    SystemMessage(content=supervisor_system_prompt),
                    HumanMessage(content=response.research_brief),
                ],
            },
        },
    )
