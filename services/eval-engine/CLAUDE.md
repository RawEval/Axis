# CLAUDE.md — services/eval-engine

**This is the moat.** LLM-as-judge scoring + correction loop processing. Spec §6.6. Read `services/CLAUDE.md` first.

## Responsibilities

- Score every agent action against a rubric using Haiku-as-judge
- Store composite scores in `eval_results` table
- Process user corrections and feed them into two loops:
  - **Short loop (hours):** correction → rubric update → system prompt mutation → next action uses new behavior
  - **Long loop (months):** aggregated corrections → fine-tuning dataset → periodic fine-tune of owned open-source model (Llama / Mistral)

## Rubrics

| Rubric type | Dimensions (each scored 1–5) |
|---|---|
| `summarisation` | faithfulness, coverage, conciseness |
| `action` | correctness, scope, safety |
| `proactive_surface` | relevance, timing, actionability |

Composite = weighted average (weights per rubric type in `app/rubrics/`).

## Layout

```
app/
├── main.py
├── config.py
├── db.py
├── rubrics/
│   ├── base.py            Rubric protocol
│   ├── summarisation.py   prompt template + weights
│   ├── action.py
│   └── proactive.py
├── judges/
│   └── haiku.py           Haiku-as-judge client
├── repositories/
│   └── eval_results.py
└── routes/
    ├── health.py
    ├── score.py           POST /score
    └── correct.py         POST /corrections
```

## Flow

```
agent-orchestration completes action
    → fire-and-forget POST /eval-engine/score
    → eval-engine builds rubric prompt
    → Haiku returns per-dimension scores + reasons
    → composite computed, row inserted into eval_results
    → if composite < 3 or dimension < 2, flagged=true (show in correction queue)
    → return scores to caller (or just 202 if fire-and-forget)

user submits correction
    → POST /corrections
    → row in correction_signals
    → short loop: derive system prompt delta, push to agent-orchestration's user config
    → long loop: append to `axis-corrections-<month>.jsonl` in R2 for fine-tuning
```

## Don't

- Don't use Sonnet for judging — too expensive. Haiku only.
- Don't skip the correction opt-out check. Enterprise plan includes opt-out from aggregate training data.
- Don't expose raw rubric prompts to the user — show a simple quality indicator (e.g., "high/medium/low confidence").
- Don't fine-tune in this service. Training jobs live elsewhere (Modal / Together / managed).
