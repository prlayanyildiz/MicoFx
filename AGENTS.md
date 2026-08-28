# AGENTS.md

Live **fx** bot, `C:\Users\Administrator\MicoFx`. Constitution:
`MASTER_PROMPT.md` §19. Do not port remaining `D:\MicoAi` extras
(`orb_retest`, Ai score formula, `autostart_mt5`) unasked.
`trail_mode` / `hour_risk_scales` / `max_combos=2000` are already here.

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
  `breakeven_at_r` (live 1.5, not 0.5 — BE-2 GER40 −32 R), one-shot
  `partial_at_r` (ticket lot × 1/3, broker min/step), and
  `harvest_at_r` / `harvest_step_atr` (tighten trail_step once paid;
  live off book-wide — paper net R 26.08). None is an
  `OPT_FIELDS` axis.
- `exits.overlay_stop` is the closed-bar trail/BE level. Live still owns
  broker clamp + modify. Change the helper or both callers. Cover
  identity tests.
- A forming candle never signals. Buy ∧ sell on one bar → neither.
- Opt apply writes `OPT_FIELDS` only (plus documented secondary fields).
  Never silently enable `ensemble_enabled`. Apply gates are `_slice_ok`,
  `reject_reason` and `_beats_incumbent`. Calendar reopt is gone.
  AI auto-search is **quarantine only** (not decay, not weekly). Manual
  `POST /api/opt/run` still starts a search.
- `EXIT_RISK_FIELDS` mid-trade → **409**. `breakeven_at_r`,
  `partial_at_r`, `harvest_at_r` and `harvest_step_atr` are
  deliberately **not** in that set.
- Watch mode never opens. Wrong `broker_symbol` → unavailable, no fuzzy
  fallback.
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
- **8 families.** Do not re-add `alpha_trend` or `mavilim`. `st_trend`
  and `macd_flip` retired 26.08 (never applied, not live). `ichimoku`
  stays. Leftover DB names fail closed (no signal), they do not crash.
- **No restart while positions are open.** `POST /api/app/restart` and
  `/api/app/shutdown` are **409** while this process's magics still have
  tickets (MT5 down still allowed so a wedged bind can recover).
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
  `Store.opt_params()` drops it.
- **Yellow** (ask): supervisor. **Red** (explicit):
  leverage, account lock, daily brake, live flatten-all.
- HTTP writes match the panel. Symbol POST: sessions +
  `enabled` / `group` / `broker_symbol` / `max_lot` / `max_margin_pct`.
  System POST: `max_margin_usage_pct`
  / `max_positions` / `max_lot` / `mt5_terminal_path` / `autostart_mt5`.
  Opt POST: `lookback_days` /
  `refine_rounds` / `max_combos`. Family / TF / exits / magic / grid /
  lot_mode / leftover symbol `max_positions` /
  daily_loss_* / size_by_edge / max_concurrent_risk_pct /
  `max_total_positions` / `risk_percent` are 400. `POST .../reset` is
  400. GET still returns readout fields.
- `POST /api/opt/run` `strategies` is **one-off**. Empty inherits the
  saved list. Do not persist a subset into `opt_params`. `apply_best`
  still defaults true.
- Holdout `capture = net_r / sum(mfe_r)` is a visible column. **Not** a
  score input and **not** an apply gate.
- Cursor is project lead and codes, **full authority vs Claude**.
  Claude executes Cursor briefs, scans on its own, and if the operator
  asks Claude, Claude does it and writes `claude/FOR_CURSOR.md`.
  No Antigravity auto-bridge. Yellow/red stay operator.
- Commit/push only when the operator asks. Named files; no secrets; no
  `--no-verify`. `cursor/`, `claude/`, `antigravity/` are gitignored.

## Important locations (only non-obvious)

- Runtime: `data/micofx.db`, `logs/micofx.log` (gitignored).
- Bridge (gitignored): Cursor writes `cursor/FOR_CLAUDE.md`; Claude
  writes `claude/FOR_CURSOR.md`. Shared wake `.bridge/WAKE.txt`.
  Cursor arms `cursor/ARM.bat` (watches Claude inbox). Claude arms
  `claude/ARM.bat` (watches Cursor inbox). Do not watch a file you write.
