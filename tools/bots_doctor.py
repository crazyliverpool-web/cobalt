#!/usr/bin/env python3
"""bots_doctor.py — one-shot health check of every studio launchd bot.

Usage:  python3 -I tools/bots_doctor.py        (stdlib only; any cwd)

Prints one line per bot:  PASS|WARN|FAIL  <label>  <short reason>
and exits 1 if any bot FAILs (0 otherwise).

Read-only by design: never kickstarts a job, never sends LINE, never writes state.
Bots come from tools/bot_registry.py (shared with digest_watchdog.py / digest_catchup.py)
— a bot not registered there is invisible to the doctor.

Per bot, where it applies:
  1. launchd   loaded? `last exit code` from `launchctl print gui/<uid>/<label>` (0 = ok);
               loaded program/args still match the plist on disk
  2. heartbeat mtime vs threshold — exit 0 with a stale heartbeat = FAIL (silent bot)
  3. plist     python3.14 called directly (no shell), script exists, EnvironmentVariables PATH set
  4. env/bins  required .env keys present (names only), required binaries on the plist PATH
  5. stderr    a Traceback written to the job's stderr log in the last 72h = WARN
  6. bot state "fetch failed" vs "nothing new": ThaiVI per-thread parse counts + session cookie,
               YouTube RSS failures in the last run + Google OAuth token age, PROSPECT last log line
Why: "exit 0" and "ไม่มีอะไรใหม่" both look healthy while a bot is blind
(youtube-digest was dead 32 days). See guides/bots/README.md.
"""
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot_registry import BOTS, PYTHON, ROOT, YT_DIR  # noqa: E402

LAUNCH_AGENTS = os.path.expanduser("~/Library/LaunchAgents")
NOW = time.time()
ORDER = {"PASS": 0, "WARN": 1, "FAIL": 2}
TRACEBACK_WINDOW_H = 72
OAUTH_TESTING_DAYS = 7  # Google Cloud app in Testing mode: refresh token dies 7 days after consent


def hours(sec):
    return sec / 3600


def age_h(path):
    return hours(NOW - os.path.getmtime(path))


def fmt_age(h):
    return f"{h:.0f}h" if h < 72 else f"{h / 24:.1f}d"


def read_env_keys(path):
    keys = set()
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if v.strip():
                    keys.add(k.strip())
    return keys


def tail_lines(path, n=400):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read().splitlines()[-n:]


class Result:
    def __init__(self):
        self.issues = []  # (level, text)
        self.notes = []   # shown only when PASS

    def add(self, level, text):
        if level == "PASS":
            self.notes.append(text)
        else:
            self.issues.append((level, text))

    @property
    def level(self):
        return max((lvl for lvl, _ in self.issues), key=ORDER.get, default="PASS")

    def reason(self):
        if not self.issues:
            return ", ".join(self.notes) or "ok"
        ranked = sorted(self.issues, key=lambda x: -ORDER[x[0]])
        return "; ".join(t for _, t in ranked)


# ---------------------------------------------------------------- generic checks

