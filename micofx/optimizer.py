from __future__ import annotations

import contextlib
import os
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor
from concurrent.futures import wait as futures_wait
from concurrent.futures.process import BrokenProcessPool
from typing import Any

import numpy as np

from . import backtest
from .logbus import LOG
from .models import (
    EXIT_RISK_FIELDS, OPT_FIELDS, SECONDARY_FIELDS, STRATEGIES, STRATEGY_TIMEFRAMES,
    SWING_GRID_OVERLAY, TIMEFRAMES, SymbolConfig, invalid_exit_param, is_scalp_strategy,
    strategy_allows_timeframe, uses_swing_exits,
)
from .mt5client import Bars, MT5Client, timeframe_seconds
from .store import Store


def _sweep_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Run one timeframe x strategy walk-forward in a separate process.

    Every sweep is fully independent - same bars in, its own grid, its own
    three-way split - so the grid search is embarrassingly parallel. Only plain
    arrays and dicts cross the process boundary; MT5 is never touched here (the
    bars were already fetched by the parent under the client lock).
    """
    bars = Bars.__new__(Bars)
    for name in ("time", "open", "high", "low", "close", "spread", "volume"):
        setattr(bars, name, payload["bars"][name])
    bars.forming_time = 0

    cfg = SymbolConfig.from_dict(payload["cfg"])
    try:
        outcome = backtest.walk_forward(
            cfg, bars, payload["point"], payload["tf_seconds"], payload["grid"],
            payload["min_trades"], payload["segments"], payload["max_combos"],
            payload["min_positive"], payload["plateau"],
            commission_price=payload["commission"],
            refine_rounds=payload["refine_rounds"],
            min_stop=payload.get("min_stop"),
            all_hours=bool(payload.get("all_hours")),
            day_end_flatten_min=int(payload.get("day_end_flatten_min") or 0),
            max_cost_share=float(payload.get("max_cost_share") or 0.0),
            spread_scale=float(payload.get("spread_scale") or 1.0),
        )
    except Exception as exc:                      # keep one bad sweep from killing the run
        outcome = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    outcome["timeframe"] = payload["timeframe"]
    outcome["strategy"] = payload["strategy"]
    outcome["order"] = payload.get("order", 0)
    return outcome


_BLAS_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")


def _limit_blas_threads() -> None:
    """Pin each worker's BLAS to one thread before the pool is spawned.

    Spawned children inherit this environment. Without it every worker starts
    its own OpenBLAS thread pool sized to the whole machine: the sweeps are
    already the parallelism, so those threads only add contention, and their
    per-thread buffers are enough to exhaust memory and kill the pool.
    """
    for var in _BLAS_VARS:
        os.environ.setdefault(var, "1")


def _free_memory_gb() -> float:
    """Available physical memory, without depending on psutil being installed.

    The previous psutil-based probe was inside a bare ``except``, and psutil is
    not in requirements.txt - so on this machine the memory clamp silently never
    ran and the worker count was decided by the hard cap alone.
    """
    try:
        import ctypes

        class _Status(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        status = _Status()
        status.dwLength = ctypes.sizeof(_Status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return status.ullAvailPhys / (1024 ** 3)
    except Exception:
        pass
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 ** 3)
    except Exception:
        return 0.0


# Each worker holds one bar window plus its own IndicatorCache; this is the
# headroom that keeps the pool from being killed on a busy machine.
_WORKER_MEMORY_GB = 0.6


def _worker_count(configured: int = 0) -> int:
    """How many sweeps to run at once, leaving the machine usable.

    ``MICO_OPT_WORKERS`` env var overrides everything (debugging/ops escape
    hatch). Otherwise ``configured`` (Sistem > opt_max_workers) wins when set -
    a weaker/shared cloud VM can cap this from the UI without an env var. 0
    falls back to the automatic guess: one core left for the engine's live
    poll loop and one for the OS, then memory decides the rest.
    """
    try:
        override = int(os.environ.get("MICO_OPT_WORKERS", "0"))
    except ValueError:
        override = 0
    if override > 0:
        return override
    if configured > 0:
        return configured
    workers = max(1, min(16, (os.cpu_count() or 2) - 2))
    free_gb = _free_memory_gb()
    if free_gb > 0:
        workers = max(1, min(workers, int(free_gb / _WORKER_MEMORY_GB)))
    return workers


class Optimizer:
    """Background walk-forward parameter search over the configured symbols."""

    def __init__(self, store: Store, client: MT5Client) -> None:
        self.store = store
        self.client = client
        self._thread: threading.Thread | None = None
        self._cancel = threading.Event()
        self._lock = threading.RLock()
        self.job: dict[str, Any] = {"state": "idle"}
        # Wired late by run.py (engine.supervisor.optimizer = optimizer is the
        # same late-binding pattern) to Engine.entry_lock - constructed here
        # as a plain attribute, not a real lock, because Optimizer has no
        # Engine reference at __init__ time and must not require one. apply()/
        # apply_secondary() only take it when set, so tests and any other
        # caller that never wires an engine keep working lock-free.
        self.entry_lock: threading.Lock | None = None

    @property
    def busy(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self.job, busy=self.busy)

    def cancel(self) -> dict[str, Any]:
        self._cancel.set()
        return {"ok": True, "message": "Iptal istegi gonderildi."}

    def start(self, symbols: list[str] | None = None, apply_best: bool = True,
              bars: int | None = None, source: str = "manual",
              timeframes: list[str] | None = None) -> dict[str, Any]:
        with self._lock:
            if self.busy:
                return {"ok": False, "error": "Optimizasyon zaten calisiyor."}
            targets = [s for s in (symbols or list(self.store.symbols)) if s in self.store.symbols]
            if not targets:
                return {"ok": False, "error": "Sembol secilmedi."}
            # One-off restriction of this run to a subset of the configured
            # timeframes (e.g. "just scan M5 today") - None/empty means the
            # saved opt_params selection, same as before this existed.
            tf_override = [t for t in (timeframes or []) if t in TIMEFRAMES] or None
            self._cancel.clear()
            self.job = {
                "state": "running", "started_at": time.time(), "finished_at": 0.0,
                "symbols": targets, "apply_best": bool(apply_best),
                "source": str(source or "manual"), "timeframes": tf_override or [],
                "done": 0, "total": len(targets), "current": "",
                "combo_done": 0, "combo_total": 0, "best_score": None,
                "results": [], "error": "",
            }
            self._thread = threading.Thread(
                target=self._run, args=(targets, bool(apply_best), bars, tf_override),
                name="micofx-optimizer", daemon=True,
            )
            self._thread.start()
        return {"ok": True, "job": self.status()}

    # ------------------------------------------------------------------ work

    def _set(self, **patch: Any) -> None:
        with self._lock:
            self.job.update(patch)

    def _run(self, targets: list[str], apply_best: bool, bars_override: int | None,
             tf_override: list[str] | None = None) -> None:
        # Thread target - nothing downstream of start() is allowed to leave
        # self.job stuck in "running" forever. A bad opt_params value (e.g. a
        # None a client bug slipped through, or hand-edited settings) used to
        # raise straight out of this thread with no handler, silently killing
        # it: the Start button (job.state == "running") stayed disabled
        # indefinitely with no error ever surfaced anywhere.
        try:
            self._run_unsafe(targets, apply_best, bars_override, tf_override)
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
            self._set(state="done", finished_at=time.time(), current="", error=err)
            LOG.emit(f"Optimizasyon beklenmedik hatayla durdu: {err}", "OPT")

    def _run_unsafe(self, targets: list[str], apply_best: bool, bars_override: int | None,
                    tf_override: list[str] | None = None) -> None:
        self.client.set_terminal_path(self.store.system.mt5_terminal_path)
        self.client.set_overrides(
            {c.symbol: c.broker_symbol for c in list(self.store.symbols.values())})
        if not self.client.ensure():
            err = self.client.last_error or "MT5 baglantisi kurulamadi"
            self._set(state="done", finished_at=time.time(), current="", error=err)
            LOG.emit(f"Optimizasyon baslatilamadi: {err}", "OPT")
            return

        params = self.store.opt_params()
        lookback_days = int(params.get("lookback_days", 180))
        bar_cap = int(bars_override or params.get("max_bars", 45000))
        min_trades = int(params.get("min_trades", 25))
        segments = int(params.get("segments", 4))
        max_combos = int(params.get("max_combos", 2500))
        min_positive = float(params.get("min_positive_ratio", 0.6))
        plateau = float(params.get("plateau_weight", 0.4))
        timeframes = [t for t in (tf_override or params.get("timeframes") or ["M5"]) if t in TIMEFRAMES] \
            or ["M5"]
        refine_rounds = int(params.get("refine_rounds", 2))
        shared = {k: v for k, v in (params.get("grid") or {}).items() if isinstance(v, list) and v}
        families = [s for s in (params.get("strategies") or ["t3_stoch"]) if s in STRATEGIES] \
            or ["t3_stoch"]
        family_grids = params.get("strategy_grids") or {}
        # One sweep per family: its own parameters on top of the shared risk
        # grid. There used to be a second axis here - an ``exit_styles`` block
        # that split every family into a "targeted" and a "trail" sweep,
        # because how a trade is closed was a searchable choice. It is not any
        # more: the system has exactly one exit regime (hard ATR stop, then ATR
        # trail), so there is nothing left to split on and every candidate is
        # comparable to every other without it.
        # ``own`` is kept apart from the merged grid because the swing overlay
        # has to sit between them: it widens what the shared grid proposes and
        # steps aside for any axis the family itself has an opinion about.
        variants = [{"key": name, "strategy": name,
                     "own": {k: v for k, v in (family_grids.get(name) or {}).items()
                             if isinstance(v, list) and v},
                     "grid": {**shared, **{k: v for k, v in (family_grids.get(name) or {}).items()
                                           if isinstance(v, list) and v}}}
                    for name in families]
        # Optional override of the shipped family→TF map (empty list = inherit).
        tf_allow = params.get("strategy_timeframes")
        if not isinstance(tf_allow, dict):
            tf_allow = STRATEGY_TIMEFRAMES

        LOG.emit(f"Optimizasyon basladi | {len(targets)} sembol | son {lookback_days} gun | "
                 f"{segments} segment (son segment dogrulama) | "
                 f"zaman dilimleri {'/'.join(timeframes)} | stratejiler {'/'.join(families)} | "
                 f"cikis: sert ATR stop + ATR takip ({len(variants)} tarama/zaman dilimi) | "
                 f"scalp TF kilidi acik | "
                 f"max {max_combos} kombinasyon | "
                 f"{_worker_count(self.store.system.opt_max_workers)} paralel surec", "OPT")

        self._run_all(targets, lookback_days, bar_cap, variants, min_trades, segments,
                      max_combos, min_positive, plateau, timeframes, refine_rounds,
                      apply_best, tf_allow)

        cancelled = self._cancel.is_set()
        self._set(state="cancelled" if cancelled else "done", finished_at=time.time(), current="")
        with self._lock:
            results = list(self.job.get("results") or [])
            tag = "Zamanlanmis optimizasyon" if self.job.get("source") == "scheduled" \
                else "Optimizasyon"
        if cancelled:
            LOG.emit(f"{tag} iptal edildi.", "OPT")
        else:
            applied = [r["symbol"] for r in results if r.get("applied")]
            rejected = [r.get("symbol", "?") for r in results if not r.get("applied")]
            applied_txt = " (" + ", ".join(applied) + ")" if applied else ""
            rejected_txt = " (" + ", ".join(rejected) + ")" if rejected else ""
            LOG.emit(f"{tag} tamamlandi | uygulanan {len(applied)}{applied_txt} | "
                     f"uygulanmayan {len(rejected)}{rejected_txt}", "OPT")

    @staticmethod
    def _exit_grid_for(merged: dict[str, Any], own: dict[str, Any],
                       family: str, timeframe: str) -> dict[str, Any]:
        """Search grid for one family/timeframe pairing.

        Precedence is shared -> swing overlay -> the family's own statement.

        It used to be written the other way round - overlay first, then
        ``merged`` on top - with the intent "a family that states its own
        stop/trail range means it". But ``merged`` is not the family's own
        grid, it is ``{**shared, **own}``, and the shared grid defines all four
        overlay axes. So the shared values overwrote the overlay for every
        family on every timeframe and the widening never happened at all -
        exactly the failure SWING_GRID_OVERLAY's own comment names, "the search
        only ever offers H1 candidates a stop tight enough to be noise".

        It showed in what the search returned: FRA40 came back with burst/M30
        carrying sl_atr_mult 0.5, half the overlay's own floor and a value that
        exists only in the shared grid, on thirty-minute bars.
        """
        grid = dict(merged)
        if uses_swing_exits(family, timeframe):
            # Widen what the shared grid proposed, but never over an axis the
            # family itself has an opinion about - that is the part the old
            # comment got right.
            grid.update({k: v for k, v in SWING_GRID_OVERLAY.items() if k not in own})
        return grid

    def _spread_scale(self, symbol: str) -> float:
        """Measured live-tick / bar spread median for this symbol, or 1.0.

        Read from the store rather than from the engine: the engine already
        persists the histogram there, so the search does not need a handle on
        a running engine (and the pooled workers could not have one anyway).

        Returns 1.0 - the old behaviour, exactly - until the symbol has
        cleared the sample threshold. Half a session of ticks from one hour is
        the reading that already misled us once; nothing moves the search
        until the distribution is real.
        """
        try:
            from .engine import (SPREAD_RATIO_BUCKETS, SPREAD_RATIO_MIN_SAMPLES,
                                 _ratio_percentile)
            blob = self.store.get_setting("spread_ratio", {}) or {}
            counts = blob.get(symbol)
            if not isinstance(counts, (list, tuple)):
                return 1.0
            counts = [int(v) for v in counts
                      if isinstance(v, (int, float)) and not isinstance(v, bool)]
            if len(counts) != SPREAD_RATIO_BUCKETS:
                return 1.0
            if sum(counts) < SPREAD_RATIO_MIN_SAMPLES:
                return 1.0
            median = _ratio_percentile(counts, 0.50)
            if not median or median <= 0:
                return 1.0
            # Bounded both ways, but the two bounds do different jobs.
            #
            # The floor is a stance: a ratio under 1 says the live tick is
            # TIGHTER than the bar, and letting that make the search cheerier
            # than the bars justify is the one direction this whole mechanism
            # exists to prevent. Clamped to 1.0.
            #
            # The ceiling is only a sanity bound, and the first version set it
            # at 3.0 with no data behind it. There is data now: across fifteen
            # symbols the highest measured median is CHFJPY at 3.35 over 3204
            # samples - above that ceiling. So 3.0 was not catching an absurd
            # reading, it was truncating the single measurement that matters
            # most, and searching the book's most expensive symbol ~10% cheaper
            # than it really is.
            #
            # The glitch guard is SPREAD_RATIO_MIN_SAMPLES, not this: a frozen
            # feed or a one-off gap cannot hold a stable median across hundreds
            # of samples spanning hours.
            #
            # 5.0 is the histogram's own maximum - its last bucket is an
            # overflow reported at its lower edge, so no median can exceed it.
            # The ceiling is therefore the measurement's resolution rather than
            # a number picked here, and anything lower would clip real data
            # again the moment a symbol measures above it.
            return float(min(5.0, max(1.0, median)))
        except Exception:
            return 1.0

    def _plan_symbol(self, cfg, lookback_days: int, bar_cap: int,
                     variants: list[dict[str, Any]],
                     min_trades: int, segments: int, max_combos: int, min_positive: float,
                     plateau: float, timeframes: list[str],
                     refine_rounds: int,
                     tf_allow: dict[str, list[str]] | None = None) -> dict[str, Any]:
        """Fetch this symbol's bars and build its sweep jobs.

        Runs in the parent thread so every MT5 call stays behind the client's
        single lock; the jobs it returns are plain arrays and dicts that any
        worker process can pick up.
        """
        plan: dict[str, Any] = {"cfg": cfg, "started": time.time(),
                                "attempts": [], "jobs": [], "error": ""}
        info = self.client.info(cfg.symbol)
        if info is None:
            plan["error"] = "sembol bulunamadi"
            return plan

        commission = backtest.commission_in_price(
            cfg.commission_per_lot, info["tick_value"], info["tick_size"])
        # Real broker floor (stops_level/freeze_level/current spread), not the
        # flat point*10 the search falls back to when this is unavailable - the
        # same number the live engine enforces via min_stop_distance, so a
        # symbol whose broker requires a wider stop than that guess gets judged
        # against the floor it will actually have to trade under.
        min_stop = self.client.min_stop_distance(cfg.symbol)
        # What the LIVE gate will actually see, rather than what the bars
        # recorded. simulate() charges and gates on the entry bar's spread;
        # engine._try_entry uses the current tick, which runs wider, so a
        # ceiling picked here was enforced there against a bigger number -
        # FRA40 could not clear a single hour of its own session because of
        # it. The engine measures the ratio continuously and parks it in the
        # same store this reads, so nothing new is coupled; 1.0 until the
        # sample threshold is cleared, which leaves the search exactly as it
        # was until there is real evidence to move it.
        spread_scale = self._spread_scale(cfg.symbol)
        # The system-wide override that drops session windows live - the search
        # has to score the same product that is actually trading (see
        # ``backtest.session_mask``'s ``all_hours`` branch).
        all_hours = bool(self.store.system.trade_all_hours)
        # Same reasoning for the forced day-end close (see
        # ``backtest.flatten_mask``) - independent of all_hours live, so it is
        # threaded through unconditionally.
        day_end_flatten_min = int(self.store.system.day_end_flatten_min)
        # Same ceiling engine._try_entry applies before every order, expressed as
        # a share of R rather than a percentage. Without it the search ranked
        # tight-stop configs whose spread+commission ate most of the risk, and
        # live then refused every one of those entries - the optimizer and the
        # engine disagreeing about what is tradable. Zero when the live gate is
        # off, which leaves the search unfiltered exactly as before.
        sys_cfg = self.store.system
        max_cost_share = (float(sys_cfg.max_cost_pct_of_risk) / 100.0
                          if (sys_cfg.block_high_cost and sys_cfg.max_cost_pct_of_risk > 0)
                          else 0.0)

        # Timeframe and strategy family are both search dimensions; each pairing is
        # judged on its own held-out slice so they compete on equal terms.
        # Scalp families are never paired with M15+ - that search is pure noise
        # against a cost model built for M5 bars.
        allow = tf_allow if isinstance(tf_allow, dict) else STRATEGY_TIMEFRAMES
        needed_tfs = [tf for tf in timeframes
                      if any(strategy_allows_timeframe(v["strategy"], tf, allow)
                             for v in variants)]
        cached_bars: dict[str, Any] = {}
        for tf in needed_tfs:
            # Same calendar window for every timeframe, otherwise a slow timeframe
            # gets judged on years of history while a fast one gets days.
            want = min(bar_cap, int(lookback_days * 86400 / timeframe_seconds(tf)))
            cached_bars[tf] = self.client.bars(cfg.symbol, tf, want)

        for tf in timeframes:
            bars = cached_bars.get(tf)
            for variant in variants:
                family = variant["strategy"]
                if not strategy_allows_timeframe(family, tf, allow):
                    continue
                if bars is None or len(bars) < 600:
                    plan["attempts"].append(
                        {"timeframe": tf, "strategy": family,
                         "ok": False,
                         "order": len(plan["jobs"]) + len(plan["attempts"]),
                         "error": f"veri yetersiz ({len(bars) if bars else 0} bar)"})
                    continue
                grid = self._exit_grid_for(variant["grid"], variant["own"], family, tf)
                plan["jobs"].append({
                    "symbol": cfg.symbol, "timeframe": tf, "strategy": family,
                    "order": len(plan["jobs"]) + len(plan["attempts"]),
                    "cfg": {**cfg.to_dict(), "timeframe": tf, "strategy": family},
                    "bars": {name: np.asarray(getattr(bars, name))
                             for name in ("time", "open", "high", "low", "close",
                                          "spread", "volume")},
                    "point": float(info["point"]), "tf_seconds": timeframe_seconds(tf),
                    "spread_scale": spread_scale,
                    "grid": grid, "min_trades": min_trades, "segments": segments,
                    "max_combos": max_combos, "min_positive": min_positive,
                    "plateau": plateau, "commission": commission, "min_stop": min_stop,
                    "refine_rounds": refine_rounds, "all_hours": all_hours,
                    "day_end_flatten_min": day_end_flatten_min,
                    # The live entry gate's own ceiling, handed to the search so
                    # it stops proposing configs the engine will refuse. Read
                    # from the same setting the engine reads, and only when that
                    # gate is actually switched on - otherwise 0 leaves the
                    # search unfiltered, exactly as before.
                    "max_cost_share": max_cost_share,
                })
        return plan

    def _run_all(self, targets: list[str], lookback_days: int, bar_cap: int,
                 variants: list[dict[str, Any]],
                 min_trades: int, segments: int, max_combos: int,
                 min_positive: float, plateau: float, timeframes: list[str],
                 refine_rounds: int, apply_best: bool,
                 tf_allow: dict[str, list[str]] | None = None) -> None:
        """Search every symbol through one shared pool of worker processes.

        Every (symbol, timeframe, family) sweep is independent, so they all go
        into a single queue rather than one pool per symbol. That matters for
        wall clock in three ways: the pool is spawned once instead of once per
        symbol; sweep durations differ by two orders of magnitude (an M5 pullback
        search against an H1 one), so draining one symbol at a time left every
        worker idling on that symbol's slowest sweep while the next symbol's
        short ones waited; and bar fetching - which must stay in this thread,
        behind the MT5 lock - now overlaps the search instead of running as a
        serial prologue in front of it.
        """
        plans: dict[str, dict[str, Any]] = {}
        allow = tf_allow if isinstance(tf_allow, dict) else STRATEGY_TIMEFRAMES
        # Count only legal family×TF pairs so the progress bar is honest.
        legal = sum(1 for v in variants for tf in timeframes
                    if strategy_allows_timeframe(v["strategy"], tf, allow))
        total_sweeps = len(targets) * max(1, legal)
        done_sweeps = 0
        finished = 0

        def close_out(plan: dict[str, Any]) -> None:
            nonlocal finished
            report = self._finish_symbol(plan, apply_best)
            finished += 1
            with self._lock:
                self.job["results"].append(report)
                self.job["done"] = finished

        def note(job: dict[str, Any], outcome: dict[str, Any]) -> None:
            """Record one finished sweep, closing the symbol out when it is the last."""
            nonlocal done_sweeps
            plan = plans[job["symbol"]]
            plan["attempts"].append(outcome)
            plan["outstanding"] -= 1
            done_sweeps += 1
            best = max((a["best"]["score"] for p in plans.values()
                        for a in p["attempts"] if a.get("ok")), default=None)
            active = sorted(s for s, p in plans.items() if p["outstanding"] > 0)
            self._set(combo_done=done_sweeps * max_combos,
                      combo_total=max(total_sweeps, done_sweeps) * max_combos,
                      best_score=best, current=", ".join(active[:3]))
            if plan["outstanding"] <= 0:
                close_out(plan)

        def plan_next(symbol: str) -> list[dict[str, Any]]:
            """Fetch one symbol's bars and hand back its sweep jobs."""
            cfg = self.store.symbols.get(symbol)
            if cfg is None:
                return []
            plan = self._plan_symbol(cfg, lookback_days, bar_cap, variants, min_trades,
                                     segments, max_combos, min_positive, plateau,
                                     timeframes, refine_rounds, allow)
            plans[symbol] = plan
            plan["outstanding"] = len(plan["jobs"])
            if not plan["jobs"]:
                close_out(plan)          # nothing to wait for
            return plan["jobs"]

        _limit_blas_threads()
        workers = _worker_count(self.store.system.opt_max_workers)
        if workers > 1:
            try:
                self._search_parallel(targets, plan_next, note, workers)
                return
            except BrokenProcessPool:
                # Usually memory pressure. Finishing slowly beats not finishing.
                LOG.emit("Paralel arama basarisiz, tek surece dusuldu.", "OPT")

        # Single-process fallback: same work, same results, one core. A symbol
        # already planned may still owe sweeps the broken pool never returned,
        # so those are re-run here rather than skipped along with the symbol.
        for symbol in targets:
            if self._cancel.is_set():
                return
            plan = plans.get(symbol)
            if plan is None:
                self._set(current=symbol)
                jobs = plan_next(symbol)
                plan = plans.get(symbol)
            elif plan["outstanding"] > 0:
                self._set(current=symbol)
                measured = {(a.get("timeframe"), a.get("strategy"))
                            for a in plan["attempts"]}
                jobs = [j for j in plan["jobs"]
                        if (j["timeframe"], j["strategy"]) not in measured]
            else:
                continue
            for job in jobs:
                if self._cancel.is_set():
                    return
                note(job, _sweep_worker(job))

    def _search_parallel(self, targets: list[str], plan_next, note, workers: int) -> None:
        """Feed every symbol's sweeps into one pool, fetching bars as it goes."""
        with ProcessPoolExecutor(max_workers=workers) as pool:
            inflight: dict[Any, dict[str, Any]] = {}

            def harvest(block: bool) -> bool:
                """Collect finished sweeps; False once a cancel has been seen."""
                if not inflight:
                    return not self._cancel.is_set()
                if block:
                    done, _ = futures_wait(list(inflight), return_when=FIRST_COMPLETED)
                else:
                    done = [f for f in inflight if f.done()]
                for future in list(done):
                    job = inflight.pop(future)
                    try:
                        note(job, future.result())
                    except BrokenProcessPool:
                        raise
                    except Exception as exc:
                        note(job, {"timeframe": job["timeframe"], "strategy": job["strategy"],
                                   "order": job["order"], "ok": False,
                                   "error": f"{type(exc).__name__}: {exc}"})
                if self._cancel.is_set():
                    for future in inflight:
                        future.cancel()
                    inflight.clear()
                    return False
                return True

            for symbol in targets:
                if self._cancel.is_set():
                    return
                # Bars are fetched here, in this thread, so MT5 stays behind its
                # single lock; the workers already running keep the cores busy.
                for job in plan_next(symbol):
                    inflight[pool.submit(_sweep_worker, job)] = job
                if not harvest(block=False):
                    return

            while inflight:
                if not harvest(block=True):
                    return

    def _finish_symbol(self, plan: dict[str, Any], apply_best: bool) -> dict[str, Any]:
        """Pick the winning sweep for one symbol, gate it, store it, log it."""
        cfg = plan["cfg"]
        started = plan["started"]
        # Sweeps come back in completion order now that they share one queue;
        # restore the deterministic timeframe x family order so ties between
        # equally scoring sweeps break the same way on every run.
        attempts = sorted(plan["attempts"], key=lambda a: a.get("order", 0))
        if plan.get("error"):
            return {"symbol": cfg.symbol, "ok": False, "error": plan["error"]}

        usable = [a for a in attempts if a.get("ok") and a.get("validated")]
        if not usable:
            usable = [a for a in attempts if a.get("ok")]
        if not usable:
            reasons = "; ".join(f"{a['timeframe']}/{a['strategy']}: {a.get('error', '?')}"
                                for a in attempts[:4]) or "sonuc yok"
            report = {"symbol": cfg.symbol, "ok": False, "error": reasons,
                      "elapsed_sec": round(time.time() - started, 1)}
            LOG.emit(f"{cfg.symbol}: {reasons}", "OPT", cfg.symbol)
            return report

        # Search scores are not comparable between families or timeframes - each
        # sweep explores a different space. The validation slice is the common
        # yardstick, and it is not the slice the final numbers are read from.
        report = self._pick_by_validation(usable)
        report["symbol"] = cfg.symbol
        report["tried"] = [
            {"timeframe": a["timeframe"], "strategy": a.get("strategy", "?"),
             "ok": bool(a.get("ok")), "validated": bool(a.get("validated")),
             "score": a["best"]["score"] if a.get("ok") else None,
             "validation_net_r": a["best"]["validation"]["net_r"] if a.get("ok") else None,
             "holdout_net_r": a["best"]["holdout"]["net_r"] if a.get("ok") else None,
             "error": a.get("error", "")}
            for a in attempts
        ]
        report["elapsed_sec"] = round(time.time() - started, 1)

        best = report["best"]
        score = float(best["score"])
        # Named up front so the UI can explain a red number instead of leaving
        # it looking like the symbol's live setup is the thing losing money.
        reason = self.reject_reason(cfg, best)
        report["keep_reason"] = reason
        report["holdout_retention"] = round(self.holdout_retention(best), 3)
        incumbent = ((getattr(cfg, "opt_summary", None) or {}).get("holdout") or {})
        report["incumbent"] = {
            "net_r": incumbent.get("net_r"), "score": incumbent.get("score"),
            "profit_factor": incumbent.get("profit_factor"),
            "trades": incumbent.get("trades"),
            "strategy": cfg.strategy, "timeframe": cfg.timeframe,
            "updated_at": float(getattr(cfg, "opt_updated_at", 0.0) or 0.0),
        } if incumbent else None
        applied = False
        if apply_best and report.get("validated") and not reason:
            apply_result = self.apply(cfg.symbol, best["params"], score,
                       {**best, "holdout_days": report.get("holdout_days", 0.0)},
                       timeframe=report["timeframe"], strategy=report["strategy"])
            applied = bool(apply_result.get("ok"))
            if not applied:
                # apply() itself refused (e.g. the TF-lock check) - the run
                # otherwise looked like a normal validated win, so make sure
                # that doesn't get reported as "uygulandi" with the live
                # config silently left on whatever it was before.
                report["keep_reason"] = apply_result.get("error", "uygulanamadi")
                LOG.emit(f"{cfg.symbol}: uygulama reddedildi - "
                         f"{apply_result.get('error', '?')}", "OPT", cfg.symbol)
            # The runner-up is stored (never auto-traded) so the user can switch
            # the symbol to two signals from the UI. Refreshed on every applied
            # run, and cleared when this run found none, so a stale candidate can
            # never outlive the primary it was measured against - but only when
            # the primary actually landed. apply_secondary(None) *clears*, it
            # does not skip, so calling it here when apply() itself refused
            # would wipe out a perfectly good existing secondary over a primary
            # change that never happened.
            if applied:
                second = self._pick_secondary(report, attempts)
                sec_result = self.apply_secondary(cfg.symbol, second)
                if not sec_result.get("ok"):
                    # Primary already landed; surface secondary failure instead
                    # of silently leaving a stale pairing / empty clear.
                    report["secondary_error"] = sec_result.get(
                        "error", "ikincil aday yazilamadi")
                    LOG.emit(f"{cfg.symbol}: ikincil aday yazilamadi - "
                             f"{report['secondary_error']}", "WARN", cfg.symbol)
                report["secondary"] = (
                    {"timeframe": second["timeframe"], "strategy": second["strategy"],
                     "score": second["best"]["score"]} if second else None)
                if second and sec_result.get("ok"):
                    sec_hold = second["best"]["holdout"]
                    LOG.emit(
                        f"{cfg.symbol}: ikincil aday {second['strategy']}/{second['timeframe']} "
                        f"saklandi | test {sec_hold['trades']} islem "
                        f"PF {sec_hold['profit_factor']:.2f} net {sec_hold['net_r']:+.1f}R "
                        f"(Semboller sekmesinden acilabilir)", "OPT", cfg.symbol)

        self.store.record_opt_run(cfg.symbol, score, {
            "timeframe": report["timeframe"], "strategy": report["strategy"],
            "params": best["params"],
            "selection": best["selection"], "validation": best["validation"],
            "holdout": best["holdout"],
            "positive_ratio": best["positive_ratio"],
            "baseline": report.get("baseline", {}), "combos": report.get("combos", 0),
            "candidates": report.get("candidates", 0),
            "bars": report.get("bars", 0), "elapsed_sec": report["elapsed_sec"],
            "holdout_days": report.get("holdout_days", 0.0),
            "validation_days": report.get("validation_days", 0.0),
            "validated": bool(report.get("validated")),
            "holdout_retention": report["holdout_retention"],
            "keep_reason": reason,
        }, applied)

        report["applied"] = applied
        hold = best["holdout"]
        val = best["validation"]
        sel = best["selection"]
        if applied:
            tail = " -> uygulandi"
        else:
            # Say *why* nothing was written, and say that the live config is
            # untouched - a red backtest number next to a symbol otherwise reads
            # as if the running setup is the thing losing money.
            # keep_reason may have been overwritten above with apply()'s own
            # refusal (e.g. the TF-lock) after `reason` (the gate check) had
            # already come back empty - that candidate passed every OOS gate,
            # so falling back to the stale `reason` here logged a misleading
            # "dogrulanmadi" for something that actually validated fine and
            # was rejected for an unrelated, more specific cause.
            tail = f" -> uygulanmadi ({report.get('keep_reason') or reason or 'dogrulanmadi'})"
            if report.get("incumbent"):
                tail += (f", mevcut ayar korundu "
                         f"(test net {float(report['incumbent'].get('net_r') or 0.0):+.1f}R)")
        LOG.emit(
            f"{cfg.symbol}: {report['strategy']}/{report['timeframe']}"
            f" skor {score:.2f} | "
            f"secim {sel['trades']} islem "
            f"PF {sel['profit_factor']:.2f} ({best['positive_ratio']:.0%} segment pozitif) | "
            f"secmeli dogrulama {val['trades']} islem PF {val['profit_factor']:.2f} "
            f"net {val['net_r']:+.1f}R | "
            f"dokunulmamis test {hold['trades']} islem "
            f"PF {hold['profit_factor']:.2f} net {hold['net_r']:+.1f}R"
            f"{tail}",
            "OPT", cfg.symbol,
        )
        return report

    # Above this, spread plus commission eats so much of each trade's risk that no
    # backtest edge survives contact with a live account.
    MAX_COST_PER_TRADE_R = 0.25

    # The ceiling above is absolute, measured against the trade's RISK - so it
    # asks "is this instrument expensive?" and never "can this candidate's own
    # edge carry what it costs?". Those come apart badly at the thin end.
    # Measured across the live book, cost as a share of gross edge
    # (cost / (cost + expectancy)):
    #
    #   XAUUSD    5%   NAS100  9%   GBPUSD  9%   USDCHF 10%   ... CADJPY 35%
    #   CA60     43%   COPPER 45%   US30   46%   COFFEE 51%   USDJPY 58%
    #
    # USDJPY hands the broker 58% of everything it makes and sails through the
    # absolute gate, because 0.16 is comfortably under 0.25 - while its gross
    # edge is only 0.277R and cannot carry that. XAUUSD could carry 0.22R of
    # cost on a 0.476R gross edge, and is charged 0.025. Same ceiling, opposite
    # verdicts warranted.
    #
    # Set at half rather than at the widest gap in the data (which sits nearer
    # 40%): past half the trade is more a payment to the broker than a strategy,
    # and what remains is inside the noise of the cost estimate itself - spread
    # and commission both vary live. Half is the claim the evidence supports
    # without curve-fitting the threshold to this particular portfolio.
    MAX_COST_SHARE_OF_EDGE = 0.50

    # A config that is still recent was measured on data that mostly overlaps this
    # run's, so its holdout number is a fair yardstick and worth defending. Past
    # this age the comparison is between two different market periods, the
    # incumbent has to be allowed to refresh, and the OOS gates alone decide.
    INCUMBENT_GUARD_DAYS = 60.0

    # How much of the per-trade edge the search *found* must still be there on
    # the untouched slice. A parameter set that generalises decays gracefully; a
    # fitted one keeps its trade count and even its profit factor while the money
    # per trade falls off a cliff - which is exactly how AUDUSD looked when its
    # validation and holdout net-R turned out negatively correlated across
    # sweeps. The existing gates cannot see this: a candidate can clear net_r>0,
    # 12 trades and PF 1.10 on a holdout while having thrown away six sevenths of
    # its expectancy.
    #
    # Calibrated against the twenty live configs rather than guessed. Retention
    # of every healthy one sits between 0.53 (EURUSD) and 2.11 (UK100); only
    # AUS200 falls below this line, at 0.16 - in-sample 0.40-0.51 R per trade
    # against 0.065 on the holdout. Raising the bar further would start rejecting
    # configs whose holdout genuinely held up, so it sits where the evidence
    # actually separates.
    MIN_HOLDOUT_RETENTION = 0.25

    # Two candidates whose validation scores sit inside this band are, on a
    # single out-of-sample slice, not distinguishable - the difference is inside
    # the noise of how many trades happened to land in that window. When that is
    # the case a scalping product should take the one that trades more often:
    # more samples is also the more measurable of the two going forward.
    TIE_BAND = 0.05

    def _pick_by_validation(self, usable: list[dict[str, Any]]) -> dict[str, Any]:
        """Highest validation score, with scalp-family preference then trade
        count breaking near-ties.

        This is a *tiebreaker only*, and only among candidates that already
        cleared every out-of-sample gate. Nothing here can promote a candidate
        that failed one: a mixed pool (the fallback branch, where nothing
        validated) skips the tiebreak entirely, and the apply gates downstream
        are untouched either way. The product's stated priority is scalping,
        swing is the fallback when scalping genuinely does not validate for a
        symbol - so a scalp family (micro_rev/burst) among the near-tied peers
        wins over an equally-valid swing one; it never wins over a swing
        candidate that is not actually tied on validation.
        """
        top = max(usable, key=lambda a: a["best"]["validation"]["score"])
        if len(usable) < 2 or not all(a.get("validated") for a in usable):
            return top
        ceiling = float(top["best"]["validation"]["score"])
        if ceiling <= 0.0:
            return top
        peers = [a for a in usable
                 if float(a["best"]["validation"]["score"]) >= ceiling * (1.0 - self.TIE_BAND)]
        if len(peers) < 2:
            return top
        # Both OOS slices count, so a candidate cannot win the tiebreak on a
        # validation window that simply happened to be busier.
        return max(peers, key=lambda a: (
            1 if is_scalp_strategy(a["strategy"]) else 0,
            int(a["best"]["validation"].get("trades", 0) or 0)
            + int(a["best"]["holdout"].get("trades", 0) or 0),
            float(a["best"]["validation"]["score"]),
        ))

    @staticmethod
    def holdout_retention(best: dict[str, Any]) -> float:
        """Holdout expectancy as a fraction of the weaker in-sample slice.

        Measured against ``min(selection, validation)`` rather than the mean so a
        candidate cannot hide a collapse behind whichever slice flattered it.
        Returns 0.0 when there is no positive in-sample expectancy to decay from,
        which callers read as "not measurable" rather than "failed".
        """
        hold = best.get("holdout") or {}
        sel = best.get("selection") or {}
        val = best.get("validation") or {}
        reference = min(float(sel.get("expectancy", 0.0) or 0.0),
                        float(val.get("expectancy", 0.0) or 0.0))
        if reference <= 0.0:
            return 0.0
        return float(hold.get("expectancy", 0.0) or 0.0) / reference

    def _generalises(self, best: dict[str, Any], symbol: str = "") -> bool:
        """Reject candidates whose edge mostly evaporates out of sample."""
        retention = self.holdout_retention(best)
        if retention <= 0.0 or retention >= self.MIN_HOLDOUT_RETENTION:
            return True
        if not symbol:
            return False        # secondary-candidate screening; not worth a log line
        LOG.emit(f"{symbol}: aday asiri uyum gosteriyor - test segmentinde islem basina "
                 f"beklenti ic ornegin sadece %{retention * 100:.0f} kadari "
                 f"(alt sinir %{self.MIN_HOLDOUT_RETENTION * 100:.0f}), uygulanmadi.",
                 "OPT", symbol)
        return False

    def _is_improvement(self, cfg, best: dict[str, Any]) -> bool:
        """Only overwrite a live config when both out-of-sample slices pay, and
        when the replacement is not measurably worse than what is already live.

        The OOS gates below are unchanged - they are the floor every candidate
        has to clear. The incumbent check on top of them is a *tightening*: a
        wider search finds a higher validation score more often, and the winner
        it promotes can hold out worse than the config it would overwrite (seen
        directly on NAS100/UK100/GBPUSD when the search budget was raised). A
        scheduled re-opt should not be able to trade a measured, still-current
        edge for a weaker one just because it searched harder.

        ``cfg`` is the config being replaced; secondary-candidate checks pass
        ``None`` and skip the incumbent comparison.
        """
        return not self.reject_reason(cfg, best)

    def reject_reason(self, cfg, best: dict[str, Any]) -> str:
        """Why this candidate may not replace the live config; "" means it may.

        Same gates as before in the same order - this only names them, so the UI
        can say which one stopped an apply instead of leaving the user to guess
        from a red number.
        """
        hold = best.get("holdout", {})
        val = best.get("validation", {})
        if not backtest._slice_ok(val):
            return "dogrulama segmenti kar etmedi"
        if not backtest._slice_ok(hold):
            return "dokunulmamis test segmenti kar etmedi"
        # Must track the same setting the search itself gates candidates on
        # (backtest.py's walk_forward min_positive_ratio param, default 0.6,
        # UI-configurable down to 0.3) - a hardcoded 0.6 here silently
        # overrode any lower value the user configured: the search would
        # admit/validate a 0.4-0.59 candidate exactly as asked, then this
        # gate re-rejected it anyway with a threshold the user never set,
        # under a generic message indistinguishable from a real failure.
        min_positive = float(self.store.opt_params().get("min_positive_ratio", 0.6)) \
            if self.store is not None else 0.6
        if best.get("positive_ratio", 0) < min_positive:
            return "secim segmentleri arasinda tutarsiz"
        if hold.get("cost_per_trade_r", 0) > self.MAX_COST_PER_TRADE_R:
            return "islem maliyeti riske gore cok yuksek"
        # ...and the same cost measured against what this candidate actually
        # earns, which the absolute ceiling above cannot see (see the constant).
        cost = float(hold.get("cost_per_trade_r", 0.0) or 0.0)
        gross = cost + float(hold.get("expectancy", 0.0) or 0.0)
        if gross > 0 and cost / gross > self.MAX_COST_SHARE_OF_EDGE:
            return "maliyet brut kenarin cogunu yiyor"
        if float(best["score"]) <= 0.0:
            return "arama skoru pozitif degil"
        # Removed once on request, then silently reintroduced by someone else,
        # then removed again by me - and the very next full run demonstrated
        # exactly the failure mode this guard exists for: GER40 1.26->1.10,
        # NAS100 1.76->1.10 on 15 trades, AUDUSD 2.08->1.12 on 15 trades, all
        # auto-applied over strictly stronger incumbents because nothing bare-
        # minimum-passing had anything to lose to. Back in, on real evidence
        # this time, not a stance.
        if not self._beats_incumbent(cfg, hold):
            return "mevcut ayardan zayif"
        # Retention: a candidate can beat a weak/absent incumbent while still
        # having mostly evaporated out of sample - beating the incumbent says
        # nothing about whether the edge itself is real. cfg=None (secondary
        # screening in _pick_secondary) has no incumbent to beat above, so this
        # is the only OOS-collapse check that pool gets.
        if not self._generalises(best, getattr(cfg, "symbol", "")):
            return "holdout kenari zayifladi (retention)"
        return ""

    def _beats_incumbent(self, cfg, hold: dict[str, Any]) -> bool:
        """Is this holdout at least as good as the live config's own holdout?

        Compared on ``Result.score`` - the same thin-sample and drawdown
        discounted number the rest of the optimizer ranks on - so a candidate
        cannot win on raw R while trading a handful of times.
        """
        if cfg is None:
            return True
        summary = getattr(cfg, "opt_summary", None) or {}
        previous = summary.get("holdout") or {}
        age_days = (time.time() - float(getattr(cfg, "opt_updated_at", 0.0) or 0.0)) / 86400.0
        if not previous or age_days > self.INCUMBENT_GUARD_DAYS:
            return True
        old_score = float(previous.get("score", 0.0) or 0.0)
        if old_score <= 0.0:
            return True
        # The incumbent's score is only comparable if it was measured under the
        # same spread assumption. It very often is not: the live tick spread is
        # measured continuously now, and the moment that measurement clears its
        # sample threshold the search starts charging a different - higher -
        # cost than the incumbent was ever scored against.
        #
        # Vetoing on that comparison makes the calibration unreachable by
        # construction. An honest candidate trades less and earns less in
        # total, so it loses to a config whose score was inflated by a cost
        # model we have since measured to be wrong: XAUUSD scored 79.4 at
        # scale 1.0 against 45.1 at the measured 1.25, CHFJPY 10.4 against 7.4
        # at 3.00. The older number is not better, it is differently measured.
        #
        # So the veto is skipped when the assumption moved. Nothing else is
        # relaxed - the candidate still has to clear validation, the
        # consistency ratio, both cost gates and the retention check, all of
        # which are absolute rather than relative to the incumbent.
        # Read from the summary, which is where apply() writes it - not from
        # ``previous`` (the holdout block inside it).
        old_scale = float(summary.get("spread_scale", 0.0) or 0.0)
        if old_scale <= 0.0:
            # Nothing recorded means the config predates this field, and every
            # such config WAS measured at 1.0: walk_forward's spread_scale
            # defaults to 1.0 and the optimizer did not pass one at all before
            # the calibration shipped. So this is a fact about how it was
            # measured, not a guess - and treating it as "unknown, skip the
            # comparison" would drop the incumbent guard for the entire book
            # on the next run, including the ~10 symbols whose measured scale
            # is 1.0 and whose assumption therefore never moved.
            #
            # A config applied in the narrow window between the calibration
            # shipping and this field existing could have used a real scale
            # while recording none. The error that produces is a wrongly
            # KEPT incumbent, never a wrongly applied candidate, which is the
            # safe direction and self-clears on the first apply.
            old_scale = 1.0
        new_scale = self._spread_scale(getattr(cfg, "symbol", ""))
        # Half a ratio-bucket (SPREAD_RATIO_STEP = 0.1). Round before the
        # compare: ``1.05 - 1.0`` is ``0.050000000000000044`` in IEEE float,
        # which would otherwise look like a material move and drop the guard
        # for every unrecorded incumbent whose live median sits on 1.05
        # (NZDUSD's window is exactly that). Same bucket = same assumption.
        if round(abs(new_scale - old_scale), 2) > 0.05:
            LOG.emit(f"{cfg.symbol}: mevcut ayar farkli spread olcegiyle olculmus "
                     f"({old_scale or 'kayitsiz'} -> {new_scale:.2f}), skor kiyasi "
                     f"atlandi - aday kendi kapilariyla degerlendirildi.",
                     "OPT", cfg.symbol)
            return True
        new_score = float(hold.get("score", 0.0) or 0.0)
        if new_score >= old_score:
            return True
        LOG.emit(f"{cfg.symbol}: yeni aday mevcut ayardan zayif "
                 f"(test skoru {new_score:.2f} < {old_score:.2f}), uygulanmadi.",
                 "OPT", cfg.symbol)
        return False

    def _pick_secondary(self, primary: dict[str, Any],
                        attempts: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Best validated candidate from a *different* family than the primary.

        Two entries per symbol only help if they fire on different bars for
        different reasons; a second timeframe of the same family is the same bet
        sampled twice, so the family must differ. It has to clear exactly the
        same gates the primary did - both out-of-sample slices, the consistency
        ratio and the cost ceiling - because a weaker second signal does not add
        opportunity, it dilutes the edge.
        """
        family = primary.get("strategy")
        pool = [a for a in attempts
                if a.get("ok") and a.get("validated") and a.get("strategy") != family
                and self._is_improvement(None, a["best"])]
        if not pool:
            return None
        return self._pick_by_validation(pool)

    def apply_secondary(self, symbol: str, attempt: dict[str, Any] | None) -> dict[str, Any]:
        """Store (or clear) the second signal. Never flips ``ensemble_enabled``."""
        with (self.entry_lock if self.entry_lock is not None else contextlib.nullcontext()):
            return self._apply_secondary_locked(symbol, attempt)

    def _apply_secondary_locked(self, symbol: str, attempt: dict[str, Any] | None) -> dict[str, Any]:
        """Body of apply_secondary() - callers must already hold entry_lock.

        Split out so apply() can clear a stale secondary in the *same*
        critical section as the primary write below, instead of releasing
        the lock and re-acquiring it a moment later - the gap that let a
        fresh secondary-tagged fill land under the old family/timeframe
        pairing between the two writes.
        """
        cfg = self.store.symbols.get(symbol)
        if cfg is None:
            return {"ok": False, "error": "sembol yok"}
        # Same reasoning as apply(): client.positions() reads [] on disconnect
        # exactly like "nothing open", which would let live_tagged below fail
        # closed as empty and skip the holdback - never actually verifying
        # whether a secondary-tagged position is open.
        if not self.client.connected:
            return {"ok": False,
                    "error": f"{symbol}: MT5 baglantisi yok, acik pozisyon dogrulanamiyor - "
                             f"islem guvenlik icin reddedildi"}
        next_identity = ((attempt["strategy"], attempt["timeframe"]) if attempt is not None
                        else ("", ""))
        identity_changing = (cfg.secondary_strategy, cfg.secondary_timeframe) != next_identity
        tf_allow = self.store.opt_params().get("strategy_timeframes")
        allow = tf_allow if isinstance(tf_allow, dict) else None
        if attempt is not None and not strategy_allows_timeframe(
                attempt["strategy"], attempt["timeframe"], allow):
            # _pick_secondary only ranks already-searched attempts, and the
            # search itself is TF-gated - this should not fire - but apply()
            # enforces the same lock on the primary, so the secondary getting
            # a free pass here would be the one place a dead pairing (one
            # stored while an operator had that family pinned to a narrower set
            # of bars) could still land, silently unusable the moment ensemble
            # was switched on.
            attempt = None
        if attempt is None:
            patch = {"secondary_strategy": "", "secondary_timeframe": "",
                     "secondary_params": {}, "secondary_score": 0.0,
                     "secondary_updated_at": 0.0, "secondary_summary": {}}
        else:
            best = attempt["best"]
            params = {k: v for k, v in best["params"].items() if k in OPT_FIELDS}
            # Same gate as apply(): engine.py builds the secondary signal's
            # exit payload straight from this dict, so a broken exit model
            # here drives a real position exactly like the primary one does.
            bad = invalid_exit_param(params)
            if bad:
                LOG.emit(f"Ikincil cikis parametresi reddedildi: {bad}", "OPT", symbol)
                return {"ok": False, "error": f"ikincil cikis parametresi gecersiz: {bad}"}
            patch = {
                "secondary_strategy": attempt["strategy"],
                "secondary_timeframe": attempt["timeframe"],
                "secondary_params": params,
                "secondary_score": float(best["score"]),
                "secondary_updated_at": time.time(),
                "secondary_summary": {
                    "holdout_retention": round(self.holdout_retention(best), 3),
                    "holdout": best.get("holdout", {}),
                    "validation": best.get("validation", {}),
                    "selection": best.get("selection", {}),
                    "positive_ratio": best.get("positive_ratio", 0.0),
                    "params": params,
                },
            }
        patch = {k: v for k, v in patch.items() if k in SECONDARY_FIELDS}
        # Same reasoning as apply()'s pending_exit_patch default: this call is
        # the new authoritative secondary candidate (or clears it entirely),
        # so any earlier held-back refine is superseded unless the elif below
        # holds one back again - otherwise a stale pending_secondary_exit_patch
        # could get replayed on top of this by Engine._apply_pending_exits.
        patch["pending_secondary_exit_patch"] = {}
        # Caller (apply_secondary() or apply()) already holds entry_lock -
        # held across the open-tagged-position check + the write so a fill
        # cannot land in the gap between them (see Engine.entry_lock).
        # secondary_tickets is engine-owned but persisted, so it is readable
        # here without an engine reference.
        tagged = {int(t) for t in (self.store.get_setting("secondary_tickets", []) or [])}
        # A fill Engine._try_entry couldn't identify/close is a still-open
        # secondary candidate too - it just has not made it into ``tagged``
        # yet (or ever will, since Engine safety-closes it on sight). Gating
        # only on ``tagged`` here meant that exact in-flight window - between
        # a secondary fill landing and either its tag or its safety-close
        # being recorded - let an identity swap through against a position
        # neither this check nor manage_positions() could yet see as "ours".
        orphan_tickets = {int(t) for t in (self.store.get_setting("secondary_orphan_tickets", []) or [])}
        orphan_scan = self.store.get_setting("secondary_orphan_scan", {}) or {}
        pending_scan = symbol in orphan_scan and int(orphan_scan[symbol].get("magic", -1)) == cfg.magic
        watch_tickets = tagged | orphan_tickets
        same_magic = self.client.positions(magic=cfg.magic) if watch_tickets else []
        if watch_tickets and not self.client.connected:
            # Same mid-call disconnect gap as apply(): this positions() call
            # could have failed and returned [] regardless of what is really
            # open, which would make live_tagged/live_orphan wrongly look empty.
            return {"ok": False,
                    "error": f"{symbol}: MT5 baglantisi koptu, acik ikincil pozisyon "
                             f"dogrulanamadi - islem guvenlik icin reddedildi"}
        live_tagged = [p for p in same_magic if p["ticket"] in tagged]
        live_orphan = [p for p in same_magic if p["ticket"] in orphan_tickets]
        if identity_changing:
            # A position tagged secondary was opened, sized and its exits
            # picked under the CURRENT secondary_strategy/timeframe's ATR.
            # manage_positions() only falls back to the primary's exits
            # once cfg.secondary_strategy is empty - clearing it takes
            # effect immediately, but replacing it with a *different*
            # family/TF would otherwise hand that same still-open ticket
            # to a signal it was never opened or sized under, same hazard
            # apply() guards for the primary. An unresolved orphan ticket or
            # a still-in-progress orphan scan is the same risk before it is
            # even tagged, so it holds the swap back too.
            if live_tagged or live_orphan or pending_scan:
                blocked = len(live_tagged) + len(live_orphan)
                note = " (+ tanimlanamayan ticket taramasi devam ediyor)" if pending_scan else ""
                return {"ok": False,
                        "error": f"{symbol}: {blocked} acik ikincil-sinyal pozisyonu var{note}, "
                                 f"ikincil strateji degistirilemedi (once kapanmasini bekleyin)"}
        elif attempt is not None and (live_tagged or live_orphan or pending_scan):
            # Same family/timeframe, just refined params ("refine"). Engine's
            # manage_positions() re-reads cfg.secondary_params live every
            # cycle via _secondary_config(), the same live-reread hazard
            # apply() holds back exit/risk fields for on the primary side -
            # this path had no equivalent holdback at all until now. L2: the
            # identity-swap block above already treats live_orphan/pending_scan
            # as equal risk to live_tagged (an unresolved/untracked fill is
            # exactly the same "position under this magic may exist" hazard) -
            # this elif only checked live_tagged, so a refine could sail
            # through while an orphan ticket or scan window was still open.
            sec_params = patch.get("secondary_params", {})
            held_back = [k for k in sec_params if k in EXIT_RISK_FIELDS]
            if held_back:
                pending = {k: sec_params[k] for k in held_back}
                patch["secondary_params"] = {k: v for k, v in sec_params.items()
                                             if k not in EXIT_RISK_FIELDS}
                if "secondary_summary" in patch:
                    summary_params = {k: v for k, v in patch["secondary_summary"].get("params", {}).items()
                                      if k not in EXIT_RISK_FIELDS}
                    patch["secondary_summary"] = {**patch["secondary_summary"], "params": summary_params,
                                                  "pending_exit_fields": sorted(held_back)}
                patch["pending_secondary_exit_patch"] = pending
                blocked = len(live_tagged) + len(live_orphan)
                note = " (+ tanimlanamayan ticket taramasi devam ediyor)" if pending_scan else ""
                LOG.emit(f"{symbol}: {blocked} acik ikincil-sinyal pozisyonu var{note}, "
                         f"ikincil cikis/risk parametreleri ({', '.join(sorted(held_back))}) "
                         f"pozisyon kapanana kadar bekletildi.", "OPT", symbol)
        # update_symbol drops None values, so an empty candidate has to be
        # written as empty strings/dicts rather than None to actually clear.
        updated = self.store.update_symbol(symbol, patch)
        return {"ok": updated is not None, "symbol": symbol}

    def apply(self, symbol: str, params: dict[str, Any], score: float,
              detail: dict[str, Any] | None = None,
              timeframe: str | None = None, strategy: str | None = None) -> dict[str, Any]:
        cfg = self.store.symbols.get(symbol)
        if cfg is None:
            return {"ok": False, "error": "sembol yok"}
        next_tf = timeframe if timeframe in TIMEFRAMES else cfg.timeframe
        next_strat = strategy if strategy in STRATEGIES else cfg.strategy
        # Same custom map the search itself used, not always the shipped
        # default - a user-widened or -narrowed override would otherwise
        # search under one allowlist and get validated against another.
        tf_allow = self.store.opt_params().get("strategy_timeframes")
        allow = tf_allow if isinstance(tf_allow, dict) else None
        if not strategy_allows_timeframe(next_strat, next_tf, allow):
            return {"ok": False,
                    "error": f"{next_strat}/{next_tf} eslesmesi yasak "
                             f"(scalp yalnizca M5; uzun TF swing ailelerine ait)"}
        primary_changed = (
            (strategy in STRATEGIES and strategy != cfg.strategy)
            or (timeframe in TIMEFRAMES and timeframe != cfg.timeframe)
        )
        applied_params = {k: v for k, v in params.items() if k in OPT_FIELDS}
        # Last gate before this reaches a live symbol. The API checks the same
        # bounds on its own request bodies, but auto-apply (Optimizer.start
        # with apply_best) lands here straight off a search result without
        # touching an HTTP handler - and the search grid is user-editable, so
        # an axis containing 0 could be searched, win, and switch that
        # symbol's trail off permanently. Refused rather than clamped: a
        # candidate scored under an exit model this broken is not a candidate
        # whose numbers should be quietly rewritten into a different one.
        bad = invalid_exit_param(applied_params)
        if bad:
            LOG.emit(f"Cikis parametresi reddedildi: {bad}", "OPT", symbol)
            return {"ok": False, "error": f"cikis parametresi gecersiz: {bad}"}
        patch = dict(applied_params)
        if timeframe in TIMEFRAMES:
            patch["timeframe"] = timeframe
        if strategy in STRATEGIES:
            patch["strategy"] = strategy
        patch["opt_score"] = float(score)
        patch["opt_updated_at"] = time.time()
        if detail:
            patch["opt_summary"] = {
                "holdout_retention": round(self.holdout_retention(detail), 3),
                "holdout": detail.get("holdout", {}),
                "validation": detail.get("validation", {}),
                "selection": detail.get("selection", {}),
                "holdout_days": detail.get("holdout_days", 0.0),
                "positive_ratio": detail.get("positive_ratio", 0.0),
                "params": applied_params,
                # The spread scale this candidate was measured under. Every
                # number beside it - score, expectancy, cost_per_trade_r - is
                # only meaningful against that assumption, and _beats_incumbent
                # compares scores across runs. Without it, a config measured
                # while the search still charged the raw bar spread would be
                # compared, as though like for like, against one measured at
                # the tick spread the live gate actually enforces.
                "spread_scale": round(self._spread_scale(symbol), 3),
            }
        else:
            # No evidence came with this apply, so the evidence already on the
            # row may no longer describe what trades. Everything else here is
            # written unconditionally - strategy, timeframe, params, score - so
            # without this the summary quietly outlives its own configuration.
            #
            # It is not decoration: portfolio-gates decides measurability, the
            # cost gate and the review layer from holdout.trades/expectancy/
            # cost_per_trade_r, risk._edge_metric sizes from holdout.net_r over
            # holdout_days, and _beats_incumbent compares the next candidate
            # against holdout and spread_scale. All three would read numbers
            # earned by different parameters as current.
            #
            # Only dropped when it provably disagrees. Re-applying the same
            # numbers keeps its record; the summary is void when the config it
            # measured is not the config that results.
            recorded = (getattr(cfg, "opt_summary", None) or {}).get("params")
            if isinstance(recorded, dict) and any(
                    recorded.get(k) != v for k, v in patch.items() if k in recorded):
                patch["opt_summary"] = {}
        # Held across the open-position check + the write so the engine's
        # own entry path (same lock; see Engine.entry_lock) cannot land a
        # fresh fill under cfg.magic in the gap between "nothing open yet"
        # and this patch actually landing - the same race DELETE/PATCH close
        # for the web routes, from the optimizer's side of the same field.
        with (self.entry_lock if self.entry_lock is not None else contextlib.nullcontext()):
            # self.client.positions() returns [] both when genuinely flat and
            # when MT5 is disconnected - trusting an empty result during a
            # disconnect would skip the holdback below entirely and write
            # exit/risk fields straight onto a position we simply couldn't
            # see, instead of holding them back like normal. Fail closed the
            # same way the web PATCH routes already do (_require_connected).
            if not self.client.connected:
                return {"ok": False,
                        "error": f"{symbol}: MT5 baglantisi yok, acik pozisyon dogrulanamiyor - "
                                 f"islem guvenlik icin reddedildi"}
            # A live position was opened, sized and its trail managed under the
            # CURRENT config's ATR assumptions - checked regardless of whether
            # this is a family swap or a same-family "refine", since engine.py's
            # manage_positions/_update_stop re-read cfg live every cycle, not a
            # snapshot taken at entry.
            open_here = [p for p in self.client.positions() if p["magic"] == cfg.magic]
            if not self.client.connected:
                # positions() itself can flip this False mid-call (same class
                # of gap as MT5Client.close_all()) - the pre-check above only
                # proves the connection was alive a moment earlier. An empty
                # open_here from a call that just failed is not "flat".
                return {"ok": False,
                        "error": f"{symbol}: MT5 baglantisi koptu, acik pozisyon dogrulanamadi - "
                                 f"islem guvenlik icin reddedildi"}
            # A same-magic orphan ticket (engine.py's H1 tracking) is already
            # a real MT5 position, so it is already IN open_here above - only
            # the zero-candidate orphan-scan window needs adding here: that
            # fill is genuinely invisible to client.positions() yet (that is
            # the entire reason the scan exists), so open_here alone would
            # read this magic as flat and skip both the family-swap block and
            # the exit/risk holdback below for a position that may still turn
            # up. Same risk class apply_secondary() already guards for.
            orphan_scan = self.store.get_setting("secondary_orphan_scan", {}) or {}
            pending_scan = (symbol in orphan_scan
                            and int(orphan_scan[symbol].get("magic", -1)) == cfg.magic)
            # Default: this apply() is the new authoritative candidate, so any
            # earlier held-back patch is superseded and must be dropped - the
            # held-back branch below overwrites this with the fresh one when
            # (and only when) it actually holds something back again. Without
            # this, a stale pending_exit_patch from a PREVIOUS apply() (while
            # a position was still open) would survive an unrelated later
            # apply() that landed directly while flat, and then get replayed
            # on top of it by Engine._apply_pending_exits the next time this
            # magic is seen flat - silently reverting the newer values.
            patch["pending_exit_patch"] = {}
            if open_here or pending_scan:
                scan_note = " (+ tanimlanamayan ticket taramasi devam ediyor)" if pending_scan else ""
                if primary_changed:
                    # Swapping the family out from under it mid-trade hands that
                    # same position's ongoing trail/breakeven math to a
                    # different, unrelated strategy's params entirely - wait for
                    # flat rather than let that happen.
                    return {"ok": False,
                            "error": f"{symbol}: {len(open_here)} acik pozisyon var{scan_note}, "
                                     f"strateji/TF degisikligi pozisyon kapanana kadar bekliyor "
                                     f"(parametre iyilestirmesi degil, aile degisikligi)"}
                # Same family/timeframe: entry-signal params (t3_length, adx_min,
                # etc.) are safe to land immediately - they only shape the NEXT
                # entry. Exit/risk params (the hard stop and the trail) are
                # held back so the open position keeps trading under the numbers
                # it was actually opened and sized against; they take effect
                # once the position is flat.
                held_back = [k for k in patch if k in EXIT_RISK_FIELDS]
                if held_back:
                    pending = {k: patch[k] for k in held_back}
                    patch = {k: v for k, v in patch.items() if k not in EXIT_RISK_FIELDS}
                    # Previously the held-back values were only logged, never
                    # stored - "take effect once flat" was a comment, not
                    # code, so the new exit/risk candidate was silently lost
                    # forever unless another apply() happened to land later
                    # while the symbol was flat. Engine._apply_pending_exits
                    # writes this the moment this magic is next seen flat.
                    patch["pending_exit_patch"] = pending
                    if "opt_summary" in patch:
                        # opt_summary.params otherwise claimed the held-back
                        # exit values were live immediately - drop them from
                        # the reported "applied" set and flag what's pending
                        # so the UI can show it honestly.
                        summary_params = {k: v for k, v in patch["opt_summary"].get("params", {}).items()
                                          if k not in EXIT_RISK_FIELDS}
                        patch["opt_summary"] = {**patch["opt_summary"], "params": summary_params,
                                                "pending_exit_fields": sorted(held_back)}
                    LOG.emit(f"{symbol}: {len(open_here)} acik pozisyon var{scan_note}, "
                             f"cikis/risk parametreleri ({', '.join(sorted(held_back))}) "
                             f"pozisyon kapanana kadar bekletildi.", "OPT", symbol)
            # Clear the stale secondary BEFORE writing the new primary family.
            # Doing it after update_symbol left a window where primary landed
            # and a failed clear (disconnect mid-call) was ignored - apply
            # still returned ok:True with the old secondary attached.
            if primary_changed and cfg.has_secondary():
                # Called inline (not via apply_secondary(), which re-acquires
                # entry_lock and would deadlock on this plain Lock) so the
                # clear lands in the SAME critical section as the primary
                # write below.
                sec_clear = self._apply_secondary_locked(symbol, None)
                if not sec_clear.get("ok"):
                    return {"ok": False,
                            "error": sec_clear.get(
                                "error",
                                f"{symbol}: eski ikincil sinyal temizlenemedi - "
                                f"aile degisikligi reddedildi"),
                            "symbol": symbol, "config": None}
            updated = self.store.update_symbol(symbol, patch)
        return {"ok": updated is not None, "symbol": symbol, "config": updated.to_dict() if updated else None}
