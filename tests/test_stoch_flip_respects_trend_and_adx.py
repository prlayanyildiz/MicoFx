"""stoch_flip is the live majority family and must not fire in chop.

Four of six live names run Slow Stochastic %K/%D crosses with no trend
filter (JPN/NAS/US30/Brent). Public trend-following templates pair that
cross with a higher-timeframe bias and an ADX floor. burst/_mtf_pullback
already have ``_trend_gate`` and ``_regime``; this family did not, so
leftover ``htf_factor`` / ``adx_min`` on the card were a lie and every
cross was an entry. Fail-first: a high ADX floor or an HTF gate has to
be able to veto a cross that the ungated family would take.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.strategy import IndicatorCache, Params, compute, opt_fields_read


def _cache(n=900, seed=7):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 0.4, n))
    high = close + 0.35
    low = close - 0.35
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    return IndicatorCache(high=high, low=low, close=close, open_=open_,
                          times=np.arange(n, dtype=np.int64) * 300, tf_seconds=300)


def test_stoch_flip_reads_the_trend_and_adx_gates():
    read = opt_fields_read("stoch_flip")
    assert "htf_factor" in read
    assert "adx_min" in read


@pytest.mark.parametrize("name", ("stoch_flip", "parabolic_flip"))
def test_an_adx_floor_can_veto_a_flip(name):
    cache = _cache()
    open_ = compute(cache, Params(strategy=name, adx_min=0.0))
    gated = compute(cache, Params(strategy=name, adx_min=40.0))
    assert open_.buy.any() or open_.sell.any(), f"{name} must signal ungated"
    assert gated.buy.sum() + gated.sell.sum() < open_.buy.sum() + open_.sell.sum()


def test_unstamped_leftover_htf_does_not_bind_on_from_config():
    """Overnight Brent/NAS carried htf_factor from a previous family.

    The stoch_flip apply stamp does not include that dial. Honouring it would
    change the live signal vs the holdout that was just written.
    """
    cfg = SymbolConfig(symbol="NAS100", strategy="stoch_flip", htf_factor=12,
                       opt_summary={"params": {"stoch_k_period": 10, "sl_atr_mult": 1.0},
                                    "holdout": {"net_r": 1.0}, "validated": True})
    p = Params.from_config(cfg)
    assert p.htf_factor in (0, 1)


def test_dual_t3_unstamped_adx_stays_on_from_config():
    """GER40 dual_t3 stamp omitted adx_min; the row 15 is the live dial.

    Zeroing it on restart would drop the floor the 00:06 holdout inherited.
    """
    cfg = SymbolConfig(symbol="GER40", strategy="dual_t3", adx_min=15.0,
                       opt_summary={"params": {"t3_fast": 8, "sl_atr_mult": 1.0},
                                    "holdout": {"net_r": 1.0}, "validated": True})
    p = Params.from_config(cfg)
    assert p.adx_min == 15.0


def test_stamped_htf_survives_from_config():
    cfg = SymbolConfig(symbol="XAUUSD", strategy="burst", htf_factor=6,
                       opt_summary={"params": {"htf_factor": 6, "brst_lookback": 20},
                                    "holdout": {"net_r": 1.0}, "validated": True})
    p = Params.from_config(cfg)
    assert p.htf_factor == 6


def test_apply_writes_zero_for_unstamped_flip_gates():
    """Panel leftover must not outlive a stoch_flip apply that never named it."""
    from micofx.optimizer import Optimizer

    class _Store:
        def __init__(self, cfg):
            self._cfg = cfg
            self.symbols = {cfg.symbol: cfg}
            self.updated_with = None

        def get_setting(self, key, default=None):
            return default

        def opt_params(self):
            return {}

        def update_symbol(self, symbol, patch, source=""):
            self.updated_with = patch
            for k, v in patch.items():
                if v is not None:
                    setattr(self._cfg, k, v)
            return self._cfg

    class _Client:
        connected = True

        def positions(self, magic=None, symbol=None):
            return []

    cfg = SymbolConfig(symbol="NAS100", magic=1, strategy="stoch_flip",
                       timeframe="M30", htf_factor=12, adx_min=15.0,
                       sl_atr_mult=1.0, trail_step_atr=0.6)
    store = _Store(cfg)
    opt = Optimizer(store=store, client=_Client())
    opt._holdout_costed = lambda *a, **k: None
    result = opt.apply(
        "NAS100",
        {"stoch_k_period": 10, "sl_atr_mult": 1.5},
        score=4.34,
        detail={"holdout": {"trades": 40, "expectancy": 0.2, "net_r": 8.0,
                            "max_dd_r": 4.0},
                "holdout_days": 30.0, "validated": True,
                "validation": {}, "selection": {}, "positive_ratio": 1.0},
        strategy="stoch_flip", timeframe="M30")
    assert result["ok"] is True
    assert store.updated_with["htf_factor"] == 0
    assert store.updated_with["adx_min"] == 0
    assert store.updated_with["opt_summary"]["params"]["htf_factor"] == 0
