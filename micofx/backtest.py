from __future__ import annotations

import copy
import math
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import indicators as ind
from .models import SymbolConfig, trail_min_step
from .sessions import WEEKEND_OPEN_GROUPS
from .strategy import IndicatorCache, Params, compute

_DAY = 24 * 60

# Grid axis that is not a Params field: it only rewrites the entry mask.
SESSION_GRID_FIELDS = frozenset({"blocked_entry_hours"})


def _blocked_entry_hours(cfg: SymbolConfig) -> list[int]:
    raw = getattr(cfg, "blocked_entry_hours", None) or []
    return [int(h) for h in raw if isinstance(h, (int, float)) and 0 <= int(h) <= 23]


def _drop_blocked_entry_hours(cfg: SymbolConfig, times: np.ndarray,
                              mask: np.ndarray) -> np.ndarray:
    hours = _blocked_entry_hours(cfg)
    if not hours:
        return mask
    bar_hour = (np.asarray(times) % 86400) // 3600
    return mask & ~np.isin(bar_hour, np.asarray(hours, dtype=np.int64))

# Out-of-sample samples thinner than this are noise, not evidence.
MIN_TEST_TRADES = 12

# Reported when nothing lost: the best a profit factor can describe. A run with
# no losses has no denominator, and returning the win total instead silently
# swaps a ratio for a sum - the same score then means "excellent" or "dreadful"
# depending only on how big the wins happened to be. Finite rather than inf
# because these numbers are serialised into /api/ai and /api/opt/history, and
# json.dumps writes ``Infinity``, which is not valid JSON.
PF_NO_LOSSES = 99.0
# Same bar used by walk_forward's validated flag and the optimizer's apply gate,
# so the UI never labels a candidate "validated" that auto-apply would reject.
MIN_OOS_PF = 1.10

# How the validation slice picks among candidates that already cleared the
# gates. ``score`` is the shipped formula (net_r × sample × dd). The others
# are measurement tools: they change which survivor wins, not whether a
# survivor is valid.
SELECTION_METRICS = ("score", "money_per_day", "gap_freq", "costed_e")


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
    trade_events: list = field(default_factory=list)  # (entry_ts, exit_ts, r)

    @property
    def win_rate(self) -> float:
        return self.wins / self.trades * 100.0 if self.trades else 0.0

    @property
    def expectancy(self) -> float:
        return self.net_r / self.trades if self.trades else 0.0

    @property
    def profit_factor(self) -> float:
        if self.gross_loss_r <= 0:
            return PF_NO_LOSSES if self.gross_win_r > 0 else 0.0
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


def _payoff_ratio(slice_dict: dict[str, Any]) -> float:
    """avg win / avg loss from a Result.as_dict payload."""
    wins = int(slice_dict.get("wins") or 0)
    losses = int(slice_dict.get("losses") or 0)
    pf = float(slice_dict.get("profit_factor") or 0)
    if wins <= 0 or losses <= 0 or pf <= 0:
        return 0.0
    return pf * losses / wins


def selection_value(slice_dict: dict[str, Any], metric: str, days: float, *,
                    risk_dollar: float = 1.0, min_trades: int = 25) -> float:
    """Rank key for one already-gated slice. Gates are applied elsewhere."""
    metric = metric if metric in SELECTION_METRICS else "score"
    if metric == "score":
        return float(slice_dict.get("score") or 0.0)
    n = int(slice_dict.get("trades") or 0)
    e = float(slice_dict.get("expectancy") or 0.0)
    span = max(float(days), 1e-9)
    tpd = n / span
    if metric == "money_per_day":
        return e * tpd * float(risk_dollar)
    if metric == "gap_freq":
        ratio = _payoff_ratio(slice_dict)
        if ratio <= 0:
            return 0.0
        be = 100.0 / (1.0 + ratio)
        return (float(slice_dict.get("win_rate") or 0.0) - be) * tpd
    # costed_e: holdout/validation E, but only once n clears the same
    # min_trades the score formula uses as its sample floor. Below that the
    # number is noise; returning 0 keeps the candidate behind any real edge.
    if n < max(1, int(min_trades)):
        return 0.0
    return e


def rank_for_selection(candidates: list[dict[str, Any]], metric: str,
                       validation_days: float, *,
                       risk_dollar: float = 1.0,
                       min_trades: int = 25) -> list[dict[str, Any]]:
    """Order gated candidates. Default metric reproduces the old tuple sort."""
    metric = metric if metric in SELECTION_METRICS else "score"

    def key(c: dict[str, Any]) -> tuple[float, float]:
        valid = c.get("validation") or {}
        if metric == "score":
            return (float(valid.get("score") or 0.0), float(c.get("score") or 0.0))
        return (
            selection_value(valid, metric, validation_days,
                            risk_dollar=risk_dollar, min_trades=min_trades),
            float(c.get("score") or 0.0),
        )

    return sorted(candidates, key=key, reverse=True)


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
            return _drop_blocked_entry_hours(cfg, times, np.ones(times.size, dtype=bool))
        return _drop_blocked_entry_hours(cfg, times, ~weekend)

    if not cfg.use_sessions:
        windows: list[tuple[int, int]] = []
    else:
        windows = cfg.session_windows()

    allowed_day = np.isin(days, np.array(cfg.trade_days or [1, 2, 3, 4, 5], dtype=np.int64))

    if not windows:
        return _drop_blocked_entry_hours(cfg, times, allowed_day)

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
    return _drop_blocked_entry_hours(cfg, times, mask)


