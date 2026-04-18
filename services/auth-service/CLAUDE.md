# CLAUDE.md — services/auth-service

Owns user identity. Register, login, JWT issuance, session refresh, password reset (later). **This is the only service that issues JWTs.** Read `services/CLAUDE.md` first.

## Responsibilities

- User register with bcrypt password hashing
- User login returning a signed JWT
- JWT verification and `/me` endpoint
- Session refresh (to be added)
- Password reset flow (to be added)
- Integration with Supabase auth (Phase 2 — currently self-hosted)

## Not responsibilities

- Do not verify JWTs for other services' routes. Each service has its own `get_current_user_id` dependency that reads the shared secret.
- Do not handle connector OAuth. That is connector-manager.
- Do not own session history or audit log of logins. That lives in Postgres and is queried by the eval / ops surfaces.

## Endpoints

| Path | Method | Body | Returns |
|---|---|---|---|
| `/healthz` | GET | — | `{status, service}` |
| `/register` | POST | `{email, password, name?}` | `{user_id, access_token, token_type}` |
| `/login` | POST | `{email, password}` | `{access_token, token_type}` |
| `/me` | GET | — (Bearer token) | `{id, email, name, plan, created_at}` |

## Data model

Uses the `users` table from `infra/docker/init/postgres/001_init.sql`:

```sql
users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  plan TEXT NOT NULL DEFAULT 'free',
  settings JSONB,
  usage JSONB,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
```

We add a `password_hash` column via migration 002 (first thing this service does).

## Security

- **Passwords** hashed with bcrypt (via passlib) — cost factor 12.
- **JWT** signed HS256 with `JWT_SECRET`. Expiry = 60 minutes by default.
- **JWT claims:** `sub` (user_id), `email`, `plan`, `iat`, `exp`. Nothing sensitive.
- **Never return the password hash** in any response. Ever.
- **Never log** the password field, even at debug level.
- **Rate limiting** on login — to be added via Redis token bucket.

## Layout

```
app/
├── main.py        FastAPI app, lifespan
├── config.py      Settings (jwt_secret, postgres_url, jwt_expiry_minutes)
├── db.py          asyncpg pool
├── security.py    hash_password, verify_password, create_access_token, decode_token
├── models.py      Pydantic request/response models
├── repositories/
│   └── users.py   UserRepository (create, get_by_email, get_by_id)
└── routes/
    ├── health.py
    └── auth.py    register, login, me
```

## Dev

```bash
cd services/auth-service
uv sync
uv run uvicorn app.main:app --reload --port 8006
open http://localhost:8006/docs
```

## Don't

- Don't store passwords in plaintext, even transiently.
- Don't return JWT in a URL query string. Body only.
- Don't add "forgot password" magic links via email until Resend is wired up in notification-service AND rate-limiting is in place.
- Don't trust email uniqueness from the client — always check the DB.
- Don't issue JWTs without an expiry.
