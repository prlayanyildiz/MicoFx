# OPTIMIZATIONS.md

Read-only notes. **Not executed by the engine.** Latest pass:
**26.08 08:40** Cursor clean scan (below). Prior: **08:00** landing,
**08:05** Claude measurement pass, **07:50** reverse-engineering scan.

**HEAD** `0c33d72` + this working tree. Latest pass: **26.08 12:50**
Cursor SCAN-2 (profit/model + remaining opt/security). Prior: **08:40**
clean scan. Live PID **12:32:15** (disk loaded; book was flat at scan).
Do not restart while opens exist just to load `open_original_sl`.

---

### Closed ledger (do not re-open)

| Item | Evidence now |
|---|---|
| F1 `trigger_pad` hoist | `walk_forward` passes `trigger_pad=` into `simulate`. |
| `/api/schema` catalogs | `GET /api/schema`. `/api/state` has no `opt_fields`. |
| Panel 1.5s during search | `app.js` `hidden ? 6000 : 3000`. |
| Snapshot second `positions_get` | `_panel_positions` reuses a fresh cycle book. |
| 45s full bar refetch | Unused name; integrity 900s. |
| `entry_blocks` every-poll commit | 45s debounce. |
| `_sig_cache` full clear | LRU cap 4. |
| Tick/info TTL | 120s / 0.5s. |
| alpha_trend / mavilim | Retired 26.08 holdout. 13 families. |
| `original_sl` RAM-only | **Landed.** `note_fill` writes `open_original_sl`; `track()` restores before first-sight. Pre-patch tickets still first-sight. Do not persist the fallback. |
| Fill-verify blocks `_cycle` | **Landed.** Immediate peek (no sleep if the ticket is there). Engine `defer_verify=True`: pending + inflight + side thread; drain books the fill. Fail-closed: no second send while inflight. Sleeps still exist — on the verifier thread, not `micofx-engine`. |
| Supervisor 14d inside `_cycle` | **Landed.** `_kick_supervisor_review` daemon thread; gate prevents stacking. |
| `/api/state` full `symbol_payload` | **Landed.** State carries `symbols_sig`; panel refetches `/api/symbols` when the set changes. |
| Scale-out remain / second `info` | **Landed.** Clamp `filled` ≤ position; cash from the existing `info` dict. |
| Duplicated trail/BE math | **Landed.** `micofx/exits.py` `overlay_stop`; live clamp stays in `_update_stop`; paper `_trail_one` is the single simulate path. |
| Opt `copy_rates` holds the lock | **Landed (chunked).** `_BAR_FETCH_CHUNK=2500`; lock released between chunks. Still the live client — no second `initialize()`. |
| Stale 1.5s / Windows-day comments | **Landed.** |
| Short MFE ask pad (08:05 C-2) | **Landed.** `_mfe_tick` shorts use `entry - (bar_low + pad)`. |
| `_merge` drops `trade_mfes` (08:05 C-3) | **Landed.** `total.trade_mfes.extend(r.trade_mfes)`. |
| LOG.emit CR/LF minting extra TRADE rows | **Landed.** `logbus.emit` flattens `\r`/`\n` to space. |
| Incumbent holdout replayed twice | **Landed.** `_fresh_incumbent_holdout` memo; `allow_fetch=False`. |
| `/api/opt/run` Origin-unchecked | **Landed 08:45.** `_CRITICAL_MUTATIONS` includes `/api/opt/run` and `/api/opt/cancel`. `strategies`/`timeframes` `max_length=32`. |
| Snapshot `account_info` every 3s | **Landed 08:45.** `_panel_account` reuses cycle book; `_ACCOUNT_TTL` 2s. |
| `day_stats` 5s on every snapshot | **Landed 08:45 (TTL only).** snapshot `max_age=15`; halt path stays 5s. Not a separate `/api/day`. |
| Panel `attempts` mixed units | **Landed 08:45.** Signals column is the count; poll retries on pill `title`. Window not reset. |
| `el({html})` XSS sink | **Landed 08:45.** Branch removed. |
| snapshot `day_stats` fetch on web thread | **Landed 09:15.** `fetch=False`; cycle warms after reap; halt stays 5s. |
| `capacity()` N× `order_calc_margin` every `/api/state` | **Landed 09:15.** `_panel_capacity` 3s TTL, invalidate on ticket/volume; `margin_for` 5s TTL. |
| Panel innerHTML every 3s | **Landed 09:15.** `viewPulse` skip when unchanged; tab switch forces render. |
| Origin only on a named critical set | **Landed 09:15.** Every POST/PUT/PATCH/DELETE needs Origin. Authenticated TestClient sends it. |
| Incremental `IndicatorCache` | **Closed 09:15 (measured won't-do).** Fresh cache+`compute` 1680 bars **2.57ms**; 6×M5 close ≈15ms. Identity risk > ROI. |
| Numba `simulate` | **Closed 09:15 (measured won't-do until grid 3×).** `simulate` 1680 bars **6.53ms**. Live irrelevant; search unpaid. |
| TRADE log on SL modify | **Closed 09:15 (won't-change).** `_stop_bar` already one modify/log per ticket per bar. Autopsy pairs on TRADE. |
| Flatten autopsy `profit` empty | **Landed 09:32.** `_close_tracked` used `profit=None`; `close_position` now puts deal PnL (or `kar~` fallback) on `fill["profit"]`. Do not rewrite the 27 historical rows. R/capture were already complete. |
| Autopsy `left_on_table_r` paints losers | **Landed 09:43.** Panel + report total **winners only** (`r_realised > 0`). Stored row formula unchanged. MFE is bar-extreme, not harvestable. |
| Halt-flatten tests AttributeError `_day_cache` | **Landed 09:43.** Fixture `__new__` miss after cycle-warm `day_stats()`. Live brake unchanged. |
| AGENTS.md density | **Landed 10:12** from Claude 10:05 proposal + Cursor keeps (bridges, overlays, 900s, verifier). |
| Lying `scalp TF kilidi acik` | **Landed 12:50.** `tf_lock_status(tf_allow)` — empty `STRATEGY_TIMEFRAMES` logs `aile TF kilidi kapali`. XAUUSD is live burst/M15. |
| Silent panel flatten-all | **Landed 12:50.** `Engine.close_all(reason=)` — panel doors pass `panel tumunu kapat` / `panel sembol kapat`. Panic/session/daily-loss stay on their own lines. Do not rewrite the 12:22 rows. |
| Opt pickles bars 13× per TF | **Landed 13:05.** One npy folder per `(symbol, TF)`; workers `mmap_mode='r'`. Same arrays. Temp dir cleared when the run ends. |

### Still open (identity tests / profile first — do not treat as this-scan bugs)

* 900s integrity still fetches full `required_bars` (chunked; no compute). Stamp-only fetch needs verification.
* Search wall: Numba still unpaid if `OPT_FIELDS` grows 3× — re-profile a GER40 worker then, not now.
* `/api/state` during a 14-worker search: measured **148s** this page (shared MT5 `RLock`). Serve-stale / skip-lock needs identity tests. Not a second `initialize()`.
* O-1/O-2/O-3 settings blob rewrite: still measure-first (SCAN-1). **O-4 landed 26.08:** Origin-less POST 403 is the gate; the unused `_CRITICAL_MUTATIONS` frozenset is gone.

---

## 26.08 12:50 — Cursor SCAN-2 (opt + security + profit/model)

Live `/api/state` (cookie): **0 open**, bot watch+trade on, PID 12:32:15,
demo 61562752, eq=bal 2313.55, day −2.09% / −49.44 realised, halt off.
Manual opt **running** `apply_best=true` 0/6 (GER40, JPN225, NAS100 in
flight). Operator raised US30/JPN225/GER40/NAS100/SpotBrent
`max_positions` to 3; `size_by_edge` on; concurrent cap 30%. 12:22
silent flatten of the previous 6 then IPC −10001.

Constitution (§0 / §19) **not** reopened: session/day-end flatten,
no TP ladders, `trail_start <= trail_step` legal, 13 families,
`_slice_ok` / incumbent gate stays the apply door. Capture is not a
score input.

### 1) Optimization Summary

* Health still **good for a 6-symbol ATR book**. Closed-ledger landings
  hold. New residual cost is the **shared MT5 RLock under a 14-worker
  search** (state 148s this page).
* Top 3 this pass: (1) state/trail starved during search, (2) lying
  `scalp TF kilidi acik` log, (3) silent panel flatten-all (12:22).
* Biggest risk if unchanged: a flatten or apply cannot be autopsied,
  and operators trust a TF lock that is **off**.

### 2) Findings (Prioritized)

* **Title:** `/api/state` blocks on opt `copy_rates`
* **Category:** Concurrency / I/O
* **Severity:** High (operator) / Medium (trail delay)
* **Impact:** panel + cycle wait on the same `RLock` as 14 workers
* **Evidence:** this page, 148s for cookie+state+symbols while
  `opt.busy=true` `done=0/6`. `last_cycle_ms` was 1355ms just after
  restart, 4.8ms later between chunks.
* **Why:** live client is the only `initialize()`. Chunked fetch
  releases between 2500-bar slices; 14 processes still queue.
* **Recommended fix:** serve last cycle book for panel when opt is
  busy (TTL already exists). Measure first. **Not** a second MT5.
* **Tradeoffs:** stale equity for seconds during search
* **Expected impact:** panel 148s → <1s during search
* **Removal Safety:** Needs Verification
* **Reuse Scope:** `engine.snapshot` / `_panel_*`
* **Status:** still open (measure)

* **Title:** OPT start line claimed scalp TF lock while map is empty
* **Category:** Reliability / Maintainability
* **Severity:** Medium
* **Impact:** operators misread which pairings the search is allowed
* **Evidence:** `optimizer.py` hardcoded `scalp TF kilidi acik`;
  `STRATEGY_TIMEFRAMES == {}`; live XAUUSD `burst/M15`
* **Why:** leftover string after the restriction was lifted
* **Recommended fix:** `tf_lock_status(tf_allow)` — **landed 12:50**
* **Tradeoffs:** none
* **Expected impact:** log matches the book
* **Removal Safety:** Safe
* **Reuse Scope:** `optimizer.py`

* **Title:** Panel flatten-all left no caller line
* **Category:** Reliability
* **Severity:** High (forensics) / Low (runtime)
* **Impact:** 12:22 six `kar~` closes cannot be distinguished from
  halt/session/panic
* **Evidence:** log 12:22:03–04 then IPC; no `Zorunlu flatten` /
  `Gunluk zarar` / `ACIL DURDURMA` / `Bot durduruldu`. Panel
  `POST /api/positions-close-all` called `close_all()` bare.
* **Recommended fix:** `close_all(reason=)` — **landed 12:50**
* **Tradeoffs:** none
* **Expected impact:** next silent flatten is greppable
* **Removal Safety:** Safe
* **Reuse Scope:** engine + web doors

### 3) Quick Wins (Do First)

1. Honest TF-lock fragment — done.
2. Panel flatten reason — done.
3. Do **not** cancel the in-flight search; churn brake (48h /
   `_beats_incumbent`) still gates apply.

### 4) Deeper Optimizations (Do Next)

1. Stale snapshot while opt holds the lock (identity tests).
2. 900s integrity stamp-only fetch (still open).
3. O-1/2/3 blob rewrite — measure at 2000-row cap, not today.

### 5) Validation Plan

* `tests/test_tf_lock_status_tells_the_truth.py`
* `tests/test_panel_flatten_names_the_caller.py`
* `tests/test_session_csrf_gate.py` (close_all signature)
* Overlay identity already in `test_backtest_trail_step_mirrors_live.py`
  — do not re-open.
* Next search start line must contain `aile TF kilidi kapali`.

### 6) Optimized Code / Patch

See `tf_lock_status` in `optimizer.py` and `Engine.close_all(reason=)`.

### Profit / model (one-by-one)

| Surface | Verdict |
|---|---|
| Hard stop + ATR trail + `overlay_stop` | Identity tests green; live clamp stays in `_update_stop`. Do not split again. |
| `trail_start <= trail_step` | Legal. Live: GER40 0.5/2.2, SpotBrent 2.0/2.2, JPN 0.5/1.6, NAS 1.0/1.8, US30 1.4/1.6. XAUUSD **2.0/0.4** (start>step, tight once armed) is opt-chosen holdout +76 R — do not override mid-search. |
| `breakeven_at_r` | All six at **1.5**. Not 0.5. Not an OPT axis. |
| `partial_at_r` | GER40 **1.5** only; others 0. One-shot third. Do not bring ladders back. |
| `trail_mode` | All `atr`. Structure/hybrid remain searchable. |
| 13 families | Live: parabolic_flip, burst, stoch_flip×3, mtf_pullback. No alpha_trend/mavilim. |
| TFs | SpotBrent M15, XAUUSD M15, GER40 M30, JPN225 M15, NAS100 M30, US30 **M5**. Empty `STRATEGY_TIMEFRAMES` is deliberate; scalp-on-M15 is allowed. |
| Session/day-end flatten | Settled 09.08. Overnight gap risk. Do not file as a bug. |
| Apply / churn | MATCH-1 still stands: strategies directionally correct; churn was the leak. 48h age + `_beats_incumbent` + `_slice_ok` stay. Capture is **not** a gate. `apply_best` default true — questioned, not silently changed. |
| Book today | GER40 −45 (4 trades, sl 1.0 ATR + BE 1.5 + partial 1.5) looks like chop against a tight stop, not a trail bug. Do not PATCH overlays during the running search. |
| `max_positions=3` on correlated indices | Yellow. Operator set it. Nominal book ≈ 0.8% × 3 × EDGE_MAX 2.2 × 5 + gold ≈ 28% vs 30% cap. Selector still ranks; cap refuses the tail. Do not revert unasked. |
| `size_by_edge` | On. Yellow. Leave. |

**Do not code:** new families, TP, time-stop, score/capture-as-gate, Ai extras, second MT5, rewriting historical autopsy rows.

**Refuse:** generic ORM/Redis “scans”.

### SECURITY AUDIT: SCAN-2 (working tree vs 0c33d72)

**Risk Assessment:** Low (dirty tree is prior landed work + these two log fixes)

#### Findings:
* None new on this pass. Origin-on-every-mutation and `el({html})` removal stay in the closed ledger. Ticket highlight has `test_log_ticket_highlight_is_escape_safe.py`.

#### Observations:
* `apply_best` still defaults True on `OptRun` — churn door, gated.
* `/api/state` stall is availability under search, not an auth hole.
* Claude SCAN-2 inbound; they may add findings — do not pre-empt.

---

Section 2 below is the **07:50 scan** kept as evidence. Landed items are in the closed ledger — do not re-open them from the old wording.

---

---

### 2) Findings (Prioritized)

* **Title:** Fill verifier sleeps ~2.1s on the engine thread
* **Category:** Concurrency / Reliability
* **Severity:** High
* **Impact:** cycle latency; delayed trail/BE/flatten/scale-out on every other symbol
* **Evidence:** `_verify_ambiguous_send` (`mt5client.py:1446-1519`). Loop `for attempt in range(4): time.sleep(0.3 if attempt == 0 else 0.6)` then `with self._lock: mt5.positions_get` (`:1486-1492`). Math: 0.3 + 3×0.6 = **2.1s**. Sleep is **outside** `_lock` (correct). Caller is `open_market` → `_try_entry` under `entry_lock` (`engine.py:2478-2488`) on the `micofx-engine` thread, **after** `manage_positions` in the same `_cycle` (`:842` then `:938-969`).
* **Why it’s inefficient:** The poll loop is single-threaded. One lagging fill blocks every later symbol’s entry and the *next* cycle’s manage until the window ends.
* **Recommended fix:** Return `ambiguous` / pending immediately; finish verify on a side queue; keep fail-closed (no second order until verified). UK100/US30 11.08 storm + comment at `:1468-1476` is the constraint. Do **not** delete the sleeps as a “perf fix”.
* **Tradeoffs / Risks:** Duplicate-entry protection must stay as strict as today. At `max_positions>1` the comment already warns the empty-book retry is weaker.
* **Expected impact estimate:** High on fill storms (cycle no longer +2s); Low on quiet days.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`mt5client.py` + `engine.py` entry)

* **Title:** `original_sl` lives only in `execution._open` RAM
* **Category:** Reliability
* **Severity:** High (measurement) / n/a CPU
* **Impact:** autopsy R after any restart-with-opens; trail-win `r_realised` tautology
* **Evidence:** `track()` `setdefault("original_sl", current sl)` (`execution.py:278-283`). `note_fill` also `setdefault`s into RAM (`:302-306`). `_persist` writes `execution_samples`, not the open book (`:209-217`). Process death empties `_open`. Next `positions_get` SL is the **trail**.
* **Why it’s inefficient:** N/A CPU. The book is rebuilt from the live stop, which is current, not fill-time.
* **Recommended fix:** Persist `{ticket: original_sl, risk_dist}` via `Store` on `note_fill`; reload before `track()` setdefault. Prune with the same live-set as `scale_out_done`. Do **not** restart while opens exist just to “load a patch”.
* **Tradeoffs / Risks:** Stale rows if the broker reuses a ticket (rare). Must prune.
* **Expected impact estimate:** High for autopsy truth; zero live PnL.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`execution.py` + store key)

* **Title:** Optimizer bar fetch shares the live MT5 `RLock`
* **Category:** Concurrency / I/O
* **Severity:** High (when a search runs) / Low (opt idle)
* **Impact:** live cycle jitter; search wall time
* **Evidence:** Planner thread `self.client.bars` per symbol/TF (`optimizer.py:717-747`), including a halving retry loop that can `bars()` several times. Workers get numpy payloads only. Public MT5 calls take `self._lock` (`mt5client.py:190`). Panel `/api/state` still calls `snapshot()` every 3s (`app.py:677-687`); fallback `positions_get` if the cycle book is stale.
* **Why it’s inefficient:** One connection is required; the waste is **search using the live client as a history bus** while `_update_stop` needs the same lock.
* **Recommended fix:** Prefetch all search bars once, then detach workers. UI already prefers `_panel_positions`. Lower `opt_max_workers` while `engine.running`. Never a second `mt5.initialize()`.
* **Tradeoffs / Risks:** Snapshot age vs live quote; search must not open a second terminal bind.
* **Expected impact estimate:** High cycle jitter during opt; none when idle. **Likely** — measure lock wait, do not guess wall %.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide

* **Title:** Supervisor 14-day `deals_since` inside `_cycle`
* **Category:** I/O / Reliability
* **Severity:** Medium
* **Impact:** occasional multi-second cycle stalls (review ticks)
* **Evidence:** `_cycle` calls `supervisor.review` when `due()` (`engine.py:876-880`) **before** evaluate/entry. Default `review_interval_sec=120`, `lookback_days=14` (`supervisor.py:23-24`). `review` → `_closed_trades` → `client.deals_since` (`supervisor.py:494`) under the same MT5 lock.
* **Why it’s inefficient:** Trading loop waits on a reporting query.
* **Recommended fix:** Run review after the cycle or on a worker; never hold `_cycle` on 14d history.
* **Tradeoffs / Risks:** Quarantine can lag one interval (already 120s).
* **Expected impact estimate:** Medium on review ticks; Low average. **Likely** until lock-wait is instrumented.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** module (`engine.py`, `supervisor.py`)

* **Title:** `/api/state` still serializes full `symbol_payload()` + `day_stats()` every 3s
* **Category:** I/O / Frontend / Caching
* **Severity:** Medium
* **Impact:** JSON size, panel CPU; occasional MT5 lock on cache miss
* **Evidence:** `state()` returns `engine.snapshot()` + `symbols: symbol_payload()` + `system` + `opt` (`app.py:677-687`). `symbol_payload` 1.5s cache then `client.info` per symbol (`:615-637`). `snapshot()` always calls `day_stats()` (`engine.py:4023-4024`). `day_stats` caches **5s** then `deals_since(day_start)` (`:3772-3786`). `_symbol_daily_halt` also reads `day_stats()` (`:3709`).
* **Why it’s inefficient:** Config rows rarely change; deal history is a reporting query on the web thread when the 5s cache expires. Catalogs already moved; **symbol rows did not**.
* **Recommended fix:** Serve symbols on `/api/symbols` (already exists `:689-691`); state carries ids + dirty stamp. Keep cycle-book reuse. Keep `day_stats` 5s cache; do not drop it.
* **Tradeoffs / Risks:** UI must tolerate slightly stale config rows (already 1.5s).
* **Expected impact estimate:** Medium JSON/CPU; Low lock time while cycle + day cache are fresh.
* **Removal Safety:** Needs Verification (payload consumers)
* **Reuse Scope:** service-wide

* **Title:** Full `IndicatorCache` + `compute()` on every new closed bar
* **Category:** CPU / I/O / Algorithm
* **Severity:** Medium (live CPU) — **not** the old “every 45s” claim
* **Impact:** cycle CPU and `copy_rates` IPC on bar close
* **Evidence:** After a fetch, same `last_closed_time` → return False (`engine.py:2253-2254`). New bar → rebuild cache + `compute()` (`:2257-2259`). Fetch itself still pulls `required_bars` (often 400–1680+) on due/integrity (`:2186-2187`). Integrity every 900s even with no new bar (`:2182`).
* **Why it’s inefficient:** Live only needs the last closed bar’s signal. Full rebuild on **bar close** is honest; a 900s integrity pass is cheap vs the old 45s timer. Incremental indicators would help M5 (12 closes/hour × N symbols), not the idle 900s path.
* **Recommended fix:** Append-one-bar warm start **only** with bit-identical tests vs full `compute()`. Keep 900s integrity. Do **not** re-enable `_STALE_BAR_REFRESH`.
* **Tradeoffs / Risks:** Drift vs walk-forward = live/paper desync.
* **Expected impact estimate:** Medium on M5 books; Low on M30. **Likely**  — profile `compute()` share of `last_cycle_ms` first.
* **Removal Safety:** Needs Verification (signal identity)
* **Reuse Scope:** module (`engine.py`, `strategy.py`)
* **Classification:** not Dead Code — the unused `_STALE_BAR_REFRESH` **name** is Dead Code (Safe to leave as comment; Needs Verification to delete the constant in case a test imports it).

* **Title:** Duplicated stop math: `_update_stop` vs `simulate` — **Reuse Opportunity**
* **Category:** Maintainability (runtime cost Low)
* **Severity:** Medium
* **Impact:** live↔paper drift (costlier than CPU)
* **Evidence:** Live `Engine._update_stop` (`engine.py:3349-3529`) vs Python bar loop in `simulate` (`backtest.py:459+`, trail/BE ~636+, ~1007+). Constitution: change both. Uncommitted MFE tracking did not unify them.
* **Why it’s inefficient:** Two implementations of trail_start / step / hybrid / min_step / BE / `partial_at_r` overlays.
* **Recommended fix:** Pure `desired_sl(closed_bar, params, pos) -> float`; live adds broker clamp + modify only.
* **Tradeoffs / Risks:** Large refactor; keep quote feasibility (`settled` / retry) separate.
* **Expected impact estimate:** Low CPU; High maintenance ROI if exits keep growing.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide

* **Title:** Python `simulate()` bar loop dominates search wall, not live
* **Category:** Algorithm / CPU
* **Severity:** Medium (opt wall) / Low (live)
* **Impact:** search duration; cost of any grid expansion
* **Evidence:** Series converted to lists; sequential loop (`backtest.py:526+`). No Numba. Uncommitted `_mfe_tick` / `trade_mfes` add O(1) per bar inside that loop (`Result.trade_mfes`, `capture` at `:73-93`) — not a new bottleneck.
* **Why it’s inefficient:** Branchy exits resist naive vectorization; O(bars × open trades) in CPython.
* **Recommended fix:** `py-spy` one GER40 `walk_forward` in the venv **before** Numba. If >70% of worker time is the loop, compile trail/exit only. Do **not** expand `OPT_FIELDS` until this is paid. Do **not** put `capture` into `score()`.
* **Tradeoffs / Risks:** Bit-identical R vs live is a product invariant.
* **Expected impact estimate:** Medium–High on search (qualitative until profiled); none on the 2s live cycle.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`backtest.py`)

