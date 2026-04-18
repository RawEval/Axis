# Use cases — the plethora

This is the ground-truth reference for "what can a user actually do with Axis." Every feature we ship should map to at least one of these. When we design new API surfaces, check them against this list first.

Organized by persona, by tool, by temporal mode (reactive vs proactive), and by action type (read vs write vs synthesise). Not exhaustive — a living doc.

---

## Persona 1 — The startup ops lead (primary)

### Reactive queries

**Daily triage**
- "What happened in #product yesterday?" → Slack read + summary
- "What are the top 3 things I should know from email this morning?" → Gmail prioritize
- "Did anyone reply to the Acme contract thread?" → Gmail search + status
- "Is the deploy blocker in Linear still open?" → Linear query

**Search-as-a-service (your message example)**
- "Find the email from Samir about the vendor renewal" → Gmail natural-language search
- "Show me every doc that mentions our pricing decision" → Drive + Notion full-text
- "Where did we decide to ship Feature X on Nov 1?" → cross-tool decision audit (the killer query for §6.3 unrecorded decisions)

**Cross-tool join**
- "What's the status of every feature mentioned in the roadmap doc?" → Notion read → Linear query
- "For every ticket I opened last week in Linear, find the Slack thread it came from" → Linear + Slack join
- "Which of my Jira tickets have PRs open?" → Jira + GitHub join (Phase 2)

### Cross-project queries (user-level-two)
- "What follow-ups am I owing anyone this week?" → fan out across every project
- "Which client engagements have open blockers?" → classifier picks multi-project → merge
- "What did Aditi say about the vendor renewal?" (classifier picks 1 project if unambiguous, asks otherwise)

### Write actions (gated)
- "Draft a reply to Samir confirming we'll ship by EOD Friday" → Gmail draft (user confirms send)
- "Create a Linear ticket for the deploy bug from #incidents" → Linear create
- "Update the roadmap doc to reflect the new ship date" → Notion append
- "Comment on PR #42 that this needs a second reviewer" → GitHub comment

### Proactive surfaces (§6.3)
- "You have 3 Slack DMs from yesterday you haven't replied to"
- "The roadmap doc hasn't been updated but 4 feature ships were discussed in #product"
- "Your Linear ticket 'Fix checkout flow' is 2 days past due"
- "Aditi's PR has been waiting for review for 18 hours"

---

## Persona 2 — The founder / CEO

### Morning brief
- Daily digest at 8am local: unresolved threads + stale docs + upcoming deadlines + open decisions
- Configurable: "tell me the headline, hide everything else"
- Can reply to any surface inline from the brief notification

### Quick mobile actions (Phase 2)
- Voice: "Send Aditi a quick thanks for handling the incident last night"
- Swipe-to-confirm on writes
- Widget on home screen for instant prompt

---

## Persona 3 — Head of AI / Technical PM

### Eval loop integration
- "Show me every agent output from last week where I corrected the summary" → eval dashboard
- "What's our fine-tune dataset size this month?" → correction signals count
- "Which rubric dimensions are we weakest on?" → eval trend query

### Internal tool ops
- Connects Axis to their internal PostHog / Grafana / BigQuery via HTTP connector
- "Alert me when MRR drops more than 2% week-over-week" → threshold proactive surface

---

## By tool (Phase 1 connectors)

### Slack
- **Read**: "What did I miss in #product?" "Find the thread about the checkout bug"
- **Write**: "Post a reminder in #engineering" "DM Aditi the incident report"
- **Proactive**: unanswered DMs, stale threads, decisions with no docs

### Notion
- **Read**: "Find the doc about Q3 planning" "Summarize the roadmap" "Show me every page Aditi wrote last month"
- **Write**: "Append today's standup notes to the team page" "Create a meeting notes doc from this transcript"
- **Proactive**: stale pages referenced in conversations, contradiction between two pages on the same topic

### Gmail
- **Read** (your message example): "Find the email from John about the contract" "Summarize unread from this week" "What's in my inbox about payments?"
- **Write**: "Draft a reply" "Send a status update to the client team" (always requires explicit confirmation per spec §7)
- **Proactive**: unreplied 24h+, commitments detected ("I'll get back to you by Friday")

