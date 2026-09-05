"""Book silence watch — per-symbol session-inside gap (~1 fire/month).

Report-only. Quiet first bars are normal; a long *in-session* stretch with
zero *new* entry-block signals (vs stamp at first in-window tick) can mean
bars/session/clock stuck. Do not use raw 7d rolling totals.

Thresholds (Claude 11:34 / 12:04): per-symbol session-inside minutes
calibrated to ~1 fire/month. p50/270 joint was ~115 false alarms/month —
rejected. Gaps accumulate across days inside each symbol's session only
(not overnight / out-of-session). EU channel_break (GER40/US30) landed
first; full book 12:04 with live session windows.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / ".bridge" / "SESSION_OPEN_SILENCE.json"
PANEL = "http://127.0.0.1:8900"

# (thresh_min, h_lo, h_hi, wrap). Hours inclusive; wrap=True => overnight
# session (lo > hi). Window must match *tradable* mask, not leftover
# sessions JSON: JPN225 use_sessions=False => 100% tradable (Claude 13:52),
# so 2520min is wall-clock like BTC/XAU — not the unread 23-08 wrap.
BOOK: dict[str, tuple[int, int, int, bool]] = {
    "GER40": (870, 8, 15, False),
    "US30": (1680, 8, 16, False),
    "NAS100": (690, 15, 21, False),
    "JPN225": (2520, 0, 23, False),
    "BTCUSD": (3630, 0, 23, False),
    "SpotBrent": (510, 14, 22, False),
    "XAUUSD": (960, 0, 23, False),
}
SYMBOLS: tuple[str, ...] = tuple(BOOK.keys())
SILENCE_THRESH_MIN: dict[str, int] = {s: BOOK[s][0] for s in SYMBOLS}
# Legacy aliases (GER40 EU floor) for older callers/tests.
SILENCE_AFTER_MIN = SILENCE_THRESH_MIN["GER40"]
SESSION_H_LO = 8
SESSION_H_HI = 15


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def broker_hm(panel: str = PANEL) -> tuple[int | None, int | None]:
    """Return (hour, minute) from mt5.server_time, or (None, None)."""
    import http.cookiejar

    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    try:
        op.open(panel + "/")
        st = json.loads(
            op.open(
                urllib.request.Request(
                    panel + "/api/state", headers={"Origin": panel})
            ).read().decode()
        )
    except (OSError, json.JSONDecodeError, urllib.error.URLError):
        return None, None
    stamp = str((st.get("mt5") or {}).get("server_time") or "")
    parts = stamp.replace("T", " ").split()
    if len(parts) < 2:
        return None, None
    try:
        hh, mm, *_ = parts[1].split(":")
        return int(hh), int(mm)
    except (TypeError, ValueError, IndexError):
        return None, None


def session_day_key(broker_h: int | None) -> str:
    return datetime.now().strftime("%Y-%m-%d")


def in_session(
    broker_h: int | None,
    *,
    h_lo: int,
    h_hi: int,
    wrap: bool = False,
) -> bool:
    if broker_h is None:
        return False
    h = int(broker_h)
    if wrap:
        return h >= int(h_lo) or h <= int(h_hi)
    return int(h_lo) <= h <= int(h_hi)


def minutes_open_in_session(
    broker_h: int | None,
    broker_min: int | None = None,
    *,
    h_lo: int = SESSION_H_LO,
    h_hi: int = SESSION_H_HI,
    wrap: bool = False,
) -> int | None:
    """Minutes since session open for this window; None if out of session."""
    if not in_session(broker_h, h_lo=h_lo, h_hi=h_hi, wrap=wrap):
        return None
    h = int(broker_h)  # type: ignore[arg-type]
    m = int(broker_min or 0)
    if wrap:
        if h >= int(h_lo):
            return (h - int(h_lo)) * 60 + m
        return (24 - int(h_lo)) * 60 + h * 60 + m
    return (h - int(h_lo)) * 60 + m


def ensure_open_stamp(
    raw_signals: dict[str, int],
    *,
    in_window: bool,
    day: str,
    state_path: Path | None = None,
    symbols: tuple[str, ...] | None = None,
) -> dict[str, int]:
    """Stamp absolute rolling counts at first in-window sight; return delta.

    ``in_window`` here means *any* focus symbol is in its session (stamp
    ownership). Per-symbol silence uses per-symbol windows in evaluate.
    """
    syms = symbols or SYMBOLS
    path = state_path if state_path is not None else STATE_PATH
    state = _load(path)
    stamped_day = str(state.get("stamp_day") or "")
    base = state.get("stamp_signals") or {}
    if not in_window:
        return dict.fromkeys(syms, 0)
    if stamped_day != day or not isinstance(base, dict):
        stamp = {s: int(raw_signals.get(s) or 0) for s in syms}
        state["stamp_day"] = day
        state["stamp_signals"] = stamp
        state["stamped_at"] = datetime.now().isoformat(timespec="seconds")
        _save(path, state)
        return dict.fromkeys(syms, 0)
    # Book expand mid-day: seed missing symbols at current raw (0 delta).
    missing = [s for s in syms if s not in base]
    if missing:
        base = dict(base)
        for s in missing:
            base[s] = int(raw_signals.get(s) or 0)
        state["stamp_signals"] = base
        _save(path, state)
    return {
        s: max(0, int(raw_signals.get(s) or 0) - int(base.get(s) or 0))
        for s in syms
    }


def update_session_gaps(
    *,
    signals: dict[str, int],
    minutes_open_by_sym: dict[str, int | None],
    in_window_by_sym: dict[str, bool],
    day: str,
    state_path: Path | None = None,
) -> dict[str, int]:
    """Accumulate per-symbol session-inside silent minutes across days."""
    path = state_path if state_path is not None else STATE_PATH
    state = _load(path)
    gaps = {
        s: int((state.get("gaps") or {}).get(s) or 0) for s in SYMBOLS
    }
    alerted = dict(state.get("gap_alerted") or {})
    tick_day = dict(state.get("gap_tick_day_by") or {})
    tick_mo = dict(state.get("gap_tick_mo_by") or {})

    for s in SYMBOLS:
        if not in_window_by_sym.get(s):
            continue
        mo = minutes_open_by_sym.get(s)
        if mo is None:
            continue
        last_day = str(tick_day.get(s) or "")
        try:
            last_mo = int(tick_mo.get(s) or 0)
        except (TypeError, ValueError):
            last_mo = 0
        if s not in tick_day:
            # First sight / book-expand: seed tick. Catch up gap to today's
            # minutes_open when starting from 0; keep non-zero gaps (migrate).
            if int(signals.get(s) or 0) > 0:
                gaps[s] = 0
                alerted.pop(s, None)
            elif int(gaps[s]) == 0:
                gaps[s] = int(mo)
            tick_day[s] = day
            tick_mo[s] = int(mo)
            continue
        base_mo = last_mo if last_day == day else 0
        delta_mo = max(0, int(mo) - base_mo)
        if int(signals.get(s) or 0) > 0:
            gaps[s] = 0
            alerted.pop(s, None)
        else:
            gaps[s] = int(gaps[s]) + delta_mo
        tick_day[s] = day
        tick_mo[s] = int(mo)

    state["gaps"] = gaps
    state["gap_alerted"] = alerted
    state["gap_tick_day_by"] = tick_day
    state["gap_tick_mo_by"] = tick_mo
    # Legacy joint fields (GER40) for older readers.
    if "GER40" in tick_mo:
        state["gap_tick_day"] = tick_day.get("GER40")
        state["gap_tick_mo"] = tick_mo.get("GER40")
    _save(path, state)
    return gaps


def snapshot(
    panel: str = PANEL,
    *,
    silence_after_min: int | None = None,
    thresholds: dict[str, int] | None = None,
    state_path: Path | None = None,
) -> dict[str, Any]:
    bh, bm = broker_hm(panel)
    try:
        raw = fetch_signal_counts(panel)
    except (OSError, json.JSONDecodeError, urllib.error.URLError):
        raw = dict.fromkeys(SYMBOLS, 0)

    in_by: dict[str, bool] = {}
    mo_by: dict[str, int | None] = {}
    for s, (thresh, lo, hi, wrap) in BOOK.items():
        in_by[s] = in_session(bh, h_lo=lo, h_hi=hi, wrap=wrap)
        mo_by[s] = minutes_open_in_session(
            bh, bm, h_lo=lo, h_hi=hi, wrap=wrap)
        _ = thresh  # thresholds applied in evaluate

    any_in = any(in_by.values())
    day = session_day_key(bh)
    delta = ensure_open_stamp(
        raw, in_window=any_in, day=day, state_path=state_path)
    gaps = update_session_gaps(
        signals=delta,
        minutes_open_by_sym=mo_by,
        in_window_by_sym=in_by,
        day=day,
        state_path=state_path,
    )
    thr = dict(thresholds or SILENCE_THRESH_MIN)
    if silence_after_min is not None:
        thr = {s: int(silence_after_min) for s in SYMBOLS}
    out = evaluate(
        broker_h=bh,
        broker_min=bm,
        signals=delta,
        gaps=gaps,
        thresholds=thr,
        raw_signals=raw,
        in_window_by_sym=in_by,
        minutes_open_by_sym=mo_by,
    )
    try:
        out["bar_health"] = fetch_bar_health(panel)
    except Exception:
        out["bar_health"] = {"overall": "unknown"}
    return out


def fetch_signal_counts(
    panel: str = PANEL,
    *,
    symbols: tuple[str, ...] = SYMBOLS,
) -> dict[str, int]:
    import http.cookiejar

    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/analysis/entry-blocks",
                headers={"Origin": panel},
            )
        ).read().decode()
    )
    out = dict.fromkeys(symbols, 0)
    for row in body.get("rows") or []:
        sym = str(row.get("symbol") or "")
        if sym in out:
            out[sym] = int(row.get("signals") or 0)
    return out


def evaluate(
    *,
    broker_h: int | None,
    broker_min: int | None = None,
    signals: dict[str, int] | None = None,
    silence_after_min: int | None = None,
    gaps: dict[str, int] | None = None,
    thresholds: dict[str, int] | None = None,
    raw_signals: dict[str, int] | None = None,
    in_window_by_sym: dict[str, bool] | None = None,
    minutes_open_by_sym: dict[str, int | None] | None = None,
) -> dict[str, Any]:
    """Fire when any in-session symbol's silent gap hits its ~1/mo threshold."""
    sigs = {s: int((signals or {}).get(s) or 0) for s in SYMBOLS}
    thr = dict(thresholds or SILENCE_THRESH_MIN)
    if silence_after_min is not None:
        thr = {s: int(silence_after_min) for s in SYMBOLS}

    in_by: dict[str, bool] = {}
    mo_by: dict[str, int | None] = {}
    for s, (_, lo, hi, wrap) in BOOK.items():
        if in_window_by_sym is not None and s in in_window_by_sym:
            in_by[s] = bool(in_window_by_sym[s])
        else:
            in_by[s] = in_session(broker_h, h_lo=lo, h_hi=hi, wrap=wrap)
        if minutes_open_by_sym is not None and s in minutes_open_by_sym:
            mo_by[s] = minutes_open_by_sym[s]
        else:
            mo_by[s] = minutes_open_in_session(
                broker_h, broker_min, h_lo=lo, h_hi=hi, wrap=wrap)

    if gaps is None:
        g: dict[str, int] = {}
        for s in SYMBOLS:
            g[s] = (
                int(mo_by[s] or 0)
                if int(sigs.get(s) or 0) == 0 and mo_by[s] is not None
                else 0
            )
        gaps = g
    else:
        gaps = {s: int(gaps.get(s) or 0) for s in SYMBOLS}

    fire_syms = [
        s for s in SYMBOLS
        if in_by.get(s)
        and int(sigs.get(s) or 0) == 0
        and gaps[s] >= int(thr.get(s) or 10**9)
    ]
    fire = bool(fire_syms)
    # Legacy joint EU fields for income / older logs.
    eu_mo = mo_by.get("GER40")
    if eu_mo is None:
        eu_mo = mo_by.get("US30")
    total_sig = sum(int(sigs.get(s) or 0) for s in ("GER40", "US30"))
    out: dict[str, Any] = {
        "in_window": any(in_by.values()),
        "minutes_open": eu_mo,
        "signals": {s: int(sigs.get(s) or 0) for s in ("GER40", "US30")},
        "signals_all": sigs,
        "total_signals": total_sig,
        "silence_after_min": int(thr.get("GER40") or SILENCE_AFTER_MIN),
        "thresholds_min": {s: int(thr.get(s) or 0) for s in SYMBOLS},
        "gaps_min": gaps,
        "in_window_by": in_by,
        "minutes_open_by": mo_by,
        "fire_syms": fire_syms,
        "fire": fire,
    }
    if raw_signals is not None:
        out["raw_signals"] = {s: int(raw_signals.get(s) or 0) for s in SYMBOLS}
    return out


