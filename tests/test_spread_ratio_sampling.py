"""The gap between what the search charges for spread and what live enforces.

simulate() gates on the entry BAR's recorded spread:

    spread_price[j0] > atr_entry * p.max_spread_atr   -> skip

_try_entry gates on the CURRENT TICK's:

    tick["spread"] > atr * cfg.max_spread_atr         -> refuse

So a ceiling the search picked against one number is enforced against the
other. That is not theoretical: FRA40's ceiling sat under its own typical
spread and shut all 14 hours of its session, and USDCHF was deleted for the
same thing before it was recognised.

Measured continuously instead of estimated. A spot reading is worthless -
2.5 minutes of one liquid hour put the median at 1.28x while reporting
ratios below 1.0 for symbols whose bar median covers hours the sample never
touched. The bot is awake all session, so it collects the whole distribution
for free, and nothing is reported usable below the sample threshold.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import (SPREAD_RATIO_BUCKETS, SPREAD_RATIO_MIN_SAMPLES,
                           SPREAD_RATIO_STEP, Engine, SymbolState,
                           _ratio_percentile)
from micofx.models import SymbolConfig

POINT = 0.01


class _Bars:
    def __init__(self, spread_points):
        self.spread = np.asarray([spread_points], dtype=np.float64)
        self.close = np.array([100.0])

    def __len__(self):
        return 1


class _Store:
    """Real Store always exposes .symbols; the flush prunes against it."""

    def __init__(self, symbols=None):
        self.saved = {}
        self.symbols = {s: object() for s in
                        (symbols if symbols is not None else
                         ("X", "A", "B", "AYNI", "EURJPY", "UK100", "GER40",
                          "FRA40", "GBPUSD", "NAS100", "BUSY", "QUIET",
                          "KALAN", "US500", "US30"))}
        self.writes = 0

    def get_setting(self, k, d=None):
        return self.saved.get(k, d)

    def set_setting(self, k, v):
        self.writes += 1
        self.saved[k] = v


class _Client:
    def __init__(self, point=POINT):
        self.point = point

    def info(self, symbol):
        return {"point": self.point} if self.point is not None else None


def _engine(store=None, client=None):
    eng = object.__new__(Engine)
    eng.store = store or _Store()
    eng.client = client or _Client()
    eng._spread_ratio = {}
    eng._spread_ratio_dirty = False
    eng._spread_ratio_at = 0.0
    return eng


def _feed(eng, symbol, bar_points, tick_spread, times=1):
    cfg = SymbolConfig(symbol=symbol, magic=1)
    state = SymbolState(symbol)
    state.bars = _Bars(bar_points)
    for _ in range(times):
        eng._sample_spread_ratio(cfg, state, {"spread": tick_spread})


def _row(eng, symbol):
    return next(r for r in eng.spread_ratio()["rows"] if r["symbol"] == symbol)


# ------------------------------------------------------------ measurement

def test_a_tick_matching_the_bar_reads_as_one():
    eng = _engine()
    _feed(eng, "GER40", bar_points=10, tick_spread=10 * POINT, times=500)
    assert _row(eng, "GER40")["median"] == pytest.approx(1.0, abs=0.06)


@pytest.mark.parametrize("factor", [1.3, 2.0, 3.5])
def test_a_wider_tick_reads_as_that_multiple(factor):
    eng = _engine()
    _feed(eng, "FRA40", bar_points=10, tick_spread=10 * POINT * factor, times=500)
    assert _row(eng, "FRA40")["median"] == pytest.approx(factor, abs=0.06)


def test_a_narrower_tick_is_recorded_too():
    """Below 1.0 is a real reading, not an error - it must not be clamped."""
    eng = _engine()
    _feed(eng, "GBPUSD", bar_points=10, tick_spread=5 * POINT, times=500)
    assert _row(eng, "GBPUSD")["median"] == pytest.approx(0.5, abs=0.06)


def test_the_p90_sees_the_tail_the_median_hides():
    """The ceiling has to survive the tail, which is the whole point."""
    eng = _engine()
    _feed(eng, "UK100", bar_points=10, tick_spread=10 * POINT, times=900)
    _feed(eng, "UK100", bar_points=10, tick_spread=30 * POINT, times=200)
    row = _row(eng, "UK100")
    assert row["median"] == pytest.approx(1.0, abs=0.06)
    assert row["p90"] >= 2.5


def test_an_extreme_ratio_lands_in_the_overflow_bucket():
    eng = _engine()
    _feed(eng, "X", bar_points=1, tick_spread=1000 * POINT, times=500)
    assert _row(eng, "X")["median"] >= (SPREAD_RATIO_BUCKETS - 1) * SPREAD_RATIO_STEP


def test_samples_accumulate_per_symbol():
    eng = _engine()
    _feed(eng, "A", 10, 10 * POINT, times=3)
    _feed(eng, "B", 10, 20 * POINT, times=7)
    rows = {r["symbol"]: r for r in eng.spread_ratio()["rows"]}
    assert rows["A"]["samples"] == 3 and rows["B"]["samples"] == 7


# ------------------------------------------- nothing usable on thin evidence

def test_a_thin_sample_is_flagged_not_trusted():
    eng = _engine()
    _feed(eng, "X", 10, 13 * POINT, times=5)
    row = _row(eng, "X")
    assert row["enough"] is False
    assert eng.spread_ratio()["ready"] == 0


def test_the_threshold_is_high_enough_to_outlast_one_hour():
    """A 2s cycle makes 1800 samples an hour; the bar must exceed a spot read."""
    assert SPREAD_RATIO_MIN_SAMPLES >= 100


def test_enough_flips_once_the_threshold_is_cleared():
    eng = _engine()
    _feed(eng, "X", 10, 13 * POINT, times=SPREAD_RATIO_MIN_SAMPLES)
    assert _row(eng, "X")["enough"] is True
    assert eng.spread_ratio()["ready"] == 1


# --------------------------------------------- bad inputs are simply ignored

@pytest.mark.parametrize("tick", [None, {}, {"spread": 0.0}, {"spread": -1.0},
                                  {"spread": float("nan")}])
def test_an_unusable_tick_is_not_counted(tick):
    eng = _engine()
    cfg = SymbolConfig(symbol="X", magic=1)
    state = SymbolState("X")
    state.bars = _Bars(10)
    eng._sample_spread_ratio(cfg, state, tick)
    assert eng.spread_ratio()["rows"] == []


@pytest.mark.parametrize("bar_points", [0.0, -5.0])
def test_a_bar_without_a_spread_is_not_counted(bar_points):
    eng = _engine()
    _feed(eng, "X", bar_points, 10 * POINT)
    assert eng.spread_ratio()["rows"] == []


def test_no_bars_yet_is_not_counted():
    eng = _engine()
    cfg = SymbolConfig(symbol="X", magic=1)
    state = SymbolState("X")
    eng._sample_spread_ratio(cfg, state, {"spread": 0.1})
    assert eng.spread_ratio()["rows"] == []


def test_an_unreadable_point_is_not_counted():
    """Same stance the walk-forward now takes: no guessed price scale."""
    for point in (0.0, None):
        eng = _engine(client=_Client(point=point))
        _feed(eng, "X", 10, 0.1)
        assert eng.spread_ratio()["rows"] == []


def test_a_broken_client_never_reaches_the_cycle():
    class _Boom(_Client):
        def info(self, symbol):
            raise RuntimeError("mt5 dustu")

    eng = _engine(client=_Boom())
    _feed(eng, "X", 10, 0.1)                # must not raise
    assert eng.spread_ratio()["rows"] == []


# ------------------------------------------------------------- persistence

def test_the_histogram_is_not_written_every_cycle():
    """Every symbol samples every cycle; a naive flush writes SQLite at 2s."""
    store = _Store()
    eng = _engine(store)
    _feed(eng, "X", 10, 0.13, times=10)
    for _ in range(50):
        eng._flush_spread_ratio()
    assert store.writes == 1, f"{store.writes} yazma - kisitlama calismiyor"


def test_it_does_write_once_the_interval_passes():
    store = _Store()
    eng = _engine(store)
    _feed(eng, "X", 10, 0.13)
    eng._flush_spread_ratio(interval=0.0)
    assert store.saved["spread_ratio"]["X"]


def test_a_write_failure_never_interrupts_a_cycle():
    class _Broken(_Store):
        def set_setting(self, k, v):
            raise RuntimeError("disk dolu")

    eng = _engine(_Broken())
    _feed(eng, "X", 10, 0.13)
    eng._flush_spread_ratio(interval=0.0)   # must not raise
    assert _row(eng, "X")["samples"] == 1


def test_the_histogram_survives_a_restart():
    store = _Store()
    eng = _engine(store)
    _feed(eng, "X", 10, 13 * POINT, times=600)
    eng._flush_spread_ratio(interval=0.0)

    revived = _engine(store)
    revived._spread_ratio = {
        str(s): [int(v) for v in c][:SPREAD_RATIO_BUCKETS]
        for s, c in store.get_setting("spread_ratio", {}).items()
    }
    assert _row(revived, "X")["samples"] == 600
    assert _row(revived, "X")["median"] == pytest.approx(1.3, abs=0.06)


@pytest.mark.parametrize("blob", [
    {"X": "bozuk"}, {"X": None}, {"X": [1, "iki"]}, {"X": {"a": 1}}, {"X": 5},
])
def test_a_corrupt_histogram_does_not_stop_start_up(blob):
    kept = {
        str(s): [int(v) for v in c][:SPREAD_RATIO_BUCKETS]
        for s, c in blob.items()
        if isinstance(c, (list, tuple))
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in c)
    }
    eng = _engine()
    eng._spread_ratio = kept
    assert eng.spread_ratio()["rows"] == []


# --------------------------------------------------------- the percentile

def test_an_empty_histogram_has_no_percentile():
    assert _ratio_percentile([0] * SPREAD_RATIO_BUCKETS, 0.5) is None


def test_the_percentile_reports_the_bucket_centre():
    """Naming the lower edge would understate every reading by half a bucket."""
    counts = [0] * SPREAD_RATIO_BUCKETS
    counts[13] = 100                      # ratios in [1.3, 1.4)
    assert _ratio_percentile(counts, 0.5) == pytest.approx(1.35, abs=0.001)


def test_the_panel_is_wired_to_the_endpoint():
    """A renamed id leaves the view blank and nothing else notices."""
    web = Path(__file__).resolve().parents[1] / "micofx" / "web"
    js = (web / "static" / "app.js").read_text(encoding="utf-8")
    html = (web / "templates" / "index.html").read_text(encoding="utf-8")

    assert "/api/analysis/spread-ratio" in js
    for element_id in ("ratio-table", "ratio-note", "btn-ratio-refresh"):
        assert f'id="{element_id}"' in html, f"index.html'de {element_id} yok"
        assert f'"#{element_id}"' in js, f"app.js {element_id} kullanmiyor"
    # All three diagnostic views live on the Tani tab and load together.
    assert 'name === "tani"' in js and "loadSpreadRatio()" in js
    for panel in ("gates-table", "blocks-table", "ratio-table"):
        assert html.index(panel) > html.index('id="page-tani"'), \
            f"{panel} Tani sekmesinde degil"


# ------------------------------------------ a deleted symbol leaves no trace

def test_a_deleted_symbol_is_dropped_from_the_histogram():
    """The panel was showing measurements for seven symbols that were gone."""
    store = _Store(symbols=("KALAN",))
    eng = _engine(store)
    _feed(eng, "KALAN", 10, 0.13, times=5)
    _feed(eng, "SILINDI", 10, 0.13, times=5)
    eng._flush_spread_ratio(interval=0.0)
    names = {r["symbol"] for r in eng.spread_ratio()["rows"]}
    assert names == {"KALAN"}
    assert "SILINDI" not in store.saved["spread_ratio"]


def test_the_stale_histogram_cannot_be_reapplied_to_a_fresh_config():
    """_spread_scale looks the histogram up by name; a re-added symbol must
    not inherit a distribution measured under its previous config."""
    store = _Store(symbols=("KALAN",))
    eng = _engine(store)
    _feed(eng, "SILINDI", 10, 30 * POINT, times=SPREAD_RATIO_MIN_SAMPLES)
    eng._flush_spread_ratio(interval=0.0)
    assert store.saved["spread_ratio"].get("SILINDI") is None


# --------------------------- only the hours an entry can actually happen in

def test_sampling_sits_behind_both_gates_in_the_cycle():
    """The measurement must describe what _try_entry's spread gate will see,
    and that gate only runs on an open session with a live feed.

    Taken before those gates it also recorded the hours the symbol never
    trades, and that is not a small perturbation. Measured at 00:01 with every
    session closed, AUDUSD's tick sat at 57x its own ceiling and GBPJPY's at
    59x, against roughly 1.0x during their sessions. This book already moved
    FX off hour 0 because it cost 216% of risk; feeding those hours back into
    the number that prices the search undoes that.

    The weekend is what makes it urgent: Friday close to Sunday open is ~48
    hours of dead-market spread, more samples than a whole trading day.
    """
    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "engine.py").read_text(encoding="utf-8")
    body = src.split("def _evaluate(", 1)[1].split("\n    def ", 1)[0]

    sample_at = body.index("self._sample_spread_ratio(")
    session_gate = body.index("if not sess.open:")
    market_gate = body.index("if not self.client.market_open(")

    assert sample_at > session_gate, "seans kapisindan ONCE ornekleniyor"
    assert sample_at > market_gate, "piyasa kapisindan ONCE ornekleniyor"


def test_it_is_sampled_exactly_once_per_cycle():
    """Two call sites would double-count every reading."""
    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "engine.py").read_text(encoding="utf-8")
    body = src.split("def _evaluate(", 1)[1].split("\n    def ", 1)[0]
    assert body.count("self._sample_spread_ratio(") == 1


def test_the_tick_is_still_in_scope_where_it_is_sampled():
    """It has to be the same instant's tick, not a re-read."""
    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "engine.py").read_text(encoding="utf-8")
    body = src.split("def _evaluate(", 1)[1].split("\n    def ", 1)[0]
    assert body.index("tick = self.client.tick(") < body.index("self._sample_spread_ratio(")
    assert "self._sample_spread_ratio(cfg, state, tick)" in body
