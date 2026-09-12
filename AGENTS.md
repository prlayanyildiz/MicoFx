# AGENTS.md

Live **fx** bot, `C:\Users\Administrator\MicoFx`. Constitution:
`MASTER_PROMPT.md` §19. Do not port remaining `D:\MicoAi` extras
(`orb_retest`, Ai score formula) unasked. `autostart_mt5` /
`trail_mode` / `hour_risk_scales` / `max_combos=2000` are already here.

## Operator charter — 07.09 (full agent authority & profit mandate)

Operator granted **full operator authority** to Cursor / Claude /
Antigravity (Gemini), including rewriting this constitution and
MASTER_PROMPT, with explicit directive: *"anayasa benim kısıtlı bilgimle
oluştu en iyi sistemi için olması gereken neyse yapın. herkesin
değiştirebilirsiniz yeterki çok iyi.kar eden bir otomatik sistem olsun."*

1. **Solo Cursor (12.09).** Operator cancelled all peer bridges
   (`FOR_GEMINI` / `FOR_CLAUDE` / Antigravity): Claude and Gemini are
   offline. **Cursor lands alone** — no peer ACK wait. Yellow/red that
   used to wait on peers now land under operator chat authority. Safety
   floor (item 4) still binds. Do not resurrect bridge ACK as a blocker
   unasked; bridge files may exist as archives only.
