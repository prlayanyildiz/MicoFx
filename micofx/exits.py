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


def mfe_lock_to_r(*, profit: float, original_risk: float,
                  lock1_at_r: float, lock1_to_r: float,
                  lock2_at_r: float, lock2_to_r: float,
                  peak_profit: float | None = None) -> float:
    """Highest profit-lock rung armed by peak (or current) open profit.

    Returns the lock distance in original-R units (0 = no lock). Rung 2
    wins when both fire. Zero ``*_at_r`` disables that rung.
    """
    if original_risk <= 0:
        return 0.0
    arm = float(profit if peak_profit is None else peak_profit)
    if arm <= 0:
        return 0.0
    to_r = 0.0
    if lock1_at_r > 0 and lock1_to_r > 0 and arm + 1e-9 >= lock1_at_r * original_risk:
        to_r = max(to_r, float(lock1_to_r))
    if lock2_at_r > 0 and lock2_to_r > 0 and arm + 1e-9 >= lock2_at_r * original_risk:
        to_r = max(to_r, float(lock2_to_r))
    return to_r


def overlay_stop(*, is_buy: bool, entry: float, ref: float, atr: float,
                 trail_start_atr: float, trail_step_atr: float,
                 trail_mode: str, struct_sl: float | None,
                 breakeven_at_r: float, original_risk: float,
                 be_offset: float = 0.0,
                 harvest_at_r: float = 0.0,
                 harvest_step_atr: float = 0.0,
                 mfe_lock1_at_r: float = 0.0,
                 mfe_lock1_to_r: float = 0.0,
                 mfe_lock2_at_r: float = 0.0,
                 mfe_lock2_to_r: float = 0.0,
                 peak_profit: float | None = None) -> float | None:
    """Stop the trail/BE/MFE-lock overlay wants at this closed bar, or None.

    ``be_offset`` is paper's round-turn commission in price (live passes 0).
    Structure/hybrid callers pass ``struct_sl`` already buffered; ``None``
    keeps the ATR trail. ``harvest_at_r`` / ``harvest_step_atr`` (0 = off)
    tighten the ATR step on a paid trade; they are not OPT axes.

    MFE locks (Antigravity 07.09): once peak open profit clears
    ``mfe_lockN_at_r``, the stop may not sit worse than
    ``entry ± mfe_lockN_to_r * original_risk``. Not a hard TP. 0 = off.
    """
    if atr <= 0:
        return None
    profit = (ref - entry) if is_buy else (entry - ref)
    if profit <= 0 and (peak_profit is None or peak_profit <= 0):
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
    if trail_armed and step > 0 and profit > 0:
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
    # Float: ``entry - (entry - 1.5*risk)`` can undershoot the threshold by
    # ~1e-13 (XAU #324842945), so a bare ``>=`` skipped BE and left only a
    # trail level that live min_step then refused — stop stuck at hard SL.
    if (breakeven_at_r > 0 and original_risk > 0
            and profit + 1e-9 >= breakeven_at_r * original_risk):
        be_sl = entry + be_offset if is_buy else entry - be_offset
        if target is None:
            target = be_sl
        else:
            target = max(target, be_sl) if is_buy else min(target, be_sl)
    lock_r = mfe_lock_to_r(
        profit=profit, original_risk=original_risk,
        lock1_at_r=mfe_lock1_at_r, lock1_to_r=mfe_lock1_to_r,
        lock2_at_r=mfe_lock2_at_r, lock2_to_r=mfe_lock2_to_r,
        peak_profit=peak_profit)
    if lock_r > 0 and original_risk > 0:
        lock_sl = (entry + lock_r * original_risk) if is_buy else (
            entry - lock_r * original_risk)
        if target is None:
            target = lock_sl
        else:
            target = max(target, lock_sl) if is_buy else min(target, lock_sl)
    return target
