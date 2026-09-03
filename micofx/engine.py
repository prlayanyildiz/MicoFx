from __future__ import annotations

import calendar
import math
import threading
import time
from typing import Any

from . import account_lock, backtest, execution, sessions
from . import indicators as ind
from .autopilot import AutoPilot
from .execution import ExecutionMonitor
from .exits import harvest_trail_step, overlay_stop
from .logbus import LOG
from .models import (
    PRIMARY_LAND_KEYS,
    STRATEGIES,
    TIMEFRAMES,
    SymbolConfig,
    invalid_exit_param,
    is_scalp_strategy,
    scale_out_slice,
    strategy_allows_timeframe,
    trail_min_step,
)
from .mt5client import (
    AMBIGUOUS_RETCODES,
    DECISION_CLOCK_MAX_AGE_SEC,
    NON_RETRYABLE_RETCODES,
    Bars,
    MT5Client,
    live_stop_level,
    timeframe_seconds,
)
from .risk import (
    AUTOPSY_R_ABS_MAX,
    RiskManager,
    sanitize_autopsy_r,
    shakeout_size_note,
    shakeout_sl_atr_mult,
)
from .store import Store, as_dict, as_list, as_number
from .strategy import IndicatorCache, Params, Signals, compute, required_bars
from .supervisor import Supervisor

_BAR_INTEGRITY_REFRESH = 900.0  # rare full copy_rates with no new bar
_ENTRY_BLOCK_FLUSH_SEC = 45.0
_ACCOUNT_TTL = 2.0
# Panel polls /api/state every 3s. At 3.0 this TTL expired on every poll,
# so each tick walked all symbols through order_calc_margin on the MT5 lock
# the cycle already shares with the worker. 9s still refreshes lot/margin
# three times between position changes; ticket sig invalidates immediately.
_CAPACITY_TTL = 15.0
_CASH_FLOW_TTL = 30.0
_TERMINAL_FLAGS_TTL = 5.0
_PANEL_STATE_KEYS = (
    "symbol", "last_bar", "atr", "adx", "t3_rising", "htf", "k", "d", "signal",
    "primary_signal", "bars_ready", "note", "entry_block", "session", "spread_atr",
    "last_signal_at",
)

# A cooldown is meant to stop the same setup re-firing on the next bar or two,
# so it belongs on the strategy's own clock. The stored seconds were written for
# the M5-and-slower presets; left alone they would silently cost an M5 config
# five bars of opportunity per fill. Capped, never extended - a config that asks
# for a short pause still gets exactly what it asks for.
_COOLDOWN_BARS = 2
# Swing / higher-TF families already wait a full bar between signals; one bar of
# post-fill silence is enough. Two H1 bars would idle the symbol for two hours.
_COOLDOWN_BARS_SWING = 1
# Both moved to ``sessions`` so the walk-forward can refuse the same gap fills
# this gate refuses live. Re-exported under the old private name because the
# constant is quoted by name in tests and in OPTIMIZATIONS.md.
_MAX_SIGNAL_BAR_AGE_BARS = sessions.MAX_SIGNAL_BAR_AGE_BARS
signal_bar_expired = sessions.signal_bar_expired


def _round_or_none(value: float | None, digits: int) -> float | None:
    """round() that carries a "not measured" through instead of raising."""
    return None if value is None else round(value, digits)


def _fill_original_sl(side: str, entry: float, sl_dist: float,
                      reported_sl: float) -> float | None:
    """Persisted hard stop for autopsy/repair — never negative or zero."""
    try:
        rep = float(reported_sl or 0.0)
    except (TypeError, ValueError):
        rep = 0.0
    if rep > 0:
        return rep
    try:
        dist = float(sl_dist or 0.0)
        px = float(entry or 0.0)
    except (TypeError, ValueError):
        return None
    if dist <= 0 or px <= 0:
        return None
    if side == "buy":
        return px - dist
    if side == "sell":
        return px + dist
    return None


def _fill_log_price(result: dict[str, Any], fallback: float) -> float:
    try:
        px = float(result.get("price") or 0.0)
    except (TypeError, ValueError):
        px = 0.0
    return px if px > 0 else float(fallback or 0.0)

# Live-tick-spread / bar-spread histogram: buckets of 0.1 from 0.0 to 5.0,
# plus a final overflow bucket for anything above.
SPREAD_RATIO_STEP = 0.1
SPREAD_RATIO_BUCKETS = 51

# Past this, the newest tick stamp is no longer evidence of what time it is at
# the broker. Generous on purpose: ticks thin out overnight, and the case this
# has to catch is a shut market, which is hours away from this bound, not
# minutes.
BROKER_CLOCK_MAX_AGE_SEC = DECISION_CLOCK_MAX_AGE_SEC
CLOCK_STALE_WARN_SEC = 900.0
CLOCK_STALE_WARN_AFTER_CYCLES = 15
# Below this many samples the ratio is not reported or applied - a handful of
# ticks from one hour is exactly the reading that misled us once already.
SPREAD_RATIO_MIN_SAMPLES = 400

# Observation ring for entry-block *identity* (symbol, reason, bar_key, epoch).
# Counters in ``entry_blocks`` stay as they are; this does not replace them
# and is not read by any gate. Live rate measured 14-16.08: 156 signals in
# 2 days ~ 78/day. 2048 rows is ~26 days, a few hundred KB of JSON at most
# - small next to ``execution_samples``, enough for a G7-style window after
# a restart. Oldest dropped.
ENTRY_EVENT_LIMIT = 2048
# Lifetime counter blob age. Flush writes are debounced at 45s; this rolls the
# *counts* (not the bounded events ring) so income_dev_loop / panel tallies
# stop acting on weeks-old spread noise. Matches ~1 week of live rate.
ENTRY_BLOCKS_ROLL_SEC = 7 * 86400
# Closed-trade autopsies. Separate ring, own dirty flag: this is ~2000 rows
# of per-trade fields, not the entry-block episode log that hit 9 GB/day when
# it flushed on every poll. A close without a row here is the defect POST-1
# exists to catch.
TRADE_AUTOPSY_LIMIT = 2000


def _bar_key_json(bar_key: Any) -> list | str | int | float | None:
    """JSON-safe form of a bar identity. Tuples become lists."""
    if bar_key is None:
        return None
    if isinstance(bar_key, (list, tuple)):
        out: list[Any] = []
        for x in bar_key:
            if isinstance(x, bool):
                out.append(str(x))
            elif isinstance(x, int):
                out.append(int(x))
            elif isinstance(x, float):
                out.append(int(x) if x == int(x) else float(x))
            else:
                out.append(str(x))
        return out
    if isinstance(bar_key, bool):
        return str(bar_key)
    if isinstance(bar_key, int):
        return int(bar_key)
    if isinstance(bar_key, float):
        return int(bar_key) if bar_key == int(bar_key) else float(bar_key)
    return str(bar_key)

# How long to leave a symbol alone after the broker link refused its order.
#
# A connection-class rejection is verified against the position book before it
# is believed, and that verification sleeps ~2.1s when it finds nothing. The
# result is correctly marked "safe to retry on the next poll" - but on a 2s
# cycle, a sustained outage turns that into a retry every couple of seconds,
# each one paying the 2.1s again. On 2026-08-11 a 40-minute broker outage on
# UK100 and US30 produced 1090 such rejections: 1090 x 2.1s is 38 minutes of
# the 40 spent asleep inside the verifier, while manage_positions - trailing
# stops, breakeven, forced flatten - waited its turn.
#
# 30s is chosen against the bar sizes actually traded: it costs at most a few
# percent of an M15+ bar, and the signal is NOT dropped, only delayed, so a
# link that recovers still gets the entry on the same bar.
LINK_BACKOFF_SEC = 30.0


# can_open()'s refusals collapsed into one "risk_limiti" bucket, which was not
# enough to answer the question they were being read for. Working out that the
# ensemble's second leg is refused for signalling AGAINST an open primary
# position - rather than for hitting a count limit - took an elimination
# argument across three separate settings (max_positions 10, 4 positions open,
# scalp/swing caps off). The counter should just say so.
#
# Matched on the stable prefix of each reason, because most of them carry the
# limit value in the text. Anything unrecognised keeps the old bucket rather
# than growing the key space from a string the caller controls.
_RISK_BLOCK_KEYS: tuple[tuple[str, str], ...] = (
    ("sembol pozisyon limiti", "risk_sembol_limiti"),
    ("ters yonde acik pozisyon", "risk_ters_yon"),
    ("toplam pozisyon limiti", "risk_toplam_limit"),
    ("pozisyon limiti", "risk_kova_limiti"),      # scalp/swing bucket
    ("sembol marj limiti", "risk_sembol_marj"),
    ("marj hesaplanamadi", "risk_marj_okunamadi"),
    ("serbest marj yetersiz", "risk_serbest_marj"),
    ("marj kullanimi limiti", "risk_marj_kullanimi"),
    ("eszamanli risk limiti", "risk_eszamanli"),
    ("stopsuz acik pozisyon", "risk_stopsuz"),
)


def _risk_block_key(reason: str) -> str:
    """Stable counter key for a can_open refusal."""
    text = str(reason or "").lower()
    for needle, key in _RISK_BLOCK_KEYS:
        if needle in text:
            return key
    return "risk_limiti"


def _ratio_percentile(counts: list[int], q: float) -> float | None:
    """Percentile of the bucketed tick/bar spread ratio, or None when empty.

    Reported at the CENTRE of the bucket that crosses ``q``: the value is
    known to 0.1, and naming the lower edge would understate every reading by
    half a bucket. The overflow bucket reports its lower edge instead, since
    it has no upper bound to take a centre of.
    """
    total = sum(counts)
    if total <= 0:
        return None
    target = q * total
    seen = 0
    for idx, n in enumerate(counts):
        seen += n
        if seen >= target:
            if idx >= SPREAD_RATIO_BUCKETS - 1:
                return round(idx * SPREAD_RATIO_STEP, 2)
            return round((idx + 0.5) * SPREAD_RATIO_STEP, 2)
    return round((len(counts) - 1) * SPREAD_RATIO_STEP, 2)


def _cooldown_for(cfg: SymbolConfig) -> float:
    """Per-symbol pause after a fill, clamped to a few bars of its TF."""
    configured = max(0, int(cfg.cooldown_sec))
    bars = _COOLDOWN_BARS_SWING if (
        not is_scalp_strategy(cfg.strategy)
        and timeframe_seconds(cfg.timeframe) >= 900
    ) else _COOLDOWN_BARS
    return float(min(configured, bars * timeframe_seconds(cfg.timeframe)))


class SymbolState:
    """Per-symbol live view kept between cycles and surfaced to the web UI."""

    __slots__ = ("symbol", "last_bar", "next_bar_at", "last_fetch", "atr", "adx", "t3",
                 "t3_rising", "k", "d", "signal", "bars_ready", "cooldown_until",
                 "note", "session", "spread", "spread_atr", "last_signal_at", "htf", "bars",
                 "primary_signal", "signal_source",
                 "pending_bar_key", "entry_block", "t3_kind")

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.last_bar = 0
        self.next_bar_at = 0.0
        self.last_fetch = 0.0
        self.atr = 0.0
        self.primary_signal = ""
        self.signal_source = ""      # "" | "primary"  (filled-bar / pending-bar key; the second leg is gone)
        # None until a bar is computed, and None thereafter for a family that
        # does not measure it - 0.0/False would read as a real flat reading.
        self.adx = None
        self.t3 = None
        self.t3_rising = None
        self.t3_kind = None
        self.htf = 0
        self.k = None
        self.d = None
        self.signal = ""
        self.bars_ready = 0
        self.cooldown_until = 0.0
        self.note = ""
        self.session: dict[str, Any] = {}
        self.spread = 0.0
        self.spread_atr = 0.0
        self.last_signal_at = 0.0
        self.bars: Bars | None = None  # most recent Bars snapshot, for structure-based trailing
        # and not yet filled - lets _evaluate retry a signal a transient block
        # (spread/slot/AI gate) ate earlier in the same bar. (0, 0) means none.
        self.pending_bar_key: tuple[str | int, int] = (0, 0)
        # Which gate refused THIS cycle's entry attempt, as a stable key rather
        # than the display note. Only meaningful right after _try_entry ran;
        # _cycle reads it once and tallies it. See Engine._entry_blocks.
        self.entry_block = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "last_bar": self.last_bar, "atr": round(self.atr, 6),
            # None where the family does not measure it - see Signals.last().
            # Rounding None would raise, and defaulting it back to 0.0 here
            # would undo the whole point.
            "adx": _round_or_none(self.adx, 1),
            "t3": _round_or_none(self.t3, 6), "t3_rising": self.t3_rising,
            "t3_kind": self.t3_kind,
            "htf": self.htf,
            "k": _round_or_none(self.k, 1), "d": _round_or_none(self.d, 1),
            "signal": self.signal,
            "signal_source": self.signal_source,
            "primary_signal": self.primary_signal,
            "bars_ready": self.bars_ready, "note": self.note,
            "entry_block": self.entry_block, "session": self.session,
            "spread": round(self.spread, 6), "spread_atr": round(self.spread_atr, 3),
            "last_signal_at": self.last_signal_at,
        }


def after_stop_excursions(
    side: str,
    entry: float,
    sl: float,
    exit_px: float,
    times: Any,
    high: Any,
    low: Any,
    *,
    exit_time: float,
    horizon_sec: float = 3600.0,
    bar_sec: float = 0.0,
) -> dict[str, Any] | None:
    """What price did in the hour after a stop, in the trade's own R.

    ``extra_r`` is continuation past the stop (the stop saved this).
    ``recovery_r`` is the bounce back from the stop.     ``through_entry`` is a shakeout after a *losing* exit: price came back
    through the original entry. A winner already closed on the profit side
    of entry, so ``mx >= entry`` is tautological and is not a shakeout.
    Missing prices or an empty window return None so callers skip.

    Bar stamps are opens. ``bar_sec`` is the bar length so a candle that
    was still open at the stop (and the one that closes the hour) count
    as overlapping the hour, matching ``_fill_after_stop``'s ready gate.
    ``bar_sec=0`` keeps the open-stamp window used by the unit tests.
    """
    r = abs(float(entry) - float(sl))
    if r <= 0:
        return None
    try:
        t_arr = [float(x) for x in times]
        h_arr = [float(x) for x in high]
        l_arr = [float(x) for x in low]
    except (TypeError, ValueError):
        return None
    if not t_arr or len(t_arr) != len(h_arr) or len(t_arr) != len(l_arr):
        return None
    hi_cut = float(exit_time) + float(horizon_sec)
    span = max(0.0, float(bar_sec))
    window_h: list[float] = []
    window_l: list[float] = []
    for t, h, lo in zip(t_arr, h_arr, l_arr, strict=True):
        if t + span <= float(exit_time):
            continue
        if t > hi_cut:
            continue
        window_h.append(h)
        window_l.append(lo)
    if not window_h:
        return None
    mx = max(window_h)
    mn = min(window_l)
    entry_px = float(entry)
    out_px = float(exit_px)
    if str(side).lower() == "buy":
        extra_r = max(0.0, (out_px - mn) / r)
        recovery_r = max(0.0, (mx - out_px) / r)
        # Shakeout: price came back through entry after a losing exit.
        # A winner already closed above entry, so mx >= entry is tautological
        # (gold trail 24.08 14:46, dip still 13.75 above entry). Claude 16:16.
        through_entry = out_px <= entry_px and mx >= entry_px
    else:
        extra_r = max(0.0, (mx - out_px) / r)
        recovery_r = max(0.0, (out_px - mn) / r)
        through_entry = out_px >= entry_px and mn <= entry_px
    return {
        "after_1h_extra_r": round(extra_r, 4),
        "after_1h_recovery_r": round(recovery_r, 4),
        "after_1h_through_entry": bool(through_entry),
        "after_1h_bars": len(window_h),
    }


