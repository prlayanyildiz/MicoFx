# AGENTS.md

This tree is the live **fx** bot (`C:\Users\Administrator\MicoFx`). Constitution: `MASTER_PROMPT.md` §19. Do not copy remaining `D:\MicoAi` extras (`orb_retest`, Ai score formula, `autostart_mt5`) unless asked. `trail_mode` / `hour_risk_scales` / `max_combos=2000` are already here.

## Must-follow constraints

- Python: `C:\MicoFX-venv\Scripts\python.exe` (not system Python, not a second venv).
- Live process owns `data/micofx.db` and the MT5 terminal. No second sqlite writer. No `mt5.initialize()` sidecar. **Never** `mt5.shutdown()` except the dying process on `/api/app/restart`.
- Live writes go through the running bot: `GET http://127.0.0.1:8900/` (session cookie) then API. Critical mutations need `Origin: http://127.0.0.1:8900`. Port busy → do not steal 8900.
- No LLM / third-party coder **inside** the engine, optimizer, or supervisor. Panel "AI" is the rule supervisor.
- Exit model: hard ATR stop + ATR trail. Do not reintroduce `tp_atr_mult`, `partial_tp_r` ladders, `max_bars_in_trade`, `stale_exit_ratio`, or `breakeven_atr`. Overlays (0 = off): `breakeven_at_r` (live 1.5; not 0.5 — BE-2 GER40 −32 R) and one-shot `partial_at_r` (lot from ticket × 1/3, broker min/step). Neither is an `OPT_FIELDS` axis.
- `engine._update_stop` and `backtest.simulate` are the same exit rule twice. Change both. Cover identity tests.
- Forming candle never signals. Buy∧sell on one bar → neither side.
- Opt apply writes only `OPT_FIELDS` (plus documented secondary fields). Never silently enable `ensemble_enabled`. OOS `_slice_ok` / `_is_improvement` is the only apply gate; scheduled reopt uses the same path.
- `EXIT_RISK_FIELDS` mid-trade → API 409. `breakeven_at_r` and `partial_at_r` are **not** in that set: overlays apply to already-open tickets (25.08 GER 0→1.5 then fired). Intended; do not add them unless the operator accepts 409.
- Watch mode never opens. Wrong `broker_symbol` → unavailable, no fuzzy fallback.
- Session flatten / day-end flatten / daily-loss flatten are settled (owner 09.08). Do not "fix" them.
- `trail_start_atr <= trail_step_atr` is legal. Do not add a grid/UI ban.
- Do not holdout-capture while positions are open. Do not start a live search unless asked.
- Tests must not append `logs/micofx.log` or `logs/gece_restart.log`.

## Validation before finishing

```
C:\MicoFX-venv\Scripts\python.exe -m pytest tests/<touched>.py -q --tb=short
C:\MicoFX-venv\Scripts\python.exe -m ruff check micofx/ tests/<touched>.py
```

Fail-first: write the test, watch it fail, then implement. `pyproject.toml` already sets `--basetemp=.pytest_tmp` (Windows symlink policy).

## Repo-specific conventions

- UI/log strings: Turkish. Comments/commit subject: English *why*.
- Persist only via `Store` methods. Immediate write, no separate Save.
- All MT5 through `MT5Client` + its `RLock`. Web handlers must not import `MetaTrader5` directly.
- New search axis: add to `OPT_FIELDS` **and** pay the grid-size cost; otherwise `Store.opt_params()` drops it.
- Yellow (ask): `risk_percent`, `max_positions`, supervisor, `size_by_edge`. Red (do not touch unless explicit): leverage, account lock, daily brake, live flatten-all.

## Important locations (only non-obvious)

- Runtime DB/log: `data/micofx.db`, `logs/micofx.log` (gitignored).
- Agent bridge (gitignored): `cursor/FOR_CLAUDE.md` (event-only), `claude/FOR_CURSOR.md`.
- Installer: `KUR.bat` → `KUR.ps1`. Launchers stay at repo root.
- Audit notes (not executable): `OPTIMIZATIONS.md`.

## Change safety rules

- Preserve walk-forward score formula and fill-next-open honesty unless explicitly asked to change them.
- Do not invent strategy families without holdout + `defaults.json` grid + UI + `STRATEGIES`.
- Commit/push only when the operator asks (or a standing order in **this** conversation). Named files only; no secrets; no `--no-verify`.
- Cursor is project lead: every product change needs Cursor approval. Claude may inspect anything (book, logs, autopsy, diff) and **must** question; Claude does not ship patches, PATCH, search, or restart without that approval. Yellow/red gates stay operator.

## Known gotchas

- Book / autopsy day cuts use **`gmtime` / UTC**, same as `risk.py` `day_key` (daily brake). Local UTC+3 calendar dates (00:00–03:00 closes) are the previous UTC day — that was the 44 vs 30 count.
- Autopsy `r_realised` / `mfe_r` / `mae_r` divide by `|entry − original_sl|` (fallback `risk_dist`). **Do not rewrite** the pre-fix rows (25.08: five `sl`+`r=+1.0`, including the GER40 trio). Cash/`kar=` is the truth for those. First clean check is a ticket opened *after* the patch is live that then dies on a trailed SL — `r_realised` must not be 1.0 and must match cash R within 2%. Do not restart while opens exist just to load the patch — `track()` first-sight would freeze `original_sl` to the current trail.
- Scale-out TRADE log is `kar={cash}, {R}R` (gate R = `profit_dist / original_risk`). Pre-fix lines were `NxATR` with no cash — do not derive P&L from those.
- `scale_out_done` prunes to live tickets in `manage_positions` (same lock as weekend_pending). `remain` uses `fill["volume"]`; `done.add` stays one-shot even on IOC `DONE_PARTIAL`.
- Panel `/api/state` every 3s (does not speed up during a search) shares the MT5 lock with the engine.
- Fill verifier can `sleep` ~2.1s **on the engine thread** (`mt5client.py`). Do not "fix" duplicate-entry protection while changing this.
- `_BAR_INTEGRITY_REFRESH = 900s` is the no-new-bar full `required_bars` fetch. `due` must use **broker** clock, not local minus naive bar time.
- `cursor/` and `claude/` are gitignored; do not `git add` them. Tests that call `gece_restart.say()` must patch the log path.
- `graft/` is stale sourcedump — do not treat line numbers there as live.
