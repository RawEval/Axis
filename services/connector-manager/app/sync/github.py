"""GitHubSyncWorker — pulls recent GitHub events and writes them to
activity_events. Mirrors GDriveSyncWorker exactly, swapping vendor specifics.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from axis_common import get_logger

from app.db import db
from app.repositories.activity import ActivityEventsRepository
from app.repositories.connectors import ConnectorsRepository
from app.repositories.sync_state import ConnectorSyncStateRepository
from app.security import decrypt_token
from app.sync import registry as sync_registry
from app.sync.base import SyncResult, categorize_error

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONNECTORS_ROOT = _REPO_ROOT / "connectors"
if str(_CONNECTORS_ROOT) not in sys.path:
    sys.path.insert(0, str(_CONNECTORS_ROOT))

from github.src.client import GitHubClient  # noqa: E402

logger = get_logger(__name__)


class GitHubSyncWorker:
    source = "github"

    async def freshen(
        self,
        user_id: UUID,
        *,
        since: datetime | None = None,
        force: bool = False,
        _pool: object = None,
    ) -> SyncResult:
        pool = _pool or db.raw
        conn_repo = ConnectorsRepository(pool)
        activity_repo = ActivityEventsRepository(pool)
        state_repo = ConnectorSyncStateRepository(pool)

        connectors = await conn_repo.list_by_user_and_tool(user_id=str(user_id), tool="github")
        if not connectors:
            return SyncResult(rows_added=0, status="ok")

        rows_added = 0
        newest_event: datetime | None = None

        for conn_row in connectors:
            try:
                token = decrypt_token(conn_row["auth_token_encrypted"])
            except Exception as e:  # noqa: BLE001
                await state_repo.record_failure(user_id, "github", status="auth_failed", error=str(e))
                return SyncResult(rows_added=0, status="auth_failed", error_message=str(e))

            client = GitHubClient(access_token=token)
            try:
                events = await client.list_recent(since=since, limit=100)
            except Exception as e:  # noqa: BLE001
                status, msg = categorize_error(e)
                await state_repo.record_failure(user_id, "github", status=status, error=msg)
                return SyncResult(rows_added=0, status=status, error_message=msg)

            for event in events:
                mapped = _map_github_event(event)
                if mapped is None:
                    continue
                result = await activity_repo.upsert(
                    user_id=str(user_id),
                    project_id=str(conn_row["project_id"]) if conn_row.get("project_id") else None,
                    source="github",
                    event_type=mapped["event_type"],
                    key=mapped["key"],
                    external_id=mapped["key"],
                    title=mapped["title"],
                    snippet=mapped.get("snippet"),
                    actor=mapped.get("actor"),
                    actor_id=mapped.get("actor_id"),
                    occurred_at=mapped["occurred_at"],
                    raw_ref=mapped.get("raw_ref"),
                )
                if result["inserted"]:
                    rows_added += 1
                if newest_event is None or (mapped["occurred_at"] and mapped["occurred_at"] > newest_event):
                    newest_event = mapped["occurred_at"]

        await state_repo.record_success(
            user_id, "github",
            last_event_at=newest_event,
            cursor={},
        )
        return SyncResult(rows_added=rows_added, last_event_at=newest_event, status="ok")


def _synthesize_title(event: dict[str, Any]) -> str:
    actor = (event.get("actor") or {}).get("login") or "someone"
    repo = (event.get("repo") or {}).get("name") or "a repo"
    etype = event.get("type", "Event")
    map_ = {
        "PushEvent": f"{actor} pushed to {repo}",
        "PullRequestEvent": f"{actor} updated a PR in {repo}",
        "IssuesEvent": f"{actor} updated an issue in {repo}",
        "IssueCommentEvent": f"{actor} commented on an issue in {repo}",
        "PullRequestReviewEvent": f"{actor} reviewed a PR in {repo}",
        "PullRequestReviewCommentEvent": f"{actor} commented on a PR review in {repo}",
        "CreateEvent": f"{actor} created something in {repo}",
        "DeleteEvent": f"{actor} deleted something in {repo}",
        "ReleaseEvent": f"{actor} cut a release in {repo}",
        "WatchEvent": f"{actor} starred {repo}",
        "ForkEvent": f"{actor} forked {repo}",
    }
    return map_.get(etype, f"{actor} {etype} in {repo}")


def _map_github_event(event: dict[str, Any]) -> dict[str, Any] | None:
    external_id = event.get("id")
    if not external_id:
        return None

    event_type = event.get("type", "GithubEvent")
    key = external_id
    title = _synthesize_title(event)
    snippet = None
    actor = event.get("actor", {}).get("login")
    actor_id = event.get("actor", {}).get("login")

    try:
        occurred_at = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError):
        occurred_at = datetime.now(tz=timezone.utc)

    return {
        "event_type": event_type,
        "key": key,
        "title": title,
        "snippet": snippet,
        "actor": actor,
        "actor_id": actor_id,
        "occurred_at": occurred_at,
        "raw_ref": {
            "event_id": event["id"],
            "type": event.get("type"),
            "repo": event.get("repo", {}).get("name"),
            "actor": event.get("actor", {}).get("login"),
        },
    }


sync_registry.register(GitHubSyncWorker())
