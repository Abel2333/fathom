# API Documentation

This document describes how to use Fathom programmatically in your Python code.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Configuration](#configuration)
- [Custom Tools](#custom-tools)
- [Advanced Usage](#advanced-usage)
- [API Reference](#api-reference)

## Basic Usage

### Running a Research Query

```python
import asyncio
from fathom.agents.workflow import research_workflow

async def main():
    # Define your research query
    query = "Analyze the impact of AI on healthcare in 2024-2025"

    # Run the research workflow
    result = await research_workflow.ainvoke({
        "messages": [{"role": "user", "content": query}]
    })

    # Get the final report
    final_report = result.get("final_report", "")
    print(final_report)

# Run the async function
asyncio.run(main())
```

### Accessing Research Notes

```python
async def main():
    result = await research_workflow.ainvoke({
        "messages": [{"role": "user", "content": "Your query here"}]
    })

    # Access different parts of the result
    final_report = result.get("final_report", "")
    notes = result.get("notes", [])
    research_brief = result.get("research_brief", "")

    print(f"Research Brief: {research_brief}")
    print(f"Number of notes: {len(notes)}")
    print(f"Report length: {len(final_report)} characters")
```

## Configuration

### Loading Custom Configuration

```python
from fathom.config.loader import ConfigLoader

# Load default configuration
config = ConfigLoader()

# Access configuration values
print(config.config["llm"]["provider"])
print(config.config["research"]["concurrency"])

# Access model names
print(config.report_model)
print(config.research_model)
print(config.summary_model)
```

### Programmatic Configuration

```python
from fathom.config.loader import ConfigLoader

# Create custom configuration
config = ConfigLoader()

# Override settings
config.config["research"]["concurrency"] = 8
config.config["research"]["max_depth"] = 3
config.config["output"]["language"] = "English"

# Use custom config in your workflow
# (Note: You'll need to pass this to the workflow initialization)
```

## Custom Tools

### Creating a Custom Tool

```python
from langchain_core.tools import tool
from fathom.tools.utils import register_tool

@register_tool
@tool
def my_custom_tool(query: str) -> str:
    """
    Custom tool for specialized research.

    Args:
        query: The search query

    Returns:
        Research results as a string
    """
    # Your custom logic here
    result = f"Custom research for: {query}"
    return result
```

### Using Custom Tools

Once registered, your custom tool will be automatically available to researchers:

```python
from fathom.tools.utils import get_all_tools

# Get all tools (including your custom tool)
tools = get_all_tools()
print([tool.name for tool in tools])
# Output: ['tavily_search', 'think_tool', 'my_custom_tool']
```

### Example: Database Query Tool

```python
from langchain_core.tools import tool
from fathom.tools.utils import register_tool
import sqlite3

@register_tool
@tool
def query_database(sql: str) -> str:
    """
    Query a local database for research data.

    Args:
        sql: SQL query to execute

    Returns:
        Query results as formatted string
    """
    conn = sqlite3.connect('research.db')
    cursor = conn.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    conn.close()

    return "\n".join([str(row) for row in results])
```

## Advanced Usage

### Streaming Research Progress

```python
import asyncio
from fathom.agents.workflow import research_workflow

async def stream_research(query: str):
    """Stream research progress in real-time."""

    async for event in research_workflow.astream({
        "messages": [{"role": "user", "content": query}]
    }):
        # Process each event
        if "supervisor" in event:
            print(f"Supervisor: {event['supervisor']}")
        elif "researcher" in event:
            print(f"Researcher: {event['researcher']}")
        elif "final_report" in event:
            print(f"Report: {event['final_report']}")

asyncio.run(stream_research("Your query here"))
```

### Running Individual Agents

#### Clarification Agent

```python
from fathom.agents.clarification import clarify_with_user

async def check_clarification(query: str):
    result = await clarify_with_user({
        "messages": [{"role": "user", "content": query}]
    })

    if result.get("need_clarification"):
        print(f"Question: {result['question']}")
    else:
        print(f"Ready to research: {result['verification']}")
```

#### Supervisor Agent

```python
from fathom.agents.supervisor import supervisor_subgraph

async def run_supervisor(research_brief: str):
    result = await supervisor_subgraph.ainvoke({
        "research_brief": research_brief,
        "supervisor_messages": []
    })

    notes = result.get("notes", [])
    print(f"Collected {len(notes)} research notes")
```

#### Researcher Agent

```python
from fathom.agents.researcher import researcher_subgraph

async def run_researcher(topic: str):
    result = await researcher_subgraph.ainvoke({
        "research_topic": topic,
        "researcher_messages": []
    })

    compressed = result.get("compressed_research", "")
    raw_notes = result.get("raw_notes", [])

    print(f"Compressed research: {compressed[:200]}...")
    print(f"Raw notes count: {len(raw_notes)}")
```

### Custom Search Implementation

```python
from langchain_core.tools import tool
from fathom.tools.utils import register_tool

@register_tool
@tool
async def custom_search(queries: list[str]) -> dict:
    """
    Custom search implementation using your preferred API.

    Args:
        queries: List of search queries

    Returns:
        Structured search results
    """
    results = []

    for query in queries:
        # Your custom search logic
        result = {
            "url": "https://example.com",
            "title": f"Results for {query}",
            "summary": "Custom search results..."
        }
        results.append(result)

    return {
        "queries": queries,
        "results": results
    }
```

## API Reference

### Core Functions

#### `research_workflow.ainvoke(input: dict) -> dict`

Main entry point for running research.

**Parameters:**
- `input` (dict): Input dictionary with:
  - `messages` (list): List of message dictionaries with `role` and `content`

**Returns:**
- `dict`: Result dictionary with:
  - `final_report` (str): Generated research report
  - `notes` (list): Research notes collected
  - `research_brief` (str): Processed research brief
  - `messages` (list): Conversation history

**Example:**
```python
result = await research_workflow.ainvoke({
    "messages": [{"role": "user", "content": "Your query"}]
})
```

### Configuration Classes

#### `ConfigLoader()`

Loads and manages configuration from `config.toml`.

**Attributes:**
- `config` (dict): Full configuration dictionary
- `report_model` (str): Model name for report generation
- `research_model` (str): Model name for research
- `summary_model` (str): Model name for summarization
- `clarify_model` (str): Model name for clarification

**Methods:**
- `get(key: str, default: Any) -> Any`: Get configuration value

**Example:**
```python
config = ConfigLoader()
concurrency = config.config["research"]["concurrency"]
```

### Tool Functions

#### `get_all_tools() -> list[BaseTool]`

Returns all available tools for researchers.

**Returns:**
- `list[BaseTool]`: List of all registered tools

**Example:**
```python
from fathom.tools.utils import get_all_tools

tools = get_all_tools()
print([tool.name for tool in tools])
```

#### `register_tool(tool_func: BaseTool) -> BaseTool`

Decorator to register custom tools.

**Parameters:**
- `tool_func` (BaseTool): Tool function decorated with `@tool`

**Returns:**
- `BaseTool`: The registered tool

**Example:**
```python
from fathom.tools.utils import register_tool
from langchain_core.tools import tool

@register_tool
@tool
def my_tool(query: str) -> str:
    return f"Result for {query}"
```

### Search Functions

#### `tavily_search(queries: list[str], max_results: int = 5, topic: str = "general") -> dict`

Performs web search using Tavily API.

**Parameters:**
- `queries` (list[str]): List of search queries
- `max_results` (int): Maximum results per query (default: 5)
- `topic` (str): Topic filter - "general", "news", or "finance" (default: "general")

**Returns:**
- `dict`: Search results with:
  - `queries` (list): Original queries
  - `results` (list): List of result dictionaries
  - `formatted_output` (str): Markdown-formatted results

**Example:**
```python
from fathom.tools.search import tavily_search

results = await tavily_search(
    queries=["AI in healthcare", "medical AI applications"],
    max_results=5,
    topic="general"
)
```

### Report Functions

#### `save_report_to_file(content: str, research_brief: str = "") -> str`

Saves report to markdown file.

**Parameters:**
- `content` (str): Report content
- `research_brief` (str): Research brief for filename (optional)

**Returns:**
- `str`: Path to saved file

**Example:**
```python
from fathom.agents.report import save_report_to_file

path = save_report_to_file(
    content="# My Report\n\nContent here...",
    research_brief="AI Healthcare Analysis"
)
print(f"Saved to: {path}")
```

## Error Handling

### Handling Research Failures

```python
async def safe_research(query: str):
    try:
        result = await research_workflow.ainvoke({
            "messages": [{"role": "user", "content": query}]
        })
        return result
    except Exception as e:
        print(f"Research failed: {e}")
        return {"final_report": "Error occurred", "notes": []}
```

### Timeout Handling

```python
import asyncio

async def research_with_timeout(query: str, timeout: int = 300):
    """Run research with timeout (default 5 minutes)."""
    try:
        result = await asyncio.wait_for(
            research_workflow.ainvoke({
                "messages": [{"role": "user", "content": query}]
            }),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        print(f"Research timed out after {timeout} seconds")
        return None
```

## Best Practices

### 1. Use Async/Await

Always use async functions when calling Fathom APIs:

```python
# Good
async def main():
    result = await research_workflow.ainvoke(...)

# Bad
def main():
    result = research_workflow.ainvoke(...)  # Won't work!
```

### 2. Handle Errors Gracefully

```python
async def robust_research(query: str):
    try:
        result = await research_workflow.ainvoke({
            "messages": [{"role": "user", "content": query}]
        })

        if not result.get("final_report"):
            print("Warning: Empty report generated")

        return result
    except Exception as e:
        print(f"Error: {e}")
        return None
```

### 3. Configure Appropriately

```python
from fathom.config.loader import ConfigLoader

config = ConfigLoader()

# Adjust for your use case
if quick_research:
    config.config["research"]["max_depth"] = 3
    config.config["research"]["concurrency"] = 2
else:
    config.config["research"]["max_depth"] = 6
    config.config["research"]["concurrency"] = 8
```

### 4. Monitor Progress

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Run research
result = await research_workflow.ainvoke(...)
```

## Examples

### Complete Example: Research Pipeline

```python
import asyncio
from fathom.agents.workflow import research_workflow
from fathom.agents.report import save_report_to_file

async def research_pipeline(query: str):
    """Complete research pipeline with error handling."""

    print(f"Starting research: {query}")

    try:
        # Run research
        result = await research_workflow.ainvoke({
            "messages": [{"role": "user", "content": query}]
        })

        # Extract results
        report = result.get("final_report", "")
        notes = result.get("notes", [])
        brief = result.get("research_brief", "")

        # Save report
        if report:
            path = save_report_to_file(report, brief)
            print(f"Report saved to: {path}")

        # Print summary
        print(f"\nResearch Summary:")
        print(f"- Brief: {brief[:100]}...")
        print(f"- Notes collected: {len(notes)}")
        print(f"- Report length: {len(report)} characters")

        return result

    except Exception as e:
        print(f"Research failed: {e}")
        return None

# Run the pipeline
asyncio.run(research_pipeline("Your research query here"))
```

---

For more examples, see the `tests/` directory in the repository.
