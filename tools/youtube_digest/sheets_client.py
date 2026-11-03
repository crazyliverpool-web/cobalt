"""Google Sheets client - OAuth (Desktop app flow) + safe row writing.

Security: any cell value that starts with =, +, -, or @ gets a leading
apostrophe prefix so Google Sheets never interprets attacker-controlled
video titles/descriptions as a formula. (Codex spec review, 2026-07-08.)
"""
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_PATH = os.path.join(BASE_DIR, "data", "google_oauth_client.json")
TOKEN_PATH = os.path.join(BASE_DIR, "data", "google_oauth_token.json")
SERVICE_ACCOUNT_PATH = os.path.join(BASE_DIR, "data", "service_account.json")

VIDEO_SUMMARIES_HEADER = [
    "Published At", "Processed At", "Channel Name", "Channel ID",
    "Video Title", "Video ID", "Video URL",
    "One-line Summary", "Key Points", "Watch Recommendation",
    "Relevance Score", "Why It Matters",
]


def get_credentials():
    # Service account: no consent screen, no refresh token, never expires.
    # Preferred path once data/service_account.json exists (see for-opus/questions.md Q29).
    if os.path.exists(SERVICE_ACCOUNT_PATH):
        return ServiceAccountCredentials.from_service_account_file(
            SERVICE_ACCOUNT_PATH, scopes=SCOPES
        )

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    return creds


def _safe_cell(value):
    """Prefix cells starting with formula-trigger characters."""
    if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def ensure_spreadsheet(creds, spreadsheet_id: str | None, title: str) -> str:
    """Create a new spreadsheet if spreadsheet_id is None, else validate it exists.
    Ensures the 'Video Summaries' tab exists with the correct header row."""
    service = build("sheets", "v4", credentials=creds)

    if not spreadsheet_id:
        body = {
            "properties": {"title": title},
            "sheets": [{"properties": {"title": "Video Summaries"}}],
        }
        result = service.spreadsheets().create(body=body).execute()
        spreadsheet_id = result["spreadsheetId"]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="Video Summaries!A1",
            valueInputOption="RAW",
            body={"values": [VIDEO_SUMMARIES_HEADER]},
        ).execute()
        print(f"Created new spreadsheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit")

    return spreadsheet_id


def append_video_row(creds, spreadsheet_id: str, row: dict) -> None:
    service = build("sheets", "v4", credentials=creds)
    values = [_safe_cell(row.get(col, "")) for col in [
        "published_at", "processed_at", "channel_name", "channel_id",
        "video_title", "video_id", "video_url",
        "one_line_summary", "key_points", "watch_recommendation",
        "relevance_score", "why_it_matters",
    ]]
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="Video Summaries!A:A",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [values]},
    ).execute()
