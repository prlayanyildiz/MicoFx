"""One-shot scale-out: the ticket and the broker grid pick the lot, not 0.20.

About one third of the position, snapped down to ``volume_step``, at least
``volume_min``, remainder at least min. GER40 0.70 / min 0.10 lands on 0.20
because that is what the grid allows, not because 0.20 is a product constant.
A 0.01 gold or a 0.10 JPN cannot split and is skipped.

The R gate (``partial_at_r``) is the on-switch. ``partial_close_lots`` is
leftover and must not drive the close. Not a TP ladder. Not an OPT_FIELD.
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

from micofx.engine import Engine
from micofx.logbus import LOG
from micofx.models import (
    EXIT_RISK_FIELDS,
    OPT_FIELDS,
    SCALE_OUT_FRAC,
    SymbolConfig,
    scale_out_slice,
    scale_out_volume,
)
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
    partial_close_lots = 0.0
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


def test_the_slice_is_one_third_snapped_to_the_broker_grid():
    assert SCALE_OUT_FRAC == pytest.approx(1.0 / 3.0)
    # GER 0.70 → 0.233 → 0.20. The old 0.20 was this rounding, not a standard.
    assert scale_out_slice(0.70, 0.1, 0.1) == pytest.approx(0.20)
    assert scale_out_slice(0.80, 0.1, 0.1) == pytest.approx(0.20)
    assert scale_out_slice(1.00, 0.1, 0.1) == pytest.approx(0.30)
    assert scale_out_slice(0.50, 0.1, 0.1) == pytest.approx(0.10)


def test_a_min_lot_ticket_cannot_split():
    assert scale_out_slice(0.10, 0.1, 0.1) is None
    assert scale_out_slice(0.01, 0.01, 0.01) is None


def test_two_min_lots_banks_one():
    """0.02 gold / 0.20 Brent: third snaps under min, so close exactly min."""
    assert scale_out_slice(0.02, 0.01, 0.01) == pytest.approx(0.01)
    assert scale_out_slice(0.20, 0.1, 0.1) == pytest.approx(0.10)


def test_scale_out_volume_skips_when_remainder_would_be_under_min():
    assert scale_out_volume(0.10, 0.20, 0.1, 0.1) is None
    assert scale_out_volume(0.01, 0.20, 0.01, 0.01) is None


def test_scale_out_volume_skips_when_off():
    assert scale_out_volume(0.70, 0.0, 0.1, 0.1) is None
    assert scale_out_slice(0.70, 0.1, 0.1, frac=0.0) is None


def test_live_closes_a_third_once_past_the_r_gate():
    client = _ScaleClient(bid=101.6)
    eng = _eng(client)
    pos = _pos(sl=100.0, entry=100.0, ticket=11)
    pos["volume"] = 0.70
    pos["symbol"] = "GER40"
    assert eng._maybe_scale_out(_ScaleCfg(), pos, ATR, _Bars(101.6)) is True
    assert client.closes == [(11, pytest.approx(0.20), "MicoFX parca")]
    assert 11 in eng._scale_out_done
    assert eng.store.settings["scale_out_done"] == [11]


def test_leftover_lots_field_does_not_pick_the_size():
    """GER still has 0.20 in the DB from the first overlay. The ticket size
    must win, not that leftover."""
    client = _ScaleClient(bid=101.6)
    eng = _eng(client)
    pos = _pos(sl=100.0, entry=100.0, ticket=14)
    pos["volume"] = 1.00
    pos["symbol"] = "GER40"
    cfg = _ScaleCfg()
    cfg.partial_close_lots = 0.20
    assert eng._maybe_scale_out(cfg, pos, ATR, _Bars(101.6)) is True
    assert client.closes == [(14, pytest.approx(0.30), "MicoFX parca")]


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


def test_paper_without_a_frac_uses_the_same_third():
    """Live GER rows carry at_r=1.5 and frac=0. Paper must still bank a third
    or the overlay is a live-only fiction."""
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
    kwargs = {"open_": open_, "spread_pts": np.zeros(n), "point": 0.01,
              "entries": np.array([entry_bar]), "min_stop": 0.01}
    auto = backtest.simulate(
        cache, sig,
        p=Params(sl_atr_mult=1.0, trail_start_atr=9.0, trail_step_atr=2.2,
                 partial_at_r=1.5),
        **kwargs)
    third = backtest.simulate(
        cache, sig,
        p=Params(sl_atr_mult=1.0, trail_start_atr=9.0, trail_step_atr=2.2,
                 partial_at_r=1.5, partial_close_frac=SCALE_OUT_FRAC),
        **kwargs)
    assert auto.trades == third.trades == 1
    assert auto.trade_rs[0] == pytest.approx(third.trade_rs[0])


def test_min_lot_index_cannot_split():
    client = _ScaleClient(bid=101.6)
    eng = _eng(client)
    pos = _pos(sl=100.0, entry=100.0, ticket=13)
    pos["volume"] = 0.10
    pos["symbol"] = "GER40"
    eng._maybe_scale_out(_ScaleCfg(), pos, ATR, _Bars(101.6))
    assert client.closes == []


def test_scale_out_log_is_r_and_cash(monkeypatch):
    """Gate R, not ATR multiples, and the cash the slice actually booked."""
    lines: list[str] = []
    monkeypatch.setattr(
        LOG, "emit", lambda msg, *a, **k: lines.append(str(msg)))
    client = _ScaleClient(bid=101.6)
    eng = _eng(client)
    pos = _pos(sl=100.0, entry=100.0, ticket=11)
    pos["volume"] = 0.70
    pos["symbol"] = "GER40"
    assert eng._maybe_scale_out(_ScaleCfg(), pos, ATR, _Bars(101.6)) is True
    text = " ".join(lines)
    assert "xATR" not in text
    assert "kar=" in text
    assert "1.60R" in text or "1.6R" in text


def test_remain_uses_filled_volume_not_requested():
    """IOC can return DONE_PARTIAL; the book and the log must follow fill volume."""
    class _Partial(_ScaleClient):
        def close_position(self, ticket, slippage=20, comment="", volume=None, fill=None):
            self.closes.append((int(ticket), volume, comment))
            if fill is not None:
                fill.update({
                    "symbol": "GER40", "side": "buy", "requested": float(volume or 0),
                    "price": self.bid, "volume": 0.10, "risk_dist": 1.0,
                })
            return True

    client = _Partial(bid=101.6)
    eng = _eng(client)
    pos = _pos(sl=100.0, entry=100.0, ticket=11)
    pos["volume"] = 0.70
    pos["symbol"] = "GER40"
    assert eng._maybe_scale_out(_ScaleCfg(), pos, ATR, _Bars(101.6)) is True
    assert pos["volume"] == pytest.approx(0.60)
    assert 11 in eng._scale_out_done


def test_closed_tickets_drop_out_of_scale_out_done():
    import threading
    from types import SimpleNamespace

    eng = object.__new__(Engine)
    eng.client = SimpleNamespace(connected=True)
    eng.store = _Store()
    eng.store.symbols = {}
    eng.entry_lock = threading.Lock()
    eng._positions = [{"ticket": 11, "magic": 1, "symbol": "GER40"}]
    eng._scale_out_done = {11, 999}
    eng._weekend_pending = set()
    eng._force_flat_pending = set()
    eng._sec_tickets = set()
    eng._orphan_tickets = set()
    eng._stop_bar = {}
    eng._unmanaged_seen = set()
    eng._stopless_seen = set()
    eng.states = {}
    Engine.manage_positions(eng, server_now=0.0)
    assert eng._scale_out_done == {11}
    assert eng.store.settings["scale_out_done"] == [11]


def test_partial_at_r_is_a_live_overlay_not_a_mid_trade_409():
    """14:02 wrote 0→1.5 with opens; 62s later GER fired. Same door as BE."""
    assert "partial_at_r" not in EXIT_RISK_FIELDS
    assert "breakeven_at_r" not in EXIT_RISK_FIELDS
