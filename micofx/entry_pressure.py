"""Entry-block pressure helpers for autopilot and Tanı honesty.

Separates soft/capacity (expected governors) from actionable spread/chase so
fill% and auto-tunes do not treat NAS ``seans_disi`` or ``bar_doldu`` as
income bugs.
"""
from __future__ import annotations

from typing import Any

# Soft / clock — expected when session or bar rules bind (not MSA/chase fodder).
SOFT_BLOCKS: frozenset[str] = frozenset({
    "seans_disi",
    "piyasa_kapali",
    "saat_kapali",
    "gun_kapali",
    "hafta_sonu",
    "hafta_sonu_oncesi",
    "kapanis_oncesi",
    "gun_sonu",
    "saat_bayat",
    "bar_bosluk",
    "bar_doldu",  # 1 fill/bar by design
    "cooldown",
})

# Stack governors — working as designed while at cap / spacing.
CAPACITY_BLOCKS: frozenset[str] = frozenset({
    "risk_sembol_limiti",
    "risk_kademe_aralik",
    "risk_eszamanli",
    "risk_ters_yon",
    "risk_serbest_marj",
    "risk_marj_kullanimi",
    "risk_marj_okunamadi",
    "risk_stopsuz",
    "risk_kova_limiti",
    "risk_toplam_limit",
})

INTENTIONAL_BLOCKS: frozenset[str] = SOFT_BLOCKS | CAPACITY_BLOCKS

# Holdout-protected MSA ceilings (autopilot / msa_exec must not widen past).
MSA_CEILING_KEEPERS: dict[str, float] = {
    "SpotBrent": 0.06,
}


def gate_class(code: str) -> str:
    key = str(code or "")
    if key in SOFT_BLOCKS:
        return "soft"
    if key in CAPACITY_BLOCKS:
        return "capacity"
    if key in ("spread", "kovalama_asimi", "maliyet", "volatilite"):
        return "actionable"
    if key in ("acildi",):
        return "ok"
    return "other"


def spread_pressure(row: dict[str, Any] | None) -> int:
    """How strongly spread is blocking fills on this entry-block row.

    ``blocks.spread`` counts refuse *kinds* per signal window; while a bar
    signal stays live the engine also increments ``retries.spread`` every
    cycle. US30 04.09 night: 8 signals / 0 opens / blocks=2 / retries=879 —
    unique blocks alone never reach the autopilot/holdout_live threshold of
    10, so the exec gap stayed invisible.
    """
    return _gate_pressure(row, "spread")


def chase_pressure(row: dict[str, Any] | None) -> int:
    """Same retry-aware pressure for ``kovalama_asimi`` (chase ceiling)."""
    return _gate_pressure(row, "kovalama_asimi")


def _gate_pressure(row: dict[str, Any] | None, key: str) -> int:
    if not isinstance(row, dict):
        return 0
    try:
        blocks = int((row.get("blocks") or {}).get(key) or 0)
    except (TypeError, ValueError):
        blocks = 0
    try:
        retries = int((row.get("retries") or {}).get(key) or 0)
    except (TypeError, ValueError):
        retries = 0
    return max(blocks, retries // 50)


def competing_block_top(blocks: dict[str, Any] | None) -> int:
    """Max unique-block count among non-intentional gates (spread vs spread)."""
    if not isinstance(blocks, dict) or not blocks:
        return 0
    hard = 0
    for k, v in blocks.items():
        if str(k) in INTENTIONAL_BLOCKS:
            continue
        try:
            hard = max(hard, int(v or 0))
        except (TypeError, ValueError):
            continue
    return hard


def action_fill_rate(row: dict[str, Any] | None) -> float | None:
    """Opened / (signals − soft blocks). Soft refusals do not fake a 0% book."""
    if not isinstance(row, dict):
        return None
    try:
        total = int(row.get("signals") or 0)
        opened = int(row.get("opened") or 0)
    except (TypeError, ValueError):
        return None
    soft_n = 0
    for k, v in (row.get("blocks") or {}).items():
        if str(k) not in SOFT_BLOCKS:
            continue
        try:
            soft_n += int(v or 0)
        except (TypeError, ValueError):
            continue
    denom = total - soft_n
    if denom <= 0:
        return None
    return round(opened / denom, 3)


def auto_hint(row: dict[str, Any] | None) -> str:
    """What hands-off automation should do (or explicitly not do)."""
    if not isinstance(row, dict):
        return "izle"
    blocks = row.get("blocks") or {}
    if not blocks:
        return "izle"
    fill = None
    try:
        fill = float(row.get("fill_rate")) if row.get("fill_rate") is not None else None
    except (TypeError, ValueError):
        fill = None
    a_fill = action_fill_rate(row)
    use_fill = a_fill if a_fill is not None else fill
    sp = spread_pressure(row)
    cp = chase_pressure(row)
    top_hard = competing_block_top(blocks)

    # Dominant intentional → label, do not tune.
    try:
        top_code, top_n = max(
            ((str(k), int(v or 0)) for k, v in blocks.items()),
            key=lambda kv: kv[1],
            default=("", 0),
        )
    except (TypeError, ValueError):
        top_code, top_n = "", 0
    if top_code in SOFT_BLOCKS and top_n >= max(sp, cp, 1):
        return "beklenen_soft"
    if top_code in CAPACITY_BLOCKS and top_n >= max(sp, cp, 1):
        return "beklenen_kapasite"

    if sp >= 10 and (use_fill is None or use_fill < 0.35) and sp >= top_hard:
        return "spread_kalibre"
    if cp >= 8 and (use_fill is None or use_fill < 0.40) and cp >= top_hard:
        return "chase_nudge"
    return "izle"


def annotate_entry_row(row: dict[str, Any]) -> dict[str, Any]:
    """Copy row with honesty + auto fields for API / autopilot."""
    out = dict(row)
    out["action_fill_rate"] = action_fill_rate(row)
    out["spread_pressure"] = spread_pressure(row)
    out["chase_pressure"] = chase_pressure(row)
    out["auto_hint"] = auto_hint(row)
    blocks = row.get("blocks") or {}
    if blocks:
        try:
            top_code = max(blocks.items(), key=lambda kv: int(kv[1] or 0))[0]
        except (TypeError, ValueError):
            top_code = ""
        out["dominant_gate"] = str(top_code)
        out["dominant_class"] = gate_class(str(top_code))
    else:
        out["dominant_gate"] = ""
        out["dominant_class"] = "izle"
    return out


def clamp_msa_cap(symbol: str, cap: float) -> float:
    """Pin holdout keepers (SpotBrent 0.06) so AP cannot widen past charter."""
    try:
        c = float(cap)
    except (TypeError, ValueError):
        return 0.0
    ceiling = MSA_CEILING_KEEPERS.get(str(symbol))
    if ceiling is None:
        return c
    return min(c, float(ceiling))
