# BYO Credentials — bring your own OAuth client

**Decision date:** 2026-04-16
**Status:** Active
**ADR number:** 003
**Inspired by:** [Pipedream — Bring your own OAuth clients](https://pipedream.com/blog/bring-your-own-oauth-clients/)

## Context

Every agent platform we surveyed (Lindy, Pipedream, Zapier, n8n-cloud, Make, Relay) uses one of three credential models:

| Model | Who owns the OAuth app | Who grants access | Used by |
|---|---|---|---|
| **Platform-only** | The vendor | User grants vendor's app | Lindy, Zapier, n8n-cloud |
| **BYO-only** | The user (admin-supplied) | User grants user's own app | n8n self-hosted |
| **Hybrid (BYO optional)** | Vendor default, user can override | User grants their chosen app | **Pipedream**, Make |

The hybrid pattern is the only one that scales across both "Sarah the founder wants to connect her personal Gmail in 10 seconds" AND "Alex the VP eng at a Series C will not paste their workspace Slack token into any third-party app whose security review they haven't done."

**Axis ships the hybrid pattern.** By default, a user connects using Axis's OAuth apps (fastest path). If they want to use their own OAuth client (for compliance, for scope-limiting, for audit), they can.

## User experience

### Default path (10 seconds)

1. User clicks "Connect Notion"
2. Redirected to Notion's OAuth consent screen — Axis's client_id in the URL
3. User approves, redirected back, token encrypted and stored
4. Done

### BYO path (for security-conscious users)

1. User opens Settings → Credentials → Notion
2. Pastes **their own** `client_id` and `client_secret` (from https://www.notion.so/my-integrations)
3. Clicks "Save"
4. Next time they click "Connect Notion", Axis uses their app's `client_id` and their redirect URI, sends the OAuth flow through *their* app, token is still encrypted and stored in Axis's DB — but the consent screen shows *their* integration, not ours

**Key point:** the token storage is identical. What differs is *which OAuth client signed the authorization request*. From the provider's audit log, a BYO connection shows up as "Acme Corp's internal integration," not "Axis." This is what enterprises need.

## Schema

```sql
CREATE TABLE user_oauth_apps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_secret_encrypted BYTEA NOT NULL,
    redirect_uri TEXT,
    extra JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, tool_name)
);
```

The `client_secret_encrypted` uses the same AES-256-GCM key as `connectors.auth_token_encrypted` (`TOKEN_ENCRYPTION_KEY`).

**Note:** BYO client credentials are per **user**, not per **project**. A user has one set of Notion dev credentials and uses them across all their projects. This matches the mental model (you create ONE integration in Notion's dev console and reuse it).

## OAuth flow — resolver pattern

Every connector's OAuth module exposes:

```python
def build_authorize_url(*, state: str, client_id: str, redirect_uri: str) -> str: ...
async def exchange_code(*, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict: ...
```

Note both arguments are parameterized. At request time, `connector-manager` calls:

```python
app = await oauth_apps_repo.get(user_id, tool="notion")
if app is not None:
    client_id, client_secret, redirect_uri = app["client_id"], decrypt(app["client_secret_encrypted"]), app["redirect_uri"]
else:
    client_id, client_secret, redirect_uri = settings.notion_client_id, settings.notion_client_secret, settings.notion_oauth_redirect_uri
```

The rest of the flow is identical whether BYO is used or not.

## API surface

```
PUT    /oauth-apps/{tool}         { client_id, client_secret, redirect_uri? }
GET    /oauth-apps                 list user's custom apps (secrets redacted)
GET    /oauth-apps/{tool}          single tool (secret redacted)
DELETE /oauth-apps/{tool}          forget custom app; fall back to Axis default
```

All routes are authed. Writing a new client_secret encrypts immediately; reads return `client_secret_encrypted: "[redacted]"` and an `is_custom: true` flag.

## Rotation

When the user updates the client_secret, **existing stored OAuth tokens obtained with the old client continue to work** — providers validate tokens against the grant, not against your current client_secret. We simply use the new secret for the next `exchange_code` call.

## Revocation

Deleting a custom app does NOT disconnect existing connectors. It just means the next `connect` flow uses the Axis default app. If the user wants to fully disconnect, they use the connector's disconnect button (see `docs/runbooks/disconnect-flow.md`).

## Security notes

- BYO credentials are per-user, never global
- Client secrets are encrypted at rest (AES-256-GCM), same key as connector tokens
- Secrets are never returned in responses — only `[redacted]` + `is_custom`
- The `redirect_uri` override is validated server-side to match a known safe pattern (must be HTTPS in prod, or localhost in dev)
- BYO client credentials do not cross project boundaries — they are always user-scoped

## Not in scope

- OAuth **dynamic client registration** (RFC 7591). Only Notion MCP supports this today among our P1 tools; not worth the plumbing.
- **Service account** flows (Google Workspace domain-wide delegation). Phase 3 enterprise feature.
- **Per-project BYO credentials**. Phase 2 when we have shared projects.

## See also

- `projects-model.md`
- `../architecture/prompt-flow.md`
- [Pipedream's BYO pattern](https://pipedream.com/blog/bring-your-own-oauth-clients/)
- [n8n credential overrides](https://docs.n8n.io/integrations/builtin/credentials/)
