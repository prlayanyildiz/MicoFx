"""Unread burst cost_rank_max on other families must not look like a live lever."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.strategy import Params


def test_channel_break_from_config_zeros_unread_cost_rank():
    cfg = SymbolConfig(symbol="GER40", magic=1, strategy="channel_break",
                       timeframe="M30", cost_rank_max=0.3)
    p = Params.from_config(cfg)
    assert p.cost_rank_max == 0.0


def test_burst_from_config_keeps_cost_rank():
    cfg = SymbolConfig(symbol="NAS100", magic=1, strategy="burst",
                       timeframe="M30", cost_rank_max=0.5)
    p = Params.from_config(cfg)
    assert p.cost_rank_max == 0.5
