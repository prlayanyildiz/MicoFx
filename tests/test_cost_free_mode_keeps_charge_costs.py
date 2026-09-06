"""Zero-commission must NOT disable live spread charging.

Pepperstone CFDs often ship commission_per_lot=0 while spread is the real
fill cost. Turning charge_costs off made WFO prefer paper-optimal stops
(Claude 03.09 GER40/BTC autopsy; 04.09 income_dev_loop --auto repeat).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.cost_free_mode import apply_cost_free_mode


def test_cost_free_mode_does_not_disable_charge_costs():
    headers = {"Origin": "http://127.0.0.1:8900"}
    state = {
        "system": {
            "charge_costs": True,
            "block_high_cost": True,
            "max_cost_pct_of_risk": 25.0,
        }
    }
    symbols = {
        "symbols": [
            {"symbol": "GER40", "enabled": True, "commission_per_lot": 0.0},
            {"symbol": "US30", "enabled": True, "commission_per_lot": 0.0},
        ]
    }

    def fake_urlopen(req, timeout=20):
        url = getattr(req, "full_url", "") or str(req)
        resp = MagicMock()
        if url.endswith("/api/state"):
            resp.read.return_value = json.dumps(state).encode()
        elif url.endswith("/api/symbols"):
            resp.read.return_value = json.dumps(symbols).encode()
        elif url.endswith("/api/system"):
            raise AssertionError("must not POST /api/system to disable costs")
        else:
            resp.read.return_value = b"{}"
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        lines = apply_cost_free_mode(headers)
    assert any("charge_costs korundu" in x or "dokunulmadi" in x for x in lines)
    assert not any("charge_costs=false" in x for x in lines)
