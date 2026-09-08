# AGENTS.md

Live **fx** bot, `C:\Users\Administrator\MicoFx`. Constitution:
`MASTER_PROMPT.md` §19. Do not port remaining `D:\MicoAi` extras
(`orb_retest`, Ai score formula, `autostart_mt5`) unasked.
`trail_mode` / `hour_risk_scales` / `max_combos=2000` are already here.

## Operator charter — 07.09 (full agent authority & profit mandate)

Operator granted **full operator authority** to Cursor / Claude /
Antigravity (Gemini), including rewriting this constitution and
MASTER_PROMPT, with explicit directive: *"anayasa benim kısıtlı bilgimle
oluştu en iyi sistemi için olması gereken neyse yapın. herkesin
değiştirebilirsiniz yeterki çok iyi.kar eden bir otomatik sistem olsun."*

1. **Mutual approval.** A material change (anayasa, risk, sizing,
   unfreeze, session, opt apply, live flatten, leverage-adjacent)
   needs a brief ACK from the other bridge peer(s) before land —
   Cursor ↔ Gemini via `FOR_GEMINI.md`, Cursor ↔ Claude via
   `FOR_CLAUDE.md` / `FOR_CURSOR.md`. Same-day ping is enough; silence
   after a clear ask is not an ACK. Yellow/red that used to wait on the
   human now wait on **peer ACK** unless the operator overrides in chat.
2. **Book is 7 symbols, forever open & all net-profitable.** Live set
   stays `BTCUSD GER40 JPN225 NAS100 SpotBrent US30 XAUUSD`. All 7
   symbols are verified net-positive on holdout (+393.5 R total). Do
   **not** disable, delete, or “close for bleed” any of them.
   Improve fill / exits / gates / sizing / search instead (“kapatma
   geliştir”).
3. **Full capacity + full auto + dynamic growth sizing.** Goal is
   maximum useful throughput under honest WFO/fill gates and a hands-off
   loop (autopilot, quarantine reopt, calibrate, watches). Inline kasa
   sizing scales dynamically with equity (`LOT_MULT_MAX = 2.2`,
   expanded equity tiers), while `max_concurrent_risk_pct = 25%` and
   symbol `max_positions` (1..5) allow high-edge scale-ins without
   starving free margin. Until Thursday: continue with **Gemini
   (Antigravity)** as the active peer; Claude joins the recurring loop
   Thursday with Cursor. Push to GitHub when a peer-ACK’d package lands
   (operator 07.09).
4. **Safety floor still binds the process:** one Python, live owns
   DB/MT5, Origin on writes, no second `mt5.initialize()`, no LLM in
   engine/optimizer/supervisor. Peer ACK does not waive these.

## Must-follow constraints

- Python is `C:\MicoFX-venv\Scripts\python.exe`. No other interpreter.
- The live process **owns** `data/micofx.db` and the MT5 terminal. No
  second sqlite writer, no `mt5.initialize()` sidecar. `mt5.shutdown()`
  only in the dying process on `/api/app/restart`.
- Live writes go through the running bot: `GET http://127.0.0.1:8900/`
  then the API. **Every** POST/PUT/PATCH/DELETE needs
  `Origin: http://127.0.0.1:8900`. Port busy: do not steal 8900.
- No LLM inside engine, optimizer or supervisor. Panel "AI" is the rule
  supervisor.
- Exit model is hard ATR stop + ATR trail. Do not bring back
  `tp_atr_mult`, `partial_tp_r` ladders, `max_bars_in_trade`,
  `stale_exit_ratio`, `breakeven_atr`. Overlays (0 = off):
  `breakeven_at_r` (live 1.5), one-shot `partial_at_r` (POST 0 only),
  `harvest_at_r`/`harvest_step_atr` (live off; F41 costed loser), and
  MFE locks `mfe_lock1_at_r`/`mfe_lock1_to_r` + `mfe_lock2_*`
  (Antigravity 07.09 defaults 1.5→0.75R / 2.0→1.25R; not hard TP;
  not OPT). Optional `stale_flat_bars` (0=off) is momentum-flat flatten,
  not banned `max_bars_in_trade`. None is an `OPT_FIELDS` axis.
- `exits.overlay_stop` is the closed-bar trail/BE level. Live still owns
  broker clamp + modify. Change the helper or both callers. Cover
  identity tests.
