"""A malformed session window must be refused, not turned into 24/7 trading.

models._hhmm is deliberately lenient - anything it cannot parse returns 0 -
and session_windows() drops any window whose start equals its end. Those two
reasonable behaviours compose into an unreasonable one:

    {"start": "9", "end": "17"}  ->  (0, 0)  ->  dropped  ->  no windows
    evaluate(): "if not cfg.use_sessions or not windows" -> open every minute

So a symbol configured for eight hours trades twenty-four, on a live account,
with "7/24" in the panel as the only hint. Typing "9" instead of "09:00" is an
entirely ordinary mistake, and nothing validated this field at all.

trade_days had the same gap: [] or [0, 9] was accepted, leaving the symbol
permanently shut while the panel reported it opening in 0 minutes.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.sessions import describe
from micofx.web.app import create_app


class _FakeSystem:
    slippage_points = 20

    def to_dict(self):
        return {}


class _Store:
    def __init__(self, cfg):
        self.symbols = {cfg.symbol: cfg}
        self.system = _FakeSystem()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def opt_history(self, symbol, limit):
        return []

    def update_symbol(self, symbol, patch, source=""):
        cfg = self.symbols.get(symbol)
        current = cfg.to_dict()
        for k, v in patch.items():
            if k in current and v is not None:
                current[k] = v
        self.symbols[symbol] = SymbolConfig.from_dict(current)
        return self.symbols[symbol]


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return None

    def resolve(self, symbol):
        return symbol

    def tick(self, symbol):
        return None


class _Engine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


class _Optimizer:
    def apply(self, *a, **k):
        return {"ok": True}

    def refresh_live_costed_stamp(self, symbol: str):
        """Added 05.09. patch_symbol calls this on any session-clock change.

        The double had drifted behind the production class, so every test in
        this file that PATCHes a session window died on AttributeError before
        reaching its assertion. That is how ``trade_days`` validation could be
        moved after a ``return`` and go unnoticed: the only tests covering the
        session-write path were red for an unrelated reason, and a red test
        proves nothing. Returning None is the "nothing to restamp" branch, so
        the caller leaves ``updated`` alone.
        """
        return None


def _client():
    cfg = SymbolConfig(symbol="XAUUSD", magic=990021)
    cfg.sessions = [{"start": "09:00", "end": "17:00"}]
    cfg.trade_days = [1, 2, 3, 4, 5]
    store = _Store(cfg)
    return TestClient(create_app(store, _Client(), _Engine(), _Optimizer())), store


BAD_WINDOWS = [
    ("saat-eksik", {"start": "9", "end": "17"}),
    ("harf", {"start": "abc", "end": "xyz"}),
    ("bos", {"start": "", "end": ""}),
    ("saniyeli", {"start": "09:00:00", "end": "17:00:00"}),
    ("sifir-uzunluk", {"start": "09:00", "end": "09:00"}),
    ("gecersiz-saat", {"start": "25:00", "end": "26:00"}),
    ("gecersiz-dakika", {"start": "09:99", "end": "17:00"}),
    ("bosluklu-bozuk", {"start": "9 00", "end": "17 00"}),
]


@pytest.mark.parametrize("name,window", BAD_WINDOWS, ids=[b[0] for b in BAD_WINDOWS])
def test_a_malformed_window_is_refused(name, window):
    tc, store = _client()
    before = list(store.symbols["XAUUSD"].sessions)
    res = tc.post("/api/symbols/XAUUSD", json={"sessions": [window]})
    assert res.status_code == 400, f"{window} kabul edildi"
    assert store.symbols["XAUUSD"].sessions == before, "bozuk pencere yine de yazildi"


# The malformed spellings split into two distinct consequences, and the tests
# below assert the actual one for each rather than one blanket claim.
UNPARSEABLE = [w for n, w in BAD_WINDOWS
               if n in ("saat-eksik", "harf", "bos", "saniyeli",
                        "sifir-uzunluk", "bosluklu-bozuk",
                        # "25:00" and "26:00" both clamp to 23:59, so this one
                        # collapses to a zero-length window too.
                        "gecersiz-saat")]
SILENTLY_SHIFTED = [w for n, w in BAD_WINDOWS if n in ("gecersiz-dakika",)]


@pytest.mark.parametrize("window", UNPARSEABLE)
def test_an_unparseable_window_would_otherwise_have_meant_24_7(window):
    """The worse consequence: the window vanishes and the day opens fully."""
    cfg = SymbolConfig(symbol="T", magic=1)
    cfg.use_sessions = True
    cfg.sessions = [window]
    assert cfg.session_windows() == [], window
    assert describe(cfg) == "7/24"


@pytest.mark.parametrize("window", SILENTLY_SHIFTED)
def test_an_out_of_range_window_would_otherwise_have_shifted_silently(window):
    """The quieter consequence: it parses, to a time nobody typed.

    "09:99" becomes 10:39 and "25:00" clamps to 23:59 - no window is lost, so
    the panel shows a plausible range that is simply not the one requested.
    """
    cfg = SymbolConfig(symbol="T", magic=1)
    cfg.use_sessions = True
    cfg.sessions = [window]
    windows = cfg.session_windows()
    assert windows, window
    start_min = windows[0][0]
    # Rendered back as a clock time, it is not the string that was typed:
    # "09:99" reads back as 10:39 and "25:00" clamps to 23:59.
    rendered = f"{start_min // 60:02d}:{start_min % 60:02d}"
    assert rendered != window["start"], "bu deger aslinda gecerli bir saatmis"


BAD_DAYS = [("bos", []), ("sifir", [0]), ("dokuz", [9]), ("karisik", [1, 8]),
            ("liste-degil", "hepsi")]


@pytest.mark.parametrize("name,days", BAD_DAYS, ids=[b[0] for b in BAD_DAYS])
def test_bad_trade_days_are_refused(name, days):
    tc, store = _client()
    before = list(store.symbols["XAUUSD"].trade_days)
    res = tc.post("/api/symbols/XAUUSD", json={"trade_days": days})
    assert res.status_code == 400, f"{days} kabul edildi"
    assert store.symbols["XAUUSD"].trade_days == before


def test_bulk_is_gated_too():
    """The door that would apply a bad window to the whole portfolio."""
    tc, store = _client()
    res = tc.post("/api/symbols-bulk",
                  json={"patch": {"sessions": [{"start": "9", "end": "17"}]}})
    assert res.status_code == 400


VALID = [
    [{"start": "09:00", "end": "17:00"}],
    [{"start": "00:00", "end": "23:59"}],
    [{"start": "22:00", "end": "02:00"}],                      # rolls midnight
    [{"start": "09:00", "end": "12:00"}, {"start": "14:00", "end": "18:00"}],
    [{"start": "1:05", "end": "23:55"}],                       # single-digit hour
]


@pytest.mark.parametrize("windows", VALID)
def test_valid_windows_still_go_through(windows):
    tc, store = _client()
    res = tc.post("/api/symbols/XAUUSD", json={"sessions": windows})
    assert res.status_code == 200, res.text
    assert store.symbols["XAUUSD"].session_windows(), "gecerli pencere dusuruldu"


def test_valid_trade_days_still_go_through():
    tc, store = _client()
    assert tc.post("/api/symbols/XAUUSD", json={"trade_days": [1, 5, 7]}).status_code == 200
    assert store.symbols["XAUUSD"].trade_days == [1, 5, 7]


def test_the_live_portfolio_windows_all_pass():
    """Nothing shipped or currently configured may be rejected by this gate."""
    tc, _ = _client()
    for windows in ([{"start": "01:00", "end": "23:55"}],
                    [{"start": "02:00", "end": "23:55"}],
                    [{"start": "03:15", "end": "22:55"}],
                    [{"start": "09:00", "end": "22:55"}],
                    [{"start": "03:00", "end": "22:55"}]):
        assert tc.post("/api/symbols/XAUUSD", json={"sessions": windows}).status_code == 200
