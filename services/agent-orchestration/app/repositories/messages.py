"""Rich-history repository — agent_messages + agent_citations + citation_spans.

Every /run produces:
  - 1 user message (role='user', content=the prompt)
  - 1 assistant message (role='assistant', content=the response)
  - 0+ citations attached to the assistant message
  - 0+ spans per citation (start/end offsets into the assistant text)

Backward compat: we still write the aggregate agent_actions row via the
existing AgentActionsRepository. The rich tables are additive.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import asyncpg


def _to_datetime(v: Any) -> datetime | None:
    """Capabilities return occurred_at as an ISO string; asyncpg needs datetime."""
    if v is None or isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            return None
    return None


class MessagesRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def record_turn(
        self,
        *,
        user_id: str,
        project_id: str | None,
        action_id: str | None,
        task_id: str | None,
        user_prompt: str,
        assistant_content: str,
        assistant_metadata: dict[str, Any],
        citations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Persist user → assistant turn + citations + spans in one transaction.

        ``citations`` is a list of dicts shaped like::

            {
              "source_type": "notion_page",
              "provider": "notion",
              "ref_id": "abc-123",
              "url": "https://notion.so/...",
              "title": "Q3 Planning",
              "actor": "samir@raweval.com",
              "actor_id": "...",
              "excerpt": "We decided to ship Nov 1...",
              "occurred_at": <datetime or None>,
              "spans": [
                  {"start": 12, "end": 40, "label": "quote"},
                  ...
              ],
            }
        """
        async with self._pool.acquire() as conn, conn.transaction():
            user_msg = await conn.fetchrow(
                """
                INSERT INTO agent_messages
                    (user_id, project_id, action_id, task_id, role, content, metadata)
                VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, 'user', $5, '{}'::jsonb)
                RETURNING id, created_at
                """,
                user_id,
                project_id,
                action_id,
                task_id,
                user_prompt,
            )

            assistant_msg = await conn.fetchrow(
                """
                INSERT INTO agent_messages
                    (user_id, project_id, action_id, task_id, role, content,
                     content_format, metadata, parent_message_id)
                VALUES ($1::uuid, $2::uuid, $3::uuid, $4::uuid, 'assistant', $5,
                        'markdown', $6::jsonb, $7::uuid)
                RETURNING id, created_at
                """,
                user_id,
                project_id,
                action_id,
                task_id,
                assistant_content,
                json.dumps(assistant_metadata),
                user_msg["id"],
            )

            citation_rows: list[dict[str, Any]] = []
            for c in citations:
                cit = await conn.fetchrow(
                    """
                    INSERT INTO agent_citations
                        (message_id, user_id, project_id,
                         source_type, provider, ref_id, url, title, actor,
                         actor_id, excerpt, occurred_at, metadata)
                    VALUES ($1::uuid, $2::uuid, $3::uuid,
                            $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb)
                    RETURNING id
                    """,
                    assistant_msg["id"],
                    user_id,
                    project_id,
                    c.get("source_type", "web_page"),
                    c.get("provider"),
                    c.get("ref_id"),
                    c.get("url"),
                    c.get("title"),
                    c.get("actor"),
                    c.get("actor_id"),
                    c.get("excerpt"),
                    _to_datetime(c.get("occurred_at")),
                    json.dumps(c.get("metadata", {})),
                )
                for span in c.get("spans", []):
                    await conn.execute(
                        """
                        INSERT INTO citation_spans
                            (citation_id, message_id, start_offset, end_offset, label)
                        VALUES ($1::uuid, $2::uuid, $3, $4, $5)
                        """,
                        cit["id"],
                        assistant_msg["id"],
                        int(span["start"]),
                        int(span["end"]),
                        span.get("label"),
                    )
                citation_rows.append({"id": str(cit["id"]), **c})

        return {
            "user_message_id": str(user_msg["id"]),
            "assistant_message_id": str(assistant_msg["id"]),
            "citations": citation_rows,
        }

    async def list_for_project(
        self, user_id: str, project_id: str, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return the hydrated messages (with citations + spans) for a project."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, role, content, content_format, metadata, citations, created_at
                FROM agent_messages_hydrated
                WHERE user_id = $1::uuid AND project_id = $2::uuid
                ORDER BY created_at DESC
                LIMIT $3
                """,
                user_id,
                project_id,
                limit,
            )
        return [dict(r) for r in rows]
