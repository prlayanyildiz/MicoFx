"""cost_rank_exec: NAS 0.4 peak + write-scope."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.cost_rank_exec import apply_cost_rank_upgrade, best_cost_rank_upgrade


def test_best_cost_rank_picks_nas_0_4():
    scored = {
        0.3: {"net_r": 64.2, "profit_factor": 1.17, "trades": 539},
        0.4: {"net_r": 118.6, "profit_factor": 1.31, "trades": 551},
        0.5: {"net_r": 103.8, "profit_factor": 1.27, "trades": 559},
        0.7: {"net_r": 88.5, "profit_factor": 1.23, "trades": 564},
    }
    pick = best_cost_rank_upgrade(0.5, scored, min_delta_r=5.0)
    assert pick is not None
    assert pick["cost_rank_max"] == 0.4


def test_best_cost_rank_keeps_live():
    scored = {
        0.2: {"net_r": 154.0, "profit_factor": 1.73, "trades": 314},
        0.3: {"net_r": 158.4, "profit_factor": 1.72, "trades": 332},
        0.4: {"net_r": 138.4, "profit_factor": 1.60, "trades": 344},
    }
    assert best_cost_rank_upgrade(0.3, scored, min_delta_r=5.0) is None


def test_apply_cost_rank_posts_only_cost_rank():
    row = {"symbol": "NAS100", "cost_rank_max": 0.5, "opt_score": 63.0}
    pick = {
        "cost_rank_max": 0.4,
        "net_r": 118.6,
        "live_net_r": 103.8,
        "live_cr": 0.5,
        "profit_factor": 1.31,
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
            assert set(body["params"]) == {"cost_rank_max"}
        return _Resp()

    with patch("scripts.cost_rank_exec.propose_cost_rank_upgrade", return_value=pick):
        with patch("urllib.request.urlopen", fake_urlopen):
            ok, msg = apply_cost_rank_upgrade(
                {}, panel="http://127.0.0.1:8900", row=row)
    assert ok and "0.4" in msg
    assert posted[0]["force"] is True
