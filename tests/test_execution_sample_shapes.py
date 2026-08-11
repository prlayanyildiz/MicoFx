"""One malformed restored sample must not take the whole panel down.

_summarise reads row["adverse"] and row["leg"] without a default, which is
correct: record() always writes both, and the optional fields (r, money) are
already guarded with `in` checks. The gap was on the way back in - _restore
filtered rows to isinstance(r, dict) and stopped there, so a row missing
either key reached _summarise and raised KeyError.

Where that lands is what makes it worth closing: stats() is called by
/api/state on every panel poll, so a single bad row does not degrade the
execution view, it 500s the entire panel.

Not reachable from anything the current record() writes. This is a blob
restored from a backup written by an older row shape, or a hand-edited row -
the same class store's container guards cover, applied to the elements.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.execution import MAX_SAMPLES, ExecutionMonitor


class _Store:
    def __init__(self, data=None):
        self.data = data or {}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _monitor(samples):
    return ExecutionMonitor(_Store({"execution_samples": samples}))


GOOD = {"t": 1.0, "leg": "entry", "adverse": 0.5, "points": 2.0}

MALFORMED = [
    ("bos-sozluk", {}),
    ("alakasiz-alan", {"bozuk": True}),
    ("adverse-metin", {"adverse": "metin", "leg": "entry"}),
    ("adverse-eksik", {"leg": "entry"}),
    ("leg-eksik", {"adverse": 0.5}),
    ("leg-sayi", {"adverse": 0.5, "leg": 7}),
    ("adverse-bool", {"adverse": True, "leg": "entry"}),
    ("adverse-nan", {"adverse": float("nan"), "leg": "entry"}),
    ("adverse-inf", {"adverse": float("inf"), "leg": "entry"}),
    ("sozluk-degil", "satir"),
    ("none", None),
]


@pytest.mark.parametrize("name,row", MALFORMED, ids=[m[0] for m in MALFORMED])
def test_a_malformed_sample_does_not_break_stats(name, row):
    monitor = _monitor({"XAUUSD": [row]})
    stats = monitor.stats()                 # must not raise
    json.dumps(stats)                       # and must stay JSON safe
    assert stats["per_symbol"].get("XAUUSD", {}).get("samples", 0) == 0


@pytest.mark.parametrize("name,row", MALFORMED, ids=[m[0] for m in MALFORMED])
def test_a_malformed_sample_does_not_discard_the_good_ones(name, row):
    monitor = _monitor({"XAUUSD": [GOOD, row, dict(GOOD, adverse=-0.25)]})
    stats = monitor.stats()
    assert stats["per_symbol"]["XAUUSD"]["samples"] == 2
    assert stats["per_symbol"]["XAUUSD"]["adverse"] == 1
    assert stats["per_symbol"]["XAUUSD"]["favourable"] == 1


def test_healthy_samples_are_restored_untouched():
    """The guard must not quietly drop real history on every start."""
    rows = [dict(GOOD, adverse=0.1 * i, r=0.01 * i, money=1.0) for i in range(1, 6)]
    stats = _monitor({"XAUUSD": rows}).stats()
    assert stats["per_symbol"]["XAUUSD"]["samples"] == 5
    assert stats["total"]["samples"] == 5


def test_a_symbol_whose_rows_are_all_malformed_is_dropped_entirely():
    """No empty shell in per_symbol claiming a symbol has execution data."""
    stats = _monitor({"XAUUSD": [{}, {"bozuk": 1}]}).stats()
    assert "XAUUSD" not in stats["per_symbol"]


def test_record_still_produces_rows_that_pass_the_guard():
    """The round trip: whatever record() writes must survive _restore."""
    store = _Store()
    monitor = ExecutionMonitor(store)
    monitor.record("XAUUSD", "entry", 100.0, 100.5, True,
                   risk_dist=10.0, point=0.01, volume=0.1, money_per_price=10.0)
    # ...and the version with every optional field absent.
    monitor.record("XAUUSD", "stop", 100.0, 99.5, False)
    monitor._persist(force=True)

    restored = ExecutionMonitor(store)
    assert restored.stats()["per_symbol"]["XAUUSD"]["samples"] == 2


def test_the_sample_cap_still_holds():
    rows = [dict(GOOD) for _ in range(MAX_SAMPLES * 3)]
    monitor = _monitor({"XAUUSD": rows})
    assert monitor.stats()["per_symbol"]["XAUUSD"]["samples"] <= MAX_SAMPLES


def test_a_wrong_shaped_blob_is_ignored():
    for blob in ("metin", 42, ["liste"], {"XAUUSD": "liste-degil"}):
        stats = ExecutionMonitor(_Store({"execution_samples": blob})).stats()
        assert stats["per_symbol"] == {}
