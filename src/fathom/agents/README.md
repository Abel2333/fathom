# Fathom Research Agent Architecture

This directory contains the modular implementation of the Fathom deep research agent system. The codebase has been split into logical, maintainable modules for better organization and scalability.

## Architecture Overview

The research agent follows a hierarchical multi-agent architecture:

```
┌─────────────────────────────────────────────────────┐
│                  Main Workflow                      │
│                  (workflow.py)                      │
└─────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌────────────────┐ ┌─────────────┐ ┌────────────────┐
│ Clarification  │ │Supervisor   │ │     Report     │
│ (clarification)│ │(supervisor) │ │    (report)    │
└────────────────┘ └─────────────┘ └────────────────┘
                         │
                    ┌────┴────┐
                    │Delegates│
                    └────┬────┘
                         │
                    ┌────▼───────┐
                    │Researcher  │
                    │(researcher)│
                    └────────────┘
```

## Module Structure

### 1. **clarification.py**

Handles user interaction and research scope clarification.

**Key Functions:**

- `clarify_with_user()`: Analyzes user messages and asks clarifying questions if needed
- `write_research_brief()`: Transforms user messages into a structured research brief

**When it runs:**

- First phase of the workflow
- Can optionally be disabled via config

**Outputs:**

- Research brief for the supervisor
- Clarifying questions to the user (if needed)

---

### 2. **supervisor.py**

Manages the overall research strategy and delegates work to researchers.

**Key Functions:**

- `supervisor()`: Plans research strategy and breaks down tasks
- `supervisor_tools()`: Executes supervisor tool calls (ConductResearch, think_tool, ResearchComplete)

**Available Tools:**

- `ConductResearch`: Delegate research to a sub-researcher
- `ResearchComplete`: Signal completion of research
- `think_tool`: Strategic reflection and planning

**Workflow:**

```
supervisor → supervisor_tools → supervisor (loop)
                  │
                  └──> END (when complete)
```

**Configuration:**

- `max_depth`: Maximum supervisor iterations
- `concurrency`: Maximum parallel research units

---

### 3. **researcher.py**

Individual researcher agent that conducts focused research on specific topics.

**Key Functions:**

- `researcher()`: Main research logic, calls LLM with tools
- `researcher_tools()`: Executes tool calls (search, think_tool, etc.)
- `compress_research()`: Synthesizes findings into a summary

**Available Tools:**

- All tools from `get_all_tools()` (search, custom tools)
- `think_tool`: Strategic reflection between searches

**Workflow:**

```
researcher → researcher_tools → researcher (loop)
                  │
                  └──> compress_research → END
```

**Configuration:**

- `max_tool_calls`: Maximum iterations per researcher

---

### 4. **report.py**

Generates the final comprehensive research report.

**Key Functions:**

- `final_report_generation()`: Synthesizes all research into a final report

**Inputs:**

- Research brief
- All collected notes from researchers
- Original user messages

**Outputs:**

- Final comprehensive research report

---

### 5. **workflow.py**

Assembles all components into the complete workflow.

**Main Export:**

- `deep_researcher`: Compiled LangGraph workflow

**Workflow Sequence:**

```
START
  ↓
clarify_with_user ←→ user (if needed)
  ↓
write_research_brief
  ↓
research_supervisor (supervisor subgraph)
  ↓
final_report_generation
  ↓
END
```

---

### 6. **research.py** (Entry Point)

Main entry point that re-exports all components for backward compatibility.

**Usage:**

```python
# Import the complete workflow
from fathom.agents.research import deep_researcher

# Or import specific components
from fathom.agents.research import supervisor, researcher
```

## Data Flow

### State Objects

**AgentState** (Main workflow state):

- `messages`: Conversation history with user
- `supervisor_messages`: Messages for supervisor subgraph
- `research_brief`: Generated research brief
- `notes`: Compressed research findings
- `raw_notes`: Raw research data
- `final_report`: Generated final report

**SupervisorState** (Supervisor subgraph):

- `supervisor_messages`: Supervisor conversation history
- `research_brief`: Research brief to guide research
- `notes`: Collected research notes
- `research_iterations`: Current iteration count
- `raw_notes`: Raw research data

