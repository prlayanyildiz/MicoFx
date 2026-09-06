"""``capture_book`` validates its own timeframe override.

Found by the 05.09 stale-code sweep. The override was validated only by the
single HTTP caller in ``web/app.py``, so a direct call - a script, a future
caller, an agent - could pass a retired bar. ``mt5client.timeframe_const``
falls back rather than raising (correctly: one bad row must not take the engine
down), so "M5" would have produced M30 bars written to
``holdout_bars/<SYM>_M5.npz``: a snapshot whose filename disagrees with its
contents, behind one WARN line. Every measurement reading that file afterwards
would have believed it was M5 data.

Nothing reached that path in practice. This pins the refusal so nothing can.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import holdout_cost
from micofx.models import TIMEFRAMES, SymbolConfig
from tests.retired_lexicon import RETIRED_TIMEFRAMES


class _Store:
    def __init__(self):
        self.symbols = {
            "XAUUSD": SymbolConfig(symbol="XAUUSD", magic=1, enabled=True,
                                   timeframe="M15"),
        }

    def get_setting(self, key, default=None):
        return default


class _Client:
    """Fails loudly if reached - a refused call must not touch the terminal."""

    connected = True

    def bars(self, *a, **k):
        raise AssertionError("capture_book reddetmeden terminale gitti")

    def info(self, symbol):
        raise AssertionError("capture_book reddetmeden terminale gitti")


@pytest.mark.parametrize("bad", RETIRED_TIMEFRAMES)
def test_a_retired_override_is_refused(bad):
    with pytest.raises(ValueError) as err:
        holdout_cost.capture_book(client=_Client(), store=_Store(),
                                  timeframes=[bad])
    assert bad in str(err.value)


def test_a_mixed_override_is_refused_whole():
    """One bad name refuses the call rather than silently capturing the rest.

    Partial success would leave a book half-pinned with no signal that the
    other half was dropped.
    """
    with pytest.raises(ValueError):
        holdout_cost.capture_book(client=_Client(), store=_Store(),
                                  timeframes=["M30", "M5"])


def test_a_live_bar_is_not_refused_by_the_new_guard():
    """The guard must reject retired bars only - it is not a kill switch.

    A legal bar must get past validation and reach the per-symbol capture loop,
    which catches one symbol's failure into a WARN row rather than raising. So
    "returned a row for this timeframe" is the proof it was not refused -
    a refusal raises ValueError before any row exists.
    """
    for tf in TIMEFRAMES:
        out = holdout_cost.capture_book(client=_Client(), store=_Store(),
                                        timeframes=[tf])
        rows = out.get("results") if isinstance(out, dict) else None
        assert rows, f"{tf} icin satir yok - gecerli bar reddedilmis olabilir"
        assert any(r.get("timeframe") == tf for r in rows), tf
