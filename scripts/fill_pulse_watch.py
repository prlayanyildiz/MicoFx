"""Monday fill-rate pulse — wake when SpotBrent (or book) fill moves.

Read-only HTTP. No MT5. No config writes. Arms a bridge note + WAKE when
SpotBrent cumulative opened increases or book fill_rate rises — the P0
income check after bar+scale gate bind (Py/Grok 06.09).
"""
from __future__ import annotations

import http.cookiejar
import json
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
STATE = ROOT / ".bridge" / "FILL_PULSE_STATE.json"
WAKE = ROOT / ".bridge" / "WAKE.txt"
INBOX = ROOT / "cursor" / "FOR_CLAUDE.md"


def _session():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(PANEL + "/")
    return op


def _load() -> dict:
    if not STATE.is_file():
        return {}
    try:
        return json.loads(STATE.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def snapshot() -> dict:
    op = _session()
    body = json.loads(op.open(PANEL + "/api/analysis/entry-blocks").read().decode())
    cum = (body.get("cumulative") or {}).get("rows") or []
    by = {r.get("symbol"): r for r in cum if isinstance(r, dict)}
    spot = by.get("SpotBrent") or {}
    opened = sum(int(r.get("opened") or 0) for r in cum)
    signals = sum(int(r.get("signals") or 0) for r in cum)
    return {
        "spot_opened": int(spot.get("opened") or 0),
        "spot_signals": int(spot.get("signals") or 0),
        "spot_fill": float(spot.get("fill_rate") or 0.0),
        "book_opened": opened,
        "book_signals": signals,
        "book_fill": (opened / signals) if signals else 0.0,
        "at": datetime.now().isoformat(timespec="seconds"),
    }


def maybe_alert(cur: dict | None = None) -> list[str]:
    """Wake once when SpotBrent opens increase or book fill jumps ≥5pp."""
    now = cur if cur is not None else snapshot()
    prev = _load()
    lines: list[str] = []
    spot_up = int(now["spot_opened"]) > int(prev.get("spot_opened") or 0)
    book_prev = float(prev.get("book_fill") or 0.0)
    book_jump = float(now["book_fill"]) - book_prev >= 0.05 and int(
        now["book_opened"]
    ) > int(prev.get("book_opened") or 0)
    if not prev:
        _save({**now, "alerted_at": None})
        return ["baseline set"]
    if not (spot_up or book_jump):
        _save({**prev, **{k: now[k] for k in now}, "last_seen_at": now["at"]})
        return []
    if prev.get("alerted_sig") == (
        now["spot_opened"],
        now["book_opened"],
        round(now["book_fill"], 3),
    ):
        return []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = (
        f"# Cursor -> Claude -- {ts} -- FILL PULSE "
        f"(Spot {now['spot_opened']}/{now['spot_signals']} "
        f"fill={now['spot_fill']:.0%}; "
        f"book {now['book_opened']}/{now['book_signals']} "
        f"fill={now['book_fill']:.0%})\n\n"
        "Bar+scale gate bind sonrasi ilk hareket. Opt hala fill dogrulama "
        "sonrasi. msa gevsetme / FROZEN zorla yok.\n"
    )
    try:
        WAKE.write_text("WAKE fill pulse\n", encoding="utf-8")
        lines.append(f"wake -> {WAKE}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")
    try:
        prev_txt = INBOX.read_text(encoding="utf-8") if INBOX.is_file() else ""
        INBOX.write_text(body + ("\n---\n\n" + prev_txt if prev_txt else ""), encoding="utf-8")
        lines.append(f"inbox -> {INBOX}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    _save({
        **now,
        "alerted_at": now["at"],
        "alerted_sig": (now["spot_opened"], now["book_opened"], round(now["book_fill"], 3)),
    })
    print("AGENT_LOOP_WAKE_fill_pulse", flush=True)
    return lines


if __name__ == "__main__":
    snap = snapshot()
    print(json.dumps(snap, indent=2))
    for line in maybe_alert(snap):
        print(line)
