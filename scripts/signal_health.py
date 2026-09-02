"""Session signal health — warn when the book goes quiet too long."""
from __future__ import annotations

import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "logs" / "micofx.log"
PANEL = "http://127.0.0.1:8900"
ACTIVE = ("GER40", "JPN225", "NAS100", "US30")
# During open index sessions, no primary-leg signal for this long is worth flagging.
QUIET_HOURS = 2.5


def _session() -> dict[str, str]:
    req = urllib.request.Request(f"{PANEL}/", method="GET")
    resp = urllib.request.urlopen(req, timeout=10)
    cookies = resp.headers.get_all("Set-Cookie") or []
    h = {"Origin": PANEL}
    if cookies:
        h["Cookie"] = "; ".join(x.split(";")[0] for x in cookies)
    return h


def _last_signals() -> dict[str, float]:
    if not LOG.is_file():
        return {}
    pat = re.compile(
        r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) SIGNAL \[(\w+)\]")
    out: dict[str, float] = {}
    for line in LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        m = pat.match(line)
        if not m:
            continue
        sym = m.group(2)
        if sym not in ACTIVE:
            continue
        try:
            ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            continue
        out[sym] = max(out.get(sym, 0.0), ts)
    return out


def check_signal_health(headers: dict[str, str] | None = None) -> list[str]:
    """Return log lines for enabled symbols quiet too long while session open."""
    import json

    h = headers or _session()
    req = urllib.request.Request(f"{PANEL}/api/state", headers=h, method="GET")
    st = json.loads(urllib.request.urlopen(req, timeout=20).read())
    pos = len(st.get("positions") or [])
    mt5 = st.get("mt5") or {}
    if mt5.get("clock_stale"):
        return ["signal_health: saat kilidi aktif — sinyal beklenmiyor"]
    if pos > 0:
        return [f"signal_health: {pos} pozisyon acik — sessizlik normal olabilir"]

    now = time.time()
    last = _last_signals()
    lines: list[str] = []
    any_open = False
    for sym in ACTIVE:
        s = (st.get("states") or {}).get(sym) or {}
        if not (s.get("session") or {}).get("open"):
            continue
        any_open = True
        age_h = (now - last.get(sym, 0.0)) / 3600.0 if sym in last else 999.0
        note = s.get("note") or ""
        if age_h >= QUIET_HOURS:
            lines.append(
                f"signal_health {sym}: son sinyal {age_h:.1f}sa once, note={note}")
        elif note == "broker saati bayat":
            lines.append(f"signal_health {sym}: saat kilidi ({note})")

    if not any_open:
        lines.append("signal_health: aktif sembol seanslari kapali")
    elif not lines:
        newest = max((last.get(s, 0.0) for s in ACTIVE), default=0.0)
        if newest > 0:
            age = (now - newest) / 3600.0
            lines.append(f"signal_health: kitap aktif, en yeni sinyal {age:.1f}sa once")
        else:
            lines.append("signal_health: logda aktif sembol sinyali yok")
    return lines


def main() -> int:
    for line in check_signal_health():
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
