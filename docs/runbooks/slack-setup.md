# Slack App Setup — One-time Platform Configuration

**Time:** 2 minutes. You do this once. Every Axis user after that just clicks "Connect."

---

## Step 1: Create the app from manifest (30 seconds)

1. Open **https://api.slack.com/apps?new_app=1**
2. Choose **"From an app manifest"**
3. Pick your Slack workspace
4. Paste the contents of `infra/slack-app-manifest.yaml`
5. Click **Create**

That's it — all scopes, redirect URLs, bot user, and event subscriptions are pre-configured by the manifest. No manual checkbox clicking.

## Step 2: Copy 3 values into .env (30 seconds)

On the app's **Basic Information** page, copy:

```
SLACK_CLIENT_ID=<App Credentials → Client ID>
SLACK_CLIENT_SECRET=<App Credentials → Client Secret>
SLACK_SIGNING_SECRET=<App Credentials → Signing Secret>
```

Paste them into your `.env` file (or Railway environment variables for production).

## Step 3: Restart connector-manager (10 seconds)

```bash
# Local dev — touch triggers the --reload watcher
touch services/connector-manager/app/main.py

# Production — redeploy the service
railway up -s connector-manager
```

## Done

Every user can now click **Connect Slack** on the /connections page. They'll see a popup asking "Allow Axis to access your workspace?" — one click, done. No configuration, no scopes, no redirect URLs.

---

## For production

Before going live, update two things in the manifest (or in the Slack App Dashboard):

1. **Redirect URL**: change `http://localhost:8002/oauth/slack/callback` to your production URL (e.g. `https://api.axis.raweval.com/oauth/slack/callback`)
2. **Event subscription URL**: change `https://your-domain.com/webhooks/slack` to your production URL (e.g. `https://api.axis.raweval.com/webhooks/slack`)

## BYO credentials (enterprise feature)

Enterprise customers who need to use their own Slack App for compliance can register their own Client ID/Secret via the **Credentials** page (`/credentials`). The OAuth flow automatically resolves: project credentials → org credentials → user credentials → Axis default. This is an advanced feature — most users never touch it.
