from __future__ import annotations

import calendar
import math
import threading
import time
from typing import Any

from . import backtest, execution, indicators as ind, sessions
from .logbus import LOG
from .models import (SymbolConfig, invalid_exit_param, is_scalp_strategy,
                     strategy_allows_timeframe, trail_min_step)
from .mt5client import AMBIGUOUS_RETCODES, MT5Client, NON_RETRYABLE_RETCODES, timeframe_seconds
from .execution import ExecutionMonitor
from .risk import RiskManager
from .store import Store, as_dict, as_list, as_number
from .strategy import IndicatorCache, Params, Signals, compute, required_bars
from .supervisor import Supervisor

_STALE_BAR_REFRESH = 45.0   # force a bar refresh at least this often
_ACCOUNT_TTL = 1.0

# A cooldown is meant to stop the same setup re-firing on the next bar or two,
# so it belongs on the strategy's own clock. The stored seconds were written for
# the M5-and-slower presets; left alone they would silently cost an M5 config
# five bars of opportunity per fill. Capped, never extended - a config that asks
# for a short pause still gets exactly what it asks for.
_COOLDOWN_BARS = 2
# Swing / higher-TF families already wait a full bar between signals; one bar of
# post-fill silence is enough. Two H1 bars would idle the symbol for two hours.
_COOLDOWN_BARS_SWING = 1

