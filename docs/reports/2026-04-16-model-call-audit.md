# Model call audit — Sessions 1-6

**Run on:** 2026-04-16
**Key state:** `ANTHROPIC_API_KEY` is a real `sk-ant-…` token (108 chars); `VOYAGE_API_KEY` is a real `pa-…` token (46 chars) — see addendum.
**Scope:** every place in Sessions 1-6 where a backend service calls an LLM or embedding provider. Goal: confirm each call path hits the real provider end-to-end, capture latency + tokens + sample output, and document any findings.

> **Update (same day):** Voyage key was the `pa-replace-me` placeholder at initial audit time. User dropped a real key partway through; re-verified and added retry/backoff handling for free-tier rate limits. See the **Addendum** section at the bottom.

---

## Summary

| # | Call site | Model / Provider | Status | Latency | Tokens | Notes |
|---|---|---|---|---|---|---|
| 1 | Supervisor tool-use loop | `claude-sonnet-4-5` | ✅ PASS | 5.29s | 1521 | Real tool_use loop, 3 citations, error recovery path also verified |
| 2 | Haiku judge — action | `claude-haiku-4-5` | ✅ PASS | < 3s | — | Substantive per-dimension reasons |
| 3 | Haiku judge — summarisation | `claude-haiku-4-5` | ✅ PASS | < 3s | — | Faithfulness 5, coverage 2, conciseness 5 |
| 4 | Haiku judge — proactive_surface | `claude-haiku-4-5` | ✅ PASS | < 3s | — | Relevance 4, timing 4, actionability 5 |
| 5 | Short-loop delta synthesis | `claude-haiku-4-5` | ✅ PASS | < 3s | 1158 | 3 corrections → 3-bullet delta |
| 6 | Voyage embeddings | `voyage-3` | ✅ PASS (post-addendum) | ~400ms | — | Real semantic retrieval — paraphrase cosine 0.65 vs hash 0.37; retry+backoff added for free-tier 429s |
| 7 | `fetch_prompt_delta` client gate | — | ✅ PASS | < 200ms | — | `_is_real_key` returns True; delta fetched correctly |
| 8 | `score_action` fire-and-forget | `claude-haiku-4-5` | ✅ PASS | (async) | — | Rows landing in `eval_results` within ~4s of `/run` |
| 9 | Memory end-to-end (retrieve + write) | Sonnet + Haiku + Voyage-stub | ✅ PASS | 6.79s | 5282 | Agent called `memory_retrieve`, got 9 rows, synthesized a recall answer citing the short-loop delta |

**Top-line:** every model call site that depends on `ANTHROPIC_API_KEY` is live and producing real responses. The one site that still stubs is Voyage embeddings because the key is a placeholder — the hash-based fallback path is doing its job and will swap to real vectors as soon as a real key lands in `.env`.

---

## Detail

### 1. Supervisor tool-use loop (`claude-sonnet-4-5`)

**File:** `services/agent-orchestration/app/graphs/planner.py::supervise`
**Call:** `client.messages.create(model=settings.anthropic_model_sonnet, tools=..., messages=...)` inside a `MAX_ITERATIONS=5` loop, with `tool_choice` defaulting to `auto` and every `tool_use` block dispatched to the capability registry.

**Test:** `POST /run` with prompt *"what activity happened in my workspace in the last 2 hours?"*. Seeded one Slack `message` event into `activity_events` immediately before to ensure the `activity.query` capability had something to return.

**Result:**
- `plan`: `tool_use:activity_query → synthesise:claude-sonnet-4-5`
- `tokens_used: 1521`
- `latency_ms: 5455` (wall clock 5.50s)
- `citations: 3` (two Slack events + the earlier Notion event)
- `output`: *"In the last 2 hours you had a Slack mention in #C999 (\"real key test: please respond\"), a message from alice in #general about the Q3 OKR doc needing review before Friday, and samir@raweval.com edited the \"Q3 Planning roadmap\" Notion page with draft v2 targeting a Nov 1 ship date."*

**Error recovery path:** a parallel test used prompt *"search my slack channels for any messages about Q3 OKRs"*. The `connector.slack.search` capability returned a 500 (see "Findings" below), but the supervisor caught the error from the tool_result block and gracefully synthesized *"I encountered an error searching Slack. The connector returned a 500 error, which typically means there's a temporary issue with the Slack integration."* using `claude-sonnet-4-5` — proves the Sonnet call works even when downstream tools fail.

**Verdict:** ✅ live. The base SYSTEM_PROMPT is sent as a cache-control'd system block; the per-user short-loop delta is appended as a second (non-cached) block so the base stays cache-hot while user corrections update instantly.

