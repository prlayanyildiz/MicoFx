"""GER40 snapshot dirty-head trim (Claude 16:14 / 16:38)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ger40_snapshot_trim import find_clean_start


def test_find_clean_start_skips_zero_spread_head():
    # 1000 junk zeros, then 600 good spreads — first window with miss <5%
    # starts slightly before the hard edge (24 zeros / 500 = 4.8%).
    sp = np.concatenate([
        np.zeros(1000),
        np.full(600, 15.0),
    ])
    cut = find_clean_start(sp, roll_win=500, max_miss=0.05)
    assert cut is not None
    assert 950 <= cut <= 1000
    miss = (~np.isfinite(sp)) | (sp <= 0.0)
    assert float(miss[cut:cut + 500].mean()) < 0.05
    if cut > 0:
        assert float(miss[cut - 1:cut - 1 + 500].mean()) >= 0.05


def test_find_clean_start_none_when_all_junk():
    assert find_clean_start(np.zeros(800), roll_win=500) is None