def launchctl_print(label):
    p = subprocess.run(["launchctl", "print", f"gui/{os.getuid()}/{label}"],
                       capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def parse_launchctl(out):
    info = {}
    m = re.search(r"^\s*last exit code = (.+)$", out, re.M)
    info["last_exit"] = m.group(1).strip() if m else None
    m = re.search(r"^\s*runs = (\d+)$", out, re.M)
    info["runs"] = int(m.group(1)) if m else None
    m = re.search(r"^\s*program = (.+)$", out, re.M)
    info["program"] = m.group(1).strip() if m else None
    m = re.search(r"^\s*arguments = \{\n(.*?)\n\s*\}", out, re.M | re.S)
    info["args"] = [a.strip() for a in m.group(1).splitlines()] if m else []
    return info


EXIT_HINTS = {
    "127": "can't open script — TCC/shell wrapper? see guardrails",
    "126": "not executable",
    "1": "script error/abort",
}


def check_launchd(bot, plist, r, expect_never_ran=False):
    """Loaded? last exit code; loaded program/args still match the plist on disk."""
    out = launchctl_print(bot.label)
    if out is None:
        r.add("FAIL", "not loaded in launchd (bootstrap the plist)")
        return None
    info = parse_launchctl(out)
    code = info["last_exit"]
    if code is None:
        r.add("WARN", "couldn't read last exit code")
    elif code.startswith("(never"):
        # normal after a reboot until the next scheduled slot; silence is caught by the heartbeat check
        r.add("PASS", "not run since load" if not expect_never_ran else "not run yet (expected)")
    elif code != "0":
        hint = bot_exit_hint(bot, code) or EXIT_HINTS.get(code, "")
        r.add("FAIL", f"last exit {code}" + (f" ({hint})" if hint else ""))
    else:
        r.add("PASS", "exit 0")
    if plist:
        pa = plist.get("ProgramArguments", [])
        if pa and ((info["program"] and info["program"] != pa[0]) or (info["args"] and info["args"][:2] != pa[:2])):
            r.add("WARN", "loaded job differs from plist on disk — bootout+bootstrap to reload")
    return info


def bot_exit_hint(bot, code):
    if bot.label == "com.alonsi.roikonroihoon-digest":
        return {"2": "ThaiVI session expired + auto-relogin failed",
                "3": "logged in but 0 posts parsed in every thread — selector changed",
                "4": "new posts found but Claude/Notion/LINE failed — not marked seen, next run re-sends",
                "5": "crashed (uncaught exception, e.g. page-load timeout after retry) — see digest_log.txt CRASH; "
                     "alerted once per error class",
                "1": "missing .env keys, or (pre-2026-10-11 code) an uncaught crash"}.get(code)
    if bot.label == "com.alonsi.youtube-digest":
        return {"2": "RSS fetch failed for every channel — saw nothing"}.get(code)
    if bot.label == "com.alonsi.prospect-occupancy-watch":
        return {"1": "SET page fetch failed after retries, new-filing LINE not delivered, or missing env — see log",
                "5": "crashed (uncaught exception) — traceback in prospect_occupancy_watch_launchd.err"}.get(code)
    return None


def check_plist(bot, r):
    path = os.path.join(LAUNCH_AGENTS, f"{bot.label}.plist")
    if not os.path.exists(path):
        r.add("FAIL", f"plist missing: {path}")
        return None
    try:
        with open(path, "rb") as f:
            plist = plistlib.load(f)
    except Exception as e:  # noqa: BLE001
        r.add("FAIL", f"plist unreadable: {e}")
        return None
    pa = plist.get("ProgramArguments", [])
    if not pa:
        r.add("FAIL", "plist has no ProgramArguments")
        return plist
    if pa[0] in ("/bin/zsh", "/bin/sh", "/bin/bash"):
        r.add("FAIL", f"plist runs via shell {pa[0]} (TCC blocks Desktop -> exit 127)")
    elif pa[0] != PYTHON:
        r.add("FAIL", f"plist interpreter is {pa[0]}, expected {PYTHON}")
    elif not os.path.exists(PYTHON):
        r.add("FAIL", "python 3.14 binary missing (Python upgraded? update every plist + TCC)")
    script = pa[1] if len(pa) > 1 else None
    if not script or not os.path.exists(script):
        r.add("FAIL", f"plist script missing: {script}")
    elif os.path.realpath(script) != os.path.realpath(bot.script):
        r.add("WARN", f"plist script {script} != registry {bot.script}")
    if not plist.get("EnvironmentVariables", {}).get("PATH"):
        r.add("WARN", "plist has no EnvironmentVariables PATH (guardrails rule)")
    return plist


def check_heartbeat(bot, r):
    if not bot.heartbeat:
        return None
    if not os.path.exists(bot.heartbeat):
        r.add("FAIL", f"heartbeat missing ({os.path.relpath(bot.heartbeat, ROOT)}) — never ran OK")
        return None
    a = age_h(bot.heartbeat)
    if bot.stale_hours and a > bot.stale_hours:
        r.add("FAIL", f"silent: heartbeat {fmt_age(a)} old (limit {bot.stale_hours}h)")
    else:
        r.add("PASS", f"heartbeat {fmt_age(a)} old")
    return a


def check_env_and_bins(bot, plist, r):
    if bot.env_keys:
        have = set()
        for f in bot.env_files:
            have |= read_env_keys(f)
        missing = [k for k in bot.env_keys if k not in have]
        if missing:
            r.add("FAIL", f"missing .env keys: {', '.join(missing)}")
    if bot.path_bins:
        path = (plist or {}).get("EnvironmentVariables", {}).get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
        for b in bot.path_bins:
            if not shutil.which(b, path=path):
                r.add("FAIL", f"{b} not found on plist PATH")


def check_stderr(plist, r):
    err = (plist or {}).get("StandardErrorPath")
    if not err or not os.path.exists(err) or os.path.getsize(err) == 0:
        return
    a = age_h(err)
    if a > TRACEBACK_WINDOW_H:
        return
    text = "\n".join(tail_lines(err, 200))
    if "Traceback" in text:
        last_exc = [l for l in text.splitlines() if re.match(r"^[\w.]+(Error|Exception|Iteration)\b", l)]
        what = last_exc[-1][:80] if last_exc else "Traceback"
        r.add("WARN", f"crash {fmt_age(a)} ago in {os.path.basename(err)}: {what}")


# ---------------------------------------------------------------- bot-specific checks

def check_thaivi(bot, r):
    try:
        st = json.load(open(bot.heartbeat, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        r.add("FAIL", f"digest_state.json unreadable: {e}")
        return
    if st.get("_session_alert_sent"):
        r.add("FAIL", "ThaiVI session expired (bot already alerted) — user must run login_and_fetch.py")
    tickers = {k: v for k, v in st.items() if not k.startswith("_") and isinstance(v, dict)}
    zero = [k for k, v in tickers.items() if not v.get("last_post_count")]
    stale = []
    for k, v in tickers.items():
        try:
            ts = datetime.fromisoformat(v["last_checked"]).timestamp()
            if hours(NOW - ts) > bot.stale_hours:
                stale.append(k)
        except Exception:  # noqa: BLE001
            stale.append(k)
    if zero:
        r.add("FAIL", f"0 posts recorded for {'/'.join(zero)} (scrape failure, not a quiet day)")
    if stale:
        r.add("FAIL", f"not parsed in >{bot.stale_hours}h: {'/'.join(stale)} (heartbeat fresh but threads failing)")
    if not zero and not stale:
        r.add("PASS", f"{len(tickers)}/{len(tickers)} threads parsed")
    # session cookie (phpBB autologin key, rotated each successful run)
    sess = os.path.join(ROOT, "stock-research", "thaivi", "thaivi_state.json")
    try:
        cookies = json.load(open(sess, encoding="utf-8")).get("cookies", [])
    except Exception as e:  # noqa: BLE001
        r.add("FAIL", f"thaivi_state.json unreadable: {e}")
        return
    k = [c for c in cookies if c.get("name", "").endswith("_k") and "thaivi" in c.get("domain", "")]
    if not k:
        r.add("FAIL", "thaivi_state.json has no phpBB autologin (_k) cookie — login again")
        return
    exp = max(c.get("expires", -1) for c in k)
    days = (exp - NOW) / 86400
    if exp <= 0:
        r.add("WARN", "ThaiVI autologin cookie is session-only (dies with browser) — relogin with 'remember me'")
    elif days < 0:
        r.add("FAIL", f"ThaiVI autologin cookie expired {datetime.fromtimestamp(exp):%Y-%m-%d}")
    elif days < 30:
        r.add("WARN", f"ThaiVI autologin cookie expires in {days:.0f}d ({datetime.fromtimestamp(exp):%Y-%m-%d})")
    else:
        r.add("PASS", f"cookie to {datetime.fromtimestamp(exp):%Y-%m-%d}")


YT_RUN_END = ("No new videos. Exiting cleanly.", "Sent LINE digest", "No videos successfully summarized",
              "ERROR:")  # "ERROR: missing env" / "ERROR: RSS fetch failed for all N channels"


def check_youtube(bot, plist, r):
    try:
        hb = json.load(open(bot.heartbeat, encoding="utf-8"))
        if hb.get("status") != "ok":
            r.add("FAIL", f"heartbeat status={hb.get('status')!r}")
    except Exception as e:  # noqa: BLE001
        r.add("WARN", f"heartbeat unreadable: {e}")
    # last run(s) from stdout log: "No new videos" after every RSS fetch failed = blind, not quiet
    out = (plist or {}).get("StandardOutPath")
    channels_path = os.path.join(YT_DIR, "config", "channels.json")
    try:
        n_ch = len([c for c in json.load(open(channels_path, encoding="utf-8")) if c.get("enabled", True)])
    except Exception as e:  # noqa: BLE001
        r.add("WARN", f"channels.json unreadable: {e}")
        n_ch = None
    if out and os.path.exists(out) and n_ch:
        if abs(os.path.getmtime(out) - os.path.getmtime(bot.heartbeat)) > 600:
            r.add("WARN", "stdout log and heartbeat from different runs — can't verify RSS fetch")
        else:
            lines = tail_lines(out)
            ends = [i for i, l in enumerate(lines) if l.startswith(YT_RUN_END)]
            runs, start = [], 0
            for e in ends:
                runs.append(lines[start:e + 1])
                start = e + 1
            blind = 0
            for run in reversed(runs):
                fails = sum(l.startswith("WARN: RSS fetch failed") for l in run)
                if fails >= n_ch:
                    blind += 1
                else:
                    break
            last_fails = sum(l.startswith("WARN: RSS fetch failed") for l in runs[-1]) if runs else 0
            if blind:
                quiet = runs[-1][-1].startswith("No new videos")  # pre-2026-10-11 code faked a quiet day
                r.add("FAIL", f"RSS fetch failed for all {n_ch} channels in last {blind} run(s) — saw nothing"
                              + (" (logged 'No new videos')" if quiet else ""))
            elif last_fails:
                r.add("WARN", f"RSS fetch failed for {last_fails}/{n_ch} channels in last run")
            elif runs:
                r.add("PASS", f"RSS ok {n_ch}/{n_ch}")
    # Google auth for the Sheet (only exercised when new videos are found)
    if os.path.exists(os.path.join(YT_DIR, "data", "service_account.json")):
        r.add("PASS", "Google service account")
        return
    tok = os.path.join(YT_DIR, "data", "google_oauth_token.json")
    if not os.path.exists(tok):
        r.add("FAIL", "no Google OAuth token / service account — next new video will crash")
        return
    err = (plist or {}).get("StandardErrorPath")
    if err and os.path.exists(err) and os.path.getmtime(err) > os.path.getmtime(tok) \
            and "invalid_grant" in "\n".join(tail_lines(err, 60)):
        r.add("FAIL", "Google OAuth refresh failed (invalid_grant) after last token write — re-consent")
        return
    tok_days = age_h(tok) / 24
    dies_by = datetime.fromtimestamp(os.path.getmtime(tok) + OAUTH_TESTING_DAYS * 86400)
    if tok_days >= OAUTH_TESTING_DAYS:
        r.add("WARN", f"Google OAuth token last written {tok_days:.0f}d ago — Testing-mode token likely dead; "
                      "next run with new videos will crash (use service account)")
    elif tok_days >= OAUTH_TESTING_DAYS - 2:
        r.add("WARN", f"Google OAuth (Testing mode) dies by {dies_by:%Y-%m-%d %H:%M} at the latest")
    else:
        r.add("PASS", f"OAuth ok until <= {dies_by:%m-%d}")


# log lines that never decide a run's outcome (alerts/retries around the real result)
PROSPECT_NOISE = ("LINE push", "[dry-run]", "goto failed", "networkidle not reached", "Crash alert")


def check_prospect(bot, r):
    # only "[ts] msg" lines: old code logged Playwright's multi-line "Call log" too
    lines = [l for l in tail_lines(bot.heartbeat, 80) if l.startswith("[")]
    msgs = [re.sub(r"^\[[^\]]+\]\s*", "", l) for l in lines]
    msgs = [m for m in msgs if not m.startswith(PROSPECT_NOISE)]
    if not msgs:
        r.add("FAIL", "log has no run outcome")
        return
    last = msgs[-1]
    if last.startswith(("fetch failed", "Missing LINE", "CRASH", "New-filing alert not delivered")):
        r.add("FAIL", f"last run: {last[:90]}")
    elif last.startswith("No matching filing"):
        n = 0
        for m in reversed(msgs):
            if m.startswith("No matching filing"):
                n += 1
            else:
                break
        r.add("WARN", f"no MD&A/F45/financial statement found on SET news tab {n} run(s) in a row — the page rendered "
                      "but the parser matched nothing (title wording/layout changed?) — check set.or.th by hand")
    elif last.startswith(("No change", "New filing", "LINE push OK")):
        r.add("PASS", "last run parsed the latest filing")
    else:
        r.add("WARN", f"unrecognised last log line: {last[:80]}")


def check_watchdog(bot, r):
    if not os.path.exists(bot.heartbeat):
        return
    lines = [l for l in tail_lines(bot.heartbeat, 20) if l.strip()]
    last = lines[-1] if lines else ""
    if last.startswith("ERROR"):
        r.add("FAIL", f"last run: {last[:90]}")
    elif last == "Alert sent.":
        r.add("WARN", "watchdog sent a stale-bot alert on its last run")


def check_relogin(bot, plist, info, r):
    sci = (plist or {}).get("StartCalendarInterval", {})
    try:
        when = datetime(sci["Year"], sci["Month"], sci["Day"], sci.get("Hour", 0), sci.get("Minute", 0))
    except Exception:  # noqa: BLE001
        r.add("WARN", "plist StartCalendarInterval has no full Year/Month/Day date")
        return
    log = (plist or {}).get("StandardOutPath")
    fired = bool((info and (info.get("runs") or 0) > 0)
                 or (log and os.path.exists(log) and os.path.getsize(log) > 0))
    if datetime.now() < when and fired:
        r.add("WARN", f"reminder already fired before {when:%Y-%m-%d} — launchd ignored Year?")
    elif datetime.now() >= when and not fired:
        r.add("WARN", f"reminder due {when:%Y-%m-%d} but never fired — relogin ThaiVI by hand")
    elif datetime.now() >= when:
        r.add("WARN", f"reminder fired ({when:%Y-%m-%d}) — after relogin, move date +1y and reload plist")
    else:
        r.add("PASS", f"scheduled {when:%Y-%m-%d %H:%M}")


# ---------------------------------------------------------------- main

def doctor(bot):
    r = Result()
    plist = check_plist(bot, r)
    one_shot = bot.label == "com.alonsi.thaivi-relogin-reminder"
    no_schedule_ok = bot.label == "com.alonsi.digest-catchup"
    info = check_launchd(bot, plist, r, expect_never_ran=one_shot or no_schedule_ok)
    check_heartbeat(bot, r)
    check_env_and_bins(bot, plist, r)
    check_stderr(plist, r)
    hb_ok = bot.heartbeat and os.path.exists(bot.heartbeat)
    if bot.label == "com.alonsi.roikonroihoon-digest" and hb_ok:
        check_thaivi(bot, r)
    elif bot.label == "com.alonsi.youtube-digest" and hb_ok:
        check_youtube(bot, plist, r)
    elif bot.label == "com.alonsi.prospect-occupancy-watch" and hb_ok:
        check_prospect(bot, r)
    elif bot.label == "com.alonsi.digest-watchdog":
        check_watchdog(bot, r)
    elif one_shot:
        check_relogin(bot, plist, info, r)
    return r


def main():
    any_fail = False
    for bot in BOTS:
        try:
            r = doctor(bot)
            level, reason = r.level, r.reason()
        except Exception as e:  # noqa: BLE001 — a doctor crash must not hide other bots
            level, reason = "FAIL", f"doctor error: {type(e).__name__}: {e}"
        any_fail |= level == "FAIL"
        print(f"{level:<4}  {bot.label:<38}  {reason}")
    # launchd jobs that exist but aren't registered = nobody (doctor/watchdog/catchup) watches them
    known = {b.label for b in BOTS}
    extra = sorted(f[:-6] for f in os.listdir(LAUNCH_AGENTS)
                   if f.startswith("com.alonsi.") and f.endswith(".plist") and f[:-6] not in known)
    for label in extra:
        print(f"WARN  {label:<38}  plist not in tools/bot_registry.py — unmonitored")
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
