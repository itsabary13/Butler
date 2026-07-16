"""One-time, interactive Google Calendar OAuth setup. Run this manually
once, never as part of the running service, never automated.

Before running:
1. Create a Google Cloud project, enable the Calendar API.
2. Configure the OAuth consent screen (External, scope: calendar.events
   only). IMPORTANT: set publishing status to "In production", not
   "Testing" — testing-mode refresh tokens silently expire after 7 days,
   which would quietly break calendar creation a week in with no obvious
   error. You'll see an "unverified app" warning during consent below;
   that's expected for a personal single-user app and safe to click
   through.
3. Create an OAuth Client ID of type "Desktop app". Note the client ID
   and client secret.

Usage:
    GOOGLE_OAUTH_CLIENT_ID=... GOOGLE_OAUTH_CLIENT_SECRET=... python scripts/google_oauth_setup.py

Prints the resulting refresh token — paste it into .env as
GOOGLE_OAUTH_REFRESH_TOKEN. This script is never run as part of the
request path; the running service only ever uses the refresh token to
mint short-lived access tokens.
"""

import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def main() -> int:
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET env vars first.")
        return 1

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    credentials = flow.run_local_server(port=0)

    print("\nSuccess. Add this to backend/voice-relay/.env:\n")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={credentials.refresh_token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
