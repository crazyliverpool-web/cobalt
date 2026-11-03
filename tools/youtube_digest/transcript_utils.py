"""Fetch and clean YouTube captions via yt-dlp.

Works for both public videos (no auth needed) and Membership-only videos
(uses this Mac's live, logged-in Chrome session via --cookies-from-browser).
Never downloads video/audio - captions only.
"""
import subprocess
import tempfile
import os
import re
import glob


def fetch_transcript(video_url: str, lang: str = "th") -> str | None:
    """Return cleaned plain-text transcript, or None if unavailable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_template = os.path.join(tmpdir, "cap.%(ext)s")
        cmd = [
            "yt-dlp", "--skip-download",
            "--write-auto-sub", "--write-sub",
            "--sub-lang", lang,
            "--sub-format", "vtt",
            "--cookies-from-browser", "chrome",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            "-o", out_template,
            video_url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        vtt_files = glob.glob(os.path.join(tmpdir, f"cap.{lang}.vtt"))
        if not vtt_files:
            return None
        with open(vtt_files[0], encoding="utf-8") as f:
            raw = f.read()
        return _clean_vtt(raw)


def _clean_vtt(content: str) -> str:
    """Dedupe Facebook/YouTube karaoke-style rolling captions into plain text."""
    lines = content.split("\n")
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:
            continue
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean:
            text_lines.append(clean)

    result = []
    prev = ""
    for l in text_lines:
        if l == prev or (prev and l.startswith(prev)):
            prev = l
            continue
        result.append(l)
        prev = l

    full_text = " ".join(result)
    full_text = re.sub(r"\s+", " ", full_text).strip()
    return full_text
