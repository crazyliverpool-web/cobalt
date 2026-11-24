#!/usr/bin/env python3
"""Daily YouTube digest pipeline.

1. Read enabled channels from config/channels.json
2. Fetch each channel's recent uploads via public RSS (no API key)
3. Skip anything already in state.json (dedup by video ID)
4. For new videos: fetch Thai transcript (yt-dlp), summarize (Claude API)
5. Append rows to the Google Sheet
6. Send one Gmail digest if any new videos were processed
7. Save updated state

Run manually:  python3 digest.py [--dry-run]

Exit codes: 0 ok (heartbeat written), 1 missing env, 2 network never came up (netwait) or RSS fetch failed for EVERY channel
(error, not a quiet day — heartbeat NOT written so watchdog/bots_doctor flag it; 2026-10-10/11
both channels 404'd and the bot used to log "No new videos" + status ok). Partial RSS failure
proceeds and prints "WARN: partial RSS failure ..." (surfaced by tools/bots_doctor.py).
NOTE: step 6 is LINE + Notion now, not Gmail.
"""
import os
import sys
import json
import argparse
import time
import urllib.error
from datetime import datetime, timezone

import state
import rss_utils
import transcript_utils
import summarize
import sheets_client
import line_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.dirname(BASE_DIR)
sys.path.insert(0, TOOLS_DIR)
import notion_helper  # noqa: E402 (parent dir, path set above)
import netwait  # noqa: E402

# Hosts that must be reachable before we start (DarkWake: Mac awake, Wi-Fi not yet) — see netwait.py
NET_HOSTS = ("www.youtube.com", "api.line.me", "api.anthropic.com", "api.notion.com", "sheets.googleapis.com")

CHANNELS_PATH = os.path.join(BASE_DIR, "config", "channels.json")
ENV_PATH = os.path.join(BASE_DIR, ".env")
MAX_VIDEOS_PER_RUN = 10
MAX_VIDEOS_PER_CHANNEL_SCAN = 5
RSS_ATTEMPTS = 2       # YouTube RSS 404s/5xx intermittently — one retry after a pause
RSS_BACKOFF_S = 20


def _retryable(e: Exception) -> bool:
    if isinstance(e, urllib.error.HTTPError):
        return e.code in (404, 408, 429) or e.code >= 500
    return isinstance(e, (urllib.error.URLError, TimeoutError, ConnectionError))


def fetch_with_retry(ch: dict):
    """Return entries, or raise the last error after RSS_ATTEMPTS tries."""
    for attempt in range(1, RSS_ATTEMPTS + 1):
        try:
            return rss_utils.fetch_recent_videos(ch["channel_id"], limit=MAX_VIDEOS_PER_CHANNEL_SCAN)
        except Exception as e:  # noqa: BLE001
            if attempt == RSS_ATTEMPTS or not _retryable(e):
                raise
            print(f"  retry RSS for {ch['name']} in {RSS_BACKOFF_S}s ({e})")
            time.sleep(RSS_BACKOFF_S)


