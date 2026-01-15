import argparse
import asyncio
import sys

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from fathom.agents.research import deep_researcher
from fathom.config.logging import LoggerSetup, get_logger
from fathom.models.schema import AgentInputState
from fathom.tools.search import get_langfuse_handler


def _print_status(message: str, prefix: str = "→"):
    """Print a status message with formatting."""
    print(f"\n{prefix} {message}", flush=True)


async def _run(prompt: str) -> str:
    """Run the deep research workflow with the provided user prompt."""
    LoggerSetup.setup_logging()
    logger = get_logger(__name__)
    logger.info("Starting Fathom Deep Research Agent")
    logger.debug(f"User prompt: {prompt[:200]}{'...' if len(prompt) > 200 else ''}")

    _print_status("🔍 Starting Fathom Deep Research Agent", "")
    _print_status(
        f"Research Query: {prompt[:100]}{'...' if len(prompt) > 100 else ''}", "📝"
    )

    initial_state: AgentInputState = {"messages": [HumanMessage(content=prompt)]}

    final_report = ""
    current_phase = None
    researcher_count = 0

    # Get Langfuse handler for workflow-level tracing
    langfuse_handler = get_langfuse_handler()
    stream_config: RunnableConfig | None = None
    if langfuse_handler:
        stream_config = RunnableConfig(callbacks=[langfuse_handler])
        logger.info("Langfuse tracing enabled for workflow")

    try:
        async for event in deep_researcher.astream(initial_state, config=stream_config):
            # Track which node is executing
            for node_name, node_state in event.items():
                if node_name == "clarify_with_user":
                    if current_phase != "clarify":
                        _print_status("Analyzing your request...", "🤔")
                        current_phase = "clarify"

                elif node_name == "write_research_brief":
                    if current_phase != "brief":
                        _print_status("Creating research plan...", "📋")
                        current_phase = "brief"

                elif node_name == "research_supervisor":
                    if current_phase != "research":
                        _print_status("Starting research phase...", "🔬")
                        current_phase = "research"

                    # Count researchers and searches from notes
                    notes = node_state.get("notes", [])
                    if len(notes) > researcher_count:
                        researcher_count = len(notes)
                        _print_status(
                            f"Research findings collected: {researcher_count}", "📊"
                        )

                elif node_name == "final_report_generation":
                    if current_phase != "report":
                        _print_status("Generating final report...", "📝")
                        print()  # Empty line before report
                        current_phase = "report"

                    # Get the final report
                    final_report = node_state.get("final_report", "")

    except Exception:
        logger.exception("Workflow failed")
        _print_status("❌ Research workflow failed. Check logs for details.", "")
        raise
    finally:
        # Flush Langfuse traces if handler exists
        if langfuse_handler:
            try:
                # Get the Langfuse client and flush traces
                from fathom.tools.search import _langfuse_client
                if _langfuse_client:
                    _langfuse_client.flush()
                    logger.debug("Langfuse traces flushed successfully")
            except Exception as e:
                logger.debug(f"Could not flush Langfuse traces: {e}")

    logger.info("Fathom session completed")
    print()  # Empty line after report
    _print_status("✅ Research completed!", "")
    return final_report


def main():
    """CLI entry point: runs the deep research agent on a prompt."""
    parser = argparse.ArgumentParser(
        description="Fathom Deep Research Agent CLI",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        help="Research request to run. If omitted, read from stdin.",
    )
    args = parser.parse_args()

    prompt = args.prompt or sys.stdin.read().strip()
    if not prompt:
        parser.error("Please provide a prompt (argument or stdin).")

    final_report = asyncio.run(_run(prompt))
    print(final_report)


if __name__ == "__main__":
    main()
