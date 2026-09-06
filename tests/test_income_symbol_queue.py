"""income_dev_loop — symbol queue load for postponed adds."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.income_dev_loop import (
    load_action_queues,
    load_day25_checklist,
    load_symbol_queues,
)


def test_load_symbol_queues(tmp_path):
    q = {
        "decision": "SIMDI_HAYIR",
        "symbols": ["UK100", "FRA40"],
        "after": ["25 new closes"],
        "reason": "measured",
    }
    (tmp_path / "SYMBOL_QUEUE_UK100_FRA40.json").write_text(
        json.dumps(q), encoding="utf-8")
    (tmp_path / "noise.txt").write_text("x", encoding="utf-8")
    out = load_symbol_queues(tmp_path)
    assert len(out) == 1
    assert out[0]["symbols"] == ["UK100", "FRA40"]
    assert out[0]["_path"] == "SYMBOL_QUEUE_UK100_FRA40.json"


def test_load_symbol_queues_empty(tmp_path):
    assert load_symbol_queues(tmp_path) == []


def test_load_action_queues(tmp_path):
    (tmp_path / "XAU_MIN_BODY_APPLY_QUEUE.json").write_text(
        json.dumps({
            "status": "measured_ready_after_unfreeze",
            "symbol": "XAUUSD",
            "field": "min_body_ratio",
            "challenger": 0.1,
            "when": "after 25",
            "note": "apply body",
        }),
        encoding="utf-8",
    )
    (tmp_path / "NAS100_SESSION_REEVAL_ONCE.json").write_text(
        json.dumps({"status": "measured_keep_live_15_21",
                    "recommendation": "KEEP 15-21"}),
        encoding="utf-8",
    )
    (tmp_path / "XAU_BE_AT_R_HOLD_ONLY.json").write_text(
        json.dumps({
            "status": "HOLD_ONLY_review",
            "symbol": "XAUUSD",
            "field": "breakeven_at_r",
            "live": 1.5,
            "decision": "KEEP 1.5 until slice also agrees",
            "do_not_apply_now": True,
        }),
        encoding="utf-8",
    )
    out = load_action_queues(tmp_path)
    assert len(out) == 3
    xau = next(a for a in out if a["_path"].startswith("XAU_MIN_BODY"))
    assert xau["challenger"] == 0.1
    assert xau["symbol"] == "XAUUSD"
    be = next(a for a in out if a["_path"].startswith("XAU_BE_AT_R"))
    assert be["status"] == "HOLD_ONLY_review"
    assert be["when"] == "blocked_until_unfreeze"


def test_load_day25_checklist(tmp_path):
    payload = {
        "phase": "idle_until_25",
        "axes": {"exit": "CLOSED", "trail_mechanism": "HEALTHY"},
        "readiness": {
            "frozen": True,
            "baseline_new": 5,
            "baseline_target": 25,
            "ready_to_execute": False,
        },
        "day_of_25_when_ready": [
            "safety@25: catastrophe only",
            "WFO wire after 25",
        ],
        "latest_close": {"symbol": "JPN225", "r": -1.0},
    }
    (tmp_path / "UNFREEZE_DAY25_CHECKLIST.json").write_text(
        json.dumps(payload), encoding="utf-8")
    out = load_day25_checklist(tmp_path)
    assert out["phase"] == "idle_until_25"
    assert out["baseline_new"] == 5
    assert out["baseline_target"] == 25
    assert out["ready_to_execute"] is False
    assert out["axes"]["exit"] == "CLOSED"
    assert len(out["day_of_25_when_ready"]) == 2
    assert out["latest_close"]["symbol"] == "JPN225"


def test_load_day25_checklist_missing(tmp_path):
    assert load_day25_checklist(tmp_path) == {}
