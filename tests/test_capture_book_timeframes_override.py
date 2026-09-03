"""capture_book can pin an explicit TF list (M5 bake-off)."""
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
    out = capture_book(client=object(), store=store, timeframes=["M5"])
    assert out["captured"] == 2
    assert set(calls) == {("XAUUSD", "M5"), ("US30", "M5")}
