-- Axis — Session 10: device tokens for push notifications
--
-- Each row maps a user to a specific device token (APNs or FCM).
-- The notification-service reads these when it needs to fan out a push.

CREATE TABLE IF NOT EXISTS user_devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('ios', 'android', 'web')),
    token TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, platform, token)
);

CREATE INDEX IF NOT EXISTS idx_user_devices_user
    ON user_devices (user_id) WHERE active = TRUE;
