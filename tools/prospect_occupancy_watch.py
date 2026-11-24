#!/usr/bin/env python3
"""
prospect_occupancy_watch.py — Weekly watcher for new PROSPECT REIT quarterly
filings (MD&A / F45 summary) on set.or.th. When a new quarter's filing appears,
pushes a LINE reminder to update the occupancy-rate table in PROSPECT_deepdive.html.

This script only detects and notifies — it does NOT edit the HTML itself.
Updating the table (and re-querying the NotebookLM notebook for the new
quarter's occupancy figure) should be done by asking Claude directly once the
reminder arrives.

Usage: python3 prospect_occupancy_watch.py [--dry-run]
  --dry-run: fetch + log only; LINE pushes are logged instead of sent, state json not written.
Exit codes: 0 ok, 1 missing env / fetch failed after retries (LINE alert sent),
  5 uncaught exception (traceback to stderr, LINE alert). Log lines are always single-line
  so tools/bots_doctor.py can read the last run's outcome.
Requires: tools/.env with LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
"""
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import requests
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

import netwait

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "stock-research/prospect_occupancy_watch_state.json"
LOG_PATH = ROOT / "stock-research/prospect_occupancy_watch.log"

NEWS_URL = "https://www.set.or.th/th/market/product/stock/quote/PROSPECT/news"
DEEPDIVE_PATH = "PROSPECT_deepdive.html"

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

DRY_RUN = "--dry-run" in sys.argv
# Hosts that must be reachable before we start (DarkWake: Mac awake, Wi-Fi not yet) — see netwait.py.
# The goto retries below stay as a second line of defence.
NET_HOSTS = ("www.set.or.th", "api.line.me")

# Page load: the news list is client-rendered (Nuxt), so we must let XHRs settle, but a
# networkidle that never settles shouldn't kill the run. Retries cover the 2026-10-12 case:
# launchd fired the missed 07:30 job during a 45s maintenance DarkWake at 07:41 before Wi-Fi
# was up -> net::ERR_INTERNET_DISCONNECTED. Backoff long enough to span the next wake.
GOTO_TIMEOUT_MS = 60000
GOTO_ATTEMPTS = 3
GOTO_BACKOFF_S = 90
IDLE_TIMEOUT_MS = 30000
# Section heading that is always on a rendered news tab — absent = page didn't render
# (fetch problem), which must not be reported as "No matching filing found".
RENDERED_MARKER = "ข่าวงบการเงิน"

# Titles that mark a new quarterly/annual result filing worth watching for
WATCH_KEYWORDS = [
    "คำอธิบายและวิเคราะห์ของฝ่ายจัดการ",
    "สรุปผลการดำเนินงานของบจ.",
]
# Detection is by reporting PERIOD, not title (2026-10-12). The news tab previews only the 5
# newest items per section, so the MD&A drops out of "ข่าวบริษัท" within weeks; the
# "ข่าวงบการเงิน" section (งบการเงินไตรมาสที่ N/YYYY, งบการเงินรายปี YYYY — filed with the
# MD&A) keeps ~1 year visible. Both sources map to (BE year, quarter); annual = quarter 4.
FIN_Q_RE = re.compile(r"งบการเงินไตรมาสที่\s*([1-4])\s*/\s*(25\d\d)")
FIN_FY_RE = re.compile(r"งบการเงินรายปี\s*(25\d\d)")
QUARTER_RE = re.compile(r"ไตรมาสที่\s*([1-4])")
YEAR_RE = re.compile(r"25\d\d")


def period_of(line: str) -> tuple[int, int] | None:
    """(BE year, quarter) a filing title reports on, or None if it isn't a watched filing."""
    if m := FIN_Q_RE.search(line):
        return int(m.group(2)), int(m.group(1))
    if m := FIN_FY_RE.search(line):
        return int(m.group(1)), 4
    if any(kw in line for kw in WATCH_KEYWORDS):
        years = YEAR_RE.findall(line)  # period-end year, e.g. "สิ้นสุดวันที่ 30 มิ.ย. 2569"
        if not years:
            return None
        q = QUARTER_RE.search(line)
        return int(years[-1]), int(q.group(1)) if q else 4  # no quarter = annual MD&A
    return None


def period_label(p) -> str:
    return f"Q{p[1]}/{p[0]}" if p else "none"


def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def one_line(text) -> str:
    """Playwright errors carry a multi-line 'Call log' — keep the first line only."""
    return (str(text).splitlines() or [""])[0][:200]


def log(msg: str):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def line_push(token: str, user_id: str, text: str) -> bool:
    """True on HTTP 200 (or dry-run)."""
    if DRY_RUN:
        log(f"[dry-run] would LINE push: {text[:200]!r}")
        return True
    try:
        resp = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"to": user_id, "messages": [{"type": "text", "text": text[:4900]}]},
            timeout=15,
        )
    except requests.RequestException as e:  # e.g. network still down — don't turn it into a crash
        log(f"LINE push failed: {type(e).__name__}: {one_line(e)}")
        return False
    if resp.status_code != 200:
        log(f"LINE push failed: {resp.status_code} {one_line(resp.text)}")
        return False
    log("LINE push OK")
    return True


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"last_title": None, "last_date": None}