- A forming candle never signals. Buy âˆ§ sell on one bar â†’ neither.
- Opt apply writes `OPT_FIELDS` only (plus documented secondary fields).
  Never silently enable `ensemble_enabled`. Apply gates are `_slice_ok`,
  `reject_reason` and `_beats_incumbent`. Calendar reopt is gone.
  AI auto-search is **quarantine only** (not decay, not weekly). Manual
  `POST /api/opt/run` still starts a search. Family/TF apply while this
  magic has a ticket queues `pending_primary_patch` (same door as
  `pending_exit_patch`); engine lands it when flat. Do not drop the winner.
- `EXIT_RISK_FIELDS` mid-trade â†’ **409**. `breakeven_at_r`,
  `partial_at_r`, `harvest_at_r` and `harvest_step_atr` are
  deliberately **not** in that set.
- Watch mode never opens. Wrong `broker_symbol` â†’ unavailable, no fuzzy
 fallback.
- `spread_calibration.cap_from_bands` defaults widen-only
  (`daraltilmadi` when calm band is under live). System
  `spread_narrow_on_calm` (default on, 07.09) may step the cap down
  by at most 0.02 ATR units per calibrate — not a free fall (F49).
- Session / day-end / daily-loss flatten are settled (owner 09.08).
- `trail_start_atr <= trail_step_atr` is legal; do not ban it.
- Do not holdout-capture with positions open. `POST /api/holdout/capture`
  is **409** while this process's magics still have tickets. Do not start
  a live search unasked.
- Tests must not append `logs/micofx.log` or `logs/gece_restart.log`.
  `gece_restart.say()` tests must patch the log path. Disk sink is off
  until `run.py` calls `LOG.enable_disk()`; ad-hoc `import micofx` must
  not enable it.
- Hands-off keys (system plumbing, cost toggles, AI knobs, strategy guts)
  return **400** on POST. Search `apply()` still writes `OPT_FIELDS`.
  Do not dump them into `_INTERNAL_ONLY_FIELDS` (pending-exit staging).
- **5 families.** `ichimoku` retired 02.09 (no symbol/TF holdout win).
  `stoch_flip`, `dual_t3`, `t3_flip`, `parabolic_flip` retired 01.09
  (flip/zero-win class). `nr_break` / `roc_pace` **fully deleted** 03.09
  (matrix: never best; operator full-delete). `band_fade` not shipped.
  Live search set: `burst`, `mtf_pullback`, `channel_break`, `super_trend`
  (added 07.09: dynamic volatility envelope breakout / continuation, 7/7
  holdout net profitable +341.85 R total), `keltner_break` (added 07.09:
  dynamic Keltner Channel EMA+ATR envelope breakout, 7/7 holdout net
  profitable +392.7 R total). `sweep_fade` / `range_fade` stay in
  code/STRATEGIES but are **not** in the live search list (dormant; do not
  ship unasked). Leftover DB names fail closed.
- **Soft-restart with open tickets is allowed** (operator 02.09):
  `POST /api/app/restart` keeps MT5 fills; `track()` / `open_original_sl`
  reattach after bind. `/api/app/shutdown` and `POST /api/holdout/capture`
  are still **409** while this process's magics have tickets (MT5 down
  still allowed on shutdown/restart so a wedged bind can recover).
  `gece_restart` skips the midnight taskkill when `/api/state` shows
  tickets; unread/wedged still kills (22.08 recovery). `track()` first-sights
  missing `open_original_sl` to the *current trail*.

## Validation before finishing

```
C:\MicoFX-venv\Scripts\python.exe -m pytest tests/<touched>.py -q --tb=short
C:\MicoFX-venv\Scripts\python.exe -m ruff check micofx/ tests/<touched>.py
```

Fail-first: write the test, watch it fail, then implement.
`pyproject.toml` already sets `--basetemp=.pytest_tmp`.

## Repo-specific conventions

- UI/log strings: Turkish. Comments/commit subject: English *why*.
- Persist only via `Store`. Immediate write, no separate Save.
- All MT5 through `MT5Client` + `RLock`. Web handlers never import
  `MetaTrader5`.
- New search axis: add to `OPT_FIELDS` **and** pay the grid cost, or
 `Store.opt_params()` drops it. Editing a shipped grid axis in
 `config/defaults.json` does **not** reach a live book: the merge is
 `{**shipped, **stored}` per axis, so a stored axis keeps its values
 unless the shipped list has extras (those append: trail_step 2.8).
 Only a brand-new axis back-fills the whole list.
