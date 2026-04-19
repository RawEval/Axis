-- 015_connector_sync_state.sql
-- Single source of truth for "is data fresh?" per (user, source).
-- Read by the freshness chip, the FreshenBeforeRead mixin, and the cron scheduler.

CREATE TABLE IF NOT EXISTS connector_sync_state (
  user_id            UUID        NOT NULL,
  source             TEXT        NOT NULL CHECK (source IN ('slack','notion','gmail','gdrive','github')),
  last_synced_at     TIMESTAMPTZ,
  last_status        TEXT        NOT NULL DEFAULT 'never'
                     CHECK (last_status IN ('never','ok','auth_failed','vendor_error','network_error')),
  last_error         TEXT,
  last_event_at      TIMESTAMPTZ,
  consecutive_fails  INT         NOT NULL DEFAULT 0,
  cursor             JSONB       NOT NULL DEFAULT '{}'::jsonb,
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, source)
);

CREATE INDEX IF NOT EXISTS connector_sync_state_status_not_ok_idx
  ON connector_sync_state (last_status)
  WHERE last_status != 'ok';

ALTER TABLE connector_sync_state ENABLE ROW LEVEL SECURITY;

CREATE POLICY connector_sync_state_user_isolation ON connector_sync_state
  FOR ALL USING (user_id = current_setting('app.current_user_id', true)::uuid);
