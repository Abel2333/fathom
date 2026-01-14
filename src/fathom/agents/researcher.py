"""Individual researcher agent module for conducting focused research.

This module contains the researcher agent that conducts focused research on
specific topics using available tools like search and strategic thinking.
"""

import asyncio
import hashlib
from typing import Literal, cast

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    filter_messages,
)
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from fathom.config.loader import ConfigLoader
from fathom.config.logging import get_logger
from fathom.models.schema import ResearcherOutputState, ResearcherState
from fathom.prompts import (
    compress_research_simple_human_message,
    research_system_prompt,
)
from fathom.tools.search import build_model
from fathom.tools.utils import get_all_tools, get_today_str, remove_up_to_last_ai_message

settings = ConfigLoader()
logger = get_logger(__name__)


def get_researcher_id(topic: str) -> str:
    """Generate a short unique ID for a researcher based on the topic."""
    # Create a hash of the topic and take first 6 characters
    topic_hash = hashlib.md5(topic.encode()).hexdigest()[:6]
    return f"R-{topic_hash}"



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
    topic = state.get("research_topic", "unknown topic")

    # Generate unique researcher ID based on topic
    researcher_id = get_researcher_id(topic)

    # Extract topic summary (first 80 chars)
    topic_summary = topic[:80] + "..." if len(topic) > 80 else topic

    logger.info("=" * 60)
    logger.info(f"RESEARCHER [{researcher_id}] LOOP: Starting")
    logger.info("=" * 60)
    logger.info(f"[{researcher_id}] Topic: {topic_summary}")
    logger.debug(f"[{researcher_id}] Current researcher messages: {len(researcher_messages)}")

    # Get all available research tools (search, think_tool)
    tools = get_all_tools()
    if len(tools) == 0:
        logger.error(
            f"[{researcher_id}] No tools found to conduct research: Please configure either your "
            "search API or add custom tools."
        )
        raise ValueError(
            "No tools found to conduct research: Please configure either your "
            "search API or add custom tools."
        )

    # Configure the researcher model with tool
    researcher_prompt = research_system_prompt.format(date=get_today_str())

    # Configure model with tools
    research_model = build_model(settings.research_model).bind_tools(tools)
    logger.debug(
        f"[{researcher_id}] Using model: {settings.research_model} with {len(tools)} bound tools"
    )

    messages = [SystemMessage(content=researcher_prompt)] + researcher_messages
    logger.debug(f"[{researcher_id}] Invoking researcher model with system prompt and messages")
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
    iteration = state.get("tool_call_iterations", 0)
    topic = state.get("research_topic", "unknown topic")

    # Generate unique researcher ID based on topic
    researcher_id = get_researcher_id(topic)

    logger.info(f"[{researcher_id}] RESEARCHER TOOLS: iteration {iteration + 1}")

    # Early exit if no tool calls were made (including native web search)
    has_tool_calls = bool(most_recent_message.tool_calls)

    if not has_tool_calls:
        logger.info(f"[{researcher_id}] No tool calls found; proceeding to compression")
        return Command(goto="compress_research")

    tools = get_all_tools()
    tools_by_name = {tool.name: tool for tool in tools}
    logger.debug(f"[{researcher_id}] Available tools for execution: {list(tools_by_name.keys())}")

    # Execute all tool calls in parallel
    tool_calls = most_recent_message.tool_calls
    logger.info(f"[{researcher_id}] Executing {len(tool_calls)} tool call(s)")
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
        if exceeded_iterations:
            logger.warning(
                f"[{researcher_id}] Max tool call iterations reached; moving to compression stage"
            )
        if research_complete_called:
            logger.info(f"[{researcher_id}] ResearchComplete tool detected; moving to compression")
        # End research and proceed to compression
        return Command(
            goto="compress_research", update={"researcher_messages": tool_outputs}
        )

    # Continue research loop with tool results
    logger.info(f"[{researcher_id}] Continuing research loop with tool outputs")
    return Command(goto="researcher", update={"researcher_messages": tool_outputs})


async def compress_research(state: ResearcherState):
    """
    Compress and synthesize research findings into a concise, structured summary.

    This function takes all the research findings, tool outputs, and AI messages from
    a researcher's work and distills them into a clean, comprehensive summary while
    preserving all important information and findings.

    Args:
        state: Current researcher state with accumulated research messages

    Returns:
        Dictionary containing compressed research summary and raw notes
    """
    synthesis_model = build_model(settings.summary_model)
    topic = state.get("research_topic", "unknown topic")

    # Generate unique researcher ID based on topic
    researcher_id = get_researcher_id(topic)

    logger.info(f"[{researcher_id}] COMPRESS RESEARCH: starting synthesis")
    logger.debug(f"[{researcher_id}] Using summary model: {settings.summary_model}")

    researcher_messages = state.get("researcher_messages", [])
    researcher_messages.append(
        HumanMessage(content=compress_research_simple_human_message)
    )

    # Attempt compression with retry logic for token limit issues
    synthesis_attempts = 0
    max_attempts = 3

    while synthesis_attempts < max_attempts:
        logger.info(f"[{researcher_id}] Compression attempt {synthesis_attempts + 1} of {max_attempts}")
        try:
            # Create system prompt focused on compression task
            compression_prompt = compress_research_simple_human_message.format(
                date=get_today_str()
            )
            messages = [SystemMessage(content=compression_prompt)] + researcher_messages

            # Execute compression with streaming
            logger.info(f"[{researcher_id}] Starting compression with streaming output...")
            accumulated_content = ""

            async for chunk in synthesis_model.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    content_chunk = str(chunk.content)
                    accumulated_content += content_chunk
                    # Print streaming output to console for real-time feedback
                    print(content_chunk, end="", flush=True)

            # Print newline after streaming completes
            print()

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
            logger.info(f"[{researcher_id}] Compression succeeded")
            return {
                "compressed_research": accumulated_content,
                "raw_notes": [raw_notes_content],
            }
        except Exception:
            logger.exception(f"[{researcher_id}] Compression failed; retrying with truncated context")
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

    logger.error(f"[{researcher_id}] Compression failed after maximum retries; returning error payload")
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
