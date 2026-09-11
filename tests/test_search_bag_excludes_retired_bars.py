"""The default WFO bag is M15/M30, and the API refuses a retired bar.

This file replaces ``test_search_includes_m5_by_default`` (05.09), which was
the opposite guard: it asserted ``"M5" in TIMEFRAMES`` and carried the 03.09
bake-off argument for it ("GER40 M5 burst +74 > live channel/M30 +42") in its
own docstring. That case did not survive re-measurement - 0/7 symbols would
pick M5, five outright negative, at +6-32% cost per trade - so the file was
reading as a live argument for a decision that had been reversed.

The plumbing it covered is worth keeping, so only the verdict is inverted:
the shipped bag must equal SEARCH_TIMEFRAMES, the optimizer must not carry a
hard-coded retired fallback, and ``POST /api/opt/params`` must refuse a bag
that is empty or contains only bars nothing searches.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SEARCH_TIMEFRAMES, TIMEFRAMES, SymbolConfig, SystemConfig
from micofx.web.app import create_app
from tests.retired_lexicon import RETIRED_TIMEFRAMES

ROOT = Path(__file__).resolve().parents[1]


def test_no_retired_bar_is_in_the_default_search_bag():
    for tf in RETIRED_TIMEFRAMES:
        assert tf not in TIMEFRAMES, tf
        assert tf not in SEARCH_TIMEFRAMES, tf
    assert SEARCH_TIMEFRAMES == ["M15", "M30"]


def test_shipped_search_bag_matches_search_timeframes():
    defaults = json.loads(
        (ROOT / "config" / "defaults.json").read_text(encoding="utf-8"))
    assert defaults["optimizer"]["timeframes"] == SEARCH_TIMEFRAMES


def test_optimizer_has_no_hard_coded_retired_fallback():
    """An empty stored blob must fall back to SEARCH_TIMEFRAMES, not a literal.

    A hard-coded ``["M5"]`` here would reopen the bar without anyone editing
    models.py or defaults.json - the cheapest resurrection path of all.
    """
    src = (ROOT / "micofx" / "optimizer.py").read_text(encoding="utf-8")
    assert "or SEARCH_TIMEFRAMES" in src
    tail = src.split("timeframes =", 1)[1][:400]
    for tf in RETIRED_TIMEFRAMES:
        assert f'or ["{tf}"]' not in tail, tf


class _Store:
    def __init__(self):
        self.system = SystemConfig()
        self.symbols = {
            "XAUUSD": SymbolConfig(symbol="XAUUSD", magic=1, enabled=False),
        }
        self.defaults = {"symbols": [], "group_presets": {}}
        self.saved_opt = None

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def save_opt_params(self, params):
        self.saved_opt = params
        return params

    def update_system(self, patch, source=""):
        return self.system

    def update_symbol(self, symbol, patch, source=""):
        return self.symbols[symbol]


class _Client:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, mapping):
        pass

    def info(self, symbol):
        return None


class _Engine:
    def __init__(self):
        self.states = {}
        self.supervisor = None


def _client():
    store = _Store()
    app = create_app(store, _Client(), _Engine(), optimizer=None)
    return TestClient(app), store


def test_opt_params_post_writes_the_live_search_bag():
    tc, store = _client()
    res = tc.post("/api/opt/params", json={"timeframes": ["M15", "M30"]})
    assert res.status_code == 200, res.text
    assert store.saved_opt["timeframes"] == ["M15", "M30"]


def test_opt_params_post_refuses_an_empty_or_retired_bag():
    tc, store = _client()
    assert tc.post("/api/opt/params", json={"timeframes": []}).status_code == 400
    for tf in RETIRED_TIMEFRAMES:
        res = tc.post("/api/opt/params", json={"timeframes": [tf]})
        assert res.status_code == 400, f"{tf} kabul edildi: {res.text}"
    assert store.saved_opt is None


def test_the_panel_offers_exactly_the_bars_the_code_allows():
    """``OPT_TF_OPTIONS`` asked a human to keep two lists in step.

    Operator, 11.09: "m5 opt sayfasinda yok" - correct, and deliberate: the
    comment above that constant says offering a retired bar would let the
    panel set a timeframe the entry gate refuses
    (``strategy_allows_timeframe`` -> ``READABLE_TIMEFRAMES``), i.e. a
    silently dead symbol. It ends "Keep in step with models.TIMEFRAMES", and
    nothing checked that it was. Two hand-maintained lists with a comment
    between them is the same shape as every other drift this file guards.

    Both directions matter. A bar in the panel but not in the code is a dead
    symbol; a bar in the code but not in the panel is a search the operator
    cannot reach - which is exactly how ``strategies`` and
    ``min_positive_ratio`` sat unreachable until 11.09.
    """
    import re

    js = (ROOT / "micofx" / "web" / "static" / "app.js").read_text("utf-8")
    m = re.search(r"const OPT_TF_OPTIONS\s*=\s*\[([^\]]*)\]", js)
    assert m, "OPT_TF_OPTIONS bulunamadi - adi mi degisti?"
    offered = [t.strip().strip('"\'') for t in m.group(1).split(",") if t.strip()]
    assert offered == TIMEFRAMES, (
        f"panel {offered} sunuyor, kod {TIMEFRAMES} kabul ediyor")
    for tf in RETIRED_TIMEFRAMES:
        assert tf not in offered, f"panel emekli bari sunuyor: {tf}"
