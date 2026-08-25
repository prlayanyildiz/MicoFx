# AGENTS.md

This tree is the live **fx** bot (`C:\Users\Administrator\MicoFx`). Constitution: `MASTER_PROMPT.md` §19. Do not copy remaining `D:\MicoAi` extras (`orb_retest`, Ai score formula, `autostart_mt5`) unless asked. `trail_mode` / `hour_risk_scales` / `max_combos=2000` are already here.

## Must-follow constraints

- Python: `C:\MicoFX-venv\Scripts\python.exe` (not system Python, not a second venv).
- Live process owns `data/micofx.db` and the MT5 terminal. No second sqlite writer. No `mt5.initialize()` sidecar. **Never** `mt5.shutdown()` except the dying process on `/api/app/restart`.
- Live writes go through the running bot: `GET http://127.0.0.1:8900/` (session cookie) then API. Critical mutations need `Origin: http://127.0.0.1:8900`. Port busy → do not steal 8900.
- No LLM / third-party coder **inside** the engine, optimizer, or supervisor. Panel "AI" is the rule supervisor.
- Exit model: hard ATR stop + ATR trail. Do not reintroduce `tp_atr_mult`, partials, `max_bars_in_trade`, `stale_exit_ratio`, or `breakeven_atr`. `breakeven_at_r` is a config overlay (0 = off; live 1.5). **Not** an `OPT_FIELDS` axis. Do not apply 0.5 R (BE-2 GER40 −32 R).
- `engine._update_stop` and `backtest.simulate` are the same exit rule twice. Change both. Cover identity tests.
- Forming candle never signals. Buy∧sell on one bar → neither side.
- Opt apply writes only `OPT_FIELDS` (plus documented secondary fields). Never silently enable `ensemble_enabled`. OOS `_slice_ok` / `_is_improvement` is the only apply gate; scheduled reopt uses the same path.
- `EXIT_RISK_FIELDS` mid-trade → API 409. `breakeven_at_r` is currently **not** in that set (25.08 apply-with-opens). Do not add it while positions are open unless the operator accepts 409.
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

## Known gotchas

- `poll_interval_sec` default 2s; watch-only floor 3s. Panel `/api/state` every 3s (1.5s during opt) shares the MT5 lock with the engine.
- Fill verifier can `sleep` ~2.1s **on the engine thread** (`mt5client.py`). Do not "fix" duplicate-entry protection while changing this.
- `_STALE_BAR_REFRESH = 45s` can recompute full `required_bars` even with no new bar. `due` must use **broker** clock, not local minus naive bar time.
- `cursor/` and `claude/` are gitignored; do not `git add` them. Tests that call `gece_restart.say()` must patch the log path.
- `graft/` is stale sourcedump — do not treat line numbers there as live.
