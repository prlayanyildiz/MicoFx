"""Quarantine PF bar is per-symbol, calibrated to 5% FA on the stamp.

A single min_trades=80 false-alarms healthy XAUUSD ~13% of the time (SUP-4)
and almost never catches SpotBrent (FA ~0 at n=80). The count arm already
reads holdout win_rate (SUP-1). The PF arm must do the same: smallest n
whose P(PF_hat < quarantine_pf | stamp wr, PF) is <= 5%.

Fail-first against the live bar of 80:
  * XAUUSD at 80 trades and a broken PF still quarantines today.
  * SpotBrent at 8 trades and a broken PF cannot, because 8 < 80.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, Supervisor

# Live supervisor after HR-2 / SUP-2. Pin so DEFAULTS (25/10) cannot mask it.
LIVE = dict(DEFAULTS, min_trades=80, watch_min_trades=80, quarantine_losses=11,
            quarantine_pf=0.80, watch_pf=1.00)

XAUUSD_HOLD = {"win_rate": 24.72, "profit_factor": 1.1279, "trades": 538}
BRENT_HOLD = {"win_rate": 72.37, "profit_factor": 2.2471, "trades": 120}


class _Store:
    def __init__(self, cfg):
        self.symbols = {cfg.symbol: cfg}
        self.data = {"supervisor": {}}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _sup(symbol: str, hold: dict | None) -> Supervisor:
    cfg = SymbolConfig(symbol=symbol, magic=900001)
    if hold is not None:
        cfg.opt_summary = {"holdout": dict(hold)}
    sup = Supervisor.__new__(Supervisor)
    sup._lock = threading.RLock()
    sup.store = _Store(cfg)
    sup.risk_scale = 1.0
    sup.verdicts = {}
    sup.notes = []
    sup.last_review = 0.0
    return sup


def _trades(nets: list[float]) -> list[dict]:
    return [{"profit": float(n), "commission": 0.0, "swap": 0.0,
             "time": float(1_700_000_000 + i * 3600), "symbol": "TEST"}
            for i, n in enumerate(nets)]


def _judge(symbol: str, hold: dict | None, nets: list[float],
           cfgs: dict | None = None):
    sup = _sup(symbol, hold)
    return sup._judge(sup.store.symbols[symbol], _trades(nets),
                      dict(cfgs or LIVE))


def _broken(n: int, wins: int) -> list[float]:
    """n trades, PF well under 0.80, no 10-loss streak."""
    if wins <= 0:
        # Spread the losses across hours; still a streak of n, so callers
        # must keep n below quarantine_losses.
        return [-2.0] * n
    at = {round((i + 0.5) * n / wins) - 1 for i in range(wins)}
    out = [1.0 if i in at else -2.0 for i in range(n)]
    while sum(1 for x in out if x > 0) < wins:
        out[out.index(-2.0)] = 1.0
    return out


def test_xauusd_at_eighty_broken_trades_is_not_quarantined():
    """Today this fires: 80 >= min_trades and PF 0.5 < 0.80.

    XAUUSD's stamp needs n=127 before FA is 5%. Eighty is still noise.
    """
    nets = _broken(80, 32)  # PF = 32/96 = 0.33
    v = _judge("XAUUSD", XAUUSD_HOLD, nets)
    assert v.trades == 80
    assert v.profit_factor < LIVE["quarantine_pf"]
    assert v.consecutive_losses < LIVE["quarantine_losses"]
    assert v.state != "quarantine", v.reason


def test_spotbrent_at_eight_broken_trades_is_quarantined():
    """Today this cannot fire: 8 < min_trades=80.

    SpotBrent's stamp already has FA < 5% at n=8. A broken PF there is
    evidence, not noise.
    """
    nets = _broken(8, 4)  # PF = 4/8 = 0.50
    v = _judge("SpotBrent", BRENT_HOLD, nets)
    assert v.trades == 8
    assert v.profit_factor < LIVE["quarantine_pf"]
    assert v.consecutive_losses < LIVE["quarantine_losses"]
    assert v.state == "quarantine", v.reason


def test_no_stamp_falls_back_to_global_min_trades():
    nets = _broken(80, 32)
    v = _judge("XAUUSD", None, nets)
    assert v.state == "quarantine", v.reason


def test_watch_bar_is_not_derived_this_round():
    """Watch still reads watch_min_trades. XAUUSD at 80 is watch, not a
    raised per-symbol bar that would leave it at full size."""
    nets = _broken(80, 32)
    v = _judge("XAUUSD", XAUUSD_HOLD, nets)
    assert v.state == "watch", v.reason
    assert v.risk_scale == LIVE["watch_risk_scale"]


def test_derived_n_matches_sup4_book_stamps():
    """Analytic n vs SUP-4 MC (20k). Discrete CDF vs sampling: ± a few."""
    cfgs = dict(LIVE)
    cases = [
        ("XAUUSD", XAUUSD_HOLD, 127),
        ("SpotBrent", BRENT_HOLD, 8),
        ("GER40", {"win_rate": 27.43, "profit_factor": 1.213}, 80),
        ("JPN225", {"win_rate": 50.79, "profit_factor": 1.4291}, 30),
        ("NAS100", {"win_rate": 30.53, "profit_factor": 1.1422}, 106),
        ("US30", {"win_rate": 33.00, "profit_factor": 1.1922}, 80),
    ]
    for name, hold, expected in cases:
        cfg = SymbolConfig(symbol=name, magic=1)
        cfg.opt_summary = {"holdout": dict(hold)}
        got = Supervisor.quarantine_min_trades(cfg, cfgs)
        assert abs(got - expected) <= 5, f"{name}: {got} vs MC {expected}"


def test_pathological_stamp_is_capped():
    cfg = SymbolConfig(symbol="THIN", magic=1)
    cfg.opt_summary = {"holdout": {"win_rate": 8.0, "profit_factor": 1.02}}
    n = Supervisor.quarantine_min_trades(cfg, dict(LIVE))
    assert n == Supervisor.QUARANTINE_N_CAP
