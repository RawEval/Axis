# Axis Plan 12 — Slack Channel Resolver + GDrive Doc Resolver + Uniform Write Gating

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Apply the Plan 11 disambiguation+gating pattern to Slack `post` (channel resolver) and GDrive `append` (doc resolver). Result: when the user says "post to #product" with multiple matching channels, or "append to Q3 doc" with multiple matching docs, they see a `<TargetPicker>` and a `<WritePreviewCard>` exactly as Gmail does today.

**Why:** Slack `post` and GDrive `append` are currently capability-permission-only — they execute on user permission grant without showing the diff or letting the user fix targeting mistakes. Gmail send already does this right (Plan 11). This plan brings Slack post and GDrive append up to the same bar.

**Architecture:** Two new resolvers (`SlackChannelResolver`, `GDriveDocResolver`) added to `services/agent-orchestration/app/writeback/resolver.py` next to the existing `GmailRecipientResolver`. Two existing capabilities (`connector.slack.post`, `connector.gdrive.append`) refactored to call the resolver → if N=0 error, N=1 auto-resolve, N>1 publish `write.target_pick_required` event. The frontend already handles all three event types (Plan 11 B3); no UI changes needed beyond verifying.

**Out of scope (Plan 13+):**
- Slack DM with user resolver (`connector.slack.dm` as separate capability from `connector.slack.post`)
- Slack `react` retrofit (uses message permalink so target is unambiguous; lower priority)
- GDrive `create_doc` folder resolver (target folder disambiguation)
- Notion `append` page resolver retrofit (Notion already uses search but doesn't surface as picker yet)
- Webhook handlers (Gmail Pub/Sub, GDrive push, GitHub)

---

## File structure

**Modify:**

```
services/agent-orchestration/app/writeback/resolver.py             # add SlackChannelResolver + GDriveDocResolver
services/agent-orchestration/app/capabilities/slack.py             # refactor _SlackPost to use resolver + write gate
services/agent-orchestration/app/capabilities/gdrive.py            # refactor _GDriveAppend to use resolver + write gate
```

**No new files.** No frontend changes (already handles the three event types from Plan 11).

**Total:** 3 modified files, 3 commits.

---

## Phase A — Resolvers + retrofits

### Task A1: Add SlackChannelResolver + GDriveDocResolver

**File:** `services/agent-orchestration/app/writeback/resolver.py`

Read the existing file first — it already has `GmailRecipientResolver` and the `TargetCandidate` + `ResolutionError` framework. Add two new resolver classes at the bottom, mirroring `GmailRecipientResolver`'s structure exactly.

```python
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
            topic = (ch.get("topic") or {}).get("value") or ""
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
```

⚠️ The adapters (channels lister, gdrive search) are passed in by the capability — same pattern Gmail used. Capability builds an adapter that calls the existing CM client.

Commit: `feat(orchestration): add SlackChannelResolver + GDriveDocResolver to writeback`

### Task A2: Retrofit `connector.slack.post` capability

**File:** `services/agent-orchestration/app/capabilities/slack.py`

Read the existing `_SlackPost` class first. It currently takes `channel` (Slack channel id directly) and posts immediately. Refactor to:

1. Accept `channel_query` instead of `channel` in inputs (a free-text channel name like "product" or "#product").
2. Use `SlackChannelResolver` to convert that to candidates.
3. Apply the same gate flow Gmail uses:
   - 0 candidates → CapabilityResult error
   - 1 candidate → write_action with target_chosen + target_id, publish `write.preview`, return pending_confirmation
   - >1 candidates → write_action with target_options, publish `write.target_pick_required`, return pending_target_pick

Mirror `_GmailSend.__call__` from `gmail_write.py` exactly for the lifecycle + repository calls. The only difference is the resolver and the diff body shape (Slack diff = `{after: {channel, text, thread_ts?}}`).

Important pattern notes (from Plan 11 lessons):
- Use `WritesRepository(db.raw)` not `WriteActionsRepository()`
- `from app.db import db` to get the raw connection
- Action id from `inputs.get("_action_id") or _NULL_ACTION_ID` (define `_NULL_ACTION_ID` if not already in slack.py)
- `publish_event(user_id=..., event_type=..., payload=..., project_id=...)` keyword args
- Target id when N>1: empty string `""` not None
- `before_state={}` (no resource snapshot for outbound message)
- `CapabilityResult.pending_target_pick(write_id=...)` is a classmethod (added in Plan 11 A5)
- For the pending_confirmation path, Slack capability's existing return convention should be preserved (look at how `notion_write._NotionAppend` returns it — copy that exactly)

Add `SlackChannelLister` adapter inside slack.py (mirror Gmail's `_RemoteGmailSearchAdapter` pattern):

```python
class _SlackChannelsAdapter:
    def __init__(self, cm: ConnectorManagerClient, *, user_id: str, project_id: str):
        self._cm = cm
        self._user_id = user_id
        self._project_id = project_id

    async def __call__(self) -> list[dict[str, Any]]:
        # Reads /tools/slack/channels via the existing client method.
        return await self._cm.slack_channels(user_id=self._user_id, project_id=self._project_id, limit=200)
```

(SlackChannelResolver takes the lister as a callable; this adapter provides one.)

Update the input schema:
```python
input_schema = {
    "type": "object",
    "properties": {
        "channel_query": {"type": "string", "description": "Free-text channel name like 'product' or '#product-eng'"},
        "text": {"type": "string"},
        "thread_ts": {"type": "string", "description": "Optional thread timestamp to reply within"},
    },
    "required": ["channel_query", "text"],
}
```

⚠️ Backward compat: if `inputs` contains an exact `channel` key with a `C…` Slack channel ID (already-resolved), skip the resolver and proceed with that target directly. This prevents breaking any existing callers that pass channel ids already.

After all changes, `python -m py_compile services/agent-orchestration/app/capabilities/slack.py` must pass.

Commit: `refactor(orchestration): slack.post uses SlackChannelResolver + write gate (uniform with gmail.send)`

### Task A3: Retrofit `connector.gdrive.append` capability

**File:** `services/agent-orchestration/app/capabilities/gdrive.py`

Plan 11 added `_GDriveAppend` (commit `4ba949b`). It currently takes `doc_id` directly and calls `_tool_call("gdrive/append", ...)` immediately. Refactor to:

1. Accept `doc_query` instead of `doc_id` in inputs (free-text doc name like "Q3 roadmap").
2. Use `GDriveDocResolver` to convert that to candidates.
3. Apply the gate flow exactly like slack.post.

Add `_GDriveSearchAdapter` (mirror Gmail's pattern):

```python
class _GDriveSearchAdapter:
    def __init__(self, cm: ConnectorManagerClient, *, user_id: str, project_id: str):
        self._cm = cm
        self._user_id = user_id
        self._project_id = project_id

    async def search(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        # The existing /tools/gdrive/search endpoint returns normalized docs with the fields
        # GDriveDocResolver expects (id, name, mimeType, modifiedTime, webViewLink/owners).
        # If the normalized response doesn't include mimeType, may need a /tools/gdrive/search-raw
        # variant — check the route; only add a raw endpoint if necessary.
        return await self._cm._tool_call(
            "gdrive/search",
            user_id=self._user_id, project_id=self._project_id, query=query, limit=limit,
        )
```

⚠️ Read `tools.py` for the actual /tools/gdrive/search response shape before assuming it has `mimeType`. The existing `_normalize_gdrive_hit` function may strip it. If so:
- Either add a `raw: bool = False` query param to /tools/gdrive/search that returns unfiltered hits when set
- OR add a new /tools/gdrive/search-raw endpoint (mirror what Plan 11 did for Gmail)
- Whichever fits the existing pattern better

Backward compat: if `inputs` contains `doc_id` directly (already-resolved id), skip resolver.

Update input_schema to use `doc_query`:
```python
self.input_schema = {
    "type": "object",
    "properties": {
        "doc_query": {"type": "string", "description": "Free-text doc name like 'Q3 roadmap'."},
        "text": {"type": "string"},
    },
    "required": ["doc_query", "text"],
}
```

After all changes, `python -m py_compile services/agent-orchestration/app/capabilities/gdrive.py` must pass.

Commit: `refactor(orchestration): gdrive.append uses GDriveDocResolver + write gate (uniform with gmail.send)`

---

## Phase B — Verify

### Task B1: Workspace verify

```bash
cd /Users/mrinalraj/Documents/Axis && \
  pnpm test 2>&1 | grep -E "(Test Files|Tests).*passed" | head -10 && \
  pnpm --filter @axis/web type-check 2>&1 | tail -3 && \
  pnpm --filter @axis/design-system type-check 2>&1 | tail -3 && \
  pnpm lint 2>&1 | tail -3 && \
  pnpm --filter @axis/web build 2>&1 | grep -E "(Compiled|Failed)" | head -3
```

Expected: design-system **120**, web **31**, all type-check + lint + build clean. **Frontend tests + types unaffected** by Plan 12 — backend-only changes.

For the Python files, verify:
```bash
python -m py_compile services/agent-orchestration/app/writeback/resolver.py
python -m py_compile services/agent-orchestration/app/capabilities/slack.py
python -m py_compile services/agent-orchestration/app/capabilities/gdrive.py
```

All three must compile.

(No commit for verify.)

---

## What you have at the end

- `SlackChannelResolver` + `GDriveDocResolver` added to the central resolver module.
- `connector.slack.post` accepts free-text channel name → picker if multiple match.
- `connector.gdrive.append` accepts free-text doc name → picker if multiple match.
- Both writes now create `write_actions` rows with diff preview (uniform with Gmail send).
- Frontend already handles the three event types (`write.preview`, `write.target_pick_required`, `write.target_chosen`) from Plan 11 — zero frontend changes needed.

## What's deferred to Plan 13

- `connector.slack.dm` as a separate capability with `SlackUserResolver`.
- `connector.slack.react` retrofit (currently uses channel + ts; ts is unambiguous so just needs the gate).
- `connector.gdrive.create_doc` folder resolver (where to put the new doc).
- `connector.notion.append` page resolver retrofit (currently uses page_id directly).
- Webhook handlers for Gmail Pub/Sub, GDrive push, GitHub.

## Self-Review

- **Spec coverage:** Closes the audit's gap — Slack post and GDrive append now use the same write-gate + disambiguation pattern Gmail send established in Plan 11.
- **Placeholder scan:** No "TBD"; each task says exactly which existing files to read and what shapes to mirror.
- **Type consistency:** All three new resolvers return `list[TargetCandidate]` (the shared shape); all three retrofitted capabilities use `WritesRepository.create_pending` with the same `target_options`/`target_chosen` semantics.
- **Backward compat:** Both retrofits accept either the old direct-id input or the new `*_query` input, so existing callers continue working.
