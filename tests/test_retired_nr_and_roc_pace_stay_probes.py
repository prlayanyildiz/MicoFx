"""nr_break / roc_pace are fully deleted — not probes, not Params axes."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import micofx.strategy as strategy
from micofx.models import OPT_FIELDS, STRATEGIES, SymbolConfig
from micofx.strategy import _FAMILIES, Params


def test_nr_break_and_roc_pace_are_gone_entirely():
    assert "nr_break" not in STRATEGIES
    assert "roc_pace" not in STRATEGIES
    assert "nr_break" not in _FAMILIES
    assert "roc_pace" not in _FAMILIES
    assert not hasattr(strategy, "_nr_break")
    assert not hasattr(strategy, "_roc_pace")
    assert "nr_lookback" not in OPT_FIELDS
    assert "rp_roc_len" not in OPT_FIELDS
    assert "nr_lookback" not in Params.__dataclass_fields__
    assert "rp_roc_len" not in Params.__dataclass_fields__
    assert "nr_lookback" not in SymbolConfig.__dataclass_fields__
    assert "rp_roc_len" not in SymbolConfig.__dataclass_fields__
    assert set(STRATEGIES) == {"mtf_pullback", "burst", "channel_break"}


def test_dead_unstamped_gates_plumbing_is_gone():
    assert not hasattr(strategy, "unstamped_gates_to_zero")
    assert not hasattr(strategy, "_GATED_FLIPS")
    assert not hasattr(strategy, "_UNSTAMPED_GATES")