- **Yellow** (peer ACK): supervisor knobs, AI soft-size, session widen,
  opt run/apply, unfreeze checklist, concurrent/lot bumps.
  **Red** (peer ACK + explicit risk note in the brief): leverage,
  account_lock rebind, daily_loss, live flatten-all. Operator chat
  still overrides peers.
- HTTP writes match the panel. Symbol POST: sessions +
  `enabled` / `group` / `broker_symbol`.
  `partial_at_r` (0 only, F44).
 System POST: `max_margin_usage_pct`
 / `mt5_terminal_path` / `autostart_mt5` /
 `autopilot_enabled` / `autopilot_interval_sec` /
 `lot_multiplier` / `max_concurrent_risk_pct` / `daily_loss_pct` /
 cost toggles (`charge_costs` / `block_high_cost` / `max_cost_pct_of_risk`).
 Opt POST: `lookback_days` /
 `refine_rounds` / `max_combos` / `timeframes`, plus the shared grid's
 **cost axes only** (`max_spread_atr`, `cost_rank_max`, F50 — the write
 merges onto the stored grid; a whole-value assign would delete the other
 axes). Family / TF / exits / magic / rest-of-grid /
  lot_mode /
  `daily_loss_flatten` / size_by_edge /
  `max_total_positions` / `risk_percent` / system `max_lot` /
 system `max_positions` / symbol `max_lot` / `max_margin_pct`
 are 400. `POST .../reset` is
 400. GET still returns readout fields.
- `POST /api/opt/run` `strategies` is **one-off**. Empty inherits the
  saved list. Do not persist a subset into `opt_params`. `apply_best`
  still defaults true.
- Holdout `capture = net_r / sum(mfe_r)` is a visible column. **Not** a
  score input and **not** an apply gate.
- Cursor is project lead and codes, **full authority vs Claude and
  Antigravity (Gemini)**. Claude/Gemini scan and write briefs; Cursor
  decides and lands. Yellow/red wait on **peer ACK** (operator chat
  overrides). Thursday: Cursor **and Claude** join the recurring loop
  with Gemini.
- Commit/push only when the operator asks. Named files; no secrets; no
  `--no-verify`. `cursor/`, `claude/`, `antigravity/` are gitignored.

## Important locations (only non-obvious)

- Runtime: `data/micofx.db`, `logs/micofx.log` (gitignored).
- Bridge (gitignored):
  - Claude: Cursor → `cursor/FOR_CLAUDE.md`; Claude → `claude/FOR_CURSOR.md`.
  - Gemini: Antigravity → `antigravity/FOR_GEMINI.md` (and/or
    `FOR_CURSOR.md`); Cursor → `cursor/FOR_GEMINI.md`.
  - Shared wake `.bridge/WAKE.txt`. Cursor arms
    `cursor/watch_bridges.ps1` (watches `antigravity/FOR_GEMINI.md` +
    Claude inbox; emits `AGENT_LOOP_WAKE_gemini_bridge` within 5s).
    Antigravity arms `antigravity/WATCH.ps1` (watches
    `cursor/FOR_GEMINI.md`). Do not watch a file you write.
- Installer: `KUR.bat` â†’ `KUR.ps1`. Launchers stay at repo root.
- Audit notes (not executable): `OPTIMIZATIONS.md`. Trust the closed
  ledger at the top.
- `graft/` is a stale dump â€” its line numbers are not live.

## Change safety rules

- Preserve walk-forward score and fill-next-open honesty unless asked.
- Do not invent families without holdout + `defaults.json` grid + UI +
  `STRATEGIES`.

## Known gotchas

- Next process loads HTTP-off exits (family/TF/magic/grid/reset 400).
  This PID still PATCHes them. GER40 `pending_exit_patch` still
  apply()s on flat either way. Family/TF winners queue in
  `pending_primary_patch` (this PID needs the new engine to land them).
  Do not add `/exit-override` unasked.
- Day cuts use `gmtime(naive broker epoch)` â€” "do not shift a second
  time", not "convert to UTC". A 00:00â€“03:00 local close is **today**.
  Hour buckets on autopsy `fill_time` are the same clock. Do not
  `fromtimestamp`/`localtime` those stamps (invents a 00:00 SL bucket).
