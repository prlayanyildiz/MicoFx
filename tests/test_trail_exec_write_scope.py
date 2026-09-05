"""trail_exec apply payload is trail_step_atr-only."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.trail_exec import apply_trail_upgrade


def test_apply_trail_upgrade_posts_only_trail_step():
    row = {
        "symbol": "JPN225",
        "strategy": "burst",
        "timeframe": "M30",
        "trail_step_atr": 2.8,
        "opt_score": 129.0,
    }
    pick = {
        "trail_step_atr": 3.6,
        "net_r": 158.4,
        "live_net_r": 148.3,
        "live_step": 2.8,
        "profit_factor": 1.72,
    }
    posted: list[dict] = []

    class _Resp:
        def read(self):
            return b'{"ok":true}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        if req.get_method() == "POST":
            body = json.loads(req.data.decode())
            posted.append(body)
            assert body.get("force") is True
            assert set(body["params"]) == {"trail_step_atr"}
            assert "strategy" not in body["params"]
            assert "max_spread_atr" not in body["params"]
            assert "sessions" not in body
        return _Resp()

    with patch("scripts.trail_exec.propose_trail_upgrade", return_value=pick):
        with patch("urllib.request.urlopen", fake_urlopen):
            ok, msg = apply_trail_upgrade(
                {"Origin": "http://127.0.0.1:8900"},
                panel="http://127.0.0.1:8900", row=row)
    assert ok
    assert "3.6" in msg
    assert posted and posted[0]["params"]["trail_step_atr"] == 3.6


def test_apply_trail_start_posts_only_trail_start():
    from scripts.trail_exec import apply_trail_start_upgrade

    row = {
        "symbol": "US30",
        "trail_start_atr": 0.5,
        "trail_step_atr": 2.2,
        "opt_score": 19.0,
    }
    pick = {
        "trail_start_atr": 1.8,
        "net_r": 41.4,
        "live_net_r": 29.4,
        "live_start": 0.5,
        "profit_factor": 1.30,
    }
    posted: list[dict] = []

    class _Resp:
        def read(self):
            return b'{"ok":true}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        if req.get_method() == "POST":
            body = json.loads(req.data.decode())
            posted.append(body)
            assert set(body["params"]) == {"trail_start_atr"}
            assert "trail_step_atr" not in body["params"]
        return _Resp()

    with patch("scripts.trail_exec.propose_trail_start_upgrade", return_value=pick):
        with patch("urllib.request.urlopen", fake_urlopen):
            ok, msg = apply_trail_start_upgrade(
                {"Origin": "http://127.0.0.1:8900"},
                panel="http://127.0.0.1:8900", row=row)
    assert ok and "1.8" in msg
    assert posted[0]["params"]["trail_start_atr"] == 1.8
