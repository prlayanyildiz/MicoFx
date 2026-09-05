"""body_exec pick + write-scope."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.body_exec import BODY_CANDIDATES, apply_body_upgrade, best_body_upgrade


def test_body_candidates_include_mtf_grid_01():
    """Claude EK23 / Cursor dry-run: 0.1 is the XAU winner; must be searchable."""
    assert 0.1 in BODY_CANDIDATES


def test_best_body_picks_xau_0_3():
    scored = {
        0.0: {"net_r": 245.4, "profit_factor": 1.31, "trades": 1103},
        0.25: {"net_r": 251.5, "profit_factor": 1.32, "trades": 1082},
        0.30: {"net_r": 262.8, "profit_factor": 1.34, "trades": 1066},
        0.40: {"net_r": 257.1, "profit_factor": 1.35, "trades": 1018},
    }
    pick = best_body_upgrade(0.0, scored, min_delta_r=5.0)
    assert pick is not None
    assert pick["min_body_ratio"] == 0.3


def test_apply_body_posts_only_field():
    pick = {
        "min_body_ratio": 0.3,
        "net_r": 262.8,
        "live_net_r": 245.4,
        "live_body": 0.0,
        "profit_factor": 1.34,
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
        assert set(body["params"]) == {"min_body_ratio"}
        return _Resp()

    with patch("scripts.body_exec.propose_body_upgrade", return_value=pick):
        with patch("urllib.request.urlopen", fake_urlopen):
            ok, msg = apply_body_upgrade(
                {}, panel="http://127.0.0.1:8900",
                row={"symbol": "XAUUSD", "min_body_ratio": 0.0, "opt_score": 200})
    assert ok and "0.3" in msg
    assert posted[0]["force"] is True