2. **Book is 3 symbols: `GER40 NAS100 XAUUSD`.** It went 7 -> 3 -> 4 -> 3
   across 10-11.09, all operator calls. **Staying deleted**: JPN225 + BTCUSD
   (10.09 10:42), SpotBrent (21:37), BRENTOIL-PERP (22:2x - added and cut the
   same evening, before it ever traded: every session window the search tried
   scored negative, -16.1 on all-hours, and its one selection-clearing
   candidate was refused for a negative costed holdout), and **US30** (out
   21:35, back 23:3x, out for good 11.09 - "us30 verimsizse sil spread 20
   onda"). All five are in `tests/retired_lexicon.py: RETIRED_SYMBOLS`, so a
   seed-overwrite cannot rebuild them.
   US30 lost on three independent axes that agreed: **cost** - median traded
   spread 0.0694 ATR against NAS100's 0.0167 and XAUUSD's 0.0144, four times
   the next index; **correlation** - +0.799 with NAS100 and +0.744 with GER40
   while XAUUSD sits at ~0.15, so it was the least diversifying row in the
   book; **yield** - backtest holdout +0.0495 R/day, the bottom, and live
   -4.00R at PF 0.93 over 98 trades. The correlation is what settled it: the
   per-symbol position cap came off the same day, and three index legs at
   0.69-0.80 stack one bet.
   Do **not** re-add the retired five unasked, and do
   **not** disable, delete, or “close for bleed” the three that remain.
   Improve fill / exits / gates / sizing / search instead (“kapatma
   geliştir”).
   The old “7 symbols, +393.5 R holdout” line described account
   61562752. The terminal is **61592522 @ Pepperstone-Demo** as of 10.09
   21:27 (its own install, `MetaTrader 5 - 1`, separate from the
   real-money terminal another project drives), so that R total belongs
   to an account this book does not trade. Two searches on 10.09 applied
   0 of 5 — and the reason is measured, not guessed: the incumbents beat
   the best candidate by 7 / 42 / 58 points on GER40 / US30 / NAS100
   (`scripts/ab_search.py`). "Zero applied" is the gates working, not a
   fault. Coverage is *not* the bottleneck: `burst` is searched at 0.005%
   and it does not matter when the incumbent is 2-3x the best candidate.
3. **Full capacity + full auto + dynamic growth sizing.** Goal is
   maximum useful throughput under honest WFO/fill gates and a hands-off
   loop (autopilot, quarantine reopt, calibrate, watches). Inline kasa
   sizing scales dynamically with equity (`LOT_MULT_MAX = 2.5`,
   expanded equity tiers — `kasa_sizing.py` basamakları: under $2K=1.15-1.3x,
   $2K-$3.5K=1.5x, $3.5K-$6K=1.75x, $8K≈1.95x, $10.5K=2.2x tier,
   $13.5K+=2.5x tavan),
   while `max_concurrent_risk_pct = 25%` is the book-wide risk brake.
   Per-symbol `max_positions` is live again at **1** on the book (12.09:
   scale-in autopsy −17.9R / ~34% of live loss; operator override of the
   earlier unlimited-0 charter). `0` still means unlimited in code.
   Push to GitHub when a material package lands (operator 07.09; no peer
   ACK required while bridges are cancelled).
4. **Safety floor still binds the process:** one Python, live owns
   DB/MT5, Origin on writes, no second `mt5.initialize()`, no LLM in
   engine/optimizer/supervisor. Solo authority does not waive these.
5. **No account lock — the bot follows the terminal.** Removed 10.09
   (operator: "hedefteki mt5 hesap neyse o olsun"). `account_lock.py`,
   `Engine._enforce_account_lock`, `POST /api/account-lock` and
   `SystemConfig.account_lock_login/_server` are **gone**; do not bring
   any of them back unasked. Whatever account the terminal has open is
   the account that trades, demo or real, with no confirmation step.
   What remains is a record, not a gate: `_note_attached_account` logs
   the attached account once per change (ERROR + "GERCEK PARA" on a real
   account) and the Sistem tab shows the account and its type. **This is
   now the only thing standing between an accidental live login and live
   fills on a demo-tuned book** — the 06.09 live→demo migration was made
   safe by the lock refusing entries, and that route no longer exists.
   Pinned by `tests/test_the_bot_follows_the_attached_account.py`.

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
- **Never rank on the holdout. It is the referee, and selecting on it
  consumes it.** `scripts/gate_verdict.py` ranked on holdout R/day and printed
  "en iyi kapi" until 11.09. That is how NAS100 got `adx_min=10` /
  `min_body_ratio=0.1` written live. Scored on all five slices afterwards:

      adx/body   sel-1    sel-2    sel-3   valid   HOLD    worst
      0 / 0.2    0.0311  +0.0066   0.0716  0.1341  0.1452  +0.0066   <- incumbent
      10 / 0.1   0.0379  -0.0325   0.0467  0.0808  0.1719  -0.0325   <- what landed

  Best on the one slice it was ranked on, worse on the other four, and
  negative on a selection segment. Reverted the same day. The tool now
  describes the holdout and refuses to name a winner.
  **Read the worst slice, not the best number**, and read the curve's shape:
  a lone spike between two lower neighbours is noise, not edge.
  **And check the value is IN THE GRID.** `adx_min=10` is not
  (`[0, 15, 20, 12, 18, 25]`), nor is `max_spread_atr=0.06` - an off-grid live
  value is one the search can neither re-derive nor refute, so it sits there
  forever unexamined.
- **The selection score is NOT an optimisation target. Measured 11.09.**
  Coordinate descent (`scripts/symbol_engine.py`) walks the grid axis by axis
  instead of sampling it, ranking on `walk_forward`'s own score. It raised the
  score enormously and destroyed the holdout on two symbols of three:
  GER40 score 2.5 -> 7.2 with holdout +0.0684 -> **+0.1030** R/day;
  NAS100 score 0.23 -> **18.5 (79x)** with holdout +0.1719 -> **+0.0851**;
  XAUUSD score 6.4 -> 28.4 with holdout +0.3689 -> **+0.1555**, PF 1.39 ->
  1.14 and drawdown 13.8 -> **30.4**. One positive in three is chance.
  Two consequences, and the second one overturns a claim made earlier the
  same day:
  (1) Any search that optimises this score hard enough will overfit. The
  bigger the score jump, the worse the holdout - that ratio is the warning
  sign to watch.
  (2) `max_combos=2000` against a multi-billion grid is **regularisation, not
  a bottleneck**. I called the grid-to-budget ratio "the real bottleneck" at
  midday; removing the limit made the system measurably worse. More search is
  not the fix; a selection criterion that survives out of sample is. That is
  what the literature on deflated Sharpe / probability of backtest overfitting
  (Bailey & Lopez de Prado) and combinatorial purged CV is for, and it is the
  open question here.
  The tool stays because the experiment is worth repeating, and because a
  coordinate walk is the cheapest way to ask "is this config a plateau or a
  spike". It must not be used to write a live config on score alone.
- **A flip gate benchmarks what the incumbent earns NOW, never a stamp.**
  F1/F2 read `_flip_benchmark`, which prefers the sweep's own
  `baseline["holdout"]` (the live config replayed on that sweep's holdout
  slice, `backtest.py:1536` - same bars, same window, same cost regime,
  already computed), then a `_fresh_incumbent_holdout` replay, then the
  stamp. Until 10.09 they read `cfg.opt_summary["holdout"]` directly, and
  the bar was four to five times what the incumbent actually delivers on the
  slice being compared. Candidate vs incumbent **on the same holdout slice**,
  against the bar that was applied:
  NAS100 `range_fade`/M30 +21.5R PF 1.45 vs +16.8R PF 1.27, bar **79.1R**;
  XAUUSD +33.2R PF 1.10 vs +31.0R PF 1.11, bar **162.2R**;
  US30 `keltner_break`/M30 +26.2R PF 1.15 vs +17.2R PF 1.05, bar **27.0R**.
  With the measurement in its place those bars are 19.3R, 35.6R and 19.8R -
  two pass, XAUUSD still fails on a genuine +2R margin, which is what the
  churn brake is for. This is why the operator said "taramada isle yaramiyor
  aile vs bulamiyr". The rejection now names its benchmark (`ayni kosu` /
  `taze test` / `damga`); if you ever see `damga` on a symbol that has bars,
  ask why there was no replay.
  **Read the right baseline.** `baseline["net_r"]` is the incumbent over the
  whole span (-22.6R / -30.1R / -17.9R for those three) and
  `baseline["holdout"]["net_r"]` is the incumbent on the holdout slice. The
  gates compare the slice. Quoting the span number as "the incumbent loses
  money" overstates the case badly - it was quoted that way in this file on
  11.09 and corrected the same night.
