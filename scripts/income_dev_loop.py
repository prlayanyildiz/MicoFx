"""Income development loop — audit live book, apply safe fixes, auto-recover.

Runs outside the engine process. Reads micofx.db read-only where possible;
writes go through the live panel API (Origin + session cookie required).

Usage:
    C:\\MicoFX-venv\\Scripts\\python.exe scripts/income_dev_loop.py
    C:\\MicoFX-venv\\Scripts\\python.exe scripts/income_dev_loop.py --apply-safe
    C:\\MicoFX-venv\\Scripts\\python.exe scripts/income_dev_loop.py --auto
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from micofx.entry_pressure import spread_pressure  # noqa: E402
from micofx.paths import DB_PATH, LOG_DIR  # noqa: E402

PANEL = "http://127.0.0.1:8900"
ORIGIN = PANEL
BOOK = ("BTCUSD", "GER40", "JPN225", "NAS100", "SpotBrent", "US30", "XAUUSD")
BRIDGE = ROOT / ".bridge"


def htf_gate_label(params: dict[str, Any] | None) -> str:
    """Claude 11:12: htf=0 display is not a block when factor<=1 (gate OFF)."""
    p = params or {}
    try:
        factor = int(p.get("htf_factor") or 0)
    except (TypeError, ValueError):
        factor = 0
    mode = str(p.get("htf_mode") or "t3")
    if mode == "t3" and factor > 1:
        return f"ON/{factor}"
    return "OFF"


def load_symbol_queues(bridge: Path = BRIDGE) -> list[dict[str, Any]]:
    """Postponed symbol adds (e.g. UK100/FRA40 after 25+unfreeze)."""
    out: list[dict[str, Any]] = []
    if not bridge.is_dir():
        return out
    for path in sorted(bridge.glob("SYMBOL_QUEUE_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            data = {**data, "_path": path.name}
            out.append(data)
    return out


# Post-freeze income actions (measurement queues — not SYMBOL_QUEUE adds).
_ACTION_QUEUE_FILES: tuple[str, ...] = (
    "XAU_MIN_BODY_APPLY_QUEUE.json",
    "NAS100_MIN_BODY_APPLY_QUEUE.json",
    "NAS100_SESSION_REEVAL_ONCE.json",
    "WFO_APPLY_GATE_QUEUE.json",
    "GER40_SNAPSHOT_RECLEAN_QUEUE.json",
    "GER40_TRAIL_STEP_HOLD_ONLY.json",
    "XAU_TRAIL_STEP_GIVEBACK_QUEUE.json",
    "XAU_BE_AT_R_HOLD_ONLY.json",
    "STALE_RUNTIME_WATCH_QUEUE.json",
)


def load_action_queues(bridge: Path = BRIDGE) -> list[dict[str, Any]]:
    """Unfreeze action board: body/session/WFO/GER40 measurement queues."""
    out: list[dict[str, Any]] = []
    if not bridge.is_dir():
        return out
    for name in _ACTION_QUEUE_FILES:
        path = bridge / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        when = data.get("when") or data.get("do_not_wire_while")
        if when is None and (
            data.get("do_not_apply_now") or data.get("do_not_run_now")
        ):
            when = "blocked_until_unfreeze"
        out.append({
            "_path": name,
            "status": data.get("status") or data.get("recommendation") or "?",
            "when": when,
            "summary": (
                data.get("decision")
                or data.get("recommendation")
                or data.get("note")
                or data.get("source")
                or ""
            ),
            "symbol": data.get("symbol"),
            "challenger": data.get("challenger"),
            "field": data.get("field"),
        })
    return out


def load_day25_checklist(bridge: Path = BRIDGE) -> dict[str, Any]:
    """Day-of-25 idle board: axes CLOSED + readiness + when-ready actions."""
    path = bridge / "UNFREEZE_DAY25_CHECKLIST.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    ready = data.get("readiness") if isinstance(data.get("readiness"), dict) else {}
    axes = data.get("axes") if isinstance(data.get("axes"), dict) else {}
    items = data.get("day_of_25_when_ready")
    if not isinstance(items, list):
        items = []
    latest = data.get("latest_close")
    if not isinstance(latest, dict):
        latest = {}
    return {
        "_path": path.name,
        "phase": data.get("phase") or "",
        "axes": axes,
        "baseline_new": int(ready.get("baseline_new") or 0),
        "baseline_target": int(ready.get("baseline_target") or 25),
        "ready_to_execute": bool(ready.get("ready_to_execute")),
        "frozen": bool(ready.get("frozen")),
        "day_of_25_when_ready": [str(x) for x in items if x is not None],
        "latest_close": latest,
        "ts": data.get("ts") or "",
    }


# fill_rate below this with spread as top block -> spread calibration candidate
_SPREAD_FILL_ALERT = 0.25
# margin usage above this fraction of the configured cap -> alert
_MARGIN_ALERT_FRAC = 0.75
# auto spread-calibrate when dominant spread blocks exceed this (per enabled name)
_SPREAD_AUTO_MIN = 10
# Ignore lifetime entry_blocks if the counter epoch is older than this (F-D3).
# Engine also rolls at ENTRY_BLOCKS_ROLL_SEC after restart; this guards the
# income loop against pre-restart DB noise.
_ENTRY_BLOCKS_MAX_AGE_SEC = 7 * 86400


def _db() -> sqlite3.Connection:
    last: Exception | None = None
    for delay in (0.0, 0.5, 1.0, 2.0):
        if delay:
            time.sleep(delay)
        try:
            c = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10.0)
            c.row_factory = sqlite3.Row
            return c
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower():
                raise
            last = exc
    raise last or sqlite3.OperationalError("database is locked")


def _setting(c: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["value"])
    except json.JSONDecodeError:
        return default




def day_brake_snapshot(c: sqlite3.Connection) -> dict[str, Any]:
    """Cash-flow-aware daily brake readout (operator C3)."""
    start = float(_setting(c, "day_start_balance", 0.0) or 0.0)
    flow = float(_setting(c, "day_cash_flow", 0.0) or 0.0)
    sys_ = _setting(c, "system", {}) or {}
    if not isinstance(sys_, dict):
        sys_ = {}
    loss_pct = float(sys_.get("daily_loss_pct") or 0.0)
    denom = start + max(0.0, flow)
    room = abs(loss_pct) / 100.0 * denom if loss_pct and denom > 0 else 0.0
    return {
        "day_start_balance": round(start, 2),
        "day_cash_flow": round(flow, 2),
        "brake_denom": round(denom, 2),
        "daily_loss_pct": loss_pct,
        "brake_room_usd": round(room, 2),
        "effective_brake_pct_of_equity_hint": (
            round(100.0 * room / denom, 2) if denom > 0 else 0.0
        ),
    }


def _symbols(c: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in c.execute("SELECT symbol, payload FROM symbols ORDER BY symbol"):
        out[row["symbol"]] = json.loads(row["payload"])
    return out


def _api_session() -> tuple[dict[str, str], bool]:
    """Return (headers with session cookie, panel_up)."""
    try:
        req = urllib.request.Request(f"{PANEL}/", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            cookies = resp.headers.get_all("Set-Cookie") or []
        headers: dict[str, str] = {"Origin": ORIGIN}
        if cookies:
            headers["Cookie"] = "; ".join(c.split(";")[0] for c in cookies)
        return headers, True
    except (urllib.error.URLError, TimeoutError, OSError):
        return {"Origin": ORIGIN}, False


def _api_get(path: str, headers: dict[str, str]) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(f"{PANEL}{path}", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _api_post(path: str, headers: dict[str, str], body: dict[str, Any] | None = None) -> tuple[bool, str]:
    data = json.dumps(body or {}).encode()
    h = {**headers, "Origin": ORIGIN, "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(f"{PANEL}{path}", data=data, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return True, resp.read().decode()[:400]
    except urllib.error.HTTPError as exc:
        return False, exc.read().decode()[:400]
    except Exception as exc:
        return False, str(exc)


def _enabled_symbols(syms: dict[str, dict[str, Any]]) -> list[str]:
    """Operator's active book — disabled names stay off."""
    return sorted(sym for sym, p in syms.items() if p.get("enabled"))


