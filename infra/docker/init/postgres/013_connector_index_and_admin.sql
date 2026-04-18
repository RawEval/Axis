-- Axis — Session 11: Connector data index + admin metrics
--
-- connector_index: pre-indexed connector data for instant local search.
-- Background sync workers populate this table continuously; the agent
-- queries it instead of hitting live provider APIs every time.
--
-- admin_metrics: aggregated system metrics for the admin dashboard.
-- Refreshed by a materialized view or periodic job.

-- ============================================================================
-- 1. Connector data index — local search cache
-- ============================================================================

CREATE TABLE IF NOT EXISTS connector_index (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    tool TEXT NOT NULL,              -- slack | notion | gmail | gdrive | github
    resource_type TEXT NOT NULL,     -- message | page | email | file | issue | pr | thread
    resource_id TEXT NOT NULL,       -- provider-native ID (channel:ts for Slack, page_id for Notion, etc.)
    title TEXT,
    body TEXT,                       -- full text for FTS
    url TEXT,
    author TEXT,
    author_id TEXT,
    occurred_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stale BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (user_id, tool, resource_id)
);

-- Full-text search index on title + body
CREATE INDEX IF NOT EXISTS idx_connector_index_fts
    ON connector_index USING gin(to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(body, '')));

-- User + tool lookup for filtered searches
CREATE INDEX IF NOT EXISTS idx_connector_index_user_tool
    ON connector_index (user_id, tool, occurred_at DESC);

-- Project-scoped lookup
CREATE INDEX IF NOT EXISTS idx_connector_index_project
    ON connector_index (project_id, tool) WHERE project_id IS NOT NULL;

-- Stale-row cleanup index
CREATE INDEX IF NOT EXISTS idx_connector_index_stale
    ON connector_index (stale, indexed_at) WHERE stale = TRUE;

-- ============================================================================
-- 2. Sync cursors — track where each background sync left off
-- ============================================================================

CREATE TABLE IF NOT EXISTS sync_cursors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    tool TEXT NOT NULL,
    cursor_type TEXT NOT NULL,      -- 'page_token' | 'timestamp' | 'change_id'
    cursor_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, tool, cursor_type)
);

-- ============================================================================
-- 3. Admin daily metrics (materialized snapshot)
-- ============================================================================

CREATE TABLE IF NOT EXISTS admin_daily_metrics (
    date DATE NOT NULL,
    metric TEXT NOT NULL,           -- 'total_users' | 'total_runs' | 'avg_latency_ms' | etc.
    value NUMERIC NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    PRIMARY KEY (date, metric)
);

-- ============================================================================
-- 4. Useful views for admin queries
-- ============================================================================

-- Connector health across all users
CREATE OR REPLACE VIEW admin_connector_health AS
SELECT
    c.tool_name,
    c.health_status,
    COUNT(*) AS connector_count,
    COUNT(DISTINCT c.user_id) AS user_count,
    MAX(c.last_sync) AS most_recent_sync
FROM connectors c
WHERE c.status = 'connected'
GROUP BY c.tool_name, c.health_status
ORDER BY c.tool_name, c.health_status;

-- Run stats per day
CREATE OR REPLACE VIEW admin_run_stats AS
SELECT
    DATE(aa.timestamp) AS run_date,
    COUNT(*) AS run_count,
    COUNT(DISTINCT aa.user_id) AS unique_users,
    AVG((aa.result->>'latency_ms')::numeric) AS avg_latency_ms,
    AVG((aa.result->>'tokens_used')::numeric) AS avg_tokens,
    SUM((aa.result->>'tokens_used')::numeric) AS total_tokens
FROM agent_actions aa
GROUP BY DATE(aa.timestamp)
ORDER BY run_date DESC;

-- Eval quality trend
CREATE OR REPLACE VIEW admin_eval_trend AS
SELECT
    DATE(er.created_at) AS eval_date,
    er.rubric_type,
    COUNT(*) AS eval_count,
    AVG(er.composite_score) AS avg_composite,
    COUNT(*) FILTER (WHERE er.flagged) AS flagged_count,
    ROUND(COUNT(*) FILTER (WHERE er.flagged)::numeric / NULLIF(COUNT(*), 0) * 100, 1) AS flagged_pct
FROM eval_results er
GROUP BY DATE(er.created_at), er.rubric_type
ORDER BY eval_date DESC, er.rubric_type;

-- Index coverage per user
CREATE OR REPLACE VIEW admin_index_coverage AS
SELECT
    ci.user_id,
    u.email,
    ci.tool,
    ci.resource_type,
    COUNT(*) AS indexed_rows,
    MAX(ci.indexed_at) AS last_indexed,
    COUNT(*) FILTER (WHERE ci.stale) AS stale_rows
FROM connector_index ci
JOIN users u ON u.id = ci.user_id
GROUP BY ci.user_id, u.email, ci.tool, ci.resource_type
ORDER BY u.email, ci.tool;
