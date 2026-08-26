"""Closed-bar stop overlay shared by live trail and the walk-forward.

``engine._update_stop`` and ``backtest.simulate`` are the same exit rule
twice. The live path still owns broker clamp + modify; paper still owns
fill-at-SL. This module is only the level those two agree on.
"""
from __future__ import annotations


def harvest_trail_step(*, trail_step_atr: float, harvest_at_r: float,
                       harvest_step_atr: float, profit: float,
                       original_risk: float) -> float:
    """ATR trail distance for this bar: OPT step, or the harvest overlay.

    Default (harvest_at_r or harvest_step_atr = 0) returns ``trail_step_atr``
    unchanged. Once open profit reaches ``harvest_at_r`` original R, the
    distance is the tighter of the two so a 1.8-step NAS trail can hug like
    XAUUSD 0.4 without rewriting the searched ``trail_step_atr``.
    """
    step = float(trail_step_atr)
    if (harvest_at_r > 0 and harvest_step_atr > 0 and original_risk > 0
            and profit >= harvest_at_r * original_risk):
        tight = float(harvest_step_atr)
        return min(step, tight) if step > 0 else tight
    return step


def overlay_stop(*, is_buy: bool, entry: float, ref: float, atr: float,
                 trail_start_atr: float, trail_step_atr: float,
                 trail_mode: str, struct_sl: float | None,
                 breakeven_at_r: float, original_risk: float,
                 be_offset: float = 0.0,
                 harvest_at_r: float = 0.0,
                 harvest_step_atr: float = 0.0) -> float | None:
    """Stop the trail/BE overlay wants at this closed bar, or None.

    ``be_offset`` is paper's round-turn commission in price (live passes 0).
    Structure/hybrid callers pass ``struct_sl`` already buffered; ``None``
    keeps the ATR trail. ``harvest_at_r`` / ``harvest_step_atr`` (0 = off)
    tighten the ATR step on a paid trade; they are not OPT axes.
    """
    if atr <= 0:
        return None
    profit = (ref - entry) if is_buy else (entry - ref)
    if profit <= 0:
        return None
    harvest_on = (
        harvest_at_r > 0 and harvest_step_atr > 0 and original_risk > 0
        and profit >= harvest_at_r * original_risk)
    step = harvest_trail_step(
        trail_step_atr=trail_step_atr, harvest_at_r=harvest_at_r,
        harvest_step_atr=harvest_step_atr, profit=profit,
        original_risk=original_risk)
    target: float | None = None
    trail_armed = (
        (trail_start_atr > 0 and profit >= atr * trail_start_atr)
        or harvest_on)
    if trail_armed and step > 0:
        trail_atr = (ref - atr * step) if is_buy else (
            ref + atr * step)
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