def imputed_spread_pts(spread: np.ndarray) -> np.ndarray:
    """Replace recorded-zero spreads with the symbol's own median quote.

    GER40 M30: 24% of 90k bars have spread 0, and the first fifth is *all*
    zeros - a history hole, not a free market. Charging those bars as 0
    (AV1) made the search pick a max_spread_atr below the live quote.
    Dropping them would throw away the price path and rewrite WF windows.
    Median of the bars that *do* quote keeps the calendar and prices the
    hole at what this symbol typically costs.
    """
    pts = np.asarray(spread, dtype=np.float64)
    quoted = pts[pts > 0]
    if quoted.size == 0:
        return pts
    return np.where(pts > 0, pts, float(np.median(quoted)))


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


def stop_floor_const(min_stop: float | None, point: float) -> float:
    """Broker stop floor used when the caller has a single number, not a series.

    ``None`` means the caller never asked the broker. ``0.0`` is what
    ``min_stop_distance`` returns when symbol info is missing - also unknown.
    Both become ten points. Zero is the one that used to be swallowed by
    ``if min_stop else`` with no warning, and by a different rule in each
    caller: simulate() took it as a floor of zero, walk_forward() as ten
    points.

    Deliberately silent. This runs inside the optimizer's worker PROCESSES
    (ProcessPoolExecutor), thousands of times per sweep, and logbus serialises
    on a thread lock that does not reach across processes - its rotation is a
    read-truncate-rewrite that two processes would interleave. The warning
    belongs where the number is read once, in the parent: see
    Optimizer._plan_symbol.
    """
    if min_stop is None:
        return float(point) * 10.0
    value = float(min_stop)
    if value == 0.0:
        return float(point) * 10.0
    return value


def stop_fill_price(is_buy: bool, sl: float, bar_open: float,
                    bar_high: float, bar_low: float,
                    trigger_pad: float = 0.0) -> float | None:
    """Stop/trail fill price, or None if this bar did not trigger the stop.

    Trigger is the live one: long on ``bar_low <= sl``, short on
    ``bar_high + trigger_pad >= sl`` (the pad is the bar's spread so a short
    covers on the ask). Fill used to be the SL even when the bar *opened*
    through it — paper then booked a clean −1R on a gap that live fills near
    the open. GAP-1 measured that gift at 8% of book holdout net R.

    When the open is already through the SL, fill is the open. The trigger
    pad stays a trigger, not a second charge. Flatten/time are not this
    function; they already exit at close.
    """
    if is_buy:
        if bar_low > sl:
            return None
        return float(bar_open) if bar_open < sl else float(sl)
    if bar_high + float(trigger_pad) < sl:
        return None
    return float(bar_open) if bar_open > sl else float(sl)


def max_open_from_cfg(cfg) -> int:
    """Concurrent slots paper must score the same way live caps them.

    ``simulate`` defaults to 1. ``walk_forward`` and the charged holdout used
    to omit the argument, so a config with ``max_positions=2`` was still
    scored as 1 - the number that decided whether stacking was even worth
    turning on. At ``max_positions=1`` this still returns 1, and every
    existing search result stays bit-identical.
    """
    try:
        n = int(getattr(cfg, "max_positions", 1) or 1)
    except (TypeError, ValueError):
        n = 1
    return max(1, n)


