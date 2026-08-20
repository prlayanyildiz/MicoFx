"""When every sweep is ok and none validated, the report names no winner.

IDX-1 GER40: six families all ``validated=false``. The consolation branch
then labelled ``st_trend`` (best validation, holdout −0.43 R) as the
search's pick. Apply already required ``validated``, so the live book
would have kept the incumbent — but the report is what got written down.

Fail-first: the named strategy must not be the validation leader, the
holdout leader, or any of the six. ``best`` is None; ``tried`` stays.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_closed_symbol_scan_does_not_apply import _finish_opt, _finish_plan

FAMILIES = (
    ("aroon_flip", 18.5, 12.07, 9.56),
    ("parabolic_flip", 28.58, 24.22, 9.59),
    ("wavetrend_flip", 43.37, -6.57, 13.56),
    ("stoch_flip", 57.6, 256.92, 22.82),
    ("macd_flip", 55.75, 24.12, 9.87),
    ("st_trend", 79.83, -0.43, 16.41),
)


def _unvalidated_plan():
    plan, stamped = _finish_plan(enabled=True)
    attempts = []
    for i, (family, val_r, hold_r, score) in enumerate(FAMILIES):
        row = {
            "ok": True,
            "validated": False,
            "order": i,
            "timeframe": "M30",
            "strategy": family,
            "charge_costs": True,
            "holdout_days": 30.0,
            "best": {
                "score": score,
                "params": {"sl_atr_mult": 1.0 + i * 0.1},
                "selection": dict(plan["attempts"][0]["best"]["selection"]),
                "validation": {
                    **plan["attempts"][0]["best"]["validation"],
                    "net_r": val_r,
                    "score": val_r,
                    "profit_factor": 1.05,
                },
                "holdout": {
                    **plan["attempts"][0]["best"]["holdout"],
                    "net_r": hold_r,
                    "profit_factor": 1.05 if hold_r > 0 else 0.9,
                },
                "positive_ratio": 0.8,
            },
        }
        attempts.append(row)
    plan["attempts"] = attempts
    return plan, stamped


def test_six_ok_unvalidated_attempts_do_not_name_a_winner():
    opt, store = _finish_opt()
    plan, stamped = _unvalidated_plan()
    store.symbols[plan["cfg"].symbol] = plan["cfg"]
    before = dict(plan["cfg"].opt_summary)

    report = opt._finish_symbol(plan, apply_best=True)

    assert report["ok"] is True
    assert report["best"] is None
    assert report.get("strategy") not in {f[0] for f in FAMILIES}
    assert report.get("keep_reason") == "hicbir aday kapidan gecmedi"
    assert report.get("applied") is False
    assert report.get("validated") is False
    tried = report["tried"]
    assert len(tried) == 6
    assert {t["strategy"] for t in tried} == {f[0] for f in FAMILIES}
    assert all(t["ok"] and not t["validated"] for t in tried)
    assert store.symbols["JPN225"].opt_summary == before == stamped
    payload = store.runs[-1]["payload"]
    assert payload["strategy"] is None
    assert payload["keep_reason"] == "hicbir aday kapidan gecmedi"
    assert payload["validated"] is False
    assert len(payload["tried"]) == 6


def test_pick_by_validation_refuses_an_unvalidated_pool():
    opt, _ = _finish_opt()
    plan, _ = _unvalidated_plan()
    with pytest.raises(ValueError, match="validated kume bos"):
        opt._pick_by_validation(plan["attempts"])