- `EXIT_RISK_FIELDS` mid-trade â†’ **409**. `breakeven_at_r`,
  `partial_at_r`, `harvest_at_r` and `harvest_step_atr` are
  deliberately **not** in that set.
- The live **trade mask** is four fields, not two:
  `_SESSION_CLOCK_FIELDS = {use_sessions, sessions, trade_days,
  flat_before_close_min}`. `session_state()` re-reads `trade_days` and
  `should_flatten()` re-reads `flat_before_close_min` off the live cfg every
  cycle, exactly as they re-read the windows, so all four decide whether an
  open ticket gets truncated *now*. Moving any of them while this magic has
  tickets (or a pending orphan scan) → **409**, on the per-symbol route
  **and** on `/api/symbols-bulk` — bulk reached these fields with no check at
  all, so one batch could truncate the whole book. A mask edit that lands
  restamps the costed holdout (both routes; the stored number was measured
  under the old mask). Add a field to the mask → add it to that set, not to a
  second copy of the check.
- Watch mode never opens. Wrong `broker_symbol` â†’ unavailable, no fuzzy
 fallback.
- `spread_calibration.cap_from_bands` defaults widen-only
  (`daraltilmadi` when calm band is under live). System
  `spread_narrow_on_calm` (default on, 07.09) may step the cap down
  by at most 0.02 ATR units per calibrate — not a free fall (F49).
- Session / day-end / daily-loss flatten are settled (owner 09.08).
- `trail_start_atr <= trail_step_atr` is legal; do not ban it.
- No trail axis may cap below where the book lands
  (`test_trail_grid_reaches_past_the_incumbents`). `keltner_break`
  `trail_step_atr` shipped `[0.6, 1.0, 1.5]` while all 7 live symbols run
  2.2–3.6, so the family could not express any trail that has ever won —
  the ceiling was choosing the parameter. Widened to `2.8` (same top as
  shared / `channel_break`) 10.09, operator authority in chat. Budget is
  unchanged (`coverage_budget` splits a fixed pool); the family's own
  coverage goes 51% → 31%, which is still far above the million-combo
  families' 0%. `super_trend` had the same defect one notch higher (2.0,
  which clears the guard but is still under every live value) and took the
  same `2.8`. Neither family's tight end moved.
