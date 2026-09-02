"""Retired family helpers must not return. ``ensure_terminal_process`` stays.

trix / delta_proxy / zscore had no remaining production caller after trix_flip
and flow_rev left. If they come back they will be searched again.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import micofx.indicators as ind

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_retired_indicator_helpers_are_gone():
    for name in ("trix", "delta_proxy", "zscore", "macd", "macd_periods",
                 "wavetrend"):
        assert not hasattr(ind, name), name


def test_retired_kivanc_losers_are_gone():
    """26.08 holdout: alpha_trend unmeasurable (7 trades < 12), mavilim
    negative (GER -20.2 R / PF 0.92). ichimoku stayed - it passed the gate.
    """
    from micofx.models import STRATEGIES
    from micofx.strategy import _FAMILIES

    for name in ("alpha_trend_rsi", "mavilim_w"):
        assert not hasattr(ind, name), name
    for name in ("alpha_trend", "mavilim"):
        assert name not in STRATEGIES, name
        assert name not in _FAMILIES, name
    assert "ichimoku" in STRATEGIES and "ichimoku" in _FAMILIES


def test_never_applied_scan_waste_is_gone():
    """26.08 opt history: st_trend 1/0 apply, macd_flip 5/0 apply, neither
    live. Each still ate a full max_combos slot per TF. ichimoku stays -
    it cleared the same holdout gate (GER +27.9 R).
    """
    from micofx.models import OPT_FIELDS, STRATEGIES
    from micofx.strategy import _FAMILIES, IndicatorCache, Params

    for name in ("st_trend", "macd_flip"):
        assert name not in STRATEGIES, name
        assert name not in _FAMILIES, name
    for field in ("macd_fast", "macd_slow", "macd_signal"):
        assert field not in OPT_FIELDS, field
        assert field not in Params.__dataclass_fields__
    assert not hasattr(IndicatorCache, "macd")
    assert "ichimoku" in STRATEGIES
    # 8 since 31.08: channel_break, added on an out-of-sample measurement.
    # The old donchian went in the 12.08 cull for never being searchable,
    # which is not a verdict on the shape - this one is in ``strategies``.
    assert len(STRATEGIES) == 4


def test_the_three_lottery_families_are_gone():
    """27.08: retired for search cost, not for a bad holdout.

    ``t3_stoch``'s own grid is ~8M and it does not carry its own exit axes,
    so the shared 6x6x5 exit product multiplies it to ~1.43e9 against a 2000
    budget - coverage 0.0001. It was first in STRATEGIES, 18 runs / 3
    applies, and live on nothing. A draw that size is not a search.

    ``wavetrend_flip`` 20 runs / 2 applies, holdout retention 0.453;
    ``micro_rev`` 11 runs, retention 0.382. Neither live.

    The families that stayed either own their exit axes (so the 180x never
    lands on them) or are cheap enough to cover fully: ``ichimoku`` is ~12,960
    combos and 144 seconds.
    """
    from micofx.models import OPT_FIELDS, SCALP_STRATEGIES, STRATEGIES
    from micofx.strategy import _FAMILIES, IndicatorCache, Params

    for name in ("t3_stoch", "wavetrend_flip", "micro_rev"):
        assert name not in STRATEGIES, name
        assert name not in _FAMILIES, name
        assert name not in SCALP_STRATEGIES, name
    # Axes only these three read. ``stoch_band`` went with them: only
    # ``_t3_stoch`` ever read it and it is not an engine/exit axis, so it
    # is the same case as ``macd_fast`` when ``macd_flip`` left.
    for field in ("mr_fast", "mr_stretch_cost", "mr_confirm",
                  "wt_channel_len", "wt_avg_len", "stoch_band"):
        assert field not in OPT_FIELDS, field
        assert field not in Params.__dataclass_fields__, field
    assert not hasattr(IndicatorCache, "wavetrend")
    # Shared T3/stoch axes stay - panel status and _common() still report them.
    for kept in ("t3_length", "t3_volume_factor", "stoch_length", "rsi_length"):
        assert kept in OPT_FIELDS, kept
    assert SCALP_STRATEGIES == frozenset({"burst"})


def test_parabolic_flip_is_gone():
    from micofx.models import STRATEGIES
    from micofx.strategy import _FAMILIES

    assert "parabolic_flip" not in STRATEGIES
    assert "parabolic_flip" not in _FAMILIES


def test_stoch_and_t3_families_are_gone():
    """01.09: F39 null edge on stoch_flip; dual_t3/t3_flip weakest asymmetry."""
    from micofx.models import STRATEGIES
    from micofx.strategy import _FAMILIES

    for name in ("stoch_flip", "dual_t3", "t3_flip"):
        assert name not in STRATEGIES, name
        assert name not in _FAMILIES, name


def test_retired_family_functions_are_gone():
    """01.09 families left _FAMILIES but the builders stayed in strategy.py.

    Leftover DB names already fail closed. The functions themselves were
    dead weight and a false 'still in the tree' read for anyone grepping
    the module. Same shape as trix/wavetrend after those families left.
    """
    import micofx.strategy as strategy

    for name in ("_dual_t3", "_t3_flip", "_stoch_flip", "_parabolic_flip",
                 "_t3_accel", "_flip_gates"):
        assert not hasattr(strategy, name), name
    from micofx.strategy import IndicatorCache
    for name in ("supertrend", "stoch_slow", "psar"):
        assert not hasattr(IndicatorCache, name), name


def test_the_default_family_is_one_that_still_exists():
    """``SymbolConfig``/``Params`` defaulted to ``t3_stoch``. A seed written
    against a retired name would be refused by the enum check the moment it
    was saved."""
    from micofx.models import STRATEGIES, SymbolConfig
    from micofx.strategy import Params

    assert SymbolConfig(symbol="X", magic=1).strategy in STRATEGIES
    assert Params().strategy in STRATEGIES


def test_autostart_is_a_real_feature_not_a_stub():
    """run.py reads autostart_mt5 and calls ensure_terminal_process."""
    from micofx.mt5client import MT5Client
    src = inspect.getsource(MT5Client.ensure_terminal_process)
    assert "terminal_path" in src
    run = (Path(__file__).resolve().parents[1] / "run.py").read_text(encoding="utf-8")
    assert "autostart_mt5" in run
    assert "ensure_terminal_process" in run
    ensure = inspect.getsource(MT5Client.ensure)
    assert "ensure_terminal_process" in ensure
