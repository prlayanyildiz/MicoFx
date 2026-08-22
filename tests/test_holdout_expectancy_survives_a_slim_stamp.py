"""A slim GAP-5 holdout still has an edge; missing expectancy is not zero.

Five live rows were restamped with net_r and trades and without the
``expectancy`` key. priority() and _attach_expectation() read that key and
treated absence as 0.0, so a same-cycle slot race preferred the one symbol
that still carried the field. The number is net_r / trades either way.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import Supervisor


def _cfg(hold: dict) -> SymbolConfig:
    return SymbolConfig(symbol="GER40", opt_summary={"holdout": hold})


def test_a_slim_stamp_derives_expectancy_from_net_and_trades():
    cfg = _cfg({"net_r": 180.4772, "max_dd_r": 34.0743, "trades": 1294,
                "win_rate": 27.4})
    got = Supervisor.holdout_expectancy(cfg)
    assert abs(got - 180.4772 / 1294) < 1e-9
    assert got > 0.1


def test_an_explicit_expectancy_is_not_recomputed():
    cfg = _cfg({"expectancy": 0.169, "net_r": 85.35, "trades": 504})
    assert Supervisor.holdout_expectancy(cfg) == 0.169


def test_missing_key_does_not_lose_to_a_smaller_explicit_edge():
    """The live failure: GER40 slim-stamped, XAUUSD keyed, slot race inverted."""
    slim = _cfg({"net_r": 180.4772, "trades": 1294})
    small = _cfg({"expectancy": 0.05, "net_r": 25.0, "trades": 500})
    assert Supervisor.holdout_expectancy(slim) > 0.1
    assert Supervisor.holdout_expectancy(slim) > Supervisor.holdout_expectancy(small)


def test_the_stored_key_and_the_derived_value_match_on_the_same_blob():
    hold = {"expectancy": 180.4772 / 1294, "net_r": 180.4772, "trades": 1294}
    assert abs(Supervisor.holdout_expectancy(_cfg(hold))
               - Supervisor.holdout_expectancy(_cfg({k: hold[k] for k in ("net_r", "trades")}))) < 1e-12
