"""How much the book actually moves together, as a number rather than an argument.

Eight of thirteen live symbols are equity indices. Whether that is a
concentration problem or just a long list had been argued both ways with
nobody measuring it. Stops cap what any ONE trade loses; they do nothing
about several positions losing at once, because each stops out independently
at full risk. So the question is how correlated the book is, and that is
measurable.

Computed on log returns rather than prices - raw prices trend, and a
correlation of trending series reports almost everything as correlated.
Pairs align on their shared tail because symbols quote different session
lengths, so the bar count is reported per pair.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.web.app import create_app


class _Bars:
    def __init__(self, close):
        self.close = np.asarray(close, dtype=np.float64)
        self.high = self.close + 0.5
        self.low = self.close - 0.5
        self.open = self.close
        self.volume = np.full(self.close.size, 100.0)
        self.spread = np.full(self.close.size, 5.0)
        self.time = np.arange(self.close.size, dtype=np.int64) * 3600

    def __len__(self):
        return self.close.size


class _System:
    slippage_points = 20

    def to_dict(self):
        return {}


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = _System()
        self.defaults = {"symbols": [], "group_presets": {}}

    def get_setting(self, k, default=None):
        return default

    def opt_params(self):
        return {}

    def opt_history(self, s, n):
        return []


class _Client:
    connected = True

    def __init__(self, book):
        self.book = book

    def bars(self, symbol, timeframe, count):
        return self.book.get(symbol)

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, m):
        pass

    def info(self, s):
        return None

    def resolve(self, s):
        return s

    def tick(self, s):
        return None


class _Engine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25

    def apply(self, *a, **k):
        return {"ok": True}


def _client(book, groups=None, enabled=None):
    groups = groups or {}
    cfgs = []
    for i, sym in enumerate(book):
        cfg = SymbolConfig(symbol=sym, magic=i + 1,
                           group=groups.get(sym, "index"))
        if enabled is not None:
            cfg.enabled = enabled.get(sym, True)
        cfgs.append(cfg)
    return TestClient(create_app(_Store(cfgs), _Client(book), _Engine(), _Optimizer()))


def _walk(seed, n=400, shared=None, weight=0.0):
    rng = np.random.default_rng(seed)
    own = rng.normal(0, 0.01, n)
    steps = own if shared is None else weight * shared + (1 - weight) * own
    return 100 * np.exp(np.cumsum(steps))


def _pair(res, a, b):
    for p in res.json()["pairs"]:
        if {p["a"], p["b"]} == {a, b}:
            return p
    raise AssertionError(f"{a}/{b} cifti yok")


def test_two_symbols_driven_by_the_same_shocks_read_as_correlated():
    rng = np.random.default_rng(1)
    shared = rng.normal(0, 0.01, 400)
    book = {"GER40": _Bars(_walk(2, shared=shared, weight=0.95)),
            "FRA40": _Bars(_walk(3, shared=shared, weight=0.95))}
    res = _client(book).get("/api/analysis/correlation")
    assert res.status_code == 200
    assert _pair(res, "GER40", "FRA40")["r"] > 0.8


def test_independent_symbols_read_as_uncorrelated():
    book = {"GER40": _Bars(_walk(11)), "XAUUSD": _Bars(_walk(12))}
    res = _client(book, groups={"XAUUSD": "commodity"}).get("/api/analysis/correlation")
    assert abs(_pair(res, "GER40", "XAUUSD")["r"]) < 0.3


def test_an_inverse_pair_is_reported_as_negative_and_ranked_high():
    rng = np.random.default_rng(7)
    shared = rng.normal(0, 0.01, 400)
    book = {"A": _Bars(_walk(8, shared=shared, weight=0.95)),
            "B": _Bars(_walk(9, shared=-shared, weight=0.95))}
    res = _client(book).get("/api/analysis/correlation")
    pair = _pair(res, "A", "B")
    assert pair["r"] < -0.8
    # Ranked by absolute value: an inverse pair is just as much a concentration.
    assert res.json()["pairs"][0]["r"] == pair["r"]
    assert pair in res.json()["high_pairs"]


def test_prices_are_not_correlated_directly():
    """Two unrelated upward drifts must not report as one bet."""
    n = 400
    book = {"A": _Bars(100 + np.arange(n) * 0.5 + np.random.default_rng(4).normal(0, 2, n)),
            "B": _Bars(200 + np.arange(n) * 0.9 + np.random.default_rng(5).normal(0, 3, n))}
    res = _client(book).get("/api/analysis/correlation")
    assert abs(_pair(res, "A", "B")["r"]) < 0.3


def test_disabled_symbols_are_excluded():
    book = {"ON": _Bars(_walk(21)), "OFF": _Bars(_walk(22))}
    res = _client(book, enabled={"OFF": False}).get("/api/analysis/correlation")
    assert res.json()["symbols"] == ["ON"]
    assert res.json()["pairs"] == []


def test_a_symbol_without_enough_bars_is_skipped_not_fatal():
    book = {"GOOD": _Bars(_walk(31)), "SHORT": _Bars(_walk(32, n=20))}
    res = _client(book).get("/api/analysis/correlation")
    assert res.status_code == 200
    assert "SHORT" in res.json()["skipped"]
    assert res.json()["symbols"] == ["GOOD"]


def test_a_symbol_with_no_bars_at_all_is_skipped():
    class _NoBars(_Client):
        def bars(self, symbol, timeframe, count):
            return None if symbol == "DEAD" else self.book.get(symbol)

    store = _Store([SymbolConfig(symbol="GOOD", magic=1),
                    SymbolConfig(symbol="DEAD", magic=2)])
    tc = TestClient(create_app(store, _NoBars({"GOOD": _Bars(_walk(41))}),
                               _Engine(), _Optimizer()))
    res = tc.get("/api/analysis/correlation")
    assert res.status_code == 200
    assert "DEAD" in res.json()["skipped"]


def test_a_flat_series_does_not_divide_by_zero():
    book = {"FLAT": _Bars(np.full(400, 100.0)), "MOVES": _Bars(_walk(51))}
    res = _client(book).get("/api/analysis/correlation")
    assert res.status_code == 200
    assert all(np.isfinite(p["r"]) for p in res.json()["pairs"])


def test_a_non_positive_price_does_not_produce_nan():
    close = _walk(61)
    close[100:110] = 0.0
    book = {"BROKEN": _Bars(close), "OK": _Bars(_walk(62))}
    res = _client(book).get("/api/analysis/correlation")
    assert res.status_code == 200
    for p in res.json()["pairs"]:
        assert np.isfinite(p["r"])


def test_a_disconnected_client_refuses_rather_than_guessing():
    class _Down(_Client):
        connected = False

    store = _Store([SymbolConfig(symbol="A", magic=1)])
    tc = TestClient(create_app(store, _Down({}), _Engine(), _Optimizer()))
    assert tc.get("/api/analysis/correlation").status_code == 503


def test_an_unknown_timeframe_falls_back_rather_than_failing():
    book = {"A": _Bars(_walk(71)), "B": _Bars(_walk(72))}
    res = _client(book).get("/api/analysis/correlation?timeframe=ZZ")
    assert res.status_code == 200
    assert res.json()["timeframe"] == "H1"


# --------------------------------------- judging a symbol that is not ours yet

def test_a_candidate_can_be_measured_without_being_added():
    """Adding then removing a symbol destroys its opt_runs history, so a
    candidate has to be judgeable from outside the book."""
    book = {"GER40": _Bars(_walk(81)), "CA60": _Bars(_walk(82))}
    store = _Store([SymbolConfig(symbol="GER40", magic=1)])
    tc = TestClient(create_app(store, _Client(book), _Engine(), _Optimizer()))
    res = tc.get("/api/analysis/correlation?extra=CA60")
    assert res.status_code == 200
    assert set(res.json()["symbols"]) == {"GER40", "CA60"}
    assert res.json()["candidates"] == ["CA60"]
    _pair(res, "GER40", "CA60")


def test_a_candidate_that_duplicates_the_book_shows_it():
    rng = np.random.default_rng(91)
    shared = rng.normal(0, 0.01, 400)
    book = {"US500": _Bars(_walk(92, shared=shared, weight=0.95)),
            "US400": _Bars(_walk(93, shared=shared, weight=0.95))}
    store = _Store([SymbolConfig(symbol="US500", magic=1)])
    tc = TestClient(create_app(store, _Client(book), _Engine(), _Optimizer()))
    res = tc.get("/api/analysis/correlation?extra=US400")
    assert _pair(res, "US500", "US400")["r"] > 0.8


def test_several_candidates_at_once():
    book = {"GER40": _Bars(_walk(101)), "A": _Bars(_walk(102)),
            "B": _Bars(_walk(103))}
    store = _Store([SymbolConfig(symbol="GER40", magic=1)])
    tc = TestClient(create_app(store, _Client(book), _Engine(), _Optimizer()))
    res = tc.get("/api/analysis/correlation?extra=A,B")
    assert sorted(res.json()["candidates"]) == ["A", "B"]


def test_a_candidate_the_broker_does_not_know_is_skipped():
    class _Partial(_Client):
        def bars(self, symbol, timeframe, count):
            return self.book.get(symbol)

    store = _Store([SymbolConfig(symbol="GER40", magic=1)])
    tc = TestClient(create_app(store, _Partial({"GER40": _Bars(_walk(111))}),
                               _Engine(), _Optimizer()))
    res = tc.get("/api/analysis/correlation?extra=YOKBOYLESEMBOL")
    assert res.status_code == 200
    assert "YOKBOYLESEMBOL" in res.json()["skipped"]


def test_a_duplicate_or_blank_extra_is_ignored():
    book = {"GER40": _Bars(_walk(121))}
    store = _Store([SymbolConfig(symbol="GER40", magic=1)])
    tc = TestClient(create_app(store, _Client(book), _Engine(), _Optimizer()))
    res = tc.get("/api/analysis/correlation?extra=GER40, ,,")
    assert res.json()["symbols"] == ["GER40"]
    assert res.json()["candidates"] == []


# ------------------------------ different session lengths must not fake a zero

def _stamped(close, step_sec, start=0):
    b = _Bars(close)
    b.time = (start + np.arange(b.close.size, dtype=np.int64) * step_sec)
    return b


def test_two_symbols_on_different_session_lengths_still_align():
    """The bug this replaced: last-N-bars alignment compared different weeks.

    Both series are driven by the same shocks on the hours they share, but one
    only quotes every other hour - so position alignment slides them apart.
    """
    rng = np.random.default_rng(301)
    shared = rng.normal(0, 0.01, 800)
    dense_close = 100 * np.exp(np.cumsum(shared))
    dense = _stamped(dense_close, 3600)
    # Same instrument sampled every 2nd hour: identical path, half the bars.
    sparse = _stamped(dense_close[::2], 7200)

    store = _Store([SymbolConfig(symbol="DENSE", magic=1)])
    tc = TestClient(create_app(store, _Client({"DENSE": dense, "SPARSE": sparse}),
                               _Engine(), _Optimizer()))
    res = tc.get("/api/analysis/correlation?extra=SPARSE")
    pair = _pair(res, "DENSE", "SPARSE")
    # Every shared timestamp carries the same underlying move.
    assert pair["r"] > 0.5, f"zaman hizalamasi calismiyor: {pair}"
    assert pair["bars"] <= sparse.close.size


def test_pairs_with_no_overlapping_bars_are_dropped_not_invented():
    a = _stamped(_walk(311), 3600, start=0)
    b = _stamped(_walk(312), 3600, start=10_000_000)
    store = _Store([SymbolConfig(symbol="A", magic=1)])
    tc = TestClient(create_app(store, _Client({"A": a, "B": b}),
                               _Engine(), _Optimizer()))
    res = tc.get("/api/analysis/correlation?extra=B")
    assert res.status_code == 200
    assert res.json()["pairs"] == []


def test_the_shared_count_is_the_overlap_not_the_shorter_series():
    a = _stamped(_walk(321, n=400), 3600, start=0)
    b = _stamped(_walk(322, n=400), 3600, start=200 * 3600)   # half overlap
    store = _Store([SymbolConfig(symbol="A", magic=1)])
    tc = TestClient(create_app(store, _Client({"A": a, "B": b}),
                               _Engine(), _Optimizer()))
    pair = _pair(tc.get("/api/analysis/correlation?extra=B"), "A", "B")
    assert 150 <= pair["bars"] <= 205, pair["bars"]
