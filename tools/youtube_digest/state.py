"""Local JSON state store - tracks which video IDs have already been processed."""
import json
import os
from datetime import datetime, timezone

STATE_PATH = os.path.join(os.path.dirname(__file__), "data", "state.json")
HEARTBEAT_PATH = os.path.join(os.path.dirname(__file__), "data", "last_run.json")


def load_state() -> dict:
    if not os.path.exists(STATE_PATH):
        return {"seen_video_ids": {}}
    with open(STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def is_seen(state: dict, channel_id: str, video_id: str) -> bool:
    return video_id in state.get("seen_video_ids", {}).get(channel_id, [])


def mark_seen(state: dict, channel_id: str, video_id: str) -> None:
    state.setdefault("seen_video_ids", {}).setdefault(channel_id, [])
    if video_id not in state["seen_video_ids"][channel_id]:
        state["seen_video_ids"][channel_id].append(video_id)
        # keep only the most recent 200 IDs per channel so the file doesn't grow forever
        state["seen_video_ids"][channel_id] = state["seen_video_ids"][channel_id][-200:]


def write_heartbeat() -> None:
    """Called once at the end of a successful run (see digest.py). Watched by
    tools/digest_watchdog.py to detect silent failures (see for-opus/questions.md Q29)."""
    os.makedirs(os.path.dirname(HEARTBEAT_PATH), exist_ok=True)
    with open(HEARTBEAT_PATH, "w", encoding="utf-8") as f:
        json.dump({"ts": datetime.now(timezone.utc).isoformat(), "status": "ok"}, f)
