"""Thin all-loss with stamped edge must watch — live JPN hole (Claude/agent).

JPN showed PF 0.00 over 1 deal at risk_scale 1.0 while NAS was watch@0.6
from autopsy. watch_min_trades and count_is_damning both miss n=1 all-loss
when holdout WR is ~37% (P(W=0)≈0.63 > 5%). Stamped positive expected_r
means the book still believes in the name — sizing down is the soft response,
not idle@1.0.

Unstamped thin all-loss stays ok (USDJPY n=4 in test_watch_on_thin_but_damning).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, Supervisor


class _Store:
    def __init__(self, cfg):
        self.symbols = {cfg.symbol: cfg}
        self.data = {"supervisor": {}}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _judge(nets: list[float], *, holdout_exp: float | None,
           holdout_wr: float | None = 37.0,
           cfgs: dict | None = None):
    cfg = SymbolConfig(symbol="JPN225", magic=900002)
    hold: dict = {"trades": 400}
    if holdout_wr is not None:
        hold["win_rate"] = holdout_wr
    if holdout_exp is not None:
        hold["expectancy"] = holdout_exp
    cfg.opt_summary = {"holdout": hold}
    # holdout_expectancy reads expectancy from stamp
    if holdout_exp is not None:
        cfg.opt_summary["holdout"]["expectancy"] = holdout_exp
        cfg.opt_summary["score"] = 1.0
    sup = Supervisor.__new__(Supervisor)
    sup._lock = threading.RLock()
    sup.store = _Store(cfg)
    # Autopsy empty so rescue path stays quiet
    sup.store.data["trade_autopsies"] = []
    sup.risk_scale = 1.0
    sup.verdicts = {}
    sup.notes = []
    sup.last_review = 0.0
    trades = [
        {
            "profit": float(n), "commission": 0.0, "swap": 0.0,
            "time": float(1_700_000_000 + i * 3600), "symbol": "JPN225",
        }
        for i, n in enumerate(nets)
    ]
    return sup._judge(cfg, trades, dict(cfgs or DEFAULTS))


def test_single_loss_with_stamped_edge_is_watch():
    """Live JPN shape: n=1, PF 0, expected_r > 0 → soft size cut."""
    v = _judge([-10.46], holdout_exp=0.327)
    assert v.trades == 1 and v.wins == 0
    assert v.expected_r > 0
    assert v.state == "watch", v.reason
    assert v.risk_scale == DEFAULTS["watch_risk_scale"]
    assert "kenar" in v.reason.lower() or "lot" in v.reason.lower() or "pf" in v.reason.lower()


def test_unstamped_thin_all_loss_still_ok():
    """USDJPY-class: no edge stamp → do not invent a watch from n=4."""
    v = _judge([-1.0] * 4, holdout_exp=None, holdout_wr=None)
    # Clear stamp entirely
    cfg = SymbolConfig(symbol="USDJPY", magic=900003)
    sup = Supervisor.__new__(Supervisor)
    import threading as th
    sup._lock = th.RLock()
    store = _Store(cfg)
    store.data["trade_autopsies"] = []
    sup.store = store
    sup.risk_scale = 1.0
    sup.verdicts = {}
    sup.notes = []
    trades = [
        {"profit": -1.0, "commission": 0.0, "swap": 0.0,
         "time": float(1_700_000_000 + i * 3600), "symbol": "USDJPY"}
        for i in range(4)
    ]
    v = sup._judge(cfg, trades, dict(DEFAULTS))
    assert v.state == "ok", v.reason


def test_thin_all_loss_zero_edge_stamp_left_alone():
    """Stamp present but expected_r ~0 → not the 'edge believed' hole."""
    v = _judge([-1.0], holdout_exp=0.0)
    assert v.state == "ok", v.reason
