"""Closed-bar stop overlay shared by live trail and the walk-forward.

``engine._update_stop`` and ``backtest.simulate`` are the same exit rule
twice. The live path still owns broker clamp + modify; paper still owns
fill-at-SL. This module is only the level those two agree on.
"""
from __future__ import annotations


def overlay_stop(*, is_buy: bool, entry: float, ref: float, atr: float,
                 trail_start_atr: float, trail_step_atr: float,
                 trail_mode: str, struct_sl: float | None,
                 breakeven_at_r: float, original_risk: float,
                 be_offset: float = 0.0) -> float | None:
    """Stop the trail/BE overlay wants at this closed bar, or None.

    ``be_offset`` is paper's round-turn commission in price (live passes 0).
    Structure/hybrid callers pass ``struct_sl`` already buffered; ``None``
    keeps the ATR trail.
    """
    if atr <= 0:
        return None
    profit = (ref - entry) if is_buy else (entry - ref)
    if profit <= 0:
        return None
    target: float | None = None
    if trail_start_atr > 0 and profit >= atr * trail_start_atr:
        trail_atr = (ref - atr * trail_step_atr) if is_buy else (
            ref + atr * trail_step_atr)
        trail = trail_atr
        if struct_sl is not None and trail_mode in ("structure", "hybrid"):
            if trail_mode == "hybrid":
                trail = max(trail_atr, struct_sl) if is_buy else min(
                    trail_atr, struct_sl)
            else:
                trail = struct_sl
        target = trail
    if breakeven_at_r > 0 and original_risk > 0 and profit >= breakeven_at_r * original_risk:
        be_sl = entry + be_offset if is_buy else entry - be_offset
        if target is None:
            target = be_sl
        else:
            target = max(target, be_sl) if is_buy else min(target, be_sl)
    return target
