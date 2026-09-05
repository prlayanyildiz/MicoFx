"""cost_free_mode must not write system cost toggles (04.09 --auto damage)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _load():
    spec = importlib.util.spec_from_file_location(
        "cost_free_mode", Path(__file__).resolve().parents[1] / "scripts" / "cost_free_mode.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_skips_writes_and_preserves_gates_message():
    mod = _load()
    state = {
        "system": {
            "charge_costs": True,
            "block_high_cost": True,
            "max_cost_pct_of_risk": 25.0,
        },
    }
    symbols = {
        "symbols": [
            {"symbol": "GER40", "enabled": True, "commission_per_lot": 0,
             "strategy": "burst", "timeframe": "M5",
             "max_spread_atr": 0.25, "cost_rank_max": 0.3},
        ],
    }

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return json.dumps(self._payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=0):
        url = req.full_url
        if url.endswith("/api/state"):
            return _Resp(state)
        if url.endswith("/api/symbols"):
            return _Resp(symbols)
        raise AssertionError(f"unexpected write url {url}")

    with patch("urllib.request.urlopen", fake_urlopen):
        lines = mod.apply_cost_free_mode({"Origin": "http://127.0.0.1:8900"})
    assert any("charge_costs korundu" in x or "dokunulmadi" in x for x in lines)
    assert any("gate korunur" in x for x in lines)
    assert not any("charge_costs=false" in x for x in lines)
