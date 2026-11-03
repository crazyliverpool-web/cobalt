#!/usr/bin/env python3
"""First-run setup: Google OAuth flow (opens browser once), creates the
Google Sheet if needed, and writes .env with the resulting config.
Run once manually before enabling the LaunchAgent: python3 setup.py
"""
import os
import sys

import sheets_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")


def main():
    print("Starting Google OAuth flow - your browser will open now...")
    creds = sheets_client.get_credentials()
    print("OAuth OK. Token saved.")

    existing_id = None
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH, encoding="utf-8"):
            if line.startswith("GOOGLE_SPREADSHEET_ID="):
                existing_id = line.split("=", 1)[1].strip() or None

    spreadsheet_id = sheets_client.ensure_spreadsheet(
        creds, existing_id, title="YouTube Digest"
    )

    recipient = os.environ.get("DIGEST_RECIPIENT_EMAIL") or input("Digest recipient email: ").strip()

    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write(f"GOOGLE_SPREADSHEET_ID={spreadsheet_id}\n")
        f.write(f"DIGEST_RECIPIENT_EMAIL={recipient}\n")

    print(f"\nSetup complete.")
    print(f"Sheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")
    print(f"Digest recipient: {recipient}")
    print(f"\nTest it now with: python3 digest.py --dry-run")


if __name__ == "__main__":
    main()
