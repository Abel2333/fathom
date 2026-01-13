import pytest

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import utils


class DummyModel:
    """Minimal async model that satisfies the interface used in utils."""

    def __init__(self, summary="demo summary", key_excerpts=None):
        self.summary = summary
        self.key_excerpts = key_excerpts or ["point a", "point b"]

    def with_structured_output(self, schema):
        # Ignore schema and return self as the runnable.
        return self

    async def ainvoke(self, inputs, **kwargs):
        return utils.SummaryResponse(
            summary=self.summary,
            key_excerpts=self.key_excerpts,
        )


@pytest.mark.asyncio
async def test_summarize_content_structured_output(monkeypatch):
    # Force deterministic date to avoid prompt variation in model behavior.
    monkeypatch.setattr(utils, "get_today_str", lambda: "Mon Jan 1, 2024")
    model = DummyModel(summary="short summary", key_excerpts=["k1", "k2"])

    result = await utils.summarize_content(
        model=model,
        content="X" * 600,  # exceed threshold to trigger summarization
        timeout=5,
    )

    assert result["summary"] == "short summary"
    assert result["key_excerpts"] == ["k1", "k2"]


@pytest.mark.asyncio
async def test_summarize_content_short_circuit():
    # Content too short should bypass model call.
    model = DummyModel(summary="should not be used")
    result = await utils.summarize_content(model=model, content="short text", timeout=5)
    assert result == {"summary": "short text", "key_excerpts": []}


@pytest.mark.asyncio
async def test_tavily_search_builds_model_and_summarizes(monkeypatch):
    # Arrange fake search output
    fake_results = [
        {
            "query": "q1",
            "results": [
                {
                    "url": "http://example.com/a",
                    "title": "Example A",
                    "raw_content": "A" * 800,
                    "content": "unused content",
                }
            ],
        }
    ]

    async def fake_search_async(*args, **kwargs):
        return fake_results

    # Track whether builder was invoked
    built = {"called": False}

    def fake_build_model():
        built["called"] = True
        return DummyModel(summary="built summary", key_excerpts=["p1"])

    monkeypatch.setattr(utils, "tavily_search_async", fake_search_async)
    monkeypatch.setattr(utils, "_build_summary_model", fake_build_model)

    output = await utils.tavily_search(
        queries=["q1"],
        summarization_model=None,  # force builder usage
        max_results=1,
        topic="general",
        max_char_to_include=500,
    )

    assert built["called"] is True
    assert output["queries"] == ["q1"]
    assert len(output["results"]) == 1
    first = output["results"][0]
    assert first["url"] == "http://example.com/a"
    assert first["summary"] == "built summary"
    assert first["key_excerpts"] == ["p1"]
