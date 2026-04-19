-- 017_users_timezone.sql
-- IANA timezone name, used by activity.query to compute "today" in user's local time.
ALTER TABLE users ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'UTC';
