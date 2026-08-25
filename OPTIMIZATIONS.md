# OPTIMIZATIONS.md

Read-only audit of `C:\Users\Administrator\MicoFx` (started HEAD `0954206`).
Several items landed 25.08: F1 hoist `1624607` (identity `125a545`), `/api/schema`,
capture lock+CSRF, snapshot cycle-book, panel 3s during search, F4/F6/F7.
Still open: fill-verifier 2.1s queue (fail-closed).

Assumptions at audit time: `poll_interval_sec` default 2.0; panel poll 3s
(1.5s while opt `running` — that fast path was removed `d3d1b45`); ~6 enabled
symbols; optimizer may share the host while live.

---

### 1) Optimization Summary

* Health is **good for a 6-symbol ATR book**, already hardened (tick/info TTL, trail once per closed bar, capped rings, opt `_sig_cache` size 4, `opt_runs` trim). The remaining cost is **shared-lock contention and full recomputes**, not micro-allocs.
* Top 3 highest-impact improvements:
  1. Hoist `imputed_spread_pts` / `trigger_pad` out of `simulate()` — Claude measured **~6.90 ms/call at 90k bars**, ~10k calls/symbol/TF ⇒ **~21 min** wasted on a 6×3 full search (`backtest.py:487` vs already-imputed `spread_pts` at `:1251`). Do not impute twice — `:1251` is already imputed. (Measured idempotent 25.08, so a double pass does not change values; the rule is about intent, not a numeric trap.)
  2. Slim `/api/state` and stop a second `positions_get` on every panel poll.
  3. Stop blocking `_cycle` on the ~2.1s fill-verifier `sleep` chain.
* Biggest risk if no changes: during a search the panel speeds up to 1.5s while workers + engine queue on the same MT5 lock — cycle stretch, late trails, missed bar-close entries. A fill-verify stall on one symbol freezes management for the rest of the book for >2s.

---

### 2) Findings (Prioritized)

* **Title:** `imputed_spread_pts` re-run inside every `simulate()` — hoist, not Numba
* **Category:** CPU / Algorithm
* **Severity:** High (search wall) / Low (live)
* **Impact:** optimizer wall time (~21 min on a 6×3 full scan at `max_bars=90000`)
* **Evidence:** Claude microbenchmark (isolated, no live process): 20k bars 1.59 ms/call, **90k bars 6.90 ms/call**. `backtest.py:487` builds `trigger_pad` from `imputed_spread_pts(spread_pts)` per `simulate()`. `walk_forward` already imputes once at `:1251` and passes `spread_price` / `min_stop_series` / `flatten`; it does not pass `trigger_pad`. ~2000 combos × 5 windows ≈ 10k calls/symbol/TF.
* **Why it’s inefficient:** Input is constant for a walk-forward. The caller already paid imputation; `simulate` pays it again. A profiler will attribute this to the bar loop if you look at the wrong line.
* **Recommended fix:** Compute `trigger_pad` once in `walk_forward`, pass `trigger_pad=` into `simulate()`, keep the in-function fallback for direct `simulate()` / tests. **Do not impute twice** — `:1251` `spread_pts` is already imputed. (Measured idempotent 25.08: a double pass does not change values; `125a545` pins that. The rule is about intent, not a numeric trap.)
* **Tradeoffs / Risks:** If walk_forward ever passes raw `bars.spread` as `spread_pts`, the hoist pad and simulate()'s None fallback diverge. Keep the impute at that call site.
* **Expected impact estimate:** ~69 s/symbol/TF; ~21 min on 6 symbols × 3 TF (Claude). Not live-cycle.
* **Removal Safety:** Needs Verification (identity of `trigger_pad`)
* **Reuse Scope:** module (`backtest.py`)

