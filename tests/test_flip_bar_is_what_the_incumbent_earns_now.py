"""Operator, 10.09 23:3x: "taramada isle yaramiyor aile vs bulamiyr".

They were right, and the reason was in the two runs sitting in ``opt_runs``.

NAS100, M30, candidate ``range_fade``: selection +34.6R at PF 1.36, holdout
+21.5R at PF 1.45, holdout retention 1.855 - the untouched slice scored
*better* than the one it was picked on. Refused, ``keep_reason``:
``aile/TF flip icin holdout yetersiz (21.5R < 79.1R)``.

The same report's ``baseline`` block - the live config replayed on the same
bars, in the same run - was **-22.6R at PF 0.85**. XAUUSD the same evening:
candidate +33.2R refused for "< 162.2R", incumbent measured at -30.1R.

So F1 was defending a config that loses money, using the scorecard that
config earned on the day it was applied. ``_incumbent_guard_holdout`` reads
``cfg.opt_summary["holdout"]``, a stamp; nothing ages it. The system already
knew better: ``_incumbent_kept_tail`` prints the fresh replay in the log line
right beside the rejection ("taze test -22.6R"). Only the gate that made the
decision ignored it.

F1 and F2 now benchmark against ``_flip_benchmark``: the fresh same-window
replay when there is one, the stamp when there is not.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


def _opt(cfg: SymbolConfig, *, charging: bool = True) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.symbols = {cfg.symbol: cfg}
    opt.store.system = MagicMock(charge_costs=charging, block_high_cost=False)
    opt.store.opt_params.return_value = {"min_positive_ratio": 0.6}
    opt.store.get_setting.return_value = {"reopt_min_age_hours": 0.0}
    opt._force_apply = False
    opt._beats_incumbent = lambda cfg, hold: True
    opt._generalises = lambda best, symbol: True
    return opt


def _best(hold_net: float, pos: float = 1.0) -> dict:
    return {
        "score": 10.0,
        "positive_ratio": pos,
        "min_positive_ratio": 0.6,
        "holdout": {
            "net_r": hold_net, "score": 8.0, "trades": 152,
            "expectancy": 0.141, "profit_factor": 1.45,
            "cost_per_trade_r": 0.01,
        },
        "validation": {
            "net_r": hold_net, "score": 9.0, "trades": 152,
            "expectancy": 0.141, "profit_factor": 1.45,
            "cost_per_trade_r": 0.01,
        },
    }


def _nas100() -> SymbolConfig:
    """The live row as it stood, with the stamp that produced the 79.1R bar."""
    cfg = SymbolConfig(symbol="NAS100", magic=990014, strategy="mtf_pullback",
                       timeframe="M30")
    cfg.opt_updated_at = time.time() - 30 * 86400
    cfg.opt_summary = {
        "holdout": {"net_r": 68.8, "score": 40.0},   # x1.15 -> the 79.1R bar
        "positive_ratio": 1.0,
        "validated": True,
        "charge_costs": True,
    }
    return cfg


# ------------------------------------------------------------- the live case

def test_a_losing_incumbent_no_longer_blocks_a_winning_candidate():
    cfg = _nas100()
    opt = _opt(cfg)
    opt._fresh_incumbent_holdout = lambda c: {"net_r": -22.6, "score": -8.0,
                                              "profit_factor": 0.85}
    reason = opt.reject_reason(cfg, _best(21.5), strategy="range_fade",
                               timeframe="M30")
    assert reason == "", f"still blocked: {reason}"


def test_the_stamp_alone_would_have_blocked_it():
    """Same numbers, no fresh replay: the 10.09 behaviour, for contrast."""
    cfg = _nas100()
    opt = _opt(cfg)
    opt._fresh_incumbent_holdout = lambda c: None
    reason = opt.reject_reason(cfg, _best(21.5), strategy="range_fade",
                               timeframe="M30")
    assert "aile/TF flip" in reason
    assert "79.1R" in reason, reason


# ----------------------------------------------- what must still be defended

def test_a_winning_incumbent_still_gets_its_fifteen_percent():
    """The brake exists for a reason: a profitable config is not swapped for
    a marginally better one, because a flip discards its live record."""
    cfg = _nas100()
    opt = _opt(cfg)
    opt._fresh_incumbent_holdout = lambda c: {"net_r": 100.0, "score": 40.0}
    assert "aile/TF flip" in opt.reject_reason(
        cfg, _best(110.0), strategy="range_fade", timeframe="M30")
    assert opt.reject_reason(
        cfg, _best(116.0), strategy="range_fade", timeframe="M30") == ""


def test_the_fresh_measurement_wins_over_the_stamp_in_both_directions():
    """Not "take the lower bar" - take the current one. A stamp that
    understates a now-profitable incumbent must not wave a candidate
    through either."""
    cfg = _nas100()
    cfg.opt_summary["holdout"] = {"net_r": 10.0, "score": 5.0}  # stale, low
    opt = _opt(cfg)
    opt._fresh_incumbent_holdout = lambda c: {"net_r": 90.0, "score": 40.0}
    # 20R clears the stale 11.5R bar and fails the real 103.5R one.
    reason = opt.reject_reason(cfg, _best(20.0), strategy="range_fade",
                               timeframe="M30")
    assert "aile/TF flip" in reason
    assert "103.5R" in reason, reason


def test_a_cost_free_search_still_uses_the_stamp():
    """_fresh_incumbent_holdout refuses to replay when the book searches
    cost-free (A1 churn: a charged replay would depress the incumbent and
    wave every paper candidate through). The fallback must hold there."""
    cfg = _nas100()
    opt = _opt(cfg, charging=False)
    reason = opt.reject_reason(cfg, _best(21.5), strategy="range_fade",
                               timeframe="M30")
    assert "aile/TF flip" in reason, reason


def test_same_family_nudges_are_untouched():
    cfg = _nas100()
    opt = _opt(cfg)
    opt._fresh_incumbent_holdout = lambda c: {"net_r": -22.6, "score": -8.0}
    assert opt.reject_reason(cfg, _best(1.0), strategy="mtf_pullback",
                             timeframe="M30") == ""


# ------------------------------------------------------- say which bar it was

def test_the_rejection_names_the_benchmark_it_used():
    """"21.5R < 79.1R" read as arithmetic. It was today against last month."""
    cfg = _nas100()
    opt = _opt(cfg)
    opt._fresh_incumbent_holdout = lambda c: None
    assert "damga" in opt.reject_reason(
        cfg, _best(21.5), strategy="range_fade", timeframe="M30")

    opt2 = _opt(_nas100())
    cfg2 = opt2.store.symbols["NAS100"]
    opt2._fresh_incumbent_holdout = lambda c: {"net_r": 100.0, "score": 40.0}
    assert "taze test" in opt2.reject_reason(
        cfg2, _best(110.0), strategy="range_fade", timeframe="M30")


def test_the_dwell_gate_reads_the_same_benchmark():
    """F2 compared a holdout jump against the stamp too, inside 12h."""
    import inspect

    src = inspect.getsource(Optimizer.reject_reason)
    assert src.count("_flip_benchmark(cfg, baseline)") == 2, \
        "F1 and F2 must both read the same benchmark, baseline included"
    assert "self._incumbent_guard_holdout(cfg).get" not in src, \
        "a gate is back on the stamp directly"


def test_the_sweeps_own_baseline_is_preferred_over_any_replay():
    """walk_forward measured it already: Params.from_config(cfg) on this
    sweep's holdout slice, this sweep's window, this sweep's cost regime
    (backtest.py:1536). Free, and exactly apples-to-apples."""
    cfg = _nas100()
    opt = _opt(cfg)
    opt._fresh_incumbent_holdout = lambda c: {"net_r": 500.0}  # must not win
    block, name = opt._flip_benchmark(cfg, {"holdout": {"net_r": -22.6}})
    assert name == "ayni kosu"
    assert block["net_r"] == -22.6
    reason = opt.reject_reason(cfg, _best(21.5), strategy="range_fade",
                               timeframe="M30",
                               baseline={"holdout": {"net_r": -22.6}})
    assert reason == "", reason


def test_an_empty_baseline_falls_through_to_the_replay():
    cfg = _nas100()
    opt = _opt(cfg)
    opt._fresh_incumbent_holdout = lambda c: {"net_r": -22.6}
    for empty in (None, {}, {"holdout": {}}, {"holdout": {"net_r": None}},
                  {"holdout": None}):
        block, name = opt._flip_benchmark(cfg, empty)
        assert name == "taze test", empty
        assert block["net_r"] == -22.6


def test_the_production_caller_hands_the_baseline_over():
    """The gate cannot see it unless _finish_symbol passes it."""
    import inspect

    src = inspect.getsource(Optimizer)
    assert "baseline=report.get(\"baseline\")" in src, \
        "the report's baseline no longer reaches reject_reason"


def test_the_benchmark_falls_back_rather_than_inventing_a_number():
    """No replay is not a zero bar - it is "use the stamp".

    ``_fresh_incumbent_holdout`` swallows its own failures and returns None
    (tests build Optimizer with object.__new__ and no client), so these three
    shapes are the whole space of "no fresh number".
    """
    cfg = _nas100()
    opt = _opt(cfg)
    for stub in (lambda c: None, lambda c: {}, lambda c: {"net_r": None}):
        opt._fresh_incumbent_holdout = stub
        block, name = opt._flip_benchmark(cfg)
        assert block["net_r"] == 68.8
        assert name == "damga"

    opt._fresh_incumbent_holdout = lambda c: {"net_r": -22.6}
    block, name = opt._flip_benchmark(cfg)
    assert block["net_r"] == -22.6
    assert name == "taze test"
