-- Axis — OAuth state storage for in-flight authorization flows.
-- Stores: state, user_id, tool, PKCE verifier. 10-minute TTL.

CREATE TABLE IF NOT EXISTS oauth_states (
    state TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool TEXT NOT NULL,
    pkce_verifier TEXT,
    redirect_after TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '10 minutes'
);
CREATE INDEX IF NOT EXISTS idx_oauth_states_expires ON oauth_states(expires_at);

-- Token refresh tracking
ALTER TABLE connectors
    ADD COLUMN IF NOT EXISTS refresh_token_encrypted BYTEA,
    ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS scopes TEXT,
    ADD COLUMN IF NOT EXISTS workspace_id TEXT,
    ADD COLUMN IF NOT EXISTS workspace_name TEXT;
