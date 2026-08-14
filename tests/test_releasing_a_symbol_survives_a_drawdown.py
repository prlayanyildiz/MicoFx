""""Serbest birak" must mean something while the day is bleeding.

Reported 14.08 20:30 - "AI kararlarini sifirlasam da degismiyor" - with eight of
ten symbols refused at ``prefer_strong_on_dd``. The release itself worked: it set
the verdict to "ok" and stamped ``history_cleared_at`` so old trades stop
counting as evidence against the config running now. Two minutes later the review
ran, found no trades after that epoch, and set the symbol to "idle" (see the
``if not trades`` branch) - which the drawdown gate refused right alongside
"watch".

So releasing a symbol destroyed the evidence it needed to reach "ok", and the
button became a permanent no-op for exactly as long as the drawdown lasted. The
two meanings of "idle" have to be told apart: never judged is unproven, whereas
just released is unproven *by the operator's own instruction*. Proven-weak
symbols ("watch", and the negative-expectancy rule below it) are untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import Supervisor, SymbolVerdict


class _Store:
    """``settings`` is a read-only property built off the store."""

    def get_setting(self, key, default=None):
        return {"enabled": True, "prefer_strong_on_dd": True, "min_trades": 25}


def _sup(risk_scale: float = 0.4) -> Supervisor:
    s = Supervisor.__new__(Supervisor)
    s.store = _Store()
    s.risk_scale = risk_scale
    s.verdicts = {}
    return s


def _gate(sup: Supervisor, v: SymbolVerdict):
    sup.verdicts[v.symbol] = v
    return Supervisor._gate_locked(sup, SymbolConfig(symbol=v.symbol), 1786728000.0)


def _verdict(state: str, cleared_at: float = 0.0) -> SymbolVerdict:
    v = SymbolVerdict(symbol="NAS100", state=state, reason="")
    v.history_cleared_at = cleared_at
    v.trades = 0
    return v


def test_a_released_symbol_can_open_again():
    """The reported failure: release, review rebuilds "idle", still refused."""
    allowed, reason, _ = _gate(_sup(), _verdict("idle", cleared_at=1786728000.0))
    assert allowed is True, f"the release button did nothing: {reason}"


def test_a_symbol_nobody_judged_is_still_held():
    """Unproven with no operator instruction behind it - the rule's real target."""
    allowed, reason, _ = _gate(_sup(), _verdict("idle"))
    assert allowed is False
    assert "ispatlanmamis" in reason


def test_a_proven_weak_symbol_is_still_held_even_after_a_release():
    """Release does not buy a symbol out of a verdict the evidence rebuilt.

    The record that counts is the one made after the epoch the release stamped;
    once those trades exist and the review has rebuilt "watch" on top of them,
    the refusal stands whatever the operator pressed earlier.
    """
    v = _verdict("watch", cleared_at=1786728000.0)
    v.judged_trades = 30
    allowed, _, _ = _gate(_sup(), v)
    assert allowed is False, "watch is earned from trades after the epoch"


def test_none_of_this_applies_outside_a_drawdown():
    """With risk_scale at 1.0 the branch must not fire at all."""
    for state in ("idle", "watch"):
        allowed, _, _ = _gate(_sup(risk_scale=1.0), _verdict(state))
        assert allowed is True, f"{state} refused while the day is flat"


def test_a_fresh_config_is_not_shut_out_by_the_old_ones_record():
    """The deadlock seen right after the 14.08 20:46 re-search.

    ``watch`` is built from the full 30-day window on purpose - a soft 0.6x
    sizing cut may remember a long record. This branch turns it into a hard
    refusal, and the ten fresh configs that landed at 20:46 reset every judged
    count to 0. Eight symbols were then held shut on the previous configs'
    labels, which is the "judge config B by config A's record" failure the rest
    of supervisor.py exists to prevent - and it cannot resolve itself, because
    a symbol that may not trade never earns the evidence that would open it.
    """
    v = _verdict("watch")
    v.judged_trades = 0
    allowed, _, _ = _gate(_sup(), v)
    assert allowed is True, "no evidence about the config running now"


def test_a_config_that_has_proven_weak_is_still_shut():
    """Once the current config has its own record, the refusal stands."""
    v = _verdict("watch")
    v.judged_trades = 30
    allowed, reason, _ = _gate(_sup(), v)
    assert allowed is False
    assert "ispatlanmamis" in reason


def test_the_negative_rule_also_reads_the_config_running_now():
    """The rule left holding the door after the watch branch was fixed.

    ``trades``/``expectancy`` are the full 30-day window. Six symbols
    re-optimised an hour earlier and released by hand were still refused on the
    record of configs they no longer run - NAS100 at E -1.699 over 72 trades,
    none of them taken by the config that would have opened the entry.
    """
    v = _verdict("ok")
    v.trades, v.expectancy = 72, -1.699      # the old configs' record
    v.judged_trades, v.judged_pf = 0, 0.0    # nothing under this one yet
    allowed, _, _ = _gate(_sup(), v)
    assert allowed is True


def test_a_config_that_has_proven_negative_is_refused():
    """Once its own record is long enough and losing, the refusal stands."""
    v = _verdict("ok")
    v.judged_trades, v.judged_pf = 30, 0.72
    allowed, reason, _ = _gate(_sup(), v)
    assert allowed is False
    assert "negatif" in reason
