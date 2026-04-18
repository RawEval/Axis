-- Axis — initial Postgres schema
-- Maps to the data model in docs/axis_full_spec.docx §09

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    plan TEXT NOT NULL DEFAULT 'free',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    usage JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Connectors
CREATE TABLE IF NOT EXISTS connectors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    auth_token_encrypted BYTEA,
    permissions JSONB NOT NULL DEFAULT '{"read": true, "write": false}'::jsonb,
    last_sync TIMESTAMPTZ,
    health_status TEXT NOT NULL DEFAULT 'green',
    error_log JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, tool_name)
);
CREATE INDEX idx_connectors_user ON connectors(user_id);
CREATE INDEX idx_connectors_health ON connectors(health_status) WHERE health_status != 'green';

-- Agent actions (the core log)
CREATE TABLE IF NOT EXISTS agent_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    plan JSONB,
    result JSONB,
    eval_score JSONB,
    correction JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_actions_user_ts ON agent_actions(user_id, timestamp DESC);

-- Write actions
CREATE TABLE IF NOT EXISTS write_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_id UUID NOT NULL REFERENCES agent_actions(id) ON DELETE CASCADE,
    tool TEXT NOT NULL,
    target_id TEXT,
    target_type TEXT,
    diff JSONB,
    confirmed_by_user BOOLEAN NOT NULL DEFAULT FALSE,
    confirmed_at TIMESTAMPTZ,
    snapshot_id TEXT,
    rolled_back BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_writes_action ON write_actions(action_id);

-- Proactive surfaces
CREATE TABLE IF NOT EXISTS proactive_surfaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    signal_type TEXT NOT NULL,
    title TEXT NOT NULL,
    context_snippet TEXT,
    confidence_score NUMERIC(3,2),
    proposed_action JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    user_response_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_surfaces_user_pending ON proactive_surfaces(user_id, status) WHERE status = 'pending';

-- Eval results
CREATE TABLE IF NOT EXISTS eval_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_id UUID NOT NULL REFERENCES agent_actions(id) ON DELETE CASCADE,
    rubric_type TEXT NOT NULL,
    scores JSONB NOT NULL,
    composite_score NUMERIC(3,2),
    flagged BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_by_user BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Correction signals
CREATE TABLE IF NOT EXISTS correction_signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action_id UUID NOT NULL REFERENCES agent_actions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    correction_type TEXT NOT NULL,
    note TEXT,
    applied_to_memory BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_corrections_user ON correction_signals(user_id);

-- Row-level security (per spec §10)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE connectors ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE write_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE proactive_surfaces ENABLE ROW LEVEL SECURITY;
ALTER TABLE eval_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE correction_signals ENABLE ROW LEVEL SECURITY;
