"""MFE profit-lock rungs in overlay_stop (Antigravity 07.09)."""
from __future__ import annotations

import pytest

from micofx.exits import mfe_lock_to_r, overlay_stop


def _kw(**over):
    base = {
        "is_buy": True, "entry": 100.0, "ref": 101.6, "atr": 1.0,
        "trail_start_atr": 10.0, "trail_step_atr": 0.4,
        "trail_mode": "atr", "struct_sl": None, "breakeven_at_r": 0.0,
        "original_risk": 1.0,
    }
    base.update(over)
    return base


def test_mfe_lock_rung1_locks_075r():
    # +1.6R open → lock at +0.75R = 100.75
    sl = overlay_stop(**_kw(
        mfe_lock1_at_r=1.5, mfe_lock1_to_r=0.75,
        mfe_lock2_at_r=2.0, mfe_lock2_to_r=1.25))
    assert sl == pytest.approx(100.75)


def test_mfe_lock_rung2_beats_rung1():
    sl = overlay_stop(**_kw(
        ref=102.1,
        mfe_lock1_at_r=1.5, mfe_lock1_to_r=0.75,
        mfe_lock2_at_r=2.0, mfe_lock2_to_r=1.25))
    assert sl == pytest.approx(101.25)


def test_mfe_lock_uses_peak_after_giveback():
    # Current profit 0.5R but peak was 1.6R → still lock 0.75
    assert mfe_lock_to_r(
        profit=0.5, original_risk=1.0,
        lock1_at_r=1.5, lock1_to_r=0.75,
        lock2_at_r=2.0, lock2_to_r=1.25,
        peak_profit=1.6) == pytest.approx(0.75)
    sl = overlay_stop(**_kw(
        ref=100.5,
        peak_profit=1.6,
        mfe_lock1_at_r=1.5, mfe_lock1_to_r=0.75,
        mfe_lock2_at_r=0.0, mfe_lock2_to_r=0.0))
    assert sl == pytest.approx(100.75)


def test_mfe_lock_off_when_at_r_zero():
    assert overlay_stop(**_kw(mfe_lock1_at_r=0.0, mfe_lock1_to_r=0.75)) is None


def test_engine_update_stop_reads_execution_mfe():
    import numpy as np

    from micofx.engine import Engine

    class _Client:
        def __init__(self, bid=102.0):
            self.bid = bid
            self.modifies = []
        def tick(self, sym):
            return {"bid": self.bid, "ask": self.bid + 0.01}
        def min_stop_distance(self, sym):
            return 0.1
        def modify_position(self, ticket, sl, tp, sym):
            self.modifies.append(sl)
            return True

    class _Execution:
        def __init__(self, mfe=0.0):
            self._mfe = mfe
        def snapshot(self, ticket):
            return {"mfe": self._mfe}

    class _Bars:
        def __init__(self, close=100.5):
            self.close = np.array([close])
        @property
        def last_closed_time(self):
            return 1_000_000

    class _Cfg:
        symbol = "XAUUSD"
        magic = 1
        timeframe = "M15"
        sl_atr_mult = 1.0
        trail_start_atr = 10.0
        trail_step_atr = 0.4
        trail_mode = "atr"
        trail_lookback = 5
        breakeven_at_r = 0.0
        mfe_lock1_at_r = 1.5
        mfe_lock1_to_r = 0.75
        mfe_lock2_at_r = 0.0
        mfe_lock2_to_r = 0.0

    eng = Engine.__new__(Engine)
    client = _Client(bid=102.0)
    eng.client = client
    eng.states = {}
    eng.execution = _Execution(mfe=1.6)

    # Raw MT5 position dict - contains NO 'mfe_px' field!
    pos = {
        "ticket": 999, "symbol": "XAUUSD", "side": "buy", "sl": 99.0,
        "tp": 0.0, "price_open": 100.0, "volume": 0.1, "magic": 1,
        "time": 1_000_010,
    }

    # Reference bar closed at 100.5 (+0.5R, below mfe_lock1 threshold 1.5R).
    # But peak excursion in ExecutionMonitor reached 1.6R.
    # _update_stop MUST read mfe from eng.execution.snapshot and ratchet SL to 100.75!
    res = eng._update_stop(_Cfg(), pos, 1.0, _Bars(close=100.5))
    assert res is True
    assert client.modifies == [pytest.approx(100.75)]
    assert pos["sl"] == pytest.approx(100.75)


def test_engine_update_stop_giveback_preserves_mfe_lock():
    import numpy as np

    from micofx.engine import Engine

    class _Client:
        def __init__(self, bid=101.5):
            self.bid = bid
            self.modifies = []
        def tick(self, sym):
            return {"bid": self.bid, "ask": self.bid + 0.01}
        def min_stop_distance(self, sym):
            return 0.1
        def modify_position(self, ticket, sl, tp, sym):
            self.modifies.append(sl)
            return True

    class _Execution:
        def __init__(self, mfe=0.0):
            self._mfe = mfe
        def snapshot(self, ticket):
            return {"mfe": self._mfe}

    class _Bars:
        def __init__(self, close=99.8):
            self.close = np.array([close])
        @property
        def last_closed_time(self):
            return 1_000_000

    class _Cfg:
        symbol = "XAUUSD"
        magic = 1
        timeframe = "M15"
        sl_atr_mult = 1.0
        trail_start_atr = 10.0
        trail_step_atr = 0.4
        trail_mode = "atr"
        trail_lookback = 5
        breakeven_at_r = 0.0
        mfe_lock1_at_r = 1.5
        mfe_lock1_to_r = 0.75
        mfe_lock2_at_r = 0.0
        mfe_lock2_to_r = 0.0

    eng = Engine.__new__(Engine)
    client = _Client(bid=101.5)
    eng.client = client
    eng.states = {}
    eng.execution = _Execution(mfe=1.6)

    pos = {
        "ticket": 999, "symbol": "XAUUSD", "side": "buy", "sl": 99.0,
        "tp": 0.0, "price_open": 100.0, "volume": 0.1, "magic": 1,
        "time": 1_000_010,
    }

    # Reference bar closed at 99.8 (profit_dist = -0.2 <= 0, giveback bar!).
    # But peak excursion in ExecutionMonitor reached 1.6R.
    # Live quote is 101.5, allowing placement of 100.75 lock!
    # _update_stop MUST NOT early return on profit_dist <= 0! It must ratchet SL to 100.75!
    res = eng._update_stop(_Cfg(), pos, 1.0, _Bars(close=99.8))
    assert res is True
    assert client.modifies == [pytest.approx(100.75)]
    assert pos["sl"] == pytest.approx(100.75)


