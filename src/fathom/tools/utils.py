"""Miscellaneous utility functions and tools."""

from datetime import datetime

from langchain_core.messages import (
    AIMessage,
    MessageLikeRepresentation,
    filter_messages,
)
from langchain_core.tools import BaseTool, tool


def get_today_str() -> str:
    """Get current date formatted for display in prompts and outputs.

    Returns:
        Human-readable date string in format like 'Mon Jan 15, 2024'
    """
    now = datetime.now()
    return f"{now:%a} {now:%b} {now.day}, {now:%Y}"


@tool(description="Strategic reflection tool for research planning")
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"


def get_notes_from_tool_calls(messages: list[MessageLikeRepresentation]):
    """Extract notes from tool call messages."""
    return [
        tool_msg.content for tool_msg in filter_messages(messages, include_types="tool")
    ]


def remove_up_to_last_ai_message(
    messages: list[MessageLikeRepresentation],
) -> list[MessageLikeRepresentation]:
    """
    Truncate message history by removing up to the last AI message.

    This is useful for handling token limit exceeded errors by removing recent context.

    Args:
        messages: List of message objects to truncate

    Returns:
        Truncated message list up to (but not including) the last AI message
    """
    # Search backwards through messages to find the last AI message
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage):
            # Return everything up to (but not including) the last AI message
            return messages[:i]

    # No AI messages found, return original list
    return messages


# Global registry for custom tools
_custom_tools_registry: list[BaseTool] = []


def register_tool(tool_func: BaseTool) -> BaseTool:
    """Register a custom tool to be included in the researcher's toolset.

    This decorator allows you to register custom tools that will be automatically
    included when get_all_tools() is called.

    Args:
        tool_func: A tool function (decorated with @tool) or Pydantic BaseModel

    Returns:
        The original tool function, unchanged

    Example:
        >>> from langchain_core.tools import tool
        >>> from fathom.tools.utils import register_tool
        >>>
        >>> @register_tool
        >>> @tool
        >>> def my_custom_tool(query: str) -> str:
        ...     '''Custom tool description.'''
        ...     return "Result"
    """
    _custom_tools_registry.append(tool_func)
    return tool_func


def get_all_tools() -> list[BaseTool]:
    """Get all available tools for the researcher.

    This function collects all built-in tools and any custom tools that have been
    registered via the @register_tool decorator. It provides a centralized way to
    manage tools for the research agent.

    Built-in tools:
    - tavily_search: Web search and summarization tool
    - think_tool: Strategic reflection and planning tool

    To add custom tools, use one of these methods:

    Method 1: Using the @register_tool decorator (Recommended):
        >>> from langchain_core.tools import tool
        >>> from fathom.tools.utils import register_tool
        >>>
        >>> @register_tool
        >>> @tool
        >>> def my_custom_tool(query: str) -> str:
        ...     '''My custom tool description.'''
        ...     return "Result"

    Method 2: Direct registration:
        >>> from fathom.tools.utils import register_tool
        >>> register_tool(my_tool_function)

    Returns:
        List of all available tools for binding to the research model

    Example:
        >>> from fathom.tools.utils import get_all_tools
        >>> from fathom.tools.search import build_model
        >>> researcher_tools = get_all_tools()
        >>> model = build_model("deepseek-chat").bind_tools(researcher_tools)
    """
    from fathom.tools.search import tavily_search

    # Built-in tools that are always available
    tools = [
        tavily_search,
        think_tool,
    ]

    # Add all registered custom tools
    tools.extend(_custom_tools_registry)

    return tools
