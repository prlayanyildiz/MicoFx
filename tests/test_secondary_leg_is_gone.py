"""The second leg is gone. Panel and tally still pretended it could speak.

Found 14.08: ``state.signal_source`` is only ever written as ``"primary"``
or empty (``engine._merge_signals``). Nothing assigns ``"secondary"`` or
``"conflict"``. The card still drew `` (2)`` and CAPRAZ, the status JSON
still shipped an empty ``secondary_signal``, and ``_tally_entry`` still
branched on a source that cannot arrive.

``signal_source`` itself stays - it keys ``_filled_bars`` / ``pending_bar_key``.
It is two-valued now, not three.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig


def test_state_json_has_no_secondary_signal_field():
    st = SymbolState("XAUUSD")
    st.signal = "buy"
    st.primary_signal = "buy"
    st.signal_source = "primary"
    payload = st.as_dict()
    assert "secondary_signal" not in payload
    assert payload["signal_source"] in ("", "primary")


def test_merge_signals_only_emits_empty_or_primary():
    eng = object.__new__(Engine)
    st = SymbolState("XAUUSD")
    cfg = SymbolConfig(symbol="XAUUSD")
    st.primary_signal = "sell"
    eng._merge_signals(cfg, st)
    assert st.signal == "sell"
    assert st.signal_source == "primary"
    st.primary_signal = ""
    eng._merge_signals(cfg, st)
    assert st.signal == ""
    assert st.signal_source == ""


def test_entry_tally_leg_is_always_primary():
    """Passing the retired source name must not mint a second tally bucket."""
    eng = object.__new__(Engine)
    eng._entry_blocks = {}
    eng._entry_last_bar = {}
    eng._entry_blocks_dirty = False
    eng._tally_entry("XAUUSD", "spread", source="secondary", bar_key=1)
    assert list(eng._entry_blocks["XAUUSD"]) == ["primary"]


def test_the_panel_does_not_draw_a_second_leg():
    js = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static" / "app.js"
          ).read_text(encoding="utf-8")
    assert 'st.signal_source === "secondary"' not in js
    assert 'st.signal_source === "conflict"' not in js
    assert "CAPRAZ" not in js


def test_leftover_secondary_tickets_do_not_hold_entry():
    """_sec_tickets is a stale tag set. Entry waits on _orphan_scan, not on it."""
    from types import SimpleNamespace

    cfg = SymbolConfig(symbol="EURUSD", group="crypto", magic=1)
    eng = object.__new__(Engine)
    eng.store = SimpleNamespace(system=SimpleNamespace())
    eng.client = SimpleNamespace(connected=True)
    eng._link_backoff = {}
    eng._orphan_scan = {}
    eng._sec_tickets = {99}
    st = SymbolState("EURUSD")
    st.signal = "buy"
    st.atr = float("nan")
    eng._try_entry(cfg, st, account={"balance": 1000.0})
    assert st.entry_block != "ikincil_tarama"
    assert st.entry_block == "atr_yok"


def test_a_nonempty_secondary_tickets_row_is_logged_not_silenced(tmp_path, monkeypatch):
    from micofx import store as store_module
    from micofx.logbus import LOG
    from micofx.store import Store

    class _Client:
        connected = True

        def positions(self, magic=None, symbol=None):
            return []

        def set_overrides(self, mapping):
            pass

        def min_stop_distance(self, symbol):
            return 0.0

        def info(self, symbol):
            return None

        def resolve(self, symbol):
            return symbol

        def tick(self, symbol):
            return None

        def account(self):
            return {}

        def bars(self, *a, **k):
            return None

    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "sec.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    store = Store()
    store.set_setting("secondary_tickets", [333])
    seen = []
    orig = LOG.emit

    def _cap(msg, level="INFO", symbol=""):
        seen.append((msg, level, symbol))
        return orig(msg, level, symbol)

    LOG.emit = _cap
    try:
        Engine(store, _Client())
    finally:
        LOG.emit = orig
        store.close()
    assert any(
        "secondary_tickets" in m and level == "WARN" for m, level, _ in seen
    ), seen
