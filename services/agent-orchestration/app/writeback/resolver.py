"""Target resolvers — turn a free-text reference like "Mrinal" into a list
of candidate addressable targets. Each connector that does writes against
ambiguous targets registers a resolver here.

The capability calls resolver.resolve(query, ctx) → list[TargetCandidate].
- 0 candidates: capability raises ResolutionError ("couldn't find anyone matching X")
- 1 candidate: capability proceeds with that target auto-selected
- >1 candidates: capability creates the write_action with target_options
  populated and returns status='pending_target_pick' to the planner.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Protocol


@dataclass
class TargetCandidate:
    """One option the user might pick from a disambiguation picker."""
    kind: str             # 'email_address' | 'slack_user' | 'slack_channel' | 'notion_page' | 'github_issue' | ...
    id: str               # provider-native unique id (the email, the channel id, the page id, ...)
    label: str            # primary display ("Mrinal Raj")
    sub_label: str | None # secondary display ("mrinal@raweval.com")
    context: str | None   # tiny disambiguating context ("last replied 2d ago — 'Q3 plan'")
    metadata: dict[str, Any] | None = None  # extra payload the consumer may need

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


class ResolutionError(Exception):
    """Raised when resolution finds zero candidates."""


class TargetResolver(Protocol):
    async def resolve(self, query: str, *, user_id: str, project_id: str) -> list[TargetCandidate]: ...


# ---------------- Gmail recipient resolver ----------------


class GmailRecipientResolver:
    """Find Gmail recipients matching a free-text query.

    Searches the user's recent Gmail messages (sent + received) for
    From/To headers + sender names matching the query, dedupes by
    address, and returns each unique recipient with the most recent
    interaction snippet.

    Strategy:
      1. Use Gmail's native search query: `(from:Mrinal OR to:Mrinal OR Mrinal)` limit 25
      2. For each hit, extract From + To headers
      3. Group by lowercased email; keep the display name from the first hit
      4. For each address: snippet = first hit's `snippet` field
      5. Sort by recency (Date header desc).
    """

    def __init__(self, client) -> None:
        self._client = client

    async def resolve(self, query: str, *, user_id: str, project_id: str) -> list[TargetCandidate]:
        q = query.strip()
        if not q:
            return []
        # Gmail search syntax — match in any header or body. The OR groups
        # widen the catchment because just "from:X" misses people the user
        # hasn't received from yet.
        gmail_q = f"(from:{q} OR to:{q} OR {q})"
        hits = await self._client.search(gmail_q, limit=25)

        # Aggregate by lowercased email
        candidates: dict[str, TargetCandidate] = {}
        for hit in hits:
            headers = {h["name"]: h["value"] for h in hit.get("payload", {}).get("headers", [])}
            for header_name in ("From", "To"):
                raw = headers.get(header_name) or ""
                for parsed in _parse_addresses(raw):
                    email = parsed["email"].lower()
                    if not email or _looks_like_self(email, headers.get("Delivered-To", "")):
                        continue
                    if not _matches_query(parsed, q):
                        continue
                    if email not in candidates:
                        candidates[email] = TargetCandidate(
                            kind="email_address",
                            id=email,
                            label=parsed["name"] or email,
                            sub_label=email if parsed["name"] else None,
                            context=hit.get("snippet"),
                            metadata={"first_seen_message_id": hit.get("id")},
                        )
        return list(candidates.values())


def _parse_addresses(raw: str) -> list[dict[str, str]]:
    """Split a header value like '"Mrinal Raj" <mrinal@x.com>, alex@y.com' into name+email parts."""
    import email.utils
    parsed = email.utils.getaddresses([raw]) if raw else []
    return [{"name": n.strip(), "email": e.strip()} for (n, e) in parsed if e]


def _looks_like_self(email: str, delivered_to: str) -> bool:
    return bool(delivered_to) and email == delivered_to.lower()


def _matches_query(parsed: dict[str, str], q: str) -> bool:
    needle = q.lower()
    return needle in parsed["name"].lower() or needle in parsed["email"].lower()


# ---------------- Slack channel resolver ----------------


class SlackChannelResolver:
    """Find Slack channels matching a free-text query.

    Calls /tools/slack/channels via the adapter, filters by name match
    (case-insensitive substring), returns each as a TargetCandidate
    keyed by the Slack channel id.
    """

    def __init__(self, channels_lister) -> None:
        self._lister = channels_lister  # callable: async () -> list[dict]

    async def resolve(self, query: str, *, user_id: str, project_id: str) -> list[TargetCandidate]:
        q = query.strip().lstrip("#").lower()
        if not q:
            return []
        channels = await self._lister()
        out: list[TargetCandidate] = []
        for ch in channels:
            name = (ch.get("name") or "").lower()
            if not name or q not in name:
                continue
            ch_id = ch.get("id") or ""
            if not ch_id:
                continue
            topic_raw = ch.get("topic")
            if isinstance(topic_raw, dict):
                topic = topic_raw.get("value") or ""
            else:
                topic = topic_raw or ""
            members = ch.get("num_members")
            ctx_parts: list[str] = []
            if topic:
                ctx_parts.append(topic[:80])
            if isinstance(members, int):
                ctx_parts.append(f"{members} members")
            out.append(TargetCandidate(
                kind="slack_channel",
                id=ch_id,
                label=f"#{ch.get('name')}",
                sub_label=None,
                context=" · ".join(ctx_parts) or None,
                metadata={"is_private": bool(ch.get("is_private"))},
            ))
        # Stable: exact name first, then alphabetical
        out.sort(key=lambda c: (0 if c.label.lower().lstrip("#") == q else 1, c.label.lower()))
        return out


# ---------------- GDrive doc resolver ----------------


class GDriveDocResolver:
    """Find Google Docs matching a free-text query.

    Calls /tools/gdrive/search via the adapter, narrows to mimeType
    application/vnd.google-apps.document, returns each as a TargetCandidate.
    """

    def __init__(self, search) -> None:
        self._search = search  # callable: async (query: str, *, limit: int) -> list[dict]

    async def resolve(self, query: str, *, user_id: str, project_id: str) -> list[TargetCandidate]:
        q = query.strip()
        if not q:
            return []
        # Drive search syntax: name contains '<q>' AND mimeType = '...document'
        # The search adapter handles the actual API call; we just pass the query.
        hits = await self._search(q, limit=25)
        out: list[TargetCandidate] = []
        for h in hits:
            mime = h.get("mimeType") or ""
            # Only Google Docs are appendable as plain text via append_to_doc.
            if mime and "application/vnd.google-apps.document" not in mime:
                continue
            doc_id = h.get("id") or ""
            if not doc_id:
                continue
            modified = h.get("modifiedTime") or h.get("modified_time")
            owner = (h.get("owners") or [{}])[0].get("displayName") if isinstance(h.get("owners"), list) else None
            ctx_parts: list[str] = []
            if owner:
                ctx_parts.append(f"owned by {owner}")
            if modified:
                ctx_parts.append(f"modified {modified}")
            out.append(TargetCandidate(
                kind="gdrive_doc",
                id=doc_id,
                label=h.get("name") or "(untitled doc)",
                sub_label=h.get("webViewLink") or h.get("url"),
                context=" · ".join(ctx_parts) or None,
                metadata={"mime_type": mime},
            ))
        return out
