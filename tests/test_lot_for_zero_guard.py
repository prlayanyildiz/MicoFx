"""RiskManager.lot_for must fail closed on a zero lot, not floor to min lot.

Both sizing branches report their broker-minimum overshoot as ``floor / raw``,
so a ``raw`` of exactly 0 raised ZeroDivisionError inside the f-string - and
had that division not been there, ``lot = max(floor, raw)`` would have been
worse than the crash: a config asking to risk nothing would have come back
with the broker's minimum lot, the LARGEST position this function can produce.

Neither zero is reachable through the panel today (the API refuses
fixed_lot/risk_percent <= 0, and every ai_scale of 0 - AI quarantine, a
blocked hour, the drawdown hold - refuses the entry before lot_for is called).
That is exactly why this is worth pinning: the guard rests on an invariant
spread across three files, and the value can still arrive from a hand-edited
DB row or a restored backup.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.risk import RiskManager


class _FakeClient:
    """Just enough broker for lot_for: one lot table, one tick value."""

    def __init__(self, volume_min: float = 0.1) -> None:
        self.volume_min = volume_min

    def info(self, symbol):
        return {"volume_min": self.volume_min, "volume_max": 100.0}

    def money_per_price_unit(self, symbol, lot):
        return 10.0 * lot

    def min_stop_distance(self, symbol):
        return 0.0

    def normalize_volume(self, symbol, lot):
        return round(lot, 2)


class _FakeStore:
    def __init__(self, cfg: SymbolConfig) -> None:
        self.symbols = {cfg.symbol: cfg}
        self.system = SystemConfig()
        self.system.size_by_edge = False   # keep edge_scale out of the arithmetic


def _risk(cfg: SymbolConfig) -> RiskManager:
    rm = RiskManager.__new__(RiskManager)   # no DailyGuard / no DB
    rm.store = _FakeStore(cfg)
    rm.client = _FakeClient()
    return rm


def test_leftover_zero_fixed_lot_still_sizes_from_risk_percent():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, lot_mode="fixed",
                       fixed_lot=0.0, risk_percent=1.0)
    lot, note = _risk(cfg).lot_for(cfg, sl_distance=1.0, balance=10_000.0)
    assert lot > 0
    assert "atlandi" not in note


def test_zero_risk_percent_skips_the_trade():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, lot_mode="risk", risk_percent=0.0)
    lot, note = _risk(cfg).lot_for(cfg, sl_distance=1.0, balance=10_000.0)
    assert lot == 0.0
    assert "atlandi" in note


def test_zero_balance_skips_the_trade():
    """A blown or freshly-opened account sizes to nothing, not to min lot."""
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, lot_mode="risk", risk_percent=0.5)
    lot, note = _risk(cfg).lot_for(cfg, sl_distance=1.0, balance=0.0)
    assert lot == 0.0
    assert "atlandi" in note


def test_zero_ai_scale_skips_the_trade():
    """The supervisor's own 0.0 (quarantine) must not round back up to min lot."""
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, risk_percent=0.5)
    lot, note = _risk(cfg).lot_for(cfg, sl_distance=1.0, balance=10_000.0,
                                   ai_scale=0.0)
    assert lot == 0.0
    assert "atlandi" in note


def test_normal_sizing_is_untouched():
    """The guard is "exactly zero", not a new floor on small sizes."""
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, risk_percent=1.0)
    # 10_000 * 1% / (1.0 * 10.0) = 10.0 lots
    lot, note = _risk(cfg).lot_for(cfg, sl_distance=1.0, balance=10_000.0)
    assert lot > 0
    assert "atlandi" not in note


def test_a_small_but_nonzero_lot_still_takes_the_overshoot_path():
    """Below the floor but within MAX_MIN_LOT_OVERSHOOT: rounded up, not skipped.

    Guards the boundary the zero-check sits next to - `raw` of 0.05 against a
    0.1 floor is a 2x overshoot, under the 3.0x limit, so it still trades.
    """
    # 10_000 * 0.005% / 10 = 0.05 lot vs 0.1 floor
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, risk_percent=0.005)
    lot, note = _risk(cfg).lot_for(cfg, sl_distance=1.0, balance=10_000.0)
    assert lot == pytest.approx(0.1)
    assert "atlandi" not in note
