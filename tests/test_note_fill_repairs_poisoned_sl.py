"""Repair must overwrite a poisoned (<=0) original_sl; trail must not."""
from __future__ import annotations

from types import SimpleNamespace

from micofx import execution as execution_mod
from micofx.engine import Engine
from micofx.execution import ExecutionMonitor


def _tracker() -> ExecutionMonitor:
    return ExecutionMonitor(SimpleNamespace(
        get_setting=lambda *_a, **_k: {},
        set_setting=lambda *_a, **_k: None,
        symbols={},
    ))


def test_note_fill_repairs_poisoned_original_sl():
    eq = _tracker()
    # Legacy / race: book already holds a poisoned value (not via note_fill).
    eq._open[1] = {"original_sl": -49.5, "risk_dist": 50.0, "entry": 25874.0, "side": "buy"}
    eq.note_fill(1, original_sl=25824.0, risk_dist=50.0)
    assert eq._open[1]["original_sl"] == 25824.0
    assert eq._originals[1]["original_sl"] == 25824.0


def test_note_fill_rejects_non_positive_original_sl():
    eq = _tracker()
    eq.note_fill(9, original_sl=-49.5, risk_dist=50.0)
    assert "original_sl" not in eq._open.get(9, {})


def test_note_fill_does_not_overwrite_valid_original_sl():
    eq = _tracker()
    eq.note_fill(2, original_sl=100.0, risk_dist=1.0)
    eq.note_fill(2, original_sl=100.5, risk_dist=0.5)
    assert eq._open[2]["original_sl"] == 100.0


def test_autopsy_poisoned_original_sl_labels_sl_not_trail():
    eng = Engine.__new__(Engine)
    eng._trade_autopsies = []
    eng._trade_autopsy_limit = 100
    row = eng._autopsy_row(
        book={"entry": 25874.0, "side": "buy", "risk_dist": 50.0,
              "original_sl": -49.5, "sl": 25824.0, "mfe": 38.0, "mae": 49.0},
        ticket=324015050, symbol="GER40", exit_price=25822.7, exit_time=100,
        profit=-17.84, reason_code=execution_mod.DEAL_REASON_SL, comment="",
    )
    assert row["exit_reason"] == "sl"


def test_track_heals_poisoned_saved_original_sl():
    eq = _tracker()
    eq._originals[3] = {"original_sl": -138.6, "risk_dist": 138.6}
    eq.track([{
        "ticket": 3, "symbol": "US30", "side": "buy", "sl": 53037.2, "tp": 0.0,
        "price_open": 53123.4, "price_current": 53100.0, "magic": 1, "time": 10,
    }])
    # Reconstruct from risk_dist, not the trailed live SL.
    assert eq._open[3]["original_sl"] == 53123.4 - 138.6
    assert eq._originals[3]["original_sl"] == 53123.4 - 138.6
