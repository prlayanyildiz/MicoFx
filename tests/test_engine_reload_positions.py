"""Mid-cycle positions() failure must not wipe the engine's live snapshot."""
from __future__ import annotations

import threading
from types import SimpleNamespace

from micofx.engine import Engine
from micofx.models import SymbolConfig


class _Client:
    def __init__(self):
        self.connected = True
        self._next: list[dict] = []
        self._flip = False

    def positions(self):
        if self._flip:
            self.connected = False
            return []
        return list(self._next)


def test_reload_positions_keeps_snapshot_when_positions_get_fails():
    eng = object.__new__(Engine)
    eng.client = _Client()
    eng._positions = [{"ticket": 7, "magic": 1}]
    eng.client._next = [{"ticket": 8, "magic": 1}]
    eng.client._flip = True

    ok = Engine._reload_positions(eng)

    assert ok is False
    assert eng._positions == [{"ticket": 7, "magic": 1}]
    assert eng.client.connected is False


def test_manage_positions_skips_tag_prune_when_disconnected():
    eng = object.__new__(Engine)
    eng.client = _Client()
    eng.client.connected = False
    eng.store = SimpleNamespace(
        symbols={},
        system=SimpleNamespace(slippage_points=5),
        set_setting=lambda *a, **k: None,
        get_setting=lambda *a, **k: None,
    )
    eng._positions = []  # would look "flat"
    eng._sec_tickets = {42}
    eng._orphan_tickets = {99}
    eng._weekend_pending = set()
    eng._partials = {}
    eng._stop_bar = {}
    eng.states = {}
    eng.entry_lock = threading.Lock()

    Engine.manage_positions(eng, server_now=0.0)

    assert eng._sec_tickets == {42}
    assert eng._orphan_tickets == {99}
