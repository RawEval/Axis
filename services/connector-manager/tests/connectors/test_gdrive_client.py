"""Tests for GDriveClient.list_recent — uses sys.path shim."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import respx
from httpx import Response

_REPO_ROOT = Path(__file__).resolve().parents[5]
_CONNECTORS_ROOT = _REPO_ROOT / "connectors"
if str(_CONNECTORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONNECTORS_ROOT))

from gdrive.src.client import GDriveClient  # noqa: E402

DRIVE = "https://www.googleapis.com/drive/v3"


@respx.mock
async def test_list_recent_passes_modified_time_query_when_since_given():
    captured = {"q": None, "orderBy": None}

    def _record(request):
        captured["q"] = dict(request.url.params).get("q")
        captured["orderBy"] = dict(request.url.params).get("orderBy")
        return Response(200, json={"files": []})

    respx.get(f"{DRIVE}/files").mock(side_effect=_record)

    client = GDriveClient(access_token="t")
    since = datetime(2026, 4, 19, 0, 0, 0, tzinfo=timezone.utc)
    await client.list_recent(since=since, limit=10)

    assert captured["q"] is not None
    assert "modifiedTime" in captured["q"]
    assert "2026-04-19T00:00:00Z" in captured["q"]
    assert "trashed = false" in captured["q"]
    assert captured["orderBy"] == "modifiedTime desc"


@respx.mock
async def test_list_recent_default_query_when_no_since():
    captured = {"q": None}

    def _record(request):
        captured["q"] = dict(request.url.params).get("q")
        return Response(200, json={"files": []})

    respx.get(f"{DRIVE}/files").mock(side_effect=_record)

    client = GDriveClient(access_token="t")
    await client.list_recent(limit=10)

    assert captured["q"] == "trashed = false"


@respx.mock
async def test_list_recent_returns_files_array():
    respx.get(f"{DRIVE}/files").mock(
        return_value=Response(200, json={
            "files": [
                {
                    "id": "f1",
                    "name": "Q3 Plan.docx",
                    "mimeType": "application/vnd.google-apps.document",
                    "modifiedTime": "2026-04-19T18:25:00.000Z",
                    "webViewLink": "https://docs.google.com/document/d/f1",
                    "lastModifyingUser": {"emailAddress": "alice@example.com"},
                },
            ]
        })
    )

    client = GDriveClient(access_token="t")
    files = await client.list_recent(limit=10)
    assert len(files) == 1
    assert files[0]["id"] == "f1"
    assert files[0]["name"] == "Q3 Plan.docx"
