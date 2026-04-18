# eval-engine

LLM-as-judge scoring. Every agent output is evaluated against a rubric relevant to
the action type (summarisation / action / proactive_surface). See spec §6.6.

**This is the moat.** Corrections accumulate into a fine-tuning dataset per customer.