- `_flush_entry_blocks` 45s window covers counters **and**
  `entry_block_events`. Do not restore `not events_dirty` skip.
  `reset` / symbol-delete / `shutdown` (after the worker joins) pass
  `force=True`. `execution.flush()` sits on the same side of `join`.
  Do not flush either blob before `_stop.set()` â€” the last in-flight
  cycle then hits a fresh window and drops its rows.
- Live count allows **scale-in tickets up to `cfg.max_positions` (clipped 1..5)**
  (operator + peer ACK 07.09; live caps are edge-weighted: XAUUSD=5, SpotBrent=4,
  GER40=3, BTCUSD=3, US30=2, JPN225=2, NAS100=2).
  Guarded against 13.08 restack via: (1) ATR spacing >= 0.75 ATR from nearest open
  ticket (strictly profit-direction only — BUY: eff_px >= max(opens)+0.75ATR, SELL: eff_px <= min(opens)-0.75ATR;
  was 1.0 ATR until 08.09 — entry_blocks showed risk_kademe_aralik blocking 0.7–0.85 ATR trends;
  losers do not add — bug fixed and regression tested 07.09 dc61af5), (2) max 1 new fill per symbol
  per closed bar (`_filled_bars`), (3) **each ticket sized at full nominal 1R**
  (`risk_percent` / auto-1R / margin share — not divided by `max_positions`;
  dividing ate baseline income on single-ticket fills, fixed 07.09 `406d3b2`),
  (4) book-wide `max_concurrent_risk_pct` (expanded to 25.0%, 07.09 Cursor ACK)
  and daily loss bounds remain the stack governor when several full tickets are open,
  (5) no hedging (opposite side blocked). System `max_positions` and symbol `max_lot` /
  `max_margin_pct` remain unread/400. Search still scores `max_open=1` for honest WFO.
