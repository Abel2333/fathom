import asyncio
from typing import Literal, cast

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    filter_messages,
    get_buffer_string,
)
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from fathom.config.loader import ConfigLoader
from fathom.config.logging import get_logger
from fathom.models.schema import (
    AgentInputState,
    AgentState,
    ClarifyWithUser,
    ConductResearch,
    ResearchComplete,
    ResearcherOutputState,
    ResearcherState,
    ResearchQuestion,
    SupervisorState,
)
from fathom.prompts import (
    clarify_with_user_instructions,
    compress_research_simple_human_message,
    final_report_generation_prompt,
    lead_researcher_prompt,
    research_system_prompt,
    transform_messages_into_research_topic_prompt,
)
from fathom.tools.search import build_model
from fathom.tools.utils import (
    get_all_tools,
    get_notes_from_tool_calls,
    get_today_str,
    remove_up_to_last_ai_message,
    think_tool,
)

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
    logger.info("Starting clarification phase")

    # Check allow clarifying
    if not settings.config["research"]["allow_clarification"]:
        logger.info("Clarification disabled, proceeding directly to research brief")
        return Command(goto="write_research_brief")

    # Prepare the model
    messages = state["messages"]
    logger.debug(f"Analyzing {len(messages)} messages for clarification needs")

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
        logger.info("Clarification needed, asking user for more information")
        logger.debug(f"Clarification question: {response.question[:100]}...")
        return Command(
            goto=cast(Literal["__end__"], END),
            update={"messages": [AIMessage(content=response.question)]},
        )
    else:
        # Proceed to research with verification message
        logger.info("No clarification needed, proceeding to research brief")
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
    logger.info("Writing research brief from user messages")

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

    logger.info(f"Research brief generated: {response.research_brief[:150]}...")
    logger.debug(f"Full research brief: {response.research_brief}")

    # Initiallize supervisor with research brief and instructions
    supervisor_system_prompt = lead_researcher_prompt.format(
        date=get_today_str(),
        max_concurrent_research_units=settings.config["research"]["concurrency"],
        max_researcher_iterations=settings.config["research"]["max_depth"],
    )

    logger.info("Initializing research supervisor with brief and instructions")

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


async def supervisor(state: SupervisorState):
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
    current_iteration = state.get("research_iterations", 0)
    logger.info(f"Research supervisor starting iteration {current_iteration + 1}")

    lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]

    research_model = build_model(settings.research_model).bind_tools(
        lead_researcher_tools
    )

    supervisor_messages = state.get("supervisor_messages", [])
    logger.debug(f"Supervisor processing {len(supervisor_messages)} messages")

    response = await research_model.ainvoke(supervisor_messages)

    # Log tool calls if any
    if hasattr(response, "tool_calls") and response.tool_calls:
        tool_names = [tc.get("name", "unknown") for tc in response.tool_calls]
        logger.info(f"Supervisor calling tools: {', '.join(tool_names)}")

    # Updatte state and proceed to tool execution
    logger.debug(
        f"Proceeding to supervisor_tools, iteration count: {current_iteration + 1}"
    )

    return Command(
        goto="supervisor_tools",
        update={
            "supervisor_messages": [response],
            "research_iterations": state.get("research_iterations", 0) + 1,
        },
    )


