---
name: status
description: Check X (Twitter) authentication status and token health
allowed-tools:
  - Bash
  - Read
---

# X Status

Check the current X authentication status.

## Action

Run the auth check:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/x-api.py check-auth
```

Also read `~/.claude/x.local.md` for the full settings.

## Report to user

Tell the user:
- Whether they are authenticated
- Their display name and @username
- Token status (minutes until expiration, or "expired - will auto-refresh")
- Whether a refresh token is present
- If the refresh token is missing, tell them to run `/x:setup` to re-authenticate

Do NOT display the access_token or client_secret values.