class Engine:
    """Polling engine over every configured symbol.

    The worker thread runs for the whole life of the app so the terminal always
    shows live indicator and session state. Placing orders and moving stops is
    gated separately by ``_trading``, which is what the start/stop buttons flip.
    """

    def __init__(self, store: Store, client: MT5Client) -> None:
        self.store = store
        self.client = client
        self.risk = RiskManager(store, client)
        self.supervisor = Supervisor(store, client)
        # Lot budget is the remaining book margin split across vacant enabled
        # names. A quarantined name cannot open, so leaving it in that split
        # sized every real entry down by the number of suspended symbols.
        self.risk.supervisor_blocked = self.supervisor.is_suspended
        self.risk.supervisor_edge_health = (
            lambda sym: float(getattr(self.supervisor.verdicts.get(sym),
                                      "edge_health", 0.0) or 0.0))
        # In-process income loop (replaces scripts/start_income_loop.ps1).
        self.autopilot = AutoPilot(self)
        # Requested-vs-filled bookkeeping. Purely diagnostic: it never gates a
        # trade, it makes the one cost the backtest cannot model visible.
        self.execution = ExecutionMonitor(store)
        self.states: dict[str, SymbolState] = {}
        self._thread: threading.Thread | None = None
        self._trading = False
        self._stop = threading.Event()
        self._lock = threading.RLock()
        # Serialises "open a new position under magic X" against "delete/
        # re-magic the config that owns X" (web thread). Without it, a DELETE
        # or magic-PATCH can pass its own open-position check an instant
        # before this cycle's fill lands, orphaning the fresh position from
        # trail/BE the moment it exists.
        self.entry_lock = threading.Lock()
        self._supervisor_gate = threading.Lock()
        self._autopilot_gate = threading.Lock()
        self._verify_inflight: set[str] = set()
        self._fill_verify_done: list[dict[str, Any]] = []
        self._fill_verify_lock = threading.Lock()
        self._account: dict[str, Any] = {}
        self._account_at = 0.0
        self._positions: list[dict[str, Any]] = []
        self._terminal_flags_cache: dict[str, Any] = {}
        self.cycle_count = 0
        self.last_cycle_at = 0.0
        self.last_cycle_ms = 0.0
        self.last_error = ""
        self._clock_stale_warned_at = 0.0
        # Last logged broker-vs-local hour gap. None until first read; a
        # change to a non-zero value is the October DST leak becoming visible.
        #
        # Restored from the database rather than starting empty. The gap is
        # only measurable while ticks flow, so a restart over a shut market
        # used to lose it entirely - and the one moment it matters is the
        # moment it changes, which is a DST switch at 03:00 on a Sunday,
        # inside exactly the gap where nothing can be measured. Keeping the
        # last known value across the outage is what lets the first tick
        # afterwards answer "did the broker move" instead of "here is a
        # number with nothing to compare it to".
        #
        # This is a cross-check, not an input. Nothing extrapolates the broker
        # clock from this machine's: over a weekend that extrapolation would
        # be wrong precisely when a DST switch made it matter, which is why
        # decision_now refuses rather than guesses.
        self._session_clock_skew: int | None = None
        try:
            stored = store.get_setting("session_clock_skew")
            if stored is not None and not isinstance(stored, bool):
                self._session_clock_skew = int(stored)
        except (TypeError, ValueError):
            # A hand-edited or older row is not worth refusing to start over;
            # the next measurable tick writes a clean value.
            self._session_clock_skew = None
        self._day_cache: dict[str, Any] = {}
        self._day_cache_at = 0.0
        self._cash_flow_at = 0.0
        self._capacity_cache: dict[str, Any] = {}
        self._capacity_cache_at = 0.0
        self._capacity_pos_sig: tuple = ()
        self._capacity_sys_sig: tuple = ()
        # Warm-start capacity rows: a fresh boot has ATR=0 until min_bars land,
        # which zeroed lot/risk in the panel for ~15s even though the prior
        # cycle already had a good number. Display only — lot_for still waits.
        self._last_good_atr: dict[str, float] = {}
        # ticket -> {"rungs": how many scale-out steps already banked,
        #            "orig": the volume the position opened with}. Fractions are
        #            of the *original* size, matching the backtest ladder.
        # Persisted (like secondary_tickets below): without it, a restart after
        # the first rung fired would forget "rungs" was ever 1 *and* re-derive
        # "orig" from the position's now-reduced live volume, so the next rung's
        # fraction would be computed against the wrong base entirely.
        # ``_stop_bar`` - a ticket -> last-managed-bar throttle - lived here
        # until 31.08. It stopped being read when manage_positions moved to
        # "always re-run overlay_stop on this closed bar" (the level does not
        # move until last_bar does, so a repeat is a no-op at min_step), and
        # what remained was a dict that was written, pruned and never asked.
        # Bar-close discipline is still enforced, by _update_stop's own
        # reference-bar check.
        # Tickets seen open under a magic no longer in the book. The API
        # refuses to delete a symbol or move its magic while a position is
        # open (web/app.py's 409s), so this set is meant to stay empty - but
        # every one of those guards lives in the API, and a hand-written row
        # in micofx.db goes around all of them. The engine's own answer to an
        # unmapped magic is a bare ``continue``: no trail, no stop management,
        # no flatten, and - until now - no line anywhere saying so. Every
        # other skip in that loop is sticky and retried; this one was silent
        # and permanent. Latched per ticket because the poll runs every few
        # seconds and the warning is worth exactly once.
        self._unmanaged_seen: set[int] = set()
        # One INFO after boot: which live tickets this process claimed by
        # magic. manage_positions already maps that way; the line is so a
        # restart is visible in the log instead of only in the book.
        self._open_resume_logged = False
        # Tickets already WARN/ERROR-logged as stopless. Repair is retried every
        # cycle until a stop lands; this set only dedupes the operator shout.
        self._stopless_seen: set[int] = set()
        # symbol -> (bar key, how many of ours were open) at the moment a send
        # came back "verified unfilled". That verdict is a two-second look at
        # the position book, not proof the order never reached the market, and
        # the signal is deliberately left alive so a genuinely failed entry can
        # retry. What protected the retry from a fill that landed late was the
        # position limit: at max_positions=1 the count gate refused it. Above
        # 1 that refusal disappears and the retry sends a second order for the
        # same signal on the same bar - one signal, two entries, which is the
        # duplicate open_market's verifier exists to prevent. So the retry
        # carries its own check now: if our count has grown since the failed
        # send, the entry landed and there is nothing left to retry.
        self._unfilled_probe: dict[str, tuple[tuple[int, int], int]] = {}
        # Diagnostic flushes that have failed and not yet succeeded again.
        # The three _flush_* methods swallow their exceptions on purpose: a
        # transient sqlite lock should retry silently, and the dirty bit is
        # left True so it does retry. What the swallow also hid was permanent
        # failure. The damage is not lost trades but two readers drifting
        # apart - the panel serves these tables out of memory and stays
        # fresh, while the forward reports, the autopsy table and the
        # optimiser's spread scale read them back out of sqlite and would go
        # on quoting a frozen number as a live one. One line the first time,
        # cleared on the next success, so a signal firing every two seconds
        # does not become a log of its own.
        self._flush_warned: set[str] = set()
        # Tickets whose weekend force-close failed at least once - kept sticky
        # across the Sat/Sun -> Monday boundary so a broker that rejected the
        # close all weekend doesn't just quietly resume normal trailing the
        # instant weekend_closed() flips False, without ever actually landing
        # that close. Not persisted, same tradeoff the removed stop-bar
        # throttle carried: worst case
        # after a restart during the very rare failed-all-weekend window is
        # one fewer retry, not a correctness issue - the next weekend still
        # catches it fresh. Persisted (unlike the comment above originally
        # argued): a restart that lands in the narrow window between a
        # failed Sat/Sun close and the calendar flipping to Monday would
        # otherwise drop this in-memory set and let the position resume
        # normal trailing without ever landing the flatten it still owes.
        self._weekend_pending: set[int] = {
            int(t) for t in (as_list(store.get_setting("weekend_pending_tickets"), "weekend_pending_tickets")) if str(t).isdigit()
        }
        # Session / day-end flatten sticky: should_flatten / day_end_close are
        # time windows - a DONE_PARTIAL True during the window used to look
        # "handled", then once the window flipped off the remainder fell into
        # normal trail. Same sticky contract as weekend_pending.
        self._force_flat_pending: set[int] = {
            int(t) for t in (as_list(store.get_setting("force_flat_pending_tickets"), "force_flat_pending_tickets"))
            if str(t).isdigit()
        }
        self._netting_warned = False
        self._account_lock_reason = ""
        # Retired ladder key. The one-shot overlay lives in scale_out_done.
        if store.get_setting("partial_state"):
            store.set_setting("partial_state", {})
        self._scale_out_done: set[int] = {
            int(t) for t in (as_list(store.get_setting("scale_out_done"), "scale_out_done"))
            if str(t).isdigit()
        }
        # Leftover tagged tickets from the retired secondary leg (persisted
        # because positions outlive the process). Nothing mints new tags.
        # The set is still loaded so a non-empty row is visible; it does not
        # gate entries (that wait is ``_orphan_scan``, which serves primary
        # fills whose ticket never resolved).
        self._sec_tickets: set[int] = {
            int(t) for t in (as_list(store.get_setting("secondary_tickets"), "secondary_tickets")) if str(t).isdigit()
        }
        if self._sec_tickets:
            LOG.emit(
                f"Kalinti secondary_tickets satiri dolu: {sorted(self._sec_tickets)} "
                f"- ikincil bacak uretmiyor, bu anahtar yok sayilacak.",
                "WARN")
        # Unresolved fills whose broker ticket could not be identified/closed
        # at entry. The settings keys keep the historical ``secondary_orphan_*``
        # names so old rows stay readable; the machine itself is for any fill
        # (primary included) that came back ok without a ticket.
        # ``_orphan_tickets`` is a known ticket still needing a retried close;
        # ``_orphan_scan`` is a symbol whose fill produced zero same-magic
        # candidates yet, so every cycle re-diffs against the snapshot taken
        # at failure time until one appears (broker replication lag) or the
        # scan goes stale. Persisted like weekend_pending_tickets - a restart
        # mid-retry must not forget either.
        self._orphan_tickets: set[int] = {
            int(t) for t in (as_list(store.get_setting("secondary_orphan_tickets"), "secondary_orphan_tickets")) if str(t).isdigit()
        }
        self._orphan_scan: dict[str, dict[str, Any]] = {
            str(k): v for k, v in (as_dict(store.get_setting("secondary_orphan_scan"), "secondary_orphan_scan")).items()
            if isinstance(v, dict)
        }
        # Sticky per-symbol daily-loss halt (see _symbol_daily_halt) - once a
        # symbol trips its own cap, stays tripped (blocking both new entries
        # and, via manage_positions(), keeps retrying the flatten) until the
        # next day rollover, same persistence guarantee DailyGuard.loss_halted
        # already has at the account level. Cleared in _cycle() alongside it.
        self._symbol_halted: dict[str, str] = {
            str(k): str(v) for k, v in (as_dict(store.get_setting("symbol_daily_halted"), "symbol_daily_halted")).items()
        }
        # Why entries do not happen, counted per symbol per gate.
        #
        # Every symbol in this book trades far under the frequency its own
        # holdout implies - 7% to 38% of it - and until now nothing recorded
        # which gate ate the difference. _try_entry sets state.note and
        # returns; the note is overwritten on the next cycle, nothing is
        # logged and nothing is counted, so the one question that matters for
        # the shortfall was simply unanswerable from a running system.
        #
        # Counted only where a signal actually reached the entry stage, which
        # is exactly what _try_entry being called means (_cycle skips a symbol
        # with no signal). So the totals separate the two candidate causes
        # that look identical from outside: a gate refusing entries, versus
        # signals never firing at all. "acildi" is counted alongside the
        # refusals to give the denominator.
        # Shape is {symbol: {leg: {"attempts": {reason: n}, "signals": {...}}}}.
        # Anything that does not match - including the flat {symbol: {reason:
        # n}} this shipped with for one afternoon - is dropped rather than
        # coerced: a half-read counter is worse than an empty one, because it
        # looks like evidence.
        self._entry_blocks: dict[str, dict[str, dict[str, dict[str, int]]]] = {}
        for sym, legs in as_dict(store.get_setting("entry_blocks"), "entry_blocks").items():
            if not isinstance(legs, dict):
                continue
            kept: dict[str, dict[str, dict[str, int]]] = {}
            for leg, counts in legs.items():
                if not isinstance(counts, dict):
                    continue
                buckets: dict[str, dict[str, int]] = {}
                for field in ("attempts", "signals"):
                    raw = counts.get(field)
                    if not isinstance(raw, dict):
                        break
                    try:
                        buckets[field] = {str(k): int(v) for k, v in raw.items()}
                    except (TypeError, ValueError):
                        break
                else:
                    kept[str(leg)] = buckets
            if kept:
                self._entry_blocks[str(sym)] = kept
        self._entry_blocks_since = as_number(
            store.get_setting("entry_blocks_since"), 0.0, "entry_blocks_since") or time.time()
        # Aged lifetime tallies (F-D3) must not survive into this process.
        self._entry_blocks_dirty = bool(self._roll_entry_blocks_if_stale())
        # In-memory only: the (bar, reason) episode each leg was last counted
        # for, so the per-poll retry loop cannot inflate the signal count. A
        # restart starting a fresh episode is the honest reading - the new
        # process re-derives the signal from bars it fetched itself. Bar
        # identity for later measurement lives in ``_entry_events`` (persisted
        # separately); this map is only the de-dupe latch.
        self._entry_last_bar: dict[str, dict[str, tuple]] = {}
        self._entry_event_limit = ENTRY_EVENT_LIMIT
        self._entry_events: list[dict[str, Any]] = []
        self._entry_events_dirty = False
        self._load_entry_events()
        self._trade_autopsy_limit = TRADE_AUTOPSY_LIMIT
        self._trade_autopsies: list[dict[str, Any]] = []
        self._trade_autopsies_dirty = False
        self._trade_autopsies_since = time.time()
        self._load_trade_autopsies()
        self._rebuild_autopsy_pending()
        self._entry_blocks_flushed_at = 0.0
        # How much wider the live tick's spread runs than the bar spread the
        # walk-forward charges, per symbol, as a coarse histogram of the ratio.
        #
        # The two gate on different numbers and always have. simulate() checks
        # ``spread_price[j0] > atr * max_spread_atr`` using the ENTRY BAR's
        # recorded spread; _try_entry checks the CURRENT TICK's. A ceiling
        # chosen against the first is applied against the second, so the search
        # can pick a bound the live gate then breaches on ordinary ticks - which
        # is what FRA40 and USDCHF were doing, and why one was nearly deleted
        # for it.
        #
        # Sampling continuously rather than estimating it: a spot reading is
        # worthless here. Measured over 2.5 minutes of one liquid hour the
        # median came out 1.28x, but the same method reported ratios below 1.0
        # on symbols whose bar median spans hours the sample never touched. The
        # bot is already awake every second of every session, so it can collect
        # the whole distribution for free.
        #
        # Buckets of 0.1 up to 5.0 plus an overflow. Coarse on purpose: this
        # feeds a ceiling that moves in steps, a median is all it needs, and a
        # histogram stays bounded where a growing sample list would not.
        self._spread_ratio: dict[str, list[int]] = {
            str(sym): [int(v) for v in counts][:SPREAD_RATIO_BUCKETS]
            for sym, counts in as_dict(store.get_setting("spread_ratio"), "spread_ratio").items()
            if isinstance(counts, (list, tuple))
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in counts)
        }
        self._spread_ratio_dirty = False
        self._spread_ratio_at = 0.0
        # symbol -> epoch until which entries are not re-attempted after the
        # broker link refused one. In memory only: a restart has already
        # lost the connection state this describes.
        self._link_backoff: dict[str, float] = {}
        # Post-fill cooldown, per symbol, as an absolute epoch. Lived only in
        # SymbolState until now - which is rebuilt empty on every start, so a
        # restart inside the cooldown window dropped the one guard that stops
        # the bar's signal being taken twice. See _restore_cooldown().
        self._cooldowns: dict[str, float] = {
            str(k): float(v) for k, v in (as_dict(store.get_setting("entry_cooldowns"), "entry_cooldowns")).items()
            if isinstance(v, (int, float))
        }
        # symbol -> [signal_source, bar timestamp] of the last signal actually
        # filled. The cooldown above spaces entries out; this is what stops the
        # SAME bar's signal being taken twice, which a restart otherwise does
        # for free - SymbolState is rebuilt empty and the signal recomputes
        # identically off the same still-last-closed bar. Cooldown cannot cover
        # it: 2 minutes against a 5-60 minute bar.
        # {symbol: {signal_source: bar timestamp}}. Per LEG, not per symbol.
        # A single slot per symbol assumed "a symbol only ever fills off
        # whichever leg is currently driving", which is not true once the
        # ensemble is on: the primary fills and records its bar, then the
        # secondary fills and OVERWRITES it, and the primary's already-taken
        # bar is unguarded again. A restart inside that bar then re-enters it -
        # precisely the double entry this record exists to stop.
        self._filled_bars: dict[str, dict[str, int]] = {}
        for sym, value in (as_dict(store.get_setting("filled_bars"), "filled_bars")).items():
            by_leg: dict[str, int] = {}
            # The bar timestamp has to be a number, not merely present: a bare
            # length check let ["sig", "yok"] through to int(), which raises
            # inside __init__ and takes the whole start-up with it.
            def _ok(bar: Any) -> bool:
                return isinstance(bar, (int, float)) and not isinstance(bar, bool)
            if isinstance(value, dict):
                by_leg = {str(k): int(v) for k, v in value.items() if _ok(v)}
            elif (isinstance(value, (list, tuple)) and len(value) == 2
                  and _ok(value[1])):
                # The single-slot shape this replaced. Migrated rather than
                # dropped so the guard keeps covering the leg it did record
                # across the restart that installs this change.
                by_leg = {str(value[0]): int(value[1])}
            if by_leg:
                self._filled_bars[str(sym)] = by_leg

    # ------------------------------------------------------------- lifecycle

    @property
    def watching(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def running(self) -> bool:
        return self._trading and self.watching

    def start_watch(self) -> None:
        """Bring up the observation loop; does not enable order placement."""
        with self._lock:
            if self.watching:
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="micofx-engine", daemon=True)
            self._thread.start()

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self.running:
                return {"ok": True, "running": True, "message": "Bot zaten calisiyor."}
            if not self.client.ensure():
                return {"ok": False, "running": False,
                        "message": self.client.last_error or "MT5 baglantisi yok"}
            self.start_watch()
            self._trading = True
            self.store.update_system({"running": True}, source="bot baslatma")
        LOG.emit("Bot baslatildi - islem acmaya hazir.", "INFO")
        return {"ok": True, "running": True, "message": "Bot baslatildi."}

    def stop(self, close_positions: bool | None = None) -> dict[str, Any]:
        with self._lock:
            was_trading = self._trading
            self._trading = False
            self.store.update_system({"running": False}, source="bot durdurma")
            closed = 0
            remaining = 0
            if close_positions if close_positions is not None else self.store.system.close_on_stop:
                closed, remaining = self.close_all()
        if was_trading:
            if remaining < 0:
                extra = " MT5 baglantisi dogrulanamadi - pozisyon durumu bilinmiyor!"
            elif remaining:
                extra = f" {remaining} pozisyon kapatilamadi!"
            else:
                extra = ""
            LOG.emit(f"Bot durduruldu - izleme devam ediyor."
                     f"{f' {closed} pozisyon kapatildi.' if closed else ''}{extra}",
                     "ERROR" if remaining else "INFO")
        return {"ok": remaining == 0, "running": False, "closed": closed, "remaining": remaining,
                "message": "Bot durduruldu."}

    def shutdown(self) -> None:
        """Tear the worker thread down for good (application exit)."""
        self.stop(close_positions=False)
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=8.0)
        self.execution.flush()
        self._flush_entry_blocks(force=True)
        self._thread = None

    def panic(self) -> dict[str, Any]:
        """Stop trading and flatten everything the bot owns.

        ``ok`` reflects whether the account actually ended up flat, not just
        whether close_all() ran without crashing - a caller relying on this
        as a kill-switch needs to know the difference between "handled" and
        "N pozisyon hala acik, elle mudahale gerekiyor".
        """
        self.stop(close_positions=False)
        closed, remaining = self.close_all()
        if remaining < 0:
            LOG.emit("ACIL DURDURMA: MT5 baglantisi dogrulanamadi - pozisyonlarin gercekten "
                     "kapandigindan EMIN DEGILIZ, elle kontrol edin.", "ERROR")
        elif remaining:
            LOG.emit(f"ACIL DURDURMA: {closed} pozisyon kapatildi, {remaining} pozisyon HALA ACIK "
                     f"- elle mudahale gerekebilir.", "ERROR")
        else:
            LOG.emit(f"ACIL DURDURMA: {closed} pozisyon kapatildi.", "WARN")
        return {"ok": remaining == 0, "closed": closed, "remaining": remaining}

    def close_all(self, symbol: str | None = None, *,
                  reason: str = "") -> tuple[int, int]:
        """Returns ``(closed, remaining)`` - see ``MT5Client.close_all``.

        ``reason`` is the caller name for the log. Panic / session / daily-loss
        already emit their own line; the panel doors did not, so a flatten
        showed up as six ``Pozisyon kapatildi kar~`` rows and nothing else
        (26.08 12:22). Empty keeps the broker call silent for those paths.
        """
        magics = {c.magic for c in list(self.store.symbols.values())}
        if reason:
            target = symbol or "tum"
            LOG.emit(f"{reason}: flatten basladi ({target}).", "WARN")
        return self.client.close_all(magics=magics, symbol=symbol)

    def _reload_positions(self) -> bool:
        """Refresh ``self._positions`` from the broker.

        ``positions()`` returns ``[]`` both when flat and when
        ``positions_get`` failed mid-call (which flips ``connected`` False).
        Assigning that empty list mid-cycle used to make ``manage_positions``
        prune secondary/orphan tags as "gone" and let ``can_open`` under-count
        exposure. On failure keep the previous snapshot and return False.
        """
        fresh = self.client.positions()
        if not self.client.connected:
            LOG.emit("pozisyon listesi yenilenemedi - onceki anlik goruntu korundu "
                     "(baglanti koptu).", "WARN")
            return False
        self._positions = fresh
        return True

    # ------------------------------------------------------------------ loop

    def _run(self) -> None:
        while not self._stop.is_set():
            begin = time.perf_counter()
            try:
                self._cycle()
                self.last_error = ""
            except Exception as exc:  # keep the loop alive through transient MT5 faults
                self.last_error = f"{type(exc).__name__}: {exc}"
                LOG.emit(f"Dongu hatasi: {self.last_error}", "ERROR")
            self.last_cycle_ms = (time.perf_counter() - begin) * 1000.0
            self.last_cycle_at = time.time()
            self.cycle_count += 1
            interval = max(0.5, float(self.store.system.poll_interval_sec))
            if not self._trading:
                interval = max(interval, 3.0)  # watch-only needs no tight loop
            self._stop.wait(max(0.2, interval - (time.perf_counter() - begin)))

    def _cycle(self) -> None:
        if not self.client.ensure():
            return

        self.client.set_overrides({c.symbol: c.broker_symbol for c in list(self.store.symbols.values())})

        account = self.refresh_account(force=True)
        if not account:
            return

        self._probe_book_ticks()
        getter = getattr(self.client, "decision_now", None)
        server_now = getter() if callable(getter) else None
        self._note_stale_decision_clock(server_now)
        self._note_session_clock(self.client.server_now())
        login = int(account.get("login") or 0)
        balance = float(account.get("balance", 0.0) or 0.0)
        if server_now is not None:
            self._handle_daily_rollover(server_now, balance, login=login)
        else:
            observer = getattr(self.risk.daily, "observe_account", None)
            if callable(observer):
                observer(login, balance)
        # Must follow the rollover (which resets the figure) and precede the
        # guard.check() below, so the breaker never sees a deposit as profit.
        self._refresh_cash_flow()

        # Through _reload_positions, not a bare assignment: on a failed
        # positions_get that helper keeps the previous snapshot instead of
        # leaving an unreliable empty list behind. The bail below covers this
        # cycle, but _positions is also what _panel_positions serves and what
        # _apply_pending_exits derives open_magics from - and those patches
        # land "when flat". A blip that empties the book looks exactly like
        # flat.
        self._reload_positions()
        if not self.client.connected:
            # positions() itself flips this False when mt5.positions_get()
            # fails mid-cycle (disconnect after the ensure() check above
            # already passed) - self._positions is then an unreliable empty
            # list, not "flat". Bail before manage_positions/entries act on
            # it; the next cycle's ensure() will reconnect first.
            return
        self._reap_execution()
        self.day_stats()
        self._apply_pending_exits()
        self._scan_orphan_candidates()
        if not self.client.connected:
            # Scan path may have called positions() again (post-close refresh /
            # last-look). Same fail-closed stance as cycle-start: do not
            # manage/entry on an emptied or stale-unverified book.
            return
        # Unconditional: this only manages positions already open (trail/BE/
        # partial/session-flatten/day-end-flatten), never opens new ones.
        # Gating it on _trading meant that with close_on_stop=false (the
        # default - a stopped bot does not close what is already open) any
        # position still open while stopped sat completely unmanaged: no
        # trailing, no breakeven, no forced flatten near session/day close.
        # Only the broker-native stop kept protecting it. New entries are
        # still gated separately below via allow_entry.
        self.manage_positions(self._flatten_clock(server_now))

        guard = self.risk.daily.check(
            account.get("equity", 0.0), self.store.system,
            login=login, balance=balance,
        )
        # The loss guard alone only ever blocked NEW entries - an already-open
        # position kept riding its own (possibly distant) stop while the
        # account kept bleeding floating loss past the configured limit. When
        # the halt is specifically the loss side (not the profit-target side,
        # where letting winners run is a legitimate choice), flatten what is
        # still open so "daily loss limit" actually stops the daily loss.
        # Runs every cycle while halted, not just once - self-healing if a
        # partial close_all() attempt left something behind.
        # Sticky (DailyGuard.loss_halted), not re-derived from live equity -
        # re-checking pnl_pct here every cycle meant a bounce back above the
        # threshold (another position's floating P/L recovering, a stray
        # tick) silently turned the flatten off for that cycle even though
        # the day is still halted and still supposed to be flattening. The
        # halt itself only ever clears on rollover/resume, so this should too.
        loss_halted = self.risk.daily.halted and self.risk.daily.loss_halted
        if loss_halted and self._positions:
            closed, remaining = self.close_all()
            if closed:
                LOG.emit(f"Gunluk zarar limiti: {closed} pozisyon flatten edildi.", "WARN")
            if remaining < 0:
                # Same honesty as panic(): remaining=-1 means disconnect/resolve
                # failure, not "minus one ticket still open".
                LOG.emit("Gunluk zarar limiti: flatten dogrulanamadi "
                         "(MT5 baglantisi/resolve) - pozisyonlarin gercekten "
                         "kapandigindan EMIN DEGILIZ, elle kontrol edin.", "ERROR")
            elif remaining:
                LOG.emit(f"Gunluk zarar limiti: flatten sonrasi {remaining} pozisyon hala acik.", "ERROR")
        if self.supervisor.due():
            try:
                pnl = self.risk.daily.pnl_pct(account.get("equity", 0.0))
            except Exception:
                pnl = 0.0
            self._kick_supervisor_review(pnl)
        if getattr(self, "autopilot", None) is not None and self.autopilot.due():
            self._kick_autopilot()

        # Every position-count guard here (max_positions, weekend/secondary)
        # ticket tracking, partial-TP ladder bookkeeping) assumes one ticket
        # per opened trade - a netting account merges same-direction trades
        # on a symbol into a single ticket instead, silently defeating all of
        # them ("Maks pozisyon 5" becomes "one ticket, unlimited volume").
        # Refuse new entries entirely rather than trade under assumptions
        # that do not hold for this account type.
        netting = bool(account.get("netting"))
        if netting and not self._netting_warned:
            self._netting_warned = True
            LOG.emit("Hesap NETTING modunda - bu sistemin pozisyon-sayisi tabanli "
                     "risk kontrolleri (Maks pozisyon, hafta sonu/ikincil ticket "
                     "takibi) tek ticket = tek pozisyon varsayimina dayaniyor, "
                     "netting'de gecersiz kaliyor. Yeni islem acilmasi guvenlik "
                     "icin durduruldu - hedging hesabina gecin.", "ERROR")
        lock_reason = getattr(self, "_account_lock_reason", "")
        if lock_reason:
            for st in self.states.values():
                if st.note in ("", "bekliyor", "sinyal yok"):
                    st.note = lock_reason
        allow_entry = (self._trading and guard.ok and not netting
                       and self.client.connected and not lock_reason)
        # Two-pass cycle: first refresh every symbol, then fill free slots in
        # priority order so a weak signal does not steal the last seat from a
        # stronger one when several bars close in the same poll.
        ready: list[SymbolConfig] = []
        for cfg in list(self.store.symbols.values()):
            state = self.states.get(cfg.symbol)
            if state is None:
                state = SymbolState(cfg.symbol)
                self._restore_cooldown(state)
                self.states[cfg.symbol] = state
            if not cfg.enabled:
                self._evaluate_disabled(cfg, state, server_now, account)
                continue
            try:
                wants = self._evaluate(cfg, state, server_now, account, allow_entry=allow_entry)
                if wants:
                    ready.append(cfg)
                # Daily halt (and only that) used to return from _evaluate
                # before _try_entry, so the ready-loop tally never saw it.
                # Observation only - this does not change whether entries run.
                if state.signal and self._trading and not guard.ok:
                    self._tally_entry(cfg.symbol, "gunluk_halt",
                                      bar_key=state.pending_bar_key,
                                      source=state.signal_source)
                if not self._trading and state.note in ("", "bekliyor", "sinyal yok"):
                    state.note = "bot durdu - izleme"
                elif self._trading and not guard.ok:
                    state.note = guard.reason
            except Exception as exc:
                state.note = f"hata: {exc}"
                LOG.emit(f"Degerlendirme hatasi: {exc}", "ERROR", cfg.symbol)

        self._drain_fill_verify()
        if allow_entry and ready:
            ready.sort(key=lambda c: self.supervisor.priority(c), reverse=True)
            for cfg in ready:
                state = self.states[cfg.symbol]
                if not state.signal:
                    continue
                try:
                    # Read the leg BEFORE the entry, not after. _try_entry
                    # decides which leg it is acting on from exactly this value
                    # on the way in, and its successful-fill path then clears
                    # the signal it consumed - so reading it afterwards gave
                    # "" for every fill and filed all of them under primary.
                    # Twenty-five secondary fills were lost that way over one
                    # counter window while primary read 65 against 66 in the
                    # log. Refusals return long before the clearing, which is
                    # why only the fills were mis-attributed.
                    entry_leg = state.signal_source
                    # An entry triggered by the secondary signal is executed with
                    # the parameters it was validated under, not the primary's.
                    self._try_entry(cfg, state, account)
                    self._tally_entry(cfg.symbol, state.entry_block,
                                      bar_key=state.pending_bar_key,
                                      source=entry_leg)
                    # account was a single snapshot taken at the top of this
                    # cycle - if that entry just filled, every later symbol in
                    # this same ready list would otherwise size/margin-check
                    # itself against margin the fill above already spent.
                    account = self.refresh_account(force=True) or account
                except Exception as exc:
                    state.note = f"hata: {exc}"
                    self._tally_entry(cfg.symbol, "hata")
                    LOG.emit(f"Giris hatasi: {exc}", "ERROR", cfg.symbol)
        # Always, not only when something was ready. Daily/symbol halt tallies
        # happen on cycles where allow_entry is False and ready stays empty.
        self._flush_entry_blocks()
        self._flush_trade_autopsies()
        self._flush_spread_ratio()

    def _kick_supervisor_review(self, pnl: float) -> None:
        """14d deals_since must not sit in front of evaluate/entry.

        review() still runs; it just does not hold this cycle. Quarantine
        can lag one interval (already 120s).
        """
        gate = getattr(self, "_supervisor_gate", None)
        if gate is None:
            self._supervisor_gate = threading.Lock()
            gate = self._supervisor_gate
        if not gate.acquire(blocking=False):
            return

        def _run() -> None:
            try:
                self.supervisor.review(pnl)
            except Exception as exc:
                LOG.emit(f"AI denetleyici hatasi: {exc}", "ERROR")
            finally:
                gate.release()

        threading.Thread(target=_run, name="micofx-supervisor", daemon=True).start()

    def _kick_autopilot(self) -> None:
        """Income tick must not sit in front of evaluate/entry."""
        gate = getattr(self, "_autopilot_gate", None)
        if gate is None:
            self._autopilot_gate = threading.Lock()
            gate = self._autopilot_gate
        if not gate.acquire(blocking=False):
            return
        ap = getattr(self, "autopilot", None)
        if ap is None:
            gate.release()
            return

        def _run() -> None:
            try:
                ap.tick()
            except Exception as exc:
                LOG.emit(f"Autopilot hatasi: {exc}", "ERROR")
            finally:
                gate.release()

        threading.Thread(target=_run, name="micofx-autopilot", daemon=True).start()

    def _run_fill_verify(self, pending: dict[str, Any]) -> None:
        kwargs = dict(pending.get("verify_kwargs") or {})
        try:
            result = self.client._verify_ambiguous_send(**kwargs)
        except Exception as exc:
            result = {"ok": False, "ambiguous": True,
                      "error": f"dogrulama hatasi: {exc}"}
        item = {**pending, "result": result}
        lock = getattr(self, "_fill_verify_lock", None)
        if lock is None:
            self._fill_verify_lock = threading.Lock()
            lock = self._fill_verify_lock
        with lock:
            done = getattr(self, "_fill_verify_done", None)
            if done is None:
                self._fill_verify_done = []
                done = self._fill_verify_done
            done.append(item)

    def _drain_fill_verify(self) -> None:
        lock = getattr(self, "_fill_verify_lock", None)
        if lock is None:
            return
        with lock:
            done = list(getattr(self, "_fill_verify_done", []) or [])
            self._fill_verify_done = []
        inflight = getattr(self, "_verify_inflight", None)
        for item in done:
            symbol = str(item.get("symbol") or "")
            if isinstance(inflight, set):
                inflight.discard(symbol)
            result = item.get("result") or {}
            state = self.states.get(symbol)
            cfg = self.store.symbols.get(symbol) if getattr(self, "store", None) else None
            if state is None:
                continue
            if result.get("ok"):
                if cfg is None:
                    continue
                self._book_deferred_fill(cfg, state, result, item)
                continue
            state.note = result.get("error", "emir hatasi")
            state.entry_block = "emir_hatasi"
            if result.get("verified_unfilled") or result.get("retcode") in AMBIGUOUS_RETCODES:
                self._link_backoff[symbol] = time.time() + LINK_BACKOFF_SEC
            if result.get("verified_unfilled"):
                bar = item.get("bar_key") or (int(state.last_bar or 0), 0)
                count = int(item.get("probe_count") or 0)
                self._unfilled_probe[symbol] = (tuple(bar), count)
                LOG.emit(result.get("error", "emir hatasi"), "WARN", symbol)
            else:
                LOG.emit(result.get("error", "emir hatasi"), "ERROR", symbol)
            if result.get("ambiguous"):
                state.signal = ""
                state.signal_source = ""
                state.primary_signal = ""
                state.pending_bar_key = (0, 0)
                state.note = "emir sonucu belirsiz - tekrar denenmeyecek, MT5'i kontrol edin"
                state.entry_block = "emir_belirsiz"

    def _book_deferred_fill(self, cfg: SymbolConfig, state: SymbolState,
                            result: dict[str, Any], item: dict[str, Any]) -> None:
        """note_fill / cooldown for a fill the verifier found off-thread."""
        side = str(item.get("side") or state.signal or "")
        sl_dist = float(item.get("sl_dist") or 0.0)
        lot = float(item.get("lot") or result.get("volume") or 0.0)
        entry = float(item.get("entry") or result.get("requested") or 0.0)
        note = str(item.get("note") or "")
        if result.get("partial_fill"):
            LOG.emit(f"Kismi dolum: {result['volume']:g} lot (istenen {lot:g} lot) - "
                     f"kalan hacim iptal edildi, tekrar denenmedi.", "WARN", cfg.symbol)
        info = self.client.info(cfg.symbol) or {}
        self.execution.record(
            cfg.symbol, "entry", result.get("requested", entry), result["price"],
            deal_is_buy=(side == "buy"), risk_dist=sl_dist,
            point=float(info.get("point", 0.0) or 0.0), volume=result["volume"],
            money_per_price=self.client.money_per_price_unit(cfg.symbol, result["volume"]),
        )
        state.cooldown_until = time.time() + _cooldown_for(cfg)
        self._save_cooldown(cfg.symbol, state.cooldown_until)
        # Book the bar that was sent, not whatever evaluate armed while the
        # verifier slept. Cycle order is evaluate → drain → entries, so T+1
        # can already be live here. Marking live last_bar / clearing the
        # chain both: misses that new entry, and files filled_bars under ""
        # once live source was already wiped.
        booked_source = str(item.get("signal_source") or state.signal_source or "")
        booked_bar = int(item.get("last_bar") or 0)
        if not booked_bar:
            key = item.get("bar_key") or ()
            booked_bar = int(key[0] or 0) if key else 0
        if not booked_bar:
            booked_bar = int(state.last_bar or 0)
        self._mark_bar_filled(cfg.symbol, booked_source, booked_bar)
        if int(state.last_bar or 0) == booked_bar:
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
        state.note = "islem acildi"
        state.entry_block = "acildi"
        ticket = int(result.get("position", 0) or 0)
        fill_px = _fill_log_price(result, entry)
        note_fill = getattr(self.execution, "note_fill", None)
        if ticket and callable(note_fill):
            sig_close = None
            if state.bars is not None and len(state.bars.close):
                sig_close = float(state.bars.close[-1])
            point = float(info.get("point") or 0)
            fill_vs = None
            if sig_close is not None and side:
                fill_vs = (fill_px - sig_close) if side == "buy" else (sig_close - fill_px)
            atr_pct = None
            if state.atr and sig_close:
                atr_pct = float(state.atr) / sig_close
            note_fill(
                ticket,
                signal_bar_time=int(booked_bar or 0) or None,
                fill_time=self._broker_now_int(),
                fill_price=fill_px,
                signal_close=sig_close,
                fill_vs_signal_close=fill_vs,
                fill_vs_signal_close_pts=(fill_vs / point if point and fill_vs is not None else None),
                fill_vs_signal_close_r=(fill_vs / sl_dist if sl_dist and fill_vs is not None else None),
                # Send-time stamp from pending — evaluate may have overwritten
                # state.spread_atr while the verifier slept.
                spread_atr=float(item["spread_atr"]) if item.get("spread_atr") is not None
                else float(state.spread_atr or 0),
                adx=state.adx,
                atr_pct=atr_pct,
                tf_seconds=timeframe_seconds(cfg.timeframe),
                side=side,
                entry=fill_px,
                risk_dist=float(sl_dist or 0),
                original_sl=_fill_original_sl(side, fill_px, sl_dist,
                                                float(result.get("sl") or 0)),
            )
        cost_bit = ""
        vol = float(result["volume"])
        mpu = self.client.money_per_price_unit(cfg.symbol, vol)
        r_value = float(sl_dist or 0.0) * mpu
        if r_value > 0:
            cost = cfg.commission_per_lot * vol
            tick = item.get("tick") or {}
            cost += float(tick.get("spread") or 0.0) * mpu
            cost_bit = f" maliyet %{cost / r_value * 100.0:.1f}"
        log_sl = live_stop_level(float(result.get("sl") or 0))
        if log_sl <= 0:
            log_sl = _fill_original_sl(side, fill_px, sl_dist,
                                       float(result.get("sl") or 0)) or 0.0
        LOG.emit(
            f"#{ticket} {side.upper()} {vol:g} lot @ {_fill_log_price(result, fill_px):.5f} "
            f"SL={log_sl:.5f} TP={float(result.get('tp') or 0):.5f} magic={cfg.magic}"
            f"{cost_bit} | lot: {note}",
            "TRADE", cfg.symbol)
        try:
            self._reload_positions()
        except Exception:
            pass

    # ----------------------------------------------------- entry diagnostics

    def _sample_spread_ratio(self, cfg: SymbolConfig, state: SymbolState,
                             tick: dict[str, Any] | None) -> None:
        """Record one live-tick vs bar spread reading. Never raises.

        Both numbers have to describe the same instant to be comparable, so
        this uses the bar currently forming (the last row of the fetched
        series) against the tick that was just read for the same symbol in the
        same cycle.
        """
        try:
            if not tick:
                return
            bars = state.bars
            if bars is None or len(bars) < 1:
                return
            info = self.client.info(cfg.symbol) or {}
            point = float(info.get("point", 0.0) or 0.0)
            if point <= 0:
                return
            bar_spread = float(bars.spread[-1]) * point
            tick_spread = float(tick.get("spread", 0.0) or 0.0)
            if not (bar_spread > 0 and tick_spread > 0):
                return
            ratio = tick_spread / bar_spread
            if not math.isfinite(ratio) or ratio <= 0:
                return
            counts = self._spread_ratio.setdefault(
                cfg.symbol, [0] * SPREAD_RATIO_BUCKETS)
            if len(counts) != SPREAD_RATIO_BUCKETS:
                counts = [0] * SPREAD_RATIO_BUCKETS
                self._spread_ratio[cfg.symbol] = counts
            idx = min(SPREAD_RATIO_BUCKETS - 1, int(ratio / SPREAD_RATIO_STEP))
            counts[idx] += 1
            self._spread_ratio_dirty = True
        except Exception:
            pass

    def _flush_failed(self, name: str, exc: BaseException) -> None:
        """First failure of a diagnostic flush gets one line; repeats stay quiet.

        Reached from inside the flush ``except``, so it is the last place
        allowed to raise: anything thrown here leaves the handler and breaks
        the one guarantee these methods make, which is that a diagnostic
        write can never interrupt a trading cycle. Hence getattr rather than
        plain attribute access - the same idiom the flush bodies already use
        for their own rings, and what keeps a partially built engine (tests,
        and any future construction order) from turning a swallowed disk
        error into a live exception.
        """
        try:
            warned = getattr(self, "_flush_warned", None)
            if warned is None:
                warned = set()
                self._flush_warned = warned
            if name in warned:
                return
            warned.add(name)
            LOG.emit(f"teshis kaydi diske yazilamadi ({name}: {type(exc).__name__}) - "
                     f"panel bellekten taze okumaya devam eder, sqlite okuyan "
                     f"raporlar donmus sayi gorur", "WARN")
        except Exception:                       # the warning is never worth a cycle
            pass

    def _flush_ok(self, name: str) -> None:
        """A landed flush re-arms the warning for the next distinct outage."""
        warned = getattr(self, "_flush_warned", None)
        if warned:
            warned.discard(name)

    def _flush_spread_ratio(self, interval: float = 300.0) -> None:
        """Persist the histogram, at most once every few minutes.

        Every symbol contributes a sample on every cycle, so the dirty flag is
        set continuously and a naive flush would rewrite the whole blob to
        SQLite every two seconds forever. Losing the last few minutes of
        counts to a hard kill costs nothing - this is a distribution, not a
        ledger.
        """
        if not self._spread_ratio_dirty:
            return
        now = time.time()
        if now - self._spread_ratio_at < interval:
            return
        try:
            # Drop symbols that have left the portfolio, the same way
            # _mark_bar_filled bounds its own record. Two reasons, and the
            # second is not just tidiness: the panel showed measurements for
            # seven symbols that no longer exist, and _spread_scale looks the
            # histogram up BY NAME - so re-adding one of them later would have
            # applied a stale distribution to a fresh config.
            live = set(self.store.symbols)
            self._spread_ratio = {s: c for s, c in self._spread_ratio.items()
                                  if s in live}
            self.store.set_setting("spread_ratio", self._spread_ratio)
            self._spread_ratio_dirty = False
            self._spread_ratio_at = now
            self._flush_ok("spread_ratio")
        except Exception as exc:
            self._flush_failed("spread_ratio", exc)

    def spread_ratio(self) -> dict[str, Any]:
        """Per-symbol median and 90th percentile of tick spread / bar spread."""
        rows: list[dict[str, Any]] = []
        for symbol, counts in sorted(list(self._spread_ratio.items())):
            counts = list(counts)
            total = sum(counts)
            if total <= 0:
                continue
            rows.append({
                "symbol": symbol, "samples": total,
                "median": _ratio_percentile(counts, 0.50),
                "p90": _ratio_percentile(counts, 0.90),
                "enough": total >= SPREAD_RATIO_MIN_SAMPLES,
            })
        rows.sort(key=lambda r: -(r["median"] or 0))
        ready = [r for r in rows if r["enough"]]
        return {
            "rows": rows,
            "min_samples": SPREAD_RATIO_MIN_SAMPLES,
            "ready": len(ready),
            "note": (
                f"{len(ready)}/{len(rows)} sembolde {SPREAD_RATIO_MIN_SAMPLES} "
                f"orneklik esik asildi"
                if rows else "henuz olcum yok - bot calistikca birikir"
            ),
        }

    def _tally_entry(self, symbol: str, reason: str,
                     bar_key: tuple | None = None, source: str = "") -> None:
        """Record the outcome of one entry attempt. Never raises.

        Two counts, because they answer different questions and the first one
        alone is misleading. A blocked signal is re-offered every poll until
        its bar rolls over, so on a 2s interval one refused M15 signal shows
        up as several hundred "attempts" - EURJPY produced 339 of them from a
        single sell in thirteen minutes. Comparing that to a holdout trade
        count, which counts distinct trades, is meaningless.

        ``attempts`` therefore measures persistence: how long the gate held
        the signal off. ``signals`` counts distinct (bar, source) episodes and
        is the one that compares to the walk-forward.

        ``source`` matters because a symbol with the ensemble on has two legs
        with their own parameters, and it is routinely the SECONDARY that is
        refused - six of thirteen live symbols carry a secondary spread
        ceiling tighter than their primary, up to 3.6x. A tally that did not
        separate them would report the symbol as blocked without saying which
        config owns the ceiling doing it.

        An empty reason means _try_entry returned without passing any marked
        point, which should not happen - bucket it rather than lose it, so a
        future edit that adds an unmarked return shows up as a rising
        "isaretsiz" instead of silently shrinking the total.
        """
        try:
            key = str(reason or "isaretsiz")
            # The second leg no longer produces a source. A stale
            # ``source=="secondary"`` argument must not mint a bucket the
            # panel would read as a live config that does not exist.
            leg = "primary"
            legs = self._entry_blocks.setdefault(str(symbol), {})
            counts = legs.setdefault(leg, {"attempts": {}, "signals": {}})
            attempts, signals = counts["attempts"], counts["signals"]
            attempts[key] = int(attempts.get(key, 0)) + 1
            # One episode per (bar, leg, reason); the retry loop must not
            # inflate it. The de-dupe latch is in-memory (a restart starting a
            # fresh episode is the honest reading). The bar identity itself is
            # appended to ``_entry_events`` and persisted, so a later window
            # can name the bars the counters only counted.
            seen = self._entry_last_bar.setdefault(str(symbol), {})
            episode = (repr(bar_key), key)
            if seen.get(leg) != episode:
                seen[leg] = episode
                signals[key] = int(signals.get(key, 0)) + 1
                self._record_entry_event(str(symbol), key, bar_key)
            self._entry_blocks_dirty = True
        except Exception:
            pass

    def _tally_evaluate_refuse(self, cfg: SymbolConfig, state: SymbolState,
                               reason: str, bar_key: int) -> None:
        """Count an `_evaluate` refuse that already has a live signal.

        The ready-loop tally only sees symbols that return True from here
        and then hit `_try_entry`. Gates that return False after
        `_merge_signals` (session closed, market halted, gap age,
        already-filled bar, symbol halt) used to vanish from the panel
        while still refusing correctly. No-signal returns stay silent.
        """
        if not state.signal:
            return
        self._tally_entry(
            cfg.symbol, reason,
            bar_key=state.pending_bar_key or (state.signal_source, bar_key),
            source=state.signal_source,
        )

    def forget_filled_bars(self, symbol: str) -> None:
        """Drop one symbol's filled-bar record at delete, not at the next prune.

        Fourth and last of these. The record is keyed by symbol name and says
        which bar already produced a fill, so a symbol re-added under the same
        name inherits "already traded that bar" from an instrument that is gone.
        Found 15.08 after the perpetuals were deleted: everything else was clean
        and settings.filled_bars still held BRENTOIL-PERP.
        """
        if self._filled_bars.pop(str(symbol), None) is not None:
            self.store.set_setting("filled_bars", self._filled_bars)

    def forget_spread_ratio(self, symbol: str) -> None:
        """Drop one symbol's spread histogram now, not at the next flush.

        _flush_spread_ratio already prunes symbols that have left the book, and
        its own comment says why that matters - _spread_scale looks the
        histogram up BY NAME, so a re-added symbol would inherit a dead one's
        distribution. But the flush is throttled to once every five minutes, so
        "delete leaves nothing behind" was true eventually rather than
        immediately. Deleting and re-adding inside that window is exactly what
        an operator testing the delete path does.
        """
        if self._spread_ratio.pop(str(symbol), None) is not None:
            self._spread_ratio_dirty = True
            self._spread_ratio_at = 0.0          # bypass the throttle, once
            self._flush_spread_ratio()

    def forget_entry_blocks(self, symbol: str) -> None:
        """Drop one symbol's entry tally now, rather than at the next flush.

        The flush prunes against the live book, so a symbol deleted and re-added
        under the same name before the next flush keeps counters that belong to
        the instrument that left.
        """
        name = str(symbol)
        dropped = self._entry_blocks.pop(name, None) is not None
        last = getattr(self, "_entry_last_bar", None)
        if isinstance(last, dict) and last.pop(name, None) is not None:
            dropped = True
        events = getattr(self, "_entry_events", None)
        if events:
            kept = [e for e in events if e.get("symbol") != name]
            if len(kept) != len(events):
                self._entry_events = kept
                dropped = True
        if dropped:
            self._entry_blocks_dirty = True
            self._entry_events_dirty = True
            self._flush_entry_blocks(force=True)

    def _load_entry_events(self) -> None:
        """Restore the observation ring. Corrupt rows are skipped, not coerced."""
        try:
            limit = int(getattr(self, "_entry_event_limit", ENTRY_EVENT_LIMIT)
                        or ENTRY_EVENT_LIMIT)
            events: list[dict[str, Any]] = []
            for item in as_list(self.store.get_setting("entry_block_events"),
                                "entry_block_events"):
                if not isinstance(item, dict):
                    continue
                try:
                    symbol = str(item["symbol"])
                    reason = str(item["reason"])
                    epoch = float(item["epoch"])
                except (KeyError, TypeError, ValueError):
                    continue
                bar_key = item.get("bar_key")
                if isinstance(bar_key, tuple):
                    bar_key = list(bar_key)
                elif bar_key is not None and not isinstance(bar_key, list):
                    continue
                events.append({
                    "symbol": symbol,
                    "reason": reason,
                    "bar_key": bar_key,
                    "epoch": epoch,
                })
            self._entry_events = events[-limit:]
        except Exception:
            self._entry_events = []

    def _record_entry_event(self, symbol: str, reason: str, bar_key: Any) -> None:
        """Append one new-episode row and drop the oldest if the ring is full."""
        events = getattr(self, "_entry_events", None)
        if events is None:
            self._entry_events = []
            events = self._entry_events
        events.append({
            "symbol": str(symbol),
            "reason": str(reason),
            "bar_key": _bar_key_json(bar_key),
            "epoch": time.time(),
        })
        limit = int(getattr(self, "_entry_event_limit", ENTRY_EVENT_LIMIT)
                    or ENTRY_EVENT_LIMIT)
        if len(events) > limit:
            self._entry_events = events[-limit:]
        self._entry_events_dirty = True

    def _roll_entry_blocks_if_stale(self, now: float | None = None) -> bool:
        """Wipe aged counters; keep the bounded events ring for autopsy windows."""
        now = float(now if now is not None else time.time())
        since = float(getattr(self, "_entry_blocks_since", 0.0) or 0.0)
        window = float(getattr(self, "_entry_blocks_roll_sec", ENTRY_BLOCKS_ROLL_SEC)
                       or ENTRY_BLOCKS_ROLL_SEC)
        if since <= 0 or (now - since) < window:
            return False
        self._entry_blocks = {}
        self._entry_last_bar = {}
        self._entry_blocks_since = now
        self._entry_blocks_dirty = True
        return True

    def _flush_entry_blocks(self, force: bool = False) -> None:
        """Persist counters and, separately, the observation ring.

        Both blobs share one 45s window. A new episode used to skip that
        window (``not events_dirty``), rewriting ~86 KB every poll while
        a gate held a bar off. Crash may lose up to 45s of observation
        rows; ``reset`` / symbol-delete pass ``force=True``.
        """
        try:
            self._roll_entry_blocks_if_stale()
            blocks_dirty = getattr(self, "_entry_blocks_dirty", False)
            events_dirty = getattr(self, "_entry_events_dirty", False)
            if not blocks_dirty and not events_dirty:
                return
            now = time.time()
            last = float(getattr(self, "_entry_blocks_flushed_at", 0.0) or 0.0)
            if (not force and last
                    and now - last < _ENTRY_BLOCK_FLUSH_SEC):
                return
            live = set(self.store.symbols)
            if blocks_dirty:
                self._entry_blocks = {s: c for s, c in self._entry_blocks.items()
                                      if s in live}
                self.store.set_setting("entry_blocks", self._entry_blocks)
                self.store.set_setting("entry_blocks_since", self._entry_blocks_since)
                self._entry_blocks_dirty = False
            if events_dirty:
                events = [e for e in list(getattr(self, "_entry_events", []) or [])
                          if e.get("symbol") in live]
                limit = int(getattr(self, "_entry_event_limit", ENTRY_EVENT_LIMIT)
                            or ENTRY_EVENT_LIMIT)
                self._entry_events = events[-limit:]
                self.store.set_setting("entry_block_events", self._entry_events)
                self._entry_events_dirty = False
            self._entry_blocks_flushed_at = now
            self._flush_ok("entry_blocks")
        except Exception as exc:
            self._flush_failed("entry_blocks", exc)

    def entry_blocks(self) -> dict[str, Any]:
        """The tally, per symbol and per leg.

        ``signals`` is the number that compares to a holdout trade count;
        ``attempts`` only says how many polls the gate held each one off.
        """
        # Snapshot every level with list()/dict() before iterating it. This
        # runs on the web thread while the engine thread is inside
        # _tally_entry, and nothing serialises the two - a new reason key
        # appearing mid-iteration (which happens whenever the gate refusing a
        # symbol changes, so: normally) raised "dictionary changed size during
        # iteration" and 500'd the view. Same defence list(self.states.items())
        # already uses at the two other cross-thread reads.
        rows: list[dict[str, Any]] = []
        for symbol, legs in sorted(list(self._entry_blocks.items())):
            if not isinstance(legs, dict):
                continue
            for leg, counts in sorted(list(legs.items())):
                if not isinstance(counts, dict):
                    continue
                attempts = {str(k): int(v) for k, v in
                            list((counts.get("attempts") or {}).items())}
                signals = {str(k): int(v) for k, v in
                           list((counts.get("signals") or {}).items())}
                total = sum(signals.values())
                opened = int(signals.get("acildi", 0))
                rows.append({
                    "symbol": symbol, "leg": leg,
                    "signals": total, "opened": opened,
                    "attempts": sum(attempts.values()),
                    "fill_rate": round(opened / total, 3) if total else None,
                    "blocks": dict(sorted(
                        ((k, v) for k, v in signals.items() if k != "acildi"),
                        key=lambda kv: -kv[1])),
                    "retries": dict(sorted(
                        ((k, v) for k, v in attempts.items() if k != "acildi"),
                        key=lambda kv: -kv[1])),
                })
        rows.sort(key=lambda r: (-r["signals"], -r["attempts"]))
        totals: dict[str, int] = {}
        for row in rows:
            for k, v in row["blocks"].items():
                totals[k] = totals.get(k, 0) + v
        return {
            "since": self._entry_blocks_since,
            "rows": rows,
            "totals": dict(sorted(totals.items(), key=lambda kv: -kv[1])),
            "signals": sum(r["signals"] for r in rows),
            "attempts": sum(r["attempts"] for r in rows),
            "opened": sum(r["opened"] for r in rows),
        }

    def reset_entry_blocks(self) -> None:
        self._entry_blocks = {}
        self._entry_last_bar = {}
        self._entry_events = []
        prev = float(getattr(self, "_entry_blocks_since", 0.0) or 0.0)
        self._entry_blocks_since = max(time.time(), prev + 1e-6)
        self._entry_blocks_dirty = True
        self._entry_events_dirty = True
        self._flush_entry_blocks(force=True)

    def _broker_now_int(self) -> int:
        """Broker wall-clock as a naive epoch, same stamps as deal.time.

        Machine local (UTC+3) ``time.time()`` is the fallback only when the
        broker clock has never been read - mixing the two for held_min would
        look like a three-hour hold on a one-minute trade.
        """
        client = getattr(self, "client", None)
        getter = getattr(client, "broker_now", None) if client is not None else None
        now = 0.0
        if callable(getter):
            try:
                now = float(getter() or 0.0)
            except (TypeError, ValueError):
                now = 0.0
        if now > 0:
            return int(now)
        return int(time.time())

    def _flatten_clock(self, decision_now: float | None) -> float | None:
        """Clock for weekend/session/day-end flatten.

        Entries stay on strict ``decision_now()`` (None when the tick is
        stale). Flatten must not: a Friday feed stall that blanks
        decision_now used to skip ``weekend_closed`` / ``should_flatten``
        entirely and ride the gap (H2). Prefer decision_now when fresh;
        else broker_now, else server_now.
        """
        if decision_now is not None:
            try:
                value = float(decision_now)
            except (TypeError, ValueError):
                value = 0.0
            if value > 0:
                return value
        client = getattr(self, "client", None)
        for name in ("broker_now", "server_now"):
            getter = getattr(client, name, None) if client is not None else None
            if not callable(getter):
                continue
            try:
                value = float(getter() or 0.0)
            except (TypeError, ValueError):
                continue
            if value > 0:
                return value
        return None

    def _autopsy_window_start(self, rows: list[dict[str, Any]] | None = None) -> float:
        """Oldest exit stamp still in the ring, or now if the ring is empty.

        ``trade_autopsies_since`` used to be a start-of-feature stamp restored
        even when the ring was empty. The n>=50 gate and FWD completeness then
        used a denominator the table never covered. The window is the rows.
        """
        if rows is None:
            rows = list(getattr(self, "_trade_autopsies", []) or [])
        times: list[float] = []
        for row in rows:
            t = self._autopsy_float(row.get("exit_time"))
            if t is not None and t > 0:
                times.append(t)
        if times:
            return float(min(times))
        return time.time()

    def _load_trade_autopsies(self) -> None:
        """Restore the close ring. Corrupt rows are skipped, not coerced."""
        try:
            limit = int(getattr(self, "_trade_autopsy_limit", TRADE_AUTOPSY_LIMIT)
                        or TRADE_AUTOPSY_LIMIT)
            rows: list[dict[str, Any]] = []
            for item in as_list(self.store.get_setting("trade_autopsies"),
                                "trade_autopsies"):
                if not isinstance(item, dict):
                    continue
                try:
                    symbol = str(item["symbol"])
                    ticket = int(item["ticket"])
                except (KeyError, TypeError, ValueError):
                    continue
                row = dict(item)
                row["symbol"] = symbol
                row["ticket"] = ticket
                rows.append(sanitize_autopsy_r(row))
            self._trade_autopsies = rows[-limit:]
            # The stored stamp is not the table. It was written when the
            # feature first started (empty ring, 19.08 09:43) and then
            # restored across restarts; the first row landed at 15:19.
            # Completeness vs broker closes used that stamp and counted
            # four SL exits the ring never contained. Oldest exit_time
            # still in the ring is the window the n>=50 gate actually has.
            self._trade_autopsies_since = self._autopsy_window_start(
                self._trade_autopsies)
            self._rebuild_autopsy_pending()
        except Exception:
            self._trade_autopsies = []
            self._trade_autopsies_since = time.time()
            self._autopsy_pending = {}

    def _autopsy_safe(self, **fields: Any) -> None:
        """Record one close for diagnostics, and never let that break a close.

        Both call sites sit in the bookkeeping that runs *after* the position
        is already gone from the broker - one reaping a broker exit, one after
        _close_tracked succeeded. An exception raised while building a
        diagnostic row would abort that bookkeeping, and in _close_tracked it
        would surface to the caller as a failed close that in fact happened.
        Nothing measured here is worth that.
        """
        try:
            self.record_trade_autopsy(self._autopsy_row(**fields))
        except Exception as exc:                    # diagnostics only
            LOG.emit(f"otopsi kaydi atlandi: {type(exc).__name__}", "WARN")

    def record_trade_autopsy(self, row: dict[str, Any]) -> None:
        """Append one close. Oldest dropped past the cap. Does not trade."""
        events = getattr(self, "_trade_autopsies", None)
        if events is None:
            self._trade_autopsies = []
            events = self._trade_autopsies
        events.append(sanitize_autopsy_r(dict(row)))
        limit = int(getattr(self, "_trade_autopsy_limit", TRADE_AUTOPSY_LIMIT)
                    or TRADE_AUTOPSY_LIMIT)
        if len(events) > limit:
            self._trade_autopsies = events[-limit:]
            self._rebuild_autopsy_pending()
        else:
            self._pending_autopsy_add(events[-1])
        self._trade_autopsies_since = self._autopsy_window_start()
        self._trade_autopsies_dirty = True

    def _flush_trade_autopsies(self) -> None:
        """Persist the close ring only when a close actually landed."""
        try:
            if not getattr(self, "_trade_autopsies_dirty", False):
                return
            limit = int(getattr(self, "_trade_autopsy_limit", TRADE_AUTOPSY_LIMIT)
                        or TRADE_AUTOPSY_LIMIT)
            rows = list(getattr(self, "_trade_autopsies", []) or [])[-limit:]
            self._trade_autopsies = rows
            self._rebuild_autopsy_pending()
            self.store.set_setting("trade_autopsies", rows)
            self._trade_autopsies_since = self._autopsy_window_start(rows)
            self.store.set_setting("trade_autopsies_since",
                                   float(self._trade_autopsies_since))
            self._trade_autopsies_dirty = False
            self._flush_ok("trade_autopsies")
        except Exception as exc:
            self._flush_failed("trade_autopsies", exc)

    @staticmethod
    def _autopsy_hold_bucket(held_min: float | None) -> str:
        if held_min is None:
            return "unknown"
        if held_min < 5:
            return "0-5"
        if held_min < 30:
            return "5-30"
        if held_min < 120:
            return "30-120"
        return "120+"

    @staticmethod
    def _autopsy_exit_reason(reason_code: int | None, comment: str,
                             book: dict[str, Any]) -> str:
        """Map a close onto the five labels CHOP-1 will count.

        Broker SL that still sits on the first-sight stop is ``sl``; a moved
        stop is ``trail``. Engine comments decide flatten vs weekend. Manual
        (terminal/phone/web) is ``manuel``. Stop-out is counted as ``sl``:
        the position hit a hard loss, not a flatten we sent.
        """
        if reason_code in (execution.DEAL_REASON_CLIENT,
                           execution.DEAL_REASON_MOBILE,
                           execution.DEAL_REASON_WEB):
            return "manuel"
        if reason_code == execution.DEAL_REASON_SL:
            try:
                orig = float(book.get("original_sl") or 0)
            except (TypeError, ValueError):
                orig = 0.0
            try:
                cur_sl = float(book.get("sl") or 0)
            except (TypeError, ValueError):
                cur_sl = 0.0
            # Poisoned (<=0) originals must not count as a moved trail
            # (GER40/US30 02.09: original_sl=-49.5 labelled "trail").
            if orig > 0 and cur_sl > 0 and abs(cur_sl - orig) > max(1e-9, abs(orig) * 1e-8):
                return "trail"
            return "sl"
        if reason_code == execution.DEAL_REASON_TP:
            return "trail"
        if reason_code == execution.DEAL_REASON_SO:
            return "sl"
        text = (comment or "").lower()
        if "hafta" in text:
            return "weekend"
        return "flatten"

    @staticmethod
    def _autopsy_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            out = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(out):
            return None
        return out

    def _autopsy_row(self, *, book: dict[str, Any], ticket: Any, symbol: Any,
                     exit_price: float | None, exit_time: Any,
                     profit: float | None, reason_code: Any,
                     comment: str) -> dict[str, Any]:
        """Build one close row from the open book plus the exit print.

        Takes the raw report fields rather than coerced ones: the caller sits
        in a close path, so any coercion it did would raise outside the guard
        in ``_autopsy_safe``. A row with a missing ticket is still worth
        keeping - it carries the excursions - so absent values become 0 here
        instead of ending the row.
        """
        ticket = int(self._autopsy_float(ticket) or 0)
        symbol = str(symbol or book.get("symbol") or "")
        exit_time = int(self._autopsy_float(exit_time) or 0)
        reason_code = (None if reason_code is None
                       else int(self._autopsy_float(reason_code) or 0))
        entry = self._autopsy_float(book.get("entry"))
        if entry is None:
            entry = self._autopsy_float(book.get("fill_price"))
        # Original hard stop, not the close-time trail. A winning SL fill at a
        # moved stop has |exit-entry| == |sl-entry|, so dividing by risk_dist
        # from the close-time SL is tautologically 1.0 R (25.08 GER40 trio).
        orig_sl = self._autopsy_float(book.get("original_sl"))
        if entry is not None and orig_sl is not None and orig_sl > 0:
            risk = abs(entry - orig_sl)
        else:
            risk = self._autopsy_float(book.get("risk_dist")) or 0.0
        side = str(book.get("side") or "")
        mfe = self._autopsy_float(book.get("mfe"))
        mae = self._autopsy_float(book.get("mae"))
        mfe_r = (mfe / risk) if mfe is not None and risk > 0 else None
        mae_r = (mae / risk) if mae is not None and risk > 0 else None
        r_realised = None
        px = self._autopsy_float(exit_price)
        if entry is not None and px is not None and risk > 0 and side in ("buy", "sell"):
            move = (px - entry) if side == "buy" else (entry - px)
            r_realised = move / risk
        left = None
        if mfe_r is not None and r_realised is not None:
            left = mfe_r - r_realised
        fill_t = int(book.get("fill_time") or book.get("opened_at") or 0)
        closed_at = int(exit_time or 0)
        held_min = None
        if fill_t > 0 and closed_at > fill_t:
            held_min = (closed_at - fill_t) / 60.0
        tf = int(book.get("tf_seconds") or 0)
        bars_held = None
        if held_min is not None and tf > 0:
            bars_held = (held_min * 60.0) / tf

        def _round(value: float | None, digits: int) -> float | None:
            return None if value is None else round(value, digits)

        return {
            "symbol": symbol,
            "ticket": ticket,
            "side": side,
            "signal_bar_time": int(book.get("signal_bar_time") or 0) or None,
            "fill_time": fill_t or None,
            "exit_time": closed_at or None,
            "fill_vs_signal_close": _round(
                self._autopsy_float(book.get("fill_vs_signal_close")), 6),
            "fill_vs_signal_close_pts": _round(
                self._autopsy_float(book.get("fill_vs_signal_close_pts")), 3),
            "fill_vs_signal_close_r": _round(
                self._autopsy_float(book.get("fill_vs_signal_close_r")), 4),
            "mfe_r": _round(mfe_r, 4),
            "mae_r": _round(mae_r, 4),
            "r_realised": _round(r_realised, 4),
            "left_on_table_r": _round(left, 4),
            "exit_reason": self._autopsy_exit_reason(reason_code, comment, book),
            "held_min": _round(held_min, 2),
            "bars_held": _round(bars_held, 2),
            "spread_atr": _round(self._autopsy_float(book.get("spread_atr")), 4),
            "adx": _round(self._autopsy_float(book.get("adx")), 2),
            "atr_pct": _round(self._autopsy_float(book.get("atr_pct")), 6),
            "profit": _round(self._autopsy_float(profit), 2),
            # Frozen prices so the hour after the stop can be scored later
            # without parsing TRADE lines. Missing values stay None; the
            # sweeper then marks the row done rather than retrying forever.
            "entry": _round(entry, 6),
            "sl": _round(self._autopsy_float(book.get("sl")), 6),
            "original_sl": _round(self._autopsy_float(book.get("original_sl")), 6),
            "exit_price": _round(px, 6),
        }

    def _rebuild_autopsy_pending(self) -> None:
        """Index close rows that still need the hour-after-stop fill."""
        pending: dict[str, list[dict[str, Any]]] = {}
        for row in list(getattr(self, "_trade_autopsies", []) or []):
            if row.get("after_1h_bars") is not None:
                continue
            pending.setdefault(str(row.get("symbol") or ""), []).append(row)
        self._autopsy_pending = pending

    def _pending_autopsy_add(self, row: dict[str, Any]) -> None:
        if row.get("after_1h_bars") is not None:
            return
        idx = getattr(self, "_autopsy_pending", None)
        if not isinstance(idx, dict):
            self._autopsy_pending = {}
            idx = self._autopsy_pending
        idx.setdefault(str(row.get("symbol") or ""), []).append(row)

    def _pending_autopsies(self, symbol: str) -> list[dict[str, Any]]:
        idx = getattr(self, "_autopsy_pending", None)
        if not isinstance(idx, dict):
            return [r for r in list(getattr(self, "_trade_autopsies", []) or [])
                    if str(r.get("symbol") or "") == symbol
                    and r.get("after_1h_bars") is None]
        return list(idx.get(symbol, ()))

    def _drop_pending_autopsy(self, symbol: str, row: dict[str, Any]) -> None:
        idx = getattr(self, "_autopsy_pending", None)
        if not isinstance(idx, dict):
            return
        bucket = idx.get(symbol)
        if not bucket:
            return
        idx[symbol] = [r for r in bucket if r is not row]

    def _fill_after_stop(self, symbol: str, state: SymbolState) -> None:
        """Score the hour after a close once that hour's bars exist.

        Observation only. Never raises into ``_evaluate``. A row without
        prices, or whose hour contained no closed bars, is marked
        ``after_1h_bars=0`` so the sweeper does not retry it forever.
        R is the frozen original stop, not a later trail.
        """
        bars = getattr(state, "bars", None)
        if bars is None:
            return
        last_closed = float(getattr(bars, "last_closed_time", 0) or 0)
        if last_closed <= 0:
            return
        times = getattr(bars, "time", None)
        high = getattr(bars, "high", None)
        low = getattr(bars, "low", None)
        if times is None or high is None or low is None:
            return
        rows = getattr(self, "_trade_autopsies", None)
        if not rows:
            return
        pending = self._pending_autopsies(symbol)
        if not pending:
            return
        dirty = False
        horizon = 3600.0
        store = getattr(self, "store", None)
        cfg = (getattr(store, "symbols", None) or {}).get(symbol) if store is not None else None
        tf_sec = int(timeframe_seconds(cfg.timeframe) or 0) if cfg is not None else 0
        for row in pending:
            exit_t = self._autopsy_float(row.get("exit_time"))
            if exit_t is None or exit_t <= 0:
                continue
            # last_closed_time is the OPEN of the last closed bar. The hour
            # after the exit exists once that bar has closed (open + tf).
            # Comparing open stamps delayed gold's 14:46 hour until 16:15 —
            # the 16:00 bar's close — instead of 16:00, when the 15:45 M15
            # had already finished (97s past the wall hour). Measured 24.08.
            if last_closed + tf_sec < float(exit_t) + horizon:
                continue
            entry = self._autopsy_float(row.get("entry"))
            orig = self._autopsy_float(row.get("original_sl"))
            sl = orig if orig and orig > 0 else self._autopsy_float(row.get("sl"))
            exit_px = self._autopsy_float(row.get("exit_price"))
            side = str(row.get("side") or "")
            if entry is None or sl is None or exit_px is None or not side:
                row["after_1h_bars"] = 0
                dirty = True
                self._drop_pending_autopsy(symbol, row)
                continue
            filled = after_stop_excursions(
                side, entry, sl, exit_px, times, high, low,
                exit_time=float(exit_t), horizon_sec=horizon,
                bar_sec=float(tf_sec),
            )
            if filled is None:
                row["after_1h_bars"] = 0
            else:
                row.update(filled)
            dirty = True
            self._drop_pending_autopsy(symbol, row)
        if dirty:
            self._trade_autopsies_dirty = True

    def trade_autopsy_report(self) -> dict[str, Any]:
        """Symbol x exit_reason x hold-time bucket, plus left-on-table total.

        Observation only. ``n<30`` on a cell is a count, not a finding.
        """
        rows = list(getattr(self, "_trade_autopsies", []) or [])
        groups: dict[tuple[str, str, str], dict[str, Any]] = {}
        left_total = 0.0
        left_n = 0
        for row in rows:
            bucket = self._autopsy_hold_bucket(self._autopsy_float(row.get("held_min")))
            key = (str(row.get("symbol") or ""),
                   str(row.get("exit_reason") or ""),
                   bucket)
            cell = groups.setdefault(key, {
                "symbol": key[0], "exit_reason": key[1], "held": key[2],
                "n": 0, "r_sum": 0.0, "r_n": 0, "left_sum": 0.0, "left_n": 0,
            })
            cell["n"] += 1
            realised = self._autopsy_float(row.get("r_realised"))
            # |R| past AUTOPSY_R_ABS_MAX is a denominator artifact (NAS −195).
            if realised is not None and abs(realised) > AUTOPSY_R_ABS_MAX:
                realised = None
            if realised is not None:
                cell["r_sum"] += realised
                cell["r_n"] += 1
            left = self._autopsy_float(row.get("left_on_table_r"))
            # Loser left ≈ mfe + 1R: that is the loss, not giveback. Headline
            # and cells that say "masada" only count winners (r > 0).
            if (left is not None and realised is not None and realised > 0):
                cell["left_sum"] += left
                cell["left_n"] += 1
                left_total += left
                left_n += 1
        summary = []
        for cell in groups.values():
            summary.append({
                "symbol": cell["symbol"],
                "exit_reason": cell["exit_reason"],
                "held": cell["held"],
                "n": cell["n"],
                "mean_r": (round(cell["r_sum"] / cell["r_n"], 4)
                           if cell["r_n"] else None),
                "left_on_table_r": (round(cell["left_sum"], 4)
                                    if cell["left_n"] else None),
            })
        summary.sort(key=lambda r: (r["symbol"], r["exit_reason"], r["held"]))
        after_n = 0
        through_n = 0
        extra_ge = 0
        recov_ge = 0
        for row in rows:
            bars_n = self._autopsy_float(row.get("after_1h_bars"))
            if bars_n is None or bars_n <= 0:
                continue
            after_n += 1
            if row.get("after_1h_through_entry"):
                through_n += 1
            extra = self._autopsy_float(row.get("after_1h_extra_r"))
            if extra is not None and extra >= 0.5:
                extra_ge += 1
            recov = self._autopsy_float(row.get("after_1h_recovery_r"))
            if recov is not None and recov >= 0.5:
                recov_ge += 1
        return {
            "since": float(self._autopsy_window_start(rows)),
            "n": len(rows),
            "left_on_table_r": round(left_total, 4) if left_n else None,
            "after_1h_n": after_n,
            "after_1h_through_entry": through_n,
            "after_1h_extra_ge_0_5r": extra_ge,
            "after_1h_recovery_ge_0_5r": recov_ge,
            "premature_by_symbol": self._premature_by_symbol(rows),
            "summary": summary,
            "rows": rows,
        }

    @staticmethod
    def _premature_by_symbol(rows: list) -> list[dict[str, Any]]:
        """Per-symbol premature-SL counts (hybrid gate / morning watch)."""
        from .optimizer import premature_sl_count_from_autopsy
        symbols: list[str] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            sym = str(row.get("symbol") or "")
            if not sym or sym in seen:
                continue
            seen.add(sym)
            symbols.append(sym)
        out: list[dict[str, Any]] = []
        for sym in symbols:
            n = premature_sl_count_from_autopsy(rows, sym)
            if n <= 0:
                continue
            out.append({"symbol": sym, "premature_n": n})
        out.sort(key=lambda r: (-int(r["premature_n"]), str(r["symbol"])))
        return out

    # ------------------------------------------------------------ evaluation

    def _evaluate_disabled(self, cfg: SymbolConfig, state: SymbolState,
                           server_now: float | None, account: dict[str, Any]) -> None:
        """Handle one ``cfg.enabled == False`` symbol for this cycle.

        A position can still be open under this magic (the user paused a
        symbol, not stopped-and-flattened it) - full skip (old behaviour)
        stops state.last_bar/atr from ever advancing again, and
        manage_positions() then never fires _update_stop for that ticket
        again: trail/BE/partial-TP freezes silently for good, with only the
        broker's own static stop left protecting it. allow_entry=False guarantees
        _evaluate() can never arm a NEW entry here (same gate every other
        allow_entry=False path already relies on - bot stopped, daily guard
        tripped, netting - none of which clear the signal chain either,
        since a merely-not-actionable signal is not a stale one).
        """
        if any(p["magic"] == cfg.magic for p in self._positions):
            try:
                self._evaluate(cfg, state, server_now, account, allow_entry=False)
            except Exception as exc:
                LOG.emit(f"Degerlendirme hatasi (kapali sembol): {exc}", "ERROR", cfg.symbol)
            state.note = "kapali"
        else:
            # Same stale-signal hazard as the session/market_open gates:
            # clearing only state.signal leaves primary_signal/pending_bar_key
            # standing, so re-enabling before a new bar closes could revive
            # and fire a signal from before the symbol was disabled.
            state.note = "kapali"
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
            state.pending_bar_key = (0, 0)

    def _evaluate(self, cfg: SymbolConfig, state: SymbolState, server_now: float | None,
                  account: dict[str, Any], allow_entry: bool) -> bool:
        """Refresh state; return True when this symbol wants an entry this bar."""
        state.note = ""
        state.entry_block = ""
        if self.client.resolve(cfg.symbol) is None:
            state.note = (f"broker sembolu bulunamadi"
                          f"{f' ({cfg.broker_symbol})' if cfg.broker_symbol else ''}"
                          f" - Sistem sekmesinden esleyin")
            # Same stale-signal hazard as the other gates - clear the whole
            # chain, not just state.signal, so a fixed mapping doesn't revive
            # a signal from before resolution broke.
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
            state.pending_bar_key = (0, 0)
            return False

        if server_now is None:
            # Last tick is too old to be "now". Do not evaluate Friday's close
            # as Sunday's session, and do not fall back to Windows time.
            state.note = "broker saati bayat"
            state.session = {"open": False, "window": "saat bayat",
                             "minutes_to_close": None, "minutes_to_open": None}
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
            state.pending_bar_key = (0, 0)
            return False

        params = Params.from_config(cfg)
        all_hours = bool(self.store.system.trade_all_hours)
        sess = sessions.evaluate(cfg, server_now, all_hours)
        state.session = {
            "open": sess.open, "window": sess.window,
            "minutes_to_close": sess.minutes_to_close,
            "minutes_to_open": sess.minutes_to_open,
        }

        tick = self.client.tick(cfg.symbol)
        if tick:
            state.spread = tick["spread"]
            state.spread_atr = tick["spread"] / state.atr if state.atr > 0 else 0.0

        primary_fresh = self._refresh_signals(cfg, state, params)
        try:
            self._fill_after_stop(cfg.symbol, state)
        except Exception:
            pass
        self._merge_signals(cfg, state)
        fresh = primary_fresh
        bar_key = state.last_bar
        driving_fresh = primary_fresh
        if driving_fresh and state.signal:
            state.pending_bar_key = (state.signal_source, bar_key)
        elif not state.signal:
            state.pending_bar_key = (0, 0)

        if not sess.open:
            state.note = f"seans disi ({sess.window})"
            # Merge already ran, so a live signal can sit here. Tally it
            # before clearing: this is the same invisibility as bar_bosluk,
            # one gate earlier. No-signal closed polls stay silent via the
            # helper. Clearing the whole chain still matters: only
            # ``state.signal`` used to be wiped, so ``_merge_signals``
            # resurrected it from the still-set primary on the next poll
            # and a pre-close signal could fire the instant the session
            # reopened, on whatever bar was still cached.
            self._tally_evaluate_refuse(cfg, state, "seans_disi", bar_key)
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
            state.pending_bar_key = (0, 0)
            state.entry_block = "seans_disi"
            return False
        if not self.client.market_open(cfg.symbol):
            # Same staleness hazard as the sess.open branch above: with
            # trade_all_hours on, sess.open is true around the clock and this
            # is the only gate that actually catches an overnight index/
            # commodity halt, so it has to clear the whole signal chain too.
            self._tally_evaluate_refuse(cfg, state, "piyasa_kapali", bar_key)
            state.note = "piyasa kapali / fiyat akmiyor"
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
            state.pending_bar_key = (0, 0)
            state.entry_block = "piyasa_kapali"
            return False
        # Sampled here, past BOTH gates, rather than beside the tick read.
        #
        # The point of this measurement is what _try_entry's spread gate will
        # see when it tries to enter, and that gate only ever runs on a symbol
        # whose session is open and whose feed is live. Taken earlier it also
        # recorded the hours the symbol never trades - and those are not a
        # small perturbation. Measured at 00:01 with every session closed:
        # AUDUSD's tick sat at 57x its own ceiling and GBPJPY's at 59x, while
        # the same symbols run near 1.0x during their sessions.
        #
        # This book already knows that hour is different: FX sessions were
        # moved off hour 0 precisely because it cost 216% of risk, 6.3x the
        # median. Feeding the excluded hours back into the number that prices
        # the search undoes that.
        #
        # The weekend is what makes it urgent rather than cosmetic. Friday
        # close to Sunday open is ~48 hours of dead-market spread, more
        # samples than a whole trading day, all of it from hours no entry can
        # happen in.
        self._sample_spread_ratio(cfg, state, tick)
        tf_sec = timeframe_seconds(cfg.timeframe)
        if signal_bar_expired(state.last_bar, server_now, tf_sec):
            # Friday's last closed M30 arriving at Monday session open after a
            # restart. Session-close clearing does not cover this: last_bar
            # was 0, so the still-last-closed Friday stamp looked fresh.
            # Tally before clearing: the ready-loop never sees this return.
            self._tally_evaluate_refuse(cfg, state, "bar_bosluk", bar_key)
            state.note = "sinyal bari gecmis (bosluk)"
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
            state.pending_bar_key = (0, 0)
            state.entry_block = "bar_bosluk"
            return False
        if not fresh and state.signal == "":
            state.note = state.note or "bekliyor"
            return False

        if not allow_entry:
            return False
        if sessions.should_flatten(cfg, server_now, all_hours):
            state.note = "kapanis oncesi giris yok"
            return False
        if sessions.day_end_close(server_now, self.store.system.day_end_flatten_min):
            state.note = "gun sonu - giris yok"
            return False
        if time.time() < state.cooldown_until:
            state.note = f"cooldown {int(state.cooldown_until - time.time())}sn"
            return False
        symbol_halt = self._symbol_daily_halt(cfg)
        if symbol_halt:
            state.note = symbol_halt
            self._tally_evaluate_refuse(cfg, state, "sembol_halt", bar_key)
            return False
        if not state.signal:
            state.note = state.note if state.note else "sinyal yok"
            return False
        if self._filled_bars.get(cfg.symbol, {}).get(state.signal_source) == bar_key:
            # This bar's signal has already been filled once. Held in the
            # store, because it is the only thing standing between a restart
            # and a second position on the same signal: SymbolState is rebuilt
            # empty on every start, the signal recomputes identically from the
            # same still-last-closed bar, and nothing else says no.
            #
            # The post-fill cooldown does NOT cover this. It is 2 minutes,
            # while a bar is 5 to 60, so a restart even slightly later walks
            # straight past it - which is exactly what happened live:
            #
            #   19:00:27 NAS100 BUY @ 29728.00
            #   19:01:22 restart
            #   19:09:26 NAS100 BUY @ 29705.90   (same M30 bar, cooldown long gone)
            #
            # Both stopped out for -14.22 each.
            self._tally_evaluate_refuse(cfg, state, "bar_doldu", bar_key)
            state.note = "bu barin sinyali zaten dolduruldu"
            state.entry_block = "bar_doldu"
            return False
        if state.pending_bar_key == (state.signal_source, bar_key):
            # Same bar as when the signal first appeared (see the marking
            # above) and not yet filled - keep offering it every poll until
            # the block clears, the position fills (_try_entry's success path
            # clears state.signal, which clears pending_bar_key next cycle),
            # or the bar rolls over and bar_key stops matching. Backtest still
            # tries a signal exactly once per bar; this only stops live from
            # discarding one to a transient block backtest never modelled.
            return True
        state.note = state.note if state.note else "sinyal yok"
        return False

    def _cost_series(self, cfg: SymbolConfig, bars) -> Any:
        """Per-bar round-turn cost in price units, exactly as the backtest models it.

        The scalping families measure their entry threshold in cost multiples,
        so live has to hand them the same number the walk-forward charged -
        bar spread converted through ``point`` plus the round-turn commission
        expressed in price units. Returns None when the symbol's tick data is
        missing, which makes those families produce no signal rather than a
        signal built on a guessed cost.
        """
        info = self.client.info(cfg.symbol)
        if not info:
            return None
        point = float(info.get("point", 0.0) or 0.0)
        if point <= 0:
            return None
        commission = backtest.commission_in_price(
            cfg.commission_per_lot,
            float(info.get("tick_value", 0.0) or 0.0),
            float(info.get("tick_size", 0.0) or 0.0))
        return bars.spread * point + commission

    def _note_bar_stamp(self, symbol: str, kind: str, stamp: int | float,
                        message: str) -> None:
        """WARN once per (kind, symbol, stamp). Prune and cap so it cannot grow.

        Review 24.08 08:30: the rewind latch was unbounded, and the future
        escape reset last_bar with no line. Same class as the silent refuse.
        Bound is small because these events are rare; clearing on overflow
        may re-WARN, which is the safe direction.
        """
        key = (kind, str(symbol), int(stamp))
        logged = getattr(self, "_bar_rewind_logged", None)
        if logged is None:
            self._bar_rewind_logged = logged = set()
        symbols = getattr(getattr(self, "store", None), "symbols", None)
        if symbols is not None:
            live = set(symbols)
            logged.intersection_update(k for k in logged if k[1] in live)
        if len(logged) > 64:
            logged.clear()
        if key in logged:
            return
        logged.add(key)
        LOG.emit(message, "WARN", symbol)

    def _bar_window_pins(self, symbol: str, timeframe: str,
                         closed_count: int) -> tuple[int, int] | None:
        """Oldest and last-closed stamps, or None to force a full copy."""
        getter = getattr(self.client, "bar_window_pins", None)
        if not callable(getter):
            return None
        try:
            pins = getter(symbol, timeframe, closed_count)
        except Exception:
            return None
        if not pins or len(pins) != 2:
            return None
        try:
            return (int(pins[0]), int(pins[1]))
        except (TypeError, ValueError):
            return None

    def _refresh_signals(self, cfg: SymbolConfig, state: SymbolState, params: Params) -> bool:
        """Pull bars and recompute indicators when a new bar has closed."""
        now = time.time()
        # Against the BROKER's clock, not this machine's. ``next_bar_at`` is
        # built from ``bars.last_closed_time``, a naive epoch holding the
        # broker's wall-clock reading, while ``server_now()`` is a true epoch -
        # subtracting one from the other leaves the broker's whole UTC offset
        # in the answer, +10800 on this GMT+3 server. Measured 15.08 00:01:
        # last closed bar 164 minutes "ahead" of local, next_bar_at 174 minutes
        # ahead, so ``due`` was False on every cycle for the life of the
        # process. The refresh still happened - ``stale`` fires every 45s - so
        # nothing looked broken, and that is the point: the intended trigger
        # was dead and a fallback silently carried the system. It also moved
        # every entry off the bar close and onto a 45-second timer, which is
        # what the measured 21-30s-into-the-bar entry timing was.
        #
        # Same fix ``market_open`` already uses: compare two readings of one
        # clock. 0.0 means no tick has been read yet, and falling back to the
        # timer there is the behaviour that has been running all along.
        broker_now = self.client.broker_now()
        due = broker_now > 0.0 and broker_now >= state.next_bar_at
        # 15.08: stale-every-45s silently carried the system when `due` used
        # the machine clock. `due` is broker-clock now. A 900s pass with no
        # new bar pins the window ends (two small copy_rates) and only
        # full-fetches on mismatch. A middle-bar hole with both ends
        # unchanged is the remaining miss — rarer than the old 900s lock hold.
        integrity = now - state.last_fetch > _BAR_INTEGRITY_REFRESH
        if not (due or integrity or state.last_bar == 0):
            return False

        need = required_bars(params)
        if (integrity and not due and state.last_bar
                and state.bars is not None and len(state.bars) >= need):
            pins = self._bar_window_pins(cfg.symbol, cfg.timeframe, len(state.bars))
            if pins is not None:
                oldest, last_closed = pins
                if (last_closed == int(state.last_bar)
                        and oldest == int(state.bars.time[0])):
                    state.last_fetch = now
                    return False
        bars = self.client.bars(cfg.symbol, cfg.timeframe, need)
        state.last_fetch = now
        # required_bars() states what the indicator stack needs to be
        # trustworthy, and the fetch above asks for exactly that - but the
        # guard used to accept a flat 60, which is 8% of it. MT5 populates
        # chart history lazily, so a symbol can genuinely return far less than
        # was asked for during the first cycles after start-up, and the
        # signals computed on that stub are not weaker versions of the real
        # ones, they are different ones.
        #
        # Measured on a 4000-bar series, 20 families, 100 sample bars each,
        # comparing the last bar's signal against the same bar computed with
        # full history: 720 bars disagreed on 0 of 116 real signals, 360 on 2,
        # 240 on 2, then 200 on 24 and 60 on 82 - wrong more often than right
        # at the old floor, and 100% wrong for mtf_pullback and stoch_flip.
        #
        # Half of required_bars sits in the flat part of that curve and is
        # derived from the number the code already computes rather than one
        # picked by hand. Every live symbol currently holds 400-1680 bars, so
        # this costs nothing today; it closes the start-up window.
        min_bars = max(60, need // 2)
        if bars is None or len(bars) < min_bars:
            state.note = f"yeterli bar yok ({len(bars) if bars else 0}/{min_bars})"
            state.bars_ready = len(bars) if bars else 0
            return False

        tf_sec = timeframe_seconds(cfg.timeframe)
        broker_now = self.client.broker_now()
        # Same-clock as last_closed (broker naive epoch). Machine time is the
        # UTC-offset trap. No tick yet (0.0) means we cannot judge "future".
        if broker_now > 0.0 and state.last_bar > broker_now + tf_sec:
            # Escape hatch for the rewind gate below. That gate has no way
            # out: once last_bar sits in the future, every real bar is older
            # and the symbol never signals again. The tick path already
            # drops those stamps (_MAX_TICK_AHEAD_SEC); bars did not, and
            # 6c3de07 made a poisoned last_bar fatal. Review 24.08 07:55.
            poisoned = state.last_bar
            state.last_bar = 0
            self._note_bar_stamp(
                cfg.symbol, "future", poisoned,
                "bar damgasi ileri tarih - last_bar sifirlandi")
        if broker_now > 0.0 and bars.last_closed_time > broker_now + tf_sec:
            state.note = "bar damgasi ileri tarih"
            self._note_bar_stamp(
                cfg.symbol, "future_fetch", bars.last_closed_time,
                "bar damgasi ileri tarih - last_bar yazilmadi")
            return False

        if state.last_bar > 0 and bars.last_closed_time < state.last_bar:
            # History rewound after attach. Measured 24.08 01:00: NAS100
            # SIGNAL identical to 22.08 08:26 (K=40.1 D=52.1 ATR=56.39410).
            # The process never restarted, so last_bar was not 0, and SIGNAL
            # only emits when last_closed != last_bar. copy_rates handed back
            # an older last-closed stamp; the equality check below only
            # catches "same stamp". Keep the in-memory bar, do not re-fire it.
            state.note = "bar gecmisi geri sarildi"
            self._note_bar_stamp(
                cfg.symbol, "rewind", bars.last_closed_time,
                "bar gecmisi geri sarildi - taze sinyal sayilmadi")
            return False

        state.bars_ready = len(bars)
        state.bars = bars
        state.next_bar_at = bars.last_closed_time + 2 * tf_sec + 2

        if bars.last_closed_time == state.last_bar:
            return False
        state.last_bar = bars.last_closed_time

        cache = IndicatorCache(bars.high, bars.low, bars.close, bars.time, tf_sec,
                               bars.open, bars.volume, self._cost_series(cfg, bars))
        sig: Signals = compute(cache, params)
        snap = sig.last()
        state.t3 = snap.get("t3")
        state.t3_rising = snap.get("t3_rising")
        state.t3_kind = snap.get("t3_kind")
        state.k = snap.get("k")
        state.d = snap.get("d")
        state.atr = snap.get("atr", 0.0)
        state.adx = snap.get("adx")
        state.htf = int(snap.get("htf", 0))
        if snap.get("buy"):
            state.primary_signal = "buy"
        elif snap.get("sell"):
            state.primary_signal = "sell"
        else:
            state.primary_signal = ""
        if state.primary_signal:
            state.last_signal_at = time.time()
            # Only the readings this family actually measures. The fixed
            # layout printed "K=0.0 D=0.0 ADX=0" for every flip family, which
            # is the same falsehood the status panel carried - and it is this
            # line the loss reviews read back afterwards.
            parts = [f"Sinyal {state.primary_signal.upper()}"]
            for name, value, fmt in (("K", state.k, ".1f"), ("D", state.d, ".1f"),
                                     ("ATR", state.atr, ".5f"), ("ADX", state.adx, ".0f")):
                if value is not None:
                    parts.append(f"{name}={value:{fmt}}")
            parts.append(f"HTF={state.htf:+d}")
            LOG.emit(" | ".join(parts), "SIGNAL", cfg.symbol)
        return True

    def _merge_signals(self, cfg: SymbolConfig, state: SymbolState) -> None:
        """Primary signal is the only entry source.

        Secondary production was removed 14.08 (operator). Overlay config,
        sec_* state and the disagreement skip are gone with it.
        ``signal_source`` is therefore two-valued: ``"primary"`` or empty.
        It still keys filled-bar / pending-bar tracking.
        """
        primary = state.primary_signal
        state.signal = primary
        state.signal_source = "primary" if primary else ""

    def _try_entry(self, base: SymbolConfig, state: SymbolState,
                   account: dict[str, Any]) -> None:
        state.entry_block = ""
        inflight = getattr(self, "_verify_inflight", None)
        if isinstance(inflight, set) and base.symbol in inflight:
            state.note = "emir dogrulaniyor"
            state.entry_block = "emir_dogrulaniyor"
            return
        until = float(self._link_backoff.get(base.symbol, 0.0) or 0.0)
        if until > time.time():
            # The broker link refused this symbol's last order and the position
            # book confirmed nothing landed. Retrying every poll is safe but
            # not free - each attempt re-runs the ~2.1s verification - so wait
            # rather than spend the cycle on a link that is still down. The
            # signal is untouched and fires the moment the wait is over.
            state.note = f"baglanti reddi - {int(until - time.time())}sn bekleniyor"
            state.entry_block = "baglanti_beklemede"
            return
        if base.symbol in self._orphan_scan:
            # A prior secondary fill on this symbol/magic is still waiting on
            # a delayed broker ticket - self._positions cannot be trusted to
            # reflect it (that is exactly why the scan is still open), so
            # can_open()'s position-count check below cannot be relied on to
            # block a duplicate order here. Refuse ANY entry (not just
            # secondary-sourced ones - a fresh primary trade could just as
            # easily collide with a slot the still-invisible position already
            # holds) until _scan_orphan_candidates() has fully DROPPED this
            # scan entry - "abandoned" only stops actively re-diffing every
            # cycle (see _scan_orphan_candidates), it does not mean the
            # position is no longer possibly out there. Keeping the entry
            # blocked through the abandon grace window too removes the
            # contradiction of calling a symbol "abandoned" while still
            # letting fresh trades stack on top of an unresolved one.
            state.note = "ikincil ticket taramasi devam ediyor - giris beklemede"
            state.entry_block = "ikincil_tarama"
            return
        side = state.signal
        cfg = base
        atr = state.atr
        # ``atr <= 0`` alone is not fail-closed for NaN: NaN compares False to
        # everything, so ``NaN <= 0`` is False and a NaN'd indicator (a bad bar,
        # a broker glitch) would sail straight through and size sl_dist/tp_dist
        # off it below - isfinite() is the only thing that actually catches it.
        if not math.isfinite(atr) or atr <= 0:
            state.note = "ATR yok"
            state.entry_block = "atr_yok"
            return

        # No family is restricted by default any more - every one of them may
        # be searched on every timeframe, and the exit envelope follows the bar
        # rather than the family name. The check stays because the mechanism
        # does: an operator can still pin a family to a subset, and a config
        # stored under an older, narrower map must not keep trading a pairing
        # that is no longer permitted. Same custom map the search/apply used,
        # not always the shipped default - checking against the wrong table
        # here would refuse (or wrongly allow) a pairing the optimizer itself
        # judged by different rules.
        tf_allow = self.store.opt_params().get("strategy_timeframes")
        allow = tf_allow if isinstance(tf_allow, dict) else None
        if not strategy_allows_timeframe(cfg.strategy, cfg.timeframe, allow):
            state.note = f"{cfg.strategy}/{cfg.timeframe} eslesmesi yasak"
            state.signal = ""
            state.entry_block = "tf_yasak"
            return

        # Last mile before the order. The session gate already refuses weekends,
        # but this is the one call that actually spends money, so it does not
        # take that on trust.
        getter = getattr(self.client, "decision_now", None)
        if callable(getter):
            clock = getter()
            if clock is None:
                state.note = "broker saati bayat"
                state.signal = ""
                state.entry_block = "saat_bayat"
                return
            if sessions.weekend_closed(base, clock):
                state.note = "hafta sonu kapali"
                state.signal = ""
                state.entry_block = "hafta_sonu"
                return
        else:
            clock = 0.0

        tick = self.client.tick(cfg.symbol)
        if tick is None:
            state.note = "fiyat yok"
            state.entry_block = "fiyat_yok"
            return

        if cfg.max_spread_atr > 0 and tick["spread"] > atr * cfg.max_spread_atr:
            state.note = f"spread genis ({tick['spread'] / atr:.2f}xATR)"
            state.entry_block = "spread"
            return
        # Autopsy used to keep evaluate-time spread_atr while this gate used a
        # later tick — US30/JPN225 losers then looked over-cap when the gate
        # had actually passed (Claude 03.09 night). Stamp the gate tick.
        if atr > 0 and tick.get("spread") is not None:
            state.spread = float(tick["spread"])
            state.spread_atr = float(tick["spread"]) / atr
        price_ref = tick["ask"] if side == "buy" else tick["bid"]
        if cfg.min_atr_ratio > 0 and price_ref > 0 and (atr / price_ref) < cfg.min_atr_ratio:
            state.note = "volatilite dusuk"
            state.entry_block = "volatilite"
            return

        allowed, ai_reason, scale = self.supervisor.gate(cfg, clock)
        if not allowed:
            state.note = ai_reason
            state.entry_block = "ai_gate"
            return

        min_stop = self.client.min_stop_distance(cfg.symbol)
        # The hard stop. Always sent with the entry and never lifted: it is the
        # only protection that survives this process dying, and the broker's own
        # minimum distance is a floor on it, never a reason to skip it.
        sl_mult = shakeout_sl_atr_mult(
            cfg.sl_atr_mult, cfg.symbol,
            getattr(self, "_trade_autopsies", None),
            since_ts=float(getattr(cfg, "opt_updated_at", 0.0) or 0.0))
        sl_dist = max(atr * sl_mult, min_stop)
        # Size the lot against the stop that is actually sent. Using the raw
        # cfg.sl_atr_mult distance while shakeout widened sl_dist overstated
        # 1R risk on every widened fill (Claude C1).
        # No take-profit, ever. A trailing system decides when a move is over by
        # watching the move, not by naming a price in advance.
        tp_dist = 0.0

        # Optional live cost gate — off by default; optimizer already models cost.
        sys = self.store.system
        if sys.block_high_cost and sys.max_cost_pct_of_risk > 0:
            lot_probe, _ = self.risk.lot_for(
                cfg, sl_dist, account.get("balance", 0.0),
                account=account, side=side, positions=self._positions)
            if lot_probe > 0:
                r_value = sl_dist * self.client.money_per_price_unit(cfg.symbol, lot_probe)
                cost = cfg.commission_per_lot * lot_probe
                cost += tick["spread"] * self.client.money_per_price_unit(cfg.symbol, lot_probe)
                if r_value > 0 and (cost / r_value * 100.0) > sys.max_cost_pct_of_risk:
                    state.note = (f"maliyet yuksek "
                                  f"(%{cost / r_value * 100.0:.0f} > %{sys.max_cost_pct_of_risk:g})")
                    state.entry_block = "maliyet"
                    return

        lot, note = self.risk.lot_for(
            cfg, sl_dist, account.get("balance", 0.0), ai_scale=scale,
            account=account, side=side, positions=self._positions)
        if sl_mult > float(cfg.sl_atr_mult or 0) + 1e-9:
            logged = getattr(self, "_sl_floor_logged", None)
            if logged is None:
                self._sl_floor_logged = logged = {}
            if logged.get(cfg.symbol) != sl_mult:
                logged[cfg.symbol] = sl_mult
                extra = shakeout_size_note(lot, note)
                LOG.emit(
                    f"{cfg.symbol} stop {cfg.sl_atr_mult:g}->{sl_mult:g} ATR "
                    f"(sembol orijinal SL kaybi, sonraki giris, {extra})",
                    "WARN")
        if lot <= 0:
            state.note = f"lot hesaplanamadi ({note})"
            state.entry_block = "lot"
            return

        verdict = self.risk.can_open(
            cfg, side, lot, self._positions, account, sl_distance=sl_dist)
        if not verdict.ok:
            state.note = verdict.reason
            state.entry_block = _risk_block_key(verdict.reason)
            return

        entry = tick["ask"] if side == "buy" else tick["bid"]
        sl = entry - sl_dist if side == "buy" else entry + sl_dist
        tp = 0.0 if tp_dist <= 0 else (entry + tp_dist if side == "buy" else entry - tp_dist)
        if sl <= 0:
            state.note = "stop seviyesi gecersiz"
            state.entry_block = "stop"
            return

        # Held across the actual order_send + position bookkeeping so a
        # concurrent DELETE/magic-PATCH (web thread) cannot pass its own
        # open-position check in the gap between "no position exists yet"
        # and "the fill just created one" - see Engine.entry_lock. That only
        # covers one direction though: this cycle already decided to enter
        # on ``cfg`` *before* taking the lock, so a DELETE/magic-PATCH that
        # ran first (and, seeing nothing open, went ahead) would otherwise
        # have this fill land under the now-stale cfg.magic once the lock is
        # acquired - a fresh orphan from the other side of the same race. The
        # re-check below closes that direction too.
        before_tickets = {p["ticket"] for p in self._positions if p["magic"] == base.magic}
        probe = self._unfilled_probe.pop(cfg.symbol, None)
        if probe is not None:
            probe_bar, probe_count = probe
            here = (int(state.last_bar or 0), int(state.pending_bar_key[1] or 0))
            if probe_bar == here and len(before_tickets) > probe_count:
                # A previous send on this same bar came back "verified
                # unfilled" - and since then a position of ours has appeared.
                # The order did reach the market, just later than the two
                # seconds the verifier watched for. Sending again would give
                # this one signal a second entry, which the position limit
                # used to prevent only because it was set to one.
                LOG.emit(f"onceki emir gec dolmus (acik {probe_count} -> "
                         f"{len(before_tickets)}) - ayni bar icin ikinci emir "
                         f"gonderilmedi.", "WARN", cfg.symbol)
                self._mark_bar_filled(cfg.symbol, state.signal_source, state.last_bar)
                state.signal = ""
                state.signal_source = ""
                state.note = "onceki emir gec dolmus - tekrar gonderilmedi"
                state.entry_block = "gec_dolum"
                return
        orphan_closed = False
        unresolved_ticket = False
        with self.entry_lock:
            live_cfg = self.store.symbols.get(base.symbol)
            if live_cfg is None or live_cfg.magic != base.magic:
                state.note = "sembol silindi/degisti - islem iptal"
                state.entry_block = "sembol_degisti"
                return
            # Fill-time widen: gate passed, then spread blew out before send
            # (Claude 03.09 US30/JPN225 -38.8R bucket). Refuse; do not send.
            if cfg.max_spread_atr > 0 and atr > 0:
                fresh = self.client.tick(cfg.symbol)
                if fresh is not None:
                    tick = fresh
                    state.spread = float(tick["spread"])
                    state.spread_atr = float(tick["spread"]) / atr
                    if tick["spread"] > atr * cfg.max_spread_atr:
                        state.note = (
                            f"spread genis (gonderim {tick['spread'] / atr:.2f}xATR)")
                        state.entry_block = "spread"
                        return
                    entry = tick["ask"] if side == "buy" else tick["bid"]
                    sl = entry - sl_dist if side == "buy" else entry + sl_dist
                    if sl <= 0:
                        state.note = "stop seviyesi gecersiz"
                        state.entry_block = "stop"
                        return
            result = self.client.open_market(
                cfg.symbol, side, lot, sl, tp, cfg.magic,
                slippage=self.store.system.slippage_points,
                comment=f"MicoFX {cfg.timeframe}",
                defer_verify=True,
            )
            if result.get("pending_verify"):
                inflight = getattr(self, "_verify_inflight", None)
                if inflight is None:
                    self._verify_inflight = set()
                    inflight = self._verify_inflight
                inflight.add(cfg.symbol)
                pending = {
                    "symbol": cfg.symbol,
                    "side": side,
                    "sl_dist": sl_dist,
                    "lot": lot,
                    "entry": entry,
                    "note": note,
                    "tick": dict(tick),
                    "spread_atr": float(state.spread_atr or 0),
                    "bar_key": (int(state.last_bar or 0),
                                int(state.pending_bar_key[1] or 0)
                                if state.pending_bar_key else 0),
                    "probe_count": len(before_tickets),
                    "signal_source": str(state.signal_source or ""),
                    "last_bar": int(state.last_bar or 0),
                    "verify_kwargs": result.get("verify_kwargs") or {},
                }
                state.note = "emir dogrulaniyor"
                state.entry_block = "emir_dogrulaniyor"
                threading.Thread(
                    target=self._run_fill_verify, args=(pending,),
                    name=f"micofx-fill-verify-{cfg.symbol}", daemon=True,
                ).start()
                return
            if result.get("ok"):
                if not self._reload_positions():
                    # Fill reported ok but the book cannot be verified - do
                    # not treat [] as "no new ticket" (would open a ghost
                    # orphan-scan). Without a broker ticket start a scan
                    # window with the pre-fill known set.
                    if not result.get("position"):
                        unresolved_ticket = True
                        self._orphan_scan[cfg.symbol] = {
                            "magic": base.magic,
                            "known": sorted(before_tickets),
                            "since": time.time(),
                        }
                        self._save_orphan_scan()
                        LOG.emit("Islem acildi ama pozisyon listesi "
                                 "dogrulanamadi - orphan tarama baslatildi.",
                                 "ERROR", cfg.symbol)
                elif not result.get("position"):
                    # open_market() itself could not resolve which broker
                    # ticket this fill became. Diff same-magic tickets
                    # against the snapshot taken before this entry even
                    # started - retried a few times inside this same lock,
                    # since positions() can lag the fill by a beat on a
                    # slow broker. A single clean candidate is the fill;
                    # ambiguity (0 or >1 candidates) is the safety-close
                    # / scan path below.
                    new_tickets: set[int] = set()
                    after_tickets: set[int] = set()
                    for attempt in range(3):
                        after_tickets = {p["ticket"] for p in self._positions
                                        if p["magic"] == base.magic}
                        new_tickets = after_tickets - before_tickets
                        if new_tickets or attempt == 2:
                            break
                        time.sleep(0.2)
                        if not self._reload_positions():
                            # Mid-retry disconnect: do not conclude
                            # "zero candidates" from a failed list.
                            unresolved_ticket = True
                            self._orphan_scan[cfg.symbol] = {
                                "magic": base.magic,
                                "known": sorted(before_tickets),
                                "since": time.time(),
                            }
                            self._save_orphan_scan()
                            LOG.emit("Ticket cozumlemesi yarida kaldi - "
                                     "pozisyon listesi dogrulanamadi, orphan tarama "
                                     "baslatildi.", "ERROR", cfg.symbol)
                            new_tickets = set()
                            break
                    if unresolved_ticket:
                        pass
                    elif len(new_tickets) == 1:
                        result["position"] = int(next(iter(new_tickets)))
                    elif not new_tickets:
                        unresolved_ticket = True
                        self._orphan_scan[cfg.symbol] = {
                            "magic": base.magic,
                            "known": sorted(after_tickets),
                            "since": time.time(),
                        }
                        self._save_orphan_scan()
                        LOG.emit("Islem acildi ama pozisyon ticket'i "
                                 "cozulemedi (yeni ticket bulunamadi) - her dongude "
                                 "tekrar taranacak.",
                                 "ERROR", cfg.symbol)
                    else:
                        # More than one same-magic ticket appeared since the fill -
                        # we cannot tell which one is ours, so close all of them
                        # rather than guess.
                        gone, still = self._close_orphan_tickets(
                            new_tickets, "MicoFX cozulemeyen ticket")
                        if gone == new_tickets:
                            orphan_closed = True
                            LOG.emit(f"Islem acildi ama ticket'i "
                                     f"cozulemedi - pozisyon(lar) {sorted(gone)} "
                                     f"guvenlik icin hemen kapatildi, sinyal tekrar "
                                     f"denenecek.", "ERROR", cfg.symbol)
                        else:
                            unresolved_ticket = True
                            self._orphan_tickets |= still
                            self._save_orphan_tickets()
                            if gone:
                                LOG.emit(f"Islem acildi, ticket'i "
                                         f"cozulemedi - {sorted(gone)} kapatildi ama "
                                         f"{sorted(still)} KAPATILAMADI/KISMI - her "
                                         f"dongude tekrar kapatma denenecek.",
                                         "ERROR", cfg.symbol)
                            else:
                                LOG.emit(f"Islem acildi, ticket'i "
                                         f"cozulemedi VE {sorted(still)} "
                                         f"kapatilamadi/kismi - her dongude tekrar "
                                         f"kapatma denenecek.", "ERROR", cfg.symbol)
        if orphan_closed:
            # Treat exactly like a failed entry (the position is flat again,
            # closed a moment after opening) - not the normal successful-fill
            # path below, which would record execution/cooldown/state.signal
            # bookkeeping for a "trade" that no longer exists.
            state.note = "ticket cozulemedi - guvenlik icin kapatildi"
            state.entry_block = "ikincil_cozulemedi_kapatildi"
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
            state.pending_bar_key = (0, 0)
            return
        if unresolved_ticket:
            # Position is still open (couldn't be identified, or identified but
            # not closed) - unlike orphan_closed above this is NOT a clean
            # failed-entry retry state, so signal/cooldown are left untouched
            # rather than misreported as a normal successful fill. The
            # zero-candidate case also just wrote self._orphan_scan[cfg.symbol]
            # above - the entry-time gate at the top of this function (not
            # can_open()'s position-count check, which self._positions being
            # stale here makes unreliable) is what actually stops the next
            # poll from firing another order_send at this same symbol.
            # _scan_orphan_candidates()/manage_positions() retry the close
            # every cycle from here on.
            state.note = ("ticket cozulemedi - pozisyon acik kaldi, "
                          "otomatik tekrar denenecek")
            state.entry_block = "ikincil_cozulemedi_acik"
            return
        if not result.get("ok"):
            if result.get("invalid_stops_retry_failed"):
                try:
                    n = int(self.store.get_setting("invalid_stops_retry_fail", 0) or 0)
                    self.store.set_setting("invalid_stops_retry_fail", n + 1)
                    LOG.emit(f"INVALID_STOPS ikinci ret (sayac {n + 1})", "WARN", cfg.symbol)
                except Exception:
                    pass
            state.note = result.get("error", "emir hatasi")
            state.entry_block = "emir_hatasi"
            # Park on any verified-flat link refusal, not only TRADE_RETCODE_*
            # in AMBIGUOUS_RETCODES. order_send None / IPC last_error codes
            # (-10001 etc.) are outside that set but took the same verifier
            # path - without verified_unfilled they would still hammer every
            # poll. Retcode check kept as belt-and-suspenders.
            if result.get("verified_unfilled") or result.get("retcode") in AMBIGUOUS_RETCODES:
                self._link_backoff[base.symbol] = time.time() + LINK_BACKOFF_SEC
            if result.get("verified_unfilled"):
                # Remember what "nothing landed" was counted against, so the
                # retry can tell a late fill from a genuine miss.
                self._unfilled_probe[cfg.symbol] = (
                    (int(state.last_bar or 0), int(state.pending_bar_key[1] or 0)),
                    sum(1 for p in self._positions if p["magic"] == cfg.magic),
                )
            # Verified-flat is the gate working: book readable, nothing filled,
            # symbol parked. WARN so fault scans do not treat a successful
            # refuse as a live Error (same reason pending-drop went WARN).
            # Still ERROR when the book itself is unreadable (ambiguous).
            if result.get("verified_unfilled"):
                LOG.emit(result.get("error", "emir hatasi"), "WARN", cfg.symbol)
            else:
                LOG.emit(result.get("error", "emir hatasi"), "ERROR", cfg.symbol)
            if result.get("ambiguous"):
                # open_market() could not establish whether the order filled
                # (timeout plus an unreadable position book, or several new
                # same-magic tickets). Retrying on the next poll is the one
                # thing that must not happen here: if it did fill, the retry
                # doubles the position. Drop the whole signal chain so nothing
                # re-offers this entry before a new bar closes, by which point
                # _reload_positions() has seen whatever is really open and
                # can_open()'s max_positions gate applies normally again.
                state.signal = ""
                state.signal_source = ""
                state.primary_signal = ""
                state.pending_bar_key = (0, 0)
                state.note = "emir sonucu belirsiz - tekrar denenmeyecek, MT5'i kontrol edin"
                state.entry_block = "emir_belirsiz"
                return
            if result.get("retcode") in NON_RETRYABLE_RETCODES:
                # This reject will not clear up before the bar rolls over -
                # keeping pending_bar_key set just re-offers the same doomed
                # order_send every poll until then. Drop the whole signal
                # chain, same as the session/market-closed gates do.
                state.signal = ""
                state.signal_source = ""
                state.primary_signal = ""
                state.pending_bar_key = (0, 0)
            # Key is set on the branch above; restated here so this exit carries
            # it locally and the coverage guard can stay strict.
            state.entry_block = state.entry_block or "emir_hatasi"
            return

        if result.get("partial_fill"):
            LOG.emit(f"Kismi dolum: {result['volume']:g} lot (istenen {lot:g} lot) - "
                     f"kalan hacim iptal edildi, tekrar denenmedi.", "WARN", cfg.symbol)

        if not result.get("sl_tp_reanchored", True):
            # The fill itself is fine - this is the position running the
            # pre-fill-tick SL/TP (or, rarer, no resolvable position ticket at
            # all) instead of the fill-anchored one. Not silent: the next
            # trail check still corrects it once profit crosses trail_start,
            # but a loss before then would be sized off the stale stop.
            LOG.emit("Fill sonrasi SL/TP yeniden ayarlanamadi - eski (tick bazli) "
                     "seviyede kaldi.", "WARN", cfg.symbol)

        # Entry slippage, measured exactly: ``entry`` is the tick the order was
        # built from, ``result["price"]`` is what the broker actually gave us.
        info = self.client.info(cfg.symbol) or {}
        self.execution.record(
            cfg.symbol, "entry", result.get("requested", entry), result["price"],
            deal_is_buy=(side == "buy"), risk_dist=sl_dist,
            point=float(info.get("point", 0.0) or 0.0), volume=result["volume"],
            money_per_price=self.client.money_per_price_unit(cfg.symbol, result["volume"]),
        )

        state.cooldown_until = time.time() + _cooldown_for(cfg)
        self._save_cooldown(cfg.symbol, state.cooldown_until)
        self._mark_bar_filled(cfg.symbol, state.signal_source, state.last_bar)
        state.signal = ""
        state.signal_source = ""
        state.primary_signal = ""
        state.note = "islem acildi"
        state.entry_block = "acildi"
        # The ticket, so an entry can be matched to its own close later. The
        # close line has carried it all along; this one did not, and matching
        # them meant FIFO by symbol - which silently pairs the wrong two the
        # moment a symbol holds more than one position. Every attempt at
        # per-trade loss forensics today ran into it: realised stop distance
        # came out at 1.29x intended, and the number was an artefact of the
        # pairing, not of the stops. 0 means open_market could not resolve it
        # (ambiguous multi-fill) and is written as such rather than omitted,
        # because a missing field and an unresolved one are different facts.
        ticket = int(result.get("position", 0) or 0)
        fill_px = _fill_log_price(result, float(result.get("requested", entry) or entry))
        # Not ``note``: that name already holds the lot-sizing explanation this
        # method logs a few lines down. Rebinding it printed a bound method in
        # place of "risk %1.09 -> 0.515" on every fill.
        note_fill = getattr(self.execution, "note_fill", None)
        if ticket and callable(note_fill):
            # Fill-time facts the close path cannot reconstruct: the signal
            # bar is already consumed, and spread/ADX on state will move.
            # Broker clock, same stamps as deal.time, so held_min is a
            # duration not a UTC-vs-wall-clock gap.
            sig_close = None
            if state.bars is not None and len(state.bars.close):
                sig_close = float(state.bars.close[-1])
            point = float(info.get("point") or 0)
            fill_vs = None
            if sig_close is not None:
                # Positive = worse for the account, same sign as execution.
                fill_vs = (fill_px - sig_close) if side == "buy" else (sig_close - fill_px)
            atr_pct = None
            if state.atr and sig_close:
                atr_pct = float(state.atr) / sig_close
            note_fill(
                ticket,
                signal_bar_time=int(state.last_bar or 0) or None,
                fill_time=self._broker_now_int(),
                fill_price=fill_px,
                signal_close=sig_close,
                fill_vs_signal_close=fill_vs,
                fill_vs_signal_close_pts=(fill_vs / point if point and fill_vs is not None else None),
                fill_vs_signal_close_r=(fill_vs / sl_dist if sl_dist and fill_vs is not None else None),
                spread_atr=float(state.spread_atr or 0),
                adx=state.adx,
                atr_pct=atr_pct,
                tf_seconds=timeframe_seconds(cfg.timeframe),
                side=side,
                entry=fill_px,
                risk_dist=float(sl_dist or 0),
                original_sl=_fill_original_sl(side, fill_px, sl_dist,
                                                float(result.get("sl") or 0)),
            )
        cost_bit = ""
        vol = float(result["volume"])
        mpu = self.client.money_per_price_unit(cfg.symbol, vol)
        r_value = float(sl_dist or 0.0) * mpu
        if r_value > 0:
            cost = cfg.commission_per_lot * vol
            cost += float((tick or {}).get("spread") or 0.0) * mpu
            cost_bit = f" maliyet %{cost / r_value * 100.0:.1f}"
        log_sl = live_stop_level(float(result.get("sl") or 0))
        if log_sl <= 0:
            log_sl = _fill_original_sl(side, fill_px, sl_dist,
                                       float(result.get("sl") or 0)) or 0.0
        LOG.emit(
            f"#{ticket} {side.upper()} {vol:g} lot @ {_fill_log_price(result, fill_px):.5f} "
            f"SL={log_sl:.5f} TP={float(result.get('tp') or 0):.5f} magic={cfg.magic}"
            f"{cost_bit} | lot: {note}",
            "TRADE", cfg.symbol,
        )

    def _save_orphan_tickets(self) -> None:
        # Historical key name; the scan is for any unresolved fill, not a
        # retired secondary leg. Renaming would drop old rows on restart.
        self.store.set_setting("secondary_orphan_tickets", sorted(self._orphan_tickets))

    def _save_orphan_scan(self) -> None:
        # Historical key name; see _save_orphan_tickets.
        self.store.set_setting("secondary_orphan_scan", self._orphan_scan)

    def _close_orphan_tickets(self, tickets: set[int], comment: str) -> tuple[set[int], set[int]]:
        """Safety-close orphan tickets; re-diff the live book before trusting gone.

        ``close_position`` returns True for ``TRADE_RETCODE_DONE_PARTIAL`` too
        (remaining volume still open on the same ticket). Weekend flatten
        keeps sticky retries until the ticket leaves ``self._positions``;
        orphan paths used to treat True as fully flat and drop tracking.
        Returns ``(gone, still_open)``. On reload/disconnect failure every
        ticket is treated as still open (fail closed - keep tracking).
        """
        if not tickets:
            return set(), set()
        for ticket in tickets:
            self.client.close_position(
                ticket, self.store.system.slippage_points, comment)
        if not self._reload_positions():
            return set(), set(tickets)
        live = {p["ticket"] for p in self._positions}
        gone = {t for t in tickets if t not in live}
        return gone, tickets - gone

    def _scan_orphan_candidates(self) -> None:
        """Re-diff symbols whose secondary fill produced zero candidates at
        entry time. Broker replication lag can mean ``positions()`` genuinely
        had not caught up yet - this keeps checking every cycle instead of
        writing the position off as untraceable after one failed diff.

        New entries on the symbol stay refused (see ``_try_entry``) for as
        long as its scan entry exists at all, ``abandoned`` or not - past
        ``stale_after`` this stops actively expecting the ticket to show up
        (it is unlikely to now) and starts counting down a short grace
        window instead, but the entry itself is only ever cleared by finding
        the ticket (closed on sight) or by the grace window finally expiring,
        never by giving up on the wait alone. A same-magic ticket that turns
        up during that grace window is still closed rather than left to run
        under the wrong strategy's exits.

        Locked against seed-overwrite / DELETE magic-reuse paths that clear
        these maps under the same ``entry_lock`` - otherwise a last-look or
        failed close could re-persist orphan state against freshly seeded
        default magics (TOCTOU).
        """
        with self.entry_lock:
            self._scan_orphan_candidates_locked()

    def _scan_orphan_candidates_locked(self) -> None:
        if not self._orphan_scan:
            return
        stale_after = 900.0    # generous - broker lag, not a retry budget
        # Entry stays blocked (see _try_entry) for this whole window too -
        # abandoning only stops the active re-diff every cycle (below), it is
        # NOT a green light for new trades on this magic. Only a full drop
        # (ticket found+closed, or this grace window also expiring) actually
        # clears self._orphan_scan and re-opens entry.
        abandon_grace = 300.0
        changed = False
        for symbol in list(self._orphan_scan):
            entry = self._orphan_scan[symbol]
            magic = int(entry.get("magic", -1))
            known = {int(t) for t in entry.get("known", [])}
            current = {p["ticket"] for p in self._positions if p["magic"] == magic}
            new_tickets = current - known
            if new_tickets:
                gone, still = self._close_orphan_tickets(
                    new_tickets, "MicoFX gecikmis ikincil ticket")
                if gone:
                    LOG.emit(f"Gecikmis ikincil ticket bulundu ve kapatildi: {sorted(gone)}.",
                             "WARN", symbol)
                if still:
                    self._orphan_tickets |= still
                    self._save_orphan_tickets()
                    LOG.emit(f"Gecikmis ikincil ticket bulundu ama kapatilamadi/kismi: "
                             f"{sorted(still)} - her dongude tekrar denenecek.",
                             "ERROR", symbol)
                del self._orphan_scan[symbol]
                changed = True
                continue
            if entry.get("abandoned"):
                if time.time() - float(entry.get("abandoned_at", 0.0)) > abandon_grace:
                    # Final look with a fresh positions() call (not the
                    # possibly-stale self._positions snapshot this cycle
                    # started with) before giving up for good - closes the
                    # gap between "last checked" and "actually dropping",
                    # since after this the symbol is untracked and a ticket
                    # that shows up even one broker tick later would run
                    # under the primary's exit params instead.
                    last_positions = self.client.positions()
                    if not self.client.connected:
                        # positions_get failed mid-call → [] is not "flat".
                        # Dropping the scan here would free the magic while a
                        # live fill may still exist (same fail-open class the
                        # web _positions() helper closes). Keep watching.
                        LOG.emit(
                            f"{symbol}: son sans orphan taramasi ertelendi - "
                            f"MT5 pozisyon listesi dogrulanamadi.", "WARN", symbol)
                        continue
                    last_look = {p["ticket"] for p in last_positions if p["magic"] == magic}
                    last_new = last_look - known
                    if last_new:
                        gone, still = self._close_orphan_tickets(
                            last_new, "MicoFX gecikmis ikincil ticket (son sans)")
                        if gone:
                            LOG.emit(f"Son sans taramasinda ikincil ticket bulundu ve "
                                     f"kapatildi: {sorted(gone)}.", "WARN", symbol)
                        if still:
                            self._orphan_tickets |= still
                            self._save_orphan_tickets()
                            LOG.emit(f"Son sans taramasinda ticket bulundu ama "
                                     f"kapatilamadi/kismi: {sorted(still)} - her dongude "
                                     f"tekrar denenecek.", "ERROR", symbol)
                    else:
                        LOG.emit("Gecikmis ikincil ticket taramasi (ek bekleme suresi de doldu) - "
                                 "pozisyon hicbir zaman gorunmedi, tarama tamamen birakiliyor, "
                                 "elle kontrol edin.", "ERROR", symbol)
                    del self._orphan_scan[symbol]
                    changed = True
                continue
            if time.time() - float(entry.get("since", 0.0)) > stale_after:
                entry["abandoned"] = True
                entry["abandoned_at"] = time.time()
                changed = True
                LOG.emit(f"Gecikmis ikincil ticket taramasi {stale_after:g}sn zaman asimina "
                         f"ugradi - pozisyon hicbir zaman gorunmedi, {symbol} icin giris hala "
                         f"engelli, gec beliren bir ticket'i kapatmak icin {abandon_grace:g}sn "
                         f"daha izlenecek, sonra tarama tamamen birakilacak.", "ERROR", symbol)
        if changed:
            self._save_orphan_scan()

    # ---------------------------------------------------- position management

    def manage_positions(self, server_now: float | None) -> None:
        if not self.client.connected:
            # Caller should have bailed already; never prune tags / exposure
            # from an unverified empty book.
            return
        by_magic = {c.magic: c for c in list(self.store.symbols.values())}
        live = {p["ticket"] for p in self._positions}
        self._unmanaged_seen &= live
        self._stopless_seen &= live
        # The prune is held under entry_lock because the seed-overwrite and
        # DELETE magic-reuse paths clear these same maps under it (see
        # web/app.py's seed handler and _scan_orphan_candidates). Pruning
        # against ``live`` - a snapshot taken from this cycle's position read -
        # while a clear runs concurrently could otherwise re-persist tag state
        # the clear had just dropped, against freshly seeded default magics.
        # Only the prune is inside: the management loop below sends broker
        # calls (modify/close) that can block for seconds, and holding the
        # entry lock across those would stall every web write behind them.
        with self.entry_lock:
            if self._weekend_pending - live:
                self._weekend_pending &= live
                self.store.set_setting("weekend_pending_tickets", sorted(self._weekend_pending))
            if self._force_flat_pending - live:
                self._force_flat_pending &= live
                self.store.set_setting("force_flat_pending_tickets",
                                       sorted(self._force_flat_pending))
            if self._sec_tickets - live:
                self._sec_tickets &= live
                self.store.set_setting("secondary_tickets", sorted(self._sec_tickets))
            if self._orphan_tickets - live:
                # Gone from the broker already (closed by a previous cycle's
                # retry, or manually) - stop chasing it.
                self._orphan_tickets &= live
                self._save_orphan_tickets()
            done = getattr(self, "_scale_out_done", None)
            if isinstance(done, set) and done - live:
                # One-shot overlay: a closed ticket must not occupy the set
                # forever, or the blob grows without bound and a reused
                # ticket id would never scale out again.
                self._scale_out_done = done & live
                self.store.set_setting("scale_out_done", sorted(self._scale_out_done))
        if not getattr(self, "_open_resume_logged", False):
            # First connected manage_positions is a trusted book (_cycle
            # already bailed if positions() flipped connected). Latch even
            # when flat so a fill hours later is not stamped "Restart".
            claimed = [
                f"#{int(p['ticket'])} {by_magic[p['magic']].symbol}"
                for p in self._positions
                if p.get("magic") in by_magic
            ]
            self._open_resume_logged = True
            if claimed:
                LOG.emit(
                    "Restart: magic ile "
                    f"{len(claimed)} acik ticket devam ediyor: "
                    + ", ".join(claimed),
                    "WARN")
        for pos in self._positions:
            if pos["ticket"] in self._orphan_tickets:
                # An unresolved secondary fill from a prior cycle - never let it
                # fall through to normal trail/BE/primary-exit management while
                # it is still waiting on a close retry; keep retrying instead.
                # Sticky like weekend_pending: close_position True includes
                # DONE_PARTIAL, so do NOT discard tracking on True - the prune
                # against the live book at the top of the next cycle is what
                # confirms the ticket is actually gone.
                fill: dict[str, Any] = {}
                if self._close_tracked(pos, "MicoFX cozulemeyen ikincil ticket",
                                       "exit", fill=fill):
                    filled = float(fill.get("volume", pos["volume"]))
                    if filled + 1e-9 >= float(pos["volume"]):
                        LOG.emit(f"Cozulemeyen ikincil ticket #{pos['ticket']} kapatildi.",
                                 "TRADE")
                    else:
                        LOG.emit(f"Cozulemeyen ikincil ticket #{pos['ticket']} kismen "
                                 f"kapatildi ({filled:g}/{pos['volume']:g} lot), "
                                 f"kalan tekrar denenecek.", "WARN")
                continue
            cfg = by_magic.get(pos["magic"])
            if cfg is None:
                # Deliberately not closed: without a config we cannot say what
                # this position is for, and closing something we cannot
                # identify is worse than leaving it on its broker-side stop.
                # What we can do is stop it being invisible.
                ticket = int(pos["ticket"])
                if ticket not in self._unmanaged_seen:
                    self._unmanaged_seen.add(ticket)
                    LOG.emit(f"#{ticket} ({pos.get('symbol', '?')}, magic "
                             f"{pos['magic']}) kitapta karsiligi olmayan bir "
                             f"magic altinda acik - MicoFX bu pozisyonu "
                             f"yonetmiyor (trail/stop yok), yalnizca brokerin "
                             f"stopu gecerli.", "WARN")
                continue
            state = self.states.get(cfg.symbol)
            atr = state.atr if state else 0.0

            ticket_no = int(pos["ticket"])
            if live_stop_level(pos.get("sl")) <= 0:
                if self._repair_stopless_stop(cfg, pos, atr):
                    LOG.emit(f"#{ticket_no} STOPSUZ pozisyona stop eklendi "
                             f"@ {float(pos['sl']):.5f}",
                             "WARN", cfg.symbol)
                    self._stopless_seen.discard(ticket_no)
                elif ticket_no not in self._stopless_seen:
                    self._stopless_seen.add(ticket_no)
                    LOG.emit(f"#{ticket_no} STOPSUZ acik - bu sistemde tek cikis "
                             f"stoptur, trail ise yalnizca kardayken calisir, "
                             f"yani zararda koruma yok. MT5'i elle kontrol edin.",
                             "ERROR", cfg.symbol)
            elif ticket_no in self._stopless_seen:
                # A stop turned up again (restored by hand, or the trail set
                # one once the trade moved into profit) - re-arm, so a second
                # disappearance is reported instead of being muted.
                self._stopless_seen.discard(ticket_no)

            # weekend_closed() already gated new entries; it never touched a
            # position that was already open going into the weekend. Crypto
            # is exempt (weekend_closed() itself returns False for it).
            if (server_now is not None
                    and sessions.weekend_closed(cfg, server_now)
                    and pos["ticket"] not in self._weekend_pending):
                self._weekend_pending.add(pos["ticket"])
                self.store.set_setting("weekend_pending_tickets", sorted(self._weekend_pending))
            if pos["ticket"] in self._weekend_pending:
                # Sticky: once flagged during Sat/Sun, keep retrying every
                # cycle - including past the Monday boundary - until the
                # close actually lands, instead of a failed weekend attempt
                # silently falling through to normal trailing the moment the
                # calendar flips back to a weekday. Deliberately NOT removed
                # from _weekend_pending here on a True return -
                # close_position() reports TRADE_RETCODE_DONE_PARTIAL as
                # success too (remaining volume genuinely still open on the
                # same ticket), so "the call succeeded" does not mean "fully
                # flat". The prune at the top of this method (against the
                # freshly re-queried self._positions) is what actually
                # confirms the ticket is gone, and clears it correctly either
                # way - full close this pass, or a later one after retries.
                weekend_fill: dict[str, Any] = {}
                if self._close_tracked(pos, "MicoFX hafta sonu", "exit", fill=weekend_fill):
                    filled = float(weekend_fill.get("volume", pos["volume"]))
                    if filled + 1e-9 >= float(pos["volume"]):
                        LOG.emit("Hafta sonu: pozisyon kapatildi.", "TRADE", cfg.symbol)
                    else:
                        LOG.emit(f"Hafta sonu: pozisyon kismen kapatildi ({filled:g}/"
                                 f"{pos['volume']:g} lot), kalan tekrar denenecek.",
                                 "WARN", cfg.symbol)
                continue
            # Same "a loss limit should stop the loss, not just further
            # entries" reasoning as the account-wide daily guard above -
            # _symbol_daily_halt() only ever blocked new entries for THIS
            # symbol, so one instrument could keep bleeding floating loss
            # past its own configured cap while every other symbol traded on.
            if self._symbol_daily_halt(cfg):
                fill = {}
                if self._close_tracked(pos, "MicoFX sembol gunluk zarar limiti",
                                       "exit", fill=fill):
                    filled = float(fill.get("volume", pos["volume"]))
                    if filled + 1e-9 >= float(pos["volume"]):
                        LOG.emit("Sembol gunluk zarar limiti: pozisyon kapatildi.",
                                 "TRADE", cfg.symbol)
                    else:
                        LOG.emit(f"Sembol gunluk zarar limiti: kismen kapatildi "
                                 f"({filled:g}/{pos['volume']:g} lot), kalan tekrar "
                                 f"denenecek.", "WARN", cfg.symbol)
                continue
            # Flag session / day-end flatten into a sticky set BEFORE the
            # window can expire - DONE_PARTIAL True must not fall through to
            # trail once should_flatten/day_end_close flips False.
            if server_now is not None and (
                    sessions.should_flatten(cfg, server_now, self.store.system.trade_all_hours)
                    or sessions.day_end_close(server_now, self.store.system.day_end_flatten_min)):
                if pos["ticket"] not in self._force_flat_pending:
                    self._force_flat_pending.add(pos["ticket"])
                    self.store.set_setting("force_flat_pending_tickets",
                                           sorted(self._force_flat_pending))
            if pos["ticket"] in self._force_flat_pending:
                fill = {}
                if self._close_tracked(pos, "MicoFX zorunlu flatten", "exit", fill=fill):
                    filled = float(fill.get("volume", pos["volume"]))
                    if filled + 1e-9 >= float(pos["volume"]):
                        LOG.emit("Zorunlu flatten: pozisyon kapatildi.", "TRADE", cfg.symbol)
                    else:
                        LOG.emit(f"Zorunlu flatten: kismen kapatildi "
                                 f"({filled:g}/{pos['volume']:g} lot), kalan tekrar "
                                 f"denenecek.", "WARN", cfg.symbol)
                continue

            # No time stop and no stale-loss exit. Both used to close a trade
            # purely because the clock ran out, which is how a system that is
            # supposed to ride trends ends up cutting exactly the ones worth
            # holding. A position leaves only through its stop - hard at first,
            # trailing once the move pays for it - or through the session /
            # day-end / daily-loss flatten above, which are calendar and risk
            # limits rather than opinions about the trade.

            if atr > 0:
                bars = None
                last_bar = 0
                if state is not None:
                    bars = state.bars
                    last_bar = state.last_bar
                ticket = pos["ticket"]
                # Trail/BE/partial need a closed-bar pin. Signal ``last_bar``
                # can stay 0 after restart/history gap while ``state.bars``
                # already holds closed candles — use that pin so the ticket
                # is not left on the broker hard stop alone.
                if not last_bar and bars is not None:
                    try:
                        last_bar = int(getattr(bars, "last_closed_time", 0) or 0)
                    except (TypeError, ValueError):
                        last_bar = 0
                if last_bar:
                    # Always re-run overlay_stop on this closed bar. The level
                    # does not move until last_bar does, so a same-target retry
                    # is a no-op (min_step). What used to skip here was a BE /
                    # harvest PATCH after overlay_stop had returned None: the
                    # bar was marked settled and the new overlay sat idle until
                    # the next candle, which is the opposite of "overlays apply
                    # to open tickets". False still means "ask again this bar"
                    # because the live quote, not the close, blocked placement.
                    self._update_stop(cfg, pos, atr, bars)
                else:
                    # No closed-bar pin at all: trail/BE/partial/harvest skip
                    # and the ticket runs on its broker stop alone. Reachable
                    # after a restart into a history gap. Silence made an
                    # unmanaged position look like a managed one.
                    self._note_unmanaged_ticket(cfg, pos)
                self._maybe_scale_out(cfg, pos, atr, bars)

    # ------------------------------------------------------ execution quality

    def _reap_execution(self) -> None:
        """Score any position that closed since the last cycle.

        Only touches MT5 when something actually disappeared, so the normal
        cycle costs nothing. A close the engine itself sent was already recorded
        against its own requested tick, so ``reap`` measures only the fills the
        broker generated (server-side stop or target) and ``forget`` drops the
        rest.
        """
        try:
            self._reconcile_untracked_closes()
            gone = self.execution.track(self._positions)
            if not gone:
                return
            # Off the broker's clock, not this machine's. Deal timestamps are
            # naive epochs holding the broker's wall-clock reading, so a true
            # epoch handed to deals_since() lands the window three hours out on
            # this GMT+3 server: measured 15.08, asking for two hours returned a
            # 3.2-hour span. Wider is not free here - reap() matches a closed
            # position against these deals, and the extra hours are candidates
            # it has to discriminate. broker_now() is the same clock the deals
            # are stamped on, so the subtraction cancels the offset; 0.0 means
            # no tick has been read yet and the old behaviour stands.
            broker_now = self.client.broker_now()
            since = (broker_now if broker_now > 0.0 else time.time()) - 7200
            deals = self.client.deals_since(since)
            for report in self.execution.reap(gone, deals, self.client):
                self._log_broker_exit(report)
            self.execution.forget(gone)
        except Exception as exc:                  # never let diagnostics stop the loop
            LOG.emit(f"Gerceklesme olcumu hatasi: {exc}", "WARN")

    def _reconcile_untracked_closes(self) -> None:
        """Log/otopsi broker closes that finished while this process was down.

        ``execution.track`` only notices tickets that left ``_open``. After a
        restart that dict is empty, so an SL that filled in the shutdown window
        (XAU #324655544 04.09 01:24) never becomes ``gone`` — balance moves,
        no TRADE line, no autopsy. One-shot scan of recent OUT deals for our
        magics fills the gap.
        """
        if getattr(self, "_untracked_closes_done", False):
            return
        if not self.client.connected:
            return
        self._untracked_closes_done = True
        magics = {c.magic for c in list(self.store.symbols.values())}
        if not magics:
            return
        live = {int(p["ticket"]) for p in self._positions}
        seen: set[int] = set(live)
        for row in getattr(self, "_trade_autopsies", []) or []:
            if not isinstance(row, dict):
                continue
            try:
                t = int(row.get("ticket") or 0)
            except (TypeError, ValueError):
                continue
            if t:
                seen.add(t)
        broker_now = self.client.broker_now()
        since = (broker_now if broker_now > 0.0 else time.time()) - 7200.0
        try:
            deals = self.client.deals_since(since)
        except Exception as exc:
            LOG.emit(f"restart arasi kapanis taramasi basarisiz: {exc}", "WARN")
            return
        closers: dict[int, list[dict[str, Any]]] = {}
        net: dict[int, float] = {}
        for deal in deals or []:
            try:
                magic = int(deal.get("magic") or 0)
                reason = int(deal.get("reason", -1))
                pos = int(deal.get("position") or 0)
            except (TypeError, ValueError):
                continue
            if magic not in magics or pos <= 0:
                continue
            net[pos] = (net.get(pos, 0.0)
                        + float(deal.get("profit", 0.0) or 0.0)
                        + float(deal.get("commission", 0.0) or 0.0)
                        + float(deal.get("swap", 0.0) or 0.0))
            if reason not in execution._CLOSED_ELSEWHERE:
                continue
            closers.setdefault(pos, []).append(deal)
        for pos, chunks in closers.items():
            if pos in seen:
                continue
            deal = chunks[-1]
            volume = sum(float(d.get("volume", 0.0) or 0.0) for d in chunks)
            if volume > 0:
                price = sum(
                    float(d.get("price", 0.0) or 0.0)
                    * float(d.get("volume", 0.0) or 0.0)
                    for d in chunks) / volume
            else:
                price = float(deal.get("price") or 0.0)
            report = {
                "ticket": pos,
                "symbol": str(deal.get("symbol") or ""),
                "magic": int(deal.get("magic") or 0),
                "reason": int(deal.get("reason") or 0),
                "label": execution._REASON_LABEL.get(
                    int(deal.get("reason") or 0), "broker"),
                "price": price,
                "volume": volume,
                "profit": round(net.get(pos, float(deal.get("profit") or 0.0)), 2),
                "time": int(deal.get("time") or 0),
                "book": {},
                "restart_gap": True,
            }
            self._log_broker_exit(report)

    def _restore_cooldown(self, state: SymbolState) -> None:
        """Carry a still-running post-fill cooldown across a restart.

        The cooldown is what stops one bar's signal being filled twice. It only
        ever lived in SymbolState, which is rebuilt empty on every start - so a
        restart inside the window let the same bar's signal, recomputed from
        the same still-last-closed bar, open a second position seconds after
        the first. Seen repeatedly in the live log:

            16:00:03 [US30] BUY 0.2 @ 53994.90 SL=53974.20
            16:01:33 Yeniden baslatma istegi alindi.
            16:01:40 [US30] BUY 0.2 @ 53997.10 SL=53976.40
            16:09:42 [US30] Stop ile kapandi kar=-4.14
            16:09:42 [US30] Stop ile kapandi kar=-4.14

        One signal, two positions, both stopped out - the loss doubled. The
        broker-side position cap could not catch it (max_positions is
        deliberately above 1) and every other guard the entry path relies on is
        equally in-memory.

        Deliberately not persisted for anything else the state holds: bars,
        ATR and signals are all recomputed from the broker within a cycle, and
        a stale copy of those would be worse than no copy.
        """
        until = float(self._cooldowns.get(state.symbol, 0.0) or 0.0)
        if until > time.time():
            state.cooldown_until = until

    def _mark_bar_filled(self, symbol: str, source: str, bar: int) -> None:
        """Record that this bar's signal has been taken, so a restart cannot
        take it again. Same order-path safety as _save_cooldown: a failure here
        must never cost the TRADE line of a fill that already happened.
        """
        try:
            if not bar:
                return
            current = getattr(self, "_filled_bars", None)
            if not isinstance(current, dict):
                current = {}
            # Per LEG. A single slot per symbol let a secondary fill erase the
            # primary's record (and the reverse), leaving an already-taken bar
            # unguarded against the restart this whole record exists for.
            legs = current.get(symbol)
            if not isinstance(legs, dict):
                legs = {}
            legs[str(source)] = int(bar)
            current[symbol] = legs
            # Bounded: only symbols still in the portfolio are worth keeping.
            live = set(self.store.symbols)
            self._filled_bars = {s: v for s, v in current.items() if s in live}
            self.store.set_setting("filled_bars", self._filled_bars)
        except Exception as exc:
            LOG.emit(f"Dolum bar kaydi yazilamadi: {exc}", "WARN", symbol)

    def _save_cooldown(self, symbol: str, until: float) -> None:
        # Runs on the order path, immediately after a fill and before the TRADE
        # line is written - so it must not be able to take that log line, or
        # the rest of the cycle, down with it. Losing one cooldown write costs
        # a possible duplicate entry; raising here would cost the audit trail
        # of a fill that already happened.
        try:
            now = time.time()
            # Drop the expired ones on the way past so the blob cannot grow
            # without bound as symbols come and go.
            current = getattr(self, "_cooldowns", None)
            if not isinstance(current, dict):
                current = {}
            self._cooldowns = {s: t for s, t in current.items() if t > now}
            self._cooldowns[symbol] = float(until)
            self.store.set_setting("entry_cooldowns", self._cooldowns)
        except Exception as exc:
            LOG.emit(f"Cooldown kaydedilemedi: {exc}", "WARN", symbol)

    def _log_broker_exit(self, report: dict[str, Any]) -> None:
        """Put one broker-generated exit in the log.

        Restricted to this portfolio's magics: the account may carry positions
        this bot never opened (manual trades, another EA), and reporting their
        stops as MicoFX exits would make the log lie about what the bot did.
        A margin stop-out is a WARN, not a TRADE - it means the account ran out
        of margin, which is an account-level event, not a strategy exit.
        """
        magics = {c.magic for c in list(self.store.symbols.values())}
        if report["magic"] not in magics:
            return
        self._autopsy_safe(
            book=report.get("book") or {},
            ticket=report.get("ticket"),
            symbol=report.get("symbol"),
            exit_price=self._autopsy_float(report.get("price")),
            exit_time=report.get("time"),
            profit=self._autopsy_float(report.get("profit")),
            reason_code=report.get("reason"),
            comment="",
        )
        profit = report["profit"]
        gap = "Restart arasi " if report.get("restart_gap") else ""
        detail = (f"{gap}{report['label'].capitalize()} ile kapandi #{report['ticket']} "
                  f"@ {report['price']:g} ({report['volume']:g} lot) kar={profit:.2f}")
        if report["reason"] == execution.DEAL_REASON_SO:
            LOG.emit(detail, "WARN", report["symbol"])
        else:
            LOG.emit(detail, "TRADE", report["symbol"])

    def _apply_pending_exits(self) -> None:
        """Land apply() patches that were held back while a position was open.

        Same-family exit/risk lives in ``cfg.pending_exit_patch``. A family/TF
        swap lives in ``cfg.pending_primary_patch`` (the winner used to be
        dropped because apply() returned an error). Both land the moment this
        magic is next seen flat. Runs every cycle - cheap (in-memory dict
        lookups against ``self._positions``, already refreshed this cycle)
        and self-correcting if a cycle is missed.
        Leftover ``pending_secondary_exit_patch`` is ignored (A3.3); the
        field stays on the model until A4.
        """
        if not self._positions:
            open_magics: set[int] = set()
        else:
            open_magics = {p["magic"] for p in self._positions}
        # A zero-candidate orphan-scan window (H1) is genuinely invisible to
        # self._positions - that is the entire reason it exists - so without
        # this, this magic reads as flat here even though a fill may still
        # turn up, and the held-back exit/risk patch would land on a position
        # that was never actually confirmed closed. Same risk class
        # Optimizer.apply() already guards for on the write side; this is the
        # corresponding read-side gap on the "did it ever actually go flat"
        # check.
        for entry in self._orphan_scan.values():
            magic = int(entry.get("magic", -1))
            open_magics.add(magic)
        # Same lock optimizer.apply()/web PATCH hold across their own
        # open-position check + write - without it, a concurrent apply() on
        # the web thread could land a fresh patch (correctly clearing
        # pending_exit_patch) in the gap between this method reading the OLD
        # cfg snapshot and writing it, and this call's stale pending patch
        # would silently overwrite that fresh one right back.
        with self.entry_lock:
            for cfg in list(self.store.symbols.values()):
                if cfg.magic in open_magics:
                    continue
                if cfg.pending_primary_patch:
                    self._land_pending_primary(cfg)
                    symbols = self.store.symbols
                    cfg = (symbols.get(cfg.symbol) if hasattr(symbols, "get") else None) or cfg
                if cfg.pending_exit_patch and cfg.magic not in open_magics:
                    pending = dict(cfg.pending_exit_patch)
                    # Re-validate at the moment of landing, not only where the
                    # patch was staged. Optimizer.apply() checks these bounds
                    # now, but a pending patch is a value that sat in the DB
                    # across an arbitrary gap - it can predate that check, or
                    # arrive from a restored backup or a hand-edited row. The
                    # field is API-blocked (_INTERNAL_ONLY_FIELDS), so this is
                    # not about a live request; it is about the one write path
                    # that trusts stored data verbatim.
                    bad = invalid_exit_param(pending)
                    if bad:
                        # Dropped, not retried: nothing about a stored patch
                        # changes between cycles, so keeping it would re-log
                        # and re-refuse forever. The live config keeps the
                        # values it already validated, which is the safe side.
                        updated = self.store.update_symbol(cfg.symbol, {"pending_exit_patch": {}},
                                                             source="motor bekleyen-cikis")
                        # WARN, not ERROR: dropping a stale/poisoned pending
                        # patch is the gate working as designed. ERROR made
                        # fault scans treat a successful refuse as a live
                        # failure (and the line persists on disk forever).
                        LOG.emit(f"{cfg.symbol}: bekletilen cikis parametresi gecersiz "
                                 f"({bad}) - uygulanmadi, mevcut ayar korundu.",
                                 "WARN", cfg.symbol)
                    else:
                        updated = self.store.update_symbol(cfg.symbol,
                                                           {**pending, "pending_exit_patch": {}},
                                                           source="motor bekleyen-cikis")
                        if updated is not None:
                            LOG.emit(f"{cfg.symbol}: bekletilen cikis/risk parametreleri "
                                     f"({', '.join(sorted(pending))}) artik acik pozisyon yok, "
                                     f"uygulandi.", "OPT", cfg.symbol)

    def _land_pending_primary(self, cfg: SymbolConfig) -> None:
        """Copy a queued family/TF apply onto the live row, or drop it."""
        pending = dict(cfg.pending_primary_patch or {})
        land = {k: pending[k] for k in pending if k in PRIMARY_LAND_KEYS}
        next_strat = land.get("strategy", cfg.strategy)
        next_tf = land.get("timeframe", cfg.timeframe)
        drop = {"pending_primary_patch": {}, "pending_exit_patch": {}}
        if next_strat not in STRATEGIES or next_tf not in TIMEFRAMES:
            self.store.update_symbol(cfg.symbol, drop, source="motor bekleyen-aile")
            LOG.emit(f"{cfg.symbol}: bekletilen aile/TF gecersiz "
                     f"({next_strat}/{next_tf}) - uygulanmadi, mevcut ayar korundu.",
                     "WARN", cfg.symbol)
            return
        tf_allow = self.store.opt_params().get("strategy_timeframes") if hasattr(self.store, "opt_params") else None
        allow = tf_allow if isinstance(tf_allow, dict) else None
        if not strategy_allows_timeframe(next_strat, next_tf, allow):
            self.store.update_symbol(cfg.symbol, drop, source="motor bekleyen-aile")
            LOG.emit(f"{cfg.symbol}: bekletilen {next_strat}/{next_tf} eslesmesi yasak "
                     f"- uygulanmadi, mevcut ayar korundu.",
                     "WARN", cfg.symbol)
            return
        bad = invalid_exit_param(land)
        if bad:
            self.store.update_symbol(cfg.symbol, drop, source="motor bekleyen-aile")
            LOG.emit(f"{cfg.symbol}: bekletilen aile/TF cikis parametresi gecersiz "
                     f"({bad}) - uygulanmadi, mevcut ayar korundu.",
                     "WARN", cfg.symbol)
            return
        updated = self.store.update_symbol(
            cfg.symbol, {**land, **drop}, source="motor bekleyen-aile")
        if updated is None:
            return
        LOG.emit(f"{cfg.symbol}: bekletilen {next_strat}/{next_tf} "
                 f"artik acik pozisyon yok, uygulandi.", "OPT", cfg.symbol)
        opt = getattr(getattr(self, "supervisor", None), "optimizer", None)
        if opt is not None and hasattr(opt, "_recalibrate_spread_cap"):
            opt._recalibrate_spread_cap(cfg.symbol, next_tf)

    def _close_tracked(self, pos: dict[str, Any], comment: str, leg: str,
                       volume: float | None = None, fill: dict[str, Any] | None = None) -> bool:
        """``close_position`` that also books the requested-vs-filled sample."""
        if fill is None:
            fill = {}
        ok = self.client.close_position(pos["ticket"], self.store.system.slippage_points,
                                        comment, volume=volume, fill=fill)
        if ok and fill:
            info = self.client.info(fill["symbol"]) or {}
            self.execution.record(
                fill["symbol"], leg, fill["requested"], fill["price"],
                # The closing leg trades the opposite way to the position.
                deal_is_buy=(fill["side"] == "sell"),
                risk_dist=float(fill.get("risk_dist", 0.0)),
                point=float(info.get("point", 0.0) or 0.0),
                volume=fill.get("volume", 0.0),
                money_per_price=self.client.money_per_price_unit(fill["symbol"],
                                                                 fill.get("volume", 0.0)),
            )
        if ok:
            # A partial close is not the trade ending. The remainder still
            # runs; its autopsy waits for the last exit.
            pos_vol = float(pos.get("volume") or 0)
            filled_vol = float(fill.get("volume") or 0) if fill else 0.0
            partial = volume is not None
            if pos_vol > 0 and filled_vol > 0 and filled_vol + 1e-8 < pos_vol:
                partial = True
            if not partial:
                snap = getattr(self.execution, "snapshot", None)
                book = snap(int(pos["ticket"])) if callable(snap) else None
                book = dict(book) if book else {}
                book.setdefault("symbol", pos.get("symbol"))
                book.setdefault("side", pos.get("side"))
                book.setdefault("entry", pos.get("price_open"))
                self._autopsy_safe(
                    book=book,
                    ticket=pos.get("ticket"),
                    symbol=pos.get("symbol") or book.get("symbol") or "",
                    exit_price=self._autopsy_float(fill.get("price")) if fill else None,
                    exit_time=self._broker_now_int(),
                    profit=(self._autopsy_float(fill.get("profit")) if fill else None),
                    reason_code=None,
                    comment=comment,
                )
        return ok

    def _fill_time_risk(self, pos: dict[str, Any], cfg: SymbolConfig,
                        atr: float, min_stop: float) -> float:
        """Original R unit: fill-time stop distance, not this bar's ATR.

        Paper freezes ``sl_dist`` at entry. Live used ``atr * sl_atr_mult``
        every trail poll, so an expanding ATR delayed harvest/BE/partial
        (the leftover the autopsy kept counting) and a shrinking ATR fired
        them early. Only the persisted ``open_original_sl`` blob counts —
        first-sight of a trailed stop after restart is not original risk.
        """
        fallback = max(float(atr) * float(cfg.sl_atr_mult), float(min_stop))
        try:
            ticket = int(pos.get("ticket") or 0)
        except (TypeError, ValueError):
            return fallback
        if not ticket:
            return fallback
        originals = getattr(getattr(self, "execution", None), "_originals", None)
        if not isinstance(originals, dict):
            return fallback
        saved = originals.get(ticket)
        if not isinstance(saved, dict):
            return fallback
        try:
            rd = float(saved.get("risk_dist") or 0.0)
        except (TypeError, ValueError):
            return fallback
        return rd if rd > 0 else fallback

    def _repair_stopless_stop(self, cfg: SymbolConfig, pos: dict[str, Any],
                              atr: float) -> bool:
        """Attach the fill-time hard stop to a broker-stopless ticket."""
        min_stop = self.client.min_stop_distance(cfg.symbol)
        atr_use = float(atr or 0.0)
        if atr_use <= 0:
            st = self.states.get(cfg.symbol)
            atr_use = float(getattr(st, "atr", 0.0) or 0.0) if st else 0.0
        sl_mult = shakeout_sl_atr_mult(
            cfg.sl_atr_mult, cfg.symbol,
            getattr(self, "_trade_autopsies", None),
            since_ts=float(getattr(cfg, "opt_updated_at", 0.0) or 0.0))
        risk_dist = self._fill_time_risk(pos, cfg, atr_use, min_stop)
        if risk_dist <= 0 and atr_use > 0:
            risk_dist = max(atr_use * sl_mult, min_stop)
        if risk_dist <= 0:
            return False
        try:
            entry = float(pos.get("price_open") or 0.0)
        except (TypeError, ValueError):
            return False
        if entry <= 0:
            return False
        is_buy = pos.get("side") == "buy"
        side = "buy" if is_buy else "sell"
        sent_sl = entry - risk_dist if is_buy else entry + risk_dist
        if sent_sl <= 0:
            return False
        ticket = int(pos["ticket"])
        attached_sl, attached_tp, ok = self.client.attach_position_sl_tp(
            cfg.symbol, ticket, side, entry, float(sent_sl), float(pos.get("tp") or 0.0))
        if not ok:
            return False
        pos["sl"] = float(attached_sl)
        note_fill = getattr(self.execution, "note_fill", None)
        if callable(note_fill):
            note_fill(
                ticket,
                original_sl=float(attached_sl),
                risk_dist=float(risk_dist),
                entry=entry,
                side=side,
            )
        return True

    def _update_stop(self, cfg: SymbolConfig, pos: dict[str, Any], atr: float,
                     bars: Any = None) -> bool:
        """Ratchet one position's stop. Returns whether this bar is settled.

        ``False`` means "ask again on the next poll, same bar": the trail level
        this bar wants is computed from the closed bar's close and does not
        move until the next bar closes, but whether it can be *placed* depends
        on the live quote, because the broker refuses a stop nearer than
        min_stop_distance to the current price. Those two facts pull apart
        whenever price retraces right after the bar closes - the update is
        legitimately earned and simply not placeable at this instant.

        The caller marks a ticket done for the bar the moment it calls here, so
        returning nothing made every such deferral permanent for the rest of
        the bar - an hour on H1 - even though the retry the min-stop branch
        below promises costs one comparison. Nothing about the *level* is
        re-derived from the live quote, so retrying does not drift from what
        the walk-forward validated; only feasibility is re-tested.
        """
        tick = self.client.tick(cfg.symbol)
        if tick is None:
            return False
        is_buy = pos["side"] == "buy"
        # Broker distance checks need the live bid/ask; BE/trail *math* must use
        # the closed bar's close - same input the walk-forward advances on. Using
        # the tick here used to ratchet stops on wicks the backtest never saw.
        live = tick["bid"] if is_buy else tick["ask"]
        if bars is not None and hasattr(bars, "close") and len(bars.close) > 0:
            # The reference bar has to have closed AFTER this position opened.
            # The entry fires on a signal from the bar that just closed, so on
            # the first pass that same bar is still the last closed one - and
            # its close is where price was BEFORE the fill, not profit the trade
            # has made. Every entry filling better than its signal bar's close
            # (which is most of a mean-reversion book: the whole point is to buy
            # the dip under it) therefore read as instantly in profit and got
            # its stop ratcheted in on the strength of it, seconds after
            # opening, to a distance far tighter than the one the position was
            # sized against. The walk-forward never modelled that: it enters at
            # bar j0's open and first consults close[j0], a bar that closes
            # after the entry by construction.
            # Absent only on a stand-in bars object; a real Bars always carries
            # it. Skipping the check then (rather than treating "unknown" as
            # "too old") keeps the failure pointing at "trail still works",
            # never at "trail silently switched off for every position".
            opened_at = int(pos.get("time", 0) or 0)
            closed_at = getattr(bars, "last_closed_time", None)
            if opened_at and closed_at is not None \
                    and int(closed_at) + timeframe_seconds(cfg.timeframe) <= opened_at:
                return True
            ref = float(bars.close[-1])
            # Everything derived from a closed bar is fixed until the next one
            # closes, so a "no" for those reasons is final for this bar.
            settled = True
        else:
            # Without bars the reference IS the live quote, so every decision
            # below can legitimately change within the same bar.
            ref = live
            settled = False
        entry = pos["price_open"]
        profit_dist = (ref - entry) if is_buy else (entry - ref)
        if profit_dist <= 0:
            return settled

        min_stop = self.client.min_stop_distance(cfg.symbol)
        current_sl = pos["sl"]
        target: float | None = None
        # Once the stop has been ratcheted past entry - by the trail, or by
        # breakeven_at_r - the live-quote min_stop clamp below must never
        # be allowed to put it back on the losing side. That clamp exists to
        # respect the broker's distance rule, not to hand back protection the
        # trade has already earned.
        #
        # The trail target is ``ref - trail_step_atr * atr``, so it is above
        # entry exactly when profit_dist exceeds ``trail_step_atr * atr`` -
        # true regardless of trail_start_atr, which only decides how early the
        # trail starts tightening the stop below entry. A config with
        # trail_start_atr <= trail_step_atr is legal and reaches trail
        # breakeven at the same point; see SymbolConfig's note.
        #
        # ``breakeven_at_r`` is the separate lock: once profit_dist reaches
        # that many original-risk units, the stop jumps to entry without
        # waiting for the trail (and without pulling a trail already past
        # entry). Zero is off. Not an OPT_FIELD.
        breakeven_locked = current_sl != 0 and (current_sl >= entry if is_buy else current_sl <= entry)
        # Same original-risk the floor below uses, and the R unit the lock
        # counts. Computed once so the threshold and the "don't trail behind
        # the hard stop" check cannot drift apart inside one call.
        # Fill-time when we have it (paper freezes sl_dist at entry);
        # current ATR is only the fallback for a pre-persist ticket.
        original_risk = self._fill_time_risk(pos, cfg, atr, min_stop)

        struct_sl = None
        if cfg.trail_mode in ("structure", "hybrid"):
            if bars is None:
                state = self.states.get(cfg.symbol)
                bars = state.bars if state else None
            if bars is not None and hasattr(bars, "low") and len(bars.low) > cfg.trail_lookback:
                lookback = max(3, cfg.trail_lookback)
                if is_buy:
                    swings = ind.swing_lows(bars.low, lookback)
                    struct_sl = swings[-1] - atr * 0.15
                else:
                    swings = ind.swing_highs(bars.high, lookback)
                    struct_sl = swings[-1] + atr * 0.15

        be_r = float(getattr(cfg, "breakeven_at_r", 0.0) or 0.0)
        harvest_at = float(getattr(cfg, "harvest_at_r", 0.0) or 0.0)
        harvest_step = float(getattr(cfg, "harvest_step_atr", 0.0) or 0.0)
        target = overlay_stop(
            is_buy=is_buy, entry=entry, ref=ref, atr=atr,
            trail_start_atr=float(cfg.trail_start_atr),
            trail_step_atr=float(cfg.trail_step_atr),
            trail_mode=str(cfg.trail_mode or "atr"),
            struct_sl=struct_sl, breakeven_at_r=be_r,
            original_risk=original_risk, be_offset=0.0,
            harvest_at_r=harvest_at, harvest_step_atr=harvest_step)

        if target is None:
            return settled

        # Respect the broker's stop distance against the *live* quote and only
        # push the stop forward.
        limit = live - min_stop if is_buy else live + min_stop
        wanted = target
        target = min(target, limit) if is_buy else max(target, limit)
        # Whether the live quote is what held this update back. When it is, the
        # refusals below are about *this instant*, not about this bar, and the
        # ticket must stay eligible for another attempt before the bar closes.
        if target != wanted:
            settled = False
        if breakeven_locked and (target < entry if is_buy else target > entry):
            # Price has retraced enough since the bar closed that even a stop
            # placed exactly at entry would violate the broker's min-stop
            # distance from the current live quote right now - moving it
            # anyway would place a stop worse than breakeven. Skip this
            # cycle; retry once price allows it.
            return False
        active_step = harvest_trail_step(
            trail_step_atr=float(cfg.trail_step_atr),
            harvest_at_r=harvest_at, harvest_step_atr=harvest_step,
            profit=profit_dist, original_risk=original_risk)
        step = trail_min_step(min_stop, atr, active_step)
        if current_sl != 0 and (target - current_sl < step if is_buy else current_sl - target < step):
            return settled
        # The position's real initial risk is the fill-time stop (or
        # max(atr*sl_atr_mult, min_stop) when that blob is missing) -
        # open_market sizes it that way (see the entry path above) whenever the
        # broker's own floor is wider than the ATR distance. Comparing against
        # the bare ATR number here was tighter than the SL actually placed, so
        # on any symbol where min_stop binds this could refuse a trail update
        # that was still a genuine improvement over the real original stop.
        if is_buy and target <= entry - original_risk:
            return settled
        if not is_buy and target >= entry + original_risk:
            return settled
        # Never clear a live stop by sending sl=0 (low-priced symbols /
        # bad trail arithmetic). Index books are safe; the path is not.
        if float(target) <= 0:
            return settled

        if self.client.modify_position(pos["ticket"], target, pos["tp"], cfg.symbol):
            # Write the level we just placed onto this cycle's position dict.
            # execution.track copies pos["sl"] into the slippage book; if we
            # leave it stale until the next positions_get, a stop that fires
            # in the same poll is scored against the old stop. Pepperstone
            # returning retcode=0/Done used to make modify_position False
            # here even when the broker had already moved — same hole.
            pos["sl"] = float(target)
            # The ticket, for the same reason the entry line carries one:
            # JPN225 held five positions today and logged two trail moves in
            # the same second. Without it a trail move cannot be paired with
            # the close it produced, and "Stop ile kapandi" is emitted for a
            # trailed exit and a stopped-out one alike - so the sign of the
            # profit was the only thing separating them.
            LOG.emit(f"#{pos['ticket']} SL guncellendi -> {target:.5f} "
                     f"(kar {profit_dist / atr:.2f}xATR)",
                     "TRADE", cfg.symbol)
            return True
        # A rejected modify (requote, momentary "invalid stops", a blip in the
        # trade server) must not cost the position its trail for the rest of
        # the bar - that is exactly the update the trade earned.
        return False

    def _maybe_scale_out(self, cfg: SymbolConfig, pos: dict[str, Any], atr: float,
                         bars: Any = None) -> bool:
        """Bank about one third of the ticket once closed-bar profit hits the R gate.

        Size comes from the ticket and the broker min/step, not a leftover
        lot dial. Remainder keeps the trail. False means not
        this poll (below the gate, unsplittable, already done, or refused).
        """
        at_r = float(getattr(cfg, "partial_at_r", 0.0) or 0.0)
        if at_r <= 0 or atr <= 0:
            return False
        ticket = int(pos.get("ticket") or 0)
        if not ticket:
            return False
        done = getattr(self, "_scale_out_done", None)
        if done is None:
            self._scale_out_done = set()
            done = self._scale_out_done
        if ticket in done:
            return False
        if bars is None or not hasattr(bars, "close") or len(bars.close) == 0:
            return False
        opened_at = int(pos.get("time", 0) or 0)
        closed_at = getattr(bars, "last_closed_time", None)
        if (opened_at and closed_at is not None
                and int(closed_at) + timeframe_seconds(cfg.timeframe) <= opened_at):
            return False
        is_buy = pos["side"] == "buy"
        ref = float(bars.close[-1])
        entry = pos["price_open"]
        profit_dist = (ref - entry) if is_buy else (entry - ref)
        min_stop = self.client.min_stop_distance(cfg.symbol)
        original_risk = self._fill_time_risk(pos, cfg, atr, min_stop)
        if original_risk <= 0 or profit_dist < at_r * original_risk:
            return False
        info = self.client.info(cfg.symbol) or {}
        close_vol = scale_out_slice(
            float(pos.get("volume") or 0),
            float(info.get("volume_min") or 0),
            float(info.get("volume_step") or 0),
        )
        if close_vol is None:
            return False
        fill: dict[str, Any] = {}
        ok = self._close_tracked(pos, "MicoFX parca", "scale_out",
                                 volume=close_vol, fill=fill)
        if not ok:
            return False
        done.add(ticket)
        setter = getattr(getattr(self, "store", None), "set_setting", None)
        if callable(setter):
            setter("scale_out_done", sorted(done))
        # IOC can fill less than requested; remain and the log follow the
        # broker print. done.add stays: one-shot, even on DONE_PARTIAL.
        filled_raw = float(fill.get("volume") or close_vol)
        pos_vol = float(pos.get("volume") or 0)
        filled = max(0.0, min(filled_raw, pos_vol)) if pos_vol > 0 else max(0.0, filled_raw)
        if abs(filled_raw - filled) > 1e-9:
            LOG.emit(
                f"#{ticket} parca hacmi uyusmadi (broker {filled_raw:g}, "
                f"pozisyon {pos_vol:g}) - {filled:g} kullanildi.",
                "WARN", cfg.symbol)
        remain = max(0.0, pos_vol - filled)
        r_now = profit_dist / original_risk if original_risk else 0.0
        px = float(fill.get("price") or 0)
        move = ((px - entry) if is_buy else (entry - px)) if px else profit_dist
        tick_size = float(info.get("tick_size") or info.get("point") or 0)
        tick_value = float(info.get("tick_value") or 0)
        if tick_size > 0 and tick_value > 0:
            cash = (tick_value / tick_size) * filled * move
        else:
            cash = self.client.money_per_price_unit(cfg.symbol, filled) * move
        LOG.emit(
            f"#{ticket} parca kapatildi {filled:g} lot "
            f"(kar={cash:.2f}, {r_now:.2f}R, kalan {remain:g})",
            "TRADE", cfg.symbol)
        pos["volume"] = remain
        return True

    def _enforce_account_lock(self, account: dict[str, Any]) -> str:
        """Bind on first sight, or block new entries when the terminal moved.

        Open-position management is intentionally not gated on this: leaving
        an already-open ticket unmanaged is worse than trading the wrong book.
        """
        sys = getattr(self.store, "system", None)
        decision = account_lock.decide_account_lock(
            int(getattr(sys, "account_lock_login", 0) or 0),
            str(getattr(sys, "account_lock_server", "") or ""),
            int(account.get("login") or 0),
            str(account.get("server") or ""),
            trade_mode=int(account.get("trade_mode") or 0),
        )
        updater = getattr(self.store, "update_system", None)
        if decision.bind_login is not None and callable(updater):
            updater(
                {
                    "account_lock_login": decision.bind_login,
                    "account_lock_server": decision.bind_server or "",
                },
                source="hesap-kilidi",
            )
            LOG.emit(
                f"hesap kilidi kuruldu: {decision.bind_login} @ {decision.bind_server}",
                "WARN",
            )
        reason = "" if decision.allow_entry else decision.reason
        prev = getattr(self, "_account_lock_reason", "")
        if reason and reason != prev:
            LOG.emit(reason, "ERROR")
        self._account_lock_reason = reason
        return reason

    # ---------------------------------------------------------------- reports

    def refresh_account(self, force: bool = False) -> dict[str, Any]:
        now = time.time()
        if not force and self._account and now - self._account_at < _ACCOUNT_TTL:
            return self._account
        account = self.client.account()
        if account:
            self._account = account
            self._account_at = now
            self._enforce_account_lock(account)
            return self._account
        if force:
            # A forced refresh that came back empty means the live call just
            # failed (see mt5client.account()'s connected=False on that path) -
            # falling through to the stale cached snapshot here used to hide
            # that from the trading cycle's `if not account: return` guard,
            # letting it proceed on a minutes-old balance/equity. Report the
            # failure honestly instead; only non-forced (dashboard) callers
            # still get the last-known snapshot for display continuity.
            return {}
        return self._account

    def positions_view(self) -> list[dict[str, Any]]:
        return self._decorate_positions(self.client.positions())

    def _decorate_positions(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_magic = {c.magic: c for c in list(self.store.symbols.values())}
        done = getattr(self, "_scale_out_done", None) or set()
        execu = getattr(self, "execution", None)
        snap = getattr(execu, "snapshot", None) if execu is not None else None
        out = []
        for pos in raw:
            cfg = by_magic.get(pos["magic"])
            item = dict(pos)
            item["managed"] = cfg is not None
            item["config_symbol"] = cfg.symbol if cfg else pos["symbol"]
            item["group"] = cfg.group if cfg else "-"
            book = None
            if callable(snap):
                try:
                    book = snap(int(pos.get("ticket") or 0))
                except (TypeError, ValueError):
                    book = None
            try:
                ticket = int(pos.get("ticket") or 0)
            except (TypeError, ValueError):
                ticket = 0
            item.update(self.live_open_metrics(
                item, book, partial_done=ticket in done))
            out.append(item)
        return out

    @staticmethod
    def live_open_metrics(pos: dict[str, Any], book: dict[str, Any] | None,
                          *, partial_done: bool = False) -> dict[str, Any]:
        """Live R against the fill-time stop. Cash P/L is a different unit.

        ``original_sl`` from the open book wins; a trailed broker SL would
        make a winner read as ~1R. Missing book (pre-persist ticket) falls
        back to the live stop — same first-sight rule as ``track()``.
        """
        book = book or {}
        side = str(pos.get("side") or "")
        try:
            entry = float(pos.get("price_open") or 0)
            cur = float(pos.get("price_current") or 0)
            live_sl = float(pos.get("sl") or 0)
        except (TypeError, ValueError):
            entry = cur = live_sl = 0.0
        orig = Engine._autopsy_float(book.get("original_sl"))
        if orig is None or orig <= 0:
            orig = live_sl if live_sl > 0 else None
        if entry > 0 and orig is not None and orig > 0:
            risk = abs(entry - orig)
        else:
            risk = Engine._autopsy_float(book.get("risk_dist")) or 0.0
        r_open = None
        if risk > 0 and entry > 0 and cur > 0 and side in ("buy", "sell"):
            move = (cur - entry) if side == "buy" else (entry - cur)
            r_open = round(move / risk, 4)
        mfe = Engine._autopsy_float(book.get("mfe"))
        mfe_r = (round(mfe / risk, 4) if mfe is not None and risk > 0 else None)
        trail_moved = bool(
            orig and live_sl
            and abs(live_sl - orig) > max(1e-9, abs(orig) * 1e-8))
        be_locked = False
        if live_sl > 0 and entry > 0:
            if side == "buy":
                be_locked = live_sl >= entry
            elif side == "sell":
                be_locked = live_sl <= entry
        return {
            "r_open": r_open,
            "mfe_r": mfe_r,
            "trail_moved": trail_moved,
            "be_locked": be_locked,
            "partial_done": bool(partial_done),
        }

    def _harvest_view(self) -> dict[str, Any]:
        """Closed-winner leftover plus which symbols have the one-shot scale-out on.

        Observation only. Does not change entries, exits, or apply gates.
        """
        report = self.trade_autopsy_report()
        by_sym: dict[str, float] = {}
        for cell in report.get("summary") or []:
            left = cell.get("left_on_table_r")
            if left:
                sym = str(cell.get("symbol") or "")
                if not sym:
                    continue
                by_sym[sym] = round(by_sym.get(sym, 0.0) + float(left), 4)
        partial_on: list[str] = []
        harvest_on: list[str] = []
        store = getattr(self, "store", None)
        symbols = getattr(store, "symbols", None) if store is not None else None
        if symbols:
            for cfg in symbols.values():
                name = str(getattr(cfg, "symbol", "") or "")
                if not name:
                    continue
                if float(getattr(cfg, "partial_at_r", 0) or 0) > 0:
                    partial_on.append(name)
                if (float(getattr(cfg, "harvest_at_r", 0) or 0) > 0
                        and float(getattr(cfg, "harvest_step_atr", 0) or 0) > 0):
                    harvest_on.append(name)
        return {
            "n": int(report.get("n") or 0),
            "left_on_table_r": report.get("left_on_table_r"),
            "by_symbol": dict(sorted(by_sym.items(), key=lambda kv: -kv[1])),
            "partial_on": partial_on,
            "harvest_on": harvest_on,
        }

    def _cycle_book_is_fresh(self) -> bool:
        if not self.client.connected or not self.last_cycle_at:
            return False
        interval = float(getattr(self.store.system, "poll_interval_sec", 2.0) or 2.0)
        return (time.time() - self.last_cycle_at) <= max(4.0, 2.0 * interval)

    def _search_is_busy(self) -> bool:
        probe = getattr(self, "search_busy", None)
        if callable(probe):
            return bool(probe())
        opt = getattr(getattr(self, "supervisor", None), "optimizer", None)
        return bool(getattr(opt, "busy", False))

    def _panel_reuse_cycle_book(self) -> bool:
        """True when /api/state must not take the MT5 lock.

        Once the engine has cycled at least once, always serve the last
        cycle book. A long cycle or lock contention must not block the
        panel on positions_get/account_info (148s measured 26.08). The
        worker refreshes the book every poll; stale is honest until the
        next cycle lands. Halt/flatten still wait inside ``_cycle``.

        Disconnected is the same hazard from the other side: ensure() is
        inside initialize() (IPC timeout) and the panel used to fall
        through because ``_cycle_book_is_fresh`` requires ``connected``.
        """
        if not getattr(self.client, "connected", False):
            return True
        return bool(self.last_cycle_at)

    def _panel_positions(self) -> list[dict[str, Any]]:
        """Positions for /api/state. Reuse the cycle book when it is fresh.

        snapshot() used to call positions() on every panel poll, taking the
        same MT5 lock the worker already held at cycle start. Empty is a
        valid flat book, so this must not fall through with ``or``.
        """
        if self._panel_reuse_cycle_book():
            return self._decorate_positions(self._positions)
        return self.positions_view()

    def _panel_account(self) -> dict[str, Any]:
        """Account for /api/state. Reuse the cycle snapshot when it is fresh.

        Panel poll is 3s; ``refresh_account`` TTL used to be 1s, so every
        visible poll took ``account_info`` on the same MT5 lock the cycle
        already held. Empty is not a valid cached book (no reading yet),
        so this *does* fall through on a missing snapshot.
        """
        if self._panel_reuse_cycle_book():
            return self._account or {}
        if self._search_is_busy():
            return self._account or {}
        return self.refresh_account()

    def _panel_terminal_flags(self) -> dict[str, Any]:
        """terminal_info for /api/state. Same lock as copy_rates."""
        cache = getattr(self, "_terminal_flags_cache", None) or {}
        now = time.time()
        last = float(getattr(self, "_terminal_flags_at", 0.0) or 0.0)
        if not getattr(self.client, "connected", False) or self._search_is_busy():
            return cache
        if cache and now - last < _TERMINAL_FLAGS_TTL:
            return cache
        flags = self.client.terminal_flags()
        if flags:
            self._terminal_flags_cache = flags
            self._terminal_flags_at = now
            return flags
        return cache or flags

    def _panel_capacity(self, positions: list[dict[str, Any]],
                        account: dict[str, Any],
                        atrs: dict[str, float]) -> dict[str, Any]:
        """Capacity for /api/state. Recompute on ticket/volume change, else TTL.

        ``risk.capacity`` calls ``order_calc_margin`` per symbol under the
        live MT5 lock. Equity can tick every poll; slot counts do not.
        """
        sig = tuple(sorted(
            (int(p.get("ticket") or 0), round(float(p.get("volume") or 0), 4))
            for p in positions))
        now = time.time()
        # Search holds the MT5 lock for order_calc_margin. Lot/margin stay on
        # the frozen copy; open count, floating P/L and enabled do not need
        # that lock (27.08: capacity said US30=0 / 6 tickets while the book
        # had 7). Overlay from the positions this snapshot already holds.
        if self._search_is_busy() and self._capacity_cache:
            return self._overlay_capacity_opens(self._capacity_cache, positions)
        if not getattr(self.client, "connected", False):
            if self._capacity_cache:
                return self._overlay_capacity_opens(self._capacity_cache, positions)
            return {}
        sys_cfg = self.store.system
        sys_sig = (
            float(getattr(sys_cfg, "lot_multiplier", 0.0) or 0.0),
            float(getattr(sys_cfg, "max_margin_usage_pct", 0.0) or 0.0),
            float(getattr(sys_cfg, "max_concurrent_risk_pct", 0.0) or 0.0),
            bool(getattr(sys_cfg, "size_by_edge", False)),
        )
        if sys_sig != self._capacity_sys_sig:
            self._capacity_cache = {}
            self._capacity_sys_sig = sys_sig
        if (self._capacity_cache
                and sig == self._capacity_pos_sig
                and now - self._capacity_cache_at < _CAPACITY_TTL):
            return self._capacity_cache
        out = self.risk.capacity(
            positions, account, atrs,
            autopsies=getattr(self, "_trade_autopsies", None))
        self._capacity_cache = out
        self._capacity_cache_at = now
        self._capacity_pos_sig = sig
        return out

    def _overlay_capacity_opens(self, blob: dict[str, Any],
                                positions: list[dict[str, Any]]) -> dict[str, Any]:
        """Refresh open count / P/L / enabled on a search-frozen capacity blob."""
        out = dict(blob)
        rows = []
        for raw in blob.get("rows") or []:
            row = dict(raw)
            names = {row.get("symbol"), row.get("broker_symbol")} - {None, ""}
            mine = [p for p in positions if p.get("symbol") in names]
            n = len(mine)
            old_n = int(row.get("open_positions") or 0)
            old_free = int(row.get("free_slots") or 0)
            row["open_positions"] = n
            row["open_profit"] = round(sum(
                float(p.get("profit") or 0) + float(p.get("swap") or 0)
                for p in mine), 2)
            cfg = (getattr(self.store, "symbols", None) or {}).get(row.get("symbol"))
            if cfg is not None:
                row["enabled"] = bool(getattr(cfg, "enabled", False))
            if not row.get("enabled"):
                row["free_slots"] = 0
            else:
                row["free_slots"] = max(0, old_free - (n - old_n))
            rows.append(row)
        out["rows"] = rows
        n_all = len(positions)
        old_total = int(blob.get("open_total") or 0)
        old_global = int(blob.get("global_free_slots") or 0)
        out["open_total"] = n_all
        out["global_free_slots"] = max(0, old_global - (n_all - old_total))
        out["search_frozen"] = True
        acc = getattr(self, "_account", None) or {}
        try:
            balance = float(acc.get("balance") or acc.get("equity") or 0.0)
        except (TypeError, ValueError):
            balance = 0.0
        proj = self.risk.fill_holdout_projection(rows, balance)
        out.update(proj)
        return out

    def _symbol_daily_halt(self, cfg: SymbolConfig) -> str:
        """Non-empty block reason once THIS symbol has lost its own daily cap.

        Independent of, and in addition to, the account-wide DailyGuard: that
        one only trips on total equity, so a single misbehaving symbol can burn
        most of the day's allowed loss while every other symbol keeps trading
        normally, right up until the whole account crosses the global line.
        Sourced from real MT5 deal history (``day_stats``) plus this symbol's
        current floating P/L - EXCEPT once tripped, which is sticky
        (persisted, cleared only on day rollover - see ``_cycle()``) just like
        DailyGuard.loss_halted. Without that, floating P/L recovering mid-cycle
        (another position on the same symbol swinging back, a stray tick) made
        the halt - and the flatten manage_positions() drives off it - flap
        back off for that cycle even though the day's cap was already blown.
        """
        if float(getattr(cfg, "symbol_daily_loss_pct", 0.0) or 0.0) <= 0:
            return ""
        if cfg.symbol in self._symbol_halted:
            return self._symbol_halted[cfg.symbol]
        guard = self.risk.daily
        if guard.start_balance <= 0:
            return ""
        row = next((r for r in self.day_stats().get("per_symbol", [])
                    if r["symbol"] == cfg.symbol), None)
        realised = row["profit"] if row is not None else 0.0
        # Realised-only missed a symbol that was already deep in a floating
        # loss on an open position - closed trades hadn't caught up yet, so
        # the halt (and the flatten it now triggers - see manage_positions())
        # never fired until that position finally closed and booked it.
        # ``realised`` above nets the deal's own commission in (day_stats():
        # ``deal["profit"] + deal["commission"] + deal["swap"]``) - MT5's
        # TradePosition struct has no live-accruing commission field to match
        # that with on the *open* side (unlike history deals, positions_get()
        # genuinely does not expose one), so the still-open round-turn cost is
        # estimated from cfg.commission_per_lot (documented as the full
        # round-turn commission in account currency) instead of left at zero.
        # Slightly conservative if the broker only charges commission at
        # close - it books the anticipated exit-side cost a bit early - but
        # that is the safe direction for a loss *halt* to be wrong in.
        floating = sum(p.get("profit", 0.0) + p.get("swap", 0.0)
                       - cfg.commission_per_lot * p.get("volume", 0.0)
                       for p in self._positions if p["magic"] == cfg.magic)
        if row is None and floating == 0.0:
            return ""
        loss_pct = -(realised + floating) / guard.start_balance * 100.0
        if loss_pct >= cfg.symbol_daily_loss_pct:
            reason = f"gunluk sembol zarar limiti ({loss_pct:.2f}%)"
            self._symbol_halted[cfg.symbol] = reason
            self._save_symbol_halted()
            return reason
        return ""

    def _save_symbol_halted(self) -> None:
        self.store.set_setting("symbol_daily_halted", self._symbol_halted)

    def _day_start_epoch(self) -> float:
        """Epoch the current trading day's deal history starts at.

        Raw MT5 deal timestamps are naive epochs encoding the broker's own
        wall-clock reading (not true UTC). ``day_key`` is that same calendar
        date via ``gmtime(broker epoch)``, and ``calendar.timegm`` of midnight
        on that date is the matching naive midnight. Converting that date
        through the machine timezone into a true UTC epoch would shift the
        day by the broker's UTC offset.
        """
        guard = self.risk.daily
        if guard.day_key:
            try:
                return float(calendar.timegm(time.strptime(guard.day_key, "%Y-%m-%d")))
            except (ValueError, OverflowError):
                pass
        return self.client.server_now() - 86400

    def _refresh_cash_flow(self) -> None:
        # Deposits/withdrawals rarely move. history_deals_get shares the MT5
        # lock with trail/flatten; skip while balance is unchanged and the
        # last good fetch is fresh. A jump (13.08 +500) fetches immediately.
        now = time.time()
        balance = float((self._account or {}).get("balance") or 0.0)
        last_bal = getattr(self, "_cash_flow_balance", None)
        last_at = float(getattr(self, "_cash_flow_at", 0.0) or 0.0)
        if (last_bal is not None
                and abs(balance - last_bal) < 0.005
                and now - last_at < _CASH_FLOW_TTL):
            return
        flow = self.client.cash_flow_since(self._day_start_epoch())
        self.risk.daily.set_cash_flow(flow)
        if flow is None:
            return
        self._cash_flow_at = now
        self._cash_flow_balance = balance

    def _handle_daily_rollover(self, server_now: float, balance: float, login: int = 0) -> None:
        if self.risk.daily.rollover(server_now, balance, login=login):
            # New broker day - every symbol-level sticky halt from yesterday
            # is stale, same as DailyGuard.loss_halted resetting itself.
            if self._symbol_halted:
                self._symbol_halted = {}
                self._save_symbol_halted()
            self._day_cache = {}
            self._day_cache_at = 0.0
            self._cash_flow_at = 0.0

    def _empty_day_stats(self) -> dict[str, Any]:
        guard = self.risk.daily
        return {
            "day_key": getattr(guard, "day_key", "") or "",
            "start_balance": round(float(getattr(guard, "start_balance", 0.0) or 0.0), 2),
            "closed_trades": 0, "wins": 0, "losses": 0, "win_rate": 0.0,
            "realised": 0.0, "per_symbol": [],
            "halted": bool(getattr(guard, "halted", False)),
            "halt_reason": getattr(guard, "halt_reason", "") or "",
        }

    def day_stats(self, max_age: float = 5.0, fetch: bool = True) -> dict[str, Any]:
        """Closed-trade totals for the current broker-calendar day, per symbol."""
        if self._day_cache and time.time() - self._day_cache_at < max_age:
            return self._day_cache
        if not fetch:
            return self._day_cache or self._empty_day_stats()
        guard = self.risk.daily
        day_start = self._day_start_epoch()

        by_magic = {c.magic: c.symbol for c in list(self.store.symbols.values())}
        per_symbol: dict[str, dict[str, Any]] = {}
        total = wins = losses = 0
        gross = 0.0
        # One entry per closed position, not per partial-TP fill - otherwise a
        # net-winning trade that scaled out in two rungs shows up as an extra
        # phantom loss and skews the day's win-rate (see merge_round_trips).
        deals = self.client.merge_round_trips(self.client.deals_since(day_start))
        for deal in deals:
            symbol = by_magic.get(deal["magic"])
            if symbol is None:
                continue
            # Key by our canonical symbol (via magic), not the deal's raw
            # broker-resolved name - those differ whenever broker_symbol maps
            # to a different case/name (e.g. CATTLE -> "Cattle"), which made
            # _symbol_daily_halt's lookup by cfg.symbol silently never match.
            net = deal["profit"] + deal["commission"] + deal["swap"]
            row = per_symbol.setdefault(symbol, {"symbol": symbol, "trades": 0,
                                                 "wins": 0, "losses": 0, "profit": 0.0})
            row["trades"] += 1
            row["profit"] = round(row["profit"] + net, 2)
            total += 1
            gross += net
            if net >= 0:
                row["wins"] += 1
                wins += 1
            else:
                row["losses"] += 1
                losses += 1

        stats = {
            "day_key": guard.day_key,
            "start_balance": round(guard.start_balance, 2),
            "closed_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / total * 100.0, 1) if total else 0.0,
            "realised": round(gross, 2),
            "per_symbol": sorted(per_symbol.values(), key=lambda r: r["profit"]),
            "halted": guard.halted,
            "halt_reason": guard.halt_reason,
        }
        self._day_cache = stats
        self._day_cache_at = time.time()
        return stats

    def _states_view(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        broker_now = float(self.client.broker_now() or 0.0)
        for name, st in list(self.states.items()):
            raw = st.as_dict()
            row = {k: raw[k] for k in _PANEL_STATE_KEYS if k in raw}
            cfg = self.store.symbols.get(name)
            tf = getattr(cfg, "timeframe", "") if cfg else ""
            bar = int(getattr(st, "last_bar", 0) or 0)
            if bar > 0:
                row["last_bar_time"] = time.strftime(
                    "%H:%M", time.gmtime(bar))
            if broker_now > 0 and tf:
                tf_sec = timeframe_seconds(tf)
                if tf_sec > 0:
                    secs_into = int(broker_now) % tf_sec
                    row["minutes_to_bar"] = max(
                        0, (tf_sec - secs_into + 59) // 60)
            out[name] = row
        return out

    def _measured_clock_skew(self, server_now: float) -> int | None:
        """Broker-vs-machine hour gap, or None when it cannot be measured.

        The broker clock is only knowable while ticks flow - MetaTrader5's
        Python API exposes no TimeCurrent() - so a shut market freezes it and
        the difference stops being an offset and becomes "how long since the
        close". Reading a stale stamp as the current broker time is what put
        "broker saati yerel saatten -42 saat farkli" in the log all weekend.
        """
        getter = getattr(self.client, "broker_now", None)
        broker_now = float(getter() or 0.0) if callable(getter) else 0.0
        ager = getattr(self.client, "broker_now_age", None)
        age = ager() if callable(ager) else None
        if age is None or age > BROKER_CLOCK_MAX_AGE_SEC:
            return None
        return sessions.session_clock_skew_hours(broker_now, server_now)

    def _session_clock_payload(self) -> dict[str, Any]:
        skew = self._measured_clock_skew(self.client.server_now())
        return {
            "session_clock_warning": sessions.session_clock_warning(skew),
        }

    def _note_unmanaged_ticket(self, cfg: SymbolConfig, pos: dict[str, Any]) -> None:
        """One WARN when an open ticket is getting no closed-bar management.

        ``_update_stop`` (trail, breakeven, harvest) only runs under a non-zero
        ``last_bar``, and ``_refresh_signals`` returns before setting one when
        the symbol is under its ``min_bars`` floor. The ticket then rides its
        broker stop alone with nothing in the log saying so. Latched on the
        same per-ticket set the unmapped-magic case uses, which
        ``manage_positions`` already prunes against the live book, so a
        recovered symbol re-arms the warning instead of muting it forever.
        """
        ticket = int(pos["ticket"])
        if ticket in self._unmanaged_seen:
            return
        self._unmanaged_seen.add(ticket)
        state = self.states.get(cfg.symbol)
        have = getattr(state, "bars_ready", 0) if state else 0
        LOG.emit(f"#{ticket} yeterli bar yok ({have}) - trail/BE/harvest bu "
                 f"pozisyon icin calismiyor, yalnizca brokerin stopu gecerli.",
                 "WARN", cfg.symbol)

    def _probe_book_ticks(self) -> None:
        """Read every book symbol so a recovered feed can unstick the clock.

        ``decision_now`` is computed once per cycle and handed to every
        ``_evaluate``. That method used to call ``tick()`` only *after* the
        stale-clock return, and a flat book never reached ``_update_stop``
        either. 27.08 00:00 seeded 23:58:59, the 60s pace window expired,
        and 8400 cycles later the six names were still 'broker saati bayat'
        with a green panel. The refuse is correct; never polling again is
        the deadlock.
        """
        tick = getattr(self.client, "tick", None)
        if not callable(tick):
            return
        for cfg in list(self.store.symbols.values()):
            try:
                tick(cfg.symbol, force=True)
            except Exception:
                pass

    def _note_stale_decision_clock(self, server_now: float | None) -> None:
        """Say so when the refuse has lasted past the startup unknown window.

        ``last_error`` is wiped on every successful cycle, so it cannot
        carry this. One WARN per ``CLOCK_STALE_WARN_SEC``; the first minute
        after a restart is still quiet on purpose.
        """
        if server_now is not None:
            self._clock_stale_warned_at = 0.0
            return
        if int(getattr(self, "cycle_count", 0) or 0) < CLOCK_STALE_WARN_AFTER_CYCLES:
            return
        now = time.time()
        last = float(getattr(self, "_clock_stale_warned_at", 0.0) or 0.0)
        if now - last < CLOCK_STALE_WARN_SEC:
            return
        self._clock_stale_warned_at = now
        stamp = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.gmtime(float(self.client.broker_now() or 0.0)))
        LOG.emit(f"broker saati bayat ({stamp}) - yeni giris yok", "WARN")

    def _note_session_clock(self, server_now: float) -> None:
        """Log once when broker wall clock leaves the machine's wall clock.

        Measurement only. Does not rewrite session windows.

        An unmeasurable clock - a shut market, or the first minute after a
        restart - leaves the last known gap in place instead of erasing it.
        Erasing it would mean the next reading has nothing to be compared
        against, and the reading worth catching is a *change*: the broker
        shifting an hour at a DST switch, which happens on a Sunday inside
        the very outage where measurement is impossible. The stored value is
        what turns the first tick after the weekend into an answer.
        """
        skew = self._measured_clock_skew(server_now)
        if skew is None:
            return
        prev = getattr(self, "_session_clock_skew", None)
        if skew == prev:
            return
        self._session_clock_skew = skew
        try:
            self.store.set_setting("session_clock_skew", skew)
        except Exception as exc:                  # measurement, never a cycle
            self._flush_failed("session_clock_skew", exc)
        if prev is not None and prev != skew:
            LOG.emit(f"broker saati kaydi: {prev:+d} -> {skew:+d} saat "
                     f"(yaz/kis saati degisimi olabilir - seans pencereleri "
                     f"broker damgasinda, kontrol edin)", "WARN")
            return
        warn = sessions.session_clock_warning(skew)
        if warn:
            LOG.emit(warn, "WARN")

    def _panel_atrs(self) -> dict[str, float]:
        """ATR map for capacity display; reuse last good value across warm-up."""
        out: dict[str, float] = {}
        for sym, st in list(self.states.items()):
            try:
                atr = float(st.atr or 0.0)
            except (TypeError, ValueError):
                atr = 0.0
            if atr > 0:
                self._last_good_atr[sym] = atr
                out[sym] = atr
            else:
                cached = float(self._last_good_atr.get(sym) or 0.0)
                if cached > 0:
                    out[sym] = cached
        return out

    def snapshot(self) -> dict[str, Any]:
        account = self._panel_account()
        positions = self._panel_positions()
        capacity = self._panel_capacity(
            positions, account, self._panel_atrs())
        day = self.day_stats(max_age=15.0, fetch=False)
        equity = float(account.get("equity", 0.0))
        getter = getattr(self.client, "decision_now", None)
        clock_stale = getter() is None if callable(getter) else False
        return {
            "bot": {
                "running": self.running,
                "watching": self.watching,
                "cycle": self.cycle_count,
                "last_cycle_at": self.last_cycle_at,
                "last_cycle_ms": round(self.last_cycle_ms, 1),
                "last_error": self.last_error,
            },
            "mt5": {
                "connected": self.client.connected,
                "error": self.client.last_error,
                "server_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(
                    self.client.broker_now() or self.client.server_now())),
                "clock_stale": clock_stale,
                **self._panel_terminal_flags(),
                **self._session_clock_payload(),
            },
            "account": account,
            "account_lock": {
                "ok": not getattr(self, "_account_lock_reason", ""),
                "reason": getattr(self, "_account_lock_reason", ""),
                "expected_login": int(getattr(self.store.system, "account_lock_login", 0) or 0),
                "expected_server": str(getattr(self.store.system, "account_lock_server", "") or ""),
            },
            "day": {
                "closed_trades": day.get("closed_trades", 0),
                "win_rate": day.get("win_rate", 0.0),
                "realised": day.get("realised", 0.0),
                "per_symbol": day.get("per_symbol") or [],
                "halted": bool(day.get("halted")),
                "halt_reason": day.get("halt_reason", "") or "",
                "pnl_pct": round(self.risk.daily.pnl_pct(equity), 2),
            },
            "capacity": capacity,
            "execution": self.execution.stats(),
            "positions": positions,
            "harvest": self._harvest_view(),
            "states": self._states_view(),
            "ai": self.supervisor.status(),
            "autopilot": (
                self.autopilot.status()
                if getattr(self, "autopilot", None) is not None
                else {"enabled": False}
            ),
        }
