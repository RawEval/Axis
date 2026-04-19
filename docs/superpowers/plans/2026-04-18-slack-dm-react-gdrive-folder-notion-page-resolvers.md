# Axis Plan 13 — Slack DM + Slack React + GDrive Folder + Notion Page resolvers

> REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.

**Goal:** Apply the Plan 11/12 resolver+gate pattern to the four remaining write capabilities so every write across all 5 connectors goes through uniform diff-preview + disambiguation.

**Pattern (already established, repeated mechanically):**
```
capability call → build adapter → resolver.resolve(query) → 0/1/N branch
  N=0 → CapabilityResult(error="couldn't find ...")
  N=1 → WritesRepository.create_pending(target_chosen=...) → publish "write.preview" → CapabilityResult(content={status: pending_confirmation, write_id, ...})
  N>1 → WritesRepository.create_pending(target_options=[c.as_dict() for c in candidates], target_id="") → publish "write.target_pick_required" → CapabilityResult.pending_target_pick(write_id=...)
```

Frontend already handles all three event types (Plan 11 B3) — no UI changes.

**Out of scope (Plan 14):** webhook handlers (Gmail Pub/Sub, GDrive push, GitHub) — fundamentally different work (receivers + provider HMAC verification + subscription registration).

---

## File structure

**Modify:**

```
services/agent-orchestration/app/writeback/resolver.py     # +SlackUserResolver, +GDriveFolderResolver, +NotionPageResolver
services/agent-orchestration/app/capabilities/slack.py     # new _SlackDM capability + retrofit _SlackReact
services/agent-orchestration/app/capabilities/gdrive.py    # retrofit _GDriveCreateDoc with optional folder resolver
services/agent-orchestration/app/capabilities/notion_write.py  # retrofit _NotionAppend to use NotionPageResolver
apps/web/lib/capabilities.ts                               # add connector.slack.dm
```

**Total:** 5 modified files, ~3 commits.

---

## Phase A — Resolvers + retrofits

### Task A1: Three new resolvers

**File:** `services/agent-orchestration/app/writeback/resolver.py`

Append three classes after the existing resolvers, mirroring `SlackChannelResolver` / `GDriveDocResolver` shape.

#### `SlackUserResolver`
Calls a `users_lister` adapter that returns Slack `users.list` rows. Filters by `name`, `real_name`, or `display_name` substring (case-insensitive). Returns:
- `kind="slack_user"`
- `id=U…` (Slack user id)
- `label=real_name or name`
- `sub_label=email if profile.email else None`
- `context=title from profile if any` (else None)
- `metadata={is_bot, is_admin, deleted}` — exclude rows where `deleted=True` from output entirely

#### `GDriveFolderResolver`
Calls a `search` adapter (raw search). Filters to `mimeType == 'application/vnd.google-apps.folder'`. Returns:
- `kind="gdrive_folder"`
- `id`
- `label=name`
- `sub_label=webViewLink`
- `context=f"in {parent_name}" or None`

#### `NotionPageResolver`
Calls a `search` adapter (Notion search via /tools/notion/search). Returns one candidate per page hit:
- `kind="notion_page"`
- `id=page_id`
- `label=last_edited title from properties.title or url path tail`
- `sub_label=url`
- `context=last_edited_time + " · " + (icon emoji if any)`

After: `python -m py_compile services/agent-orchestration/app/writeback/resolver.py` must pass.

Commit: `feat(orchestration): add SlackUserResolver + GDriveFolderResolver + NotionPageResolver`

### Task A2: Slack DM capability + Slack react retrofit

**File:** `services/agent-orchestration/app/capabilities/slack.py`

#### Add `_SlackDM`

New capability `connector.slack.dm` mirrors `_SlackPost` but:
- Resolver: `SlackUserResolver` (use a `_SlackUsersAdapter` mirroring `_SlackChannelsAdapter`)
- Inputs: `{user_query: str, text: str}`
- Diff: `{after: {user_id: None|resolved, text}, summary: f"DM to … : {text[:50]}"}`
- target_type="slack_user"
- Backward-compat: if `inputs.get("user")` starts with `U`, use directly.

