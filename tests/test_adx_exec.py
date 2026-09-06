"""adx_exec pick + write-scope."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.adx_exec import apply_adx_upgrade, best_adx_upgrade


def test_best_adx_picks_nas_15():
    scored = {
        0.0: {"net_r": 118.6, "profit_factor": 1.31, "trades": 551},
        12.0: {"net_r": 123.1, "profit_factor": 1.33, "trades": 538},
        15.0: {"net_r": 127.8, "profit_factor": 1.36, "trades": 512},
        18.0: {"net_r": 104.6, "profit_factor": 1.34, "trades": 453},
    }
    pick = best_adx_upgrade(0.0, scored, min_delta_r=5.0)
    assert pick is not None
    assert pick["adx_min"] == 15.0


def test_best_adx_keeps_ger():
    scored = {
        0.0: {"net_r": 72.7, "profit_factor": 1.29, "trades": 422},
        15.0: {"net_r": 73.8, "profit_factor": 1.34, "trades": 373},
        18.0: {"net_r": 34.5, "profit_factor": 1.17, "trades": 335},
    }
    assert best_adx_upgrade(15.0, scored, min_delta_r=5.0) is None


def test_apply_adx_posts_only_adx_min():
    row = {"symbol": "NAS100", "adx_min": 0.0, "opt_score": 90.0}
    pick = {
        "adx_min": 15.0,
        "net_r": 127.8,
        "live_net_r": 118.6,
        "live_adx": 0.0,
        "profit_factor": 1.36,
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
            assert set(body["params"]) == {"adx_min"}
            assert body["force"] is True
        return _Resp()

    with patch("scripts.adx_exec.propose_adx_upgrade", return_value=pick):
        with patch("urllib.request.urlopen", fake_urlopen):
            ok, msg = apply_adx_upgrade({}, panel="http://127.0.0.1:8900", row=row)
    assert ok and "15" in msg
