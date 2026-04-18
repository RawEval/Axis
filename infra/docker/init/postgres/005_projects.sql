-- Axis — projects as the unit of work (ADR 002).
-- Every tenant table gains project_id. A user's "Personal" project is
-- auto-created on first signup and used as the default when no project is
-- explicitly pinned.
--
-- Also adds user_oauth_apps for BYO OAuth credentials (ADR 003).

-- ============================================================================
-- 1. projects
-- ============================================================================
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, name)
);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
-- Only ONE default per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_user_default
    ON projects(user_id) WHERE is_default = TRUE;

-- ============================================================================
-- 2. user_oauth_apps (BYO credentials)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_oauth_apps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_secret_encrypted BYTEA NOT NULL,
    redirect_uri TEXT,
    extra JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, tool_name)
);
CREATE INDEX IF NOT EXISTS idx_user_oauth_apps_user ON user_oauth_apps(user_id);

-- ============================================================================
-- 3. Add project_id to every tenant table
-- ============================================================================
ALTER TABLE connectors
    ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE agent_actions
    ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE proactive_surfaces
    ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE write_actions
    ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;
ALTER TABLE correction_signals
    ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE CASCADE;

-- ============================================================================
-- 4. Backfill: create a "Personal" project for every existing user and
--    attach all their existing rows to it.
-- ============================================================================
INSERT INTO projects (user_id, name, description, is_default)
SELECT id, 'Personal', 'Your default workspace', TRUE
FROM users
ON CONFLICT (user_id, name) DO NOTHING;

-- Attach existing connectors
UPDATE connectors c
SET project_id = p.id
FROM projects p
WHERE c.user_id = p.user_id AND p.is_default = TRUE AND c.project_id IS NULL;

UPDATE agent_actions a
SET project_id = p.id
FROM projects p
WHERE a.user_id = p.user_id AND p.is_default = TRUE AND a.project_id IS NULL;

UPDATE proactive_surfaces ps
SET project_id = p.id
FROM projects p
WHERE ps.user_id = p.user_id AND p.is_default = TRUE AND ps.project_id IS NULL;

UPDATE correction_signals cs
SET project_id = p.id
FROM projects p
WHERE cs.user_id = p.user_id AND p.is_default = TRUE AND cs.project_id IS NULL;

-- write_actions don't have user_id directly; join via agent_actions
UPDATE write_actions wa
SET project_id = aa.project_id
FROM agent_actions aa
WHERE wa.action_id = aa.id AND wa.project_id IS NULL;

-- ============================================================================
-- 5. Loosen the UNIQUE constraint on connectors so a user can connect the
--    same tool to multiple projects (e.g., two different Slack workspaces).
-- ============================================================================
ALTER TABLE connectors DROP CONSTRAINT IF EXISTS connectors_user_id_tool_name_key;
-- Guard against duplicates that may already exist from earlier testing
DO $$
BEGIN
    BEGIN
        ALTER TABLE connectors
            ADD CONSTRAINT connectors_user_project_tool_uniq
            UNIQUE (user_id, project_id, tool_name);
    EXCEPTION WHEN duplicate_object THEN
        -- constraint already exists, move on
        NULL;
    END;
END $$;

-- ============================================================================
-- 6. Helpful indexes for project-scoped reads
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_connectors_project ON connectors(project_id);
CREATE INDEX IF NOT EXISTS idx_actions_project_ts ON agent_actions(project_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_surfaces_project_pending
    ON proactive_surfaces(project_id, status) WHERE status = 'pending';
