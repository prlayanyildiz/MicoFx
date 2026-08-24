"""required_bars must not scale by an HTF dial the family never reads.

searchable_axes already drops unread OPT axes. The fetch size did not: a
dual_t3 row with htf_factor=12 (SpotBrent, 24.08) asked for 960 bars while
the same stack with factor 1 needs 640. The extra 320 never enter compute.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.strategy import Params, opt_fields_read, required_bars


def test_unread_htf_factor_does_not_inflate_required_bars():
    assert "htf_factor" not in opt_fields_read("dual_t3")
    fat = Params(strategy="dual_t3", htf_mode="t3", htf_factor=12, t3_length=4)
    thin = Params(strategy="dual_t3", htf_mode="t3", htf_factor=1, t3_length=4)
    assert required_bars(fat) == required_bars(thin)


def test_a_family_that_reads_htf_still_scales_required_bars():
    assert "htf_factor" in opt_fields_read("burst")
    wide = Params(strategy="burst", htf_mode="t3", htf_factor=6)
    narrow = Params(strategy="burst", htf_mode="t3", htf_factor=1)
    assert required_bars(wide) > required_bars(narrow)