* **Title:** `/api/state` ships the whole world every 3s and re-queries MT5 positions
* **Category:** I/O / Network / Frontend
* **Severity:** High
* **Impact:** latency of engine cycle (lock wait), panel CPU, JSON size, MT5 IPC
* **Evidence:** `micofx/web/app.py:648-663` returns `engine.snapshot()` + full `symbol_payload()` + `system.to_dict()` + `opt_fields` catalogs every poll. `Engine.snapshot` (`engine.py:3811-3813`) calls `positions_view()` → `client.positions()` (`engine.py:3494-3498`) while `_cycle` already did `positions_get`. Panel `refresh()` (`app.js:2261-2295`) hits this every 3s, **1.5s while optimizer is running**.
* **Why it’s inefficient:** Duplicate MT5 book read + serialize N full `SymbolConfig` dicts + static opt-field catalogs that never change during a poll. Poll accelerates exactly when the lock is hottest.
* **Recommended fix:** Light `/api/state` (bot, account, positions, states, opt status). Serve symbols / opt catalogs on their own slower endpoints. Snapshot reuse `engine._positions` from the last cycle. Do not speed the poll during opt.
* **Tradeoffs / Risks:** UI must tolerate slightly stale symbol rows; opt tab already has `/api/opt/*`.
* **Expected impact estimate:** High — likely 30–60% less MT5 lock time from the web thread while the panel is open (measure, do not guess wall %).
* **Removal Safety:** Needs Verification (payload consumers)
* **Reuse Scope:** service-wide (`app.py`, `engine.py`, `app.js`)

* **Title:** Fill verifier sleeps ~2.1s on the engine thread
* **Category:** Concurrency / Reliability
* **Severity:** High
* **Impact:** cycle latency, delayed trail/BE/flatten on every other symbol
* **Evidence:** `mt5client.py:1486-1490` — `for attempt in range(4): time.sleep(0.3 if attempt == 0 else 0.6)` then `positions_get`. Comment documents the 2.1s path. Called inline from market-entry on the `micofx-engine` thread.
* **Why it’s inefficient:** Sleep is outside `_lock` (correct) but still **serializes the whole poll loop**. One ambiguous fill freezes manage/entry for the book.
* **Recommended fix:** Return immediately with `ambiguous`/pending; finish verify on a side queue; only hold `entry_lock` around book mutations. Keep fail-closed (no second order until verified).
* **Tradeoffs / Risks:** Duplicate-entry protection must stay as strict as today (UK100/US30 storm 11.08). Do not fire-and-forget.
* **Expected impact estimate:** High on fill storms (cycle no longer +2s); Low on quiet days.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`mt5client.py` + `engine.py` entry)

* **Title:** Full history fetch + full `compute()` every new bar and every 45s
* **Category:** CPU / I/O / Algorithm
* **Severity:** High
* **Impact:** cycle CPU, MT5 `copy_rates` IPC, late signals
* **Evidence:** `_STALE_BAR_REFRESH = 45.0` (`engine.py:33`). `_refresh_signals` (`engine.py:2095-2101`) fetches `required_bars(params)` (often 400–1680+) whenever `due or stale or last_bar==0`, then rebuilds `IndicatorCache` and `compute()`. Comment at 2084-2089: stale path used to silently carry the system when `due` was wrong.
* **Why it’s inefficient:** Live only needs the last closed bar’s signal. Rebuilding the whole series every 45s even with no new bar is a timer, not an event.
* **Recommended fix:** If `last_closed_time` unchanged, skip the fetch. Append one bar on close; warm-start indicators. Keep a rare full rebuild as integrity check (e.g. 15–30 min), not 45s.
* **Tradeoffs / Risks:** Incremental indicators can drift from a full recompute — must match `compute()` bit-for-bit or you desync live vs walk-forward.
* **Expected impact estimate:** High CPU/IPC on M5 (12 bars/hour × 6 symbols today plus 80 stale rebuilds/hour). Likely 5–10× less bar IPC if stale skip works.
* **Removal Safety:** Needs Verification (signal identity tests)
* **Reuse Scope:** module (`engine.py`, `strategy.py`)

* **Title:** One MT5 `RLock` for engine, panel, and optimizer bar fetch
* **Category:** Concurrency
* **Severity:** High (when opt running) / Medium (panel only)
* **Impact:** throughput of the live cycle, search wall time
* **Evidence:** `MASTER_PROMPT.md` §12; `mt5client.py` wraps public calls in `_lock`. Optimizer plans call `client.bars` for thousands of bars. Panel `positions`/`info` compete.
* **Why it’s inefficient:** Correctness requires a single MT5 connection; the waste is **UI and search using the live client as a query bus**.
* **Recommended fix:** UI reads engine snapshots only. Prefetch all search bars once, then detach workers from MT5. Lower `opt_max_workers` while `engine.running`.
* **Tradeoffs / Risks:** Snapshot age vs live quote; search must not open a second `initialize()`.
* **Expected impact estimate:** High during opt (cycle jitter); Medium otherwise.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide

