#!/usr/bin/env python3
"""
roikonroihoon_digest.py — Daily digest bot for the "ห้องร้อยคนร้อยหุ้น" threads
(board.thaivi.org forum f=49) of the user's tracked hospital-sector stocks.

Flow: fetch latest page of each tracked ticker's thread -> diff against last-seen
state -> summarize new posts with Claude -> push a Thai digest via LINE Messaging API.

Usage: python3 roikonroihoon_digest.py [--dry-run]
  --dry-run: scrape + log only; LINE pushes are logged instead of sent, no Claude/Notion
             calls, digest_state.json is not written (the ThaiVI session file still is,
             since phpBB rotates the autologin key on use).
Exit codes: 0 ok, 1 missing env, 2 session expired, 3 0 posts parsed everywhere,
  4 new posts found but Claude/Notion/LINE failed — digest_state.json NOT written, so the
    posts stay "unseen" and the next run re-sends them (and the stale heartbeat trips the watchdog),
  5 uncaught exception (e.g. page load timeout after retry, or netwait.NetworkUnavailable) — traceback logged, one LINE alert per
    error class (deduped via digest_crash_alert.json), digest_state.json NOT written.
Requires: tools/.env with ANTHROPIC_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
Requires: stock-research/thaivi/thaivi_state.json (valid Playwright login session)
"""
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

import netwait
import notion_helper

ROOT = Path(__file__).resolve().parent.parent
THAIVI_DIR = ROOT / "stock-research/thaivi"
STATE_PATH = THAIVI_DIR / "thaivi_state.json"
DIGEST_STATE_PATH = THAIVI_DIR / "digest_state.json"
LOG_PATH = THAIVI_DIR / "digest_log.txt"
# Crash-alert dedupe flag. Separate file on purpose: the crash handler must never write
# digest_state.json (that would commit half-updated post counts = lost posts).
CRASH_ALERT_PATH = THAIVI_DIR / "digest_crash_alert.json"

# Page loads: phpBB HTML is server-rendered, so DOMContentLoaded is enough for the parser;
# "load" waited on slow third-party assets and timed out at 30s (2026-10-10, 2026-10-11).
GOTO_TIMEOUT_MS = 45000
GOTO_ATTEMPTS = 2
GOTO_BACKOFF_S = 5
# phpBB check_form_key() rejects a form submitted in the same second its token was created
# ("not a human") -> "การส่งค่าผิดพลาด. กรุณาลองใหม่อีกครั้ง" (FORM_INVALID). Wait before submit.
LOGIN_SUBMIT_DELAY_S = 2.5

TICKERS = {
    "BCH":  53828,
    "WPH":  60840,
    "BDMS": 53653,
    "CHG":  54888,
    "VIH":  53579,
    "RJH":  59837,
}

# Hosts that must be reachable before we start (DarkWake: Mac awake, Wi-Fi not yet) — see netwait.py
NET_HOSTS = ("board.thaivi.org", "api.line.me", "api.anthropic.com", "api.notion.com")

MODEL = "claude-sonnet-5"
CLEAN_STREAK_THRESHOLD = 5  # consecutive successful (non-expired) runs before declaring the 2026-08-04 session-persistence fix confirmed

# Must match the UA in stock-research/thaivi/login_and_fetch.py — phpBB's browser_check
# invalidates a session if the UA changes between the login and a later request.
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

# --- env loading (same pattern as tools/structure_transcript.py) ---
def load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def log(msg: str):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


DRY_RUN = "--dry-run" in sys.argv  # no LINE push, no Claude/Notion call, digest_state.json not written


def line_push(token: str, user_id: str, text: str) -> bool:
    """Returns True on HTTP 200 (or in dry-run)."""
    if DRY_RUN:
        log(f"[dry-run] would LINE push: {text[:300]!r}")
        return True
    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"to": user_id, "messages": [{"type": "text", "text": text[:4900]}]},
        timeout=15,
    )
    if resp.status_code != 200:
        log(f"LINE push failed: {resp.status_code} {resp.text}")
        return False
    log("LINE push OK")
    return True


