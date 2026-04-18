-- Axis — Session 5: per-user system-prompt deltas (short-loop correction)
--
-- The short loop reads the last N correction_signals for a user, asks
-- Haiku for a one-paragraph behavior delta, and caches the result here
-- keyed by user_id. Agent-orchestration fetches this row before every
-- supervisor call and prepends the ``delta`` to its SYSTEM_PROMPT.
--
-- Also used for long-loop training data — the ``source_corrections``
-- array points back at the correction rows that produced this delta so
-- later fine-tune exports can include the training pairs.

CREATE TABLE IF NOT EXISTS user_prompt_deltas (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    delta TEXT NOT NULL DEFAULT '',
    source_corrections UUID[] NOT NULL DEFAULT '{}',
    model TEXT,
    token_count INT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompt_deltas_updated
    ON user_prompt_deltas (updated_at DESC);
