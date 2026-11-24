#!/usr/bin/env python3
"""Catch-up for the scheduled LINE bots (YouTube digest, thaivi digest,
PROSPECT occupancy watch) — runs at boot/login (RunAtLoad) and kickstarts any
bot whose last run is stale, so a missed run (because the Mac was fully off,
not just asleep) gets caught the moment the Mac comes back online instead of
waiting for the next scheduled slot. Uses the same heartbeat files as
digest_watchdog.py, with a per-job threshold since the digests run daily but
the PROSPECT watch runs weekly.
"""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))

# label -> (heartbeat file, stale threshold in hours). Defined once in bot_registry.py
# (shared with digest_watchdog.py and bots_doctor.py). Dailies 25h; the weekly PROSPECT
# watch 100h (its heartbeat is the append-only .log).
sys.path.insert(0, ROOT)
from bot_registry import JOBS  # noqa: E402


def main():
    uid = str(os.getuid())
    now = time.time()
    for label, (heartbeat, stale_hours) in JOBS.items():
        age_hours = None if not os.path.exists(heartbeat) else (now - os.path.getmtime(heartbeat)) / 3600
        stale = age_hours is None or age_hours > stale_hours
        if not stale:
            print(f"{label}: fresh ({age_hours:.1f}h old), skipping")
            continue
        status = "no heartbeat file found" if age_hours is None else f"{age_hours:.1f}h old"
        print(f"{label}: stale ({status}), kickstarting")
        subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"], check=False)


if __name__ == "__main__":
    main()
