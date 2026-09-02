from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor
from concurrent.futures import wait as futures_wait
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from typing import Any

import numpy as np

from . import backtest
from .holdout_cost import charged_holdout
from .logbus import LOG
from .models import (
    EXIT_RISK_FIELDS,
    OPT_FIELDS,
    PRIMARY_LAND_KEYS,
    SEARCH_TIMEFRAMES,
    STRATEGIES,
    STRATEGY_TIMEFRAMES,
    SWING_GRID_OVERLAY,
    TIMEFRAMES,
    SymbolConfig,
    invalid_exit_param,
    is_scalp_strategy,
    strategy_allows_timeframe,
    uses_swing_exits,
)
from .mt5client import Bars, MT5Client, timeframe_seconds
from .spread_calibration import calibrate
from .store import Store
from .strategy import absent_regime_gates_to_zero, searchable_axes, unstamped_gates_to_zero

APPLY_STAMP_MISSING = "uygulama damgasi yok (holdout/validated/holdout_days)"


def tf_lock_status(tf_allow: Any) -> str:
    """OPT start-line fragment: whether the family→TF map actually restricts.

    ``STRATEGY_TIMEFRAMES`` empty means every family may search every TF
    (scalps on M15+ included). A hardcoded "scalp TF kilidi acik" lied after
    that map was cleared — XAUUSD is live burst/M15.
    """
    if isinstance(tf_allow, dict) and tf_allow:
        return "aile TF kilidi acik"
    return "aile TF kilidi kapali"


def family_max_combos(opt_blob: dict[str, Any] | None, family: str,
                      default: int) -> int:
    """Per-family search budget, else the global ``max_combos``.

    Absent map, missing family, unreadable value, or a non-positive override
    all fall back so a saved blob cannot silently disable a family (0) or
    change live searches until the operator writes a real number.
    """
    fallback = int(default)
    raw = (opt_blob or {}).get("strategy_max_combos")
    if not isinstance(raw, dict) or family not in raw:
        return fallback
    try:
        n = int(raw[family])
    except (TypeError, ValueError):
        return fallback
    return n if n > 0 else fallback


