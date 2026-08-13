"""Switching costs off has to reach the fills, not just the cost column.

Operator decision (13.08): the live cost gate went off, every per-symbol
max_spread_atr ceiling went to 0, and the search was to be scored on the same
terms - buy at the printed price, sell at the printed price, and judge the
result on what was bought and sold.

The naive version of that change is to stop adding ``cost_r``. It would not be
the same thing. In ``simulate`` the spread moves the fills themselves:

    entry      = open[j0] + s   on a buy
    exit_price = close[j] + s   on a sell
    stop check = bar_high + s >= sl

so a run with ``cost_r`` suppressed but the series intact still buys the ask
and sells the bid, and still stops out on a wick that only the spread reached.
Zeroing the series is what actually removes it, and ``cost_r`` then accumulates
nothing of its own accord.

The default stays on. A book selected with costs charged cannot be compared
against candidates scored without them - it is the same incomparability the
spread_scale guard already exists for - so flipping this makes every stored
holdout number incommensurable and the book needs re-searching. That is a
decision, and it is recorded as one.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import backtest
from micofx.models import SystemConfig


# ------------------------------------------------------- the switch exists

def test_the_system_carries_the_switch_and_defaults_to_charging():
    assert SystemConfig().charge_costs is True


def test_walk_forward_takes_it():
    import inspect
    sig = inspect.signature(backtest.walk_forward)
    assert "charge_costs" in sig.parameters
    assert sig.parameters["charge_costs"].default is True


def test_the_optimiser_reads_it_from_the_live_system_and_passes_it_down():
    src = (Path(__file__).resolve().parents[1] / "micofx" / "optimizer.py").read_text(
        encoding="utf-8")
    assert 'getattr(sys_cfg, "charge_costs", True)' in src, "sistemden okunmuyor"
    assert '"charge_costs": charge_costs' in src, "payload'a girmiyor"
    assert 'charge_costs=bool(payload.get("charge_costs", True))' in src, (
        "isci surece gecmiyor")


# ------------------------------------------- it reaches the fills, not just cost_r

def _spread_series_after(charge: bool) -> np.ndarray:
    """Reproduce walk_forward's own two lines, which is where the switch acts."""
    spread_pts = np.array([2.0, 3.0, 2.5, 4.0])
    point = 0.1
    spread_price = spread_pts * point * 1.0
    if not charge:
        spread_price = np.zeros_like(spread_price)
    return spread_price


def test_switching_off_zeroes_the_series_the_fills_are_built_from():
    assert _spread_series_after(True).any(), "acikken spread yok - test kendini gozden gecirsin"
    assert not _spread_series_after(False).any(), (
        "kapaliyken seri hala dolu - giris hala ask'ten alir")


def test_the_zeroing_is_in_walk_forward_before_the_cost_series_is_built():
    """cost_price = spread_price + commission_price is assembled after it, so
    both halves fall out together rather than only the accounting one."""
    src = (Path(__file__).resolve().parents[1] / "micofx" / "backtest.py").read_text(
        encoding="utf-8")
    zero = src.index("spread_price = np.zeros_like(spread_price)")
    assembled = src.index("cost_price = spread_price + float(commission_price)")
    assert zero < assembled, "sifirlama maliyet serisi kurulduktan SONRA yapiliyor"
    assert "commission_price = 0.0" in src[zero:assembled], "komisyon sifirlanmiyor"


def test_the_fills_really_do_use_the_spread():
    """If simulate ever stops moving fills by ``s``, zeroing the series would
    become a cosmetic change and this whole switch would need rethinking."""
    src = (Path(__file__).resolve().parents[1] / "micofx" / "backtest.py").read_text(
        encoding="utf-8")
    assert "entry = float(open_[j0] + s) if is_buy else float(open_[j0])" in src
    assert 'exit_price = close[j] + (0.0 if is_buy else s)' in src
