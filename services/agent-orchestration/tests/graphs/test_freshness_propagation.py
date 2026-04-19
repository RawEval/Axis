"""Verify freshness propagates from CapabilityResult through state."""
from __future__ import annotations

from app.capabilities.base import CapabilityResult


def test_capability_result_carrying_freshness_produces_extractable_dict():
    """Smoke test that the data shape is what the planner expects to walk:
    CapabilityResult.content is a dict with a 'freshness' key whose value
    is itself a dict with at least 'source' and 'sync_status'."""
    result = CapabilityResult(
        summary="found 3 events",
        content={
            "events": [{"title": "x"}],
            "freshness": {
                "source": "notion",
                "last_synced_at": "2026-04-19T18:30:00+00:00",
                "sync_status": "ok",
                "error_message": None,
            },
        },
    )
    assert isinstance(result.content, dict)
    fr = result.content.get("freshness")
    assert isinstance(fr, dict)
    assert fr["source"] == "notion"
    assert fr["sync_status"] == "ok"


def test_capability_result_without_freshness_is_safely_skippable():
    """For older capabilities that don't return freshness (e.g.
    connector.notion.search), result.content may be a list or a dict
    without 'freshness'. The planner extraction must not crash."""
    result_list_content = CapabilityResult(summary="ok", content=[{"hit": 1}])
    assert not (isinstance(result_list_content.content, dict)
                and "freshness" in result_list_content.content)

    result_dict_no_freshness = CapabilityResult(summary="ok", content={"events": []})
    assert "freshness" not in result_dict_no_freshness.content
