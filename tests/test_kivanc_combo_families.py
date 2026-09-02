"""Retired kivanc combo families stay gone (alpha_trend, mavilim, ichimoku).

Ichimoku retired 02.09: no symbol/TF holdout win in the Claude+Cursor matrix.
Leftover DB names fail closed at compute().
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import STRATEGIES
from micofx.strategy import _FAMILIES


def test_ichimoku_is_retired():
    assert "ichimoku" not in STRATEGIES
    assert "ichimoku" not in _FAMILIES
