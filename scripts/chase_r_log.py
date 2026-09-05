"""Chase (kovalama) measure-only LOG helpers — Claude 21:38.

At fill time compute ``fill_vs_signal`` / ``chase_r`` and format a log
fragment. **Never gates entry** — AGENTS forbids an adverse-fill entry
gate on ``fill_vs_signal_close_r``. Threshold talk only after n>=50 OOS
new entries with the same monotone shape.
"""
from __future__ import annotations

from typing import Any


def fill_vs_signal(
    fill_px: Any,
    sig_close: Any,
    side: Any,
) -> float | None:
    """Signed price distance. Positive = adverse chase (buy above / sell below)."""
    try:
        fill = float(fill_px)
        sig = float(sig_close)
    except (TypeError, ValueError):
        return None
    s = str(side or "").strip().lower()
    if s not in ("buy", "sell"):
        return None
    return (fill - sig) if s == "buy" else (sig - fill)


def chase_r(
    fill_px: Any,
    sig_close: Any,
    side: Any,
    sl_dist: Any,
) -> float | None:
    """Signed fill_vs / sl_dist — same convention as autopsy fill_vs_signal_close_r."""
    vs = fill_vs_signal(fill_px, sig_close, side)
    try:
        dist = float(sl_dist)
    except (TypeError, ValueError):
        return None
    if vs is None or dist <= 0:
        return None
    return vs / dist


def chase_r_abs(
    fill_px: Any,
    sig_close: Any,
    sl_dist: Any,
) -> float | None:
    """Queue formula: abs(price - sig_close) / sl_dist (magnitude only)."""
    try:
        fill = float(fill_px)
        sig = float(sig_close)
        dist = float(sl_dist)
    except (TypeError, ValueError):
        return None
    if dist <= 0:
        return None
    return abs(fill - sig) / dist


def format_chase_log(
    *,
    fill_vs_r: float | None = None,
    chase_abs: float | None = None,
) -> str:
    """TRADE-log fragment. Empty when nothing measurable."""
    bits: list[str] = []
    if fill_vs_r is not None:
        bits.append(f"fill_vs_r={fill_vs_r:+.4f}")
    if chase_abs is not None:
        bits.append(f"chase_r_abs={chase_abs:.4f}")
    return (" " + " ".join(bits)) if bits else ""


def log_chase_line(
    *,
    ticket: Any = None,
    side: Any = None,
    fill_px: Any = None,
    sig_close: Any = None,
    sl_dist: Any = None,
) -> str:
    """Full measure-only line body (no gate language). Empty if incomplete."""
    signed = chase_r(fill_px, sig_close, side, sl_dist)
    abs_r = chase_r_abs(fill_px, sig_close, sl_dist)
    bit = format_chase_log(fill_vs_r=signed, chase_abs=abs_r)
    if not bit:
        return ""
    t = int(ticket) if ticket is not None else 0
    s = str(side or "").strip().upper() or "?"
    return f"#{t} {s} kovalama olcum{bit}"
