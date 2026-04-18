-- Axis — multi-scope BYO OAuth credentials.
--
-- Original design (ADR 003 migration 005) had user_oauth_apps — per-user only.
-- This migration introduces a unified oauth_apps table that can carry
-- credentials at three scopes:
--
--   1. user     — a single user's personal OAuth app
--   2. org      — shared across everyone in an organization
--   3. project  — scoped to a specific project
--
-- At call time the resolver looks up in this order:
--
--   project  →  org  →  user  →  Axis default (from settings)
--
-- The first hit wins. Admins+ can save org-scoped apps. Managers+ can save
-- project-scoped apps. Any user can save their own personal app.
--
-- We keep the existing user_oauth_apps table unchanged so the data survives;
-- a view unifies reads. Next session can do a real data migration if desired.

-- ============================================================================
-- 1. The unified table
-- ============================================================================
CREATE TABLE IF NOT EXISTS oauth_apps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scope TEXT NOT NULL,             -- user | org | project
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_secret_encrypted BYTEA NOT NULL,
    redirect_uri TEXT,
    extra JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (scope IN ('user', 'org', 'project')),
    -- Exactly one scope column set
    CHECK (
        (scope = 'user'    AND user_id    IS NOT NULL AND org_id IS NULL  AND project_id IS NULL)
     OR (scope = 'org'     AND user_id    IS NULL     AND org_id IS NOT NULL AND project_id IS NULL)
     OR (scope = 'project' AND user_id    IS NULL     AND org_id IS NULL  AND project_id IS NOT NULL)
    )
);

-- One record per (scope, identity, tool). Partial unique indexes make this
-- enforceable even though the "identity" column varies by scope.
CREATE UNIQUE INDEX IF NOT EXISTS uq_oauth_apps_user
    ON oauth_apps(user_id, tool_name) WHERE scope = 'user';
CREATE UNIQUE INDEX IF NOT EXISTS uq_oauth_apps_org
    ON oauth_apps(org_id, tool_name) WHERE scope = 'org';
CREATE UNIQUE INDEX IF NOT EXISTS uq_oauth_apps_project
    ON oauth_apps(project_id, tool_name) WHERE scope = 'project';

-- Lookup-by-tool indexes for the resolver
CREATE INDEX IF NOT EXISTS idx_oauth_apps_tool
    ON oauth_apps(tool_name);

-- ============================================================================
-- 2. Backfill from user_oauth_apps (keeps old and new in sync)
-- ============================================================================
INSERT INTO oauth_apps (
    scope, user_id, tool_name, client_id, client_secret_encrypted,
    redirect_uri, extra, created_by, created_at, updated_at
)
SELECT
    'user', user_id, tool_name, client_id, client_secret_encrypted,
    redirect_uri, extra, user_id, created_at, updated_at
FROM user_oauth_apps
ON CONFLICT DO NOTHING;
