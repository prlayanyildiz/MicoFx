# MicoFX / MicoAi Family — Master Agent Prompt

Use this prompt when working on any of:
- `D:\MicoFX` (ops / portfolio / strict MT5 lock — primary live FX tree)
- `D:\MicoFX Orj` (lean baseline snapshot)
- `D:\MicoAi` (richer exits / scoring / risk experiments)

They are **one product line**, not three products. Branding is `MicoFX` (legacy name MicoAI; first run may rename `data/micoai.db` → `data/micofx.db`).

At the start of a task, detect which tree is the workspace root and enable only that variant’s extras (see §19). Never mix Ai experimental scoring into FX without an explicit ask.

---

## 0. The exit model — one regime, do not add to it

Read this before touching anything that closes a position.

The trade's **own** exit logic is the stop and nothing else:

1. **Hard stop.** `max(sl_atr_mult * ATR, broker min_stop)`, attached to the
   entry order and never lifted. It is the only protection that survives the
   process, the machine or the connection dying. Never make it conditional.
2. **ATR trail.** Once open profit reaches `trail_start_atr * ATR`, the stop
   follows `trail_step_atr * ATR` behind the **closed bar's** price. Ratchet
   only: never widens, never lands worse than the original hard stop.

**But three flattens close positions over the top of that, and they do fire on
winners.** Say so plainly — "the trail is the only way out" is true of the
trade's logic, not of the system:

| Flatten | Source | Currently |
|---|---|---|
| Session end | `cfg.flat_before_close_min` | **5 min, on every symbol** |
| Day end | `system.day_end_flatten_min` | **5 min** |
| Daily loss halt | `system.daily_loss_flatten` | on |
| Weekend | `sessions.weekend_closed` | on (crypto exempt) |

With near-24h session windows the first two mean **no position survives the
local day**, so an H1 trend follower cannot hold a multi-day move.

**This is a settled decision, confirmed by the owner on 2026-08-09: keep it.**
The reasoning is overnight gap risk on a small account — an index or commodity
gap jumps straight over the hard stop, which is the one protection the model
leans on entirely. Every current optimizer result was also measured under this
constraint, so removing it would invalidate the whole portfolio at once.

Do not file this as a bug and do not "fix" it. If it is ever revisited it is a
deliberate change that requires a full re-optimization, and the daily-loss
flatten stays regardless (that one is account risk, not a view on the trade).

### Breakeven — state it exactly

The trail target is `close - trail_step_atr * ATR`, so it is above entry
**exactly when open profit exceeds `trail_step_atr * ATR`**. Unconditional;
`trail_start_atr` does not enter into it.

`trail_start_atr <= trail_step_atr` is therefore **legal and often better**,
not a misconfiguration. It only means the trail starts tightening the stop
while it is still below entry, cutting risk earlier. Measured on a
ramp-then-collapse replay (`tests/test_trail_breakeven_invariant.py`):

| pair | +1.0 ATR | +1.5 ATR | +2.0 ATR | +3.0 ATR |
|---|---|---|---|---|
| 0.5 / 1.6 (`start < step`) | −0.60R | −0.10R | +0.40R | +1.40R |
| 2.0 / 1.6 (`start > step`) | −1.00R | −1.00R | +0.40R | +1.40R |

Identical past breakeven, strictly better before it. **Do not add a grid rule,
apply validation or UI check forbidding `start <= step`** — an earlier, looser
wording of this section caused exactly that proposal.

**Deliberately removed. Do not reintroduce, and do not accept a config,
grid axis or UI field that reimplements one:**

