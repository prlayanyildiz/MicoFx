"""A stop already at the wanted level was reported as a failed modify.

``modify_position`` returned False on ``TRADE_RETCODE_NO_CHANGES``.
``_update_stop`` reads that False as "the broker refused the update the trade
earned" and retries on the next poll - so for every bar where the trail does
not move, every open position paid a broker round trip per poll, forever, on
the same global MT5 lock every ``/api/state`` read queues behind.

The broker is saying the stop is where we asked for it. That is the success
condition, not a rejection.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import micofx.mt5client as mt5client
from micofx.mt5client import MT5Client


class _Result:
    def __init__(self, retcode, comment=""):
        self.retcode = retcode
        self.comment = comment
        self.order = 0
        self.deal = 0


def _client(monkeypatch, result):
    c = MT5Client("")
    monkeypatch.setattr(mt5client.mt5, "order_send", lambda req: result,
                        raising=False)
    monkeypatch.setattr(MT5Client, "resolve", lambda self, s: s)
    monkeypatch.setattr(MT5Client, "normalize_price",
                        lambda self, s, p: float(p))
    return c


def _no_changes_code():
    return getattr(mt5client.mt5, "TRADE_RETCODE_NO_CHANGES", 10025)


# ------------------------------------------------------------- the defect

def test_no_changes_reads_as_success(monkeypatch):
    c = _client(monkeypatch, _Result(_no_changes_code()))
    assert c.modify_position(1, 2000.0, 0.0, "XAUUSD") is True


def test_no_changes_does_not_emit_a_warn(monkeypatch):
    """It is not a failure, so it must not enter the SL-fail silence book."""
    c = _client(monkeypatch, _Result(_no_changes_code()))
    seen = []
    monkeypatch.setattr(MT5Client, "_emit_sltp_fail",
                        lambda self, *a: seen.append(a))
    c.modify_position(1, 2000.0, 0.0, "XAUUSD")
    assert seen == []


# --------------------------------------------------- what must keep working

def test_a_real_rejection_is_still_a_failure(monkeypatch):
    c = _client(monkeypatch, _Result(10016, "Invalid stops"))
    monkeypatch.setattr(MT5Client, "_emit_sltp_fail", lambda self, *a: None)
    assert c.modify_position(1, 2000.0, 0.0, "XAUUSD") is False


def test_a_none_result_is_still_a_failure(monkeypatch):
    c = _client(monkeypatch, None)
    monkeypatch.setattr(MT5Client, "_emit_sltp_fail", lambda self, *a: None)
    assert c.modify_position(1, 2000.0, 0.0, "XAUUSD") is False
