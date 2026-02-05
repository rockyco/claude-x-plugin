---
name: x-api
description: Use when composing X (Twitter) posts, formatting content for X, or troubleshooting X API issues. Provides knowledge of X API v2 conventions, post formatting best practices, and content guidelines.
---

# X API Knowledge

## Post Creation

X API v2 endpoint for creating posts:
```
POST https://api.x.com/2/tweets
Authorization: Bearer {access_token}
Content-Type: application/json

{"text": "Hello world"}
```

### With media:
```json
{
  "text": "Check this out",
  "media": {
    "media_ids": ["1234567890"]
  }
}
```

## Authentication

X uses **OAuth 2.0 with PKCE** (Proof Key for Code Exchange):
- Authorization URL: `https://x.com/i/oauth2/authorize`
- Token URL: `https://api.x.com/2/oauth2/token`
- Access tokens expire in **2 hours**
- Refresh tokens valid for **6 months** (requires `offline.access` scope)
- The plugin auto-refreshes tokens before each API call

Required scopes: `tweet.read tweet.write users.read media.write offline.access`

## Media Upload

Single-shot upload to `POST https://api.x.com/2/media/upload`:
- Format: `multipart/form-data`
- Fields: `media_data` (base64), `media_category` ("tweet_image")
- Returns `data.id` (media ID string)

### Constraints
- Max 4 images per post
- Images: max 5 MB (JPG, PNG, GIF, WEBP)
- GIFs: max 15 MB, resolution max 1280x1080
- Videos: max 512 MB, 0.5-140 seconds (requires chunked upload)

## Post Content Guidelines

- Free tier: **280 characters** per post
- Premium/X Blue: **25,000 characters**
- Hashtags: use sparingly, 2-3 max
- @mentions count toward character limit
- URLs are shortened to 23 characters by t.co
- Line breaks are preserved

## Free Tier Limits

- 1,500 posts per month
- Write-only (cannot read timelines)
- Media upload available with `media.write` scope
- Rate limit: measured in 24-hour windows

## Common Errors

- **401 Unauthorized**: Token expired. The plugin auto-refreshes, but if refresh fails, re-run `/x:setup`.
- **403 Forbidden**: Missing required scope or app permissions. Check User Authentication Settings in the developer portal.
- **429 Too Many Requests**: Rate limited. Wait and retry.
- **400 Bad Request**: Invalid payload. Check character count and media IDs.

## Reply and Quote Posts

### Reply:
```json
{
  "text": "Great point!",
  "reply": {"in_reply_to_tweet_id": "1234567890"}
}
```

### Quote:
```json
{
  "text": "This is interesting",
  "quote_tweet_id": "1234567890"
}
```

## Scripts Location

The X API scripts are at `${CLAUDE_PLUGIN_ROOT}/scripts/`:
- `oauth-server.py` - OAuth 2.0 PKCE flow with local callback server and auto token refresh
- `x-api.py` - Post creation, media upload, auth check, token refresh
