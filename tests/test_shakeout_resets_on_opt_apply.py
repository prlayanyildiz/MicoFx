"""Shakeout must not punish a fresh apply with the previous config's SL deaths.

F7: after family/TF/grid apply, opt_updated_at resets the evidence window.
NAS/XAU mtf (10:44) were floored to 2.0 ATR by pre-apply burst SL deaths,
then T1 skipped min-lot on $248 — the +698R edge never opened.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.risk import shakeout_sl_atr_mult


def _sl(symbol: str, n: int, *, exit_time: float,
        reason: str = "sl", r: float = -1.0) -> list[dict]:
    return [{"symbol": symbol, "exit_reason": reason,
             "r_realised": r, "exit_time": exit_time}
            for _ in range(n)]


def test_pre_apply_sl_deaths_do_not_floor_a_fresh_config():
    apply_ts = 1_000_000.0
    rows = _sl("NAS100", 5, exit_time=apply_ts - 3600)
    assert shakeout_sl_atr_mult(0.5, "NAS100", rows, since_ts=apply_ts) == 0.5


def test_post_apply_sl_deaths_still_raise_the_floor():
    apply_ts = 1_000_000.0
    rows = (_sl("XAUUSD", 2, exit_time=apply_ts - 60)
            + _sl("XAUUSD", 3, exit_time=apply_ts + 60))
    assert shakeout_sl_atr_mult(0.5, "XAUUSD", rows, since_ts=apply_ts) == 2.0


def test_zero_since_keeps_legacy_full_window():
    rows = _sl("GER40", 3, exit_time=100.0)
    assert shakeout_sl_atr_mult(1.0, "GER40", rows) == 2.0
    assert shakeout_sl_atr_mult(1.0, "GER40", rows, since_ts=0.0) == 2.0


def test_entry_path_passes_opt_updated_at():
    src = (Path(__file__).resolve().parents[1] / "micofx" / "engine.py"
           ).read_text(encoding="utf-8")
    body = src[src.index("def _try_entry"):]
    chunk = body[body.index("shakeout_sl_atr_mult"): body.index("sl_dist = max")]
    assert "opt_updated_at" in chunk
