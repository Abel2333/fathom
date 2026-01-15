"""Search and summarization tools for the Deep Research agent."""

import asyncio
import os
from typing import Annotated, Dict, Literal, Optional, cast

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.tools import InjectedToolArg, tool
from tavily import AsyncTavilyClient

from fathom import prompts
from fathom.config.loader import ConfigLoader
from fathom.config.logging import get_logger
from fathom.models.extended import ChatDeepSeekReasoningAware
from fathom.models.schema import Summary

TAVILY_SEARCH_DESCRIPTION = (
    "A search engine optimized for comprehensive, accurate, and trusted results. "
    "Useful for when you need to answer questions about current events."
)

load_dotenv()

# Get settings from TOML
settings = ConfigLoader()

# Get logger
logger = get_logger(__name__)

# Initialize Langfuse callback handler if enabled
_langfuse_handler = None
_langfuse_client = None  # Keep reference to prevent garbage collection


def get_langfuse_handler():
    """Get or initialize the Langfuse callback handler."""
    global _langfuse_handler, _langfuse_client

    if _langfuse_handler is not None:
        return _langfuse_handler

    # Check if Langfuse is enabled in config
    langfuse_config = settings.config.get("langfuse", {})
    if not langfuse_config.get("enabled", False):
        logger.debug("Langfuse tracing is disabled in config")
        return None

    # Check if required environment variables are set
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        logger.warning(
            "Langfuse is enabled but LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY "
            "environment variables are not set. Tracing will be disabled."
        )
        return None

    try:
        # Import Langfuse client and callback handler
        from langfuse import Langfuse
        from langfuse.langchain import CallbackHandler

        # Get host from config or environment variable
        host = langfuse_config.get("host") or os.getenv("LANGFUSE_HOST")

        # Initialize the Langfuse client first (required for v2.0+)
        # Keep reference to prevent garbage collection
        if host:
            _langfuse_client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
            )
        else:
            _langfuse_client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
            )

        # Now create the callback handler
        _langfuse_handler = CallbackHandler()

        logger.info("Langfuse tracing initialized successfully")
        return _langfuse_handler

    except ImportError:
        logger.warning(
            "Langfuse is enabled but 'langfuse' package is not installed. "
            "Install it with: uv add langfuse"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse: {e}")
        return None


def build_model(model_name: str) -> BaseChatModel:
    """Instantiate the summarization model based on configuration with Langfuse tracing."""
    # Get Langfuse handler if available
    langfuse_handler = get_langfuse_handler()

    # Build model configuration
    model_config = {
        "model": model_name,
        "api_key": settings.config["llm"].get("api_key"),
        "api_base": settings.config["llm"].get("base_url"),
        "temperature": settings.config["llm"].get("temperature", 0.0),
        "timeout": settings.config["llm"].get("timeout", 60),
        # Add retry configuration to handle rate limits better
        "max_retries": settings.config["llm"].get("max_retries", 3),
    }

    # Add max_tokens if specified in config (optional)
    max_tokens = settings.config["llm"].get("max_tokens")
    if max_tokens:
        model_config["max_tokens"] = max_tokens

    # Add Langfuse callback if available
    if langfuse_handler:
        model_config["callbacks"] = [langfuse_handler]
        logger.debug(f"Building model '{model_name}' with Langfuse tracing enabled")
    else:
        logger.debug(f"Building model '{model_name}' without Langfuse tracing")

    return ChatDeepSeekReasoningAware(**model_config)


@tool
async def tavily_search(
    queries: list[str],
    max_results: Annotated[int, InjectedToolArg] = settings.config["search"][
        "max_results"
    ],
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
    max_char_to_include: Annotated[int, InjectedToolArg] = settings.config["scraping"][
        "summary_max_chars"
    ],
) -> dict:
    """
    Fetch and summarize search results from Tavily search API.

    Args:
        queries: List of search queries to execute
        max_results: Maximum number of results to return per query
        topic: Topic filter for search results (general, news, or finance)
        max_char_to_include: Maximum characters to include from each result for summarization

    Returns:
        Structured dict containing queries and summarized results.
    """

    logger.info(f"Tavily search invoked with {len(queries)} querie(s)")
    search_results = await tavily_search_async(
        queries,
        max_results=max_results,
        topic=topic,
        include_raw_content=True,
    )

    # Deduplicate results by URL across all queries
    unique_results: Dict[str, dict] = {}
    for response in search_results:
        for result in response["results"]:
            url = result["url"]
            if url not in unique_results:
                unique_results[url] = {**result, "query": response["query"]}

    logger.info(
        f"Collected {sum(len(r['results']) for r in search_results)} raw result(s) "
        f"across {len(search_results)} query response(s); {len(unique_results)} after dedup"
    )

    # Build model from configuration.
    summarization_model = build_model(settings.summary_model)
    logger.debug(
        f"Summarizing results with model={settings.summary_model} "
        f"max_chars={max_char_to_include}"
    )

    async def noop():
        """No-op function for results without raw content."""
        return {"summary": None, "key_excerpts": []}

    summarization_tasks = [
        noop()
        if not result.get("raw_content")
        else summarize_content(
            summarization_model, result["raw_content"][:max_char_to_include]
        )
        for result in unique_results.values()
    ]

    # Execute all summarization tasks in parallel
    summaries = await asyncio.gather(*summarization_tasks)

    summarized_results = []
    for (url, result), summary in zip(unique_results.items(), summaries):
        summarized_results.append(
            {
                "url": url,
                "title": result.get("title"),
                "query": result.get("query"),
                "summary": summary.get("summary") if summary else None,
                "key_excerpts": summary.get("key_excerpts") if summary else [],
            }
        )

    # Format results as markdown with clickable links for better citation
    formatted_results = []
    for result in summarized_results:
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        query = result.get("query", "")
        summary = result.get("summary", "")

        # Format as markdown with source link
        formatted_result = f"""
### [{title}]({url})
**Query**: {query}
**Source**: {url}

{summary}
"""
        formatted_results.append(formatted_result.strip())

    # Return both structured data and formatted markdown
    formatted_output = "\n\n---\n\n".join(formatted_results)

    return {
        "queries": queries,
        "results": summarized_results,
        "formatted_output": formatted_output,
    }


async def tavily_search_async(
    search_queries,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = True,
):
    """Execute multiple Tavily search queries asynchronously.

    Args:
        search_queries: List of search query strings to execute
        max_results: Maximum number of results per query
        topic: Topic category for filtering results
        include_raw_content: Whether to include full webpage content

    Returns:
        List of search result dictionaries from Tavily API
    """
    logger.info(
        f"Dispatching Tavily queries ({len(search_queries)}): topic={topic}, max_results={max_results}"
    )
    # Initialize the Tavily client with API key from config
    tavily_client = AsyncTavilyClient(api_key=settings.config["search"]["api_key"])

    # Create search tasks for parallel execution
    search_tasks = [
        tavily_client.search(
            query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )
        for query in search_queries
    ]

    # Execute all search queries in parallel and return results
    search_results = await asyncio.gather(*search_tasks)
    logger.debug("Tavily queries completed")
    return search_results


async def summarize_content(
    model: BaseChatModel,
    content: str,
    timeout: int = 30,
    query: Optional[str] = None,
) -> dict:
    """
    Summarize content using AI model with timeout protection.

    Args:
        model: The chat model configured for summarization
        content: Raw content to be summarized
        timeout: Timeout for model first response
        query: If given, indicate a direction to summariza

    Returns:
        Dict containing `summary` (str) and `key_excerpts` (list[str]).
        Falls back to echoing the original content when summarization fails.
    """
    from fathom.tools.utils import get_today_str

    if not content or len(content) < 500:
        logger.debug("Content length below threshold; returning original content")
        return {"summary": content, "key_excerpts": []}

    base_instruction = prompts.summarize_content_prompt

    current_date = get_today_str()

    system_prompt_str = (
        f"{base_instruction}\n\n"
        "Return a concise summary and a excerpt as structured fields.\n"
        f"\n\nCurrent Date: {current_date}"
    )

    if query is not None:
        system_prompt_str += (
            f"\n\nIMPORTANT: Focus specifically on information related to: '{query}'"
        )

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt_str), ("human", "{content}")]
    )

    structured_model = model.with_structured_output(Summary)
    chain: Runnable = prompt | structured_model

    try:
        response = await asyncio.wait_for(
            chain.ainvoke({"content": content}), timeout=float(timeout)
        )
        return cast(Summary, response).model_dump()

    except asyncio.TimeoutError:
        # Timeout during summarization - return original content
        logger.warning(
            "Summarization timed out after 60 seconds, returning original content"
        )
        return {"summary": content, "key_excerpts": []}
    except Exception as e:
        # Other errors during summarization - log and return original content
        logger.warning(
            f"Summarization failed with error: {str(e)}, returning original content"
        )
        return {"summary": content, "key_excerpts": []}
