# Row-Level Security — Phase 1 Decision

**Decision date:** 2026-04-15
**Status:** Active
**Supersedes:** `001_init.sql`'s original `ENABLE ROW LEVEL SECURITY` clauses (neutralized in `003_rls.sql`)

## Context

The spec (§10 "Security & Privacy") says:

> User data isolated at the database level. Row-level security on all PostgreSQL tables.

Our initial scaffold honored that literally: `001_init.sql` ended with `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` on every table. **No `CREATE POLICY` statements were written.** That combination is a P0 silent-breakage trap.

## The trap

When RLS is ON without any policies:
- **The table owner** still reads/writes everything because owners have `BYPASSRLS` by default (our local `axis` dev role is the owner of every table, so local dev worked fine).
- **Any other role** — which is what you get in Supabase, Railway Postgres, or any managed cloud where you log in as a non-owner — reads **zero rows silently**. No error. Just empty results.

This means: "smoke tests pass locally, production is a ghost town."

## Why we're disabling instead of fixing

Writing correct per-user policies requires either:

1. **Per-request session variables:** `SET LOCAL axis.user_id = '<uuid>'` inside every asyncpg connection wrapper, plus policies like `USING (user_id::text = current_setting('axis.user_id', true))`. Adds per-request overhead, requires tight discipline in every repository, and doesn't compose well with connection pools that multiplex.
2. **Supabase auth JWT claims:** `USING (user_id = auth.uid())` — only works once we're on Supabase (Phase 2 per spec §8.5).

Phase 1 has ten services to ship and three months to do it. **We accept application-level isolation.** Every query in `services/*/app/repositories/*` already includes `WHERE user_id = $1`. The audit (see `audit-findings.md`) confirmed 100% of existing queries are parameterized with the user_id.

## What we lose

- A second safety net. If a route ever forgets `WHERE user_id`, users see each other's data.
- Strictly-correct spec compliance until Phase 2.

## Mitigations we keep

1. **Code review enforcement.** Any new repository must take `user_id` as the first parameter. `services/CLAUDE.md` states this as a rule.
2. **Per-user Qdrant namespaces.** Vector isolation remains spec-compliant via collection naming, not RLS.
3. **Audit logging.** `login_events` table tracks every auth event. If isolation breaks, we'll see unusual access patterns.
4. **Tests.** Phase-1 test plan (task #18) includes a cross-user isolation test on `connectors` and `agent_actions`.

## Re-enable plan (Phase 2)

When we migrate to Supabase:

```sql
ALTER TABLE users              ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_self ON users
  FOR ALL TO authenticated USING (auth.uid() = id);

ALTER TABLE connectors         ENABLE ROW LEVEL SECURITY;
CREATE POLICY connectors_self ON connectors
  FOR ALL TO authenticated USING (auth.uid() = user_id);

-- ... same pattern for agent_actions, write_actions, proactive_surfaces,
-- eval_results, correction_signals, user_devices, login_events
```

Tracked in `docs/runbooks/supabase-migration.md` (TBD).

## Enforcement

- `003_rls.sql` disables RLS on all nine tables.
- This doc is the ADR; link from any future migration that touches isolation.
- Re-enabling RLS without policies is a **PR-blocker**. Add to CODEOWNERS if we adopt them.
