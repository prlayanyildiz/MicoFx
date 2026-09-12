"""NAS soft-bleed CLI shim — logic lives in ``xau_streak_watch``.

The standalone watch duplicated baseline streak expectancy (exp < −0.30R /
10, plus net ≤ −3.0R). That path now runs every ``baseline_accumulate_watch``
tick via ``alert_book``. Keep this file as a one-shot diagnostic CLI and for
import compatibility; do not schedule a second process.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.panel_session import opener as _panel_opener  # noqa: E402
from scripts.xau_streak_watch import (  # noqa: E402
    EXP_ALERT_R,
    EXP_WINDOW,
    NET_ALERT_R,
    recent_expectancy,
)

PANEL = "http://127.0.0.1:8900"
SYMBOL = "NAS100"
LAST_N = EXP_WINDOW
EXP_FLOOR = EXP_ALERT_R
NET_FLOOR = NET_ALERT_R


def window_stats(
    rows: list[dict[str, Any]],
    *,
    symbol: str = SYMBOL,
    last_n: int = LAST_N,
) -> dict[str, Any]:
    """Newest ``last_n`` closes → n / net_r / expectancy (streak helper)."""
    exp = recent_expectancy(rows, symbol=symbol, n=last_n)
    return {
        "n": int(exp.get("n") or 0),
        "net_r": float(exp.get("net_r") or 0.0),
        "expectancy": float(exp.get("expectancy_r") or 0.0),
        "wins": 0,
        "losses": 0,
        "tickets": [],
    }


def evaluate(
    stats: dict[str, Any],
    *,
    strategy: str | None = None,
    exp_floor: float = EXP_FLOOR,
    net_floor: float = NET_FLOOR,
    min_n: int = 5,
) -> dict[str, Any]:
    """``fire`` on soft live window — family no longer gates (any live family)."""
    del strategy  # retained for call-site compat; soft bleed is family-agnostic
    n = int(stats.get("n") or 0)
    exp = float(stats.get("expectancy") or 0.0)
    net = float(stats.get("net_r") or 0.0)
    soft = n >= min_n and (exp < exp_floor or net <= net_floor)
    return {
        "strategy": None,
        "family_ok": True,
        "stats": stats,
        "exp_floor": exp_floor,
        "net_floor": net_floor,
        "min_n": min_n,
        "fire": soft,
        "reason": (
            f"{SYMBOL} live exp {exp:.2f}R / {n} "
            f"(<{exp_floor}; net {net:.2f}R)"
            if soft else ""
        ),
    }


def maybe_alert(
    report: dict[str, Any],
    *,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    gemini_inbox: Path | None = None,
) -> list[str]:
    """No-op: baseline streak watch owns wakes. Kept so old callers stay quiet."""
    del report, state_path, wake_path, gemini_inbox
    return []


def fetch_bundle(panel: str = PANEL) -> tuple[str | None, list[dict[str, Any]]]:
    import urllib.request

    op = _panel_opener(panel)
    sym_body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/symbols", headers={"Origin": panel},
            ),
            timeout=20,
        ).read().decode()
    )
    rows = sym_body.get("symbols") if isinstance(sym_body, dict) else None
    strategy = None
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and row.get("symbol") == SYMBOL:
                strategy = str(row.get("strategy") or "") or None
                break
    aut = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/analysis/trade-autopsies",
                headers={"Origin": panel},
            ),
            timeout=30,
        ).read().decode()
    )
    trades = aut.get("rows") or []
    return strategy, list(trades) if isinstance(trades, list) else []


def main(argv: list[str] | None = None) -> int:
    del argv
    strategy, rows = fetch_bundle()
    stats = window_stats(rows)
    report = evaluate(stats, strategy=strategy)
    report["note"] = "shim — soft bleed wakes via baseline_accumulate_watch"
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
