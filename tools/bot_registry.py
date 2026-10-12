"""Single source of truth for the studio's launchd bots (stdlib only).

Read by:
  - tools/digest_watchdog.py  -> HEARTBEATS (bots with watched=True, threshold stale_hours)
  - tools/digest_catchup.py   -> JOBS       (bots with catchup_hours set)
  - tools/bots_doctor.py      -> BOTS       (every bot: launchd, heartbeat, plist, env, state checks)

Adding a bot: append a Bot(...) here, write its guides/bots/<label>.md. Order matters only for
the order bots appear in watchdog alerts / catchup output / doctor lines.
"""
import os
from dataclasses import dataclass

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
PYTHON = "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
TOOLS_ENV = os.path.join(TOOLS, ".env")
YT_DIR = os.path.join(TOOLS, "youtube_digest")


@dataclass(frozen=True)
class Bot:
    label: str                       # launchd label (com.alonsi.*)
    name: str                        # human name (used in watchdog LINE alerts)
    script: str                      # absolute path; must equal plist ProgramArguments[1]
    heartbeat: str | None = None     # file whose mtime proves the bot ran
    stale_hours: float | None = None  # doctor + watchdog: older than this = bot is silent
    catchup_hours: float | None = None  # catchup kickstarts when older than this (None = not caught up)
    watched: bool = False            # include in watchdog HEARTBEATS
    env_files: tuple = (TOOLS_ENV,)  # .env files the bot loads (keys checked as a union)
    env_keys: tuple = ()             # keys that must be present in env_files
    path_bins: tuple = ()            # binaries that must resolve on the plist PATH
    guide: str = ""                  # guides/bots/<file>


BOTS = [
    Bot(
        label="com.alonsi.youtube-digest",
        name="YouTube digest",
        script=os.path.join(YT_DIR, "digest.py"),
        heartbeat=os.path.join(YT_DIR, "data", "last_run.json"),
        stale_hours=36, catchup_hours=25, watched=True,
        env_files=(os.path.join(YT_DIR, ".env"), TOOLS_ENV),
        env_keys=("GOOGLE_SPREADSHEET_ID", "LINE_CHANNEL_ACCESS_TOKEN", "LINE_USER_ID",
                  "ANTHROPIC_API_KEY", "NOTION_API_KEY", "NOTION_DATABASE_ID"),
        path_bins=("yt-dlp",),
        guide="youtube-digest.md",
    ),
    Bot(
        label="com.alonsi.roikonroihoon-digest",
        name="thaivi digest",
        script=os.path.join(TOOLS, "roikonroihoon_digest.py"),
        heartbeat=os.path.join(ROOT, "stock-research", "thaivi", "digest_state.json"),
        stale_hours=36, catchup_hours=25, watched=True,
        env_keys=("ANTHROPIC_API_KEY", "LINE_CHANNEL_ACCESS_TOKEN", "LINE_USER_ID",
                  "NOTION_API_KEY", "NOTION_DATABASE_ID"),
        guide="roikonroihoon-digest.md",
    ),
    Bot(
        # weekly (Mon 07:30); heartbeat is the append-only .log because the state json
        # only changes when a new filing appears (months apart)
        label="com.alonsi.prospect-occupancy-watch",
        name="PROSPECT occupancy watch",
        script=os.path.join(TOOLS, "prospect_occupancy_watch.py"),
        heartbeat=os.path.join(ROOT, "stock-research", "prospect_occupancy_watch.log"),
        stale_hours=216, catchup_hours=100, watched=True,
        env_keys=("LINE_CHANNEL_ACCESS_TOKEN", "LINE_USER_ID"),
        guide="prospect-occupancy-watch.md",
    ),
    Bot(
        # daily 09:00; prints one line per run to its stdout log -> that is its heartbeat
        label="com.alonsi.digest-watchdog",
        name="digest watchdog",
        script=os.path.join(TOOLS, "digest_watchdog.py"),
        heartbeat=os.path.join(TOOLS, "digest_watchdog.out.log"),
        stale_hours=36,
        env_keys=("LINE_CHANNEL_ACCESS_TOKEN", "LINE_USER_ID"),
        guide="watchdog-and-catchup.md",
    ),
    Bot(
        # RunAtLoad only (boot/login) -> no schedule, so no freshness threshold
        label="com.alonsi.digest-catchup",
        name="digest catch-up",
        script=os.path.join(TOOLS, "digest_catchup.py"),
        env_files=(),
        guide="watchdog-and-catchup.md",
    ),
    Bot(
        # one-shot on 2027-07-15 07:05 (date lives in the plist); never having run is normal
        label="com.alonsi.thaivi-relogin-reminder",
        name="ThaiVI relogin reminder",
        script=os.path.join(TOOLS, "line_reminder.py"),
        env_keys=("LINE_CHANNEL_ACCESS_TOKEN", "LINE_USER_ID"),
        guide="thaivi-relogin-reminder.md",
    ),
]

# name -> (heartbeat file, stale threshold in hours) — consumed by digest_watchdog.py
HEARTBEATS = {b.name: (b.heartbeat, b.stale_hours) for b in BOTS if b.watched}
# label -> (heartbeat file, stale threshold in hours) — consumed by digest_catchup.py
JOBS = {b.label: (b.heartbeat, b.catchup_hours) for b in BOTS if b.catchup_hours is not None}
