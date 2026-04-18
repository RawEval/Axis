# Axis Agent Workflow — Complete Architecture Diagram

**Updated:** 2026-04-18
**Scope:** Every operation from prompt input to final output, across all 5 connectors, 13 capabilities, and 8 services.

---

## 1. High-Level System Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER (Browser / Mobile)                       │
│                                                                         │
│   Prompt: "Summarize #product this week and find the Q3 roadmap doc"    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY (:8000)                              │
│                                                                         │
│  JWT verify → project scope resolve → rate limit → forward              │
│                    │                              │                      │
│              POST /agent/run              WS /ws (live events)           │
└────────────┬──────────────────────────────────┬─────────────────────────┘
             │                                  │
             ▼                                  │ Redis pub/sub subscribe
┌────────────────────────────────────┐          │ axis:events:{user_id}
│   AGENT ORCHESTRATION (:8001)      │          │
│                                    │──────────┘
│   LangGraph: route → supervise     │  publishes events ──►
│                                    │
│  ┌──────────────────────────────┐  │
│  │     SUPERVISOR LOOP          │  │
│  │     (max 5 iterations)       │  │
│  │                              │  │
│  │  1. Fetch prompt delta       │  │◄── eval-engine /prompt-deltas
│  │  2. Call Claude Sonnet 4.5   │  │
│  │  3. Parse tool_use blocks    │  │
│  │  4. Permission gate          │  │
│  │  5. Dispatch capabilities    │  │──► connector-manager /tools/*
│  │  6. Collect citations        │  │──► memory-service /retrieve
│  │  7. Loop or synthesize       │  │
│  └──────────────────────────────┘  │
│                                    │
│  POST-RUN (sequential):            │
│    ├─ agent_actions (1 row)        │
│    ├─ agent_tasks + steps          │
│    └─ agent_messages + citations   │
│                                    │
│  FIRE-AND-FORGET (background):     │
│    ├─ eval score ──────────────────┼──► eval-engine /score
│    └─ episodic memory write ───────┼──► memory-service /episodic
└────────────────────────────────────┘
```

---

## 2. Supervisor Loop — Detailed Decision Tree

```
                    ┌──────────────────┐
                    │   POST /run      │
                    │   {prompt, user, │
                    │    project_ids}  │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  route_project   │
                    │  pick first      │
                    │  project_id      │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
              ┌─────┤  ANTHROPIC KEY?  ├─────┐
              │     └──────────────────┘     │
            NO│                              │YES
              ▼                              ▼
     ┌────────────────┐          ┌───────────────────┐
     │ _stub_supervise│          │ fetch_prompt_delta │◄── eval-engine
     │ (deterministic │          │ (2s timeout)       │    GET /prompt-deltas/{uid}
     │  test path)    │          └─────────┬──────────┘
     └────────┬───────┘                    │
              │                  ┌─────────▼──────────┐
              │                  │ Build system prompt │
              │                  │                     │
              │                  │ Block 1: base       │ ◄── cached (ephemeral)
              │                  │ SYSTEM_PROMPT       │
              │                  │                     │
              │                  │ Block 2: user delta │ ◄── NOT cached
              │                  │ (from corrections)  │     (updates instantly)
              │                  └─────────┬──────────┘
              │                            │
              │                  ┌─────────▼──────────┐
              │                  │ ──► EVENT:          │
              │                  │ task.started        │
              │                  └─────────┬──────────┘
              │                            │
              │          ┌─────────────────▼──────────────────┐
              │          │         ITERATION LOOP              │
              │          │         (max 5 rounds)              │
              │          │                                     │
              │          │  ┌───────────────────────────────┐  │
              │          │  │  Claude Sonnet 4.5 API call   │  │
              │          │  │                               │  │
              │          │  │  system: [base + delta]       │  │
              │          │  │  tools:  [13 capabilities]    │  │
              │          │  │  messages: [history so far]   │  │
              │          │  └──────────────┬────────────────┘  │
              │          │                 │                    │
              │          │       ┌─────────▼─────────┐         │
              │          │       │   stop_reason?     │         │
              │          │       └─────────┬─────────┘         │
              │          │          ┌──────┴───────┐           │
              │          │          │              │            │
              │          │      end_turn      tool_use         │
              │          │          │              │            │
              │          │          ▼              ▼            │
              │          │  ┌──────────┐  ┌──────────────────┐ │
              │          │  │SYNTHESIZE│  │FOR EACH tool_use │ │
              │          │  │          │  │block:            │ │
              │          │  │Extract   │  │                  │ │
              │          │  │text →    │  │ ┌──────────────┐ │ │
              │          │  │output    │  │ │1. LOOKUP cap │ │ │
              │          │  │          │  │ │   in registry│ │ │
              │          │  │──► EVENT:│  │ │              │ │ │
              │          │  │task.     │  │ │Unknown? ─────┼─┼─┼──► error result
              │          │  │completed │  │ └──────┬───────┘ │ │
              │          │  │          │  │        │         │ │
              │          │  │RETURN    │  │ ┌──────▼───────┐ │ │
              │          │  └──────────┘  │ │2. PERMISSION │ │ │
              │          │                │ │   GATE       │ │ │
              │          │                │ │              │ │ │
              │          │                │ │ See §3 below │ │ │
              │          │                │ │              │ │ │
              │          │                │ │Denied? ──────┼─┼─┼──► error result
              │          │                │ └──────┬───────┘ │ │
              │          │                │        │granted  │ │
              │          │                │ ┌──────▼───────┐ │ │
              │          │                │ │──► EVENT:    │ │ │
              │          │                │ │step.started  │ │ │
              │          │                │ └──────┬───────┘ │ │
              │          │                │        │         │ │
              │          │                │ ┌──────▼───────┐ │ │
              │          │                │ │3. EXECUTE    │ │ │
              │          │                │ │   capability │ │ │
              │          │                │ │              │ │ │
              │          │                │ │ See §4 below │ │ │
              │          │                │ └──────┬───────┘ │ │
              │          │                │        │         │ │
              │          │                │ ┌──────▼───────┐ │ │
              │          │                │ │──► EVENT:    │ │ │
              │          │                │ │step.completed│ │ │
              │          │                │ │              │ │ │
              │          │                │ │Collect       │ │ │
              │          │                │ │citations     │ │ │
              │          │                │ └──────┬───────┘ │ │
              │          │                │        │         │ │
              │          │                │ NEXT tool_use    │ │
              │          │                │ block            │ │
              │          │                └────────┬─────────┘ │
              │          │                         │           │
              │          │              Append all tool_results│
              │          │              to message history     │
              │          │                         │           │
              │          │              NEXT ITERATION ────────┘
              │          │              (back to Claude call)
              │          └─────────────────────────────────────┘
              │
              ▼
       ┌──────────────────────────────────────────────┐
       │              RETURN TO /run                   │
       │                                               │
       │  {output, citations, plan, tokens_used, model}│
       └───────────────────────────────────────────────┘
```

---

## 3. Permission Gate — Decision Flow

```
                    ┌────────────────────┐
                    │ check_and_gate()   │
                    │                    │
                    │ capability.name    │
                    │ capability.scope   │
                    │ default_permission │
                    └────────┬───────────┘
                             │
                    ┌────────▼───────────┐
                    │ default_permission? │
                    └────────┬───────────┘
                     ┌───────┼────────┐
                     │       │        │
                   auto     ask   always_gate
                     │       │        │
                     ▼       ▼        │
              ┌──────────┐  ┌──────────────┐
              │GRANT     │  │CHECK DB for  │◄─── also for always_gate
              │immediately│  │prior grant   │     (but skips prior check)
              │           │  │              │
              │source:    │  │permission_   │
              │'auto'     │  │grants table  │
              └──────────┘  └──────┬───────┘
                                   │
                          ┌────────▼────────┐
                          │ Prior grant     │
                          │ found?          │
                          └────────┬────────┘
                           ┌───────┼────────┐
                           │       │        │
                          YES    NO/       always_gate
                        granted  expired    (skip)
                           │       │        │
                           ▼       ▼        ▼
                    ┌──────────┐  ┌──────────────────────┐
                    │GRANT     │  │ LIVE APPROVAL        │
                    │          │  │                      │
                    │source:   │  │ 1. Generate          │
                    │'prior_   │  │    pending_id        │
                    │ grant'   │  │                      │
                    └──────────┘  │ 2. asyncio.Event()   │
                                  │                      │
                                  │ 3. ──► EVENT:        │
                                  │    permission.request │─► Redis ─► WS ─► UI modal
                                  │                      │
                                  │ 4. AWAIT event       │
                                  │    (120s timeout)    │
                                  │                      │◄── POST /permissions/resolve
                                  └──────────┬───────────┘    {pending_id, granted,
                                             │                 lifetime}
                                    ┌────────▼────────┐
                                    │ Result?         │
                                    └────────┬────────┘
                                 ┌───────────┼───────────┐
                                 │           │           │
                              granted     denied      timeout
                                 │           │           │
                                 ▼           ▼           ▼
                          ┌──────────┐ ┌──────────┐ ┌──────────┐
                          │GRANT     │ │DENY      │ │DENY      │
                          │          │ │          │ │          │
                          │If durable│ │source:   │ │source:   │
                          │lifetime: │ │'denied'  │ │'timeout' │
                          │persist   │ └──────────┘ └──────────┘
                          │to DB     │
                          └──────────┘

    LIFETIME OPTIONS:
    ┌─────────────┬──────────────┬──────────────┐
    │ session     │ Not persisted│ This call    │
    │ 24h         │ Persisted    │ expires_at   │
    │ project     │ Persisted    │ project_id   │
    │ forever     │ Persisted    │ no expiry    │
    └─────────────┴──────────────┴──────────────┘
```

---

## 4. Connector Dispatch — All 5 Connectors

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      AGENT ORCHESTRATION (:8001)                                │
│                                                                                 │
│   13 Capabilities auto-discovered from app/capabilities/*.py                    │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐    │
│   │                     CAPABILITY REGISTRY                                │    │
│   │                                                                        │    │
│   │  INTERNAL (no connector-manager call):                                 │    │
│   │  ┌──────────────────┐  ┌──────────────────┐                           │    │
│   │  │ activity.query   │  │ memory.retrieve  │                           │    │
│   │  │ scope: read      │  │ scope: read      │                           │    │
│   │  │ perm: auto       │  │ perm: auto       │                           │    │
│   │  │ source: Postgres │  │ source: memory-  │                           │    │
│   │  │ (activity_events)│  │ service (:8004)  │                           │    │
│   │  └──────────────────┘  └──────────────────┘                           │    │
│   │                                                                        │    │
│   │  CONNECTOR-BACKED (via connector-manager (:8002) HTTPS):               │    │
│   │                                                                        │    │
│   │  ┌─────────────────────────────────────────────────────────────────┐   │    │
│   │  │                         SLACK (6 caps)                          │   │    │
│   │  │                                                                 │   │    │
│   │  │  READ (auto):                    WRITE (ask → gate):            │   │    │
│   │  │  ┌────────────────────┐          ┌────────────────────┐        │   │    │
│   │  │  │ slack.search       │          │ slack.post         │        │   │    │
│   │  │  │ → /tools/slack/    │          │ → /tools/slack/    │        │   │    │
│   │  │  │   search           │          │   post             │        │   │    │
│   │  │  ├────────────────────┤          │ GATED: needs       │        │   │    │
│   │  │  │ slack.channel_     │          │ user confirmation  │        │   │    │
│   │  │  │ summary            │          └────────────────────┘        │   │    │
│   │  │  │ → /tools/slack/    │          ┌────────────────────┐        │   │    │
│   │  │  │   history          │          │ slack.react        │        │   │    │
│   │  │  ├────────────────────┤          │ → /tools/slack/    │        │   │    │
│   │  │  │ slack.thread_      │          │   react            │        │   │    │
│   │  │  │ context            │          │ GATED              │        │   │    │
│   │  │  │ → /tools/slack/    │          └────────────────────┘        │   │    │
│   │  │  │   thread           │                                        │   │    │
│   │  │  ├────────────────────┤                                        │   │    │
│   │  │  │ slack.user_profile │                                        │   │    │
│   │  │  │ → /tools/slack/    │                                        │   │    │
│   │  │  │   user             │                                        │   │    │
│   │  │  └────────────────────┘                                        │   │    │
│   │  └─────────────────────────────────────────────────────────────────┘   │    │
│   │                                                                        │    │
│   │  ┌─────────────────────────────────────────────────────────────────┐   │    │
│   │  │                        NOTION (2 caps)                          │   │    │
│   │  │                                                                 │   │    │
│   │  │  READ (auto):                    WRITE (ask → gate):            │   │    │
│   │  │  ┌────────────────────┐          ┌────────────────────┐        │   │    │
│   │  │  │ notion.search      │          │ notion.append      │        │   │    │
│   │  │  │ → /tools/notion/   │          │ → snapshot +       │        │   │    │
│   │  │  │   search           │          │   diff preview +   │        │   │    │
│   │  │  └────────────────────┘          │   write.preview    │        │   │    │
│   │  │                                  │   event → confirm  │        │   │    │
│   │  │                                  │   → /tools/notion/ │        │   │    │
│   │  │                                  │   append           │        │   │    │
│   │  │                                  │ GATED + DIFF +     │        │   │    │
│   │  │                                  │ ROLLBACK           │        │   │    │
│   │  │                                  └────────────────────┘        │   │    │
│   │  └─────────────────────────────────────────────────────────────────┘   │    │
│   │                                                                        │    │
│   │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐             │    │
│   │  │ GMAIL (1 cap)  │ │ GDRIVE (1 cap) │ │ GITHUB (1 cap) │             │    │
│   │  │                │ │                │ │                │             │    │
│   │  │ gmail.search   │ │ gdrive.search  │ │ github.search  │             │    │
│   │  │ → /tools/gmail/│ │ → /tools/      │ │ → /tools/      │             │    │
│   │  │   search       │ │   gdrive/search│ │   github/search│             │    │
│   │  │ perm: auto     │ │ perm: auto     │ │ perm: auto     │             │    │
│   │  └────────────────┘ └────────────────┘ └────────────────┘             │    │
│   └────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                        ALL connector calls go through:
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     CONNECTOR MANAGER (:8002, HTTPS)                            │
│                                                                                 │
│  Owns: encrypted OAuth tokens, token decryption, provider API calls             │
│  Agent orchestration NEVER sees plaintext tokens                                │
│                                                                                 │
│  For each /tools/* call:                                                        │
│    1. Lookup connector row by (user_id, project_id, tool_name)                  │
│    2. Decrypt auth_token_encrypted (AES-256-GCM)                                │
│    3. Call provider API with decrypted token                                    │
│    4. Normalize response → return to caller                                     │
│                                                                                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │   SLACK   │  │  NOTION   │  │   GMAIL   │  │  GDRIVE   │  │  GITHUB   │    │
│  │           │  │           │  │           │  │           │  │           │    │
│  │ xoxb bot  │  │ workspace │  │ Google    │  │ Google    │  │ OAuth     │    │
│  │ token     │  │ token     │  │ OAuth     │  │ OAuth     │  │ token     │    │
│  │           │  │           │  │ token     │  │ token     │  │           │    │
│  │ Endpoints:│  │ Endpoints:│  │           │  │           │  │ Endpoints:│    │
│  │ /search   │  │ /search   │  │ Endpoint: │  │ Endpoint: │  │ /search   │    │
│  │ /channels │  │ /blocks   │  │ /search   │  │ /search   │  │           │    │
│  │ /history  │  │ /append   │  │           │  │           │  │           │    │
│  │ /thread   │  │           │  │           │  │           │  │           │    │
│  │ /user     │  │           │  │           │  │           │  │           │    │
│  │ /post     │  │           │  │           │  │           │  │           │    │
│  │ /react    │  │           │  │           │  │           │  │           │    │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘    │
│        │              │              │              │              │            │
│        ▼              ▼              ▼              ▼              ▼            │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                       PROVIDER APIs (internet)                           │   │
│  │                                                                          │   │
│  │  slack.com/api/*   api.notion.com/v1/*   gmail.googleapis.com/*          │   │
│  │  googleapis.com/drive/v3/*   api.github.com/*                            │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Post-Run Pipeline — Persist + Score + Remember

```
┌─────────────────────────────────────────────────────────────────┐
│                  AFTER supervise() RETURNS                       │
│                  (still on critical path)                        │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ SEQUENTIAL WRITES (3 repositories, ~50ms total)           │  │
│  │                                                           │  │
│  │  ┌─────────────────┐                                      │  │
│  │  │ 1. agent_actions│  1 row — backward compat aggregate   │  │
│  │  │    (actions.py) │  prompt, plan, result blob            │  │
│  │  └────────┬────────┘                                      │  │
│  │           │                                                │  │
│  │  ┌────────▼────────┐                                      │  │
│  │  │ 2. agent_tasks  │  1 task + N steps                    │  │
│  │  │    + steps      │  each tool_use = 1 step row          │  │
│  │  │    (tasks.py)   │  with role, capability, status       │  │
│  │  └────────┬────────┘                                      │  │
│  │           │                                                │  │
│  │  ┌────────▼────────┐                                      │  │
│  │  │ 3. messages +   │  2 messages (user + assistant)        │  │
│  │  │    citations +  │  N citations with source metadata     │  │
│  │  │    spans        │  M spans (text offset highlights)     │  │
│  │  │    (messages.py)│                                       │  │
│  │  └─────────────────┘                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ FIRE-AND-FORGET (asyncio.create_task, never blocks user)  │  │
│  │                                                           │  │
│  │  ┌─────────────────────────┐  ┌──────────────────────┐   │  │
│  │  │ _score_background()    │  │ _remember_turn()     │   │  │
│  │  │                         │  │                      │   │  │
│  │  │ POST eval-engine /score │  │ POST memory-service  │   │  │
│  │  │                         │  │ /episodic × 2        │   │  │
│  │  │ Sends:                  │  │                      │   │  │
│  │  │ • action_id             │  │ Sends:               │   │  │
│  │  │ • prompt + output       │  │ • user prompt        │   │  │
│  │  │ • citations + plan      │  │ • assistant output   │   │  │
│  │  │ • rubric_type='action'  │  │ • action_id          │   │  │
│  │  │                         │  │ • project_id         │   │  │
│  │  │ Eval-engine calls:      │  │                      │   │  │
│  │  │ Haiku-as-judge with     │  │ Memory-service:      │   │  │
│  │  │ submit_scores tool      │  │ Voyage embed →       │   │  │
│  │  │ → eval_results row      │  │ Qdrant upsert →     │   │  │
│  │  │                         │  │ episodic collection  │   │  │
│  │  │ If flagged:             │  │                      │   │  │
│  │  │ → refresh_prompt_delta  │  │                      │   │  │
│  │  │ → user_prompt_deltas    │  │                      │   │  │
│  │  └─────────────────────────┘  └──────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Write-Back Flow (Notion Append Example)

```
    Claude says: tool_use connector_notion_append {page_id, text}
                            │
                            ▼
              ┌──────────────────────────┐
              │ 1. SNAPSHOT              │
              │    GET /tools/notion/    │
              │    blocks               │──► connector-manager
              │    → before_state       │    → Notion API
              └────────────┬─────────────┘
                           │
              ┌────────────▼─────────────┐
              │ 2. DIFF                  │
              │    compute_diff(         │
              │      before_lines,       │
              │      after_lines)        │
              │    → [{type:add/del/eq,  │
              │        text:...}]        │
              └────────────┬─────────────┘
                           │
              ┌────────────▼─────────────┐
              │ 3. PERSIST PENDING       │
              │    write_actions row     │
              │    write_snapshots row   │
              │    (confirmed=false)     │
              └────────────┬─────────────┘
                           │
              ┌────────────▼─────────────┐
              │ 4. ──► EVENT:            │
              │    write.preview         │──► Redis ──► WS ──► UI DiffViewer
              │    {diff_lines, tool,    │
              │     write_action_id}     │
              └────────────┬─────────────┘
                           │
              ┌────────────▼─────────────┐
              │ 5. RETURN TO CLAUDE      │
              │    "pending user         │
              │     confirmation"        │
              │    Claude moves on       │
              └──────────────────────────┘

                    ... later ...

    User clicks CONFIRM in DiffViewer:
              ┌──────────────────────────┐
              │ POST /writes/{id}/       │
              │ confirm                  │
              │                          │
              │ 1. Set confirmed=true    │
              │ 2. POST /tools/notion/   │
              │    append → Notion API   │
              │ 3. Capture after_state   │
              └──────────────────────────┘

    User clicks ROLLBACK (within 30 days):
              ┌──────────────────────────┐
              │ POST /writes/{id}/       │
              │ rollback                 │
              │                          │
              │ 1. Set rolled_back=true  │
              │ 2. (Phase 2: delete      │
              │     appended blocks)     │
              └──────────────────────────┘
```

---

## 7. Eval + Correction Feedback Loop

```
    ┌──────────────────────────────────────────────────────────┐
    │                  THE MOAT LOOP                            │
    │                                                          │
    │  Every /run:                                             │
    │                                                          │
    │  ┌────────┐    ┌──────────────┐    ┌─────────────────┐  │
    │  │ /run   │───►│ eval-engine  │───►│ eval_results    │  │
    │  │ output │    │ /score       │    │ table           │  │
    │  │        │    │              │    │                 │  │
    │  │        │    │ Haiku judge  │    │ composite score │  │
    │  │        │    │ 3 dimensions │    │ per-dim reasons │  │
    │  └────────┘    └──────────────┘    └────────┬────────┘  │
    │                                             │           │
    │  User sees bad output:                      │ flagged?  │
    │                                             ▼           │
    │  ┌────────────────┐    ┌──────────────────────────────┐ │
    │  │ "Flag issue"   │───►│ correction_signals table     │ │
    │  │ button on chat │    │                              │ │
    │  │                │    │ type: wrong / rewrite /      │ │
    │  │ POST /eval/    │    │   memory_update / scope      │ │
    │  │ corrections    │    │ note: "always cite URLs"     │ │
    │  └────────────────┘    └──────────────┬───────────────┘ │
    │                                       │                 │
    │                               ┌───────▼───────┐        │
    │                               │ SHORT LOOP    │        │
    │                               │               │        │
    │                               │ Haiku reads   │        │
    │                               │ last 20       │        │
    │                               │ corrections   │        │
    │                               │ → synthesizes │        │
    │                               │ ≤6-bullet     │        │
    │                               │ behavior      │        │
    │                               │ delta         │        │
    │                               └───────┬───────┘        │
    │                                       │                 │
    │                               ┌───────▼───────┐        │
    │                               │ user_prompt_  │        │
    │                               │ deltas table  │        │
    │                               │               │        │
    │                               │ cached delta: │        │
    │                               │ "- Keep       │        │
    │                               │   responses   │        │
    │                               │   under 3     │        │
    │                               │   sentences"  │        │
    │                               └───────┬───────┘        │
    │                                       │                 │
    │  NEXT /run:                           │                 │
    │                                       ▼                 │
    │  ┌─────────────────────────────────────────────────┐   │
    │  │ fetch_prompt_delta(user_id) on critical path    │   │
    │  │ → prepend delta to system prompt                │   │
    │  │ → Claude's behavior changes on the next run     │   │
    │  └─────────────────────────────────────────────────┘   │
    │                                                          │
    │  LOOP CLOSED: correction → delta → behavior change       │
    └──────────────────────────────────────────────────────────┘
```

---

## 8. Memory System — Three-Tier Architecture

```
    ┌─────────────────────────────────────────────────────────────┐
    │                  MEMORY SERVICE (:8004)                      │
    │                                                             │
    │  POST /retrieve → fan out to all 3 tiers → merge + rerank  │
    │                                                             │
    │  ┌────────────────────────────────────────────────────────┐ │
    │  │ TIER 1: EPISODIC (Qdrant)                              │ │
    │  │                                                        │ │
    │  │  Per-user collection: axis_episodic_{user_id}          │ │
    │  │  Each point: {vector, user_id, project_id, role,       │ │
    │  │               content, action_id, occurred_at, tags}   │ │
    │  │                                                        │ │
    │  │  Score = 0.7 × vector_similarity + 0.3 × recency      │ │
    │  │  Recency: linear decay 1.0→0.0 over 90 days           │ │
    │  │                                                        │ │
    │  │  Vectors: Voyage-3 (1024-dim) or hash fallback         │ │
    │  │  Auto-populated: every /run writes 2 rows              │ │
    │  └────────────────────────────────────────────────────────┘ │
    │                                                             │
    │  ┌────────────────────────────────────────────────────────┐ │
    │  │ TIER 2: SEMANTIC (Neo4j)                               │ │
    │  │                                                        │ │
    │  │  Nodes: (:Entity {user_id, name, kind, attrs})         │ │
    │  │  Edges: -[:RELATES_TO {label, weight}]->               │ │
    │  │                                                        │ │
    │  │  Kinds: person | project | topic | doc | tool          │ │
    │  │  Search: substring match + 1-2 hop traversal           │ │
    │  │                                                        │ │
    │  │  Score = 1.0 - (index_position / limit)                │ │
    │  └────────────────────────────────────────────────────────┘ │
    │                                                             │
    │  ┌────────────────────────────────────────────────────────┐ │
    │  │ TIER 3: PROCEDURAL (Postgres)                          │ │
    │  │                                                        │ │
    │  │  Source: users.settings JSONB column                   │ │
    │  │  Keys: trust_level, output_format, brief_time, etc.    │ │
    │  │  Score = 1.0 (always relevant if key matches)          │ │
    │  └────────────────────────────────────────────────────────┘ │
    │                                                             │
    │  MERGE: global score-sort across all 3 tiers → top N       │
    └─────────────────────────────────────────────────────────────┘
```

---

## 9. Real-Time Events — Redis → WebSocket → UI

```
    AGENT ORCHESTRATION                REDIS               API GATEWAY        BROWSER
    (:8001)                            (:6379)              (:8000)

    publish("task.started") ──────► axis:events:{uid} ──► /ws subscriber ──► LiveTaskTree
                                                                              component
    publish("step.started") ──────► axis:events:{uid} ──► /ws subscriber ──► step card
                                                                              (running)

    publish("permission.    ──────► axis:events:{uid} ──► /ws subscriber ──► PermissionModal
     request")                                                                (4 buttons)

                                                          POST /permissions/ ◄── user clicks
                                                          resolve              "Allow for
                                                               │               project"
                                                               ▼
    resolve_pending() ◄────────────────────────────────── agent-orch
    asyncio.Event.set()                                   /permissions/resolve

    publish("step.completed") ────► axis:events:{uid} ──► /ws subscriber ──► step card
                                                                              (done ✓)

    publish("write.preview") ─────► axis:events:{uid} ──► /ws subscriber ──► DiffViewer
                                                                              + Confirm btn

    publish("task.completed") ────► axis:events:{uid} ──► /ws subscriber ──► LiveTaskTree
                                                                              cleared after
                                                                              1.5s
```

---

## 10. Resource Allocation Summary

| Resource | What | When Consumed | Budget |
|---|---|---|---|
| **Claude Sonnet 4.5** | Supervisor reasoning + tool selection | Every iteration of the loop (1-5 per /run) | ~500-2000 tokens/iteration |
| **Claude Haiku 4.5** | Eval scoring | Background, after every /run | ~200-500 tokens/score |
| **Claude Haiku 4.5** | Short-loop delta synthesis | Background, on correction or flagged run | ~800-1200 tokens/refresh |
| **Voyage-3** | Episodic memory embeddings | Background, 2 rows per /run | 2 API calls per /run |
| **Postgres** | All persistence | Critical path (3 repos) + background (eval, corrections) | ~5 queries per /run |
| **Redis** | Event pub/sub | Fire-and-forget per event (~5 per /run) | Negligible |
| **Qdrant** | Episodic vector store | Background write + on-demand search | 2 upserts + 0-1 search per /run |
| **Neo4j** | Semantic entity graph | On-demand search (when memory.retrieve fires) | 0-2 queries per /run |
| **Provider APIs** | Slack, Notion, Gmail, Drive, GitHub | On-demand per tool_use (1-3 per /run typical) | Rate-limited by provider |

---

## 11. Example Multi-Tool Run

**Prompt:** *"Summarize what happened in #product this week and check if there's a related Notion doc"*

```
Iteration 1:
  Claude → tool_use: connector_slack_channel_summary {channel_id: "C_PRODUCT", limit: 50}
           tool_use: connector_notion_search {query: "product updates this week"}

  Permission gate: both auto (read) → pass immediately

  Step 1: slack.channel_summary → connector-manager /tools/slack/history
           → Slack API conversations.history → 50 messages
           → CapabilityResult(summary="50 messages", citations=[1])

  Step 2: notion.search → connector-manager /tools/notion/search
           → Notion API /search → 3 pages
           → CapabilityResult(summary="3 pages", citations=[3])

  Both results appended to message history as tool_results

Iteration 2:
  Claude → end_turn (synthesize)
  Output: "This week in #product: Alice discussed pricing strategy (12 messages),
           Bob raised a deployment concern (thread, 8 replies)...
           Related Notion docs: 'Product Roadmap Q3', 'Pricing Strategy v2', 'Deploy Checklist'"

  4 citations total (1 channel + 3 pages)
  Tokens: ~1800
  Latency: ~6s

Post-run:
  → 1 agent_actions row
  → 1 agent_tasks + 2 agent_task_steps
  → 2 agent_messages + 4 agent_citations
  → eval score (Haiku, background) → composite 4.2
  → 2 episodic memory rows (Qdrant, background)
```