### Google Drive
- **Read**: "Find the slide with the revenue chart" "Show me docs edited by anyone other than me this week"
- **Write**: "Add a section to the proposal doc" "Create a new doc with the meeting summary"
- **Proactive**: contradicting versions of the same doc, external sharing alerts

### GitHub
- **Read**: "What PRs are waiting on my review?" "Show me issues closed this week in axis-monorepo" "Summarize the commits to main since Monday"
- **Write**: "Comment on PR #42" "Commit this markdown change to docs/" "Open an issue for the deploy failure" (writes to main branch always gated)
- **Proactive**: CI failures on main, stale draft PRs, security alerts

### Linear (Phase 2)
- **Read**: "Show me my tickets due this week" "What's blocking the P0?"
- **Write**: "Create a ticket for the design bug" "Move the checkout issue to In Review"
- **Proactive**: approaching due dates, tickets with no owner

### Google Calendar (Phase 2)
- **Read**: "What's my schedule tomorrow?" "Who am I meeting with Aditi this week?"
- **Write**: "Block 2 hours tomorrow for the architecture review"
- **Proactive**: back-to-back meetings, meetings with no prep docs

---

## By temporal mode

### Reactive (user types something)
- Single-project: router trivially picks the active project, runs once
- Multi-project: router fans out, merges

### Proactive (background)
- Per project, per signal type, per user's daily cap
- Surfaces land in the feed and optionally push notification

### Scheduled
- Morning brief (daily digest)
- Weekly retrospective (Phase 2)
- Custom rules (Phase 3 — "every time a Linear ticket is marked Done, post in #product")

---

## By action type

### Read-only (no confirmation)
Anything that queries a tool and returns a result to the user. Zero risk. Fast path, no gates.

### Write with preview
1. User prompts "post a reminder in #eng"
2. Agent drafts the message
3. UI shows `DiffViewer` with the exact content that will be sent
4. User clicks "Confirm" (or edits and re-confirms)
5. Action executes
6. Rollback available for 30 days (spec §6.5)

### Destructive writes (always gated regardless of trust)
- Gmail send
- GitHub force-push or merge
- Drive delete
- Notion archive
- Linear ticket delete

Even at high trust level, these need explicit user confirmation every time.

---

## By project mode

### One project pinned (most common)
- User selects "Acme Engagement" in the sidebar
- Every prompt runs in that project's context
- Fast, unambiguous, zero overhead

### "All projects" mode
- User selects "All" in the project picker
- Router fans out to every project
- Each project runs in parallel with its own connectors
- Results merged by a Sonnet pass
- Use for cross-cutting questions: "What follow-ups do I owe?"

### Auto mode (Phase 2)
- User doesn't pick a project, just types
- Haiku classifier reads the prompt + project metadata, picks the most likely project
- If confidence < 0.6, asks "Which project is this about?"

---

## Onboarding flow (the first 90 seconds)

1. User signs up → auto-created "Personal" project, default selected
2. Welcome screen: "Connect your first tool to unlock Axis"
3. Click "Connect Slack" → Axis's default OAuth consent screen → redirected back → green check
4. Welcome screen: "Connect one more to activate cross-tool intelligence"
5. Click "Connect Notion" → same flow
6. Now unlocked: the chat input is enabled with a starter prompt ("Summarize what's in my workspace")
7. User can rename "Personal" or create a new project from the sidebar any time

Total clicks: 5. Total time: ~60 seconds. This is the bar.

## Settings that matter

- **Active project** (sidebar dropdown — persistent)
- **Default landing view** (feed / chat / history)
- **Notification cap** (max proactive per day — default 5)
- **Trust level** (low / medium / high — affects write confirmation gates)
- **BYO OAuth apps** (Settings → Credentials, per tool)
- **Export my data** (per project, as JSON) — GDPR requirement, spec §10
- **Delete my data** (cascades to vector store + memory graph within 24h per spec §10)

## Anti-use-cases (things Axis will NOT do)

