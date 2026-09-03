"""Leverage-driven kasa targets — shared by inline sizing and autopilot margin.

Dial ``target_leverage`` (broker-capped) chooses buying power. Pure function;
no Store / MT5. ``lot_for`` / ``can_open`` call this live; autopilot may still
patch ``max_margin_usage_pct`` on its slow tick.
"""
from __future__ import annotations

from typing import Any

DEPLOY_FRAC = 0.80
LOT_MULT_MIN = 0.3
LOT_MULT_MAX = 1.6
LOT_REF_LEV = 40.0
RISK_PCT = 2.0
CONC_MIN = 5.0
CONC_HARD_MAX = 50.0
NOTIONAL_MARGIN_SOFT_PCT = 95.0


def equity_lot_base(eq: float) -> float:
    if eq < 120:
        return 0.65
    if eq < 250:
        return 0.92
    if eq < 500:
        return 1.0
    if eq < 1200:
        return 1.15
    if eq < 3000:
        return 1.3
    return min(LOT_MULT_MAX, 1.3 + (eq - 3000) / 8000.0)


def quantize_lot_mult(value: float, step: float = 0.02) -> float:
    if step <= 0:
        return round(value, 2)
    q = round(round(value / step) * step, 2)
    return max(LOT_MULT_MIN, min(LOT_MULT_MAX, q))


def compute_kasa_targets(
    *,
    equity: float,
    leverage: float,
    n_enabled: int,
    global_free_slots: int = 1,
    margin_usage_pct: float = 0.0,
    max_margin_usage_pct: float = 85.0,
    lot_multiplier: float = 1.0,
    max_concurrent_risk_pct: float = 10.0,
    zero_lot: int = 0,
    lot_blocks: int = 0,
    broker_leverage: float = 0.0,
    base_notional_at_1x: float = 0.0,
) -> dict[str, Any]:
    """Return recommended knobs. ``leverage`` is already dial-capped."""
    eq = max(0.0, float(equity or 0.0))
    eff_lev = max(1.0, float(leverage or 1.0))
    broker = max(eff_lev, float(broker_leverage or 0.0) or eff_lev)
    n = max(1, int(n_enabled or 1))
    lot_cur = float(lot_multiplier or 1.0)
    aggression = min(1.0, eff_lev / broker)
    buying_power = eq * eff_lev
    target_deploy = DEPLOY_FRAC * buying_power

    tier = equity_lot_base(eq)
    if base_notional_at_1x > 1e-6:
        lot_target = max(LOT_MULT_MIN, min(LOT_MULT_MAX,
                                           target_deploy / base_notional_at_1x))
    else:
        lot_target = max(
            LOT_MULT_MIN,
            min(LOT_MULT_MAX, tier * (eff_lev / LOT_REF_LEV)),
        )
    lot_target = quantize_lot_mult(lot_target)

    margin_target = round(min(85.0, max(
        40.0,
        DEPLOY_FRAC * 100.0 * (0.45 + 0.55 * aggression),
    )), 1)
    if aggression >= 0.8 and eq < 500:
        margin_target = max(margin_target, 78.0)

    per_trade = RISK_PCT * lot_target
    conc_max = min(CONC_HARD_MAX, 15.0 + aggression * 40.0)
    conc_target = round(min(conc_max, max(CONC_MIN, n * per_trade * 1.1)), 1)

    if global_free_slots == 0 and margin_usage_pct >= max_margin_usage_pct * 0.9:
        lot_target = quantize_lot_mult(max(LOT_MULT_MIN, lot_cur * 0.85))

    heal_notes: list[str] = []
    if zero_lot > 0:
        margin_target = round(min(85.0, margin_target + 5.0 + zero_lot * 2.0), 1)
        lot_target = quantize_lot_mult(min(1.2, lot_target + 0.05 * zero_lot))
        heal_notes.append(f"lot=0 sembol {zero_lot} -> marj/lot artir")

    patch: dict[str, Any] = {}
    reasons: list[str] = list(heal_notes)
    flat_growth = (
        global_free_slots > 0
        and margin_usage_pct < 15.0
        and zero_lot == 0
    )

    if abs(margin_target - float(max_margin_usage_pct or 0)) >= 1.0:
        if not (flat_growth and margin_target < float(max_margin_usage_pct or 0)):
            patch["max_margin_usage_pct"] = margin_target
            reasons.append(
                f"marj %{max_margin_usage_pct:g}->%{margin_target:g} "
                f"(alim gucu ${buying_power:.0f})")

    if abs(lot_target - lot_cur) >= 0.05:
        if not (flat_growth and lot_target < lot_cur):
            patch["lot_multiplier"] = lot_target
            reasons.append(
                f"lot_mult {lot_cur}->{lot_target} "
                f"(1:{int(eff_lev)} / eq ${eq:.0f})")

    if abs(conc_target - float(max_concurrent_risk_pct or 0)) >= 2.0:
        patch["max_concurrent_risk_pct"] = conc_target
        reasons.append(
            f"conc_risk %{max_concurrent_risk_pct:g}->%{conc_target:g} "
            f"(x{n} x %{per_trade:g})")

    return {
        "patch": patch,
        "targets": {
            "max_margin_usage_pct": margin_target,
            "lot_multiplier": lot_target,
            "max_concurrent_risk_pct": conc_target,
        },
        "reasons": reasons,
        "equity": eq,
        "leverage": eff_lev,
        "broker_leverage": broker,
        "aggression": round(aggression, 4),
        "buying_power": round(buying_power, 2),
        "n_enabled": n,
        "global_free_slots": global_free_slots,
        "margin_usage_pct": margin_usage_pct,
    }
