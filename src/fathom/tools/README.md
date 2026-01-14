# Fathom Research Tools

This directory contains all tools available to the Fathom research agent, including built-in tools and custom extensions.

## Built-in Tools

### 1. Tavily Search (`tavily_search`)
Web search and content summarization tool powered by Tavily API.

**Features:**
- Multi-query search support
- Automatic content summarization
- Deduplication of results
- Configurable result limits

**Usage:**
```python
results = await tavily_search(
    queries=["AI safety research", "transformer models"],
    max_results=5,
    topic="general"
)
```

### 2. Think Tool (`think_tool`)
Strategic reflection tool for research planning and decision-making.

**Purpose:**
- Analyze research progress
- Identify information gaps
- Plan next research steps
- Make strategic decisions

**Usage:**
```python
reflection = think_tool(
    reflection="I have found information about X, but still need Y..."
)
```

## Creating Custom Tools

### Method 1: Using the @register_tool Decorator (Recommended)

```python
from langchain_core.tools import tool
from fathom.tools import register_tool

@register_tool
@tool
async def my_custom_tool(query: str) -> str:
    """Description of what this tool does.

    Args:
        query: Description of the parameter

    Returns:
        Description of the return value
    """
    # Your tool implementation
    return "result"
```

### Method 2: Direct Registration

```python
from fathom.tools import register_tool
from langchain_core.tools import tool

@tool
def existing_tool(param: str) -> str:
    """Tool description."""
    return "result"

# Register it
register_tool(existing_tool)
```

### Method 3: Pydantic BaseModel Tools

You can also create tools using Pydantic BaseModel:

```python
from pydantic import BaseModel, Field
from fathom.tools import register_tool

@register_tool
class MyToolInput(BaseModel):
    """Tool for doing something specific."""

    query: str = Field(description="The query parameter")
    max_results: int = Field(default=5, description="Maximum results")
```

## Using All Tools

The `get_all_tools()` function collects all built-in and registered custom tools:

```python
from fathom.tools import get_all_tools
from fathom.tools.search import build_model

# Get all available tools
researcher_tools = get_all_tools()

# Bind them to your model
model = build_model("deepseek-chat").bind_tools(researcher_tools)

# Now the model can use all registered tools
response = await model.ainvoke("Research query")
```

## Tool Development Best Practices

1. **Clear Descriptions**: Provide detailed docstrings explaining what the tool does, when to use it, and what it returns.

2. **Type Hints**: Use proper type hints for all parameters and return values.

3. **Error Handling**: Include robust error handling and return meaningful error messages.

4. **Async Support**: Prefer async functions for I/O-bound operations (API calls, file operations).

5. **Parameter Validation**: Use Pydantic Field validators for complex parameter requirements.

6. **Testing**: Write tests for your custom tools before deploying.

## Example: Weather Tool

```python
from langchain_core.tools import tool
from fathom.tools import register_tool
import httpx

@register_tool
@tool
async def fetch_weather(city: str, units: str = "metric") -> str:
    """Fetch current weather for a city.

    Args:
        city: City name (e.g., "London", "New York")
        units: Temperature units - "metric" (Celsius) or "imperial" (Fahrenheit)

    Returns:
        Weather information including temperature, conditions, and humidity
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": city, "units": units, "appid": "YOUR_API_KEY"}
            )
            data = response.json()

            return f"Weather in {city}: {data['main']['temp']}°, {data['weather'][0]['description']}"
    except Exception as e:
        return f"Error fetching weather: {str(e)}"
```

## Registering Custom Tools in Your Application

To make your custom tools available, import them in your main application:

```python
# main.py
from fathom.tools import get_all_tools

# Import your custom tools module to register them
import fathom.tools.custom_tools_example  # This registers the tools

# Now get_all_tools() will include your custom tools
all_tools = get_all_tools()
```

## Tool Registry

The tool registry is a global list that stores all registered custom tools. You can inspect it:

```python
from fathom.tools.utils import _custom_tools_registry

print(f"Registered custom tools: {len(_custom_tools_registry)}")
for tool in _custom_tools_registry:
    print(f"  - {tool.name}: {tool.description}")
```

## Configuration

Tools can access the global configuration:

```python
from fathom.config.loader import ConfigLoader

settings = ConfigLoader()
api_key = settings.config["my_tool"]["api_key"]
```

Add tool-specific configuration to your `config.toml`:

```toml
[my_tool]
api_key = "your-api-key"
timeout = 30
max_retries = 3
```
