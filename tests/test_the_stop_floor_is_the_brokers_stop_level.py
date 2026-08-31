"""The freeze zone was widening every stop, and every stop widens shrinks a lot.

``min_stop_distance`` took ``max(stops_level, freeze_level)``. Those are two
different broker numbers:

* ``trade_stops_level`` is the minimum distance a stop may sit from price -
  exactly what this function is for.
* ``trade_freeze_level`` is a no-modify window around the market: inside it the
  broker refuses *changes* to an existing order. It says nothing about how far
  away a stop has to be placed.

Folding the freeze zone into the floor widened ``sl_dist = max(atr * sl_mult,
min_stop)``, and the lot is risk divided by that distance - so on any symbol
whose freeze level exceeds its stop level, every entry was sized smaller than
the risk model asked for, permanently.

``freeze_level`` is kept as a fallback for brokers that report ``stops_level``
as 0 while still refusing stops at market; dropping it outright there would
replace an over-wide stop with a rejected order.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.mt5client import MT5Client

POINT = 0.01


def _client(monkeypatch, *, stops_level, freeze_level, spread=0.0):
    c = object.__new__(MT5Client)
    monkeypatch.setattr(MT5Client, "info", lambda self, s: {
        "point": POINT, "stops_level": stops_level, "freeze_level": freeze_level,
    })
    monkeypatch.setattr(MT5Client, "tick",
                        lambda self, s: {"spread": spread} if spread else None)
    return c


# ------------------------------------------------------------- the defect

def test_a_wide_freeze_zone_does_not_widen_the_stop(monkeypatch):
    c = _client(monkeypatch, stops_level=20, freeze_level=500)
    assert MT5Client.min_stop_distance(c, "GER40") == 20 * POINT


def test_the_stop_level_is_what_binds(monkeypatch):
    c = _client(monkeypatch, stops_level=300, freeze_level=50)
    assert MT5Client.min_stop_distance(c, "GER40") == 300 * POINT


# --------------------------------------------------- what must keep working

def test_freeze_level_still_covers_a_broker_reporting_no_stop_level(monkeypatch):
    """0 stops_level with a real freeze zone must not become a stop at market."""
    c = _client(monkeypatch, stops_level=0, freeze_level=200)
    assert MT5Client.min_stop_distance(c, "GER40") == 200 * POINT


def test_the_spread_floor_still_applies(monkeypatch):
    c = _client(monkeypatch, stops_level=1, freeze_level=0, spread=10.0)
    assert MT5Client.min_stop_distance(c, "GER40") == 15.0


def test_the_ten_point_floor_still_applies(monkeypatch):
    c = _client(monkeypatch, stops_level=0, freeze_level=0)
    assert MT5Client.min_stop_distance(c, "GER40") == 10 * POINT


def test_no_symbol_info_is_zero(monkeypatch):
    c = object.__new__(MT5Client)
    monkeypatch.setattr(MT5Client, "info", lambda self, s: None)
    assert MT5Client.min_stop_distance(c, "GER40") == 0.0
