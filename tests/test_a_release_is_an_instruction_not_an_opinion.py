""""Serbest birak" must still mean something two minutes later.

Reported three times on 14.08 - "ai denetleyici hala sifirlamiyor, 120sn sonra
yine izlemeye aliyor". ``clear()`` did its part: it set the verdict to "ok" and
stamped ``history_cleared_at`` so trades before it stop counting. But the watch
branch read ``v.profit_factor`` / ``v.trades`` / ``v.wins``, all built from the
full 30-day window, so the next review rebuilt "watch" from the very history the
operator had just said to disregard.

The 30-day memory is deliberate against a *config change* - that is the system's
own opinion that the past is stale, and a soft 0.6x sizing cut is allowed to
check it. A release is not an opinion, it is an instruction. So after one, the
watch bar reads only the trades made since - and none is not a record.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import inspect

from micofx.supervisor import Supervisor

SRC = inspect.getsource(Supervisor._review_symbol
                        if hasattr(Supervisor, "_review_symbol") else Supervisor)


def test_the_watch_bar_reads_the_release_epoch():
    assert "released_at = float(v.history_cleared_at or 0.0)" in SRC, (
        "the watch bar still cannot see that the operator released the symbol")
    assert "watch_n, watch_pf_val, watch_wins = v.trades, v.profit_factor, v.wins" in SRC, (
        "without a release the full 30-day window must still be what is read")


def test_the_watch_branch_uses_those_numbers_and_not_the_window():
    assert "elif (watch_n > 0 and watch_pf_val < float(cfgs[\"watch_pf\"])" in SRC, (
        "the branch reads the window again, so the release is undone by it")
    branch = SRC[SRC.index("elif (watch_n > 0"):][:400]
    for windowed in ("v.profit_factor <", "v.trades >=", "v.wins <"):
        assert windowed not in branch, f"{windowed} puts the 30-day record back"


def test_an_empty_record_is_not_a_record():
    """_pf returns 0.0 for an empty list, which is under every watch_pf.

    Without the explicit count guard the branch happens to fall through on the
    second condition's arithmetic (0 < 0 is false) - a coincidence, not a rule.
    """
    assert Supervisor._pf([]) == 0.0
    assert "watch_n > 0 and" in SRC


def test_a_record_made_after_the_release_still_counts():
    """The release clears the past, it does not grant immunity."""
    assert "float(d.get(\"time\", 0.0)) >= released_at" in SRC, (
        "trades since the release have to be gathered and judged")
