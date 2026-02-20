#!/usr/bin/env python3
"""
X (Twitter) API v2 wrapper for posting content.

Supports: text posts, image posts (up to 4 images).
Uses only Python stdlib (urllib, json, ssl) - no external dependencies.
Includes automatic token refresh when access token expires.

Usage:
    python3 x-api.py post-text --text "Hello X"
    python3 x-api.py post-text --text-file /tmp/x_post.txt
    python3 x-api.py post-image --text "Check this" --images /path/to/img.png
    python3 x-api.py upload-media --file /path/to/image.png
    python3 x-api.py check-auth
"""

import argparse
import base64
import json
import mimetypes
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

SETTINGS_PATH = Path.home() / ".claude" / "x.local.md"
API_BASE = "https://api.x.com/2"
TOKEN_URL = "https://api.x.com/2/oauth2/token"


def load_settings():
    """Load settings from the YAML frontmatter in x.local.md."""
    if not SETTINGS_PATH.exists():
        print("ERROR=Settings file not found. Run /x:setup first.", file=sys.stderr)
        sys.exit(1)

    content = SETTINGS_PATH.read_text()
    if not content.startswith("---"):
        print("ERROR=Invalid settings file format.", file=sys.stderr)
        sys.exit(1)

    frontmatter = content.split("---")[1]
    settings = {}
    for line in frontmatter.strip().split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, value = line.partition(":")
            value = value.strip().strip('"').strip("'")
            settings[key.strip()] = value

    required = ["access_token", "client_id", "client_secret"]
    for key in required:
        if key not in settings or not settings[key]:
            print(f"ERROR=Missing {key} in settings. Run /x:setup first.",
                  file=sys.stderr)
            sys.exit(1)

    return settings


def refresh_access_token(settings):
    """Refresh the access token using the refresh token."""
    refresh_token = settings.get("refresh_token", "")
    if not refresh_token:
        print("ERROR=No refresh token. Run /x:setup to re-authenticate.",
              file=sys.stderr)
        sys.exit(1)

    client_id = settings["client_id"]
    client_secret = settings["client_secret"]

    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }).encode()

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {credentials}",
    }

    req = urllib.request.Request(TOKEN_URL, data=data, headers=headers)
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            token_data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"ERROR=Token refresh failed: {e.code} {e.reason}", file=sys.stderr)
        if error_body:
            print(f"DETAILS={error_body}", file=sys.stderr)
        print("ERROR=Run /x:setup to re-authenticate.", file=sys.stderr)
        sys.exit(1)

    new_access = token_data["access_token"]
    new_refresh = token_data.get("refresh_token", refresh_token)
    expires_in = token_data.get("expires_in", 7200)
    expires_at = int(time.time()) + expires_in

    # Update the settings file with new tokens
    content = SETTINGS_PATH.read_text()
    parts = content.split("---")
    if len(parts) >= 3:
        frontmatter = parts[1]
        rest = "---".join(parts[2:])

        # Replace tokens in frontmatter
        new_lines = []
        for line in frontmatter.strip().split("\n"):
            if line.strip().startswith("access_token:"):
                new_lines.append(f'access_token: "{new_access}"')
            elif line.strip().startswith("refresh_token:"):
                new_lines.append(f'refresh_token: "{new_refresh}"')
            elif line.strip().startswith("token_expires_at:"):
                new_lines.append(f"token_expires_at: {expires_at}")
            else:
                new_lines.append(line)

        new_content = "---\n" + "\n".join(new_lines) + "\n---" + rest
        SETTINGS_PATH.write_text(new_content)

    settings["access_token"] = new_access
    settings["refresh_token"] = new_refresh
    settings["token_expires_at"] = str(expires_at)

    print("TOKEN_REFRESHED=true", file=sys.stderr)
    return settings


def ensure_valid_token(settings):
    """Check token expiration and refresh if needed."""
    expires_at = int(settings.get("token_expires_at", 0))
    # Refresh if token expires within 5 minutes
    if expires_at and time.time() > (expires_at - 300):
        print("TOKEN_STATUS=expired, refreshing...", file=sys.stderr)
        return refresh_access_token(settings)
    return settings


def api_request(method, url, headers, data=None, binary_data=None,
                content_type=None):
    """Make an API request and return the response."""
    ctx = ssl.create_default_context()

    if binary_data is not None:
        req = urllib.request.Request(url, data=binary_data, headers=headers,
                                    method=method)
    elif data is not None:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode(), headers=headers, method=method
        )
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            response_headers = dict(resp.headers)
            body = resp.read().decode()
            return {
                "status": resp.status,
                "headers": response_headers,
                "body": json.loads(body) if body else {},
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"ERROR=API request failed: {e.code} {e.reason}", file=sys.stderr)
        if error_body:
            print(f"DETAILS={error_body}", file=sys.stderr)
        sys.exit(1)


def get_api_headers(access_token):
    """Return standard X API v2 headers."""
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }


