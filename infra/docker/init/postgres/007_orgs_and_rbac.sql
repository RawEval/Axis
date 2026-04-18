-- Axis — organizations + role-based delegation (ADR 010).
--
-- Introduces organizations as the top-level tenant. Every user gets a
-- personal org on first signup. Projects belong to orgs. Roles are
-- permission tiers — NEVER job titles. The only allowed role names are:
--   owner / admin / manager / member / viewer
--
-- See docs/architecture/org-and-rbac.md for the design.

-- ============================================================================
-- 1. organizations
-- ============================================================================
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE,                     -- optional short handle
    plan TEXT NOT NULL DEFAULT 'free',    -- free | pro | team | enterprise
    is_personal BOOLEAN NOT NULL DEFAULT FALSE,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_orgs_active ON organizations(id) WHERE deleted_at IS NULL;

-- ============================================================================
-- 2. organization_members
-- ============================================================================
CREATE TABLE IF NOT EXISTS organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    invited_by UUID REFERENCES users(id) ON DELETE SET NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    removed_at TIMESTAMPTZ,                -- soft delete for audit
    UNIQUE (org_id, user_id),
    CHECK (role IN ('owner', 'admin', 'manager', 'member', 'viewer'))
);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id) WHERE removed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(org_id) WHERE removed_at IS NULL;

-- ============================================================================
-- 3. organization_invites
-- ============================================================================
CREATE TABLE IF NOT EXISTS organization_invites (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,  -- optional scope
    token TEXT UNIQUE NOT NULL,             -- 32-char random, in the magic link
    invited_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CHECK (role IN ('owner', 'admin', 'manager', 'member', 'viewer'))
);
CREATE INDEX IF NOT EXISTS idx_org_invites_token ON organization_invites(token) WHERE consumed_at IS NULL AND revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_org_invites_email ON organization_invites(email) WHERE consumed_at IS NULL AND revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_org_invites_org ON organization_invites(org_id);

-- ============================================================================
-- 4. project_members (already implied by ADR 010 — scoped role override)
-- ============================================================================
CREATE TABLE IF NOT EXISTS project_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,                    -- override for this project
    added_by UUID REFERENCES users(id) ON DELETE SET NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    removed_at TIMESTAMPTZ,
    UNIQUE (project_id, user_id),
    CHECK (role IN ('owner', 'admin', 'manager', 'member', 'viewer'))
);
CREATE INDEX IF NOT EXISTS idx_project_members_user ON project_members(user_id) WHERE removed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_project_members_project ON project_members(project_id) WHERE removed_at IS NULL;

-- ============================================================================
-- 5. Add org_id + default_grant to projects
-- ============================================================================
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS default_grant TEXT NOT NULL DEFAULT 'org';

ALTER TABLE projects
    DROP CONSTRAINT IF EXISTS projects_default_grant_check;
ALTER TABLE projects
    ADD CONSTRAINT projects_default_grant_check CHECK (default_grant IN ('org', 'explicit'));

CREATE INDEX IF NOT EXISTS idx_projects_org ON projects(org_id);

-- ============================================================================
-- 6. Add token_owner_user_id to connectors (shared vs personal)
-- ============================================================================
ALTER TABLE connectors
    ADD COLUMN IF NOT EXISTS token_owner_user_id UUID REFERENCES users(id) ON DELETE SET NULL;
-- NULL means shared / org-scoped.

-- ============================================================================
-- 7. Backfill — create a personal org for every existing user and attach
--    their existing default project to it. Every existing connector row
--    with a user_id becomes a personal-owned token.
-- ============================================================================

-- 7a-7e. Deterministic personal-org seed: one personal org per user,
-- the user is the sole owner, and all their projects attach to it.
-- Uses a row-by-row loop so the name JOIN can never duplicate.
DO $$
DECLARE
    u RECORD;
    org_uuid UUID;
BEGIN
    FOR u IN SELECT id, email, COALESCE(name, 'Personal') AS display_name FROM users
    LOOP
        -- Skip if this user already belongs to any org (re-runs are safe)
        IF EXISTS (SELECT 1 FROM organization_members WHERE user_id = u.id) THEN
            CONTINUE;
        END IF;

        INSERT INTO organizations (name, is_personal)
        VALUES (u.display_name, TRUE)
        RETURNING id INTO org_uuid;

        INSERT INTO organization_members (org_id, user_id, role)
        VALUES (org_uuid, u.id, 'owner');

        UPDATE projects
        SET org_id = org_uuid
        WHERE user_id = u.id AND org_id IS NULL;
    END LOOP;
END $$;

-- 7f. Stamp existing connector rows with the user as the token owner
UPDATE connectors
SET token_owner_user_id = user_id
WHERE token_owner_user_id IS NULL
  AND user_id IS NOT NULL;