* **Title:** Scale-out remain unclamped; cash takes a second `info()` path
* **Category:** Reliability / I/O
* **Severity:** Low
* **Impact:** one-poll poisoned `pos["volume"]`; extra `info()` on a rare event
* **Evidence:** `_maybe_scale_out` (`engine.py:3531-3596`). `info()` for min/step (`:3566`); `filled = float(fill.get("volume") or close_vol)` then `remain = volume - filled` with **no** clamp (`:3585-3587`); `pos["volume"] = remain` (`:3595`). Cash: `money_per_price_unit` (`:3590`) → another `info()` (`mt5client.py:960-969`), usually TTL-hit. Gate R uses `max(atr * sl_atr_mult, min_stop)` (`:3563`) — **not** `book.original_sl`. `done.add` is one-shot even on IOC `DONE_PARTIAL` (intended).
* **Why it’s inefficient:** Second info is reporting-only. Unclamped remain can go negative until the next `positions_get`.
* **Recommended fix:** `filled = min(filled, pos.volume)`; clamp remain ≥ 0; WARN on mismatch. Pass tick_value/tick_size from the existing `info` dict for cash.
* **Tradeoffs / Risks:** Clamping hides a broker lie; WARN is enough. Cash is audit trail, not a deal.
* **Expected impact estimate:** Low (once per scaled ticket; DONE_PARTIAL rare).
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`engine.py`)

* **Title:** Per-ticket `tick` + `min_stop_distance` in `_update_stop`
* **Category:** I/O / Algorithm
* **Severity:** Low–Medium
* **Impact:** MT5 IPC × open tickets; CPU if `trail_mode` in {structure, hybrid}
* **Evidence:** `_update_stop` (`engine.py:3349+`) takes a fresh tick + `min_stop_distance`. Structure/hybrid can scan swings over the series. Trail already latched per closed bar via `_stop_bar` in `manage_positions`.
* **Why it’s inefficient:** Cycle already has a tick per symbol; backtest precomputes swings once.
* **Recommended fix:** Reuse cycle tick; cache swing series on bar close; keep `trail_min_step` gate.
* **Tradeoffs / Risks:** Stale min_stop if freeze_level jumps intra-bar (rare).
* **Expected impact estimate:** Medium with many tickets + structure; Low on current ATR-only book. **Likely**.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** module

* **Title:** Panel full `innerHTML` rebuild on every poll
* **Category:** Frontend
* **Severity:** Low
* **Impact:** browser main thread
* **Evidence:** `refresh()` (`app.js:2289-2298`) calls `renderTop` / `renderCards` / positions on each successful `/api/state` when the panel tab is active. `esc()` is used (`:84`).
* **Why it’s inefficient:** 6 cards × 0.3 Hz is fine; 20 symbols is not free.
* **Recommended fix:** Patch text nodes; rebuild cards only when the symbol set changes.
* **Tradeoffs / Risks:** Easy to miss a field; DOM tests are thin.
* **Expected impact estimate:** Low on this book; Medium if the portfolio grows.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`app.js`)
* **Classification:** Reuse Opportunity (diff render)

