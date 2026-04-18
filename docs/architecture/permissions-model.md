# Permissions Model — Claude-Code-style interactive grants

**Decision date:** 2026-04-16
**Status:** Design (Phase 2 implementation)
**ADR number:** 006

## Context

Phase 1 gates only **writes**. Every read (query Slack, fetch a Notion page) runs silently — if the OAuth token has the scope, the agent uses it.

Your message made the bar higher: users want to know when their data is being read, not just written. Like Claude Code's "Are you sure I should read this file?" prompt, but with the ability to remember the answer.

## Decision

Introduce a **permission grant** object — first-class DB row — with these axes:

| Axis | Values |
|---|---|
| **Scope** | `user` (all projects) / `project` (this project) / `task` (this run only) |
| **Capability** | e.g. `connector.notion.read`, `connector.gmail.send`, `web.fetch`, `git.clone` |
| **Action** | `read` / `write` / `execute` |
| **Lifetime** | `session` (until logout) / `24h` / `project-lifetime` / `forever` |
| **Decision** | `granted` / `denied` |

Before a capability executes, the agent checks for a matching grant. If none, it **pauses the task**, emits a `permission_request` event via the streaming layer, and waits.

## Schema

```sql
CREATE TABLE permission_grants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,  -- NULL = user-wide
    capability TEXT NOT NULL,   -- e.g. 'connector.notion.read'
    action TEXT NOT NULL,       -- read | write | execute
    decision TEXT NOT NULL,     -- granted | denied
    lifetime TEXT NOT NULL,     -- session | 24h | project | forever
    expires_at TIMESTAMPTZ,     -- NULL for 'forever' or 'project'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    granted_by TEXT NOT NULL DEFAULT 'user',   -- user | auto | system
    CHECK (decision IN ('granted', 'denied')),
    CHECK (action IN ('read', 'write', 'execute')),
    CHECK (lifetime IN ('session', '24h', 'project', 'forever'))
);
CREATE INDEX ON permission_grants (user_id, capability, action);
CREATE INDEX ON permission_grants (project_id) WHERE project_id IS NOT NULL;
```

## Defaults

These are baked into the capability registry and are the most important piece of UX:

| Capability | Default | Rationale |
|---|---|---|
| `connector.*.read` | **ask first time**, remember for session by default | Reads are low-risk but users want awareness the first time |
| `memory.retrieve` | **auto** (never ask) | User's own memory |
| `web.search`, `web.fetch` | **auto** (never ask) | Public internet data |
| `connector.*.write` (append/comment) | **ask every time** unless trust=high | Reversible writes |
| `connector.gmail.send` | **always gate, every time**, no matter what | Irreversible, spec §6.5 |
| `connector.github.merge` | **always gate, every time** | Irreversible |
| `connector.*.delete` | **always gate, every time** | Irreversible |
| `git.clone` (public repos) | **auto** | Public code |
| `git.push` (to remote) | **always gate** | Irreversible |
| `code.run` (sandboxed) | **ask first time**, remember for session | Low risk, sandboxed |
| `code.run` (network out) | **ask every time** | Could leak data |

"Always gate, every time" is non-negotiable and cannot be changed by the user. This is the trust floor.

## Resolution order

When the supervisor tries to call a capability, the permission service checks:

```
def check_grant(user_id, project_id, capability, action) -> Decision:
    # 1. Task-scope grant (this run only) — in-memory, not persisted
    if task_grants.get((capability, action)) == "granted":
        return AUTO_GRANTED

    # 2. Project-scope grant
    row = find_grant(user_id, project_id, capability, action,
                     lifetime in ['project', '24h', 'session'])
    if row:
        return row.decision

    # 3. User-scope grant (across all projects)
    row = find_grant(user_id, None, capability, action,
                     lifetime in ['forever', '24h', 'session'])
    if row:
        return row.decision

    # 4. Default from capability registry
    default = capability_registry[capability].default_permission
    if default == "auto":
        return AUTO_GRANTED
    if default == "always-gate":
        return ASK_USER_EVERY_TIME
    # "ask first time"
    return ASK_USER_AND_REMEMBER
```

