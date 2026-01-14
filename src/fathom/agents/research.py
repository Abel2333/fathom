from typing import Literal, cast

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    get_buffer_string,
)
from langgraph.graph import END
from langgraph.types import Command

from fathom.config.loader import ConfigLoader
from fathom.prompts import (
    clarify_with_user_instructions,
    lead_researcher_prompt,
    transform_messages_into_research_topic_prompt,
)
from fathom.models.schema import (
    AgentState,
    ClarifyWithUser,
    ConductResearch,
    ResearchComplete,
    ResearchQuestion,
)
from fathom.tools.search import build_model
from fathom.tools.utils import get_today_str, think_tool

settings = ConfigLoader()


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
    # Check allow clarifying
    if not settings.config["research"]["allow_clarification"]:
        return Command(goto="write_research_brief")

    # Prepare the model
    messages = state["messages"]
    clarify_model = build_model(settings.summary_model).with_structured_output(
        ClarifyWithUser
    )

    # Prompt
    prompt_content = clarify_with_user_instructions.format(
        messages=get_buffer_string(messages), date=get_today_str()
    )
    response = cast(
        ClarifyWithUser,
        await clarify_model.ainvoke([HumanMessage(content=prompt_content)]),
    )

    # Route based on clarification analysis
    if response.need_clarification:
        # End with clarifying question for user
        # End here denote the end of AI messages in this turn
        return Command(
            goto=cast(Literal["__end__"], END),
            update={"messages": [AIMessage(content=response.question)]},
        )
    else:
        # Proceed to research with verification message
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
    # Set up the research model for structured output
    research_model = build_model(settings.research_model).with_structured_output(
        ResearchQuestion
    )

    # Prompt
    prompt_content = transform_messages_into_research_topic_prompt.format(
        message=get_buffer_string(state.get("messages", [])), date=get_today_str()
    )
    response = cast(
        ResearchQuestion,
        await research_model.ainvoke([HumanMessage(content=prompt_content)]),
    )

    # Initiallize supervisor with research brief and instructions
    supervisor_system_prompt = lead_researcher_prompt.format(
        date=get_today_str(),
        max_concurrent_research_units=settings.config["research"]["concurrency"],
        max_researcher_iterations=settings.config["research"]["max_depth"],
    )

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


async def supervisor(state: AgentState):
    """
    Lead research supervisor that plans research strategy and delegates to researchers.

    The supervisor analyzes the research brief and decides how to break down the research
    into manageable tasks. It can use think_tool for strategic planning, ConductResearch
    to delegate tasks to sub-researchers, or ResearchComplete when satisfied with findings.

    Args:
        state: Current supervisor state with messages and research context

    Returns:
        Command to proceed to supervisor_tools for tool execution
    """
    lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]

    research_model = build_model(settings.research_model).bind_tools(
        lead_researcher_tools
    )

    supervisor_messages = state.get("supervisor_messages", [])
    response = await research_model.ainvoke(supervisor_messages)

    # Updatte state and proceed to tool execution
    return Command(
        goto="supervisor_tools",
        update={
            "supervisor_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1,
        },
    )