def _aggregate_entry_blocks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge buy/sell legs per symbol."""
    by_sym: dict[str, dict[str, Any]] = {}
    for row in rows:
        sym = str(row.get("symbol") or "")
        if not sym:
            continue
        agg = by_sym.setdefault(sym, {"signals": 0, "opened": 0, "blocks": {}})
        agg["signals"] += int(row.get("signals") or 0)
        agg["opened"] += int(row.get("opened") or 0)
        for k, v in (row.get("blocks") or {}).items():
            agg["blocks"][str(k)] = agg["blocks"].get(str(k), 0) + int(v)
    out: list[dict[str, Any]] = []
    for sym, agg in sorted(by_sym.items()):
        total = int(agg["signals"])
        opened = int(agg["opened"])
        out.append({
            "symbol": sym,
            "signals": total,
            "opened": opened,
            "fill_rate": round(opened / total, 3) if total else 0.0,
            "blocks": agg["blocks"],
        })
    return out


def fetch_entry_blocks(headers: dict[str, str]) -> list[dict[str, Any]]:
    data = _api_get("/api/analysis/entry-blocks", headers)
    if not data:
        return []
    since = float(data.get("since") or 0.0)
    if since > 0 and (time.time() - since) > _ENTRY_BLOCKS_MAX_AGE_SEC:
        # Stale lifetime tallies poison spread/lot auto actions.
        return []
    return _aggregate_entry_blocks(list(data.get("rows") or []))


def fetch_live(headers: dict[str, str]) -> dict[str, Any]:
    state = _api_get("/api/state", headers) or {}
    positions = list(state.get("positions") or [])
    open_syms = {str(p.get("symbol") or "") for p in positions}
    cap = dict(state.get("capacity") or {})
    return {
        "panel_up": bool(state.get("ok")),
        "mt5_connected": bool((state.get("mt5") or {}).get("connected")),
        "positions": len(positions),
        "open_symbols": sorted(s for s in open_syms if s),
        "margin_usage_pct": float(cap.get("margin_usage_pct") or 0.0),
        "max_margin_usage_pct": float(cap.get("max_margin_usage_pct") or 0.0),
        "margin_budget": float(cap.get("margin_budget") or 0.0),
        "global_free_slots": int(cap.get("global_free_slots") or 0),
        "opt_busy": (state.get("opt") or {}).get("busy"),
        "halted": bool((state.get("day") or {}).get("halted")),
    }


def margin_alerts(live: dict[str, Any], entry_rows: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    used = float(live.get("margin_usage_pct") or 0.0)
    cap = float(live.get("max_margin_usage_pct") or 0.0)
    if cap > 0 and used >= cap * _MARGIN_ALERT_FRAC:
        actions.append(
            f"MARJ %{used:.1f}/%{cap:g} — yeni girisler marj limitinde; "
            f"kapanis bekleniyor veya lot_multiplier dusurulebilir"
        )
    margin_blocks = sum(
        int((r.get("blocks") or {}).get("marj", 0) or 0)
        for r in entry_rows
    )
    if margin_blocks >= 10:
        actions.append(
            f"MARJ engeli: {margin_blocks} sinyal marj limitinde kaldi — "
            f"pozisyon kapaninca veya marj bosalinca acilir"
        )
    lot_blocks = sum(int((r.get("blocks") or {}).get("lot", 0) or 0) for r in entry_rows)
    if lot_blocks >= 15:
        actions.append(
            f"LOT engeli: {lot_blocks} sinyal lot yetersiz — supervisor watch veya "
            f"risk butcesi; zorla acma"
        )
    return actions


def spread_recovery_actions(entry_rows: list[dict[str, Any]],
                            active: set[str]) -> list[str]:
    """Symbols losing trades to spread gate — calibrate when flat."""
    actions: list[str] = []
    for row in entry_rows:
        sym = row.get("symbol", "")
        if sym not in active:
            continue
        blocks = row.get("blocks") or {}
        spread_n = spread_pressure(row)
        signals = int(row.get("signals") or 0)
        fill = float(row.get("fill_rate") or 0.0)
        if spread_n < 5 or signals < 10:
            continue
        top = max(int(v or 0) for v in blocks.values()) if blocks else 0
        spread_dominant = spread_n >= max(top, 1)
        low_fill = fill < _SPREAD_FILL_ALERT
        if spread_dominant and (low_fill or spread_n >= 15):
            actions.append(
                f"SPREAD {sym}: {spread_n}/{signals} sinyal spread'de "
                f"(fill %{fill*100:.0f}) — pozisyon yokken kalibre"
            )
        elif spread_n >= 15 and not low_fill:
            actions.append(
                f"SPREAD {sym}: {spread_n} spread blogu (fill %{fill*100:.0f}) "
                f"— ikincil; once baskin engeli coz"
            )
    return actions


def spread_auto_targets(entry_rows: list[dict[str, Any]],
                        open_symbols: set[str],
                        active: set[str]) -> list[str]:
    """Flat enabled symbols where spread is the dominant blocker with evidence."""
    out: list[str] = []
    for row in entry_rows:
        sym = str(row.get("symbol") or "")
        if sym not in active or sym in open_symbols:
            continue
        blocks = row.get("blocks") or {}
        spread_n = spread_pressure(row)
        signals = int(row.get("signals") or 0)
        fill = float(row.get("fill_rate") or 0.0)
        if spread_n < _SPREAD_AUTO_MIN or signals < 5:
            continue
        top = max(int(v or 0) for v in blocks.values()) if blocks else 0
        if spread_n >= max(top, _SPREAD_AUTO_MIN) and fill < 0.35:
            out.append(sym)
        elif spread_n >= _SPREAD_AUTO_MIN and fill < 0.25:
            out.append(sym)
    return out


def audit(c: sqlite3.Connection) -> dict[str, Any]:
    syms = _symbols(c)
    active = set(_enabled_symbols(syms))
    sup_state = _setting(c, "supervisor_state", {}) or {}
    verdicts = sup_state.get("verdicts") or {}
    system = _setting(c, "system", {}) or {}
    job = _setting(c, "last_opt_job", {}) or {}
    supervisor = _setting(c, "supervisor", {}) or {}

    ranked = []
    for sym in sorted(active):
        p = syms.get(sym) or {}
        hold = (p.get("opt_summary") or {}).get("holdout") or {}
        v = verdicts.get(sym) or {}
        ranked.append({
            "symbol": sym,
            "enabled": True,
            "strategy": p.get("strategy"),
            "timeframe": p.get("timeframe"),
            "max_spread_atr": p.get("max_spread_atr"),
            "htf_gate": htf_gate_label(p),
            "htf_factor": p.get("htf_factor"),
            "opt_score": round(float(p.get("opt_score") or 0), 2),
            "holdout_net_r": round(float(hold.get("net_r") or 0), 1),
            "expectancy": round(float(hold.get("expectancy") or 0), 3),
            "retention": round(float((p.get("opt_summary") or {}).get("holdout_retention") or 0), 2),
            "supervisor": v.get("state", "?"),
            "live_net_r": round(float(v.get("net") or 0), 1),
            "partial_at_r": p.get("partial_at_r"),
            "opt_age_h": round((time.time() - float(p.get("opt_updated_at") or 0)) / 3600.0, 1)
            if float(p.get("opt_updated_at") or 0) > 0 else None,
        })
    ranked.sort(key=lambda x: (x["holdout_net_r"], x["opt_score"]), reverse=True)

    reopt_ready = [
        r["symbol"] for r in ranked
        if r["opt_age_h"] is not None
        and r["opt_age_h"] >= float(supervisor.get("reopt_min_age_hours", 48))
        and (r["retention"] < 0.8 or r["supervisor"] in ("watch", "quarantine"))
    ]

    actions: list[str] = []
    for r in ranked:
        if r["partial_at_r"] not in (0, 0.0, None):
            actions.append(f"FIX partial_at_r=0 on {r['symbol']}")
    if supervisor.get("prefer_strong_on_dd"):
        actions.append("SET prefer_strong_on_dd=false (gunluk kayipta sembol bekletmesin)")
    if not supervisor.get("hard_block_only_quarantine", True):
        actions.append("SET hard_block_only_quarantine=true (AI sadece lot kisssin)")

    if not system.get("autostart_bot"):
        actions.append("SET autostart_bot=true")
    if job.get("state") == "running":
        actions.append("WAIT opt job running — do not start another scan")

    headers, panel_up = _api_session()
    live: dict[str, Any] = {"panel_up": panel_up}
    entry_rows: list[dict[str, Any]] = []
    if panel_up:
        live = fetch_live(headers)
        entry_rows = fetch_entry_blocks(headers)
        actions.extend(margin_alerts(live, entry_rows))
        actions.extend(spread_recovery_actions(entry_rows, active))

    return {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "live": live,
        "day_brake": day_brake_snapshot(c),
        "entry_blocks": [r for r in entry_rows if r.get("symbol") in active],
        "active_symbols": sorted(active),
        "system": {
            "lot_multiplier": system.get("lot_multiplier"),
            "size_by_edge": system.get("size_by_edge"),
            "max_margin_usage_pct": system.get("max_margin_usage_pct"),
            "max_concurrent_risk_pct": system.get("max_concurrent_risk_pct"),
            "autostart_bot": system.get("autostart_bot"),
        },
        "supervisor": {
            "enabled": supervisor.get("enabled"),
            "prefer_strong_on_dd": supervisor.get("prefer_strong_on_dd"),
            "hard_block_only_quarantine": supervisor.get("hard_block_only_quarantine"),
        },
        "opt_job": job.get("state"),
        "ranked": ranked,
        "reopt_ready": reopt_ready,
        "actions": actions,
        "spread_auto": spread_auto_targets(
            entry_rows, set(live.get("open_symbols") or []), active),
        "keep_live": [r["symbol"] for r in ranked if r["holdout_net_r"] >= 20],
    }


def apply_safe(report: dict[str, Any]) -> list[str]:
    headers, up = _api_session()
    if not up:
        return ["panel offline — safe fixes skipped"]
    done: list[str] = []

    state = _api_get("/api/state", headers)
    if state and not (state.get("system") or {}).get("autostart_bot"):
        ok, msg = _api_post("/api/system", headers, {"autostart_bot": True})
        done.append(f"autostart_bot={'ok' if ok else 'fail'} {msg[:80]}")

    for sym in report.get("active_symbols") or []:
        row = next((r for r in report["ranked"] if r["symbol"] == sym), None)
        if not row or row["partial_at_r"] in (0, 0.0, None):
            continue
        ok, msg = _api_post(f"/api/symbols/{sym}", headers, {"partial_at_r": 0})
        done.append(f"{sym} partial_at_r=0 {'ok' if ok else 'fail'}")

    return done


def apply_trust_entries(report: dict[str, Any]) -> list[str]:
    """AI trust knobs only — never band-calibrate here.

    Spread widen lives in ``apply_spread_calibration`` (evidence + freeze +
    upgrade_robust). This path used to POST ``/spread-calibrate`` on every
    flat active symbol and undid NAS100 0.05→0.06 (04.09).
    """
    headers, up = _api_session()
    if not up:
        return ["panel offline — trust mode atlandi"]
    done: list[str] = []

    ok, msg = _api_post("/api/ai/settings", headers, {
        "prefer_strong_on_dd": False,
        "hard_block_only_quarantine": True,
    })
    done.append(f"AI trust mode {'ok' if ok else 'fail'} {msg[:80]}")
    return done


def spread_calib_targets(report: dict[str, Any]) -> list[str]:
    """Flat symbols with evidence spread pain — not every active name.

    04.09 ``--auto`` added all ``active_symbols`` and band-calibrated NAS100
    0.05→0.06 while charged preferred 0.05. Match in-process autopilot:
    only ``spread_auto`` evidence rows.
    """
    live = report.get("live") or {}
    open_syms = {str(s) for s in (live.get("open_symbols") or []) if s}
    out: list[str] = []
    for sym in report.get("spread_auto") or []:
        s = str(sym or "")
        if s and s not in open_syms:
            out.append(s)
    return sorted(set(out))


def apply_spread_calibration(report: dict[str, Any]) -> list[str]:
    """Auto widen spread caps on flat enabled symbols with spread pain."""
    from scripts.exec_gates import pipeline_frozen
    if pipeline_frozen():
        return ["spread: exec pipeline FREEZE (Claude 03:36)"]
    headers, up = _api_session()
    if not up:
        return ["panel offline — spread kalibrasyon atlandi"]
    live = report.get("live") or {}
    if live.get("opt_busy"):
        return ["opt calisiyor — spread kalibrasyon atlandi"]
    if not live.get("mt5_connected"):
        return ["MT5 bagli degil — spread kalibrasyon atlandi"]

    st = _api_get("/api/state", headers) or {}
    if not (st.get("system") or {}).get("charge_costs", True):
        return ["spread kalibrasyon atlandi (charge_costs=false)"]

    done: list[str] = []
    for sym in spread_calib_targets(report):
        row = next((r for r in report["ranked"] if r["symbol"] == sym), None)
        cap = float((row or {}).get("max_spread_atr") or 0.0)
        hist = _api_get(f"/api/opt/history?symbol={sym}&limit=50", headers) or {}
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "spread_exec", ROOT / "scripts" / "spread_exec.py")
        spread_mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(spread_mod)
        ok, msg = spread_mod.apply_spread_widen(
            headers, panel=PANEL, symbol=sym, current_cap=cap,
            history=list(hist.get("history") or []),
            strategy=str((row or {}).get("strategy") or "") or None)
        done.append(msg if ok else f"FAIL {msg}")
    if not done:
        done.append("spread: kanitli hedef yok")
    return done


def render_markdown(report: dict[str, Any], applied: list[str]) -> str:
    live = report.get("live") or {}
    lines = [
        f"# Gelir dongusu — {report['ts']}",
        "",
        "## Canli",
        f"- pozisyon: {live.get('positions', '?')} "
        f"({', '.join(live.get('open_symbols') or []) or 'flat'})",
        f"- marj: %{live.get('margin_usage_pct', '?')}/"
        f"%{live.get('max_margin_usage_pct', '?')}",
        f"- MT5: {'bagli' if live.get('mt5_connected') else 'kopuk'}",
        f"- opt: {report.get('opt_job')}",
        "",
    ]
    db = report.get("day_brake") or {}
    if db:
        lines.extend([
            "## Gunluk brake (C3 payda)",
            (
                f"- start={db.get('day_start_balance')} flow={db.get('day_cash_flow')} "
                f"denom={db.get('brake_denom')} loss%={db.get('daily_loss_pct')} "
                f"room_usd={db.get('brake_room_usd')}"
            ),
            "",
        ])
    d25 = report.get("day25_checklist") or {}
    if d25:
        axes = d25.get("axes") or {}
        axis_bits = ", ".join(
            f"{k}={v}" for k, v in axes.items() if v is not None
        ) or "-"
        lines.extend([
            "## Day25 checklist (idle until 25)",
            (
                f"- phase={d25.get('phase') or '-'} "
                f"new={d25.get('baseline_new')}/{d25.get('baseline_target')} "
                f"frozen={d25.get('frozen')} "
                f"ready={d25.get('ready_to_execute')} "
                f"axes=[{axis_bits}]"
            ),
        ])
        latest = d25.get("latest_close") or {}
        if latest:
            lines.append(
                f"- latest_close: {latest.get('symbol')} "
                f"#{latest.get('ticket')} {latest.get('exit')} "
                f"r={latest.get('r')} mfe={latest.get('mfe_r')}"
            )
        for item in (d25.get("day_of_25_when_ready") or [])[:8]:
            lines.append(f"- when_ready: {item}")
        lines.append("")
    up = report.get("unfreeze_prep") or {}
    if up:
        lines.extend([
            "## Unfreeze prep (Claude 10:14 board)",
            (
                f"- new={(up.get('baseline') or {}).get('new_trades')}/"
                f"{(up.get('baseline') or {}).get('target')} "
                f"phase={((up.get('gate_frame') or {}).get('phase'))} "
                f"premature_total={up.get('premature_total')} "
                f"premature_post={up.get('premature_total_post_restart')} "
                f"rate_post="
                f"{((up.get('premature_metrics_post_restart') or {}).get('rate'))} "
                f"lift="
                f"{((up.get('premature_metrics') or {}).get('lift'))} "
                f"lift_raw="
                f"{((up.get('premature_metrics') or {}).get('lift_nonsl_raw'))} "
                f"lift_vs_all="
                f"{((up.get('premature_metrics') or {}).get('lift_vs_all'))} "
                f"give_back="
                f"{((up.get('give_back_post_restart') or {}).get('ratio'))}"
                f"(n={((up.get('give_back_post_restart') or {}).get('n'))}"
                f",gate={((up.get('give_back_post_restart') or {}).get('is_gate'))}"
                f",by_exit={((up.get('give_back_post_restart') or {}).get('by_exit'))}) "
                f"geometry="
                f"{((up.get('trail_geometry') or {}).get('axis_status')) or 'AXIS_CLOSED_OPTIMUM'} "
                f"wide="
                f"{((up.get('trail_geometry') or {}).get('wide_symbols'))
                   or ((up.get('trail_geometry') or {}).get('trap_symbols'))
                   or []} "
                f"gate6={((up.get('gate6') or {}).get('ok_all'))} "
                f"safety={up.get('safety_checkpoint_ok')} "
                f"evidence={up.get('evidence_gate_ok')} "
                f"ready_hint={up.get('unfreeze_ready_hint')}"
            ),
            "",
        ])
    tg = (report.get("unfreeze_prep") or {}).get("trail_geometry") or {}
    wide = tg.get("wide_symbols") or tg.get("trap_symbols") or []
    if wide or tg.get("axis_status") == "AXIS_CLOSED_OPTIMUM":
        axis = tg.get("axis_status") or "AXIS_CLOSED_OPTIMUM"
        lines.append(f"## Trail geometry ({axis} — monitor, not a fix)")
        by = tg.get("by_symbol") or {}
        for sym in wide:
            g = by.get(sym) or {}
            lines.append(
                f"- {sym}: improves@"
                f"{g.get('trail_improves_at_r')}R "
                f"> BE@{g.get('breakeven_at_r')} "
                f"(step={g.get('trail_step_atr')} sl={g.get('sl_atr_mult')}) "
                f"— {g.get('why') or 'OPTIMUM wide geometry'}"
            )
        if not wide:
            lines.append("- (no wide symbols; axis closed OPTIMUM)")
        lines.append("")
    for q in report.get("symbol_queues") or []:
        syms = ",".join(q.get("symbols") or []) or "?"
        lines.extend([
            f"## Symbol queue ({syms})",
            (
                f"- decision={q.get('decision')} "
                f"after={'; '.join(q.get('after') or [])}"
            ),
            f"- reason: {q.get('reason')}",
            "",
        ])
    aq = report.get("action_queues") or []
    if aq:
        lines.append("## Unfreeze action queue")
        for a in aq:
            bit = f"- {a.get('_path')}: status={a.get('status')}"
            if a.get("symbol") and a.get("field"):
                bit += (
                    f" {a.get('symbol')}.{a.get('field')}"
                    f"->{a.get('challenger')}"
                )
            when = a.get("when")
            if when is not None:
                bit += f" when={when}"
            summ = str(a.get("summary") or "").replace("\n", " ")
            if summ:
                bit += f" — {summ[:160]}"
            lines.append(bit)
        lines.append("")
    bl = report.get("post_restart_baseline") or {}
    if bl.get("armed"):
        lines.extend([
            "## Post-restart baseline (Claude TEMIZ WAIT)",
            (
                f"- new closes: {bl.get('new_trades')}/{bl.get('target')} "
                f"(autopsy {bl.get('autopsy_n')}; restart {bl.get('restart_at')})"
            ),
            (
                f"- streak/exp wakes: "
                f"{'SUSPEND' if bl.get('suppressed') else 'ARMED'} "
                f"({bl.get('note')})"
            ),
            "",
        ])
    uf = report.get("us30_fill") or {}
    if uf:
        lines.extend([
            "## US30 fill (post-restart spread-gate)",
            (
                f"- fill={uf.get('fill_rate')} "
                f"sig={uf.get('signals')} opened={uf.get('opened')} "
                f"spread_blocks={uf.get('spread_blocks')} "
                f"poor={uf.get('poor_fill')}"
            ),
            "",
        ])
    gf = report.get("ger40_fill") or {}
    if gf:
        lines.extend([
            "## GER40 fill (EU open heighten)",
            (
                f"- fill={gf.get('fill_rate')} "
                f"sig={gf.get('signals')} opened={gf.get('opened')} "
                f"poor={gf.get('poor_fill')}"
            ),
            "",
        ])
    nf = report.get("nas100_fill") or {}
    if nf:
        lines.extend([
            "## NAS100 fill (15:00 session-open heighten)",
            (
                f"- fill={nf.get('fill_rate')} "
                f"act_fill={nf.get('action_fill_rate')} "
                f"act={nf.get('actionable_signals')} "
                f"sig={nf.get('signals')} opened={nf.get('opened')} "
                f"poor={nf.get('poor_fill')} "
                f"spread_blocks={nf.get('spread_blocks')} "
                f"dominant={nf.get('dominant_block') or '-'} "
                f"(honesty: raw fill includes seans_disi; act_fill is in-session)"
            ),
            "",
        ])
    sil = report.get("eu_silence") or {}
    if sil:
        lines.extend([
            "## EU session silence (book)",
            (
                f"- open_min={sil.get('minutes_open')} "
                f"sig={sil.get('signals')} fire={sil.get('fire')} "
                f"gaps={sil.get('gaps_min')} "
                f"thr={sil.get('thresholds_min')} "
                f"fire_syms={sil.get('fire_syms')}"
            ),
            "",
        ])
    eb = report.get("entry_blocks_summary") or {}
    if eb:
        lines.extend([
            "## Entry blocks (7g / tum-zaman)",
            (
                f"- rolling {eb.get('opened')}/{eb.get('signals')} "
                f"| cumulative {eb.get('cum_opened')}/{eb.get('cum_signals')}"
            ),
            "",
        ])
    lines.extend([
        "## Sistem",
        f"- lot_multiplier: {report['system'].get('lot_multiplier')}",
        f"- size_by_edge: {report['system'].get('size_by_edge')}",
        f"- concurrent risk: {report['system'].get('max_concurrent_risk_pct')}%",
        f"- aktif semboller: {', '.join(report.get('active_symbols') or [])}",
        "",
        "## Denetci",
        f"- prefer_strong_on_dd: {report.get('supervisor', {}).get('prefer_strong_on_dd')}",
        f"- hard_block_only: {report.get('supervisor', {}).get('hard_block_only_quarantine')}",
        "- kasa_auto: scripts/kasa_auto.py (lev + eq -> lot/marj)",
        "",
        "## Kacan islem (entry-blocks)",
        "",
        (
            "| Sembol | Sinyal | Acilan | Fill | Spread | Sembol dolu | "
            "Ters yon | Seans disi | Saat kapali |"
        ),
        (
            "|--------|--------|--------|------|--------|-------------|"
            "----------|------------|-------------|"
        ),
    ])
    for row in report.get("entry_blocks") or []:
        blocks = row.get("blocks") or {}
        lines.append(
            f"| {row['symbol']} | {row['signals']} | {row['opened']} | "
            f"%{float(row.get('fill_rate') or 0)*100:.0f} | "
            f"{blocks.get('spread', 0)} | {blocks.get('risk_sembol_limiti', 0)} | "
            f"{blocks.get('risk_ters_yon', 0)} | "
            f"{blocks.get('seans_disi', 0)} | {blocks.get('saat_kapali', 0)} |"
        )
    lines.extend([
        "",
        "## Sembol siralamasi (holdout net R)",
        "",
        "| Sembol | Aile/TF | Holdout R | Skor | Spread | HTF gate | Supervisor |",
        "|--------|---------|-----------|------|--------|----------|------------|",
    ])
    for r in report["ranked"]:
        lines.append(
            f"| {r['symbol']} | {r['strategy']}/{r['timeframe']} | "
            f"{r['holdout_net_r']:+.0f} | {r['opt_score']:.1f} | "
            f"{r.get('max_spread_atr')} | {r.get('htf_gate', '?')} | "
            f"{r['supervisor']} |"
        )
    lines.extend([
        "",
        "## Koru (aktif + guclu holdout)",
        ", ".join(report["keep_live"]),
        "",
        "## Reopt hazir (48h+ ve zayif)",
        ", ".join(report["reopt_ready"]) or "(yok)",
        "",
        "## Otomatik spread hedefleri (flat)",
        ", ".join(report.get("spread_auto") or []) or "(yok)",
        "",
        "## 6-slice compose (book audit)",
        "",
    ])
    robust = report.get("robust_slices") or []
    if robust:
        lines.append(
            "| Sembol | wins | floor | sumR | durum |"
        )
        lines.append(
            "|--------|------|-------|------|-------|"
        )
        for r in robust:
            wins = r.get("wins")
            sum_r = r.get("sum_r")
            lines.append(
                f"| {r['symbol']} | "
                f"{'-' if wins is None else f'{wins}/{r.get('parts', 6)}'} | "
                f"{r.get('floor')} | "
                f"{'-' if sum_r is None else f'{sum_r:+.1f}'} | "
                f"{r.get('note')} |"
            )
    else:
        lines.append("(olculmedi)")
    xs = report.get("xau_streak") or {}
    if xs:
        exp = xs.get("expectancy") or {}
        lines.extend([
            "",
            "## XAU non-winner streak",
            (
                f"{xs.get('symbol', 'XAUUSD')}: streak={xs.get('streak')} "
                f"level={xs.get('level')} "
                f"(review>={xs.get('review_at')}, "
                f"escalate>={xs.get('escalate_at')}); "
                f"last{exp.get('n')}/{exp.get('window')} "
                f"exp={exp.get('expectancy_r')}R"
            ),
        ])
    book = report.get("book_streaks") or []
    if book:
        lines.extend(["", "## Book non-winner streaks", ""])
        lines.append("| Sembol | streak | level | exp10 |")
        lines.append("|--------|--------|-------|-------|")
        for r in book:
            exp = r.get("expectancy") or {}
            lines.append(
                f"| {r.get('symbol')} | {r.get('streak')} | "
                f"{r.get('level')} | {exp.get('expectancy_r')} |"
            )
    chain = report.get("pending_chain") or {}
    if chain:
        lines.extend([
            "",
            "## Pending chain (freeze-bind / XAU sl 0.7)",
            (
                f"resume={chain.get('resume')} pending_sl={chain.get('xau_sl')} "
                f"reenable={chain.get('reenable')} done_bind={chain.get('bind_done')} "
                f"done_sl={chain.get('sl_done')} xau_enabled={chain.get('xau_enabled')} "
                f"xau_sl={chain.get('xau_sl_live')}"
            ),
        ])
    lines.extend([
        "",
        "## Onerilen aksiyonlar",
    ])
    for a in report["actions"]:
        lines.append(f"- {a}")
    if applied:
        lines.extend(["", "## Uygulanan fixler"])
        for a in applied:
            lines.append(f"- {a}")
    lines.extend([
        "",
        "## Agent dongusu",
        "Auto-pilot: scripts/auto_pilot.py (15dk gelir + AR-GE).",
        "Holdout vs canli: scripts/holdout_live_sync.py (flat aktif semboller).",
        "AR-GE: scripts/research_scanner.py -> cursor/RESEARCH_QUEUE.md",
        "Operator kapattigi semboller otomatik acilmaz.",
    ])
    return "\n".join(lines) + "\n"


def _run_family_audit(headers: dict[str, str]) -> list[str]:
    """Report-only — never force-apply a different family (04.09 SpotBrent/NAS)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "family_audit", ROOT / "scripts" / "family_audit.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.audit_report(headers)