def save_state(state: dict):
    if DRY_RUN:
        log("[dry-run] state json not written.")
        return
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_filings(page) -> list[tuple[tuple[int, int], str, str]]:
    """Return [(period, title, date_text)] for every watched filing visible on the news tab
    (both sections). Raises if the page can't be loaded or didn't render."""
    for attempt in range(1, GOTO_ATTEMPTS + 1):
        try:
            page.goto(NEWS_URL, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            break
        except PlaywrightError as e:  # timeouts + net::ERR_* (e.g. no network right after wake)
            if attempt == GOTO_ATTEMPTS:
                raise
            log(f"goto failed (attempt {attempt}/{GOTO_ATTEMPTS}): {one_line(e)} — retrying in {GOTO_BACKOFF_S}s")
            time.sleep(GOTO_BACKOFF_S)
    try:
        page.wait_for_load_state("networkidle", timeout=IDLE_TIMEOUT_MS)
    except PlaywrightError:
        log(f"networkidle not reached in {IDLE_TIMEOUT_MS // 1000}s — parsing what rendered")
    page.wait_for_timeout(2000)
    text = page.inner_text("body")
    if RENDERED_MARKER not in text:
        raise RuntimeError(f"news page did not render (no '{RENDERED_MARKER}' section; title={page.title()!r})")
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    found = []
    for i, line in enumerate(lines):
        period = period_of(line)
        if period is None:
            continue
        # date/time usually appear a few lines above the title in this layout
        date_text = ""
        for back in range(1, 6):
            j = i - back
            if j >= 0 and YEAR_RE.search(lines[j]) and period_of(lines[j]) is None:
                date_text = lines[j]
                break
        found.append((period, line, date_text))
    return found


def main():
    netwait.hold_awake(log)
    load_env()
    line_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    line_user = os.environ.get("LINE_USER_ID")
    if not line_token or not line_user:
        log("Missing LINE env vars — aborting.")
        sys.exit(1)

    state = load_state()
    if "last_period" not in state:
        # one-time migration from title-based state: derive the period of the last alerted
        # filing so switching detection method doesn't re-alert an already-alerted quarter
        derived = period_of(state.get("last_title") or "")
        state["last_period"] = list(derived) if derived else None
        log(f"Migrated state: last_period={period_label(derived)} (from last_title)")
        save_state(state)
    last_period = tuple(state["last_period"]) if state.get("last_period") else None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()
        try:
            netwait.wait_for_network(NET_HOSTS, log=log)  # NetworkUnavailable -> fetch-failed path below
            found = fetch_filings(page)
        except Exception as e:  # noqa: BLE001
            log(f"fetch failed: {type(e).__name__}: {one_line(e)}")
            browser.close()
            line_push(line_token, line_user,
                      f"❌ บอทเช็คไฟลิ่ง PROSPECT ERROR {datetime.now().strftime('%d/%m/%Y')}\n"
                      f"เปิดหน้าข่าว SET ไม่ได้: {type(e).__name__}: {one_line(e)[:150]}\n"
                      "สัปดาห์นี้ยังไม่ได้เช็ค — รอบหน้า (จันทร์หน้า) จะลองใหม่ หรือสั่ง kickstart เองครับ")
            sys.exit(1)
        browser.close()

    if not found:
        log("No matching filing found on news page.")
        return

    latest = max(p for p, _, _ in found)
    items = [(t, d) for p, t, d in found if p == latest]
    items = list(dict.fromkeys(items))  # same item can't appear twice, but be safe
    seen = f"{len(found)} watched item(s) on page"
    if last_period and latest <= last_period:
        log(f"No change. Latest period {period_label(latest)} (recorded {period_label(last_period)}; {seen}): "
            f"{items[0][0]} ({items[0][1]})")
        return

    title, date_text = items[0]
    log(f"New filing detected: {period_label(latest)} (recorded {period_label(last_period)}; {seen}): "
        + " + ".join(f"{t} ({d})" for t, d in items))
    message = (
        f"📊 PROSPECT REIT มีไฟลิ่งไตรมาสใหม่ ({period_label(latest)})\n\n"
        + "\n".join(f"• {t} ({d})" for t, d in items) + "\n\n"
        "เปิด Claude Code แล้วบอกให้ 'อัปเดต occupancy rate ไตรมาสล่าสุดของ PROSPECT ใน "
        f"{DEEPDIVE_PATH}' ได้เลย"
    )
    if not line_push(line_token, line_user, message):
        # Don't record the filing as seen — next run re-detects it and re-sends.
        log("New-filing alert not delivered — state not updated, will retry next run.")
        sys.exit(1)

    state["last_period"] = list(latest)
    state["last_title"] = title
    state["last_date"] = date_text
    state["last_checked"] = datetime.now(timezone.utc).isoformat()
    save_state(state)


def run() -> None:
    """main() + crash handler: any uncaught exception -> single-line log, traceback to stderr,
    best-effort LINE alert, exit 5. Weekly bot, so no alert dedupe needed."""
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        log(f"CRASH: {type(e).__name__}: {one_line(e)}")
        traceback.print_exc()
        try:
            load_env()
            token, user = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"), os.environ.get("LINE_USER_ID")
            if token and user:
                line_push(token, user, f"❌ บอทเช็คไฟลิ่ง PROSPECT ERROR {datetime.now().strftime('%d/%m/%Y')}\n"
                                       f"รันพังกลางทาง: {type(e).__name__}: {one_line(e)[:150]}")
        except Exception as e2:  # noqa: BLE001
            log(f"Crash alert LINE push itself failed: {type(e2).__name__}: {one_line(e2)}")
        sys.exit(5)


if __name__ == "__main__":
    run()
