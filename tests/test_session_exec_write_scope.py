"""session_exec apply payload is sessions-only (Claude 04.09 lockdown)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.session_exec import apply_session_upgrade, best_session_upgrade


def test_best_session_upgrade_uses_charged_net_r_not_paper_only():
    scored = [
        ([{"start": "13:00", "end": "21:00"}],
         {"net_r": 22.8, "profit_factor": 1.17, "trades": 215}),
        ([{"start": "14:00", "end": "22:00"}],
         {"net_r": 32.0, "profit_factor": 1.23, "trades": 222}),
    ]
    pick = best_session_upgrade(
        [{"start": "13:00", "end": "21:00"}], scored, min_delta_r=5.0)
    assert pick is not None
    assert set(pick) >= {
        "sessions", "use_sessions", "net_r", "profit_factor", "live_net_r"}
    assert pick["use_sessions"] is True
    assert "strategy" not in pick
    assert "max_spread_atr" not in pick
    assert "sl_atr_mult" not in pick


def test_apply_session_upgrade_posts_only_sessions_fields():
    row = {
        "symbol": "SpotBrent",
        "strategy": "mtf_pullback",
        "timeframe": "M30",
        "use_sessions": True,
        "sessions": [{"start": "13:00", "end": "21:00"}],
        "max_spread_atr": 0.05,
    }
    pick = {
        "sessions": [{"start": "14:00", "end": "22:00"}],
        "use_sessions": True,
        "net_r": 32.0,
        "live_net_r": 22.8,
        "profit_factor": 1.23,
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
            assert set(body.keys()) <= {"sessions", "use_sessions"}
            assert "strategy" not in body
            assert "max_spread_atr" not in body
        return _Resp()

    with patch("scripts.session_exec.propose_session_upgrade", return_value=pick):
        with patch("urllib.request.urlopen", fake_urlopen):
            ok, msg = apply_session_upgrade(
                {"Origin": "http://127.0.0.1:8900"},
                panel="http://127.0.0.1:8900", row=row)
    assert ok
    assert "14:00-22:00" in msg
    assert posted and set(posted[0]) == {"sessions", "use_sessions"}