def summarize_with_claude(client, prompt: str, attempts: int = 2, backoff_s: float = 15) -> str | None:
    """Return the summary text, or None if Claude errors or returns no text block on every
    attempt (2026-10-10: a response with no text block crashed the run via StopIteration
    after the posts had already been marked seen — that batch was lost)."""
    for attempt in range(1, attempts + 1):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
            text = next((b.text for b in resp.content if b.type == "text"), "").strip()
            if text:
                return text
            log(f"Claude returned no text (attempt {attempt}/{attempts}, stop_reason={resp.stop_reason!r}, "
                f"blocks={[b.type for b in resp.content]})")
        except anthropic.APIError as e:
            log(f"Claude call failed (attempt {attempt}/{attempts}): {type(e).__name__}: {e}")
        if attempt < attempts:
            time.sleep(backoff_s)
    return None


def goto(page, url: str):
    """page.goto with DOMContentLoaded + one retry on timeout/network error; re-raises after."""
    for attempt in range(1, GOTO_ATTEMPTS + 1):
        try:
            return page.goto(url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
        except PlaywrightError as e:  # TimeoutError is a subclass; net::ERR_* are plain Error
            if attempt == GOTO_ATTEMPTS:
                raise
            log(f"goto failed (attempt {attempt}/{GOTO_ATTEMPTS}) {url}: {type(e).__name__}: "
                f"{(str(e).splitlines() or [''])[0][:120]} — retrying in {GOTO_BACKOFF_S}s")
            time.sleep(GOTO_BACKOFF_S)


def fetch_latest_page(page, ticker: str, topic_id: int):
    """Return (posts: list[str], is_login_expired: bool)."""
    resp = goto(page, f"https://board.thaivi.org/viewtopic.php?t={topic_id}&start=99999")
    # Since ~2026-09-16 ThaiVI no longer redirects guests to mode=login: it serves an
    # HTTP 403 "ข้อมูลทั่วไป / เนื้อหาส่วนนี้เฉพาะสมาชิก" page at the same URL. Treat any
    # page without a logout link (i.e. not logged in) as an expired session.
    html = page.content()
    if (
        "mode=login" in page.url
        or "เข้าสู่ระบบ" in page.title()
        or (resp is not None and resp.status in (401, 403))
        or "mode=logout" not in html  # (don't match "เฉพาะสมาชิก" text — users post it)
    ):
        return [], True
    posts = page.query_selector_all(".postbody .content")
    texts = [p.inner_text().strip() for p in posts]
    return texts, False


def auto_login(page, username: str, password: str) -> bool:
    """Fresh username/password login when the saved session has expired, so a burned
    autologin key or IP change doesn't require a manual relogin. Must load a fresh
    login page each attempt — phpBB's form_token/sid are single-use per page load."""
    goto(page, "https://board.thaivi.org/ucp.php?mode=login")
    page.fill("#username", username)
    page.fill("#password", password)
    page.check("#autologin")
    time.sleep(LOGIN_SUBMIT_DELAY_S)  # form token must be >=1s old (see LOGIN_SUBMIT_DELAY_S)
    page.click('input[name="login"]')
    page.wait_for_load_state("domcontentloaded", timeout=GOTO_TIMEOUT_MS)
    if "mode=logout" in page.content():
        return True
    err = page.query_selector(".error, #message, .panel .inner p")
    log(f"Auto re-login page said: {(err.inner_text().strip()[:200] if err else '(no error element)')!r}")
    return False


def run_ticker_loop(page, digest_state):
    """Return (new_by_ticker, is_login_expired, parse_errors)."""
    new_by_ticker = {}
    parse_errors = []
    for ticker, topic_id in TICKERS.items():
        posts, expired = fetch_latest_page(page, ticker, topic_id)
        if expired:
            log(f"ERROR {ticker}: session expired / not logged in (login redirect or members-only 403 page).")
            return new_by_ticker, True, parse_errors
        if not posts:
            # A long-running thread's last page always has >=1 post — 0 means the
            # selector broke or we got a non-thread page. Never record it as "quiet",
            # and don't overwrite the last good count with 0.
            log(f"ERROR {ticker}: parsed 0 posts on t={topic_id} (title={page.title()!r}) — scrape failure, not a quiet day.")
            parse_errors.append(ticker)
            continue
        last_count = digest_state.get(ticker, {}).get("last_post_count", 0)
        if len(posts) > last_count:
            new_posts = posts[last_count:]
            new_by_ticker[ticker] = new_posts
            log(f"{ticker}: {len(new_posts)} new post(s) (total now {len(posts)}, was {last_count})")
        else:
            log(f"{ticker}: no new posts (total {len(posts)})")
        digest_state.setdefault(ticker, {})["last_post_count"] = len(posts)
        digest_state[ticker]["topic_id"] = topic_id
        digest_state[ticker]["last_checked"] = datetime.now(timezone.utc).isoformat()
    return new_by_ticker, False, parse_errors


def main():
    netwait.hold_awake(log)
    load_env()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    line_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    line_user = os.environ.get("LINE_USER_ID")
    missing = [n for n, v in [("ANTHROPIC_API_KEY", api_key), ("LINE_CHANNEL_ACCESS_TOKEN", line_token), ("LINE_USER_ID", line_user)] if not v]
    if missing:
        log(f"Missing env vars: {missing} — aborting.")
        sys.exit(1)

    # Never up within 10 min -> NetworkUnavailable -> run()'s crash handler: exit 5, one LINE
    # alert attempt (fails quietly while offline), digest_state.json untouched.
    netwait.wait_for_network(NET_HOSTS, log=log)

    digest_state = json.loads(DIGEST_STATE_PATH.read_text(encoding="utf-8")) if DIGEST_STATE_PATH.exists() else {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(STATE_PATH), user_agent=USER_AGENT)
        page = context.new_page()

        new_by_ticker, login_expired, parse_errors = run_ticker_loop(page, digest_state)

        if login_expired:
            thaivi_user = os.environ.get("THAIVI_USER")
            thaivi_pass = os.environ.get("THAIVI_PASS")
            if thaivi_user and thaivi_pass:
                log("Session expired — attempting auto re-login.")
                # Stale/expired cookies still in the context interfere with a fresh
                # login attempt (confirmed: identical login code succeeds in a clean
                # context but fails when old cookies are present) — clear first.
                context.clear_cookies()
                if auto_login(page, thaivi_user, thaivi_pass):
                    log("Auto re-login succeeded — retrying ticker loop.")
                    new_by_ticker, login_expired, parse_errors = run_ticker_loop(page, digest_state)
                else:
                    log("Auto re-login failed (bad creds, captcha, or lockout).")
            else:
                log("THAIVI_USER/THAIVI_PASS not set — cannot auto re-login.")

        if not login_expired:
            # phpBB rotates the autologin key server-side whenever it's actually used to
            # re-establish a session — persist whatever key/cookies we ended up with, or
            # the next run presents an already-invalidated key and gets logged out.
            tmp_path = STATE_PATH.with_suffix(".json.tmp")
            tmp_path.write_text(
                json.dumps(context.storage_state(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            tmp_path.replace(STATE_PATH)

        browser.close()

    def save_digest_state():
        if DRY_RUN:
            log("[dry-run] digest_state.json not written.")
            return
        DIGEST_STATE_PATH.write_text(json.dumps(digest_state, ensure_ascii=False, indent=2), encoding="utf-8")

    if login_expired:
        digest_state["_clean_run_streak"] = 0
        save_digest_state()
        if not digest_state.get("_session_alert_sent"):
            line_push(
                line_token, line_user,
                "⚠️ บอทเช็คกระทู้ ร้อยคนร้อยหุ้น หยุดทำงาน — session thaivi.org หมดอายุ และ auto-relogin ก็ล้มเหลวด้วย\n"
                "(อาจเจอ captcha/รหัสผ่านผิด/ถูกล็อก) รัน login_and_fetch.py บนเครื่อง Mac เพื่อ login ใหม่ครับ",
            )
            digest_state["_session_alert_sent"] = True
            save_digest_state()
            log("Notified user of expired session. Exiting.")
        else:
            log("Session still expired — alert already sent, staying quiet. Exiting.")
        sys.exit(2)

    digest_state["_session_alert_sent"] = False
    today_th = datetime.now().strftime("%d/%m/%Y")

    if parse_errors and len(parse_errors) == len(TICKERS):
        # Logged in but nothing parsed anywhere — almost certainly a markup/selector
        # change. Report loudly instead of a "quiet day".
        digest_state["_clean_run_streak"] = 0
        save_digest_state()
        line_push(
            line_token, line_user,
            f"❌ บอทเช็คกระทู้ ร้อยคนร้อยหุ้น ERROR {today_th}\n"
            f"login ได้แต่ parse โพสต์ได้ 0 ทุกกระทู้ ({'/'.join(parse_errors)}) — selector/หน้าเว็บน่าจะเปลี่ยน ไม่ใช่วันเงียบ ต้องแก้ roikonroihoon_digest.py ครับ",
        )
        log(f"ERROR: 0 posts parsed for all tickers {parse_errors} — sent error notice instead of quiet-day. Exiting.")
        sys.exit(3)

    digest_state["_clean_run_streak"] = 0 if parse_errors else digest_state.get("_clean_run_streak", 0) + 1
    if (
        digest_state["_clean_run_streak"] >= CLEAN_STREAK_THRESHOLD
        and not digest_state.get("_pagination_fix_reminder_sent")
    ):
        line_push(
            line_token, line_user,
            f"✅ บอทเช็คกระทู้ ร้อยคนร้อยหุ้น ไม่หลุด session มา {digest_state['_clean_run_streak']} รอบติดแล้ว — "
            "fix ผ่านแล้ว ถึงคิวทำ pagination bug fix ต่อ (fetch_latest_page นับจากหน้าสุดท้ายอย่างเดียว) ครับ",
        )
        digest_state["_pagination_fix_reminder_sent"] = True
        log(f"Clean-run streak reached {digest_state['_clean_run_streak']} — sent pagination-fix reminder.")

    error_note = (
        f"\n\n⚠️ ERROR: parse โพสต์ได้ 0 ใน {', '.join(parse_errors)} (scrape พัง ไม่ใช่ไม่มีโพสต์)" if parse_errors else ""
    )
    if not new_by_ticker:
        save_digest_state()  # nothing to deliver -> safe to commit counts now
        if parse_errors:
            line_push(line_token, line_user, f"📊 อัปเดตกระทู้หุ้น รพ. {today_th}\n\nตัวที่เช็คได้ไม่มีโพสต์ใหม่{error_note}")
            log(f"No new posts in tickers that parsed; ERROR for {parse_errors} — sent notice with error.")
        else:
            line_push(line_token, line_user, f"📊 อัปเดตกระทู้หุ้น รพ. {today_th}\n\nวันนี้ไม่มีโพสต์ใหม่ในกระทู้ที่ติดตามทั้ง 6 ตัว (BCH/WPH/BDMS/CHG/VIH/RJH)")
            log("No new posts across all tickers — sent quiet-day notice.")
        return

    if DRY_RUN:
        log(f"[dry-run] would summarize new posts for {list(new_by_ticker)} via Claude + Notion; skipped.{error_note}")
        return

    # From here on, new posts are only committed (digest_state.json written) after the digest
    # is delivered. Any failure -> leave the file untouched so the next run re-sends them.
    client = anthropic.Anthropic(api_key=api_key)
    sections = []
    for ticker, posts in new_by_ticker.items():
        sections.append(f"=== {ticker} ({len(posts)} โพสต์ใหม่) ===\n" + "\n---\n".join(posts))
    raw_text = "\n\n".join(sections)

    prompt = f"""นี่คือโพสต์ใหม่วันนี้จากกระทู้ "ห้องร้อยคนร้อยหุ้น" (board.thaivi.org) ของหุ้นกลุ่มโรงพยาบาลที่ติดตามอยู่ 6 ตัว: BCH, WPH, BDMS, CHG, VIH, RJH

{raw_text}

สรุปเป็นข้อความสั้นๆ ภาษาไทย สำหรับส่งเข้า LINE (ไม่เกิน ~1500 ตัวอักษร):
- ตัวไหนมีคนคุยเยอะ/กระแสแรงวันนี้
- ประเด็นสำคัญที่ถูกพูดถึงแต่ละตัว (ตัวเลข ข่าว มุมมอง คำถามเด่น) แบบสั้นกระชับ
- ถ้าตัวไหนไม่มีโพสต์ใหม่ ไม่ต้องพูดถึง
- ห้ามใส่คำแนะนำซื้อ/ขาย เป็นแค่สรุปกระแสการพูดคุย
- ใช้ bullet สั้นๆ อ่านเร็วบนมือถือได้"""

    tickers_list = list(new_by_ticker.keys())

    def fail_undelivered(stage: str, can_line: bool = True):
        log(f"ERROR: digest for {tickers_list} not delivered ({stage}) — digest_state.json NOT written; "
            "posts stay unseen and will be re-sent next run. Exiting 4.")
        if can_line:
            line_push(
                line_token, line_user,
                f"❌ บอทเช็คกระทู้ ร้อยคนร้อยหุ้น ERROR {today_th}\n"
                f"มีโพสต์ใหม่ใน {', '.join(tickers_list)} แต่สรุป/ส่งไม่สำเร็จ ({stage}) — "
                "ยังไม่นับว่าอ่านแล้ว รอบหน้าจะส่งใหม่ครับ",
            )
        sys.exit(4)

    digest_text = summarize_with_claude(client, prompt)
    if not digest_text:
        fail_undelivered("Claude ไม่คืนข้อความ")

    first_ticker = tickers_list[0]
    try:
        notion_url = notion_helper.create_digest_page(
            title=f"หุ้น รพ. — {today_th} ({', '.join(tickers_list)})",
            source="thaivi ร้อยคนร้อยหุ้น",
            ticker_channel=", ".join(tickers_list),
            date_iso=datetime.now().strftime("%Y-%m-%d"),
            summary=digest_text[:500],
            link=f"https://board.thaivi.org/viewtopic.php?t={TICKERS[first_ticker]}",
            content_markdown=digest_text,
        )
    except Exception as e:  # noqa: BLE001
        log(f"Notion page creation failed: {type(e).__name__}: {e}")
        fail_undelivered("สร้างหน้า Notion ไม่ได้")
    log(f"Notion page created: {notion_url}")

    message = f"📊 กระแสหุ้น รพ. วันนี้ {today_th}\nมีความเคลื่อนไหว: {', '.join(tickers_list)}\n\nรายละเอียด: {notion_url}{error_note}"
    if not line_push(line_token, line_user, message):
        # Notion page exists; next run will create another one for the same posts (acceptable).
        fail_undelivered("ส่ง LINE ไม่ได้", can_line=False)
    save_digest_state()  # delivered -> now mark the posts seen
    log(f"Sent digest covering {tickers_list}")


def handle_crash(exc: BaseException) -> None:
    """Uncaught exception: log traceback (digest_log + stderr), LINE-alert once per error
    class, exit 5. Never writes digest_state.json."""
    tb = traceback.format_exc()
    log(f"CRASH: {type(exc).__name__}: {(str(exc).splitlines() or [''])[0][:200]}\n{tb}")
    traceback.print_exc()  # -> digest_launchd.err (bots_doctor reads it)
    err_class = type(exc).__name__
    short = (str(exc).splitlines() or [""])[0][:150]
    try:
        prev = json.loads(CRASH_ALERT_PATH.read_text(encoding="utf-8")).get("error_class")
    except Exception:  # noqa: BLE001 — missing/corrupt flag = not alerted yet
        prev = None
    if prev == err_class:
        log(f"Same crash class ({err_class}) already alerted last run — staying quiet. Exiting 5.")
        sys.exit(5)
    try:
        load_env()
        token, user = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"), os.environ.get("LINE_USER_ID")
        sent = bool(token and user) and line_push(
            token, user,
            f"❌ บอทเช็คกระทู้ ร้อยคนร้อยหุ้น ERROR {datetime.now().strftime('%d/%m/%Y')}\n"
            f"รันพังกลางทาง: {err_class}: {short}\n"
            "ยังไม่นับโพสต์ว่าอ่านแล้ว รอบหน้าจะลองใหม่ (ถ้าพังแบบเดิมซ้ำจะไม่เตือนอีก) ครับ",
        )
    except Exception as e:  # noqa: BLE001
        log(f"Crash alert LINE push itself failed: {type(e).__name__}: {e}")
        sent = False
    if sent and not DRY_RUN:
        CRASH_ALERT_PATH.write_text(json.dumps({"error_class": err_class, "ts": datetime.now(timezone.utc).isoformat(),
                                                "error": short}, ensure_ascii=False), encoding="utf-8")
    sys.exit(5)


def run() -> None:
    """Entry point: main() + crash handler. A run that ends without crashing (any exit code
    from main, incl. 2/3/4 which alert on their own) clears the crash-alert flag."""
    try:
        main()
    except SystemExit:
        CRASH_ALERT_PATH.unlink(missing_ok=True)
        raise
    except Exception as e:  # noqa: BLE001
        handle_crash(e)
    CRASH_ALERT_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    run()
