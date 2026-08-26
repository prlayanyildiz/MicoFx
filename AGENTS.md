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
  `breakeven_at_r` (live 1.5, not 0.5 — BE-2 GER40 −32 R) and one-shot
  `partial_at_r` (ticket lot × 1/3, broker min/step). Neither is an
  `OPT_FIELDS` axis.
- `exits.overlay_stop` is the closed-bar trail/BE level. Live still owns
  broker clamp + modify. Change the helper or both callers. Cover
  identity tests.
- A forming candle never signals. Buy ∧ sell on one bar → neither.
- Opt apply writes `OPT_FIELDS` only (plus documented secondary fields).
  Never silently enable `ensemble_enabled`. `_slice_ok` /
  `_is_improvement` is the only gate; scheduled reopt uses the same path.
- `EXIT_RISK_FIELDS` mid-trade → **409**. `breakeven_at_r` and
  `partial_at_r` are deliberately **not** in that set.
- Watch mode never opens. Wrong `broker_symbol` → unavailable, no fuzzy
  fallback.
- Session / day-end / daily-loss flatten are settled (owner 09.08).
- `trail_start_atr <= trail_step_atr` is legal; do not ban it.
- Do not holdout-capture with positions open. Do not start a live search
  unasked.
- Tests must not append `logs/micofx.log` or `logs/gece_restart.log`.
  `gece_restart.say()` tests must patch the log path.
- **13 families.** Do not re-add `alpha_trend` or `mavilim`. `ichimoku`
  stays. Leftover DB names fail closed (no signal), they do not crash.
- **No restart while positions are open.** `track()` first-sights
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
- **Yellow** (ask): `risk_percent`, `max_positions`, supervisor,
  `size_by_edge`. **Red** (explicit): leverage, account lock, daily
  brake, live flatten-all.
- `POST /api/opt/run` `strategies` is **one-off**. Empty inherits the
  saved list. Do not persist a subset into `opt_params`. `apply_best`
  still defaults true.
- Holdout `capture = net_r / sum(mfe_r)` is a visible column. **Not** a
  score input and **not** an apply gate.
- Cursor is project lead and codes. Claude inspects and **must**
  question; no live PATCH/search/restart without Cursor OK. Antigravity
  suite is **manual only** (auto-bridge cut 26.08). Yellow/red stay
  operator.
- Commit/push only when the operator asks. Named files; no secrets; no
  `--no-verify`. `cursor/`, `claude/`, `antigravity/` are gitignored.

## Important locations (only non-obvious)

- Runtime: `data/micofx.db`, `logs/micofx.log` (gitignored).
- Bridge (gitignored): `cursor/FOR_CLAUDE.md`, `claude/FOR_CURSOR.md`,
  `cursor/HANDOFF_NEW_CHAT.md`. Cursor inbound: `cursor/watch_bridges.ps1`
  (**Claude only**; Antigravity auto-bridge cut). Claude inbox:
  `claude/WATCH.ps1`. Do not watch a file you write.
- Installer: `KUR.bat` → `KUR.ps1`. Launchers stay at repo root.
- Audit notes (not executable): `OPTIMIZATIONS.md`. Trust the closed
  ledger at the top.
- `graft/` is a stale dump — its line numbers are not live.

## Change safety rules

- Preserve walk-forward score and fill-next-open honesty unless asked.
- Do not invent families without holdout + `defaults.json` grid + UI +
  `STRATEGIES`.

## Known gotchas

- Day cuts use `gmtime(naive broker epoch)` — "do not shift a second
  time", not "convert to UTC". A 00:00–03:00 local close is **today**.
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
  `/api/symbols`; state carries `symbols_sig`. A 14-worker search can
  stall state for minutes (148s measured 26.08) — do not add a second
  `initialize()` to dodge it. Opt jobs share one npy folder per
  `(symbol, TF)` (`bars_path`); do not pickle the window onto every family.
- `STRATEGY_TIMEFRAMES` empty = unlocked. Opt start line must use
  `tf_lock_status`; do not hardcode `scalp TF kilidi acik`.
- Panel flatten-all must pass `close_all(reason=)`. A reason-less
  `Pozisyon kapatildi kar~` burst (26.08 12:22) cannot be autopsied.
- Fill verifier `sleep`s on a **side thread** (`defer_verify`). Do not
  delete the sleeps; do not return `verified_unfilled` early.
- `_BAR_INTEGRITY_REFRESH = 900s` is the no-new-bar full fetch.
  `_STALE_BAR_REFRESH = 45` is unused — do not wire it back. `due` uses
  **broker** clock.
- `_MAX_SIGNAL_BAR_AGE_BARS = 2` × timeframe. US30 is the only M5; its
  600 s `bar_bosluk` on overnight drought is normal.
