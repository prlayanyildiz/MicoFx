"""Margin%-driven kasa targets — shared by inline sizing and autopilot.

Operator dial is ``max_margin_usage_pct`` only. Broker leverage comes from
``order_calc_margin`` inside ``_margin_lot_ceiling``. Pure function; no MT5.
"""
from __future__ import annotations

from typing import Any

LOT_MULT_MIN = 0.3
LOT_MULT_MAX = 1.6
# Equity-tier lot at this margin% reads as 1.0× aggression.
MARGIN_REF_PCT = 80.0
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
    n_enabled: int,
    max_margin_usage_pct: float,
    lot_multiplier: float = 1.0,
    max_concurrent_risk_pct: float = 10.0,
    global_free_slots: int = 1,
    margin_usage_pct: float = 0.0,
    zero_lot: int = 0,
    lot_blocks: int = 0,
    # Unused leftovers kept so older call sites (leverage=) do not TypeError.
    leverage: float = 0.0,
    broker_leverage: float = 0.0,
    base_notional_at_1x: float = 0.0,
) -> dict[str, Any]:
    """Derive lot_mult + concurrent from margin% (and equity / n)."""
    eq = max(0.0, float(equity or 0.0))
    n = max(1, int(n_enabled or 1))
    lot_cur = float(lot_multiplier or 1.0)
    try:
        pct = float(max_margin_usage_pct or 0.0)
    except (TypeError, ValueError):
        pct = MARGIN_REF_PCT
    pct = max(0.0, min(100.0, pct))
    # 0 = uncapped margin path in the engine → treat as full aggression.
    if pct <= 0:
        aggression = 1.0
        pct = MARGIN_REF_PCT
    else:
        aggression = min(1.25, pct / MARGIN_REF_PCT)

    tier = equity_lot_base(eq)
    lot_target = quantize_lot_mult(tier * max(aggression, LOT_MULT_MIN / max(tier, 0.01)))

    # Autopilot may still nudge margin% toward a soft band; with the dial as
    # the operator source of truth, targets.margin mirrors the dial (no rewrite
    # unless heal / flat-growth rules fire).
    margin_target = round(pct, 1) if pct > 0 else 80.0

    per_trade = RISK_PCT * lot_target
    conc_max = min(CONC_HARD_MAX, 15.0 + aggression * 40.0)
    conc_target = round(min(conc_max, max(CONC_MIN, n * per_trade * 1.1)), 1)

    if global_free_slots == 0 and margin_usage_pct >= pct * 0.9 and pct > 0:
        lot_target = quantize_lot_mult(max(LOT_MULT_MIN, lot_cur * 0.85))

    heal_notes: list[str] = []
    if zero_lot > 0:
        lot_target = quantize_lot_mult(min(1.2, lot_target + 0.05 * zero_lot))
        heal_notes.append(f"lot=0 sembol {zero_lot} -> lot artir")

    patch: dict[str, Any] = {}
    reasons: list[str] = list(heal_notes)
    flat_growth = (
        global_free_slots > 0
        and margin_usage_pct < 15.0
        and zero_lot == 0
    )

    # Do not PATCH margin% — it is the operator dial. Only lot/conc targets
    # are computed for inline use; autopilot may ignore lot/conc patches.
    if abs(lot_target - lot_cur) >= 0.05:
        if not (flat_growth and lot_target < lot_cur):
            patch["lot_multiplier"] = lot_target
            reasons.append(
                f"lot_mult {lot_cur}->{lot_target} "
                f"(marj %{pct:g} / eq ${eq:.0f})")

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
        "margin_pct": pct,
        "aggression": round(aggression, 4),
        "n_enabled": n,
        "global_free_slots": global_free_slots,
        "margin_usage_pct": margin_usage_pct,
        # Compat keys for older log lines / tests.
        "leverage": float(leverage or broker_leverage or 0.0),
        "broker_leverage": float(broker_leverage or leverage or 0.0),
        "buying_power": round(eq * (pct / 100.0), 2),
    }
