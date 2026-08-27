"""The 3s /api/state poll must not carry opt.results[].top / baseline.

Claude 27.08: with 3 symbols done, 64% of /api/state was the ranked
top-10 plus the incumbent-replay baseline. app.js never reads either
(renderOptJob uses best / incumbent / keep_reason). Serialize happens
on the bot process that also holds the MT5 lock. The live job still
keeps the full rows for opt_runs.
"""
from __future__ import annotations

import re
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def _opt():
    opt = Optimizer.__new__(Optimizer)
    opt._lock = threading.RLock()
    opt._thread = None
    opt.job = {
        "state": "running",
        "results": [{
            "symbol": "GER40",
            "ok": True,
            "best": {"score": 12.0, "params": {"sl_atr_mult": 2.0},
                     "holdout": {"net_r": 180.0}},
            "incumbent": {"net_r": 90.0, "strategy": "stoch_flip"},
            "keep_reason": "mevcut ayar 7 saatlik",
            "validated": True,
            "top": [{"score": i, "params": {}, "holdout": {}, "validation": {}}
                    for i in range(10)],
            "baseline": {"net_r": -4.0, "trades": 100},
        }],
    }
    return opt


def test_panel_js_does_not_read_ranked_top_or_baseline():
    assert re.search(r"\br\.top\b", JS) is None
    assert re.search(r"\bjob\.top\b", JS) is None
    assert "r.baseline" not in JS
    assert "job.baseline" not in JS
    assert re.search(r"\br\.tried\b", JS) is None
    assert "job.tried" not in JS


def test_status_drops_top_and_baseline_without_touching_the_job():
    opt = _opt()
    opt.job["results"][0]["tried"] = [{"strategy": "stoch_flip"}] * 6
    got = opt.status()
    row = got["results"][0]
    assert "top" not in row
    assert "baseline" not in row
    assert "tried" not in row
    assert row["best"]["score"] == 12.0
    assert row["incumbent"]["net_r"] == 90.0
    assert row["keep_reason"].startswith("mevcut ayar")
    stored = opt.job["results"][0]
    assert len(stored["top"]) == 10
    assert stored["baseline"]["net_r"] == -4.0
    assert len(stored["tried"]) == 6