- Installer: `KUR.bat` → `KUR.ps1`. Launchers stay at repo root.
- Audit notes (not executable): `OPTIMIZATIONS.md`. Trust the closed
  ledger at the top.
- `graft/` is a stale dump — its line numbers are not live.

## Change safety rules

- Preserve walk-forward score and fill-next-open honesty unless asked.
- Do not invent families without holdout + `defaults.json` grid + UI +
  `STRATEGIES`.

## Known gotchas

- Next process loads HTTP-off exits (family/TF/magic/grid/reset 400).
  This PID still PATCHes them. GER40 `pending_exit_patch` still
  apply()s on flat either way. Do not add `/exit-override` unasked.
- Day cuts use `gmtime(naive broker epoch)` — "do not shift a second
  time", not "convert to UTC". A 00:00–03:00 local close is **today**.
  Hour buckets on autopsy `fill_time` are the same clock. Do not
  `fromtimestamp`/`localtime` those stamps (invents a 00:00 SL bucket).
- `_flush_entry_blocks` 45s window covers counters **and**
  `entry_block_events`. Do not restore `not events_dirty` skip.
  `reset` / symbol-delete / `shutdown` (after the worker joins) pass
  `force=True`. `execution.flush()` sits on the same side of `join`.
  Do not flush either blob before `_stop.set()` — the last in-flight
  cycle then hits a fresh window and drops its rows.
- Leftover per-symbol `max_positions` stays unread (DB 5/10 must not
  return). Live count is `SystemConfig.max_positions` (default 1).
  Per-symbol `max_lot` and `max_margin_pct` bind (0 = off; denetci +
  risk% size inside the cap). Leftover `max_concurrent_risk_pct` and
  `max_total_positions` stay unread. Search still scores `max_open=1`.
- Do not add an adverse-fill entry gate on `fill_vs_signal_close_r`.
  Walk-forward is fill-next-open (zero variance). Claude 18:45: Q4
  looks cursed in-sample; threshold scan is a curve-fit; unverifiable.
- `GET /api/ai` and `POST /api/logs/clear` are gone. Panel reads
  `STATE.ai`; Temizle is DOM-only. Do not restore the ring-wipe POST.
- Autopsy R divides by `|entry − original_sl|`. Do not rewrite pre-fix
  `sl`+`r=+1.0` rows; cash is the truth. Flatten rows before
  `fill["profit"]` have empty `profit` — **R is still valid**; do not
  sum autopsy `kar` across those 27. Panel/report “masada” is **winners
  only**; stored `left_on_table_r` still includes losers. `mfe_r` is an
  intrabar peak, not harvestable.
- Scale-out TRADE `kar=` is computed (`tick_value/tick_size` or
  `money_per_price_unit`), not `_closing_deal_pnl`. Pre-fix lines were
  `NxATR` with no cash.
- Keep-line is `(taze test …R)` or `(damga …R, dd.mm)`, not a live
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
  clear live `state.last_bar` after the verifier sleeps — that wipes a
  T+1 signal and files `filled_bars` under `""`.
- `_BAR_INTEGRITY_REFRESH = 900s` pins window ends (two small
  `copy_rates`) and full-fetches only on mismatch. `due` uses **broker**
  clock. Do not re-add a stale-bar 45s refresh. Pins are
  `(bars.time[0], bars.last_closed_time)` — **not** `forming_time`.
  `Bars` ctor 2nd arg is the forming candle. A middle-bar hole with
  both ends unchanged is the remaining miss.
- Calendar `_maybe_reoptimize` is gone. Apply age is `reject_reason`
  + `reopt_min_age_hours`. Quarantine still queues via
  `_queue_reoptimization` (retry cooldown). Do not resurrect a
  weekly/decay auto-search.
- `_MAX_SIGNAL_BAR_AGE_BARS = 2` × timeframe. US30 is the only M5; its
  600 s `bar_bosluk` on overnight drought is normal.
