"""required_bars must not scale by an HTF dial the family never reads.

searchable_axes already drops unread OPT axes. The fetch size did not: leftover
htf_factor on a family that never calls _trend_gate asked for extra bars the
stack cannot use.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.strategy import Params, opt_fields_read, required_bars


def test_a_family_that_reads_htf_still_scales_required_bars():
    assert "htf_factor" in opt_fields_read("burst")
    wide = Params(strategy="burst", htf_mode="t3", htf_factor=6)
    narrow = Params(strategy="burst", htf_mode="t3", htf_factor=1)
    assert required_bars(wide) > required_bars(narrow)


def test_channel_break_scales_required_bars_with_htf():
    assert "htf_factor" in opt_fields_read("channel_break")
    wide = Params(strategy="channel_break", htf_mode="t3", htf_factor=6)
    narrow = Params(strategy="channel_break", htf_mode="t3", htf_factor=1)
    assert required_bars(wide) > required_bars(narrow)


def test_mtf_pullback_scales_required_bars_with_htf():
    assert "htf_factor" in opt_fields_read("mtf_pullback")
    wide = Params(strategy="mtf_pullback", htf_mode="t3", htf_factor=12)
    narrow = Params(strategy="mtf_pullback", htf_mode="t3", htf_factor=1)
    assert required_bars(wide) > required_bars(narrow)