* **Title:** TRADE log on every successful SL modify
* **Category:** I/O
* **Severity:** Low
* **Impact:** disk, log rotation
* **Evidence:** `_update_stop` emits TRADE on successful modify (`engine.py` ~3522-3524).
* **Why it’s inefficient:** Trailing index on M30 is fine; a choppy M5 book is chatter.
* **Recommended fix:** Coalesce trail logs (ticket + new SL + bar time); keep first BE lock as TRADE.
* **Tradeoffs / Risks:** Autopsy of intra-bar trail chatter gets coarser.
* **Expected impact estimate:** Low
* **Removal Safety:** Likely Safe
* **Reuse Scope:** module

* **Title:** Stale comments that will re-open closed work — **Over-Abstracted / stale docs**
* **Category:** Maintainability
* **Severity:** Low
* **Impact:** agents re-litigate 1.5s poll / “Windows day”
* **Evidence:** `/api/schema` docstring still says catalogs rode `/api/state` “1.5s while a search runs” (`app.py:662`). `day_stats` docstring says “current local (Windows) day” (`engine.py:3773`) but `_day_start_epoch` is broker-calendar (`:3742-3750`).
* **Why it’s inefficient:** Dual source of truth; not runtime.
* **Recommended fix:** One-line docstring fixes when next touching those functions. Not this audit.
* **Tradeoffs / Risks:** None
* **Expected impact estimate:** n/a
* **Removal Safety:** Safe
* **Reuse Scope:** local file

* **Title:** `graft/` markdown mirrors — **Dead Code** (docs, not executed)
* **Category:** Cost (agent context)
* **Severity:** Low
* **Impact:** grep noise, wrong line maps
* **Evidence:** `graft/micofx/*.md` vs live `micofx/`.
* **Why it’s inefficient:** Stale sourcedump.
* **Recommended fix:** Do not treat as live. Already in AGENTS.md.
* **Tradeoffs / Risks:** Archaeology if dated.
* **Expected impact estimate:** Low
* **Removal Safety:** Needs Verification (if any tool still reads graft)
* **Reuse Scope:** repo

* **Title:** Uncommitted `strategies=` opt filter is not a live hot-path win until used
* **Category:** Cost / Concurrency
* **Severity:** n/a (door, not a bottleneck)
* **Impact:** a one-off sweep can skip families without writing `opt_params`
* **Evidence:** `OptRun.strategies` (`app.py:90-101`) → `optimizer.start(..., strategies=)` (`:2146-2150`). Whitelist against `STRATEGIES` (`optimizer.py:314-339`). Empty = inherit. Comment: a saved subset would stick scheduled reopt (`:314-317`).
* **Why it’s inefficient:** N/A. Full 13-family sweep still hits `client.bars` on the planner when someone starts `/api/opt/run` with no filter.
* **Recommended fix:** When **flat** and asked: pass the family list on the run body; `apply_best` still operator. Do not persist the subset.
* **Tradeoffs / Risks:** `apply_best` default remains `True` on `OptRun`.
* **Expected impact estimate:** High lock time avoided only if the operator actually restricts the run.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide

---

### 3) Quick Wins (Do First)

1. Persist `original_sl` (restart-with-opens stops lying). After a gece load when **flat**, not instead of it.
2. Clamp scale-out `filled` ≤ `pos.volume`; compute `kar=` from the `info` dict already in `_maybe_scale_out`.
3. Fix the two stale comments (`app.py:662`, `engine.py:3773`) so the next scan does not re-open 1.5s poll / UTC-day.
4. Do **not** start a live search, holdout-capture, or flatten to “make restart safe.”

Already done (not wins anymore): hoist `trigger_pad`; `/api/schema`; 3s poll; cycle-book snapshot; 900s integrity; entry_blocks 45s debounce; retire alpha_trend/mavilim in this working tree.

---

### 4) Deeper Optimizations (Do Next)

1. Deferred fill-verify queue (fail-closed). Highest remaining live-cycle item.
2. `/api/state` without full `symbol_payload` every 3s; keep `day_stats` 5s cache.
3. Supervisor review off the `_cycle` critical path.
4. Shared `desired_sl()` live↔paper.
5. Incremental `IndicatorCache` vs 900s full rebuild — identity tests required.
6. Optimizer: fetch bars once, CPU-only workers; optional `strategies=` on a **flat** book.
7. Numba/Cython `simulate` inner loop **only after** a worker profile; required before any 3× grid (BE-3).

Do **not:** micro-optimize `secrets.compare_digest` on `/api/state`; unroll ATR; re-enable `_STALE_BAR_REFRESH`; put `capture` into the walk-forward score; reintroduce `tp_atr_mult` / `partial_tp_r` / `max_bars_in_trade`; resurrect `alpha_trend` / `mavilim`.

---

### 5) Validation Plan

* **Benchmarks:** `engine.last_cycle_ms` p50/p95 from `/api/state` over 15 min quiet vs 15 min with panel open vs 15 min with opt running. Count `copy_rates` / `positions_get` / `deals_since` via a thin counter on `MT5Client` (measure first; do not log every call to disk).
* **Profiling:** `py-spy` on the live PID **read-only** (no `mt5.shutdown`). Separate profile of one `walk_forward` GER40 job in `C:\MicoFX-venv\Scripts\python.exe`.
* **Metrics before/after:** cycle_ms, sqlite `set_setting` commits/min, `/api/state` JSON bytes, panel `refresh` duration, opt worker CPU, MT5 lock-acquire time, first post-load trail-win autopsy (`r_realised ≠ 1.000`, cash R within 2%).
* **Correctness tests (must stay green):** trail/BE identity suite (`test_engine_breakeven_lock_at_r.py`, `test_breakeven_lock_does_not_give_the_stop_back.py`, `test_trail_breakeven_invariant.py`, `test_backtest_trail_step_mirrors_live.py`, `test_trail_retry_within_bar.py`), `test_core.py` (signal-on-close / fill-next-open), `test_scale_out_once.py`, `test_panel_does_not_fast_poll_during_opt.py`. Uncommitted: `test_simulate_records_per_trade_mfe.py`, `test_keep_log_does_not_quote_a_stale_stamp.py`, `test_opt_run_can_restrict_families.py`, `test_retired_indicators_stay_gone.py`. Any incremental-indicator change needs “full vs append identical last signal”.
* **Do not** validate by adding a second MT5 bind or writing `data/micofx.db` from a sidecar.

---

### 6) Optimized Code / Patch (proposals only — not applied)

**A. Persist original stop (sketch)**

```python
# note_fill already has original_sl; also Store.set_setting("open_original_sl", {ticket: sl})
# track(): setdefault from that map before pos["sl"]
```

**B. Scale-out remain + cash from existing `info`**

```python
filled = max(0.0, min(float(fill.get("volume") or close_vol), float(pos.get("volume") or 0)))
remain = float(pos.get("volume") or 0) - filled
tick_size = float(info.get("tick_size") or info.get("point") or 0)
tick_value = float(info.get("tick_value") or 0)
mpp = (tick_value / tick_size) * filled if tick_size > 0 and tick_value > 0 else 0.0
cash = mpp * move
```

**C. Fill verify:** do not delete the 2.1s sleeps until a queue preserves “no second order while ambiguous” (`mt5client.py:1457-1480`).

What would change: less MT5/UI coupling; honest autopsy R after restart. What must not change: forming-bar drop, buy∧sell→neither, fail-closed duplicates, live↔paper trail/BE identity, score formula, `capture` as a visible column only.

---

### SECURITY AUDIT: working tree vs HEAD `0c33d72`

**Risk Assessment:** Low

Uncommitted product change is holdout cleanup + observability: retire two families, report `capture`, honest keep-log, one-off `strategies=` on existing `POST /api/opt/run`, tally silent `_evaluate` refuses. No new endpoints, no SQL, no secrets, no `subprocess` change.

#### **Findings:**

* **Authenticated opt family list unbounded before whitelist** (Severity: Low)
* **Location:** `micofx/web/app.py:90-101` (`OptRun.strategies`); `micofx/optimizer.py:317-331`
* **The Exploit:** A session-holding caller POSTs a huge `strategies` array. Names are `str()`’d then filtered to `STRATEGIES`. Unknown names drop; all-unknown → 409. Same class as existing `timeframes`. Not RCE/SQLi. Classic CSRF from another site is mitigated by SameSite=Strict cookie; `/api/opt/run` is **not** in `_CRITICAL_MUTATIONS` (`app.py:569-575`) — **pre-existing**, not introduced here.
* **The Fix:** Optional `max_length` on the list (same as timeframes if added). Do not apply in this audit.

* **Unauthenticated fill volume trusted for remain** (Severity: Low) — **unchanged, still open**
* **Location:** `micofx/engine.py:3585-3595`
* **The Exploit:** Not remote. MT5 `result.volume` (or a stub) larger than `pos.volume` writes negative `pos["volume"]` for one poll. Panel/API cannot inject this field.
* **The Fix:** Clamp as in §6 B. Do not apply in this audit.

#### **Observations:**

* `apply_best` still defaults `True` on `OptRun` — family subset + apply is an operator write to live configs, same privilege as HEAD.
* Unknown leftover `strategy: alpha_trend|mavilim` in the live DB will not trade (`strategy.py:406-413`); it will WARN once per name. Not a crash, not an auth bypass.
* `capture` is read-only on holdout dicts; not a mutation surface.
* Session cookie + Origin on `_CRITICAL_MUTATIONS` unchanged. Holdout capture stays Origin-gated (`:574`).
* No hardcoded credentials in the diff. Tests only.
* `innerHTML` in `app.js` still goes through `esc()` (`:84`) on the poll path this diff did not widen.

---

### 25.08 book baseline (measurements, not software TODOs)

Do not re-litigate these as CPU findings. Do not ship TP / time-stop / skip_after_loss / BE 0.5 from them.

* UTC day full closes n=38 cash **+14.91**; GER scale-out ≈**+107.5** extra (not in autopsy `$`). Balance check: 2192.73 + 14.91 + 107.5 ≈ 2315.
* US30 21 closes **−96.62** (SELL 14 / −120.33 vs BUY 7 / +23.71). Never-green = **MFE ≤ 0.05 R**.
* Winner capture median ~**50%**; book capture is not a score input.
* O-5: five pre-fix autopsy rows with `sl`+`r=+1.0` (GER trio cash **+158**). Do not rewrite. Cash/`kar=` is truth.
* Reverse-after-SL is post-fill cooldown geometry (`max_positions=1` frees the slot). Not a trail bug.
* Keep-line `test net` was the apply stamp; working-tree logs `(taze test …R)` / `(damga …R, dd.mm)`.

---

# 26.08 08:05 UTC+3 — Claude diff-level pass (adds to the 07:50 scan, does not replace it)

The 07:50 scan is a **system/hot-path** audit and its closed ledger holds. This
pass re-read the same uncommitted diff for **correctness of the new measurements**
and found five things the 07:50 pass did not carry. Two of them contradict a
conclusion above; both are named as disagreements, not corrections.

Read-only. Live PID 10424, started **26.08 01:38:46**, so the diff is **not
loaded**. Nothing applied.

### 1) Optimization Summary

* The diff's three products (evaluate-refuse tally, per-trade MFE → `capture`,
  opt `strategies=` + fresh incumbent replay) are all pointed the right way.
  The remaining cost is not CPU — it is **the numbers themselves**: a new count
  shares a column with an old count of a different unit, and `capture` is biased
  on one side of the book.
* Top 3:
  1. `_mfe_tick` does not pad the short side (**C-2**). `capture` reads low on
     sells only — and US30 SELL is the next cohort queued for judgment.
  2. `entry_blocks.attempts` now carries two units in one column (**C-1**),
     measured live: US30 `bar_bosluk` ratio **1.0** against `spread` **104.7**.
  3. `_merge()` drops `trade_mfes` (**C-3**) — every pooled Result reports
     `capture: null`, silently.
* Biggest risk: both agents rank symbols off these tables. A column in the wrong
  unit opens the wrong gate. This is a **verdict** risk, not a latency risk.

### 2) Findings (Prioritized)

* **Title:** `_mfe_tick` omits the ASK pad on the short side — `capture` is biased on sells
* **Category:** Algorithm (measurement correctness)
* **Severity:** High
* **Impact:** `Result.capture`, `opt_summary.holdout.capture`, any buy-vs-sell capture comparison
* **Evidence:** New helper (`backtest.py:720-723`): `fav = (bar_high - entry) if is_buy else (entry - bar_low)`. Eight lines above, `_mae_tick` (`:704-712`) does pad the same side: `adverse = bar_high + float(trigger_pad[j]) - entry`. `stop_fill_price` (`:424-426`) states the rule: *"short on `bar_high + trigger_pad >= sl` (the pad is the bar's spread so a short covers on the ask)"*. A short's best realisable price is `bar_low + trigger_pad`, not `bar_low`.
* **Why it's inefficient:** Not wrong on the long side — a buy enters at `open + s` (ask) and exits at the bid, so no pad is owed and `bar_high - entry` is right. Shorts overstate MFE by exactly one spread, so `capture = net_r / sum(mfe_r)` reads **low on sells only**. Live `maliyet` lines give the scale (US30 2.0%, JPN225 4.7%, SpotBrent 4.8%, GER40 7.4% of risk — spread+commission), so roughly 1–4% of R per short, one-directional.
* **Recommended fix:** `fav = (bar_high - entry) if is_buy else (entry - (bar_low + float(trigger_pad[j])))`. `j` is already a parameter; `trigger_pad` is already in the closure.
* **Tradeoffs / Risks:** `capture` values go **up** (smaller denominator), so any `opt_summary.holdout.capture` already written is not comparable across the fix. Same stamp-vs-fresh trap the keep-line just paid for — date the change.
* **Expected impact estimate:** +1–4 percentage points of capture on short-heavy symbols. It is the only change that makes a US30 BUY-vs-SELL capture split legitimate.
* **Removal Safety:** Needs Verification (stored capture stamps)
* **Reuse Scope:** local file (`backtest.py`)
* **Disagreement:** the 07:50 entry "Python `simulate()` bar loop dominates search wall" judged `_mfe_tick` as "O(1) per bar — not a new bottleneck". That is correct about **CPU** and says nothing about the pad. Both hold.

