from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import indicators as ind
from .models import SymbolConfig
from .sessions import WEEKEND_OPEN_GROUPS
from .strategy import IndicatorCache, Params, compute

_DAY = 24 * 60

# Out-of-sample samples thinner than this are noise, not evidence.
MIN_TEST_TRADES = 12
# Same bar used by walk_forward's validated flag and the optimizer's apply gate,
# so the UI never labels a candidate "validated" that auto-apply would reject.
MIN_OOS_PF = 1.10


@dataclass
class Result:
    trades: int = 0
    wins: int = 0
    losses: int = 0
    net_r: float = 0.0
    gross_win_r: float = 0.0
    gross_loss_r: float = 0.0
    max_dd_r: float = 0.0
    longest_loss_streak: int = 0
    avg_bars: float = 0.0
    cost_r: float = 0.0              # total spread+commission drag, in R
    exits: dict[str, int] = field(default_factory=dict)
    trade_rs: list = field(default_factory=list)  # per-trade R, for diagnostics only

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades * 100.0 if self.trades else 0.0

    @property
    def expectancy(self) -> float:
        return self.net_r / self.trades if self.trades else 0.0

    @property
    def profit_factor(self) -> float:
        if self.gross_loss_r <= 0:
            return float(self.gross_win_r) if self.gross_win_r > 0 else 0.0
        return self.gross_win_r / self.gross_loss_r

    def score(self, min_trades: int) -> float:
        """Total R, discounted for thin samples and deep drawdowns.

        This is the shared-core formula (MASTER_PROMPT.md sec.8) and is what
        selection/validation/holdout ranking and the apply gate use. Do not
        change it without an explicit ask - see ``score_consistency`` below
        for an additional, non-gating diagnostic.
        """
        if self.trades <= 0 or self.net_r <= 0:
            return float(round(min(0.0, self.net_r), 3))
        sample = min(1.0, self.trades / max(1, min_trades))
        dd = self.net_r / (self.net_r + self.max_dd_r) if self.max_dd_r > 0 else 1.0
        return float(round(self.net_r * sample * dd, 3))

    def score_consistency(self, min_trades: int) -> float:
        """Diagnostic-only variant that also rewards steady per-trade R and
        penalizes deep drawdowns harder (adapted from the MicoAi experimental
        fork). Never used for selection/validation/holdout ranking or the
        auto-apply gate - shown in the UI/opt summary purely as a second
        opinion on candidates that already passed the shared-core gates.
        """
        base = self.score(min_trades)
        if self.trades < 10 or not self.trade_rs:
            return base
        arr = np.asarray(self.trade_rs, dtype=float)
        std_r = max(float(np.std(arr)), 0.001)
        sharpe = float(np.mean(arr)) / std_r
        consistency = min(0.3, max(-0.3, sharpe * 0.05))
        if self.max_dd_r > 15:
            dd_penalty = 0.5
        elif self.max_dd_r > 10:
            dd_penalty = 0.75
        else:
            dd_penalty = 1.0
        return float(round(base * dd_penalty * (1.0 + consistency), 3))

    def as_dict(self, min_trades: int = 25) -> dict[str, Any]:
        # Values accumulate as numpy scalars; cast so the payload stays JSON safe.
        return {
            "trades": int(self.trades), "wins": int(self.wins), "losses": int(self.losses),
            "win_rate": float(round(self.win_rate, 1)),
            "net_r": float(round(self.net_r, 2)),
            "expectancy": float(round(self.expectancy, 3)),
            "profit_factor": float(round(self.profit_factor, 2)),
            "max_dd_r": float(round(self.max_dd_r, 2)),
            "longest_loss_streak": int(self.longest_loss_streak),
            "avg_bars": float(round(self.avg_bars, 1)),
            "cost_r": float(round(self.cost_r, 2)),
            "cost_per_trade_r": float(round(self.cost_r / self.trades, 4)) if self.trades else 0.0,
            "score": self.score(min_trades),
            "score_consistency": self.score_consistency(min_trades),
            "exits": {str(k): int(v) for k, v in self.exits.items()},
        }


