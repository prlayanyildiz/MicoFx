"""A family must not search OPT axes its compute path never reads.

The allow-list is derived by walking ``p.field`` in the family function and
same-module callees. A hand-written table would drift. Docstring words
such as "no ADX" must not count.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import OPT_FIELDS
from micofx.optimizer import Optimizer
from micofx.strategy import (
    _FAMILIES,
    ENGINE_OPT_FIELDS,
    opt_fields_read,
    searchable_axes,
)


def test_ichimoku_reads_regime_gates():
    """ichimoku now filters like the other swing families (FX literature)."""
    read = opt_fields_read("ichimoku")
    assert "adx_min" in read
    assert "htf_factor" in read
    assert "atr_pct_min" in read


def test_a_family_that_calls_regime_does_read_adx_min():
    assert "adx_min" in opt_fields_read("burst")
    assert "adx_min" in opt_fields_read("channel_break")


def test_no_family_grid_axis_is_unread():
    """Any OPT key left in the merged search grid must be read or engine-owned."""
    defaults = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "defaults.json")
        .read_text(encoding="utf-8"))
    opt = defaults["optimizer"]
    shared = {k: v for k, v in (opt.get("grid") or {}).items()
              if isinstance(v, list) and v}
    family_grids = opt.get("strategy_grids") or {}
    poisoned = {k: [0] for k in OPT_FIELDS}
    for name in _FAMILIES:
        own = {k: v for k, v in (family_grids.get(name) or {}).items()
               if isinstance(v, list) and v}
        allow = opt_fields_read(name) | ENGINE_OPT_FIELDS
        for label, axes in (
            ("own", searchable_axes(name, {**own, **poisoned})),
            ("merged", searchable_axes(name, {**shared, **own, **poisoned})),
            ("exit_grid", Optimizer._exit_grid_for(
                {**shared, **own, **poisoned}, own, name, "M5")),
        ):
            unread = sorted(k for k in axes if k in OPT_FIELDS and k not in allow)
            assert not unread, f"{name} {label} still searches unread OPT axes: {unread}"


def test_searchable_axes_keeps_ichimoku_entry_and_exit_axes():
    kept = searchable_axes("ichimoku", {
        "adx_min": [0, 15], "htf_factor": [0, 3],
        "atr_pct_min": [0, 0.25],
        "sl_atr_mult": [1.0, 2.0], "trail_start_atr": [0.5, 1.0],
    })
    assert "adx_min" in kept
    assert "htf_factor" in kept
    assert "sl_atr_mult" in kept
    assert "trail_start_atr" in kept