**ResearcherState** (Researcher subgraph):

- `researcher_messages`: Researcher conversation history
- `research_topic`: Assigned research topic
- `tool_call_iterations`: Current iteration count
- `compressed_research`: Synthesized research summary
- `raw_notes`: Raw research findings

### Message Flow

1. **User Input** → `clarify_with_user`
   - Analyzes: Do we need clarification?
   - Output: Research brief or clarifying question

2. **Research Brief** → `supervisor`
   - Plans: How to break down research?
   - Delegates: Multiple researchers in parallel

3. **Research Topics** → `researcher` (parallel)
   - Searches: Web search, custom tools
   - Reflects: Uses think_tool for strategy
   - Compresses: Synthesizes findings

4. **Research Notes** → `final_report_generation`
   - Synthesizes: All findings into report
   - Output: Final comprehensive report

## Adding Custom Tools

Custom tools are automatically available to researchers through the `get_all_tools()` function:

```python
from langchain_core.tools import tool
from fathom.tools import register_tool

@register_tool
@tool
async def my_custom_tool(query: str) -> str:
    """Custom tool description."""
    # Your implementation
    return "result"
```

See `src/fathom/tools/README.md` for detailed tool development guide.

## Configuration

Key configuration options in `config.toml`:

```toml
[research]
allow_clarification = true  # Enable user clarification
concurrency = 3             # Max parallel researchers
max_depth = 5               # Max supervisor iterations
max_tool_calls = 10         # Max iterations per researcher
```

## Development Guidelines

### When to Modify Each Module

**clarification.py**:

- Change clarification logic
- Modify research brief generation

**supervisor.py**:

- Adjust research delegation strategy
- Add supervisor-level tools
- Modify concurrency handling

**researcher.py**:

- Change individual research logic
- Modify tool execution
- Adjust compression strategy

**report.py**:

- Change final report format
- Modify report generation prompts

**workflow.py**:

- Add/remove workflow steps
- Change workflow routing logic
- Add conditional branches

### Testing Individual Components

Each module can be tested independently:

```python
# Test clarification
from fathom.agents.clarification import clarify_with_user
result = await clarify_with_user(test_state)

# Test supervisor
from fathom.agents.supervisor import supervisor_subgraph
result = await supervisor_subgraph.ainvoke(test_state)

# Test researcher
from fathom.agents.researcher import researcher_subgraph
result = await researcher_subgraph.ainvoke(test_state)
```

## Debugging

Enable debug logging to see detailed execution:

```python
import logging
logging.getLogger("fathom.agents").setLevel(logging.DEBUG)
```

Each module logs at key decision points:

- Clarification needs
- Supervisor iterations
- Tool calls
- Research compression
- Report generation

## Dependencies Between Modules

```
workflow.py
  ├── clarification.py
  ├── supervisor.py
  │     └── researcher.py (imported at runtime)
  └── report.py

researcher.py
  └── tools/ (get_all_tools)
```

**Note:** The supervisor imports `researcher_subgraph` at runtime inside `supervisor_tools()` to avoid circular dependencies.

## Future Enhancements

Potential areas for expansion:

1. **Multi-turn Clarification**: Allow multiple rounds of clarification
2. **Dynamic Tool Selection**: Let supervisor choose which tools researchers use
3. **Research Prioritization**: Rank research tasks by importance
4. **Incremental Reporting**: Generate partial reports during research
5. **Research Caching**: Cache research results for similar queries
6. **Quality Scoring**: Assess research quality and trigger re-research if needed

## Migration Guide

If you have existing code importing from `research.py`, no changes needed:

```python
# Old code (still works)
from fathom.agents.research import deep_researcher

# New code (also works, more specific)
from fathom.agents.workflow import deep_researcher
from fathom.agents.supervisor import supervisor_subgraph
```

## File Size Comparison

**Before:**

- `research.py`: 693 lines

**After:**

- `clarification.py`: ~160 lines
- `supervisor.py`: ~270 lines
- `researcher.py`: ~250 lines
- `report.py`: ~75 lines
- `workflow.py`: ~50 lines
- `research.py`: ~60 lines (re-exports)

**Total:** ~865 lines (including documentation and better structure)
