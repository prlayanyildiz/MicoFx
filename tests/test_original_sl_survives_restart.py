"""Fill-time original_sl must survive a process restart with opens.

track() setdefault's original_sl from the live stop. After a trail, that
is the current trail, not the fill. Autopsy R then becomes tautological.
Persist on note_fill; restore before the first-sight fallback. Do not
persist the fallback itself (that would freeze a pre-patch trail).
"""
from __future__ import annotations

from micofx.execution import ExecutionMonitor


class _Store:
    def __init__(self, settings=None):
        self.settings = dict(settings or {})
        self.symbols = {"GER40": object()}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


def _pos(ticket=7, sl=99.0, current=100.0):
    return {
        "ticket": ticket, "symbol": "GER40", "side": "buy",
        "sl": sl, "tp": 0.0, "price_open": 100.0, "price_current": current,
        "magic": 1, "time": 10,
    }


def test_note_fill_writes_original_sl_to_the_store():
    store = _Store()
    mon = ExecutionMonitor(store)
    mon.note_fill(7, original_sl=99.0, risk_dist=1.0, entry=100.0)
    blob = store.settings["open_original_sl"]
    assert blob["7"]["original_sl"] == 99.0
    assert blob["7"]["risk_dist"] == 1.0


def test_a_restart_with_a_trailed_stop_keeps_the_fill_time_original():
    store = _Store({"open_original_sl": {"7": {"original_sl": 99.0, "risk_dist": 1.0}}})
    mon = ExecutionMonitor(store)
    mon.track([_pos(sl=101.5, current=102.0)])
    book = mon._open[7]
    assert book["original_sl"] == 99.0
    assert book["risk_dist"] == 1.0


def test_first_sight_without_a_saved_row_still_uses_the_live_stop():
    """Pre-patch tickets: we cannot invent fill-time SL. Do not persist that."""
    store = _Store()
    mon = ExecutionMonitor(store)
    mon.track([_pos(sl=101.5)])
    assert mon._open[7]["original_sl"] == 101.5
    assert "open_original_sl" not in store.settings


def test_a_closed_ticket_is_dropped_from_the_blob():
    store = _Store({"open_original_sl": {
        "7": {"original_sl": 99.0, "risk_dist": 1.0},
        "8": {"original_sl": 50.0, "risk_dist": 2.0},
    }})
    mon = ExecutionMonitor(store)
    mon.track([_pos(ticket=7, sl=99.0)])
    blob = store.settings["open_original_sl"]
    assert "7" in blob
    assert "8" not in blob