def classify_bar_health(
    *,
    last_bars: dict[str, int | None],
    broker_epoch: int | None,
    max_age_sec: int = 75 * 60,
    symbols: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Quiet vs stuck: M30 closed-bar age vs broker clock."""
    syms = symbols or ("GER40", "US30")
    per: dict[str, Any] = {}
    worst = "ok"
    for sym in syms:
        lb = last_bars.get(sym)
        age = None
        status = "missing"
        if broker_epoch is not None and lb is not None and int(lb) > 0:
            age = max(0, int(broker_epoch) - int(lb))
            status = "stuck" if age > int(max_age_sec) else "ok"
        per[sym] = {"last_bar": lb, "age_sec": age, "status": status}
        if status == "stuck":
            worst = "stuck"
        elif status == "missing" and worst == "ok":
            worst = "missing"
    return {"overall": worst, "symbols": per, "max_age_sec": int(max_age_sec)}


def fetch_bar_health(panel: str = PANEL) -> dict[str, Any]:
    """Live last_bar ages for silence evidence (data-gap vs quiet)."""
    import http.cookiejar
    import time as _time

    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    try:
        op.open(panel + "/")
        st = json.loads(
            op.open(
                urllib.request.Request(
                    panel + "/api/state", headers={"Origin": panel})
            ).read().decode()
        )
    except (OSError, json.JSONDecodeError, urllib.error.URLError):
        return classify_bar_health(last_bars={}, broker_epoch=None)
    stamp = str((st.get("mt5") or {}).get("server_time") or "")
    broker_epoch = None
    parts = stamp.replace("T", " ").split()
    try:
        broker_epoch = int((st.get("mt5") or {}).get("server_time_epoch") or 0) or None
    except (TypeError, ValueError):
        broker_epoch = None
    if broker_epoch is None and len(parts) >= 2:
        try:
            import calendar
            broker_epoch = int(calendar.timegm(_time.strptime(
                f"{parts[0]} {parts[1]}", "%Y-%m-%d %H:%M:%S")))
        except (ValueError, OverflowError):
            broker_epoch = None
    states = st.get("states") or {}
    last_bars: dict[str, int | None] = {}
    for sym in ("GER40", "US30"):
        row = states.get(sym) or {}
        try:
            last_bars[sym] = int(row.get("last_bar") or 0) or None
        except (TypeError, ValueError):
            last_bars[sym] = None
    return classify_bar_health(last_bars=last_bars, broker_epoch=broker_epoch)


def maybe_alert(
    report: dict[str, Any],
    *,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    if not report.get("fire"):
        return []
    path = state_path if state_path is not None else STATE_PATH
    state = _load(path)
    fire_syms = list(report.get("fire_syms") or [])
    if not fire_syms:
        return []
    alerted = dict(state.get("gap_alerted") or {})
    new_syms = [s for s in fire_syms if not alerted.get(s)]
    if not new_syms:
        return []
    wake = wake_path if wake_path is not None else (ROOT / ".bridge" / "WAKE.txt")
    inbox = cursor_inbox if cursor_inbox is not None else (
        ROOT / "cursor" / "FOR_CLAUDE.md")
    lines: list[str] = []
    try:
        wake.parent.mkdir(parents=True, exist_ok=True)
        wake.write_text("WAKE\n", encoding="utf-8")
        lines.append(f"wake -> {wake}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    gaps = report.get("gaps_min") or {}
    thr = report.get("thresholds_min") or SILENCE_THRESH_MIN
    health = report.get("bar_health")
    if not isinstance(health, dict):
        try:
            health = fetch_bar_health()
        except Exception:
            health = {"overall": "unknown"}
    lean = (
        "gercek-quiet (bars ok)" if health.get("overall") == "ok"
        else "data-gap smell (bars stuck/missing)" if health.get("overall") in (
            "stuck", "missing") else "bars unknown"
    )
    body = (
        f"# Cursor -> Claude -- {ts} -- BOOK SILENCE (~1/mo): "
        f"{','.join(new_syms)} gap hit.\n\n"
        f"gaps_min={ {s: gaps.get(s) for s in new_syms} } "
        f"thr={ {s: thr.get(s) for s in new_syms} } "
        f"delta={report.get('signals_all') or report.get('signals')}. "
        f"bar_health={health} lean={lean}. "
        "Confirm data-gap vs quiet — not a config apply. Exec FROZEN stays.\n"
        "MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.parent.mkdir(parents=True, exist_ok=True)
        inbox.write_text(
            body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"silence -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    day = datetime.now().strftime("%Y-%m-%d")
    for s in new_syms:
        alerted[s] = day
    state["gap_alerted"] = alerted
    state["alerted_day"] = day
    state["alerted_at"] = datetime.now().isoformat(timespec="seconds")
    state["last"] = {
        k: report.get(k) for k in (
            "minutes_open", "signals", "signals_all", "total_signals", "fire",
            "fire_syms", "gaps_min", "thresholds_min", "raw_signals")
    }
    _save(path, state)
    print("AGENT_LOOP_WAKE_eu_session_silence", flush=True)
    return lines
