"""Operator, 10.09 23:3x: "taramada isle yaramiyor aile vs bulamiyr".

The flip bar was a stamp - ``cfg.opt_summary["holdout"]``, the number the
incumbent scored on the day it was applied. Nothing ages it, so a candidate
measured today had to beat 1.15x a figure from another run, another slice and
sometimes another cost model. What the incumbent scores on *this* sweep's
holdout slice sits in the same report, in ``baseline["holdout"]``
(``backtest.py:1536``), and was ignored.

The three runs of 10-11.09, candidate vs incumbent **on the same slice**,
against the bar that was actually applied:

    NAS100 range_fade/M30   +21.5R PF 1.45  vs  +16.8R PF 1.27  bar 79.1R
    XAUUSD mtf_pullback/M30 +33.2R PF 1.10  vs  +31.0R PF 1.11  bar 162.2R
    US30   keltner_break/M30 +26.2R PF 1.15 vs  +17.2R PF 1.05  bar 27.0R

The bar was four to five times what the incumbent delivers on the slice being
compared. With the measurement in its place the bars become 19.3R, 35.6R and
19.8R: NAS100 and US30 pass, XAUUSD still fails - correctly, it is a genuine
+2R improvement and the churn brake exists for exactly that.

The fix is not "lower the bar", it is "measure it". A later US30 sweep found a
weaker candidate (+21.9R against an incumbent scoring +29.8R on that slice)
and is refused, as it should be.

Beware the two different numbers here: ``baseline["net_r"]`` is the incumbent
over the whole span (-22.6R for NAS100, -30.1R for XAUUSD, -17.9R for US30),
while ``baseline["holdout"]["net_r"]`` is the incumbent on the holdout slice.
The gates compare the holdout slice, so that is the one that belongs beside a
candidate's holdout. Reading the span number as "the incumbent loses money"
overstates the case by a wide margin - these configs are not losing on the
slice they are judged on.
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
    opt._beats_incumbent = lambda *a, **k: True
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


# ---------------------------------------------------------- the shape of it

def test_a_losing_incumbent_no_longer_blocks_a_winning_candidate():
    """Synthetic: an incumbent that genuinely loses on the compared slice.

    None of the three live cases were this - see the module docstring, they
    scored +16.8R to +31.0R on their own holdout slices. This pins the
    direction the stamp made impossible: a bar of 79.1R cannot be cleared by
    anything honest, whatever the incumbent is really worth.
    """
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


# ------------------------------------- the same disease, one gate further in

def test_beats_incumbent_reads_the_same_benchmark():
    """US30, 11.09 00:29: the candidate cleared F6 and F1 and reached here.

    That particular refusal turned out to be right - +21.9R against an
    incumbent scoring +29.8R on the same slice - but it was reached for the
    wrong reason. The tail of _beats_incumbent already preferred a replay over the stamp,
    but ``_holdout_costed(allow_fetch=False)`` returns None on a narrow run
    whose bars were never cached - and then the stamp decided anyway.
    """
    cfg = _nas100()
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.system = MagicMock(charge_costs=True)
    opt._spread_scale = lambda symbol: 1.0
    opt._fresh_incumbent_holdout = lambda c: None      # narrow run, no bars
    cfg.opt_summary["holdout"] = {"net_r": 68.8, "score": 40.0}

    # Stamp alone: a candidate scoring 8 loses to a stamp of 40.
    assert opt._beats_incumbent(cfg, {"score": 8.0}) is False
    # With the sweep's own measurement of the incumbent, it wins.
    assert opt._beats_incumbent(
        cfg, {"score": 8.0},
        {"holdout": {"net_r": -17.9, "score": -6.0}}) is True


def test_a_measured_benchmark_skips_the_assumption_waivers():
    """The two "measured under a different assumption" escapes exist for a
    stamp carried over from another run. A number produced in this sweep, or
    replayed now, shares every assumption by construction - and
    _incumbent_guard_was_charging answers by identity against the stamp's own
    sub-block, so it cannot answer for a measurement at all."""
    import inspect

    src = inspect.getsource(Optimizer._beats_incumbent)
    assert "measured_now" in src
    assert "if measured_now:" in src
    assert "was_charging = charging" in src


def test_an_unvalidated_stamp_is_still_not_a_bar():
    """_measured_incumbent exists precisely so this branch cannot fall back
    to the stamp: an unvalidated one froze NAS100 on a config thirty live
    days had already judged PF 0.50."""
    cfg = _nas100()
    cfg.validated = False
    cfg.opt_summary["validated"] = False
    cfg.opt_summary["holdout"] = {"net_r": 500.0, "score": 500.0}
    opt = Optimizer.__new__(Optimizer)
    opt.store = MagicMock()
    opt.store.system = MagicMock(charge_costs=True)
    opt._spread_scale = lambda symbol: 1.0
    opt._fresh_incumbent_holdout = lambda c: None
    assert opt._beats_incumbent(cfg, {"score": 1.0}) is True
    assert opt._measured_incumbent(cfg, None) is None
