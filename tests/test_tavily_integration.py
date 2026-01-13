import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import utils

load_dotenv()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("TAVILY_API_KEY"),
    reason="TAVILY_API_KEY not set; skipping live Tavily search test.",
)
async def test_tavily_search_async_live():
    """Live test against Tavily search (skipped when no API key)."""
    results = await utils.tavily_search(
        ["latest technology news", "Copper Market"],
        max_results=5,
        topic="news",
    )

    # Show a concise diagnostic to stdout when running directly.
    print(results)

    assert isinstance(results, list)
    assert results, "Expected at least one query result object"
    first_query = results[0]
    assert "results" in first_query
    assert isinstance(first_query["results"], list)

    # If Tavily returned any hits, validate basic shape
    if first_query["results"]:
        first_hit = first_query["results"][0]
        assert "url" in first_hit
        assert "title" in first_hit