def upload_media(access_token, file_path):
    """Upload media to X and return the media ID.

    Uses v2 JSON endpoint with base64-encoded media field.
    The v1.1 multipart endpoint requires OAuth 1.0a and returns 403
    with OAuth 2.0 Bearer tokens.
    """
    file_path = Path(file_path).resolve()
    if not file_path.exists():
        print(f"ERROR=File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()
    file_size = len(file_bytes)

    if file_size > 5 * 1024 * 1024:
        print(f"ERROR=File too large ({file_size} bytes). Max 5MB for images.",
              file=sys.stderr)
        sys.exit(1)

    url = f"{API_BASE}/media/upload"
    media_b64 = base64.b64encode(file_bytes).decode()

    payload = {
        "media": media_b64,
        "media_category": "tweet_image",
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    body = json.dumps(payload).encode()

    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            result = json.loads(resp.read().decode())
            media_data = result.get("data", result)
            media_id = str(media_data.get("id",
                                          media_data.get("media_id_string",
                                                         media_data.get("media_id", ""))))
            return media_id
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"ERROR=Media upload failed: {e.code} {e.reason}", file=sys.stderr)
        if error_body:
            print(f"DETAILS={error_body}", file=sys.stderr)
        sys.exit(1)


def create_post(access_token, text, media_ids=None):
    """Create an X post."""
    post_data = {"text": text}

    if media_ids:
        post_data["media"] = {"media_ids": media_ids}

    headers = get_api_headers(access_token)
    resp = api_request("POST", f"{API_BASE}/tweets", headers, data=post_data)

    tweet_data = resp["body"].get("data", {})
    tweet_id = tweet_data.get("id", "")
    return tweet_id


def resolve_text(args):
    """Get post text from --text or --text-file argument."""
    if hasattr(args, "text_file") and args.text_file:
        p = Path(args.text_file)
        if not p.exists():
            print(f"ERROR=Text file not found: {p}", file=sys.stderr)
            sys.exit(1)
        return p.read_text().strip()
    return args.text


def cmd_check_auth(args):
    """Check authentication status."""
    settings = load_settings()
    expires_at = int(settings.get("token_expires_at", 0))
    remaining = expires_at - int(time.time())
    minutes_left = remaining // 60

    print("AUTHENTICATED=true")
    print(f"USER_ID={settings.get('user_id', 'unknown')}")
    print(f"USERNAME={settings.get('username', 'unknown')}")
    print(f"DISPLAY_NAME={settings.get('display_name', 'Unknown')}")

    if remaining > 0:
        print(f"TOKEN_MINUTES_LEFT={minutes_left}")
    else:
        print("TOKEN_STATUS=expired (will auto-refresh on next API call)")

    refresh = settings.get("refresh_token", "")
    print(f"REFRESH_TOKEN={'present' if refresh else 'missing'}")


def cmd_post_text(args):
    """Post text-only content."""
    settings = load_settings()
    settings = ensure_valid_token(settings)
    text = resolve_text(args)

    if len(text) > 25000:
        print(f"WARNING=Text is {len(text)} chars. X limit is 25,000 for premium, "
              "280 for free accounts.", file=sys.stderr)

    tweet_id = create_post(settings["access_token"], text)
    print("SUCCESS=Post created")
    print(f"TWEET_ID={tweet_id}")
    username = settings.get("username", "")
    if username and tweet_id:
        print(f"URL=https://x.com/{username}/status/{tweet_id}")


def cmd_post_image(args):
    """Post with images."""
    settings = load_settings()
    settings = ensure_valid_token(settings)
    text = resolve_text(args)

    if len(args.images) > 4:
        print("ERROR=X allows at most 4 images per post.", file=sys.stderr)
        sys.exit(1)

    media_ids = []
    for i, img_path in enumerate(args.images):
        print(f"UPLOADING={i+1}/{len(args.images)} {img_path}", file=sys.stderr)
        media_id = upload_media(settings["access_token"], img_path)
        media_ids.append(media_id)
        print(f"MEDIA_ID={media_id}", file=sys.stderr)

    tweet_id = create_post(settings["access_token"], text, media_ids=media_ids)
    print(f"SUCCESS=Post with {len(media_ids)} image(s) created")
    print(f"TWEET_ID={tweet_id}")
    username = settings.get("username", "")
    if username and tweet_id:
        print(f"URL=https://x.com/{username}/status/{tweet_id}")


def cmd_upload_media(args):
    """Upload media and return its ID."""
    settings = load_settings()
    settings = ensure_valid_token(settings)
    media_id = upload_media(settings["access_token"], args.file)
    print(f"MEDIA_ID={media_id}")


def cmd_refresh_token(args):
    """Manually refresh the access token."""
    settings = load_settings()
    settings = refresh_access_token(settings)
    print("SUCCESS=Token refreshed")
    expires_at = int(settings.get("token_expires_at", 0))
    minutes_left = (expires_at - int(time.time())) // 60
    print(f"TOKEN_MINUTES_LEFT={minutes_left}")


def main():
    parser = argparse.ArgumentParser(description="X API v2 wrapper")
    sub = parser.add_subparsers(dest="command", required=True)

    # check-auth
    sub.add_parser("check-auth", help="Check authentication status")

    # refresh-token
    sub.add_parser("refresh-token", help="Manually refresh the access token")

    # post-text
    p = sub.add_parser("post-text", help="Create a text-only post")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="Post text content")
    g.add_argument("--text-file", help="Path to file containing post text")

    # post-image
    p = sub.add_parser("post-image", help="Create a post with images")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--text", help="Post text content")
    g.add_argument("--text-file", help="Path to file containing post text")
    p.add_argument("--images", nargs="+", required=True,
                   help="Paths to image files (1-4)")

    # upload-media
    p = sub.add_parser("upload-media", help="Upload media and get its ID")
    p.add_argument("--file", required=True, help="Path to media file")

    args = parser.parse_args()
    cmd_map = {
        "check-auth": cmd_check_auth,
        "post-text": cmd_post_text,
        "post-image": cmd_post_image,
        "upload-media": cmd_upload_media,
        "refresh-token": cmd_refresh_token,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
