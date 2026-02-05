---
name: setup
description: Set up X (Twitter) API authentication (OAuth 2.0 with PKCE)
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
  - WebSearch
---

# X OAuth Setup

Guide the user through setting up X API authentication. This is a one-time process.

## Step 1: Check existing settings

Read `~/.claude/x.local.md` to see if already authenticated. If the file exists and has a valid refresh token, inform the user they are already set up and ask if they want to re-authenticate.

## Step 2: X Developer App

If the user does not have credentials, walk them through creating an X Developer App:

1. Tell the user to go to https://developer.x.com/en/portal/dashboard and sign in
2. If they don't have a developer account, they need to sign up for the **Free** tier
3. Create a new project and app:
   - Go to Projects & Apps in the sidebar
   - Click "Add App" or create a new project
   - App name: anything descriptive
4. In the app settings, go to **Keys and tokens**:
   - Copy the **OAuth 2.0 Client ID** and **Client Secret**
   - These are under "OAuth 2.0 Client ID and Client Secret" section
5. In **User authentication settings**, click "Set up":
   - App permissions: **Read and write**
   - Type of App: **Web App, Automated App or Bot**
   - Callback URI: `http://localhost:9877/callback`
   - Website URL: any valid URL (e.g. https://github.com/your-username)
   - Click Save

Use AskUserQuestion to collect the Client ID and Client Secret from the user.

## Step 3: Run OAuth flow

Once you have the client_id and client_secret, run the OAuth server:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/oauth-server.py "<client_id>" "<client_secret>"
```

This will:
1. Generate a PKCE code verifier and challenge
2. Print an authorization URL and open the user's browser
3. Wait for the OAuth callback on localhost:9877
4. Exchange the authorization code for access + refresh tokens
5. Fetch the user's profile
6. Save everything to `~/.claude/x.local.md`

Tell the user to authorize the app in their browser when it opens.

## Step 4: Verify

After the script completes, read `~/.claude/x.local.md` and confirm to the user:
- Their display name and @username
- Token expiration (2 hours, auto-refreshed)
- Refresh token status

Tell them they can now use `/x:post` to publish content.

## Important

- Never display the client_secret or access_token in plain text to the user
- The settings file at `~/.claude/x.local.md` contains sensitive credentials
- Access tokens expire every 2 hours but auto-refresh using the refresh token
- Refresh tokens are valid for 6 months; re-run `/x:setup` if refresh fails
- Free tier: 1,500 posts per month
