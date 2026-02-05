---
name: post
description: Compose and publish a post to X (Twitter)
argument-hint: "[text or description of what to post]"
allowed-tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
  - Glob
---

# X Post

Compose and publish content to X (Twitter). Supports text and image posts.

## Step 1: Check authentication

Run this to verify credentials:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/x-api.py check-auth
```

If it fails, tell the user to run `/x:setup` first.
The token auto-refreshes, so "expired" status is usually fine - it will refresh on the next API call.

## Step 2: Determine post type

Based on the user's request and any arguments provided, determine the post type:

- **Text only**: User provides just text content
- **With images**: User provides text + image file paths (1-4 images)

If the user's intent is unclear, use AskUserQuestion to clarify.

## Step 3: Prepare content

Review the post text with the user before publishing:
- Show them the full text that will be posted
- Note the character count (280 for free accounts, 25,000 for premium)
- List any images that will be uploaded
- Ask for confirmation before publishing

## Step 4: Publish

IMPORTANT: Always write post text to a temp file and use `--text-file`. Never pass multi-line text via `--text` on the command line.

```bash
# 1. Write post text to temp file (use Write tool)
#    Write to: /tmp/x_post.txt

# 2. Run the appropriate command with --text-file:
```

### Text only:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/x-api.py post-text --text-file /tmp/x_post.txt
```

### With images (1-4):
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/x-api.py post-image --text-file /tmp/x_post.txt --images "/path/to/img1.png" "/path/to/img2.png"
```

## Step 5: Confirm

After successful posting:
1. Tell the user the tweet ID and URL (from script output)
2. The URL format is: `https://x.com/{username}/status/{tweet_id}`

## Important notes

- Free tier: 280 character limit, 1,500 posts/month
- Premium/X Blue: 25,000 character limit
- Images: up to 4 per post, max 5MB each (JPG, PNG, GIF, WEBP)
- Always use absolute paths for image files
- Always show the user the full post content and ask for confirmation before publishing
- Always use --text-file instead of --text to avoid shell quoting issues
- Access tokens auto-refresh; if refresh fails, run `/x:setup` again
