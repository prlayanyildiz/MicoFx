# OPTIMIZATIONS.md

Read-only notes. **Not executed by the engine.** Latest:
**27.08 22:10** operator hardest A–Z (API/web/dead leftovers/8 families/
counterfactuals, numbers only). Prior **20:40**. Shakeout floor stays;
do not teach search it. Live search **idle** (20:21 job died at 160k
on 21:20 restart-with-opens). Do **not** start a new search unasked.
GER40 #367727827 open → no restart. Harvest off. Numba/O-1/F1/F2
won't-do. HEAD `122e434` + dirty tree.

---

## 27.08 22:10 — Operator hardest A–Z (measured; no patch)

Independent Cursor pass after operator: API/web/engine/families/symbols,
stripped-feature leftovers, missed fills, reverse+forward, counterfactuals
**with numbers**. Did **not** PATCH, start a search, flatten, capture,
restart, or commit. 1 GER40 ticket open. Claude given a heavier independent
brief (22:08) — this file is Cursor's numbers, not Claude's.

Live GET `/` cookie then `/api/state` `/api/symbols` `/api/system`
`/api/analysis/*` `/openapi.json`. Log `logs/micofx.log` 27.08 only.
Autopsies dated with `gmtime` (naive broker epoch). 82 tests green:
csrf, openapi, cancel-abandon, hands-off HTTP, unused names, shakeout,
panel DOM.

**Live 22:05–22:10:** demo 61562752. Balance **$1957.88** / equity **~$1958**
/ floating **−$0.1**. Day **38** closes WR **26.3%** realised **−$186.61**
`pnl_pct` **−8.69%** halt **false**. `opt.state=idle`. `last_cycle_ms` **3–7**.
`last_error` empty. 1 open: GER40 #367727827 BUY 0.1 SL **26303.1** (entry
26379.1 ≈ **2.0 ATR**, ATR 38.0). AI `risk_scale` **0.60** enforced
(`Gunluk zarar %8.69`). JPN `ok`; other five `watch`.

### 1) Optimization Summary

* **Health:** No new engine leak vs 20:40. Today's **−$186.61 / −13.22 R**
  is GER40 `stoch_flip` 1.0 orig-SL (**8/11**, **−$138.52 / −8.89 R**) plus
  JPN225 (**−$73.79 / −7.16 R**) with **no daily halt** (`daily_loss_pct=0`)
  and **no ticket cap** (`max_total_positions` **unread**). Idle cycle is
  paid (**3–7 ms**). Search is **not** running. Claude 20:50 openapi+cancel
  holes are **closed on this PID** (404 + disk abandon).
* **Top 3 highest-impact (none is a silent CPU patch):**
  1. Keep the open GER40. Restart first-sights stops; 21:20 and 21:43 already
     restarted **with tickets** (5 then 3).
  2. After **flat only**: `daily_loss_pct=0` vs a 3% brake. Start equity
     inferred **$2144** from `pnl_pct`. 3% ≈ **$64**. Realised **$186**.
     Gap **~$122** is the measured extra bleed **if** the 3% halt would have
     fired and flattened; it would also have flattened later US30/XAU winners
     (US30 today **+$21.78 / +2.19 R**, XAU **+$8.97 / +1.37 R**). Yellow/red.
  3. GER40 searched stop **1.0** vs shakeout next-entry **2.0** (this PID,
     22:01 `lot serbest, risk ayni`). Floor is live on **all 6** names
     (last-10 `exit_reason=sl` losers ≥3; all of those were `sl==original_sl`).
     Search still prefers 1.0. Do not PATCH SL. Do not disable the floor.
* **Biggest risk if no changes:** Operational, not ms. Next `apply_best`
  of a 1-slot walk-forward onto a book that stacks until **margin 90% /
  reverse / STOPSUZ** is an untested regime. Panel still ranks dead
  `risk_sembol_limiti` **209** as lifetime #2 (producer gone). Day can
  keep bleeding with no halt.

### 2) Findings (Prioritized)

* **Title** `max_total_positions=100` is unread — 100-slot / 80% 1R does **not** bind
* **Category** Algorithm / Reliability
* **Severity** High (operator model; corrects 20:40)
* **Impact** Live stacking cap is **margin 90%**, reverse, STOPSUZ, scalp/swing
  only if those leftovers **>0** (live **0/0 = off**). Capacity
  `global_free_slots=237`, `margin_usage_pct=0.39`, `open_risk_pct=0.45`.
* **Evidence** `can_open` `risk.py:570-604` has no total-count check.
  `max_positions` **zero reads** in `risk.py`. Capacity still **dumps**
  `max_total_positions: 100` and leftover `max_concurrent_risk_pct: 30`.
  field_help already says unread.
* **Why it’s inefficient** 20:40 / Claude 20:35 treated 100×0.8%=80% 1R as
  a live ceiling. It is a stored number. Concurrent 1R also unread
  (`risk.py:601-602`).
