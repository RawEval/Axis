-- Plan 11: write_actions can now stage multiple target candidates and let
-- the user pick before the write executes. target_options carries the
-- list of {kind, id, label, sub_label, context} dicts; target_chosen is
-- the picked one. Both NULL = no disambiguation needed.

ALTER TABLE write_actions
    ADD COLUMN IF NOT EXISTS target_options JSONB,
    ADD COLUMN IF NOT EXISTS target_chosen JSONB;
