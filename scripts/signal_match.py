"""Signal + cost-series parity — refute or confirm engine/strategy divergence.

Claude deferred this as SIGNAL_MATCH (post-25). Protocol:
  1) cost_series live-style vs replay-style on the same snapshot
  2) autopsy ``signal_bar_time`` ⊆ compute() signal bars (config-era + TF filter)

Read-only: panel GET + ``data/holdout_bars``. No MT5. No POST.

    python scripts/signal_match.py
    python scripts/signal_match.py --symbols NAS100,XAUUSD

Verdicts per symbol:
  COST_DIVERGE  — live vs replay cost series disagree enough to change signals
  SIGNAL_MISS   — filled live bars the current cfg does not signal (integrity)
  SIGNAL_OK     — filled bars ⊆ compute set (gates may still block extras)
  NO_COVERAGE   — snapshot / autopsy window do not overlap usefully
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from micofx import backtest  # noqa: E402
from micofx.bar_snapshot import read, snapshot_path  # noqa: E402
from micofx.models import SymbolConfig  # noqa: E402
from micofx.mt5client import timeframe_seconds  # noqa: E402
from micofx.strategy import IndicatorCache, Params, compute  # noqa: E402
from scripts.panel_session import opener as _panel_opener  # noqa: E402

PANEL = "http://127.0.0.1:8900"
LIVE_DEFAULT = ("GER40", "NAS100", "XAUUSD")
OUT = ROOT / ".bridge" / "SIGNAL_MATCH_REPORT.json"

# Cost: median |live-replay|/median(replay) above this → diverge.
_COST_REL_MEDIAN = 0.15
# Cost: share of bars where relative gap > 25% → diverge.
_COST_FRAC_HOT = 0.20
# Signal: miss rate among covered autopsy fills above this → SIGNAL_MISS.
_MISS_RATE_FIRE = 0.15
# TF filter: |gap - tf_sec| / tf_sec
_TF_TOL = 0.35


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def tf_gap_ok(fill_time: float, signal_bar_time: float, tf_sec: int,
              tol: float = _TF_TOL) -> bool:
    """EK24-G: fill−signal_bar_open clusters on the live TF length."""
    if tf_sec <= 0 or signal_bar_time <= 0 or fill_time <= 0:
        return False
    gap = float(fill_time) - float(signal_bar_time)
    if gap <= 0:
        return False
    return abs(gap - tf_sec) / tf_sec <= tol


def filter_autopsy_rows(
    rows: list[dict[str, Any]],
    *,
    symbol: str,
    tf_sec: int,
    since_ts: float = 0.0,
) -> list[dict[str, Any]]:
    """Config-era + TF-matched filled signals for one symbol."""
    out: list[dict[str, Any]] = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("symbol") or "") != symbol:
            continue
        sig = _f(r.get("signal_bar_time"))
        fill = _f(r.get("fill_time"))
        if sig <= 0 or fill <= 0:
            continue
        if since_ts > 0 and fill < since_ts:
            continue
        if not tf_gap_ok(fill, sig, tf_sec):
            continue
        out.append(r)
    return out


def live_style_cost(spread: np.ndarray, point: float, commission: float) -> np.ndarray:
    """Engine._cost_series: raw bar spread * point + commission (no impute/scale)."""
    return np.asarray(spread, dtype=np.float64) * float(point) + float(commission)


def replay_style_cost(spread: np.ndarray, point: float, scale: float,
                      commission: float) -> np.ndarray:
    """walk_forward / charged_holdout path."""
    _, spread_price, _, _ = backtest.spread_cost_series(
        spread, float(point), float(scale), min_stop=None)
    return np.asarray(spread_price, dtype=np.float64) + float(commission)


def cost_parity(
    live_cost: np.ndarray,
    replay_cost: np.ndarray,
    *,
    rel_median_fire: float = _COST_REL_MEDIAN,
    frac_hot_fire: float = _COST_FRAC_HOT,
) -> dict[str, Any]:
    live = np.asarray(live_cost, dtype=np.float64)
    rep = np.asarray(replay_cost, dtype=np.float64)
    n = int(min(live.size, rep.size))
    if n == 0:
        return {"n": 0, "diverge": False, "reason": "empty"}
    live, rep = live[:n], rep[:n]
    denom = np.maximum(np.abs(rep), 1e-12)
    rel = np.abs(live - rep) / denom
    med_rep = float(np.median(np.abs(rep)))
    med_gap = float(np.median(np.abs(live - rep)))
    rel_med = (med_gap / med_rep) if med_rep > 0 else 0.0
    frac_hot = float(np.mean(rel > 0.25))
    # Signal-relevant: would cost_rank / burst thresholds flip?
    diverge = bool(rel_med >= rel_median_fire or frac_hot >= frac_hot_fire)
    return {
        "n": n,
        "median_live": float(np.median(live)),
        "median_replay": float(np.median(rep)),
        "median_abs_gap": med_gap,
        "rel_median_gap": round(rel_med, 4),
        "frac_bars_rel_gt_25pct": round(frac_hot, 4),
        "diverge": diverge,
        "reason": (
            f"rel_med={rel_med:.3f} frac_hot={frac_hot:.3f}"
            if diverge else "within band"
        ),
    }


def signal_bar_times(sig, times: np.ndarray, tradable: np.ndarray | None = None
                     ) -> tuple[set[int], set[int], set[int]]:
    """Bar open stamps where compute fires buy / sell (session-masked)."""
    buy = np.asarray(sig.buy, dtype=bool).copy()
    sell = np.asarray(sig.sell, dtype=bool).copy()
    if tradable is not None:
        mask = np.asarray(tradable, dtype=bool)
        m = min(mask.size, buy.size)
        buy[:m] &= mask[:m]
        sell[:m] &= mask[:m]
        buy[m:] = False
        sell[m:] = False
    t = np.asarray(times, dtype=np.int64)
    buy_t = {int(t[i]) for i in np.flatnonzero(buy) if i < t.size}
    sell_t = {int(t[i]) for i in np.flatnonzero(sell) if i < t.size}
    return buy_t | sell_t, buy_t, sell_t


def match_autopsy_to_signals(
    autopsy: list[dict[str, Any]],
    all_sig: set[int],
    buy_t: set[int],
    sell_t: set[int],
    *,
    time_lo: int,
    time_hi: int,
) -> dict[str, Any]:
    """Filled live signals inside snapshot window vs compute set."""
    covered = [
        r for r in autopsy
        if time_lo <= int(_f(r.get("signal_bar_time"))) <= time_hi
    ]
    hit = miss = side_miss = 0
    misses: list[dict[str, Any]] = []
    for r in covered:
        sig_t = int(_f(r.get("signal_bar_time")))
        side = str(r.get("side") or "").lower()
        if sig_t in all_sig:
            hit += 1
            if side == "buy" and sig_t not in buy_t and sig_t in sell_t:
                side_miss += 1
            elif side == "sell" and sig_t not in sell_t and sig_t in buy_t:
                side_miss += 1
        else:
            miss += 1
            if len(misses) < 12:
                misses.append({
                    "ticket": r.get("ticket"),
                    "signal_bar_time": sig_t,
                    "side": side,
                    "r_realised": r.get("r_realised"),
                })
    n = len(covered)
    miss_rate = (miss / n) if n else 0.0
    return {
        "autopsy_tf_filtered": len(autopsy),
        "covered_in_snapshot": n,
        "hit": hit,
        "miss": miss,
        "side_miss": side_miss,
        "miss_rate": round(miss_rate, 4),
        "hit_rate": round((hit / n) if n else 0.0, 4),
        "miss_samples": misses,
    }


def build_signals_for_cfg(
    snap: dict[str, Any],
    cfg: SymbolConfig,
    *,
    cost_mode: str,
) -> tuple[Any, np.ndarray, np.ndarray]:
    """Return (Signals, cost_series, tradable_mask)."""
    bars = snap["bars"]
    info = snap["info"]
    point = float(info["point"])
    commission = backtest.commission_in_price(
        cfg.commission_per_lot,
        float(info["tick_value"]),
        float(info["tick_size"]),
    )
    if cost_mode == "live":
        cost = live_style_cost(bars.spread, point, commission)
    elif cost_mode == "replay":
        cost = replay_style_cost(
            bars.spread, point, float(snap["spread_scale"]), commission)
    else:
        raise ValueError(cost_mode)
    tf_sec = timeframe_seconds(str(cfg.timeframe))
    cache = IndicatorCache(
        bars.high, bars.low, bars.close, bars.time, tf_sec,
        bars.open, bars.volume, cost,
    )
    p = Params.from_config(cfg)
    sig = compute(cache, p)
    tradable = backtest.session_mask(
        cfg, bars.time, bool(snap["trade_all_hours"]))
    return sig, cost, tradable


def analyse_symbol(
    row: dict[str, Any],
    autopsy_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    sym = str(row.get("symbol") or "")
    tf = str(row.get("timeframe") or "")
    path = snapshot_path(sym, tf)
    base: dict[str, Any] = {
        "symbol": sym,
        "strategy": row.get("strategy"),
        "timeframe": tf,
        "opt_updated_at": row.get("opt_updated_at"),
        "snapshot": str(path),
        "snapshot_exists": path.exists(),
    }
    if not path.exists():
        base["verdict"] = "NO_COVERAGE"
        base["note"] = "holdout snapshot missing"
        return base

    snap = read(path)
    # Overlay live row onto SymbolConfig (not the stamped snapshot config).
    cfg = SymbolConfig.from_dict({
        **(snap.get("config") or {}),
        **{k: v for k, v in row.items()
           if k not in ("available", "digits", "description", "session_text",
                        "resolved_symbol", "volume_min", "volume_step")},
    })
    tf_sec = timeframe_seconds(tf)
    since = _f(row.get("opt_updated_at"))
    autopsy_era = filter_autopsy_rows(
        autopsy_rows, symbol=sym, tf_sec=tf_sec, since_ts=since)
    autopsy_tf = filter_autopsy_rows(
        autopsy_rows, symbol=sym, tf_sec=tf_sec, since_ts=0.0)

    sig_live, cost_live, tradable = build_signals_for_cfg(
        snap, cfg, cost_mode="live")
    sig_rep, cost_rep_series, _ = build_signals_for_cfg(
        snap, cfg, cost_mode="replay")
    cost_rep = cost_parity(cost_live, cost_rep_series)

    all_l, buy_l, sell_l = signal_bar_times(sig_live, snap["bars"].time, tradable)
    all_r, buy_r, sell_r = signal_bar_times(sig_rep, snap["bars"].time, tradable)
    only_live = len(all_l - all_r)
    only_rep = len(all_r - all_l)
    union = len(all_l | all_r) or 1
    sig_cost_jaccard = len(all_l & all_r) / union

    t = np.asarray(snap["bars"].time, dtype=np.int64)
    time_lo, time_hi = int(t[0]), int(t[-1])
    match_era = match_autopsy_to_signals(
        autopsy_era, all_l, buy_l, sell_l, time_lo=time_lo, time_hi=time_hi)
    match_tf = match_autopsy_to_signals(
        autopsy_tf, all_l, buy_l, sell_l, time_lo=time_lo, time_hi=time_hi)
    match_rep_tf = match_autopsy_to_signals(
        autopsy_tf, all_r, buy_r, sell_r, time_lo=time_lo, time_hi=time_hi)

    # Prefer era-matched autopsy when the snapshot still covers post-apply fills;
    # otherwise TF-window match is diagnostic only (cfg may have churned).
    era_ok = match_era["covered_in_snapshot"] >= 5
    match = match_era if era_ok else match_tf
    match_mode = "era" if era_ok else "tf_window"

    snap_stale = bool(since > 0 and time_hi < since)

    if cost_rep["diverge"] and sig_cost_jaccard < 0.85:
        verdict = "COST_DIVERGE"
        note = (
            f"cost {cost_rep['reason']}; signal jaccard live/replay="
            f"{sig_cost_jaccard:.3f} (only_live={only_live} only_rep={only_rep})"
        )
    elif match["covered_in_snapshot"] == 0:
        verdict = "NO_COVERAGE"
        note = (
            "no TF-matched autopsy fills inside snapshot window"
            + ("; snapshot ends before opt_updated_at" if snap_stale else "")
        )
    elif (
        match["miss_rate"] >= _MISS_RATE_FIRE
        and match["covered_in_snapshot"] >= 5
        and match_mode == "era"
    ):
        verdict = "SIGNAL_MISS"
        note = (
            f"era miss_rate={match['miss_rate']:.3f} "
            f"({match['miss']}/{match['covered_in_snapshot']}) "
            f"current cfg does not reproduce post-apply fills"
        )
    elif (
        match_mode == "tf_window"
        and match["miss_rate"] >= _MISS_RATE_FIRE
        and match["covered_in_snapshot"] >= 5
    ):
        # Historical fills under possibly other family/TF — soft flag, not fail.
        verdict = "SIGNAL_DRIFT"
        note = (
            f"tf_window miss_rate={match['miss_rate']:.3f} "
            f"({match['miss']}/{match['covered_in_snapshot']}); "
            f"era_covered={match_era['covered_in_snapshot']}"
            + ("; SNAPSHOT_STALE" if snap_stale else "")
            + " - capture fresh holdout to harden"
        )
    else:
        verdict = "SIGNAL_OK"
        note = (
            f"mode={match_mode} hit_rate={match['hit_rate']:.3f} "
            f"covered={match['covered_in_snapshot']} "
            f"cost={cost_rep['reason']}"
            + ("; SNAPSHOT_STALE" if snap_stale else "")
        )

    base.update({
        "verdict": verdict,
        "note": note,
        "snapshot_stale_vs_opt": snap_stale,
        "match_mode": match_mode,
        "cost_parity": cost_rep,
        "signal_counts": {
            "live_cost": len(all_l),
            "replay_cost": len(all_r),
            "only_live_cost": only_live,
            "only_replay_cost": only_rep,
            "jaccard": round(sig_cost_jaccard, 4),
        },
        "match_era": match_era,
        "match_tf_window": match_tf,
        "match_replay_tf_window": match_rep_tf,
        "snapshot_time_range": [time_lo, time_hi],
    })
    return base


def fetch_bundle(panel: str = PANEL) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
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
    symbols = list(rows) if isinstance(rows, list) else []
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
    return symbols, list(trades) if isinstance(trades, list) else []


def run_report(
    symbols: list[dict[str, Any]],
    autopsy: list[dict[str, Any]],
    *,
    want: set[str] | None = None,
) -> dict[str, Any]:
    rows = [
        r for r in symbols
        if isinstance(r, dict) and (want is None or r.get("symbol") in want)
    ]
    out_rows = [analyse_symbol(r, autopsy) for r in rows]
    hard = [r for r in out_rows if r.get("verdict") in ("COST_DIVERGE", "SIGNAL_MISS")]
    soft = [r for r in out_rows if r.get("verdict") == "SIGNAL_DRIFT"]
    stale = any(r.get("snapshot_stale_vs_opt") for r in out_rows)
    if hard:
        book = "INTEGRITY_FAIL"
    elif soft:
        book = "INTEGRITY_DRIFT"
    elif any(r.get("verdict") == "NO_COVERAGE" for r in out_rows):
        book = "INCONCLUSIVE"
    elif stale:
        book = "INTEGRITY_OK_STALE_SNAP"
    else:
        book = "INTEGRITY_OK"
    return {
        "at": datetime.now(UTC).isoformat(),
        "note": "measure-only; Claude SIGNAL_MATCH protocol",
        "book_verdict": book,
        "rows": out_rows,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--panel", default=PANEL)
    ap.add_argument("--symbols", default=",".join(LIVE_DEFAULT))
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    want = {s.strip() for s in args.symbols.split(",") if s.strip()}

    symbols, autopsy = fetch_bundle(args.panel)
    report = run_report(symbols, autopsy, want=want or None)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"book_verdict={report['book_verdict']}", flush=True)
    for r in report["rows"]:
        print(f"{r['symbol']}: {r['verdict']} - {r.get('note')}", flush=True)
    print(f"wrote {args.out}", flush=True)
    return 0 if report["book_verdict"] != "INTEGRITY_FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