async def supervisor_tools(
    state: SupervisorState,
) -> Command[Literal["supervisor", "__end__"]]:
    """
    Execute tools called by the suypervisor, including research delegation and strategic thinking.

    This function handles three types of supervisor tool calls:
    1. think_tool - Strategic reflection that continues the conversation
    2. ConductResearch - Delegates research tasks to sub-researchers
    3. ResearchComplete - Signals completion of research phase

    Args:
        state: Current supervisor state with messages and iteration count

    Returns:
        Command to either continue supervision loop or end research phase
    """
    # Extract current state and check exit conditions
    supervisor_messages = state.get("supervisor_messages", [])
    research_iterations = state.get("research_iterations", 0)
    most_recent_message = cast(AIMessage, supervisor_messages[-1])

    logger.info(f"Supervisor tools executing at iteration {research_iterations}")

    # Define exit criteria for research phase
    exceed_allowed_iterations = (
        research_iterations > settings.config["research"]["max_depth"]
    )
    no_tool_calls = not most_recent_message.tool_calls
    research_complete_tool_call = any(
        tool_call["name"] == "ResearchComplete"
        for tool_call in most_recent_message.tool_calls
    )

    # Check exit conditions and log appropriately
    if exceed_allowed_iterations:
        logger.warning(
            f"Research exceeded max depth ({settings.config['research']['max_depth']} iterations), "
            "ending research phase"
        )
    elif no_tool_calls:
        logger.warning(
            "No tool calls found in supervisor message, ending research phase"
        )
    elif research_complete_tool_call:
        logger.info("ResearchComplete tool called, ending research phase")

    if exceed_allowed_iterations or no_tool_calls or research_complete_tool_call:
        logger.info("Finalizing research and extracting notes")
        return Command(
            goto=cast(Literal["__end__"], END),
            update={
                "notes": get_notes_from_tool_calls(supervisor_messages),
                "research_brief": state.get("research_brief", ""),
            },
        )

    # Process all tool calls together (both think_tool and ConductResearch)
    all_tool_messages = []
    update_payload = {"supervisor_messages": []}

    # Handle think_tool calls (strategic reflection)
    think_tool_calls = [
        tool_call
        for tool_call in most_recent_message.tool_calls
        if tool_call["name"] == "think_tool"
    ]

    for tool_call in think_tool_calls:
        reflection_content = tool_call["args"]["reflection"]
        all_tool_messages.append(
            ToolMessage(
                content=f"Reflection recorded: {reflection_content}",
                name="think_tool",
                tool_call_id=tool_call["id"],
            )
        )

    # Handle ConductResearch calls (research delegation)
    conduct_research_calls = [
        tool_call
        for tool_call in most_recent_message.tool_calls
        if tool_call["name"] == "ConductResearch"
    ]

    if conduct_research_calls:
        try:
            # Limit concurrent research units to prevent resource exhaustion
            allowed_conduct_research_calls = conduct_research_calls[
                : settings.config["research"]["concurrency"]
            ]
            overflow_conduct_research_calls = conduct_research_calls[
                settings.config["research"]["concurrency"] :
            ]

            # Execute research tasks in parallel
            research_tasks = [
                researcher_subgraph.ainvoke(
                    {
                        "researcher_messages": [
                            HumanMessage(content=tool_call["args"]["research_topic"])
                        ],
                        "research_topic": tool_call["args"]["research_topic"],
                    },
                )
                for tool_call in allowed_conduct_research_calls
            ]

            tool_results = await asyncio.gather(*research_tasks)

            # Create tool messages with research results
            for observation, tool_call in zip(
                tool_results, allowed_conduct_research_calls
            ):
                all_tool_messages.append(
                    ToolMessage(
                        content=observation.get(
                            "compressed_research",
                            "Error synthesizing research report: Maximum retries exceeded",
                        ),
                        name=tool_call["name"],
                        tool_call_id=tool_call["id"],
                    )
                )

            # Handle overflow research calls with error messages
            for overflow_call in overflow_conduct_research_calls:
                all_tool_messages.append(
                    ToolMessage(
                        content=f"Error: Did not run this research as you have already exceeded the maximum number of concurrent research units. Please try again with {settings.config['research']['concurrency']} or fewer research units.",
                        name="ConductResearch",
                        tool_call_id=overflow_call["id"],
                    )
                )

            # Aggregate raw notes from all research results
            raw_notes_concat = "\n".join(
                [
                    "\n".join(observation.get("raw_notes", []))
                    for observation in tool_results
                ]
            )

            if raw_notes_concat:
                update_payload["raw_notes"] = [raw_notes_concat]
        except Exception:
            # Handle research execution errors
            return Command(
                goto=cast(Literal["__end__"], END),
                update={
                    "notes": get_notes_from_tool_calls(supervisor_messages),
                    "research_brief": state.get("research_brief", ""),
                },
            )

    # Return command with all tool results
    update_payload["supervisor_messages"] = all_tool_messages
    return Command(goto="supervisor", update=update_payload)


# Supervisor Subgraph Construction
# Create the supervisor workflow that manages research delegation and coordination
supervisor_builder = StateGraph(SupervisorState)

# Add supervisor nodes for research management
supervisor_builder.add_node("supervisor", supervisor)
supervisor_builder.add_node("supervisor_tools", supervisor_tools)

# Define supervisor workflow edges
supervisor_builder.add_edge(START, "supervisor")

# Compile supervisor subgraph for use in main workflow
supervisor_subgraph = supervisor_builder.compile()