- **Do not take the gate axes out of the search grids.** Proposed 10.09 on a
  coverage argument (`burst` is 42M combos at a 2000 budget = 0.005%, and
  `max_spread_atr` × `cost_rank_max` × `adx_min` × `min_body_ratio` is a 160×
  multiplier that `scripts/axis_exec.py` tunes again afterwards). Peer-ACK'd
  YES/Yellow by Cursor and Gemini, then **measured and refuted** — the A/B
  Gemini required is the only reason it did not land. GER40 M30, same bars,
  same 2000 budget, same seed, only the grid differing:

      channel_break  13.897 -> 13.723    11,025,000 -> 275,625
      keltner_break   5.786 ->  5.662         6,480 ->     720
      super_trend     5.332 ->  0.679         3,888 ->     432

  The last two lean grids fit under the budget, so they are searched
  **exhaustively** - sampling luck and `combo_seed` cannot explain the loss,
  and super_trend still fell 8x. Candidates clearing the gates collapsed
  197 -> 17.

  Mechanism: `Params.from_config` inherits an axis that is not in the grid
  from the **live cfg** (verified - it works correctly). GER40's live cfg is
  tuned for `channel_break`, so with the gates out of the grid every
  `keltner_break` / `super_trend` challenger is measured at a rival family's
  gates. Families are ranked head to head, so this cripples the challenger by
  construction. The gate axes are part of the edge, not a duplicate of the
  post-hoc tuner.

  The coverage number stands and is still unexplained; this particular fix
  for it does not. Do not re-propose it without a *different* mechanism.
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
- **There is no backup feature.** Removed whole 10.09 (operator: "yedekle
  alakali tum kalintilari temizle", after "backup.py surecini bastan sona
  iptal edelim"). Gone: `backup.py`, the `MicoFX Aksam Yedegi` scheduled
  task, `KUR.ps1`'s step 5, `SystemConfig.backup_*` (all five fields), the
  `/api/system` path validation and UNC latch, the panel's Yedek block and
  its `field_help` entries, the shipped config keys, and nine tests. Do not
  reintroduce any of it unasked.
  What it costs, recorded where the decision is: `data/micofx.db` is not in
  Git, so every symbol config, optimiser result and supervisor verdict now
  exists in **exactly one copy**, with nothing in the codebase able to make
  another. Two old archives still sit in `C:\MicoFX_Yedek` - they were left
  deliberately, being the only copies of any earlier DB state.
  Pinned by `tests/test_there_is_no_backup_feature.py`, which checks the whole
  surface (script, config keys, model fields, imports, installer task, log)
  because the feature was trimmed in pieces twice before and grew back both
  times from a leftover default key.
- **7 families.** `ichimoku` retired 02.09 (no symbol/TF holdout win).
  `stoch_flip`, `dual_t3`, `t3_flip`, `parabolic_flip` retired 01.09
  (flip/zero-win class). `nr_break` / `roc_pace` **fully deleted** 03.09
  (matrix: never best; operator full-delete). `band_fade` not shipped.
  Live search set: `burst`, `mtf_pullback`, `channel_break`, `super_trend`
  (added 07.09: dynamic volatility envelope breakout / continuation, 7/7
  holdout net profitable +341.85 R total), `keltner_break` (added 07.09:
  dynamic Keltner Channel EMA+ATR envelope breakout, 7/7 holdout net
  profitable +392.7 R total). `range_fade` / `sweep_fade` **joined the live
  search set 10.09** (operator: full authority, "strategiler sorun");
  dormant since 04.09, never once ranked by the real search.

  The reason to try them: the other five are four breakout/trend shapes plus
  one pullback - a monotone book. Measured offline first, and they lost badly
  (best 3-15 against incumbents of 21-94). That test is **not** the reason to
  keep them out, because it is flawed the same way the gate-axis proposal was:
  `ab_search` calls `walk_forward` directly and skips the session shortlist
  pre-step, so both fades ran on the *incumbent's* window - NAS100's
  15:00-21:00 is a breakout window, and a mean-reversion family wants
  different hours. The real search picks a window per candidate, which is the
  only honest test, and enabling them is how it gets run.

  Safe because the gates are the guard, not the list: nothing applies unless
  it beats the incumbent, and 10.09 measured that bar at 21 / 75 / 94 across
  GER40 / US30 / NAS100 with four of four incumbents unbeaten. Cost is search
  time (the searched set goes from five to seven, ~+40%). Reverting is
  one line in `config/defaults.json`.

  Leftover DB names fail closed.
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
- **Yellow** (solo Cursor while bridges cancelled 12.09): supervisor knobs,
  AI soft-size, session widen, opt run/apply, unfreeze checklist,
  concurrent/lot bumps — land with a measured note in chat/log; no peer wait.
  **Red** (solo + explicit risk note in the brief): leverage,
  daily_loss, live flatten-all, and anything that changes *which* MT5
  account or which symbols trade (the account lock that used to make the
  first of those a controlled step is gone — see charter item 5).
  Operator chat still overrides everything.
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
- Cursor is project lead and codes with **solo full authority** while
  Claude/Gemini bridges are cancelled (operator 12.09). Do not block
  lands on peer ACK. Re-arm bridges only if the operator asks.
- Commit/push only when the operator asks. Named files; no secrets; no
  `--no-verify`. `cursor/`, `claude/`, `antigravity/` are gitignored.

## Important locations (only non-obvious)

- Runtime: `data/micofx.db`, `logs/micofx.log` (gitignored).
- Bridge (gitignored; **cancelled 12.09** — archive only, not a land gate):
  - Claude: Cursor → `cursor/FOR_CLAUDE.md`; Claude → `claude/FOR_CURSOR.md`.
  - Gemini: Antigravity → `antigravity/FOR_GEMINI.md` (and/or
    `FOR_CURSOR.md`); Cursor → `cursor/FOR_GEMINI.md`.
  - Shared wake `.bridge/WAKE.txt`. Do not arm peer watchers unasked
    while bridges are cancelled.
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
- Live count allows **scale-in tickets up to `cfg.max_positions`, and the
  1..5 clip is GONE (operator 11.09: "max poz limit ve sinirini kaldir").**
  `risk.position_cap` owns it: **0 = no per-symbol limit**, any positive value
  is honoured as written. One helper, so the decision can be found and
  reversed in one place.
  What governs instead: book-wide `max_concurrent_risk_pct` (25%, re-armed
  31.08 as exactly this backstop), one new fill per symbol per closed bar,
  0.75 ATR spacing profit-direction only, no hedging, `daily_loss_pct`,
  margin share.
  **The evidence against stacking was not refuted, it was overruled** - record
  it so nobody re-derives it as news: (1) 13.08, JPN225 took eight SELLs into
  a rising market, five stacked tickets gave back 38.44 while the two trailed
  ones made +34.80 (NAS100 held seven BUYs, GER40 five) - "not ten times the
  risk, ten times the same risk"; (2) `walk_forward` validates exactly ONE
  position, so every searched number - PF, expectancy, above all `max_dd_r` -
  describes a one-position system; (3) measured 11.09, 85 scale-in tickets
  returned **-24.03R** at a 29.4% win rate, 30% of the whole loss;
  (4) the index legs are the same bet - US30/NAS100 correlate **+0.799**,
  US30/GER40 +0.744, NAS100/GER40 +0.691 (XAUUSD is independent at ~0.15).
  (Was: operator + peer ACK 07.09, edge-weighted caps XAUUSD=5, SpotBrent=4,
  GER40=3, BTCUSD=3, US30=2, JPN225=2, NAS100=2.)
  Guarded against 13.08 restack via: (1) ATR spacing >= 0.75 ATR from nearest open
  ticket (strictly profit-direction only — BUY: eff_px >= max(opens)+0.75ATR, SELL: eff_px <= min(opens)-0.75ATR;
  was 1.0 ATR until 08.09 — entry_blocks showed risk_kademe_aralik blocking 0.7–0.85 ATR trends;
  losers do not add — bug fixed and regression tested 07.09 dc61af5), (2) max 1 new fill per symbol
  per closed bar (`_filled_bars`), (3) **each ticket sized at full nominal 1R**
  (`risk_percent` / auto-1R / margin share — not divided by `max_positions`;
  dividing ate baseline income on single-ticket fills, fixed 07.09 `406d3b2`),
  (4) book-wide `max_concurrent_risk_pct` (expanded to 25.0%, 07.09 Cursor ACK)
  and daily loss bounds remain the stack governor when several full tickets are open,
  (5) no hedging (opposite side blocked). **Symbol** `max_positions` (DB payload,
  per-symbol 0-100, 0 = unlimited) is live and read by the engine. **System
  POST** `/api/system max_positions` returns 400 (HTTP-off). Search still scores `max_open=1` for honest WFO.
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
  curve-fit; unverifiable). Live `chase_max_atr` (book **0.35** on all 7;
  shipped default still 0.25) is a separate ATR-unit tick-vs-signal-close
  ceiling in `_try_entry`; 0 = off. Autopilot may nudge +0.05 toward **0.40**
  from `kovalama_asimi` pressure; never re-arms chase when 0.
  Walk-forward stays fill-next-open (zero variance).