* **Title:** `entry_blocks.attempts` now carries two different units in one column
* **Category:** Reliability (measurement integrity)
* **Severity:** High
* **Impact:** the missed-signal table both agents rank symbols with
* **Evidence:** Live DB read-only (`settings.entry_blocks`; `entry_blocks_since` = 1786905256.33 → **16.08 21:34:16**, a **226.2 h** window):

      US30       spread              attempts=11520  signals=110  ratio=104.7
      US30       risk_sembol_limiti  attempts= 7121  signals= 58  ratio=122.8
      US30       risk_ters_yon       attempts=  830  signals= 27  ratio= 30.7
      US30       bar_bosluk          attempts=    7  signals=  7  ratio=  1.0
      GER40      risk_ters_yon       attempts= 7995  signals=  9  ratio=888.3
      SpotBrent  risk_ters_yon       attempts=  772  signals= 37  ratio= 20.9

  Mechanism: `seans_disi` (`engine.py:2007`), `piyasa_kapali` (`:2020`) and `bar_bosluk` (`:2055`) clear the **whole** signal chain (`signal`, `signal_source`, `primary_signal`, `pending_bar_key`). On the next poll `_refresh_signals` has no fresh bar, so `state.signal` stays empty and `_tally_evaluate_refuse` returns early. Those three can therefore tally **at most once per bar**. Every other reason (`spread`, `risk_*`, `bar_doldu`, `sembol_halt`) leaves the signal standing and re-tallies each poll until the bar rolls.
* **Why it's inefficient:** `_tally_entry`'s own docstring defines `attempts` as persistence ("one refused M15 signal shows up as several hundred attempts — EURJPY produced 339 from a single sell"). That definition no longer holds for part of the table. The 22:13 missed-signal analysis used exactly this column. `bar_bosluk` at 7/7 today is the mechanism already visible in production; the diff adds `seans_disi` and `piyasa_kapali` to the same one-shot class (`bar_doldu` stays in the persistent class).
* **Recommended fix:** Do not reset the window — 226 h of series. Either publish a per-reason `unit: "bar" | "poll"` in `entry_blocks()` and hide `attempts` for the one-shot class, or compare on `signals` only (it is already distinct-episode). Naming the unit is cheaper than changing the counting.
* **Tradeoffs / Risks:** Resetting `entry_blocks_since` would make the two definitions one window and destroy the series. Do not.
* **Expected impact estimate:** Runtime 0. Measured distortion on US30 today spans 1600× (11520/7) to 16× (110/7) depending on which column is read.
* **Removal Safety:** Needs Verification (panel consumers)
* **Reuse Scope:** module (`engine.py`, panel block table)

* **Title:** `_merge()` does not carry `trade_mfes` — pooled `capture` is always null
* **Category:** Algorithm / Reliability
* **Severity:** Medium-High
* **Impact:** the `baseline` report block; every multi-segment total
* **Evidence:** `backtest.py:1197-1216` extends `trade_rs` and `trade_cost_rs` but not `trade_mfes`. `Result.capture` (`:86-93`) then sees `total <= 0.0` and returns `None`. `backtest.py:1453` `baseline = _merge(base_parts).as_dict(...)` → `capture: null`, always. The paths that matter still work: `validation` / `holdout` come from `measure()` → a single `simulate`, and `_holdout_costed` → `charged_holdout` (`holdout_cost.py:61-64`) is also a single `simulate`, so `opt_summary.holdout.capture` is real.
* **Why it's inefficient:** A field that is present and permanently empty, where `None` cannot be told apart from "no MFE recorded". It also breaks the AGENTS.md invariant *"Per-trade MFE is `Result.trade_mfes` (same length)"* for pooled results — the same class of silently-misread field the keep-line stamp just cost a day.
* **Recommended fix:** `total.trade_mfes.extend(r.trade_mfes)` in `_merge`. `trade_events` is not carried either; if that is deliberate, one comment line, otherwise the same fix.
* **Tradeoffs / Risks:** None. `capture` is not a score input and not an apply gate.
* **Expected impact estimate:** Negligible runtime; report correctness.
* **Removal Safety:** Safe
* **Reuse Scope:** local file (`backtest.py`)

* **Title:** The same charged holdout replay runs twice per kept symbol
* **Category:** CPU / Caching
* **Severity:** Medium
* **Impact:** search wall; MT5 lock time when a search shares the host with live
* **Evidence:** `reject_reason` → `_beats_incumbent` (`optimizer.py:1383`) → `_fresh_incumbent_holdout(cfg)` (`:1530`). Then the keep log at `:1140` calls `_incumbent_kept_tail(cfg)` → `_fresh_incumbent_holdout(cfg)` again (`:1402`). Same `cfg`, same `OPT_FIELDS`, no memo. Separately, the "hicbir aday kapidan gecmedi" path (`:1017`) paid **zero** replays before this diff and now pays one.
* **Why it's inefficient:** `_holdout_costed` is a full `charged_holdout`: `spread_cost_series` + `session_mask` + `flatten_mask` + `compute` + `simulate` over up to `max_bars`. Bars are usually free (`_bar_snap` hit), the simulate is not.
* **Recommended fix:** Run-scoped memo keyed on `(symbol, timeframe, strategy, params)` — the params must be in the key because `apply()` can mutate `cfg` inside the same run. Clear it beside `_bar_snap` (`:816`).
* **Tradeoffs / Risks:** A symbol-only key would serve a stale replay after an apply.
* **Expected impact estimate:** One extra full replay per kept symbol. **Measure, do not guess:** `opt_runs.elapsed_sec` before/after on the same symbol/TF/family set.
* **Removal Safety:** Safe (pure function, identical inputs)
* **Reuse Scope:** module (`optimizer.py`)

* **Title:** Keep-line replay can fetch bars outside the run snapshot under `timeframes=`
* **Category:** I/O / Concurrency
* **Severity:** Medium
* **Impact:** MT5 lock shared with the live engine; the window the "taze" number was measured on
* **Evidence:** `_bars_for_holdout` (`:1581-1599`) falls back to `self.client.bars(...)` when `_bar_snap[(symbol, timeframe)]` misses, and `_bar_snap` is only filled for the timeframes the sweep actually ran (`:747`). A run started with `timeframes=["M5"]` against a symbol whose live `cfg.timeframe` is M30 misses. Its own docstring forbids this: *"A second client.bars() mid-run can close a new bar and shift the window the candidate was scored on (AS3)."* The diff makes that path reachable on **every kept symbol**, not just the gate.
* **Why it's inefficient:** Two costs. The lock, shared with `_update_stop`; and a "taze test" figure measured on a different window than the candidate it is printed beside. Fresh is true; same-slice is not.
* **Recommended fix:** `_fresh_incumbent_holdout(cfg, allow_fetch=False)` from the log path, falling back to the stamp — the line already distinguishes `(damga …R, dd.mm)`, so it stays honest.
* **Tradeoffs / Risks:** TF-restricted runs print the stamp instead. Acceptable, because the line **says** it is a stamp.
* **Expected impact estimate:** Zero on an unrestricted run; one `client.bars(max_bars)` per kept symbol on a restricted one.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`optimizer.py`)

* **Title:** `state.entry_block` — four writers, zero readers — **Dead Code**
* **Category:** Dead Code
* **Severity:** Low
* **Impact:** maintenance surface; the field's meaning
* **Evidence:** The diff adds `engine.py:2007` (`seans_disi`), `:2020` (`piyasa_kapali`), `:2098` (`bar_doldu`); `:2055` (`bar_bosluk`) already existed. The field's only reader is `engine.py:958`, the ready-loop tally, which runs strictly after `_try_entry` — and all four of these paths `return False`, so the symbol never joins `ready`. `_try_entry` also resets the field to `""` at `:2304`, so nothing carries to a later cycle. `SymbolState.as_dict()` does not publish it, and no handler in `app.py` / `app.js` / `index.html` reads it (the `entry_blocks` counters are a different thing).
* **Why it's inefficient:** Write-only state invites the next reader to assume the panel shows it. `sembol_halt` (`:2072`) is the inverse — it tallies but sets nothing — so the field is now maintained on 4 of 5 gates and read on none.
* **Recommended fix:** Pick an end, not the middle: delete all four writes (the tally already records the reason), or publish the field in `as_dict()`, show it, and set it on `sembol_halt` too.
* **Tradeoffs / Risks:** Deleting changes no behaviour — the single reader is unreachable from these paths.
* **Expected impact estimate:** Runtime 0. Readability.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`engine.py`)

* **Title:** `timeframes` and `strategies` validation blocks are line-for-line twins — **Reuse Opportunity**
* **Category:** Maintainability
* **Severity:** Low
* **Impact:** a third axis copies it a third time
* **Evidence:** `optimizer.py:294-311` (timeframes) and `:314-331` (families): ~18 lines each, differing only in the whitelist (`TIMEFRAMES` / `STRATEGIES`), the Turkish noun, and the field name. Same log line, same all-dropped 409, same `*_override` shape.
* **Recommended fix:** `_one_off_subset(requested, allowed, noun)` returning `(kept_or_None, error_or_None)`. Two call sites.
* **Tradeoffs / Risks:** The Turkish operator-facing strings must survive verbatim; pass the noun, do not rebuild the sentence.
* **Expected impact estimate:** ~30 lines; closes the drift risk.
* **Removal Safety:** Safe
* **Reuse Scope:** module (`optimizer.py`)

### 3) Quick Wins (Do First)

1. `total.trade_mfes.extend(r.trade_mfes)` in `_merge` (C-3) — one line, no risk.
2. Pad the short side in `_mfe_tick` (C-2) — one line, but it invalidates stored `capture` stamps; date it.
3. Run-scoped memo for `_fresh_incumbent_holdout` (C-4).
4. Delete the four dead `state.entry_block` writes (C-6).

### 4) Deeper Optimizations (Do Next)

* Publish a per-reason unit on `entry_blocks()` and compare on `signals` (C-1). **Do not reset the window.**
* `allow_fetch=False` on the keep-line replay (C-5).
* Extract `_one_off_subset` (C-7) before a third axis lands.

### 5) Validation Plan

* **C-2:** fail-first — one synthetic short with a known `trigger_pad`, asserting MFE is `entry - (low + pad)`; a long on the same bar asserting no pad. Then re-run `test_simulate_records_per_trade_mfe.py`.
* **C-3:** two-segment `_merge`, assert `len(total.trade_mfes) == len(total.trade_rs)` and `capture is not None`.
* **C-1:** after the diff loads, at the first session close assert `seans_disi` has `attempts == signals`. `bar_bosluk` at 7/7 today is the expected shape, not an anomaly.
* **C-4:** `opt_runs.elapsed_sec` before/after on the same symbol/TF/family set.
* **C-5:** run with `timeframes=["M5"]` against a symbol whose live TF is not M5; `client.bars` call count from the log path must be 0.
* Standard gate: `pytest tests/<touched>.py -q --tb=short` + `ruff check micofx/`.

### 6) Optimized Code / Patch (proposals only — not applied)

```python
# backtest.py _merge — C-3
total.trade_mfes.extend(r.trade_mfes)

# backtest.py _mfe_tick — C-2: a short covers on the ask, same as _mae_tick
def _mfe_tick(is_buy, entry, mfe_px, j):
    bar_high, bar_low = high[j], low[j]
    fav = ((bar_high - entry) if is_buy
           else (entry - (bar_low + float(trigger_pad[j]))))
    return fav if fav > mfe_px else mfe_px

# optimizer.py — C-4: one replay per (symbol, tf, strategy, params) per run
key = (cfg.symbol, cfg.timeframe, cfg.strategy,
       tuple(sorted((k, getattr(cfg, k)) for k in OPT_FIELDS if hasattr(cfg, k))))
# self._incumbent_memo, cleared beside _bar_snap at optimizer.py:816
```

---

### SECURITY AUDIT (Claude): same working tree — **raises the 07:50 rating to Medium**

**Risk Assessment:** Medium (the 07:50 pass rated this Low; the disagreement is one finding, below)

#### **Findings:**

* **Log injection — forged lines in the audit trail** (Severity: Medium)
* **Location:** `micofx/optimizer.py:319-323` (new, families) and `:302-305` (pre-existing, timeframes); writer `micofx/logbus.py:96`
* **The Exploit:** `POST /api/opt/run` with `{"strategies": ["x\n2026-08-26 07:00:00 TRADE  [US30] #999 BUY 1.0 lot @ ... kar=+500"]}`. The value is not in `STRATEGIES`, so it lands in `dropped_fam` and is interpolated straight into `LOG.emit` via `', '.join(dropped_fam)`. `_write_file` does `fh.write(f"{stamp} {level:6} {sym}{entry['message']}\n")` — no escaping — so an embedded newline produces a complete, well-formed extra line. In this repo the log **is** the audit trail: scale-out P&L, autopsy R and the keep-line were all read from it on the night of 25.08. `logbus._rotate` cuts on a line boundary, so a forged line survives rotation.
* **The Fix:** One choke point in `LOG.emit` — `message = str(message).replace("\r", " ").replace("\n", " ")` — plus `', '.join(dropped_fam[:8])` at the call sites to bound the line. **Not applied.**
* **Why this is not Low:** the 07:50 finding treats `strategies` purely as an unbounded-list issue and concludes "names are `str()`'d then filtered". The filtering protects the *sweep*; it does not protect the *log*, because the rejected names are exactly what gets printed.