* **Title:** `entry_blocks` counters can `commit` every poll
* **Category:** DB / I/O
* **Severity:** Medium
* **Impact:** engine-thread sqlite lock, SSD write amp
* **Evidence:** `engine.py:1251-1268` — “Counters are ~1 KB and may hit disk every poll while a signal is held off.” `_flush_entry_blocks` from the cycle (`~966`, `~1200`, `~1342`). Contrast: spread-ratio flush is throttled (300s).
* **Why it’s inefficient:** Hundreds of blocked attempts per bar (comment: EURJPY 339 / 13 min) each persist JSON settings.
* **Recommended fix:** Debounce counter flush 30–60s; keep the event ring throttle as-is.
* **Tradeoffs / Risks:** Panel tally lags by one debounce window after restart mid-bar.
* **Expected impact estimate:** Medium — drops sqlite commits from ~0.5 Hz to ~1/min while gated.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`engine.py`)

* **Title:** Python bar loop in `simulate()` dominates search, not live
* **Category:** Algorithm / CPU
* **Severity:** Medium (opt wall) / Low (live)
* **Impact:** search duration, cost of BE-3-style grid expansion
* **Evidence:** `backtest.py` converts series to lists and walks bars in Python (`simulate` bar loop; `max_open>1` path). Walk-forward `_sig_cache` clears at len>4 (`backtest.py` ~1295-1313) — already bounded.
* **Why it’s inefficient:** Branchy exits (trail, BE, flatten, min_stop) resist naive vectorization; still O(bars × trades) in CPython.
* **Recommended fix:** Profile one GER40 stoch_flip window before Numba. If >70% of worker time is the loop, compile `_trail_one`/`_exit_check` only. Do **not** expand OPT_FIELDS (BE-3) until this is paid.
* **Tradeoffs / Risks:** Bit-identical R vs live is a product invariant — a faster loop that differs by 0.01 R will mis-apply.
* **Expected impact estimate:** Medium–High on search (qualitative until profiled); none on the 2s live cycle.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`backtest.py`)

* **Title:** Supervisor 14-day `deals_since` inside `_cycle`
* **Category:** I/O / Reliability
* **Severity:** Medium
* **Impact:** occasional multi-second cycle stalls
* **Evidence:** Review ~120s (`MASTER_PROMPT.md` §11); `engine.py` calls supervisor from `_cycle` (~870). History fetch shares the MT5 lock.
* **Why it’s inefficient:** Trading loop waits on a reporting query.
* **Recommended fix:** Run review after the cycle or on a worker; never hold `_cycle` on 14d history.
* **Tradeoffs / Risks:** Quarantine can lag one interval (already 120s).
* **Expected impact estimate:** Medium on review ticks; Low average.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** module (`engine.py`, `supervisor.py`)

* **Title:** Per-ticket `tick` + `min_stop_distance` (+ optional full swing scan)
* **Category:** I/O / Algorithm
* **Severity:** Medium
* **Impact:** MT5 IPC × open tickets; CPU if `trail_mode` in {structure, hybrid}
* **Evidence:** `engine.py` `_update_stop` (~3255+): `tick`, `min_stop_distance` (info+tick), structure branch `swing_lows/highs` over the whole series. Trail is already latched per closed bar (`_stop_bar`) — good.
* **Why it’s inefficient:** Cycle already has a tick per symbol; swings can be computed once per bar as backtest does.
* **Recommended fix:** Reuse cycle tick; cache swing series on bar close; keep `trail_min_step` gate (already).
* **Tradeoffs / Risks:** Stale min_stop if broker freeze_level jumps intra-bar (rare).
* **Expected impact estimate:** Medium with 6 tickets + structure; Low on current ATR-only GER40/US30.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** module