- Be an employee monitoring tool (spec §4 — no surveillance use)
- Auto-reply to email without confirmation (even if trust=high, sends are always gated)
- Aggregate sensitive data across users (per-user isolation is an invariant)
- Host arbitrary code execution ("do whatever the agent wants on my laptop")
- Make decisions for the user — it surfaces, drafts, proposes; humans confirm

## Metrics we care about (from spec §14)

- **WAAU** — weekly active agent actions per user. Target: 5+/week in P1, 12+/week in P3
- **Connectors per active user** — target 3+ in P1
- **Proactive accept rate** — target 25%+ in P2, 40%+ in P3
- **Correction rate** — target under 20% in P1

Every use case above contributes to at least one of these.

## See also

- `projects-model.md`
- `byo-credentials.md`
- `project-router.md`
- `prompt-flow.md`
- `agentic-architecture.md`
- `permissions-model.md`
- `activity-feed.md`
- `streaming-real-time.md`
- `axis_full_spec.docx` §6 (feature specs) — ground truth

---

## Appendix A — User-level scope queries (Phase 2)

The user-level scope answers questions that span the entire workspace, across all projects, over a time window. Powered by the `activity_events` firehose.

### Time-window queries
- **"What happened in the last hour?"** → query `activity_events WHERE occurred_at >= NOW() - INTERVAL '1 hour'`, summarise
- **"What happened today?"** → same with `INTERVAL '1 day'`
- **"What happened this week?"** → same with `INTERVAL '7 days'`
- **"What did I miss overnight?"** → activity since `last_login_at`
- **"What did I do yesterday?"** → activity where `actor_id = <user_provider_id>` between yesterday and today

### Cross-source digests
- **"Give me the morning brief"** → agent runs a canned plan: top Slack threads + top emails + overdue Linear + upcoming Calendar, merges into a narrative
- **"Show me everything Aditi touched this week"** → activity filtered by actor name across every source
- **"Summarize all activity in the Acme engagement project today"** → `activity_events WHERE project_id = X`
- **"What decisions were made this week?"** → search activity + agent_actions for decision-language; classifier surfaces candidates

### Activity-backed proactive surfaces
- **"You have 3 Slack DMs from yesterday you haven't replied to"** ← events where `source='slack' AND event_type='mention'` AND no reply event from `actor_id=user`
- **"The roadmap doc got 4 comments but you haven't looked"** ← gdrive event stream
- **"3 PRs are waiting on your review"** ← github event stream
- **"Tomorrow's meeting with Acme has no prep doc"** ← gcal event + absent notion/gdrive link

## Appendix B — Task-level real-time flows (Phase 2)

For any non-trivial task, the user sees live progress via streaming events.

### Live task tree
Every task has a tree of steps. Each step emits:
- `step.started` — with agent role + capability
- `step.token_delta` — token-by-token LLM output
- `step.tool_call_started` — "calling git.clone..."
- `step.tool_call_result` — "cloned 243 files"
- `step.completed` — done + elapsed + tokens

The web UI (`apps/web/components/task-tree.tsx`) renders this as a collapsible tree that updates in place. User can click any step to see its full input/output.

### Interactive permissions
When a step wants to call a gated capability:
1. Task pauses with `permission.request`
2. Modal pops in the UI: *"Axis wants to read from Gmail — search for 'vendor renewal' (max 20 results). [Allow once | Allow for this task | Allow always | Deny]"*
3. User picks; grant persists (if applicable)
4. Task resumes with `permission.resolved`

For destructive writes, the modal is different — a DiffViewer preview + "Review and edit" button, no auto-remember.

### Cancellation + budget
User can cancel a running task at any time. When tasks approach their token budget the supervisor pauses with a `budget_exceeded` event so the user can say "keep going" or "stop".

## Appendix C — Multi-agent tasks (Phase 2)

### Deep research
- **"Research our top 3 competitors"** → supervisor plans: `web.search` → `web.fetch × N` → summarise per-competitor → merge into comparison table → optional: draft slack post