* **`/api/opt/run` outside `_CRITICAL_MUTATIONS`** (Severity: Low — agrees with 07:50, restated for the fix)
* **Location:** `micofx/web/app.py:569-577`
* **The Exploit:** Session-cookie only, no `Origin` check. `HttpOnly` + `SameSite=Strict` means a real cross-site POST will not carry the cookie in a current browser, which is why this stays Low. But the repo already decided the cookie alone was insufficient for `/api/bot/panic` (AS1), and this endpoint now accepts a new field that reaches the log.
* **The Fix:** add `"/api/opt/run"` to `_CRITICAL_MUTATIONS`; the panel already posts same-origin. **Not applied.**

#### **Observations:**

* No hardcoded credentials, keys or tokens in the diff. Confirms 07:50.
* `OptRun` is `_ForbidModel`; extra fields rejected. `_FAMILIES.get` (`strategy.py:406`, `:1243`) warns once on an unknown name rather than raising — a leftover `alpha_trend` / `mavilim` in the DB fails closed. Confirms 07:50.
* `strategies` has no length bound, so a 10k-element list becomes one log line. Not a DoS; an unbounded line.
* `capture` remains read-only on holdout dicts; `_slice_ok` / `_is_improvement` untouched.

---

### Reverse engineering — live readings (read-only, 26.08 07:48)

Not code claims. Read from the running system.

* **Process:** PID 10424, started **26.08 01:38:46**, `127.0.0.1:8900` LISTENING. HEAD `0c33d72` was committed after that start, so the live process is **pre-HEAD** and certainly does not carry the uncommitted diff. Any "live behaves like this" claim about the diff is currently **unverifiable**.
* **The keep-line has never fired.** Searching `logs/micofx.log` for `taze test` / `damga` returns three lines — all three are `"broker saati ... broker damgasinda, Windows DST sapmasi"` (lines 920, 922, 923). `_incumbent_kept_tail` has not emitted once in this log. The 25.08 keep-line fix is **unproven in production**; first thing to check on the next search.
* **Counter window:** `entry_blocks_since` = 1786905256.33 → **16.08 21:34:16**, 226.2 h. All C-1 ratios come from that window.
* **13 families:** the panel reports 13 and post-diff `STRATEGIES` is 13, so the live DB `opt_params.strategies` already dropped `alpha_trend` / `mavilim`. The code constant follows the DB rather than leading it.
* **Book at 07:48:** JPN225 #366201717 still open (04:15 entry, SL fixed at 66139.73815 since 06:00, logged peak 4.92×ATR); SpotBrent #366298271 BUY 0.12 at 07:15; GER40 #366302421 SELL 0.8 at 07:30. Overnight closes: GER40 −27.53, NAS100 +11.04, NAS100 −15.36.

---

# 26.08 08:40 UTC+3 — Cursor clean scan (this chat)

Read-only. Trust the closed ledger: do **not** re-open fill-verify sleep-on-cycle,
RAM-only `original_sl`, supervisor-inside-`_cycle`, full `symbol_payload` on
`/api/state`, unclamped scale-out, duplicated trail math, or unchunked
`copy_rates`. Those landed on disk. Live PID (started 26.08 01:38) may still
be pre-diff. **No restart while opens exist. No code applied this pass.**

`micofx/exits.py` is **untracked**. Product diff vs HEAD: `micofx/` + tests +
AGENTS/MASTER/OPTIMIZATIONS (~32 files, +1382/−591). Suite claimed green on
the other page (147 targeted / 2492 full); this pass did not re-run pytest.

AGENTS.md: already dense enough (venv, live-owns-DB, no sidecar MT5, yellow/red
gates, overlay_stop, 13 families, gotchas). Do **not** rewrite it here. Only
gap worth a later one-liner: `exits.py` is untracked so a clone-from-HEAD
misses the shared stop helper until commit.

Do **not** treat as software TODOs: trail_step PATCH, `reverse_on_signal`,
US30 close, ichimoku apply, `capture` into score, flatten, restart-with-opens.

---

### 1) Optimization Summary

* Health is **good for a ~6-symbol ATR book**. The 07:50/08:00 hot-path items
  landed. Remaining cost is the **shared MT5 `RLock`** (web `snapshot`,
  supervisor 14d, fill-verify peeks, chunked bar fetch) plus full
  `IndicatorCache.compute()` on every closed bar. Search wall is still CPython
  `simulate()` — profile before Numba.
* Top 3 highest-impact remaining:
  1. `day_stats()` still sits in `snapshot()` — 5s cache, miss takes
     `history_deals_get` on the same lock as trail/flatten.
  2. Incremental indicators on bar close (M5 especially) — identity tests
     required; **likely** until `compute()` share of `last_cycle_ms` is
     measured.
  3. Landing leftovers: supervisor 14d and fill-verify sleeps no longer block
     `_cycle`, but both still **contend** the MT5 lock from other threads.
* Biggest risk if nothing else changes: a mid-session `/api/app/restart` (or
  `gece_restart` if flatten failed and a ticket is still open at 00:00)
  first-sights pre-`note_fill` tickets and poisons autopsy R until they die.
  Disk persist does not retro-stamp tickets already open.

---

### 2) Findings (Prioritized)

* **Title:** `day_stats()` still runs inside every `snapshot()`
* **Category:** I/O / Caching / DB (MT5 history)
* **Severity:** Medium
* **Impact:** panel-poll lock time; cycle jitter when the 5s cache misses
* **Evidence:** `Engine.snapshot()` always unpacks `self.day_stats()`
  (`engine.py:4222-4223`). Cache is 5s (`:3971-3974`) then
  `client.deals_since(day_start)` + `merge_round_trips` (`:3985`) under
  `MT5Client._lock` (`mt5client.py:1053`). Panel `refresh()` hits `/api/state`
  every 3s (`app.js:2325`). ~2 of 3 polls hit; every miss is a reporting query
  on the web thread. `_symbol_daily_halt` also reads `day_stats()`.
* **Why it’s inefficient:** Deal history is not needed to trail or enter. The
  panel already has `symbols_sig`; this is the leftover reporting query on the
  3s path.
* **Recommended fix:** Serve day totals on `/api/day` (or stamp + refetch like
  symbols). Keep the 5s cache. Cycle halt path can call `day_stats()` directly,
  not via snapshot.
* **Tradeoffs / Risks:** UI must tolerate ~5s stale day cards (already does).
* **Expected impact estimate:** Medium lock-wait on miss; Low average.
  **Likely** until `deals_since` wait is counted.
* **Removal Safety:** Needs Verification (panel `renderDayTable` / halt banner)
* **Reuse Scope:** service-wide

* **Title:** Full `IndicatorCache` + `compute()` on every new closed bar
* **Category:** CPU / Algorithm
* **Severity:** Medium (live, M5) / Low (M30)
* **Impact:** cycle CPU on bar roll; not the old 45s refetch myth
* **Evidence:** Same stamp → return False (`engine.py:2420-2421`). New bar →
  `IndicatorCache(bars.high, …)` + `compute(cache, params)` (`:2424-2426`).
  Cache memos inside one object (`strategy.py:142-178`) then is discarded.
  Fetch still pulls `required_bars` (400–1680+) on due / 900s integrity.
* **Why it’s inefficient:** Live only needs the last closed bar’s signal.
  Rebuilding T3/stoch/ATR/ADX/HTF over the whole window on every M5 close
  (12/hour × N symbols) is honest but heavier than an append-one-bar warm start.
* **Recommended fix:** Append-one-bar only with **bit-identical** last-signal
  tests vs full `compute()`. Keep 900s integrity. Do **not** re-enable
  `_STALE_BAR_REFRESH`.
* **Tradeoffs / Risks:** Drift vs walk-forward = live/paper desync. Highest
  correctness cost in the remaining list.
* **Expected impact estimate:** Medium on M5; Low on M30. **Likely** — profile
  `compute()` share of `last_cycle_ms` first.
* **Removal Safety:** Needs Verification (signal identity)
* **Reuse Scope:** module (`engine.py`, `strategy.py`)

* **Title:** Supervisor 14d and fill-verify still contend the live MT5 lock
* **Category:** Concurrency
* **Severity:** Medium (contention) — **not** the closed “blocks `_cycle`” bug
* **Impact:** trail/modify latency while a side thread holds `_lock`
* **Evidence:** `_kick_supervisor_review` (`engine.py:983-1004`) daemon +
  non-blocking gate. `review()` → `deals_since` 14d (`supervisor.py:494`) still
  takes `with self._lock`. Fill-verify: first `_look()` is sync; if empty and
  `defer=True`, engine returns pending (`mt5client.py:1541-1543`); side thread
  then sleeps 2.1s **between** `_look()` calls that each take the lock
  (`:1515-1517`, `:1545-1547`). Inflight still blocks a second send (intended).
* **Why it’s inefficient:** Cycle is free of the sleep; the lock is not. A 14d
  `history_deals_get` can stall `modify_position` / `tick` for other symbols.
* **Recommended fix:** Measure lock-hold histograms first. If 14d is the
  spike, snapshot deals on the supervisor thread with a timeout / chunk, or
  reuse the day’s `day_stats` merge and only extend the lookback when due.
  Do **not** delete verifier sleeps.
* **Tradeoffs / Risks:** Quarantine lag already 120s. Weaker verify = duplicate
  entries (fail-closed is the product rule).
* **Expected impact estimate:** Medium on review ticks / ambiguous fills; Low
  on quiet polls. **Likely**.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`engine.py`, `mt5client.py`, `supervisor.py`)

* **Title:** `_ACCOUNT_TTL` is 1s; panel poll is 3s
* **Category:** I/O / Caching
* **Severity:** Low–Medium
* **Impact:** extra `account_info` IPC on every `/api/state`
* **Evidence:** `refresh_account` TTL = 1.0s (`engine.py:38`, `:3833-3836`).
  `snapshot()` always calls it (`:4192`). Panel delay 3000ms (`app.js:2325`).
  Every visible poll therefore misses the TTL unless a cycle refreshed <1s ago.
* **Why it’s inefficient:** Positions already reuse `_panel_positions` when the
  cycle book is fresh. Account does not get the same courtesy.
* **Recommended fix:** Raise TTL to ~2s, or reuse cycle account when
  `_cycle_book_is_fresh()`. Keep `force=True` after a fill (`engine.py:972`).
* **Tradeoffs / Risks:** Equity/margin on the panel can lag ~2s (already the
  cycle interval). Daily brake must keep using the cycle’s forced refresh.
* **Expected impact estimate:** Low (account_info is cheap vs deals_since);
  still one lock acquire per poll that is easy to drop.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`engine.py`)

* **Title:** Python `simulate()` bar loop still dominates search wall
* **Category:** Algorithm / CPU
* **Severity:** Medium (opt) / Low (live)
* **Impact:** search duration; cost of any `OPT_FIELDS` expansion
* **Evidence:** Sequential list loop (`backtest.py:526+`). No Numba. Shared
  `overlay_stop` (`exits.py`) is per-bar Python. `_mfe_tick` is O(1) per bar
  (correctness, not CPU).
* **Why it’s inefficient:** Branchy exits resist naive vectorization; O(bars ×
  open trades) in CPython.
* **Recommended fix:** `py-spy` one GER40 `walk_forward` in
  `C:\MicoFX-venv\Scripts\python.exe` **before** Numba. If the loop is >70% of
  worker time, compile trail/exit only. Do **not** expand `OPT_FIELDS` until
  paid. Do **not** put `capture` into `score()`.
* **Tradeoffs / Risks:** Bit-identical R vs live is a product invariant.
* **Expected impact estimate:** Medium–High on search (qualitative until
  profiled); none on the ~2s live cycle.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`backtest.py`, `exits.py`)

* **Title:** `entry_blocks.attempts` still mixes poll persistence and one-shot bar gates
* **Category:** Reliability (measurement) — **Reuse Opportunity** (panel)
* **Severity:** Medium (verdict risk, not latency)
* **Impact:** missed-signal ranking if someone sorts on `attempts`
* **Evidence:** `entry_blocks()` already splits `signals`/`blocks` vs
  `attempts`/`retries` (`engine.py:1480-1516`) and the docstring says
  `signals` is the comparable count. Panel `loadBlocks` still prints
  `r.signals / r.attempts deneme` (`app.js:386`) and ignores `retries`.
  Evaluate-refuse for `seans_disi` / `piyasa_kapali` / `bar_bosluk` clears the
  signal chain (`engine.py:2168-2187`, `:2222`) so those tally **once per bar**.
  `spread` / `risk_*` leave the signal standing and re-tally each poll.
  Window `entry_blocks_since` ≈ 16.08 21:34 (do **not** reset).
* **Why it’s inefficient:** Two units in one column. API already has the split;
  the UI does not use it.
* **Recommended fix:** Show `signals` + `blocks`; hide or label `attempts` as
  poll-retries; optional `unit: "bar"|"poll"` later. Compare on `signals`.
* **Tradeoffs / Risks:** Resetting the 226h series would destroy history. Do not.
* **Expected impact estimate:** Runtime 0. Ranking error if `attempts` is used.
* **Removal Safety:** Needs Verification (panel consumers)
* **Reuse Scope:** module (panel; API already ok)

* **Title:** Panel full `innerHTML` rebuild on every 3s poll
* **Category:** Frontend
* **Severity:** Low
* **Impact:** browser main thread
* **Evidence:** `refresh()` (`app.js:2287-2309`) always `renderTop`; on panel
  tab also cards/capacity/positions/day. Logs use `esc()` (`:2276-2277`).
  Cards patch `.scard-live` innerHTML every poll (`:1228-1240`) even when
  values are unchanged.
* **Why it’s inefficient:** 6 cards × 0.3 Hz is fine; 20 symbols is not free.
* **Recommended fix:** Patch text nodes; rebuild cards only when `symbols_sig`
  changes (already the fetch gate).
