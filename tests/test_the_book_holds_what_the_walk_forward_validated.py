"""The walk-forward validates one position at a time. Live allowed ten.

``simulate`` scans for the next entry only after the current trade closes::

    resume_signal = max(exit_bar, j0 + cooldown_bars - 1)
    while ptr < entries.size and entries[ptr] <= resume_signal:
        ptr += 1

Every signal at or before ``exit_bar`` is skipped, so the simulation never
holds two positions on a symbol at once. Every number the search produces -
profit factor, expectancy, and above all ``max_dd_r`` - describes that system.

Live carried ``max_positions = 10`` on all ten symbols. On 13.08 JPN225 opened
eight SELLs between 04:00 and 14:30 while price rose, and four of them died at
their original stop; the two older positions that had been trailed returned
+16.90 and +17.90 while the five stacked on top gave back 38.44. NAS100 held
seven BUYs, GER40 five.

That is not ten times the risk, it is ten times the *same* risk: one symbol,
one direction, one leg, one idea. The holdout's drawdown never saw it.

Set to 1, which is the only count the search actually validated. Two would be a
reasonable compromise - one position per leg - but the two legs running
together are not validated anywhere either.

This test pins the property the limit is derived from. If ``simulate`` ever
starts overlapping trades, the reasoning behind a live limit of 1 is gone and
this fails rather than leaving the old number sitting there unexplained.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKTEST = (Path(__file__).resolve().parents[1] / "micofx" / "backtest.py").read_text(
    encoding="utf-8")
RISK = (Path(__file__).resolve().parents[1] / "micofx" / "risk.py").read_text(
    encoding="utf-8")


# ------------------------------------------- what the search actually validates

def test_the_simulation_never_holds_two_positions_at_once():
    """The whole basis for a per-symbol limit of 1."""
    assert "resume_signal = max(exit_bar," in BACKTEST, (
        "giris sayaci artik exit_bar'a gore ilerlemiyor - simulasyon ust uste "
        "islem tutuyor olabilir, canli limitin gerekcesi gitti")
    block = BACKTEST[BACKTEST.index("resume_signal = max(exit_bar,"):]
    block = block[:block.index("\n\n")]
    assert "entries[ptr] <= resume_signal" in block
    assert "ptr += 1" in block


def test_the_cooldown_only_ever_pushes_the_resume_later():
    """max() of the two - a cooldown can delay the next entry, never bring it
    forward into the open trade."""
    assert "max(exit_bar, j0 + cooldown_bars - 1)" in BACKTEST


# ------------------------------------------------- what enforces it live

def test_the_live_gate_reads_the_symbol_slot_cap():
    """One ticket per name. Leftover cfg.max_positions is unread.

    The book-wide 1R ceiling used to be asserted absent here; the operator
    re-armed it 31.08 and it is covered by test_concurrent_risk_gate.
    """
    assert "sembol pozisyon limiti (" in RISK
    assert "sys_cfg.max_positions" not in RISK
    # Binding leftover 5/10 is the 13.08 stack.
    assert "getattr(cfg, \"max_positions\"" not in RISK


def test_the_opposite_direction_block_is_still_there():
    """With one position per symbol this rarely fires, but it is the guard that
    stops a hedge appearing if the limit is ever raised again."""
    assert 'if any(p["side"] != side for p in same_symbol):' in RISK


def test_the_leftover_total_slot_cap_is_unread():
    """Book-wide leftover max_total_positions stays unread."""
    assert "len(mine) >= sys_cfg.max_total_positions" not in RISK
    assert "toplam pozisyon limiti" not in RISK
