"""A broker outage must not spend the whole cycle re-verifying the same refusal.

open_market() never trusts a timeout or a "no network" rejection: it diffs the
position book to find out whether the order landed anyway. That check sleeps
0.3 + 0.6 + 0.6 + 0.6 = 2.1s when it finds nothing, and then correctly reports
the failure as safe to retry.

Safe, but not free. On 2026-08-11 a 40-minute broker outage on UK100 and US30
produced 1090 such rejections - one every 2.2s across the pair. 1090 x 2.1s is
38 minutes of a 40-minute window spent asleep inside the verifier, while
manage_positions - trailing stops, breakeven, forced flatten - waited behind
it. Open positions kept their broker-side stops throughout, so nothing was
unprotected; the engine was simply doing almost nothing else.

The verification is right and is untouched. What changes is that a
connection-class refusal now parks that symbol for 30s instead of being
re-offered on the next poll. The signal is NOT dropped - only delayed - so a
link that recovers still takes the entry on the same bar.

Distinct from the ``ambiguous`` path, which drops the signal chain outright
because there the order MIGHT have filled and a retry would double the
position. Here the book was readable and confirmed nothing landed.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import LINK_BACKOFF_SEC, Engine, SymbolState
from micofx.models import SymbolConfig
from micofx.mt5client import AMBIGUOUS_RETCODES


def _engine():
    eng = object.__new__(Engine)
    eng._link_backoff = {}
    eng._orphan_scan = {}
    return eng


def _blocked(eng, symbol, state):
    """The gate at the top of _try_entry, in isolation."""
    until = float(eng._link_backoff.get(symbol, 0.0) or 0.0)
    if until > time.time():
        state.note = f"baglanti reddi - {int(until - time.time())}sn bekleniyor"
        state.entry_block = "baglanti_beklemede"
        return True
    return False


# --------------------------------------------------------------- the gate

def test_a_symbol_is_parked_after_a_link_refusal():
    eng = _engine()
    state = SymbolState("UK100")
    eng._link_backoff["UK100"] = time.time() + LINK_BACKOFF_SEC
    assert _blocked(eng, "UK100", state)
    assert state.entry_block == "baglanti_beklemede"


def test_the_park_expires_on_its_own():
    eng = _engine()
    state = SymbolState("UK100")
    eng._link_backoff["UK100"] = time.time() - 1.0
    assert not _blocked(eng, "UK100", state)


def test_only_the_refused_symbol_waits():
    eng = _engine()
    eng._link_backoff["UK100"] = time.time() + LINK_BACKOFF_SEC
    assert _blocked(eng, "UK100", SymbolState("UK100"))
    assert not _blocked(eng, "GER40", SymbolState("GER40"))


def test_a_symbol_that_never_failed_is_never_parked():
    assert not _blocked(_engine(), "GER40", SymbolState("GER40"))


# ------------------------------------------- which failures earn the wait

def _set_backoff_if_link(eng, symbol, retcode):
    """The branch _try_entry runs on a failed order result."""
    if retcode in AMBIGUOUS_RETCODES:
        eng._link_backoff[symbol] = time.time() + LINK_BACKOFF_SEC


@pytest.mark.parametrize("retcode", sorted(AMBIGUOUS_RETCODES))
def test_a_link_class_refusal_sets_the_wait(retcode):
    """10031 no-network and 10012 timeout - the pair that caused this."""
    eng = _engine()
    _set_backoff_if_link(eng, "UK100", retcode)
    assert eng._link_backoff.get("UK100", 0) > time.time()


@pytest.mark.parametrize("retcode", [10004, 10006, 10018, 10019, 0, None])
def test_an_ordinary_rejection_does_not(retcode):
    """A requote or a closed market says nothing about the link."""
    eng = _engine()
    _set_backoff_if_link(eng, "UK100", retcode)
    assert "UK100" not in eng._link_backoff


def test_the_storm_retcode_is_in_the_set():
    """10031 is what the 1090 rejections carried."""
    assert 10031 in AMBIGUOUS_RETCODES


# ---------------------------------------------------- the size of the win

def test_the_wait_is_long_enough_to_matter_and_short_enough_to_be_free():
    # Against a 2s cycle: without the wait a 40-minute outage costs 1090
    # verifications at 2.1s each; with it, roughly one per 30s per symbol.
    outage_sec = 40 * 60
    without = outage_sec / 2.2                    # measured rate, both symbols
    with_wait = (outage_sec / LINK_BACKOFF_SEC) * 2
    assert with_wait < without / 5, (without, with_wait)
    # And it must not eat a meaningful part of the shortest bar traded.
    assert LINK_BACKOFF_SEC <= 300 * 0.2


def test_the_signal_itself_is_never_dropped_by_the_wait():
    """Delayed, not discarded - the distinction from the ambiguous path."""
    eng = _engine()
    state = SymbolState("UK100")
    state.signal = "buy"
    state.signal_source = "primary"
    state.pending_bar_key = ("primary", 123)
    eng._link_backoff["UK100"] = time.time() + LINK_BACKOFF_SEC
    _blocked(eng, "UK100", state)
    assert state.signal == "buy"
    assert state.pending_bar_key == ("primary", 123)


def test_the_gate_is_actually_wired_into_try_entry():
    """A gate that exists only in this test file protects nothing."""
    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "engine.py").read_text(encoding="utf-8")
    body = src.split("def _try_entry(", 1)[1].split("\n    def ", 1)[0]
    assert "_link_backoff" in body
    assert "baglanti_beklemede" in body
    assert "AMBIGUOUS_RETCODES" in body


def test_verifier_failure_dict_must_carry_retcode():
    """Regression: verified-flat used to omit retcode, so the park never armed.

    open_market routes 10031 through _verify_ambiguous_send; Engine parks on
    verified_unfilled (and AMBIGUOUS retcodes). Pin both bridges in source.
    """
    root = Path(__file__).resolve().parents[1]
    mt5_src = (root / "micofx" / "mt5client.py").read_text(encoding="utf-8")
    eng_src = (root / "micofx" / "engine.py").read_text(encoding="utf-8")
    verify = mt5_src.split("def _verify_ambiguous_send(", 1)[1].split("\n    def ", 1)[0]
    assert "retcode:" in verify or "retcode=" in verify
    assert '"retcode": retcode' in verify
    assert "verified_unfilled" in verify
    assert "yeni pozisyon olusmamis" in verify
    assert any('"retcode": retcode' in ln for ln in verify.splitlines())
    fail_branch = eng_src.split("if not result.get(\"ok\"):", 1)[1].split("\n            if result.get(\"ambiguous\")", 1)[0]
    assert "verified_unfilled" in fail_branch
    assert "_link_backoff" in fail_branch
