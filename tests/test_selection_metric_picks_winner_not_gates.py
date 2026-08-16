"""Selection metric changes which gated candidate wins, not the gates.

BK claimed score preferred high-n low-E over high-E (GER40 wavetrend vs
stoch on an unfair family table). BJ then showed that table was the AO4
trap. The metrics stay as a measurement tool: same survivors, different
ranking. Found when the operator asked for a panel-selectable pick after
the score-is-broken claim was withdrawn.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import inspect

from micofx import backtest
from micofx.backtest import rank_for_selection, selection_value


def _cand(name, *, score, val_score, n, e, wr, wins, losses, pf):
    return {
        "name": name,
        "score": score,
        "validation": {
            "score": val_score,
            "trades": n,
            "expectancy": e,
            "win_rate": wr,
            "wins": wins,
            "losses": losses,
            "profit_factor": pf,
        },
    }


# High-n, modest E, high score (what net_r ranking likes).
HIGH_N = _cand("high_n", score=80.0, val_score=40.0, n=200, e=0.10,
               wr=30.0, wins=60, losses=140, pf=1.20)
# Low-n, fat E, low score (what costed_e likes).
HIGH_E = _cand("high_e", score=8.0, val_score=5.0, n=40, e=0.40,
               wr=40.0, wins=16, losses=24, pf=2.00)


def test_default_score_keeps_the_high_n_winner():
    ranked = rank_for_selection([HIGH_E, HIGH_N], "score", 50.0)
    assert ranked[0]["name"] == "high_n"


def test_costed_e_picks_the_fatter_edge():
    """Without rank_for_selection the walk_forward sort is always validation score."""
    ranked = rank_for_selection([HIGH_E, HIGH_N], "costed_e", 50.0, min_trades=25)
    assert ranked[0]["name"] == "high_e"


def test_costed_e_is_zero_below_min_trades():
    thin = dict(HIGH_E)
    thin["validation"] = {**HIGH_E["validation"], "trades": 10, "expectancy": 0.9}
    assert selection_value(thin["validation"], "costed_e", 50.0, min_trades=25) == 0.0


def test_unknown_metric_falls_back_to_score():
    ranked = rank_for_selection([HIGH_E, HIGH_N], "not_a_metric", 50.0)
    assert ranked[0]["name"] == "high_n"


def test_walk_forward_ranks_with_the_metric_not_a_hardcoded_score_sort():
    src = inspect.getsource(backtest.walk_forward)
    assert "rank_for_selection" in src
    assert "selection_metric" in src
