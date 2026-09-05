"""Supervisor autopsy recent-exp watch (Claude 04.35 gap fill)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, Supervisor


def _sup(autopsies: list[dict]) -> Supervisor:
    store = MagicMock()
    store.symbols = {
        "NAS100": SymbolConfig(
            symbol="NAS100", magic=1, enabled=True,
            strategy="mtf_pullback", timeframe="M30",
        ),
    }
    store.get_setting = MagicMock(return_value=autopsies)
    store.system = MagicMock()
    client = MagicMock()
    client.connected = True
    return Supervisor(store, client)


def test_autopsy_recent_exp_r_mean():
    rows = [
        {"symbol": "NAS100", "r_realised": -0.5},
        {"symbol": "NAS100", "r_realised": -0.6},
        {"symbol": "XAUUSD", "r_realised": 2.0},
        {"symbol": "NAS100", "r_realised": -0.4},
    ]
    sup = _sup(rows)
    exp, n = sup._autopsy_recent_exp_r("NAS100", n=10)
    assert n == 3
    assert abs(exp - (-0.5)) < 1e-9


def test_judge_watches_on_autopsy_exp_bleed():
    """Empty deal window + autopsy exp < -0.30 → watch (not idle)."""
    autos = [
        {"symbol": "NAS100", "r_realised": -0.5 + (i % 3) * -0.05}
        for i in range(10)
    ]
    sup = _sup(autos)
    cfg = next(iter(sup.store.symbols.values()))
    v = sup._judge(cfg, trades=[], cfgs=dict(DEFAULTS))
    assert v.state == "watch"
    assert "otopsi" in (v.reason or "")
    assert v.risk_scale < 1.0


def test_judge_idle_when_autopsy_exp_healthy():
    autos = [{"symbol": "NAS100", "r_realised": 0.2} for _ in range(10)]
    sup = _sup(autos)
    cfg = next(iter(sup.store.symbols.values()))
    v = sup._judge(cfg, trades=[], cfgs=dict(DEFAULTS))
    assert v.state == "idle"
