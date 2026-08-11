"""M10 is no longer offered anywhere, but a config stored while it was must not break.

Removed from the search, the symbol editor and the set of valid PATCH values.
Deliberately KEPT in the two name->number translation tables: those are
lookups, not menus, and dropping M10 from them would send a legacy config
down the fallback and quietly trade it on M5 bars instead of refusing or
correcting it. H4 has always sat there on the same footing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import (STRATEGY_TIMEFRAMES, TIMEFRAMES, SymbolConfig,
                           strategy_allows_timeframe)

ROOT = Path(__file__).resolve().parents[1]


def test_m10_is_not_a_valid_timeframe():
    assert "M10" not in TIMEFRAMES


def test_no_strategy_family_still_lists_it():
    for family, allowed in STRATEGY_TIMEFRAMES.items():
        assert "M10" not in allowed, family


def test_every_family_still_has_somewhere_to_run():
    """Removing a timeframe must not strand a family with no legal pairing."""
    for family, allowed in STRATEGY_TIMEFRAMES.items():
        assert set(allowed) & set(TIMEFRAMES), f"{family} hicbir TF'de calisamaz"


@pytest.mark.parametrize("family", ["micro_rev", "burst", "t3_ribbon"])
def test_the_scalp_families_keep_m5(family):
    assert strategy_allows_timeframe(family, "M5")
    assert not strategy_allows_timeframe(family, "M10")


def test_the_shipped_config_does_not_search_it():
    data = json.loads((ROOT / "config" / "defaults.json").read_text(encoding="utf-8-sig"))
    opt = data["optimizer"]
    assert "M10" not in opt.get("timeframes", [])
    for family, tfs in (opt.get("strategy_timeframes") or {}).items():
        assert "M10" not in tfs, family


def test_no_shipped_symbol_is_configured_on_it():
    data = json.loads((ROOT / "config" / "defaults.json").read_text(encoding="utf-8-sig"))
    for entry in data["symbols"]:
        assert entry.get("timeframe") != "M10", entry["symbol"]
        assert entry.get("secondary_timeframe") != "M10", entry["symbol"]


def test_the_panel_no_longer_offers_it():
    js = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
    assert '"M10"' not in js


# ------------------------------------------- a legacy config must still work

def test_a_stored_secondary_on_m10_is_cleared_not_kept():
    cfg = SymbolConfig.from_dict({
        "symbol": "GBPJPY", "magic": 1,
        "secondary_strategy": "micro_rev", "secondary_timeframe": "M10",
    })
    assert cfg.secondary_timeframe == ""


def test_the_translation_tables_still_know_it():
    """A lookup, not a menu - dropping it would silently reinterpret a config."""
    from micofx.models import uses_swing_exits
    from micofx.mt5client import timeframe_seconds

    assert timeframe_seconds("M10") == 600
    assert timeframe_seconds("H4") == 14400
    # models.py keeps its own copy of the same table for the swing-exit rule;
    # M10 is under the 900s swing threshold and H4 is over it, and both must
    # still land on the correct side rather than on the 0 default.
    assert uses_swing_exits("t3_flip", "M10") is False
    assert uses_swing_exits("t3_flip", "H4") is True
