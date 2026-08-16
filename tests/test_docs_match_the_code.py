"""Docs must not claim a strategy or timeframe the code does not have.

README said "20 strateji ailesi" and MASTER_PROMPT listed 14 including two that
were retired and whose indicators are gone - a reader (or an agent) planning
work off those files would plan around families that cannot be selected. The
count and the names are derivable, so nothing has to be kept in sync by hand.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import STRATEGIES, TIMEFRAMES

ROOT = Path(__file__).resolve().parents[1]
DOCS = ["README.md", "MASTER_PROMPT.md"]
RETIRED = ("trix_flip", "flow_rev", "t3_ribbon", "squeeze_brk", "orb",
           "vwap_rev", "donchian", "liq_sweep")
RETIRED_TF = ("H1", "H4", "M10", "M1 ", "M3 ")


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_the_family_count_matches_the_code():
    for name in DOCS:
        for hit in re.findall(r"(\d+)\s+(?:strateji\s+)?aile", _read(name)):
            assert int(hit) == len(STRATEGIES), (
                f"{name}: '{hit} aile' yaziyor, kodda {len(STRATEGIES)} var")


# Bir emekli ismin gecmesi tek basina hata degil - "su aileler kaldirildi"
# notu tam olarak gecmesi gereken yer. Aranan sey, isminin **kaldirildigini
# soylemeden** gecmesi. O yuzden satirin kendisine degil, etrafindaki iki
# satirlik pencereye bakiyoruz.
GONE_WORDS = ("kaldirildi", "kaldirilmis", "silindi", "emekli", "retired",
              "gone", "artik yok")


def _says_removed(lines: list[str], i: int) -> bool:
    window = " ".join(lines[max(0, i - 2):i + 3]).lower()
    return any(w in window for w in GONE_WORDS)


def test_a_retired_family_is_not_presented_as_live():
    for name in DOCS:
        lines = _read(name).splitlines()
        for i, line in enumerate(lines):
            for fam in RETIRED:
                # Kelime siniri sart: "orb" duz arandiginda "forbidding"
                # icinde eslesiyor ve bekci kendi yanlis pozitifini uretiyor.
                if re.search(rf"{re.escape(fam)}", line) and not _says_removed(lines, i):
                    assert False, (
                        f"{name}:{i+1} emekli aile '{fam}' canliymis gibi geciyor: "
                        f"{line[:70]}")


def test_a_retired_timeframe_is_not_presented_as_live():
    live = set(TIMEFRAMES)
    for name in DOCS:
        for line in _read(name).splitlines():
            for tf in RETIRED_TF:
                bare = tf.strip()
                if bare in live:
                    continue
                if re.search(rf"\b{bare}\b", line) and "emekli" not in line.lower():
                    assert False, f"{name}: emekli bar '{bare}' geciyor: {line[:70]}"
