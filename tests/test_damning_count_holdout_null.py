"""The thin-record watch branch used a coin-flip null. This book does not.

``wins < n/2 - sqrt(n)`` is two sigma below 50%. Trend followers in this
book win 25-37% of the time by design and make their money on payoff, so a
healthy GER40 at 2 wins in 11 (expected ~3) tripped watch 38% of the time.
USDCHF's hole was real; the reference was wrong.

Holdout ``win_rate`` is the null. No stamp, no count verdict - silence
beats a made-up coin. The trade-count bar (watch_min_trades) is unchanged.
"""
from __future__ import annotations

import math
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, Supervisor

# Live bar is 80 after HR-2; the gap the count branch exists to fill is
# everything below that. Tests pin it so they do not inherit DEFAULTS (10)
# or an older live 25.
CFGS = dict(DEFAULTS, watch_min_trades=80, min_trades=80, quarantine_losses=11)


class _Store:
    def __init__(self, cfg):
        self.symbols = {cfg.symbol: cfg}
        self.data = {"supervisor": {}}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _sup(holdout_wr=None) -> Supervisor:
    cfg = SymbolConfig(symbol="TEST", magic=900001)
    if holdout_wr is not None:
        cfg.opt_summary = {"holdout": {"win_rate": holdout_wr, "trades": 400}}
    sup = Supervisor.__new__(Supervisor)
    sup._lock = threading.RLock()
    sup.store = _Store(cfg)
    sup.risk_scale = 1.0
    sup.verdicts = {}
    sup.notes = []
    sup.reopt_queue = []
    sup.last_review = 0.0
    return sup


def _mix(wins: int, losses: int, win_size: float = 1.0, loss_size: float = 3.0):
    total = wins + losses
    if total == 0:
        return []
    at = {round((i + 0.5) * total / wins) - 1 for i in range(wins)} if wins else set()
    out = [win_size if i in at else -loss_size for i in range(total)]
    while sum(1 for x in out if x > 0) < wins:
        out[out.index(-loss_size)] = win_size
    return out


def _judge(nets, holdout_wr=None, cfgs=None):
    sup = _sup(holdout_wr)
    trades = [{"profit": float(n), "commission": 0.0, "swap": 0.0,
               "time": float(1_700_000_000 + i * 3600), "symbol": "TEST"}
              for i, n in enumerate(nets)]
    return sup._judge(sup.store.symbols["TEST"], trades, dict(cfgs or CFGS))


def test_healthy_trend_follower_at_n11_is_not_watch():
    """GER40 holdout wr 27.43%. Two wins in eleven is the coin-flip trigger
    (wins < 11/2 - sqrt(11) = 2.18) and a typical draw under 27%.

    Fail-first: the coin-flip null puts this on watch. The holdout null must
    not.
    """
    n, sqrt_n = 11, math.sqrt(11)
    assert 2 < n / 2.0 - sqrt_n, "2 wins still trips the coin-flip floor"
    v = _judge(_mix(2, 9), holdout_wr=27.43)
    assert v.trades == 11 and v.wins == 2
    assert v.profit_factor < CFGS["watch_pf"]
    assert v.consecutive_losses < CFGS["quarantine_losses"]
    assert v.state == "ok", f"saglikli wr%27 n=11 watch oldu: {v.reason}"


def test_no_holdout_win_rate_is_silent_on_the_count_branch():
    """PLTR's stamp had empty wr. Do not invent 50%."""
    v = _judge(_mix(1, 10), holdout_wr=None)
    assert v.trades == 11
    assert v.state == "ok"


def test_one_win_in_eleven_is_still_watch_against_a_50pct_holdout():
    """USDCHF shape, now with an honest FX-like null instead of a hardcoded
    coin. P(X<=1 | n=11, p=0.5) ~ 0.006."""
    v = _judge(_mix(1, 10), holdout_wr=50.0)
    assert v.trades == 11 and v.wins == 1
    assert v.state == "watch"


def test_binom_cdf_matches_the_eleven_coin_values():
    cdf = Supervisor._binom_cdf_le
    assert cdf(0, 11, 0.5) == pytest.approx(1 / 2048, rel=1e-9)
    assert cdf(1, 11, 0.5) == pytest.approx(12 / 2048, rel=1e-9)


def test_ger40_n11_threshold_does_not_include_two_wins():
    p = 0.2743
    k = Supervisor.damning_max_wins(11, p)
    assert k < 2
    assert not Supervisor.count_is_damning(2, 11, 27.43)
    assert not Supervisor.count_is_damning(2, 11, p)
    # Zero wins may or may not be in the 5% tail; the important bound is
    # that the coin-flip trigger (2) is not.
    assert Supervisor.count_is_damning(1, 11, 50.0)
    assert not Supervisor.count_is_damning(1, 11, None)
