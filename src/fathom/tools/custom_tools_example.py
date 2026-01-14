"""Example custom tools for the Fathom research agent.

This file demonstrates how to create and register custom tools that will be
automatically included in the researcher's toolset.

To create your own custom tools:
1. Import the necessary decorators
2. Create your tool function with @tool decorator
3. Register it with @register_tool decorator
4. Import this module in your main application to register the tools
"""

from langchain_core.tools import tool

from fathom.tools.utils import register_tool


@register_tool
@tool
async def calculate(expression: str) -> str:
    """Perform mathematical calculations safely.

    This tool can evaluate mathematical expressions and return the result.

    Args:
        expression: A mathematical expression to evaluate (e.g., "2 + 2", "sqrt(16)")

    Returns:
        The result of the calculation as a string
    """
    # Simple example - in production you'd want to use a safe eval library
    # like simpleeval or numexpr to prevent code injection
    try:
        import math

        # Create a safe namespace with only math functions
        safe_dict = {
            "sqrt": math.sqrt,
            "pow": math.pow,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "log": math.log,
            "exp": math.exp,
        }
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        return f"Result: {result}"
    except Exception as e:
        return f"Error calculating expression: {str(e)}"


@register_tool
@tool
async def fetch_weather(location: str) -> str:
    """Fetch weather information for a specific location.

    This is a placeholder example. In production, you would integrate with
    a real weather API.

    Args:
        location: The city or location to get weather for

    Returns:
        Weather information as a string
    """
    # Placeholder implementation
    return f"Weather data for {location} would be fetched from an API here."


# You can also register existing tool functions
def my_existing_tool(param: str) -> str:
    """An existing tool function."""
    return f"Processed: {param}"


# Register it after the fact
# register_tool(tool(my_existing_tool))
