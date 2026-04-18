-- Axis — Session 8: write snapshots for rollback (spec §6.5)
--
-- Every write action that the agent executes captures the before-state
-- of the target resource so the user can one-click rollback within 30
-- days. The snapshot_id in write_actions points here.
--
-- Snapshots are provider-agnostic blobs — Notion blocks JSON, Gmail
-- draft body, Drive doc content. The agent never interprets the blob;
-- the connector module that produced it is the one that replays it on
-- rollback.

CREATE TABLE IF NOT EXISTS write_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    write_action_id UUID NOT NULL REFERENCES write_actions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    tool TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_type TEXT,          -- 'notion_page' | 'gmail_draft' | 'gdrive_doc' | 'github_file'
    before_state JSONB NOT NULL,
    after_state JSONB,         -- populated after the write executes
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '30 days'
);

CREATE INDEX IF NOT EXISTS idx_snapshots_write_action
    ON write_snapshots (write_action_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_user_recent
    ON write_snapshots (user_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_expires
    ON write_snapshots (expires_at) WHERE expires_at IS NOT NULL;
