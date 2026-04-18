-- Axis — rich agent history (project-scoped)
--
-- Introduces the message-level history that the chat UI renders. Every
-- user prompt and every assistant response becomes a row in agent_messages.
-- Each assistant message can carry many agent_citations (one per source
-- Axis pulled data from — a Notion page, a Gmail thread, a GitHub PR,
-- a Slack message, etc.). Each citation can have many citation_spans
-- (character offsets into the assistant's text to highlight).
--
-- See docs/alignment-audit.md gap #2 (no source tracing) and gap #13
-- (chat page shows no citations).

-- ============================================================================
-- 1. agent_messages — individual turns in a conversation
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    action_id UUID REFERENCES agent_actions(id) ON DELETE CASCADE,
    task_id UUID REFERENCES agent_tasks(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,                           -- the displayed text
    content_format TEXT NOT NULL DEFAULT 'text',     -- text | markdown | json
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,     -- tokens, model, latency, tool_name, ...
    parent_message_id UUID REFERENCES agent_messages(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_messages_project_recent
    ON agent_messages (project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_user_recent
    ON agent_messages (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_action
    ON agent_messages (action_id);
-- Full-text search across every message the user has sent/received in a project
CREATE INDEX IF NOT EXISTS idx_messages_fts
    ON agent_messages USING gin (to_tsvector('english', content));

-- ============================================================================
-- 2. agent_citations — one row per external source the agent used
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES agent_messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,

    -- What kind of thing this citation points at
    source_type TEXT NOT NULL,          -- notion_page | slack_message | gmail_thread | gdrive_doc | github_pr | web_page | memory_node | file
    provider TEXT,                      -- notion | slack | gmail | gdrive | github | web | memory
    ref_id TEXT,                        -- provider-native id (notion page id, gmail thread id, ...)
    url TEXT,                           -- link-out for the UI
    title TEXT,                         -- human-readable title
    actor TEXT,                         -- person or bot attributable for this source
    actor_id TEXT,                      -- provider-native actor id
    excerpt TEXT,                       -- short snippet shown in the source card
    occurred_at TIMESTAMPTZ,            -- when the source content was created/modified

    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_citations_message ON agent_citations(message_id);
CREATE INDEX IF NOT EXISTS idx_citations_project ON agent_citations(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_citations_provider ON agent_citations(provider);

-- ============================================================================
-- 3. citation_spans — character offsets to highlight in the message text
-- ============================================================================
--
-- A single citation can be referenced in multiple places in the assistant's
-- text (e.g. "Samir said X ... and later Samir added Y" might link both
-- phrases to the same Gmail thread). We store each reference as a span with
-- start/end character offsets into agent_messages.content, plus an optional
-- label for what the span means.
CREATE TABLE IF NOT EXISTS citation_spans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    citation_id UUID NOT NULL REFERENCES agent_citations(id) ON DELETE CASCADE,
    message_id UUID NOT NULL REFERENCES agent_messages(id) ON DELETE CASCADE,
    start_offset INT NOT NULL,      -- inclusive, 0-based character index in content
    end_offset INT NOT NULL,        -- exclusive
    label TEXT,                     -- optional: "quote", "summary", "reference", ...
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (end_offset > start_offset)
);
CREATE INDEX IF NOT EXISTS idx_spans_message ON citation_spans(message_id);
CREATE INDEX IF NOT EXISTS idx_spans_citation ON citation_spans(citation_id);

-- ============================================================================
-- 4. Helpful view: hydrated message (message + its citations)
-- ============================================================================
CREATE OR REPLACE VIEW agent_messages_hydrated AS
SELECT
    m.id,
    m.user_id,
    m.project_id,
    m.action_id,
    m.task_id,
    m.role,
    m.content,
    m.content_format,
    m.metadata,
    m.created_at,
    COALESCE(
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'id', c.id,
                    'source_type', c.source_type,
                    'provider', c.provider,
                    'ref_id', c.ref_id,
                    'url', c.url,
                    'title', c.title,
                    'actor', c.actor,
                    'excerpt', c.excerpt,
                    'occurred_at', c.occurred_at,
                    'spans', COALESCE(
                        (
                            SELECT jsonb_agg(
                                jsonb_build_object(
                                    'start', s.start_offset,
                                    'end', s.end_offset,
                                    'label', s.label
                                )
                                ORDER BY s.start_offset
                            )
                            FROM citation_spans s
                            WHERE s.citation_id = c.id
                        ),
                        '[]'::jsonb
                    )
                )
                ORDER BY c.created_at
            )
            FROM agent_citations c
            WHERE c.message_id = m.id
        ),
        '[]'::jsonb
    ) AS citations
FROM agent_messages m;
