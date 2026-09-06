"""msa_exec apply posts only max_spread_atr (Claude lockdown class)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.msa_exec import apply_msa_upgrade


def test_apply_msa_upgrade_posts_only_max_spread_atr():
    row = {
        "symbol": "NAS100",
        "strategy": "burst",
        "timeframe": "M30",
        "max_spread_atr": 0.06,
        "opt_score": 63.5,
    }
    pick = {
        "max_spread_atr": 0.05,
        "live_msa": 0.06,
        "net_r": 103.8,
        "live_net_r": 91.6,
        "profit_factor": 1.35,
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
            assert body.get("params") == {"max_spread_atr": 0.05}
            assert body.get("force") is True
            assert "strategy" not in body or body.get("strategy") is None
        return _Resp()

    with patch("scripts.msa_exec.propose_msa_upgrade", return_value=pick):
        with patch("urllib.request.urlopen", fake_urlopen):
            ok, msg = apply_msa_upgrade(
                {"Origin": "http://127.0.0.1:8900"},
                panel="http://127.0.0.1:8900", row=row)
    assert ok
    assert "0.06->0.05" in msg
    assert posted and posted[0]["params"] == {"max_spread_atr": 0.05}
