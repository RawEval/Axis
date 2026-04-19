-- 016_activity_events_external_id.sql
-- Adds the vendor's stable identifier (Notion page id, Slack message ts+channel,
-- Gmail message id, etc.) and uses it as the idempotency key for ingest.
-- Backfill existing rows from the existing `id` so the constraint holds during deploy.

ALTER TABLE activity_events
  ADD COLUMN IF NOT EXISTS external_id TEXT;

UPDATE activity_events SET external_id = id::text WHERE external_id IS NULL;

ALTER TABLE activity_events ALTER COLUMN external_id SET NOT NULL;

ALTER TABLE activity_events
  ADD CONSTRAINT activity_events_source_external_uniq
  UNIQUE (user_id, source, external_id);