* **Tradeoffs / Risks:** Easy to miss a field; DOM tests are thin.
* **Expected impact estimate:** Low on this book; Medium if the book grows.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`app.js`)

* **Title:** TRADE log on every successful SL modify
* **Category:** I/O
* **Severity:** Low
* **Impact:** disk, rotation, log-tab DOM
* **Evidence:** `_update_stop` (`engine.py:3709-3711`) emits TRADE with ticket
  + new SL + `xATR`. Scale-out and broker-exit TRADE lines are separate
  (`:3432`).
* **Why it’s inefficient:** M30 trail is fine; a choppy M5 book is chatter.
* **Recommended fix:** Coalesce trail logs (ticket + SL + bar time); keep first
  BE lock and scale-out as TRADE.
* **Tradeoffs / Risks:** Intra-bar trail autopsy gets coarser.
* **Expected impact estimate:** Low
* **Removal Safety:** Likely Safe
* **Reuse Scope:** module

* **Title:** Per-ticket `tick` + `min_stop_distance` in `_update_stop`
* **Category:** I/O / Algorithm
* **Severity:** Low
* **Impact:** MT5 IPC × open tickets
* **Evidence:** `_update_stop` (`engine.py:3568`, `:3612`) fresh tick +
  `min_stop_distance` per ticket. Structure/hybrid can scan swings
  (`:3639-3650`). Trail already latched per closed bar via `_stop_bar`.
* **Why it’s inefficient:** Cycle already has a tick per symbol.
* **Recommended fix:** Reuse cycle tick; cache swing series on bar close; keep
  `trail_min_step` gate.
* **Tradeoffs / Risks:** Stale min_stop if freeze_level jumps intra-bar (rare).
* **Expected impact estimate:** Low on current ATR-only book. **Likely**.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** module

* **Title:** `gece_restart` is unconditional at 00:00 vs leftover first-sight
* **Category:** Reliability
* **Severity:** Medium (if flatten failed) / Low (by design when flat)
* **Impact:** autopsy R after a midnight load with a surviving ticket
* **Evidence:** `gece_restart.py:13-19` — deliberately no health check; midnight
  is outside every session (earliest open 01:00). `track()` still
  `setdefault("original_sl", live sl)` for tickets missing `open_original_sl`
  (`execution.py:321-328`). Persist only runs from `note_fill` of **this**
  process. Tickets opened on the pre-diff PID were never stamped.
* **Why it’s inefficient:** N/A CPU. The 00:00 load is the next time disk code
  becomes live — and the next time pre-patch tickets can be first-sighted.
* **Recommended fix:** Do not add a flatten-all. Optional: skip restart if
  `positions_get` non-empty (changes the 22.08-blind-bot contract — operator
  call). Until then: know that 00:00 loads this tree; pre-patch opens poison R.
* **Tradeoffs / Risks:** Skipping restart re-opens the “process up, terminal
  blind” incident the script exists for.
* **Expected impact estimate:** High for those tickets’ autopsy; zero live PnL.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide

* **Title:** `/api/opt/run` still outside `_CRITICAL_MUTATIONS`
* **Category:** Security-impacting / Reliability
* **Severity:** Low
* **Impact:** CSRF class on an authenticated session (search + default
  `apply_best=True`)
* **Evidence:** Set is panic/start/stop/shutdown/restart/close-all/lock/holdout
  (`web/app.py:569-575`). `POST /api/opt/run` (`:2146`) is session-cookie
  authenticated, Origin-unchecked. Cookie is HttpOnly SameSite=**Strict**
  (`:585`). Classic cross-site POST from a foreign origin should not send it.
* **Why it’s inefficient:** Defense-in-depth hole, not a measured bottleneck.
* **Recommended fix:** Add `/api/opt/run` (and maybe `/api/opt/cancel`) to the
  set. Optional `max_length` on `strategies` (same class as `timeframes`).
* **Tradeoffs / Risks:** Night/automation callers must send Origin. Panel
  already does.
* **Expected impact estimate:** n/a perf; Low residual CSRF.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`web/app.py`)

* **Title:** `state.entry_block` writes on evaluate-refuse are RAM-only UI dead weight
* **Category:** Maintainability — **Dead Code** (panel) / live state still used by engine
* **Severity:** Low
* **Impact:** none measurable; two sources of “why didn’t it enter”
* **Evidence:** `_evaluate` sets `state.entry_block` for seans/piyasa/bar_bosluk
  (`engine.py:2174+`) then clears the signal. Panel missed-signal table reads
  `GET /api/analysis/entry-blocks`, not `states[].entry_block`. Snapshot
  `_states_view` still serializes it every 3s.
* **Why it’s inefficient:** Duplicate explanation surface. Not a hot loop.
* **Recommended fix:** Keep engine field for TRADE/debug; do not build a second
  panel column. If snapshot JSON is trimmed later, this field is a candidate.
* **Tradeoffs / Risks:** Removing the attribute breaks anything grepping state.
* **Expected impact estimate:** Low (JSON bytes).
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module

* **Title:** `el(..., {html: ...})` sink exists; no current callers
* **Category:** Frontend / Security — **Over-Abstracted Code**
* **Severity:** Low (latent)
* **Impact:** next caller can skip `esc()`
* **Evidence:** `el()` (`app.js:154`) assigns `innerHTML` when `k === "html"`.
  Grep finds **no** `html:` call sites. Comment at `:79-86` still claims
  “verbatim elsewhere” — mostly stale (logs/`scard-live` use `esc()`). Residual
  interpolations: `renderTop` `val` (`:426-427`) from `num`/`signed`/literals;
  AI cards `c.val` (`:1672-1675`) from numbers/times.
* **Why it’s inefficient:** A helper that is unused but XSS-shaped.
* **Recommended fix:** Delete the `html` branch, or require a tagged
  safe-HTML type. Not this audit.
* **Tradeoffs / Risks:** None if unused.
* **Expected impact estimate:** n/a
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`app.js`)

* **Title:** Untracked `micofx/exits.py` vs HEAD
* **Category:** Maintainability / Build
* **Severity:** Low (until commit)
* **Impact:** clone-from-HEAD has no `overlay_stop`; live/paper drift returns
* **Evidence:** `git status --short` → `?? micofx/exits.py`. `engine.py` and
  `backtest.py` already import it. HEAD `0c33d72` does not contain the file.
* **Why it’s inefficient:** Shared helper is the 08:00 landing; it is not in
  the last commit.
* **Recommended fix:** Include it when the operator asks to commit. Do not
  commit from this scan.
* **Tradeoffs / Risks:** None
* **Expected impact estimate:** n/a runtime
* **Removal Safety:** n/a
* **Reuse Scope:** repo

* **Title:** Bar fetch still uses the live client (chunks only)
* **Category:** Concurrency / I/O
* **Severity:** Low when opt idle / High during a search (same as closed ledger)
* **Impact:** cycle jitter during `/api/opt/run`
* **Evidence:** `_BAR_FETCH_CHUNK=2500`; lock released between chunks
  (`mt5client.py:916-931`). Optimizer planner still calls `self.client.bars`.
  No second `initialize()`.
* **Why it’s inefficient:** One connection is required; search is still a
  history bus on the trading lock. Chunks only bound **hold duration**, not
  total copy_rates volume.
* **Recommended fix:** Prefetch once, detach workers. Use `strategies=` on a
  **flat** book when asked. Never a second terminal bind.
* **Tradeoffs / Risks:** Snapshot age vs live quote.
* **Expected impact estimate:** High jitter only while a search runs (opt is
  idle now — do not start one).
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide
* **Classification:** not a re-open of “lock held across 10k rates” — that
  landed. This is the leftover architecture.

---

### 3) Quick Wins (Do First)

1. Add `/api/opt/run` to `_CRITICAL_MUTATIONS` (Origin check; no behaviour
   change for the panel).
2. Reuse cycle account in `snapshot()` when `_cycle_book_is_fresh()` / raise
   `_ACCOUNT_TTL` to ~2s.
3. Panel: print `signals` + `blocks`; stop implying `attempts` is the same
   unit. Do **not** reset `entry_blocks_since`.
4. Include `micofx/exits.py` in the next operator-requested commit.
5. Do **not** restart, search, holdout-capture, or flatten to “load the scan”.

Already done (not wins): persist `original_sl`; deferred fill-verify; supervisor
off `_cycle`; `symbols_sig`; scale-out clamp; `overlay_stop`; chunked bars;
short MFE pad; `_merge` mfes; log CR/LF flatten; incumbent memo.

---

### 4) Deeper Optimizations (Do Next)

1. `day_stats` off the 3s snapshot path (keep 5s cache / halt caller).
2. Incremental `IndicatorCache` — identity tests vs full `compute()`.
3. Measure MT5 lock-hold (supervisor 14d vs verify peeks vs `account_info`)
   before more thread splits.
4. Optimizer: prefetch bars once; CPU-only workers; optional `strategies=`
   when **flat**.
5. Numba/Cython `simulate` inner loop **only after** a worker profile;
   required before any 3× grid.
6. Patch panel text nodes instead of innerHTML every poll.

Do **not:** micro-optimize `secrets.compare_digest`; unroll ATR; re-enable
`_STALE_BAR_REFRESH`; put `capture` into the walk-forward score; reintroduce
`tp_atr_mult` / `partial_tp_r` / `max_bars_in_trade`; resurrect `alpha_trend`
/ `mavilim`; PATCH `trail_step`; enable `reverse_on_signal`.

---

### 5) Validation Plan

* **Benchmarks:** `engine.last_cycle_ms` p50/p95 from `/api/state` over 15 min
  quiet vs 15 min panel-open vs (only if asked) opt running. Count
  `copy_rates` / `positions_get` / `history_deals_get` / `account_info` via a
  thin counter on `MT5Client` (measure first; do not log every call).
* **Profiling:** `py-spy` on the live PID **read-only** (no `mt5.shutdown`).
  Separate GER40 `walk_forward` in `C:\MicoFX-venv\Scripts\python.exe`.
* **Metrics before/after:** cycle_ms, MT5 lock-acquire time, `/api/state` JSON
  bytes, `deals_since` calls/min, panel `refresh` duration, first post-load
  trail-win autopsy (`r_realised ≠ 1.000`, cash R within 2%).
* **Correctness (must stay green):** trail/BE identity suite, `test_core.py`,
  `test_scale_out_once.py`, fill-verify / defer tests, `test_simulate_records_per_trade_mfe.py`,
  `test_keep_log_does_not_quote_a_stale_stamp.py`, `test_opt_run_can_restrict_families.py`,
  `test_retired_indicators_stay_gone.py`. Incremental indicators need
  “full vs append identical last signal”.
* **Do not** validate with a second MT5 bind, a sidecar sqlite writer, or
  `/api/app/restart` while opens exist.

---

### 6) Optimized Code / Patch (proposals only — not applied)

**A. Origin-gate opt run**

```python
_CRITICAL_MUTATIONS = frozenset({
    "/api/bot/panic", "/api/bot/start", "/api/bot/stop",
    "/api/app/shutdown", "/api/app/restart",
    "/api/positions-close-all",
    "/api/account-lock",
    "/api/holdout/capture",
    "/api/opt/run",
})
```

**B. Snapshot reuses cycle account**

```python
def snapshot(self) -> dict[str, Any]:
    account = (self._account if self._cycle_book_is_fresh() and self._account
               else self.refresh_account())
    ...
```

**C. Day totals off the 3s payload (sketch)**

`/api/state` keeps `day.pnl_pct` / `floating` from `DailyGuard` (already in
RAM). `day.symbols` / win-loss table loads from `/api/day` with the existing
5s `day_stats()` cache.

**D. Incremental cache:** not sketched. Requires identity tests first; a wrong
append is a live/paper desync.

What must not change: forming-bar drop, buy∧sell→neither, fail-closed
duplicates, live↔paper `overlay_stop` identity, score formula, `capture` as a
visible column only.

---

### ### SECURITY AUDIT: working tree vs HEAD `0c33d72`

**Risk Assessment:** Low

Uncommitted change is persist/defer/lock-chunk/UI-split plus holdout cleanup
(`exits.py` untracked; log CR/LF flatten; `open_original_sl` in sqlite
settings). No new public bind, no SQL concatenation, no secrets, no
`subprocess` change (`gece_restart` netstat/stop is pre-existing). Session
cookie remains HttpOnly SameSite=Strict. Live process may not be running this
tree.

#### **Findings:**

* **Opt run not Origin-checked** (Severity: Low)
* **Location:** `micofx/web/app.py:569-575`, `:2146`
* **The Exploit:** A session-holding browser that also visits an attacker page
  would need the cookie to be sent cross-site. SameSite=Strict blocks that for
  classic CSRF. Residual: non-browser clients with a stolen cookie, or a
  same-site confusion on `127.0.0.1`. Body can start a search with
  `apply_best=True` (pre-existing default) and an unbounded `strategies` list
  (filtered to `STRATEGIES`; unknown → drop / 409).
* **The Fix:** Add `/api/opt/run` to `_CRITICAL_MUTATIONS`. Optional list
  `max_length`. Do not apply in this audit.

* **XSS helper still accepts raw `html`** (Severity: Low / latent)
* **Location:** `micofx/web/static/app.js:154` (`k === "html"`); comment `:79-86`
* **The Exploit:** No current caller. A future `el("div", {html: user})` bypasses
  `esc()`. Token sits in a `<meta>` on the same page (`:82-83`). Remaining
  interpolations (`renderTop` `val`, AI `c.val`) are `num`/`signed`/literals,
  not broker comments. Logs and symbol cards use `esc()`. `group` CSS class is
  enum-validated server-side (`_ENUM_FIELDS`).
* **The Fix:** Remove the `html` branch. Do not apply in this audit.