def load_env():
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def load_channels() -> list[dict]:
    with open(CHANNELS_PATH, encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't write to Sheet or send email")
    args = parser.parse_args()

    netwait.hold_awake()
    load_env()
    spreadsheet_id = os.environ.get("GOOGLE_SPREADSHEET_ID")
    line_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    line_user = os.environ.get("LINE_USER_ID")
    if not spreadsheet_id or not line_token or not line_user:
        print("ERROR: missing GOOGLE_SPREADSHEET_ID / LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID in .env")
        sys.exit(1)

    try:
        netwait.wait_for_network(NET_HOSTS)
    except netwait.NetworkUnavailable as e:
        # same outcome as "RSS failed for every channel": saw nothing -> exit 2, no heartbeat
        print(f"ERROR: {e} — not a quiet day. Exiting 2 without heartbeat.")
        sys.exit(2)

    channels = [c for c in load_channels() if c.get("enabled", True)]
    st = state.load_state()

    new_videos = []
    failed = []
    for ch in channels:
        try:
            entries = fetch_with_retry(ch)
        except Exception as e:
            print(f"WARN: RSS fetch failed for {ch['name']}: {e}")
            failed.append(ch["name"])
            continue
        for entry in entries:
            if state.is_seen(st, ch["channel_id"], entry.video_id):
                continue
            new_videos.append((ch, entry))

    if channels and len(failed) == len(channels):
        # Saw nothing at all — must not look like a quiet day. Exit before the heartbeat.
        print(f"ERROR: RSS fetch failed for all {len(channels)} channels — not a quiet day. "
              "Exiting 2 without heartbeat.")
        sys.exit(2)
    if failed:
        print(f"WARN: partial RSS failure {len(failed)}/{len(channels)} channels: {', '.join(failed)}")

    new_videos = new_videos[:MAX_VIDEOS_PER_RUN]

    if not new_videos:
        print("No new videos. Exiting cleanly.")
        return

    print(f"Found {len(new_videos)} new video(s).")

    creds = None if args.dry_run else sheets_client.get_credentials()
    processed_rows = []

    for ch, entry in new_videos:
        print(f"Processing: [{ch['name']}] {entry.title}")
        transcript = transcript_utils.fetch_transcript(entry.url)
        if not transcript or len(transcript) < 200:
            print("  -> no usable transcript, skipping")
            state.mark_seen(st, ch["channel_id"], entry.video_id)
            continue

        summary = summarize.summarize_video(entry.title, transcript)
        if not summary:
            print("  -> summarization failed, will retry next run (not marked seen)")
            continue

        row = {
            "published_at": entry.published,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "channel_name": ch["name"],
            "channel_id": ch["channel_id"],
            "video_title": entry.title,
            "video_id": entry.video_id,
            "video_url": entry.url,
            "one_line_summary": summary.get("one_line_summary", ""),
            "key_points": "\n".join(summary.get("key_points", [])),
            "watch_recommendation": summary.get("watch_recommendation", ""),
            "relevance_score": summary.get("relevance_score", ""),
            "why_it_matters": summary.get("why_it_matters", ""),
        }
        processed_rows.append(row)
        state.mark_seen(st, ch["channel_id"], entry.video_id)

    if not processed_rows:
        print("No videos successfully summarized this run.")
        state.save_state(st)
        return

    if args.dry_run:
        print(json.dumps(processed_rows, ensure_ascii=False, indent=2))
        return

    for row in processed_rows:
        sheets_client.append_video_row(creds, spreadsheet_id, row)
    print(f"Wrote {len(processed_rows)} row(s) to Sheet.")

    date_str = datetime.now().strftime("%Y-%m-%d")
    content_lines = []
    for row in processed_rows:
        content_lines.append(f"## [{row['channel_name']}] {row['video_title']}")
        content_lines.append(f"{row['one_line_summary']}\n")
        content_lines.append(row["key_points"])
        content_lines.append(f"\nทำไมสำคัญ: {row['why_it_matters']}")
        content_lines.append(f"แนะนำ: {row['watch_recommendation']} (relevance {row['relevance_score']}/10)")
        content_lines.append(f"ลิงก์: {row['video_url']}")
    notion_content = "\n\n".join(content_lines)

    channels_str = ", ".join(sorted({r["channel_name"] for r in processed_rows}))
    notion_url = notion_helper.create_digest_page(
        title=f"YouTube digest — {date_str} ({channels_str})",
        source="YouTube",
        ticker_channel=channels_str,
        date_iso=date_str,
        summary=processed_rows[0]["one_line_summary"][:500],
        link=processed_rows[0]["video_url"],
        relevance=max((r["relevance_score"] for r in processed_rows if isinstance(r["relevance_score"], (int, float))), default=None),
        content_markdown=notion_content,
    )
    print(f"Notion page created: {notion_url}")

    email_videos = [
        {**row, "key_points": row["key_points"].split("\n") if row["key_points"] else []}
        for row in processed_rows
    ]
    line_client.send_digest(line_token, line_user, date_str, email_videos, notion_url)
    print(f"Sent LINE digest ({len(processed_rows)} video(s)).")

    state.save_state(st)


if __name__ == "__main__":
    main()
    state.write_heartbeat()
