"""Final report generation module for the research agent.

This module handles generating the comprehensive final research report
from all collected research findings.
"""

from datetime import datetime
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string

from fathom.config.loader import ConfigLoader
from fathom.config.logging import get_logger
from fathom.models.schema import AgentState
from fathom.prompts import final_report_generation_prompt
from fathom.tools.search import build_model
from fathom.tools.utils import get_today_str

settings = ConfigLoader()
logger = get_logger(__name__)


def save_report_to_file(content: str, research_brief: str = "") -> str:
    """
    Save the final report to a markdown file.

    Args:
        content: The report content to save
        research_brief: Brief description of the research topic for filename

    Returns:
        Path to the saved file
    """
    # Get output directory from config
    output_dir = settings.config.get("output", {}).get("dir", "./reports")
    output_path = Path(output_dir)

    # Create directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Try to extract title from report content (first heading)
    title_from_content = ""
    if content:
        lines = content.split("\n")
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith("# "):
                # Found a markdown H1 heading
                title_from_content = line.lstrip("# ").strip()
                break

    # Create a safe filename
    if title_from_content:
        # Use the extracted title from report
        safe_title = "".join(
            c
            for c in title_from_content[:50]
            if c.isalnum() or c in (" ", "-", "_", "：", ":")
        )
        safe_title = (
            safe_title.strip().replace(" ", "_").replace("：", "_").replace(":", "_")
        )
        filename = f"report_{timestamp}_{safe_title}.md"
    elif research_brief:
        # Fallback to research brief (first 30 chars)
        safe_brief = "".join(
            c for c in research_brief[:30] if c.isalnum() or c in (" ", "-", "_")
        )
        safe_brief = safe_brief.strip().replace(" ", "_")
        filename = f"report_{timestamp}_{safe_brief}.md"
    else:
        # Last resort: just timestamp
        filename = f"report_{timestamp}.md"

    file_path = output_path / filename

    # Write content to file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Report saved to: {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"Failed to save report to file: {e}")
        return ""


async def final_report_generation(state: AgentState):
    """
    Generate the final comprehensive research report with retry logic for token limits.

    This function takes all collected research findings and synthesizes them into a
    well-structured, comprehensive final report using the configured report generation model.

    Args:
        state: Agent state containing research findings and context

    Returns:
        Dictionary containing the final report and cleared state
    """
    notes = state.get("notes", [])
    cleared_state = {"notes": {"type": "override", "value": []}}
    findings = "\n".join(notes)

    writer_model = build_model(settings.report_model)
    logger.info("FINAL REPORT: starting generation")
    logger.debug(
        f"Using report model: {settings.report_model} | notes collected: {len(notes)}"
    )

    max_retries = 3

    async def _generate_with_stream(messages):
        """Try streaming generation for large responses with real-time output."""
        chunks: list[str] = []

        if hasattr(writer_model, "astream"):
            logger.info("Using astream for report generation")
            async for chunk in writer_model.astream(messages):
                text = getattr(chunk, "content", None) or getattr(chunk, "text", None)
                if isinstance(text, list):
                    for t in text:
                        if t:
                            chunks.append(str(t))
                            print(str(t), end="", flush=True)
                elif text:
                    chunks.append(str(text))
                    print(str(text), end="", flush=True)
            print()  # Final newline
            return "".join(chunks).strip()

        if hasattr(writer_model, "astream_events"):
            logger.info("Using astream_events for report generation")
            async for event in writer_model.astream_events(messages, version="v2"):
                if event.get("event") == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    text = getattr(chunk, "content", None)
                    if isinstance(text, list):
                        for t in text:
                            if t:
                                chunks.append(str(t))
                                print(str(t), end="", flush=True)
                    elif text:
                        chunks.append(str(text))
                        print(str(text), end="", flush=True)
            print()  # Final newline
            return "".join(chunks).strip()

        raise AttributeError("Streaming not supported by this model")

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Report generation attempt {attempt} of {max_retries}")
            final_report_prompt = final_report_generation_prompt.format(
                research_brief=state.get("research_brief", ""),
                messages=get_buffer_string(state.get("messages", [])),
                findings=findings,
                date=get_today_str(),
            )

            prompt_messages = [HumanMessage(content=final_report_prompt)]

            try:
                logger.debug("Attempting streaming generation for final report")
                streamed_content = await _generate_with_stream(prompt_messages)
                if not streamed_content:
                    raise ValueError("Stream returned empty content")
                final_report = AIMessage(content=streamed_content)
            except Exception as stream_err:
                logger.warning(
                    "Streaming failed or unsupported; falling back to ainvoke",
                    exc_info=stream_err,
                )
                final_report = await writer_model.ainvoke(prompt_messages)

            logger.info("Final report generation succeeded")

            # Save report to markdown file
            research_brief = state.get("research_brief", "") or ""
            # Ensure content is a string (handle both str and list types)
            report_content = str(final_report.content) if final_report.content else ""
            saved_path = save_report_to_file(report_content, research_brief)
            if saved_path:
                print(f"\n✓ Report saved to: {saved_path}\n")

            return {
                "final_report": final_report.content,
                "messages": [final_report],
                **cleared_state,
            }
        except Exception as e:
            logger.exception("Final report generation failed")
            if attempt == max_retries:
                logger.error("Maximum report generation retries exceeded")
                return {
                    "final_report": f"Error generating final report: {e}",
                    "messages": [
                        AIMessage(content="Report generation failed after retries")
                    ],
                    **cleared_state,
                }

    # Fallback safety (should not be reached)
    logger.error("Unexpected fallthrough in report generation loop")
    return {
        "final_report": "Error generating final report: Maximum retries exceeded",
        "messages": [
            AIMessage(content="Report generation failed after maximum retries")
        ],
        **cleared_state,
    }
