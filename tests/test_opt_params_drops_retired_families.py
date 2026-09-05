"""A saved opt blob outlives the families it named.

``Store.opt_params()`` already drops dead timeframes and axes that left
``OPT_FIELDS``. It did not drop family names that left ``STRATEGIES``.
The 26.08 retirement of ``st_trend`` / ``macd_flip`` left both in the live
saved list (13 names on GET /api/opt/params). The search already skips them
(``if s in STRATEGIES``), so they do not eat combo slots - but the merge
still appended shipped families onto that stale list, and ``strategy_grids``
/ ``strategy_max_combos`` kept keys the search cannot legally run.

Same class as the M10 filter: drop on read **and** on save, so a POST
cannot write them back into the blob.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import store as store_module
from micofx.models import STRATEGIES
from micofx.store import Store


def _fresh(tmp_path, monkeypatch) -> Store:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "opt.db")
    return Store()


def test_retired_family_names_do_not_survive_opt_params_read(tmp_path, monkeypatch):
    s = _fresh(tmp_path, monkeypatch)
    s.set_setting("opt_params", {
        "strategies": ["burst", "st_trend", "macd_flip"],
        "strategy_grids": {
            "st_trend": {"sl_atr_mult": [1.0]},
            "burst": {"sl_atr_mult": [1.2]},
        },
        "strategy_max_combos": {"st_trend": 999, "burst": 12000},
        "strategy_timeframes": {"st_trend": ["M5"], "burst": ["M5"]},
    })
    got = s.opt_params()
    names = got["strategies"]
    assert "st_trend" not in names
    assert "macd_flip" not in names
    assert "burst" in names
    # Shipped families the saved subset never named still come back.
    assert "channel_break" in names
    assert set(names) <= set(STRATEGIES)
    assert "st_trend" not in (got.get("strategy_grids") or {})
    assert got["strategy_grids"]["burst"]["sl_atr_mult"] == [1.2]
    assert "st_trend" not in (got.get("strategy_max_combos") or {})
    assert got["strategy_max_combos"]["burst"] == 12000
    assert "st_trend" not in (got.get("strategy_timeframes") or {})
    # 27.08 lottery families: same drop as st_trend / macd_flip.
    s.set_setting("opt_params", {
        "strategies": ["burst", "t3_stoch", "wavetrend_flip", "micro_rev"],
        "strategy_grids": {"t3_stoch": {"sl_atr_mult": [1.0]}, "burst": {"sl_atr_mult": [1.2]}},
        "strategy_max_combos": {"wavetrend_flip": 999, "burst": 12000},
        "strategy_timeframes": {"micro_rev": ["M5"], "burst": ["M5"]},
    })
    got = s.opt_params()
    for dead in ("t3_stoch", "wavetrend_flip", "micro_rev"):
        assert dead not in got["strategies"]
        assert dead not in (got.get("strategy_grids") or {})
        assert dead not in (got.get("strategy_max_combos") or {})
        assert dead not in (got.get("strategy_timeframes") or {})


def test_save_opt_params_does_not_persist_retired_family_names(tmp_path, monkeypatch):
    """Read-time drop is not enough: a POST can write them back into the blob."""
    s = _fresh(tmp_path, monkeypatch)
    s.save_opt_params({
        "strategies": ["burst", "st_trend", "macd_flip"],
        "strategy_grids": {"st_trend": {"sl_atr_mult": [1.0]}},
        "strategy_max_combos": {"st_trend": 999, "burst": 12000},
    })
    raw = s.get_setting("opt_params") or {}
    assert "st_trend" not in (raw.get("strategies") or [])
    assert "macd_flip" not in (raw.get("strategies") or [])
    assert "st_trend" not in (raw.get("strategy_grids") or {})
    assert "st_trend" not in (raw.get("strategy_max_combos") or {})
    assert raw["strategy_max_combos"]["burst"] == 12000
    assert "burst" in raw["strategies"]


def test_every_shipped_family_is_still_searchable_after_the_filter(tmp_path, monkeypatch):
    """The append-shipped merge must survive the drop, or a new family vanishes.

    "Shipped" means ``config/defaults.json optimizer.strategies``, not
    ``STRATEGIES``. Since 04.09 the code constant also carries dormant families
    (sweep_fade, range_fade) that are deliberately absent from the shipped list
    so nothing can select them; asserting they survive the merge would demand
    the opposite - that the search picks them up.
    """
    import json

    s = _fresh(tmp_path, monkeypatch)
    shipped = json.loads(
        (Path(__file__).resolve().parents[1] / "config" / "defaults.json")
        .read_text(encoding="utf-8"))["optimizer"]["strategies"]
    assert set(shipped) <= set(STRATEGIES)
    s.set_setting("opt_params", {"strategies": ["burst"]})
    got = s.opt_params()["strategies"]
    for name in shipped:
        assert name in got, name
    # And the dormant ones must NOT appear - that is the safety half.
    for name in set(STRATEGIES) - set(shipped):
        assert name not in got, f"{name} uykudayken aramaya sizdi"
