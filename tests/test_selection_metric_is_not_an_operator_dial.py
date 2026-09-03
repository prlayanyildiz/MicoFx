"""selection_metric stays off the panel; co-lead may set it over the API.

Claude 03.09 Fix B: charged expectancy ranking (`costed_e`) after GER40's
charged-optimal cell was missed three times under gap_freq/cost-free search.
The panel still must not offer a dial operators cannot measure; the API write
is the co-lead / measurement door. Shipped default follows the evidence.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.backtest import SELECTION_METRICS
from micofx.models import SymbolConfig, SystemConfig
from micofx.web.app import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_the_panel_does_not_offer_it():
    app_js = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert "selection_metric" not in app_js, (
        "panelden kaldirildi - operatörün ayarlayacagi bir sey degil")


def test_shipped_default_is_costed_e_after_ger40_evidence():
    assert "costed_e" in SELECTION_METRICS
    data = json.loads((ROOT / "config" / "defaults.json").read_text(encoding="utf-8"))
    assert data["optimizer"].get("selection_metric") == "costed_e"


class _Store:
    def __init__(self):
        self.system = SystemConfig()
        self.symbols = {"XAUUSD": SymbolConfig(symbol="XAUUSD", magic=1)}
        self.defaults = {"symbols": [], "group_presets": {}}
        self.saved = None

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {"selection_metric": "gap_freq", "timeframes": ["M15", "M30"]}

    def save_opt_params(self, params):
        self.saved = params
        return params

    def update_system(self, patch, source=""):
        return self.system


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


def test_api_accepts_costed_e_write():
    store = _Store()
    app = create_app(store, _Client(), _Engine(), optimizer=None)
    tc = TestClient(app)
    res = tc.post("/api/opt/params", json={"selection_metric": "costed_e"})
    assert res.status_code == 200, res.text
    assert store.saved["selection_metric"] == "costed_e"
