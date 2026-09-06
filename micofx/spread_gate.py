"""Live vs walk-forward spread gate (Claude EK34 / engine docstring).

``simulate`` refuses on the ENTRY BAR's recorded spread. Live used to refuse
on the CURRENT TICK. A ceiling chosen against the bar then blocks ordinary
breakout ticks (SpotBrent 16/0, 1777 spread retries) while holdout still
counts those fills — the book trades the calm residue and capture collapses.

Primary + send recheck both read the forming bar's spread when available so
the live door matches the search. Tick remains the fill price / cost stamp.
When bars are missing or the forming bar reports zero spread, fall back to
the tick — live has a real quote, so do not invent a median like
``imputed_spread_pts`` does in replay (Claude 06.09).
"""
from __future__ import annotations


def spread_over_cap(spread_price: float, atr: float, max_spread_atr: float) -> bool:
    if max_spread_atr <= 0 or atr <= 0:
        return False
    if not (spread_price > 0):
        return False
    return spread_price > atr * max_spread_atr


def gate_spread_price(
    *,
    tick_spread: float,
    bar_spread: float | None,
    spread_scale: float = 1.0,
) -> float:
    """Spread used for the max_spread_atr gate.

    Prefer the bar (walk-forward identity), scaled by the same live-tick/bar
    median ``spread_cost_series`` multiplies into replay. Tick only when the
    bar is unknown or zero — and then unscaled (already a live price).
    """
    if bar_spread is not None and bar_spread > 0:
        scale = float(spread_scale) if spread_scale and spread_scale > 0 else 1.0
        return float(bar_spread) * scale
    return float(tick_spread or 0.0)
