"""A symbol that has never lost must not be judged by how many dollars it made.

`Supervisor._pf` was fixed for exactly this, but `_judge` did not call it - it
carried its own inline copy of the same arithmetic:

    v.profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else (
        round(gross_win, 2) if gross_win > 0 else 0.0)

With no losing trade the "profit factor" is the raw win SUM in account
currency, while every threshold it meets is a dimensionless ratio. The unit
changes silently and only for the best possible record.

Visible live at the time of writing: GBPJPY, 1 trade, 1 win, 0 losses, net
$0.20, reported as `PF 0.20` - a flawless record wearing a catastrophic score.

Both consequences are reachable at the live settings:

  * `trades >= min_trades (50) and profit_factor < quarantine_pf (0.80)` calls
    _quarantine(): a hard 12-hour block at risk_scale 0.0. Fifty winning trades
    totalling under $0.80 earn it. Sub-dollar wins are not hypothetical here -
    GBPJPY's only closed trade made $0.20.
  * `trades >= watch_min_trades (25) and profit_factor < watch_pf (1.00)` sets
    state "watch" at 0.6x. And while the day is in drawdown, prefer_strong_on_dd
    turns "watch" into a complete refusal (effective_scale 0.0) - which is what
    NAS100/XAUUSD/JPN225 are living under right now, legitimately.

So a perfect winning streak could be quarantined for it, or blocked outright.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, PF_NO_LOSSES, Supervisor


class _Store:
    def __init__(self, symbols):
        self.symbols = symbols
        self.data = {"supervisor": {}}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _sup() -> Supervisor:
    cfg = SymbolConfig(symbol="TEST", magic=900001)
    sup = Supervisor.__new__(Supervisor)
    sup._lock = threading.RLock()
    sup.store = _Store({"TEST": cfg})
    sup.risk_scale = 1.0
    sup.verdicts = {}
    sup.notes = []
    sup.last_review = 0.0
    return sup


def _trades(nets: list[float], hour_spread: bool = True) -> list[dict]:
    """One closed round trip per net. Spread across hours so the per-hour
    rules (which bucket by hour-of-day) never collapse onto one bucket."""
    out = []
    for i, net in enumerate(nets):
        # 3600s apart -> a different hour each time, so _bad_hours never sees
        # bad_hour_min_trades in any single bucket and cannot interfere.
        t = 1_700_000_000 + (i * 3600 if hour_spread else 0)
        out.append({"profit": float(net), "commission": 0.0, "swap": 0.0,
                    "time": float(t), "symbol": "TEST"})
    return out


def _judge(nets: list[float], **overrides):
    sup = _sup()
    cfgs = dict(DEFAULTS)
    cfgs.update(overrides)
    return sup._judge(sup.store.symbols["TEST"], _trades(nets), cfgs)


# ------------------------------------------------------- the unit must not change

@pytest.mark.parametrize("nets", [
    [0.05] * 30,     # $1.50 total
    [0.02] * 30,     # $0.60 - used to read as "PF 0.60", below quarantine_pf
    [0.20],          # GBPJPY's actual live trade
    [5.00] * 30,
])
def test_a_record_with_no_losses_reports_the_same_score_whatever_it_made(nets):
    assert _judge(nets).profit_factor == PF_NO_LOSSES


def test_the_dollar_size_of_the_wins_no_longer_decides():
    assert _judge([0.02] * 30).profit_factor == _judge([5.00] * 30).profit_factor


def test_the_single_live_trade_that_exposed_this():
    """GBPJPY: 1 trade, +$0.20, 0 losses - was reported as PF 0.20."""
    v = _judge([0.20])
    assert v.wins == 1 and v.losses == 0
    assert v.profit_factor != 0.20, "kayipsiz kayit hala dolar toplamini raporluyor"
    assert v.profit_factor >= 1.0


# ------------------------------------------------------ the two reachable gates

def test_fifty_winning_trades_worth_pennies_are_not_quarantined():
    """`trades >= min_trades and profit_factor < quarantine_pf` -> 12h block."""
    v = _judge([0.01] * DEFAULTS["min_trades"])
    assert v.profit_factor >= DEFAULTS["quarantine_pf"]
    assert v.state != "quarantine", f"kusursuz seri karantinaya girdi: {v.reason}"
    assert v.quarantine_until == 0.0


def test_a_flawless_run_is_not_put_on_watch_and_throttled():
    """`trades >= watch_min_trades and profit_factor < watch_pf` -> 0.6x, and a
    complete refusal while the day is in drawdown."""
    v = _judge([0.01] * DEFAULTS["watch_min_trades"])
    assert v.profit_factor >= DEFAULTS["watch_pf"]
    assert v.state == "ok", f"kusursuz seri watch'a dustu: {v.reason}"
    assert v.risk_scale == 1.0


def test_edge_health_stays_inside_its_clamp():
    """edge_health = clamp(pf / 1.2, 0, 3) - the sentinel must not escape it."""
    v = _judge([0.05] * 30)
    assert 0.0 <= v.edge_health <= 3.0


# ------------------------------------------------------- what must keep working

def test_a_real_ratio_is_untouched():
    assert _judge([2.0] * 3 + [-1.0] * 3).profit_factor == pytest.approx(2.0)
    assert _judge([1.0] * 3 + [-2.0] * 3).profit_factor == pytest.approx(0.5)


def test_a_genuinely_bad_symbol_is_still_quarantined():
    v = _judge([1.0] * 10 + [-4.0] * 40)
    assert v.profit_factor < DEFAULTS["quarantine_pf"]
    assert v.state == "quarantine"


def test_a_weak_but_not_awful_symbol_is_still_watched():
    # Interleaved: a 13-long losing tail would trip the streak quarantine
    # (quarantine_losses=10) before PF was ever consulted.
    v = _judge([1.0, -1.2] * 13)
    assert v.profit_factor < DEFAULTS["watch_pf"]
    assert v.state == "watch"
    assert v.risk_scale == DEFAULTS["watch_risk_scale"]


def test_an_all_losing_run_is_still_zero_and_quarantined():
    v = _judge([-1.0] * DEFAULTS["min_trades"])
    assert v.profit_factor == 0.0
    assert v.state == "quarantine"


def test_no_trades_at_all_is_idle():
    sup = _sup()
    v = sup._judge(sup.store.symbols["TEST"], [], dict(DEFAULTS))
    assert v.state == "idle"


def test_the_score_is_json_safe():
    """It reaches the panel through /api/ai; Infinity is not valid JSON."""
    import json
    encoded = json.dumps({"pf": _judge([0.05] * 30).profit_factor})
    assert "Infinity" not in encoded and "NaN" not in encoded, encoded
