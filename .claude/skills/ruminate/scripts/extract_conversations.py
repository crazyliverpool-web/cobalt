#!/usr/bin/env python3
"""Condense Claude Code transcripts (JSONL) into readable text for /ruminate.

Keeps only what matters for spotting patterns: the user's own words in full,
and assistant prose truncated. Drops tool calls/results, meta and system
records — they are most of the bytes and none of the signal.

Usage:
  extract_conversations.py <project-transcript-dir> <out-dir> [--from YYYY-MM-DD] [--skip SESSION_ID ...]
"""
import argparse
import glob
import json
import os
import re
from datetime import datetime

ASSISTANT_MAX = 600  # chars of assistant prose kept per message
NOISE = re.compile(r"^<(local-command|command-name|command-message|system-reminder|task-notification)")


def text_of(content):
    if isinstance(content, str):
        return content
    parts = []
    for block in content or []:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


def extract(path):
    lines = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            kind = d.get("type")
            if kind not in ("user", "assistant") or d.get("isMeta") or d.get("isSidechain"):
                continue
            content = d.get("message", {}).get("content")
            # user records that only carry tool results have no text blocks
            text = text_of(content).strip()
            if not text or NOISE.match(text):
                continue
            ts = (d.get("timestamp") or "")[:16].replace("T", " ")
            if kind == "user":
                lines.append(f"\n### USER [{ts}]\n{text}")
            else:
                short = text if len(text) <= ASSISTANT_MAX else text[:ASSISTANT_MAX] + " …"
                lines.append(f"\n--- assistant [{ts}]\n{short}")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--from", dest="since")
    ap.add_argument("--skip", nargs="*", default=[])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    since = datetime.strptime(a.since, "%Y-%m-%d").timestamp() if a.since else 0
    for path in sorted(glob.glob(os.path.join(a.src, "*.jsonl")), key=os.path.getmtime):
        sid = os.path.basename(path)[:-6]
        if sid in a.skip or os.path.getmtime(path) < since:
            continue
        lines = extract(path)
        if not lines:
            continue
        day = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
        out = os.path.join(a.out, f"{day}_{sid[:8]}.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"# session {sid} (last active {day})\n" + "\n".join(lines))
        users = sum(1 for l in lines if l.startswith("\n### USER"))
        print(f"{out}\t{users} user msgs\t{os.path.getsize(out)//1024} KB")


if __name__ == "__main__":
    main()