- Symbol-specific MFE profit locks (07.09 evening Antigravity + Cursor ACK;
  earlier same-day 1.0–1.5 bands left ~$885 / 69 givebacks that peaked ≥0.70R
  then full-SL'd): `XAUUSD` (0.75→0.15 / 1.2→0.5), `NAS100` (0.70→0.15 / 1.1→0.4),
  `US30` (0.75→0.15 / 1.1→0.4), `JPN225` (0.75→0.15 / 1.2→0.5),
  `GER40` (0.80→0.20 / 1.4→0.7), `BTCUSD` (0.80→0.20 / 1.3→0.6),
  `SpotBrent` (1.0→0.3 / 1.6→0.8). Watch capture if 0.15R L1 scratches runners.
  NAS100 M30 session `15:00-21:00` confirmed on holdout (+59.04 R / DD 32.5 R /
  score 38.08 vs 08:00-16:00 +55.61 R / DD 37.09 R / score 33.36 under active MFE lock).
- Entry hour gates optimized on holdout (07.09 evening Antigravity + Cursor ACK):
  `JPN225` blanket block `[13..18]` removed (was strangling holdout to -4.86R, killing +55.37R
  in hours 15/17/18) → tightened to toxic-only `[3, 16, 20]`, holdout explodes to +59.29R / score 45.53.
  `GER40` blanket block `[6,8,14,18,19,20]` removed (18/19 evening trend restored) → tightened to
  chop-only `[10, 15, 16]`, holdout rises +37.12R → +57.74R / score 45.84. US30 `[0,1,16,19,21]`
  and NAS100 `15:00-21:00` [17] confirmed protective and preserved.
- SpotBrent spread cap optimized on holdout (07.09 evening Antigravity + Operator mandate):
  `SpotBrent` `max_spread_atr` tightened from loose 0.12 (was leaking 64R in spread drag to -29.16R)
  → calibrated to liquid-session 0.06, turning holdout net from -29.16R to +54.24R (score 37.28, +83.4R turnaround).
  All 7 book symbols now individually verified >+50R net positive on holdout (+458.3R total book).
- Do not add an adverse-fill entry gate on autopsy
  `fill_vs_signal_close_r` *R thresholds* (Claude 18:45: Q4 in-sample
  curve-fit; unverifiable). Live `chase_max_atr` (default 0.25) is a
  separate ATR-unit tick-vs-signal-close ceiling in `_try_entry`; 0 = off.
  Walk-forward stays fill-next-open (zero variance).
- `GET /api/ai` and `POST /api/logs/clear` are gone. Panel reads
  `STATE.ai`; Temizle is DOM-only. Do not restore the ring-wipe POST.
- Autopsy R divides by `|entry âˆ’ original_sl|`. Do not rewrite pre-fix
  `sl`+`r=+1.0` rows; cash is the truth. Flatten rows before
  `fill["profit"]` have empty `profit` â€” **R is still valid**; do not
  sum autopsy `kar` across those 27. Panel/report â€œmasadaâ€ is **winners
  only**; stored `left_on_table_r` still includes losers. `mfe_r` is an
  intrabar peak, not harvestable.
- Scale-out TRADE `kar=` is computed (`tick_value/tick_size` or
  `money_per_price_unit`), not `_closing_deal_pnl`. Pre-fix lines were
  `NxATR` with no cash.
- Keep-line is `(taze test â€¦R)` or `(damga â€¦R, dd.mm)`, not a live
  replay. A pre-fix `test net` figure is not current.
- Short MFE uses coverable ask (`bar_low + pad`); pre-26.08 shorts used
  the print low.
- `scale_out_done` prunes to live tickets (same lock as
  `weekend_pending`). Clamp `filled` to position volume.
- `/api/state` every 3s shares the MT5 lock. Symbol rows live on
  `/api/symbols`; state carries `symbols_sig`. While `optimizer.busy`,
  snapshot serves the last cycle book (positions/account/flags/capacity)
  instead of blocking. Halt/flatten still wait inside `_cycle`. Do not
  add a second `initialize()` to dodge it. Opt jobs share one npy folder
  per `(symbol, TF)` (`bars_path`); do not pickle the window onto every
  family.
- `STRATEGY_TIMEFRAMES` empty = unlocked. Opt start line must use
  `tf_lock_status`; do not hardcode `scalp TF kilidi acik`.
- Panel flatten-all must pass `close_all(reason=)`. A reason-less
  `Pozisyon kapatildi kar~` burst (26.08 12:22) cannot be autopsied.
- Fill verifier `sleep`s on a **side thread** (`defer_verify`). Do not
  delete the sleeps; do not return `verified_unfilled` early. Drain
  books the **send-time** `signal_source` + `last_bar`. Do not mark or
  clear live `state.last_bar` after the verifier sleeps â€” that wipes a
  T+1 signal and files `filled_bars` under `""`.
- `_BAR_INTEGRITY_REFRESH = 900s` pins window ends (two small
  `copy_rates`) and full-fetches only on mismatch. `due` uses **broker**
  clock. Do not re-add a stale-bar 45s refresh. Pins are
  `(bars.time[0], bars.last_closed_time)` â€” **not** `forming_time`.
  `Bars` ctor 2nd arg is the forming candle. A middle-bar hole with
  both ends unchanged is the remaining miss.
- Calendar `_maybe_reoptimize` is gone. Apply age is `reject_reason`
  + `reopt_min_age_hours`. Quarantine still queues via
  `_queue_reoptimization` (retry cooldown). Do not resurrect a
  weekly/decay auto-search.
- `_MAX_SIGNAL_BAR_AGE_BARS = 2` Ã— timeframe. Search default is M15/M30
  (`SEARCH_TIMEFRAMES`). **M5 was RETIRED 05.09** and is no longer legal
  anywhere: `TIMEFRAMES`, `READABLE_TIMEFRAMES` and `SEARCH_TIMEFRAMES` are
  `["M15","M30"]`, the panel no longer offers it, and
  `strategy_allows_timeframe` refuses it - naming it in a one-off
  `POST /api/opt/run` is dropped from the request, and if nothing legal is
  left the call is refused outright with `"Aranabilir zaman dilimi yok"`
  (verified 05.09; the earlier "produces a dead symbol" wording was wrong).
  Measured
  0/7 symbols would pick it (five outright negative) at +6-32% cost per
  trade; H1 (emekli / retired) was re-measured the same day and lost 6/6 on
  R/day, so it stays gone. Reopening
  needs `models.TIMEFRAMES` **and** `config/defaults.json optimizer.timeframes`
  - and that is all. `store.opt_params()` unions the shipped list into the
  stored blob on every read, so the stored `opt_params.timeframes` does NOT
  have to be edited. This paragraph claimed it did until 05.09; resurrection
  is a two-file change, cheaper than documented, so treat both files as live
  risk surfaces.