* **Recommended fix** After quiet: slim snapshot to panel keys. Do **not**
  restore a ticket cap unasked (US30 slot-2 overlap +4.62 R, closed won't-do).
* **Tradeoffs / Risks** Readers using GET as the contract.
* **Expected impact estimate** Clarity. Zero latency.
* **Removal Safety** Likely Safe (payload slim) / Needs Verification (restore cap)
* **Reuse Scope** `risk.py` capacity dict + `app.py` system GET

* **Title** Today's cash is GER40 1.0 orig-SL + no halt, not a fill leak
* **Category** Cost / Algorithm
* **Severity** High (today's $)
* **Impact** Day **−$186.61 / −13.22 R / 38 closes**. GER40 11 **−$138.52 /
  −8.89 R / 8 orig-SL / 2 trail / 1 manuel / 1 win**. JPN225 13 **−$73.79 /
  −7.16 R / 6 orig-SL**. US30 7 **+$21.78 / +2.19 R**. XAU 2 **+$8.97**.
  NAS 4 **−$1.14**. Brent 1 **−$3.87**. `mfe_r≥1.5` then SL **today: 0**.
* **Evidence** Autopsy `gmtime` 27.08 n=38 matches `/api/state` day.
  `fill_vs_signal_close_r` today n=25 mean **+0.088 R** (min −0.13, max +1.12)
  — not an adverse-fill leak. Window n=237: SL 132, through_entry 87,
  recovery ≥0.5 R 135.
* **Why it’s inefficient** Search still offers `sl_atr_mult=1.0` and GER40
  holds it. Shakeout only widens the **next** entry (22:01 GER40 2.0, lot free).
* **Recommended fix** Let a future search finish on a **flat** book. Do not
  PATCH SL on the open ticket. Do not cancel a search that is already idle.
* **Tradeoffs / Risks** `apply_best` may write another 1.0 onto GER40.
* **Expected impact estimate** Floor: losers stay −1 R in R-space; min-lot
  names **grow dollar risk** (see shakeout finding).
* **Removal Safety** Needs Verification
* **Reuse Scope** `risk.shakeout_sl_atr_mult` + optimizer grid

* **Title** `daily_loss_pct=0` — flatten-always is wired but unreachable
* **Category** Reliability / Cost
* **Severity** High (policy)
* **Impact** Counterfactual 3% of ~$2144 ≈ **$64**. Realised **$186**.
  Extra **~$122** if the old 3% halt would have flattened when it first
  crossed. `daily_loss_flatten` **unread** (`models.py` + field_help only);
  engine flattens whenever `loss_halted` (`engine.py:897-899`) **without**
  reading the flag. Halt never trips because `DailyGuard.check` needs
  `daily_loss_pct > 0` (`risk.py:263`).
* **Evidence** Live `system.daily_loss_pct=0`, `halted=false`. CFG 19:28
  `daily_loss_pct 20.0 -> 0.0`. HTTP 400 on POST `daily_loss_pct`.
* **Why it’s inefficient** N/A — intentional cancel. Communication: capacity
  / AI still react (`lot carpani 0.60` at −8.69%) **after** the cash is gone.
* **Recommended fix** None unless the operator wants the brake back.
  Restoring 3% is yellow/red. Do not silently write 3.
* **Tradeoffs / Risks** A halt flattens winners too.
* **Expected impact estimate** Likely capped today near −$64 vs −$186
  **if** it had been on from the open. Not a replay.
* **Removal Safety** Needs Verification
* **Reuse Scope** Store leftover + `DailyGuard`

* **Title** Concurrent 30% leftover — the cap **was** binding before the strip
* **Category** Algorithm
* **Severity** High (stripped feature, not dead)
* **Impact** Log 27.08 **8** `eszamanli` WARN lines, last `19:18:35 kitap
  %54.56 eszamanli risk istiyor, tavan %30`. After ~20:05 unread, WARNs stop.
  Live 20:39 had **7** opens. Now 1 open, `concurrent_risk_pct` dump **4.91**
  (sum of configured 1R, not a gate).
* **Evidence** Claude TUR 5 + log. `can_open` does not read
  `max_concurrent_risk_pct`. HTTP 400.
* **Why it’s inefficient** Calling it "dead code cleanup" is false — it was
  refusing entries at 31–54% demand. Operator chose to drop it; record that.
* **Recommended fix** Do not restore unasked. Do not teach search stacking
  tonight.
* **Tradeoffs / Risks** Restoring 30% re-opens a real gate (yellow).
* **Expected impact estimate** Unknown without a stacking walk-forward.
  Cannot attribute today's −$186 to the strip (no replay).
* **Removal Safety** Needs Verification
* **Reuse Scope** `risk.can_open`

* **Title** Shakeout floor is on for the whole book; min-lot **grows** dollar risk
* **Category** Cost
* **Severity** High (live overlay vs paper)
* **Impact** Last-10 `exit_reason=sl` losers: SpotBrent 3, JPN 5, GER40 7,
  US30 3, NAS 5, XAU 7 — **all ≥3**, all were `sl==original_sl`. Floor **2.0**.
  Log 6 fires: first five `lot tabanda, gercek risk buyuyor`; GER40 22:01
  `lot serbest, risk ayni`. Capacity `lot_note` `SL x2 shakeout` on five
  names; Brent still `avantaj x0.71` (sl already 2.5 ≥ floor).
* **Evidence** `shakeout_sl_atr_mult` window=10 deaths=3 floor=2.0.
  `shakeout_size_note` `risk.py:66-77`. This PID 18:00–22:01.
* **Why it’s inefficient** Walk-forward never pays the floor. Winners' R
  halves when 2.0 binds; min-lot losers **cost more $**.
* **Recommended fix** Keep the floor. Do not add it to `OPT_FIELDS`.
* **Tradeoffs / Risks** Paper vs live divergence on every 1.0-stop name.
* **Expected impact estimate** Qualitative (19:10); live log now confirms
  the min-lot branch.
* **Removal Safety** Needs Verification (do not remove)
* **Reuse Scope** `risk.py`

* **Title** Dead `risk_sembol_limiti` still ranked #2 (209 / 956)
* **Category** Frontend / Maintainability
* **Severity** High (operator model)
* **Impact** Lifetime entry-blocks: signals **956**, opened **289**
  (fill **30.2%**). totals: spread **241**, **sembol limiti 209**, ters **148**,
  bar_bosluk 45, emir_hatasi 12, bar_doldu 8, lot 4. Retries US30 spread
  17715 / GER40 sembol 40590. Producer string gone from `can_open`.
* **Evidence** `engine.py:151-159` `_RISK_BLOCK_KEYS`. Live GET
  `/api/analysis/entry-blocks`. HTTP 400 `max_positions`.
* **Why it’s inefficient** Historical counters look like a live gate.
* **Recommended fix** After quiet: drop needles **or** note suffix
  `(kalkti)` **or** reset (wipes spread/ters too). Do not reset during a
  search (none running, still don't — operator-visible).
* **Tradeoffs / Risks** Reset is one-shot irreversible on that blob.
* **Expected impact estimate** Zero latency. Stops a false #2.
* **Removal Safety** Likely Safe (mapping) / Needs Verification (reset)
* **Reuse Scope** engine.py + panel analysis

* **Title** 20:21 `apply_best` 3.08M died at 160k; restart-with-opens cancelled it
* **Category** Concurrency / Reliability
* **Severity** High (operational, now idle)
* **Impact** Log: 20:21 start 144 sweeps / 6 symbols / 8 families / 3 TF
  (`6×8×3=144`). Cancel lines 20:27–21:20 stuck **160000/3081600**.
  **21:20:58 restart** (5 tickets) + **21:43:25 restart** (3 tickets).
  No apply line. Last successful apply **15:56** GER40+NAS100.
  Disk now abandons the pool; this PID did not run that job.
* **Evidence** `logs/micofx.log` OPT/WARN. Live `opt.idle`. Tests 4/4
  `test_opt_cancel_is_noticed_mid_sweep`.
* **Why it’s inefficient** Iptal set the event; old harvest waited on
  workers. Restarts with tickets first-sight stops **and** kill the job.
* **Recommended fix** Do not start a new 3.08M unasked. Next search: either
  drop unused families from **that job's** `strategies` (one-off, not persist)
  or leave 8 — apply **can** swap (NAS100 `mtf_pullback`→`stoch_flip` 15:56).
* **Tradeoffs / Risks** A 3-family one-off cannot discover ichimoku/aroon.
* **Expected impact estimate** 5 unused families = **90/144** sweeps (62.5%)
  if this job had finished. Combo wall dominated by `stoch_flip` cap 28800.
* **Removal Safety** Needs Verification
* **Reuse Scope** optimizer start `strategies=`

* **Title** Restart/shutdown 409 still missing — proven twice tonight
* **Category** Reliability
* **Severity** Medium (constitution vs operator)
* **Impact** Two live restarts with open tickets. 21:50 four **Elle
  (terminal)** closes (US30 +9.40, JPN −3.10, GER40 +3.86, US30 +13.56 =
  **+$23.72** operator, not engine) then IPC **−10001** ×2.
* **Evidence** `app.py:1987-2016` no position check, no `_restarting` lock.
  Log 21:20 / 21:43 `Yeniden baslatma istegi alindi` + `magic ile N acik ticket`.
* **Why it’s inefficient** AGENTS.md forbids restart-with-opens; HTTP allows it.
  Double-submit can spawn two `restart.bat`.
* **Recommended fix** Notes only tonight — operator used restart with tickets
  and granted restart authority. A 409 would block that. Do not add unasked.
* **Tradeoffs / Risks** 409 vs operator override.
* **Expected impact estimate** Safety, not ms.
* **Removal Safety** Needs Verification
* **Reuse Scope** `app.py` restart/shutdown

* **Title** `size_by_edge` hidden-but-on; AI 0.60 after the loss
* **Category** Maintainability
* **Severity** Medium
* **Impact** Live True. GER40 capacity `avantaj x1.89`. HTTP 400. AI scale
  0.60 from **today's** −8.69% — haircuts **next** lots, does not unwind
  today's −$186. GER40 TRADE 22:01 `AI x0.36` with shakeout 2.0 and lot free 0.12.
* **Evidence** `GET /api/system` `size_by_edge=true`. TRADE 22:01:12.
* **Why it’s inefficient** Operator cannot dial it. AI throttle is lagging.
* **Recommended fix** After quiet: read-only chip **or** force False (yellow,
  changes lots). Do not HTTP-open it.
* **Tradeoffs / Risks** Turning it off shrinks names the stamp likes (GER40 1.89).
* **Expected impact estimate** Live lots move; idle ms unchanged.
* **Removal Safety** Needs Verification
* **Reuse Scope** Store leftover

* **Title** SIGNAL 90 vs fills 43 is **not** 47 lost +R trades
* **Category** Reliability (measurement honesty)
* **Severity** Medium
* **Impact** Log 27.08: SIGNAL **90**, TRADE opens **43**, closes **38**.
  Naive ±120s unmatched **55** — includes reverse, spread, session, restart
  re-SIGNAL (10:03:46 GER40/XAU/NAS same second; 21:20/21:43 `last_bar`
  replay). Lifetime fill 289/956=30.2% mixes the dead 209-slot era.
* **Evidence** Log parser. `filled_bars` / restart SIGNAL design (24.08 15:31).
* **Why it’s inefficient** Counting SIGNAL−TRADE as missed edge overstates.
  Need `entry_block_events` **today** (API totals are lifetime).
* **Recommended fix** Do not open spread / reverse gates unasked (MISS-1 GER40
  reverse holdout −1001 R still stands).
* **Tradeoffs / Risks** False "we left money on the table".
* **Expected impact estimate** Unmeasured without today's event rows.
* **Removal Safety** n/a
* **Reuse Scope** analysis + log

* **Title** 8 families reverse: 4 live `stoch_flip` + burst + parabolic; 5 empty are search candidates
* **Category** Algorithm
* **Severity** Medium (search cost vs option value)
* **Impact** Live book: GER40/JPN/NAS/US30 `stoch_flip` (HTF **flat**),
  XAU `burst` M15 (HTF used, misses showed HTF=−1), Brent `parabolic_flip`
  M15 (PSAR flip, HTF flat, sl 2.5). Empty: `mtf_pullback` `dual_t3`
  `t3_flip` `aroon_flip` `ichimoku`. Grids already drop unread axes
  (`test_no_family_grid_axis_is_unread`). Overlays **not** OPT_FIELDS:
  BE 1.5, partial 1.5 on five names, harvest **0**.
* **Evidence** `GET /api/symbols`. `strategy.py` builders + `searchable_axes`.
  20:21 log `144 tarama`.
* **Why it’s inefficient** 90/144 sweeps search families the book does not
  currently trade; `apply_best` **may** swap them in (NAS100 15:56).
* **Recommended fix** F1/F2 stay **won't-do**. One-off `strategies=` on a
  future manual run is allowed and does not persist.
* **Tradeoffs / Risks** Dropping 5 families forever closes NAS100-style swaps.
* **Expected impact estimate** Sweep count −62.5% on a 144-job; combo wall
  still `stoch_flip` 28800-capped.
* **Removal Safety** Needs Verification (yellow if persistent)
* **Reuse Scope** `POST /api/opt/run` strategies

* **Title** GET leftover asdict + `autostart_mt5=true` vs MASTER_PROMPT §19
* **Category** Frontend / Maintainability
* **Severity** Low
* **Impact** `/api/system` still returns unread caps and `daily_loss_flatten`.
  Panel connection card still has `autostart_mt5` (HTTP allowlist).
  MASTER_PROMPT §19 says do not port `autostart_mt5`; this tree already has it
  and AGENTS.md lists it as System POST. Not a new port.
* **Evidence** Live GET. `app.py` `_OPERATOR_SYSTEM_FIELDS`.
* **Why it’s inefficient** Agents/panel can *see* dead knobs.
* **Recommended fix** Slim GET after next boot. Do not remove autostart unasked.
* **Tradeoffs / Risks** GET-as-contract readers.
* **Expected impact estimate** Less than 1% payload.
* **Removal Safety** Likely Safe (slim) / Needs Verification (autostart)
* **Reuse Scope** app.py

* **Title** Security live: session/CSRF/openapi/hands-off hold; restart 409 is the hole
* **Category** Reliability / Security
* **Severity** Low–Medium
* **Impact** See SECURITY AUDIT below. No new injection in the probes.
* **Evidence** Live curl + 82 tests.
* **Why it’s inefficient** `/openapi.json` was the 20:50 hole; **this PID 404**.
* **Recommended fix** Notes. Do not add restart 409 tonight.
* **Tradeoffs / Risks** —
* **Expected impact estimate** —
* **Removal Safety** —
* **Reuse Scope** web middleware

### 3) Quick Wins (Do First)

* Do nothing to the open GER40. No restart, no SL PATCH, no search.
* After flat: decide daily halt (yellow/red) — measured gap ~$122 vs 3%.
* After quiet: label or drop dead `risk_sembol_limiti` / `risk_eszamanli`
  needles so Eleme Kapilari stops ranking a deleted gate #2.
* Slim capacity/system GET so unread `max_total_positions=100` /
  `max_concurrent_risk_pct=30` stop looking like live caps.
* Next manual search: optional one-off `strategies` = live three
  (`stoch_flip`,`burst`,`parabolic_flip`) **without** persisting the subset.

### 4) Deeper Optimizations (Do Next)

* Yellow: stacking walk-forward (`max_open` from live) vs paper 1. Do not
  teach it tonight.
* Yellow: persist vs one-off family subset. Option value of 15:56 NAS100 swap.
* Shakeout vs search 1.0: three-arm diagnostic (gates / floor / both) stays
  designed, not a patch. Floor is **not** an OPT axis.
* Restart 409 + single-flight `_restarting` — only if operator wants the
  constitution enforced against the panel button.
* Numba simulate / O-1 sqlite split: still won't-do (2.57ms / 6.53ms; 2000-row
  cap unmeasured). Idle cycle already 3–7 ms.

### 5) Validation Plan

* Already green this pass: `tests/test_session_csrf_gate.py` (incl. openapi
  404), `test_opt_cancel_is_noticed_mid_sweep.py`,
  `test_hands_off_fields_are_not_api_writable.py`,
  `test_unused_production_names.py`, `test_shakeout_widens_the_next_stop.py`,
  `test_panel_first_screen_shows_positions.py` — **82 passed**.
* Before/after any payload slim: `GET /api/state` capacity keys the panel
  actually reads (`test_panel_account_cards_keep_their_fields`,
  `test_unread_payload_keys_are_gone`).
* Before restoring a halt: measure start_balance × pct vs today's deal times
  (replay, not a guess).
* Before a stacking search: holdout with `max_open>1` on GER40/NAS/US30 only.
* Metrics: `last_cycle_ms`, day realised, orig-SL count, entry-blocks
  **increments** (dead keys must stay flat).

### 6) Optimized Code / Patch

**None shipped.** Disk already contains the 20:50 fixes
(`openapi_url=None`, `_abandon_search_pool`). Live PID (21:43 restart)
serves them: `/openapi.json` **404**, hands-off **400**. Remaining items
are yellow/red or operator-model. AGENTS.md **not** rewritten (see notes).

#### SECURITY AUDIT: dirty tree + live surface 22:10

**Risk Assessment:** Low on the live PID. Medium on restart-with-opens
(availability / stop first-sight), not a remote RCE.

#### **Findings:**

* **Unauthenticated `/openapi.json`** (Severity: closed on this PID)
  * **Location:** `micofx/web/app.py:587-588` `openapi_url=None`
  * **The Exploit:** Claude 20:50: cookie-less GET 200 / 42 routes / 11
    destructive names. Middleware skips non-`/api/` paths.
  * **The Fix:** Already `FastAPI(..., openapi_url=None)`. **Live 404.**
    `/docs` `/redoc` 404. Pin `test_openapi_schema_is_not_public`.

* **Origin CSRF** (Severity: held)
  * **Location:** `app.py:602-608`
  * **The Exploit:** POST `/api/system` no Origin → **403**. POST panic
    `Origin: http://evil.example` → **403**. Cookie-less `/api/state` → **401**.
  * **The Fix:** None. SameSite=Strict + Origin=Host still on.

* **Hands-off allowlist** (Severity: held on this PID; G6 closed)
  * **Location:** `app.py:418-429` `_OPERATOR_*`
  * **The Exploit:** Live POST GER40 `risk_percent` / `sl_atr_mult` / `strategy`
    / `max_positions` → **400**. System `daily_loss_pct` / `size_by_edge` /
    concurrent / total → **400**. `.../reset` 400. `/api/ai` GET **404**.
    `/api/logs/clear` **404**.
  * **The Fix:** None. Claude 20:50 G6 (old PID accepted `risk_percent`)
    does **not** reproduce here.

* **Restart with open tickets** (Severity: Medium, operator-visible)
  * **Location:** `app.py:1987-2016`
  * **The Exploit:** Panel restart does not 409. 21:20 (5 tickets) and
    21:43 (3 tickets) landed. First-sights `open_original_sl` to current
    trail. Killed the 160k search.
  * **The Fix:** 409 if `engine.positions` non-empty **plus** a
    `_restarting` latch. **Not applied** — operator used this door tonight.

* **Secrets / pickle / second initialize:** Claude 20:50 dirty-tree grep
  `eval` / `exec` / `pickle` / `shell=True` **0**. Subprocess restart.bat is
  a fixed template. Not re-diffed line-by-line this pass.

#### **Observations:**

* Static `/` 200 without cookie (must — sets the cookie). HTML 23122 bytes.
* Panel DOM: day before positions before capacity, no `panel-narrow`, no
  `tabs-spacer`.
* `autostart_mt5` True is an allowlisted connection-card dial, not a new Ai port.

#### AGENTS.md rewrite — **not shipped**

Constitution stays. Proposed **additions** only (do not delete 8-family /
exit-model / Origin / single sqlite / no restart-with-opens):

* `FastAPI(openapi_url=None)` is required; `/openapi.json` must 404.
* `Optimizer.cancel` must mark `cancelled` and abandon the pool
  (`terminate` + `shutdown(wait=False)`). Event-only cancel is a panel lie.
* `max_total_positions` / `max_positions` / `max_concurrent_risk_pct` are
  **unread**. Live stacks until margin / reverse / STOPSUZ. Do not quote
  leftover 100 as a gate.
* `daily_loss_flatten` unread; flatten runs whenever `loss_halted`. `0`
  `daily_loss_pct` disables the halt entirely.
* Next process loads HTTP-off exits; this PID still 400s them (verified).

---

### Closed ledger (do not re-open)

| Item | Evidence now |
|---|---|
| GET `/openapi.json` ungated | **Live 404.** Disk `FastAPI(openapi_url=None)`. `/docs` `/redoc` 404. Pin `test_openapi_schema_is_not_public`. Claude 20:50 was PID 17:40. |
| Opt cancel stuck at 160k | **Disk landed.** `harvest` timeout 0.5s + `_abandon_search_pool` terminate. Pin `test_opt_cancel_is_noticed_mid_sweep`. Live job was killed by restart before this PID could prove it. |
| Hands-off POST 400 | **Live 400** this PID: risk_percent, max_positions, sl/family, daily_loss_pct, size_by_edge, concurrent, total, opt strategies, reset. `max_margin_usage_pct` remains writable. |
| F1 `trigger_pad` hoist | `walk_forward` passes `trigger_pad=` into `simulate`. |
| `/api/schema` catalogs | `GET /api/schema`. `/api/state` has no `opt_fields`. |
| Panel 1.5s during search | `app.js` `hidden ? 6000 : 3000`. |
| Snapshot second `positions_get` | `_panel_positions` reuses a fresh cycle book. |
| 45s full bar refetch | Unused name; integrity 900s. |
| `entry_blocks` every-poll commit | 45s debounce. |
| `_sig_cache` full clear | LRU cap 4. |
| Tick/info TTL | 120s / 0.5s. |
| alpha_trend / mavilim / st_trend / macd_flip / t3_stoch / wavetrend_flip / micro_rev | Retired. **8 families.** |
| `original_sl` RAM-only | **Landed.** `note_fill` writes `open_original_sl`; `track()` restores before first-sight. Pre-patch tickets still first-sight. Do not persist the fallback. |
| Fill-verify blocks `_cycle` | **Landed.** Immediate peek. `defer_verify=True` side thread. Do not delete the sleeps. |
| Supervisor 14d inside `_cycle` | **Landed.** `_kick_supervisor_review` daemon; gate prevents stacking. |
| `/api/state` full `symbol_payload` | **Landed.** `symbols_sig`; panel refetches `/api/symbols`. |
| Scale-out remain / second `info` | **Landed.** Clamp `filled` ≤ position. |
| Duplicated trail/BE math | **Landed.** `exits.overlay_stop`. |
| Opt `copy_rates` holds the lock | **Landed (chunked).** `_BAR_FETCH_CHUNK=2500`. No second `initialize()`. |
| Short MFE ask pad / `_merge` `trade_mfes` / LOG CR/LF | **Landed.** |
| Incumbent holdout replayed twice | **Landed.** `_fresh_incumbent_holdout` memo. |
| Origin-less POST | **Landed.** Every mutation needs Origin. |
| Snapshot account / day_stats / capacity TTL | **Landed.** |
| `el({html})` XSS | **Landed.** Branch removed. |
| Incremental IndicatorCache / Numba simulate | **Closed (measured won't-do).** 2.57ms / 6.53ms. |
| Flatten autopsy profit / left_on winners-only | **Landed.** |
| `tf_lock_status` / panel flatten `reason=` / opt npy share | **Landed 12:50–13:05.** |
| Calendar reopt / GET `/api/ai` / `POST /api/logs/clear` | **Landed 26.08 strip.** Panel `STATE.ai`; Temizle DOM-only. |
| `backtest.run` / `mae_close` / `_stamp_values_match` / `_tf_seconds` | **Landed.** Pin `tests/test_unused_production_names.py`. |
| Unread payload (`pending_exit_fields`, `tried[]` net_r, walk_forward `raw_score`/`holdout_bars`, info `contract_size`, supervisor `saved_at`, `partial_close_lots`, `primary_max_spread_atr`) | **Landed.** Claude 18:05/18:45: production callers **0**. |
| Harvest-on / trail-to-entry clamp / BE 0.5 | **Won't-do.** Paper off beats harvest shapes; GER40 BE@0.5R = −32 R. |
| `max_positions` 3→1 from one red ticket | **Won't-do.** US30 slot-2 overlap +4.62 R (n=12). Yellow. |
| Adverse-fill entry gate (`fill_vs_signal_close_r`) | **Won't-do.** WF fill-next-open; Claude 18:45 threshold scan is a curve-fit. |
| One-day `blocked_entry_hours` | **Won't-do.** UTC+3 invented a 00:00 SL bucket; gmtime has no 00 hour. |
| `/api/state` during a 14-worker search (148s) | **Landed.** Snapshot serves last cycle book while `optimizer.busy`. Halt/flatten still wait in `_cycle`. No second `initialize()`. |
| F-1 `entry_block_events` skipped 45s debounce | **Landed.** `_flush_entry_blocks` window covers both blobs. `force=True` on reset/delete. |
| MISS-1 `shutdown()` skipped the ring | **Landed.** `shutdown()` force-flushes the ring after join. |
| MISS-2 force-flush before `thread.join` | **Landed.** Ring flush runs after join. |
| MISS-3 `execution.flush()` before `thread.join` | **Landed.** Same place as the ring: after join. Autopsies stay cycle-local (no shutdown flush). |
| 900s integrity full `required_bars` with no new bar | **Landed.** `bar_window_pins` (oldest + last closed). Full copy on mismatch / missing cache. Middle-bar hole with both ends unchanged is the remaining miss. |
| O-1/O-2/O-3 settings blob rewrite | **Won't-do until 2000-row cap is measured.** F-1 closed the hot caller. Live sqlite owner; schema split is a restart-sized migration. |
| Numba `simulate` | **Won't-do until `OPT_FIELDS` grid 3×.** 6.53ms measured. |
| Empty `compute()` series | **Landed.** Fail-closed `_no_signal` before the family builder. Live `bars()` never hands n<2. |
| `_is_improvement` / `_maybe_reoptimize` names | **Landed.** Apply gates are `_slice_ok`, `reject_reason`, `_beats_incumbent`. Calendar auto-queue is gone. Quarantine still uses `_queue_reoptimization`. |
| Family-count docs (11) | **Landed.** `tests/test_docs_match_the_code.py` scans TR `N aile` and EN `N families`. Skip only `(arsiv)`. |
| Deferred fill books live `last_bar` | **Landed.** Pending carries send-time source+bar. Drain marks those; clears live signal only if `last_bar` is still that bar. Pin `tests/test_deferred_fill_keeps_a_newer_bar_signal.py`. |
| Quarantine `last_reopt_attempt` before `start()` | **Landed.** Stamp only when `start()` returns ok (or a non-dict test double). Failed start no longer burns `reopt_retry_cooldown_hours`. |
| Saved `opt_params` kept retired families | **Landed.** `Store.opt_params()` and `save_opt_params()` drop names/grids/caps not in `STRATEGIES`. Live blob POSTed 27.08 00:50 to every family then in `STRATEGIES` (search already skipped them). Pin `tests/test_opt_params_drops_retired_families.py`. |
| Combo bar used global `max_combos` | **Landed.** `run_combo_budget` sums `family_max_combos` × refine. Live `stoch_flip` 28800 made the bar 2.38M against ~5.27M real. Next process; do not PATCH caps mid-run. |
| Hands-off panel / cost toggles off UI | **Landed (UI).** Values stay on Store. MT5 path + backup dir/secondary/keep restored. Exits readout. |
| Shakeout SL floor | **Landed (disk).** Next entry floors SL to 2.0 after 3/10 original-SL deaths. Trail not scaled (option 3, docstring). This PID still old emit. |
| Opt prefetch bars / poll drops `top`/`baseline` | **Landed (disk).** This PID still fat blob + no prefetch log. |
| Dead `SECTIONS` / `optFieldVisible` / `loadSchema` / ghost `ADVANCED_SECTIONS` | **Landed (panel JS).** `GET /api/schema` kept. Pin `test_dead_symbol_guts_ui_is_gone`. Dead AI settings form builder gone; `AI_SETTING_FIELDS` stays for FIELD_HELP. |
| Ad-hoc scripts appending `logs/micofx.log` | **Landed (disk).** `LogBus._disk` off until `run.py` `LOG.enable_disk()`. Pin `test_disk_is_off_until_the_live_launcher_enables_it`. This PID still old always-on write. |
| Unread snapshot crumbs (`day.cash_flow` / `floating` / `bot.poll_interval_sec`) | **Landed (disk).** Panel already used `day.realised` / `account.profit` / Store poll. Pin `test_unread_payload_keys_are_gone`. |
| `STOCH_MID` unused constant | **Landed.** Pin `test_dead_repair_helpers_are_gone`. |
| Hands-off fields still Origin-POST writable | **Landed (disk).** HTTP allowlist = panel dials only (sizing/sessions/enabled; opt lookback/refine/max_combos). Family/TF/exits/magic/grid/reset → 400. Pin `test_hands_off_fields_are_not_api_writable`. Apply() unchanged. |
| Dead opt-grid / `SWING_OVERLAY` / empty `SYS_DANGER_NOTES` | **Landed (disk).** Client + `GET /api/opt/params` `swing_overlay` dropped together. `SYS_FIELDS_ADVANCED = []` stays (FIELD_HELP pin). `saveOptParams` still refuses empty `body.grid = {}`. Pin `test_search_gate_internals_are_not_on_the_panel`. |
| `_FALLBACK_PATHS` empty constant | **Landed.** Gone from `mt5client.py`. Pin `test_unread_payload_keys_are_gone`. |
| `cash_flow_since` every cycle | **Landed (disk).** 30s TTL while balance unchanged; `None` does not stamp TTL; deposit-shaped jump fetches immediately; rollover resets. Pin `test_cash_flow_is_not_fetched_every_cycle`. Two-call merge still won't-do. |
| Unread payload crumbs (`session_clock_skew_hours`, `execution.tracked`, snapshot `day.wins`) | **Landed (disk).** Panel keys only on snapshot `day`. `t3_kind` stays on `as_dict` (status contract). |
| `backup_dir_allow_unc` HTTP-writable | **Landed (disk).** Dropped from `_OPERATOR_SYSTEM_FIELDS`. Same-request latch → 400. Store flag still opens UNC. Pin `test_unc_latch_is_not_http_writable`. Runtime gate in `backup.py` unchanged. |
| F5 unread `opt.results[].tried` | **Landed (disk).** `status()` pops `tried` with `top`/`baseline`. Live job / opt_runs keep it. Pin `test_opt_poll_drops_unread_rankings`. |
| F3 GER40 900-bar / 2023 holdout pin | **Landed (disk).** `capture()` refuses n<5000 or last bar >14d; old file stays. Do **not** recapture while tickets are open. Next gece writes a fat window. |
| F10 Windows spawn orphans | **Landed (disk).** Sweep now matches `spawn_main` as well as `--multiprocessing-fork`. Do **not** kill the live 14 workers while the book is open; next boot/resweep. Pin `test_orphan_sweep_stays_in_its_own_venv`. |
| F14 sweep PowerShell never parsed | **Landed (disk).** Where-Object closer is an f-string; `{`/`}` balanced. rc≠0 → `gece_restart.say`. Do **not** invoke by hand while tickets are open; next gece/restart actually Stop-Process. |
| F13 topstats `lbl`/`val` unescaped | **Landed.** Both go through `esc()`. |
| F12 `cash_flow` every cycle | **Landed (disk).** 30s TTL. |
| Unread `states.*` crumbs on `/api/state` | **Landed (disk).** `_states_view` is panel keys only. `t3_kind` stays on `as_dict` (status contract). |
| `/api/state` `terminal_info` every poll | **Landed (disk).** 5s TTL, search still serves cache. |
| F11 `AI_SETTING_FIELDS` / `SYS_FIELDS_ADVANCED` | **Closed (catalog).** 0 panel builders by design; FIELD_HELP pin still keys them. Not deleted. |
| F1 search coverage / F2 family churn | **Won't-do unasked.** Yellow: shrink axes / min-trades apply gate. Quarantine stays the broken-family valve. |
| F4 this PID vs disk | **Operational.** Restart after flat. |
| F6 entry-gate cache | **Won't-do until F1/F2.** Idle 5.4 ms. |
| F7 spread 237 refuses | **Won't-do.** No counterfactual. Do not loosen. |
| F8 `watch_pf=1.0` / AI allowlist | **Won't-do.** Design (protection while book is red). Allowlist stays `{enabled}`. |
| F9 grid HTTP lock | **Closed (intentional).** HTTP=panel. F1 if ever taken is code-side. |
| Unreachable HTTP 409 after allowlist | **Keep.** Defense. |
| Capacity N× margin / `_harvest_view` autopsy | **Won't-do until measured.** TTL 3s already; n=23 vs cap 2000. |
| Daily-loss UI + `daily_loss_flatten` unread | **Landed (disk).** Flatten always when stored halt fires. `daily_loss_pct=0` is operator cancel (no halt). Pin `test_daily_loss_halt_actually_flattens`. |
| Concurrent 1R unread + chip gone; margin on Sistem | **Landed (disk).** `can_open` does not read `max_concurrent_risk_pct`. HTTP: `max_margin_usage_pct` writable. `_note_risk_capacity` no-op. |
| Symbol card hours-only; `risk_percent` HTTP 400 | **Landed (disk).** `POSITION_SECTION` gone. Stored % still sizes lots. Pin `test_account_sizes_the_book` / `test_position_sizing_is_not_writable`. |
| AI Global Lot Carpani card | **Landed (panel).** Five AI cards one row. Throttle still on Gün `lot x` + table. Not system `lot_multiplier`. |
| `_symbol_daily_halt` getattr | **Landed.** `:4168` `getattr(..., 0.0)`. `:4198` still naked (field always on `SymbolConfig`). |

### Still open

Unpaid measured won't-dos: Numba if `OPT_FIELDS` 3×; O-1 if 2000-row autopsy
cap is hot. Harvest-on / BE 0.5 / `max_positions`→1 stay **won't-do**
(evidence, not a lock). F1+F2 together if the operator wants a search
redesign (yellow).

Operational **20:40:** a **manual** search is **running** (`apply_best`,
all 6 symbols, 160k/3.08M, current GER40/JPN225/NAS100). Do **not**
restart while 7 tickets are open. Do **not** cancel that job unasked.
GER40 pending 1.0/0.3/1.2 **already on the live row** (`pend {}`);
shakeout still overlays next-entry SL to 2.0. This PID still PATCHes
exits; **next boot is 400**. Do not PATCH `max_margin_usage_pct`
unasked. Do not add `/exit-override`. Do not kill orphan pythonw
workers while the book is open.

Panel-lie leftovers (no code tonight): `risk_sembol_limiti` 209 events
/ 73k retries are **historical** (producer gone); `field_help.js`
`lot_mode`/`fixed_lot` still describe a switch; capacity still ships
unread `max_concurrent_risk_pct=30`; `size_by_edge` still **on** with
no dial. Search `max_open=1` vs live stacking to `max_total_positions=100`.


**Live (16:40, then Claude 16:46):** day **−$169.19 / 25 / WR 20%**.
GER40 **8/0 −$122.66**. Idle `last_cycle_ms` **5.4**. No 27.08 ERROR.

Claude 16:4x: claim 3 JS "Safe delete" list is **wrong** (would
`ReferenceError` / miss Python). `SWING_OVERLAY` is assigned but
unread (`#opt-grid` gone). Cash_flow waste is **every-cycle
frequency**, not the two-call shape. GER40 exits are **6 sl + trail
+ flatten**, not 6/6 orig-SL.

---

## 27.08 20:40 — Evening-strip A–Z (Claude 20:35 + live book + dirty tree)

Independent Cursor pass. Did **not** patch, restart, cancel the search, or
commit. GET `/` then `/api/state` `/api/symbols` `/api/analysis/*`.
Claude 20:35 arithmetic (100 slots / ~80% theoretical 1R) **accepted**.
`last_cycle_ms` **7–9** (search busy; snapshot last-cycle book).
`last_error` empty. **No `ERROR` line on 27.08** in `logs/micofx.log`.

**Live (20:39 broker):** demo 61562752. Balance **$1944** / equity **$1966**
/ floating **+$21**. Day realised **−$200.15** / 30 closes / WR **20%** /
`pnl_pct` **−8.26%**. Halt **false** (`daily_loss_pct=0`). AI enabled,
`risk_scale` **0.60** enforced. 7 open: NAS100×2 buy, US30×2 sell,
GER40 buy, JPN225 buy, SpotBrent sell. All have broker SL. Reverse
signals on GER40/JPN/NAS blocked (`ters yonde acik pozisyon var`).
**`opt.state=running`** source=manual `apply_best` 160000/3081600.

Book families: 4× `stoch_flip`, XAU `burst` M15, Brent `parabolic_flip`
M15. Unused live: `mtf_pullback` `dual_t3` `t3_flip` `aroon_flip`
`ichimoku`. All `risk_percent=0.8`, `symbol_daily_loss_pct=0`.
GER40 exits **1.0 / 0.3 / 1.2** (pending applied). Harvest off.
Partial on five names. `size_by_edge=True` still read. `lot_multiplier=1.0`.

Today cash: GER40 10/0 **−$142.38** (8 orig-SL + 2 trail, **−9.24 R**);
JPN225 11 **−$64.92** (−6.68 R, 6 orig-SL); US30 −$1.18; NAS −$0.60;
XAU **+$8.97**. Autopsy window n=229: SL 131 / trail 63 / flatten 35.
After-1h on SL: 75/131 through entry, 87 recovery ≥0.5 R (shakeout
thesis still live; not a silent patch).

### 1) Optimization Summary

* **Health:** Idle cycle is paid (~8 ms) even under a 14-worker search
  because `/api/state` serves the last cycle book. Today's −$200 is
  **book + operator cancel of the daily halt**, not a new engine leak.
  GER40 `stoch_flip` 1.00 ATR stop is eating the day (8 orig-SL). Dead
  `risk_sembol_limiti` is a **panel lie**, not a live gate.
* **Top 3 highest-impact (none is a silent CPU patch):**
  1. Keep the open book. Restart first-sights stops **and** would collide
     with a running `apply_best` search.
  2. After **flat only**: decide whether `daily_loss_pct=0` stays (day
     already −8.26% with no flatten). Restoring 3% is yellow/red.
  3. After quiet: drop or relabel historical `risk_sembol_limiti` /
     `risk_eszamanli` so Eleme Kapilari stops ranking a deleted gate #2
     (209 events / 73k retries). Reset vs mapping delete vs "kalktı".
* **Biggest risk if no changes:** Operational. Search `max_open=1`
  `apply_best` can land new params onto a book that now **stacks** to
  100. Panel still teaches leftover slot limits. Day can keep bleeding
  with no halt.

### 2) Findings (Prioritized)

* **Title** Live search running (`apply_best`, 3.08M combos)
* **Category** Concurrency / Reliability
* **Severity** High (operational)
* **Impact** MT5 lock chunks; apply waits on open tickets; next-boot
  HTTP 400 vs this PID still PATCHing exits
* **Evidence** `GET /api/state` `opt.state=running` source=`manual`
  `done=0/6` `combo_done=160000` `combo_total=3081600` current
  GER40,JPN225,NAS100. Cursor did **not** start it.
* **Why it’s inefficient** Search scores `max_open_from_cfg` = **1**
  (`backtest.py:428-436`). Live `can_open` stacks same-side until
  total/margin/reverse/STOPSUZ. Holdout cannot see tonight's 7-ticket
  book.
* **Recommended fix** Do not cancel unasked. After this job: either
  keep paper honest (max_open=1) and accept live stacking as unmeasured,
  or yellow-open a stacking search. Do not apply a 1-slot score onto
  a 100-slot book without saying so.
* **Tradeoffs / Risks** Cancelling wastes 160k already scored. Letting
  `apply_best` land on first flat changes GER40/NAS/JPN under a red day.
* **Expected impact estimate** Correctness, not ms.
* **Removal Safety** Needs Verification (job is live)
* **Reuse Scope** optimizer + risk

* **Title** `daily_loss_pct=0` — day −8.26% with no halt
* **Category** Reliability / Cost (capital)
* **Severity** High (policy, not a bug)
* **Impact** Counterfactual: leftover default 3% of ~$2423 start ≈ **$73**.
  Realised already **−$200**. Flatten-always is wired but never trips.
* **Evidence** `system.daily_loss_pct=0`, `day.halted=false`,
  `DailyGuard.check` `risk.py:263` requires `> 0`. Operator cancelled
  the panel dial 27.08 evening.
* **Why it’s inefficient** N/A — intentional. The inefficiency is
  **communication**: capacity/brain still mention a limit that cannot fire.
* **Recommended fix** None unless the operator wants the brake back.
  Do not silently restore 3%.
* **Tradeoffs / Risks** A 3% halt would have flattened winners too
  (US30/NAS/XAU still trading).
* **Expected impact estimate** Would have capped today near −$73 vs −$200
  (**likely**, start_balance inferred from pnl_pct).
* **Removal Safety** Needs Verification
* **Reuse Scope** system leftover

* **Title** Dead `risk_sembol_limiti` / `risk_eszamanli` still ranked
* **Category** Frontend / Maintainability
* **Severity** High (operator model)
* **Impact** Eleme Kapilari: spread 241, **sembol limiti 209**, ters 148.
  Retries **73k / 32k**. Producer strings gone from `can_open`.
* **Evidence** `engine.py:152` mapping; `can_open` `risk.py:549-603` has
  no `"sembol pozisyon limiti"` / `"eszamanli risk limiti"`. Claude 20:35.
  Live stacking: NAS100×2 US30×2 with leftover `max_positions` 5/5 unread.
* **Why it’s inefficient** Historical counters look like a live gate.
  Same class as `daily_loss_flatten` visible-but-unread /
  `size_by_edge` hidden-but-on.
* **Recommended fix** Pick one after quiet: drop needles from
  `_RISK_BLOCK_KEYS`; or one-shot `POST /api/analysis/entry-blocks/reset`;
  or panel suffix "(kalktı)". Do not reset during a search.
* **Tradeoffs / Risks** Reset wipes spread/ters history too.
* **Expected impact estimate** Zero latency. Stops a false #2 cause.
* **Removal Safety** Likely Safe (mapping) / Needs Verification (reset)
* **Reuse Scope** engine.py + panel analysis

* **Title** Search vs live stacking (paper 1, live 100)
* **Category** Algorithm
* **Severity** High (edge measurement)
* **Impact** Holdout/net R do not include overlapping same-side tickets.
  Live theoretical 100 × 0.8% = **80% 1R** before AI 0.60 → ~48%;
  `size_by_edge` (on, ×2.2 cap) can pull up. Margin 90% binds ~175
  lots at $10/pos — **100 binds first**. Claude 20:35.
* **Evidence** `max_open_from_cfg` returns 1. `max_total_positions=100`.
  `max_positions` leftover unread. Open 7 / concurrent risk **1.59%**.
* **Why it’s inefficient** Two different products. Apply() of a 1-slot
  winner onto a stacking book is an untested regime.
* **Recommended fix** Yellow, operator. Do not teach search stacking
  tonight. Do not restore leftover `max_positions` as a silent gate.
* **Tradeoffs / Risks** Restoring slots re-opens the 209-block lie as a
  real gate (US30 slot-2 overlap was +4.62 R, closed won't-do).
* **Expected impact estimate** Unknown without a stacking walk-forward.
* **Removal Safety** Needs Verification
* **Reuse Scope** backtest + risk

* **Title** GER40 `stoch_flip` 1.0 ATR orig-SL cluster
* **Category** Algorithm / Cost
* **Severity** High (today's cash)
* **Impact** Today −$142 / −9.24 R; window −$161 / −8.52 R (n=37).
  Shakeout 3/10 orig-SL → next entry SL **2.0** (this PID has the helper).
  Floor wears winners (Cursor 19:10); does not save 8 already dead.
* **Evidence** Autopsy today GER40 8 `exit_reason=sl` with `sl==original_sl`.
  Live row `sl_atr_mult=1.0` trail 0.3/1.2 BE 1.5 partial 1.5. Open GER40
  SL **above** entry (trail in profit) — floor is next-entry only.
* **Why it’s inefficient** Search prefers 1.0. Shakeout is a live overlay
  the grid never paid for. Trail 0.3 starts inside a 1.0 stop.
* **Recommended fix** Let the running search finish. Do not PATCH SL.
  Do not disable the floor. Three-arm diagnostic (gates/floor/both)
  stays designed, not a patch.
* **Tradeoffs / Risks** `apply_best` may write another 1.0 onto GER40
  on first flat.
* **Expected impact estimate** Floor: losers stay −1 R; winners haircut
  when 2.0 binds (qualitative, 19:10).
* **Removal Safety** Needs Verification
* **Reuse Scope** risk.shakeout_sl_atr_mult

* **Title** `size_by_edge` on, dial gone
* **Category** Maintainability
* **Severity** Medium
* **Impact** Lots still × holdout net R / maxDD (`risk.py:335`).
  Panel has no switch. HTTP 400. Capacity footnote still prints it.
* **Evidence** `GET /api/state` `system.size_by_edge=true`. Claude 20:05
  asked if hiding it is a lie — **yes, still-read**.
* **Why it’s inefficient** Operator cannot see the multiplier except
  in a capacity sentence.
* **Recommended fix** After quiet: either force `False` in Store
  (yellow — changes lots) or a read-only chip. Do not HTTP-open it.
* **Tradeoffs / Risks** Turning it off shrinks names the stamp likes.
* **Expected impact estimate** Live lots move; idle ms unchanged.
* **Removal Safety** Needs Verification
* **Reuse Scope** Store leftover

* **Title** GET still dumps leftover asdict
* **Category** Network / Frontend
* **Severity** Low (n=6 symbols)
* **Impact** `/api/symbols` `/api/system` `/api/state.system` still
  carry `lot_mode` `fixed_lot` `max_lot` `max_positions`
  `max_concurrent_risk_pct` `daily_loss_flatten`. Capacity still
  ships unread `max_concurrent_risk_pct=30`.
* **Evidence** `app.py` `to_dict()` / `risk.py:837`.
* **Why it’s inefficient** Agents/panel can still *see* dead knobs
  and assume they bind. Tiny JSON.
* **Recommended fix** After next boot: slim snapshot to panel keys
  (same pattern as `_states_view`). Keep GET schema for apply/readout.
* **Tradeoffs / Risks** A reader using full GET as the contract.
* **Expected impact estimate** <1% payload. Clarity, not latency.
* **Removal Safety** Likely Safe if tests pin the slim set
* **Reuse Scope** web/app.py + risk.capacity

* **Title** `field_help.js` lot_mode / fixed_lot lie
* **Category** Maintainability
* **Severity** Low
* **Impact** Hover catalog describes a mode switch that HTTP 400s.
* **Evidence** `field_help.js:4-5` vs `lot_for` always risk%.
* **Recommended fix** Rewrite help to "Kartta yok / okunmaz" like
  `max_lot`. Pin `test_sys_hint`.
* **Tradeoffs / Risks** None.
* **Expected impact estimate** Zero runtime.
* **Removal Safety** Safe
* **Reuse Scope** field_help.js
* **Reuse Opportunity** same sentence as `risk_percent` help

* **Title** `_symbol_daily_halt` `:4198` naked attr
* **Category** Reliability
* **Severity** Low
* **Impact** Stubs without the field: `:4168` returns early; if that
  `<= 0` guard ever changes, `:4198` AttributeError. Production
  `SymbolConfig` always has the field (all 0.0 live).
* **Evidence** `engine.py:4168` vs `:4198`. Claude 20:35.
* **Recommended fix** One `getattr` at `:4198` when touching the
  function. Not tonight.
* **Removal Safety** Safe
* **Reuse Scope** engine.py local

* **Title** `AI_SETTING_FIELDS` / `GET /api/symbols/lot-mode-check`
* **Category** Dead Code
* **Severity** Low
* **Impact** Catalog with zero panel builders (FIELD_HELP pin).
  lot-mode-check name leftover; logic is min-lot overshoot.
* **Evidence** Closed ledger F11. Do not delete the const.
* **Recommended fix** Rename the path later. Keep the catalog.
* **Removal Safety** Needs Verification (help pin)
* **Reuse Scope** app.js / app.py

* **Title** Unused live families
* **Category** Algorithm
* **Severity** Medium (search cost, not idle CPU)
* **Impact** 8 families in `STRATEGIES`. Live book uses 3
  (`stoch_flip` `burst` `parabolic_flip`). Search still pays the
  other 5 × TF × refine. Running job `strategies=[]` inherits the
  saved list — likely all 8.
* **Evidence** `models.py:538-541`. Combo bar 3.08M.
* **Why it’s inefficient** Grid cost on families with no live
  symbol. ichimoku stayed for GER holdout evidence (closed ledger).
* **Recommended fix** `POST /api/opt/run` `strategies` one-off
  (already). Do not persist a subset into `opt_params` unasked.
  F1/F2 yellow if shrinking axes.
* **Tradeoffs / Risks** Dropping ichimoku without a new holdout.
* **Expected impact estimate** Combo wall-clock, not cycle ms.
* **Removal Safety** Needs Verification
* **Reuse Scope** opt_params

* **Title** After-1h SL recoveries (missed MFE, not harvestable)
* **Category** Algorithm
* **Severity** Medium (already measured)
* **Impact** 131 SL; 75 through entry in 1h; 87 recovery ≥0.5 R.
  `left_on_table_r` window **95 R** includes losers; panel masada
  is winners-only. Do not sum autopsy `kar` across flatten-empty
  profit rows.
* **Evidence** `/api/analysis/trade-autopsies` 20:39. Constitution.
* **Recommended fix** Shakeout floor is the live answer. Do not
  add an adverse-fill entry gate. Do not harvest-on (won't-do).
* **Tradeoffs / Risks** Wider SL haircuts wins (19:10).
* **Expected impact estimate** Already on the closed ledger.
* **Removal Safety** Needs Verification
* **Reuse Scope** autopsy + shakeout

* **Title** `models.py` comment still says concurrent 1R
* **Category** Maintainability
* **Severity** Low
* **Evidence** `models.py:163-164` "stacks until concurrent 1R /
  total / margin". `can_open` does not read 1R.
* **Recommended fix** Comment-only when next touching the block.
* **Removal Safety** Safe
* **Reuse Scope** models.py

### 3) Quick Wins (Do First)

* After this search + flat: rewrite `lot_mode`/`fixed_lot` help
  (Safe). `getattr` on `:4198` (Safe). Comment fix on `models.py`.
* After quiet: label or drop dead `_RISK_BLOCK_KEYS` needles
  (Likely Safe). Do **not** reset counters during the running job.
* Do not restore daily-loss or per-symbol slots unasked.

### 4) Deeper Optimizations (Do Next)

* Yellow: stacking walk-forward vs keep paper `max_open=1`.
* Yellow: `size_by_edge` on/off as an explicit operator decision.
* Slim GET leftover keys (same pattern as `_states_view`).
* Restart/shutdown **409** if bot-owned tickets exist (security #1).
* Pin Origin to loopback URLs (security #2) — not tonight.
* F1/F2 search-axis shrink only if the operator wants a redesign.

### 5) Validation Plan

* Idle: `last_cycle_ms` before/after any snapshot slim (now 7–9
  under search; 5.4 was idle 16:40).
* Book: day realised vs autopsy today cash (GER −142.38 matches).
* Gates: POST `risk_percent` / `max_positions` / `daily_loss_pct`
  → 400 (this PID may still 200 until restart).
* Shakeout: next GER40 WARN `stop 1->2 ATR` in `micofx.log`.
* Search: when `opt.state` leaves `running`, confirm `apply()`
  waited on the 7 opens.
* Tests already green for the evening strip (account_sizes,
  hands_off, fixed_mode, atr mid-trade, panel names). Full pack
  last Claude **2580 passed**.

### 6) Optimized Code / Patch

**None applied.** Notes only.

### SECURITY AUDIT: dirty tree (`122e434` + 146 files)

**Risk Assessment:** Medium-Low for the localhost operator model.
No SQLi, no secrets, Origin+allowlist+`esc()` landed. Residual is
trading-integrity races and Host-mirrored Origin.

#### Findings

* **Restart/shutdown ignore open positions** (Severity: High integrity)
* **Location:** `micofx/web/app.py` `app_restart` / `app_shutdown`;
  panel `confirm()` only
* **The Exploit:** Authenticated `POST /api/app/restart` while 7
  tickets are open → `stop(close_positions=False)` → trail/BE dies;
  broker SL remains. Violates AGENTS.
* **The Fix:** 409 if bot-owned positions exist. Do not ship tonight
  (a search is also running).

* **Origin allowlist mirrors Host** (Severity: Medium)
* **Location:** `app.py` ~601-607
* **The Exploit:** DNS-rebinding CSRF class against panic/close/restart.
  SameSite helps ordinary cross-site; not rebinding on the rebound name.
* **The Fix:** Pin `http://127.0.0.1:8900` + `http://localhost:8900`.

* **Orphan sweeper PowerShell `-Command` paths** (Severity: Low)
* **Location:** `gece_restart.py` ~102-113
* **The Exploit:** Quote-break if `sys.executable` contains `'`.
* **The Fix:** `-File` + parameters; reject quote/backtick/newline.

* **Unauthenticated `/openapi.json`** (Severity: Low)
* **Location:** `docs_url=None` but `openapi_url` still default
* **The Fix:** `openapi_url=None`.

* **`mt5_terminal_path` any existing `.exe`** (Severity: Low, conditional)
* **Location:** system allowlist + `ensure_terminal_process`
* **The Fix:** Require `terminal64.exe` basename. `autostart_mt5` is
  hands-off but still stored.

#### Observations

* Localhost trust is by design (any local process `GET /` then Origin).
* `aiHoursCell` hour strings unescaped — numeric hours only.
* `X-Mico-Token` still Origin-gated on mutations.
* No second sqlite writer in the dirty tree.

### AGENTS.md rewrite (do **not** apply tonight)

Optimization prompt forbids shipping AGENTS.md. Signal-density
fixes if the operator asks later:

* HTTP writes: add backup dir/secondary/keep + `mt5_terminal_path`
  (code already allows them; current bullet understates).
* Symbol POST already lists sessions/`enabled`/`group`/`broker_symbol`;
  add `use_sessions` / `trade_days` / `flat_before_close_min` or say
  "hours block".
* Drop leftover "concurrent 1R" mental model; `can_open` is reverse /
  total / scalp-swing-if-nonzero / margin / STOPSUZ.
* `risk_percent` already 400 — keep.
* Known gotcha: this PID vs next-boot 400; running search + stacking.
* Do not paste the optimization/security prompts into AGENTS.md.

---

## 27.08 16:40 — A–Z hard test (book, dead surface, lock, HTTP, security)


Independent Cursor pass after HTTP=panel land. Did not re-open the closed
ledger. Live GET `/` then `/api/state` (session). `last_cycle_ms` **5.4**.
`last_error` empty. **No `ERROR` line on 27.08** in `logs/micofx.log`.
AI `risk_scale` **0.60** (daily-loss floor). Opt not busy.

**Live (16:40):** demo book. Day realised **−$157.75** / 23 closes / WR
21.7% / DD **−7.36%**. Floating ~flat. 4 open: GER40 buys #367303567
#367334015 #367492600 (live SL 2.0 / 0.5/2.2, pending 1.0/0.3/1.2) and
JPN225 sell #367498872 (+). Shakeout / prefetch / slim poll / HTTP 400
**not in this PID**.

### 1) Optimization Summary

* **Health:** Idle hot path is paid (5.4 ms). Today's losses are **book**,
  not a new engine leak: GER40 6/6 original-SL (−$111.22) and JPN225
  (−$63.15). XAU +$18.40 is the only real offset. Dual `history_deals_get`
  and unread `/api/state` crumbs are real code, **not** today's 5.4 ms.
* **Top 3 highest-impact (none is a silent CPU patch):**
  1. Keep the open book. Restart would first-sight stops **and** close the
     HTTP exit door on the same boot.
  2. After **flat + restart only**: confirm shakeout WARN, prefetch log,
     slim payload, HTTP 400 on family/exit, `raw/floor` vs `volume_min`.
  3. Dead opt-grid / `SWING_OVERLAY` / `SYS_DANGER_NOTES` JS — Safe delete
     when quiet. Maintainability, not latency.
* **Biggest risk if no changes:** Operational, not CPU. GER40 pending
  1.0/0.3/1.2 lands on flat via `apply()`. Shakeout lifts next-entry SL
  to 2.0; trail 0.3/1.2 has no floor and no HTTP PATCH after next process.
  Harvest-on / BE 0.5 / `max_positions`→1 stay won't-do.

### 2) Findings (Prioritized)

* **Title** GER40 original-SL cluster is the day
* **Category** Reliability (book, not code)
* **Severity** High (cash) / Low (code)
* **Impact** Closed −$111.22 of −$157.75. 6/6 unmoved ~1.0 ATR stops
  before the 11:29 panel bump to SL 2.0.
* **Evidence** Autopsy 23 rows = `day.closed_trades`. GER40 n=6 WR 0/6
  orig-SL 6/6. Live tickets still on 2.0/0.5/2.2. Pending queued 14:28.
* **Why it’s inefficient** Not CPU. Six signals died on first-sight SL
  before the floor existed in this PID.
* **Recommended fix** None now. Shakeout floor is on disk for the **next**
  entry. Do not PATCH trail unasked. Do not flatten the 3 open buys.
* **Tradeoffs / Risks** Pending 1.0/0.3/1.2 still apply()s on flat.
* **Expected impact estimate** Cash already spent. Floor is next-entry only.
* **Removal Safety** n/a
* **Reuse Scope** n/a

* **Title** Dual `history_deals_get` per cycle + every 5s
* **Category** I/O / Concurrency
* **Severity** Medium (likely under search; idle cycle is 5.4 ms)
* **Impact** MT5 lock hold vs trail/modify / `/api/state`
* **Evidence** `_refresh_cash_flow` every `_cycle` → `cash_flow_since`
  `engine.py:843` / `mt5client.py:1149`. `day_stats()` 5s cache miss →
  `deals_since` `engine.py:854` / `mt5client.py:1089`. Same day window,
  two filters (external types vs entry types). Older pass already named
  `day_stats` in snapshot; **cash_flow has no TTL**.
* **Why it’s inefficient** Two IPC history pulls overlap. Correctness needs
  both numbers (breaker vs day table).
* **Recommended fix** One `history_deals_get`, split in-process. Or TTL
  cash_flow to the same 5s as day_stats. Measure lock hold first.
* **Tradeoffs / Risks** Deposit-as-profit breaker (13.08 +499.96) must not
  see a stale 0. Fail-closed `None` on history miss stays.
* **Expected impact estimate** Likely ms on idle (already 5.4). High if
  history stalls during a 14-worker search.
* **Removal Safety** Needs Verification
* **Reuse Scope** `mt5client` + `engine._cycle`

* **Title** `/api/state` always calls `terminal_info`
* **Category** Concurrency
* **Severity** Medium (likely)
* **Impact** Snapshot vs `_cycle` lock
* **Evidence** `_panel_terminal_flags` `engine.py:4061-4070` — busy-search
  reuses cache; idle poll always `terminal_flags()` → `mt5.terminal_info()`
  `mt5client.py:571-575`. Positions/account already reuse the cycle book.
* **Why it’s inefficient** Flags change rarely; poll is 3s.
* **Recommended fix** TTL (seconds) like capacity. Measure `/api/state`
  wall vs cycle lock wait.
* **Tradeoffs / Risks** Stale `trade_allowed` for one poll.
* **Expected impact estimate** Likely small idle; lock wait under search.
* **Removal Safety** Needs Verification
* **Reuse Scope** snapshot path

* **Title** Dead opt-grid / reset / `SWING_OVERLAY` JS
* **Category** Frontend / Dead Code
* **Severity** Medium (maintainability)
* **Impact** Bundle noise; false "grid still writable" reading
* **Evidence** HTML has no `#opt-grid` / `#opt-settings-advanced` /
  `#btn-opt-reset` (pin `test_hands_off_controls_are_not_on_the_panel`).
  JS still: `OPT_SETTING_FIELDS_ADVANCED=[]` `app.js:1308`; `SWING_OVERLAY`
  `1310-1361`; `[data-grid-key]` collect `1442`; gated reset POST `2823`.
  API reset already 400 `app.py:1797`.
* **Why it’s inefficient** Dead branches after HTTP=panel.
* **Recommended fix** Delete the empty advanced loop, overlay flag, grid
  collect, reset click. Keep GET `swing_overlay` until JS gone, or drop
  both together.
* **Tradeoffs / Risks** None if HTML stays grid-free (pinned).
* **Expected impact estimate** Zero runtime.
* **Removal Safety** Safe
* **Reuse Scope** `app.js` + `GET /api/opt/params` flag

* **Title** Unread `/api/state` crumbs after the 15:16 strip
* **Category** Network / Frontend
* **Severity** Low–Medium
* **Impact** Payload size (this PID still fat; disk already dropped
  `cash_flow`/`floating`/`poll_interval_sec`)
* **Evidence** Panel never reads: `mt5.session_clock_skew_hours` (only
  `session_clock_warning`); `day.wins`/`losses`/`day_key`/`start_balance`;
  `states.*.last_bar`/`t3`/`t3_kind`/`signal_source`/`primary_signal`/
  `spread`/`last_signal_at`; `execution.tracked`. Live table uses
  `atr/adx/t3_rising/htf/k/d/signal/bars_ready/note/session/spread_atr`.
* **Why it’s inefficient** JSON work every 3s for unused keys.
* **Recommended fix** Strip from `as_dict` / payload only. Keep engine attrs.
* **Tradeoffs / Risks** External GET `/api/state` readers (Claude panel
  probe). Pin like `test_unread_payload_keys_are_gone`.
* **Expected impact estimate** Qualifies the 99 KB → ~35 KB claim; leftover
  crumbs are the rest.
* **Removal Safety** Needs Verification
* **Reuse Scope** snapshot

* **Title** `_FALLBACK_PATHS` empty constant + `SYS_DANGER_NOTES={}`
* **Category** Dead Code
* **Severity** Low
* **Impact** None
* **Evidence** `mt5client.py:21` never read. `app.js:1868-1878` `syncSysDangerNotes`
  no-op (empty map).
* **Why it’s inefficient** Leftover scaffolding.
* **Recommended fix** Delete with a pin, or leave as documented empty.
* **Tradeoffs / Risks** None.
* **Expected impact estimate** Zero.
* **Removal Safety** Safe
* **Reuse Scope** local file

* **Title** `backup_dir_allow_unc` still HTTP-writable, not on panel
* **Category** Security / Cost
* **Severity** Medium
* **Impact** Origin-bearing agent can latch UNC backup without a control
* **Evidence** `_OPERATOR_SYSTEM_FIELDS` `app.py:425`. `BACKUP_FIELDS` only
  dir/secondary/keep `app.js:1862-1866`. Gate reads it `app.py:1614`.
* **Why it’s inefficient** Visibility ≠ lock leftover after HTTP=panel.
* **Recommended fix** Drop from allowlist (400) unless operator needs UNC.
  UNC dest tests stay on Store / allow-flag in DB.
* **Tradeoffs / Risks** Legitimate UNC backup then needs a Store write or
  a new panel toggle (yellow).
* **Expected impact estimate** Attack surface, not latency.
* **Removal Safety** Needs Verification
* **Reuse Scope** `POST /api/system`

* **Title** Unreachable HTTP 409/grid validators after allowlist
* **Category** Dead Code
* **Severity** Low
* **Impact** None while allowlist holds
* **Evidence** Hands-off fires first (`app.py:894`, `1765`). Magic/strategy/
  `EXIT_RISK` 409 and opt `_exit_axes` never see a panel body.
* **Why it’s inefficient** Dead defense, not a leak.
* **Recommended fix** Keep. Apply() and allowlist regression still need them.
* **Tradeoffs / Risks** Deleting them re-opens the hole if allowlist slips.
* **Expected impact estimate** Zero.
* **Removal Safety** Needs Verification (do not delete)
* **Reuse Scope** `web/app.py`

* **Title** Capacity N× `order_calc_margin` / tick under lock
* **Category** Concurrency
* **Severity** Medium (likely) — already TTL 3s
* **Impact** Lock vs `_cycle` when ticket/volume sig changes
* **Evidence** `engine.py:4072-4096`, `_CAPACITY_TTL=3s`. Not new; still
  the rebuild path when not `optimizer.busy`.
* **Why it’s inefficient** 6 symbols × margin+tick on sig change.
* **Recommended fix** Measure first. Do not add a second `initialize()`.
* **Tradeoffs / Risks** Stale lot gauges.
* **Expected impact estimate** Likely small on this 6-name book.
* **Removal Safety** Needs Verification
* **Reuse Scope** snapshot / `risk.py`

* **Title** `_harvest_view` full autopsy every poll
* **Category** CPU / Alloc
* **Severity** Low today (n=23; cap 2000)
* **Impact** `/api/state` CPU
* **Evidence** `engine.py:3975-4008` → `trade_autopsy_report()` then drops
  rows, keeps aggregates. Called from snapshot ~3s.
* **Why it’s inefficient** Builds `rows` then throws them away.
* **Recommended fix** Aggregate-only helper. Measure when n approaches 2000.
* **Tradeoffs / Risks** O-1 still won't-do until cap is hot.
* **Expected impact estimate** Qual; idle 5.4 ms says not today.
* **Removal Safety** Needs Verification
* **Reuse Scope** snapshot

### 3) Quick Wins (Do First)

* Delete dead opt-grid / `SWING_OVERLAY` / empty `SYS_DANGER_NOTES` JS
  (Safe, pinned HTML absence).
* Drop `_FALLBACK_PATHS` or leave documented empty.
* Do **not** restart, flatten, harvest-on, BE 0.5, cut `max_positions`.
* Operator still owns: GER40 trail recovery door vs this-PID PATCH window.

### 4) Deeper Optimizations (Do Next)

* Share one `history_deals_get` between cash_flow and day_stats (identity
  tests on the 13.08 deposit case).
* TTL `terminal_flags` on `/api/state`.
* Strip remaining unread snapshot keys after the next process confirms
  the first crumb strip.
* Incremental `IndicatorCache` / Numba — still won't-do at 2.57 / 6.53 ms
  until grid 3×.

### 5) Validation Plan

* Idle: `bot.last_cycle_ms` (now 5.4) and `/api/state` wall. No `ERROR`
  on the day file.
* After restart (flat only): shakeout WARN on next GER40 entry; prefetch
  log line; opt poll without `top`/`baseline`; HTTP 400 on `sl_atr_mult`
  / `grid` / reset; payload KB; log disk still writes from `run.py`.
* Dual history: count `history_deals_get` per `_cycle` vs per snapshot.
* Correctness: deposit cash_flow ≠ 0 still disarms DailyGuard the same way;
  day `closed_trades` still matches autopsy n; fill-next-open WF unchanged.
* Panel: 13 chips / 7 tabs still render after JS delete.

### 6) Optimized Code / Patch

Not applied (operator: notes only). Candidates if asked:

* `saveOptParams` drop `[data-grid-key]` block; drop `SWING_OVERLAY` assign.
* `_OPERATOR_SYSTEM_FIELDS` minus `backup_dir_allow_unc`.
* `cash_flow_since` + `deals_since` share one raw history list.

### Strategy reverse (27.08 closed book)

Masada = winners only. R = `|entry − original_sl|`. `mfe_r` not harvestable.
Keep-lines are `taze test`, not a live replay.

| Symbol | Family/TF | n | Cash | Orig-SL | Reverse |
|---|---|---|---:|---:|---|
| GER40 | stoch_flip M30 | 6 | −111.22 | 6/6 | Skip-all = +111 arithmetic, not WF. Pending 1.0/0.3/1.2 **unverifiable** (six already dead; 3 opens still on 2.0). |
| JPN225 | stoch_flip M15 | 9 | −63.15 | 5 | Search weaker, **not applied**. |
| US30 | stoch_flip M30 | 5 | −1.18 | 3 | Afternoon M30. Slot-2 cut stays won't-do. |
| NAS100 | stoch_flip M30 *now* | 2 | −0.60 | 1 | Both closes were **mtf_pullback**. New family: 0 closes. |
| XAUUSD | burst M15 | 1 | +18.40 | 0 | Kept (age 48h). |
| SpotBrent | parabolic_flip M15 | 0 | 0 | — | 4 SIGNAL, **no** today block log. Do not invent misses. |

Opt apply: GER40 exits pending; NAS100 family live 15:56; other four incumbent.

### SECURITY AUDIT: HTTP=panel + leftover JS + disk-off log

**Risk Assessment:** Low (write surface shrank). Residual Medium: UNC latch.

#### **Findings:**

* **Hidden UNC latch still Origin-POST writable** (Severity: Medium)
* **Location:** `micofx/web/app.py` `_OPERATOR_SYSTEM_FIELDS` / `patch_system`
* **The Exploit:** Same-origin agent POSTs `backup_dir_allow_unc:true` then a
  UNC `backup_dir`. Panel has no control. Backup job then writes off-box.
* **The Fix:** Drop the key from the allowlist (400) unless operator wants
  a visible toggle.

* **Restart closes exit PATCH** (Severity: Low / operational)
* **Location:** allowlist minus `EXIT_RISK_FIELDS`; this PID still old
* **The Exploit:** n/a. Side-effect: GER40 trail 0.3/1.2 cannot be typed
  back after next boot.
* **The Fix:** Operator door (apply / this-PID PATCH / explicit override).
  Do not reopen the allowlist unasked.

#### **Observations:**

* Origin on every mutation intact. Session cookie HttpOnly + SameSite=Strict.
* SQL still parameterized. `el({html})` still gone.
* No secrets in the working-tree web diff.
* Unreachable 409 paths are defense-in-depth, not a bypass.
* `OptRun.force` / `bars` still accepted; panel does not send them. Keep
  for one-off search, do not dump into `_INTERNAL_ONLY_FIELDS`.

### Checked, not a finding

Closed ledger still holds. No 27.08 ERROR. Incremental indicators / Numba
won't-do. Harvest / BE 0.5 / max_positions→1 won't-do. Adverse-fill gate
won't-do. Calendar reopt gone. `GET /api/schema` kept on purpose.
`AI_SETTING_FIELDS` kept for FIELD_HELP. 409 exit guards kept. Apply()
still writes `OPT_FIELDS`. Fill-verify sleeps stay. No second
`initialize()`.

---

## 27.08 15:16 — A–Z hard test (dead UI, PnL reverse, API, security)

Independent Cursor pass. Did not trust 26.08 21:57: grepped retired
families, unused JS, Origin, live GET `/` then `/api/state`, cycle ms,
today's ERROR lines, dirty-tree mutation surface. Claude 15:03 already
cleared readout+queue and Drive backup; this pass adds leftover UI and
per-symbol reverse.

**Live (15:16):** demo `61562752` @ Pepperstone-Demo. Bot running, MT5
connected, `last_cycle_ms` **4.4**, cycle 9508, `last_error` empty.
4 open, floating **+$22**. Day realised **−151.15** / 17 closes / WR
17.6% / DD **−6%**. AI enabled, `risk_scale` **0.71**. `max_margin_usage_pct`
**90**. Harvest off. **No `ERROR` line on 27.08** in `logs/micofx.log`.

### 1) Optimization Summary

* **Health:** Idle hot path is still paid (4.4 ms). Retired families
  fail-closed. Search/snapshot lock reuse already landed. Today's
  losses are **book**, not a new engine leak: GER40 6/6 original SL
  (−111$), JPN225 −51$, US30 −12$; XAU +18, NAS +5. Shakeout floor
  exists on disk for the next GER40 entry; this PID does not load it.
* **Top 3 highest-impact (none is a silent CPU patch):**
  1. Keep the running search and the open book. Restart/cancel would
     drop hours of combo work and first-sight stops.
  2. After **flat + restart only**: confirm shakeout WARN, prefetch
     log, slim opt poll, `raw/floor` vs `volume_min`.
  3. Delete dead panel blobs (`SECTIONS`, `optFieldVisible`) when the
     book is quiet — maintainability, not latency.
* **Biggest risk if no changes:** None on the idle path. Operational:
  GER40 pending 1.0/0.3/1.2 lands when two tickets close; floor still
  overlays SL. That mix is **accepted** (option 3). Harvest-on / BE 0.5
  / `max_positions`→1 stay won't-do.

### 2) Findings (Prioritized)

* **Title:** Dead symbol-guts UI (`SECTIONS` / `optFieldVisible`)
* **Category:** Frontend / Maintainability
* **Severity:** Medium (agent trap), Low (runtime)
* **Impact:** Smaller `app.js`, fewer false "restore Ileri duzey" PRs
* **Evidence:** `SECTIONS` `1020:1128:micofx/web/static/app.js` —
  definition only. `optFieldVisible` `1130:1137` never called.
  `buildSymbolCard` maps POSITION + EXIT readout + sessions only.
* **Why it’s inefficient:** ~50 field defs + schema fetch exist only
  so a removed advanced card can hide axes.
* **Recommended fix:** Delete `SECTIONS`, `optFieldVisible`, and the
  one-shot `loadSchema` if nothing else reads `SCHEMA`. Keep
  `GET /api/schema` for tests.
* **Tradeoffs / Risks:** Help/schema tests scan `SECTIONS` keys —
  update `test_field_help_covers_every_setting.py`.
* **Expected impact estimate:** Bundle/parse only; cycle ms unchanged.
* **Removal Safety:** Likely Safe after test retarget.
* **Reuse Scope:** local file (`app.js`)

* **Title:** Ghost `ADVANCED_SECTIONS` comment
* **Category:** Maintainability
* **Severity:** Medium (agent)
* **Impact:** Stops a resurrect of collapsed guts
* **Evidence:** `app.js:989-992` claims guts live in
  `ADVANCED_SECTIONS`; the name **does not exist**.
* **Why it’s inefficient:** Next agent "completes" the floor/panel.
* **Recommended fix:** Rewrite the comment to match POSITION + EXIT
  readout.
* **Tradeoffs / Risks:** None.
* **Expected impact estimate:** Zero runtime.
* **Removal Safety:** Safe
* **Reuse Scope:** local file

* **Title:** Hands-off fields still Origin-POST writable
* **Category:** Reliability / Security-impacting (operator footgun)
* **Severity:** Low (by design)
* **Impact:** A crafted POST can still flip `lot_multiplier`,
  `trade_all_hours`, `charge_costs`, harvest overlays mid-trade
  (`breakeven_at_r` not in `EXIT_RISK_FIELDS`).
* **Evidence:** `POST /api/system` = full `SystemConfig`;
  `POST /api/symbols/{id}` = full `SymbolConfig`; AI settings
  `DEFAULTS`; opt params full blob. Panel only sends a subset.
* **Why it’s inefficient:** Not CPU. Confusion: UI hide ≠ API lock.
* **Recommended fix:** Do **not** add them to
  `_INTERNAL_ONLY_FIELDS` (that tuple is pending-exit staging).
  Operator asked visibility. Yellow/red stay operator.
* **Tradeoffs / Risks:** Locking overlays mid-trade would 409 BE/partial
  which AGENTS deliberately allows.
* **Expected impact estimate:** n/a
* **Removal Safety:** Needs Verification if anyone later "locks" them
* **Reuse Scope:** service-wide

* **Title:** GER40 shakeout vs pending apply (book, not a bug)
* **Category:** Algorithm / Reliability
* **Severity:** n/a (accepted mix)
* **Impact:** Next GER40 entry: SL floored 2.0, trail 0.3/1.2 until
  window cools then stored 1.0/0.3/1.2
* **Evidence:** Card readout `2 (kuyruk 1)` / `0.5 (kuyruk 0.3)` /
  `2.2 (kuyruk 1.2)`. Today −111$ / 6 original SL. Docstring option 3.
* **Why it’s inefficient:** Not inefficient — temporary overlay.
* **Recommended fix:** None. Do not scale trail. Do not drop pending.
* **Tradeoffs / Risks:** Already written on `shakeout_sl_atr_mult`.
* **Expected impact estimate:** n/a
* **Removal Safety:** n/a
* **Reuse Scope:** `micofx/risk.py`

* **Title:** Spread/slot misses (SpotBrent, US30, JPN/XAU)
* **Category:** Algorithm (live gates)
* **Severity:** n/a (working as designed)
* **Impact:** Fill rates 13% Brent / 21% US30 vs 71% NAS100
* **Evidence:** `max_spread_atr` blocks (US30 144, Brent 65 of 909
  earlier today). Cost 18% gate refused **0**. `max_positions` slots
  JPN225/XAUUSD. AI watch scale 0.425 on 5/6 names.
* **Why it’s inefficient:** Tight spread is the real filter; do not
  loosen from one red day.
* **Recommended fix:** Let current search finish. Do not harvest-on.
  Do not cut `max_positions` to 1 (US30 slot-2 +4.62 R).
* **Tradeoffs / Risks:** Loosening spread is a curve-fit.
* **Expected impact estimate:** n/a
* **Removal Safety:** n/a
* **Reuse Scope:** live `SymbolConfig`

* **Title:** Unread snapshot crumbs
* **Category:** Network
* **Severity:** Low
* **Impact:** Bytes on `/api/state`
* **Evidence:** `day.cash_flow`, `day.floating`, `bot.poll_interval_sec`
  written, zero `app.js` reads (day.realised / positions already shown).
* **Why it’s inefficient:** Tiny ints every 3s.
* **Recommended fix:** Optional omit after panel confirm. Not hot.
* **Tradeoffs / Risks:** A future chip might want `floating`.
* **Expected impact estimate:** <<1 KB
* **Removal Safety:** Needs Verification
* **Reuse Scope:** `engine.py` snapshot

* **Title:** `GET /api/schema` consumer is dead
* **Category:** Network / Frontend
* **Severity:** Low
* **Impact:** One fetch on load
* **Evidence:** `loadSchema()` then unused except dead `optFieldVisible`.
  Tests still hit the route.
* **Recommended fix:** Keep endpoint; drop the panel fetch with SECTIONS.
* **Tradeoffs / Risks:** None if tests stay.
* **Expected impact estimate:** one GET
* **Removal Safety:** Likely Safe
* **Reuse Scope:** `app.js`

### 3) Quick Wins (Do First)

* Comment fix: `ADVANCED_SECTIONS` → actual card shape (one line).
* After **flat restart**: measure shakeout WARN on disk, prefetch
  `Barlar indirildi`, opt poll payload drop, `raw/floor`.
* Do not PATCH margin 90, harvest, BE, flatten, cancel.

### 4) Deeper Optimizations (Do Next)

* Delete `SECTIONS` + `optFieldVisible` + unused schema load (panel
  quiet). Update field-help test.
* Numba / O-1 still gated on measured 3× grid / 2000-row autopsy heat.
* Do not invent families (`dual_t3` / `t3_flip` / `aroon_flip` /
  `ichimoku` unused live is not a cue to force-assign).

### 5) Validation Plan

* Cycle: `bot.last_cycle_ms` (now 4.4) before/after any JS delete
  (must not move).
* `/api/state` size while opt busy (slim rankings wait on restart).
* `pytest tests/test_hands_off_controls_are_not_on_the_panel.py`
  `tests/test_shakeout_widens_the_next_stop.py`
  `tests/test_opt_poll_drops_unread_rankings.py`
* Log: no new `ERROR` on 27.08; shakeout line is `WARN` after restart.
* PnL: do not sum autopsy `kar` across flatten rows; panel day cash
  is the truth (−151.15).

### 6) Optimized Code / Patch

None this pass. Operator: **do not implement** until Cursor OK after
Claude's independent scan.

### Per-symbol reverse (evidence only)

| Sym | Family/TF | Today $ | Structural note |
|---|---|---|---|
| GER40 | stoch_flip M30 | −111.22 (6 SL) | Floor ON; pending 1.0/0.3/1.2 |
| JPN225 | stoch_flip M15 | −51.20 (7) | Slots 3/3; AI ok |
| US30 | stoch_flip M30 | −12.14 (2) | Spread+slot; overlap slot stays |
| NAS100 | mtf_pullback M30 | +5.01 | Unvalidated stamp; watch PF 0.58 |
| XAUUSD | burst M15 | +18.4 | max_pos 1; partial 0 |
| SpotBrent | parabolic_flip M15 | 0 closed | Fill 13%; spread@cap |

Unused live families: `dual_t3`, `t3_flip`, `aroon_flip`, `ichimoku`.
Won't-do: harvest-on, BE 0.5 (−32 R GER40), max_positions 1, adverse-fill
gate, cost-toggle off engine (0/909 maliyet blocks).

### SECURITY AUDIT: dirty tree vs HEAD `122e434`

**Risk Assessment:** Low

#### **Findings:**
* None Critical/High. `mt5_terminal_path` → `Popen([exe])` list-form,
  missing file `None` (Claude 14:5x). Origin CSRF unchanged. No
  secrets in backup Drive path. Hands-off keys remain POST-able —
  operator asked hide not lock.

#### **Observations:**
* Overlay PATCH mid-trade still allowed (not in `EXIT_RISK_FIELDS`).
* `backup_dir_secondary` Google Drive path contains `Drive'ım` —
  UTF-8 round-trips.
* AGENTS.md rewrite from the pasted template would **drop** today's
  gotchas (shakeout, prefetch, hands-off). Not rewritten this pass.

---


Independent Cursor pass. Claude 23:00 already reported 0 new findings
and 2579 passed / 1 xfailed. This pass did not trust that: grepped
retired families, unused routes, SQLi, Origin, live `/api/state`,
cycle ms, payload sizes, comment traps.

**Live (21:57, GET `/` then `/api/state`):** demo `61562752` @
Pepperstone-Demo. Bot running, MT5 connected, opt idle, harvest_on
`[]`. 5 open (XAUUSD / GER40 / NAS100 / JPN225 / SpotBrent). Day
realised **−213.22$** (59 closes, WR 30.5%). `ai.risk_scale` 0.6
(daily DD ~8.66%). `bot.last_cycle_ms` **5.2**. `/api/state` **16.7 KB**
(ai 5.1, capacity 4.0, states 2.6, positions 2.0).

### 1) Optimization Summary

* **Health / saglik:** Idle hot path is already paid. Cycle 5.2 ms with
  5 tickets, 6 symbols, 900s pin skip on. Schema no longer rides on
  every poll. Snapshot reuses the cycle book while `optimizer.busy`.
  Retired families (`alpha_trend`, `mavilim`, `st_trend`, `macd_flip`)
  are absent from `_FAMILIES` / `STRATEGIES` / `OPT_FIELDS`. Leftover
  DB names fail closed. Production callers for the unused-name pin
  list are still 0.
* **Top 3 highest-impact (none unpaid in code):**
  1. Keep the 00:05 search from overlapping an open book (ops, not a
     patch). Search lock is already snapshot-reused; `EXIT_RISK_FIELDS`
     mid-trade stay 409 / `pending_exit_patch`.
  2. Do **not** land Numba or O-1/O-2/O-3 until the measured gates
     trip (`OPT_FIELDS` 3×; 2000-row autopsy cap actually hot).
  3. Do **not** restart while these 5 tickets are open — disk already
     has the 900s / join-order landings; live PID does not.
* **Biggest risk if no changes:** None on the idle path. The overnight
  search starting while tickets remain would stall `_cycle` on the MT5
  lock for ~minutes (panel already degrades to last cycle book; halt /
  flatten still wait inside `_cycle`). That is an ops gate, already
  written into `gece_opt.py`.

### 2) Findings (Prioritized)

* **Title:** Stale `_maybe_reoptimize` comments (agent trap) /
  silinmis takvim fonksiyonuna isaret eden yorumlar
* **Category:** Dead Code
* **Severity:** Low (docs / agent, not runtime)
* **Impact:** Maintenance — agents planning work off comments would
  resurrect calendar auto-queue.
* **Evidence:** `optimizer.py` apply-age comment and
  `tests/test_apply_age_guard.py` / `tests/test_scan_skips_disabled.py`
  module docs named `supervisor._maybe_reoptimize`. Function does not
  exist. Live path is `reject_reason` + `reopt_min_age_hours` on apply;
  quarantine queues via `_queue_reoptimization`.
* **Why it’s inefficient:** Copy-paste drift after calendar reopt was
  stripped. Same class as `_is_improvement` (MISS-4).
* **Recommended fix:** Point comments at `reject_reason`. **Done this
  pass.** AGENTS gotcha added.
* **Tradeoffs / Risks:** None — comment-only.
* **Expected impact estimate:** Zero runtime. Prevents a wrong reopt
  rewrite.
* **Removal Safety:** Safe (comments). Production `_queue_reoptimization`
  must stay.
* **Reuse Scope:** module (optimizer + two tests + AGENTS)

---

* **Title:** Overnight 6-symbol search vs first fills /
  gece aramasi ilk fill penceresine biner
* **Category:** Concurrency
* **Severity:** Medium (ops). Code path already mitigated.
* **Impact:** Latency of `_cycle` / flatten during search; apply of
  family/TF refused if that symbol is open.
* **Evidence:** Armed task `MicoFX Gece Opt 0005` →
  `cursor/gece_opt.py` (gitignored). Waits for 0 positions, aborts if
  still open after 20 min **or** local hour ≥ 01:00. Six names.
  Session flatten historically ~23:54; first fills ~01:05. JPN225
  48h gate will refuse apply (`force=false`).
* **Why it’s inefficient:** 14 workers hold the MT5 `RLock` for
  `copy_rates` chunks. Panel `/api/state` already serves last cycle
  book while `optimizer.busy`. Halt/flatten still serialize on `_cycle`.
* **Recommended fix:** Do not start the search from this chat while
  n_pos > 0. Leave the armed task. Do not `force=true` on JPN225.
* **Tradeoffs / Risks:** Skipping the night search leaves old configs
  (NAS100/GER holdout age already called out). Starting it with opens
  blocks management.
* **Expected impact estimate:** 148s lock hold measured 26.08 on a
  prior search — panel hung before snapshot reuse; now it does not.
* **Removal Safety:** N/A (ops).
* **Reuse Scope:** service-wide (optimizer + engine snapshot)

---

* **Title:** 900s pin middle-bar hole /
  pin iki ucu ayni kalirsa ortadaki delik gorulmez
* **Category:** Reliability / I/O
* **Severity:** Low (accepted remaining miss)
* **Impact:** A corrupted middle of the window with unchanged oldest +
  last-closed stamps skips the full `copy_rates`.
* **Evidence:** `engine.py` integrity branch compares
  `bar_window_pins` to `(state.bars.time[0], state.last_bar)`. Pins
  are **not** `forming_time`. Tests:
  `tests/test_bar_fetch_releases_the_lock.py`.
* **Why it’s inefficient:** Full `required_bars` every 900s with no
  new bar used to hold the lock. Two small `copy_rates` are the
  cheaper honesty. A third pin (checksum / bar count in the middle)
  would close the hole and cost another MT5 call every 900s.
* **Recommended fix:** Leave it. Do not re-add `_STALE_BAR_REFRESH`.
* **Tradeoffs / Risks:** Rare broker-history hole vs lock time.
* **Expected impact estimate:** Already paid (lock hold gone on the
  common path).
* **Removal Safety:** Needs Verification to add a third pin.
* **Reuse Scope:** `engine.py` + `mt5client.py`

---

* **Title:** `TIMEFRAMES` == `READABLE_TIMEFRAMES` /
  iki liste artik ayni
* **Category:** Algorithm (Reuse Opportunity)
* **Severity:** Low
* **Impact:** Maintenance only. No runtime.
* **Evidence:** `models.py` both `["M5", "M15", "M30"]`. Comment says
  they only needed to differ while a live row still named H1.
  Tests encode the split (`test_h1_left_the_search.py`).
* **Why it’s inefficient:** Two names for one set. Merging would
  touch tests that exist specifically to keep the split reopenable.
* **Recommended fix:** **Do not merge.** One-line reopen if an hourly
  bar earns a R/day number.
* **Tradeoffs / Risks:** Merging loses the documented reopen hatch.
* **Expected impact estimate:** Zero.
* **Removal Safety:** Needs Verification.
* **Reuse Scope:** models + tests

---

* **Title:** `/api/state` 16.7 KB / 3s, `ai` 5.1 KB /
  panel polling payload
* **Category:** Network / Frontend
* **Severity:** Low
* **Impact:** Bandwidth / JSON parse on the panel. Idle ~5.6 KB/s.
* **Evidence:** Measured 21:57. Schema already extracted to
  `GET /api/schema` (was 2.1 KB × 12 `sorted()` on every poll).
  Symbol rows live on `/api/symbols` + `symbols_sig`. Hidden-tab
  poll is 6s (`app.js`).
* **Why it’s inefficient:** `supervisor.status()` rebuilds 6 rows
  with `_gate_locked` on every snapshot. Cheap vs MT5 lock.
* **Recommended fix:** Do not split `ai` off `/api/state`. 5 KB is
  not the bottleneck; `last_cycle_ms` 5.2 is.
* **Tradeoffs / Risks:** Extra round-trip would desync the AI tab
  from the header scale.
* **Expected impact estimate:** <1% CPU. Premature.
* **Removal Safety:** Needs Verification.
* **Reuse Scope:** `engine.snapshot` / `supervisor._status_locked`

---

* **Title:** Keep-list is not dead /
  tutulan isimler kullaniliyor
* **Category:** Dead Code (negative finding — do not strip)
* **Severity:** n/a
* **Impact:** Stripping these would break tests and CSRF/session
  probes, or hide operator columns.
* **Evidence:**
  * `GET /api/system`, `GET /api/positions`, `GET /api/logs` +
    download — tests + panel POST/download. Panel reads
    `STATE.positions`; GET stays for empty-book honesty.
  * `sessions.broker_epoch` — inverse of `server_datetime`; 0
    production call sites, 4 tests. Clock helper, not dead.
  * Payload keys `captured`, `raw_lot`, `trail_improves_at_r`,
    `expected_trades`, `actual_trades`, `config_age_days` — tests
    and/or panel.
  * `_SYMBOL_RISK_BOUNDS` dict stays; only `partial_close_lots`
    **entry** is gone.
  * Overlay fields `breakeven_at_r` / `partial_at_r` /
    `harvest_at_r` (0 = off) stay. Not `OPT_FIELDS`.
* **Why it’s inefficient:** It isn’t. Earlier unused-name strip
  already took the real dead set (`backtest.run`, `mae_close`,
  `edge_decomposition`, analysis routes, `GET /api/ai`,
  `POST /api/logs/clear`).
* **Recommended fix:** Leave the keep-list. Pin remains
  `tests/test_unused_production_names.py`.
* **Tradeoffs / Risks:** Stripping `broker_epoch` re-introduces
  the localtime 00:00 SL bucket the next time someone formats a
  day cut.
* **Expected impact estimate:** n/a
* **Removal Safety:** Unsafe
* **Reuse Scope:** service-wide

### 3) Quick Wins (Do First)

* Comment trap `_maybe_reoptimize` → `reject_reason`. **Done.**
* AGENTS: pin identity + calendar-name gotcha. **Done.**
* Do **not**: merge TIMEFRAMES, split `/api/state`, strip
  `broker_epoch`, restart with 5 opens, start the 00:05 search from
  this chat, re-add Numba / O-1 / harvest-on / max_positions 3→1.

### 4) Deeper Optimizations (Do Next)

* **Numba `simulate`:** won't-do until `OPT_FIELDS` grid 3×. Measured
  6.53 ms. Incremental IndicatorCache 2.57 ms. Closed ledger.
* **O-1/O-2/O-3 own tables:** won't-do until 2000-row autopsy cap is
  hot. Live sqlite owner; schema split is a restart-sized migration.
* **00:05 all-six search:** next measured event. Apply gates unchanged.
  JPN225 likely 48h-refused. Do not `force=true`.
* **Third pin / bar checksum:** only if a real middle-hole is observed
  in `bar damgasi` WARN lines.

### 5) Validation Plan

* Benchmarks already on the ledger: simulate 6.53 ms, IndicatorCache
  2.57 ms, search lock 148s (panel reuse landed). Idle cycle **5.2 ms**
  tonight — compare `bot.last_cycle_ms` after the next restart (disk
  landings load). During a search, confirm `/api/state` still returns
  while `opt.busy` and `last_cycle_ms` does not jump to seconds.
* Profiling: do not attach a sampler to the live PID. Repro in tests:
  `tests/test_snapshot_reuses_the_cycle_book.py`,
  `tests/test_bar_fetch_releases_the_lock.py`,
  `tests/test_unused_production_names.py`,
  `tests/test_retired_indicators_stay_gone.py`,
  `tests/test_docs_match_the_code.py`,
  `tests/test_apply_age_guard.py`.
* Metrics before/after (only if a real patch lands): `last_cycle_ms`,
  `/api/state` byte size, search wall time, sqlite `opt_runs` trim.
* Correctness: 8 families × TIMEFRAMES still fail-closed on unknown
  names. `compute()` empty series does not signal. Origin-less POST
  still 403.

### 6) Optimized Code / Patch

Comment-only (no behaviour). `optimizer.py` apply-age block and the
two test module docs now name `reject_reason` / quarantine
`_queue_reoptimization`. AGENTS pins `bar_window_pins` to
`(oldest, last_closed)`.

No Numba, no table split, no overlay change, no live PATCH.

### SECURITY AUDIT: dirty tree vs HEAD `122e434` (deletions dominate)

**Risk Assessment:** Secure / Low

Working tree vs HEAD is net **−1213** on `micofx/`+`tests/` (54 files,
994 / 2207). Surface area shrank: analysis routes, `GET /api/ai`,
`POST /api/logs/clear`, `edge_decomposition`, `backtest.run`,
`mae_close` kwargs.

#### Findings:

* **None Critical / High.** Session cookie + Origin gate unchanged
  (`create_app` middleware: missing session 401, missing/cross-site
  Origin 403). `docs_url=None`. Bind stays 127.0.0.1. Mutations still
  need `Origin: http://127.0.0.1:8900`.
* **Restart spawn** (Severity: Low, accepted)
  * **Location:** `micofx/web/app.py` `POST /api/app/restart` ~
    `subprocess.Popen(["cmd", "/c", restart.bat"], ...)`
  * **The Exploit:** argv is a fixed list, not request body. No
    injection. Restart still forbidden while positions are open
    (operator / AGENTS).
  * **The Fix:** none. Do not take user path into Popen.
* **Dynamic SQL placeholders** (Severity: Low, Secure)
  * **Location:** `store.purge_orphan_history` —
    `DELETE ... NOT IN ({placeholders})` with `keep` bound as params.
  * **The Exploit:** values are `?`-bound; only the count of `?` is
    interpolated. Not SQLi.
  * **The Fix:** none.
* **Secrets:** no new credentials in the diff. Session token is
  `secrets.token_urlsafe(24)`, HttpOnly, SameSite=Strict, not in HTML.

#### Observations:

* `GET /api/system` remains — CSRF tests hit it. Account-lock fields
  still refused on `POST /api/system` (door is `/api/account-lock`).
* Web handlers still do not import `MetaTrader5`.
* Pydantic bodies `forbid` extra fields (existing tests).
* Do not restore `GET /api/ai` or ring-wipe `POST /api/logs/clear`.

### AGENTS.md

Not rewritten. Signal density already at the quality bar. Two
gotchas added this pass (pin identity; `_maybe_reoptimize` gone).
Did not duplicate MASTER_PROMPT §19, README, or the closed ledger.

---

## 26.08 19:12 — live after restart + opt/sec (no further patches)

Operator asked restart then re-test, then this audit into this file.
Restart **19:10:49** → MT5 **19:10:58**. Log: `Restart: magic ile 8 acik
ticket devam ediyor` — same eight tickets as pre-restart snapshot.
All `managed=True`. SL identity: SpotBrent 88.794, JPN 66126.3 / 66039.0,
US30 53532.9 / 53507.1 / 53506.0, XAU 4613.32, NAS 29118.1. Unchanged.
`GET /api/ai` **404**, `POST /api/logs/clear` **404**. `last_cycle_ms`
3.7 then 10.6 (idle). Opt idle. Harvest on: none.

Pytest re-run after live was up: **91 passed**
(`test_snapshot_reuses_the_cycle_book`, `test_snapshot_capacity_is_cached`,
`test_entry_block_events`, `test_entry_block_tally`,
`test_entry_blocks_concurrency`, `test_a_deleted_symbol_leaves_nothing_behind`,
`test_original_sl_survives_restart`, `test_unused_production_names`,
`test_restart_waits_for_the_port`, `test_panel_does_not_fast_poll_during_opt`).

### 1) Optimization Summary

Health: **good, and now loaded**. F-1 debounce and search-stale snapshot
are in the live process (`last_cycle_ms` ~4–11, not 148). Dead-route
strip is live (404s). Remaining unpaid items are the same three
measure-first leftovers: 900s full integrity fetch, Numba if grid 3×,
settings-blob rewrite (O-1/2/3).

Top 3 unpaid:

1. 900s no-new-bar still full `copy_rates` (I/O) — stamp-only unverified.
2. `Store.set_setting` full JSON blob rewrite (DB) — F-1 closed the hot
   caller; leftover is autopsies/execution_samples, not entry events.
3. Visible-tab innerHTML rebuild (Frontend) — `viewPulse` skip exists.

Biggest risk if unchanged: a 900s integrity pass on M5 US30 still holds
the MT5 lock for a chunked full window. Idle `last_cycle_ms` stays low.

### 2) Findings (Prioritized)

* **Title:** 900s integrity still copies full `required_bars`
* **Category:** I/O
* **Severity:** Low (idle) / Medium (6 symbols × M5)
* **Impact:** Lock hold, MT5 IPC
* **Evidence:** `_BAR_INTEGRITY_REFRESH = 900`; `due or integrity` then
  `client.bars(..., need)`. Chunked. Live last_cycle_ms 3.7–10.6 so this
  is not the current cycle cost.
* **Why:** Stamp/length check would refuse a silent hole; full copy is
  the hammer.
* **Recommended fix:** Stamp-only integrity; full fetch on mismatch.
  Needs a truncated-history test. **Not this pass.**
* **Tradeoffs:** Wrong stamp API → missed holes.
* **Expected impact:** Rare 900s spike gone.
* **Removal Safety:** Needs Verification · **Reuse Scope:** `engine.py`

* **Title:** Settings KV still rewrites whole blobs (O-1 leftover)
* **Category:** DB / I/O
* **Severity:** Low after F-1
* **Impact:** Cycle I/O on autopsy/execution flush, not every poll
* **Evidence:** Claude 19:05 F-2: 51 `set_setting` sites; three blobs
  ~94% of settings bytes. F-1 closed `entry_block_events` every-poll.
  `execution_samples` already batches 20. `_flush_trade_autopsies` is
  close-driven.
* **Recommended fix:** None until measured after F-1 in a blocked-entry
  session (`bot.last_cycle_ms` p90).
* **Removal Safety:** n/a · **Reuse Scope:** `store.py`

* **Title:** Search-stale snapshot (landed, now live)
* **Category:** Concurrency / Caching
* **Severity:** n/a (closed)
* **Evidence:** 8 tickets survived restart; idle state 10.6 ms. Not
  re-measured under a 14-worker search this pass (book open — do not
  start a search).
* **Removal Safety:** Safe (tests pin) · **Reuse Scope:** `engine.snapshot`

### 3) Quick Wins (Do First)

None unpaid that is Safe without identity tests. Do not restore
`POST /api/logs/clear` or `GET /api/ai`.

### 4) Deeper Optimizations (Do Next)

Stamp-only 900s integrity. Own table for entry-block events only if
F-1 p90 still hurts in a blocked session. Numba if `OPT_FIELDS` 3×.

### 5) Validation Plan

* Idle: `bot.last_cycle_ms` already 3.7–10.6 post-restart.
* Search stall: flat book, 14-worker job, `GET /api/state` p95. Not
  tonight (8 opens).
* F-1: blocked-entry session ≥200 cycles; `entry_block_events` writes
  ≤1 per 45s.
* Restart identity: ticket set + SL map (done 19:10).

### 6) Optimized Code / Patch

**Not applied this pass.** F-1 and search-stale already on disk and
now in the live PID.

### SECURITY AUDIT: live reload of dead-route strip + F-1 + stale snapshot

**Risk Assessment:** Low (surface reduced). Restart did not add doors.

#### Findings

* **Stale panel during search** (Severity: Low / accepted)
  * Location: `engine.py` `_panel_reuse_cycle_book` / `_search_is_busy`
  * The Exploit: localhost operator sees frozen P/L while opt.busy.
    Not an unauthenticated read; Origin still on mutations. Halt path
    still waits on the lock inside `_cycle`.
  * The Fix: none. Documented. Do not add a second `initialize()`.

* **force=True flush** (Severity: none)
  * Location: `forget_entry_blocks` / `reset_entry_blocks`
  * The Exploit: none extra. Those are already Origin-gated POSTs.
    Debounce bypass is for correctness (deleted symbol must leave disk).
  * The Fix: none.

* **Removed GET `/api/ai` and POST `/api/logs/clear`** (improvement)
  * Live 404 confirmed 19:12.

* **Secrets:** none in the diff.

#### Observations

* Origin middleware still wraps every POST/PUT/PATCH/DELETE.
* 8/8 tickets `managed=True` after restart — first-sight did not steal
  trail as original_sl (persisted blob).
* `search_busy` callable is in-process only; not an HTTP knob.

---

## 26.08 18:50 — Cursor opt + security (dirty tree, no patches)

Prompt: full optimization + staged-diff security. **No code fixes this
pass** (standing: write here, do not implement unasked). Live book
open (7 tickets). Harvest `0/0` all six. Opt idle.

### 1) Optimization Summary

Health: **good for a 3s-poll localhost bot**. Hot-path TTLs, lock
chunking, symbol_sig, npy mmap, dead-route strip already landed.
Remaining cost is **shared MT5 `RLock` during search** (measured), not
Python loops on `_cycle` (last_cycle_ms 7–72 this evening).

Top 3 unpaid (all previously open; no new Critical):

1. `/api/state` stalls 148s under a 14-worker search (Concurrency / I/O).
2. 900s integrity full `copy_rates` even with no new bar (I/O) — stamp-only unverified.
3. Panel still rebuilds innerHTML on pulse when the tab is visible (Frontend) — `viewPulse` skip exists; remaining cost is the visible tab.

Biggest risk if unchanged: operator panel **looks dead** during a
manual search; they restart mid-book. Not a silent money bug.

### 2) Findings (Prioritized)

* **Title:** `/api/state` shares the MT5 lock with opt workers
* **Category:** Concurrency / I/O
* **Severity:** High (during search only; idle last_cycle_ms ~7)
* **Impact:** Panel latency; operator may restart
* **Evidence:** AGENTS gotcha; SCAN-2 148s; `snapshot()` → `_panel_positions` → `client.positions()` under `RLock`. Workers `copy_rates` in chunks but still the same lock.
* **Why it’s inefficient:** One lock, two audiences (3s UI vs 14 fetchers).
* **Recommended fix:** Serve-stale snapshot / skip-lock when `opt.state==running`. Identity tests first. **Not** a second `mt5.initialize()`.
* **Tradeoffs:** Stale positions for minutes; halt path must stay fresh.
* **Expected impact:** Panel p95 during search: 148s → ~TTL (2–3s). Idle: 0.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** `engine.snapshot` / `MT5Client`

* **Title:** 900s no-new-bar still full `required_bars` fetch
* **Category:** I/O
* **Severity:** Low (idle) / Medium (6 symbols × M5)
* **Impact:** Lock hold, MT5 IPC
* **Evidence:** `_BAR_INTEGRITY_REFRESH = 900`; `integrity = now - state.last_fetch > 900` then full bars. Chunked. No compute.
* **Why:** Stamp/length check would refuse a silent hole; full copy is the hammer.
* **Recommended fix:** Stamp-only integrity; full fetch on mismatch. Needs a test that a truncated terminal history is detected.
* **Tradeoffs:** Wrong stamp API → missed holes.
* **Expected impact:** Rare 900s spike gone; correctness-sensitive.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** `engine.py` bar fetch

* **Title:** Dead-code strip this tree (already on disk, not a new patch)
* **Category:** Maintainability / Dead Code
* **Severity:** n/a (landed)
* **Impact:** −2k lines; fewer lying payloads
* **Evidence:** `git diff --stat` 39 files. Claude 18:05/18:45 callers **0**.
* **Reuse Scope:** repo-wide
* **Removal Safety:** Safe (pinned)

* **Title:** Adverse-fill / expensive-spread entry gates
* **Category:** Algorithm (yield, not runtime)
* **Severity:** Low as a *perf* item; High as a *wrong-fix* risk
* **Evidence:** Claude 18:45. Q4 `fill_vs_signal_close_r>=0.05` n=35 net −25 R vs Q1–Q3 +1.45 — but t=0 drops 62% of trades for +2.87 R; t>0.05 remaining set goes negative. `spread_atr` Q2 +9.42, Q1 −2.46 (non-monotonic). `block_high_cost` already at 18%.
* **Recommended fix:** Do nothing. Holdout cannot see fill_vs.
* **Removal Safety:** n/a
* **Reuse Scope:** do not add

### 3) Quick Wins (Do First)

* None unpaid that is Safe without identity tests. Strip already landed.
* Do not restore `POST /api/logs/clear` or `GET /api/ai`.

### 4) Deeper Optimizations (Do Next)

* Serve-stale `/api/state` during search (finding 1).
* Stamp-only 900s integrity (finding 2).
* Numba only if `OPT_FIELDS` grid 3× (closed until then).

### 5) Validation Plan

* Search stall: start a 14-worker job on a **flat** book; time `GET /api/state` p50/p95 vs idle 7–72ms.
* Integrity: fixture with a hole in `copy_rates` mid-window; stamp-only must refuse.
* Dead-code: `pytest tests/test_unused_production_names.py`.
* Yield gates: any new entry filter needs holdout **and** live fill_vs distribution; paper cannot bless fill_vs.

### 6) Optimized Code / Patch

**Not applied.** Standing order: this file is notes.

### SECURITY AUDIT: dead-route strip + overlay-off (working tree vs `0c33d72`)

**Risk Assessment:** Low (surface reduced). No new mutation doors.

#### Findings

* **Removed ring-wipe POST** (Severity: none / improvement)
  * Location: was `web/app.py` `POST /api/logs/clear`
  * The Exploit: authenticated same-origin could empty the in-memory ring for every viewer. Panel never called it (DOM Temizle).
  * The Fix: already deleted. `LogBus.clear()` remains in-process only.

* **Removed duplicate GET `/api/ai`** (Severity: none / improvement)
  * Location: was `web/app.py`
  * The Exploit: extra authenticated read of supervisor status (same data as `/api/state`).
  * The Fix: already deleted. POST settings/review/clear stay; Origin still required.

* **innerHTML on poll** (Severity: Low, previously landed)
  * Location: `app.js` table builders
  * The Exploit: XSS if a field skips `esc()`. `el({html})` sink already removed 08:45. Log lines use `esc(e.time/level)`.
  * The Fix: none this pass. New innerHTML must keep `esc()`.

* **Query-token on download** (Severity: Low, pre-existing)
  * Location: `GET /api/logs/download` — cookie/header session, not `?token=`
  * Tests pin query token is **not** accepted on panic. Download is GET + cookie. Same-origin cookie is the session. Fine for bind 127.0.0.1.

* **Secrets:** none in the diff. No new tokens, no `docs_url`.

#### Observations

* Origin middleware still wraps every POST/PUT/PATCH/DELETE (`web/app.py` ~597–603). Strip did not punch a hole.
* `compare_digest` on the session cookie stays.
* `from_dict` ignoring unknown keys (`partial_close_lots` leftover DB) is fail-open for *config*, not auth.
* Restart/shutdown still exist; they are red operator doors, Origin-gated.

---

## 26.08 12:50 — Cursor SCAN-2 (opt + security + profit/model)

Live `/api/state` (cookie): **0 open**, bot watch+trade on, PID 12:32:15,
demo 61562752, eq=bal 2313.55, day −2.09% / −49.44 realised, halt off.
Manual opt **running** `apply_best=true` 0/6 (GER40, JPN225, NAS100 in
flight). Operator raised US30/JPN225/GER40/NAS100/SpotBrent
`max_positions` to 3; `size_by_edge` on; concurrent cap 30%. 12:22
silent flatten of the previous 6 then IPC −10001.

Constitution (§0 / §19) **not** reopened: session/day-end flatten,
no TP ladders, `trail_start <= trail_step` legal, 8 families,
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
| 8 families | Live: parabolic_flip, burst, stoch_flip×3, mtf_pullback. No alpha_trend/mavilim/st_trend/macd_flip/t3_stoch/wavetrend_flip/micro_rev. `ichimoku` stays. |
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
* `capture` remains read-only on holdout dicts; `_slice_ok` / `reject_reason` / `_beats_incumbent` untouched.

---

### Reverse engineering — live readings (read-only, 26.08 07:48)

Not code claims. Read from the running system.

* **Process:** PID 10424, started **26.08 01:38:46**, `127.0.0.1:8900` LISTENING. HEAD `0c33d72` was committed after that start, so the live process is **pre-HEAD** and certainly does not carry the uncommitted diff. Any "live behaves like this" claim about the diff is currently **unverifiable**.
* **The keep-line has never fired.** Searching `logs/micofx.log` for `taze test` / `damga` returns three lines — all three are `"broker saati ... broker damgasinda, Windows DST sapmasi"` (lines 920, 922, 923). `_incumbent_kept_tail` has not emitted once in this log. The 25.08 keep-line fix is **unproven in production**; first thing to check on the next search.
* **Counter window:** `entry_blocks_since` = 1786905256.33 → **16.08 21:34:16**, 226.2 h. All C-1 ratios come from that window.
* **13 families (arsiv):** the panel reports 13 and post-diff `STRATEGIES` is 13, so the live DB `opt_params.strategies` already dropped `alpha_trend` / `mavilim`. The code constant follows the DB rather than leading it.
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
gates, overlay_stop, 8 families, gotchas). Do **not** rewrite it here. Only
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
  `ensemble_enabled`. Apply gates are `_slice_ok`, `reject_reason` and
  `_beats_incumbent`. Calendar reopt is gone.
- `EXIT_RISK_FIELDS` mid-trade → **409**. `breakeven_at_r` and
  `partial_at_r` are deliberately **not** in that set: they apply to
  already-open tickets.
- **11 live families.** `alpha_trend` / `mavilim` / `st_trend` /
  `macd_flip` retired 26.08; `test_retired_indicators_stay_gone`
  blocks their return. `ichimoku` stays.
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
- 8 families; no restart with opens.
- Fail-first with pytest/ruff. Persist via Store only.
- Yellow/red gates stay operator-only. Holdout capture is not a score input.
- Autopsy gotchas: `open_original_sl` must be tracked, profit-empty rows exist, `gmtime` broker calendar used.
```
