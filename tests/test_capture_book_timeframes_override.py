"""capture_book can pin an explicit TF list across the book.

Written for the 03.09 M5 bake-off and pinned "M5" as the override. That bar was
retired 05.09 and ``capture_book`` now refuses a bar outside TIMEFRAMES, so the
override is exercised with a searched bar instead. The refusal itself is
covered in test_capture_book_refuses_a_retired_bar.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.holdout_cost import capture_book


def test_capture_book_honours_timeframes_override(monkeypatch, tmp_path):
    calls: list[tuple[str, str]] = []

    def fake_capture(*, client, store, symbol, timeframe, path=None):
        calls.append((symbol, timeframe))
        dest = tmp_path / f"{symbol}_{timeframe}.npz"
        dest.write_bytes(b"x")
        return dest

    monkeypatch.setattr("micofx.holdout_cost.capture", fake_capture)
    store = SimpleNamespace(symbols={
        "XAUUSD": SimpleNamespace(symbol="XAUUSD", timeframe="M15", enabled=True),
        "US30": SimpleNamespace(symbol="US30", timeframe="M30", enabled=True),
        "OFF": SimpleNamespace(symbol="OFF", timeframe="M30", enabled=False),
    })
    out = capture_book(client=object(), store=store, timeframes=["M15"])
    assert out["captured"] == 2
    assert set(calls) == {("XAUUSD", "M15"), ("US30", "M15")}
