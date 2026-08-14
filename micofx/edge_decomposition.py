"""Paper edge split into direction skill vs exit geometry.

Measured on GER40 14.08: holdout E +0.153 with real direction, +0.048 with
the same exits and a coin-flip on the same bars. That split has to be
reproducible for every config, not a one-off notebook. Live trading does
not read this module.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from . import backtest
from .strategy import Params

MIN_TRADES = 100
MIN_SEEDS = 20


@dataclass(frozen=True)
class Decomposition:
    n: int
    wr: float | None
    avg_win: float | None
    avg_loss: float | None
    E: float | None
    E_random_mean: float | None
    E_random_p10: float | None
    E_random_p90: float | None
    direction_share: float | None
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "WR": self.wr,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "E": self.E,
            "E_random_mean": self.E_random_mean,
            "E_random_p10": self.E_random_p10,
            "E_random_p90": self.E_random_p90,
            "direction_share": self.direction_share,
            "reason": self.reason,
        }


def _side_stats(rs: Sequence[float]) -> tuple[int, float, float | None, float | None, float]:
    arr = [float(x) for x in rs]
    n = len(arr)
    if n == 0:
        return 0, 0.0, None, None, 0.0
    wins = [x for x in arr if x >= 0]
    losses = [x for x in arr if x < 0]
    wr = 100.0 * len(wins) / n
    avg_win = (sum(wins) / len(wins)) if wins else None
    avg_loss = ((-sum(losses) / len(losses)) if losses else None)
    E = sum(arr) / n
    return n, wr, avg_win, avg_loss, E


def decompose(real_rs: Sequence[float],
              random_runs: Sequence[Sequence[float]],
              min_n: int = MIN_TRADES,
              min_seeds: int = MIN_SEEDS) -> Decomposition:
    """Compare one real-direction R list to many random-direction replays.

    ``random_runs`` is one R-list per seed. Percentiles need ``min_seeds``
    (default 20); fewer seeds still report the mean and say why the tails
    are missing. Thin real samples produce no numbers at all.
    """
    n = len(real_rs)
    if n < min_n:
        return Decomposition(n=n, wr=None, avg_win=None, avg_loss=None, E=None,
                             E_random_mean=None, E_random_p10=None, E_random_p90=None,
                             direction_share=None, reason="n<100, uretilmedi")
    _, wr, avg_win, avg_loss, E = _side_stats(real_rs)
    seed_e = []
    for run in random_runs:
        if len(run) < min_n:
            continue
        seed_e.append(_side_stats(run)[4])
    if not seed_e:
        return Decomposition(n=n, wr=round(wr, 1), avg_win=avg_win, avg_loss=avg_loss,
                             E=round(E, 3), E_random_mean=None, E_random_p10=None,
                             E_random_p90=None, direction_share=None,
                             reason="yetersiz tohum")
    mean_r = float(np.mean(seed_e))
    share = None if abs(E) < 1e-12 else float((E - mean_r) / E)
    tails = len(seed_e) >= min_seeds
    reason = "" if tails else "yetersiz tohum"
    return Decomposition(
        n=n, wr=round(wr, 1),
        avg_win=None if avg_win is None else round(avg_win, 3),
        avg_loss=None if avg_loss is None else round(avg_loss, 3),
        E=round(E, 3),
        E_random_mean=round(mean_r, 3),
        E_random_p10=round(float(np.percentile(seed_e, 10)), 3) if tails else None,
        E_random_p90=round(float(np.percentile(seed_e, 90)), 3) if tails else None,
        direction_share=None if share is None else round(share, 3),
        reason=reason,
    )


def replay(cache, sig, open_, spread_pts, point: float, params: Params,
           seeds: int = MIN_SEEDS, min_n: int = MIN_TRADES,
           **simulate_kw) -> Decomposition:
    """Same exits, real direction vs coin-flip direction on the same bars."""
    from dataclasses import replace

    real = backtest.simulate(cache, sig, open_, spread_pts, point, params,
                             **simulate_kw)
    entries = np.flatnonzero(sig.buy | sig.sell)
    lo = int(simulate_kw.get("lo") or 0)
    hi = simulate_kw.get("hi")
    if hi is None:
        hi = cache.close.size
    entries = entries[(entries >= lo) & (entries < int(hi) - 1)]
    random_runs: list[list[float]] = []
    for seed in range(max(0, int(seeds))):
        rng = np.random.default_rng(seed)
        buy = np.zeros(len(sig.buy), dtype=bool)
        sell = np.zeros(len(sig.sell), dtype=bool)
        pick = rng.random(entries.size) < 0.5
        if entries.size:
            buy[entries[pick]] = True
            sell[entries[~pick]] = True
        s2 = replace(sig, buy=buy, sell=sell)
        random_runs.append(list(backtest.simulate(
            cache, s2, open_, spread_pts, point, params, **simulate_kw).trade_rs))
    return decompose(list(real.trade_rs), random_runs, min_n=min_n, min_seeds=MIN_SEEDS)