# Live-tick-spread / bar-spread histogram: buckets of 0.1 from 0.0 to 5.0,
# plus a final overflow bucket for anything above.
SPREAD_RATIO_STEP = 0.1
SPREAD_RATIO_BUCKETS = 51
# Below this many samples the ratio is not reported or applied - a handful of
# ticks from one hour is exactly the reading that misled us once already.
SPREAD_RATIO_MIN_SAMPLES = 400

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
    ("marj hesaplanamadi", "risk_marj_okunamadi"),
    ("serbest marj yetersiz", "risk_serbest_marj"),
    ("marj kullanimi limiti", "risk_marj_kullanimi"),
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
                 "primary_signal", "sec_signal", "sec_atr", "sec_last_bar",
                 "sec_next_bar_at", "sec_last_fetch", "sec_bars", "signal_source",
                 "pending_bar_key", "entry_block")

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.last_bar = 0
        self.next_bar_at = 0.0
        self.last_fetch = 0.0
        self.atr = 0.0
        # ---- second (opt-in) signal, evaluated on its own timeframe ----
        self.primary_signal = ""
        self.sec_signal = ""
        self.signal_source = ""      # "" | "primary" | "secondary"
        self.sec_atr = 0.0
        self.sec_last_bar = 0
        self.sec_next_bar_at = 0.0
        self.sec_last_fetch = 0.0
        self.sec_bars = None
        self.adx = 0.0
        self.t3 = 0.0
        self.t3_rising = False
        self.htf = 0
        self.k = 0.0
        self.d = 0.0
        self.signal = ""
        self.bars_ready = 0
        self.cooldown_until = 0.0
        self.note = ""
        self.session = {}
        self.spread = 0.0
        self.spread_atr = 0.0
        self.last_signal_at = 0.0
        self.bars = None  # most recent Bars snapshot, for structure-based trailing
        # (last_bar, sec_last_bar) at the moment a fresh signal was last seen
        # and not yet filled - lets _evaluate retry a signal a transient block
        # (spread/slot/AI gate) ate earlier in the same bar. (0, 0) means none.
        self.pending_bar_key = (0, 0)
        # Which gate refused THIS cycle's entry attempt, as a stable key rather
        # than the display note. Only meaningful right after _try_entry ran;
        # _cycle reads it once and tallies it. See Engine._entry_blocks.
        self.entry_block = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol, "last_bar": self.last_bar, "atr": round(self.atr, 6),
            "adx": round(self.adx, 1), "t3": round(self.t3, 6), "t3_rising": self.t3_rising,
            "htf": self.htf,
            "k": round(self.k, 1), "d": round(self.d, 1), "signal": self.signal,
            "signal_source": self.signal_source,
            "primary_signal": self.primary_signal, "secondary_signal": self.sec_signal,
            "bars_ready": self.bars_ready, "note": self.note, "session": self.session,
            "spread": round(self.spread, 6), "spread_atr": round(self.spread_atr, 3),
            "cooldown_left": max(0, int(self.cooldown_until - time.time())),
            "last_signal_at": self.last_signal_at,
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
        self._account: dict[str, Any] = {}
        self._account_at = 0.0
        self._positions: list[dict[str, Any]] = []
        self.cycle_count = 0
        self.last_cycle_at = 0.0
        self.last_cycle_ms = 0.0
        self.last_error = ""
        self._day_cache: dict[str, Any] = {}
        self._day_cache_at = 0.0
        # ticket -> {"rungs": how many scale-out steps already banked,
        #            "orig": the volume the position opened with}. Fractions are
        #            of the *original* size, matching the backtest ladder.
        # Persisted (like secondary_tickets below): without it, a restart after
        # the first rung fired would forget "rungs" was ever 1 *and* re-derive
        # "orig" from the position's now-reduced live volume, so the next rung's
        # fraction would be computed against the wrong base entirely.
        # ticket -> last bar-close time the trailing/partial-ladder logic was run
        # against. MASTER_PROMPT §6 requires "trail / BE advance on bar closes
        # only, not intrabar wick trails" - the walk-forward only ever re-checks
        # the trail once per simulated bar, so evaluating it every ~2s poll cycle
        # instead let the live stop tighten far more often than the backtest
        # that validated it ever did. Not persisted: worst case after a restart
        # is one extra evaluation on the first cycle, not a correctness issue.
        self._stop_bar: dict[int, int] = {}
        # Tickets whose weekend force-close failed at least once - kept sticky
        # across the Sat/Sun -> Monday boundary so a broker that rejected the
        # close all weekend doesn't just quietly resume normal trailing the
        # instant weekend_closed() flips False, without ever actually landing
        # that close. Not persisted, same tradeoff as _stop_bar: worst case
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
        # A position opened before the scale-out ladder was removed can still
        # be open right now, and its old partial_state row is meaningless to
        # the current exit model - drop the setting once rather than carry a
        # reader for a feature that no longer exists.
        if store.get_setting("partial_state"):
            store.set_setting("partial_state", {})
        # Ensemble bookkeeping: the overlaid config per symbol, and which open
        # tickets came from the secondary signal (persisted, because positions
        # outlive the process and must keep being managed by the exit rules they
        # were opened under).
        self._sec_cfgs: dict[str, tuple[tuple, SymbolConfig]] = {}
        self._sec_tickets: set[int] = {
            int(t) for t in (as_list(store.get_setting("secondary_tickets"), "secondary_tickets")) if str(t).isdigit()
        }
        # Secondary fills whose broker ticket could not be identified/closed at
        # entry time. Two persisted forms, same goal (never let one silently run
        # under the primary's exit params): ``_orphan_tickets`` is a known ticket
        # still needing a retried close; ``_orphan_scan`` is a symbol whose fill
        # produced zero same-magic candidates yet, so every cycle re-diffs
        # against the snapshot taken at failure time until one appears (broker
        # replication lag) or the scan goes stale. Persisted like
        # weekend_pending_tickets - a restart mid-retry must not forget either.
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
        self._reopt_at = as_number(store.get_setting("auto_reopt_at"), 0.0, "auto_reopt_at")
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
        self._entry_blocks_dirty = False
        # In-memory only: the (bar, reason) episode each leg was last counted
        # for, so the per-poll retry loop cannot inflate the signal count. A
        # restart starting a fresh episode is the honest reading - the new
        # process re-derives the signal from bars it fetched itself.
        self._entry_last_bar: dict[str, dict[str, tuple]] = {}
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
            legs: dict[str, int] = {}
            # The bar timestamp has to be a number, not merely present: a bare
            # length check let ["sig", "yok"] through to int(), which raises
            # inside __init__ and takes the whole start-up with it.
            def _ok(bar: Any) -> bool:
                return isinstance(bar, (int, float)) and not isinstance(bar, bool)
            if isinstance(value, dict):
                legs = {str(k): int(v) for k, v in value.items() if _ok(v)}
            elif (isinstance(value, (list, tuple)) and len(value) == 2
                  and _ok(value[1])):
                # The single-slot shape this replaced. Migrated rather than
                # dropped so the guard keeps covering the leg it did record
                # across the restart that installs this change.
                legs = {str(value[0]): int(value[1])}
            if legs:
                self._filled_bars[str(sym)] = legs

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
            self.store.update_system({"running": True})
        LOG.emit("Bot baslatildi - islem acmaya hazir.", "INFO")
        return {"ok": True, "running": True, "message": "Bot baslatildi."}

    def stop(self, close_positions: bool | None = None) -> dict[str, Any]:
        with self._lock:
            was_trading = self._trading
            self._trading = False
            self.store.update_system({"running": False})
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
        self.execution.flush()
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=8.0)
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

    def close_all(self, symbol: str | None = None) -> tuple[int, int]:
        """Returns ``(closed, remaining)`` - see ``MT5Client.close_all``."""
        magics = {c.magic for c in list(self.store.symbols.values())}
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

        server_now = self.client.server_now()
        self._handle_daily_rollover(server_now, account.get("balance", 0.0))

        self._positions = self.client.positions()
        if not self.client.connected:
            # positions() itself flips this False when mt5.positions_get()
            # fails mid-cycle (disconnect after the ensure() check above
            # already passed) - self._positions is then an unreliable empty
            # list, not "flat". Bail before manage_positions/entries act on
            # it; the next cycle's ensure() will reconnect first.
            return
        self._reap_execution()
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
        self.manage_positions(server_now)

        guard = self.risk.daily.check(account.get("equity", 0.0), self.store.system)
        # The loss guard alone only ever blocked NEW entries - an already-open
        # position kept riding its own (possibly distant) stop while the
        # account kept bleeding floating loss past the configured limit. When
        # the halt is specifically the loss side (not the profit-target side,
        # where letting winners run is a legitimate choice), flatten what is
        # still open so "daily loss limit" actually stops the daily loss.
        # Runs every cycle while halted, not just once - self-healing if a
        # partial close_all() attempt left something behind.
        sys_cfg = self.store.system
        # Sticky (DailyGuard.loss_halted), not re-derived from live equity -
        # re-checking pnl_pct here every cycle meant a bounce back above the
        # threshold (another position's floating P/L recovering, a stray
        # tick) silently turned the flatten off for that cycle even though
        # the day is still halted and still supposed to be flattening. The
        # halt itself only ever clears on rollover/resume, so this should too.
        loss_halted = self.risk.daily.halted and self.risk.daily.loss_halted
        if loss_halted and sys_cfg.daily_loss_flatten and self._positions:
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
                self.supervisor.review(self.risk.daily.pnl_pct(account.get("equity", 0.0)))
            except Exception as exc:
                LOG.emit(f"AI denetleyici hatasi: {exc}", "ERROR")

        self._maybe_schedule_reopt()

        # Every position-count guard here (max_positions, weekend/secondary
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
        allow_entry = (self._trading and guard.ok and not netting
                       and self.client.connected)
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
                if not self._trading and state.note in ("", "bekliyor", "sinyal yok"):
                    state.note = "bot durdu - izleme"
                elif self._trading and not guard.ok:
                    state.note = guard.reason
            except Exception as exc:
                state.note = f"hata: {exc}"
                LOG.emit(f"Degerlendirme hatasi: {exc}", "ERROR", cfg.symbol)

        if allow_entry and ready:
            ready.sort(key=lambda c: self.supervisor.priority(c), reverse=True)
            for cfg in ready:
                state = self.states[cfg.symbol]
                if not state.signal:
                    continue
                try:
                    # An entry triggered by the secondary signal is executed with
                    # the parameters it was validated under, not the primary's.
                    self._try_entry(cfg, state, account)
                    self._tally_entry(cfg.symbol, state.entry_block,
                                      bar_key=state.pending_bar_key,
                                      source=state.signal_source)
                    # account was a single snapshot taken at the top of this
                    # cycle - if that entry just filled, every later symbol in
                    # this same ready list would otherwise size/margin-check
                    # itself against margin the fill above already spent.
                    account = self.refresh_account(force=True) or account
                except Exception as exc:
                    state.note = f"hata: {exc}"
                    self._tally_entry(cfg.symbol, "hata")
                    LOG.emit(f"Giris hatasi: {exc}", "ERROR", cfg.symbol)
            self._flush_entry_blocks()
        self._flush_spread_ratio()

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
        except Exception:
            pass

    def spread_ratio(self) -> dict[str, Any]:
        """Per-symbol median and 90th percentile of tick spread / bar spread."""
        rows = []
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
            leg = "secondary" if source == "secondary" else "primary"
            legs = self._entry_blocks.setdefault(str(symbol), {})
            counts = legs.setdefault(leg, {"attempts": {}, "signals": {}})
            attempts, signals = counts["attempts"], counts["signals"]
            attempts[key] = int(attempts.get(key, 0)) + 1
            # One episode per (bar, leg, reason); the retry loop must not
            # inflate it. Held in memory only - a restart starting a fresh
            # episode is the honest reading, since the signal is re-derived
            # from bars the new process fetches for itself.
            seen = self._entry_last_bar.setdefault(str(symbol), {})
            episode = (repr(bar_key), key)
            if seen.get(leg) != episode:
                seen[leg] = episode
                signals[key] = int(signals.get(key, 0)) + 1
            self._entry_blocks_dirty = True
        except Exception:
            pass

    def _flush_entry_blocks(self) -> None:
        """Persist the tally. Diagnostics must never interrupt a cycle."""
        if not self._entry_blocks_dirty:
            return
        try:
            # Same bound as the spread histogram and _mark_bar_filled: a
            # deleted symbol's counters are neither readable nor meaningful,
            # and left alone they grow the blob forever.
            live = set(self.store.symbols)
            self._entry_blocks = {s: c for s, c in self._entry_blocks.items()
                                  if s in live}
            self.store.set_setting("entry_blocks", self._entry_blocks)
            self.store.set_setting("entry_blocks_since", self._entry_blocks_since)
            self._entry_blocks_dirty = False
        except Exception:
            pass

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
        rows = []
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
        self._entry_blocks_since = time.time()
        self._entry_blocks_dirty = True
        self._flush_entry_blocks()

    # ------------------------------------------------- scheduled re-optimize

    def reopt_status(self) -> dict[str, Any]:
        sys_cfg = self.store.system
        days = float(sys_cfg.auto_reopt_days or 0)
        every = (max(0.5, days) * 86400.0) if days > 0 else 0.0
        return {
            "enabled": bool(sys_cfg.auto_reopt) and days > 0,
            "every_days": days,
            "hour": int(sys_cfg.auto_reopt_hour),
            "weekday": int(sys_cfg.auto_reopt_weekday),
            "last_at": self._reopt_at,
            "next_at": (self._reopt_at + every) if self._reopt_at and every else 0.0,
        }

    def _maybe_schedule_reopt(self) -> None:
        """Fire a full portfolio re-optimization once per configured interval.

        Nothing here bypasses the usual apply path: it calls the same
        ``Optimizer.start(apply_best=True)`` a manual run uses, so every symbol
        still has to clear ``_slice_ok`` on both out-of-sample slices and
        ``_is_improvement`` before anything is written. A symbol whose fresh
        search is worse than what it already runs simply keeps its config.
        """
        sys_cfg = self.store.system
        optimizer = getattr(self.supervisor, "optimizer", None)
        if not sys_cfg.auto_reopt or optimizer is None:
            return
        days = float(sys_cfg.auto_reopt_days or 0)
        # <=0 means "interval disabled" (distinct from auto_reopt=false). The
        # old max(0.5, days) clamp turned an intentional 0 into a half-day
        # cadence, so the only way to park the scheduler was the master bool.
        if days <= 0:
            return
        every = max(0.5, days) * 86400.0
        now = time.time()
        if self._reopt_at <= 0:
            # First run ever: start the clock instead of firing at boot, so a
            # restart never kicks off an unexpected full sweep.
            self._reopt_at = now
            self.store.set_setting("auto_reopt_at", self._reopt_at)
            return
        weekday = int(sys_cfg.auto_reopt_weekday)
        # A preferred weekday recurs every 7 days no matter what ``every`` is
        # set to. If the last successful run happened to land on a different
        # day of the week than the preference (e.g. whatever day the bot
        # first ran on, or a week it caught up late), the raw interval and
        # the weekday permanently disagree: by the time ``every`` has fully
        # elapsed the preferred weekday has already passed for that cycle, so
        # it waits a full extra week and lands one day short again - the
        # configured day is never actually hit. A couple of days of early
        # tolerance lets the preferred weekday catch the window before the
        # raw interval technically elapses, locking the cadence onto it.
        tolerance = min(2 * 86400.0, every / 3.0) if 0 <= weekday <= 6 else 0.0
        if now - self._reopt_at < every - tolerance:
            return
        # Missing the exact weekday+hour once (bot offline through that whole
        # hour, market closed, etc.) used to mean waiting a full extra
        # ``every`` for the next match - the window never catches up on its
        # own. Two days past due is well past any single missed slot, so
        # drop the weekday/hour gate at that point and just run on the next
        # cycle instead of silently skipping a week (or more) of re-opt.
        catch_up = now - self._reopt_at - every >= 2 * 86400.0
        # Gated on the machine's own local clock, not the broker/server time:
        # server_now() used to depend on a detected MT5 offset that could
        # drift or be briefly wrong (e.g. a broker/cloud clock hiccup), which
        # made this fire on the wrong weekday. The System tab's day/hour
        # pickers should mean exactly what they say against Windows time.
        local = time.localtime(now)
        if not catch_up and 0 <= weekday <= 6 and local.tm_wday != weekday:
            return                       # wait for the preferred local weekday
        hour = int(sys_cfg.auto_reopt_hour)
        if not catch_up and 0 <= hour <= 23 and local.tm_hour != hour:
            return                       # wait for the preferred local hour
        if catch_up:
            LOG.emit("Haftalik yeniden optimizasyon: planlanan pencere kacirilmisti, "
                     "telafi olarak simdi baslatiliyor.", "OPT")
        if optimizer.busy:
            LOG.emit("Haftalik yeniden optimizasyon ertelendi: optimizer mesgul.", "OPT")
            return
        targets = [c.symbol for c in list(self.store.symbols.values()) if c.enabled]
        if not targets:
            return
        result = optimizer.start(targets, apply_best=True, source="scheduled")
        if not result.get("ok"):
            LOG.emit(f"Haftalik yeniden optimizasyon baslatilamadi: "
                     f"{result.get('error', '?')}", "OPT")
            return
        self._reopt_at = now
        self.store.set_setting("auto_reopt_at", self._reopt_at)
        LOG.emit(f"Haftalik yeniden optimizasyon basladi ({len(targets)} sembol) - "
                 f"sonuclar ayni dogrulama kapilarindan gececek, zorla uygulanmaz.", "OPT")

    # ------------------------------------------------------------ evaluation

    def _has_open_secondary_ticket(self, cfg: SymbolConfig) -> bool:
        return any(p["magic"] == cfg.magic and p["ticket"] in self._sec_tickets
                  for p in self._positions)

    def _evaluate_disabled(self, cfg: SymbolConfig, state: SymbolState,
                           server_now: float, account: dict[str, Any]) -> None:
        """Handle one ``cfg.enabled == False`` symbol for this cycle.

        A position can still be open under this magic (the user paused a
        symbol, not stopped-and-flattened it) - full skip (old behaviour)
        stops state.last_bar/atr from ever advancing again, and
        manage_positions()'s per-bar throttle (self._stop_bar vs last_bar)
        then never fires _update_stop for that ticket again: trail/BE/
        partial-TP freezes silently for good, with only the broker's own
        static stop left protecting it. allow_entry=False guarantees
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
            state.sec_signal = ""
            state.pending_bar_key = (0, 0)

    def _evaluate(self, cfg: SymbolConfig, state: SymbolState, server_now: float,
                  account: dict[str, Any], allow_entry: bool) -> bool:
        """Refresh state; return True when this symbol wants an entry this bar."""
        state.note = ""
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
            state.sec_signal = ""
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
        if cfg.has_secondary():
            sec_fresh = self._refresh_secondary(cfg, state)
        elif self._has_open_secondary_ticket(cfg):
            # ensemble_enabled/secondary_strategy can be toggled off (a plain
            # PATCH {"ensemble_enabled": false} - patch_symbol()'s guard only
            # tracks secondary_strategy/secondary_timeframe, not this flag)
            # while a secondary-opened ticket is still live. Fully stopping
            # the refresh below (old behaviour) freezes state.sec_last_bar/
            # sec_atr at whatever they were the instant this flipped -
            # manage_positions()'s per-bar throttle (self._stop_bar vs
            # sec_last_bar) then never advances again, silently freezing that
            # ticket's trail/BE/partial-TP for good. Keep refreshing instead;
            # _merge_signals() below already ignores state.sec_signal
            # whenever has_secondary() is False, so this can never arm a NEW
            # secondary entry - it only keeps the already-open one managed.
            sec_fresh = self._refresh_secondary(cfg, state)
        else:
            sec_fresh = False
            if state.sec_signal or state.sec_last_bar or state.sec_atr:
                state.sec_signal = ""
                state.sec_last_bar = 0
                state.sec_bars = None
                state.sec_atr = 0.0
        self._merge_signals(cfg, state, primary_fresh, sec_fresh)
        fresh = primary_fresh or sec_fresh
        # Keyed on the leg actually driving state.signal, not the combined
        # (primary_bar, sec_bar) pair. With the combined key, a secondary
        # signal sitting stale (unchanged for several of its own bars) got
        # re-armed for a fresh retry window every time the *primary* leg
        # closed an unrelated new bar - primary_fresh alone made ``fresh``
        # true, and the pair's primary half changing was enough to look like
        # a new bar_key. That let one real secondary signal get retried
        # indefinitely across many primary bars instead of the single live
        # bar the backtest gives it. Each leg now only rearms/matches off its
        # own bar timestamp.
        bar_key = (state.last_bar if state.signal_source == "primary" else state.sec_last_bar)
        driving_fresh = (
            (state.signal_source == "primary" and primary_fresh)
            or (state.signal_source == "secondary" and sec_fresh)
        )
        if driving_fresh and state.signal:
            state.pending_bar_key = (state.signal_source, bar_key)
        elif not state.signal:
            state.pending_bar_key = (0, 0)

        if not sess.open:
            state.note = f"seans disi ({sess.window})"
            # Clearing only ``state.signal`` left ``primary_signal``/``sec_signal``
            # (and therefore ``pending_bar_key``) untouched across the closure.
            # No new bar means no new bar_key either, so on the very next poll
            # ``_merge_signals`` resurrected ``state.signal`` from the still-set
            # primary_signal, matching the still-stale pending_bar_key - a signal
            # from just before the close could fire the instant the session
            # reopens, on whatever bar was still cached, before the first fresh
            # bar of the new session had even been fetched. Clearing the whole
            # signal chain here means reopening always starts from nothing.
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
            state.sec_signal = ""
            state.pending_bar_key = (0, 0)
            return False
        if not self.client.market_open(cfg.symbol):
            # Same staleness hazard as the sess.open branch above: with
            # trade_all_hours on, sess.open is true around the clock and this
            # is the only gate that actually catches an overnight index/
            # commodity halt, so it has to clear the whole signal chain too.
            state.note = "piyasa kapali / fiyat akmiyor"
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
            state.sec_signal = ""
            state.pending_bar_key = (0, 0)
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
            state.note = "bu barin sinyali zaten dolduruldu"
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

    def _refresh_signals(self, cfg: SymbolConfig, state: SymbolState, params: Params) -> bool:
        """Pull bars and recompute indicators when a new bar has closed."""
        now = time.time()
        due = self.client.server_now() >= state.next_bar_at
        stale = now - state.last_fetch > _STALE_BAR_REFRESH
        if not (due or stale or state.last_bar == 0):
            return False

        need = required_bars(params)
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
        # at the old floor, and 100% wrong for mtf_pullback, wavetrend_flip
        # and stoch_flip.
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

        state.bars_ready = len(bars)
        state.bars = bars
        tf_sec = timeframe_seconds(cfg.timeframe)
        state.next_bar_at = bars.last_closed_time + 2 * tf_sec + 2

        if bars.last_closed_time == state.last_bar:
            return False
        state.last_bar = bars.last_closed_time

        cache = IndicatorCache(bars.high, bars.low, bars.close, bars.time, tf_sec,
                               bars.open, bars.volume, self._cost_series(cfg, bars))
        sig: Signals = compute(cache, params)
        snap = sig.last()
        state.t3 = snap.get("t3", 0.0)
        state.t3_rising = snap.get("t3_rising", False)
        state.k = snap.get("k", 0.0)
        state.d = snap.get("d", 0.0)
        state.atr = snap.get("atr", 0.0)
        state.adx = snap.get("adx", 0.0)
        state.htf = int(snap.get("htf", 0))
        if snap.get("buy"):
            state.primary_signal = "buy"
        elif snap.get("sell"):
            state.primary_signal = "sell"
        else:
            state.primary_signal = ""
        if state.primary_signal:
            state.last_signal_at = time.time()
            LOG.emit(f"Sinyal {state.primary_signal.upper()} | K={state.k:.1f} D={state.d:.1f} "
                     f"ATR={state.atr:.5f} ADX={state.adx:.0f} HTF={state.htf:+d}",
                     "SIGNAL", cfg.symbol)
        return True

    # ------------------------------------------------------- second signal

    def _secondary_config(self, cfg: SymbolConfig) -> SymbolConfig:
        """``cfg`` with the stored secondary timeframe and parameters overlaid.

        Everything the secondary was validated with - its entry parameters *and*
        its stop/target/trail multipliers - has to travel together, otherwise the
        trade taken live is not the trade the walk-forward measured. Magic, lots,
        sessions and every other non-optimiser field stay the primary's, because
        the two signals share one symbol, one broker position limit and one
        risk budget.
        """
        # The old signature only tracked the secondary's own identity
        # (strategy/timeframe/updated_at), not the primary fields it starts
        # from below (magic, lots, sessions, ...). Editing one of those
        # through a plain PATCH left this cache serving a stale overlay until
        # the secondary itself happened to change. Comparing the full primary
        # dict is the only way to catch every field that could drift.
        payload = cfg.to_dict()
        sig = tuple(sorted(payload.items()))
        hit = self._sec_cfgs.get(cfg.symbol)
        if hit and hit[0] == sig:
            return hit[1]
        payload.update(cfg.secondary_params)          # already OPT_FIELDS-only
        payload["strategy"] = cfg.secondary_strategy
        payload["timeframe"] = cfg.secondary_timeframe
        built = SymbolConfig.from_dict(payload)
        self._sec_cfgs[cfg.symbol] = (sig, built)
        return built

    def _refresh_secondary(self, cfg: SymbolConfig, state: SymbolState) -> bool:
        """Same bar-close logic as the primary, on the secondary's timeframe."""
        sec = self._secondary_config(cfg)
        params = Params.from_config(sec)
        now = time.time()
        due = self.client.server_now() >= state.sec_next_bar_at
        stale = now - state.sec_last_fetch > _STALE_BAR_REFRESH
        if not (due or stale or state.sec_last_bar == 0):
            return False

        sec_need = required_bars(params)
        bars = self.client.bars(cfg.symbol, sec.timeframe, sec_need)
        state.sec_last_fetch = now
        # Same warmup floor as the primary leg above - the secondary signal
        # opens real positions on the same account and has no reason to run on
        # a shallower stack than the primary would accept.
        if bars is None or len(bars) < max(60, sec_need // 2):
            return False

        state.sec_bars = bars
        tf_sec = timeframe_seconds(sec.timeframe)
        state.sec_next_bar_at = bars.last_closed_time + 2 * tf_sec + 2
        if bars.last_closed_time == state.sec_last_bar:
            return False
        state.sec_last_bar = bars.last_closed_time

        cache = IndicatorCache(bars.high, bars.low, bars.close, bars.time, tf_sec,
                               bars.open, bars.volume, self._cost_series(sec, bars))
        snap = compute(cache, params).last()
        state.sec_atr = snap.get("atr", 0.0)
        if snap.get("buy"):
            state.sec_signal = "buy"
        elif snap.get("sell"):
            state.sec_signal = "sell"
        else:
            state.sec_signal = ""
        if state.sec_signal:
            state.last_signal_at = time.time()
            LOG.emit(f"Ikincil sinyal {state.sec_signal.upper()} "
                     f"({sec.strategy}/{sec.timeframe}) ATR={state.sec_atr:.5f}",
                     "SIGNAL", cfg.symbol)
        return True

    def _merge_signals(self, cfg: SymbolConfig, state: SymbolState,
                       primary_fresh: bool = False, sec_fresh: bool = False) -> None:
        """Combine both signals; disagreement cancels the bar for both of them.

        Invariant: a symbol never holds a buy and a sell view at once. Inside one
        family that is enforced bar-by-bar in ``strategy``; across the two
        ensemble signals it is enforced here, so an ensemble symbol can never do
        something a single-strategy symbol would refuse to do.

        When both legs hold a signal in the same direction, the one that just
        closed a bar on its own timeframe wins - a stale leg (holding a value
        from several of its own bars ago, only still sitting there because
        nothing has invalidated it yet) must not keep out-voting a leg that
        genuinely just fired. If neither refreshed this cycle (both are mid-bar
        retries, e.g. blocked earlier by spread/cooldown) the existing
        primary-first preference holds, matching prior behaviour.
        """
        primary, second = state.primary_signal, state.sec_signal
        if not cfg.has_secondary():
            state.signal = primary
            state.signal_source = "primary" if primary else ""
            return
        if primary and second and primary != second:
            if state.signal_source != "conflict":
                LOG.emit(f"Capraz sinyal (birincil {primary.upper()} / "
                         f"ikincil {second.upper()}) - islem atlandi.", "SIGNAL", cfg.symbol)
            state.signal = ""
            state.signal_source = "conflict"
            state.note = "capraz sinyal - atlandi"
            return
        if primary and second:
            if sec_fresh and not primary_fresh:
                state.signal, state.signal_source = second, "secondary"
            else:
                state.signal, state.signal_source = primary, "primary"
        elif primary:
            state.signal, state.signal_source = primary, "primary"
        elif second:
            state.signal, state.signal_source = second, "secondary"
        else:
            state.signal, state.signal_source = "", ""

    def _try_entry(self, base: SymbolConfig, state: SymbolState,
                   account: dict[str, Any]) -> None:
        state.entry_block = ""
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
        secondary = state.signal_source == "secondary"
        cfg = self._secondary_config(base) if secondary else base
        atr = state.sec_atr if secondary else state.atr
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
        if sessions.weekend_closed(base, self.client.server_now()):
            state.note = "hafta sonu kapali"
            state.signal = ""
            state.entry_block = "hafta_sonu"
            return

        tick = self.client.tick(cfg.symbol)
        if tick is None:
            state.note = "fiyat yok"
            state.entry_block = "fiyat_yok"
            return

        if cfg.max_spread_atr > 0 and tick["spread"] > atr * cfg.max_spread_atr:
            state.note = f"spread genis ({tick['spread'] / atr:.2f}xATR)"
            state.entry_block = "spread"
            return
        price_ref = tick["ask"] if side == "buy" else tick["bid"]
        if cfg.min_atr_ratio > 0 and price_ref > 0 and (atr / price_ref) < cfg.min_atr_ratio:
            state.note = "volatilite dusuk"
            state.entry_block = "volatilite"
            return

        allowed, ai_reason, scale = self.supervisor.gate(cfg, self.client.server_now())
        if not allowed:
            state.note = ai_reason
            state.entry_block = "ai_gate"
            return

        min_stop = self.client.min_stop_distance(cfg.symbol)
        # The hard stop. Always sent with the entry and never lifted: it is the
        # only protection that survives this process dying, and the broker's own
        # minimum distance is a floor on it, never a reason to skip it.
        sl_dist = max(atr * cfg.sl_atr_mult, min_stop)
        # No take-profit, ever. A trailing system decides when a move is over by
        # watching the move, not by naming a price in advance; a fixed target is
        # just a cap on the winners that pay for the losers. mt5client.open_market
        # reads tp <= 0 as "no take-profit level".
        tp_dist = 0.0

        # Optional live cost gate — off by default; optimizer already models cost.
        sys = self.store.system
        if sys.block_high_cost and sys.max_cost_pct_of_risk > 0:
            lot_probe, _ = self.risk.lot_for(cfg, sl_dist, account.get("balance", 0.0))
            if lot_probe > 0:
                r_value = sl_dist * self.client.money_per_price_unit(cfg.symbol, lot_probe)
                cost = cfg.commission_per_lot * lot_probe
                cost += tick["spread"] * self.client.money_per_price_unit(cfg.symbol, lot_probe)
                if r_value > 0 and (cost / r_value * 100.0) > sys.max_cost_pct_of_risk:
                    state.note = (f"maliyet yuksek "
                                  f"(%{cost / r_value * 100.0:.0f} > %{sys.max_cost_pct_of_risk:g})")
                    state.entry_block = "maliyet"
                    return

        lot, note = self.risk.lot_for(cfg, sl_dist, account.get("balance", 0.0), ai_scale=scale)
        if lot <= 0:
            state.note = f"lot hesaplanamadi ({note})"
            state.entry_block = "lot"
            return

        verdict = self.risk.can_open(cfg, side, lot, self._positions, account,
                                     sec_tickets=frozenset(self._sec_tickets))
        if not verdict.ok:
            state.note = verdict.reason
            state.entry_block = _risk_block_key(verdict.reason)
            return

        entry = tick["ask"] if side == "buy" else tick["bid"]
        sl = entry - sl_dist if side == "buy" else entry + sl_dist
        tp = 0.0 if tp_dist <= 0 else (entry + tp_dist if side == "buy" else entry - tp_dist)

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
        orphan_closed = False
        unresolved_ticket = False
        with self.entry_lock:
            live_cfg = self.store.symbols.get(base.symbol)
            if live_cfg is None or live_cfg.magic != base.magic:
                state.note = "sembol silindi/degisti - islem iptal"
                state.entry_block = "sembol_degisti"
                return
            result = self.client.open_market(
                cfg.symbol, side, lot, sl, tp, cfg.magic,
                slippage=self.store.system.slippage_points,
                comment=f"MicoFX {cfg.timeframe}",
            )
            if result.get("ok"):
                if not self._reload_positions():
                    # Fill reported ok but the book cannot be verified - do
                    # not treat [] as "no new ticket" (would open a ghost
                    # orphan-scan or skip tagging). Secondary without a
                    # broker ticket → scan window with pre-fill known set;
                    # with a ticket → tag it from the result alone.
                    if secondary:
                        if result.get("position"):
                            self._tag_secondary({int(result["position"])})
                        else:
                            unresolved_ticket = True
                            self._orphan_scan[cfg.symbol] = {
                                "magic": base.magic,
                                "known": sorted(before_tickets),
                                "since": time.time(),
                            }
                            self._save_orphan_scan()
                            LOG.emit("Ikincil sinyal islemi acildi ama pozisyon listesi "
                                     "dogrulanamadi - orphan tarama baslatildi.",
                                     "ERROR", cfg.symbol)
                elif secondary:
                    if result.get("position"):
                        # Tagged inside the same lock as the fill itself -
                        # moved here from after the lock's release because
                        # apply_secondary() also takes entry_lock and reads
                        # self._sec_tickets to decide whether a secondary
                        # position is open. With the tag written only after
                        # the lock released, a family-changing
                        # apply_secondary() call landing in that gap saw this
                        # brand new ticket as untagged and let the
                        # identity/exit rewrite through.
                        self._tag_secondary({int(result["position"])})
                    else:
                        # open_market() itself could not resolve which broker
                        # ticket this fill became. Diff same-magic tickets
                        # against the snapshot taken before this entry even
                        # started - retried a few times inside this same lock,
                        # since positions() can lag the fill by a beat on a
                        # slow broker. A single clean candidate confirmed this
                        # way is trustworthy enough to tag normally; ambiguity
                        # (0 or >1 candidates) is what actually needs the
                        # safety-close path below.
                        new_tickets: set[int] = set()
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
                                LOG.emit("Ikincil ticket cozumlemesi yarida kaldi - "
                                         "pozisyon listesi dogrulanamadi, orphan tarama "
                                         "baslatildi.", "ERROR", cfg.symbol)
                                new_tickets = set()
                                break
                        if unresolved_ticket:
                            pass
                        elif len(new_tickets) == 1:
                            self._tag_secondary(new_tickets)
                        elif not new_tickets:
                            unresolved_ticket = True
                            self._orphan_scan[cfg.symbol] = {
                                "magic": base.magic,
                                "known": sorted(after_tickets),
                                "since": time.time(),
                            }
                            self._save_orphan_scan()
                            LOG.emit("Ikincil sinyal islemi acildi ama pozisyon ticket'i "
                                     "cozulemedi (yeni ticket bulunamadi) - her dongude "
                                     "tekrar taranacak, primer parametreyle yonetilmeyecek.",
                                     "ERROR", cfg.symbol)
                        else:
                            # More than one same-magic ticket appeared since the fill -
                            # a second signal firing on this same lock, or a stale
                            # snapshot - we cannot tell which one is ours, so the safe
                            # move is closing all of them rather than guessing and
                            # leaving an untracked position running under the wrong
                            # strategy's exits.
                            gone, still = self._close_orphan_tickets(
                                new_tickets, "MicoFX cozulemeyen ikincil ticket")
                            if gone == new_tickets:
                                orphan_closed = True
                                LOG.emit(f"Ikincil sinyal islemi acildi ama ticket'i "
                                         f"cozulemedi - pozisyon(lar) {sorted(gone)} "
                                         f"guvenlik icin hemen kapatildi, sinyal tekrar "
                                         f"denenecek.", "ERROR", cfg.symbol)
                            else:
                                unresolved_ticket = True
                                self._orphan_tickets |= still
                                self._save_orphan_tickets()
                                if gone:
                                    LOG.emit(f"Ikincil sinyal islemi acildi, ticket'i "
                                             f"cozulemedi - {sorted(gone)} kapatildi ama "
                                             f"{sorted(still)} KAPATILAMADI/KISMI - her "
                                             f"dongude tekrar kapatma denenecek, primer "
                                             f"parametreyle yonetilmeyecek.",
                                             "ERROR", cfg.symbol)
                                else:
                                    LOG.emit(f"Ikincil sinyal islemi acildi, ticket'i "
                                             f"cozulemedi VE {sorted(still)} "
                                             f"kapatilamadi/kismi - her dongude tekrar "
                                             f"kapatma denenecek, primer parametreyle "
                                             f"yonetilmeyecek.", "ERROR", cfg.symbol)
        if orphan_closed:
            # Treat exactly like a failed entry (the position is flat again,
            # closed a moment after opening) - not the normal successful-fill
            # path below, which would record execution/cooldown/state.signal
            # bookkeeping for a "trade" that no longer exists.
            state.note = "ikincil ticket cozulemedi - guvenlik icin kapatildi"
            state.entry_block = "ikincil_cozulemedi_kapatildi"
            state.signal = ""
            state.signal_source = ""
            state.primary_signal = ""
            state.sec_signal = ""
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
            state.note = ("ikincil ticket cozulemedi - pozisyon acik kaldi, "
                          "otomatik tekrar denenecek")
            state.entry_block = "ikincil_cozulemedi_acik"
            return
        if not result.get("ok"):
            state.note = result.get("error", "emir hatasi")
            state.entry_block = "emir_hatasi"
            # Park on any verified-flat link refusal, not only TRADE_RETCODE_*
            # in AMBIGUOUS_RETCODES. order_send None / IPC last_error codes
            # (-10001 etc.) are outside that set but took the same verifier
            # path - without verified_unfilled they would still hammer every
            # poll. Retcode check kept as belt-and-suspenders.
            if result.get("verified_unfilled") or result.get("retcode") in AMBIGUOUS_RETCODES:
                self._link_backoff[base.symbol] = time.time() + LINK_BACKOFF_SEC
            # Verified-flat is the gate working: book readable, nothing filled,
            # symbol parked. WARN so fault scans do not treat a successful
            # refuse as a live Error (same reason pending-drop went WARN).
            # Still ERROR when the book itself is unreadable (ambiguous).
            _lvl = "WARN" if result.get("verified_unfilled") else "ERROR"
            LOG.emit(result.get("error", "emir hatasi"), _lvl, cfg.symbol)
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
                state.sec_signal = ""
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
                state.sec_signal = ""
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
        self._mark_bar_filled(cfg.symbol, state.signal_source,
                              state.sec_last_bar if secondary else state.last_bar)
        state.signal = ""
        state.signal_source = ""
        state.primary_signal = ""
        state.sec_signal = ""
        state.note = "islem acildi"
        state.entry_block = "acildi"
        LOG.emit(
            f"{side.upper()} {result['volume']:g} lot @ {result['price']:.5f} "
            f"SL={result['sl']:.5f} TP={result['tp']:.5f} | lot: {note}"
            f"{f' | ikincil {cfg.strategy}/{cfg.timeframe}' if secondary else ''}",
            "TRADE", cfg.symbol,
        )

    def _tag_secondary(self, tickets: set[int]) -> None:
        if not tickets:
            return
        self._sec_tickets |= {int(t) for t in tickets}
        self.store.set_setting("secondary_tickets", sorted(self._sec_tickets))

    def _save_orphan_tickets(self) -> None:
        self.store.set_setting("secondary_orphan_tickets", sorted(self._orphan_tickets))

    def _save_orphan_scan(self) -> None:
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

    def manage_positions(self, server_now: float) -> None:
        if not self.client.connected:
            # Caller should have bailed already; never prune tags / exposure
            # from an unverified empty book.
            return
        by_magic = {c.magic: c for c in list(self.store.symbols.values())}
        live = {p["ticket"] for p in self._positions}
        self._stop_bar = {t: v for t, v in self._stop_bar.items() if t in live}
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
                continue
            state = self.states.get(cfg.symbol)
            atr = state.atr if state else 0.0
            if pos["ticket"] in self._sec_tickets and cfg.secondary_strategy:
                # Opened by the second signal: manage it with the exits that
                # signal was validated with, on its own timeframe's ATR.
                cfg = self._secondary_config(cfg)
                atr = state.sec_atr if state and state.sec_atr > 0 else atr

            # weekend_closed() already gated new entries; it never touched a
            # position that was already open going into the weekend. Crypto
            # is exempt (weekend_closed() itself returns False for it).
            if sessions.weekend_closed(cfg, server_now) and pos["ticket"] not in self._weekend_pending:
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
                fill: dict[str, Any] = {}
                if self._close_tracked(pos, "MicoFX hafta sonu", "exit", fill=fill):
                    filled = float(fill.get("volume", pos["volume"]))
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
            if self.store.system.daily_loss_flatten and self._symbol_daily_halt(cfg):
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
            if (sessions.should_flatten(cfg, server_now, self.store.system.trade_all_hours)
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
                is_secondary = pos["ticket"] in self._sec_tickets
                bars = None
                last_bar = 0
                if state is not None:
                    bars = state.sec_bars if is_secondary else state.bars
                    last_bar = state.sec_last_bar if is_secondary else state.last_bar
                # Secondary tickets must use the secondary ATR they were validated
                # with. Falling back to the primary ATR (different TF / regime)
                # silently warps BE, trail and partial distances. ``<= 0`` alone
                # is not fail-closed for NaN (NaN <= 0 is False) - without
                # isfinite() a NaN'd sec_atr slipped past this guard and got
                # trailed on the silently-substituted primary atr anyway.
                if is_secondary and (state is None or not math.isfinite(state.sec_atr)
                                     or state.sec_atr <= 0):
                    continue
                ticket = pos["ticket"]
                if last_bar and last_bar != self._stop_bar.get(ticket):
                    # Marked done only once _update_stop reports the bar
                    # settled. It answers False when the live quote - not the
                    # closed bar the trail level comes from - is what blocked
                    # the move, and marking the bar regardless silently threw
                    # away an earned trail update until the next bar closed.
                    if self._update_stop(cfg, pos, atr, bars):
                        self._stop_bar[ticket] = last_bar

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
            gone = self.execution.track(self._positions)
            if not gone:
                return
            deals = self.client.deals_since(time.time() - 7200)
            for report in self.execution.reap(gone, deals, self.client):
                self._log_broker_exit(report)
            self.execution.forget(gone)
        except Exception as exc:                  # never let diagnostics stop the loop
            LOG.emit(f"Gerceklesme olcumu hatasi: {exc}", "WARN")

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
        profit = report["profit"]
        detail = (f"{report['label'].capitalize()} ile kapandi #{report['ticket']} "
                  f"@ {report['price']:g} ({report['volume']:g} lot) kar={profit:.2f}")
        if report["reason"] == execution.DEAL_REASON_SO:
            LOG.emit(detail, "WARN", report["symbol"])
        else:
            LOG.emit(detail, "TRADE", report["symbol"])

    def _apply_pending_exits(self) -> None:
        """Land exit/risk params an optimizer apply() held back while a position was open.

        ``Optimizer.apply()``/``_apply_secondary_locked()`` store the held-back
        fields in ``cfg.pending_exit_patch``/``cfg.pending_secondary_exit_patch``
        instead of applying them immediately. This is the other half of that
        promise: once the relevant position is no longer open, write them for
        real. Runs every cycle - cheap (in-memory dict lookups against
        ``self._positions``, already refreshed this cycle) and self-correcting
        if a cycle is missed.
        """
        if not self._positions:
            open_magics: set[int] = set()
            sec_open_magics: set[int] = set()
        else:
            open_magics = {p["magic"] for p in self._positions}
            sec_open_magics = {p["magic"] for p in self._positions
                               if p["ticket"] in self._sec_tickets or p["ticket"] in self._orphan_tickets}
        # A zero-candidate orphan-scan window (H1) is genuinely invisible to
        # self._positions - that is the entire reason it exists - so without
        # this, this magic reads as flat here even though a fill may still
        # turn up, and both the primary and secondary held-back exit/risk
        # patches would land on a position that was never actually confirmed
        # closed. Same risk class Optimizer.apply()/apply_secondary() already
        # guard for on the write side; this is the corresponding read-side
        # gap on the "did it ever actually go flat" check.
        for entry in self._orphan_scan.values():
            magic = int(entry.get("magic", -1))
            open_magics.add(magic)
            sec_open_magics.add(magic)
        # Same lock optimizer.apply()/web PATCH hold across their own
        # open-position check + write - without it, a concurrent apply() on
        # the web thread could land a fresh patch (correctly clearing
        # pending_exit_patch) in the gap between this method reading the OLD
        # cfg snapshot and writing it, and this call's stale pending patch
        # would silently overwrite that fresh one right back.
        with self.entry_lock:
            for cfg in list(self.store.symbols.values()):
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
                        # Only the bad patch is cleared - the secondary block
                        # below still gets its turn this cycle.
                        updated = self.store.update_symbol(cfg.symbol, {"pending_exit_patch": {}})
                        # WARN, not ERROR: dropping a stale/poisoned pending
                        # patch is the gate working as designed. ERROR made
                        # fault scans treat a successful refuse as a live
                        # failure (and the line persists on disk forever).
                        LOG.emit(f"{cfg.symbol}: bekletilen cikis parametresi gecersiz "
                                 f"({bad}) - uygulanmadi, mevcut ayar korundu.",
                                 "WARN", cfg.symbol)
                    else:
                        updated = self.store.update_symbol(cfg.symbol,
                                                           {**pending, "pending_exit_patch": {}})
                        if updated is not None:
                            LOG.emit(f"{cfg.symbol}: bekletilen cikis/risk parametreleri "
                                     f"({', '.join(sorted(pending))}) artik acik pozisyon yok, "
                                     f"uygulandi.", "OPT", cfg.symbol)
                    if updated is not None:
                        cfg = updated
                if cfg.pending_secondary_exit_patch and cfg.magic not in sec_open_magics:
                    pending_sec = dict(cfg.pending_secondary_exit_patch)
                    merged_params = {**cfg.secondary_params, **pending_sec}
                    # Validated on the MERGED result, not on the patch alone:
                    # the patch is applied over the existing secondary_params,
                    # so what has to be usable is what the merge produces -
                    # that is the dict engine.py builds the secondary signal's
                    # exit payload from.
                    bad_sec = invalid_exit_param(merged_params)
                    if bad_sec:
                        self.store.update_symbol(cfg.symbol,
                                                 {"pending_secondary_exit_patch": {}})
                        LOG.emit(f"{cfg.symbol}: bekletilen ikincil cikis parametresi gecersiz "
                                 f"({bad_sec}) - uygulanmadi, mevcut ayar korundu.",
                                 "WARN", cfg.symbol)
                    else:
                        self.store.update_symbol(cfg.symbol, {
                            "secondary_params": merged_params, "pending_secondary_exit_patch": {},
                        })
                        LOG.emit(f"{cfg.symbol}: bekletilen ikincil cikis/risk parametreleri "
                                 f"({', '.join(sorted(pending_sec))}) artik acik ikincil pozisyon "
                                 f"yok, uygulandi.", "OPT", cfg.symbol)

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
        return ok

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
        # Once the stop has been ratcheted past entry - by the trail, on this
        # or any earlier bar - the live-quote min_stop clamp below must never
        # be allowed to put it back on the losing side. That clamp exists to
        # respect the broker's distance rule, not to hand back protection the
        # trade has already earned. There is no separate breakeven step: the
        # trail target is ``ref - trail_step_atr * atr``, so it is above entry
        # exactly when profit_dist exceeds ``trail_step_atr * atr`` - true
        # regardless of trail_start_atr, which only decides how early the
        # trail starts tightening the stop below entry. A config with
        # trail_start_atr <= trail_step_atr is legal and reaches breakeven at
        # the same point; see SymbolConfig's note.
        breakeven_locked = current_sl != 0 and (current_sl >= entry if is_buy else current_sl <= entry)

        if cfg.trail_start_atr > 0 and profit_dist >= atr * cfg.trail_start_atr:
            # ATR-based trailing (always computed as the baseline / fallback)
            trail_atr = ref - atr * cfg.trail_step_atr if is_buy else ref + atr * cfg.trail_step_atr
            trail = trail_atr

            # Structure-based or hybrid trailing (opt-in via cfg.trail_mode)
            if cfg.trail_mode in ("structure", "hybrid"):
                if bars is None:
                    state = self.states.get(cfg.symbol)
                    bars = state.bars if state else None
                if bars is not None and hasattr(bars, "low") and len(bars.low) > cfg.trail_lookback:
                    lookback = max(3, cfg.trail_lookback)
                    if is_buy:
                        swings = ind.swing_lows(bars.low, lookback)
                        struct_sl = swings[-1] - atr * 0.15  # small buffer below swing low
                    else:
                        swings = ind.swing_highs(bars.high, lookback)
                        struct_sl = swings[-1] + atr * 0.15  # small buffer above swing high

                    if cfg.trail_mode == "hybrid":
                        # Use the tighter of ATR trail and structure trail
                        trail = max(trail_atr, struct_sl) if is_buy else min(trail_atr, struct_sl)
                    else:
                        trail = struct_sl

            if target is None or (trail > target if is_buy else trail < target):
                target = trail

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
        step = trail_min_step(min_stop, atr, cfg.trail_step_atr)
        if current_sl != 0 and (target - current_sl < step if is_buy else current_sl - target < step):
            return settled
        # The position's real initial risk is max(atr*sl_atr_mult, min_stop) -
        # open_market sizes it that way (see the entry path above) whenever the
        # broker's own floor is wider than the ATR distance. Comparing against
        # the bare ATR number here was tighter than the SL actually placed, so
        # on any symbol where min_stop binds this could refuse a trail update
        # that was still a genuine improvement over the real original stop.
        original_risk = max(atr * cfg.sl_atr_mult, min_stop)
        if is_buy and target <= entry - original_risk:
            return settled
        if not is_buy and target >= entry + original_risk:
            return settled

        if self.client.modify_position(pos["ticket"], target, pos["tp"], cfg.symbol):
            LOG.emit(f"SL guncellendi -> {target:.5f} (kar {profit_dist / atr:.2f}xATR)",
                     "TRADE", cfg.symbol)
            return True
        # A rejected modify (requote, momentary "invalid stops", a blip in the
        # trade server) must not cost the position its trail for the rest of
        # the bar - that is exactly the update the trade earned.
        return False

    # ---------------------------------------------------------------- reports

    def refresh_account(self, force: bool = False) -> dict[str, Any]:
        now = time.time()
        if not force and self._account and now - self._account_at < _ACCOUNT_TTL:
            return self._account
        account = self.client.account()
        if account:
            self._account = account
            self._account_at = now
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
        by_magic = {c.magic: c for c in list(self.store.symbols.values())}
        out = []
        for pos in self.client.positions():
            cfg = by_magic.get(pos["magic"])
            item = dict(pos)
            item["managed"] = cfg is not None
            item["config_symbol"] = cfg.symbol if cfg else pos["symbol"]
            item["group"] = cfg.group if cfg else "-"
            out.append(item)
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
        if cfg.symbol_daily_loss_pct <= 0:
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

    def _handle_daily_rollover(self, server_now: float, balance: float) -> None:
        if self.risk.daily.rollover(server_now, balance):
            # New broker day - every symbol-level sticky halt from yesterday
            # is stale, same as DailyGuard.loss_halted resetting itself.
            if self._symbol_halted:
                self._symbol_halted = {}
                self._save_symbol_halted()

    def day_stats(self, max_age: float = 5.0) -> dict[str, Any]:
        """Closed-trade totals for the current local (Windows) day, per symbol."""
        if self._day_cache and time.time() - self._day_cache_at < max_age:
            return self._day_cache
        guard = self.risk.daily
        # Raw MT5 deal timestamps are naive epochs encoding the broker's own
        # wall-clock reading (not true UTC) - the same naive-epoch encoding
        # calendar.timegm() below produces from day_key's local calendar date,
        # so the two line up as long as the broker's clock and this machine's
        # local clock read the same wall-clock time (true for this setup).
        day_start = self.client.server_now() - 86400
        if guard.day_key:
            try:
                day_start = calendar.timegm(time.strptime(guard.day_key, "%Y-%m-%d"))
            except (ValueError, OverflowError):
                pass

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

    def snapshot(self) -> dict[str, Any]:
        account = self.refresh_account()
        positions = self.positions_view()
        capacity = self.risk.capacity(positions, account,
                                      {s: st.atr for s, st in list(self.states.items())})
        equity = float(account.get("equity", 0.0))
        return {
            "bot": {
                "running": self.running,
                "watching": self.watching,
                "cycle": self.cycle_count,
                "last_cycle_at": self.last_cycle_at,
                "last_cycle_ms": round(self.last_cycle_ms, 1),
                "last_error": self.last_error,
                "poll_interval_sec": self.store.system.poll_interval_sec,
            },
            "mt5": {
                "connected": self.client.connected,
                "error": self.client.last_error,
                "server_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.client.server_now())),
                **self.client.terminal_flags(),
            },
            "account": account,
            "day": {
                **self.day_stats(),
                "pnl_pct": round(self.risk.daily.pnl_pct(equity), 2),
                "floating": round(float(account.get("profit", 0.0)), 2),
            },
            "capacity": capacity,
            "reopt": self.reopt_status(),
            "execution": self.execution.stats(),
            "positions": positions,
            "states": {s: st.as_dict() for s, st in list(self.states.items())},
            "ai": self.supervisor.status(),
        }
