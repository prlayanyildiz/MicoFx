"""Randomised stress on the ratchet invariants of Engine._update_stop.

The other trail tests pin named scenarios. This one walks random price paths
instead, in both directions and all three trail modes, and asserts on every
single stop the engine actually places:

  R1 ratchet    buy: the stop only ever rises; sell: only ever falls
  R2 min-stop   the placed stop respects the broker distance vs the LIVE quote
  R3 no giveback  once the stop is at or past entry it never returns behind it
  R4 risk floor   the stop is never placed at or beyond the original risk
  R5 step       every accepted move clears trail_min_step

Seeded, so a failure is reproducible rather than a story about a run nobody
can repeat. Deliberately a pytest module rather than a standalone script:
_update_stop calls LOG.emit at TRADE level on every placement, which is a
PERSISTED level, so running this outside pytest appends tens of thousands of
fake trade lines to the real logs/micofx.log - enough to blow past its 4MB
rotation cap and take the genuine history with it. tests/conftest.py's
autouse no_real_log_file fixture is what makes this safe, and it only applies
under pytest.
"""
from __future__ import annotations

import random

import numpy as np
import pytest

from micofx.engine import Engine
from micofx.exits import harvest_trail_step
from micofx.models import trail_min_step

TF_SEC = 300
BAR_OPEN = 1_000_000
ENTRY = 100.0


class _Bars:
    def __init__(self, closes, last_closed):
        self.close = np.asarray(closes, dtype=float)
        self.high = self.close + 0.5
        self.low = self.close - 0.5
        self._last = last_closed

    @property
    def last_closed_time(self):
        return self._last


class _Client:
    def __init__(self, min_stop):
        self.bid = ENTRY
        self.ask = ENTRY + 0.01
        self._min_stop = min_stop
        self.modify_ok = True
        self.modifies: list[float] = []

    def tick(self, symbol):
        return {"bid": self.bid, "ask": self.ask, "spread": self.ask - self.bid}

    def min_stop_distance(self, symbol):
        return self._min_stop

    def modify_position(self, ticket, sl, tp, symbol):
        self.modifies.append(sl)
        return self.modify_ok


class _Cfg:
    symbol = "FUZZ"
    magic = 7
    timeframe = "M5"
    harvest_at_r = 0.0
    harvest_step_atr = 0.0

    def __init__(self, sl_mult, start, step, mode, lookback,
                 harvest_at_r=0.0, harvest_step_atr=0.0):
        self.sl_atr_mult = sl_mult
        self.trail_start_atr = start
        self.trail_step_atr = step
        self.trail_mode = mode
        self.trail_lookback = lookback
        self.harvest_at_r = harvest_at_r
        self.harvest_step_atr = harvest_step_atr


def _engine(client) -> Engine:
    eng = Engine.__new__(Engine)      # no MT5 connect, no store
    eng.client = client
    eng.states = {}
    return eng


def _walk(rng: random.Random, side: str, mode: str, *,
          harvest_at_r: float = 0.0, harvest_step_atr: float = 0.0) -> int:
    atr = rng.uniform(0.2, 3.0)
    min_stop = rng.choice([0.0, 0.05, 0.5, 1.0, 2.5])
    cfg = _Cfg(sl_mult=rng.uniform(0.5, 3.0),
               start=rng.choice([0.1, 0.3, 0.5, 1.0, 2.0]),
               step=rng.choice([0.4, 0.8, 1.2, 1.6, 3.0]),
               mode=mode, lookback=rng.choice([3, 5, 10]),
               harvest_at_r=harvest_at_r, harvest_step_atr=harvest_step_atr)
    client = _Client(min_stop)
    eng = _engine(client)

    is_buy = side == "buy"
    original_risk = max(atr * cfg.sl_atr_mult, min_stop)
    pos = {"ticket": 1, "symbol": "FUZZ", "side": side,
           "sl": ENTRY - original_risk if is_buy else ENTRY + original_risk,
           "tp": 0.0, "price_open": ENTRY, "volume": 0.3, "magic": 7,
           "time": BAR_OPEN + 10}

    n = 60
    closes = [ENTRY]
    for _ in range(n):
        closes.append(closes[-1] + rng.gauss(0, atr * 0.6))
    closes = np.array(closes)

    past_breakeven = False
    for i in range(5, n):
        bars = _Bars(closes[: i + 1], BAR_OPEN + (i - 5) * TF_SEC)
        # The live quote wanders independently of the closed bar - that gap is
        # exactly what the min-stop clamp and the retry path exist for.
        client.bid = float(closes[i]) + rng.gauss(0, atr * 0.4)
        client.ask = client.bid + rng.uniform(0.0, 0.05)
        live = client.bid if is_buy else client.ask

        before = pos["sl"]
        sent = len(client.modifies)
        client.modify_ok = rng.random() > 0.15      # the broker rejects sometimes

        eng._update_stop(cfg, pos, atr, bars)

        if len(client.modifies) == sent or not client.modify_ok:
            continue
        placed = client.modifies[-1]
        ref = float(closes[i])
        profit = (ref - ENTRY) if is_buy else (ENTRY - ref)
        active = harvest_trail_step(
            trail_step_atr=cfg.trail_step_atr,
            harvest_at_r=cfg.harvest_at_r,
            harvest_step_atr=cfg.harvest_step_atr,
            profit=profit, original_risk=original_risk)
        step = trail_min_step(min_stop, atr, active)

        if before != 0:
            assert (placed > before) if is_buy else (placed < before), \
                f"R1 stop moved backwards {before} -> {placed} ({side}/{mode})"
            moved = (placed - before) if is_buy else (before - placed)
            assert moved >= step - 1e-9, f"R5 sub-step move {moved} < {step}"

        gap = (live - placed) if is_buy else (placed - live)
        assert gap >= min_stop - 1e-9, f"R2 min-stop violated: {gap} < {min_stop}"

        if is_buy:
            assert placed > ENTRY - original_risk - 1e-9, "R4 placed beyond original risk"
        else:
            assert placed < ENTRY + original_risk + 1e-9, "R4 placed beyond original risk"

        at_breakeven = (placed >= ENTRY) if is_buy else (placed <= ENTRY)
        if past_breakeven:
            assert at_breakeven, f"R3 gave back breakeven: {placed} vs entry {ENTRY}"
        past_breakeven = past_breakeven or at_breakeven

        pos["sl"] = placed

    return len(client.modifies)


@pytest.mark.parametrize("mode", ["atr", "structure", "hybrid"])
@pytest.mark.parametrize("side", ["buy", "sell"])
def test_the_ratchet_holds_over_random_price_paths(side, mode):
    # Seeded per (side, mode) so each case is independent and reproducible.
    rng = random.Random(f"{side}-{mode}-20260810")
    placed = sum(_walk(rng, side, mode) for _ in range(120))
    # Guards the fixture itself: a run that never placed a stop would pass
    # every assertion above without testing anything at all.
    assert placed > 100, f"only {placed} stops placed - the walk is not exercising the trail"


@pytest.mark.parametrize("mode", ["atr", "structure", "hybrid"])
@pytest.mark.parametrize("side", ["buy", "sell"])
def test_the_harvest_ratchet_holds_over_random_price_paths(side, mode):
    rng = random.Random(f"{side}-{mode}-harvest-20260826")
    placed = sum(
        _walk(rng, side, mode, harvest_at_r=1.5, harvest_step_atr=0.4)
        for _ in range(40))
    assert placed > 20, f"only {placed} harvest stops placed - walk is idle"
