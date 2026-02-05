#!/usr/bin/env python3
"""
X (Twitter) OAuth 2.0 with PKCE local callback server.

Starts a temporary HTTP server on localhost to receive the OAuth callback,
exchanges the authorization code for an access token using PKCE,
fetches the user's profile, and writes credentials to the settings file.

Usage:
    python3 oauth-server.py <client_id> <client_secret> [--port PORT]
"""

import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import time
import urllib.parse
import urllib.request
import ssl
import webbrowser
from pathlib import Path

DEFAULT_PORT = 9877
SCOPES = "tweet.read tweet.write users.read media.write offline.access"
SETTINGS_PATH = Path.home() / ".claude" / "x.local.md"
AUTH_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"


def generate_pkce_pair():
    """Generate PKCE code_verifier and code_challenge (S256)."""
    code_verifier = secrets.token_urlsafe(64)[:128]
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def exchange_code_for_token(code, client_id, client_secret, redirect_uri, code_verifier):
    """Exchange authorization code for access + refresh tokens."""
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
        "client_id": client_id,
    }).encode()

    # Use Basic auth for confidential clients
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {credentials}",
    }

    req = urllib.request.Request(TOKEN_URL, data=data, headers=headers)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx) as resp:
        return json.loads(resp.read().decode())


def fetch_user_info(access_token):
    """Fetch the authenticated user's profile."""
    req = urllib.request.Request(
        "https://api.x.com/2/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx) as resp:
        data = json.loads(resp.read().decode())
    user = data.get("data", {})
    return user.get("id", ""), user.get("username", ""), user.get("name", "Unknown")


def save_settings(client_id, client_secret, access_token, refresh_token,
                   user_id, username, display_name, expires_in):
    """Write credentials to the settings file."""
    expires_at = int(time.time()) + expires_in

    content = f"""---
client_id: "{client_id}"
client_secret: "{client_secret}"
access_token: "{access_token}"
refresh_token: "{refresh_token}"
user_id: "{user_id}"
username: "{username}"
display_name: "{display_name}"
token_expires_at: {expires_at}
---

# X Plugin Settings

Authenticated as **{display_name}** (@{username}, ID: {user_id}).

Access token expires at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_at))}

Access tokens expire every 2 hours. The plugin auto-refreshes using the refresh token.
Refresh tokens are valid for 6 months. Re-run `/x:setup` if refresh fails.
"""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(content)


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handle the OAuth redirect callback."""

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" not in params:
            error = params.get("error", ["unknown"])[0]
            error_desc = params.get("error_description", ["No details"])[0]
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<h2>Authorization failed</h2><p>{error}: {error_desc}</p>".encode()
            )
            self.server.auth_result = {"error": error, "error_description": error_desc}
            return

        state = params.get("state", [""])[0]
        if state != self.server.expected_state:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>State mismatch - possible CSRF attack</h2>")
            self.server.auth_result = {"error": "state_mismatch"}
            return

        code = params["code"][0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<h2>Authorization successful!</h2>"
            b"<p>You can close this tab and return to Claude Code.</p>"
        )
        self.server.auth_result = {"code": code}


def run_oauth_flow(client_id, client_secret, port=DEFAULT_PORT):
    """Run the full OAuth 2.0 PKCE flow."""
    redirect_uri = f"http://localhost:{port}/callback"
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = generate_pkce_pair()

    auth_url = (
        AUTH_URL + "?" + urllib.parse.urlencode({
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": SCOPES,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })
    )

    server = http.server.HTTPServer(("localhost", port), OAuthCallbackHandler)
    server.expected_state = state
    server.auth_result = None

    print(f"OAUTH_URL={auth_url}")
    print(f"REDIRECT_URI={redirect_uri}")
    print("STATUS=waiting_for_callback")
    sys.stdout.flush()

    webbrowser.open(auth_url)

    # Handle exactly one request (the callback)
    server.handle_request()
    server.server_close()

    result = server.auth_result
    if not result or "error" in result:
        error = result.get("error", "unknown") if result else "no_response"
        desc = result.get("error_description", "") if result else ""
        print(f"ERROR={error} {desc}")
        sys.exit(1)

    code = result["code"]
    print("STATUS=exchanging_token")
    sys.stdout.flush()

    # Exchange code for tokens (with PKCE verifier)
    token_data = exchange_code_for_token(
        code, client_id, client_secret, redirect_uri, code_verifier
    )
    access_token = token_data["access_token"]
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 7200)

    print("STATUS=fetching_profile")
    sys.stdout.flush()

    # Fetch user info
    user_id, username, display_name = fetch_user_info(access_token)

    # Save settings
    save_settings(
        client_id, client_secret, access_token, refresh_token,
        user_id, username, display_name, expires_in
    )

    print(f"SUCCESS=Authenticated as {display_name} (@{username})")
    print(f"TOKEN_EXPIRES_IN={expires_in}")
    print(f"SETTINGS_PATH={SETTINGS_PATH}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="X OAuth 2.0 PKCE flow")
    parser.add_argument("client_id", help="X app Client ID")
    parser.add_argument("client_secret", help="X app Client Secret")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Callback port")
    args = parser.parse_args()

    run_oauth_flow(args.client_id, args.client_secret, args.port)
