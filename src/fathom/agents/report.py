"""Final report generation module for the research agent.

This module handles generating the comprehensive final research report
from all collected research findings.
"""

from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string

from fathom.config.loader import ConfigLoader
from fathom.config.logging import get_logger
from fathom.models.schema import AgentState
from fathom.prompts import final_report_generation_prompt
from fathom.tools.search import build_model
from fathom.tools.utils import get_today_str

settings = ConfigLoader()
logger = get_logger(__name__)


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