async def researcher(state: ResearcherState) -> Command[Literal["researcher_tools"]]:
    """
    Individual researcher that conducts focused research on specific topics.

    This researcher is given a specific research topic by the supervisor and uses
    available tools (search, think_tool) to gather comprehensive information.
    It can use think_tool for strategic planning between searches.

    Args:
        state: Current researcher state with messages and topic context

    Returns:
        Command to proceed to researcher_tools for tool execution
    """
    researcher_messages = state.get("researcher_messages", [])

    # Get all available research tools (search, think_tool)
    tools = get_all_tools()
    if len(tools) == 0:
        raise ValueError(
            "No tools found to conduct research: Please configure either your "
            "search API or add custom tools."
        )

    # Configure the researcher model with tool
    researcher_prompt = research_system_prompt.format(date=get_today_str())

    # Configure model with tools
    research_model = build_model(settings.research_model).bind_tools(tools)

    messages = [SystemMessage(content=researcher_prompt)] + researcher_messages
    response = await research_model.ainvoke(messages)

    # Update state and proceed to tool execution
    return Command(
        goto="researcher_tools",
        update={
            "researcher_messages": [response],
            "tool_call_iterations": state.get("tool_call_iterations", 0) + 1,
        },
    )


# Tool Execution Helper Function
async def execute_tool_safely(tool, args):
    """Safely execute a tool with error handling."""
    try:
        return await tool.ainvoke(args)
    except Exception as e:
        return f"Error executing tool: {str(e)}"


async def researcher_tools(
    state: ResearcherState,
) -> Command[Literal["researcher", "compress_research"]]:
    """
    Execute tools called by the researcher, including search tools and strategic thinking.

    This function handles various types of researcher tool calls:
    1. think_tool - Strategic reflection that continues the research conversation
    2. Search tools (tavily_search, web_search) - Information gathering
    3. MCP tools - External tool integrations
    4. ResearchComplete - Signals completion of individual research task

    Args:
        state: Current researcher state with messages and iteration count

    Returns:
        Command to either continue research loop or proceed to compression
    """
    researcher_messages = state.get("researcher_messages", [])
    most_recent_message = cast(AIMessage, researcher_messages[-1])

    # Early exit if no tool calls were made (including native web search)
    has_tool_calls = bool(most_recent_message.tool_calls)

    if not has_tool_calls:
        return Command(goto="compress_research")

    tools = get_all_tools()
    tools_by_name = {
        tool.name if hasattr(tool, "name") else tool.get("name", "web_search"): tool
        for tool in tools
    }

    # Execute all tool calls in parallel
    tool_calls = most_recent_message.tool_calls
    tool_execution_tasks = [
        execute_tool_safely(tools_by_name[tool_call["name"]], tool_call["args"])
        for tool_call in tool_calls
    ]
    observations = await asyncio.gather(*tool_execution_tasks)

    # Create tool messages from execution results
    tool_outputs = [
        ToolMessage(
            content=observation, name=tool_call["name"], tool_call_id=tool_call["id"]
        )
        for observation, tool_call in zip(observations, tool_calls)
    ]

    # Check late exit conditions (after processing tools)
    exceeded_iterations = (
        state.get("tool_call_iterations", 0)
        >= settings.config["research"]["max_tool_calls"]
    )
    research_complete_called = any(
        tool_call["name"] == "ResearchComplete"
        for tool_call in most_recent_message.tool_calls
    )

    if exceeded_iterations or research_complete_called:
        # End research and proceed to compression
        return Command(
            goto="compress_research", update={"researcher_messages": tool_outputs}
        )

    # Continue research loop with tool results
    return Command(goto="researcher", update={"researcher_messages": tool_outputs})


