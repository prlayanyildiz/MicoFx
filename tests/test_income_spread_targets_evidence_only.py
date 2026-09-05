"""income_dev_loop spread auto must not target every flat symbol (NAS 04.09)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.income_dev_loop import apply_trust_entries, spread_calib_targets


def test_spread_calib_targets_evidence_only():
    report = {
        "live": {"open_symbols": ["BTCUSD"]},
        "spread_auto": ["US30"],
        "active_symbols": ["US30", "NAS100", "GER40", "SpotBrent", "BTCUSD"],
    }
    assert spread_calib_targets(report) == ["US30"]


def test_spread_calib_targets_skips_open_even_if_listed():
    report = {
        "live": {"open_symbols": ["US30"]},
        "spread_auto": ["US30", "NAS100"],
        "active_symbols": ["US30", "NAS100"],
    }
    assert spread_calib_targets(report) == ["NAS100"]


def test_spread_calibration_skips_when_pipeline_frozen(monkeypatch):
    """Exec freeze must also block income-loop MSA widen (Claude 03:36)."""
    import scripts.income_dev_loop as loop

    monkeypatch.setattr(
        "scripts.exec_gates.pipeline_frozen", lambda: True)
    out = loop.apply_spread_calibration({
        "live": {"opt_busy": False, "mt5_connected": True},
        "spread_auto": ["US30"],
        "ranked": [{"symbol": "US30", "max_spread_atr": 0.08}],
        "active_symbols": ["US30"],
    })
    assert out and "FREEZE" in out[0]


def test_trust_entries_does_not_band_calibrate():
    """Trust mode must not call spread-calibrate (NAS 0.05→0.06 leak)."""
    posts: list[str] = []

    def fake_session():
        return {"Origin": "http://127.0.0.1:8900"}, True

    def fake_post(path, headers, body):
        posts.append(path)
        return True, "{}"

    def fake_get(path, headers):
        return {"system": {"charge_costs": True}}

    with patch("scripts.income_dev_loop._api_session", fake_session):
        with patch("scripts.income_dev_loop._api_post", fake_post):
            with patch("scripts.income_dev_loop._api_get", fake_get):
                out = apply_trust_entries({
                    "live": {"open_symbols": []},
                    "active_symbols": ["US30", "NAS100"],
                })
    assert any("AI trust" in x for x in out)
    assert all("/spread-calibrate" not in p for p in posts)
    assert any("/api/ai/settings" in p for p in posts)
