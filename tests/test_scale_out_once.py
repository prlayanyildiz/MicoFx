"""Operator 25.08: scale out a fixed lot once, remainder keeps the trail.

GER40 0.70 in profit → close 0.20, leave 0.50. Not a TP ladder (partial_tp_r
stays gone). Not an OPT_FIELD. Zero lots / zero R is off.

Remainder must stay at least the broker min lot; otherwise the ticket is
skipped (XAUUSD 0.01, JPN225 0.10 cannot shed 0.20).
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_trail_retry_within_bar import ATR, _Bars, _engine, _pos

from micofx.models import OPT_FIELDS, SymbolConfig, scale_out_volume
from micofx.strategy import Params
from micofx.web.app import _SYMBOL_RISK_BOUNDS


class _ScaleCfg:
    symbol = "GER40"
    magic = 7
    timeframe = "M5"
    sl_atr_mult = 1.0
    trail_start_atr = 3.0
    trail_step_atr = 2.2
    trail_mode = "atr"
    trail_lookback = 5
    breakeven_at_r = 1.5
    partial_close_lots = 0.20
    partial_at_r = 1.5
    partial_close_frac = 0.0


class _ScaleClient:
    def __init__(self, bid: float = 101.6, min_stop: float = 0.1) -> None:
        self.bid = bid
        self._min_stop = min_stop
        self.modifies: list[float] = []
        self.closes: list[tuple] = []
        self.slippage_points = 20

    def tick(self, symbol):
        return {"bid": self.bid, "ask": self.bid + 0.01, "spread": 0.01}

    def min_stop_distance(self, symbol):
        return self._min_stop

    def modify_position(self, ticket, sl, tp, symbol):
        self.modifies.append(sl)
        return True

    def info(self, symbol):
        return {"volume_min": 0.1, "volume_max": 100.0, "volume_step": 0.1,
                "point": 0.1, "tick_value": 1.0, "tick_size": 0.1}

    def close_position(self, ticket, slippage=20, comment="", volume=None, fill=None):
        self.closes.append((int(ticket), volume, comment))
        if fill is not None:
            fill.update({
                "symbol": "GER40", "side": "buy", "requested": self.bid,
                "price": self.bid, "volume": float(volume or 0), "risk_dist": 1.0,
            })
        return True

    def money_per_price_unit(self, symbol, volume):
        return 1.0


class _Store:
    def __init__(self) -> None:
        self.settings: dict = {}
        self.system = SimpleNamespace(slippage_points=20)

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


def _eng(client=None):
    client = client or _ScaleClient()
    eng = _engine(client)
    eng.store = _Store()
    eng._scale_out_done = set()
    eng.execution = SimpleNamespace(record=lambda *a, **k: None, snapshot=None)
    return eng


def test_not_a_search_axis():
    for name in ("partial_close_lots", "partial_at_r", "partial_close_frac"):
        assert name not in OPT_FIELDS
    src = inspect.getsource(Params.key)
    assert "partial_close" not in src and "partial_at_r" not in src


def test_zero_is_off():
    cfg = SymbolConfig(symbol="GER40", magic=1)
    assert cfg.partial_close_lots == 0.0
    assert cfg.partial_at_r == 0.0
    assert cfg.partial_close_frac == 0.0
    assert Params().partial_at_r == 0.0
    assert Params().partial_close_frac == 0.0


def test_params_from_config_carries_the_paper_frac():
    cfg = SymbolConfig(symbol="GER40", magic=1,
                       partial_at_r=1.5, partial_close_frac=0.3)
    p = Params.from_config(cfg)
    assert p.partial_at_r == 1.5
    assert p.partial_close_frac == 0.3


def test_api_zero_lots_is_legal():
    lo, hi, inclusive = _SYMBOL_RISK_BOUNDS["partial_close_lots"]
    assert lo == 0.0 and inclusive and hi >= 0.20
    lo, hi, inclusive = _SYMBOL_RISK_BOUNDS["partial_at_r"]
    assert lo == 0.0 and inclusive and hi >= 1.5


def test_scale_out_volume_sheds_point_two_from_point_seven():
    assert scale_out_volume(0.70, 0.20, 0.1, 0.1) == pytest.approx(0.20)


def test_scale_out_volume_skips_when_remainder_would_be_under_min():
    assert scale_out_volume(0.10, 0.20, 0.1, 0.1) is None
    assert scale_out_volume(0.01, 0.20, 0.01, 0.01) is None


def test_scale_out_volume_skips_when_off():
    assert scale_out_volume(0.70, 0.0, 0.1, 0.1) is None


def test_live_closes_point_two_once_past_the_r_gate():
    client = _ScaleClient(bid=101.6)
    eng = _eng(client)
    pos = _pos(sl=100.0, entry=100.0, ticket=11)
    pos["volume"] = 0.70
    pos["symbol"] = "GER40"
    assert eng._maybe_scale_out(_ScaleCfg(), pos, ATR, _Bars(101.6)) is True
    assert client.closes == [(11, pytest.approx(0.20), "MicoFX parca")]
    assert 11 in eng._scale_out_done
    assert eng.store.settings["scale_out_done"] == [11]


def test_a_second_poll_does_not_close_again():
    client = _ScaleClient(bid=101.6)
    eng = _eng(client)
    pos = _pos(sl=100.0, entry=100.0, ticket=11)
    pos["volume"] = 0.70
    pos["symbol"] = "GER40"
    eng._maybe_scale_out(_ScaleCfg(), pos, ATR, _Bars(101.6))
    eng._maybe_scale_out(_ScaleCfg(), pos, ATR, _Bars(101.6))
    assert len(client.closes) == 1


def test_below_the_r_gate_nothing_closes():
    client = _ScaleClient(bid=101.4)
    eng = _eng(client)
    pos = _pos(sl=99.0, entry=100.0, ticket=12)
    pos["volume"] = 0.70
    pos["symbol"] = "GER40"
    eng._maybe_scale_out(_ScaleCfg(), pos, ATR, _Bars(101.4))  # +1.4 R
    assert client.closes == []


def test_paper_books_the_rung_then_the_remainder():
    """0.5 at 1.5 R, then the stub dies at -1 R → 0.25, not -1.0."""
    from micofx import backtest
    from micofx.strategy import IndicatorCache, Params, Signals

    n, entry_bar = 260, 30
    close = np.empty(n)
    close[:entry_bar + 1] = 100.0
    up_end = entry_bar + 60
    close[entry_bar + 1:up_end] = np.linspace(100.0, 103.0, up_end - entry_bar - 1)
    close[up_end:] = np.linspace(103.0, 80.0, n - up_end)
    open_ = np.empty(n)
    open_[0] = close[0]
    open_[1:] = close[:-1]
    high = close + 0.5
    low = close - 0.5
    open_ = np.clip(open_, low, high)
    buy = np.zeros(n, dtype=bool)
    buy[entry_bar] = True
    sig = Signals(t3=close, k=close, d=close, atr=np.full(n, 1.0), adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300,
                           tf_seconds=300, open_=open_, volume=np.ones(n))
    p = Params(sl_atr_mult=1.0, trail_start_atr=9.0, trail_step_atr=2.2,
               partial_at_r=1.5, partial_close_frac=0.5)
    res = backtest.simulate(
        cache, sig, open_, np.zeros(n), point=0.01, p=p,
        entries=np.array([entry_bar]), min_stop=0.01)
    assert res.trades == 1
    # 0.5 * ~1.5 + 0.5 * ~(-1) ≈ 0.25. ATR fixture is ~1.
    assert 0.10 < res.trade_rs[0] < 0.45


def test_paper_off_still_dies_at_the_hard_stop():
    from micofx import backtest
    from micofx.strategy import IndicatorCache, Params, Signals

    n, entry_bar = 260, 30
    close = np.empty(n)
    close[:entry_bar + 1] = 100.0
    up_end = entry_bar + 60
    close[entry_bar + 1:up_end] = np.linspace(100.0, 103.0, up_end - entry_bar - 1)
    close[up_end:] = np.linspace(103.0, 80.0, n - up_end)
    open_ = np.empty(n)
    open_[0] = close[0]
    open_[1:] = close[:-1]
    high = close + 0.5
    low = close - 0.5
    open_ = np.clip(open_, low, high)
    buy = np.zeros(n, dtype=bool)
    buy[entry_bar] = True
    sig = Signals(t3=close, k=close, d=close, atr=np.full(n, 1.0), adx=np.zeros(n),
                  buy=buy, sell=np.zeros(n, dtype=bool),
                  htf_up=np.zeros(n, dtype=bool), htf_down=np.zeros(n, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(n) * 300,
                           tf_seconds=300, open_=open_, volume=np.ones(n))
    res = backtest.simulate(
        cache, sig, open_, np.zeros(n), point=0.01,
        p=Params(sl_atr_mult=1.0, trail_start_atr=9.0, trail_step_atr=2.2),
        entries=np.array([entry_bar]), min_stop=0.01)
    assert res.trades == 1
    assert res.trade_rs[0] == pytest.approx(-1.0, abs=0.15)


def test_min_lot_index_cannot_split():
    client = _ScaleClient(bid=101.6)
    eng = _eng(client)
    pos = _pos(sl=100.0, entry=100.0, ticket=13)
    pos["volume"] = 0.10
    pos["symbol"] = "GER40"
    eng._maybe_scale_out(_ScaleCfg(), pos, ATR, _Bars(101.6))
    assert client.closes == []