- **Entry-block taxonomy (08.09 Gemini ACK):** soft (`seans_disi`, `bar_doldu`,
  weekend/clock…) vs capacity (`risk_sembol_limiti`, `risk_kademe_aralik`…)
  vs actionable (`spread`, `kovalama_asimi`). Tanı **Hard fill** ignores soft.
  AP: spread calibrate + chase nudge; **SpotBrent `max_spread_atr` pin 0.06**
  (no blind widen). Do not treat soft/capacity as MSA fodder; never disable
  symbols for bleed. `dominant_class` follows `auto_hint` when actionable.
- `GET /api/ai` and `POST /api/logs/clear` are gone. Panel reads
  `STATE.ai`; Temizle is DOM-only. Do not restore the ring-wipe POST.
- `rsi_length`, `stoch_length`, `smooth_k`, `smooth_d` are **NOT dead code**.
  They drive `cache.stoch()` at `strategy.py:449` → `indicators.py:256`
  (`stoch_rsi()`) → StochRSI oscillator panel display. Removing them breaks
  the UI panel. (08.09 Gemini audit; confirmed alive.)
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
  R/day, so it stays gone.
  **Re-measured 11.09 and it stands - 4/4 loss.** Worth doing because the
  book had gained two families and because half the 05.09 verdict leaned on
  the two positive symbols sitting "far under their live bar", and that bar
  turned out to be an inflated stamp. Seven families, both bars, same budget,
  offline from the archived snapshots (`scripts/m5_verdict.py`), on R/day:
  GER40 +0.0684 live vs **no validated candidate on the retired bar**,
  NAS100 +0.1452 vs **none**, US30 +0.0495 vs **none**, XAUUSD +0.3689 vs
  +0.0579. Three of four symbols cannot produce a single validated candidate
  on that retired bar out of seven families.
  Remember the shape of the trap, because it is what pulled this retired bar
  back in on 03.09: 26 of 27 sweeps DID produce a candidate and failed the
  validation slice, and their raw holdout numbers run four to ten times the
  live R/day (GER40 `burst` +0.284, US30 `burst` +0.319, XAUUSD
  `mtf_pullback` +0.743). A big holdout number on a retired bar is the
  symptom, not the find - quote a **validated** R/day or leave it retired.
  Reopening
  needs `models.TIMEFRAMES` **and** `config/defaults.json optimizer.timeframes`
  - and that is all. `store.opt_params()` unions the shipped list into the
  stored blob on every read, so the stored `opt_params.timeframes` does NOT
  have to be edited. This paragraph claimed it did until 05.09; resurrection
  is a two-file change, cheaper than documented, so treat both files as live
  risk surfaces.
