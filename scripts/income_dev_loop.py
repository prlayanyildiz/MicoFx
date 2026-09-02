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

from micofx.paths import DB_PATH, LOG_DIR  # noqa: E402

PANEL = "http://127.0.0.1:8900"
ORIGIN = PANEL
FAM = frozenset({"burst", "mtf_pullback", "ichimoku", "channel_break"})
BOOK = ("BTCUSD", "GER40", "JPN225", "NAS100", "SpotBrent", "US30", "XAUUSD")

# fill_rate below this with spread as top block -> spread calibration candidate
_SPREAD_FILL_ALERT = 0.25
# margin usage above this fraction of the configured cap -> alert
_MARGIN_ALERT_FRAC = 0.75
# auto spread-calibrate when dominant spread blocks exceed this (per enabled name)
_SPREAD_AUTO_MIN = 10


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
        spread_n = int(blocks.get("spread") or 0)
        signals = int(row.get("signals") or 0)
        fill = float(row.get("fill_rate") or 0.0)
        if spread_n < 5 or signals < 10:
            continue
        top = max(blocks.values()) if blocks else 0
        spread_dominant = spread_n >= top
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
        spread_n = int(blocks.get("spread") or 0)
        signals = int(row.get("signals") or 0)
        fill = float(row.get("fill_rate") or 0.0)
        if spread_n < _SPREAD_AUTO_MIN or signals < 5:
            continue
        top = max(blocks.values()) if blocks else 0
        if spread_n >= top and fill < 0.35:
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
    """No AI hard refuse; spread calibrate only when costs are charged."""
    headers, up = _api_session()
    if not up:
        return ["panel offline — trust mode atlandi"]
    done: list[str] = []

    ok, msg = _api_post("/api/ai/settings", headers, {
        "prefer_strong_on_dd": False,
        "hard_block_only_quarantine": True,
    })
    done.append(f"AI trust mode {'ok' if ok else 'fail'} {msg[:80]}")

    st = _api_get("/api/state", headers) or {}
    if not (st.get("system") or {}).get("charge_costs", True):
        done.append("spread kalibre atlandi (charge_costs=false)")
        return done

    live = report.get("live") or {}
    open_syms = set(live.get("open_symbols") or [])
    for sym in report.get("active_symbols") or []:
        if sym in open_syms:
            continue
        ok, msg = _api_post(f"/api/symbols/{sym}/spread-calibrate", headers, {})
        if ok:
            try:
                body = json.loads(msg)
                if body.get("changed"):
                    done.append(f"{sym} spread {body.get('before')} -> {body.get('after')}")
            except json.JSONDecodeError:
                done.append(f"{sym} spread kalibre ok")
        elif "Not Found" not in msg:
            done.append(f"{sym} spread kalibre fail: {msg[:60]}")

    return done


def apply_spread_calibration(report: dict[str, Any]) -> list[str]:
    """Auto widen spread caps on flat enabled symbols with spread pain."""
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
    targets = set(report.get("spread_auto") or [])
    open_syms = set(live.get("open_symbols") or [])
    for sym in report.get("active_symbols") or []:
        if sym in open_syms:
            continue
        targets.add(sym)

    for sym in sorted(targets):
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
            history=list(hist.get("history") or []))
        done.append(msg if ok else f"FAIL {msg}")
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
        "| Sembol | Sinyal | Acilan | Fill | Spread | Sembol dolu | Ters yon |",
        "|--------|--------|--------|------|--------|-------------|----------|",
    ]
    for row in report.get("entry_blocks") or []:
        blocks = row.get("blocks") or {}
        lines.append(
            f"| {row['symbol']} | {row['signals']} | {row['opened']} | "
            f"%{float(row.get('fill_rate') or 0)*100:.0f} | "
            f"{blocks.get('spread', 0)} | {blocks.get('risk_sembol_limiti', 0)} | "
            f"{blocks.get('risk_ters_yon', 0)} |"
        )
    lines.extend([
        "",
        "## Sembol siralamasi (holdout net R)",
        "",
        "| Sembol | Aile/TF | Holdout R | Skor | Spread tavan | Supervisor |",
        "|--------|---------|-----------|------|--------------|------------|",
    ])
    for r in report["ranked"]:
        lines.append(
            f"| {r['symbol']} | {r['strategy']}/{r['timeframe']} | "
            f"{r['holdout_net_r']:+.0f} | {r['opt_score']:.1f} | "
            f"{r.get('max_spread_atr')} | {r['supervisor']} |"
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
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "family_audit", ROOT / "scripts" / "family_audit.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.sync_family_gaps(headers)


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


def main() -> int:
    parser = argparse.ArgumentParser(description="MicoFX income development loop audit")
    parser.add_argument("--apply-safe", action="store_true",
                        help="Apply safe panel fixes (partial_at_r=0, autostart)")
    parser.add_argument("--auto", action="store_true",
                        help="Safe fixes + auto spread calibration on flat symbols")
    args = parser.parse_args()
    if args.auto:
        args.apply_safe = True

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "income_loop.log"
    latest_path = LOG_DIR / "income_loop_latest.md"
    bridge_path = ROOT / "cursor" / "FOR_CLAUDE.md"

    c = _db()
    try:
        report = audit(c)
    finally:
        c.close()

    applied: list[str] = []
    if args.apply_safe:
        applied.extend(apply_safe(report))
    headers, panel_up = _api_session()
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

    bridge_path.parent.mkdir(parents=True, exist_ok=True)
    bridge_path.write_text(
        f"# Gelir dongusu {report['ts']}\n\n"
        f"Detay: `logs/income_loop_latest.md`\n\n"
        f"Aktif: {', '.join(report.get('active_symbols') or [])}\n\n"
        f"Marj: %{report.get('live', {}).get('margin_usage_pct', '?')}/"
        f"%{report.get('live', {}).get('max_margin_usage_pct', '?')}\n\n"
        f"Spread auto: {', '.join(report.get('spread_auto') or []) or 'yok'}\n\n"
        f"Aksiyonlar:\n" + "\n".join(f"- {a}" for a in report["actions"][:10]),
        encoding="utf-8",
    )

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
