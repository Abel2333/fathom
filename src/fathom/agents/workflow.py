"""Main workflow assembly module for the deep research agent.

This module assembles all the components (clarification, supervisor, researcher,
and report generation) into the complete deep research workflow.
"""

from langgraph.graph import END, START, StateGraph

from fathom.models.schema import AgentInputState, AgentState

# Import all workflow components
from fathom.agents.clarification import clarify_with_user, write_research_brief
from fathom.agents.report import final_report_generation
from fathom.agents.supervisor import supervisor_subgraph


# Main Deep Researcher Graph Construction
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
