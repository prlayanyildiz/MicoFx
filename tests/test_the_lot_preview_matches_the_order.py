"""The overshoot preview must size a trade the way the order will.

``lot_mode_diagnostics`` warns before a real order: it flags a risk-mode symbol
whose broker minimum lot forces more risk than ``risk_percent`` asked for, at
``overshoot >= 2.0``. It carried its own copy of ``lot_for``'s arithmetic -
deliberately, so it would not have to parse lot_for's free-form note string -
and the copy had drifted on both counts that separate a preview from an order:

  * ``_try_entry`` hands lot_for ``max(atr * sl_atr_mult, min_stop)``. The copy
    divided by the bare ATR distance, so when the broker's minimum stop is the
    wider of the two it sized against a stop the broker would refuse.
  * lot_for cancels the edge multiplier when the stop is pinned to that broker
    minimum, because a tight stop and a strong edge stack two amplifiers that
    were never validated together. The copy always applied edge.

Both errors run the same direction - a bigger raw lot, so a SMALLER reported
overshoot - and both bite on exactly the same symbols: the ones whose stop is
pinned to the broker minimum, which is where a min-lot overshoot is most likely
in the first place. A warning that under-reports precisely where it is needed.

The arithmetic now lives once, in ``_risk_raw_lot``, and both callers use it.
That is the actual fix: a comment would not have stopped the next drift, and
this pair had already drifted twice.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.risk import RiskManager


class _System:
    lot_multiplier = 1.0
    size_by_edge = True
    max_margin_usage_pct = 0.0
    min_free_margin = 0.0
    max_total_positions = 20


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = _System()

    def get_setting(self, key, default=None):
        return default

    def set_setting(self, key, value):
        pass


class _Bars:
    """Flat bars: true range is a constant 2.0, so ATR resolves to 2.0."""

    def __init__(self, n=40):
        self.close = np.full(n, 100.0)
        self.high = np.full(n, 101.0)
        self.low = np.full(n, 99.0)


class _Client:
    """ATR resolves to 2.0 with the bars below; one point is one price unit."""

    def __init__(self, min_stop=0.0):
        self._min_stop = min_stop

    def info(self, symbol):
        return {"volume_min": 0.10, "volume_max": 100.0, "point": 0.01,
                "tick_size": 0.01, "tick_value": 0.01, "filling_mode": 1}

    def money_per_price_unit(self, symbol, volume):
        return 1.0 * float(volume)

    def min_stop_distance(self, symbol):
        return self._min_stop

    def bars(self, symbol, timeframe, count):
        return _Bars(count)

    def resolve(self, symbol):
        return symbol

    def normalize_volume(self, symbol, lot):
        return round(lot, 2)

    def tick(self, symbol):
        return None

    def margin_for(self, symbol, lot, side):
        return 1.0


# Sized so the raw lot lands either side of the 0.10 broker floor: at the ATR
# stop (2.0) raw is 0.10 and nothing is flagged; at a 6.0 broker minimum stop it
# is 0.033, a 3x overshoot - past MAX_MIN_LOT_OVERSHOOT (1.5) the order skips.
BALANCE = 100.0


def _cfg(symbol="GER40", risk=0.2, sl_mult=1.0, edge_ready=True):
    c = SymbolConfig(symbol=symbol, magic=1, timeframe="M15", strategy="stoch_flip")
    c.lot_mode = "risk"
    c.risk_percent = risk
    c.sl_atr_mult = sl_mult
    c.atr_period = 14
    c.max_lot = 100.0          # keep lot_for's ceiling out of the comparison
    if edge_ready:
        # edge_scale needs three symbols with a positive metric before it does
        # anything; without that it returns a flat 1.0 and the cap under test
        # can never fire.
        c.opt_summary = {"holdout_days": 30.0,
                         "holdout": {"trades": 300, "net_r": 60.0, "expectancy": 0.2}}
    return c


def _rm(min_stop, cfgs=None):
    cfgs = cfgs or [_cfg()]
    return RiskManager(_Store(cfgs), _Client(min_stop))


def _row(rm, symbol="GER40"):
    rows = rm.lot_mode_diagnostics(BALANCE)
    return next(r for r in rows if r["symbol"] == symbol)


# ------------------------------------------------------------- the defect

def test_the_preview_uses_the_broker_minimum_stop_when_it_is_the_wider_one():
    """ATR distance is 2.0; a 6.0 broker minimum is what the order would use."""
    wide = _row(_rm(min_stop=6.0))
    narrow = _row(_rm(min_stop=0.0))
    assert wide["raw_lot"] < narrow["raw_lot"], (
        "onizleme broker'in kabul etmeyecegi bir stop mesafesine gore boyutlandiriyor")
    assert wide["overshoot"] > narrow["overshoot"]


def test_the_understated_overshoot_becomes_a_flag():
    """The whole point of the row: at the real stop distance it crosses 2.0."""
    assert _row(_rm(min_stop=0.0))["flagged"] is False
    assert _row(_rm(min_stop=6.0))["flagged"] is True


def test_a_stop_pinned_to_the_broker_minimum_reports_the_edge_cap():
    row = _row(_rm(min_stop=6.0))
    assert "edge_capped" in row


# --------------------------------------------------- preview equals order

def test_the_preview_and_lot_for_agree_on_the_same_symbol():
    """The invariant the shared helper exists to hold."""
    for min_stop in (0.0, 1.0, 6.0):
        rm = _rm(min_stop)
        cfg = rm.store.symbols["GER40"]
        sl = max(2.0 * cfg.sl_atr_mult, min_stop)
        lot, _ = rm.lot_for(cfg, sl, BALANCE)
        row = _row(rm)
        floor = 0.10
        raw = float(row["raw_lot"])
        overshoot = (floor / raw) if raw > 0 else 0.0
        # T1: past MAX_MIN_LOT_OVERSHOOT the order skips; preview must not
        # invent a rounded-up fill the live path refuses.
        if overshoot > RiskManager.MAX_MIN_LOT_OVERSHOOT:
            expected = 0.0
        else:
            expected = max(floor, raw)
        assert abs(lot - round(expected, 2)) < 0.011, (
            f"min_stop={min_stop}: onizleme {expected:.4f}, gercek emir {lot:.4f}")


def test_an_unpinned_stop_is_unchanged_by_any_of_this():
    """min_stop of 0 is the ordinary case and must read exactly as before."""
    row = _row(_rm(min_stop=0.0))
    assert row["raw_lot"] > 0
    assert row["edge_capped"] is False


def test_a_symbol_with_no_tick_value_is_skipped_rather_than_divided_by():
    class _Dead(_Client):
        def money_per_price_unit(self, symbol, volume):
            return 0.0

    rm = RiskManager(_Store([_cfg()]), _Dead(0.0))
    assert rm.lot_mode_diagnostics(BALANCE) == []


def test_a_leftover_fixed_lot_symbol_is_still_in_the_table():
    cfg = _cfg()
    cfg.lot_mode = "fixed"
    assert _rm(0.0, [cfg]).lot_mode_diagnostics(BALANCE)
