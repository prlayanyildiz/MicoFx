"""Income development loop — audit live book, apply safe fixes, plan next steps.

Runs outside the engine process. Reads micofx.db read-only where possible;
safe writes go through the live panel API (Origin header required).

Usage:
    C:\\MicoFX-venv\\Scripts\\python.exe scripts/income_dev_loop.py
    C:\\MicoFX-venv\\Scripts\\python.exe scripts/income_dev_loop.py --apply-safe
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
RETIRED = frozenset({"stoch_flip", "dual_t3", "t3_flip", "parabolic_flip",
                     "wavetrend_flip", "t3_stoch", "macd_flip", "aroon_flip"})
BOOK = ("BTCUSD", "GER40", "JPN225", "NAS100", "SpotBrent", "US30", "XAUUSD")

# fill_rate below this with spread as top block → spread calibration candidate
_SPREAD_FILL_ALERT = 0.25


def _db() -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10.0)
    c.row_factory = sqlite3.Row
    return c


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
    """Return (cookie_header, panel_up)."""
    try:
        req = urllib.request.Request(f"{PANEL}/", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            cookies = resp.headers.get_all("Set-Cookie") or []
        if not cookies:
            return {}, True
        return {"Cookie": "; ".join(c.split(";")[0] for c in cookies)}, True
    except (urllib.error.URLError, TimeoutError, OSError):
        return {}, False


def _api_get(path: str, headers: dict[str, str]) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(f"{PANEL}{path}", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def _api_post(path: str, headers: dict[str, str], body: dict[str, Any]) -> tuple[bool, str]:
    data = json.dumps(body).encode()
    h = {**headers, "Origin": ORIGIN, "Content-Type": "application/json"}
    try:
        req = urllib.request.Request(f"{PANEL}{path}", data=data, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return True, resp.read().decode()[:200]
    except urllib.error.HTTPError as exc:
        return False, exc.read().decode()[:300]
    except Exception as exc:
        return False, str(exc)


def fetch_entry_blocks(headers: dict[str, str]) -> list[dict[str, Any]]:
    data = _api_get("/api/analysis/entry-blocks", headers)
    if not data:
        return []
    return list(data.get("rows") or [])


def spread_recovery_actions(headers: dict[str, str]) -> list[str]:
    """Symbols losing trades to spread gate — calibrate when flat."""
    rows = fetch_entry_blocks(headers)
    actions: list[str] = []
    for row in rows:
        sym = row.get("symbol", "")
        if sym not in BOOK:
            continue
        blocks = row.get("blocks") or {}
        spread_n = int(blocks.get("spread") or 0)
        signals = int(row.get("signals") or 0)
        fill = float(row.get("fill_rate") or 0.0)
        if spread_n < 10 or signals < 20:
            continue
        if spread_n >= max(blocks.values(), default=0) and fill < _SPREAD_FILL_ALERT:
            actions.append(
                f"SPREAD {sym}: {spread_n}/{signals} sinyal spread'de kaldi "
                f"(fill %{fill*100:.0f}) — pozisyon yokken opt apply ile kalibre et"
            )
    return actions


def audit(c: sqlite3.Connection) -> dict[str, Any]:
    syms = _symbols(c)
    sup_state = _setting(c, "supervisor_state", {}) or {}
    verdicts = sup_state.get("verdicts") or {}
    system = _setting(c, "system", {}) or {}
    job = _setting(c, "last_opt_job", {}) or {}
    supervisor = _setting(c, "supervisor", {}) or {}

    ranked = []
    for sym in BOOK:
        p = syms.get(sym) or {}
        hold = (p.get("opt_summary") or {}).get("holdout") or {}
        v = verdicts.get(sym) or {}
        ranked.append({
            "symbol": sym,
            "enabled": bool(p.get("enabled")),
            "strategy": p.get("strategy"),
            "timeframe": p.get("timeframe"),
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
        if not r["enabled"] and float(r.get("opt_score") or 0) > 0:
            actions.append(f"ENABLE {r['symbol']} (optimized, currently off)")

    if not system.get("autostart_bot"):
        actions.append("SET autostart_bot=true")
    if job.get("state") == "running":
        actions.append("WAIT opt job running — do not start another scan")

    headers, panel_up = _api_session()
    if panel_up:
        actions.extend(spread_recovery_actions(headers))

    return {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system": {
            "lot_multiplier": system.get("lot_multiplier"),
            "size_by_edge": system.get("size_by_edge"),
            "max_margin_usage_pct": system.get("max_margin_usage_pct"),
            "max_concurrent_risk_pct": system.get("max_concurrent_risk_pct"),
            "autostart_bot": system.get("autostart_bot"),
        },
        "opt_job": job.get("state"),
        "ranked": ranked,
        "reopt_ready": reopt_ready,
        "actions": actions,
        "keep_live": [
            r["symbol"] for r in ranked
            if r["symbol"] in ("XAUUSD", "NAS100", "JPN225", "BTCUSD")
        ],
    }


def apply_safe(report: dict[str, Any]) -> list[str]:
    headers, up = _api_session()
    if not up:
        return ["panel offline — safe fixes skipped"]
    headers["Origin"] = ORIGIN
    done: list[str] = []

    state = _api_get("/api/state", headers)
    if state and not (state.get("system") or {}).get("autostart_bot"):
        ok, msg = _api_post("/api/system", headers, {"autostart_bot": True})
        done.append(f"autostart_bot={'ok' if ok else 'fail'} {msg[:80]}")

    for sym in BOOK:
        row = next((r for r in report["ranked"] if r["symbol"] == sym), None)
        if not row or row["partial_at_r"] in (0, 0.0, None):
            continue
        ok, msg = _api_post(f"/api/symbols/{sym}", headers, {"partial_at_r": 0})
        done.append(f"{sym} partial_at_r=0 {'ok' if ok else 'fail'}")

    return done


def render_markdown(report: dict[str, Any], applied: list[str]) -> str:
    lines = [
        f"# Gelir dongusu — {report['ts']}",
        "",
        "## Sistem",
        f"- lot_multiplier: {report['system'].get('lot_multiplier')}",
        f"- size_by_edge: {report['system'].get('size_by_edge')}",
        f"- margin: {report['system'].get('max_margin_usage_pct')}%",
        f"- concurrent risk: {report['system'].get('max_concurrent_risk_pct')}%",
        f"- opt job: {report.get('opt_job')}",
        "",
        "## Sembol siralamasi (holdout net R)",
        "",
        "| Sembol | Aile/TF | Holdout R | Skor | Supervisor | Yas (saat) |",
        "|--------|---------|-----------|------|------------|------------|",
    ]
    for r in report["ranked"]:
        lines.append(
            f"| {r['symbol']} | {r['strategy']}/{r['timeframe']} | "
            f"{r['holdout_net_r']:+.0f} | {r['opt_score']:.1f} | "
            f"{r['supervisor']} | {r['opt_age_h'] or '-'} |"
        )
    lines.extend([
        "",
        "## Koru (canli > opt adayi)",
        ", ".join(report["keep_live"]),
        "",
        "## Reopt hazir (48h+ ve zayif)",
        ", ".join(report["reopt_ready"]) or "(yok)",
        "",
        "## Onerilen aksiyonlar",
    ])
    for a in report["actions"]:
        lines.append(f"- {a}")
    if applied:
        lines.extend(["", "## Uygulanan guvenli fixler"])
        for a in applied:
            lines.append(f"- {a}")
    lines.extend([
        "",
        "## Agent sonraki tur",
        "1. `reopt_ready` semboller icin manuel opt dusun (pozisyon yokken).",
        "2. Watch sembollerde lot kisik — supervisor kanit toplansin, zorla acma.",
        "3. XAUUSD/NAS100/JPN225 risk yarisi oncelikli (priority + size_by_edge).",
        "4. Kod degisikligi: fail-first test, pytest, ruff, operator onayi ile commit.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="MicoFX income development loop audit")
    parser.add_argument("--apply-safe", action="store_true",
                        help="Apply safe panel fixes (partial_at_r=0, autostart)")
    args = parser.parse_args()

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
        applied = apply_safe(report)

    md = render_markdown(report, applied)
    latest_path.write_text(md, encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n{'=' * 60}\n")
        fh.write(md)

    bridge_path.parent.mkdir(parents=True, exist_ok=True)
    bridge_path.write_text(
        f"# Gelir dongusu {report['ts']}\n\n"
        f"Detay: `logs/income_loop_latest.md`\n\n"
        f"Reopt hazir: {', '.join(report['reopt_ready']) or 'yok'}\n\n"
        f"Aksiyonlar:\n" + "\n".join(f"- {a}" for a in report["actions"][:8]),
        encoding="utf-8",
    )

    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
