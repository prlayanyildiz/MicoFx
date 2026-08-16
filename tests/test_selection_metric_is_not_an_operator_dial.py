"""The metric is an instrument, not a control the operator is asked to set.

It was added to answer whether `score` picks the wrong winner. Three pieces of
evidence for that said yes and then died under a fair search, so the default did
not move and there is nothing here for an operator to decide - a dial that
cannot be set correctly without a measurement is a way to break a working book.

It stays reachable over the API so the question can still be measured: run the
same symbols under each metric with apply_best=False and compare. If one ever
wins on live results, the default changes in code and the operator is told.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROOT = Path(__file__).resolve().parents[1]


def test_the_panel_does_not_offer_it():
    app_js = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert "selection_metric" not in app_js, (
        "panelden kaldirildi - operatörün ayarlayacagi bir sey degil")


def test_the_setting_still_exists_server_side():
    from micofx.backtest import SELECTION_METRICS

    assert "score" in SELECTION_METRICS
    for name in ("money_per_day", "gap_freq", "costed_e"):
        assert name in SELECTION_METRICS, f"{name} olcum icin erisilebilir kalmali"


def test_the_shipped_default_is_still_score():
    data = json.loads((ROOT / "config" / "defaults.json").read_text(encoding="utf-8"))
    assert data["optimizer"].get("selection_metric", "score") == "score", (
        "varsayilan degismedi: eski siralamanin yanlis oldugu kanitlanmadi")
