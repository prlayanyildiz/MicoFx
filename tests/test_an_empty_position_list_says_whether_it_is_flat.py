"""An empty position list must say whether the book is flat or unreadable.

``client.positions()`` returns ``[]`` in two completely different situations:
the account really is flat, and ``positions_get`` failed mid-call (which flips
``connected`` False - see mt5client.py). The codebase already treats confusing
those two as a defect and says so twice, in ``_require_connected`` and in
``_positions``: every mutating route - DELETE, seed-overwrite, magic reuse,
primary exit-family PATCH - fails closed rather than agree there is nothing to
protect. ``/api/state`` needs no such refusal because it ships ``mt5.connected``
in the same payload as its copy of the list.

``GET /api/positions`` had neither. It answered ``{"ok": true, "positions": []}``
whether nine positions were open behind a dropped connection or none existed,
and that is the endpoint the review loops read to assert "every open position
has a stop". A disconnect would have produced "no positions, nothing
unprotected" - a clean bill of health drawn from an unreadable book - which is
the same fail-open the mutating guards were written to prevent.

Reported rather than refused, because unlike those guards there is no mutation
here to fail closed on, and 503-ing a display route would blank the dashboard on
a blip. The distinction is handed to the caller instead.

Fourth call site of the same rule: engine's cycle snapshot, its orphan
last-look, and the web mutate helper all check ``connected`` immediately after
reading positions. This was the one read path that did not.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.web.app import create_app


class _System:
    slippage_points = 20

    def to_dict(self):
        return {}


class _Store:
    def __init__(self, cfg):
        self.symbols = {cfg.symbol: cfg}
        self.system = _System()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, k, default=None):
        return default

    def opt_params(self):
        return {}

    def opt_history(self, s, n):
        return []


class _Client:
    """``connected`` False with an empty list is exactly what a mid-call
    positions_get failure leaves behind."""

    def __init__(self, connected=True, positions=()):
        self.connected = connected
        self._positions = list(positions)

    def positions(self, magic=None, symbol=None):
        if magic is not None:
            return [p for p in self._positions if p["magic"] == magic]
        return list(self._positions)

    def set_overrides(self, m):
        pass

    def info(self, s):
        return None

    def resolve(self, s):
        return s

    def tick(self, s):
        return None


class _Supervisor:
    def __init__(self):
        self.settings = {"lookback_days": 30}

    def status(self):
        return {"symbols": []}


class _Engine:
    def __init__(self, client, store):
        self.client = client
        self.store = store
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}
        self.supervisor = _Supervisor()

    def positions_view(self):
        by_magic = {c.magic: c for c in self.store.symbols.values()}
        out = []
        for pos in self.client.positions():
            cfg = by_magic.get(pos["magic"])
            item = dict(pos)
            item["managed"] = cfg is not None
            item["config_symbol"] = cfg.symbol if cfg else pos["symbol"]
            item["group"] = cfg.group if cfg else "-"
            out.append(item)
        return out


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25

    def apply(self, *a, **k):
        return {"ok": True}


def _get(connected: bool, positions=()):
    cfg = SymbolConfig(symbol="GER40", magic=1, timeframe="M15", strategy="stoch_flip")
    store = _Store(cfg)
    client = _Client(connected, positions)
    tc = TestClient(create_app(store, client, _Engine(client, store), _Optimizer()))
    return tc.get("/api/positions").json()


_OPEN = ({"ticket": 1, "magic": 1, "symbol": "GER40", "sl": 26411.8,
          "profit": 13.3, "type": 0, "volume": 0.1, "price_open": 26500.0},)


# ------------------------------------------------------------- the defect

def test_a_dropped_connection_is_not_reported_as_an_empty_book():
    res = _get(connected=False)
    assert res["positions"] == []
    assert res["connected"] is False, (
        "bos liste 'duz' mu 'okunamadi' mi ayirt edilemiyor")


def test_a_genuinely_flat_book_is_distinguishable_from_that():
    res = _get(connected=True)
    assert res["positions"] == []
    assert res["connected"] is True


def test_the_two_empty_answers_differ():
    """The whole point: same list, different meaning, and the payload says so."""
    assert _get(connected=False) != _get(connected=True)


# --------------------------------------------------- what must keep working

def test_open_positions_are_still_returned_unchanged():
    res = _get(connected=True, positions=_OPEN)
    assert res["ok"] is True
    assert len(res["positions"]) == 1
    assert res["positions"][0]["sl"] == 26411.8
    assert res["positions"][0]["managed"] is True


def test_the_route_does_not_refuse_on_a_disconnect():
    """A display route must not 503 the dashboard on a blip - unlike the
    mutating guards, there is nothing here to fail closed on."""
    cfg = SymbolConfig(symbol="GER40", magic=1, timeframe="M15", strategy="stoch_flip")
    store = _Store(cfg)
    client = _Client(False, ())
    tc = TestClient(create_app(store, client, _Engine(client, store), _Optimizer()))
    assert tc.get("/api/positions").status_code == 200


def test_positions_held_behind_a_dropped_connection_still_list_with_the_flag():
    """mt5client can hand back a stale list while already flagged down; the
    flag must not be read as "so the list is empty"."""
    res = _get(connected=False, positions=_OPEN)
    assert res["connected"] is False
    assert len(res["positions"]) == 1