def _run_signal_health(headers: dict[str, str]) -> list[str]:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "signal_health", ROOT / "scripts" / "signal_health.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.check_signal_health(headers)


def _run_holdout_live_sync(headers: dict[str, str]) -> list[str]:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "holdout_live_sync",
        ROOT / "scripts" / "holdout_live_sync.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.sync_flat_symbols(headers)


def _run_session_upgrades(headers: dict[str, str]) -> list[str]:
    """Charged session-window upgrades on flat enabled names (SpotBrent pattern)."""
    import importlib.util
    st = _api_get("/api/state", headers) or {}
    if (st.get("opt") or {}).get("busy"):
        return ["seans: opt busy — atlandi"]
    open_syms = {str(p.get("symbol") or "") for p in st.get("positions") or []}
    body = _api_get("/api/symbols", headers) or {}
    rows = body.get("symbols") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        return ["seans: symbols okunamadi"]
    spec = importlib.util.spec_from_file_location(
        "session_exec", ROOT / "scripts" / "session_exec.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    done: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("enabled"):
            continue
        sym = str(row.get("symbol") or "")
        if not sym or sym in open_syms:
            continue
        ok, msg = mod.apply_session_upgrade(headers, panel=PANEL, row=row)
        done.append(msg if ok else f"FAIL {msg}")
    return done


def _run_msa_upgrades(headers: dict[str, str]) -> list[str]:
    """Charged max_spread_atr upgrades on flat enabled names (US30/NAS pattern)."""
    import importlib.util
    st = _api_get("/api/state", headers) or {}
    if (st.get("opt") or {}).get("busy"):
        return ["msa: opt busy — atlandi"]
    open_syms = {str(p.get("symbol") or "") for p in st.get("positions") or []}
    body = _api_get("/api/symbols", headers) or {}
    rows = body.get("symbols") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        return ["msa: symbols okunamadi"]
    spec = importlib.util.spec_from_file_location(
        "msa_exec", ROOT / "scripts" / "msa_exec.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    done: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("enabled"):
            continue
        sym = str(row.get("symbol") or "")
        if not sym or sym in open_syms:
            continue
        ok, msg = mod.apply_msa_upgrade(headers, panel=PANEL, row=row)
        done.append(msg if ok else f"FAIL {msg}")
    return done


def _run_cost_rank_upgrades(headers: dict[str, str]) -> list[str]:
    """Charged cost_rank_max upgrades (entry gate; OK while open)."""
    import importlib.util
    st = _api_get("/api/state", headers) or {}
    if (st.get("opt") or {}).get("busy"):
        return ["cost_rank: opt busy — atlandi"]
    body = _api_get("/api/symbols", headers) or {}
    rows = body.get("symbols") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        return ["cost_rank: symbols okunamadi"]
    spec = importlib.util.spec_from_file_location(
        "cost_rank_exec", ROOT / "scripts" / "cost_rank_exec.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    done: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("enabled"):
            continue
        sym = str(row.get("symbol") or "")
        if not sym:
            continue
        ok, msg = mod.apply_cost_rank_upgrade(headers, panel=PANEL, row=row)
        done.append(msg if ok else f"FAIL {msg}")
    return done


def _run_trail_upgrades(headers: dict[str, str]) -> list[str]:
    """Charged trail_step_atr upgrades on flat names (neighbor-spike gated)."""
    import importlib.util
    st = _api_get("/api/state", headers) or {}
    if (st.get("opt") or {}).get("busy"):
        return ["trail: opt busy — atlandi"]
    open_syms = {str(p.get("symbol") or "") for p in st.get("positions") or []}
    body = _api_get("/api/symbols", headers) or {}
    rows = body.get("symbols") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        return ["trail: symbols okunamadi"]
    spec = importlib.util.spec_from_file_location(
        "trail_exec", ROOT / "scripts" / "trail_exec.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    done: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("enabled"):
            continue
        sym = str(row.get("symbol") or "")
        if not sym or sym in open_syms:
            continue
        ok, msg = mod.apply_trail_upgrade(headers, panel=PANEL, row=row)
        done.append(msg if ok else f"FAIL {msg}")
        # Re-read row after step land so start measure uses new step.
        body2 = _api_get("/api/symbols", headers) or {}
        rows2 = body2.get("symbols") if isinstance(body2, dict) else None
        if isinstance(rows2, list):
            for r2 in rows2:
                if isinstance(r2, dict) and r2.get("symbol") == sym:
                    row = r2
                    break
        ok2, msg2 = mod.apply_trail_start_upgrade(headers, panel=PANEL, row=row)
        done.append(msg2 if ok2 else f"FAIL {msg2}")
    return done


def _load_exec(name: str, path: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _run_charged_tunes(headers: dict[str, str]) -> list[str]:
    """One charged land per symbol — fixed axis order (Claude compound gate).

    Order: seans → msa → cost_rank → adx → atr_pct → body → trail_step → trail_start.
    EXIT_RISK axes (trail_*) skip symbols with open tickets.
    """
    from scripts.exec_gates import pipeline_frozen
    if pipeline_frozen():
        return ["tune: exec pipeline FREEZE (Claude 03:36)"]
    st = _api_get("/api/state", headers) or {}
    if (st.get("opt") or {}).get("busy"):
        return ["tune: opt busy — atlandi"]
    open_syms = {str(p.get("symbol") or "") for p in st.get("positions") or []}
    body = _api_get("/api/symbols", headers) or {}
    rows = body.get("symbols") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        return ["tune: symbols okunamadi"]

    sess = _load_exec("session_exec", ROOT / "scripts" / "session_exec.py")
    msa = _load_exec("msa_exec", ROOT / "scripts" / "msa_exec.py")
    cr = _load_exec("cost_rank_exec", ROOT / "scripts" / "cost_rank_exec.py")
    adx = _load_exec("adx_exec", ROOT / "scripts" / "adx_exec.py")
    atrp = _load_exec("atr_pct_exec", ROOT / "scripts" / "atr_pct_exec.py")
    bodyx = _load_exec("body_exec", ROOT / "scripts" / "body_exec.py")
    trail = _load_exec("trail_exec", ROOT / "scripts" / "trail_exec.py")

    done: list[str] = []
    kept = 0
    scanned = 0
    for row in rows:
        if not isinstance(row, dict) or not row.get("enabled"):
            continue
        sym = str(row.get("symbol") or "")
        if not sym:
            continue
        scanned += 1
        flat = sym not in open_syms
        landed = False

        if flat:
            ok, msg = sess.apply_session_upgrade(headers, panel=PANEL, row=row)
            done.append(msg if ok else f"FAIL {msg}")
            if ok and "->" in msg and "degismedi" not in msg:
                landed = True
        if not landed and flat:
            ok, msg = msa.apply_msa_upgrade(headers, panel=PANEL, row=row)
            done.append(msg if ok else f"FAIL {msg}")
            if ok and "->" in msg and "degismedi" not in msg:
                landed = True
        if not landed:
            ok, msg = cr.apply_cost_rank_upgrade(headers, panel=PANEL, row=row)
            done.append(msg if ok else f"FAIL {msg}")
            if ok and "->" in msg and "degismedi" not in msg:
                landed = True
        if not landed:
            ok, msg = adx.apply_adx_upgrade(headers, panel=PANEL, row=row)
            done.append(msg if ok else f"FAIL {msg}")
            if ok and "->" in msg and "degismedi" not in msg:
                landed = True
        if not landed:
            ok, msg = atrp.apply_atr_pct_upgrade(headers, panel=PANEL, row=row)
            done.append(msg if ok else f"FAIL {msg}")
            if ok and "->" in msg and "degismedi" not in msg:
                landed = True
        if not landed:
            ok, msg = bodyx.apply_body_upgrade(headers, panel=PANEL, row=row)
            done.append(msg if ok else f"FAIL {msg}")
            if ok and "->" in msg and "degismedi" not in msg:
                landed = True
        if not landed and flat:
            ok, msg = trail.apply_trail_upgrade(headers, panel=PANEL, row=row)
            done.append(msg if ok else f"FAIL {msg}")
            if ok and "->" in msg and "degismedi" not in msg:
                landed = True
            elif ok and "degismedi" in msg:
                ok2, msg2 = trail.apply_trail_start_upgrade(
                    headers, panel=PANEL, row=row)
                done.append(msg2 if ok2 else f"FAIL {msg2}")
                if ok2 and "->" in msg2 and "degismedi" not in msg2:
                    landed = True
        if not landed:
            kept += 1
    if scanned:
        done.append(f"tune: {kept}/{scanned} KEEP (1 land/sembol)")
    return done


def main() -> int:
    parser = argparse.ArgumentParser(description="MicoFX income development loop audit")
    parser.add_argument("--apply-safe", action="store_true",
                        help="Apply safe panel fixes (partial_at_r=0, autostart)")
    parser.add_argument("--auto", action="store_true",
                        help="Safe fixes + auto spread calibration on flat symbols")
    args = parser.parse_args()
    if args.auto:
        args.apply_safe = True
        print(
            "UYARI: --auto lockdown (04.09): family hizala OFF, cost_free "
            "no-op, spread kanitli; seans/msa/cr/trail charged + "
            "1 land/sembol/tur. Exec pipeline FREEZE (Claude 03:50) — "
            "charged tunes skip.",
            flush=True,
        )

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "income_loop.log"
    latest_path = LOG_DIR / "income_loop_latest.md"

    c = _db()
    try:
        report = audit(c)
    finally:
        c.close()

    report["symbol_queues"] = load_symbol_queues()
    report["action_queues"] = load_action_queues()
    report["day25_checklist"] = load_day25_checklist()
    try:
        from scripts.baseline_accumulate_watch import (
            maybe_alert_stale_heartbeat,
        )
        applied_pre = maybe_alert_stale_heartbeat()
    except Exception:
        applied_pre = []

    applied: list[str] = list(applied_pre)
    if args.apply_safe:
        applied.extend(apply_safe(report))
    headers, panel_up = _api_session()
    if panel_up:
        try:
            import importlib.util
            spec_br = importlib.util.spec_from_file_location(
                "book_robust_audit",
                ROOT / "scripts" / "book_robust_audit.py")
            br = importlib.util.module_from_spec(spec_br)
            assert spec_br.loader is not None
            spec_br.loader.exec_module(br)
            report["robust_slices"] = br.audit_from_panel(PANEL)
            try:
                from scripts import unfreeze_prep as _uf
                report["unfreeze_prep"] = _uf.snapshot()
            except Exception as exc:
                report["unfreeze_prep"] = {}
                applied.append(f"unfreeze_prep fail: {exc}")
            try:
                from scripts.xau_streak_watch import baseline_status, fetch_autopsy_rows
                bl = baseline_status(len(fetch_autopsy_rows()))
            except Exception:
                bl = {}
            br.append_evidence_ledger(
                report["robust_slices"],
                meta={
                    "source": "income_dev_loop",
                    "new_trades": bl.get("new_trades"),
                    "autopsy_n": bl.get("autopsy_n"),
                    "frozen": True,
                },
            )
            bad = [r for r in report["robust_slices"] if not r.get("ok")]
            if bad:
                applied.extend(br.alert_erosion(report["robust_slices"]))
        except Exception as exc:
            report["robust_slices"] = []
            applied.append(f"6-slice audit fail: {exc}")
        try:
            import importlib.util
            spec_xs = importlib.util.spec_from_file_location(
                "xau_streak_watch",
                ROOT / "scripts" / "xau_streak_watch.py")
            xs = importlib.util.module_from_spec(spec_xs)
            assert spec_xs.loader is not None
            spec_xs.loader.exec_module(xs)
            xreps, xnotes = xs.run_book(PANEL, alert=True)
            report["book_streaks"] = xreps
            xau = next(
                (r for r in xreps if r.get("symbol") == "XAUUSD"), {})
            report["xau_streak"] = xau
            applied.extend(xnotes)
            try:
                from scripts.xau_streak_watch import (
                    baseline_status,
                    fetch_autopsy_rows,
                    maybe_alert_baseline_ready,
                )
                n = len(fetch_autopsy_rows(PANEL))
                report["post_restart_baseline"] = baseline_status(n)
                applied.extend(maybe_alert_baseline_ready(n))
            except Exception as exc:
                report["post_restart_baseline"] = {"armed": False, "error": str(exc)}
            try:
                import importlib.util as _ilu2
                spec_u = _ilu2.spec_from_file_location(
                    "us30_fill_watch",
                    ROOT / "scripts" / "us30_fill_watch.py")
                uw = _ilu2.module_from_spec(spec_u)
                assert spec_u.loader is not None
                spec_u.loader.exec_module(uw)
                urep = uw.snapshot(PANEL)
                report["us30_fill"] = urep
                applied.extend(uw.maybe_alert(urep))
                try:
                    ger_path = ROOT / ".bridge" / "GER40_FILL_BASELINE.json"
                    grep = uw.snapshot(
                        PANEL, symbol="GER40", state_path=ger_path,
                        min_signals=4,
                    )
                    report["ger40_fill"] = grep
                    applied.extend(uw.maybe_alert(grep, state_path=ger_path))
                except Exception as exc:
                    report["ger40_fill"] = {}
                    applied.append(f"ger40 fill watch fail: {exc}")
                try:
                    nas_path = ROOT / ".bridge" / "NAS100_FILL_BASELINE.json"
                    nrep = uw.snapshot(
                        PANEL, symbol="NAS100", state_path=nas_path,
                        min_signals=4,
                    )
                    report["nas100_fill"] = nrep
                    applied.extend(uw.maybe_alert(nrep, state_path=nas_path))
                except Exception as exc:
                    report["nas100_fill"] = {}
                    applied.append(f"nas100 fill watch fail: {exc}")
            except Exception as exc:
                report["us30_fill"] = {}
                applied.append(f"us30 fill watch fail: {exc}")
            try:
                from scripts.session_open_silence import (
                    maybe_alert as silence_alert,
                )
                from scripts.session_open_silence import (
                    snapshot as silence_snapshot,
                )
                srep = silence_snapshot(PANEL)
                report["eu_silence"] = srep
                applied.extend(silence_alert(srep))
            except Exception as exc:
                report["eu_silence"] = {}
                applied.append(f"eu silence watch fail: {exc}")
            try:
                from scripts.xau_streak_watch import (
                    fetch_autopsy_rows as _fetch_rows,
                )
                from scripts.xau_streak_watch import (
                    maybe_alert_first_new_close,
                )
                applied.extend(maybe_alert_first_new_close(len(_fetch_rows(PANEL))))
            except Exception as exc:
                applied.append(f"first-close watch fail: {exc}")
            try:
                import http.cookiejar as _cj
                import json as _json
                import urllib.request as _ur
                _op = _ur.build_opener(_ur.HTTPCookieProcessor(_cj.CookieJar()))
                _op.open(PANEL + "/")
                _eb = _json.loads(
                    _op.open(
                        _ur.Request(
                            PANEL + "/api/analysis/entry-blocks",
                            headers={"Origin": PANEL},
                        )
                    ).read().decode()
                )
                _cum = _eb.get("cumulative") or {}
                report["entry_blocks_summary"] = {
                    "signals": _eb.get("signals"),
                    "opened": _eb.get("opened"),
                    "cum_signals": _cum.get("signals"),
                    "cum_opened": _cum.get("opened"),
                }
            except Exception as exc:
                report["entry_blocks_summary"] = {}
                applied.append(f"entry blocks summary fail: {exc}")
        except Exception as exc:
            report["book_streaks"] = []
            report["xau_streak"] = {}
            applied.append(f"xau streak watch fail: {exc}")
    # When AP was disabled only to bind freeze, restart as soon as flat.
    if panel_up:
        try:
            import importlib.util
            spec_fb = importlib.util.spec_from_file_location(
                "freeze_bind_when_flat",
                ROOT / "scripts" / "freeze_bind_when_flat.py")
            fb = importlib.util.module_from_spec(spec_fb)
            assert spec_fb.loader is not None
            spec_fb.loader.exec_module(fb)
            if fb.RESUME_FLAG.is_file():
                op = fb._session(PANEL)
                flat, npos = fb.book_flat(op, PANEL)
                if flat:
                    code, body = fb.request_restart(op, PANEL)
                    applied.append(
                        f"freeze-bind restart HTTP {code}: {body[:80]}")
                    if code in (200, 202):
                        ok, msg = fb.verify_bind(PANEL)
                        applied.append(msg if ok else f"FAIL {msg}")
                else:
                    applied.append(
                        f"freeze-bind bekleniyor: {npos} pozisyon acik")
        except Exception as exc:
            applied.append(f"freeze-bind check fail: {exc}")
        try:
            import importlib.util
            spec_xl = importlib.util.spec_from_file_location(
                "xau_sl_land",
                ROOT / "scripts" / "xau_sl_land.py")
            xl = importlib.util.module_from_spec(spec_xl)
            assert spec_xl.loader is not None
            spec_xl.loader.exec_module(xl)
            if xl.PENDING.is_file():
                ok_l, msg_l = xl.land(PANEL)
                applied.append(msg_l if ok_l else f"FAIL {msg_l}")
        except Exception as exc:
            applied.append(f"xau_sl_land fail: {exc}")
        try:
            import importlib.util
            spec_xr = importlib.util.spec_from_file_location(
                "xau_temp_reenable",
                ROOT / "scripts" / "xau_temp_reenable.py")
            xr = importlib.util.module_from_spec(spec_xr)
            assert spec_xr.loader is not None
            spec_xr.loader.exec_module(xr)
            ok_r, msg_r = xr.reenable(PANEL)
            applied.append(msg_r if ok_r else f"FAIL {msg_r}")
        except Exception as exc:
            applied.append(f"xau_temp_reenable fail: {exc}")
        report["pending_chain"] = {
            "resume": (ROOT / ".bridge" / "AUTOPILOT_RESUME_AFTER_RESTART").is_file(),
            "xau_sl": (ROOT / ".bridge" / "XAU_SL_07_PENDING").is_file(),
            "reenable": (ROOT / ".bridge" / "XAU_SL_07_REENABLE").is_file(),
            "bind_done": (ROOT / ".bridge" / "FREEZE_BIND_DONE.txt").is_file(),
            "sl_done": (ROOT / ".bridge" / "XAU_SL_07_DONE.txt").is_file(),
            "xau_enabled": None,
            "xau_sl_live": None,
        }
    if args.auto and panel_up:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "kasa_auto", ROOT / "scripts" / "kasa_auto.py")
        kasa_mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(kasa_mod)
        applied.extend(kasa_mod.apply_kasa_tune(headers))
        applied.extend(apply_trust_entries(report))
        applied.extend(apply_spread_calibration(report))
        applied.extend(_run_charged_tunes(headers))
        applied.extend(_run_holdout_live_sync(headers))
        applied.extend(_run_family_audit(headers))
        applied.extend(_run_signal_health(headers))
        import importlib.util as _ilu
        spec_cf = _ilu.spec_from_file_location(
            "cost_free_mode", ROOT / "scripts" / "cost_free_mode.py")
        cf_mod = _ilu.module_from_spec(spec_cf)
        assert spec_cf.loader is not None
        spec_cf.loader.exec_module(cf_mod)
        applied.extend(cf_mod.apply_cost_free_mode(headers))

    md = render_markdown(report, applied)
    latest_path.write_text(md, encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n{'=' * 60}\n")
        fh.write(md)

    # Do NOT rewrite cursor/FOR_CLAUDE.md — that wiped Cursor↔Claude briefs
    # every 15m. auto_pilot.py owns the <!-- autopilot:begin/end --> section.

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
