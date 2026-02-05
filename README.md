# Claude Code X Plugin

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin for posting to X (Twitter) directly from your terminal. Supports text posts and image posts via the X API v2.

Zero external dependencies - uses only Python stdlib (`urllib`, `json`, `ssl`).

## Features

- `/x:setup` - OAuth 2.0 PKCE authentication flow with local callback server
- `/x:post` - Compose and publish posts (text, images)
- `/x:status` - Check authentication status and token health

## Installation

Clone this repo into your Claude Code plugins directory:

```bash
git clone https://github.com/rockyco/claude-x-plugin.git ~/.claude/plugins/x
```

Then restart Claude Code. The plugin will be auto-discovered.

## Setup

Run `/x:setup` in Claude Code. It will walk you through:

1. Creating an X Developer App at https://developer.x.com
2. Enabling **Pay-per-use** billing (add funds - $0.01 per post)
3. Configuring User Authentication Settings with `http://localhost:9877/callback`
4. Running the OAuth 2.0 PKCE flow to obtain and store your tokens

Credentials are stored locally in `~/.claude/x.local.md` (excluded from version control).

### Remote Terminal Setup

If you're on a remote terminal (SSH/tmux) without a GUI browser:

1. The setup will generate an authorization URL - open it on your phone/laptop
2. Authorize the app on X
3. The redirect to `localhost:9877/callback` will fail (expected)
4. Copy the **full URL** from your browser's address bar
5. Paste it back to Claude Code - the auth code will be extracted automatically

Note: Authorization codes expire in ~60 seconds, so paste quickly.

## Usage

### Post text

```
/x:post Just shipped a new feature
```

### Post with images

```
/x:post Check out these results --images /path/to/chart.png
```

### Check status

```
/x:status
```

## Authentication

This plugin uses **OAuth 2.0 with PKCE** (Proof Key for Code Exchange):

- Access tokens expire every **2 hours**
- The plugin **auto-refreshes** tokens using a refresh token before each API call
- Refresh tokens are valid for **6 months**
- If refresh fails, re-run `/x:setup`

No manual token management needed.

## Pricing

X API uses **pay-per-use** billing:

| Operation | Cost |
|-----------|------|
| Post (create) | $0.01 |
| Media upload | $0.01 |

Add funds in the X Developer Portal under Billing. $5 = 500 posts.

## Post Limits

| Account Type | Character Limit |
|-------------|----------------|
| Standard | 280 |
| Premium/X Blue | 25,000 |

## Image Constraints

- Up to **4 images** per post
- Max **5 MB** each (JPG, PNG, GIF, WEBP)
- GIFs: max 15 MB, resolution max 1280x1080

## Project Structure

```
.claude-plugin/
  plugin.json          # Plugin manifest
commands/
  setup.md             # OAuth PKCE setup workflow
  post.md              # Post creation workflow
  status.md            # Auth status check
scripts/
  oauth-server.py      # OAuth 2.0 PKCE flow with local callback server
  x-api.py             # API wrapper (posts, media upload, token refresh)
skills/
  x-api/
    SKILL.md           # X API v2 knowledge base
```

## Common Errors

- **401 Unauthorized**: Token expired and refresh failed. Re-run `/x:setup`.
- **402 Payment Required / Credits Depleted**: Add funds in the X Developer Portal Billing section.
- **403 Forbidden**: Missing scope. Check User Authentication Settings in the developer portal - ensure "Read and write" permissions.
- **429 Too Many Requests**: Rate limited. Wait and retry.

## Requirements

- Python 3.8+
- Claude Code CLI
- An X (Twitter) Developer App with pay-per-use billing enabled

## License

MIT
