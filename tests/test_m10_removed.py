"""M10 is gone from every menu, and now from the lookups behind them too.

It was removed from the search, the symbol editor and the set of valid PATCH
values, but deliberately KEPT in the two name->number translation tables on the
argument that they are lookups rather than menus: dropping M10 would send a
config stored while it was offered down the fallback and quietly trade it on M5
bars. H4 sat there on the same footing.

That argument depended on such a config existing. None does - every stored
symbol row uses one of TIMEFRAMES, and the last mention anywhere in the database
was a stale ``opt_params.strategy_timeframes`` blob naming M10 for micro_rev and
burst, inert because the search never asks about a bar outside TIMEFRAMES, and
now filtered on read. So the entries were protecting nothing while making the
real hazard easy to overlook: the fallback itself, which turns any unrecognised
timeframe into M5 bars. That fallback stays - refusing outright would take the
engine down over one bad row - but it now announces itself. See
test_no_retired_timeframes.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import (STRATEGY_TIMEFRAMES, TIMEFRAMES, READABLE_TIMEFRAMES,
                           SymbolConfig, strategy_allows_timeframe)

ROOT = Path(__file__).resolve().parents[1]


def test_m10_is_not_a_valid_timeframe():
    assert "M10" not in TIMEFRAMES


def test_the_family_timeframe_table_is_empty_or_clean():
    """Both loops that used to live here iterated STRATEGY_TIMEFRAMES, which is
    now ``{}`` - so they ran zero times and asserted nothing while still
    reporting green. The family->TF restriction was lifted deliberately
    (DECISIONS #2), and an empty table means "every family may use every
    TIMEFRAMES entry".

    Stated as an either/or rather than deleted: if the table is ever populated
    again, both things those loops existed for still have to hold.
    """
    if not STRATEGY_TIMEFRAMES:
        return
    for family, allowed in STRATEGY_TIMEFRAMES.items():
        assert "M10" not in allowed, family
        assert set(allowed) & set(TIMEFRAMES), f"{family} hicbir TF'de calisamaz"


@pytest.mark.parametrize("family", ["micro_rev", "burst"])
def test_a_scalp_family_may_use_m5_and_not_m10(family):
    """The scalp families are the ones M5 exists for.

    With STRATEGY_TIMEFRAMES empty this resolves through the "not configured ->
    allow every TIMEFRAMES entry" branch, so what it really asserts is that M5
    is offered and M10 is not - the point either way. It used to parametrize
    over ``t3_ribbon`` as well, one of the six families removed on 12.08; the
    name outlived the family because the assertion never depended on it, which
    is the kind of residue this sweep was looking for.
    """
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
    """Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok."""
    cfg = SymbolConfig.from_dict({
        "symbol": "GBPJPY", "magic": 1,
        "secondary_strategy": "micro_rev", "secondary_timeframe": "M10",
    })
    assert cfg.symbol == "GBPJPY"
    assert not hasattr(cfg, "secondary_timeframe")


def test_the_translation_tables_no_longer_know_it():
    """Nothing stores M10 any more, so the lookups stopped carrying it."""
    from micofx.models import uses_swing_exits
    from micofx.mt5client import timeframe_seconds

    assert timeframe_seconds("M10") == 300, "taninmayan bar M5'e dusmeli"
    assert timeframe_seconds("H4") == 300
    # Both now land on the narrow exit envelope by way of the 0 default rather
    # than on their own second counts.
    assert uses_swing_exits("t3_flip", "M10") is False
    assert uses_swing_exits("t3_flip", "H4") is False


def test_no_stored_symbol_relies_on_the_entries_that_were_dropped():
    """The premise of the removal, asserted rather than assumed."""
    import sqlite3
    db = ROOT / "data" / "micofx.db"
    if not db.exists():
        pytest.skip("canli veritabani yok")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = [json.loads(r[0]) for r in con.execute("SELECT payload FROM symbols")]
    finally:
        con.close()
    for cfg in rows:
        for field in ("timeframe", "secondary_timeframe"):
            value = cfg.get(field) or ""
            assert value == "" or value in READABLE_TIMEFRAMES, (
                f"{cfg.get('symbol')}.{field} = {value!r} artik cozulemez")
