"""xau_hybrid_sl_review — gate table, never lands."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.xau_hybrid_sl_review import markdown_table, review_sl


def test_review_keeps_live_when_no_upgrade():
    row = {
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "sl_atr_mult": 0.5,
        "strategy": "mtf_pullback",
        "use_sessions": False,
    }
    live_nets = [10.0, 20.0, 30.0, 40.0, 50.0, 250.0]
    chal_worse = [5.0, 5.0, 5.0, 5.0, 5.0, 100.0]

    def fake_slices(r, field=None, value=None, parts=6):
        if field == "sl_atr_mult" and value is not None and abs(float(value) - 0.5) > 1e-9:
            return chal_worse
        return live_nets

    scored = {
        0.5: {"net_r": 260.0, "profit_factor": 1.3, "trades": 100},
        0.7: {"net_r": 250.0, "profit_factor": 1.4, "trades": 90},
        0.8: {"net_r": 180.0, "profit_factor": 1.3, "trades": 80},
        1.0: {"net_r": 140.0, "profit_factor": 1.2, "trades": 70},
    }
    with (
        patch("scripts.xau_hybrid_sl_review.score_sl", return_value=scored),
        patch("scripts.xau_hybrid_sl_review.charged_slice_nets", side_effect=fake_slices),
        patch("scripts.xau_hybrid_sl_review.pipeline_frozen", return_value=True),
    ):
        rep = review_sl(row, autopsy_rows=[])
    assert rep["land_allowed"] is False
    assert rep["best_gated"] is None
    assert "keep sl=0.5" in rep["verdict"]
    assert "0.5" in markdown_table(rep)


def test_gated_still_no_land_when_premature_short():
    row = {"symbol": "XAUUSD", "timeframe": "M15", "sl_atr_mult": 0.5}
    live_nets = [10.0, 10.0, 10.0, 10.0, 10.0, 100.0]
    chal = [12.0, 12.0, 12.0, 12.0, 12.0, 120.0]  # +40 full, same wins

    def fake_slices(r, field=None, value=None, parts=6):
        if field == "sl_atr_mult" and value is not None and abs(float(value) - 0.7) < 1e-9:
            return chal
        return live_nets

    scored = {
        0.5: {"net_r": 100.0, "profit_factor": 1.2, "trades": 50},
        0.7: {"net_r": 150.0, "profit_factor": 1.3, "trades": 45},
        0.8: None,
        1.0: None,
    }
    with (
        patch("scripts.xau_hybrid_sl_review.score_sl", return_value=scored),
        patch("scripts.xau_hybrid_sl_review.charged_slice_nets", side_effect=fake_slices),
        patch("scripts.xau_hybrid_sl_review.pipeline_frozen", return_value=True),
        patch(
            "scripts.xau_hybrid_sl_review.premature_sl_count_from_autopsy",
            return_value=2,
        ),
    ):
        rep = review_sl(row, autopsy_rows=[{"symbol": "XAUUSD"}])
    assert rep["best_gated"] is not None
    assert rep["best_gated"]["sl"] == 0.7
    assert rep["premature_ok"] is False
    assert "premature" in rep["verdict"]
    assert rep["land_allowed"] is False