| Gone | Why |
|---|---|
| `tp_atr_mult` (take-profit) | Caps the winners that pay for the losers. The trail decides when a move is over by watching it, not by naming a price up front. |
| `partial_tp_r` / `partial2_tp_r` + fractions | Scale-outs truncate the same tail for the same reason, and split one trade's R across rungs. |
| `max_bars_in_trade` (time stop) | Closes a position because the clock ran out — exactly the trends worth holding. |
| `stale_exit_ratio` | Same, for losers; the hard stop already bounds them. |
| `breakeven_atr` | A separate "snap to exact entry" step scratches winners on ordinary noise. The trail crosses entry on its own — see the exact rule above. |

Three numbers per symbol carry the whole model — `sl_atr_mult`,
`trail_start_atr`, `trail_step_atr` — and they are what the optimizer
searches. `Store.opt_params()` filters saved grids down to `OPT_FIELDS`, so a
stale saved blob cannot resurrect a removed axis; if you add an axis, add it
to `OPT_FIELDS` or it will be silently dropped.

Backtest and live must stay identical here: `backtest.simulate`'s bar loop and
`engine._update_stop` are the same rule written twice. Change one, change both,
and cover it in `tests/test_core.py`.

---

## 1. Product in one sentence

Local **MetaTrader 5** multi-symbol autotrader with a **FastAPI + browser terminal**: always watches prices/indicators; places orders only after **Bot Başlat**; tunes each symbol via **walk-forward optimization** over four strategy families; sizes and gates risk with ATR math, daily loss halt, and a live **AI supervisor** that quarantines losers and can trigger re-opt.

---

## 2. Process & entry points

