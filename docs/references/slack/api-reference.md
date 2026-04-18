# Slack API Reference — Local Copy for Axis Development

**Fetched:** 2026-04-16 from docs.slack.dev

## Method Categories

admin, api, apps, assistant, auth, bookmarks, bots, calls, canvases, chat,
conversations, dialog, dnd, emoji, entity, files, functions, lists,
migration, oauth, openid, pins, reactions, reminders, rtm, search, stars,
team, tooling, usergroups, users, views, workflows

## Key Methods for Axis Phase 1

### conversations.list
- **URL:** `GET https://slack.com/api/conversations.list`
- **Scopes:** channels:read, groups:read, im:read, mpim:read (bot + user)
- **Params:** cursor, exclude_archived, limit (max 1000, default 100), team_id, types (public_channel,private_channel,mpim,im)
- **Rate:** Tier 2 (20+ RPM)
- **Pagination:** cursor-based via response_metadata.next_cursor

### conversations.history
- **URL:** `GET https://slack.com/api/conversations.history`
- **Scopes:** channels:history, groups:history, im:history, mpim:history
- **Params:** channel (required), latest, oldest, limit (max 999, default 100), cursor, include_all_metadata, inclusive
- **Rate:** Tier 3 (50+ RPM)
- **Returns:** messages[], has_more, pin_count, response_metadata.next_cursor

### conversations.replies
- **URL:** `GET https://slack.com/api/conversations.replies`
- **Scopes:** channels:history, groups:history, im:history, mpim:history
- **Params:** channel + ts (required), cursor, limit (default 1000), oldest, latest, inclusive, include_all_metadata
- **Rate:** Tier 3 (50+ RPM)
- **Returns:** messages[] (threaded), has_more

### conversations.info
- **URL:** `GET https://slack.com/api/conversations.info`
- **Scopes:** channels:read, groups:read, im:read, mpim:read
- **Params:** channel (required), include_locale, include_num_members

### chat.postMessage
- **URL:** `POST https://slack.com/api/chat.postMessage`
- **Scopes:** chat:write (bot + user)
- **Params:** channel (required), text, blocks, thread_ts, reply_broadcast, unfurl_links, unfurl_media, metadata
- **Rate:** Tier 3 for chat methods
- **Note:** GATED in Axis — requires user confirmation per spec §6.2

### chat.update
- **URL:** `POST https://slack.com/api/chat.update`
- **Scopes:** chat:write (bot + user)
- **Params:** channel, ts, text, blocks
- **Note:** GATED — edit existing messages

### reactions.add
- **URL:** `POST https://slack.com/api/reactions.add`
- **Scopes:** reactions:write
- **Params:** channel, name (emoji name), timestamp

### reactions.list
- **URL:** `GET https://slack.com/api/reactions.list`
- **Scopes:** reactions:read
- **Params:** user, cursor, limit

### users.info
- **URL:** `GET https://slack.com/api/users.info`
- **Scopes:** users:read
- **Params:** user (required)
- **Returns:** user object with profile (display_name, real_name, email, image_*)

### users.list
- **URL:** `GET https://slack.com/api/users.list`
- **Scopes:** users:read
- **Params:** cursor, limit
- **Returns:** members[] with profile objects

### search.messages
- **URL:** `GET https://slack.com/api/search.messages`
- **Scopes:** search:read (USER TOKEN ONLY — bots cannot search)
- **Params:** query (required), count, highlight, page, sort, sort_dir
- **Note:** Requires xoxp user token, not xoxb bot token

### files.list
- **URL:** `GET https://slack.com/api/files.list`
- **Scopes:** files:read
- **Params:** channel, ts_from, ts_to, types, user, count, page

### pins.list
- **URL:** `GET https://slack.com/api/pins.list`
- **Scopes:** pins:read
- **Params:** channel (required)

## Events API

### Setup
- Subscribe via app configuration dashboard or Socket Mode
- HTTP endpoint receives POST with Content-Type: application/json
- Must respond within **3 seconds** with HTTP 200

### Verification
- **Signed secrets** (HMAC-SHA256): `v0:{timestamp}:{body}` → compare hex digest
- url_verification challenge: echo back `{"challenge": "..."}` on first configure

### Retry Policy
- 3 retries: immediate → ~1 min → ~5 min
- Headers: x-slack-retry-num, x-slack-retry-reason
- 95%+ failure rate for 60 min → subscriptions auto-disabled

### Key Event Types
- `message` (message.channels, message.groups, message.mpim, message.im)
- `app_mention` — bot was @mentioned
- `reaction_added` / `reaction_removed`
- `member_joined_channel` / `member_left_channel`
- `channel_created` / `channel_renamed` / `channel_archive`
- `file_created` / `file_deleted` / `file_shared`
- `team_join` — new user joined workspace

### Rate Limit
- 30,000 events per workspace per app per 60 minutes
- Exceeded → `app_rate_limited` events

## OAuth Scopes for Axis

### Bot Scopes (what we request during OAuth)
```
channels:history    — read public channel messages
channels:read       — list public channels
chat:write          — post messages (GATED)
groups:history      — read private channel messages
groups:read         — list private channels
im:history          — read DMs
im:read             — list DMs
reactions:read      — read reactions
reactions:write     — add reactions (GATED)
users:read          — read user profiles
users:read.email    — read user emails
files:read          — read shared files
pins:read           — read pinned messages
```

### User Scopes (optional, for search)
```
search:read         — search.messages (requires user token)
```