* **`open_original_sl` in settings JSON** (Severity: Low / none)
* **Location:** `micofx/execution.py:243-253`
* **The Exploit:** Ticket ids + stop prices, not credentials. Same sqlite as
  the rest of the bot. No new exposure vs other `set_setting` blobs.
* **The Fix:** None. Prune on live-set (already).

* **Supervisor / verify daemon vs engine** (Severity: Low — race class, not RCE)
* **Location:** `engine.py:983-1004`, `mt5client.py:1515-1547`
* **The Exploit:** Not remote. Two threads take `RLock` (safe). Fail-closed
  inflight is the duplicate-entry control. Risk is missed trail during a 14d
  history call, not privilege escalation.
* **The Fix:** Measure; do not drop the gate.

#### **Observations:**

* Log newline injection from family names / messages is **closed** at
  `logbus.emit` (`\r`/`\n` → space). Do not re-open.
* `apply_best` still defaults `True` on `OptRun` — same privilege as HEAD.
* No hardcoded API keys/passwords in the product diff. `api_token` is still
  generated via `secrets.token_urlsafe(24)` when unset.
* `graft/` remains stale sourcedump (agent-context cost, not a vuln).
* AGENTS.md rewrite: skip. Constraints are already must/must-not. Density
  issue is `exits.py` untracked, which a commit fixes.

---

# 26.08 09:15 UTC+3 — remaining-opens landing

Independent remaining-opens audit (plus Claude event in `cursor/FOR_CLAUDE.md`).
**No restart.** Live PID still pre-diff while opens exist.

Landed: snapshot `day_stats(fetch=False)` + cycle warm; `_panel_capacity` 3s;
`margin_for` 5s; panel `viewPulse`; Origin on every mutation.

Measured won't-do: incremental cache (2.57ms/1680), Numba simulate (6.53ms/1680),
TRADE-per-SL (already once/bar via `_stop_bar`).

Leftover: 900s integrity full `required_bars` fetch (chunked, no compute).

---

## 26.08 ~09:52 — Claude derin tarama (SCAN-1)

Kapsam: canlı ağaç `micofx/`, `tests/`, `micofx/web/static/`,
`config/defaults.json`. `graft/` hariç. Üstteki **kapalı defter** esas
alındı; oradaki maddeler yeniden açılmadı.

Canlı PID **01:38** yüklemesinde; diskteki her şey **restart'a kadar
canlı değil**. Ölçemediğim yerde **"muhtemel"** yazdım ve neyin
ölçülmesi gerektiğini söyledim. Kanıtsız mikro-optimizasyon yok.

---

### 1) Optimizasyon Özeti

**Sağlık: iyi.** Gecenin landing'leri (capacity TTL, day_stats TTL,
symbols_sig, parçalı bar çekimi, viewPulse) `/api/state` yolundaki MT5
kilit baskısını gerçekten düşürmüş. Bu taramada **yeni bir sıcak döngü
bulamadım**.

Bulduğum üç şey **bugünün darboğazı değil, yarınınki**:

1. `settings` tablosundaki üç JSON blobu **tam yeniden yazılıyor**;
   halka tavanında yazma başına **~1,1 MB**'a çıkıyor (bugün 77 KB).
2. `_CRITICAL_MUTATIONS` **ölü sabit** — hem çöp hem yanıltıcı.
3. `Engine.__new__` fikstür çürümesi (52 dosya) — bugün **iki kez**
   regresyon taklidi yaptı.

**Değişmezse en büyük risk:** kırmızının anlamını yitirmesi. Süitte
fikstür çürümesi, panelde `left_on_table_r` — ikisi de "sürekli yanan
uyarı". Gerçek bir arıza bunların arasında kaybolur. Bu, CPU'dan pahalı.

---

### 2) Bulgular (öncelikli)

#### O-1 — `trade_autopsies` tam blob yeniden yazımı

* **Kategori:** I/O ölçeklenmesi · **Önem:** Orta (bugün Düşük)
* **Etki:** Her kapanışta tüm otopsi defteri tek JSON olarak sqlite'a
  yazılıyor.
* **Kanıt:** `engine.py:1659` `set_setting("trade_autopsies", rows)`;
  `engine.py:90` `TRADE_AUTOPSY_LIMIT = 2000`. Ölçüm (canlı db,
  salt-okunur): **138 satır = 77.283 bayt → ~560 bayt/satır**.
* **Neden:** Tavanda **2000 × 560 B ≈ 1,1 MB**, tek satır eklemek için.
  Günde ~40 kapanışla tavan **~50 günde** dolar.
* **Önerilen düzeltme (öneri):** Ya ayrı bir `autopsies` tablosu +
  `INSERT` + eski satır budama, ya da tavanı gerçekten okunan pencereye
  indir. Panel zaten son N satırı gösteriyor.
* **Ödünç:** Ayrı tablo = şema göçü + `Store` API genişlemesi. Tavanı
  indirmek bedava ama geçmiş kısalır.
* **Beklenen etki:** Yazma başına ~1,1 MB → ~1 KB. Bugün fark yok;
  50 gün sonra kapanış başına gözle görülür fsync.
* **Kaldırma güvenliği:** Düşük risk — `r_realised`/`mfe_r` okuyan her
  şey (capture dahil) satır listesini okur, blob biçimini değil.
* **Yeniden kullanım:** Aynı desen `entry_block_events` ve
  `execution_samples` için de geçerli.
* **Durum: muhtemel** (bugün ölçülebilir darboğaz **değil**). Ölçülecek:
  2000 satırlık defterle bir kapanışın `set_setting` süresi.

#### O-2 — `entry_block_events` aynı desen, daha sık

* **Kategori:** I/O · **Önem:** Düşük-Orta
* **Kanıt:** `engine.py:1478`; `engine.py:85` `ENTRY_EVENT_LIMIT = 2048`.
  Ölçüm: **613 satır = 75.144 bayt → ~122 bayt/satır**.
* **Neden:** 45 sn debounce var (kapalı defter), yani her poll değil.
  Ama tavanda **~250 KB / 45 sn**.
* **Düzeltme:** O-1 ile aynı; tek çözüm ikisini birden kapatır.
* **Not:** Yeni `seans_disi` / `piyasa_kapali` / `bar_bosluk` dalları
  satır üretimini artırdı. Bugün **613/2048 — taşma yok**, 9 günlük
  geçmiş duruyor. Ölçtüm, alarm değil.

#### O-3 — `execution_samples` 59 KB blob

* **Önem:** Düşük · **Kanıt:** canlı db, 59.401 bayt.
* Aynı desen. Üç blob toplamı **227 KB** ve `settings` tablosunun
  neredeyse tamamı. Tek başına iş değil; O-1 çözülürse birlikte çözülür.

#### O-4 — `_CRITICAL_MUTATIONS` ölü sabit

* **Kategori:** Ölü kod + yanıltıcı güvenlik yüzeyi
* **Önem:** Düşük (işlev) / **Orta (yanıltma)**
* **Kanıt:** `web/app.py:570` tanımlı; **dosyada başka referans yok**
  (`grep -n "_CRITICAL_MUTATIONS"` → tek satır).
* **Neden:** 09:15'te "her mutasyona Origin" inince bu küme işlevsiz
  kaldı ama silinmedi. Okuyan biri **"yalnız bu yollar korunuyor"**
  sanabilir; daha kötüsü, yeni bir uç ekleyip **koruma kazandığını**
  zannedebilir. Kod doğru, **belge yalan söylüyor**.
* **Önerilen düzeltme:** Sabiti sil. Middleware yorumunda "her mutasyon"
  zaten yazıyor.
* **Kaldırma güvenliği:** **ORTA** — *(düzeltme 26.08 10:14, Cursor
  yakaladı)*. İlk yazdığımda "referans yok, test yok" dedim; **yanlıştı**.
  Ürün kodunda okuyan yok (doğru), ama **testlerde 6 assert** var:
  `tests/test_session_csrf_gate.py:142-146` ve
  `tests/test_holdout_capture_endpoint.py:192`. Bunlar kümeyi
  **belgelenmiş kritik liste** olarak doğruluyor. Silmek **önce o
  assert'leri yeniden yazmayı** gerektirir — tek satırlık iş değil.
  Hatanın kökü: yalnız `micofx/web/app.py` içinde grep'leyip sonucu
  "hiçbir yerde yok" diye genelledim; `tests/` taramadım.
* **Durum: kesin** (ölü sabit tespiti doğru; kaldırma maliyeti
  ilk raporda **eksik değerlendirildi**).

#### O-5 — `Engine.__new__` fikstür çürümesi

* **Kategori:** Bakım yapılabilirlik · **Önem:** Orta
* **Kanıt:** `tests/` içinde `__new__` kullanan **88 dosya**:
  `Engine` **52**, `Optimizer` **30**, `Supervisor` **14**,
  `RiskManager` 3, `ExecutionMonitor` 1.
* **Neden:** `__init__`'e eklenen her alan bu fikstürleri kırar ve
  kırılma **regresyon gibi görünür**. Bugün iki kez oldu:
  `ExecutionMonitor._originals` (08:20) ve `Engine._day_cache` (09:52).
  İkisini de canlı sanıp dibine kadar kovalamak zorunda kaldım; ikisi de
  fikstürdü.
* **Asıl maliyet CPU değil, dikkat:** bir gün yığının içinde **gerçek**
  bir regresyon duracak ve "yine fikstür" diye geçilecek.
* **Önerilen düzeltme:** Ortak `make_engine()` / `make_optimizer()`
  yardımcısı `__init__`'in alan kümesini **tek yerde** yansıtsın.
* **Ödünç:** 88 dosyalık dokunuş büyük ve gürültülü. **Bu tarama
  kapsamında değil** — TASK-2 yalnız bir dosyayı göç ettiriyor.
* **Durum: kesin** (iki canlı örnek).

---

### 3) Hızlı kazanımlar

1. **O-4** — `_CRITICAL_MUTATIONS` sil. Tek satır, referanssız, testsiz.
2. **TASK-1** — panel `left_on_table_r` yalnız kazananda (ayrı görev).
3. **TASK-2** — tek fikstür dosyası (ayrı görev).

Bunların dışında **hızlı kazanım bulamadım.** Gecenin landing'leri kolay
olanları zaten almış.

---

### 4) Derin optimizasyonlar

* **O-1/O-2/O-3 birlikte:** `settings`'teki üç halka blobunu satır
  tabanlı bir tabloya taşımak. Tek iş, üç bulguyu kapatır. **Önce ölç:**
  2000 satırlık defterle bir `set_setting` ne kadar sürüyor? Ölçmeden
  yapılmamalı — bugün 77 KB'lık bir yazma darboğaz değil.
* **O-5:** fikstür yardımcısı. Performans değil, **yanlış alarm** bütçesi.

---

### 5) Doğrulama planı

| Değişiklik | Doğrulama |
|---|---|
| O-4 sil | `grep -rn "_CRITICAL_MUTATIONS" micofx/` boş; `pytest tests/test_session_csrf_gate.py` yeşil (Origin kapısı bağımsız) |
| O-1/O-2 göç | Göç öncesi/sonrası `trade_autopsy_report()` **bayt-eş**; `capture` ve `left_total` değişmemeli; 2000 satır sentetik yükle süre ölç |
| O-5 yardımcı | Göç edilen her dosya **önce kırmızı sonra yeşil**; `Engine.__init__`'e sahte alan ekleyip yardımcının yakaladığını göster |

Her biri için **fail-first**, sonra `pytest -q` + `ruff check`.

---

### 6) Önerilen yamalar (yalnızca öneri — uygulanmadı)

**O-4** — `micofx/web/app.py` ~570, sil:

    # OLU: 09:15'ten beri okunmuyor. Origin kapisi middleware'de HER
    # mutasyona uygulaniyor. Bu kume "yalniz bunlar korunuyor" izlenimi
    # veriyor - yanlis.
    _CRITICAL_MUTATIONS = frozenset({...})

**O-5** — `tests/_engine_fixture.py` (yeni, öneri):

    def make_engine(**over):
        """__init__'in alan kumesini tek yerde yansitir.

        Elle kurulan 52 Engine fiksturu yeni alan eklendiginde tek tek
        curuyor ve her curume regresyon gibi gorunuyor (26.08:
        _originals, _day_cache). Yeni alan buraya eklenince hepsi kapanir.
        """
        eng = object.__new__(Engine)
        eng._day_cache, eng._day_cache_at = {}, 0.0
        eng._entry_events, eng._entry_blocks = [], {}
        eng._trade_autopsies = []
        # ... __init__ ile ayni kume
        for k, v in over.items():
            setattr(eng, k, v)
        return eng

---

### SECURITY AUDIT: kirli ağaç (`0c33d72` → çalışan ağaç)

Kapsam: **staged + unstaged** ürün diff'i. 39 dosya, **+1227 / −514**.
Her değişen satır saldırı yüzeyi varsayıldı.

**Risk Assessment: DÜŞÜK.** Kritik veya Yüksek bulgu **yok**. Kimlik
bilgisi sızıntısı **yok**. Enjeksiyon yüzeyi **temiz**. Gecenin CSRF
sıkılaştırması diff'in en güçlü tarafı — her mutasyon artık Origin
istiyor, sadece adlandırılmış bir küme değil.

#### Findings:

