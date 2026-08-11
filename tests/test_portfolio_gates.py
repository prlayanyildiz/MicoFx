"""The pruning gates, in one view, so the failing one is visible before a cut.

Two symbol removals this session were made on the wrong number - one on
productivity that was really a spread ceiling set under the symbol's own
normal spread, three on a month of data collected under a session regime
fixed twenty minutes earlier. This endpoint exists so each gate is stated
separately rather than collapsed into a single verdict.

The cost gate reads holdout ``cost_per_trade_r``, NOT the cost-by-hour
median: that view averages every bar while the walk-forward charges cost only
where a signal fired, so it runs 5-14x higher on short timeframes. Its own
docstring records that comparing its level to a gate has already produced
wrong calls on which symbols are worth trading.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.web.app import create_app


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


class _State:
    def __init__(self, spread_atr=0.0):
        self.spread_atr = spread_atr


class _Supervisor:
    def __init__(self, live):
        self._live = live
        self.settings = {"lookback_days": 30}

    def status(self):
        return {"symbols": [{"symbol": s, "trades": t} for s, t in self._live.items()]}


class _Engine:
    def __init__(self, states, live):
        self.states = states
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}
        self.supervisor = _Supervisor(live)


class _Optimizer:
    MAX_COST_PER_TRADE_R = 0.25

    def apply(self, *a, **k):
        return {"ok": True}


def _cfg(symbol, *, trades, edge, cost_r, ceiling, hold_days=30.0,
         enabled=True, magic=1):
    c = SymbolConfig(symbol=symbol, magic=magic, enabled=enabled)
    c.max_spread_atr = ceiling
    c.opt_summary = {
        "holdout_days": hold_days,
        "holdout": {"trades": trades, "expectancy": edge,
                    "cost_per_trade_r": cost_r},
    }
    return c


def _client(cfgs, states=None, live=None):
    store = _Store(cfgs)
    engine = _Engine(states or {}, live or {})
    return TestClient(create_app(store, _Client(), engine, _Optimizer()))


def _rows(res):
    return {r["symbol"]: r for r in res.json()["rows"]}


# --------------------------------------------------------------- each gate

def test_a_clean_symbol_fails_nothing():
    # n=400, edge 0.30 -> 2SE = 0.12, comfortably measurable
    cfg = _cfg("US30", trades=400, edge=0.30, cost_r=0.05, ceiling=0.12)
    tc = _client([cfg], {"US30": _State(0.05)}, {"US30": 400})
    row = _rows(tc.get("/api/analysis/portfolio-gates"))["US30"]
    assert row["fails"] == []
    assert row["clean"] is True


def test_an_unmeasurable_edge_is_flagged():
    # n=40 -> 2SE = 0.379; an edge of 0.10 is nowhere near it
    cfg = _cfg("CHFJPY", trades=40, edge=0.10, cost_r=0.05, ceiling=0.5)
    tc = _client([cfg], {"CHFJPY": _State(0.05)}, {"CHFJPY": 40})
    row = _rows(tc.get("/api/analysis/portfolio-gates"))["CHFJPY"]
    assert "olculebilir" in row["fails"]
    assert row["sigma"] < 2.0


def test_a_costly_config_is_flagged():
    cfg = _cfg("CADJPY", trades=400, edge=0.30, cost_r=0.40, ceiling=0.5)
    tc = _client([cfg], {"CADJPY": _State(0.05)}, {"CADJPY": 400})
    row = _rows(tc.get("/api/analysis/portfolio-gates"))["CADJPY"]
    assert "maliyet" in row["fails"]
    assert row["cost_ceiling_r"] == 0.25


def test_a_symbol_over_its_own_ceiling_is_flagged():
    """FRA40's disease: the ceiling sits under the symbol's normal spread."""
    cfg = _cfg("FRA40", trades=400, edge=0.30, cost_r=0.05, ceiling=0.05)
    tc = _client([cfg], {"FRA40": _State(0.053)}, {"FRA40": 400})
    row = _rows(tc.get("/api/analysis/portfolio-gates"))["FRA40"]
    assert "tavan" in row["fails"]
    assert row["spread_atr_now"] == 0.053


def test_a_starved_symbol_is_flagged():
    """400 holdout trades over 30 days implies 400 in the window; 4 arrived."""
    cfg = _cfg("UK100", trades=400, edge=0.30, cost_r=0.05, ceiling=0.5)
    tc = _client([cfg], {"UK100": _State(0.05)}, {"UK100": 4})
    row = _rows(tc.get("/api/analysis/portfolio-gates"))["UK100"]
    assert "siklik" in row["fails"]
    assert row["expected_trades"] == 400.0
    assert row["fill_rate"] == 0.01


def test_the_gates_are_independent():
    cfg = _cfg("BAD", trades=40, edge=0.10, cost_r=0.40, ceiling=0.05)
    tc = _client([cfg], {"BAD": _State(0.5)}, {"BAD": 1})
    row = _rows(tc.get("/api/analysis/portfolio-gates"))["BAD"]
    assert set(row["fails"]) == {"olculebilir", "maliyet", "tavan", "siklik"}


# ------------------------------------------------- the reading traps

def test_a_thin_sample_is_called_out_separately():
    """n=30 with a 0.5R edge clears 2 SE while saying very little."""
    cfg = _cfg("US2000", trades=30, edge=0.60, cost_r=0.05, ceiling=0.5)
    tc = _client([cfg], {"US2000": _State(0.05)}, {"US2000": 30})
    res = tc.get("/api/analysis/portfolio-gates")
    row = _rows(res)["US2000"]
    assert "olculebilir" not in row["fails"]      # it passes...
    assert row["thin_sample"] is True             # ...but not on evidence
    assert "US2000" in res.json()["thin_sample"]


def test_a_large_sample_with_a_small_edge_is_not_thin():
    """The opposite trap: n=407 at 0.107R fails 2SE but is precisely known."""
    cfg = _cfg("US30", trades=407, edge=0.107, cost_r=0.05, ceiling=0.5)
    tc = _client([cfg], {"US30": _State(0.05)}, {"US30": 407})
    row = _rows(tc.get("/api/analysis/portfolio-gates"))["US30"]
    assert "olculebilir" in row["fails"]
    assert row["thin_sample"] is False


def test_a_disabled_ceiling_never_fires():
    """max_spread_atr = 0 switches the filter off; it must not read as a fail."""
    cfg = _cfg("X", trades=400, edge=0.30, cost_r=0.05, ceiling=0.0)
    tc = _client([cfg], {"X": _State(9.9)}, {"X": 400})
    row = _rows(tc.get("/api/analysis/portfolio-gates"))["X"]
    assert "tavan" not in row["fails"]


def test_a_disabled_symbol_is_not_judged():
    cfgs = [_cfg("ON", trades=400, edge=0.30, cost_r=0.05, ceiling=0.5, magic=1),
            _cfg("OFF", trades=0, edge=0.0, cost_r=0.0, ceiling=0.5,
                 enabled=False, magic=2)]
    tc = _client(cfgs, {"ON": _State(0.05)}, {"ON": 400})
    assert set(_rows(tc.get("/api/analysis/portfolio-gates"))) == {"ON"}


# ------------------------------------------------------ nothing crashes

def test_a_symbol_with_no_walk_forward_yet_does_not_crash():
    cfg = SymbolConfig(symbol="NEW", magic=3, enabled=True)
    tc = _client([cfg], {}, {})
    row = _rows(tc.get("/api/analysis/portfolio-gates"))["NEW"]
    assert "olculebilir" in row["fails"]
    assert row["needs_r"] is None and row["sigma"] is None
    assert row["expected_trades"] is None and row["fill_rate"] is None


def test_a_missing_engine_state_does_not_crash():
    cfg = _cfg("X", trades=400, edge=0.30, cost_r=0.05, ceiling=0.12)
    tc = _client([cfg], {}, {"X": 400})          # no state entry at all
    row = _rows(tc.get("/api/analysis/portfolio-gates"))["X"]
    assert row["spread_atr_now"] is None
    assert "tavan" not in row["fails"]


def test_a_broken_supervisor_does_not_take_the_view_down():
    class _Boom(_Supervisor):
        def status(self):
            raise RuntimeError("supervisor down")

    store = _Store([_cfg("X", trades=400, edge=0.30, cost_r=0.05, ceiling=0.5)])
    eng = _Engine({"X": _State(0.05)}, {})
    eng.supervisor = _Boom({})
    tc = TestClient(create_app(store, _Client(), eng, _Optimizer()))
    res = tc.get("/api/analysis/portfolio-gates")
    assert res.status_code == 200
    assert _rows(res)["X"]["actual_trades"] == 0


def test_the_panel_is_actually_wired_to_this_endpoint():
    """A renamed id leaves the view silently blank - nothing else catches it."""
    web = Path(__file__).resolve().parents[1] / "micofx" / "web"
    js = (web / "static" / "app.js").read_text(encoding="utf-8")
    html = (web / "templates" / "index.html").read_text(encoding="utf-8")

    assert "/api/analysis/portfolio-gates" in js
    for element_id in ("gates-table", "gates-note", "btn-gates-refresh"):
        assert f'id="{element_id}"' in html, f"index.html'de {element_id} yok"
        assert f'"#{element_id}"' in js, f"app.js {element_id} kullanmiyor"
    # The tab hook, without which the table only ever fills on a manual click.
    assert 'name === "semboller"' in js and "loadGates()" in js


def test_the_gate_labels_cover_every_gate_the_api_emits():
    """A gate added server-side must not render as a raw slug in the panel."""
    js = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static"
          / "app.js").read_text(encoding="utf-8")
    cfg = _cfg("BAD", trades=40, edge=0.10, cost_r=0.40, ceiling=0.05)
    tc = _client([cfg], {"BAD": _State(0.5)}, {"BAD": 1})
    res = tc.get("/api/analysis/portfolio-gates")
    for gate in res.json()["by_gate"]:
        assert f"{gate}:" in js, f"GATE_LABEL'da {gate} yok"


def test_the_thresholds_are_tunable():
    cfg = _cfg("X", trades=400, edge=0.30, cost_r=0.05, ceiling=0.5)
    tc = _client([cfg], {"X": _State(0.05)}, {"X": 200})
    base = tc.get("/api/analysis/portfolio-gates")
    assert "siklik" not in _rows(base)["X"]["fails"]        # 200/400 = 0.5
    tight = tc.get("/api/analysis/portfolio-gates?min_fill_rate=0.8")
    assert "siklik" in _rows(tight)["X"]["fails"]
    wide = tc.get("/api/analysis/portfolio-gates?min_sample=500")
    assert _rows(wide)["X"]["thin_sample"] is True