## The pause-ask-resume flow

When a grant is missing, the agent task transitions to `awaiting_confirmation`:

```
supervisor wants to call connector.notion.read
  → check_grant() returns ASK_USER_AND_REMEMBER
  → task.status = 'awaiting_confirmation'
  → emit event via Redis pub/sub:
      {
        "type": "permission_request",
        "task_id": "...",
        "step_id": "...",
        "capability": "connector.notion.read",
        "action": "read",
        "context": {"workspace": "Acme", "pages_to_read": 3},
        "suggested_lifetime": "session"
      }
  → gateway WebSocket fans it out to the user's active connection
  → web renders a modal: "Axis wants to read from Notion (Acme workspace, 3 pages).
                          [Allow once] [Allow for this task] [Allow for this project]
                          [Allow always] [Deny]"
  → user clicks; POST /permissions/grant with (capability, lifetime, decision)
  → backend persists the grant (if lifetime != 'once')
  → backend emits {type: "permission_granted"} via pub/sub
  → orchestrator wakes up and resumes the supervisor loop
```

## API surface

```
GET    /permissions                                list all grants for user
GET    /permissions?project_id=<uuid>              project-scoped
POST   /permissions/grant                          { capability, action, lifetime, project_id? }
POST   /permissions/deny                           same shape
DELETE /permissions/{grant_id}                     revoke
GET    /permissions/pending?task_id=<uuid>         what's blocking
```

## UX patterns (important for product feel)

### First-time permission

A modal with the context spelled out:

> **Axis wants to read from Gmail.**
>
> This is for the task: *"Find the email from Samir about the vendor renewal."*
>
> - It will search your inbox for messages from `samir@*` matching "vendor renewal"
> - No messages will be sent or deleted
> - Axis will not store the email bodies beyond this task unless you ask it to
>
> **[Allow once] [Allow for this task] [Allow for this project] [Allow always] [Deny]**

### Subsequent uses

Once granted, reads happen silently. A small badge in the live task tree shows "reading from Gmail (granted)". The user can click it to see the specific query + revoke the grant inline.

### Always-gated actions

The banner is different:

> **Axis wants to send an email on your behalf.**
>
> To: `samir@example.com`
> Subject: `Re: vendor renewal`
> Body:
> ```
> Hi Samir, confirming we'll ship by EOD Friday as discussed…
> ```
>
> **[Review and edit] [Send] [Cancel]**
>
> *You'll always be asked before sending.*

The "remember" option is absent. This is the trust floor.

## Permissions review UI

Settings → Permissions → shows:

- User-wide grants (one list)
- Per-project grants (collapsible per project)
- Pending requests (if any task is awaiting)
- Default capability behavior (read-only, cannot be edited below the floor)

Each row has: what, when granted, expires when, revoke button.

## Auditability

Every grant write + every denied request is recorded in `permission_events`:

```sql
CREATE TABLE permission_events (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    project_id UUID,
    task_id UUID,
    step_id UUID,
    capability TEXT NOT NULL,
    action TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- requested | granted | denied | auto_granted | revoked
    context JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Users can export this from Settings → Audit Log. Required for SOC 2 (spec §10).

## Degradation path

If the streaming layer is down and an agent hits a permission gate, it:
1. Writes the `permission_request` to `permission_events`
2. Marks the task `awaiting_confirmation`
3. Emails the user a magic link (Phase 2) or displays the pending request on the next page load
4. Resumes on the user's next visit

This means the product is still usable when WebSocket connectivity is flaky.

## Phase-1 → Phase-2 migration

Phase 1 has a de-facto permission model: connect a tool → grant all reads and writes on that tool. Migration to the explicit model:

1. On first login after the feature ships, for each connected tool, backfill a `forever` grant for `connector.<tool>.read` at user scope. (Users already consented to this by connecting.)
2. Writes still require confirmation. No backfill for writes.
3. User can tighten any time from Settings → Permissions.

## See also

- `agentic-architecture.md` — where capabilities come from
- `streaming-real-time.md` — how permission requests flow to the UI
- `use-cases.md` — concrete permission flows