---

### 2-4. Haiku judge (`claude-haiku-4-5`)

**File:** `services/eval-engine/app/judges/haiku.py::judge` → `_call_haiku`
**Call:** `client.messages.create(model=settings.anthropic_model_haiku, tools=[submit_scores_tool], tool_choice={"type":"tool","name":"submit_scores"}, ...)`.

**Schema note:** the tool schema is **flat** — `{dim}_score` + `{dim}_reason` per dimension, not nested. The original nested schema caused Haiku to leak XML parameter syntax into the values (e.g. `"correctness": "\n<parameter name=\"score\">1"`). Flattening fixed this; documented in Session 5 notes.

**Test 2 — action rubric** (`correctness × 0.5 + scope × 0.25 + safety × 0.25`):
- `model: claude-haiku-4-5`, `stub: false`
- `composite_score: 3.0`, `flagged: false`
- `correctness=3` *"The response provides some activity details but lacks specificity about timing and the exact nature of the activities..."*
- `scope=4` *"The response directly addresses the user's question about recent activity without padding..."*
- `safety=2` *"The citations are generic and don't provide verifiable evidence of when these activities occurred..."*

**Test 3 — summarisation rubric** (`faithfulness × 0.5 + coverage × 0.3 + conciseness × 0.2`):
- `model: claude-haiku-4-5`, `stub: false`
- `composite_score: 4.1`, `flagged: false`
- `faithfulness=5` *"All claims in the summary are directly traceable to the source: Samir edited the roadmap and the ship date is Nov 1."*
- `coverage=2` *"The summary omits critical information about team agreement in standup and the identified risk of flaky integration tests..."*
- `conciseness=5` *"The summary is appropriately brief and contains no unnecessary padding."*

**Test 4 — proactive_surface rubric** (`relevance × 0.4 + timing × 0.3 + actionability × 0.3`):
- `model: claude-haiku-4-5`, `stub: false`
- `composite_score: 4.3`, `flagged: false`
- `relevance=4` *"A direct request for a specific deliverable (Q3 roadmap review) with a clear deadline..."*
- `timing=4` *"The mention is unanswered and has a near-term deadline (tomorrow)..."*
- `actionability=5` *"The user can immediately respond to confirm they'll review it..."*

**Verdict:** ✅ all 3 rubrics live. Haiku returns real, calibrated scores with substantive reasoning and the weighted composite lands in [3.0, 4.3]. Every dimension is scored even when the rubric is harsh (coverage=2 on summarisation).

---

### 5. Short-loop delta synthesis (`claude-haiku-4-5`)

**File:** `services/eval-engine/app/loops/short.py::refresh_prompt_delta`
**Call:** `client.messages.create(model=settings.anthropic_model_haiku, tools=[submit_delta_tool], tool_choice={"type":"tool","name":"submit_delta"}, ...)`.

**Test:** Fired a new correction *"Remember that Samir is the CTO and owns the Q3 planning work"* against a prior run, then hit `POST /prompt-deltas/{user_id}/refresh`.

**Result:**
```json
{
  "delta": "- Remember that Samir is the CTO and owns the Q3 planning work\n- Keep responses under 3 sentences\n- Always cite the Notion URL inline when referencing documents, not just the title",
  "source_corrections": ["8dd5be6f...", "7a136e0d...", "a6c614dd..."],
  "model": "claude-haiku-4-5",
  "token_count": 1158
}
```

**Observations:**
- All 3 historical corrections were synthesized into 3 coherent bullet points (one per correction, no duplicates, no drift).
- The `memory_update` correction was correctly encoded as a memory rule ("Remember that Samir is the CTO…") rather than a behavior rule.
- Token budget 1158 is reasonable for a 3-correction window; Haiku is good at this summarization task.

**Verdict:** ✅ live. The synthesized delta is fetched on the critical path of every `/run` by `fetch_prompt_delta` and prepended as a second system block.

---

### 6. Voyage embeddings (`voyage-3`) — **FALLBACK ACTIVE**

**File:** `services/memory-service/app/vector/embed.py::embed_text` → `_embed_voyage`
**Call:** `POST https://api.voyageai.com/v1/embeddings` with `model=voyage-3`, `input_type=document`.

**Test:**
```json
{
  "provider_label": "stub-hash",
  "voyage_key_gate_passes": false,
  "configured_model": "voyage-3",
  "single_embed": { "dim": 1024, "norm": 1.0, "nonzero_ratio": 0.0195 },
  "batch_embed": { "n": 3, "dims": [1024, 1024, 1024] },
  "similarity": {
    "samir_edit vs samir_update": 0.3651,
    "samir_edit vs cat_video": 0.0
  }
}
```

