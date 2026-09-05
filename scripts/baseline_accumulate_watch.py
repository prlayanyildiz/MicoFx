"""Durable book monitor — baseline / US30 / night-bleed / streak / XAU EU.

Report-only (Claude TEMIZ WAIT + 06:35 auto-A veto). No config writes except
verified XAU EU re-enable when the temp-disable flag is up. Runs forever
unless ``--once`` / ``--max-ticks``.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import book_robust_audit as book_robust  # noqa: E402
from scripts.channel_break_path_watch import maybe_alert as cb_path_alert  # noqa: E402
from scripts.channel_break_path_watch import snapshot as cb_path_snapshot  # noqa: E402
from scripts.concurrent_stack_watch import maybe_alert as stack_alert  # noqa: E402
from scripts.concurrent_stack_watch import snapshot as stack_snapshot  # noqa: E402
from scripts.eu_open_brief import maybe_brief as eu_open_brief  # noqa: E402
from scripts.night_bleed_guard import maybe_alert as bleed_alert  # noqa: E402
from scripts.night_bleed_guard import snapshot as bleed_snapshot  # noqa: E402
from scripts.panel_health_watch import maybe_alert as panel_alert  # noqa: E402
from scripts.panel_health_watch import panel_ok  # noqa: E402
from scripts.session_open_silence import maybe_alert as silence_alert  # noqa: E402
from scripts.session_open_silence import snapshot as silence_snapshot  # noqa: E402
from scripts.stale_runtime_watch import maybe_alert as stale_alert  # noqa: E402
from scripts.stale_runtime_watch import snapshot as stale_snapshot  # noqa: E402
from scripts.us30_fill_watch import SESSION_OPEN_MIN_SIGNALS  # noqa: E402
from scripts.us30_fill_watch import maybe_alert as us30_alert  # noqa: E402
from scripts.us30_fill_watch import snapshot as us30_snapshot  # noqa: E402
from scripts.xau_post_eu_watch import active as post_eu_active  # noqa: E402
from scripts.xau_post_eu_watch import maybe_alert as post_eu_alert  # noqa: E402
from scripts.xau_streak_watch import (  # noqa: E402
    alert_book,
    baseline_status,
    consecutive_non_winners,
    fetch_autopsy_rows,
    fetch_enabled_symbols,
    maybe_alert_baseline_ready,
    maybe_alert_first_new_close,
    scan_book,
)
from scripts.xau_temp_reenable import FLAG as XAU_TEMP_FLAG  # noqa: E402
from scripts.xau_temp_reenable import _session as xau_session  # noqa: E402
from scripts.xau_temp_reenable import broker_hour as xau_broker_hour  # noqa: E402
from scripts.xau_temp_reenable import reenable as xau_temp_reenable  # noqa: E402

LOG = ROOT / "logs" / "baseline_accumulate.log"
PANEL = "http://127.0.0.1:8900"
# Soft restart: touch this file so the watch exits 0; launcher respawns.
RELOAD_FLAG = ROOT / ".bridge" / "BASELINE_WATCH_RELOAD"
HEARTBEAT = ROOT / ".bridge" / "BASELINE_WATCH_HEARTBEAT"
LAST_EXIT = ROOT / ".bridge" / "BASELINE_WATCH_LAST_EXIT.txt"
STALE_STATE = ROOT / ".bridge" / "BASELINE_WATCH_STALE.json"
# Watch ticks at most every ~15m; 20m with buffer = hung or dead.
HEARTBEAT_STALE_SEC = 20 * 60
# While night-disable flag is up, poll often so EU open (h>=8) is not ~15m late.
REENABLE_POLL_SEC = 60


def _log(msg: str) -> None:
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def _heartbeat() -> None:
    try:
        HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT.write_text(
            datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
        clear_stale_alert()
    except OSError:
        pass


def _write_last_exit(reason: str) -> None:
    try:
        LAST_EXIT.parent.mkdir(parents=True, exist_ok=True)
        LAST_EXIT.write_text(reason, encoding="utf-8")
    except OSError:
        pass


def _reload_requested() -> bool:
    if not RELOAD_FLAG.is_file():
        return False
    try:
        RELOAD_FLAG.unlink(missing_ok=True)
    except OSError:
        pass
    return True


def heartbeat_age_sec(
    *,
    path: Path | None = None,
    now: datetime | None = None,
) -> float | None:
    """Seconds since last heartbeat, or None if missing/unreadable."""
    hb = path if path is not None else HEARTBEAT
    if not hb.is_file():
        return None
    try:
        raw = hb.read_text(encoding="utf-8").strip()
        stamped = datetime.fromisoformat(raw)
    except (OSError, ValueError):
        return None
    return max(0.0, ((now or datetime.now()) - stamped).total_seconds())


def maybe_alert_stale_heartbeat(
    *,
    max_age_sec: float = HEARTBEAT_STALE_SEC,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
    now: datetime | None = None,
) -> list[str]:
    """Wake once when the durable watch stops heartbeating."""
    age = heartbeat_age_sec(now=now)
    if age is None or age < float(max_age_sec):
        return []
    sp = state_path if state_path is not None else STALE_STATE
    try:
        prev = json.loads(sp.read_text(encoding="utf-8")) if sp.is_file() else {}
    except (OSError, json.JSONDecodeError):
        prev = {}
    if prev.get("alerted"):
        return []
    lines: list[str] = []
    wake = wake_path if wake_path is not None else (ROOT / ".bridge" / "WAKE.txt")
    inbox = cursor_inbox if cursor_inbox is not None else (
        ROOT / "cursor" / "FOR_CLAUDE.md")
    try:
        wake.parent.mkdir(parents=True, exist_ok=True)
        wake.write_text("WAKE baseline heartbeat stale\n", encoding="utf-8")
        lines.append(f"wake -> {wake}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    body = (
        f"# Cursor -> Claude -- {ts} -- BASELINE WATCH HEARTBEAT STALE "
        f"({int(age)}s > {int(max_age_sec)}s).\n\n"
        "Durable book monitor may be hung/dead. Soft-reload flag + schtask "
        "keepalive should recover; confirm `.bridge/BASELINE_WATCH_HEARTBEAT`.\n\n"
        "MICO MOLA yok.\n"
    )
    try:
        prev_txt = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.write_text(
            body + ("\n---\n\n" + prev_txt if prev_txt else ""), encoding="utf-8")
        lines.append(f"stale heartbeat alert -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    try:
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(json.dumps({
            "alerted": True,
            "alerted_at": datetime.now().isoformat(timespec="seconds"),
            "age_sec": round(age, 1),
        }, indent=2), encoding="utf-8")
    except OSError:
        pass
    print("AGENT_LOOP_WAKE_baseline_heartbeat_stale", flush=True)
    return lines


def clear_stale_alert(*, state_path: Path | None = None) -> None:
    """Clear once heartbeat is fresh again (so a later death can re-alert)."""
    sp = state_path if state_path is not None else STALE_STATE
    try:
        if sp.is_file():
            sp.unlink()
    except OSError:
        pass


def once(panel: str = PANEL) -> tuple[bool, bool, bool, int | None]:
    """Return (baseline_ready, us30_alert, xau_reenabled, broker_h)."""
    if not panel_ok(panel):
        for n in panel_alert(ok=False, panel=panel):
            _log(n)
        return False, False, False, None
    for n in panel_alert(ok=True, panel=panel):
        _log(n)
    bh: int | None = None
    try:
        bh = xau_broker_hour(xau_session(panel), panel)
    except Exception:
        bh = None
    rows = fetch_autopsy_rows(panel)
    bl = baseline_status(len(rows))
    _log(
        f"baseline {bl.get('new_trades')}/{bl.get('target')} "
        f"suppress={bl.get('suppressed')} autopsy={bl.get('autopsy_n')}"
    )
    bnotes = maybe_alert_baseline_ready(len(rows))
    for n in bnotes:
        _log(n)
        if "BASELINE READY" in n or "baseline ready" in n.lower():
            print("AGENT_LOOP_WAKE_baseline_ready", flush=True)
    for n in maybe_alert_first_new_close(len(rows)):
        _log(n)
    # Claude 07:20: US30 closest shrink — earlier fill alert during EU open hours.
    # GER40 shares the EU open window; same report-only heighten.
    us30_min = (
        SESSION_OPEN_MIN_SIGNALS
        if bh is not None and 8 <= int(bh) <= 11
        else None
    )
    urep = us30_snapshot(panel, min_signals=us30_min)
    _log(
        f"US30 fill={urep.get('fill_rate')} sig={urep.get('signals')} "
        f"open={urep.get('opened')} poor={urep.get('poor_fill')} "
        f"min_sig={urep.get('min_signals')}"
    )
    unotes = us30_alert(urep)
    for n in unotes:
        _log(n)
    ger_notes: list[str] = []
    if bh is not None and 8 <= int(bh) <= 11:
        ger_path = ROOT / ".bridge" / "GER40_FILL_BASELINE.json"
        grep = us30_snapshot(
            panel, symbol="GER40", state_path=ger_path,
            min_signals=SESSION_OPEN_MIN_SIGNALS,
        )
        _log(
            f"GER40 fill={grep.get('fill_rate')} sig={grep.get('signals')} "
            f"act={grep.get('actionable_signals')} "
            f"open={grep.get('opened')} poor={grep.get('poor_fill')} "
            f"min_sig={grep.get('min_signals')}"
        )
        ger_notes = us30_alert(grep, state_path=ger_path)
        for n in ger_notes:
            _log(n)
    # NAS100 session 15:00-21:00 — heighten fill watch at open (same as US30/GER).
    nas_notes: list[str] = []
    if bh is not None and 15 <= int(bh) <= 17:
        from scripts.session_open_silence import session_day_key
        from scripts.us30_fill_watch import arm_session_day

        nas_path = ROOT / ".bridge" / "NAS100_FILL_BASELINE.json"
        if arm_session_day(nas_path, day_key=session_day_key(bh)):
            _log(f"NAS100 session day armed ({session_day_key(bh)})")
        nrep = us30_snapshot(
            panel, symbol="NAS100", state_path=nas_path,
            min_signals=SESSION_OPEN_MIN_SIGNALS,
        )
        _log(
            f"NAS100 fill={nrep.get('fill_rate')} sig={nrep.get('signals')} "
            f"act={nrep.get('actionable_signals')} "
            f"open={nrep.get('opened')} poor={nrep.get('poor_fill')} "
            f"min_sig={nrep.get('min_signals')}"
        )
        nas_notes = us30_alert(nrep, state_path=nas_path)
        for n in nas_notes:
            _log(n)
    try:
        srep = silence_snapshot(panel)
        _log(
            f"eu_silence fire={srep.get('fire')} open_min={srep.get('minutes_open')} "
            f"sig={srep.get('signals')}"
        )
        for n in silence_alert(srep):
            _log(n)
    except Exception as exc:
        _log(f"eu_silence fail: {exc}")
    # Claude 20:04: 1-ticket/name — alarm only on violation (silent = healthy).
    try:
        strep = stack_snapshot(panel)
        _log(
            f"stack fire={strep.get('fire')} max={strep.get('max_concurrent')} "
            f"off={strep.get('offenders')}"
        )
        for n in stack_alert(strep):
            _log(n)
    except Exception as exc:
        _log(f"stack fail: {exc}")
    # Claude 20:32: land-vs-live mtimes — noop until boot stamp (first flat restart).
    try:
        srep = stale_snapshot()
        _log(
            f"stale_runtime armed={srep.get('armed')} fire={srep.get('fire')} "
            f"n_stale={len(srep.get('stale') or [])}"
        )
        for n in stale_alert(srep, panel=panel):
            _log(n)
    except Exception as exc:
        _log(f"stale_runtime fail: {exc}")
    # Claude 09:35 next control: channel_break signal but 0 opens.
    try:
        cb = cb_path_snapshot(panel, broker_h=bh)
        _log(
            f"cb_path fire={cb.get('fire')} hits={len(cb.get('hits') or [])} "
            f"deltas={cb.get('deltas')}"
        )
        for n in cb_path_alert(cb):
            _log(n)
    except Exception as exc:
        _log(f"cb_path fail: {exc}")
    # Book streak / expectancy (suppressed until baseline target).
    try:
        enabled = fetch_enabled_symbols(panel)
        # Always include XAU even when night-disabled.
        if "XAUUSD" not in enabled:
            enabled = list(enabled) + ["XAUUSD"]
        reports = scan_book(rows, enabled)
        snotes = alert_book(
            reports, autopsy_n=len(rows))
        for n in snotes:
            _log(f"streak {n}")
    except Exception as exc:
        _log(f"streak scan fail: {exc}")
    # Night-bleed: alert-only (Claude 06:35 — never auto-disable from watcher).
    # Suspend wakes while post-restart baseline accumulates (same door as streak).
    try:
        syms = {str(r.get("symbol") or "") for r in rows if r.get("symbol")}
        streaks = {
            s: int(consecutive_non_winners(rows, symbol=s).get("streak") or 0)
            for s in syms
        }
        bsnap = bleed_snapshot(rows, streaks=streaks)
        bl_sup = bool(bl.get("suppressed"))
        _log(
            f"bleed fire={bsnap.get('fire')} dom={bsnap.get('dominant')} "
            f"loss_share={bsnap.get('loss_share')} streak_r={bsnap.get('streak_r')} "
            f"streak={bsnap.get('dominant_streak')} sole={bsnap.get('sole_recent')} "
            f"auto={bsnap.get('armed_auto_a')} "
            f"baseline_suppress={bl_sup}"
        )
        if bl_sup:
            _log("bleed wakes SUSPEND (post-restart baseline)")
        else:
            for n in bleed_alert(bsnap):
                _log(n)
    except Exception as exc:
        _log(f"night_bleed fail: {exc}")
    try:
        for n in post_eu_alert(rows):
            _log(n)
        if post_eu_active():
            _log("post_eu watch active")
    except Exception as exc:
        _log(f"post_eu fail: {exc}")
    xau_on = False
    try:
        ok, msg = xau_temp_reenable(panel)
        _log(msg)
        xau_on = bool(ok) and "enabled=true" in msg
        if xau_on:
            print("AGENT_LOOP_WAKE_xau_eu_reenable", flush=True)
    except Exception as exc:
        _log(f"xau reenable fail: {exc}")
    try:
        for n in eu_open_brief(broker_h=bh, panel=panel):
            _log(n)
    except Exception as exc:
        _log(f"eu_brief fail: {exc}")
    # Frozen-era 6-slice evidence trail (unfreeze gate proof).
    try:
        rows6 = book_robust.audit_from_panel(panel)
        book_robust.append_evidence_ledger(
            rows6,
            meta={
                "source": "baseline_watch",
                "new_trades": (baseline_status(len(rows)) or {}).get("new_trades"),
                "autopsy_n": len(rows),
                "frozen": True,
                "broker_h": bh,
            },
            min_interval_sec=900,
        )
        bad6 = [r for r in rows6 if not r.get("ok")]
        _log(
            f"gate6 ok_all={not bad6} n={len(rows6)} "
            f"bad={[r.get('symbol') for r in bad6]}"
        )
    except Exception as exc:
        _log(f"gate6 fail: {exc}")
    return (
        bool(bnotes),
        bool(unotes) or bool(ger_notes) or bool(nas_notes),
        xau_on,
        bh,
    )


def _sleep_sec(interval: int, *, broker_h: int | None = None) -> int:
    if XAU_TEMP_FLAG.is_file() or post_eu_active():
        return max(30, int(REENABLE_POLL_SEC))
    # GER40/US30 open ~08:00 — poll often through mid-morning.
    if broker_h is not None and 8 <= int(broker_h) <= 11:
        return max(30, int(REENABLE_POLL_SEC))
    # NAS100 open ~15:00 — same heighten through first hours.
    if broker_h is not None and 15 <= int(broker_h) <= 17:
        return max(30, int(REENABLE_POLL_SEC))
    return max(60, int(interval))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--panel", default=PANEL)
    p.add_argument("--interval", type=int, default=900)
    p.add_argument("--once", action="store_true")
    p.add_argument("--max-ticks", type=int, default=0,
                   help="0 = run forever (durable book monitor)")
    args = p.parse_args()
    ticks = 0
    while True:
        ticks += 1
        try:
            ready, _, xau_on, bh = once(args.panel)
            _heartbeat()
        except Exception as exc:
            _log(f"tick fail: {exc}")
            ready = False
            xau_on = False
            bh = None
        if args.once:
            return 0
        if ready:
            _log("baseline ready — continue durable monitor")
        if xau_on:
            _log("XAU EU re-enable — continue durable monitor")
        if args.max_ticks and ticks >= args.max_ticks:
            _log(f"max ticks {args.max_ticks} — exit")
            _write_last_exit("max_ticks")
            return 0
        if _reload_requested():
            _log("reload flag — clean exit 0 for launcher respawn")
            _write_last_exit("reload")
            return 0
        # Chunked sleep so soft-reload is not stuck behind a 900s nap.
        left = int(_sleep_sec(args.interval, broker_h=bh))
        while left > 0:
            if _reload_requested():
                _log("reload flag — clean exit 0 for launcher respawn")
                _write_last_exit("reload")
                return 0
            step = min(30, left)
            time.sleep(step)
            left -= step


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:
        _write_last_exit(f"crash:{type(exc).__name__}")
        raise