If `cm.slack_users` doesn't exist, add it to `services/agent-orchestration/app/clients/connector_manager.py` mirroring `slack_channels`. Confirm there's a `/tools/slack/users` route — if not, add a thin one in `services/connector-manager/app/routes/tools.py` that calls `client.list_users()`. Read `connectors/slack/src/client.py` for the SlackClient method name.

#### Retrofit `_SlackReact`

The `react` op needs `channel_id` + `timestamp` (message permalink). The timestamp is unambiguous so no resolver needed — just add the write gate. Same shape:
- Build single-candidate target (`{kind: "slack_message", id: f"{channel}:{ts}", label: ":emoji:", sub_label: ts}`)
- Create write_action with target_chosen, publish `write.preview`, return pending_confirmation
- No N>1 branch (always exactly 1)

Commit: `refactor(orchestration): add slack.dm capability + slack.react write gate`

### Task A3: GDrive create-doc folder resolver + Notion page resolver retrofit

**Files:** `gdrive.py` + `notion_write.py`

#### Retrofit `_GDriveCreateDoc`

Currently takes optional `folder_id`. Refactor to also accept `folder_query`:
- If `folder_id` is set → use directly (backward-compat)
- If `folder_query` is set → run `GDriveFolderResolver`
  - 0 folders matching → "couldn't find folder X" error (do NOT silently default to root)
  - 1 folder → use as target_chosen, write_action with `target_type="gdrive_folder"`, publish `write.preview`
  - N>1 → publish `write.target_pick_required`
- If neither → use root (existing behavior; create at user's Drive root with no folder pick)

#### Retrofit `_NotionAppend`

Currently takes `page_id` directly. Add `page_query` alternative:
- If `page_id` is set → backward-compat, use directly
- If `page_query` is set → run `NotionPageResolver`
  - Same 0/1/N branching

Both retrofits preserve the existing diff structure (block list before/after for Notion; new-doc spec for Drive).

Commit: `refactor(orchestration): gdrive.create_doc + notion.append accept query-based target with resolver`

### Task A4: Frontend `capabilities.ts`

Add `connector.slack.dm` to the `CapabilityId` union and to `CAPABILITIES` array (tier 1 — DMs are reversible by deletion):
```typescript
{ id: 'connector.slack.dm', tier: 1, label: 'DM on Slack', description: 'Send a direct message to a Slack user.' },
```

Place it next to `connector.slack.post`.

Commit: `chore(web): add connector.slack.dm to capabilities.ts`

---

## Phase B — Verify

```bash
cd /Users/mrinalraj/Documents/Axis && \
  python3 -m py_compile services/agent-orchestration/app/writeback/resolver.py \
                       services/agent-orchestration/app/capabilities/slack.py \
                       services/agent-orchestration/app/capabilities/gdrive.py \
                       services/agent-orchestration/app/capabilities/notion_write.py \
                       services/agent-orchestration/app/clients/connector_manager.py \
                       services/connector-manager/app/routes/tools.py && \
  pnpm test 2>&1 | grep -E "(Test Files|Tests).*passed" | head -5 && \
  pnpm --filter @axis/web type-check 2>&1 | tail -3 && \
  pnpm lint 2>&1 | tail -3 && \
  pnpm --filter @axis/web build 2>&1 | grep -E "(Compiled|Failed)" | head -2
```

Expected: all Python files compile, design-system 120 + web 31 tests pass, type-check + lint + build green. (No commit for verify.)

---

## What you have at the end

- 4 new write capability surfaces using the established resolver+gate pattern.
- Every write across all 5 connectors now has uniform behavior: diff preview + disambiguation when needed + user confirmation before execute.
- Frontend `<TargetPicker>` (Plan 11 B1) handles all 6 candidate kinds out of the box.

## Self-Review

- **Spec coverage:** Closes Plan 12's deferred items completely. Webhook handlers (Plan 14) are the only remaining connector work.
- **Type consistency:** All 6 resolvers return `list[TargetCandidate]` with the same kind→consumer mapping. All 6 retrofitted/new capabilities use the same `WritesRepository.create_pending` pattern.
- **Backward compat:** Every retrofit accepts both old direct-id input and new query-based input. Existing callers don't break.
- **No frontend work:** Plan 11 B3 wired the picker for any `TargetCandidate[]`; the frontend doesn't need to know about new resolver kinds.
