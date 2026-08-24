"""Say which risk gate refused an entry, instead of collapsing all of them.

Every can_open() refusal was counted as one "risk_limiti" bucket. Reading the
tally to find out why the ensemble's second leg never fills, that was not
enough: establishing it is refused for signalling AGAINST an open primary
position - rather than for hitting a count limit - took an elimination
argument across three unrelated settings (max_positions at 10, four positions
open against a cap of 100, scalp/swing buckets switched off).

The counter should just say so. Nine of the twenty-six blocked secondary
signals were the opposite-direction refusal, and knowing that changes what to
do about the ensemble: a tighter spread ceiling is a calibration problem and
might clear, while two legs disagreeing on direction is structural and will
not.

Matched on the stable prefix of each reason, since most carry their limit
value in the text. An unrecognised reason keeps the old bucket rather than
growing the key space from a string the caller composes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import _risk_block_key


@pytest.mark.parametrize("reason,key", [
    ("sembol pozisyon limiti (10)", "risk_sembol_limiti"),
    ("sembol pozisyon limiti (1)", "risk_sembol_limiti"),
    ("ters yonde acik pozisyon var", "risk_ters_yon"),
    ("toplam pozisyon limiti (100)", "risk_toplam_limit"),
    ("scalp pozisyon limiti (3)", "risk_kova_limiti"),
    ("swing pozisyon limiti (5)", "risk_kova_limiti"),
    ("marj hesaplanamadi", "risk_marj_okunamadi"),
    ("serbest marj yetersiz (10 < 20+5)", "risk_serbest_marj"),
    ("marj kullanimi limiti (%80.0 > %70)", "risk_marj_kullanimi"),
    ("eszamanli risk limiti (%8.5 > %8)", "risk_eszamanli"),
    ("stopsuz acik pozisyon", "risk_stopsuz"),
])
def test_each_refusal_gets_its_own_bucket(reason, key):
    assert _risk_block_key(reason) == key


def test_the_two_position_limits_are_not_confused():
    """Per-symbol and per-bucket both end in 'pozisyon limiti'; order matters."""
    assert _risk_block_key("sembol pozisyon limiti (10)") == "risk_sembol_limiti"
    assert _risk_block_key("toplam pozisyon limiti (100)") == "risk_toplam_limit"
    assert _risk_block_key("scalp pozisyon limiti (3)") == "risk_kova_limiti"


@pytest.mark.parametrize("reason", ["", None, "bilinmeyen sebep", "gunluk limit", 0])
def test_an_unrecognised_reason_keeps_the_old_bucket(reason):
    """The key space must not grow from text a caller composes."""
    assert _risk_block_key(reason) == "risk_limiti"


def test_the_keys_are_a_closed_set():
    from micofx.engine import _RISK_BLOCK_KEYS

    keys = {k for _, k in _RISK_BLOCK_KEYS} | {"risk_limiti"}
    assert len(keys) == len(_RISK_BLOCK_KEYS) + 1
    assert all(k.startswith("risk_") for k in keys)


def test_every_can_open_refusal_maps_to_something_specific():
    """A refusal added to risk.py without a key here silently becomes generic."""
    import re

    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "risk.py").read_text(encoding="utf-8")
    body = src.split("def can_open(", 1)[1].split("\n    def ", 1)[0]
    reasons = re.findall(r'Verdict\(False,\s*f?"([^"]+)"', body)
    assert reasons, "can_open reddi bulunamadi"
    generic = [r for r in reasons if _risk_block_key(r) == "risk_limiti"]
    assert not generic, f"kendi kovasi olmayan red sebebi: {generic}"


def test_the_engine_uses_it_at_the_can_open_gate():
    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "engine.py").read_text(encoding="utf-8")
    body = src.split("def _try_entry(", 1)[1].split("\n    def ", 1)[0]
    assert "_risk_block_key(verdict.reason)" in body
    assert 'state.entry_block = "risk_limiti"' not in body
