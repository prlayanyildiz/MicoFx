"""Open tickets must block session / use_sessions PATCH (Claude TEYIT Py #3).

09-04 XAU #325114801: use_sessions flipped True while ticket open, then 10018.
clock_changed only restamped holdout; it was not in the open-position guard set.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig, SystemConfig
from micofx.web.app import create_app

HEAD = {"Origin": "http://testserver"}


class _Store:
    def __init__(self):
        self.system = SystemConfig()
        self.defaults = {"symbols": [], "group_presets": {}}
        self.symbols = {
            "XAUUSD": SymbolConfig(
                symbol="XAUUSD", magic=990021, enabled=True,
                strategy="mtf_pullback", timeframe="M15",
                use_sessions=False,
                sessions=[{"start": "01:01", "end": "23:59"}],
                opt_updated_at=1.0, opt_score=1.0, validated=True,
            ),
        }

    def get_setting(self, key, default=None):
        return default

    def set_setting(self, key, value):
        pass

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch, source=""):
        cfg = self.symbols[symbol]
        for key, value in patch.items():
            setattr(cfg, key, value)
        return cfg


class _Client:
    connected = True

    def __init__(self, positions=None):
        self._positions = list(positions or [])

    def positions(self, magic=None, symbol=None):
        rows = self._positions
        if magic is not None:
            rows = [p for p in rows if p.get("magic") == magic]
        return rows

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return {"name": symbol, "volume_min": 0.01, "volume_step": 0.01,
                "digits": 2, "description": symbol}


class _Engine:
    entry_lock = threading.Lock()

    def refresh_account(self, force=False):
        return {}


def test_use_sessions_patch_409_while_ticket_open():
    store = _Store()
    client = _Client([{"ticket": 325114801, "symbol": "XAUUSD", "magic": 990021}])
    app = create_app(store, client, _Engine(), optimizer=None)
    tc = TestClient(app)
    res = tc.post(
        "/api/symbols/XAUUSD",
        json={"use_sessions": True},
        headers=HEAD,
    )
    assert res.status_code == 409, res.text
    assert "seans" in res.json()["detail"].lower()
    assert store.symbols["XAUUSD"].use_sessions is False


def test_sessions_patch_409_while_ticket_open():
    store = _Store()
    store.symbols["XAUUSD"].use_sessions = True
    client = _Client([{"ticket": 1, "symbol": "XAUUSD", "magic": 990021}])
    app = create_app(store, client, _Engine(), optimizer=None)
    tc = TestClient(app)
    res = tc.post(
        "/api/symbols/XAUUSD",
        json={"sessions": [{"start": "15:00", "end": "21:00"}]},
        headers=HEAD,
    )
    assert res.status_code == 409, res.text
    assert store.symbols["XAUUSD"].sessions[0]["start"] == "01:01"


def test_sessions_patch_ok_when_flat():
    store = _Store()
    store.symbols["XAUUSD"].use_sessions = True
    app = create_app(store, _Client([]), _Engine(), optimizer=None)
    tc = TestClient(app)
    res = tc.post(
        "/api/symbols/XAUUSD",
        json={"sessions": [{"start": "15:00", "end": "21:00"}]},
        headers=HEAD,
    )
    assert res.status_code == 200, res.text
    assert store.symbols["XAUUSD"].sessions[0]["start"] == "15:00"


# --------------------------------------------------------------------------
# The mask is four fields. use_sessions/sessions were guarded; the other two
# were two more doors to the same outcome - the same open trade truncated,
# through a different field.
#
# sessions.session_state() reads cfg.trade_days every cycle to decide whether
# today trades at all, and sessions.should_flatten() reads
# cfg.flat_before_close_min every cycle to decide how many minutes before the
# window closes an open position is force-closed. Both are re-read live off
# the config, exactly like the windows.

def _open_client():
    return _Client([{"ticket": 325114801, "symbol": "XAUUSD", "magic": 990021}])


def test_trade_days_patch_409_while_ticket_open():
    store = _Store()
    store.symbols["XAUUSD"].use_sessions = True
    tc = TestClient(create_app(store, _open_client(), _Engine(), optimizer=None))
    res = tc.post("/api/symbols/XAUUSD", json={"trade_days": [1, 2, 3]}, headers=HEAD)
    assert res.status_code == 409, res.text
    assert "seans" in res.json()["detail"].lower()
    assert store.symbols["XAUUSD"].trade_days == [1, 2, 3, 4, 5]


def test_flat_before_close_patch_409_while_ticket_open():
    store = _Store()
    store.symbols["XAUUSD"].use_sessions = True
    tc = TestClient(create_app(store, _open_client(), _Engine(), optimizer=None))
    res = tc.post("/api/symbols/XAUUSD",
                  json={"flat_before_close_min": 30}, headers=HEAD)
    assert res.status_code == 409, res.text
    assert store.symbols["XAUUSD"].flat_before_close_min == 0


def test_an_unchanged_mask_is_not_a_change():
    """Re-sending the same day mask under an open ticket is not a truncation.

    The refusal is about the mask MOVING. A panel that re-posts the whole row
    would otherwise be unable to touch anything while a trade is on.
    """
    store = _Store()
    store.symbols["XAUUSD"].use_sessions = True
    tc = TestClient(create_app(store, _open_client(), _Engine(), optimizer=None))
    res = tc.post("/api/symbols/XAUUSD",
                  json={"trade_days": [1, 2, 3, 4, 5], "flat_before_close_min": 0},
                  headers=HEAD)
    assert res.status_code == 200, res.text


def test_an_unchanged_sessions_list_does_not_mask_a_changed_flag():
    """``sessions`` used to ``return`` its own comparison rather than fall
    through, so an unchanged windows list in the same patch answered False for
    the whole mask and let a real use_sessions flip land mid-ticket."""
    store = _Store()
    tc = TestClient(create_app(store, _open_client(), _Engine(), optimizer=None))
    res = tc.post(
        "/api/symbols/XAUUSD",
        json={"use_sessions": True,
              "sessions": [{"start": "01:01", "end": "23:59"}]},
        headers=HEAD,
    )
    assert res.status_code == 409, res.text
    assert store.symbols["XAUUSD"].use_sessions is False


# ------------------------------------------------------- bulk is a door too

def test_bulk_mask_edit_rejected_while_ticket_open():
    """/api/symbols-bulk reached these fields with no check at all: one batch
    could truncate every open trade in the book at once."""
    store = _Store()
    store.symbols["XAUUSD"].use_sessions = True
    tc = TestClient(create_app(store, _open_client(), _Engine(), optimizer=None))
    res = tc.post("/api/symbols-bulk",
                  json={"symbols": ["XAUUSD"],
                        "patch": {"sessions": [{"start": "15:00", "end": "21:00"}]}},
                  headers=HEAD)
    assert res.status_code == 200, res.text
    assert res.json()["rejected"] == ["XAUUSD"]
    assert store.symbols["XAUUSD"].sessions[0]["start"] == "01:01"


def test_bulk_mask_edit_lands_when_flat_and_restamps():
    """Flat, it lands - and the costed holdout is restamped, because the number
    it carried was measured under the old mask."""
    store = _Store()
    store.symbols["XAUUSD"].use_sessions = True
    restamped: list[str] = []

    class _Opt:
        busy = False

        def refresh_live_costed_stamp(self, symbol):
            restamped.append(symbol)
            return None

    tc = TestClient(create_app(store, _Client([]), _Engine(), _Opt()))
    res = tc.post("/api/symbols-bulk",
                  json={"symbols": ["XAUUSD"],
                        "patch": {"trade_days": [1, 2, 3]}},
                  headers=HEAD)
    assert res.status_code == 200, res.text
    assert "rejected" not in res.json()
    assert store.symbols["XAUUSD"].trade_days == [1, 2, 3]
    assert restamped == ["XAUUSD"], "eski maskeyle olculmus holdout damgasi kaldi"
