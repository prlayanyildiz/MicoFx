from __future__ import annotations

import calendar
import threading
import time
from typing import Any

from . import backtest, indicators as ind, sessions
from .logbus import LOG
from .models import SymbolConfig, is_scalp_strategy, strategy_allows_timeframe
from .mt5client import MT5Client, NON_RETRYABLE_RETCODES, timeframe_seconds
from .execution import ExecutionMonitor
from .risk import RiskManager
from .store import Store
from .strategy import IndicatorCache, Params, Signals, compute, required_bars
from .supervisor import Supervisor

_STALE_BAR_REFRESH = 45.0   # force a bar refresh at least this often
_ACCOUNT_TTL = 1.0

# A cooldown is meant to stop the same setup re-firing on the next bar or two,
# so it belongs on the strategy's own clock. The stored seconds were written for
# the M5-and-slower presets; left alone they would silently cost an M1 config
# five bars of opportunity per fill. Capped, never extended - a config that asks
# for a short pause still gets exactly what it asks for.
_COOLDOWN_BARS = 2
# Swing / higher-TF families already wait a full bar between signals; one bar of
# post-fill silence is enough. Two H1 bars would idle the symbol for two hours.
_COOLDOWN_BARS_SWING = 1


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
                 "pending_bar_key")

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
        self._partials: dict[int, dict[str, float]] = {
            int(k): {"rungs": float(v.get("rungs", 0.0)), "orig": float(v.get("orig", 0.0)),
                     "done": float(v.get("done", 0.0))}
            for k, v in (store.get_setting("partial_state") or {}).items()
            if str(k).isdigit() and isinstance(v, dict) and float(v.get("orig", 0.0)) > 0
        }
        # Ensemble bookkeeping: the overlaid config per symbol, and which open
        # tickets came from the secondary signal (persisted, because positions
        # outlive the process and must keep being managed by the exit rules they
        # were opened under).
        self._sec_cfgs: dict[str, tuple[tuple, SymbolConfig]] = {}
        self._sec_tickets: set[int] = {
            int(t) for t in (store.get_setting("secondary_tickets") or []) if str(t).isdigit()
        }
        self._reopt_at = float(store.get_setting("auto_reopt_at", 0.0) or 0.0)

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
            if close_positions if close_positions is not None else self.store.system.close_on_stop:
                closed = self.close_all()
        if was_trading:
            LOG.emit(f"Bot durduruldu - izleme devam ediyor."
                     f"{f' {closed} pozisyon kapatildi.' if closed else ''}", "INFO")
        return {"ok": True, "running": False, "closed": closed, "message": "Bot durduruldu."}

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
        """Stop trading and flatten everything the bot owns."""
        self.stop(close_positions=False)
        closed = self.close_all()
        LOG.emit(f"ACIL DURDURMA: {closed} pozisyon kapatildi.", "WARN")
        return {"ok": True, "closed": closed}

    def close_all(self, symbol: str | None = None) -> int:
        magics = {c.magic for c in list(self.store.symbols.values())}
        return self.client.close_all(magics=magics, symbol=symbol)

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

        if self.cycle_count % 60 == 0:
            detected = self.client.detect_server_offset()
            if detected is not None and detected != self.store.system.server_utc_offset:
                self.store.update_system({"server_utc_offset": detected})
                LOG.emit(f"Sunucu saat farki guncellendi: UTC{detected:+d}", "INFO")
        self.client.set_server_offset(self.store.system.server_utc_offset)

        server_now = self.client.server_now()
        self.risk.daily.rollover(server_now, account.get("balance", 0.0))

        self._positions = self.client.positions()
        if not self.client.connected:
            # positions() itself flips this False when mt5.positions_get()
            # fails mid-cycle (disconnect after the ensure() check above
            # already passed) - self._positions is then an unreliable empty
            # list, not "flat". Bail before manage_positions/entries act on
            # it; the next cycle's ensure() will reconnect first.
            return
        self._reap_execution()
        # Unconditional: this only manages positions already open (trail/BE/
        # partial/session-flatten/day-end-flatten), never opens new ones.
        # Gating it on _trading meant that with close_on_stop=false (the
        # default - a stopped bot does not close what is already open) any
        # position still open while stopped sat completely unmanaged: no
        # trailing, no breakeven, no forced flatten near session/day close.
        # Only the broker-native SL/TP kept protecting it. New entries are
        # still gated separately below via allow_entry.
        self.manage_positions(server_now)

        guard = self.risk.daily.check(account.get("equity", 0.0), self.store.system)
        if self.supervisor.due():
            try:
                self.supervisor.review(self.risk.daily.pnl_pct(account.get("equity", 0.0)))
            except Exception as exc:
                LOG.emit(f"AI denetleyici hatasi: {exc}", "ERROR")

        self._maybe_schedule_reopt()

        allow_entry = self._trading and guard.ok
        # Two-pass cycle: first refresh every symbol, then fill free slots in
        # priority order so a weak signal does not steal the last seat from a
        # stronger one when several bars close in the same poll.
        ready: list[SymbolConfig] = []
        for cfg in list(self.store.symbols.values()):
            state = self.states.setdefault(cfg.symbol, SymbolState(cfg.symbol))
            if not cfg.enabled:
                state.note = "kapali"
                # Same stale-signal hazard as the session/market_open gates:
                # clearing only state.signal leaves primary_signal/pending_bar_key
                # standing, so re-enabling before a new bar closes could revive
                # and fire a signal from before the symbol was disabled.
                state.signal = ""
                state.signal_source = ""
                state.primary_signal = ""
                state.sec_signal = ""
                state.pending_bar_key = (0, 0)
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
                    # account was a single snapshot taken at the top of this
                    # cycle - if that entry just filled, every later symbol in
                    # this same ready list would otherwise size/margin-check
                    # itself against margin the fill above already spent.
                    account = self.refresh_account(force=True) or account
                except Exception as exc:
                    state.note = f"hata: {exc}"
                    LOG.emit(f"Giris hatasi: {exc}", "ERROR", cfg.symbol)

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
        if now - self._reopt_at < every:
            return
        broker = time.gmtime(self.client.server_now())
        weekday = int(sys_cfg.auto_reopt_weekday)
        if 0 <= weekday <= 6 and broker.tm_wday != weekday:
            return                       # wait for the preferred broker-time weekday
        hour = int(sys_cfg.auto_reopt_hour)
        if 0 <= hour <= 23 and broker.tm_hour != hour:
            return                       # wait for the preferred broker-time hour
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
        else:
            sec_fresh = False
            if state.sec_signal or state.sec_last_bar:
                state.sec_signal = ""
                state.sec_last_bar = 0
                state.sec_bars = None
        self._merge_signals(cfg, state, primary_fresh, sec_fresh)
        fresh = primary_fresh or sec_fresh
        bar_key = (state.last_bar, state.sec_last_bar)
        if fresh and state.signal:
            # Claim the retry slot the instant a fresh signal appears, before
            # any gate below gets a chance at it. Marking this after those
            # gates (allow_entry/should_flatten/cooldown/symbol_halt) meant a
            # signal that was fresh but blocked by one of them on this exact
            # poll never got marked pending at all - fresh only holds for one
            # poll per bar, so every later poll fell through to "not fresh,
            # nothing pending" and the signal was lost for the rest of the bar
            # regardless of whether the block itself cleared seconds later.
            state.pending_bar_key = bar_key
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
        if state.pending_bar_key == bar_key:
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
        if bars is None or len(bars) < 60:
            state.note = "yeterli bar yok"
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

        bars = self.client.bars(cfg.symbol, sec.timeframe, required_bars(params))
        state.sec_last_fetch = now
        if bars is None or len(bars) < 60:
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
        side = state.signal
        secondary = state.signal_source == "secondary"
        cfg = self._secondary_config(base) if secondary else base
        atr = state.sec_atr if secondary else state.atr
        if atr <= 0:
            state.note = "ATR yok"
            return

        # Scalp families (micro_rev/burst) only belong on M1/M5. A leftover
        # M15/H1 scalp config would burn the account on cost geometry the
        # walk-forward never validated for that bar size. Same custom map the
        # search/apply used, not always the shipped default - checking against
        # the wrong table here would refuse (or wrongly allow) a pairing the
        # optimizer itself judged by different rules.
        tf_allow = self.store.opt_params().get("strategy_timeframes")
        allow = tf_allow if isinstance(tf_allow, dict) else None
        if not strategy_allows_timeframe(cfg.strategy, cfg.timeframe, allow):
            state.note = f"{cfg.strategy}/{cfg.timeframe} eslesmesi yasak"
            state.signal = ""
            return

        # Last mile before the order. The session gate already refuses weekends,
        # but this is the one call that actually spends money, so it does not
        # take that on trust.
        if sessions.weekend_closed(base, self.client.server_now()):
            state.note = "hafta sonu kapali"
            state.signal = ""
            return

        tick = self.client.tick(cfg.symbol)
        if tick is None:
            state.note = "fiyat yok"
            return

        if cfg.max_spread_atr > 0 and tick["spread"] > atr * cfg.max_spread_atr:
            state.note = f"spread genis ({tick['spread'] / atr:.2f}xATR)"
            return
        price_ref = tick["ask"] if side == "buy" else tick["bid"]
        if cfg.min_atr_ratio > 0 and price_ref > 0 and (atr / price_ref) < cfg.min_atr_ratio:
            state.note = "volatilite dusuk"
            return

        allowed, ai_reason, scale = self.supervisor.gate(cfg, self.client.server_now())
        if not allowed:
            state.note = ai_reason
            return

        min_stop = self.client.min_stop_distance(cfg.symbol)
        sl_dist = max(atr * cfg.sl_atr_mult, min_stop)
        # A zero TP multiple is the "hard stop + trail only" exit mode: the order
        # goes out with no take-profit level, so nothing but the trailing stop
        # can close a winner. Without the branch the max() floor turned it into a
        # target one and a half stop-distances wide, which is the opposite of
        # letting a trend run. mt5client.open_market already reads tp <= 0 as
        # "no take-profit", so 0.0 is passed through untouched.
        tp_dist = max(atr * cfg.tp_atr_mult, min_stop * 1.5) if cfg.tp_atr_mult > 0 else 0.0

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
                    return

        lot, note = self.risk.lot_for(cfg, sl_dist, account.get("balance", 0.0), ai_scale=scale)
        if lot <= 0:
            state.note = f"lot hesaplanamadi ({note})"
            return

        verdict = self.risk.can_open(cfg, side, lot, self._positions, account,
                                     sec_tickets=frozenset(self._sec_tickets))
        if not verdict.ok:
            state.note = verdict.reason
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
        with self.entry_lock:
            live_cfg = self.store.symbols.get(base.symbol)
            if live_cfg is None or live_cfg.magic != base.magic:
                state.note = "sembol silindi/degisti - islem iptal"
                return
            result = self.client.open_market(
                cfg.symbol, side, lot, sl, tp, cfg.magic,
                slippage=self.store.system.slippage_points,
                comment=f"MicoFX {cfg.timeframe}",
            )
            if result.get("ok"):
                self._positions = self.client.positions()
        if not result.get("ok"):
            state.note = result.get("error", "emir hatasi")
            LOG.emit(result.get("error", "emir hatasi"), "ERROR", cfg.symbol)
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
        state.signal = ""
        state.signal_source = ""
        state.primary_signal = ""
        state.sec_signal = ""
        state.note = "islem acildi"
        if secondary and result.get("position"):
            # Tag the exact position the fill resolved to (deal.position_id,
            # not a before/after positions() diff) so the exit rules keep
            # matching the entry that opened it, even after a restart.
            self._tag_secondary({int(result["position"])})
        LOG.emit(
            f"{side.upper()} {result['volume']:g} lot @ {result['price']:.5f} "
            f"SL={result['sl']:.5f} TP={result['tp']:.5f} | lot: {note}"
            f"{f' | ikincil {cfg.strategy}/{cfg.timeframe}' if secondary else ''}",
            "TRADE", cfg.symbol,
        )

    def _save_partials(self) -> None:
        self.store.set_setting(
            "partial_state",
            {str(t): v for t, v in self._partials.items()})

    def _tag_secondary(self, tickets: set[int]) -> None:
        if not tickets:
            return
        self._sec_tickets |= {int(t) for t in tickets}
        self.store.set_setting("secondary_tickets", sorted(self._sec_tickets))

    # ---------------------------------------------------- position management

    def manage_positions(self, server_now: float) -> None:
        by_magic = {c.magic: c for c in list(self.store.symbols.values())}
        live = {p["ticket"] for p in self._positions}
        self._stop_bar = {t: v for t, v in self._stop_bar.items() if t in live}
        # forget scale-out bookkeeping whose position is gone
        pruned = {t: v for t, v in self._partials.items() if t in live}
        if pruned != self._partials:
            self._partials = pruned
            self._save_partials()
        if self._sec_tickets - live:
            self._sec_tickets &= live
            self.store.set_setting("secondary_tickets", sorted(self._sec_tickets))
        for pos in self._positions:
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

            if sessions.should_flatten(cfg, server_now, self.store.system.trade_all_hours):
                if self._close_tracked(pos, "MicoFX seans kapanis", "exit"):
                    LOG.emit("Seans kapanisi: pozisyon kapatildi.", "TRADE", cfg.symbol)
                continue
            if sessions.day_end_close(server_now, self.store.system.day_end_flatten_min):
                if self._close_tracked(pos, "MicoFX gun sonu", "exit"):
                    LOG.emit("Gun sonu: pozisyon kapatildi.", "TRADE", cfg.symbol)
                continue

            if cfg.max_bars_in_trade > 0:
                held = server_now - pos["time"]
                if held > cfg.max_bars_in_trade * timeframe_seconds(cfg.timeframe):
                    if self._close_tracked(pos, "MicoFX zaman stop", "exit"):
                        LOG.emit(f"Zaman stopu ({cfg.max_bars_in_trade} bar) ile kapatildi.",
                                 "TRADE", cfg.symbol)
                    continue

            if cfg.stale_exit_ratio > 0 and cfg.max_bars_in_trade > 0:
                held = server_now - pos["time"]
                bar_sec = timeframe_seconds(cfg.timeframe)
                stale_limit = cfg.max_bars_in_trade * bar_sec * cfg.stale_exit_ratio
                if held > stale_limit and pos.get("profit", 0) + pos.get("swap", 0) < 0:
                    if self._close_tracked(pos, "MicoFX erken zarar kapanisi", "exit"):
                        LOG.emit(f"Erken zarar kapanisi: {held / bar_sec:.0f} bar zararda, kapatildi.",
                                 "TRADE", cfg.symbol)
                    continue

            if atr > 0:
                is_secondary = pos["ticket"] in self._sec_tickets
                bars = None
                last_bar = 0
                if state is not None:
                    bars = state.sec_bars if is_secondary else state.bars
                    last_bar = state.sec_last_bar if is_secondary else state.last_bar
                # Secondary tickets must use the secondary ATR they were validated
                # with. Falling back to the primary ATR (different TF / regime)
                # silently warps BE, trail and partial distances.
                if is_secondary and (state is None or state.sec_atr <= 0):
                    continue
                ticket = pos["ticket"]
                if last_bar and last_bar != self._stop_bar.get(ticket):
                    self._stop_bar[ticket] = last_bar
                    self._update_stop(cfg, pos, atr, bars)

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
            self.execution.reap(gone, deals, self.client)
            self.execution.forget(gone)
        except Exception as exc:                  # never let diagnostics stop the loop
            LOG.emit(f"Gerceklesme olcumu hatasi: {exc}", "WARN")

    def _close_tracked(self, pos: dict[str, Any], comment: str, leg: str,
                       volume: float | None = None) -> bool:
        """``close_position`` that also books the requested-vs-filled sample."""
        fill: dict[str, Any] = {}
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
                     bars: Any = None) -> None:
        tick = self.client.tick(cfg.symbol)
        if tick is None:
            return
        is_buy = pos["side"] == "buy"
        # Broker distance checks need the live bid/ask; BE/trail *math* must use
        # the closed bar's close - same input the walk-forward advances on. Using
        # the tick here used to ratchet stops on wicks the backtest never saw.
        live = tick["bid"] if is_buy else tick["ask"]
        if bars is not None and hasattr(bars, "close") and len(bars.close) > 0:
            ref = float(bars.close[-1])
        else:
            ref = live
        entry = pos["price_open"]
        profit_dist = (ref - entry) if is_buy else (entry - ref)
        # _take_partial computes its own wick-based distance (bars.high/low)
        # independently of profit_dist's sign, mirroring how the backtest
        # ladder books a rung the instant a bar's wick touches it - gating
        # this call on close-based profit_dist > 0 meant a bar that wicked
        # deep into profit and closed back at/under breakeven silently never
        # took the partial live, while the backtest that trained partial_tp_r
        # banked it every time.
        if self._take_partial(cfg, pos, atr, profit_dist, bars):
            return
        if profit_dist <= 0:
            return

        min_stop = self.client.min_stop_distance(cfg.symbol)
        current_sl = pos["sl"]
        target: float | None = None

        if cfg.breakeven_atr > 0 and profit_dist >= atr * cfg.breakeven_atr:
            # Exact entry, then the shared min_stop clamp below - matches BT.
            lock = entry
            if current_sl == 0 or (lock > current_sl if is_buy else lock < current_sl):
                target = lock

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
            return

        # Respect the broker's stop distance against the *live* quote and only
        # push the stop forward.
        limit = live - min_stop if is_buy else live + min_stop
        target = min(target, limit) if is_buy else max(target, limit)
        step = max(min_stop * 0.25, atr * cfg.trail_step_atr * 0.1)
        if current_sl != 0 and (target - current_sl < step if is_buy else current_sl - target < step):
            return
        # The position's real initial risk is max(atr*sl_atr_mult, min_stop) -
        # open_market sizes it that way (see the entry path above) whenever the
        # broker's own floor is wider than the ATR distance. Comparing against
        # the bare ATR number here was tighter than the SL actually placed, so
        # on any symbol where min_stop binds this could refuse a trail update
        # that was still a genuine improvement over the real original stop.
        original_risk = max(atr * cfg.sl_atr_mult, min_stop)
        if is_buy and target <= entry - original_risk:
            return
        if not is_buy and target >= entry + original_risk:
            return

        if self.client.modify_position(pos["ticket"], target, pos["tp"], cfg.symbol):
            LOG.emit(f"SL guncellendi -> {target:.5f} (kar {profit_dist / atr:.2f}xATR)",
                     "TRADE", cfg.symbol)

    def _take_partial(self, cfg: SymbolConfig, pos: dict[str, Any], atr: float,
                      profit_dist: float, bars: Any = None) -> bool:
        """Walk the scale-out ladder, mirroring ``backtest._ladder`` exactly.

        Every rung's fraction is measured against the volume the position
        *opened* with, not against what is left, so the live blended R matches
        the number the walk-forward measured. ``done`` is set to the rung count
        once no further rung can be filled (broker minimum volume), which stops
        the engine re-probing the same position on every cycle.

        ``backtest._ladder``'s caller books a rung the instant the closed bar's
        *high/low* reaches it - a wick fill, the same way the SL/TP touch check
        works. Using only ``profit_dist`` (built from the bar's close) here was
        stricter than that: a bar that wicked through a rung and closed back
        below it would bank in the walk-forward but never fire live, quietly
        inflating the R the optimizer credits ``partial_tp_r`` with. Falling
        back to ``profit_dist`` when bars are unavailable keeps this identical
        to the previous behaviour rather than silently disabling the check.
        """
        ticket = pos["ticket"]
        if ticket not in self._partials:
            self._partials[ticket] = {"rungs": 0.0, "orig": float(pos["volume"]), "done": 0.0}
            self._save_partials()
        book = self._partials[ticket]
        if book.get("done"):
            return False

        entry = pos["price_open"]
        is_buy = pos["side"] == "buy"
        wick_dist = profit_dist
        if bars is not None and hasattr(bars, "high") and len(bars.high) > 0:
            wick_ref = float(bars.high[-1]) if is_buy else float(bars.low[-1])
            wick_dist = max(profit_dist, (wick_ref - entry) if is_buy else (entry - wick_ref))
        sl_dist = max(atr * cfg.sl_atr_mult, self.client.min_stop_distance(cfg.symbol))
        rungs = backtest._ladder(Params.from_config(cfg), entry, sl_dist, is_buy)
        taken = int(book["rungs"])
        if taken >= len(rungs):
            book["done"] = 1.0
            self._save_partials()
            return False

        _, r_mult, frac = rungs[taken]
        if wick_dist < sl_dist * r_mult:
            return False

        info = self.client.info(cfg.symbol)
        if not info:
            return False
        step, minimum = info["volume_step"], info["volume_min"]
        slice_lot = self.client.normalize_volume(cfg.symbol, book["orig"] * frac)
        # Only scale out when both sides of the split stay above the broker's
        # minimum volume - otherwise the ladder would either fail or close out.
        if slice_lot < minimum or (pos["volume"] - slice_lot) < minimum - step / 2:
            book["done"] = 1.0
            self._save_partials()
            return False

        if self._close_tracked(pos, f"MicoFX kismi kar {taken + 1}", "exit",
                               volume=slice_lot):
            book["rungs"] = taken + 1
            self._save_partials()
            if taken == 0:
                # First slice off: the remainder rides risk-free from here.
                self.client.modify_position(ticket, entry, pos["tp"], cfg.symbol)
            LOG.emit(f"Kismi kar {taken + 1}. kademe: {slice_lot:g} lot ({r_mult:.1f}R), "
                     f"kalan {'risksiz ' if taken == 0 else ''}devam ediyor",
                     "TRADE", cfg.symbol)
            return True
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
        Sourced from real MT5 deal history (``day_stats``), not a persisted
        flag, so it is correct again immediately after any restart without
        needing its own recovery bookkeeping - the day resets when the broker
        day (and therefore the cached stats) does.
        """
        if cfg.symbol_daily_loss_pct <= 0:
            return ""
        guard = self.risk.daily
        if guard.start_balance <= 0:
            return ""
        row = next((r for r in self.day_stats().get("per_symbol", [])
                    if r["symbol"] == cfg.symbol), None)
        if row is None:
            return ""
        loss_pct = -row["profit"] / guard.start_balance * 100.0
        if loss_pct >= cfg.symbol_daily_loss_pct:
            return f"gunluk sembol zarar limiti ({loss_pct:.2f}%)"
        return ""

    def day_stats(self, max_age: float = 5.0) -> dict[str, Any]:
        """Closed-trade totals for the current broker day, per symbol."""
        if self._day_cache and time.time() - self._day_cache_at < max_age:
            return self._day_cache
        guard = self.risk.daily
        # Deal timestamps live in broker-clock epoch, the same space as day_key.
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
                "server_utc_offset": self.store.system.server_utc_offset,
                "server_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(self.client.server_now())),
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
