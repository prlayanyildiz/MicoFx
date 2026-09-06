"""atr_pct_exec: GER40 0.2 peak + write-scope."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.atr_pct_exec import apply_atr_pct_upgrade, best_atr_pct_upgrade


def test_best_atr_pct_picks_ger_0_2():
    scored = {
        0.0: {"net_r": 73.8, "profit_factor": 1.34, "trades": 373},
        0.15: {"net_r": 78.9, "profit_factor": 1.42, "trades": 332},
        0.20: {"net_r": 82.1, "profit_factor": 1.46, "trades": 316},
        0.25: {"net_r": 67.3, "profit_factor": 1.42, "trades": 291},
    }
    pick = best_atr_pct_upgrade(0.0, scored, min_delta_r=5.0)
    assert pick is not None
    assert pick["atr_pct_min"] == 0.2


def test_apply_atr_pct_posts_only_field():
    pick = {
        "atr_pct_min": 0.2,
        "net_r": 82.1,
        "live_net_r": 73.8,
        "live_atr_pct": 0.0,
        "profit_factor": 1.46,
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
        body = json.loads(req.data.decode())
        posted.append(body)
        assert set(body["params"]) == {"atr_pct_min"}
        return _Resp()

    with patch("scripts.atr_pct_exec.propose_atr_pct_upgrade", return_value=pick):
        with patch("urllib.request.urlopen", fake_urlopen):
            ok, msg = apply_atr_pct_upgrade(
                {}, panel="http://127.0.0.1:8900",
                row={"symbol": "GER40", "atr_pct_min": 0.0, "opt_score": 58})
    assert ok and "0.2" in msg
    assert posted[0]["force"] is True