### Code-aware tasks
- **"Find every place we mention 'stripe' in our codebase and list the files"** → `git.clone` on the configured repo, `git.grep`, format
- **"Review this PR"** → `connector.github.read` PR + diff, `code.run` linter in sandbox, summarise issues, optionally `connector.github.comment`
- **"Update our README to reflect the new pricing"** → read Notion pricing → read github README → draft diff → `DiffViewer` preview → confirm → `connector.github.commit`

### Data-aware tasks
- **"What's our MRR trend from last quarter?"** → `connector.posthog.query` → `math.solve` for trend stats → summarise

### Cross-tool execution chains
- **"When a Linear ticket is closed, post in #product and archive the Slack thread"** → Phase 3 automation rules built on top of the agentic pipeline

## Appendix D — Configurable agents per task (Phase 2)

The frontend can send `config` on `/agent/run` to pin capabilities, roles, or budget:

```json
{
  "prompt": "Clone the acme/public repo and find every mention of 'pricing'",
  "config": {
    "capabilities": ["git.clone", "git.grep", "summarise"],
    "roles": ["code"],
    "max_steps": 5,
    "max_cost_usd": 0.10
  }
}
```

This UI is surfaced in chat as a "power mode" toggle — advanced users can override defaults per run. Projects have their own defaults so config is rarely needed day-to-day.

## Appendix E — The user-onboarding checklist (revised Phase 2)

The ideal first 5 minutes:

1. Sign up → auto-project "Personal" created, default active
2. Welcome: "Connect your first tool"
3. Click "Connect Notion" → OAuth → green check
4. **NEW:** "Want to use your own OAuth app? [Advanced]" — opens credentials page
5. **NEW:** Auto-grant prompt: "Axis can read from your connected tools to answer questions. [Allow for session / project / forever]"
6. Click "Connect Slack" → same flow
7. Chat unlocked. Starter prompts:
   - "Summarize everything that happened in my workspace today"
   - "Find the last thing Aditi said about pricing"
   - "What do I owe anyone?"
8. User types, sees the task tree live, gets the answer with sources

Target: 90 seconds. 5 clicks. Zero friction.

## Appendix F — Anti-use-cases (expanded)

In addition to the P1 list:

- **No autonomous multi-task chains.** Each task is user-initiated. "Run this task every hour" is a future feature, not default.
- **No exfiltration.** Capabilities that could send data outside the user's own tools (`web.post`, external webhooks) are `always-gate` forever.
- **No cross-user memory.** Activity events and memory are per-user, full stop.
- **No surveillance of teammates.** If a user connects a shared Slack workspace, we only read their own mentions and channels they're in — not everyone else's DMs.
- **No execution without confirmation for anything irreversible.** The trust floor is non-negotiable.
- **No job titles in the product.** Roles are permission tiers (owner/admin/manager/member/viewer), never labels like "President" or "VP." See `org-and-rbac.md`.

---

## Appendix G — Team scenarios (ADR 010)

### Onboarding a new teammate

> Priya just joined the company. An admin opens Members, clicks Invite, pastes `priya@company.com`, picks role `member`, scopes to the "Alpha Client" project, and hits Send. Because notification-service isn't live yet in Phase 1, the modal shows a copyable invite link instead of emailing — the admin pastes it to Priya in Slack.
>
> Priya clicks the link, hits a signup page pre-scoped to the invite, creates her password, and lands directly in the Alpha Client project. Her first view is the activity feed for that project only. She can run reads immediately, propose writes that land in an approval queue for a manager+, and cannot see Internal Ops or any other project.
>
> Total time from invite to first prompt: under 2 minutes.

### Delegating scoped access down the chain

> A team lead is managing three client projects and doesn't have bandwidth to run every agent action personally. They flip each client project to "Internal Ops"-style org-default, promote two managers under them, and hand each manager one client. The managers now invite their own members into their client project — the monotonic invite rule means they can only grant roles at-or-below their own, so nothing escalates.
>
> The top-of-graph admin still sees every grant in the audit log. If someone on a client project does something unusual, the trail from root to leaf is one click on the Members graph.

### Revoking access cleanly

