# CLAUDE.md — services/notification-service

Node/Fastify. APNs (iOS), FCM (Android), Resend (email), in-app feed writes. Spec §8.2, §8.3.

## Why Node and not Python

APNs and FCM have mature, well-maintained Node SDKs (`@parse/node-apn`, `firebase-admin`). Python equivalents exist but are less stable. This is the one service where Node wins on ecosystem maturity.

## Responsibilities

- Send push notifications (APNs + FCM) with rich inline action buttons
- Send transactional email via Resend
- Manage device token registration (store in Postgres `user_devices`)
- Throttle notifications per spec §6.3 (max 5 proactive surfaces/day by default)

## Not responsibilities

- Do not decide *what* to notify — proactive-monitor decides, we just deliver.
- Do not write to the in-app feed — that's persisted by proactive-monitor in Postgres.

## Endpoints

| Path | Method | Body |
|---|---|---|
| `/healthz` | GET | — |
| `/push` | POST | `{userId, title, body, actions?}` |
| `/email` | POST | `{to, subject, html, replyTo?}` |
| `/devices/register` | POST | `{userId, platform, token}` |
| `/devices/revoke` | POST | `{token}` |

## Layout

```
src/
├── index.ts
├── config.ts         zod-validated env
├── push/
│   ├── apns.ts       APNs provider
│   └── fcm.ts        Firebase Cloud Messaging
├── email/
│   └── resend.ts
├── feed/             (deprecated — feed writes moved to proactive-monitor)
└── routes/
    ├── push.ts
    ├── email.ts
    └── devices.ts
```

## Dev

```bash
cd services/notification-service
pnpm dev                                    # starts on :8005
PORT=8005 pnpm dev                          # explicit port
```

In local dev, email goes to Mailhog at `http://localhost:8025` via SMTP. Push notifications silently no-op unless APNs/FCM creds are set.

## Don't

- Don't ship actual notifications from local dev without creds. Log-only is fine.
- Don't write to Postgres from here yet — the feed table is owned by proactive-monitor.
- Don't add WebPush until Phase 3.
