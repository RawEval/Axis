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
