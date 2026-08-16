"""The per-hour size throttle must survive a restart.

hour_risk_scales is keyed by hour-of-day as an int; JSON has no integer keys,
so persisting {9: 0.62} and reading it back yields {"9": 0.62}. _gate_locked
looks it up with an int hour, so a restored map never matched and the throttle
silently returned 1.0 - a size cut earned by realised losing hours quietly not
applying.

Narrow in practice: last_review starts at 0.0, so the first cycle after a
restart runs review() and recomputes every verdict with int keys again. These
pin the round trip anyway - the restored state should be faithful rather than
depend on being overwritten quickly to stay harmless.
"""
from __future__ import annotations

import json
import time

import pytest

from micofx.supervisor import DEFAULTS, Supervisor, SymbolVerdict


class _Store:
    """Store stand-in that round-trips through JSON exactly like the real one."""

    def __init__(self) -> None:
        self._rows: dict[str, str] = {}
        self.symbols: dict = {}

    def get_setting(self, key, default=None):
        raw = self._rows.get(key)
        return default if raw is None else json.loads(raw)

    def set_setting(self, key, value):
        self._rows[key] = json.dumps(value, ensure_ascii=False)


class _Cfg:
    def __init__(self, symbol="NAS100"):
        self.symbol = symbol
        self.magic = 7
        self.opt_summary = {}


def _supervisor(store):
    return Supervisor(store, client=None)


def _persisted_with(scales) -> _Store:
    store = _Store()
    sup = _supervisor(store)
    v = SymbolVerdict(symbol="NAS100", state="ok")
    v.hour_risk_scales = scales
    sup.verdicts["NAS100"] = v
    sup._persist()
    return store


def test_hour_keys_really_become_strings_on_disk():
    # The premise of the bug, asserted directly so the test cannot pass for the
    # wrong reason if the storage format ever changes.
    store = _persisted_with({9: 0.62})
    raw = store._rows["supervisor_state"]
    assert '"9"' in raw


def test_restored_map_is_keyed_by_int_again():
    store = _persisted_with({9: 0.62, 14: 0.45})
    restored = _supervisor(store).verdicts["NAS100"].hour_risk_scales
    assert restored == {9: pytest.approx(0.62), 14: pytest.approx(0.45)}


def test_the_throttle_still_applies_after_a_restart(monkeypatch):
    store = _persisted_with({9: 0.5})
    store.set_setting("supervisor", {**DEFAULTS, "prefer_strong_on_dd": False})
    sup = _supervisor(store)

    # 09:xx local - the hour the throttle was earned in.
    monkeypatch.setattr(time, "gmtime", lambda _t=None: time.struct_time(
        (2026, 8, 10, 9, 30, 0, 0, 222, 0)))

    allowed, reason, scale = sup.gate(_Cfg(), 0.0)
    assert allowed is True
    assert reason == ""
    assert scale == pytest.approx(0.5)


def test_an_unthrottled_hour_is_left_alone(monkeypatch):
    store = _persisted_with({9: 0.5})
    store.set_setting("supervisor", {**DEFAULTS, "prefer_strong_on_dd": False})
    sup = _supervisor(store)

    monkeypatch.setattr(time, "gmtime", lambda _t=None: time.struct_time(
        (2026, 8, 10, 15, 30, 0, 0, 222, 0)))

    _allowed, _reason, scale = sup.gate(_Cfg(), 0.0)
    assert scale == pytest.approx(1.0)


@pytest.mark.parametrize("junk", [
    {"nope": 0.5},        # unparseable hour
    {"9": "abc"},         # unparseable scale
    {"99": 0.5},          # not an hour of the day
    "not a dict",
    None,
])
def test_unusable_entries_are_dropped_not_kept_inert(junk):
    # A key that can never match reads as "this hour is fine" - exactly the
    # failure this map exists to prevent, so drop it rather than carry it.
    store = _persisted_with(junk)
    restored = _supervisor(store).verdicts["NAS100"].hour_risk_scales
    assert restored == {}