def longest_first(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Submission order for the sweep pool: most expensive first.

    Every sweep is independent, so the pool's wall clock is a scheduling
    problem, and the atom is a whole (symbol, timeframe, family) sweep - far
    too coarse to pack evenly. A single-symbol search is ~24 units on 14 cores
    and the units differ by orders of magnitude: shipped grids run 1080
    (ichimoku) to 2,073,600 (dual_t3), and coverage_budget hands the bigger
    grids a bigger sampled budget on top.

    Submission order used to be the deterministic timeframe x family order,
    which is uncorrelated with cost, so a long sweep could be queued last and
    then run alone while everything else was finished. Measured on the 31.08
    US30 run: 3 of 14 workers busy for the final ten minutes of 62.

    Longest-processing-time-first is the standard heuristic for exactly this
    (makespan within 4/3 of optimal) and costs nothing here - no worker
    protocol change, and results are untouched because _finish_symbol re-sorts
    attempts by ``order`` before picking a winner. Ties fall back to ``order``
    so two equal-cost sweeps cannot swap between runs. A job with no hint
    sorts last rather than raising; it still runs.

    Returns a new list - the caller keeps the deterministic queue that the
    single-process fallback iterates.
    """
    return sorted(jobs,
                  key=lambda j: (-int(j.get("cost_hint") or 0),
                                 int(j.get("order") or 0)))


def coverage_budget(grid_totals: dict[str, int], max_combos: int) -> dict[str, int]:
    """Split one flat per-family cap by how much space each family actually has.

    A flat ``max_combos`` is only fair when every family's grid is the same
    size, and they are not: shipped 31.08, ichimoku is 180 combos and
    stoch_flip is 64,800. At a 2000 cap the coarse pass covers ichimoku,
    mtf_pullback and burst *exhaustively* and covers stoch_flip at 3.1%. The
    optimizer then ranks those families head to head to pick a symbol's
    winner, so the small-grid family presents its true optimum while the
    big-grid family presents the best of a random 3% draw - a bias toward
    small grids that has nothing to do with which idea trades better, plus
    big-grid winners that move with ``combo_seed``.

    Budget handed to a family beyond its own grid size buys nothing; there is
    no unexplored combo left to spend it on. So: give every family
    ``min(grid, cap)``, then hand the surplus the small grids could not use to
    the families still short, in proportion to how much space they have.

    Two deliberate properties:

    * the **total does not grow** - this is paid for out of waste, not out of
      wall clock, so worker count and run time are unchanged;
    * **no family goes below** ``min(grid, cap)`` - a search tuned against
      today's behaviour cannot regress.

    It narrows the gap rather than closing it. Equalising coverage outright
    would mean either trimming the bloated grids or spending more time, and
    both are decisions with their own trade-offs.
    """
    totals = {str(k): max(0, int(v)) for k, v in (grid_totals or {}).items()}
    if not totals:
        return {}
    cap = max(0, int(max_combos))
    out = {fam: min(total, cap) for fam, total in totals.items()}

    surplus = sum(cap - out[fam] for fam in totals)
    short = {fam: totals[fam] - out[fam] for fam in totals if totals[fam] > out[fam]}
    room = sum(short.values())
    if surplus <= 0 or room <= 0:
        return out

    # Proportional to unexplored space, so the family furthest from covering
    # its grid gets the largest share. Floor division keeps the total under
    # the pool; the remainder is left unspent rather than handed to whichever
    # family happens to sort first.
    for fam, gap in short.items():
        out[fam] = min(totals[fam], out[fam] + surplus * gap // room)
    return out


def run_combo_budget(
    opt_blob: dict[str, Any] | None,
    families: list[str],
    timeframes: list[str],
    max_combos: int,
    refine_rounds: int,
    n_symbols: int,
    allow: dict[str, list[str]] | None = None,
    alloc: dict[str, int] | None = None,
) -> tuple[int, dict[str, int]]:
    """Panel combo_total must match walk_forward spend, including family caps.

    Progress used to count every sweep as ``sweep_budget(max_combos, …)``.
    That was honest only while every family shared the global cap. A live
    ``strategy_max_combos.stoch_flip = 28800`` against a 2000 global cap
    spends 14× on that family; the bar still reported 2000. Percentage
    stayed consistent; wall-clock and the absolute number did not.
    """
    table = allow if isinstance(allow, dict) else STRATEGY_TIMEFRAMES
    per_sweep: dict[str, int] = {}
    total = 0
    for fam in families:
        # ``alloc`` is coverage_budget's grid-sized default. The operator's
        # explicit strategy_max_combos still overrides it, and this must stay
        # the same expression _plan_symbol spends by or the panel total drifts
        # from the real work again.
        cost = backtest.sweep_budget(
            family_max_combos(opt_blob, fam,
                              (alloc or {}).get(fam, max_combos)), refine_rounds)
        per_sweep[fam] = cost
        n_tf = sum(1 for tf in timeframes
                   if strategy_allows_timeframe(fam, tf, table))
        total += int(n_symbols) * n_tf * cost
    return total, per_sweep


def _ranked_finalists(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Params + both OOS slices for the ranked top 10. Old runs omit ``top``."""
    rows: list[dict[str, Any]] = []
    for candidate in list(report.get("top") or [])[:10]:
        rows.append({
            "params": dict(candidate.get("params") or {}),
            "score": candidate.get("score"),
            "validation": dict(candidate.get("validation") or {}),
            "holdout": dict(candidate.get("holdout") or {}),
        })
    return rows


def _grid_axis_equal(left: Any, right: Any) -> bool:
    """Numeric search lists compare equal across int/float spelling."""
    if not isinstance(left, list) or not isinstance(right, list):
        return False
    if len(left) != len(right):
        return False
    for a, b in zip(left, right, strict=True):
        try:
            if float(a) != float(b):
                return False
        except (TypeError, ValueError):
            if a != b:
                return False
    return True


_SWEEP_BAR_FIELDS = ("time", "open", "high", "low", "close", "spread", "volume")


def write_sweep_bars(dest: Path, bars: Any) -> Path:
    """Dump one TF window as mmap-able ``.npy`` files.

    Thirteen families on the same TF used to pickle the same arrays into
    thirteen ProcessPool jobs. One folder, workers mmap it read-only.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    if (dest / "close.npy").exists():
        return dest
    for name in _SWEEP_BAR_FIELDS:
        np.save(dest / f"{name}.npy", np.asarray(getattr(bars, name)),
                allow_pickle=False)
    return dest


def load_sweep_bars(dest: Path | str) -> dict[str, Any]:
    dest = Path(dest)
    return {
        name: np.load(dest / f"{name}.npy", mmap_mode="r")
        for name in _SWEEP_BAR_FIELDS
    }


def _sweep_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Run one timeframe x strategy walk-forward in a separate process.

    Every sweep is fully independent - same bars in, its own grid, its own
    three-way split - so the grid search is embarrassingly parallel. Only plain
    arrays and dicts cross the process boundary; MT5 is never touched here (the
    bars were already fetched by the parent under the client lock).
    """
    arrays = load_sweep_bars(payload["bars_path"])
    bars = Bars.__new__(Bars)
    for name in _SWEEP_BAR_FIELDS:
        setattr(bars, name, arrays[name])
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
            charge_costs=bool(payload.get("charge_costs", True)),
            selection_metric=str(payload.get("selection_metric") or "score"),
            risk_dollar=float(payload.get("risk_dollar") or 1.0),
            combo_seed=int(payload["combo_seed"]) if payload.get("combo_seed") is not None else 7,
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
        # Engine reference at __init__ time and must not require one. apply()
        # only takes it when set, so tests and any other caller that never
        # wires an engine keep working lock-free.
        self.entry_lock: threading.Lock | None = None
        # Bars fetched at plan time, reused for incumbent replay (AS3).
        self._bar_snap: dict[tuple[str, str], Any] = {}
        self._sweep_bars_dir: Path | None = None
        # First store/import failure of _spread_scale gets one WARN; a later
        # success re-arms it. Same latch the engine uses for diagnostic flushes:
        # returning 1.0 on a frozen read is the old behaviour (search still
        # runs) but quoting that 1.0 as "no measurement" is a ~10% cheap cost.
        self._spread_scale_warned = False

    def _ensure_sweep_bars_dir(self) -> Path:
        d = getattr(self, "_sweep_bars_dir", None)
        if d is None:
            d = Path(tempfile.mkdtemp(prefix="micofx_opt_bars_"))
            self._sweep_bars_dir = d
        return Path(d)

    def _clear_sweep_bars(self) -> None:
        d = getattr(self, "_sweep_bars_dir", None)
        self._sweep_bars_dir = None
        if d is not None:
            shutil.rmtree(d, ignore_errors=True)

    @property
    def busy(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def status(self) -> dict[str, Any]:
        """Panel poll copy. Drops unread ``top`` / ``baseline`` / ``tried``.

        Those blobs are most of /api/state while a search is mid-book
        (Claude 27.08). renderOptJob only reads best / incumbent / keep_reason
        / validated / holdout_retention. The live ``self.job`` keeps the
        full rows for opt_runs.
        """
        with self._lock:
            snap = dict(self.job, busy=self.busy)
        rows = snap.get("results")
        if not isinstance(rows, list):
            return snap
        slim: list[Any] = []
        for raw in rows:
            if not isinstance(raw, dict):
                slim.append(raw)
                continue
            row = dict(raw)
            row.pop("top", None)
            row.pop("baseline", None)
            row.pop("tried", None)
            slim.append(row)
        snap["results"] = slim
        return snap

    def cancel(self) -> dict[str, Any]:
        self._cancel.set()
        running = False
        snap: dict[str, Any] = {}
        with self._lock:
            running = bool(self.busy) or str((self.job or {}).get("state") or "") == "running"
            if running:
                snap = dict(self.job or {})
        if running:
            # Restart used to SIGTERM before _run noticed the event, so
            # last_opt_job stayed "running" with no OPT cancel line. Write
            # now; _run's finish overwrites the same cancelled state.
            current = snap.get("current") or "?"
            done = snap.get("combo_done")
            total = snap.get("combo_total")
            LOG.emit(
                f"Optimizasyon yari da kesiliyor: {current} {done}/{total}",
                "OPT")
            setter = getattr(self.store, "set_setting", None)
            if callable(setter):
                getter = getattr(self.store, "get_setting", None)
                prev = getter("last_opt_job", {}) if callable(getter) else {}
                if not isinstance(prev, dict):
                    prev = {}
                setter("last_opt_job", {**prev, "state": "cancelled",
                                        "finished_at": time.time(),
                                        "current": snap.get("current") or "",
                                        "combo_done": done,
                                        "combo_total": total})
            # Panel polls status() (self.job), not last_opt_job. Leave
            # finished_at to _run so busy workers are still visible as
            # cancelled-in-progress rather than a frozen "Calisiyor".
            self._set(state="cancelled")
        return {"ok": True, "message": "Iptal istegi gonderildi."}

    def start(self, symbols: list[str] | None = None, apply_best: bool = True,
              bars: int | None = None, source: str = "manual",
              timeframes: list[str] | None = None,
              force: bool = False,
              strategies: list[str] | None = None) -> dict[str, Any]:
        with self._lock:
            if self.busy:
                return {"ok": False, "error": "Optimizasyon zaten calisiyor."}
            # Waives the settling-time hold in reject_reason() for this run
            # only. Instance state rather than a threaded argument because a
            # run is exclusive - the busy check above is the guarantee.
            self._force_apply = bool(force)
            # Closing a symbol is a decision, not a death sentence. A full
            # scan used to drop disabled names, so a charged-negative close
            # (JPN225 / SpotBrent / UK100) could never be re-scored after the
            # grid moved - the operator had to type every name. Disabled
            # symbols stay in targets; _finish_symbol will not apply or enable
            # them. Operator start() with no name list still includes disabled.
            if symbols:
                targets = [s for s in symbols if s in self.store.symbols]
            else:
                targets = list(self.store.symbols)
            if not targets:
                # "Sembol secilmedi" was the answer to three different
                # situations, and it was the wrong answer to two of them.
                #
                # The one that actually happens: the picker's selection is a
                # Set that survives a symbol leaving the book, so a name
                # selected before the book was cut is still sent afterwards.
                # Every name filters out above, and the panel reported "no
                # symbol selected" about a request that named several. Nothing
                # in that message points at the cause, and the picker shows no
                # chip lit either (the "Tumu" chip only lights at size 0), so
                # there is nothing on screen to contradict it.
                if symbols:
                    unknown = [str(s) for s in symbols]
                    return {"ok": False, "error": (
                        f"Kitapta olmayan sembol: {', '.join(unknown)}. "
                        f"Secim listesi eskimis olabilir - sayfayi yenileyin "
                        f"veya 'Tumu' secip tekrar deneyin.")}
                return {"ok": False, "error": "Sembol secilmedi."}
            # One-off restriction of this run to a subset of the configured
            # timeframes (e.g. "just scan M5 today") - None/empty means the
            # saved opt_params selection, same as before this existed.
            requested = [str(t) for t in (timeframes or [])]
            if requested:
                dropped = [t for t in requested if t not in TIMEFRAMES]
                kept = [t for t in requested if t in TIMEFRAMES]
                if dropped:
                    LOG.emit(
                        f"Aranamayan zaman dilimi istekten dusuruldu: "
                        f"{', '.join(dropped)} (aranan: {', '.join(TIMEFRAMES)})",
                        "OPT")
                if not kept:
                    return {"ok": False, "error": (
                        f"Aranabilir zaman dilimi yok (istenilen: "
                        f"{', '.join(requested)}; aranan: "
                        f"{', '.join(TIMEFRAMES)})")}
                tf_override = kept
            else:
                tf_override = None
            # Same one-off door as timeframes. store.opt_params() re-appends
            # every shipped family, so a saved subset cannot actually restrict
            # a sweep - so a one-off subset is not persisted into opt_params.
            requested_fam = [str(s) for s in (strategies or [])]
            if requested_fam:
                dropped_fam = [s for s in requested_fam if s not in STRATEGIES]
                kept_fam = [s for s in requested_fam if s in STRATEGIES]
                if dropped_fam:
                    LOG.emit(
                        f"Aranamayan strateji istekten dusuruldu: "
                        f"{', '.join(dropped_fam[:8])} (aranan: {', '.join(STRATEGIES)})",
                        "OPT")
                if not kept_fam:
                    return {"ok": False, "error": (
                        f"Aranabilir strateji yok (istenilen: "
                        f"{', '.join(requested_fam)}; aranan: "
                        f"{', '.join(STRATEGIES)})")}
                fam_override = kept_fam
            else:
                fam_override = None
            self._cancel.clear()
            self._incumbent_holdout_cache = {}
            self.job = {
                "state": "running", "started_at": time.time(), "finished_at": 0.0,
                "symbols": targets, "apply_best": bool(apply_best),
                "source": str(source or "manual"), "timeframes": tf_override or [],
                "strategies": fam_override or [],
                "force": bool(force),
                "done": 0, "total": len(targets), "current": "",
                "combo_done": 0, "combo_total": 0, "best_score": None,
                "results": [], "error": "",
            }
            self._thread = threading.Thread(
                target=self._run,
                args=(targets, bool(apply_best), bars, tf_override, fam_override),
                name="micofx-optimizer", daemon=True,
            )
            self._thread.start()
            src = str(self.job.get("source") or "manual")
            fam_note = (
                f" stratejiler={'/'.join(fam_override)}" if fam_override else "")
            LOG.emit(
                f"Optimizasyon istendi | kaynak={src} "
                f"apply_best={str(bool(apply_best)).lower()} "
                f"force={str(bool(force)).lower()}{fam_note} | "
                f"{len(targets)} sembol ({', '.join(targets)})",
                "OPT")
            setter = getattr(self.store, "set_setting", None)
            if callable(setter):
                setter("last_opt_job", {
                    "source": src,
                    "apply_best": bool(apply_best),
                    "force": bool(force),
                    "symbols": list(targets),
                    "strategies": list(fam_override or []),
                    "started_at": self.job.get("started_at"),
                    "state": "running",
                })
        return {"ok": True, "job": self.status()}

    # ------------------------------------------------------------------ work

    def _set(self, **patch: Any) -> None:
        with self._lock:
            self.job.update(patch)

    def _run(self, targets: list[str], apply_best: bool, bars_override: int | None,
             tf_override: list[str] | None = None,
             fam_override: list[str] | None = None) -> None:
        # Thread target - nothing downstream of start() is allowed to leave
        # self.job stuck in "running" forever. A bad opt_params value (e.g. a
        # None a client bug slipped through, or hand-edited settings) used to
        # raise straight out of this thread with no handler, silently killing
        # it: the Start button (job.state == "running") stayed disabled
        # indefinitely with no error ever surfaced anywhere.
        try:
            self._run_unsafe(targets, apply_best, bars_override, tf_override,
                             fam_override)
        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
            self._set(state="done", finished_at=time.time(), current="", error=err)
            LOG.emit(f"Optimizasyon beklenmedik hatayla durdu: {err}", "OPT")

    def _run_unsafe(self, targets: list[str], apply_best: bool, bars_override: int | None,
                    tf_override: list[str] | None = None,
                    fam_override: list[str] | None = None) -> None:
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
        timeframes = [t for t in (tf_override or params.get("timeframes") or SEARCH_TIMEFRAMES)
                      if t in TIMEFRAMES] \
            or list(SEARCH_TIMEFRAMES)
        refine_rounds = int(params.get("refine_rounds", 2))
        shared = {k: v for k, v in (params.get("grid") or {}).items() if isinstance(v, list) and v}
        families = [s for s in (fam_override or params.get("strategies") or ["burst"])
                    if s in STRATEGIES] \
            or ["burst"]
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
                     "own": searchable_axes(name, {k: v for k, v in (family_grids.get(name) or {}).items()
                             if isinstance(v, list) and v}),
                     "grid": searchable_axes(name, {**shared, **{k: v for k, v in (family_grids.get(name) or {}).items()
                                           if isinstance(v, list) and v}}),
                     # `_plan_symbol` is a different frame; `shared` here is
                     # not visible there. Without this the first job raised
                     # NameError and `_run` marked the scan done+error.
                     "shared": shared}
                    for name in families]
        # Optional override of the shipped family→TF map (empty list = inherit).
        tf_allow = params.get("strategy_timeframes")
        if not isinstance(tf_allow, dict):
            tf_allow = STRATEGY_TIMEFRAMES

        src = str((self.job or {}).get("source") or "manual")
        LOG.emit(f"Optimizasyon basladi | kaynak={src} | {len(targets)} sembol | son {lookback_days} gun | "
                 f"{segments} segment (son segment dogrulama) | "
                 f"zaman dilimleri {'/'.join(timeframes)} | stratejiler {'/'.join(families)} | "
                 f"cikis: sert ATR stop + ATR takip ({len(variants)} tarama/zaman dilimi) | "
                 f"{tf_lock_status(tf_allow)} | "
                 f"aile basi max {max_combos} kombinasyon (izgara boyutuna gore "
                 f"paylastirilir) | "
                 f"{_worker_count(self.store.system.opt_max_workers)} paralel surec", "OPT")

        self._run_all(targets, lookback_days, bar_cap, variants, min_trades, segments,
                      max_combos, min_positive, plateau, timeframes, refine_rounds,
                      apply_best, tf_allow)

        cancelled = self._cancel.is_set()
        self._set(state="cancelled" if cancelled else "done", finished_at=time.time(), current="")
        with self._lock:
            results = list(self.job.get("results") or [])
            src = str(self.job.get("source") or "manual")
            tag = "Optimizasyon"
        setter = getattr(self.store, "set_setting", None)
        if callable(setter):
            getter = getattr(self.store, "get_setting", None)
            prev = getter("last_opt_job", {}) if callable(getter) else {}
            setter("last_opt_job", {
                **(prev or {}),
                "source": src,
                "state": "cancelled" if cancelled else "done",
                "finished_at": time.time(),
                "applied": [r.get("symbol") for r in results if r.get("applied")],
            })
        if cancelled:
            LOG.emit(f"{tag} iptal edildi | kaynak={src}.", "OPT")
        else:
            applied = [r["symbol"] for r in results if r.get("applied")]
            rejected = [r.get("symbol", "?") for r in results if not r.get("applied")]
            applied_txt = " (" + ", ".join(applied) + ")" if applied else ""
            rejected_txt = " (" + ", ".join(rejected) + ")" if rejected else ""
            LOG.emit(f"{tag} tamamlandi | kaynak={src} | uygulanan {len(applied)}{applied_txt} | "
                     f"uygulanmayan {len(rejected)}{rejected_txt}", "OPT")

    @staticmethod
    def overlay_axes_operator_owns(shared: dict[str, Any],
                                   factory: dict[str, Any]) -> set[str]:
        """Axes the operator changed away from the shipped search grid.

        The swing overlay must not overwrite those: a panel ``sl_atr_mult`` of
        [1.5, 2, 3, 4] is the measurement that flipped SpotBrent/JPN225, and
        stamping ``SWING_GRID_OVERLAY`` back on top re-introduced 1.0 on every
        M15/M30 symbol. Axes still equal to the factory list keep the overlay
        (the FRA40 0.5-on-M30 leak).
        """
        owned: set[str] = set()
        for key in SWING_GRID_OVERLAY:
            if key not in shared:
                continue
            if not _grid_axis_equal(shared[key], factory.get(key)):
                owned.add(key)
        return owned

    @staticmethod
    def _exit_grid_for(merged: dict[str, Any], own: dict[str, Any],
                       family: str, timeframe: str,
                       shared: dict[str, Any] | None = None,
                       factory: dict[str, Any] | None = None) -> dict[str, Any]:
        """Search grid for one family/timeframe pairing.

        Precedence is shared -> swing overlay -> the family's own statement,
        except an operator-touched shared axis beats the overlay.

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
            # Widen factory-default shared axes. Skip any axis the family named
            # and any axis the operator moved off the shipped list.
            owned = (
                Optimizer.overlay_axes_operator_owns(shared or {}, factory)
                if factory is not None else set()
            )
            grid.update({
                k: v for k, v in SWING_GRID_OVERLAY.items()
                if k not in own and k not in owned
            })
        return searchable_axes(family, grid)

    def _spread_scale(self, symbol: str) -> float:
        """Measured live-tick / bar spread median for this symbol, or 1.0.

        Read from the store rather than from the engine: the engine already
        persists the histogram there, so the search does not need a handle on
        a running engine (and the pooled workers could not have one anyway).

        Returns 1.0 - the old behaviour, exactly - until the symbol has
        cleared the sample threshold. Half a session of ticks from one hour is
        the reading that already misled us once; nothing moves the search
        until the distribution is real.

        A missing or thin histogram is 1.0 on purpose and stays quiet. An
        exception (import, store) is also 1.0 so the search still runs, but
        that 1.0 is a frozen read being treated as "no measurement" - the
        search then costs ~10% cheap. WARN once; clear the latch on the next
        success so a second outage is not silent.
        """
        try:
            from .engine import SPREAD_RATIO_BUCKETS, SPREAD_RATIO_MIN_SAMPLES, _ratio_percentile
            blob = self.store.get_setting("spread_ratio", {}) or {}
            counts = blob.get(symbol)
            scale = 1.0
            if isinstance(counts, (list, tuple)):
                counts = [int(v) for v in counts
                          if isinstance(v, (int, float)) and not isinstance(v, bool)]
                if (len(counts) == SPREAD_RATIO_BUCKETS
                        and sum(counts) >= SPREAD_RATIO_MIN_SAMPLES):
                    median = _ratio_percentile(counts, 0.50)
                    if median and median > 0:
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
                        scale = float(min(5.0, max(1.0, median)))
        except Exception as exc:
            if not getattr(self, "_spread_scale_warned", False):
                LOG.emit(
                    f"{symbol}: spread_ratio okunamadi ({type(exc).__name__}) - "
                    "arama 1.0 ile ucuzluyor, sqlite donmus olabilir",
                    "WARN",
                    symbol,
                )
                self._spread_scale_warned = True
            return 1.0
        self._spread_scale_warned = False
        return scale

    def _plan_symbol(self, cfg, lookback_days: int, bar_cap: int,
                     variants: list[dict[str, Any]],
                     min_trades: int, segments: int, max_combos: int, min_positive: float,
                     plateau: float, timeframes: list[str],
                     refine_rounds: int,
                     tf_allow: dict[str, list[str]] | None = None,
                     alloc: dict[str, int] | None = None) -> dict[str, Any]:
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
        # Read once here, in the parent. A zero means symbol info could not be
        # read, and the sweep will fall back to ten points for every combo -
        # worth saying once, and only sayable here: backtest.stop_floor_const
        # runs in the worker processes, where logbus cannot serialise.
        if not min_stop:
            LOG.emit(f"{cfg.symbol}: broker stop tabani okunamadi (min_stop=0) - "
                     f"arama 10 point varsayacak.", "WARN", cfg.symbol)
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
        # Off means the sweep fills at the printed price and charges nothing,
        # matching an account whose live cost gate and spread ceilings are
        # switched off. See SystemConfig.charge_costs for why the default is
        # the other way.
        charge_costs = bool(getattr(sys_cfg, "charge_costs", True))
        opt_blob = {}
        if hasattr(self.store, "opt_params"):
            try:
                opt_blob = self.store.opt_params() or {}
            except Exception:
                opt_blob = {}
        metric = str(opt_blob.get("selection_metric") or "score")
        try:
            combo_seed = int(opt_blob.get("combo_seed", 7))
        except (TypeError, ValueError):
            combo_seed = 7
        risk_dollar = max(float(getattr(cfg, "risk_percent", 0) or 0), 0.01)

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
            # 0 = no day limit, the same convention every other optional
            # ceiling here uses (symbol_daily_loss_pct, day_end_flatten_min,
            # htf_factor, max_spread_atr). It used to mean "ask for zero bars",
            # which files every timeframe as "veri yetersiz (0 bar)" and searches
            # nothing - so switching the day window off looked like switching the
            # optimiser off. Parking it at 4000 worked around that and put an
            # eleven-year window on the panel, which reads as a setting rather
            # than as "unused".
            per_tf = int(lookback_days * 86400 / timeframe_seconds(tf))
            want = min(bar_cap, per_tf) if lookback_days > 0 else bar_cap
            got = self.client.bars(cfg.symbol, tf, want)
            # A terminal that does not hold this much history for this
            # timeframe answers with nothing at all rather than with fewer
            # bars, and the caller below then files the timeframe as "veri
            # yetersiz (0 bar)" and drops it. M5 was never once searched in
            # this book's 104 recorded runs for exactly that reason: the same
            # 365-day window asks for 45000 M5 bars, the terminal serves none,
            # and a whole timeframe disappeared without anyone choosing to
            # exclude it. At 8000 bars the same request returns data and the
            # sweep runs normally.
            #
            # Halving keeps the window as long as the terminal can actually
            # serve. The floor is the 600-bar minimum the caller already
            # enforces, so this never manufactures a sample too thin to judge.
            asked = want
            while (got is None or len(got) < 600) and want > 1200:
                want //= 2
                got = self.client.bars(cfg.symbol, tf, want)
            # Say so when it happened. The halving is the right behaviour but it
            # was silent, and a silently shortened window is the same hazard as
            # every other silent substitution in this codebase: two symbols get
            # compared on different amounts of history and the run record reads
            # as though they were equal. The count that was actually served is
            # already stored on the run (walk_forward reports `bars`); this is
            # so it is visible while it is happening.
            if want < asked:
                LOG.emit(f"{cfg.symbol} {tf}: {asked} bar istendi, terminal "
                         f"vermedi - {len(got) if got is not None else 0} bar ile "
                         f"arandi (pencere kisaldi).", "WARN", cfg.symbol)
            cached_bars[tf] = got
            self._bar_snap[(cfg.symbol, tf)] = got

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
                factory = None
                if self.store is not None:
                    raw = (self.store.defaults.get("optimizer") or {}).get("grid")
                    if isinstance(raw, dict) and raw:
                        factory = raw
                grid = self._exit_grid_for(
                    variant["grid"], variant["own"], family, tf,
                    shared=variant.get("shared"), factory=factory)
                bars_dir = self._ensure_sweep_bars_dir()
                safe = "".join(
                    ch if ch.isalnum() else "_" for ch in f"{cfg.symbol}_{tf}")
                bars_path = write_sweep_bars(bars_dir / safe, bars)
                plan["jobs"].append({
                    "symbol": cfg.symbol, "timeframe": tf, "strategy": family,
                    "order": len(plan["jobs"]) + len(plan["attempts"]),
                    "cfg": {**cfg.to_dict(), "timeframe": tf, "strategy": family},
                    "bars_path": str(bars_path),
                    "point": float(info["point"]), "tf_seconds": timeframe_seconds(tf),
                    "spread_scale": spread_scale,
                    "charge_costs": charge_costs,
                    "grid": grid, "min_trades": min_trades, "segments": segments,
                    "max_combos": family_max_combos(
                        opt_blob, family, (alloc or {}).get(family, max_combos)),
                    "min_positive": min_positive,
                    # Scheduling only (longest_first). A sweep costs roughly
                    # "combos evaluated x bars walked", and both vary by orders
                    # of magnitude across families and timeframes. Never read
                    # by the worker or by scoring.
                    "cost_hint": int(family_max_combos(
                        opt_blob, family,
                        (alloc or {}).get(family, max_combos)) * len(bars)),
                    "plateau": plateau, "commission": commission, "min_stop": min_stop,
                    "refine_rounds": refine_rounds, "all_hours": all_hours,
                    "day_end_flatten_min": day_end_flatten_min,
                    # The live entry gate's own ceiling, handed to the search so
                    # it stops proposing configs the engine will refuse. Read
                    # from the same setting the engine reads, and only when that
                    # gate is actually switched on - otherwise 0 leaves the
                    # search unfiltered, exactly as before.
                    "max_cost_share": max_cost_share,
                    "selection_metric": metric,
                    "risk_dollar": risk_dollar,
                    "combo_seed": combo_seed,
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
        wall clock: the pool is spawned once instead of once per symbol, and
        sweep durations differ by two orders of magnitude (an M5 pullback
        search against an H1 one), so draining one symbol at a time left every
        worker idling on that symbol's slowest sweep while the next symbol's
        short ones waited. Bar fetching stays in this thread behind the MT5
        lock — all of it, before any sweep — so the live cycle is not sharing
        copy_rates for the whole first-symbol duration.
        """
        self._bar_snap = {}
        self._ensure_sweep_bars_dir()
        plans: dict[str, dict[str, Any]] = {}
        allow = tf_allow if isinstance(tf_allow, dict) else STRATEGY_TIMEFRAMES
        opt_blob: dict[str, Any] = {}
        if hasattr(self.store, "opt_params"):
            try:
                opt_blob = self.store.opt_params() or {}
            except Exception:
                opt_blob = {}
        families = [v["strategy"] for v in variants]
        # Sized off the *base* family grid rather than the per-timeframe exit
        # grid, because progress accounting and the sweeps themselves have to
        # agree on one number and only the base is known to both.
        grid_totals: dict[str, int] = {}
        for v in variants:
            total = 1
            for values in (v.get("grid") or {}).values():
                total *= max(1, len(values))
            grid_totals[v["strategy"]] = total
        alloc = coverage_budget(grid_totals, max_combos)
        combo_total, sweep_cost = run_combo_budget(
            opt_blob, families, timeframes, max_combos, refine_rounds,
            len(targets), allow, alloc)
        self._set(combo_total=combo_total)
        combo_done = 0
        finished = 0

        def close_out(plan: dict[str, Any]) -> None:
            nonlocal finished
            apply = apply_best and not self._cancel.is_set()
            report = self._finish_symbol(plan, apply)
            finished += 1
            with self._lock:
                self.job["results"].append(report)
                self.job["done"] = finished

        def note(job: dict[str, Any], outcome: dict[str, Any]) -> None:
            """Record one finished sweep, closing the symbol out when it is the last."""
            nonlocal combo_done
            plan = plans[job["symbol"]]
            plan["attempts"].append(outcome)
            plan["outstanding"] -= 1
            fam = str(job.get("strategy") or "")
            combo_done += sweep_cost.get(
                fam, backtest.sweep_budget(max_combos, refine_rounds))
            best = max((a["best"]["score"] for p in plans.values()
                        for a in p["attempts"] if a.get("ok")), default=None)
            active = sorted(s for s, p in plans.items() if p["outstanding"] > 0)
            self._set(combo_done=combo_done, combo_total=combo_total,
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
                                     timeframes, refine_rounds, allow, alloc)
            plans[symbol] = plan
            plan["outstanding"] = len(plan["jobs"])
            if not plan["jobs"]:
                close_out(plan)          # nothing to wait for
            return plan["jobs"]

        _limit_blas_threads()
        workers = _worker_count(self.store.system.opt_max_workers)
        try:
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
            queued: list[dict[str, Any]] = []
            for symbol in targets:
                if self._cancel.is_set():
                    return
                plan = plans.get(symbol)
                if plan is None:
                    self._set(current=f"veri: {symbol}")
                    queued.extend(plan_next(symbol))
                elif plan["outstanding"] > 0:
                    self._set(current=symbol)
                    measured = {(a.get("timeframe"), a.get("strategy"))
                                for a in plan["attempts"]}
                    queued.extend(
                        j for j in plan["jobs"]
                        if (j["timeframe"], j["strategy"]) not in measured)
            if queued:
                LOG.emit(
                    f"Barlar indirildi, tarama basliyor: {len(queued)} tarama",
                    "OPT")
            for job in queued:
                if self._cancel.is_set():
                    return
                note(job, _sweep_worker(job))
        finally:
            self._clear_sweep_bars()

    def _abandon_search_pool(self, pool: Any, inflight: dict[Any, Any]) -> None:
        """Drop in-flight sweeps. Child processes cannot see ``_cancel``.

        ``future.cancel()`` only skips work that has not started.
        ``ProcessPoolExecutor.__exit__`` waits for the rest, which is why
        Iptal looked dead: the event was set and apply() of later symbols
        was skipped, but ``job.state`` stayed running until every worker
        finished its current walk-forward.
        """
        for future in list(inflight):
            try:
                future.cancel()
            except Exception:
                pass
        inflight.clear()
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            pool.shutdown(wait=False)
        except Exception:
            pass
        procs = getattr(pool, "_processes", None) or {}
        if isinstance(procs, dict):
            procs = procs.values()
        for proc in list(procs):
            try:
                proc.terminate()
            except Exception:
                pass

    def _search_parallel(self, targets: list[str], plan_next, note, workers: int) -> None:
        """Fetch every symbol's bars, then run the sweeps CPU-only."""
        queued: list[dict[str, Any]] = []
        for symbol in targets:
            if self._cancel.is_set():
                return
            # Bars stay in this thread so MT5 stays behind its single lock.
            # The pool does not start until every window is on disk.
            self._set(current=f"veri: {symbol}")
            queued.extend(plan_next(symbol))
        if self._cancel.is_set():
            return
        LOG.emit(
            f"Barlar indirildi, tarama basliyor: {len(queued)} tarama, "
            f"{len(targets)} sembol",
            "OPT")
        pool = ProcessPoolExecutor(max_workers=workers)
        inflight: dict[Any, dict[str, Any]] = {}
        abandoned = False
        try:
            def harvest() -> bool:
                """Collect finished sweeps; False once a cancel has been seen."""
                if self._cancel.is_set():
                    return False
                if not inflight:
                    return True
                done, _ = futures_wait(
                    list(inflight), timeout=0.5, return_when=FIRST_COMPLETED)
                if not done:
                    return not self._cancel.is_set()
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
                return not self._cancel.is_set()

            # Longest sweep first so the tail is short ones, not the reverse.
            for job in longest_first(queued):
                if self._cancel.is_set():
                    self._abandon_search_pool(pool, inflight)
                    abandoned = True
                    return
                inflight[pool.submit(_sweep_worker, job)] = job
            while inflight:
                if not harvest():
                    self._abandon_search_pool(pool, inflight)
                    abandoned = True
                    return
        finally:
            if not abandoned:
                pool.shutdown(wait=True)

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

        tried = [
            {"timeframe": a["timeframe"], "strategy": a.get("strategy", "?"),
             "ok": bool(a.get("ok")), "validated": bool(a.get("validated")),
             "score": a["best"]["score"] if a.get("ok") else None,
             "val_net_r": ((a.get("best") or {}).get("validation") or {}).get("net_r")
             if a.get("ok") else None,
             "hold_net_r": ((a.get("best") or {}).get("holdout") or {}).get("net_r")
             if a.get("ok") else None,
             "hold_pf": ((a.get("best") or {}).get("holdout") or {}).get("profit_factor")
             if a.get("ok") else None,
             "hold_n": ((a.get("best") or {}).get("holdout") or {}).get("trades")
             if a.get("ok") else None,
             "error": a.get("error", "")}
            for a in attempts
        ]
        elapsed = round(time.time() - started, 1)
        usable = [a for a in attempts if a.get("ok") and a.get("validated")]
        if not usable:
            if not any(a.get("ok") for a in attempts):
                reasons = "; ".join(
                    f"{a['timeframe']}/{a['strategy']}: {a.get('error', '?')}"
                    for a in attempts[:4]) or "sonuc yok"
                report = {"symbol": cfg.symbol, "ok": False, "error": reasons,
                          "tried": tried, "elapsed_sec": elapsed}
                LOG.emit(f"{cfg.symbol}: {reasons}", "OPT", cfg.symbol)
                return report
            # Sweeps ran; the OOS gate refused every one. Naming a winner
            # here used to pick the best unvalidated validation score — a
            # label that read as the search's proposal. Apply never took it
            # (it already requires validated), but the report did, and that
            # report is what got written down. No candidate, no name.
            reason = "hicbir aday kapidan gecmedi"
            incumbent = ((getattr(cfg, "opt_summary", None) or {}).get("holdout") or {})
            report = {
                "symbol": cfg.symbol,
                "ok": True,
                "validated": False,
                "best": None,
                "tried": tried,
                "elapsed_sec": elapsed,
                "keep_reason": reason,
                "applied": False,
                "holdout_retention": None,
                "incumbent": {
                    "net_r": incumbent.get("net_r"), "score": incumbent.get("score"),
                    "profit_factor": incumbent.get("profit_factor"),
                    "trades": incumbent.get("trades"),
                    "strategy": cfg.strategy, "timeframe": cfg.timeframe,
                    "updated_at": float(getattr(cfg, "opt_updated_at", 0.0) or 0.0),
                } if incumbent else None,
            }
            self.store.record_opt_run(cfg.symbol, 0.0, {
                "timeframe": None, "strategy": None,
                "params": {},
                "selection": {}, "validation": {}, "holdout": {},
                "validated": False,
                "keep_reason": reason,
                "tried": tried,
                "elapsed_sec": elapsed,
                "force": bool(getattr(self, "_force_apply", False)),
                "applied_at": None,
                "previous": None,
            }, False)
            tail = f" -> uygulanmadi ({reason})"
            tail += self._incumbent_kept_tail(cfg)
            LOG.emit(f"{cfg.symbol}: {reason}{tail}", "OPT", cfg.symbol)
            return report

        # Search scores are not comparable between families or timeframes - each
        # sweep explores a different space. The validation slice is the common
        # yardstick, and it is not the slice the final numbers are read from.
        report = self._pick_by_validation(usable)
        report["symbol"] = cfg.symbol
        report["tried"] = tried
        report["elapsed_sec"] = elapsed

        best = report["best"]
        score = float(best["score"])
        # Named up front so the UI can explain a red number instead of leaving
        # it looking like the symbol's live setup is the thing losing money.
        reason = self.reject_reason(cfg, best)
        if self._cancel.is_set():
            # Harvest still close_out()s symbols whose last sweep already
            # returned. Cancel means stop writing the live book, not "finish
            # applying whoever happened to drain first".
            apply_best = False
            if not reason:
                reason = "iptal - uygulanmadi"
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
        # Snapshot before apply() mutates cfg. Old rows omit these keys;
        # new rows always write them so ``None`` is distinguishable from
        # ``False`` and from a missing historical field.
        previous = {"strategy": cfg.strategy, "timeframe": cfg.timeframe}
        applied = False
        closed = not bool(getattr(cfg, "enabled", True))
        if closed and apply_best and report.get("validated") and not reason:
            # Report-only: the candidate is real, the live book is not theirs
            # to rewrite, and enabled stays False. Opening is the operator's.
            reason = "kapali sembol icin aday bulundu"
            report["keep_reason"] = reason
            report["closed_candidate"] = True
        elif apply_best and report.get("validated") and not reason:
            apply_result = self.apply(cfg.symbol, best["params"], score,
                       {**best, "holdout_days": report.get("holdout_days", 0.0),
                        "validated": bool(report.get("validated")),
                        "charge_costs": report.get("charge_costs"),
                        "spread_scale": report.get("spread_scale"),
                        "min_positive_ratio": report.get("min_positive_ratio"),
                        "grid_total": report.get("grid_total"),
                        "max_combos": report.get("max_combos"),
                        "coverage": report.get("coverage"),
                        "combo_seed": report.get("combo_seed"),
                        "combos": report.get("combos")},
                       timeframe=report["timeframe"], strategy=report["strategy"])
            applied = bool(apply_result.get("ok")) and not apply_result.get("deferred")
            if apply_result.get("deferred"):
                # Winner is stored on the symbol as pending_primary_patch;
                # live family/TF stay until this magic is next seen flat.
                report["keep_reason"] = (
                    "strateji/TF pozisyon kapaninca uygulanacak")
                report["queued"] = True
                LOG.emit(
                    f"{cfg.symbol}: {report['strategy']}/{report['timeframe']} "
                    f"dogrulandi, acik pozisyon var - kuyruga alindi "
                    f"(kapaninca uygulanacak).",
                    "OPT", cfg.symbol)
            elif not applied:
                # apply() itself refused (e.g. the TF-lock check) - the run
                # otherwise looked like a normal validated win, so make sure
                # that doesn't get reported as "uygulandi" with the live
                # config silently left on whatever it was before.
                report["keep_reason"] = apply_result.get("error", "uygulanamadi")
                LOG.emit(f"{cfg.symbol}: uygulama reddedildi - "
                         f"{apply_result.get('error', '?')}", "OPT", cfg.symbol)
            else:
                # The spread ceiling is a ratio against ATR, so it means a
                # different thing on every timeframe - a bigger ATR divides the
                # same spread down. An apply that moves the timeframe therefore
                # invalidates the cap it leaves behind, silently: the 14.08
                # 21:17 run moved FRA40 from M30 to M5 and its cap went from
                # cutting 1.5% of bars to cutting 57.9% without anything being
                # written. Re-read here, off the timeframe that is now live.
                # Deferred family/TF must not do this yet - the live bar is
                # still the old one; Engine lands the cap with the patch.
                self._recalibrate_spread_cap(cfg.symbol, report["timeframe"])
            # Secondary pick/store was removed 14.08 (operator): a runner-up
            # is no longer written. Existing secondary_* rows stay inert until
            # a later stage clears the fields; this path must not mint new ones.

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
            "keep_reason": report.get("keep_reason") or reason,
            "charge_costs": report.get("charge_costs"),
            "grid_total": report.get("grid_total"),
            "max_combos": report.get("max_combos"),
            "coverage": report.get("coverage"),
            "combo_seed": report.get("combo_seed"),
            "top": _ranked_finalists(report),
            "force": bool(getattr(self, "_force_apply", False)),
            "applied_at": time.time() if applied else None,
            "previous": previous if applied else None,
        }, applied)

        report["applied"] = applied
        hold = best["holdout"]
        val = best["validation"]
        sel = best["selection"]
        if applied:
            tail = " -> uygulandi"
        elif report.get("queued"):
            tail = (f" -> kuyrukta "
                    f"({report.get('keep_reason') or 'pozisyon kapaninca'})")
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
            tail += self._incumbent_kept_tail(cfg)
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
        cleared every out-of-sample gate. The caller must not hand it an
        unvalidated consolation set — naming a winner there is how a report
        once claimed the search had picked a family the apply path would
        have refused. The product's stated priority is scalping, swing is
        the fallback when scalping genuinely does not validate for a
        symbol - so a scalp family (burst) among the near-tied peers
        wins over an equally-valid swing one; it never wins over a swing
        candidate that is not actually tied on validation.
        """
        usable = [a for a in usable if a.get("validated")]
        if not usable:
            raise ValueError("validated kume bos")
        top = max(usable, key=lambda a: a["best"]["validation"]["score"])
        if len(usable) < 2:
            return top
        ceiling = float(top["best"]["validation"]["score"])
        if ceiling <= 0.0:
            return top
        peers = [a for a in usable
                 if float(a["best"]["validation"]["score"]) >= ceiling * (1.0 - self.TIE_BAND)]
        if len(peers) < 2:
            return top
        # Both OOS slices already gated the candidate; trade-count tiebreak
        # is validation only. Holdout n here leaked the untouched slice into
        # family/TF choice (BS-2d). Name last so equal validation n is stable
        # across list order (strategy, then timeframe).
        return max(peers, key=lambda a: (
            1 if is_scalp_strategy(a["strategy"]) else 0,
            int(a["best"]["validation"].get("trades", 0) or 0),
            float(a["best"]["validation"]["score"]),
            str(a.get("strategy") or ""),
            str(a.get("timeframe") or ""),
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
        if best.get("min_positive_ratio") is not None:
            min_positive = float(best["min_positive_ratio"])
        elif self.store is not None:
            min_positive = float(self.store.opt_params().get("min_positive_ratio", 0.6))
        else:
            min_positive = 0.6
        if best.get("positive_ratio", 0) < min_positive:
            return "secim segmentleri arasinda tutarsiz"
        # A configuration gets the settling time the system already says it
        # should get. ``reopt_min_age_hours`` states the policy and
        # ``reject_reason`` enforces it on apply. Calendar auto-queue is gone
        # (quarantine search only). This route never checked age, so a
        # full scan replaced configurations the auto route would have left
        # alone, and that is where the churn came from: across 495 applies, the
        # symbols that made money had settled on one config (SpotBrent's last
        # three applies all mtf_pullback/H1, US30's all dual_t3/M15) while the
        # ones losing money never stopped moving - USDCHF through 12 distinct
        # configs in 23 applies, USDJPY 10 in 15. Every family swap discards
        # that symbol's live record, so it never reaches watch_min_trades and
        # the supervisor never gets to throttle a config that is losing: it is
        # replaced before it can be judged.
        #
        # The search still runs and still reports - the report costs nothing
        # and is information. Only the apply is held back, because the apply is
        # what discards the evidence. ``force`` is the way past it, and it was
        # needed today: two full runs twenty-five minutes apart, because the
        # first searched a grid that turned out to be broken.
        if cfg is not None and not getattr(self, "_force_apply", False):
            applied_at = float(getattr(cfg, "opt_updated_at", 0.0) or 0.0)
            if applied_at > 0:
                # Read from the store rather than hardcoded: the operator's own
                # number, same as min_positive_ratio below. 48.0 is the shipped
                # default and only stands in when the row is absent entirely.
                sup: dict[str, Any] = {}
                if self.store is not None:
                    sup = self.store.get_setting("supervisor", {}) or {}
                try:
                    min_age_h = float(sup.get("reopt_min_age_hours", 48.0))
                except (TypeError, ValueError):
                    min_age_h = 48.0
                age_h = (time.time() - applied_at) / 3600.0
                if min_age_h > 0 and age_h < min_age_h:
                    return (f"mevcut ayar {age_h:.0f} saatlik, en az "
                            f"{min_age_h:.0f} saat calismali "
                            f"(churn freni - gecmek icin 'zorla uygula', "
                            f"veya Sistem > reopt_min_age_hours)")
        # Same shape as min_positive_ratio above, for the same reason. The
        # engine refuses an entry when its live cost exceeds
        # system.max_cost_pct_of_risk, and that setting ships at 25.0 to agree
        # with the constant here - so the two only diverge once an operator
        # tightens the live one, and nothing noticed when they did. It sits at
        # 18.0 live, and USDJPY carries a config whose own holdout cost is
        # 0.1867: inside this gate, past the engine's, and four of its six
        # signals refused with "maliyet". The search validated, applied and
        # stamped a configuration that cannot trade at its own average cost.
        #
        # Tighter only. A live gate above 0.25 does not raise this ceiling -
        # the constant carries its own reasoning - and a disabled or zeroed
        # live gate refuses nothing, so there is nothing to align with.
        cost_ceiling = self.MAX_COST_PER_TRADE_R
        system = getattr(self.store, "system", None) if self.store is not None else None
        if system is not None and getattr(system, "block_high_cost", False):
            live_pct = float(getattr(system, "max_cost_pct_of_risk", 0.0) or 0.0)
            if live_pct > 0:
                cost_ceiling = min(cost_ceiling, live_pct / 100.0)
        if hold.get("cost_per_trade_r", 0) > cost_ceiling:
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
        # nothing about whether the edge itself is real.
        if not self._generalises(best, getattr(cfg, "symbol", "")):
            return "holdout kenari zayifladi (retention)"
        return ""

    def _incumbent_kept_tail(self, cfg) -> str:
        """Log suffix when the live config is kept. Quote a fresh replay.

        The apply stamp in opt_summary.holdout is the number from the day
        the config was written. 26.08 US30 logged +224.2 R from 24.08 20:52
        while the same setup on tonight's pins is -89.1 R. The gate already
        replays; this line is what operators and the other agent actually
        read, so it has to say taze vs damga.
        """
        stamp = ((getattr(cfg, "opt_summary", None) or {}).get("holdout") or {})
        fresh = self._fresh_incumbent_holdout(cfg) or {}
        if fresh.get("net_r") is not None:
            return (
                f", mevcut ayar korundu "
                f"(taze test {float(fresh['net_r']):+.1f}R)")
        if stamp.get("net_r") is not None:
            when = ""
            ts = float(getattr(cfg, "opt_updated_at", 0.0) or 0.0)
            if ts > 0:
                when = time.strftime(", %d.%m", time.gmtime(ts))
            return (
                f", mevcut ayar korundu "
                f"(damga {float(stamp['net_r']):+.1f}R{when})")
        return ""

    def _fresh_incumbent_holdout(self, cfg) -> dict[str, Any] | None:
        """Same-window holdout of the *live* config. None = use the stamp.

        Tests construct Optimizer with object.__new__ and no client; a
        raised replay must fall back, not invent a comparison.

        When the live book searches cost-free, a charged replay here would
        depress the incumbent and wave every paper candidate through (A1
        churn). Same-regime only: charged fresh iff ``charge_costs`` is on.
        """
        try:
            system = getattr(getattr(self, "store", None), "system", None)
            charging = bool(getattr(system, "charge_costs", True)) if system is not None else True
            if not charging:
                return None
            params = {k: getattr(cfg, k) for k in OPT_FIELDS if hasattr(cfg, k)}
            key = (str(cfg.symbol), str(cfg.timeframe), str(cfg.strategy),
                   tuple(sorted(params.items())))
            cache = getattr(self, "_incumbent_holdout_cache", None)
            if cache is None:
                self._incumbent_holdout_cache = {}
                cache = self._incumbent_holdout_cache
            if key in cache:
                return cache[key]
            out = self._holdout_costed(
                cfg.symbol, cfg.timeframe, cfg.strategy, params,
                allow_fetch=False)
            result = out if isinstance(out, dict) else None
            cache[key] = result
            return result
        except Exception:
            return None

    def _beats_incumbent(self, cfg, hold: dict[str, Any]) -> bool:
        """Is this holdout at least as good as the live config's own holdout?

        Compared on ``Result.score`` - the same thin-sample and drawdown
        discounted number the rest of the optimizer ranks on - so a candidate
        cannot win on raw R while trading a handful of times.
        """
        if cfg is None:
            return True
        summary = getattr(cfg, "opt_summary", None) or {}
        flag = getattr(cfg, "validated", None)
        if flag is None:
            raw = summary.get("validated")
            flag = None if raw is None else bool(raw)
        if flag is False:
            # Unvalidated stamp is not a bar (NAS100 GAP-5 +38 vs live PF
            # 0.50). Fresh same-window replay still counts if it pays
            # (GER40, same campaign, actually profitable).
            fresh = self._fresh_incumbent_holdout(cfg)
            if fresh is None:
                return True
            old_score = float(fresh.get("score", 0.0) or 0.0)
            if old_score <= 0.0:
                return True
            new_score = float(hold.get("score", 0.0) or 0.0)
            if new_score >= old_score:
                return True
            LOG.emit(f"{cfg.symbol}: yeni aday mevcut ayardan zayif "
                     f"(test skoru {new_score:.2f} < {old_score:.2f}), uygulanmadi.",
                     "OPT", cfg.symbol)
            return False
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
        # ...and only while costs are actually charged. charge_costs=False
        # zeroes the spread series before anything is scored, so the scale
        # multiplies nothing and both numbers were measured on identical
        # terms. The premise above is then simply false, and waiving on it
        # drops the one guard standing between a weaker candidate and a live
        # symbol. XAUUSD reached exactly that state - stamp 1.25, measured
        # 1.15 - and the escape fired at 13:20 with costs already off.
        system = getattr(self.store, "system", None) if self.store is not None else None
        charging = bool(getattr(system, "charge_costs", True)) if system is not None else True
        # The cost assumption itself moving is the same class of break, and a
        # sharper one: a cost-free score is strictly the larger number, so an
        # incumbent stamped under one can never be beaten by a candidate priced
        # honestly. Unstamped means it predates the switch, which means costs
        # were charged - the switch shipped defaulting to True.
        # One direction only, because the risk is not symmetric. A cost-free
        # score is the larger one, so:
        #   incumbent cost-free, now charging -> the INCUMBENT is inflated and
        #     nothing honest can pass it. Skip, or the symbol freezes.
        #   incumbent charged, now cost-free -> the CANDIDATE is inflated, and
        #     the incumbent's honest score is the stricter bar. Keep comparing;
        #     skipping here would wave the inflated one through.
        was_charging = bool(summary.get("charge_costs", True))
        if was_charging and not charging:
            pass
        elif was_charging != charging:
            LOG.emit(f"{cfg.symbol}: mevcut ayar farkli maliyet varsayimiyla olculmus "
                     f"({'maliyetli' if was_charging else 'maliyetsiz'} -> "
                     f"{'maliyetli' if charging else 'maliyetsiz'}), skor kiyasi "
                     f"atlandi - aday kendi kapilariyla degerlendirildi.",
                     "OPT", cfg.symbol)
            return True
        if charging and round(abs(new_scale - old_scale), 2) > 0.05:
            LOG.emit(f"{cfg.symbol}: mevcut ayar farkli spread olcegiyle olculmus "
                     f"({old_scale or 'kayitsiz'} -> {new_scale:.2f}), skor kiyasi "
                     f"atlandi - aday kendi kapilariyla degerlendirildi.",
                     "OPT", cfg.symbol)
            return True
        # Stamp and candidate are not the same window (JPN225 160.64 vs a
        # same-slice live replay). Replay the live config here; keep the
        # stamp only when that replay is missing (no client, thin bars).
        fresh = self._fresh_incumbent_holdout(cfg)
        if fresh is not None:
            old_score = float(fresh.get("score", 0.0) or 0.0)
            if old_score <= 0.0:
                return True
        new_score = float(hold.get("score", 0.0) or 0.0)
        if new_score >= old_score:
            return True
        LOG.emit(f"{cfg.symbol}: yeni aday mevcut ayardan zayif "
                 f"(test skoru {new_score:.2f} < {old_score:.2f}), uygulanmadi.",
                 "OPT", cfg.symbol)
        return False

    # Bars enough to rank the symbol's own spread distribution three ways; the
    # calibration refuses to read anything shorter rather than set a live gate
    # off a thin sample.
    CALIBRATION_BARS = 20000

    def _recalibrate_spread_cap(self, symbol: str, timeframe: str) -> None:
        """Re-read ``max_spread_atr`` off the timeframe that is now live.

        Never raises into the run: a failed reading leaves the cap where it is,
        which is the same thing the calibration does when the bars are too thin
        to read. Losing a calibration is not a reason to lose an apply.
        """
        try:
            cfg = self.store.symbols.get(symbol)
            if cfg is None:
                return
            bars = self.client.bars(symbol, timeframe, self.CALIBRATION_BARS)
            info = self.client.info(symbol)
            if bars is None or not info:
                return
            result = calibrate(symbol, timeframe, bars, float(info["point"]),
                               float(getattr(cfg, "max_spread_atr", 0.0) or 0.0))
            if abs(result.cap - float(getattr(cfg, "max_spread_atr", 0.0) or 0.0)) < 1e-9:
                return
            old_cap = float(getattr(cfg, "max_spread_atr", 0.0) or 0.0)
            summary = dict(getattr(cfg, "opt_summary", None) or {})
            summary["spread_recalibrated_from"] = old_cap
            summary["spread_recalibrated_to"] = float(result.cap)
            self.store.update_symbol(
                symbol,
                {"max_spread_atr": result.cap, "opt_summary": summary},
                source="spread kalibrasyonu")
            LOG.emit(f"{symbol}: makas tavani {timeframe} icin yeniden okundu "
                     f"-> {result.cap:g} ({result.reason})", "OPT", symbol)
        except Exception as exc:                      # noqa: BLE001 - see docstring
            LOG.emit(f"{symbol}: makas kalibrasyonu okunamadi ({exc}) - "
                     f"mevcut tavan korundu.", "OPT", symbol)

    def _bars_for_holdout(self, symbol: str, timeframe: str,
                          allow_fetch: bool = True):
        """Holdout bars from the run snapshot, else a live fetch.

        A second client.bars() mid-run can close a new bar and shift the
        window the candidate was scored on (AS3). Incumbent keep/gate
        replay must pass allow_fetch=False and fall back to the stamp.
        """
        snap = getattr(self, "_bar_snap", None) or {}
        got = snap.get((symbol, timeframe))
        if got is not None:
            return got
        if not allow_fetch:
            return None
        opt: dict[str, Any] = {}
        store = getattr(self, "store", None)
        if store is not None:
            try:
                opt = store.opt_params() or {}
            except Exception:
                opt = {}
        want = int(opt.get("max_bars") or 0) or 20000
        return self.client.bars(symbol, timeframe, want)

    def _holdout_costed(self, symbol: str, timeframe: str, strategy: str,
                        params: dict[str, Any], *,
                        allow_fetch: bool = True) -> dict[str, Any] | None:
        """One charged replay of the winner on the holdout slice. Not a search.

        Search may still run with ``charge_costs=False`` (#50). Live still
        pays the spread, so the number that belongs next to a cost-free
        apply is this one - same bars, same params, costs on.
        """
        cfg = self.store.symbols.get(symbol)
        if cfg is None:
            return None
        info = self.client.info(symbol)
        if not info or not (float(info.get("point") or 0) > 0):
            return None
        # Same bar count and the same number of segments the sweep just used,
        # so ``edges[-2:]`` lands on the same slice. Fixed numbers here would
        # make the log line beside this a false comparison: it names a paper
        # expectancy and a charged one as "the same slice", and 8000 bars cut
        # five ways is not the last fifth of 99000.
        opt = self.store.opt_params() or {}
        segments = int(opt.get("segments") or 0) or 5
        bars = self._bars_for_holdout(symbol, timeframe, allow_fetch=allow_fetch)
        if bars is None or len(bars) < 800:
            return None
        n = len(bars)
        if n < segments * 150:
            return None
        overlay = dict(cfg.to_dict())
        overlay["timeframe"] = timeframe
        overlay["strategy"] = strategy
        overlay.update(params)
        tmp = SymbolConfig.from_dict(overlay)
        try:
            min_stop = self.client.min_stop_distance(symbol)
        except Exception:
            min_stop = None
        system = getattr(self.store, "system", None)
        res, _, _ = charged_holdout(
            bars=bars, cfg=tmp, point=float(info["point"]),
            tick_value=float(info.get("tick_value") or 0),
            tick_size=float(info.get("tick_size") or 0),
            spread_scale=self._spread_scale(symbol),
            min_stop=min_stop, segments=segments,
            trade_all_hours=bool(getattr(system, "trade_all_hours", False)),
            day_end_flatten_min=int(getattr(system, "day_end_flatten_min", 0) or 0),
            tf_seconds=timeframe_seconds(timeframe))
        return res.as_dict()

    def _charge_costs_stamp(self, detail: dict[str, Any] | None) -> bool:
        """What the holdout numbers were actually priced under.

        Explicit sweep flag wins. An omitted key used to fall back to the
        live store, which is how a cost-free holdout got stamped True
        (opt_history apply; AV1). If the holdout has trades and paid
        nothing, the numbers are cost-free regardless of the store.
        """
        hold = (detail or {}).get("holdout") or {}
        trades = int(hold.get("trades") or 0)
        cost = float(hold.get("cost_per_trade_r") or 0.0)
        if detail is not None and detail.get("charge_costs") is not None:
            claimed = bool(detail["charge_costs"])
        else:
            claimed = bool(getattr(getattr(self.store, "system", None),
                                   "charge_costs", True))
        if claimed and trades > 0 and cost <= 0:
            return False
        return claimed

    @staticmethod
    def _apply_stamp_missing(detail: dict[str, Any] | None) -> str:
        """Refuse an apply that would change the live row without its evidence.

        ``opt_summary.holdout`` is what ``risk._edge_metric`` sizes from, and
        what the gate panel reads as current. A family swap whose OPT_FIELDS
        overlap the previous row used to look like "same params" and keep the
        previous family's holdout — NAS100 traded mtf_pullback sized as
        t3_flip. No fallback: missing holdout, holdout_days or validated
        is a refusal, not an empty summary.
        """
        if not isinstance(detail, dict):
            return APPLY_STAMP_MISSING
        hold = detail.get("holdout")
        if not isinstance(hold, dict) or not hold:
            return "uygulama damgasi eksik: holdout"
        if detail.get("holdout_days") is None:
            return "uygulama damgasi eksik: holdout_days"
        if "validated" not in detail or detail.get("validated") is None:
            return "uygulama damgasi eksik: validated"
        return ""

    def apply(self, symbol: str, params: dict[str, Any], score: float,
              detail: dict[str, Any] | None = None,
              timeframe: str | None = None, strategy: str | None = None) -> dict[str, Any]:
        cfg = self.store.symbols.get(symbol)
        if cfg is None:
            return {"ok": False, "error": "sembol yok"}
        if detail is not None and detail.get("charge_costs") is True:
            hold = detail.get("holdout") or {}
            if (int(hold.get("trades") or 0) > 0
                    and float(hold.get("cost_per_trade_r") or 0.0) <= 0
                    and not getattr(self, "_force_apply", False)):
                return {"ok": False,
                        "error": "charge_costs damgasi maliyetle celisiyor "
                                 "(cost_per_trade_r=0)"}
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
        applied_params.update(unstamped_gates_to_zero(next_strat, applied_params))
        applied_params.update(absent_regime_gates_to_zero(next_strat, applied_params))
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
        missing = self._apply_stamp_missing(detail)
        if missing:
            return {"ok": False, "error": missing}
        if not isinstance(detail, dict):
            return {"ok": False, "error": APPLY_STAMP_MISSING}
        # Charged same-slice look stamps holdout_costed / costed_negative
        # beside every apply (#50). Refuse only while the live book actually
        # charges costs — cost-free mode still wants the visibility stamp.
        costed = None
        charging = bool(getattr(getattr(self, "store", None), "system", None)
                        and getattr(self.store.system, "charge_costs", True))
        if detail is not None:
            try:
                costed = self._holdout_costed(
                    symbol, next_tf, next_strat, applied_params)
            except Exception:
                costed = None
            charged = float((costed or {}).get("expectancy") or 0.0) if costed else 0.0
            if (charging and costed is not None and charged < 0
                    and not getattr(self, "_force_apply", False)):
                return {"ok": False,
                        "error": f"maliyetli holdout negatif ({charged:+.3f})"}
        patch = dict(applied_params)
        if timeframe in TIMEFRAMES:
            patch["timeframe"] = timeframe
        if strategy in STRATEGIES:
            patch["strategy"] = strategy
        patch["opt_score"] = float(score)
        patch["opt_updated_at"] = time.time()
        # Stamp is required above. Write holdout from this config's search
        # output — the same field risk._edge_metric reads. holdout_costed is
        # a separate charged replay, added below when that look exists.
        patch["opt_summary"] = {
            "holdout_retention": round(self.holdout_retention(detail), 3),
            "holdout": detail.get("holdout") or {},
            "validation": detail.get("validation", {}),
            "selection": detail.get("selection", {}),
            "holdout_days": float(detail["holdout_days"]),
            "positive_ratio": detail.get("positive_ratio", 0.0),
            "params": applied_params,
                # The spread scale this candidate was measured under. Every
                # number beside it - score, expectancy, cost_per_trade_r - is
                # only meaningful against that assumption, and _beats_incumbent
                # compares scores across runs. Without it, a config measured
                # while the search still charged the raw bar spread would be
                # compared, as though like for like, against one measured at
                # the tick spread the live gate actually enforces.
            "spread_scale": round(float(detail["spread_scale"]), 3)
            if detail.get("spread_scale") is not None
            else round(self._spread_scale(symbol), 3),
                # Same argument, one assumption over. charge_costs=False makes
                # the sweep fill at the printed price and charge nothing, so a
                # score earned that way is not comparable with one earned while
                # costs were charged - and it is the LARGER of the two, so
                # without this stamp a cost-free incumbent can never be beaten
                # and the symbol freezes on it. SpotBrent reached exactly that
                # state: applied 13.08 12:36 inside the cost-free window with
                # cost_per_trade_r 0.0, while the other nine carry 0.011-0.105.
                # Read off the sweep, not off the store. The setting can be
                # flipped while a run is in flight, and then the store answers
                # for the clock rather than for these numbers: the 14.08 20:10
                # run started cost-free, the flag went True at 20:13, and
                # SpotBrent's row landed at 20:17 stamped charge_costs True
                # beside cost_r 0.0 over 1532 trades. The stamp exists to keep
                # a cost-free score from being compared with a charged one, so
                # a stamp that can lie is worse than none.
                #
                # AV1: the store fallback is still a lie when detail omits the
                # key (opt_history apply) and holdout.cost_per_trade_r is 0.
            "charge_costs": self._charge_costs_stamp(detail),
            "min_positive_ratio": float(detail["min_positive_ratio"])
            if detail.get("min_positive_ratio") is not None
            else float((self.store.opt_params() if self.store is not None else {})
                       .get("min_positive_ratio", 0.6) or 0.6),
            # D1c: search-budget coverage. Old stamps omit these; apply still
            # succeeds and writes None. New writes fill them. coverage is
            # max_combos / grid_total capped at 1, not evaluated / grid.
            "grid_total": None if detail.get("grid_total") is None
            else int(detail["grid_total"]),
            "max_combos": None if detail.get("max_combos") is None
            else int(detail["max_combos"]),
            "coverage": (
                float(detail["coverage"])
                if detail.get("coverage") is not None
                else backtest.coverage_of(
                    int(detail["grid_total"]), int(detail["max_combos"]))
                if detail.get("grid_total") is not None
                and detail.get("max_combos") is not None
                else None
            ),
            "combo_seed": None if detail.get("combo_seed") is None
            else int(detail["combo_seed"]),
            # Evaluated count for the winning sweep — the one-run K in the
            # MinBTL table. grid_total is the family product; this is how
            # many configs actually ran. GAP-5 slim stamps dropped it and
            # the live book cannot answer "how hard did we search" without
            # walking opt_runs. Absence is None, not a refusal.
            "combos": None if detail.get("combos") is None
            else int(detail["combos"]),
        }
        flag = bool(detail.get("validated"))
        patch["validated"] = flag
        patch["opt_summary"]["validated"] = flag
        # Search regime is the stamp above. Same charged look that
        # already gated the apply; force still stamps the flag.
        if costed is not None:
            patch["opt_summary"]["holdout_costed"] = costed
            paper = float((detail.get("holdout") or {}).get("expectancy") or 0.0)
            charged = float(costed.get("expectancy") or 0.0)
            if charged < 0:
                patch["opt_summary"]["costed_negative"] = True
                LOG.emit(
                    f"{symbol}: maliyetsiz kâğıt {paper:+.3f}, "
                    f"maliyetli ayni dilim {charged:+.3f} - "
                    f"canli bu konfigi odeyerek isletecek.",
                    "OPT", symbol)
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
            # up. Engine H1 orphan-scan is the remaining guard for that window.
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
            patch["pending_primary_patch"] = {}
            if open_here or pending_scan:
                scan_note = " (+ tanimlanamayan ticket taramasi devam ediyor)" if pending_scan else ""
                if primary_changed:
                    # Same promise as pending_exit_patch, for family/TF: do
                    # not trail an open ticket under a different family's
                    # ATR, and do not drop the winner (28.08 NAS100 burst).
                    queued = {k: v for k, v in patch.items() if k in PRIMARY_LAND_KEYS}
                    updated = self.store.update_symbol(
                        symbol,
                        {"pending_exit_patch": {}, "pending_primary_patch": queued},
                        source="opt apply")
                    LOG.emit(
                        f"{symbol}: {len(open_here)} acik pozisyon var{scan_note}, "
                        f"{next_strat}/{next_tf} kuyruga alindi "
                        f"(pozisyon kapaninca uygulanacak).",
                        "OPT", symbol)
                    return {"ok": True, "deferred": True, "symbol": symbol,
                            "config": updated.to_dict() if updated else None}
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
                        # so the UI can show it honestly. The log line below
                        # names the held-back fields; a duplicate payload key
                        # had no panel reader.
                        summary_params = {k: v for k, v in patch["opt_summary"].get("params", {}).items()
                                          if k not in EXIT_RISK_FIELDS}
                        patch["opt_summary"] = {**patch["opt_summary"], "params": summary_params}
                    LOG.emit(f"{symbol}: {len(open_here)} acik pozisyon var{scan_note}, "
                             f"cikis/risk parametreleri ({', '.join(sorted(held_back))}) "
                             f"pozisyon kapanana kadar bekletildi.", "OPT", symbol)
            # Stale secondary_* rows are left in place (inert while ensemble
            # is off). Clearing them is a later stage; this path must not call
            # a secondary writer that no longer exists, and must not refuse a
            # primary family swap because a leftover candidate is stored.
            updated = self.store.update_symbol(symbol, patch, source="opt apply")
        return {"ok": updated is not None, "symbol": symbol, "config": updated.to_dict() if updated else None}
