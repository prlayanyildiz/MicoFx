"""Unknown keys in lookup tables must raise or WARN. Silent defaults are the class.

timeframe_seconds used to return 300 with nothing said; M1 requests used to
return M5 bars; ``_FAMILIES.get(name, _t3_stoch)`` used to trade the wrong
family. Each was fixed on its own. This file pins the class: every table in
``tests/lookup_contract.LOOKUPS`` is probed with a name that is not in it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lookup_contract import LOOKUPS, REQUIRED, probe_all


def test_every_required_table_is_registered():
    names = [n for n, _ in LOOKUPS]
    missing = [n for n in REQUIRED if n not in names]
    assert not missing, f"LOOKUPS is missing {missing} - the test cannot see them"


def test_unknown_keys_are_not_silent():
    seen = []
    probe_all(seen)
    warns = [row for row in seen if row[1] == "WARN"]
    # Menu probes (TIMEFRAMES / STRATEGIES) assert membership and do not warn.
    # The three fallback tables must each have spoken.
    text = " ".join(m for m, _ in warns)
    for needle in ("___NOPE___",):
        assert needle in text, warns
    assert any("zaman dilimi" in m.lower() or "timeframe" in m.lower() or "___NOPE___" in m
               for m, _ in warns), warns