* **Title:** Duplicated stop math: `_update_stop` vs `simulate` — **Reuse Opportunity**
* **Category:** Maintainability (runtime cost Low)
* **Severity:** Medium
* **Impact:** bug surface, future opt/live drift (costs more than CPU)
* **Evidence:** `engine.py:3255-3435` vs `backtest.py` `_trail_one` / inner loop (~571-675, ~818+). `0954206` had to wire `breakeven_at_r` twice. `MASTER_PROMPT.md` §0: “the same rule written twice.”
* **Why it’s inefficient:** Two implementations of trail_start / step / hybrid / min_step / BE. Every exit change is paid twice or they diverge.
* **Recommended fix:** Pure function `desired_sl(closed_bar, params, pos) -> float`; live adds broker clamp + modify only.
* **Tradeoffs / Risks:** Large refactor; must keep live quote feasibility (`settled` / retry) separate.
* **Expected impact estimate:** Low CPU; High maintenance ROI if exits keep growing.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide

* **Title:** Panel `innerHTML` full card rebuild on poll — **Reuse Opportunity** (diff render)
* **Category:** Frontend
* **Severity:** Low–Medium
* **Impact:** browser main thread
* **Evidence:** `app.js:2261-2281` `renderTop` / `renderCards` / positions every successful `/api/state`.
* **Why it’s inefficient:** 6 cards × 0.3 Hz is fine; 20 symbols × 1.5s during opt is not free.
* **Recommended fix:** Patch text nodes; rebuild cards only when symbol set changes.
* **Tradeoffs / Risks:** Easy to miss a field; tests are weak on DOM.
* **Expected impact estimate:** Low on this book; Medium if portfolio grows.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`app.js`)

* **Title:** TRADE log line on every SL modify
* **Category:** I/O
* **Severity:** Low
* **Impact:** disk, log rotation
* **Evidence:** `logbus.py` persists TRADE; `_update_stop` emits on successful modify (`engine.py` ~3428).
* **Why it’s inefficient:** Trailing US30 (two writes 10:20/10:25) is fine; a choppy M5 book is not.
* **Recommended fix:** Coalesce trail logs (ticket + new SL + bar time); keep first BE lock as TRADE.
* **Tradeoffs / Risks:** Autopsy of intra-bar trail chatter gets coarser.
* **Expected impact estimate:** Low
* **Removal Safety:** Likely Safe
* **Reuse Scope:** module

* **Title:** `breakeven_at_r` not in `EXIT_RISK_FIELDS` — **not a CPU issue; mid-trade write amplification of lock geometry**
* **Category:** Reliability
* **Severity:** Medium (ops) / Low (CPU)
* **Impact:** open-position stop math can change from the panel without 409
* **Evidence:** `EXIT_RISK_FIELDS` (`models.py` ~379-382) is sl/trail/atr_period only. `0954206` added `breakeven_at_r`. `patch_symbol` 409 only if those keys change with opens (`app.py` ~950-991). Live PATCH 1.5 succeeded with 6 opens (25.08 10:28) — intended, still a hot-path cfg re-read every cycle.
* **Why it’s inefficient:** N/A CPU. It is an extra live branch in `_update_stop` (cheap) plus an unguarded exit-risk door.
* **Recommended fix:** After the book is flat, add the field to `EXIT_RISK_FIELDS` so later 0.5/2.0 edits wait. Do not do this while GER40/JPN/US30 are open unless the operator wants 409.
* **Tradeoffs / Risks:** 409 while open was exactly why it was left out on apply day.
* **Expected impact estimate:** n/a performance; High safety if someone types 0.5 on GER40.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide

* **Title:** MASTER_PROMPT §9 still says “ATR trail and nothing else” — **Over-Abstracted / stale docs**
* **Category:** Maintainability
* **Severity:** Low
* **Impact:** agents re-litigate BE or miss the overlay
* **Evidence:** `MASTER_PROMPT.md:394` vs §0 `breakeven_at_r` paragraph and live `engine.py`.
* **Why it’s inefficient:** Dual source of truth; not runtime.
* **Recommended fix:** One sentence in §9 pointing at §0 overlay. (Docs only; not a patch this audit.)
* **Tradeoffs / Risks:** None
* **Expected impact estimate:** n/a
* **Removal Safety:** Safe
* **Reuse Scope:** local file

