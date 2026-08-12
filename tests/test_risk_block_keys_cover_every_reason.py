"""Every refusal can_open can produce must land in a named counter.

``_RISK_BLOCK_KEYS`` maps a refusal reason onto a stable counter key by matching
a prefix of the text, and anything unrecognised falls into a catch-all. The map
is maintained by hand while the reasons live in ``risk.can_open``, so the two
drift the moment someone adds a refusal without adding a needle - and the only
symptom is entries being refused into a bucket that does not say why.

That is not hypothetical reading. The stored counter still carries eight
``risk_limiti`` entries on JPN225, US500, GER40 and US30, recorded before the
granular keys existed and never reset since. Every reason can_open produces
today maps to a specific key, so nothing new reaches that bucket - which is
exactly why those eight took two separate investigations to explain: the
catch-all name is shared between "old data under a retired label" and "a reason
we cannot explain", and nothing distinguishes them.

Renaming the catch-all was the tempting fix and is deliberately not done here -
test_risk_block_keys.py states the reason it exists ("the key space must not
grow from text a caller composes") and a relabel buys nothing behavioural. The
drift itself is what is worth guarding: the map lives in engine.py while the
reasons live in risk.can_open, so a refusal added without a needle silently
starts landing in the catch-all. That now fails here instead of surfacing three
weeks later as a count nobody can account for.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import _RISK_BLOCK_KEYS, _risk_block_key

ROOT = Path(__file__).resolve().parents[1]


def _refusal_texts() -> list[str]:
    """Every literal reason risk.can_open hands back with Verdict(False, ...)."""
    source = (ROOT / "micofx" / "risk.py").read_text(encoding="utf-8")
    start = source.index("    def can_open(")
    end = source.index("\n    def ", start + 10)
    body = source[start:end]
    out: list[str] = []
    for raw in re.findall(r'Verdict\(False,\s*f?"([^"]+)"', body):
        # f-string holes carry the limit value; the needles match the prefix,
        # so any placeholder text stands in for a real number.
        out.append(re.sub(r"\{[^}]*\}", "9", raw))
    return out


def test_the_refusals_were_actually_found():
    """Guards the parser above from passing by matching nothing."""
    texts = _refusal_texts()
    assert len(texts) >= 5, f"can_open'dan sebep cikarilamadi: {texts}"


@pytest.mark.parametrize("reason", _refusal_texts())
def test_every_can_open_refusal_maps_to_a_named_key(reason):
    key = _risk_block_key(reason)
    named = {k for _, k in _RISK_BLOCK_KEYS}
    assert key in named, (
        f"{reason!r} adlandirilmis bir sayaca dusmuyor -> {key!r}; "
        f"_RISK_BLOCK_KEYS'e bir esleme ekleyin")


def test_the_catch_all_is_outside_the_named_set():
    """Whatever it is called, an unrecognised reason must not be mistaken for
    one of the specific buckets."""
    assert _risk_block_key("bambaska bir sebep") not in {k for _, k in _RISK_BLOCK_KEYS}


def test_an_empty_reason_does_not_crash():
    assert _risk_block_key("") not in {k for _, k in _RISK_BLOCK_KEYS}
    assert _risk_block_key(None) not in {k for _, k in _RISK_BLOCK_KEYS}


def test_matching_is_case_insensitive():
    """can_open capitalises the bucket kind (Scalp/Swing)."""
    assert _risk_block_key("Scalp pozisyon limiti (3)") == "risk_kova_limiti"
    assert _risk_block_key("SEMBOL POZISYON LIMITI (10)") == "risk_sembol_limiti"


def test_the_more_specific_needle_wins():
    """"sembol pozisyon limiti" also contains "pozisyon limiti"; order matters."""
    assert _risk_block_key("sembol pozisyon limiti (10)") == "risk_sembol_limiti"
    assert _risk_block_key("toplam pozisyon limiti (12)") == "risk_toplam_limit"
