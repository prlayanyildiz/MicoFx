import numpy as np

from micofx.models import OPT_FIELDS, STRATEGIES, SymbolConfig
from micofx.strategy import _FAMILIES, IndicatorCache, Params, compute, opt_fields_read


def test_keltner_break_in_strategies():
    assert "keltner_break" in STRATEGIES
    assert "keltner_break" in _FAMILIES


def test_keltner_break_opt_fields():
    fields = opt_fields_read("keltner_break")
    assert "kelt_ema_len" in fields
    assert "kelt_atr_mult" in fields
    assert "kelt_ema_len" in OPT_FIELDS
    assert "kelt_atr_mult" in OPT_FIELDS


def test_keltner_params_key_includes_kelt_axes():
    """WFO signal cache must not reuse series when kelt_* changes."""
    a = Params(strategy="keltner_break", kelt_ema_len=10, kelt_atr_mult=1.0)
    b = Params(strategy="keltner_break", kelt_ema_len=20, kelt_atr_mult=1.0)
    c = Params(strategy="keltner_break", kelt_ema_len=10, kelt_atr_mult=2.5)
    assert a.key() != b.key()
    assert a.key() != c.key()
    assert a.kelt_ema_len in a.key()
    assert a.kelt_atr_mult in a.key()


def test_keltner_break_signals_generation():
    assert "keltner_break" in _FAMILIES
    n = 200
    times = np.arange(n, dtype=np.float64) * 1800
    close = np.ones(n) * 100.0
    # Create flat market then strong breakout at bar 100
    close[100:] = 120.0
    high = close + 1.0
    low = close - 1.0
    open_ = close
    volume = np.ones(n)
    cost = np.zeros(n)
    cache = IndicatorCache(high, low, close, times, 1800, open_, volume, cost)

    cfg = SymbolConfig(symbol="BTCUSD", strategy="keltner_break")
    p = Params.from_config(cfg)
    p.htf_factor = 0
    p.kelt_ema_len = 10
    p.kelt_atr_mult = 1.0

    sig = compute(cache, p)
    assert hasattr(sig, "buy")
    assert hasattr(sig, "sell")
    assert not (sig.buy & sig.sell).any()
    # First bar never signals
    assert not sig.buy[0]
    assert not sig.sell[0]
    # Breakout candle must trigger buy
    assert sig.buy[100]
