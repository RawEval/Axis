# Eval + Correction Loop

The moat (spec §6.6).

## Short loop — hours

```
user correction
    → rubric update
    → system prompt mutation for user
    → next identical action uses updated behavior
```

Target: change reflected within 1–6 hours.

## Long loop — months

```
correction signals (all users, opted-in)
    → aggregated by action type
    → filtered for quality / consistency
    → fine-tune dataset
    → periodic fine-tune of open-source base (Llama / Mistral)
    → proprietary model replaces Haiku for select tasks
```

## Rubrics

| Rubric | Dimensions |
|---|---|
| Summarisation | faithfulness, coverage, conciseness |
| Action | correctness, scope, safety |
| Proactive surface | relevance, timing, actionability |

All dimensions scored 1–5 by Haiku-as-judge. Composite surfaced to user as a
simple quality indicator (not the raw numbers).
