"""A family must not search OPT axes its compute path never reads.

t3_flip and ichimoku still do not call ``_regime()`` / ``_trend_gate()``.
The gated flips (stoch/parabolic/aroon) do, via ``_flip_gates``. The
allow-list is derived by walking ``p.field`` in the family function and
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


def test_t3_flip_does_not_read_adx_min():
    """t3_flip's docstring names ADX; only ``p.adx_min`` would make it searchable."""
    assert "adx_min" not in opt_fields_read("t3_flip")
    assert "htf_factor" not in opt_fields_read("t3_flip")
    assert "min_body_ratio" not in opt_fields_read("t3_flip")


def test_a_family_that_calls_regime_does_read_adx_min():
    # Measured 28.08: burst / dual_t3 / mtf_pullback / the gated flips
    # (stoch/parabolic/aroon via _flip_gates) all reach _regime.
    assert "adx_min" in opt_fields_read("burst")
    assert "adx_min" in opt_fields_read("stoch_flip")


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


def test_searchable_axes_drops_adx_min_for_t3_flip():
    kept = searchable_axes("t3_flip", {"adx_min": [0, 15], "t3_length": [5, 8],
                                       "sl_atr_mult": [1.0, 2.0]})
    assert "adx_min" not in kept
    assert "t3_length" in kept
    assert "sl_atr_mult" in kept
