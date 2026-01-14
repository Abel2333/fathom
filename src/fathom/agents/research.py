"""Research agent module - main entry point.

This module serves as the main entry point for the research agent system.
The implementation has been split into logical modules for better maintainability:

- clarification.py: User clarification and research brief generation
- supervisor.py: Research supervisor agent and delegation logic
- researcher.py: Individual researcher agent and research execution
- report.py: Final report generation
- workflow.py: Main workflow assembly

All exports are re-exported here for backward compatibility.
"""

# Re-export clarification components
from fathom.agents.clarification import (
    clarify_with_user,
    write_research_brief,
)

# Re-export report generation
from fathom.agents.report import final_report_generation

# Re-export researcher components
from fathom.agents.researcher import (
    compress_research,
    researcher,
    researcher_subgraph,
    researcher_tools,
)

# Re-export supervisor components
from fathom.agents.supervisor import (
    supervisor,
    supervisor_subgraph,
    supervisor_tools,
)

# Re-export main workflow
from fathom.agents.workflow import deep_researcher, deep_researcher_builder

__all__ = [
    # Clarification
    "clarify_with_user",
    "write_research_brief",
    # Supervisor
    "supervisor",
    "supervisor_tools",
    "supervisor_subgraph",
    # Researcher
    "researcher",
    "researcher_tools",
    "compress_research",
    "researcher_subgraph",
    # Report
    "final_report_generation",
    # Workflow
    "deep_researcher",
    "deep_researcher_builder",
]