* **Title:** `graft/` markdown mirrors — **Dead Code** (docs, not executed)
* **Category:** Build / Cost (agent context)
* **Severity:** Low
* **Impact:** agent token/context, grep noise
* **Evidence:** `graft/micofx/*.md` alongside live `micofx/`.
* **Why it’s inefficient:** Stale line maps of old functions.
* **Recommended fix:** Generate on demand or gitignore from agent search; do not load in default context.
* **Tradeoffs / Risks:** Useful archaeology if kept dated.
* **Expected impact estimate:** Low
* **Removal Safety:** Needs Verification (if any tool still reads graft)
* **Reuse Scope:** repo

---

### 3) Quick Wins (Do First)

1. Stop accelerating panel poll during `opt.state=="running"` (`app.js:2292-2294`) — one line, High ROI under search.
2. Debounce `_flush_entry_blocks` counters to 30–60s — local, Likely Safe.
3. Skip `_refresh_signals` when `last_closed_time` unchanged (keep 45s only if clock/`due` is still untrusted — re-measure; the 15.08 comment may be stale).
4. `positions_view` reuse last cycle book instead of `client.positions()` inside `snapshot()`.
5. Drop `opt_fields` / `engine_opt_fields` / `strategy_opt_fields` from `/api/state` (already known at page load).

---

### 4) Deeper Optimizations (Do Next)

1. Split `/api/state` vs `/api/symbols` vs opt meta; DOM diff the panel.
2. Deferred fill verification queue (fail-closed).
3. Incremental `IndicatorCache` with identity tests vs full `compute()`.
4. Single `desired_sl()` shared by live and paper.
5. Numba/Cython `simulate` inner loop **only after** a worker profile; required before any 3× grid (BE-3).
6. Optimizer: fetch bars once, then CPU-only workers; never a second `mt5.initialize()`.

Do **not**: micro-optimize `secrets.compare_digest` on `/api/state`; unroll ATR; add caching that can serve a forming bar as a signal.

---

### 5) Validation Plan

* **Benchmarks:** `engine.last_cycle_ms` p50/p95 from `/api/state` over 15 min quiet vs 15 min with panel open vs 15 min with opt running. Count `copy_rates` / `positions_get` via a thin counter on `MT5Client` (measure first; do not log every call to disk).
* **Profiling:** `py-spy` on the live PID **read-only** (no `mt5.shutdown`). Separate profile of one `walk_forward` GER40 job in the venv.
* **Metrics before/after:** cycle_ms, sqlite `set_setting` commits/min, `/api/state` JSON bytes, panel `refresh` duration, opt worker CPU, MT5 lock wait (instrument `_lock` acquire time).
* **Correctness tests (must stay green):** `tests/test_engine_breakeven_lock_at_r.py`, `tests/test_breakeven_lock_does_not_give_the_stop_back.py`, `tests/test_trail_breakeven_invariant.py`, `tests/test_backtest_trail_step_mirrors_live.py`, `tests/test_trail_retry_within_bar.py`, `tests/test_core.py` (signal-on-close / fill-next-open). Any incremental-indicator change needs a new “full vs append identical last signal” test.
* **Do not** validate by adding a second MT5 bind or writing `data/micofx.db` from a sidecar.

---

### 6) Optimized Code / Patch (proposals only — not applied)

**A. Do not fast-poll during search**

```javascript
// app.js refresh() finally
const delay = hidden ? 6000 : 3000; // was: fast ? 1500 : 3000
```

**B. Reuse cycle positions in snapshot (sketch)**

```python
# engine.snapshot — prefer last _cycle book if younger than poll_interval
positions = self._positions_snapshot or self.positions_view()
```

Must still refresh on empty/error; `positions_view` stays for orphan scans.

**C. Debounce entry_blocks**

```python
# flush counters at most once per 45s unless events_dirty
if blocks_dirty and (now - self._entry_blocks_flushed_at) < 45 and not events_dirty:
    return
```

**D. Fill verify:** do not delete the 2.1s sleeps until a queue preserves “no second order while ambiguous” (`mt5client.py` comment on UK100/US30).

What would change: less MT5/UI coupling; same orders, same walk-forward numbers. What must not change: forming-bar drop, buy∧sell→neither, fail-closed duplicates, live↔paper trail/BE identity.