### Runtime process
1. `ensure_dirs()` → load `config/defaults.json`
2. Bind `web_host` / `web_port` (default `127.0.0.1:8900`). If port busy → exit (do not steal).
3. `Store()` (SQLite) → `MT5Client(mt5_terminal_path)` → connect (clock is the machine's own local time, no broker-offset detection)
4. `Engine(store, client)` + `Optimizer(store, client)`; wire `engine.supervisor.optimizer`
5. `create_app(...)` → `engine.start_watch()` (observation loop always on)
6. Optional `autostart_bot` (3s timer) → open browser → `uvicorn.run` until shutdown
7. Shutdown: engine → MT5 → store

### Launchers (root — do not move)
| File | Behavior |
|---|---|
| `start.bat` | Silent background start + open browser + short console then exit |
| `start_silent.vbs` | Prefer `pythonw.exe` / minimized python `run.py` |
| `start_console.bat` | Foreground; closing window kills app |
| `stop.bat` / `restart.bat` | Kill port listener / silent restart |
| `KUR.bat` → `KUR.ps1` | **The** installer, single entry point: Python + venv at `C:\MicoFX-venv` + pip + desktop shortcuts. Idempotent, re-runnable after `git pull`. |
| `run.py` | Real entry |

Env: `MICO_HOST`, `MICO_PORT`, `MICO_OPEN_BROWSER`.

Docs: `README.md` (hub), `docs/KULLANIM.md`, `docs/KURULUM.md`, this file.

### Two modes
- **Watch-only** (`_trading=False`): indicators, UI, sessions, positions visible; **no new orders**.
- **Trading** (`Bot Başlat`): entries + position management. Persist `system.running`.

---

## 3. Package map

```
<ROOT>/
  README.md / MASTER_PROMPT.md
  docs/KULLANIM.md / docs/KURULUM.md
  run.py / backup.py / requirements.txt
  KUR.bat / KUR.ps1                         # the only installer
  start.bat / start_silent.vbs / start_console.bat / stop.bat / restart.bat
  config/defaults.json
  data/micofx.db                            # runtime (gitignored)
  logs/micofx.log                           # gitignored
  tests/
  micofx/
    models.py       SymbolConfig, SystemConfig, OPT_FIELDS, STRATEGIES
    store.py        SQLite settings/symbols/opt_runs
    paths.py        ROOT, DB_PATH, load_defaults
    logbus.py       ring + rotating file
    mt5client.py    locked MT5 bridge
    sessions.py     broker-time windows
    indicators.py   T3, StochRSI, ATR, ADX, SuperTrend, WaveTrend, Aroon, TRIX, helpers
    strategy.py     Params, IndicatorCache, 4 families → Signals
    backtest.py     bar replay + walk_forward
    optimizer.py    background TF×strategy search + apply gates
    risk.py         DailyGuard + lot_for + can_open + edge_scale
    supervisor.py   live health / quarantine / bad hours / reopt
    engine.py       poll loop
    web/app.py      FastAPI
    web/static/app.js, style.css
    web/templates/index.html
```

---

## 4. Persistence

| Item | Path / rule |
|---|---|
| DB | `<ROOT>/data/micofx.db` |
| Log | `<ROOT>/logs/micofx.log` (WARN/ERROR/TRADE/OPT/AI to disk; ring ~1500 in memory) |
| Defaults | `<ROOT>/config/defaults.json` — seed template only |
| Writes | Immediate on every system/symbol/opt/AI/day change — **no separate Save** |

Tables: `settings` (JSON blob by key), `symbols` (JSON + sort position), `opt_runs` (keep last ~40 per symbol).

Settings keys include: `system`, `opt_params`, `supervisor`, `supervisor_state`, `day_key`, `day_start_balance`, `day_halted`, `day_halt_reason`.

`opt_params` = defaults.optimizer merged with stored overrides.

### Backup invariants (`backup.py`)

- `data/micofx.db` is gitignored. The nightly archive is its **only** copy — GitHub holds none of it.
- `EXCLUDE_DIRS` ⊇ `.pytest_tmp` (alongside `.venv`, `__pycache__`, `.pytest_cache`, `.git`). Test debris must never enter an archive.
- The archive has exactly one canonical DB path: `data/micofx.db`, written via sqlite's online-backup API (consistent snapshot, not a raw copy). A second `*micofx.db` entry is a decoy → **warn, do not fail the run**.
- `C:` and `D:` are usually one physical disk. `backup_dir_secondary` must be a different physical drive or a cloud folder, and is a **copy** of the primary zip — never a second build.

---

## 5. Web terminal

Turkish UI. Poll `/api/state` ~3s (faster while opt running; slower if tab hidden).

| Tab | Role |
|---|---|
| Panel | Account, capacity, positions, day PnL, live symbol cards |
| Semboller | Per-symbol params (lots, signals, ATR risk, filters, sessions) |
| Optimizasyon | Grid settings, run/cancel, live results, history, manual apply |
| AI Denetleyici | Per-symbol health, quarantine, risk scale, bad hours, settings |
| Sistem | Bot controls, account limits, MT5 path, panic/close |
| Log | Live filtered log |

Key APIs: `/api/state`, symbols CRUD/bulk/seed/reset, system patch, bot start/stop/panic, day resume, opt params/run/cancel/history/apply, AI settings/review, logs, app shutdown.

No OpenAPI docs UI (`docs_url=None`).

---

## 6. End-to-end data flow

```
MT5 copy_rates_from_pos
  → Bars (DROP forming candle; closed bars only)
  → IndicatorCache (memoized series)
  → strategy.compute(Params) → Signals {buy,sell,...}

  ├─ OPT path
  │    walk_forward(grid) → selection / validation / holdout
  │    → pick best TF×family by validation.score
  │    → gates → Store.update_symbol(OPT_FIELDS + timeframe + strategy + opt_summary)
  │
  └─ LIVE path
       new closed bar (or stale refresh ~45s)
       → session / market / cooldown / DailyGuard / AI gate / spread / ATR floors
       → RiskManager.lot_for (+ edge_scale + AI risk_scale)
       → RiskManager.can_open
       → MT5Client.open_market(hard SL, tp=0 always, magic)
       → manage: ATR trail only (+ session / day-end / daily-loss flatten)
```

### Backtest honesty (must match live intent)
- Signal on **closed** bar → fill at **next bar open** (buy pays spread).
- Full spread + round-turn commission every trade.
- There is no TP level, so the only same-bar contest is stop vs trail; the stop is checked first.
- The trail advances on **bar closes only**, never on intrabar wicks.

### Signal conflicts
Bars where both `buy` and `sell` are True must be **dropped** (neither side). Do not prefer buy. Apply in every strategy family and guard again in backtest/engine/`Signals.last()`.

---

## 7. Strategy families (shared)

`STRATEGIES = ["t3_stoch", "flow_rev", "mtf_pullback", "micro_rev", "burst",
"dual_t3", "st_trend", "t3_flip", "macd_flip", "wavetrend_flip", "stoch_flip",
"parabolic_flip", "trix_flip", "aroon_flip"]` — 14 aile.

> `orb`, `vwap_rev`, `donchian`, `squeeze_brk`, `t3_ribbon` ve `liq_sweep`
> **kaldirildi** (12.08): optimizer'in `strategies` listesi zaten 14'tu, arama
> bunlari hicbir zaman onermiyordu. Asagidaki aile bolumleri **tam liste
> degildir** — kaynak `models.STRATEGIES`, ve
> `test_the_strategy_lists_cannot_drift_apart.py` ikisinin ayrismasini
> engelliyor.

Optimizer does **not** guess which family fits a symbol: it searches **all enabled families × timeframes** and picks by validation score.

### Shared helpers
- Always compute T3 + StochRSI + ATR; ADX if `adx_min`/`adx_max` > 0.
- `_regime`: ADX between min/max when set.
- `_trend_gate`: if `htf_mode=="t3"` and `htf_factor>1`, higher-TF T3 must agree; else allow both sides.
- `Params`: flat dataclass view of SymbolConfig fields + overrides for grid search.

### `t3_stoch`
Long: T3 rising ∧ %K crosses above %D ∧ `K < 50+stoch_band` ∧ `D < stoch_extreme` ∧ regime ∧ HTF long.  
Short: mirror. Optional body-ratio and ATR-percentile filters. Warmup bars suppressed.

### `micro_rev` (M5-native scalp)
Micro mean reversion whose entry threshold is measured in **round-turn cost multiples**,
not ATR: `|close - EMA(mr_fast)| / (bar spread + commission) >= mr_stretch_cost`. Optional
`mr_confirm` requires the bar to already be turning back. This is the one family that asks
"is this displacement worth more than what it costs to harvest", which is the question that
decides an M5 scalp and that every ATR-scaled family is blind to.

### `burst` (M5-native scalp)
Continuation off a single **range-expansion** bar: range above `mean + brst_range_z * sd`
of the trailing `brst_lookback` distribution, closing inside the top/bottom
`brst_close_pct` of its own bar. Anchored to no level at all — unlike `orb` (session) and
`donchian` (N-bar channel) — so it is available at any hour.

### `dual_t3` (minimal core: two T3 lines + ATR, nothing else)
Fast T3 crossing slow T3 **is** the entry — cross up long, cross down short. This family
deliberately computes **no** StochRSI, RSI, ADX, HTF trend, Bollinger/Keltner, order-flow
proxy, body-ratio or ATR-percentile series at all (not "disabled" — never built), and uses
no Fibonacci ratios. Exits are the shared ATR mechanics every other family uses.
The single optional confirmation is **SuperTrend** (`st_period`/`st_mult`, `st_mult=0`
disables): an ATR envelope around `(H+L)/2` whose bands ratchet toward price and whose
direction flips on a close through the active band. It is admitted only because it is
itself pure ATR; the grid may keep it off, and it must earn its place in walk-forward.
Engine-level rails (session, spread, cooldown, DailyGuard, supervisor) still apply — those
are portfolio safety, not signal indicators.

### `cost_rank_max` (shared by the two scalping families)
Adaptive cost-regime gate: the bar's cost-to-range ratio must sit inside the given
percentile of its own trailing distribution. Unlike `max_spread_atr` it is not a fixed
number, so it follows the symbol and the session.

**Cost series contract:** `IndicatorCache(..., cost=...)` carries `bar spread * point +
commission_in_price` — the exact round turn the backtest charges. Callers that cannot
supply it pass `None`, and `micro_rev` then emits **no signals at all** rather than trading
a guessed cost. Both `backtest.walk_forward` and `Engine._refresh_signals` /
`_refresh_secondary` supply it.

### Tillson T3 (indicators)
Source `(H+L+2C)/4`; six cascaded EMAs; volume factor `vf`; classic T3 weighted blend of e3..e6.

### Explicitly removed / do not reintroduce without evidence
- Exit-on-opposite-signal: measured fire rate ~0–1.6%; every exit is the stop (hard or trailed).
- Ai-only `supertrend()` helper is **dead code** — not a product feature.

---

## 8. Walk-forward optimizer (shared core)

File: `optimizer.py` + `backtest.walk_forward`.

### Calendar window
Same lookback for every TF:  
`want = min(max_bars, lookback_days * 86400 / timeframe_seconds(tf))`  
so H1 is not judged on years while M5 is judged on days.

### Segment split (`segments` clamped 4–8; defaults often 5)
Equal bar edges:
- **Selection** = `windows[:-2]` — search params (each segment scored alone).
- **Validation** = `windows[-2]` — rank survivors; pick TF/family.
- **Holdout / test** = `windows[-1]` — untouched; belief number + apply gate.

Require `n >= segments * 150`. Fail soft if bars < ~600 for a sweep.

### Search mechanics
1. Grid → full Cartesian product if small; else deterministic RNG sample (`seed=7`) up to `max_combos`.
2. Per combo: simulate each selection window.
3. Keep if `pooled.trades >= min_trades` and mean segment score > 0.
4. Consistency: `positive = (# segments with net_r > 0) / len(selection)`; reject if `< min_positive_ratio` (default 0.6).
5. Raw: `raw = mean(segment_scores) * positive²`
6. Segment score:

```
if trades <= 0 or net_r <= 0: return min(0, net_r) rounded
score = net_r * min(1, trades/min_trades) * (net_r / (net_r + max_dd_r))
```

7. Plateau blend with grid neighbors (weight `plateau_weight`, default 0.4):  
   if ≥3 neighbors: `(1-w)*own + w*mean_neighbors` else discount `own * (1 - w*0.75)`.
8. Refine: top 12 seeds → ±1 axis neighbors, `refine_rounds` times (default 2).
9. Top ~14 by blended → measure validation → sort by `(validation.score, blended)` → attach holdout → keep top 10.

### Cross TF × strategy pick
Among attempts with `ok` (prefer also `validated`):  
`max(usable, key=lambda a: a["best"]["validation"]["score"])`.

Search scores are **not** comparable across families/TFs; validation is the common yardstick.

### Shared OOS / apply gates
```
MIN_TEST_TRADES = 12
MIN_OOS_PF = 1.10
_slice_ok = net_r > 0 AND trades >= 12 AND profit_factor >= 1.10
validated = _slice_ok(validation) AND _slice_ok(holdout)
```

Auto-apply (`_is_improvement`) requires ALL of:
1. `_slice_ok(validation)` and `_slice_ok(holdout)`
2. `positive_ratio >= 0.6`
3. `holdout.cost_per_trade_r <= MAX_COST_PER_TRADE_R (0.25)`
4. `best.score > 0`

Apply writes only **`OPT_FIELDS`** (+ optional `timeframe`, `strategy`) + `opt_score`, `opt_updated_at`, `opt_summary` (holdout/validation/selection/positive_ratio/params). Never overwrite magic, broker_symbol, sessions, lot_mode, etc. via opt apply unless explicitly designed.

Commission in R: convert `commission_per_lot` via tick_value/tick_size into price units so R is lot-independent.

### Manual apply (UI)
User may force-apply unvalidated candidates after confirm. Still goes through `optimizer.apply`.

---

## 9. Live engine cycle

Daemon poll (~`poll_interval_sec`, default 2s; slower when not trading).

Per cycle:
1. `client.ensure()` MT5
2. Refresh broker overrides from symbols
3. Account + daily rollover (broker server day)
4. Positions; if trading → `manage_positions`
5. DailyGuard check
6. Supervisor review if due
7. Evaluate each symbol on new closed bar → set `state.signal`
8. Priority-sort ready symbols → `_try_entry`

Entry checks (order matters conceptually): ATR present, tick present, spread vs ATR, min ATR/price, AI gate, session/market, cooldown, DailyGuard not halted, optional live cost gate, lot sizing, `can_open`, then market order with magic.

Position management: **ATR trail and nothing else**, plus the calendar/risk flattens (session end, day end, daily-loss limit).

---

## 10. Risk & sizing

### Lot modes
- **fixed**: `fixed_lot * system.lot_multiplier * edge_scale`, clamp broker min/max and `max_lot`, then `normalize_volume` (floor to step).
- **risk**: `risk_money = balance * risk_percent/100 * multiplier`; `lot = risk_money / (sl_distance * money_per_price_unit)`.

If tick value missing in risk mode: fall back to fixed lot **via normalize_volume**.

### Edge scale (`size_by_edge`)
Holdout expectancy vs median of enabled symbols with positive expectancy (≥3 such):  
`clamp[0.6, 2.2](sqrt(mine / median))`.  
Note: at broker min lot, scale often has nowhere to round — Panel shows both Avantaj and Lot.

### DailyGuard
Day key from broker epoch GMT date; start balance persisted. Halt if `pnl_pct <= -daily_loss_pct` or (if set) `>= +daily_profit_pct`. Survives restart. Manual resume API.

### can_open
Same-symbol max positions, no opposite side on same symbol, total positions, free margin after order, projected margin usage %.

### Capacity (Panel)
How many more positions / lots fit under margin and daily loss ceilings.

---

## 11. AI supervisor

Review interval ~120s (configurable). Uses live deal history per magic/symbol.

Typical defaults:
- Quarantine: consecutive losses ≥ 4 **or** PF < 0.80 with ≥8 trades → block `quarantine_hours` (~12)
- Watch: PF < 1.00 → `risk_scale = 0.6`
- Bad hours: hour bucket PF < 0.7 with enough trades and net < 0 → block that hour
- Global DD scale: soft ~1.5% → hard ~3.0% floor ~0.4 on lot scale
- Under DD: may block watch/idle/negative expectancy
- Gate multiplier: `system_risk_scale * verdict.risk_scale`
- Priority for last slots: expected_r, live bonus, state weight
- Auto-reopt on quarantine/decay if `opt_updated_at` older than ~48h and optimizer free

---

## 12. MT5 client contracts

- All MT5 calls under one `RLock` (engine + opt + web share).
- Bars: `copy_rates_from_pos` then **drop last (forming) bar**.
- Symbol resolve: exact → fuzzy; **`broker_symbol` override never falls back** if wrong.
- Magic tags bot positions for manage/close.
- Slippage from system config.

### Path policy differs by variant (§19)
- **FX**: path mandatory; verify attached install matches configured `terminal64.exe` (incl. `origin.txt`); no bare `initialize()`; UI can hot-update path + reconnect. Optimizer must `set_terminal_path` + `set_overrides` + `ensure()` before search or abort with error.
- **Orj**: looser attach (bare initialize + fallbacks historically).
- **Ai**: path preferred + optional autostart/wait for terminal process.

---

## 13. Defaults portfolio (shared starter)

Groups: `forex`, `index`, `commodity`, `crypto`.

Starter symbols (20): EURUSD, GBPUSD, AUDUSD, USDCAD, USDCHF, GER40, FRA40, UK100, NAS100, US30, US500, HK50, HSTECH, JPN225, AUS200, XAUUSD, SpotBrent, NatGas, BTCUSD, ETHUSD — each with unique magic `99000x`.

Group presets set lot floors (FX/commodity/crypto 0.01, index 0.10), sessions, ADX floors, the ATR stop/trail triple, commissions and cooldowns.

Commission is round-turn per lot on a Pepperstone raw/ECN account: **forex 8.0**, index / commodity / crypto **0.0** (spread only).

`crypto` is deliberately its own preset, not forex or commodity: 24/7 session (`00:00-23:59`, trade_days 1-7), M15 base timeframe, a much wider ATR stop, ADX floor 22 and a longer cooldown to survive crypto's volatility.

---

## 14. Important constants (core)

| Name | Value | Role |
|---|---|---|
| OPT_FIELDS | t3/stoch/htf/adx/sl_atr_mult/trail_start/trail_step/trail_mode/body/atr%/orb/vwap/don… | Opt may overwrite only these. `Store.opt_params()` filters saved grids to this set, so a removed axis can never be resurrected by a stale saved blob. |
| MIN_TEST_TRADES | 12 | OOS slice |
| MIN_OOS_PF | 1.10 | OOS slice |
| MAX_COST_PER_TRADE_R | 0.25 | Apply gate |
| STOCH_MID | 50 | Band midpoint |
| EDGE_MIN / EDGE_MAX | 0.6 / 2.2 | Size-by-edge |
| Default port | 8900 | Web |
| Default lookback | 180 days | Opt |
| Default segments | 5 | Opt |
| Default max_combos | 1200 (FX/Orj) / 2000 (Ai) | Opt budget |

---

## 15. Web/UI opt display rules

- Sort live results by best score; failed symbols sink.
- Status pills: uygulandı / doğrulandı / doğrulanmadı.
- Guard against missing `best` object (failed runs).
- Show job.error in status if opt aborted (e.g. MT5 down).

---

## 16. Coding rules for agents in this codebase

1. Prefer surgical edits matching existing style (Turkish log/UI strings, English comments/docstrings mix as in files).
2. Do **not** change score formula, OOS gates, or honesty rules unless user explicitly asks — these define “good opt results”.
3. Do **not** invent new strategy families without walk-forward evidence and grid wiring in defaults + OPT_FIELDS + UI.
4. Preserve signal-on-close / fill-next-open semantics in any backtest change.
5. Preserve RLock MT5 access; never call MetaTrader5 from web handlers without the client wrapper.
6. Persist via Store methods; do not invent parallel config files.
7. When fixing bugs that affect opt scores, prefer correctness (conflict clear, commission, bar drop) over “making scores prettier”.
8. Do not commit/push unless asked.
9. Windows paths; PowerShell; venv under `.venv` if present.

---

## 17. Known correctness invariants (must hold)

1. Buy∧sell same bar → neither trades (strategy + backtest + live). With the
   optional per-symbol ensemble this extends *across* strategies: if the primary
   and secondary signals disagree on the same symbol at the same time, neither
   side trades.
2. Forming candle never enters IndicatorCache for signals.
3. Opt apply never writes non-OPT_FIELDS silently.
4. Validated UI label ⇔ apply gate `_slice_ok` on both OOS slices.
5. Watch mode never opens positions.
6. Wrong `broker_symbol` → symbol unavailable, no fuzzy fallback.
7. Daily halt survives process restart until resume.
8. Opt apply may write `SECONDARY_FIELDS`, but never `ensemble_enabled` —
   storing a second candidate must not start trading it.
9. Scheduled re-optimization uses the identical `_slice_ok` / `_is_improvement`
   apply path as a manual run; it never force-applies.

---

## 18. Typical user workflows

1. Set MT5 `terminal64.exe` path in Sistem → reconnect → AutoTrading ON in MT5.
2. Map broker names if suffixes differ (EURUSD.r etc.).
3. Run Optimizasyon (all or selected) with apply-best optional.
4. Review holdout PF / net R; reject unvalidated.
5. Enable size_by_edge / lot multiplier carefully (min-lot rounding).
6. Bot Başlat; watch AI quarantine and daily halt.
7. Logs: OPT for search, TRADE for fills, AI for supervisor, ERROR for MT5.

---

## 19. Variant matrix (enable only matching tree)

### Shared core (always)
4 strategies, ATR risk/exits (basic trail), sessions, DailyGuard, supervisor quarantine/bad hours/reopt_on_decay, walk-forward opt, web UI, SQLite, group presets, watch vs trade modes.

### Variant `fx` → `D:\MicoFX`
- Dynamic portfolio: add/remove symbols, broker mapping UI, wipe+seed defaults, purge orphan opt_runs.
- Strict MT5 path lock + install verify + hot path update.
- Optimizer preamble: path + overrides + ensure or abort.
- Silent start / console / stop launchers.
- defaults: `max_combos=1200`, ATR-only trail grid, no orb_retest.
- models/supervisor lean (no hour_risk_scales, no trail_mode).

### Variant `orj` → `D:\MicoFX Orj`
- Same models/defaults/supervisor as FX lean core.
- Fixed shipped portfolio mindset (`_drop_retired_symbols` style); no FX portfolio CRUD UX.
- Looser historical MT5 attach.
- optimizer body ≈ Ai file (no FX ensure preamble).
- Use as **reference baseline**, not experimental Ai.

### Variant `ai` → `D:\MicoAi`
Experimental trading richness — **do not copy into FX unless asked**:
- `orb_retest`, `trail_mode` (atr|structure|hybrid) + `trail_lookback`, swing H/L. (`stale_exit_ratio` used to be listed here too; it is removed from FX entirely — see §0 — so do not port it back.)
- Backtest score with trade-R consistency / DD penalties (diverges from FX formula)
- Supervisor `hour_risk_scales`, live PF edge-decay halving risk
- `autostart_mt5` / wait / terminal process helpers / watchdog scripts
- defaults: `max_combos=2000`, wide stop/trail/retest grids
- Fixed portfolio like Orj (no FX CRUD)
- `supertrend` in indicators = unused

### Decision rule
| Working directory | Variant |
|---|---|
| `D:\MicoFX` | `fx` |
| `D:\MicoFX Orj` | `orj` |
| `D:\MicoAi` | `ai` |

If comparing trees: treat Orj as lean reference; Ai as experimental fork; FX as production ops fork on the lean scoring/models.

---

## 20. How to answer / implement against this prompt

When asked to change behavior:
1. State which variant is active.
2. Trace the path: UI → API → Store/Engine/Optimizer → MT5.
3. Preserve §17 invariants.
4. Prefer fixes that restore shared-core honesty over Ai experimental features.
5. After opt-related changes, remind: restart process + re-run optimization; old opt_runs scores may be stale.

When asked “why opt results changed”:
- Diff `backtest.score`, strategy conflict handling, `defaults.json` optimizer grids, `models.OPT_FIELDS`, commission/tick conversion, MT5 symbol resolve / bar window — not portfolio UI cosmetics.

---

## 21. Minimal mental model

```
defaults.json ──seed──► Store(SQLite) ◄──opt apply── Optimizer
                              │                         ▲
                              ▼                         │
                         Engine loop ──bars──► Strategy families
                              │                         │
                              ▼                         ▼
                      Risk + Supervisor            walk_forward
                              │                  (sel/val/holdout)
                              ▼
                         MT5 orders
                              │
                              ▼
                      Web /api/state (UI)
```

You are editing this stack. Stay coherent with the shared core; gate extras by variant; never sacrifice fill honesty or OOS gates for prettier scores.
