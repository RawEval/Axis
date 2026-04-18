-- Axis — schema stubs for the agentic expansion.
--
-- These tables are defined now so future work doesn't need yet another
-- migration. They're not wired into the services yet. Covered by:
--   docs/architecture/agentic-architecture.md  (ADR 005)
--   docs/architecture/permissions-model.md     (ADR 006)
--   docs/architecture/activity-feed.md         (ADR 007)
--   docs/architecture/streaming-real-time.md   (ADR 008)

-- ============================================================================
-- 1. agent_tasks + agent_task_steps  (ADR 005 — supervisor+workers)
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    prompt TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'explicit',   -- explicit | all | auto | default
    status TEXT NOT NULL DEFAULT 'planning',  -- planning | running | awaiting_confirmation | done | failed | cancelled
    config JSONB,                             -- { capabilities, roles, max_steps, max_tokens, max_cost_usd }
    plan JSONB,                               -- decomposed plan from the supervisor
    result JSONB,                             -- final synthesised output
    tokens_used INT NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10, 4),
    latency_ms INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_user_recent
    ON agent_tasks (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_project_recent
    ON agent_tasks (project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status
    ON agent_tasks (status) WHERE status IN ('running', 'awaiting_confirmation');

CREATE TABLE IF NOT EXISTS agent_task_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES agent_tasks(id) ON DELETE CASCADE,
    parent_step_id UUID REFERENCES agent_task_steps(id) ON DELETE CASCADE,
    agent_role TEXT NOT NULL,     -- reader | writer | research | code | math | summarise | synthesise
    capability TEXT,              -- e.g. 'connector.notion.search', 'git.clone'
    input JSONB,
    output JSONB,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending | running | done | failed | skipped
    tokens_used INT NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_agent_task_steps_task ON agent_task_steps(task_id);

-- ============================================================================
-- 2. capabilities registry (ADR 005)
-- ============================================================================
CREATE TABLE IF NOT EXISTS capabilities (
    name TEXT PRIMARY KEY,            -- 'connector.notion.search'
    description TEXT NOT NULL,
    action TEXT NOT NULL,             -- read | write | execute
    default_permission TEXT NOT NULL, -- auto | ask | always_gate
    input_schema JSONB NOT NULL,
    output_schema JSONB,
    min_plan TEXT NOT NULL DEFAULT 'free',  -- free | pro | team | enterprise
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================================
-- 3. permission_grants (ADR 006 — Claude-Code-style grants)
-- ============================================================================
CREATE TABLE IF NOT EXISTS permission_grants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,  -- NULL = user-wide
    capability TEXT NOT NULL,
    action TEXT NOT NULL,             -- read | write | execute
    decision TEXT NOT NULL,           -- granted | denied
    lifetime TEXT NOT NULL,           -- session | 24h | project | forever
    expires_at TIMESTAMPTZ,
    granted_by TEXT NOT NULL DEFAULT 'user',  -- user | auto | system
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (decision IN ('granted', 'denied')),
    CHECK (action IN ('read', 'write', 'execute')),
    CHECK (lifetime IN ('session', '24h', 'project', 'forever'))
);
CREATE INDEX IF NOT EXISTS idx_grants_user_cap
    ON permission_grants (user_id, capability, action);
CREATE INDEX IF NOT EXISTS idx_grants_project
    ON permission_grants (project_id) WHERE project_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_grants_expires
    ON permission_grants (expires_at) WHERE expires_at IS NOT NULL;

CREATE TABLE IF NOT EXISTS permission_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    task_id UUID REFERENCES agent_tasks(id) ON DELETE SET NULL,
    step_id UUID REFERENCES agent_task_steps(id) ON DELETE SET NULL,
    capability TEXT NOT NULL,
    action TEXT NOT NULL,
    event_type TEXT NOT NULL,   -- requested | granted | denied | auto_granted | revoked
    context JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_permission_events_user
    ON permission_events (user_id, created_at DESC);

-- ============================================================================
-- 4. activity_events — user-level firehose (ADR 007)
-- ============================================================================
CREATE TABLE IF NOT EXISTS activity_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,  -- NULL for user-wide events
    source TEXT NOT NULL,             -- slack | notion | gmail | gdrive | github | linear | gcalendar | axis
    event_type TEXT NOT NULL,         -- message | mention | edit | commit | draft | agent_run_completed | ...
    actor TEXT,                       -- human/bot name
    actor_id TEXT,                    -- provider-native id
    title TEXT NOT NULL,              -- one-line summary
    snippet TEXT,                     -- short excerpt
    raw_ref JSONB,                    -- provider-native ids for re-fetching
    importance_score NUMERIC(3, 2),   -- 0.0..1.0 from the relevance engine
    occurred_at TIMESTAMPTZ NOT NULL,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_activity_user_recent
    ON activity_events (user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_project_recent
    ON activity_events (project_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_source
    ON activity_events (user_id, source, occurred_at DESC);
-- Full-text search over title+snippet for natural-language queries
CREATE INDEX IF NOT EXISTS idx_activity_fts
    ON activity_events USING gin (to_tsvector('english', title || ' ' || COALESCE(snippet, '')));

-- ============================================================================
-- 5. Seed: bootstrap capability catalog
-- ============================================================================
INSERT INTO capabilities (name, description, action, default_permission, input_schema) VALUES
    ('memory.retrieve',          'Retrieve user memory (episodic/semantic/procedural)',     'read',    'auto',        '{}'::jsonb),
    ('web.search',               'Search the public web',                                   'read',    'auto',        '{}'::jsonb),
    ('web.fetch',                'Fetch a public URL and extract text',                     'read',    'auto',        '{}'::jsonb),
    ('activity.query',           'Query the user''s activity stream',                       'read',    'auto',        '{}'::jsonb),
    ('connector.slack.read',     'Read Slack messages and channels',                        'read',    'ask',         '{}'::jsonb),
    ('connector.slack.write',    'Post Slack messages (requires confirmation)',             'write',   'ask',         '{}'::jsonb),
    ('connector.notion.read',    'Read Notion pages and databases',                         'read',    'ask',         '{}'::jsonb),
    ('connector.notion.write',   'Create/edit Notion pages (requires confirmation)',        'write',   'ask',         '{}'::jsonb),
    ('connector.gmail.read',     'Read Gmail messages',                                     'read',    'ask',         '{}'::jsonb),
    ('connector.gmail.draft',    'Draft a Gmail message (user reviews before send)',        'write',   'ask',         '{}'::jsonb),
    ('connector.gmail.send',     'Send an email (ALWAYS gated)',                            'write',   'always_gate', '{}'::jsonb),
    ('connector.gdrive.read',    'Read Google Drive documents',                             'read',    'ask',         '{}'::jsonb),
    ('connector.gdrive.write',   'Create/edit Google Docs (requires confirmation)',         'write',   'ask',         '{}'::jsonb),
    ('connector.github.read',    'Read GitHub repos/issues/PRs',                            'read',    'ask',         '{}'::jsonb),
    ('connector.github.comment', 'Comment on GitHub issues/PRs',                            'write',   'ask',         '{}'::jsonb),
    ('connector.github.merge',   'Merge a GitHub PR (ALWAYS gated)',                        'write',   'always_gate', '{}'::jsonb),
    ('git.clone',                'Clone a public Git repository',                           'read',    'auto',        '{}'::jsonb),
    ('git.grep',                 'Grep inside a cloned repository',                         'read',    'auto',        '{}'::jsonb),
    ('git.push',                 'Push commits to a remote (ALWAYS gated)',                 'execute', 'always_gate', '{}'::jsonb),
    ('code.run',                 'Run sandboxed code (Python, no network)',                 'execute', 'ask',         '{}'::jsonb),
    ('code.run.network',         'Run sandboxed code with network egress',                  'execute', 'always_gate', '{}'::jsonb),
    ('math.solve',               'Symbolic / numeric math via sympy+numpy',                 'execute', 'auto',        '{}'::jsonb)
ON CONFLICT (name) DO NOTHING;
