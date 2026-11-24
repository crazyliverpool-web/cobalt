#!/usr/bin/env python3
"""Mechanical checks for a deep-dive HTML (trendlongtun-brief Step 5c, run before the 3 critique lenses).

Catches the rules that keep getting missed when they live only as text in a skill
(2026-10-09 scan: 10/11 reports had no ROE/ROA, 7/11 had no Watch Items).
Judgment calls (one-sidedness, softened red flags, cross-sector peers) stay with the lenses.

Usage: python3 -I tools/lint_deepdive.py reports/<TICKER>_deepdive.html [...]
Exit code 1 if any FAIL, so it can gate delivery.
"""
import html
import re
import sys

# (label, regex that must appear, why) — PHILOSOPHY.md section in brackets
REQUIRED = [
    ("ROE", r"ROE|ผลตอบแทนต่อส่วนของผู้ถือหุ้น|Return on Equity", "user always wants ROE [§1.10]"),
    ("ROA", r"ROA|ผลตอบแทนต่อสินทรัพย์|Return on Assets", "user always wants ROA [§1.10]"),
    ("กำไรสะสม", r"กำไรสะสม|[Rr]etained earnings", "user always wants retained earnings [§1.10]"),
    ("Watch Items", r"ประเด็นที่ต้องติดตามต่อ|Watch Items", "Section 12 must close with Watch Items [§1.11]"),
    ("Filings sources", r"เอกสารทางการ", "Sources must have a Filings group (Step 6)"),
    ("Disclaimer", r"ไม่ใช่คำแนะนำ|ไม่ได้เป็นคำแนะนำ|not (?:personalized )?investment advice|disclaimer", "analysis only [§0]"),
]
FORBIDDEN = [
    ("moat", r"\bmoats?\b|คูเมือง", "use competitive advantage, never moat [§1.1]"),
]


def visible_text(path):
    s = open(path, encoding="utf-8").read()
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def lint(path):
    text = visible_text(path)
    fails = []
    for label, rx, why in REQUIRED:
        if not re.search(rx, text, re.I):
            fails.append(f"missing {label} — {why}")
    for label, rx, why in FORBIDDEN:
        n = len(re.findall(rx, text, re.I))
        if n:
            fails.append(f"found '{label}' x{n} — {why}")
    sections = len(re.findall(r"<h2\b", open(path, encoding="utf-8").read(), re.I))
    flags = len(re.findall(r"ยังไม่ยืนยัน|ขัดแย้ง", text))
    print(f"{'FAIL' if fails else 'PASS'}  {path}  (h2 sections: {sections}, unverified/conflict flags: {flags})")
    for f in fails:
        print(f"   - {f}")
    return not fails


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    ok = [lint(p) for p in sys.argv[1:]]
    sys.exit(0 if all(ok) else 1)