* **`Host` başlığı izinli Origin kümesini kuruyor** (Düşük)
  * **Location:** `web/app.py:610-612` — `host = request.headers.get("host")`,
    `allowed = {f"http://{host}", f"https://{host}"}`
  * **Exploit:** İstemci hem `Host: evil` hem `Origin: http://evil`
    gönderirse küme kendi kendini doğrular. Doğrudan 127.0.0.1 bind'de
    istek zaten sunucuya ulaşmaz; araya bir ters vekil girerse anlamlı
    hale gelir.
  * **Fix (öneri):** İzinli origin'i **bind adresinden** türet
    (`run.py`'deki host/port), istek başlığından değil.
  * **Not:** `sec-fetch-site == "cross-site"` reddi ve `SameSite=Strict`
    çerez bunu pratikte kapatıyor. **Derinlik savunması notu**, açık kapı
    değil.

* **Ölü `_CRITICAL_MUTATIONS` güvenlik yüzeyini yanlış anlatıyor**
  (Düşük — bkz. O-4)
  * **Location:** `web/app.py:570`
  * **Exploit:** Doğrudan sömürü yok. **Bakım riski:** bir sonraki
    geliştirici yeni uç noktayı bu kümeye ekleyip korunduğunu sanabilir.
  * **Fix:** Sil.

* **Üretilen token'ın son 6 hanesi loga yazılıyor** (Bilgilendirme)
  * **Location:** `run.py:244` — `...{api_token[-6:]} ile bitiyor`
  * **Exploit:** `token_urlsafe(24)`; 6 karakter açığa çıksa da kalan
    entropi kaba kuvvete kapalı. Log gitignore'da ve makine yerel.
  * **Fix:** Gerekmez — operatörün token'ı ayırt etmesi için bilinçli
    kolaylık. **Kayda geçiyorum, düzeltme önermiyorum.**

#### Observations (kontrol edildi — temiz):

* **SQL enjeksiyonu:** `Store` yolunda f-string / `%` / `.format` ile
  kurulmuş `execute` **yok**. Parametrize.
* **XSS:** `app.js`'te 47 `innerHTML` ataması; hepsi `esc()` / `num()` /
  `signed()` üzerinden. Kaçaksız tek interpolasyon `app.js:2224` ve değer
  **sayı** (`res.symbols.length`). `el({html})` kolu kapalı defterde
  silinmiş — **yeni sink eklenmemiş**, doğruladım.
* **CSRF:** Her `POST/PUT/PATCH/DELETE` için Origin + `sec-fetch-site`.
  Oturum karşılaştırması `secrets.compare_digest` — **sabit zamanlı**.
* **IDOR:** `/api/` altındaki her yol oturum istiyor; muaf olanlar
  (`/`, `/static`, `/favicon.ico`) mutasyon değil.
* **Girdi sınırları:** `_ForbidModel` (bilinmeyen alan reddi),
  `_validate_risk_bounds`, `_validate_sessions`, `_validate_enum_fields`,
  `OptRun.strategies/timeframes max_length=32`. Sınırsız gövde bulamadım.
* **MT5 kilidi yarışı:** Bar çekimi parçalı ve parçalar arası kilidi
  bırakıyor. İkinci `initialize()` yok. Diff'te yeni doğrudan
  `MetaTrader5` importu **yok** — doğruladım.
* **Debug yüzeyi:** `docs_url=None`, `redoc_url=None`. Açık şema yok.
* **Sınırsız döngü:** Yeni `while`/kuyruk yok; yeni sayaç dalları halka
  tavanına tabi (2048).

---

**Uygulanan hiçbir şey yok.** Bu blok not; O-1…O-5 ve güvenlik bulguları
öneri. AGENTS.md önerisi ayrı blokta. TASK-1 ve TASK-2 sırada.

### AGENTS.md proposal (not applied)

> `AGENTS.md`'ye **dokunmadım**. Aşağıdaki metin öneri; Cursor uygular
> veya reddeder. Mevcut dosyanın dili İngilizce olduğu için öneri de
> İngilizce — repo sözleşmesi (yorum/commit İngilizce) korunsun diye.
>
> Yoğunluk için yaptıklarım: her satır **tek** kural; "neden" yalnız
> davranışı değiştiriyorsa duruyor; genel yazılım tavsiyesi silindi;
> tuzaklar "ne yapma"dan "ne yanlış okunuyor"a çevrildi. Cursor'un
> pazarlıksız listesindeki maddelerin hepsi içeride.

---

# AGENTS.md

Live **fx** bot, `C:\Users\Administrator\MicoFx`. Constitution:
`MASTER_PROMPT.md` §19. Do not port `D:\MicoAi` extras unasked.

## Hard rules

- Python is `C:\MicoFX-venv\Scripts\python.exe`. No other interpreter.
- The live process **owns** `data/micofx.db` and the MT5 terminal. No
  second sqlite writer, no `mt5.initialize()` sidecar. `mt5.shutdown()`
  only in the dying process on `/api/app/restart`.
- Live writes go through the running bot: `GET http://127.0.0.1:8900/`
  for the session cookie, then the API. **Every** POST/PUT/PATCH/DELETE
  needs `Origin: http://127.0.0.1:8900` — not a named subset. Port busy:
  do not steal 8900.
- No LLM inside engine, optimizer or supervisor. Panel "AI" is the rule
  supervisor.
- Exit model is hard ATR stop + ATR trail. `tp_atr_mult`, `partial_tp_r`
  ladders, `max_bars_in_trade`, `stale_exit_ratio`, `breakeven_atr` do
  not come back. Overlays (0 = off): `breakeven_at_r` (live 1.5, not 0.5
  — BE-2 cost GER40 −32 R) and one-shot `partial_at_r`. Neither is an
  `OPT_FIELDS` axis.
- `exits.overlay_stop` is the single source; `engine._update_stop` and
  `backtest._trail_one` are its two ends. **Do not touch either without
  the identity test.**
- A forming candle never signals. Buy ∧ sell on one bar → neither.
- Opt apply writes `OPT_FIELDS` only. Never silently enable
  `ensemble_enabled`. `_slice_ok` / `_is_improvement` is the only gate;
  scheduled reopt uses the same path.
- `EXIT_RISK_FIELDS` mid-trade → **409**. `breakeven_at_r` and
  `partial_at_r` are deliberately **not** in that set: they apply to
  already-open tickets.
- **13 live families.** `alpha_trend` and `mavilim` retired 26.08 on
  holdout; `test_retired_indicators_stay_gone` blocks their return.
- **No restart while positions are open** — `track()` first-sight
  `setdefault`s `original_sl` to the *current trail*, poisoning every R
  derived from it until those tickets die.
- Watch mode never opens. Wrong `broker_symbol` → unavailable, no fuzzy
  fallback.
- Session / day-end / daily-loss flatten are settled (owner 09.08).
- `trail_start_atr <= trail_step_atr` is legal; do not ban it.
- Do not holdout-capture with positions open. Do not start a live search
  unasked.
- Tests never write `logs/` or `data/`.

## Before finishing

```
C:\MicoFX-venv\Scripts\python.exe -m pytest tests/<touched>.py -q --tb=short
C:\MicoFX-venv\Scripts\python.exe -m ruff check micofx/ tests/<touched>.py
```

**Fail-first**: write the test, watch it fail, then implement.
`pyproject.toml` already sets `--basetemp=.pytest_tmp`.

## Conventions

- UI and log strings Turkish. Comments and commit subjects: English
  *why*.
- Persist only through `Store`. Immediate write, no separate Save.
- All MT5 through `MT5Client` and its `RLock`. Web handlers never import
  `MetaTrader5`.
- New search axis: add to `OPT_FIELDS` **and** pay the grid cost, or
  `Store.opt_params()` drops it.
- **Yellow** (ask): `risk_percent`, `max_positions`, supervisor,
  `size_by_edge`. **Red** (explicit permission): leverage, account lock,
  daily brake, live flatten-all, `max_spread_atr`.
- Cursor is project lead: every product change needs Cursor's approval.
  Claude inspects anything and **must** question, but ships no patch,
  PATCH, search or restart without it.

## What gets misread

- **Day cuts follow the broker calendar.** `gmtime(naive broker epoch)`
  means "do not shift a second time", **not** "convert to UTC". While
  skew is 0, broker midnight equals machine midnight, so a 01:00 close
  belongs to **today**. Never slice against true UTC.
- **The autopsy ledger is not P&L.** All 27 pre-26.08 `flatten` rows have
  empty `profit`; summing the ledger gives the wrong **sign** (−151 USD
  against a real +379 flatten stream). `r_realised` and `mfe_r` are
  complete, so capture is unaffected. **Do not rewrite those 27 rows.**
- Realised cash appears in three log shapes: `kapandi … kar=`,
  `Pozisyon kapatildi … kar~ (anlik)`, and `parca kapatildi … kar N×ATR`
  (old form carries **no** cash). Only the first was ever in the ledger.
- `r_realised` divides by `|entry − original_sl|`. **Do not repair
  pre-fix rows** (`sl` + `r=+1.0`); their cash is the truth.
- `mfe_r` is an **intrabar peak**, never harvestable. Summing `mfe_r` and
  calling it "left on the table" is invalid. `left_on_table_r` on a loser
  is mostly the loss itself, not a missed gain.
- Holdout `capture` is a **visible column only** — not a score input, not
  an apply gate.
- The keep line reads `(taze test …R)` or `(damga …R, dd.mm)`. A pre-fix
  `test net` figure is not current.
- `_MAX_SIGNAL_BAR_AGE_BARS = 2` × timeframe. US30 is the only M5 symbol,
  so its 600 s threshold trips on overnight tick droughts — `bar_bosluk`
  there is **normal**, not a bar-refresh bug.
- `scale_out_done` prunes to live tickets under the same lock as
  `weekend_pending`; `remain` uses `fill["volume"]`.
- The fill verifier sleeps on its **own** thread, not `micofx-engine`.
  Do not "fix" duplicate-entry protection while changing it.

## Locations (non-obvious only)

- Runtime: `data/micofx.db`, `logs/micofx.log` (gitignored).
- Agent bridge (gitignored, never `git add`): `cursor/FOR_CLAUDE.md`,
  `claude/FOR_CURSOR.md`.
- Installer `KUR.bat` → `KUR.ps1`; launchers stay at repo root.
- Audit notes (not executable): `OPTIMIZATIONS.md`.
- `graft/` is a stale source dump — its line numbers are not live.

---

**Öneri sonu.** Uygulanmadı.


---

# 26.08 ~09:52 Cursor SCAN-1 (Optimization + Security + AGENTS.md)

### A) Optimization (full checklist)

#### 1. Optimization Summary
* **Health:** The system is reasonably optimized for a 6-symbol ATR book, with previous high-latency items resolved.
* **Top 3 Bottlenecks:**
  1. `IndicatorCache` rebuild on every closed bar.
  2. `simulate` inner loop during optimization.
  3. Supervisor 14d `deals_since` review blocking the `_cycle`.
* **Biggest risk if unchanged:** Expanding the search grid `OPT_FIELDS` without compiling `simulate` will hit a search wall and delay operations.

#### 2. Findings (Prioritized)

* **Title:** Full `IndicatorCache` + `compute()` on every new closed bar
* **Category:** CPU / I/O
* **Severity:** Medium
* **Impact:** High CPU usage on M5 bar closures across multiple symbols
* **Evidence:** `engine.py` rebuilds cache and calls full `compute()` on new bars.
* **Why:** Only the last closed bar signal is needed; full history rebuild is excessive.
* **Recommended fix:** Append-one-bar warm start.
* **Tradeoffs:** Risk of live/paper desync.
* **Expected impact:** High on CPU.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module

* **Title:** Python `simulate()` bar loop dominates search wall
* **Category:** CPU
* **Severity:** Medium
* **Impact:** Wall time for optimization limits grid size.
* **Evidence:** `backtest.py` loops sequentially over bars/trades.
* **Why:** Branchy logic is O(bars * open trades).
* **Recommended fix:** Implement Numba/Cython compiled simulate loop.
* **Tradeoffs:** Complex deployment.
* **Expected impact:** High ROI for search speed.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module

#### 3. Quick Wins
1. Extract `_one_off_subset` validation logic.
2. Clamp scale-out `remain` to be `>= 0`.

#### 4. Deeper Optimizations
1. Numba compiler for `simulate` inner loop.
2. Move Supervisor review to a deferred queue.
3. Incremental `IndicatorCache` logic.

#### 5. Validation Plan
* **Benchmarks:** Compare `engine.last_cycle_ms`.
* **Profiling:** Run `py-spy` on `simulate`.
* **Tests:** Exit parity tests must pass bit-for-bit.

#### 6. Optimized Code / Patch (proposal only)
```python
# Scale-out clamp fix proposal
filled = max(0.0, min(float(fill.get("volume") or close_vol), float(pos.get("volume") or 0)))
remain = max(0.0, float(pos.get("volume") or 0) - filled)
```

### SECURITY AUDIT: working tree vs HEAD 0c33d72
**Risk Assessment:** Low
#### Findings:
* **Log injection via unknown families** (Severity: Low/Medium)
* Location / Exploit / Fix: `micofx/optimizer.py` joins unknown requested strategies into `LOG.emit`. Fix: Sanitize before logging. (proposal only)
#### Observations:
* `apply_best` defaults to True on `OptRun`.
* Session cookies and Origin checks are properly enforced.

### AGENTS.md proposal (not applied)
```markdown
# AGENTS.md
Live bot at `C:\Users\Administrator\MicoFx`. Constraints:
- Use `C:\MicoFX-venv\Scripts\python.exe`.
- Live process owns DB/MT5; Origin required on all mutations.
- No LLM in engine. Exit model: hard ATR stop + ATR trail (no partial tp ladders).
- `overlay_stop` identity shared live/backtest. Forming candle never signals.
- `OPT_FIELDS` apply only; `EXIT_RISK_FIELDS` mid-trade yields 409.
- 13 families; no restart with opens.
- Fail-first with pytest/ruff. Persist via Store only.
- Yellow/red gates stay operator-only. Holdout capture is not a score input.
- Autopsy gotchas: `open_original_sl` must be tracked, profit-empty rows exist, `gmtime` broker calendar used.
```
