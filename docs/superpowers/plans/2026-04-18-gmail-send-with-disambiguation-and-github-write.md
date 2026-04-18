# Axis Plan 11 — Gmail Send (with recipient disambiguation) + GitHub Write

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Make Gmail send + draft work end-to-end with a recipient resolver + picker UI when "send mail to Mrinal" returns multiple candidates. Establish that pattern as the reusable disambiguation flow other connectors will adopt. Land GitHub write (comment, create-issue) using the same write-gating pattern.

**Why this matters (per the user's ask):** When the user types "send mail to Mrinal" and there are multiple Mrinals in their contact graph, we need to:
1. Search across Gmail (from:/to:/subject:/body) for everyone matching "Mrinal"
2. Show them as candidates with email + display name + recent context
3. Let the user pick which Mrinal
4. Then preview the draft for confirmation before send

Same pattern applies to Slack DMs (which Mrinal in Slack), Notion mentions, etc. Plan 11 builds the pattern; later plans retrofit other connectors.

**Architecture:**
- Migration 014: extends `write_actions` with `target_options` JSONB (candidates) + `target_chosen` JSONB (user pick).
- New `services/agent-orchestration/app/writeback/resolver.py` — generic resolver protocol + Gmail recipient resolver.
- `connector.gmail.send` capability: calls resolver → if 1 candidate, proceeds → if N>1, creates write_action with `target_options` populated, returns `pending_target_pick`.
- Frontend `WritePreviewCard` extended: if the action's `target_options` has >1, renders a `TargetPicker` above the body. User clicks → POST `/writes/{id}/choose-target` → row updates → preview renders → user clicks Confirm → POST `/writes/{id}/confirm` → backend executes.
- GitHub write doesn't need disambiguation (issue/PR numbers are unambiguous), so it lands without the resolver step.

**Out of scope (Plan 12+):**
- Retrofitting Slack post / Slack react / GDrive create-doc / GDrive append to use the new gate (they currently use capability-layer permission only).
- Slack DM with user disambiguation.
- Notion mention with user disambiguation.
- Webhook handlers (Gmail Pub/Sub, GDrive push, GitHub webhooks).

---

## File structure

**Create:**

```
infra/docker/init/postgres/014_write_target_options.sql       # migration
services/agent-orchestration/app/writeback/resolver.py         # generic resolver + Gmail
services/agent-orchestration/app/capabilities/gmail_write.py   # send + draft capabilities
services/agent-orchestration/app/capabilities/github_write.py  # comment + create_issue
packages/design-system/src/components/target-picker/
  target-picker.tsx
  target-picker.test.tsx
  index.ts
apps/web/lib/queries/writes.ts                                  # useChooseTarget hook
```

**Modify:**

```
services/connector-manager/app/routes/tools.py                  # +5 endpoints (gmail send/draft, github comment/create-issue, gmail resolve-recipients)
services/agent-orchestration/app/repositories/writes.py         # add target_options + target_chosen handling
services/agent-orchestration/app/main.py                        # add /writes/{id}/choose-target route
packages/design-system/src/components/write-preview-card/write-preview-card.tsx  # render picker if needed
packages/design-system/src/index.ts                             # export TargetPicker
apps/web/lib/capabilities.ts                                    # add gmail.draft + github.create-issue + github.comment, drop false-promise gmail.send (it'll be re-added once truly live)
```

**Total:** ~12 new/modified files, ~6 commits.

---

## Phase A — Backend: target options + Gmail resolver

### Task A1: Migration 014 — extend `write_actions`

**Files:** Create `infra/docker/init/postgres/014_write_target_options.sql`

```sql
-- Plan 11: write_actions can now stage multiple target candidates and let
-- the user pick before the write executes. target_options carries the
-- list of {kind, id, label, sub_label, context} dicts; target_chosen is
-- the picked one. Both NULL = no disambiguation needed.

ALTER TABLE write_actions
    ADD COLUMN IF NOT EXISTS target_options JSONB,
    ADD COLUMN IF NOT EXISTS target_chosen JSONB;
```

Commit: `feat(db): add target_options + target_chosen to write_actions (migration 014)`

### Task A2: Generic resolver + Gmail recipient resolver

**Files:** Create `services/agent-orchestration/app/writeback/resolver.py`

```python
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
```

No tests in this commit — exercised by integration when Task A4's send capability lands.

Commit: `feat(orchestration): add target resolver framework + Gmail recipient resolver`

### Task A3: Gmail send + draft route handlers

**Files:** Modify `services/connector-manager/app/routes/tools.py` — add three endpoints.

Add Pydantic models near the existing Gmail block:
```python
class GmailSendRequest(BaseModel):
    user_id: str
    project_id: str
    to: str        # resolved email address
    subject: str
    body: str

class GmailDraftRequest(BaseModel):
    user_id: str
    project_id: str
    to: str
    subject: str
    body: str

class GmailResolveRequest(BaseModel):
    user_id: str
    project_id: str
    query: str
```

Add the routes (right after `/tools/gmail/search`):

```python
async def _get_gmail_client(user_id: str, project_id: str) -> GmailClient:
    repo = ConnectorsRepository(db.raw)
    token_row = await repo.get_token(user_id, project_id, "gmail")
    if token_row is None:
        raise HTTPException(404, "gmail is not connected for this project — connect it first")
    try:
        access_token = decrypt_token(token_row["auth_token_encrypted"])
    except Exception as e:
        logger.error("gmail_token_decrypt_failed", error=str(e))
        raise HTTPException(500, "failed to decrypt gmail token") from e
    return GmailClient(access_token=access_token)


@router.post("/tools/gmail/resolve-recipients")
async def gmail_resolve_recipients(body: GmailResolveRequest) -> dict[str, Any]:
    """Free-text → list of candidate email recipients. The capability layer
    in agent-orchestration imports the resolver class directly; this endpoint
    is here for the frontend's quick-search affordances later."""
    client = await _get_gmail_client(body.user_id, body.project_id)
    from agent_orchestration_dummy import GmailRecipientResolver  # noqa: TC001 — see note
    # NOTE: this endpoint is currently used only as a debugging affordance.
    # The real call path is: capability gmail.send → resolver → candidates →
    # write_actions row with target_options. The endpoint exists because the
    # frontend's command-palette quick-search ("@Mrinal") will hit it when
    # that affordance lands.
    raise HTTPException(501, "resolve-recipients endpoint reserved; use /capabilities/run instead")


@router.post("/tools/gmail/send")
async def gmail_send(body: GmailSendRequest) -> dict[str, Any]:
    """Send via Gmail — only called AFTER user confirmation (write gate)."""
    client = await _get_gmail_client(body.user_id, body.project_id)
    result = await client.send_message(to=body.to, subject=body.subject, body=body.body)
    return {
        "ok": True,
        "id": result.get("id"),
        "thread_id": result.get("threadId"),
        "to": body.to,
    }


@router.post("/tools/gmail/draft")
async def gmail_draft(body: GmailDraftRequest) -> dict[str, Any]:
    """Create a draft — does NOT send. Safe to call without confirmation."""
    client = await _get_gmail_client(body.user_id, body.project_id)
    # Reuse send_message's MIME building but call drafts.create instead.
    # GmailClient needs a small extension here:
    if not hasattr(client, "create_draft"):
        raise HTTPException(501, "GmailClient.create_draft not implemented yet")
    result = await client.create_draft(to=body.to, subject=body.subject, body=body.body)
    return {"ok": True, "id": result.get("id"), "to": body.to}
```

⚠️ **Implementer note for the agent dispatching this task:** The `agent_orchestration_dummy` import line above is a placeholder I left to flag that the capability layer owns the resolver — the route stays a thin executor. Replace with a `raise HTTPException(501, ...)` and the real resolver-driven flow goes through the capability in Task A4.

Also: `GmailClient.create_draft` doesn't exist yet. Adding it is part of this task — extend `connectors/gmail/src/client.py`:

```python
async def create_draft(self, *, to: str, subject: str, body: str) -> dict[str, Any]:
    """drafts.create wrapping a MIME message. Mirrors send_message but
    calls users.drafts().create instead of users.messages().send."""
    import base64
    from email.mime.text import MIMEText
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    # google-api-python-client is sync; run in thread.
    import asyncio
    def _do():
        return self._service().users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}},
        ).execute()
    return await asyncio.to_thread(_do)
```

(Adapt to whatever the existing send_message uses — copy its threading + error-handling style.)

Commit: `feat(connector-manager): add /tools/gmail/{send,draft} routes + GmailClient.create_draft`

### Task A4: gmail_write capabilities (with disambiguation gating)

**Files:** Create `services/agent-orchestration/app/capabilities/gmail_write.py`

This is the meat. Two capabilities: `connector.gmail.send` and `connector.gmail.draft`.

```python
"""Gmail write capabilities with recipient disambiguation.

Flow for `connector.gmail.send`:
  1. Capability inputs: { recipient_query, subject, body }
  2. Resolve recipients via GmailRecipientResolver
     - 0 results → ResolutionError → capability returns failure
     - 1 result → set to=that email, proceed to gate
     - >1 results → create write_action with target_options populated;
       return status='pending_target_pick'; planner pauses.
  3. If gate satisfied (single recipient or user picked one):
     - Compute write diff (subject + body preview)
     - Create write_action in 'pending' state
     - Publish write.preview event
     - Return status='pending_confirmation'
  4. On POST /writes/{id}/confirm: backend hits /tools/gmail/send
     and updates write_action.confirmed_by_user=True.

Mirrors notion_write.py's structure exactly — see that file for the
write_action lifecycle pattern.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import uuid4

import httpx

from app.capabilities.types import Capability, CapabilityResult, Citation
from app.clients.connector_manager import ConnectorManagerClient
from app.events import publish_event
from app.repositories.writes import WriteActionsRepository
from app.writeback.resolver import GmailRecipientResolver, ResolutionError


class _GmailSend:
    name = "connector.gmail.send"
    description = "Send an email via Gmail. Always gated; never auto."
    action_type = "write"
    default_permission = "ask"
    input_schema = {
        "type": "object",
        "properties": {
            "recipient_query": {"type": "string", "description": "Free-text recipient name or email"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["recipient_query", "subject", "body"],
    }

    async def __call__(
        self,
        *,
        user_id: str,
        project_id: str | None,
        org_id: str | None,
        inputs: dict[str, Any],
    ) -> CapabilityResult:
        if project_id is None:
            return CapabilityResult.error("gmail.send requires a project context")

        recipient_query: str = inputs["recipient_query"]
        subject: str = inputs["subject"]
        body: str = inputs["body"]

        # Step 1: resolve candidates
        cm_client = ConnectorManagerClient()
        # We need the GmailClient over HTTP — but the resolver expects
        # a client object. The resolver only needs `.search(...)`.
        # Build a small adapter that calls /tools/gmail/search.
        adapter = _RemoteGmailSearchAdapter(cm_client, user_id=user_id, project_id=project_id)
        resolver = GmailRecipientResolver(adapter)
        try:
            candidates = await resolver.resolve(
                recipient_query, user_id=user_id, project_id=project_id
            )
        except ResolutionError as e:
            return CapabilityResult.error(str(e))

        if not candidates:
            return CapabilityResult.error(
                f"Couldn't find anyone matching '{recipient_query}' in your Gmail."
            )

        # Step 2: create the write_action with target_options if N>1
        writes_repo = WriteActionsRepository()
        diff = {
            "before": None,
            "after": {"subject": subject, "body": body},
            "summary": f"Send email — subject: {subject}",
        }

        if len(candidates) == 1:
            chosen = candidates[0]
            pending = await writes_repo.create_pending(
                action_id=...,  # planner injects via ctx
                tool="gmail",
                target_id=chosen.id,
                target_type="email_address",
                diff=diff,
                target_options=None,
                target_chosen=chosen.as_dict(),
            )
            await publish_event(
                "write.preview",
                {"write_id": str(pending["id"]), "tool": "gmail", "diff": diff, "target": chosen.as_dict()},
            )
            return CapabilityResult.pending_confirmation(write_id=str(pending["id"]))

        # N>1: create the row, surface picker
        pending = await writes_repo.create_pending(
            action_id=...,
            tool="gmail",
            target_id=None,
            target_type="email_address",
            diff=diff,
            target_options=[c.as_dict() for c in candidates],
            target_chosen=None,
        )
        await publish_event(
            "write.target_pick_required",
            {
                "write_id": str(pending["id"]),
                "tool": "gmail",
                "options": [c.as_dict() for c in candidates],
            },
        )
        return CapabilityResult.pending_target_pick(write_id=str(pending["id"]))


class _GmailDraft:
    name = "connector.gmail.draft"
    description = "Create a Gmail draft — never sends."
    action_type = "write"
    default_permission = "auto"  # drafts are non-destructive
    input_schema = {
        "type": "object",
        "properties": {
            "recipient_query": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        },
        "required": ["recipient_query", "subject", "body"],
    }

    async def __call__(self, *, user_id, project_id, org_id, inputs) -> CapabilityResult:
        # Same resolver pattern; on resolution call /tools/gmail/draft directly
        # because drafts don't need user confirmation.
        # ... mirror _GmailSend up to step 1, then call cm_client.gmail_draft(...)
        # If multiple candidates: also pause for picker, but drafts don't need confirm.
        raise NotImplementedError("Implementer: mirror _GmailSend.resolve, then call /tools/gmail/draft directly when 1 candidate; for N>1 still pause for picker.")


CAPABILITIES = [_GmailSend(), _GmailDraft()]


# ---------------- internals ----------------


class _RemoteGmailSearchAdapter:
    """Adapter so GmailRecipientResolver can call /tools/gmail/search via HTTP
    instead of needing a direct GmailClient. Exposes a `.search(query, limit)` method."""

    def __init__(self, cm: ConnectorManagerClient, *, user_id: str, project_id: str) -> None:
        self._cm = cm
        self._user_id = user_id
        self._project_id = project_id

    async def search(self, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        # cm doesn't have gmail_search yet; either add it (mirroring slack_search) or use httpx directly.
        # Add to ConnectorManagerClient: async def gmail_search(self, *, user_id, project_id, query, limit) → POST /tools/gmail/search
        return await self._cm.gmail_search(
            user_id=self._user_id, project_id=self._project_id, query=query, limit=limit
        )
```

⚠️ **Implementer notes:**
1. `WriteActionsRepository.create_pending` signature must accept `target_options` and `target_chosen` kwargs. Add them — see Task A5.
2. `CapabilityResult.pending_target_pick` doesn't exist yet — add it next to `.pending_confirmation` in `app/capabilities/types.py` (mirror the existing one but with status `pending_target_pick`).
3. `ConnectorManagerClient.gmail_search` must exist — add it mirroring `slack_search`.
4. Read `notion_write.py` carefully — copy the exact `action_id=` injection pattern (it comes from the planner's ctx, not the inputs).

Commit: `feat(orchestration): add gmail.send + gmail.draft capabilities with recipient disambiguation`

### Task A5: WriteActionsRepository changes + /writes/{id}/choose-target route

**Files:**
- Modify: `services/agent-orchestration/app/repositories/writes.py` — `create_pending` accepts `target_options` and `target_chosen`; new `choose_target(write_id, chosen)` updates the row.
- Modify: `services/agent-orchestration/app/main.py` — add `POST /writes/{write_id}/choose-target { chosen: TargetCandidate dict }` that updates the row + republishes `write.preview`.
- Modify: `services/agent-orchestration/app/capabilities/types.py` — add `pending_target_pick` factory on `CapabilityResult`.

Skeleton for the new route:
```python
@app.post("/writes/{write_id}/choose-target")
async def choose_write_target(write_id: str, body: dict[str, Any]) -> dict[str, Any]:
    chosen = body.get("chosen")
    if not chosen or not chosen.get("id"):
        raise HTTPException(400, "chosen target missing or malformed")
    repo = WriteActionsRepository()
    updated = await repo.choose_target(write_id, chosen)
    if not updated:
        raise HTTPException(404, "write not found or already executed")
    await publish_event(
        "write.target_chosen",
        {"write_id": write_id, "chosen": chosen, "diff": updated["diff"]},
    )
    return {"ok": True, "write_id": write_id, "target_id": chosen["id"]}
```

Commit: `feat(orchestration): support target_options + /writes/{id}/choose-target`

---

## Phase B — Frontend: TargetPicker + WritePreviewCard wiring

### Task B1: TargetPicker primitive

**Files:**
- Create: `packages/design-system/src/components/target-picker/{target-picker.tsx, target-picker.test.tsx, index.ts}`
- Modify: `packages/design-system/src/index.ts` (export)

Component contract:
```typescript
export interface TargetCandidate {
  kind: string;
  id: string;
  label: string;
  sub_label: string | null;
  context: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface TargetPickerProps {
  candidates: ReadonlyArray<TargetCandidate>;
  onChoose: (candidate: TargetCandidate) => void;
  busy?: string | null;  // candidate id currently being submitted
  /** Optional helper text — e.g., "Couldn't tell which Mrinal you meant — pick one:" */
  prompt?: string;
}
```

Render: a list of cards (one per candidate) with primary label, sub_label small mono, context as a snippet line; click → onChoose. Busy state on the card matching `busy === candidate.id`.

Tests: renders all candidates, click fires onChoose with the right one, busy state shows on the right card.

Commit: `feat(design-system): build TargetPicker primitive`

### Task B2: Extend WritePreviewCard to render TargetPicker

**Files:** Modify `packages/design-system/src/components/write-preview-card/write-preview-card.tsx`

Add two optional props:
- `targetOptions?: TargetCandidate[]` — when present and length > 1, render TargetPicker INSTEAD of the body + footer.
- `onChooseTarget?: (c: TargetCandidate) => void` — invoked when picker fires.

Logic: if targetOptions && targetOptions.length > 1 && !targetChosen, render the picker. Otherwise, the existing body+footer.

Tests: extend the existing test file with two new cases — picker visible when targetOptions has 2+, picker hidden when targetChosen is set.

Commit: `feat(design-system): render TargetPicker inside WritePreviewCard when disambiguation needed`

### Task B3: useChooseTarget hook + chat page wiring

**Files:**
- Create: `apps/web/lib/queries/writes.ts` — adds `useChooseTarget()` mutation calling `POST /writes/{id}/choose-target`.
- Modify: chat page or wherever WritePreviewCard is rendered today — read the live event `write.target_pick_required`, render WritePreviewCard with `targetOptions`, on choose call the mutation.

Commit: `feat(web): wire TargetPicker into chat write-preview flow`

---

## Phase C — GitHub write (no disambiguation needed)

### Task C1: GitHub write routes + capabilities

GitHub issue/PR numbers are unambiguous so no resolver — just the gate.

**Files:**
- Modify: `services/connector-manager/app/routes/tools.py` — add `/tools/github/comment` and `/tools/github/create-issue`.
- Create: `services/agent-orchestration/app/capabilities/github_write.py` — `_GitHubComment` + `_GitHubCreateIssue` capabilities, both gated, mirror `_GmailSend` minus the resolver block.

Routes (mirror Notion's pattern):
```python
class GitHubCommentRequest(BaseModel):
    user_id: str
    project_id: str
    repo: str            # "owner/repo"
    issue_number: int
    body: str

@router.post("/tools/github/comment")
async def github_comment(body: GitHubCommentRequest) -> dict[str, Any]:
    """Comment on issue/PR — only called AFTER user confirmation."""
    client = await _get_github_client(body.user_id, body.project_id)
    res = await client.create_issue_comment(repo=body.repo, issue_number=body.issue_number, body=body.body)
    return {"ok": True, "id": res.get("id"), "url": res.get("html_url")}


class GitHubCreateIssueRequest(BaseModel):
    user_id: str
    project_id: str
    repo: str
    title: str
    body: str = ""
    labels: list[str] = Field(default_factory=list)

@router.post("/tools/github/create-issue")
async def github_create_issue(body: GitHubCreateIssueRequest) -> dict[str, Any]:
    """Create issue — only called AFTER user confirmation."""
    client = await _get_github_client(body.user_id, body.project_id)
    res = await client.create_issue(repo=body.repo, title=body.title, body=body.body, labels=body.labels)
    return {"ok": True, "number": res.get("number"), "url": res.get("html_url")}
```

⚠️ `GitHubClient.create_issue` may not exist yet. Check `connectors/github/src/client.py` and add it if missing (uses the GitHub API `POST /repos/{owner}/{repo}/issues`).

Capabilities mirror `_GmailSend` minus the resolver — just compute the diff, create write_action, return pending_confirmation.

Commit: `feat: GitHub write — comment + create-issue with confirmation gating`

---

## Phase D — Capability registry alignment + verify

### Task D1: Frontend `capabilities.ts` cleanup

**Files:** Modify `apps/web/lib/capabilities.ts`

The current list declares `connector.gmail.send` and `connector.github.write` as if they exist. Now they will. Update the list to match the actual backend capability set:

```typescript
export const CAPABILITIES: ReadonlyArray<CapabilityMeta> = [
  // ... existing read entries
  { id: 'connector.slack.write',  tier: 1, label: 'Post to Slack',     description: 'Send messages to channels and DMs.' },
  { id: 'connector.notion.write', tier: 1, label: 'Edit Notion',       description: 'Append blocks to pages.' },
  { id: 'connector.gmail.draft',  tier: 1, label: 'Draft Gmail',       description: 'Create drafts. Never sends.' },
  { id: 'connector.gmail.send',   tier: 2, label: 'Send Gmail',        description: 'Send email on your behalf — irreversible.' },
  { id: 'connector.gdrive.write', tier: 1, label: 'Edit Google Drive', description: 'Create + append docs.' },
  { id: 'connector.github.write', tier: 1, label: 'Comment on GitHub', description: 'Comment on issues + PRs.' },
  { id: 'connector.github.create_issue', tier: 1, label: 'Create GitHub issue', description: 'Create new issues.' },
];
```

Commit: `chore(web): align capabilities.ts with the actual backend capability set`

### Task D2: Verify

- Backend tests: `pnpm --filter` doesn't run Python — note migration applies cleanly with `make infra-up` rebuild.
- Frontend Vitest + Playwright still green.
- Type-check + lint clean.
- Manual smoke: connect a Gmail sandbox, type "send mail to <name with multiple matches>", confirm picker appears, pick one, confirm preview appears, click Confirm, confirm send happens.

Commit nothing if no changes.

---

## What you have at the end

- Migration 014 (target_options + target_chosen on write_actions).
- `GmailRecipientResolver` + reusable `TargetCandidate` framework.
- Gmail send + draft capabilities with full disambiguation.
- `/tools/gmail/{send,draft}` routes + `GmailClient.create_draft`.
- GitHub comment + create-issue with the gate.
- New `/writes/{id}/choose-target` endpoint.
- `TargetPicker` design-system primitive.
- `WritePreviewCard` extended for picker.
- Frontend chat wiring for the picker flow.
- `capabilities.ts` aligned with reality.

## What's deferred to Plan 12+

- Slack post / Slack react / Drive create-doc / Drive append → retrofit to use the new gate (currently capability-permission only).
- Slack DM with user disambiguation.
- Slack channel disambiguation ("post to #product" when there's #product-eng + #product-marketing).
- Notion mention with user disambiguation.
- Webhook handlers (Gmail Pub/Sub, Drive push, GitHub).
- Gmail label/archive ops.
- GitHub get-issue / get-PR detail routes.
