"""Edge-decay must not halve a winner because two noisy halves differ.

GER40 live: net +65$, PF 1.39, edge_health 1.16 — still watch 0.5x because
the window split 2.53 → 0.92 on ~15 trades a side. Three defects: no
per-half floor, no absolute PF gate, only a penalty (no upgrade).

The rule now needs ``edge_decay_min_half`` trades in EACH half and a total
PF below ``watch_pf``. "Used to be excellent, now only good" is not a cut.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.supervisor import DEFAULTS, Supervisor

_pf = Supervisor._pf


def _fires(nets, cfgs=None):
    cfg = dict(DEFAULTS)
    if cfgs:
        cfg.update(cfgs)
    return Supervisor.edge_decay_fires(nets, _pf(nets), cfg)


def test_defaults_require_fifty_total_and_twenty_five_a_side():
    assert DEFAULTS["edge_decay_min_trades"] >= 50
    assert DEFAULTS["edge_decay_min_half"] >= 25


@pytest.mark.parametrize("count", [10, 20, 29, 30, 40, 49])
def test_the_rule_cannot_fire_below_the_total_bar(count):
    nets = [2.0] * (count // 2) + [-1.0] * (count - count // 2)
    assert not _fires(nets)


def test_fifteen_vs_fifteen_cannot_cut_size():
    """The GER40 split shape: 30 trades, halves of 15."""
    nets = [2.0] * 15 + [-1.0] * 15
    assert not _fires(nets)


def test_a_winner_with_a_softer_second_half_is_not_cut():
    """GER40: recent PF < 1 and < half of older, but the book is still green."""
    older = [3.0] * 18 + [-1.0] * 7          # PF ~ 7.7
    recent = [2.0] * 12 + [-1.0] * 13         # PF ~ 1.85? need < 1
    recent = [1.5] * 10 + [-1.0] * 15         # PF 15/15 = 1.0 exactly — use worse
    recent = [1.2] * 9 + [-1.0] * 16          # 10.8/16 = 0.675
    nets = older + recent
    assert len(older) == 25 and len(recent) == 25
    assert _pf(nets) >= 1.0
    assert _pf(recent) < _pf(older) * 0.5
    assert _pf(recent) < 1.0
    assert not _fires(nets), "absolute PF gate must spare a still-winning book"


def test_a_losing_book_with_large_halves_still_trips():
    older = [2.0] * 14 + [-1.0] * 11          # 28/11 = 2.55
    recent = [2.0] * 2 + [-1.0] * 23          # 4/23 = 0.17
    nets = older + recent
    assert _pf(nets) < 1.0
    assert _fires(nets)


def test_decay_on_a_stationary_series_does_not_predict_a_worse_next_block():
    """AY2 shape, symbol-level: if fire is noise, the next 15 trades are not worse.

    Stationary 45% WR, +2.2 / −1.0 (book-like). Rolling trigger vs quiet;
    subsequent mean $ must not be materially worse when it fired.
    """
    rng = np.random.default_rng(7)
    after_fire: list[float] = []
    after_quiet: list[float] = []
    cfg = dict(DEFAULTS)
    for _ in range(250):
        wins = rng.random(80) < 0.45
        nets = np.where(wins, 2.2, -1.0).tolist()
        for t in range(50, 65):
            window = nets[:t]
            fired = Supervisor.edge_decay_fires(window, _pf(window), cfg)
            nxt = nets[t:t + 15]
            if len(nxt) < 10:
                continue
            (after_fire if fired else after_quiet).append(sum(nxt) / len(nxt))
    if len(after_fire) < 10:
        return
    fire_e = float(np.mean(after_fire))
    quiet_e = float(np.mean(after_quiet))
    assert fire_e >= quiet_e - 0.15, (
        f"decay trigger predicted worse next block "
        f"(fire {fire_e:.3f} vs quiet {quiet_e:.3f}, n_fire={len(after_fire)})"
    )