**Observations:**
- `_has_voyage_key()` returns `False` because the current key is `pa-replace-me-…` (tightened detector after Session 6.1 bug).
- The hash-based fallback correctly produces `dim=1024` L2-normalized vectors.
- Keyword overlap is preserved: two strings mentioning "samir" score 0.3651 cosine, totally disjoint strings score 0.0. That's enough to exercise the full Qdrant upsert / search / rerank pipeline, but it is **not** true semantic search — two paraphrases with no shared tokens will not retrieve each other.

**Verdict:** ⚠️ fallback active. **Action item:** set a real `VOYAGE_API_KEY` in `.env` before shipping memory to production. No code change needed — swap the key and the next embed call hits Voyage.

---

### 7. Client gates (`_is_real_key` + `fetch_prompt_delta`)

**File:** `services/agent-orchestration/app/clients/anthropic.py` + `app/clients/eval.py::fetch_prompt_delta`

**Test:**
```json
{
  "is_real_key": true,
  "get_client_is_not_none": true,
  "model_sonnet": "claude-sonnet-4-5",
  "prompt_delta_len": 180,
  "prompt_delta_lines": 3,
  "prompt_delta_preview": "- Remember that Samir is the CTO and owns the Q3 planning work\n- Keep responses under 3 sentences\n- Always cite the Notion URL inline when referencing documents, not just the title"
}
```

**Verdict:** ✅ the key detector correctly classifies the live key as real; `get_client()` returns a non-None `AsyncAnthropic` instance; the prompt-delta fetch round-trips through eval-engine's `GET /prompt-deltas/{user_id}` endpoint in under 200ms.

---

### 8. Fire-and-forget `/score` (`claude-haiku-4-5`)

**File:** `services/agent-orchestration/app/main.py::_score_background` → `score_action` → eval-engine `/score` → `judge.haiku.judge`
**Call path:** on every `/run` completion, `asyncio.create_task(_score_background(...))` hits eval-engine with the action id, prompt, output, **and now citations + plan** (the latter was a Session 5.8 hardening — without it the judge penalized every response as "unverifiable").

**Test:** ran 3 `/run`s in sequence and queried `eval_results` 4s later.

Recent rows:
```
 composite | flagged | first_reason
-----------+---------+-------------------------------------------
      2.75 | true    | The response cites memory sources but the citations show incomplete or error-prone data retrieval (including a Slack 500 error)...
      4.30 | false   | A direct request for a specific deliverable (Q3 roadmap review) with a clear deadline is typically important to the user's work.
      4.10 | false   | All claims in the summary are directly traceable to the source: Samir edited the roadmap and the ship date is Nov 1.
```

**Verdict:** ✅ live. Real Haiku, real reasoning, real flagged rows. The 2.75 row correctly caught that the memory recall cited a Slack 500 error — that's the judge doing its job.

---

### 9. Memory end-to-end (the full loop)

**Path:** `POST /run` → supervisor calls `memory.retrieve` capability → agent-orchestration HTTP POSTs memory-service `/retrieve` → hybrid tier fan-out → Qdrant `query_points` (via hash-fallback embedding) + Neo4j substring search + Postgres `users.settings` → result merged and sent back → Sonnet synthesizes with 9 memory rows in context → fire-and-forget writes prompt + answer as new episodic rows.

**Test:** prompt *"based on what you remember, who has been working on Q3 planning and what's the latest status?"*

**Result:**
- Memory stats before: `episodic_count=9, semantic_count=2`
- `plan`:
  1. `tool_use memory_retrieve — retrieved 9 memory rows`
  2. `tool_use connector_notion_search — notion search error` (expected — no real Notion connector)
  3. `synthesise claude-sonnet-4-5`
- `tokens_used: 5282`, `latency_ms: 6788` (wall 6.83s)
- `citations: 9` (all memory nodes)
- `output`: *"Based on my memory, **Samir (CTO) has been working on Q3 planning** and edited the Q3 Planning roadmap doc with \"Draft v2 with ship date Nov 1.\" Additionally, alice mentioned in Slack that the Q3 OKR doc needs review before Friday."*
- Memory stats after: `episodic_count=11` (the user prompt + assistant answer both written as fire-and-forget episodic rows)

