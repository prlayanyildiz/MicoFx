"""An overlay PATCH must re-evaluate the stop on the current closed bar.

breakeven_at_r / harvest_* are not EXIT_RISK: a PATCH is supposed to
apply to already-open tickets. manage_positions used to call _update_stop
only when last_bar changed, so after overlay_stop returned None the bar
was marked settled and a later BE/harvest PATCH sat idle until the next
candle - 30 minutes on M30, on the exact trade that was already past the
new threshold on the close we already have.

The trail *level* still comes from that closed bar's close. This only
retries the same overlay_stop once the overlay numbers change.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_engine_breakeven_lock_at_r import _Cfg as _BeCfg
from test_trail_retry_within_bar import ATR, BAR_OPEN, _Bars, _Client, _pos

from micofx.engine import Engine, SymbolState
from micofx.execution import ExecutionMonitor
from micofx.models import SymbolConfig


class _Symbols:
    def __init__(self, cfg):
        self._cfg = cfg

    def values(self):
        return [self._cfg]

    def get(self, symbol):
        return self._cfg


class _Store:
    def __init__(self, cfg):
        self.system = SimpleNamespace(
            slippage_points=20, block_high_cost=False,
            max_cost_pct_of_risk=0.0, trade_all_hours=True,
            daily_loss_flatten=False, day_end_flatten_min=0)
        self.symbols = _Symbols(cfg)
        self.settings: dict = {}

    def set_setting(self, key, value):
        self.settings[key] = value


class _FillStore:
    def __init__(self, cfg):
        self.settings: dict = {}
        self.symbols = {cfg.symbol: cfg}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


def _manage_engine(cfg, pos, close: float):
    client = _Client(bid=close, min_stop=0.1)
    client.connected = True
    eng = Engine.__new__(Engine)
    eng.client = client
    eng.store = _Store(cfg)
    eng.entry_lock = threading.Lock()
    eng.execution = ExecutionMonitor(_FillStore(cfg))
    eng.execution.note_fill(pos["ticket"], original_sl=99.0, risk_dist=1.0,
                            entry=100.0)
    state = SymbolState(cfg.symbol)
    state.atr = ATR
    state.last_bar = BAR_OPEN
    state.bars = _Bars(close)
    eng.states = {cfg.symbol: state}
    eng._positions = [pos]
    eng._weekend_pending = set()
    eng._force_flat_pending = set()
    eng._orphan_tickets = set()
    eng._unmanaged_seen = set()
    eng._stopless_seen = set()
    eng._sec_tickets = set()
    eng._open_resume_logged = True
    return eng, client


def test_a_be_patch_locks_on_the_close_already_in_hand():
    """+1.2 R close is below BE 1.5. Patching to 1.0 must lock this bar."""
    cfg = _BeCfg()
    cfg.breakeven_at_r = 1.5
    cfg.partial_at_r = 0.0
    cfg.harvest_at_r = 0.0
    cfg.harvest_step_atr = 0.0
    pos = _pos(sl=99.0, entry=100.0)
    pos["magic"] = cfg.magic
    pos["volume"] = 0.1
    eng, client = _manage_engine(cfg, pos, close=101.2)

    eng.manage_positions(server_now=None)
    assert client.modifies == []

    cfg.breakeven_at_r = 1.0
    eng.manage_positions(server_now=None)
    assert client.modifies == [pytest.approx(100.0)]
    assert pos["sl"] == pytest.approx(100.0)


def test_overlay_fields_are_still_not_exit_risk():
    from micofx.models import EXIT_RISK_FIELDS, OPT_FIELDS
    for name in ("breakeven_at_r", "harvest_at_r", "harvest_step_atr",
                 "partial_at_r"):
        assert name not in EXIT_RISK_FIELDS
        assert name not in OPT_FIELDS
    assert SymbolConfig(symbol="GER40", magic=1).breakeven_at_r == 0.0