def session_mask(cfg: SymbolConfig, times: np.ndarray, all_hours: bool = False) -> np.ndarray:
    """Boolean mask of bars whose broker timestamp falls inside a trading window.

    ``all_hours`` mirrors ``sessions.evaluate``'s system-wide override: when the
    live engine has ``system.trade_all_hours`` set it drops every configured
    window/trade-day and trades any tick except the broker's real weekend
    (crypto exempt) - see ``sessions.weekend_closed``. The walk-forward used to
    have no idea this flag existed, so with it on live traded hours the search
    never scored (JPN225's 04:15-07:00 window, for one) while with it off live
    was *more* restricted than what got validated - either way the two were
    scoring a different product than the one actually trading.
    """
    days = ((times // 86400 + 3) % 7) + 1          # 1970-01-01 (Thu) -> 4, matches sessions.server_clock's Mon=1..Sun=7
    minutes = (times % 86400) // 60

    if all_hours:
        # Same day-of-week formula as below, so the weekend definition matches
        # this function's own convention rather than importing a second one.
        # Verified against 1970 epoch: 1970-01-03 (Sat) -> 6, 1970-01-04 (Sun) -> 7.
        weekend = (days == 6) | (days == 7)
        if str(getattr(cfg, "group", "") or "").strip().lower() in WEEKEND_OPEN_GROUPS:
            return np.ones(times.size, dtype=bool)
        return ~weekend

    if not cfg.use_sessions:
        windows: list[tuple[int, int]] = []
    else:
        windows = cfg.session_windows()

    allowed_day = np.isin(days, np.array(cfg.trade_days or [1, 2, 3, 4, 5], dtype=np.int64))

    if not windows:
        return allowed_day

    mask = np.zeros(times.size, dtype=bool)
    prev_days = np.where(days == 1, 7, days - 1)
    allowed_prev = np.isin(prev_days, np.array(cfg.trade_days or [1, 2, 3, 4, 5], dtype=np.int64))

    for start, end in windows:
        if start < end:
            inside = (minutes >= start) & (minutes < end) & allowed_day
            if cfg.flat_before_close_min > 0:
                inside &= minutes < (end - cfg.flat_before_close_min)
        else:
            evening = (minutes >= start) & allowed_day
            morning = (minutes < end) & allowed_prev
            if cfg.flat_before_close_min > 0:
                morning &= minutes < (end - cfg.flat_before_close_min)
            inside = evening | morning
        mask |= inside
    return mask


def flatten_mask(cfg: SymbolConfig, times: np.ndarray, all_hours: bool = False,
                 day_end_flatten_min: int = 0) -> np.ndarray:
    """Boolean mask of bars where a still-open position must be force-closed.

    Mirrors ``sessions.should_flatten`` + ``sessions.day_end_close`` +
    ``sessions.weekend_closed`` - the live engine force-closes any open
    position in these bands (``manage_positions``), but the walk-forward
    previously only used ``flat_before_close_min``/``session_mask`` to keep
    new entries out of the same band, never to exit a position already
    holding through it. A trade opened well before the band rode straight
    through what live would have already flattened, so holdout could look
    stronger than what live can actually realise.
    """
    days = ((times // 86400 + 3) % 7) + 1
    minutes = (times % 86400) // 60
    mask = np.zeros(times.size, dtype=bool)

    # Weekend: unconditional and ahead of everything else here, matching
    # manage_positions()'s own weekend_closed() check - live force-flattens
    # this regardless of all_hours, so the backtest must too or a position
    # that survives into Saturday rides the weekend numerically instead of
    # getting cut exactly where live cuts it.
    if str(getattr(cfg, "group", "") or "").strip().lower() not in WEEKEND_OPEN_GROUPS:
        mask |= (days == 6) | (days == 7)
        # FX/index bar data has no Saturday/Sunday rows at all - the market
        # simply produces no candles while closed, so the check above (which
        # only matches a bar's OWN day) never fires for exactly the symbols
        # this is meant to protect: a position rides straight from Friday's
        # last bar into Monday's first with no weekend-timestamped bar in
        # between to ever flag. Detect the gap itself instead - flatten the
        # bar right before any calendar day skipped over by the jump to the
        # next bar was a Saturday or Sunday. Bounded to a 10-day lookahead,
        # comfortably more than any realistic FX/index holiday closure.
        if times.size > 1:
            day_num = times // 86400
            next_day_num = np.empty_like(day_num)
            next_day_num[:-1] = day_num[1:]
            next_day_num[-1] = day_num[-1]           # no bar after the last one
            gap_days = next_day_num - day_num
            for offset in range(1, 11):
                candidate_day = day_num + offset
                candidate_weekday = ((candidate_day + 3) % 7) + 1
                mask |= (offset <= gap_days) & ((candidate_weekday == 6) | (candidate_weekday == 7))

    # Day-end: independent of all_hours/sessions, same as sessions.day_end_close.
    if day_end_flatten_min > 0:
        mask |= minutes >= (_DAY - day_end_flatten_min)

    # Session wind-down: only meaningful when sessions are actually enforced -
    # with all_hours on, live never winds a session down (see should_flatten).
    if not all_hours and cfg.use_sessions and cfg.flat_before_close_min > 0:
        windows = cfg.session_windows()
        allowed_day = np.isin(days, np.array(cfg.trade_days or [1, 2, 3, 4, 5], dtype=np.int64))
        prev_days = np.where(days == 1, 7, days - 1)
        allowed_prev = np.isin(prev_days, np.array(cfg.trade_days or [1, 2, 3, 4, 5], dtype=np.int64))
        fb = cfg.flat_before_close_min
        for start, end in windows:
            if start < end:
                inside = (minutes >= start) & (minutes < end) & allowed_day
                mask |= inside & (minutes >= end - fb)
            else:
                # Overnight window: the closing edge (``end``) only falls inside
                # the "morning" half - the "evening" half's close is hours away.
                morning = (minutes < end) & allowed_prev
                mask |= morning & (minutes >= end - fb)
    return mask


def _ladder(p: Params, entry: float, sl_dist: float,
            is_buy: bool) -> list[tuple[float, float, float]]:
    """Scale-out rungs as ``(price, r_multiple, fraction of original size)``.

    A rung only counts when it is further out than the one before it and when
    the ladder still leaves a runner, so a configuration can never close the
    whole position through partials and leave the trailing stop with nothing to
    manage. Shared by the backtest and the live engine so the two book the same
    banked R for the same configuration.
    """
    if p.partial_tp_r <= 0 or not (0.0 < p.partial_tp_fraction < 1.0):
        return []
    sign = 1.0 if is_buy else -1.0
    out = [(entry + sign * sl_dist * p.partial_tp_r,
            float(p.partial_tp_r), float(p.partial_tp_fraction))]
    if (p.partial2_tp_r > p.partial_tp_r and p.partial2_fraction > 0
            and p.partial_tp_fraction + p.partial2_fraction < 1.0):
        out.append((entry + sign * sl_dist * p.partial2_tp_r,
                    float(p.partial2_tp_r), float(p.partial2_fraction)))
    return out


def run(cache: IndicatorCache, open_: np.ndarray, spread_pts: np.ndarray, point: float,
        p: Params, tradable: np.ndarray | None = None, commission_price: float = 0.0) -> Result:
    """Bar-replay of the live rules, scored in R multiples.

    Conventions that keep the result honest rather than flattering:
      * a signal on a closed bar is filled at the *next* bar's open;
      * the full spread and round-turn commission are charged every trade;
      * when a bar's range contains both stop and target, the stop wins;
      * the trailing stop only advances on bar closes, never intrabar.
    """
    return simulate(cache, compute(cache, p), open_, spread_pts, point, p, tradable,
                    commission_price=commission_price)


def simulate(cache: IndicatorCache, sig, open_: np.ndarray, spread_pts: np.ndarray,
             point: float, p: Params, tradable: np.ndarray | None = None,
             lo: int = 0, hi: int | None = None, commission_price: float = 0.0,
             entries: np.ndarray | None = None,
             spread_price: np.ndarray | None = None,
             min_stop: float | None = None,
             flatten: np.ndarray | None = None) -> Result:
    """Replay one bar window using an already-computed signal set.

    ``entries`` and ``spread_price`` are optional precomputed views of values
    that are identical for every window and every combination sharing a signal
    set. Passing them in is purely a caching shortcut - when omitted they are
    derived here exactly as before, and either way the numbers are the same.
    """
    n = cache.close.size if hi is None else int(hi)
    lo = max(0, int(lo))
    res = Result()
    if n - lo < 50:
        return res

    if entries is None:
        entries = np.flatnonzero(sig.buy | sig.sell)
    # ``entries`` is sorted and unique, so slicing by position is identical to
    # the boolean mask it replaces, without rebuilding the array per window.
    entries = entries[np.searchsorted(entries, lo, "left"):
                      np.searchsorted(entries, n - 1, "left")]
    if entries.size == 0:
        return res

    # List views of the price series (see IndicatorCache.lists): the loop below
    # is sequential by nature, and list indexing avoids a numpy scalar unbox on
    # every bar. Values and therefore results are unchanged.
    high, low, close, open_l = cache.lists()
    atr = cache.atr_list(p.atr_period)
    buy_flags, sell_flags = sig.buy, sig.sell

    if spread_price is None:
        spread_price = spread_pts * point
    # Falls back to the old flat approximation when the caller doesn't know the
    # symbol's real broker floor (``mt5client.min_stop_distance`` - stops_level,
    # freeze_level, current spread) - live can legally require a wider stop than
    # this default, which understates the true SL/TP/trail floor for symbols
    # where the broker's own minimum exceeds ten points.
    if min_stop is None:
        min_stop = point * 10.0
    max_bars = p.max_bars_in_trade if p.max_bars_in_trade > 0 else n

    # Structure trail: precompute once so the loop below stays O(1) per bar.
    # swing_lows/highs are causal (rolling window excludes the current bar).
    struct_lookback = max(3, int(p.trail_lookback))
    structural = p.trail_mode in ("structure", "hybrid")
    swing_lo = ind.swing_lows(cache.low, struct_lookback).tolist() if structural else None
    swing_hi = ind.swing_highs(cache.high, struct_lookback).tolist() if structural else None
    exits: dict[str, int] = {}
    equity = 0.0
    peak = 0.0
    streak = 0
    bar_total = 0
    ptr = 0
    guard = 0

    while ptr < entries.size and guard < 100000:
        guard += 1
        i = int(entries[ptr])
        j0 = i + 1
        if j0 >= n - 1:
            break
        if tradable is not None and not tradable[j0]:
            ptr += 1
            continue

        atr_entry = atr[i]
        if atr_entry <= 0:
            ptr += 1
            continue
        s = float(spread_price[j0])
        if p.max_spread_atr > 0 and s > atr_entry * p.max_spread_atr:
            ptr += 1
            continue

        # Invariant: a bar that fired both ways trades neither side.
        if bool(buy_flags[i]) and bool(sell_flags[i]):
            ptr += 1
            continue
        is_buy = bool(buy_flags[i])
        if not is_buy and not bool(sell_flags[i]):
            ptr += 1
            continue
        sl_dist = max(atr_entry * p.sl_atr_mult, min_stop)
        entry = float(open_[j0] + s) if is_buy else float(open_[j0])
        sl = entry - sl_dist if is_buy else entry + sl_dist
        # ``tp_atr_mult <= 0`` means "no fixed target at all": the hard stop and
        # the trail are the only ways out. Without this branch the max() below
        # collapsed to ``min_stop * 1.5`` - a target roughly fifteen points from
        # entry - so a zero multiplier silently became the tightest possible
        # scalp instead of a trend runner. Pushing the level to infinity keeps
        # the bar loop branch-free while making the comparison never fire.
        if p.tp_atr_mult > 0:
            tp_dist = max(atr_entry * p.tp_atr_mult, min_stop * 1.5)
            tp = entry + tp_dist if is_buy else entry - tp_dist
        else:
            tp = float("inf") if is_buy else float("-inf")
        moved_be = False

        # Optional scale-out ladder: bank a slice at N1 x risk, another at N2,
        # run the remainder. Rungs are held as (price, r_multiple, fraction of
        # the ORIGINAL size) so the banked R is exactly what the live engine
        # books when it closes that same fraction of the opening volume.
        runner = 1.0
        banked_r = 0.0
        rungs = _ladder(p, entry, sl_dist, is_buy)
        rung = 0

        exit_price = None
        exit_bar = j0
        reason = "time"

        for j in range(j0, min(n, j0 + max_bars)):
            bar_high, bar_low = high[j], low[j]
            if is_buy:
                if bar_low <= sl:
                    exit_price, reason = sl, ("stop" if not moved_be else "trail")
                elif bar_high >= tp:
                    exit_price, reason = tp, "target"
            else:
                if bar_high + s >= sl:
                    exit_price, reason = sl, ("stop" if not moved_be else "trail")
                elif bar_low + s <= tp:
                    exit_price, reason = tp, "target"
            if exit_price is not None:
                exit_bar = j
                break

            if flatten is not None and flatten[j]:
                # Live force-closes at the current market price the instant the
                # session/day-end band starts, ahead of trail/BE/stale checks -
                # same ordering here (checked before those, right after SL/TP).
                exit_price = close[j] + (0.0 if is_buy else s)
                reason = "flatten"
                exit_bar = j
                break

            if p.stale_exit_ratio > 0 and max_bars < n:
                held = j - j0 + 1
                if held > max_bars * p.stale_exit_ratio:
                    c_now = close[j]
                    gain_now = (c_now - entry) if is_buy else (entry - c_now)
                    if gain_now < 0:
                        exit_price = c_now + (0.0 if is_buy else s)
                        reason = "stale"
                        exit_bar = j
                        break

            # Walk up the ladder; several rungs can fall inside one bar's range.
            while rung < len(rungs):
                level, r_mult, frac = rungs[rung]
                hit = (bar_high >= level) if is_buy else (bar_low + s <= level)
                if not hit:
                    break
                banked_r += r_mult * frac
                runner -= frac
                if rung == 0:
                    # First slice off: the remainder rides risk-free from here.
                    if is_buy and entry > sl:
                        sl = max(sl, entry)
                    elif not is_buy and entry < sl:
                        sl = min(sl, entry)
                    moved_be = True
                rung += 1

            c = close[j]
            a = atr[j]
            gain = (c - entry) if is_buy else (entry - c)
            if a > 0 and gain > 0:
                target = None
                # Mirrors engine._update_stop's breakeven_locked guard: once
                # breakeven is reached (now, or already from an earlier bar -
                # sl at/past entry), the min_stop clamp below must never be
                # allowed to land the final stop worse than entry. Backtest
                # previously clamped to the bar close unconditionally, which
                # could bank a "breakeven" bar that live (post-fix) actually
                # skips, since a stop worse than breakeven is not one.
                breakeven_locked = (sl >= entry) if is_buy else (sl <= entry)
                if p.breakeven_atr > 0 and not moved_be and gain >= a * p.breakeven_atr:
                    target = entry
                    moved_be = True
                    breakeven_locked = True
                if p.trail_start_atr > 0 and gain >= a * p.trail_start_atr:
                    trail_atr = c - a * p.trail_step_atr if is_buy else c + a * p.trail_step_atr
                    trail = trail_atr
                    if structural and swing_lo is not None:
                        struct_sl = (swing_lo[j] - a * 0.15) if is_buy \
                            else (swing_hi[j] + a * 0.15)
                        # Chained ternary here used to bind as
                        # `(max(...) if is_buy else min(...)) if hybrid else struct_sl`
                        # with a trailing `else struct_sl` reachable only from the
                        # is_buy==False leg - every long with trail_mode="structure"
                        # silently got the hybrid formula instead of pure struct_sl,
                        # matching engine.py's live trailing was the whole point of
                        # trail_mode existing. Mirrors _update_stop exactly now.
                        if p.trail_mode == "hybrid":
                            trail = max(trail_atr, struct_sl) if is_buy else min(trail_atr, struct_sl)
                        else:
                            trail = struct_sl
                    if target is None or (trail > target if is_buy else trail < target):
                        target = trail
                if target is not None:
                    if is_buy and target > sl:
                        new_sl = min(target, c - min_stop)
                        if not (breakeven_locked and new_sl < entry):
                            sl = new_sl
                    elif not is_buy and target < sl:
                        new_sl = max(target, c + min_stop)
                        if not (breakeven_locked and new_sl > entry):
                            sl = new_sl
            exit_bar = j

        if exit_price is None:
            exit_price = close[exit_bar] + (0.0 if is_buy else s)
            reason = "time"

        move = (exit_price - entry) if is_buy else (entry - exit_price)
        r = float((banked_r * sl_dist + move * runner - commission_price) / sl_dist)
        res.cost_r += float((commission_price + s) / sl_dist)
        if banked_r > 0 and reason in ("stop", "trail"):
            reason = "partial+" + reason
        res.trades += 1
        res.net_r += r
        res.trade_rs.append(r)
        bar_total += exit_bar - j0 + 1
        exits[reason] = exits.get(reason, 0) + 1
        if r >= 0:
            res.wins += 1
            res.gross_win_r += r
            streak = 0
        else:
            res.losses += 1
            res.gross_loss_r += -r
            streak += 1
            res.longest_loss_streak = max(res.longest_loss_streak, streak)

        equity += r
        peak = max(peak, equity)
        res.max_dd_r = max(res.max_dd_r, peak - equity)

        # Live ``_cooldown_for`` pauses new entries for up to 2 bars (scalp) or
        # 1 bar (M15+ swing) of the strategy TF after a *fill*. Mirror that so
        # scalp scores are not inflated by back-to-back fills the live engine
        # would have blocked. Longer holds already cover the pause via exit_bar.
        cooldown_bars = 0
        if p.cooldown_sec > 0 and cache.tf_seconds > 0:
            from .models import is_scalp_strategy
            max_bars_cd = 1 if (not is_scalp_strategy(p.strategy)
                                and cache.tf_seconds >= 900) else 2
            capped = min(int(p.cooldown_sec), max_bars_cd * int(cache.tf_seconds))
            cooldown_bars = max(0, capped // int(cache.tf_seconds))
        resume_signal = max(exit_bar, j0 + cooldown_bars - 1)
        while ptr < entries.size and entries[ptr] <= resume_signal:
            ptr += 1

    res.avg_bars = bar_total / res.trades if res.trades else 0.0
    res.exits = exits
    return res


def combos_from_grid(grid: dict[str, list], max_combos: int,
                     seed: int = 7) -> tuple[list[str], list[tuple[int, ...]]]:
    """Grid index tuples: the full product when small, else a deterministic sample.

    Index tuples (rather than value dicts) are returned so the plateau check can
    walk to a combination's grid neighbours cheaply.
    """
    keys = [k for k, v in grid.items() if isinstance(v, list) and v]
    if not keys:
        return [], [()]
    sizes = [len(grid[k]) for k in keys]
    total = math.prod(sizes)

    if total <= max_combos:
        combos: list[tuple[int, ...]] = [()]
        for size in sizes:
            combos = [base + (i,) for base in combos for i in range(size)]
        return keys, combos

    rng = np.random.default_rng(seed)
    seen: set[tuple[int, ...]] = set()
    attempts = 0
    while len(seen) < max_combos and attempts < max_combos * 40:
        attempts += 1
        seen.add(tuple(int(rng.integers(0, s)) for s in sizes))
    return keys, sorted(seen)


def _values(keys: list[str], grid: dict[str, list], idx: tuple[int, ...]) -> dict[str, Any]:
    return {k: grid[k][i] for k, i in zip(keys, idx)}


MIN_PLATEAU_NEIGHBOURS = 3


def _plateau_scores(keys: list[str], grid: dict[str, list],
                    scores: dict[tuple[int, ...], float],
                    weight: float,
                    pool: dict[tuple[int, ...], float] | None = None,
                    ) -> tuple[dict[tuple[int, ...], float], dict[tuple[int, ...], int]]:
    """Blend each combination's score with its immediate grid neighbours.

    An isolated spike surrounded by losers is almost always curve fitting; a
    parameter set whose neighbours also work is a real region of edge. Combos
    with too few sampled neighbours are discounted rather than trusted.

    ``pool`` is the score of *every* combination that was actually simulated,
    including the ones the consistency filter threw away (they score 0 - no
    usable edge was found there). Looking neighbours up in that pool rather than
    in the surviving-candidates map matters: previously a spike whose whole
    neighbourhood had been rejected looked like it simply had no neighbours and
    escaped with the flat discount, which is exactly backwards. The second
    return value is the neighbour count, so callers can require that a winner
    actually sits inside an explored region.
    """
    sizes = [len(grid[k]) for k in keys]
    lookup = pool if pool is not None else scores
    blended: dict[tuple[int, ...], float] = {}
    counts: dict[tuple[int, ...], int] = {}
    for idx, own in scores.items():
        neighbours = []
        for axis, size in enumerate(sizes):
            for step in (-1, 1):
                pos = idx[axis] + step
                if 0 <= pos < size:
                    probe = idx[:axis] + (pos,) + idx[axis + 1:]
                    if probe in lookup:
                        neighbours.append(lookup[probe])
        counts[idx] = len(neighbours)
        if len(neighbours) >= MIN_PLATEAU_NEIGHBOURS:
            mean = sum(neighbours) / len(neighbours)
            blended[idx] = (1.0 - weight) * own + weight * mean
        else:
            blended[idx] = own * (1.0 - weight * 0.75)
    return blended, counts


def _merge(results: list[Result]) -> Result:
    """Pool per-segment results into one aggregate for reporting."""
    total = Result()
    for r in results:
        total.trades += r.trades
        total.wins += r.wins
        total.losses += r.losses
        total.net_r += r.net_r
        total.gross_win_r += r.gross_win_r
        total.gross_loss_r += r.gross_loss_r
        total.max_dd_r = max(total.max_dd_r, r.max_dd_r)
        total.longest_loss_streak = max(total.longest_loss_streak, r.longest_loss_streak)
        total.cost_r += r.cost_r
        total.trade_rs.extend(r.trade_rs)
        for k, v in r.exits.items():
            total.exits[k] = total.exits.get(k, 0) + v
    bars = sum(r.avg_bars * r.trades for r in results)
    total.avg_bars = bars / total.trades if total.trades else 0.0
    return total


def _slice_ok(slice_dict: dict[str, Any]) -> bool:
    """Did an out-of-sample slice actually pay, on enough trades to mean it?"""
    return bool(slice_dict.get("net_r", 0) > 0
                and slice_dict.get("trades", 0) >= MIN_TEST_TRADES
                and slice_dict.get("profit_factor", 0) >= MIN_OOS_PF)


def commission_in_price(commission_per_lot: float, tick_value: float, tick_size: float) -> float:
    """Convert round-turn commission per lot into price units.

    P/L per price unit for one lot is tick_value / tick_size, so dividing the
    money cost by that ratio expresses it on the same scale as the price series
    and keeps the R calculation lot independent.
    """
    if commission_per_lot <= 0 or tick_value <= 0 or tick_size <= 0:
        return 0.0
    return float(commission_per_lot) / (float(tick_value) / float(tick_size))


def walk_forward(cfg: SymbolConfig, bars, point: float, tf_seconds: int, grid: dict[str, list],
                 min_trades: int, segments: int, max_combos: int,
                 min_positive_ratio: float = 0.6, plateau_weight: float = 0.4,
                 commission_price: float = 0.0, refine_rounds: int = 2,
                 should_cancel=None, on_progress=None,
                 min_stop: float | None = None, all_hours: bool = False,
                 day_end_flatten_min: int = 0) -> dict[str, Any]:
    """Segmented walk-forward search over a three-way split of history.

    History is cut into equal segments and used for three separate jobs, because
    a slice that picks something can no longer measure it honestly:

      * *selection* segments drive the parameter search, each scored on its own
        so a setting only ranks well if it works across different periods;
      * the *validation* segment ranks the surviving candidates - and, upstream,
        decides which strategy family and timeframe to run at all;
      * the *test* segment touches nothing. It is the number to believe.
    """
    n = len(bars)
    segments = max(4, min(8, int(segments)))
    if n < segments * 150:
        return {"ok": False, "error": f"yeterli gecmis veri yok ({n} bar)"}

    edges = [int(round(n * i / segments)) for i in range(segments + 1)]
    windows = [(edges[i], edges[i + 1]) for i in range(segments)]
    selection, validation, holdout = windows[:-2], windows[-2], windows[-1]

    tradable = session_mask(cfg, bars.time, all_hours)
    flatten = flatten_mask(cfg, bars.time, all_hours, day_end_flatten_min)
    point = float(point) if point > 0 else 1e-5

    # Identical for every combination in the sweep, so it is built once instead
    # of reallocated inside every one of the tens of thousands of simulations.
    spread_price = bars.spread * point
    # The round-turn cost the simulation will actually charge this trade. The
    # scalping families size their entry threshold against it, so it has to be
    # this exact series and not an approximation of it.
    cost_price = spread_price + float(commission_price)

    cache = IndicatorCache(bars.high, bars.low, bars.close, bars.time, tf_seconds,
                           bars.open, bars.volume, cost_price)
    keys, combos = combos_from_grid(grid, max_combos)

    per_segment_trades = max(6, int(min_trades / max(1, segments - 1)))

    # Signals depend only on the entry-side parameters (``Params.key``); the
    # exit grid - stops, targets, trailing, partials, the spread gate - does not
    # move a single bar of the signal series. Roughly nine tenths of the grid is
    # exit parameters, so recomputing the indicator stack per combination was
    # repeating identical work. The sweep below walks the grid grouped by signal
    # key and this holds the current group's series, so the cache never grows
    # past a couple of entries no matter how large the grid is.
    _sig_cache: dict[tuple, tuple[Any, np.ndarray]] = {}

    def signals_for(p: Params) -> tuple[Any, np.ndarray]:
        key = p.key()
        hit = _sig_cache.get(key)
        if hit is None:
            sig = compute(cache, p)
            hit = (sig, np.flatnonzero(sig.buy | sig.sell))
            if len(_sig_cache) > 4:
                _sig_cache.clear()
            _sig_cache[key] = hit
        return hit

    def run_window(p: Params, window: tuple[int, int], sig=None,
                   entries: np.ndarray | None = None) -> Result:
        if sig is None:
            sig, entries = signals_for(p)
        return simulate(cache, sig, bars.open, bars.spread, point, p, tradable,
                        window[0], window[1], commission_price,
                        entries=entries, spread_price=spread_price, min_stop=min_stop,
                        flatten=flatten)

    def evaluate(p: Params, sig=None, entries: np.ndarray | None = None,
                 last: Result | None = None) -> tuple[list[Result], float, float]:
        """Score ``p`` on every selection segment.

        ``last`` is the already-simulated result for the final selection
        segment, handed over by the prescreen below. It is the same window with
        the same parameters and the same signal series, so reusing it is exactly
        the value a second simulation would return - one simulation in four
        saved on every combination that survives the screen.
        """
        if sig is None:
            sig, entries = signals_for(p)
        windows = selection[:-1] if last is not None else selection
        parts = [run_window(p, w, sig, entries) for w in windows]
        if last is not None:
            parts.append(last)                      # keeps the segment order
        scored = [r.score(per_segment_trades) for r in parts]
        positive = sum(1 for r in parts if r.net_r > 0) / len(parts)
        return parts, (sum(scored) / len(scored)), positive

    def prescreen(p: Params, sig, entries: np.ndarray) -> Result:
        """Cheap first look: score the most recent selection segment only.

        Successive halving. A setting that cannot pay on one segment will never
        clear ``min_positive_ratio`` across all of them, so paying for the other
        segments is wasted work. Survivors are then scored the normal way, so
        every number that reaches ranking or the apply gate is still the full
        multi-segment score - this only decides what is worth measuring.
        """
        return run_window(p, selection[-1], sig, entries)

    def measure(values: dict[str, Any], window: tuple[int, int]) -> Result:
        p = Params.from_config(cfg, **values)
        return run_window(p, window)

    baseline_p = Params.from_config(cfg)
    base_parts, _, _ = evaluate(baseline_p)
    baseline = _merge(base_parts).as_dict(min_trades)
    baseline["validation"] = measure({}, validation).as_dict(min_trades)
    baseline["holdout"] = measure({}, holdout).as_dict(min_trades)

    raw: dict[tuple[int, ...], float] = {}
    detail: dict[tuple[int, ...], dict[str, Any]] = {}
    # Score of every combination that was simulated, rejected ones included, so
    # the plateau blend can see a spike's dead neighbourhood for what it is.
    pool: dict[tuple[int, ...], float] = {}
    rejected_inconsistent = 0
    evaluated = 0
    screened = 0
    cancelled = False

    def sweep(batch: list[tuple[int, ...]], offset: int, budget: int,
              screen: bool = False) -> bool:
        """Simulate a batch of grid points, grouped so signals are computed once.

        Every result is stored against its own grid index, so visiting the batch
        grouped by signal key rather than in grid order changes nothing about
        what is measured or recorded - only how often the indicator stack is
        rebuilt.
        """
        nonlocal rejected_inconsistent, evaluated, screened
        groups: dict[tuple, list[tuple[tuple[int, ...], dict[str, Any], Params]]] = {}
        for idx in batch:
            if idx in pool:
                continue
            values = _values(keys, grid, idx)
            p = Params.from_config(cfg, **values)
            groups.setdefault(p.key(), []).append((idx, values, p))

        i = 0
        for members in groups.values():
            sig, entries = signals_for(members[0][2])
            for idx, values, p in members:
                if should_cancel and should_cancel():
                    return False
                i += 1

                last = None
                if screen:
                    last = prescreen(p, sig, entries)
                    if last.score(per_segment_trades) <= 0.0:
                        # No edge on the most recent segment; record the dead
                        # spot for the plateau blend and move on without the
                        # rest of the simulation.
                        pool[idx] = 0.0
                        screened += 1
                        if on_progress and i % 40 == 0:
                            on_progress(offset + i, budget, max(raw.values(), default=None))
                        continue

                parts, mean_score, positive = evaluate(p, sig, entries, last)
                pooled = _merge(parts)
                evaluated += 1
                pool[idx] = 0.0

                if pooled.trades >= min_trades and mean_score > 0:
                    if positive < min_positive_ratio:
                        rejected_inconsistent += 1
                    else:
                        # Consistency across segments matters more than the size of the edge.
                        raw[idx] = round(mean_score * positive * positive, 4)
                        pool[idx] = raw[idx]
                        detail[idx] = {"params": values, "positive_ratio": round(positive, 2),
                                       "segments": [r.as_dict(per_segment_trades) for r in parts],
                                       "pooled": pooled.as_dict(min_trades)}
                if on_progress and i % 40 == 0:
                    on_progress(offset + i, budget, max(raw.values(), default=None))
        return True

    total_budget = max_combos * (1 + max(0, refine_rounds))
    if not sweep(combos, 0, total_budget, screen=True):
        return {"ok": False, "error": "iptal edildi", "cancelled": True}

    # Coarse sampling only covers a slice of a large grid, so walk downhill from
    # the best points: neighbours of good settings are the likeliest improvements.
    sizes = [len(grid[k]) for k in keys]
    for round_no in range(max(0, refine_rounds)):
        if not raw:
            break
        # Tie-broken on the grid index so equal-scoring seeds are picked in a
        # fixed order rather than in whichever order they happened to be
        # measured; the sweep visits the grid grouped by signal key, and a
        # search should not depend on that.
        seeds = sorted(raw, key=lambda k: (-raw[k], k))[:12]
        probes: list[tuple[int, ...]] = []
        seen: set[tuple[int, ...]] = set(pool)
        for seed in seeds:
            for axis, size in enumerate(sizes):
                for step in (-1, 1):
                    pos = seed[axis] + step
                    if 0 <= pos < size:
                        probe = seed[:axis] + (pos,) + seed[axis + 1:]
                        if probe not in seen:
                            seen.add(probe)
                            probes.append(probe)
        if not probes:
            break
        if not sweep(probes[:max_combos], max_combos * (round_no + 1), total_budget, screen=True):
            cancelled = True
            break

    if cancelled and not raw:
        return {"ok": False, "error": "iptal edildi", "cancelled": True}

    if not raw:
        return {"ok": False, "combos": evaluated, "baseline": baseline,
                "error": f"tutarli kazanan parametre bulunamadi "
                         f"({rejected_inconsistent} kombinasyon segmentler arasi tutarsizdi)"}

    blended, neighbours = _plateau_scores(keys, grid, raw,
                                          max(0.0, min(0.8, plateau_weight)), pool)

    # Only trust candidates whose neighbourhood was actually explored. A high
    # score with no measured neighbours is an untested claim, not a plateau -
    # and under a sparse random sample of a large grid that describes almost
    # every point, which is why the blend used to be a no-op. The refine rounds
    # above exist precisely to build these neighbourhoods around the leaders.
    grounded = [k for k in blended if neighbours.get(k, 0) >= MIN_PLATEAU_NEIGHBOURS]
    pool_for_rank = grounded or list(blended)
    order = sorted(pool_for_rank, key=lambda k: (-blended[k], k))

    # The in-sample blend only narrows the field; the validation slice picks the
    # winner, because a search score cannot be compared across search spaces.
    order = sorted(order[:14], key=lambda k: -blended[k])
    top: list[dict[str, Any]] = []
    for idx in order:
        valid = measure(detail[idx]["params"], validation)
        top.append({
            "params": detail[idx]["params"],
            "score": round(blended[idx], 3),
            "raw_score": raw[idx],
            "plateau_neighbours": neighbours.get(idx, 0),
            "positive_ratio": detail[idx]["positive_ratio"],
            "selection": detail[idx]["pooled"],
            "segments": detail[idx]["segments"],
            # OOS slices scored against the apply-gate sample size (12), not the
            # in-sample min_trades (often 40) - otherwise a clean 20-trade M5
            # holdout is ranked at half weight vs a noisier 40-trade M1 run.
            "validation": valid.as_dict(MIN_TEST_TRADES),
        })
    top.sort(key=lambda c: (c["validation"]["score"], c["score"]), reverse=True)
    for candidate in top:
        candidate["holdout"] = measure(candidate["params"], holdout).as_dict(MIN_TEST_TRADES)
    top = top[:10]

    best = top[0]
    validated = (_slice_ok(best["validation"]) and _slice_ok(best["holdout"]))

    return {
        "ok": True,
        "best": best,
        "top": top,
        "baseline": baseline,
        "validated": validated,
        "combos": evaluated,
        "simulated": len(pool),
        "screened_out": screened,
        "candidates": len(raw),
        "grounded": len(grounded),
        "rejected_inconsistent": rejected_inconsistent,
        "bars": n,
        "segments": segments,
        "holdout_bars": holdout[1] - holdout[0],
        "holdout_days": round((int(bars.time[-1]) - int(bars.time[holdout[0]])) / 86400.0, 1),
        "validation_days": round((int(bars.time[holdout[0]]) - int(bars.time[validation[0]]))
                                 / 86400.0, 1),
        "span_days": round((int(bars.time[-1]) - int(bars.time[0])) / 86400.0, 1),
        "from": int(bars.time[0]),
        "to": int(bars.time[-1]),
        "finished_at": time.time(),
    }
