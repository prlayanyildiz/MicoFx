"""flow_rev retired 14.08. Its three axes kept spending search budget.

``compute()`` never reads ``p.flow_*``. ``from_dict`` already skips unknown
keys (``_coerce``: ``if f is None: continue``), so dropping the fields from
``SymbolConfig`` is how an old row keeps loading. The axes still sat in
``OPT_FIELDS``, ``Params.key`` and ``required_bars``, which is why they
cost something after the family was gone.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import OPT_FIELDS, SymbolConfig
from micofx.strategy import Params, required_bars


def test_opt_fields_do_not_search_flow_axes():
    for name in ("flow_length", "flow_z", "flow_divergence"):
        assert name not in OPT_FIELDS


def test_params_key_ignores_a_stale_flow_z():
    """Two old rows that only differed on flow_z must share a signal cache key."""
    a = Params.from_config(SymbolConfig.from_dict(
        {"symbol": "XAUUSD", "magic": 1, "flow_z": 1.0}))
    b = Params.from_config(SymbolConfig.from_dict(
        {"symbol": "XAUUSD", "magic": 1, "flow_z": 9.0}))
    assert a.key() == b.key()
    src = inspect.getsource(Params.key)
    assert "flow_z" not in src and "flow_length" not in src


def test_an_old_row_with_flow_fields_still_loads():
    cfg = SymbolConfig.from_dict({
        "symbol": "FRA40", "magic": 2,
        "flow_length": 20, "flow_z": 2.0, "flow_divergence": True,
    })
    assert cfg.symbol == "FRA40"
    assert not hasattr(cfg, "flow_length")


def test_required_bars_does_not_depend_on_flow_length():
    src = inspect.getsource(required_bars)
    assert "flow_length" not in src
    # Retired term was flow_length*6+240 = 360 at the shipped default.
    # mtf_pullback is t3_length*20*htf(6) = 720, so 360 never bound.
    # (t3_stoch was the subject here until it retired 27.08.)
    assert required_bars(Params(strategy="mtf_pullback")) == 720


def test_the_panel_does_not_edit_a_retired_flow_family():
    js = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "static" / "app.js"
          ).read_text(encoding="utf-8")
    assert "flow_length" not in js
    assert "Akis penceresi" not in js
    assert "Emir Akisi" not in js
