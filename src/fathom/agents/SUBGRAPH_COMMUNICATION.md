# How Subgraphs Work Together in Fathom

This document explains the communication and data flow between the supervisor and researcher subgraphs.

## Overview

The Fathom research agent uses **nested subgraphs** where the supervisor delegates work to multiple researcher subgraphs running in parallel. Here's how they communicate:

## The Key Mechanism: Tool Calls as Subgraph Invocations

### Step-by-Step Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    SUPERVISOR SUBGRAPH                       │
│                                                              │
│  1. supervisor() node                                        │
│     ├─ LLM decides: "I need to research X, Y, Z"           │
│     └─ Calls tool: ConductResearch(topic="X")              │
│                                                              │
│  2. supervisor_tools() node                                  │
│     ├─ Detects: ConductResearch tool call                  │
│     ├─ Invokes: researcher_subgraph.ainvoke(...)           │
│     │                                                        │
│     │   ┌──────────────────────────────────────┐           │
│     │   │   RESEARCHER SUBGRAPH (runs here)    │           │
│     │   │                                       │           │
│     │   │  researcher → researcher_tools →     │           │
│     │   │  researcher → researcher_tools →     │           │
│     │   │  compress_research → RETURN          │           │
│     │   │                                       │           │
│     │   │  Returns: {                          │           │
│     │   │    "compressed_research": "...",     │           │
│     │   │    "raw_notes": ["..."]              │           │
│     │   │  }                                    │           │
│     │   └──────────────────────────────────────┘           │
│     │                                                        │
│     ├─ Receives: Research results                          │
│     └─ Creates: ToolMessage with results                   │
│                                                              │
│  3. Back to supervisor() node                               │
│     ├─ Sees: ToolMessage with research findings            │
│     └─ Decides: Continue or call ResearchComplete          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Detailed Code Flow

### 1. Supervisor Calls ConductResearch Tool

**Location:** `supervisor.py` - `supervisor()` function

```python
# The LLM is bound with tools including ConductResearch
lead_researcher_tools = [ConductResearch, ResearchComplete, think_tool]
research_model = build_model(settings.research_model).bind_tools(lead_researcher_tools)

# LLM generates a response with tool calls
response = await research_model.ainvoke(supervisor_messages)

# Response contains tool_calls like:
# [
#   {
#     "name": "ConductResearch",
#     "args": {"research_topic": "Latest developments in AI safety"},
#     "id": "call_123"
#   }
# ]
```

### 2. Supervisor Tools Executes the Tool Call

**Location:** `supervisor.py` - `supervisor_tools()` function (lines 160-186)

```python
# Extract ConductResearch tool calls
conduct_research_calls = [
    tool_call
    for tool_call in most_recent_message.tool_calls
    if tool_call["name"] == "ConductResearch"
]

if conduct_research_calls:
    # Import the researcher subgraph
    from fathom.agents.researcher import researcher_subgraph

    # Create parallel research tasks
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

    # Execute all researchers in parallel
    tool_results = await asyncio.gather(*research_tasks)

    # tool_results is a list of dicts:
    # [
    #   {
    #     "compressed_research": "Research findings about AI safety...",
    #     "raw_notes": ["Note 1", "Note 2"]
    #   },
    #   ...
    # ]
```

### 3. Convert Research Results to Tool Messages

**Location:** `supervisor.py` - `supervisor_tools()` function (lines 188-201)

```python
# Create tool messages with research results
for observation, tool_call in zip(tool_results, allowed_conduct_research_calls):
    all_tool_messages.append(
        ToolMessage(
            content=observation.get("compressed_research", "Error..."),
            name=tool_call["name"],
            tool_call_id=tool_call["id"],  # Links back to original tool call
        )
    )

# Return these messages to the supervisor
return Command(
    goto="supervisor",
    update={"supervisor_messages": all_tool_messages}
)
```

### 4. Supervisor Receives Results and Continues

**Location:** `supervisor.py` - `supervisor()` function

```python
# The supervisor now sees the ToolMessages in its conversation
# supervisor_messages = [
#   SystemMessage("You are a research supervisor..."),
#   HumanMessage("Research brief: ..."),
#   AIMessage(tool_calls=[{"name": "ConductResearch", ...}]),
#   ToolMessage(content="Research findings...", tool_call_id="call_123"),
# ]

# The LLM can now:
# 1. Call more ConductResearch tools for additional research
# 2. Call think_tool to reflect on findings
# 3. Call ResearchComplete when satisfied
response = await research_model.ainvoke(supervisor_messages)
```

## State Isolation

Each subgraph has its own isolated state:

### Supervisor State
```python
{
    "supervisor_messages": [...],  # Supervisor's conversation
    "research_brief": "...",
    "research_iterations": 3,
    "notes": [...],
    "raw_notes": [...]
}
```

### Researcher State (separate instance per researcher)
```python
{
    "researcher_messages": [...],  # Researcher's conversation
    "research_topic": "AI safety developments",
    "tool_call_iterations": 5,
    "compressed_research": "...",  # Output
    "raw_notes": [...]              # Output
}
```

**Key Point:** The researcher subgraph doesn't see the supervisor's messages, and vice versa. They communicate only through:
- **Input:** Research topic (string)
- **Output:** Compressed research + raw notes (dict)

## Parallel Execution

Multiple researchers can run simultaneously:

