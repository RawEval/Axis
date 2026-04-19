from __future__ import annotations

from axis_common import AxisBaseSettings


class Settings(AxisBaseSettings):
    service_name: str = "axis-connector-manager"

    # Where to redirect the user after an OAuth dance
    web_app_url: str = "http://localhost:3001"

    token_encryption_key: str = "change-me-32-bytes-base64"

    # Background ingestion
    connector_sync_enabled: bool = True

    # Notion
    notion_client_id: str = ""
    notion_client_secret: str = ""
    notion_oauth_redirect_uri: str = "http://localhost:8002/oauth/notion/callback"
    notion_version: str = "2022-06-28"
    notion_mcp_url: str = "https://mcp.notion.com/mcp"

    # Slack
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_signing_secret: str = ""
    slack_oauth_redirect_uri: str = "http://localhost:8002/oauth/slack/callback"
    slack_bot_scopes: str = (
        "channels:history,channels:read,chat:write,groups:history,groups:read,"
        "im:history,im:read,reactions:read,reactions:write,users:read,"
        "users:read.email,pins:read,files:read"
    )

    # Google — one OAuth client covers Gmail + Drive; each tool has its own
    # redirect URI so the callback route knows which connector to persist.
    google_client_id: str = ""
    google_client_secret: str = ""
    gmail_oauth_redirect_uri: str = "http://localhost:8002/oauth/gmail/callback"
    gdrive_oauth_redirect_uri: str = "http://localhost:8002/oauth/gdrive/callback"

    # GitHub
    github_client_id: str = ""
    github_client_secret: str = ""
    github_oauth_redirect_uri: str = "http://localhost:8002/oauth/github/callback"
    github_webhook_secret: str = ""


settings = Settings()
