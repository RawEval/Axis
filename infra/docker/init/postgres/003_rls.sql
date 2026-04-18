-- Axis — Row-Level Security decision
-- ============================================================================
-- See docs/architecture/rls-decision.md for the full rationale.
--
-- DECISION (Phase 1): Disable RLS and rely on application-level isolation.
-- Every query in services/*/app/repositories/* includes WHERE user_id = $1.
-- We will re-enable RLS with real policies once we move to Supabase (Phase 2)
-- where the database role is not the table owner and RLS is free.
--
-- Why not leave it enabled: when RLS is enabled without policies, any role
-- that is NOT the table owner (typical in Supabase / cloud Postgres) reads
-- zero rows silently. This is a P0 silent-breakage risk.
-- ============================================================================

ALTER TABLE users               DISABLE ROW LEVEL SECURITY;
ALTER TABLE connectors          DISABLE ROW LEVEL SECURITY;
ALTER TABLE agent_actions       DISABLE ROW LEVEL SECURITY;
ALTER TABLE write_actions       DISABLE ROW LEVEL SECURITY;
ALTER TABLE proactive_surfaces  DISABLE ROW LEVEL SECURITY;
ALTER TABLE eval_results        DISABLE ROW LEVEL SECURITY;
ALTER TABLE correction_signals  DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_devices        DISABLE ROW LEVEL SECURITY;
ALTER TABLE login_events        DISABLE ROW LEVEL SECURITY;