async def compress_research(state: ResearcherState):
    """
    Compress and synthesize research findings into a concise, structured summary.

    This function takes all the research findings, tool outputs, and AI messages from
    a researcher's work and distills them into a clean, comprehensive summary while
    preserving all important information and findings.

    Args:
        state: Current researcher state with accumulated research messages
        config: Runtime configuration with compression model settings

    Returns:
        Dictionary containing compressed research summary and raw notes
    """
    synthesis_model = build_model(settings.summary_model)

    researcher_messages = state.get("researcher_messages", [])
    researcher_messages.append(
        HumanMessage(content=compress_research_simple_human_message)
    )

    # Attempt compression with retry logic for token limit issues
    synthesis_attempts = 0
    max_attempts = 3

    while synthesis_attempts < max_attempts:
        try:
            # Create system prompt focused on compression task
            compression_prompt = compress_research_simple_human_message.format(
                date=get_today_str()
            )
            messages = [SystemMessage(content=compression_prompt)] + researcher_messages

            # Execute compression
            response = await synthesis_model.ainvoke(messages)

            # Extract raw notes from all tool and AI Messages
            raw_notes_content = "\n".join(
                [
                    str(message.content)
                    for message in filter_messages(
                        researcher_messages, include_types=["tool", "ai"]
                    )
                ]
            )

            # Return successful compression result
            return {
                "compressed_research": str(response.content),
                "raw_notes": [raw_notes_content],
            }
        except Exception:
            synthesis_attempts += 1

            # Remove older messages
            researcher_messages = remove_up_to_last_ai_message(researcher_messages)
            continue

    raw_notes_content = "\n".join(
        [
            str(message.content)
            for message in filter_messages(
                researcher_messages, include_types=["tool", "ai"]
            )
        ]
    )

    return {
        "compressed_research": "Error synthesizing research report: Maximum retries exceeded",
        "raw_notes": [raw_notes_content],
    }


# Researcher Subgraph Construction
# Creates individual researcher workflow for conducting focused research on specific topics
researcher_builder = StateGraph(ResearcherState, output_schema=ResearcherOutputState)


# Add researcher nodes for research execution and compression
researcher_builder.add_node("researcher", researcher)  # Main researcher logic
researcher_builder.add_node(
    "researcher_tools", researcher_tools
)  # Tool execution handler
researcher_builder.add_node(
    "compress_research", compress_research
)  # Research compression

# Define researcher workflow edges
researcher_builder.add_edge(START, "researcher")  # Entry point to researcher
researcher_builder.add_edge("compress_research", END)  # Exit point after compression

# Compile researcher subgraph for parallel execution by supervisor
researcher_subgraph = researcher_builder.compile()


async def final_report_generation(state: AgentState):
    """
    Generate the final comprehensive research report with retry logic for token limits.

    This function takes all collected research findings and synthesizes them into a
    well-structured, comprehensive final report using the configured report generation model.

    Args:
        state: Agent state containing research findings and context

    Returns:
        Dictionary containing the final report and cleared state
    """
    notes = state.get("notes", [])
    cleared_state = {"notes": {"type": "override", "value": []}}
    findings = "\n".join(notes)

    writer_model = build_model(settings.report_model)

    max_retries = 3
    current_retry = 0

    while current_retry <= max_retries:
        try:
            final_report_prompt = final_report_generation_prompt.format(
                researcher_brief=state.get("research_brief", ""),
                messages=get_buffer_string(state.get("messages", [])),
                findings=findings,
                date=get_today_str(),
            )

            final_report = await writer_model.ainvoke(
                [HumanMessage(content=final_report_prompt)]
            )

            # Return successful report generation
            return {
                "final_report": final_report.content,
                "messages": [final_report],
                **cleared_state,
            }
        except Exception as e:
            return {
                "final_report": f"Error generating final report: {e}",
                "messages": [
                    AIMessage(content="Report generation failed due to an error")
                ],
                **cleared_state,
            }

    return {
        "final_report": "Error generating final report: Maximum retries exceeded",
        "messages": [
            AIMessage(content="Report generation failed after maximum retries")
        ],
        **cleared_state,
    }


# Main Deep Researcher Graph COnstruction
deep_researcher_builder = StateGraph(
    AgentState,
    input_schema=AgentInputState,
)

# Add main workflow nodes for the complete research process

# User clarification phase
deep_researcher_builder.add_node("clarify_with_user", clarify_with_user)
# Research planning phase
deep_researcher_builder.add_node("write_research_brief", write_research_brief)
# Research execution phase
deep_researcher_builder.add_node("research_supervisor", supervisor_subgraph)
# Report generation phase
deep_researcher_builder.add_node("final_report_generation", final_report_generation)


# Define main workflow edges for sequential execution

# Entry point
deep_researcher_builder.add_edge(START, "clarify_with_user")
# Research to report
deep_researcher_builder.add_edge("research_supervisor", "final_report_generation")
# Final exit point
deep_researcher_builder.add_edge("final_report_generation", END)

# Compile the complete deep researcher workflow
deep_researcher = deep_researcher_builder.compile()
