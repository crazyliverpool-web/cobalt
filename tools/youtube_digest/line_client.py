"""Send the daily YouTube digest as a short LINE push message (full detail lives in Notion)."""
import os
import requests


def send_digest(token: str, user_id: str, date_str: str, videos: list[dict], notion_url: str) -> None:
    channels = sorted({v["channel_name"] for v in videos})
    lines = [f"🎥 YouTube digest {date_str}", f"คลิปใหม่ {len(videos)} คลิป จาก: {', '.join(channels)}", ""]
    for v in sorted(videos, key=lambda x: -x.get("relevance_score", 0))[:5]:
        lines.append(f"• [{v.get('watch_recommendation', '')}] {v['video_title']}")
    lines.append("")
    lines.append(f"รายละเอียด: {notion_url}")
    text = "\n".join(lines)

    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"to": user_id, "messages": [{"type": "text", "text": text[:4900]}]},
        timeout=15,
    )
    resp.raise_for_status()