def simulate(cache: IndicatorCache, sig, open_: np.ndarray, spread_pts: np.ndarray,
             point: float, p: Params, tradable: np.ndarray | None = None,
             lo: int = 0, hi: int | None = None, commission_price: float = 0.0,
             entries: np.ndarray | None = None,
             spread_price: np.ndarray | None = None,
             min_stop: float | np.ndarray | None = None,
             flatten: np.ndarray | None = None,
             max_open: int = 1,
             block_reverse: bool = False,
             reverse_on_signal: bool = False,
             breakeven_at_r: float = 0.0,
             mae_close_bars: int = 0,
             mae_close_r: float = 0.0) -> Result:
    """Replay one bar window using an already-computed signal set.

    ``entries`` and ``spread_price`` are optional precomputed views of values
    that are identical for every window and every combination sharing a signal
    set. Passing them in is purely a caching shortcut - when omitted they are
    derived here exactly as before, and either way the numbers are the same.

    ``reverse_on_signal`` is a measurement switch, default off. Off is the live
    rule: an opposite signal while a slot is full is dropped and the open
    trade waits for its stop. On closes that trade at the flip's fill bar and
    opens the other side. Search/walk_forward never pass it.

    ``block_reverse`` is the live hedge veto. Default off so a direct
    ``max_open>1`` call still means what older measurements meant (hedges
    allowed). ``walk_forward`` and the charged holdout pass it on, because
    live never hedges: risk.py's "ters yonde acik pozisyon var" fires at
    any ``max_positions``. At ``max_open=1`` the flag is a no-op - the
    slot cap already drops the opposite fill.

    ``breakeven_at_r`` is the same kind of switch (BE-1). Zero is live: the
    trail is the only way the stop crosses entry. A positive value pulls the
    stop to entry plus commission once unrealised gain reaches that many R,
    without pulling a better trail back. Search/walk_forward never pass it.

    ``mae_close_bars`` / ``mae_close_r`` are LOSS-3. Zero bars is live: MAE
    is not an exit. A positive bar count closes the trade at that bar's
    close if MAE through those bars exceeds the R threshold. Search and
    walk_forward never pass them.
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
    # Live short stops fire on the ASK. Paper OHLC is bid, so the trigger is
    # high + this bar's spread. That pad is a price reference, not a cost:
    # charge_costs may zero ``spread_price`` (the fill), but the broker still
    # covers a short when ask trades through the SL. Exit price stays the SL.
    trigger_pad = (imputed_spread_pts(np.asarray(spread_pts, dtype=np.float64))
                   * float(point)).tolist()
    # Falls back to the old flat approximation when the caller doesn't know the
    # symbol's real broker floor (``mt5client.min_stop_distance`` - stops_level,
    # freeze_level, current spread) - live can legally require a wider stop than
    # this default, which understates the true stop/trail floor for symbols
    # where the broker's own minimum exceeds ten points.
    if min_stop is None or (
            not isinstance(min_stop, np.ndarray) and float(min_stop) == 0.0):
        min_stop = stop_floor_const(
            None if min_stop is None else float(min_stop), point)
    # Per-bar, when the caller supplies a series. mt5client.min_stop_distance is
    # max(stops_level, spread * 1.5, point * 10), so the floor MOVES with the
    # spread - and the optimizer was passing one snapshot taken at plan time,
    # used for months of bars. A sweep planned in a quiet minute therefore let
    # the trail hug price in a way live could not, and every trailed exit gave
    # back less here than it does there. That is one-directional: it inflates
    # exactly the winners the reward ratio is built from.
    #
    # This is not a cost being charged - charge_costs governs that, and the
    # spread series it zeroes is a different one. This is where the broker will
    # let the stop sit.
    min_stop_at = (min_stop if isinstance(min_stop, np.ndarray)
                   else np.full(open_.size, float(min_stop), dtype=np.float64))

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
    max_open = max(1, int(max_open or 1))
    breakeven_at_r = float(breakeven_at_r or 0.0)
    mae_close_bars = max(0, int(mae_close_bars or 0))
    mae_close_r = float(mae_close_r or 0.0)

    def _cooldown_bars() -> int:
        cooldown_bars = 0
        if p.cooldown_sec > 0 and cache.tf_seconds > 0:
            from .models import is_scalp_strategy
            max_bars_cd = 1 if (not is_scalp_strategy(p.strategy)
                                and cache.tf_seconds >= 900) else 2
            capped = min(int(p.cooldown_sec), max_bars_cd * int(cache.tf_seconds))
            cooldown_bars = max(0, capped // int(cache.tf_seconds))
        return cooldown_bars

    def _record_trade(is_buy, entry, sl_dist, s, j0, exit_bar, exit_price, reason):
        nonlocal equity, peak, streak, bar_total
        if exit_price is None:
            exit_price = close[exit_bar] + (0.0 if is_buy else s)
            reason = "time"
        move = (exit_price - entry) if is_buy else (entry - exit_price)
        r = float((move - commission_price) / sl_dist)
        res.cost_r += float((commission_price + s) / sl_dist)
        res.trades += 1
        res.net_r += r
        res.trade_rs.append(r)
        res.trade_events.append((int(cache.times[j0]), int(cache.times[exit_bar]), r))
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

    def _trail_one(is_buy, entry, sl, trailing, j, s, sl_dist):
        c = close[j]
        a = atr[j]
        gain = (c - entry) if is_buy else (entry - c)
        if not (a > 0 and gain > 0):
            return sl, trailing
        target = None
        breakeven_locked = (sl >= entry) if is_buy else (sl <= entry)
        if p.trail_start_atr > 0 and gain >= a * p.trail_start_atr:
            trail_atr = c - a * p.trail_step_atr if is_buy else c + a * p.trail_step_atr
            trail = trail_atr
            if structural and swing_lo is not None and swing_hi is not None:
                struct_sl = (swing_lo[j] - a * 0.15) if is_buy \
                    else (swing_hi[j] + a * 0.15)
                if p.trail_mode == "hybrid":
                    trail = max(trail_atr, struct_sl) if is_buy else min(trail_atr, struct_sl)
                else:
                    trail = struct_sl
            if target is None or (trail > target if is_buy else trail < target):
                target = trail
        if (breakeven_at_r > 0 and sl_dist > 0
                and gain >= breakeven_at_r * sl_dist):
            be_sl = entry + commission_price if is_buy else entry - commission_price
            if target is None:
                target = be_sl
            else:
                target = max(target, be_sl) if is_buy else min(target, be_sl)
        if target is None:
            return sl, trailing
        ms = float(min_stop_at[j])
        step = trail_min_step(ms, a, p.trail_step_atr)
        if is_buy and target > sl:
            new_sl = min(target, c - ms)
            if (new_sl - sl >= step
                    and not (breakeven_locked and new_sl < entry)):
                return new_sl, True
        elif not is_buy and target < sl:
            new_sl = max(target, c + ms)
            if (sl - new_sl >= step
                    and not (breakeven_locked and new_sl > entry)):
                return new_sl, True
        return sl, trailing

    def _exit_check(is_buy, sl, trailing, j, s):
        # Four corners, live:
        #   long stop / long trail  — bid vs SL  → bar_low <= sl
        #   short stop / short trail — ask vs SL  → bar_high + pad >= sl
        # Fill is the SL unless the bar opened through it (then the open).
        # Flatten is a market cover (close, +pad on a short), not a stop.
        bar_high, bar_low = high[j], low[j]
        fill = stop_fill_price(is_buy, sl, open_l[j], bar_high, bar_low,
                               float(trigger_pad[j]))
        if fill is not None:
            return fill, ("trail" if trailing else "stop")
        if flatten is not None and flatten[j]:
            return close[j] + (0.0 if is_buy else s), "flatten"
        return None, None

    def _mae_tick(is_buy, entry, sl_dist, j0, j, mae_px):
        # LOSS-3: accumulate MAE; fire only on the Nth bar, after stop/flatten.
        if mae_close_bars <= 0 or sl_dist <= 0:
            return mae_px, False
        bar_high, bar_low = high[j], low[j]
        if is_buy:
            adverse = entry - bar_low
        else:
            adverse = bar_high + float(trigger_pad[j]) - entry
        if adverse > mae_px:
            mae_px = adverse
        held = j - j0 + 1
        if held == mae_close_bars and (mae_px / sl_dist) > mae_close_r:
            return mae_px, True
        return mae_px, False

    if max_open > 1:
        opens: list[dict] = []
        cool_until = -1
        for j in range(lo, n):
            still: list[dict] = []
            for pos in opens:
                px, reason = _exit_check(pos["is_buy"], pos["sl"], pos["trailing"], j, pos["s"])
                if px is not None:
                    _record_trade(pos["is_buy"], pos["entry"], pos["sl_dist"],
                                  pos["s"], pos["j0"], j, px, reason)
                    continue
                mae_px, mae_hit = _mae_tick(
                    pos["is_buy"], pos["entry"], pos["sl_dist"],
                    pos["j0"], j, pos.get("mae_px", 0.0))
                pos["mae_px"] = mae_px
                if mae_hit:
                    _record_trade(
                        pos["is_buy"], pos["entry"], pos["sl_dist"],
                        pos["s"], pos["j0"], j,
                        close[j] + (0.0 if pos["is_buy"] else pos["s"]),
                        "mae")
                    continue
                if j >= n - 1:
                    _record_trade(pos["is_buy"], pos["entry"], pos["sl_dist"],
                                  pos["s"], pos["j0"], j, None, "time")
                    continue
                sl, trailing = _trail_one(pos["is_buy"], pos["entry"], pos["sl"],
                                          pos["trailing"], j, pos["s"],
                                          pos["sl_dist"])
                pos["sl"] = sl
                pos["trailing"] = trailing
                still.append(pos)
            opens = still

            while ptr < entries.size and int(entries[ptr]) + 1 <= j:
                i = int(entries[ptr])
                j0 = i + 1
                if j0 != j:
                    ptr += 1
                    continue
                if j0 >= n - 1:
                    ptr += 1
                    break
                if tradable is not None and not tradable[j0]:
                    ptr += 1
                    continue
                atr_entry = atr[i]
                if not math.isfinite(atr_entry) or atr_entry <= 0:
                    ptr += 1
                    continue
                s = float(spread_price[j0])
                if p.max_spread_atr > 0 and s > atr_entry * p.max_spread_atr:
                    ptr += 1
                    continue
                if bool(buy_flags[i]) and bool(sell_flags[i]):
                    ptr += 1
                    continue
                is_buy = bool(buy_flags[i])
                if not is_buy and not bool(sell_flags[i]):
                    ptr += 1
                    continue
                price_ref = float(open_[j0] + s) if is_buy else float(open_[j0] - s)
                if (p.min_atr_ratio > 0 and price_ref > 0
                        and (atr_entry / price_ref) < p.min_atr_ratio):
                    ptr += 1
                    continue
                if i <= cool_until:
                    ptr += 1
                    continue
                if reverse_on_signal and opens:
                    # Opposite signal: cover what is open the other way at this
                    # bar's open (the fill the new side would have taken), then
                    # the slot check below decides whether the flip itself
                    # lands. Same-side signals still hit the cap, as live does.
                    kept: list[dict] = []
                    for pos in opens:
                        if pos["is_buy"] == is_buy:
                            kept.append(pos)
                            continue
                        _record_trade(
                            pos["is_buy"], pos["entry"], pos["sl_dist"],
                            pos["s"], pos["j0"], j,
                            float(open_l[j] + (0.0 if pos["is_buy"] else s)),
                            "reverse")
                    opens = kept
                if block_reverse and any(pos["is_buy"] != is_buy for pos in opens):
                    # The live rule the stacked path was missing. With
                    # max_open > 1 this replay would open a hedge beside an
                    # existing position, which the engine refuses outright
                    # (risk.py's "ters yonde acik pozisyon var"). Measuring a
                    # raised limit without this compares against a world we
                    # would never run - and biases against it twice over, since
                    # the hedge both loses on its own account and occupies the
                    # slot a same-direction entry would otherwise have taken.
                    ptr += 1
                    continue
                if len(opens) >= max_open:
                    ptr += 1
                    continue
                sl_dist = max(atr_entry * p.sl_atr_mult, float(min_stop_at[j0]))
                entry = float(open_[j0] + s) if is_buy else float(open_[j0] - s)
                sl = entry - sl_dist if is_buy else entry + sl_dist
                opens.append({
                    "is_buy": is_buy, "entry": entry, "sl": sl,
                    "sl_dist": sl_dist, "trailing": False, "j0": j0, "s": s,
                    "mae_px": 0.0,
                })
                cd = _cooldown_bars()
                if cd:
                    cool_until = max(cool_until, j0 + cd - 1)
                ptr += 1
        res.avg_bars = bar_total / res.trades if res.trades else 0.0
        res.exits = exits
        return res

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
        # Mirrors live's engine._try_entry ATR gate: NaN compares False to
        # everything, so a bare ``<= 0`` check is not fail-closed for it - a
        # NaN'd bar (corrupt input, indicator edge case) would otherwise
        # size sl_dist/tp_dist off it below and produce a garbage R value.
        if not math.isfinite(atr_entry) or atr_entry <= 0:
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
        price_ref = float(open_[j0] + s) if is_buy else float(open_[j0] - s)
        if (p.min_atr_ratio > 0 and price_ref > 0
                and (atr_entry / price_ref) < p.min_atr_ratio):
            ptr += 1
            continue
        sl_dist = max(atr_entry * p.sl_atr_mult, float(min_stop_at[j0]))
        entry = float(open_[j0] + s) if is_buy else float(open_[j0] - s)
        sl = entry - sl_dist if is_buy else entry + sl_dist
        # No take-profit level exists in this model, so the only way out is the
        # stop - hard at first, trailing once the move has paid for it. See
        # SymbolConfig's exit-model note for why there is nothing else.
        # ``trailing`` separates the two in the exit histogram: a "stop" is the
        # original risk being hit, a "trail" is giving back part of a move that
        # had already gone our way.
        trailing = False
        mae_px = 0.0

        exit_price = None
        exit_bar = j0
        reason = "time"

        # Runs to the end of the sample: nothing closes a position because it
        # has been open too long. A trade that neither stops out nor trails out
        # simply stays open, exactly as it would live. This does not blow up the
        # cost of a sweep - ``ptr`` below skips every entry signal up to the
        # exit bar, so no two simulated trades overlap and the loop still visits
        # each bar at most once per pass.
        for j in range(j0, n):
            bar_high, bar_low = high[j], low[j]
            fill = stop_fill_price(is_buy, sl, open_l[j], bar_high, bar_low,
                                   float(trigger_pad[j]))
            if fill is not None:
                exit_price, reason = fill, ("trail" if trailing else "stop")
            if exit_price is not None:
                exit_bar = j
                break

            if flatten is not None and flatten[j]:
                # Live force-closes at the current market price the instant the
                # session/day-end band starts, ahead of trail/BE/stale checks -
                # same ordering here (checked immediately after the stop).
                exit_price = close[j] + (0.0 if is_buy else s)
                reason = "flatten"
                exit_bar = j
                break

            mae_px, mae_hit = _mae_tick(is_buy, entry, sl_dist, j0, j, mae_px)
            if mae_hit:
                exit_price = close[j] + (0.0 if is_buy else s)
                reason = "mae"
                exit_bar = j
                break

            if reverse_on_signal and j > j0:
                # Signal on closed bar j-1 fills at this bar's open. An
                # opposite print covers the open side there; a same-side
                # print is ignored (max_open=1 has no slot). Stop/flatten
                # above still win if they also fire on this bar.
                sig_i = j - 1
                two_way = bool(buy_flags[sig_i]) and bool(sell_flags[sig_i])
                want_buy = bool(buy_flags[sig_i]) and not two_way
                want_sell = bool(sell_flags[sig_i]) and not two_way
                flip = (is_buy and want_sell) or ((not is_buy) and want_buy)
                if flip and (tradable is None or tradable[j]):
                    s_now = float(spread_price[j])
                    exit_price = float(open_l[j] + (0.0 if is_buy else s_now))
                    reason = "reverse"
                    exit_bar = j
                    atr_next = atr[sig_i]
                    new_buy = not is_buy
                    can_open = (
                        math.isfinite(atr_next) and atr_next > 0
                        and not (p.max_spread_atr > 0
                                 and s_now > atr_next * p.max_spread_atr)
                    )
                    price_ref = (float(open_l[j] + s_now) if new_buy
                                 else float(open_l[j] - s_now))
                    if (can_open and p.min_atr_ratio > 0 and price_ref > 0
                            and (atr_next / price_ref) < p.min_atr_ratio):
                        can_open = False
                    if can_open:
                        _record_trade(is_buy, entry, sl_dist, s, j0,
                                      exit_bar, exit_price, reason)
                        sl_dist = max(atr_next * p.sl_atr_mult,
                                      float(min_stop_at[j]))
                        entry = price_ref
                        sl = entry - sl_dist if new_buy else entry + sl_dist
                        is_buy = new_buy
                        s = s_now
                        trailing = False
                        j0 = j
                        exit_price = None
                        reason = "time"
                        mae_px = 0.0
                        continue
                    break

            c = close[j]
            a = atr[j]
            gain = (c - entry) if is_buy else (entry - c)
            if a > 0 and gain > 0:
                target = None
                # Mirrors engine._update_stop's breakeven_locked guard: once the
                # trail has ratcheted the stop to or past entry, the min_stop
                # clamp below must never put it back on the losing side. Live
                # has no separate breakeven step - the trail is above entry
                # once ``gain`` exceeds ``trail_step_atr * a``, whatever
                # trail_start_atr is. ``breakeven_at_r`` (paper, default 0)
                # is the BE-1 measurement: lock to entry+commission once
                # gain reaches that many R, without pulling a better trail.
                breakeven_locked = (sl >= entry) if is_buy else (sl <= entry)
                if p.trail_start_atr > 0 and gain >= a * p.trail_start_atr:
                    trail_atr = c - a * p.trail_step_atr if is_buy else c + a * p.trail_step_atr
                    trail = trail_atr
                    # Both series or neither (line 341-342), so the short
                    # leg's swing_hi cannot be None here. Named anyway: the
                    # guard used to test only swing_lo while the body indexes
                    # both, so the day those two stop being built together the
                    # crash lands on shorts only, in the trail, under one
                    # trail_mode - the least reproducible shape there is.
                    if structural and swing_lo is not None and swing_hi is not None:
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
                if (breakeven_at_r > 0 and sl_dist > 0
                        and gain >= breakeven_at_r * sl_dist):
                    be_sl = (entry + commission_price if is_buy
                             else entry - commission_price)
                    if target is None:
                        target = be_sl
                    else:
                        target = (max(target, be_sl) if is_buy
                                  else min(target, be_sl))
                if target is not None:
                    # Live will not send a modify for an improvement smaller
                    # than this. Without the same floor here the replay
                    # ratcheted the stop on ANY improvement, so the simulated
                    # trail rode closer behind price than live's ever can and
                    # gave back less on the reversal that ends the trade - a
                    # one-directional optimism in every number the apply gates
                    # read, and net_r is what risk._edge_metric turns into a
                    # live lot multiplier.
                    ms = float(min_stop_at[j])
                    step = trail_min_step(ms, a, p.trail_step_atr)
                    if is_buy and target > sl:
                        new_sl = min(target, c - ms)
                        if (new_sl - sl >= step
                                and not (breakeven_locked and new_sl < entry)):
                            sl = new_sl
                            trailing = True
                    elif not is_buy and target < sl:
                        new_sl = max(target, c + ms)
                        if (sl - new_sl >= step
                                and not (breakeven_locked and new_sl > entry)):
                            sl = new_sl
                            trailing = True
            exit_bar = j

        if exit_price is None:
            exit_price = close[exit_bar] + (0.0 if is_buy else s)
            reason = "time"

        move = (exit_price - entry) if is_buy else (entry - exit_price)
        r = float((move - commission_price) / sl_dist)
        res.cost_r += float((commission_price + s) / sl_dist)
        res.trades += 1
        res.net_r += r
        res.trade_rs.append(r)
        res.trade_events.append((int(cache.times[j0]), int(cache.times[exit_bar]), r))
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


def grid_total_of(grid: dict[str, Any]) -> int:
    """Cartesian size of the list-valued axes. Empty axes do not count."""
    keys = [k for k, v in grid.items() if isinstance(v, list) and v]
    if not keys:
        return 0
    return int(math.prod(len(grid[k]) for k in keys))


def coverage_of(grid_total: int, max_combos: int) -> float | None:
    """Search budget against the family grid, capped at 1.

    This is ``max_combos / grid_total``, not evaluated-combos / grid. A
    sparse sample that happened to finish early must not look like full
    coverage. Unknown or empty grids are None, not 0.
    """
    total = int(grid_total)
    if total <= 0:
        return None
    return min(1.0, float(int(max_combos)) / float(total))


def _values(keys: list[str], grid: dict[str, list], idx: tuple[int, ...]) -> dict[str, Any]:
    return {k: grid[k][i] for k, i in zip(keys, idx, strict=True)}


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


def sweep_budget(max_combos: int, refine_rounds: int) -> int:
    """Backtests one sweep actually runs: the coarse pass plus each refine round.

    The refine rounds are not free extra work on top of a 'max_combos' sweep -
    each one gets its own full budget, so a sweep costs 4x max_combos at the
    shipped refine_rounds=3. The optimizer's progress counter used to report
    plain max_combos per sweep, which made the panel state a total four times
    smaller than the work being done (1.12M against a real 4.48M). The ratio -
    and so the percentage - was right, because both sides used the same wrong
    unit; the absolute number a human reads was not. One formula, used by the
    code that spends the budget and by the code that reports it.
    """
    return int(max_combos) * (1 + max(0, int(refine_rounds)))


def walk_forward(cfg: SymbolConfig, bars, point: float, tf_seconds: int, grid: dict[str, list],
                 min_trades: int, segments: int, max_combos: int,
                 min_positive_ratio: float = 0.6, plateau_weight: float = 0.4,
                 commission_price: float = 0.0, refine_rounds: int = 2,
                 should_cancel=None, on_progress=None,
                 min_stop: float | None = None, all_hours: bool = False,
                 day_end_flatten_min: int = 0,
                 max_cost_share: float = 0.0,
                 spread_scale: float = 1.0,
                 charge_costs: bool = True,
                 selection_metric: str = "score",
                 risk_dollar: float = 1.0,
                 combo_seed: int = 7) -> dict[str, Any]:
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

    flatten = flatten_mask(cfg, bars.time, all_hours, day_end_flatten_min)
    _tradable_by_hours: dict[tuple[int, ...], np.ndarray] = {}

    def _hours_key(values: dict[str, Any] | None = None) -> tuple[int, ...]:
        raw = (values or {}).get("blocked_entry_hours", cfg.blocked_entry_hours)
        return tuple(sorted({int(h) for h in (raw or [])
                             if str(h).lstrip("-").isdigit() and 0 <= int(h) <= 23}))

    def tradable_for(values: dict[str, Any] | None = None) -> np.ndarray:
        key = _hours_key(values)
        hit = _tradable_by_hours.get(key)
        if hit is None:
            probe = copy.copy(cfg)
            probe.blocked_entry_hours = list(key)
            hit = session_mask(probe, bars.time, all_hours)
            _tradable_by_hours[key] = hit
        return hit

    if not (float(point) > 0):
        # This used to substitute 1e-5, which is not a conservative default -
        # it is a made-up price scale, and every cost in the sweep is measured
        # against it. ``spread_price = bars.spread * point``, so on an index
        # quoting point 0.01 the substitution understates spread by a factor
        # of a thousand and the search prices trading as very nearly free.
        #
        # Measured, not argued: same 3000 bars, spread 30 points. With the
        # real 0.01 the sweep finds no viable config at all. With point 0 it
        # returns ok=True and a winner carrying cost_per_trade_r 0.0003. So
        # the failure is not a slightly optimistic number - it turns "nothing
        # here is tradable" into "here is your config, and it costs nothing".
        #
        # Optimizer._plan_symbol checks ``info is None`` but never the point
        # inside it, so a partially populated symbol_info reaches this
        # unguarded. Refusing matches what the rest of the codebase already
        # does with an unusable cost input: cost_by_hour raises 503 on the
        # same condition, and IndicatorCache treats a missing cost series as
        # "produce no signals" rather than invent one.
        return {"ok": False,
                "error": (f"{cfg.symbol}: point degeri okunamadi ({point}) - "
                          f"maliyet modeli kurulamaz, arama yapilmadi")}
    point = float(point)

    # Identical for every combination in the sweep, so it is built once instead
    # of reallocated inside every one of the tens of thousands of simulations.
    # ``spread_scale`` closes the one gap between what this charges and what
    # the live engine enforces. simulate() gates on the entry BAR's recorded
    # spread; engine._try_entry gates on the CURRENT TICK's, and the tick runs
    # wider. So a ceiling chosen here was applied there against a bigger
    # number - which is how FRA40's 0.05 shut all fourteen hours of its own
    # session, and why USDCHF was deleted for the same thing.
    #
    # The factor is the engine's own measured median of tick spread over bar
    # spread for this symbol, collected continuously and only used once it has
    # cleared its sample threshold. Median rather than a high percentile on
    # purpose: the bar spread is itself a typical value with half the bars
    # above it, so scaling by the median shifts the LEVEL to what live sees
    # while leaving that statistical relationship where the backtest already
    # had it. A p90 would make the search far more pessimistic than the
    # backtest has ever been, on no evidence that it should be.
    scale = float(spread_scale) if spread_scale and spread_scale > 0 else 1.0
    spread_pts = imputed_spread_pts(bars.spread)
    spread_price = spread_pts * point * scale
    # The broker's own floor under any stop, per bar. mt5client.min_stop_distance
    # is max(stops_level, spread * 1.5, point * 10) and the caller passes the
    # value it read once at plan time; only the stops_level part of that is
    # actually constant. Rebuilding the spread-driven part from each bar's own
    # recorded spread makes the trail as constrained here as it is live.
    #
    # Deliberately built from the RAW bar spread, not from ``spread_price`` -
    # that series is zeroed when costs are switched off, and this is not a cost.
    # A stop cannot sit inside the spread whatever the accounting says.
    raw_spread_price = spread_pts * point
    floor_const = stop_floor_const(min_stop, point)
    min_stop_series = np.maximum(floor_const, raw_spread_price * 1.5)

    if not charge_costs:
        # Fill at the printed price: buy the open, sell the close. The spread
        # is not only an accounting drag here - it moves the fills themselves
        # (entry pays it on a buy, the exit and the stop check pay it on a
        # sell), so zeroing the series is what actually removes it, and
        # cost_r then accumulates nothing on its own.
        spread_price = np.zeros_like(spread_price)
        commission_price = 0.0
    # The round-turn cost the simulation will actually charge this trade. The
    # scalping families size their entry threshold against it, so it has to be
    # this exact series and not an approximation of it.
    cost_price = spread_price + float(commission_price)

    cache = IndicatorCache(bars.high, bars.low, bars.close, bars.time, tf_seconds,
                           bars.open, bars.volume, cost_price)
    combo_seed = int(combo_seed)
    keys, combos = combos_from_grid(grid, max_combos, seed=combo_seed)
    # Same helper the stamp test checks, rather than a second copy of the
    # formula: the two drifting apart would make coverage quietly wrong
    # in the stamp while every test still passed.
    grid_total = grid_total_of(grid)
    coverage = coverage_of(grid_total, max_combos)

    # ``selection`` is windows[:-2], i.e. segments-2 windows (validation and
    # holdout are held out) - the discount below divided by segments-1,
    # understating the trades expected per selection window and making the
    # sample-size discount stricter than the actual window count implies.
    per_segment_trades = max(6, int(min_trades / max(1, segments - 2)))

    # Signals depend only on the entry-side parameters (``Params.key``); the
    # exit grid - the hard stop, the trail, the spread gate - does not
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

    slot_cap = max_open_from_cfg(cfg)

    def run_window(p: Params, window: tuple[int, int], sig=None,
                   entries: np.ndarray | None = None,
                   values: dict[str, Any] | None = None) -> Result:
        if sig is None:
            sig, entries = signals_for(p)
        return simulate(cache, sig, bars.open, bars.spread, point, p,
                        tradable_for(values),
                        window[0], window[1], commission_price,
                        entries=entries, spread_price=spread_price,
                        min_stop=min_stop_series,
                        flatten=flatten,
                        max_open=slot_cap,
                        block_reverse=True)

    def evaluate(p: Params, sig=None, entries: np.ndarray | None = None,
                 last: Result | None = None,
                 values: dict[str, Any] | None = None) -> tuple[list[Result], float, float]:
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
        parts = [run_window(p, w, sig, entries, values) for w in windows]
        if last is not None:
            parts.append(last)                      # keeps the segment order
        scored = [r.score(per_segment_trades) for r in parts]
        positive = sum(1 for r in parts if r.net_r > 0) / len(parts)
        return parts, (sum(scored) / len(scored)), positive

    def prescreen(p: Params, sig, entries: np.ndarray,
                  values: dict[str, Any] | None = None) -> Result:
        """Cheap first look: score the most recent selection segment only.

        Successive halving. A setting that cannot pay on one segment will never
        clear ``min_positive_ratio`` across all of them, so paying for the other
        segments is wasted work. Survivors are then scored the normal way, so
        every number that reaches ranking or the apply gate is still the full
        multi-segment score - this only decides what is worth measuring.
        """
        return run_window(p, selection[-1], sig, entries, values)

    def measure(values: dict[str, Any], window: tuple[int, int]) -> Result:
        p = Params.from_config(cfg, **values)
        return run_window(p, window, values=values)

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
    rejected_costly = 0
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
        nonlocal rejected_inconsistent, rejected_costly, evaluated, screened
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
                    last = prescreen(p, sig, entries, values)
                    if last.score(per_segment_trades) <= 0.0:
                        # No edge on the most recent segment; record the dead
                        # spot for the plateau blend and move on without the
                        # rest of the simulation.
                        pool[idx] = 0.0
                        screened += 1
                        if on_progress and i % 40 == 0:
                            on_progress(offset + i, budget, max(raw.values(), default=None))
                        continue

                parts, mean_score, positive = evaluate(p, sig, entries, last, values)
                pooled = _merge(parts)
                evaluated += 1
                pool[idx] = 0.0

                if pooled.trades >= min_trades and mean_score > 0:
                    # Spread+commission drag per trade, in R. The simulator has
                    # always measured this; nothing used it to reject anything,
                    # so the search happily picked tight-stop configs whose cost
                    # ate most of the risk - and the LIVE engine then refused
                    # every one of those entries at its own
                    # system.max_cost_pct_of_risk gate. The two halves disagreed:
                    # the optimizer proposed configs the engine would never
                    # trade, which is why some symbols sat at one or two live
                    # trades while their backtest looked fine. Screened here so
                    # a candidate that cannot be traded also cannot win.
                    cost_share = (pooled.cost_r / pooled.trades) if pooled.trades else 0.0
                    if max_cost_share > 0 and cost_share > max_cost_share:
                        rejected_costly += 1
                    elif positive < min_positive_ratio:
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

    total_budget = sweep_budget(max_combos, refine_rounds)
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
        # Name the reason that actually applied. Reporting "inconsistent across
        # segments" when every candidate was in fact rejected for cost sends
        # the operator looking for an edge problem that isn't there - the edge
        # may be fine and simply not worth its spread on this symbol.
        why = f"{rejected_inconsistent} kombinasyon segmentler arasi tutarsizdi"
        if rejected_costly:
            why = (f"{rejected_costly} kombinasyon maliyet tavanini asti"
                   + (f", {rejected_inconsistent} tanesi segmentler arasi tutarsizdi"
                      if rejected_inconsistent else ""))
        return {"ok": False, "combos": evaluated, "baseline": baseline,
                "rejected_inconsistent": rejected_inconsistent,
                "rejected_costly": rejected_costly,
                "grid_total": grid_total,
                "max_combos": int(max_combos),
                "coverage": coverage,
                "combo_seed": combo_seed,
                "error": f"tutarli kazanan parametre bulunamadi ({why})"}

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
            "min_positive_ratio": float(min_positive_ratio),
            "selection": detail[idx]["pooled"],
            "segments": detail[idx]["segments"],
            # OOS slices scored against the apply-gate sample size (12), not the
            # in-sample min_trades (often 40) - otherwise a clean 20-trade M5
            # holdout is ranked at half weight vs a noisier 40-trade M5 run.
            "validation": valid.as_dict(MIN_TEST_TRADES),
        })
    validation_days = round((int(bars.time[holdout[0]]) - int(bars.time[validation[0]]))
                            / 86400.0, 1)
    top = rank_for_selection(
        top, selection_metric, validation_days,
        risk_dollar=risk_dollar, min_trades=min_trades)
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
        "rejected_costly": rejected_costly,
        "bars": n,
        "segments": segments,
        # The cost regime this sweep actually ran under, carried out with the
        # numbers it produced. The setting can be flipped while a run is in
        # flight, so reading it again downstream describes the clock, not the
        # sweep - see Optimizer.apply's stamp.
        "charge_costs": bool(charge_costs),
        "min_positive_ratio": float(min_positive_ratio),
        "selection_metric": (
            selection_metric if selection_metric in SELECTION_METRICS else "score"),
        "holdout_bars": holdout[1] - holdout[0],
        "holdout_days": round((int(bars.time[-1]) - int(bars.time[holdout[0]])) / 86400.0, 1),
        "validation_days": validation_days,
        "span_days": round((int(bars.time[-1]) - int(bars.time[0])) / 86400.0, 1),
        "from": int(bars.time[0]),
        "to": int(bars.time[-1]),
        "finished_at": time.time(),
        "grid_total": grid_total,
        "max_combos": int(max_combos),
        "coverage": coverage,
        "combo_seed": combo_seed,
        "spread_scale": float(scale),
    }
