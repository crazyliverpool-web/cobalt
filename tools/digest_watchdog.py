#!/usr/bin/env python3
"""Watchdog for the scheduled LINE bots (YouTube digest, thaivi digest, PROSPECT
occupancy watch) — alerts via LINE if any goes silent past its threshold.
Checks heartbeat file mtimes only, no imports from the bots themselves. Run
daily at 09:00 via com.alonsi.digest-watchdog, after the digest jobs. See
for-opus/questions.md Q29 for why this exists: youtube-digest died silently for
32 days with nobody noticing before this watchdog existed.
"""
import os
import sys
import time
from datetime import datetime

import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(ROOT, ".env")

# name -> (heartbeat file, stale threshold in hours). Defined once in bot_registry.py
# (shared with digest_catchup.py and bots_doctor.py). Dailies alert after 36h; the
# weekly PROSPECT watch after 216h (~9 days).
sys.path.insert(0, ROOT)
from bot_registry import HEARTBEATS  # noqa: E402


def load_env():
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def line_push(token: str, user_id: str, text: str):
    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"to": user_id, "messages": [{"type": "text", "text": text[:4900]}]},
        timeout=15,
    )
    print(f"LINE push: {resp.status_code}")


def main():
    load_env()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user = os.environ.get("LINE_USER_ID")
    if not token or not user:
        print("ERROR: missing LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID in tools/.env")
        return

    now = time.time()
    stale = []
    for name, (path, stale_hours) in HEARTBEATS.items():
        if not os.path.exists(path):
            stale.append((name, None))
            continue
        age_hours = (now - os.path.getmtime(path)) / 3600
        if age_hours > stale_hours:
            stale.append((name, age_hours))

    if stale:
        lines = ["⚠️ Digest watchdog — เจอบอทเงียบเกินกำหนด:"]
        for name, age in stale:
            status = "ไม่เคยรันเลย (ไม่พบไฟล์)" if age is None else f"เงียบมา {age:.0f} ชม."
            lines.append(f"- {name}: {status}")
        line_push(token, user, "\n".join(lines))
        print("Alert sent.")
        return

    # weekly liveness ping (Sunday only) so watchdog silence is itself observable
    if datetime.now().weekday() == 6:
        line_push(token, user, "✅ Digest watchdog: บอททั้งหมด (YouTube + thaivi + PROSPECT) ปกติดี")
        print("Weekly liveness ping sent.")
    else:
        print("All heartbeats fresh. No alert needed.")


if __name__ == "__main__":
    main()
