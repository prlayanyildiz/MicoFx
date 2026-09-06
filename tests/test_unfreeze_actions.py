"""unfreeze_actions — plan surfaces day25 checklist."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import unfreeze_actions as ua


def test_plan_includes_day25_checklist(tmp_path):
    payload = {
        "phase": "idle_until_25",
        "axes": {"exit": "CLOSED"},
        "readiness": {
            "frozen": True,
            "baseline_new": 6,
            "baseline_target": 25,
            "ready_to_execute": False,
        },
        "day_of_25_when_ready": ["safety@25"],
        "latest_close": {"symbol": "NAS100", "ticket": 324938232},
    }
    (tmp_path / "UNFREEZE_DAY25_CHECKLIST.json").write_text(
        json.dumps(payload), encoding="utf-8")
    with patch.object(ua, "BRIDGE", tmp_path), patch.object(
        ua, "readiness", return_value={
            "frozen": True,
            "baseline_new": 6,
            "baseline_target": 25,
            "ready_to_execute": False,
            "baseline": {},
        }
    ), patch.object(ua, "load_action_queues", return_value=[]):
        rep = ua.plan()
    d25 = rep["day25_checklist"]
    assert d25["phase"] == "idle_until_25"
    assert d25["baseline_new"] == 6
    assert d25["latest_close"]["symbol"] == "NAS100"
    assert d25["axes"]["exit"] == "CLOSED"


def test_plan_xau_resolved_keep_not_auto(tmp_path):
    """Claude 01:14 — RESOLVED_KEEP must never auto-apply on unfreeze."""
    with patch.object(ua, "BRIDGE", tmp_path), patch.object(
        ua, "readiness", return_value={
            "frozen": False,
            "baseline_new": 25,
            "baseline_target": 25,
            "ready_to_execute": True,
            "baseline": {},
        }
    ), patch.object(ua, "load_action_queues", return_value=[{
        "_path": "XAU_MIN_BODY_APPLY_QUEUE.json",
        "status": "RESOLVED_KEEP_0.3",
        "summary": "KEEP live 0.3",
        "symbol": "XAUUSD",
        "challenger": 0.1,
        "field": "min_body_ratio",
        "when": "blocked_until_unfreeze",
    }]), patch.object(ua, "load_day25_checklist", return_value={}):
        rep = ua.plan()
    acts = [a for a in rep["actions"] if a["_path"].startswith("XAU_MIN_BODY")]
    assert len(acts) == 1
    assert acts[0]["auto_on_unfreeze"] is False
    assert "KEEP" in acts[0]["intent"]


def test_execute_skips_when_no_auto_actions():
    """--execute must not call body_exec when board has zero auto rows."""
    fake_plan = {
        "readiness": {
            "frozen": False,
            "baseline_new": 25,
            "baseline_target": 25,
            "ready_to_execute": True,
        },
        "actions": [{
            "_path": "XAU_MIN_BODY_APPLY_QUEUE.json",
            "status": "RESOLVED_KEEP_0.3",
            "intent": "KEEP live min_body",
            "auto_on_unfreeze": False,
        }],
        "day25_checklist": {},
    }
    with patch.object(ua, "plan", return_value=fake_plan), patch(
        "scripts.body_exec.apply_body_upgrade"
    ) as apply_mock, patch("sys.argv", ["unfreeze_actions", "--execute"]):
        assert ua.main() == 0
    apply_mock.assert_not_called()
