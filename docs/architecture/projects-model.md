# Projects — the unit of work

**Decision date:** 2026-04-16
**Status:** Active
**ADR number:** 002

## Context

Axis was scaffolded with user-level isolation: every row in the DB carried a `user_id` and that was the tenant boundary. That shape works for a diary app — it does not work for Axis, where a single user naturally has multiple distinct contexts:

- "My startup's internal ops" (Slack = company workspace, Notion = private wiki)
- "Client engagement with Acme Corp" (Slack = shared connect channel, Drive = Acme's shared folder)
- "Personal side project" (GitHub = personal account, Notion = personal workspace)

Mixing these under one `user_id` bucket makes the proactive layer useless (signals from unrelated contexts collide), ruins the eval loop (corrections don't generalize across contexts), and breaks mental models ("what happened in my Slack" is ambiguous across two different Slacks).

## Decision

**Introduce `projects` as the unit of work.** Every domain row is scoped to a `(user_id, project_id)` pair. Connectors, agent actions, proactive surfaces, write actions, correction signals, and memory namespaces all belong to a project.

```
User (1)
  ├── Project A "Internal Ops"
  │     ├── Connector: Slack (company workspace)
  │     ├── Connector: Notion (private wiki)
  │     └── Agent actions, feed, memory …
  ├── Project B "Acme Engagement"
  │     ├── Connector: Slack (shared connect)
  │     ├── Connector: Drive (Acme folder)
  │     └── …
  └── Project C "Personal"
        └── …
```

A user automatically gets a "Personal" project on first signup. Additional projects are self-service; no admin approval.

## Schema

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, name)
);

-- Add project_id to every tenant table
ALTER TABLE connectors         ADD COLUMN project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE agent_actions      ADD COLUMN project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE proactive_surfaces ADD COLUMN project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE write_actions      ADD COLUMN project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE correction_signals ADD COLUMN project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
```

`(user_id, project_id)` is the canonical tenant key. Every query must filter by both.

## Single-owner vs shared (punt)

Phase 1: each project has exactly one owner (`user_id`). No sharing, no members. The spec §4 persona is "startup ops lead" or "founder" — single user, multiple personal contexts.

Phase 2 (deferred): a `project_members` table to share projects across users. Role-based (owner / editor / viewer). Not in scope for this doc; add it when the first user asks.

## Isolation

- **Application-level**: every repository method takes `(user_id, project_id)` as the first two args. Queries filter both.
- **Memory-level**: Qdrant collections named `axis-{project_id}`. Neo4j nodes labeled with `:Project_{project_id}`. Memory never crosses project boundaries.
- **Credentials-level**: OAuth tokens in `connectors.auth_token_encrypted` are keyed by `(user_id, project_id, tool_name)`. A user can connect Slack to both Project A and Project B with different tokens (different workspaces).
- **DB-level (Phase 2)**: when we move to Supabase, re-enable RLS with policies `USING (user_id = auth.uid())`. Project isolation remains application-level unless we add `current_setting('axis.project_id')` session vars.

## Routing (the "user level 2")

When a user sends a prompt, one of three things happens:

1. **Explicit pin**: the UI has an active project selected. The frontend sends `X-Axis-Project: <uuid>` on every request. The router node trivially uses that project.
2. **All mode**: the user chose "all projects". The router fans out to every project the user owns; agent runs in parallel (one per project); results are merged in a final synthesis node.
3. **Auto mode**: no active project, user just typed a question. A Haiku classifier reads the prompt + the list of `(project_name, project_description)` for this user and picks one (or says "ambiguous — ask the user"). Ship Phase 1 with explicit + all. Auto-classifier lands Phase 2 once we have enough projects per user for it to matter.

See `project-router.md` for the full design.

## Migration for existing users

`005_projects.sql` inserts a `(user_id, name='Personal', is_default=true)` row for every existing user and backfills `project_id` on every row in the tenant tables. Goes out as a single atomic migration.

## What this buys us

- **Cleaner mental model**: "what happened in my Slack this week" now means "my Slack in this project."
- **Clean proactive layer**: surfaces can't cross-contaminate contexts.
- **Clean correction loop**: "don't summarize like that" scopes to one project's style.
- **Multiple workspaces per tool**: a user can connect two different Slack workspaces (one per project) — today's schema (`UNIQUE(user_id, tool_name)`) actually blocks this. We change the unique constraint to `(user_id, project_id, tool_name)` in the migration.
- **Shareability later**: adding a `project_members` table in Phase 2 unlocks team accounts without reshaping the data model again.

## What it does not buy us

- Per-project billing. For now every project of a user rolls up to that user's plan. Team plans will need per-project quotas; ship with Phase 2.
- Cross-project memory. A fact learned in Project A is not available to Project B. Intentional for Phase 1 — users will ask for exceptions when they hit them.

## Open questions (answer as we ship)

- Do we let users rename the `Personal` project? Yes, but we keep the `is_default` flag so the UI can still fall back to it when no project header is set.
- Soft delete vs hard? Hard delete with `ON DELETE CASCADE` for Phase 1. Eventually add a trash / undo window.
- Project count cap? No cap in free tier, but proactive monitoring across 20 projects is expensive — enforce a soft cap at 10 via feature flag `PROJECT_MAX_COUNT`.

## See also

- `byo-credentials.md` — how user-supplied OAuth client_id/secret plugs in
- `project-router.md` — the user-level-two classification layer
- `prompt-flow.md` — end-to-end trace through the new architecture
- `use-cases.md` — the plethora of workflows this enables
