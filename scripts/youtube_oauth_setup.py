#!/usr/bin/env python3
"""Perform the one-time YouTube OAuth grant and print the Actions secrets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("client_secrets", help="Downloaded Google OAuth desktop-client JSON")
    args = parser.parse_args()

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, SCOPE)
    credentials = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    data = json.loads(Path(args.client_secrets).read_text(encoding="utf-8"))
    client = data.get("installed") or data.get("web") or {}
    print("\nAdd these three values as GitHub Actions repository secrets:\n")
    print("YOUTUBE_CLIENT_ID=" + client["client_id"])
    print("YOUTUBE_CLIENT_SECRET=" + client["client_secret"])
    print("YOUTUBE_REFRESH_TOKEN=" + str(credentials.refresh_token))
    print("\nTreat the refresh token like a password. Do not commit or share it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