```python
# If supervisor calls ConductResearch 3 times:
research_tasks = [
    researcher_subgraph.ainvoke({"research_topic": "Topic A", ...}),
    researcher_subgraph.ainvoke({"research_topic": "Topic B", ...}),
    researcher_subgraph.ainvoke({"research_topic": "Topic C", ...}),
]

# All run in parallel
results = await asyncio.gather(*research_tasks)

# Results come back as a list:
# [
#   {"compressed_research": "Findings A", "raw_notes": [...]},
#   {"compressed_research": "Findings B", "raw_notes": [...]},
#   {"compressed_research": "Findings C", "raw_notes": [...]},
# ]
```

## Complete Example Flow

Let's trace a complete example:

### User Query
"Research the latest developments in AI safety and quantum computing"

### Flow

```
1. CLARIFICATION PHASE
   └─> write_research_brief()
       Output: "Research brief: Investigate recent AI safety developments
                and quantum computing breakthroughs in 2024-2025"

2. SUPERVISOR ITERATION 1
   supervisor() receives research brief
   ├─> LLM thinks: "I need to research two topics separately"
   └─> Calls tools:
       - ConductResearch(topic="AI safety developments 2024-2025")
       - ConductResearch(topic="Quantum computing breakthroughs 2024-2025")

3. SUPERVISOR_TOOLS EXECUTION
   ├─> Launches 2 researcher subgraphs in parallel
   │
   ├─> RESEARCHER A (AI safety)
   │   ├─ researcher(): Calls tavily_search("AI safety 2024")
   │   ├─ researcher_tools(): Executes search, returns results
   │   ├─ researcher(): Calls think_tool("I found X, need Y")
   │   ├─ researcher_tools(): Records reflection
   │   ├─ researcher(): Calls tavily_search("AI safety regulations")
   │   ├─ researcher_tools(): Executes search
   │   ├─ compress_research(): Synthesizes findings
   │   └─> Returns: {"compressed_research": "AI safety summary...", ...}
   │
   └─> RESEARCHER B (Quantum computing)
       ├─ researcher(): Calls tavily_search("quantum computing 2024")
       ├─ researcher_tools(): Executes search
       ├─ researcher(): Calls tavily_search("quantum algorithms")
       ├─ researcher_tools(): Executes search
       ├─ compress_research(): Synthesizes findings
       └─> Returns: {"compressed_research": "Quantum summary...", ...}

   ├─> Both complete, results gathered
   └─> Creates ToolMessages with both research summaries

4. SUPERVISOR ITERATION 2
   supervisor() receives ToolMessages
   ├─> LLM sees both research summaries
   ├─> LLM thinks: "I have comprehensive findings"
   └─> Calls tool: ResearchComplete()

5. SUPERVISOR_TOOLS EXECUTION
   ├─> Detects ResearchComplete
   ├─> Extracts all notes from conversation
   └─> Returns to main workflow with notes

6. FINAL REPORT GENERATION
   final_report_generation()
   ├─> Receives all research notes
   └─> Generates comprehensive report
```

## Key Design Patterns

### 1. Tool Calls as Subgraph Invocations
The supervisor doesn't directly call researcher functions. Instead:
- LLM generates tool calls
- Tool execution handler invokes subgraphs
- Results return as tool messages

### 2. State Boundaries
Each subgraph maintains its own state:
- Supervisor tracks: overall strategy, iterations, collected notes
- Researcher tracks: search results, tool calls, compression

### 3. Async Parallelism
```python
# Multiple researchers run truly in parallel
await asyncio.gather(*research_tasks)
```

### 4. Type Safety
```python
# Researcher subgraph has defined input/output schemas
researcher_builder = StateGraph(
    ResearcherState,           # Input schema
    output_schema=ResearcherOutputState  # Output schema
)

# Output is guaranteed to have these fields:
# - compressed_research: str
# - raw_notes: list[str]
```

## Debugging Tips

### See Supervisor Decisions
```python
logger.info(f"Supervisor calling tools: {', '.join(tool_names)}")
```

### See Researcher Execution
```python
logger.info(f"Researcher executing tool: {tool_call['name']}")
```

### Inspect State Transitions
```python
# In supervisor_tools
print(f"Launching {len(research_tasks)} researchers")
print(f"Results: {[r.get('compressed_research')[:50] for r in tool_results]}")
```

## Why This Architecture?

### Benefits

1. **Modularity**: Each subgraph is independent and testable
2. **Parallelism**: Multiple researchers run simultaneously
3. **Scalability**: Easy to add more researchers or change concurrency
4. **State Isolation**: No accidental state leakage between agents
5. **Type Safety**: Clear input/output contracts
6. **LLM-Driven**: Supervisor decides what to research, not hardcoded logic

### Trade-offs

1. **Complexity**: More moving parts than a single agent
2. **Debugging**: Need to trace through multiple subgraphs
3. **Token Usage**: Each subgraph has its own conversation history

## Summary

The supervisor and researcher subgraphs communicate through:

1. **Supervisor → Researcher**: Via `researcher_subgraph.ainvoke()` with research topic
2. **Researcher → Supervisor**: Via return value `{"compressed_research": "...", "raw_notes": [...]}`
3. **Supervisor sees results**: As `ToolMessage` objects in its conversation

This creates a clean separation where:
- Supervisor = Strategic planning and delegation
- Researcher = Tactical execution and information gathering
- Communication = Structured input/output, no shared state
