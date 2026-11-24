"""netwait.py — make launchd bots survive "Mac woke (DarkWake) but the network isn't up yet".

Call at the very start of a bot (stdlib only):

    import netwait
    netwait.hold_awake(log)                                   # keep the Mac awake while we run
    netwait.wait_for_network(("board.thaivi.org", "api.line.me"), log=log)  # may raise NetworkUnavailable

Why (2026-10-12): the Mac slept at 07:25, launchd ran the missed 07:30 PROSPECT job inside a
45-second maintenance DarkWake at 07:41:19 before Wi-Fi associated -> net::ERR_INTERNET_DISCONNECTED.

hold_awake(): spawns `/usr/bin/caffeinate -i -s -w <our pid>` as a CHILD process.
  -s = PreventSystemSleep: blocks every sleep incl. the 'Maintenance Sleep' that ends a DarkWake,
       but per `man caffeinate` only on AC power (this Mac mini is always on AC; on a laptop on
       battery -s is ignored and only -i applies, which isn't documented to hold a DarkWake).
  -i = PreventUserIdleSystemSleep (belt and braces). -w = released automatically when we exit.
  NOT via ProgramArguments: TCC attributes ~/Desktop access to the job's launched binary, so
  `caffeinate python3 …` in the plist would fail exactly like the old zsh wrapper (exit 127).

wait_for_network(): every host must resolve (DNS) and accept a TCP connect on 443. Checks with
backoff (5s doubling to 60s) for up to max_wait_s of wall-clock time. Logs exactly one outcome line:
  "network: ok (…)", or "network: waiting up to Ns — unreachable: …" then
  "network: up after Ns" / "network: never came up after Ns — unreachable: …" (then raises).
tools/bots_doctor.py reads these lines from the job's stdout log.
"""
import os
import socket
import subprocess
import time


class NetworkUnavailable(RuntimeError):
    """Raised when the hosts stay unreachable for the whole wait window."""


def hold_awake(log=print) -> bool:
    try:
        subprocess.Popen(["/usr/bin/caffeinate", "-i", "-s", "-w", str(os.getpid())],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError as e:  # never let keep-awake break the bot
        log(f"keep-awake: caffeinate failed: {e}")
        return False


def reachable(host: str, port: int = 443, timeout: float = 5.0) -> str | None:
    """None if host resolves and accepts TCP on port, else a short reason."""
    try:
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as e:
        return f"DNS {type(e).__name__}"
    try:
        socket.create_connection((host, port), timeout=timeout).close()
    except OSError as e:
        return f"TCP {type(e).__name__}"
    return None


def _fmt(down: dict) -> str:
    return ", ".join(f"{h} ({why})" for h, why in down.items())


def wait_for_network(hosts, max_wait_s: float = 600, log=print,
                     check=None, sleep=None, clock=None) -> float:
    """Return seconds waited (0.0 if up immediately); raise NetworkUnavailable after max_wait_s.
    Wall clock on purpose: if the Mac sleeps mid-wait anyway, we re-check once after waking
    instead of counting the sleep as network time. check/sleep/clock are injectable for tests
    (resolved at call time so monkeypatching netwait.reachable / netwait.time also works)."""
    check = check or reachable
    sleep = sleep or time.sleep
    clock = clock or time.time
    hosts = tuple(hosts)
    start = clock()
    down = {h: why for h in hosts if (why := check(h))}
    if not down:
        log(f"network: ok ({', '.join(hosts)})")
        return 0.0
    log(f"network: waiting up to {max_wait_s:.0f}s — unreachable: {_fmt(down)}")
    delay = 5.0
    while (elapsed := clock() - start) < max_wait_s:
        sleep(min(delay, max(1.0, max_wait_s - elapsed)))
        delay = min(delay * 2, 60.0)
        down = {h: why for h in hosts if (why := check(h))}
        if not down:
            waited = clock() - start
            log(f"network: up after {waited:.0f}s")
            return waited
    msg = f"network never came up after {elapsed:.0f}s — unreachable: {_fmt(down)}"
    log(f"network: {msg.removeprefix('network ')}")
    raise NetworkUnavailable(msg)
