"""connector.github.{comment,create_issue} — GitHub write capabilities.

Issue/PR numbers (and ``owner/repo`` slugs) are unambiguous so there is
no resolver and no target-picker stage — every input lands directly on a
known target. The capability still goes through the standard write
gating lifecycle: snapshot → diff → ``write_actions`` row in pending
state → ``write.preview`` event → user confirms via
``POST /writes/{id}/confirm``.

Both capabilities are reversible-ish (a comment can be deleted, an issue
can be closed) so the default permission is ``ask`` rather than the
stricter ``always_gate`` Gmail send carries. The diff preview is still
shown unconditionally — spec §6.5.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.capabilities.base import Capability, CapabilityResult, Citation
from app.db import db
from app.events import publish as publish_event
from app.repositories.writes import WritesRepository


_NULL_ACTION_ID = "00000000-0000-0000-0000-000000000000"


@dataclass
class _GitHubComment:
    name: str = "connector.github.comment"
    description: str = (
        "Comment on a GitHub issue or pull request. The user will see a "
        "diff preview and must confirm before the comment is posted."
    )
    scope: str = "write"
    default_permission: str = "ask"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Target repo as 'owner/repo'.",
                },
                "issue_number": {
                    "type": "integer",
                    "description": "Issue or PR number on the repo.",
                },
                "body": {
                    "type": "string",
                    "description": "Comment body (Markdown).",
                },
            },
            "required": ["repo", "issue_number", "body"],
        }

    async def __call__(
        self,
        *,
        user_id: str,
        project_id: str | None,
        org_id: str | None,
        inputs: dict[str, Any],
    ) -> CapabilityResult:
        if not project_id:
            return CapabilityResult(
                summary="no active project",
                content=[],
                error="github comment requires an active project",
            )

        repo = (inputs.get("repo") or "").strip()
        issue_number = inputs.get("issue_number")
        body = inputs.get("body") or ""
        if not repo or not isinstance(issue_number, int) or not body:
            return CapabilityResult(
                summary="missing repo, issue_number, or body",
                content=[],
                error="repo, issue_number, and body are all required",
            )

        target_id = f"{repo}#{issue_number}"
        diff = {
            "before": None,
            "after": {"repo": repo, "issue_number": issue_number, "body": body},
            "summary": f"Comment on {target_id}",
        }

        action_id = inputs.get("_action_id") or _NULL_ACTION_ID
        writes_repo = WritesRepository(db.raw)
        pending = await writes_repo.create_pending(
            action_id=action_id,
            user_id=user_id,
            project_id=project_id,
            tool="github",
            target_id=target_id,
            target_type="github_issue",
            diff=diff,
            before_state={},
        )

        await publish_event(
            user_id=user_id,
            project_id=project_id,
            event_type="write.preview",
            payload={
                "write_action_id": pending["write_action_id"],
                "snapshot_id": pending["snapshot_id"],
                "tool": "github",
                "target_id": target_id,
                "diff": diff,
            },
        )
        return CapabilityResult(
            summary=(
                f"comment pending — {target_id}, "
                f"awaiting user confirmation"
            ),
            content={
                "write_action_id": pending["write_action_id"],
                "snapshot_id": pending["snapshot_id"],
                "status": "pending_confirmation",
                "target_id": target_id,
            },
            citations=[
                Citation(
                    source_type="github_issue",
                    provider="github",
                    ref_id=target_id,
                    title=f"Comment on {target_id}",
                    excerpt=body[:200],
                )
            ],
        )


@dataclass
class _GitHubCreateIssue:
    name: str = "connector.github.create_issue"
    description: str = (
        "Create a new GitHub issue. The user will see a diff preview and "
        "must confirm before the issue is filed."
    )
    scope: str = "write"
    default_permission: str = "ask"
    input_schema: dict[str, Any] = None

    def __post_init__(self) -> None:
        self.input_schema = {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Target repo as 'owner/repo'.",
                },
                "title": {
                    "type": "string",
                    "description": "Issue title.",
                },
                "body": {
                    "type": "string",
                    "description": "Issue body (Markdown).",
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional label names to apply.",
                },
            },
            "required": ["repo", "title"],
        }

    async def __call__(
        self,
        *,
        user_id: str,
        project_id: str | None,
        org_id: str | None,
        inputs: dict[str, Any],
    ) -> CapabilityResult:
        if not project_id:
            return CapabilityResult(
                summary="no active project",
                content=[],
                error="github create_issue requires an active project",
            )

        repo = (inputs.get("repo") or "").strip()
        title = (inputs.get("title") or "").strip()
        body = inputs.get("body") or ""
        labels_raw = inputs.get("labels") or []
        labels = [str(x) for x in labels_raw] if isinstance(labels_raw, list) else []
        if not repo or not title:
            return CapabilityResult(
                summary="missing repo or title",
                content=[],
                error="repo and title are required",
            )

        target_id = repo
        diff = {
            "before": None,
            "after": {
                "repo": repo,
                "title": title,
                "body": body,
                "labels": labels,
            },
            "summary": f"Create issue in {repo} — {title}",
        }

        action_id = inputs.get("_action_id") or _NULL_ACTION_ID
        writes_repo = WritesRepository(db.raw)
        pending = await writes_repo.create_pending(
            action_id=action_id,
            user_id=user_id,
            project_id=project_id,
            tool="github",
            target_id=target_id,
            target_type="github_repo",
            diff=diff,
            before_state={},
        )

        await publish_event(
            user_id=user_id,
            project_id=project_id,
            event_type="write.preview",
            payload={
                "write_action_id": pending["write_action_id"],
                "snapshot_id": pending["snapshot_id"],
                "tool": "github",
                "target_id": target_id,
                "diff": diff,
            },
        )
        return CapabilityResult(
            summary=(
                f"create_issue pending — {repo} ({title}), "
                f"awaiting user confirmation"
            ),
            content={
                "write_action_id": pending["write_action_id"],
                "snapshot_id": pending["snapshot_id"],
                "status": "pending_confirmation",
                "target_id": target_id,
            },
            citations=[
                Citation(
                    source_type="github_repo",
                    provider="github",
                    ref_id=repo,
                    title=f"Issue: {title}",
                    excerpt=body[:200],
                )
            ],
        )


CAPABILITIES: list[Capability] = [_GitHubComment(), _GitHubCreateIssue()]