> A contractor finishes their engagement. An admin opens the Members graph, right-clicks their node, picks "Remove from org." Backend:
>  - Deletes every `project_members` row for that user
>  - Marks their `organization_members` row as removed (soft delete for audit)
>  - Marks any personal tokens they installed as revoked (best-effort call to the provider to revoke)
>  - Marks their pending proposed writes as `abandoned`
>  - Their past `agent_actions` become read-only for everyone except admins+
>
> A notification hits their activity feed: "Your access to Acme Team was revoked."

### Morning brief scoped to what a person actually owns

> A team lead sets up a daily brief at 8 AM. The brief runs **as them** against the projects they have access to, using the activity feed model from ADR 007. Output lands in their own Axis feed and optionally pings a Slack DM.
>
> Content: top unanswered threads across their projects, overdue Linear tickets, emails flagged as high-priority, any contradictions detected between two current docs.
>
> A different team lead gets a completely different brief, generated from *their* project scope. Neither sees the other's data.

### "Find that thing" across team projects

> A member runs *"Find every mention of the refund policy across everything I have access to."* The project router sees the user has membership in 3 projects; in `all` mode it fans out and merges. Projects the user does *not* belong to are invisible — not "empty," not in the result set at all.

### Sensitive-writes approval flow

> A member drafts an email reply in Gmail via Axis. Their role can propose writes but not execute them. The draft lands in a manager's approval queue (visible as a `permission.request` event in the manager's feed). The manager sees the diff, edits a line if they want, and approves. Only then does the send happen.
>
> This is the same UX pattern Claude Code uses for permission gates — but tied to role, not to a per-capability rule.

---

## Appendix H — Delegation, rendered as a graph

The Members page renders the relationships as a graph, never as a table. Each node is a member with their role badge. Each edge is the invite that brought them in. Clicking a node opens a side panel with that member's audit log; clicking an edge shows the invite record.

```
               ┌──────────────────┐
               │  Organization    │
               │  (your team)     │
               └────────┬─────────┘
                        │
            ┌───────────┴───────────┐
            ▼                       ▼
        [owner A]              [owner B]
            │
       ┌────┴────┬───────────┐
       ▼         ▼           ▼
   [admin C]  [admin D]  [manager E]
       │         │           │
       │         │       ┌───┴────┐
       │         │       ▼        ▼
       │         │  [member F] [viewer G]
       │         │
       └────┬────┘
            ▼
        [manager H]
            │
            ▼
        [member I]
```

Properties of the render:

- **Flat by default** — nothing in the visual suggests fake hierarchy for small orgs
- **Depth appears only when delegation actually happens** — a 3-person org looks like 3 nodes, not a pyramid
- **No job titles anywhere** — the only text on a node is the member's display name plus their role badge
- **Click-to-inspect** — every node opens a side panel with that member's audit log
- **Drag to re-parent (admins)** — re-assignments are audited

---

## Appendix I — Connector onboarding patterns

### The default path (10 seconds)

1. User is at the Connections page, sees the tool grid
2. Clicks a tool's tile → OAuth consent screen opens in a new tab
3. Approves → redirected back → token encrypted and stored
4. `connectors` row gets `status=connected`, `health=green`

### The BYO path (for users who won't trust a vendor's OAuth app)

1. User goes to the user menu → Credentials
2. For each tool, pastes a `client_id` / `client_secret` / redirect URI from their own provider dev console
3. Secret is encrypted at rest with AES-256-GCM
4. Next "Connect Slack" click uses *their* OAuth client — the provider's audit log shows their internal integration, not Axis

### The shared-connector path (team-installed)

1. An admin connects a Slack workspace via the usual OAuth flow
2. At the end of the callback, the admin is prompted: *"This connector belongs to:"* with `[Me — personal]` or `[The org — shared]`
3. Picking "shared" sets `connectors.token_owner_user_id = NULL`
4. Every org member with `member+` role can now read via the shared connector; writes respect the role matrix from ADR 010
5. If the admin leaves the org, the token stays — it's not theirs, it's the org's

### The revoke path

1. User clicks Disconnect on any connector
2. Backend deletes the row, fires a best-effort provider-side revoke
3. All in-flight `write_actions` from that connector are marked `cancelled`
4. Activity-stream cursor is advanced to now (we stop polling a dead connector)