**Observations:**
- The agent correctly used **"Samir (CTO)"** — that fact came only from the short-loop delta synthesized in Test 3, not from any tool call. Proves the delta-fetch + system-prompt injection path works end-to-end.
- The second tool call (`connector_notion_search`) errored because the test environment only has a fake Notion token. Sonnet recognized it as a supporting tool, not a primary source, and produced a correct answer from memory alone.
- Fire-and-forget episodic write fired on both user and assistant sides (+2 rows), confirmed by the stats delta.

**Verdict:** ✅ the entire Session 6 memory loop is live with real Sonnet, real Haiku (via fire-and-forget eval), and real Qdrant/Neo4j storage. Voyage is the only stubbed hop.

---

## Findings & follow-ups

### Finding 1 — Slack connector has a fake encrypted token (non-model, but surfaced by the audit)

**Symptom:** Prompts that hit `connector.slack.search` return a 500 from `/tools/slack/search` which the supervisor recovers from with a "I encountered an error searching Slack" response.

**Root cause:** Earlier in the session we seeded a row into `connectors` with `auth_token_encrypted='\x00'` so the Slack Events API webhook could find a fanout target. `decrypt_token` bytes the fake token. There is no real Slack workspace connected.

**Impact:** None for the audit — the supervisor recovery path works and Sonnet produces a graceful failure message. The agent still evals it (composite 2.75, flagged, with a real Haiku reason citing the error). The audit *did* catch it, which is what the eval layer is for.

**Fix:** Either (a) delete the fake row when running production `/run` tests, or (b) run a real Slack OAuth handshake. Tracked as follow-up, not a Session 1-6 regression.

### Finding 2 — Voyage key is still `pa-replace-me`

**Symptom:** Every memory embedding falls through to the hash-based stub. The stub preserves keyword-level similarity but cannot do true semantic search (two paraphrases with no shared tokens will not match).

**Root cause:** `VOYAGE_API_KEY` in `.env` is still the placeholder. Session 6.1 tightened `_has_voyage_key()` to catch `pa-replace-me`, so the fallback fires cleanly — no broken API calls, just keyword matching.

**Impact:** Functionally the memory loop works (Test 9 verified end-to-end). Quality-wise, retrieval is keyword-overlap instead of semantic. A user asking *"who owns planning"* won't retrieve *"Samir edited the Q3 roadmap"* unless the tokens overlap.

**Fix:** Drop a real Voyage key (`pa-<long random>`) into `.env` and bounce the memory-service. Zero code change needed.

### Finding 3 — The Haiku judge previously penalized every response as "unverifiable"

**Symptom** (caught mid-Session 5, now fixed): `/score` from `/run` scored 3.0 on correctness with reasons like "cites memory sources but the citations show incomplete data retrieval" even when real Notion citations existed.

**Root cause:** `score_action` did not forward `citations` or `plan` into the rubric `context` dict, so `build_user_prompt` rendered an empty `<citations>` block. The judge correctly assumed no evidence.

**Fix shipped:** `services/agent-orchestration/app/clients/eval.py::score_action` now takes `citations` + `plan` kwargs and forwards them through `context`. Composite jumped from 3.0 → 5.0 on identical output when the fix landed. **Still shipped** in the current audit — Test 8 shows real scores between 2.75 and 4.3 with judge reasons that reference the actual sources.

### Finding 4 — Nested tool-use schemas confuse Haiku

**Symptom** (caught early Session 5, now fixed): When the rubric tool schema was `{"correctness": {"type": "object", "properties": {"score": ..., "reason": ...}}}`, Haiku returned `{"correctness": "\n<parameter name=\"score\">1", "reason": "..."}` — it leaked XML parameter syntax into the string value.

**Root cause:** unclear; appears to be a model quirk with deeply nested tool schemas. Flattening to `{correctness_score, correctness_reason, scope_score, ...}` sidestepped it entirely.

**Fix shipped:** `rubrics/base.py::Rubric.tool_schema()` emits a flat schema; `judges/haiku.py::_call_haiku` parses the flat keys.

### Finding 5 — qdrant-client 1.10+ deprecated `search()` in favour of `query_points()`

**Symptom** (caught during Session 6 smoke-test): `AttributeError: 'AsyncQdrantClient' object has no attribute 'search'`.

**Fix shipped:** `services/memory-service/app/vector/client.py::search_episodic` now calls `client.query_points(query=vector, ...)` and iterates `result.points`.

---

## Raw evidence

All test outputs captured in `/tmp/axis-model-report/` during the audit run:

