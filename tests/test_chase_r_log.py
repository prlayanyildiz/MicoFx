"""chase_r_log — measure-only helpers (Claude 21:38). No entry gate."""
from __future__ import annotations

from scripts.chase_r_log import (
    chase_r,
    chase_r_abs,
    fill_vs_signal,
    format_chase_log,
    log_chase_line,
)


def test_fill_vs_buy_adverse_positive():
    # Buy filled above signal close = adverse.
    assert fill_vs_signal(101.0, 100.0, "buy") == 1.0


def test_fill_vs_sell_adverse_positive():
    # Sell filled below signal close = adverse.
    assert fill_vs_signal(99.0, 100.0, "sell") == 1.0


def test_fill_vs_favorable_negative():
    assert fill_vs_signal(99.0, 100.0, "buy") == -1.0
    assert fill_vs_signal(101.0, 100.0, "sell") == -1.0


def test_chase_r_signed_matches_autopsy_convention():
    # Same as fill_vs_signal_close_r: adverse / sl_dist.
    assert chase_r(101.0, 100.0, "buy", 10.0) == 0.1
    assert chase_r(99.0, 100.0, "sell", 10.0) == 0.1
    assert chase_r(99.0, 100.0, "buy", 10.0) == -0.1


def test_chase_r_abs_is_queue_formula():
    # abs(price - sig_close) / sl_dist — magnitude only.
    assert chase_r_abs(101.0, 100.0, 10.0) == 0.1
    assert chase_r_abs(99.0, 100.0, 10.0) == 0.1


def test_helpers_none_on_bad_inputs():
    assert fill_vs_signal(None, 100.0, "buy") is None
    assert fill_vs_signal(100.0, None, "buy") is None
    assert fill_vs_signal(100.0, 100.0, "") is None
    assert chase_r(101.0, 100.0, "buy", 0.0) is None
    assert chase_r(101.0, 100.0, "buy", None) is None
    assert chase_r_abs(101.0, 100.0, 0.0) is None


def test_format_chase_log_includes_both():
    bit = format_chase_log(fill_vs_r=0.046, chase_abs=0.046)
    assert "fill_vs_r=+0.0460" in bit
    assert "chase_r_abs=0.0460" in bit


def test_log_chase_line_never_gates():
    # Always a string (or empty) — never raises / never says block.
    line = log_chase_line(
        ticket=1, side="buy", fill_px=101.0, sig_close=100.0, sl_dist=10.0)
    assert "chase" in line.lower() or "fill_vs" in line.lower()
    assert "engelle" not in line.lower()
    assert "block" not in line.lower()
    assert log_chase_line(
        ticket=1, side="buy", fill_px=None, sig_close=100.0, sl_dist=10.0
    ) == ""
