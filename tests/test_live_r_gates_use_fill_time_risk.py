"""Harvest / BE / partial R must use the fill-time stop, not this bar's ATR.

Paper freezes ``sl_dist`` at entry. Live used ``atr * sl_atr_mult`` on every
trail poll, so a trade that opened at 1.0 ATR and later saw ATR double
needed +3 R of *fill* movement before harvest 1.5 fired - the leftover
the autopsy kept counting. ATR shrinking did the opposite: BE/harvest
fired early and stopped winners into noise.

Restart already persists fill-time original_sl. The live trail has to
read that, not re-derive from the current bar.
"""
from __future__ import annotations

import inspect
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_engine_breakeven_lock_at_r import _Cfg as _BeCfg
from test_original_sl_survives_restart import _Store
from test_scale_out_once import _eng as _scale_eng
from test_scale_out_once import _ScaleCfg, _ScaleClient
from test_trail_retry_within_bar import _Bars, _Client, _engine, _pos

from micofx.engine import Engine
from micofx.execution import ExecutionMonitor


def _with_fill(eng, ticket=1, original_sl=99.0, risk_dist=1.0):
    store = _Store()
    eng.execution = ExecutionMonitor(store)
    eng.execution.note_fill(ticket, original_sl=original_sl, risk_dist=risk_dist,
                            entry=100.0)


class _HarvestCfg(_BeCfg):
    breakeven_at_r = 0.0
    harvest_at_r = 1.5
    harvest_step_atr = 0.4


def test_be_still_locks_when_current_atr_has_doubled():
    """+1.6 fill-R is 1.6R. Current ATR 2.0 would call it 0.8R and skip BE."""
    client = _Client(bid=101.6, min_stop=0.1)
    eng = _engine(client)
    _with_fill(eng)
    pos = _pos(sl=99.0, entry=100.0)
    assert eng._update_stop(_BeCfg(), pos, 2.0, _Bars(101.6)) is True
    assert client.modifies == [pytest.approx(100.0)]


def test_without_a_saved_fill_current_atr_is_still_the_fallback():
    client = _Client(bid=101.6, min_stop=0.1)
    eng = _engine(client)
    pos = _pos(sl=99.0, entry=100.0)
    eng._update_stop(_BeCfg(), pos, 2.0, _Bars(101.6))
    assert client.modifies == []


def test_harvest_tightens_on_fill_r_when_atr_has_doubled():
    """Trail start 3.0 is not armed; harvest 1.5 fill-R is. ATR 2.0 is not."""
    client = _Client(bid=101.6, min_stop=0.1)
    eng = _engine(client)
    _with_fill(eng)
    pos = _pos(sl=99.0, entry=100.0)
    assert eng._update_stop(_HarvestCfg(), pos, 2.0, _Bars(101.6)) is True
    # harvest step 0.4 * current ATR 2.0 = 0.8 behind close 101.6
    assert client.modifies == [pytest.approx(100.8)]


def test_partial_fires_on_fill_r_when_atr_has_doubled():
    client = _ScaleClient(bid=101.6)
    eng = _scale_eng(client)
    _with_fill(eng, ticket=1)
    pos = _pos(sl=99.0, entry=100.0)
    pos["volume"] = 0.70
    pos["symbol"] = "GER40"
    assert eng._maybe_scale_out(_ScaleCfg(), pos, 2.0, _Bars(101.6)) is True
    assert client.closes


def test_both_live_gates_read_fill_time_risk():
    assert "_fill_time_risk" in inspect.getsource(Engine._update_stop)
    assert "_fill_time_risk" in inspect.getsource(Engine._maybe_scale_out)


def test_mfe_peak_survives_a_restart():
    store = _Store()
    mon = ExecutionMonitor(store)
    mon.note_fill(7, original_sl=99.0, risk_dist=1.0, entry=100.0)
    mon.track([{"ticket": 7, "symbol": "GER40", "side": "buy", "sl": 99.0,
                "tp": 0.0, "price_open": 100.0, "price_current": 103.0,
                "magic": 1, "time": 10}])
    blob = store.settings["open_original_sl"]["7"]
    assert blob["mfe"] == pytest.approx(3.0)

    restarted = ExecutionMonitor(store)
    restarted.track([{"ticket": 7, "symbol": "GER40", "side": "buy", "sl": 101.0,
                      "tp": 0.0, "price_open": 100.0, "price_current": 101.2,
                      "magic": 1, "time": 10}])
    assert restarted._open[7]["mfe"] == pytest.approx(3.0)
    assert restarted._open[7]["original_sl"] == pytest.approx(99.0)


def _resume_engine():
    cfg = SimpleNamespace(symbol="NAS100", magic=14, group="index")
    eng = Engine.__new__(Engine)
    eng.client = SimpleNamespace(connected=True)
    eng.store = SimpleNamespace(
        symbols={"NAS100": cfg},
        system=SimpleNamespace(daily_loss_flatten=False, trade_all_hours=True,
                               day_end_flatten_min=0, slippage_points=20),
        set_setting=lambda *a, **k: None,
        get_setting=lambda *a, **k: None,
    )
    eng.entry_lock = threading.Lock()
    eng._positions = []
    eng._weekend_pending = set()
    eng._force_flat_pending = set()
    eng._sec_tickets = set()
    eng._orphan_tickets = set()
    eng._scale_out_done = set()
    eng._stop_bar = {}
    eng._unmanaged_seen = set()
    eng._stopless_seen = set()
    eng.states = {}
    return eng


def test_first_manage_cycle_logs_tickets_resumed_by_magic(monkeypatch):
    eng = _resume_engine()
    eng._positions = [{"ticket": 42, "magic": 14, "symbol": "NAS100",
                       "side": "buy", "volume": 0.3, "time": 1, "sl": 100.0,
                       "profit": 0, "swap": 0}]
    lines: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "micofx.engine.LOG.emit",
        lambda msg, level="INFO", *a, **k: lines.append((msg, level)))
    eng.manage_positions(server_now=None)
    eng.manage_positions(server_now=None)
    resumed = [(m, lvl) for m, lvl in lines
               if "magic ile" in m and "devam ediyor" in m]
    assert len(resumed) == 1
    assert resumed[0][1] == "WARN"
    assert "#42" in resumed[0][0] and "NAS100" in resumed[0][0]


def test_trusted_empty_book_does_not_label_later_fills_as_restart(monkeypatch):
    """manage_positions runs only after a connected positions() read
    (_cycle bails if that read flipped connected). Empty here is flat, not
    'list failed'. Latch on that read; a ticket that opens hours later is
    a new fill, not a resumed restart book."""
    eng = _resume_engine()
    lines: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "micofx.engine.LOG.emit",
        lambda msg, level="INFO", *a, **k: lines.append((msg, level)))
    eng.manage_positions(server_now=None)
    eng._positions = [{"ticket": 42, "magic": 14, "symbol": "NAS100",
                       "side": "buy", "volume": 0.3, "time": 1, "sl": 100.0,
                       "profit": 0, "swap": 0}]
    eng.manage_positions(server_now=None)
    resumed = [m for m, lvl in lines if "magic ile" in m and "devam ediyor" in m]
    assert resumed == []
