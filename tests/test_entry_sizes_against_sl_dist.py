"""lot_for must size against the stop that is actually sent (sl_dist).

Shakeout can widen ``sl_atr_mult`` into ``sl_dist`` while ``sl_size`` stayed
on the raw config mult. Sizing the lot off ``sl_size`` then overstated risk
vs the real stop (Claude C1 / live ~%15.8 on a $220 book).
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


def test_entry_sizes_lot_against_sl_dist_not_sl_size():
    src = inspect.getsource(Engine._try_entry)
    # Both lot_for call sites in _try_entry must pass the live stop distance.
    assert "lot_for(\n                cfg, sl_size" not in src
    assert "lot_for(\n            cfg, sl_size" not in src
    assert "sl_dist" in src
    # Cheap string gate: after sl_dist is computed, lot_for uses it.
    assert "cfg, sl_dist," in src or "cfg, sl_dist " in src
