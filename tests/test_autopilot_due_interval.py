"""Autopilot due() respects interval; overlapping ticks are skipped."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.autopilot import AutoPilot


def _ap(enabled: bool = True, interval: float = 900.0) -> AutoPilot:
    store = SimpleNamespace(
        system=SimpleNamespace(
            autopilot_enabled=enabled,
            autopilot_interval_sec=interval,
            charge_costs=True,
            autostart_bot=True,
            lot_multiplier=1.0,
            max_margin_usage_pct=50.0,
            max_concurrent_risk_pct=8.0,
            block_high_cost=True,
            max_cost_pct_of_risk=18.0,
        ),
        symbols={},
        update_system=lambda *_a, **_k: store.system,
        update_symbol=lambda *_a, **_k: None,
    )
    eng = SimpleNamespace(
        store=store,
        client=SimpleNamespace(connected=True),
        supervisor=SimpleNamespace(
            optimizer=SimpleNamespace(busy=False),
            update_settings=lambda patch: patch,
            status=lambda: {"verdicts": {}},
        ),
        entry_blocks=lambda: {"since": 1.0, "rows": []},
        _positions=[],
        _account={},
        _capacity_cache={},
    )
    return AutoPilot(eng)


def test_due_false_when_disabled():
    ap = _ap(enabled=False)
    assert ap.due() is False


def test_due_respects_interval():
    ap = _ap(interval=60.0)
    assert ap.due() is True
    ap.last_tick_at = time.time()
    assert ap.due() is False
    ap.last_tick_at = time.time() - 61.0
    assert ap.due() is True


def test_overlap_skips_second_tick():
    ap = _ap(interval=1.0)
    held = []

    def slow_blocks():
        held.append(1)
        # Simulate a long tick while a second call tries the gate.
        time.sleep(0.05)
        return {"since": 1.0, "rows": []}

    ap.engine.entry_blocks = slow_blocks
    import threading
    results: list[list[str]] = []

    def run() -> None:
        results.append(ap.tick())

    t1 = threading.Thread(target=run)
    t2 = threading.Thread(target=run)
    t1.start()
    time.sleep(0.01)
    t2.start()
    t1.join()
    t2.join()
    assert any("onceki" in " ".join(r).lower() or "devam" in " ".join(r).lower()
               for r in results)
