"""H1 left the search. It did not leave the translation tables.

Operator decision 14.08: drop H1 from the sweep to save wall-clock. The
trap is the same one M1 hit earlier - ``timeframe_seconds`` used to fall
back to 300 in silence, so taking a name out of TIMEFRAMES while leaving
it in the seconds table (or the other way around) changes what a green
test means.

H1 stays in the MT5 map and in ``timeframe_seconds`` because history still
names it: ``opt_runs`` rows, correlation, and any symbol the operator has
not moved yet. It is readable. It is not searchable. Asking the planner
for H1 must not silently become "search everything else".
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.logbus import LOG
from micofx.models import READABLE_TIMEFRAMES, TIMEFRAMES, SymbolConfig
from micofx.optimizer import Optimizer


def test_timeframes_does_not_offer_h1():
    assert "H1" not in TIMEFRAMES
    assert TIMEFRAMES == ["M5", "M15", "M30"]
    assert "H1" in READABLE_TIMEFRAMES


def test_h1_still_has_its_own_length(monkeypatch):
    """Readable, not a silent M5 stand-in. See test_unknown_timeframe_is_not_silent."""
    from micofx import mt5client
    mt5client._TF_SECONDS_WARNED.clear()
    seen = []
    monkeypatch.setattr(mt5client.LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append((msg, level)))
    assert mt5client.timeframe_seconds("H1") == 3600
    assert seen == [], "H1 is still wired; a warning here would mean it fell to M5"


class _Store:
    def __init__(self):
        self.symbols = {
            "GER40": SymbolConfig(symbol="GER40", magic=1, enabled=True),
        }

    def get_setting(self, key, default=None):
        return default


def _opt() -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt.store = _Store()
    opt._lock = threading.RLock()
    opt._cancel = threading.Event()
    opt.job = {}
    opt._thread = None
    return opt


def _start(opt: Optimizer, **kw):
    opt._run = lambda *a, **k: None
    original = threading.Thread

    class _NoThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            pass

        def is_alive(self):
            return False

    threading.Thread = _NoThread
    try:
        return opt.start(**kw)
    finally:
        threading.Thread = original


def test_an_h1_only_request_is_refused_not_rewritten(monkeypatch):
    """Silently dropping H1 used to set tf_override None and search M5/M15/M30."""
    seen = []
    monkeypatch.setattr(LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append((msg, level)))
    res = _start(_opt(), timeframes=["H1"])
    assert res["ok"] is False, res
    assert "H1" in res["error"]
    assert "Aranabilir" in res["error"] or "aranabilir" in res["error"].lower()


def test_h1_alongside_a_real_bar_is_dropped_and_logged(monkeypatch):
    seen = []
    monkeypatch.setattr(LOG, "emit",
                        lambda msg, level="INFO", symbol="": seen.append((msg, level)))
    res = _start(_opt(), timeframes=["H1", "M5"])
    assert res["ok"] is True, res
    assert res["job"]["timeframes"] == ["M5"]
    assert any("H1" in m and level == "OPT" for m, level in seen), seen


def test_a_historical_h1_opt_run_still_reads(tmp_path, monkeypatch):
    import micofx.store as store_module

    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    st = store_module.Store()
    st.record_opt_run("GER40", 1.2, {
        "timeframe": "H1", "strategy": "mtf_pullback",
        "holdout": {"trades": 40, "expectancy": 0.1},
    }, applied=True)
    rows = st.opt_history("GER40")
    assert rows, "history vanished"
    assert rows[0]["timeframe"] == "H1"
    assert rows[0]["strategy"] == "mtf_pullback"


def test_the_panel_does_not_offer_h1_as_a_choice():
    js = Path(__file__).resolve().parents[1] / "micofx" / "web" / "static" / "app.js"
    text = js.read_text(encoding="utf-8")
    assert 'OPT_TF_OPTIONS = ["M5", "M15", "M30"]' in text
    assert '["H1", "H1"]' not in text


def test_stored_opt_params_drop_h1_on_read(tmp_path, monkeypatch):
    import micofx.store as store_module

    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    st = store_module.Store()
    st.set_setting("opt_params", {"timeframes": ["M5", "H1", "M15"]})
    assert st.opt_params()["timeframes"] == ["M5", "M15"]