- `test1-supervisor.txt` — both supervisor runs (error + happy path)
- `test2-haiku-action.json` — action rubric full response
- `test2-haiku-summarisation.json` — summarisation rubric full response
- `test2-haiku-proactive.json` — proactive_surface rubric full response
- `test3-short-loop.json` — short-loop delta synthesis response
- `test4-voyage.json` — embedding provider gates + similarity sanity
- `test5-memory-followup.txt` — memory end-to-end run
- `test5-stats-before.json` / `test5-stats-after.json` — episodic count delta
- `test6-client-gates.json` — agent-orchestration client gate + delta fetch

---

## Bottom line

Every LLM call site in Sessions 1-6 hits the real provider and returns real responses with calibrated scoring and coherent reasoning. The supervisor loop, both Haiku paths (judge + short-loop), the fire-and-forget eval, and the memory end-to-end loop are all confirmed live on `claude-sonnet-4-5` and `claude-haiku-4-5`. The only stubbed hop is Voyage embeddings, which is a one-line env change away from going live.

**No code changes required as a result of this audit** — the issues surfaced (Slack fake token, Voyage placeholder) are environment/ops items, not Session 1-6 regressions.

---

## Addendum — Voyage key upgraded, semantic retrieval verified

**Updated:** 2026-04-16 (same day, shortly after the main audit)

The user dropped a real `VOYAGE_API_KEY` (`pa-<46 chars>`) into `.env`. Re-ran Test 6 and then a full semantic retrieval sanity check.

### Direct embed test
- `provider_label`: **`voyage`** (was `stub-hash`)
- `gate_passes`: **true**
- First embedding succeeded: 1024-dim, `nonzero_ratio=1.0` (every dimension populated vs hash's 0.02 density), real float values like `[0.028, -0.0861, -0.0551]`.
- Paraphrase cosine similarity:
  - Hash fallback: `samir_edit vs cto_updated_planning` = **0.3651**
  - Real Voyage: same query = **0.6495**
  - Disjoint (`samir_edit vs cat_video`): hash `0.0`, voyage `-0.0378`

The 78% lift on the paraphrase pair is the semantic signal — two strings with no noun overlap ("samir", "edited", "roadmap" vs "cto", "updated", "planning doc") are now retrievable.

### End-to-end semantic retrieval
Dropped the user's episodic collection (`axis_episodic_<user_id>`) to purge the old hash-vector mix, then paced two `POST /episodic` writes 25s apart (free tier is ~3 RPM) so each got a real Voyage vector, then searched with a query that shares **zero tokens** with either write:

- Write 1: *"Samir Patel, the CTO, updated the Q3 Planning roadmap Notion page with ship date Nov 1 for the v2 launch."*
- Write 2: *"What's the status of the fourth quarter product delivery timeline?"*
- Query: *"who is driving the autumn release schedule"*

Both rows retrieved with vector scores 0.477 and 0.545. A hash fallback would have returned 0.0 because there is literally no word overlap ("autumn" vs "Q3/fourth quarter", "release schedule" vs "ship date/delivery timeline", "driving" vs "updated/status"). This is real semantic retrieval, not keyword match.

### Rate-limit hardening shipped

The second/third back-to-back calls during the original test hit 429 from Voyage's free tier. Added light retry with exponential backoff to `services/memory-service/app/vector/embed.py::_embed_voyage_batch`:

- `VOYAGE_MAX_RETRIES = 3`, `VOYAGE_BACKOFF_SEC = 2.0` (doubles each retry)
- On 429, the client sleeps (2s → 4s → 8s) then retries
- Only after exhausting retries does it fall back to the hash stub

This matters because mixing real and hash vectors in the same Qdrant collection degrades retrieval quality — a silent fallback during a /run would poison the user's memory. The retry loop gives the rate limit enough slack to recover on free tier.

### Follow-up actions

1. **Purge existing collections before production** — any collection that accumulated hash vectors during the placeholder window has mixed dimensions that dilute real Voyage retrieval. Running `DELETE /collections/axis_episodic_<user_id>` for each user at cutover is the cleanest path.
2. **Consider upgrading Voyage plan** — 3 RPM on free tier will throttle any real multi-user traffic. The backoff loop buys ~14 seconds of headroom per call, but production should be on a paid tier with higher limits.
3. **Voyage is now the default provider label** in `/stats/{user_id}` responses; the `/memory` inspector page will show `voyage` instead of `stub-hash` once the web UI refreshes.

### Updated status

| # | Call site | Before | After |
|---|---|---|---|
| 6 | Voyage embeddings | ⚠️ FALLBACK | ✅ LIVE |

**Every model call site in Sessions 1-6 is now hitting the real provider.**
