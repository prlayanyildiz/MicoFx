# OPTIMIZATIONS.md

Read-only notes. **Not executed by the engine.** Latest:
**04.09 17:38** — Claude 00:18: min-lot R/$ asymmetry **absent on record** (0.982x; R vs $ ~2.3%). BT shakeout **landed** in `backtest.simulate` (calls `shakeout_sl_atr_mult`; stop→sl; empty closes = apply reset). Queue `landed`. **7/25** BTC+NAS open — no PATCH/restart. Axes CLOSED. FROZEN. MICO MOLA yok.
**04.09 17:32** — Claude 23:54 **corrects** 23:26: shakeout is a **protecting guard** (6/6 DD −10..−25R), not a bug — **do not remove**; **MODEL** in `backtest.simulate` (queued). Chase demoted to marker (~0.03R). NAS signal_match protocol ready post-25. **7/25** BTC #324938042 + NAS #325015448 open — no PATCH/restart. Axes CLOSED. FROZEN. MICO MOLA yok.
**04.09 23:20 — EK24-B SHAKEOUT** (Claude): live guard blind to WFO; cost −0.10..−0.12 R/trade; protect measure 23:54 keeps it; **BT model landed 17:38**. **Detay: EK24-B, dosya sonu.**
**04.09 17:22** — Claude 22:56 EK24 ACK + Day25 ref. JPN regime-charged **HYPOTHESIS_REJECTED**: full +0.275 / last12 +0.642 / holdout-seg +0.477 vs clean −0.211 — gap widens; no keep-line rewrite. Open work = kovalama + JPN/NAS only. **7/25** BTC #324938042 mfe 0.80 open — no PATCH/restart. Axes CLOSED. FROZEN. MICO MOLA yok.
**04.09 22:50 — EK24 SIZINTI DEFTERI** (Claude): 6 sizinti sinifi tek tabloda — olculen maliyet + durum + monitor. Kovalama -49.2R (ACIK, gate yasak), yigma -15.2R (COZULDU), trail-kimildamadi -6.8R gerceklesen (TASARIM), engellenen giris (spread %89, ayarlanmis kapi), JPN/NAS artik acik, land-vs-canli gecikme (COZULDU). **Detay: EK24, dosya sonu.**
**04.09 17:17** — Claude 22:44: clean-cell charged match **5/7** (US30/XAU/GER40/SpotBrent in-band); REAL gap **JPN225+NAS100 only**. JPN regime-charged measure queued; SIGNAL_MATCH -> NAS100-primary post-25. **7/25** BTC #324938042 mfe 0.80 open — no PATCH/restart. Axes CLOSED. FROZEN. MICO MOLA yok.
**04.09 17:08** — Claude 22:06: **gate proposal RETRACTED** (AGENTS adverse-fill ban; Claude invoked own 18:45 rule). Causal search NEG (delay/spread/atr_pct none explain chase; median delay=1 bar = normal fill-next-open). CHASE_R_LOG_QUEUE stays measure-only. Helpers already landed_not_armed. **6/25** BTC #324938042 mfe 0.80 + NAS #324995478 mfe 0.04 open — no PATCH/restart. Axes CLOSED. FROZEN. MICO MOLA yok.
**04.09 17:05** — chase_r LOG helpers **landed** (`scripts/chase_r_log.py` + engine TRADE hook + 8 tests). Status `helpers_landed_not_armed` — live after flat restart. **No gate.** **6/25** BTC #324938042 mfe 0.80 + NAS #324995478 mfe 0.04 open — no PATCH/restart. Axes CLOSED. FROZEN. MICO MOLA yok.
**04.09 17:00** — Claude 21:38: **chase/kovalama** = remaining gap mass (clean cell +0.016R; chase-only −49.2R). Sign correction: fill_vs+ = adverse. Queued .bridge/CHASE_R_LOG_QUEUE.json measure-only (no gate; first flat). **6/25** open BTC #324938042 mfe 0.80 + NAS #324995478 mfe 0 — no PATCH/restart. stale_runtime still not armed. FROZEN. MICO MOLA yok.
**04.09 16:56** — Idle pulse: Claude hash unchanged. **6/25** BTC #324938042 still open mfe 0.80 pnl~+2 (no mid-trade PATCH/restart). Queued `.bridge/SIGNAL_MATCH_DEFERRED.json` (post-25 only). stale_runtime still helpers_landed_not_armed. Watches healthy. Soft Claude deferred to flat. FROZEN. MICO MOLA yok.
**04.09 16:53** — Claude 21:04 correction: stacking = **36%** of hist gap (−18.1R); first-pos alone still −32.0R (64% unattributed). Day25 `gap_attribution` line. Signal-match candidate deferred idle-until-25. **6/25** BTC #324938042 mfe 0.80 trail/BE inert. No PATCH/restart. FROZEN. MICO MOLA yok.
**04.09 16:42** — `stale_runtime_watch` **helpers_landed_not_armed**: script+tests+baseline wire+`Engine._stamp_runtime_boot` (disk). Boot stamp needs first flat restart — BTC open, no restart. **6/25** BTC #324938042 mfe 0.80. No PATCH. FROZEN. MICO MOLA yok.
**04.09 16:39** — Claude 20:32: land→canli gecikme acigi; runtime CLEAN. stale_runtime_watch MONITOR_QUEUED (first flat; no mid-BTC restart). Stack teshis kapali. **6/25** BTC #324938042 mfe 0.80 trail/BE inert. Trampoline PID OK. No PATCH. FROZEN. MICO MOLA yok.
**04.09 16:30** — Claude 20:04 stack mechanism: pre-cap same-side yigma (JPN 08-28 8 tickets −4.65R). Answer **(a)** not bypass: `45decd0` 08-28 07:17 landed cap=1; live PID kept stacking until restart. `concurrent_stack_watch` LAND (baseline wired; alarm >1/name). trade_rate_ratio RETRACTED. Last25 autopsy max=1. **6/25** BTC only open. No PATCH. FROZEN. MICO MOLA yok.
**04.09 16:27** — Claude 19:36: system-day **−$36.16** (1W8L; +107.56 = manual NFP); trade_rate hist **2.93x→1.31x** campaign (monitor queued, not gate). **6/25** NAS #324938232 SL −1.00R mfe 0.31 (<<BE; inert correct). Open BTC only. `unfreeze_actions` surfaces day25 checklist. No PATCH. FROZEN. MICO MOLA yok.
**04.09 16:22** — Idle pulse **5/25** open BTC+NAS (mfe 0.43/0.31 <<BE; trail/BE inert). Claude 19:02 hash ACK'd (no soft rewrite — no new close). `load_day25_checklist` → income board + tests; NAS `act_fill` honesty on board. HB fresh. No PATCH/restart. FROZEN. MICO MOLA yok.
**04.09 16:16** — Claude 19:02 trail end-to-end: **mechanism HEALTHY** (TRAIL thresh stop-move 100%; sole current non-move = XAU wick closed-bar). Operator worry ≠ bug. **5/25** JPN225 #324938158 SL −1.00R mfe 0.33 (<<BE; trail inert correct). Day25 checklist `.bridge/UNFREEZE_DAY25_CHECKLIST.json`. No PATCH. FROZEN. MICO MOLA yok.
**04.09 16:10** — Claude 18:34: non-exit challengers **gone** — `reverse_on_signal` RED (−204R NAS); `cooldown_sec` structural no-op (M15/M30 bar-altı). Exit+non-exit axes CLOSED. silence=KEEP → n→25/100. Income/unfreeze geometry copy → **OPTIMUM / AXIS_CLOSED** (not fix-trail). 4/25 open BTC+JPN+NAS. No PATCH. FROZEN. MICO MOLA yok.
**04.09 16:05** — Claude 18:10: NAS KEEP **15-21** (Claude +49R retracted — KEEP list dropped `brst_*`/`pull_*`); trail **OPTIMUM** not trap (joint sl×step 0/12; KEEP start/step/sl). Queues CLOSED. Lift K≥3 (1.437) already ACK'd. 4/25 open BTC+JPN+NAS. No PATCH. FROZEN. MICO MOLA yok.
**04.09 15:48** — Trail follow-up: **trail not broken** — closed-bar + XAU `trail_improves_at_r`~2.57 > BE@1.5. Live #324921646 still open (+~8). Autopsy **#324842945** panel flatten ~+134 @15:31 still **missing** (n=336); no live backfill (EXPERT skipped by reap + restart reconcile). Code in tree (`overlay_stop` +1e-9, `Engine.close_all` autopsy) — tests green — **not live until flat restart**. Baseline **3/25 undercounts** (≥1). Manual EXPERT close autopsy pending restart (future close_all only; historical gap stays). No Claude pulse. FROZEN. MICO MOLA yok.
**04.09 15:45** — Operator "trail calismiyor": **(A)** closed-bar + XAU geometry (2.57R); no SLTP fails. **(B)** BE exact-R float + panel `close_all` autopsy gap fixed (tests). XAU #324842945 panel flatten ~+134; autopsy pending. 3/25. No apply/restart. MICO MOLA yok.
**04.09 15:16** — Operator give-back: XAU #324813882 MFE **+1.18R** → SL **−0.98R** (gb 1.82; after_1h +1.9R). Cause: trail_step 2.5 vs sl 0.7 needs **~2.57R** before trail beats SL; BE@1.5 unmet. Window scan tighter steps **KEEP** (holdout collapses). Queue measure-only; no apply. 2/25 open XAU+GER. MICO MOLA yok.
**04.09 14:00** — Window scan now records HOLD_ONLY: **GER40 trail_step 2.2→2.8** holdout +6.9R but slice fails robust → review queue, no apply. Still 1 APPLY (NAS body neighbor-blocked). 2/25. MICO MOLA yok.
**04.09 13:52** — Expanded window scan (+trail_step/adx/atr_pct): still **1 APPLY**=NAS body (neighbor-BLOCKED). trail_step 0 APPLY. Frontload: XAU pull/atr_pct, GER40 atr_pct, NAS adx. 2/25 flat. MICO MOLA yok.
**04.09 13:38** — NAS100 min_body 0.2→0.3: window_reconcile APPLY but **body_exec neighbor BLOCKED** (gap 15.73>15). KEEP. 2/25 flat FROZEN. MICO MOLA yok.
**04.09 13:36** — **2/25** (XAU closed). Book window scan: only APPLY = NAS100 min_body **0.2→0.3** (+6.9R holdout / +38R slice). Queued. XAU KEEP 0.3. Baseline chunked reload sleep. MICO MOLA yok.
**04.09 13:30** — NAS fill: `arm_session_day` clears alerted once/day at 15–17 heighten (one alert/session). Soft-reload baseline. 1/25 FROZEN. MICO MOLA yok.
**04.09 13:25** — `window_reconcile.py`: APPLY only if holdout AND 6-slice agree; XAU 0.1→`KEEP_CONFLICT_frontload` codified+tested. Prevents slice-sum-only false upgrades. 1/25 FROZEN. MICO MOLA yok.
**04.09 13:23** — XAU min_body **RESOLVED KEEP 0.3**: all6-slice +50R was first-half history; holdout last-20% and last equal-slice both prefer 0.3. body_exec path correct. No apply. 1/25 FROZEN. MICO MOLA yok.
**04.09 13:20** — XAU min_body **CONFLICT**: 6-slice wants 0.1 (+50R robust OK) but charged_holdout wants KEEP 0.3 (0.1 −9R). `propose_body_upgrade`=null. Auto-apply REVOKED. Ask Claude which window wins. 1/25 FROZEN. MICO MOLA yok.
**04.09 13:18** — Unfreeze action board: income surfaces queues; `unfreeze_actions.py` plan (execute blocked while FROZEN). Auto-on-unfreeze: XAU body 0.1. NAS KEEP / WFO wire manual. 1/25. MICO MOLA yok.
**04.09 13:15** — XAU min_body dry-run: live 0.3 → **0.1** +50.3R 5/6, upgrade_robust OK (Claude OOS claim confirmed on slices). `BODY_CANDIDATES` +=0.1 (was missing). Queue apply after unfreeze. NAS KEEP 15-21. 1/25 FROZEN. MICO MOLA yok.
**04.09 13:12** — NAS100 session dry-run (burst/M30): live 15-21 **+136.6R 6/6** beats 14-22 (+106R 4/6) and 01-23 (+154R 4/6 fails robust). Claude +49R 14-22 **not reproduced** on current config → KEEP 15-21. 1/25 FROZEN. MICO MOLA yok.
**04.09 13:10** — Claude 17:44: official premature **lift = K>=3 window** (after_1h_bars>=3 both sides) hist **1.437**. lift_nonsl_raw + lift_vs_all diagnostic. 1.33 retracted (self-contaminated). GER40 trim Claude-verified. 1/25 FROZEN. MICO MOLA yok.
**04.09 13:08** — GER40 trim VERIFIED: audit 5/6 valid=6 sumR=+158.1 (was valid=4 edge / fake 6/6). Book all OK no RED. WFO apply-gate helpers landed (`wfo_apply_gate.py`) NOT wired (FROZEN). 1/25. MICO MOLA yok.
**04.09 13:05** — GER40 holdout dirty-head TRIM applied (file-only): cut~2020-07-21 idx 20886, 90000→69114, `.npz.bak`. Script `ger40_snapshot_trim.py`. Measurement honesty; no live config. 1/25 FROZEN. MICO MOLA yok.
**04.09 17:10 — EK23 KONSOLIDE** (Claude): gunun 4 kalici metodoloji dersi —
D1 6-dilim yeterli degil (anchored WF sart), D2 motor tek aile secer (birlesik
olcum ulasilamaz sayi), D3 snapshot sessizce kirli olabilir (GER40 %23),
D4 kapi metrikleri guc analizinden gecmeli (give_back VE premature_sl gecemedi).
Ayakta kalan 2 aday + reddedilen 8. **Detay: EK23, dosya sonu.**
**04.09 12:54** — Claude 17:06: premature_sl reframed (safety@25 / evidence@100 + lift). Per-symbol floor off until 100. 1/25 FROZEN.
**04.09 12:38** — Claude 16:38: quality gate book-OK; GER40 valid=4 edge → recapture MEDIUM. Audit shows wins6+wins12. 1/25 FROZEN.
**04.09 12:35** — Claude 16:14: book data-quality audit 6/7 clean; GER40 only (+157.6R 5/6 confirmed). No outlier-return in our gate. 1/25 FROZEN.
**04.09 12:35** — Claude 15:48: SpotBrent KEEP (delete wins nothing). No config change. 1/25 FROZEN.
**04.09 12:32** — Claude 15:24: GER40 dirty spread head; slice data-quality gate LAND (wins/valid). NAS session one-shot + GER40 recapture queued. 1/25 FROZEN.
**04.09 12:16** — Claude 14:52: session sticky reset after family/TF flip (sticky=False). NAS live 15-21 keep. 1/25 FROZEN.
**04.09 12:12** — Claude 14:34: broker hours verified. SEARCH +=01:00-23:59; 14-22 already present. JPN sessions cleaned 01-23:59 (use_sessions=False). NAS live 15-21 keep. 1/25 FROZEN.
**04.09 12:08** — Claude 14:18: sweep standalone 4/4 loses vs incumbent; ensemble HAYIR (slot/capital). strategies stay 3; fade code dormant OK. 1/25 FROZEN.
**04.09 12:05** — Claude 13:52: sweep_fade+SpotBrent t3+GER40 atr_pct GERI (anchored WFO). Only XAU min_body grid stays (already searchable). JPN silence → 24h tradable mask. WFO apply-gate queued. 1/25 FROZEN.
**04.09 12:00** — Claude 13:16: range_fade retract; sweep_fade code+grid; pull_depth grid fix; mtf body/t3 searchable. NOT live. 1/25 FROZEN.
**04.09 11:50** — `range_fade` family #4 code+grid (Claude 12:38 US30 +208R measured). NOT live, NOT in default opt strategies. Full-book silence ~1/mo. give_back monitor/by_exit. 1/25 FROZEN. MICO MOLA yok.
**04.09 11:13** — Silence p50 270min + window 15h (Claude 11:12). htf=0=gate OFF keep. 1/25 BTC +17.53. FROZEN. MICO MOLA yok.
**04.09 11:09** — FIRST close 1/25 (BTC trail +17.53). Book flat. Heartbeat-stale wake. FROZEN. MICO MOLA yok.
Prior **04.09 10:57** — Operator FRA40/UK100 ask: SIMDI HAYIR (Claude+Cursor). Queued post-25/unfreeze bake-off. MICO MOLA yok.
Prior **04.09 10:55** — Unfreeze fill_focus actionable_signals (seans_disi not fake 0% fill).
Prior **04.09 10:52** — Baseline WMI-detached + first_close via baseline. Exec FROZEN. 0/25. MICO MOLA yok.
Prior **04.09 10:42** — NAS100 fill watch (15-17h heighten) + actionable_signals (ignore seans_disi/piyasa_kapali for poor-fill). FILL_FOCUS += NAS100. Tests 4/4. Exec FROZEN. 0/25. MICO MOLA yok.
Prior **04.09 10:30** — Unfreeze-prep board (premature/fill/gate6/baseline) -> UNFREEZE_PREP.json.
GATE_EVIDENCE 15m throttle. C3 payda live. Exec FROZEN. 0/25. MICO MOLA yok.
Prior **04.09 09:35** — EU silence@90 = gercek-quiet/rangebound (Claude+Cursor). Not data-gap.
entry_blocks GER40/US30=0 (raw channel_break silent). Config FROZEN. 0/25. MICO MOLA yok.
Prior **04.09 09:15** — Silence watch = session-open *delta* (not 7d rolling). first_close_poll
runs full EU window (no 60-tick blind exit). Exec FROZEN. 0/25. MICO MOLA yok.

Prior **04.09 08:55** — Panel Tum-zaman entry_blocks table + income-loop silence/GER40/cum. MICO MOLA yok.
Prior **04.09 08:49** â€” entry_blocks_cumulative live (roll/reset immune; API cumulative). Reattach restart. MICO MOLA yok.

Prior **04.09 08:40** â€” EU silence watch (GER40+US30, 90min/0 sig) + panel-down wake.
Post-EU seed_rows, first-close, GER40 fill heighten. Exec FROZEN. 0/25.
MICO MOLA yok.

Prior **04.09 08:25** â€” XAU EU lift verified (sl 0.7). Post-EU false-wake fixed via
`arm(seed_rows=â€¦)` (clock-skew). First-close one-shot + GER40 EU fill-watch
(alongside US30 min_sig=4). Exec FROZEN. baseline 0/25. MICO MOLA yok.

Prior **04.09 07:50** â€” Operator all-hours ask: charged **âˆ’95R** vs live sessions
(NAS/US30/Brent). Keep clocks. No apply. MICO MOLA yok.

Prior **04.09 07:25** â€” US30 session-open heighten (h=8â€“11: min_sig 4, 60s poll).
Claude 07:35 OK. Bridge daemon 5m keepalive. Next: hâ‰¥8 XAU lift. MICO MOLA yok.

Prior **04.09 07:15** â€” Bridge daemon was dead since 01:41; restarted. Schtask
`MicoFX-BridgeDaemon` now every **5m** keepalive (mutex). BaselineWatch 10m.
MICO MOLA yok.

Prior **04.09 07:10** â€” XAU session-cut proposal **retracted**: charged all-hours
+250.7R best vs day windows â‰ª. Live night bleed = regime; keep temp-disableâ†’EU
loop, not permanent session cut. Regression:
`tests/test_xau_charged_all_hours_session.py`. MICO MOLA yok.

Prior **04.09 07:00** â€” EU-open brief fired (h=7). Post-EU 3h watch armed on lift.
Forever book monitor + 10m schtask keepalive. Auto-A ARM+FORCE veto.
Next: hâ‰¥8 XAU auto re-enable. Exec FROZEN. MICO MOLA yok.

Prior **04.09 06:42** â€” BaselineWatch schtask every 10m keepalive (mutex). auto-A
needs ARM+FORCE (Claude 06:35 veto). MICO MOLA yok.

Prior **04.09 06:35** â€” Claude: keep `AUTO_NIGHT_BLEED_A` **UNARMED**. night_bleed =
alertâ†’reviewâ†’manual disable only (same risk class as unfrozen exec auto).
Detector thresholds stay. MICO MOLA yok.

Prior **04.09 06:27** â€” `night_bleed_guard` (24h dominant bleed, report-only).
Auto-A gated by `.bridge/AUTO_NIGHT_BLEED_A` (Claude OK pending). Wired into
baseline watcher. Exec FROZEN. MICO MOLA yok.

Prior **04.09 06:13** â€” False "XAU EU re-enable" bridge notes were test-mock pollution
(live `FOR_CLAUDE` write). Seal: `xau_temp_reenable` POST+GET verify; tests
redirect INBOX/WAKE. Watcher poll 60s while flag up; durable
`scripts/start_baseline_watch.ps1` + schtask. Exec FROZEN. MICO MOLA yok.

Prior **04.09 06:02** â€” Operator "kasa eriyo": night bleed â‰ˆ XAU 7/24. **A applied**:
XAUUSD `enabled=false`, sl 0.7 untouched. Flag
`.bridge/XAU_TEMP_DISABLE_UNTIL_EU`; auto re-enable broker hâ‰¥8
(`scripts/xau_temp_reenable.py`). Exec still FROZEN. MICO MOLA yok.

Prior **04.09 05:55** â€” TEMIZ WAIT / baseline-accumulate. Durable
`scripts/baseline_accumulate_watch.py` (15m) + US30 fill watch; wake only on
25/25 or poor US30 fill. Freeze stack regression:
`tests/test_exec_pipeline_freeze_stack.py`. Operator morning brief in bridge.
MICO MOLA yok.

Prior **04.09 05:47** â€” `_recalibrate_spread_cap` honors FREEZE at source (AP/HTTP/TF/opt
callers). Restart#3 bound. Baseline 0/25 kept. MICO MOLA yok.

Prior **04.09 05:43** â€” AP `_apply_spread` also honors exec FREEZE (was still calling
`_recalibrate_spread_cap` on evidence targets). Mid-trade restart#2 bound it;
baseline 0/25 kept. Trust-mode no longer band-calibrates. MICO MOLA yok.

Prior **04.09 05:22** â€” Mid-trade re-adopt restart (Claude 05:20). Fix stack live.
XAUUSD `sl_atr_mult` **0.7** + re-enabled (waiver). AP on. Exec **FROZEN**.
`.bridge/POST_RESTART_BASELINE.json` autopsy=333 target=25; streak/exp wakes
suppressed until then; one-shot wake when ready. Income-loop freeze seals:
`apply_spread_calibration` + `spread_exec` + trust-mode no longer
band-calibrates every flat symbol (NAS 0.05â†’0.06 path). Book 6-slice OK
(XAU +471 5/6). BTC #324468226 trail/BE ~+5R still open. MICO MOLA yok.

Prior **04.09 04:50** â€” Claude explicit OK: XAUUSD `sl_atr_mult` **0.5â†’0.7**.
`upgrade_robust` OK (+471 vs +400 Î£R); premature 11; last-seg âˆ’12R waived on
force widen only. Live PID still refused until restart; armed
`.bridge/XAU_SL_07_PENDING` â†’ lands after freeze-bind restart. Exec pipeline
stays **FROZEN** book-wide. MICO MOLA yok.

Prior **04.09 04:00** â€” SpotBrent msa 0.08â†’**0.05** revert (1/6 +16 vs 3/6 +50;
last-seg +81 illusion). Calibrate + `spread_exec` + HTTP opt/apply msa widens
gated by `upgrade_robust` / `refuse_msa_widen`. `book_robust_audit` in income
loop. Exec still **FROZEN**; AP off until restart+resume flag.
`upgrade_robust`: full +5R, wins non-regress, backload â‰¤15pp, â‰¥4/6, min-slice
non-worse. Reverts: NAS 15-21, GER tstep 2.2, XAU tstep 2.5. Live
`autopilot_enabled=false` until restart; `.bridge/AUTOPILOT_RESUME_AFTER_RESTART`
re-enables AP once new PID honors freeze (tune still frozen).
MICO MOLA yok.









Prior **03.09 23:xx** â€” weak-symbol + 3 bleed. EK22.
Prior **03.09 11:20** â€” per-symbol WFO round closed (monitoring). Live book:
NAS/XAU mtf, JPN burst/M30, US30 channel re-stamp hold +43, GER/BTC
incumbent max (no-candidate), SpotBrent **disabled FINAL**. Concurrent
**10%**, daily_loss **3%**, channel trail grid DB through **2.8**.
Holdout sum on stamped configs ~**+698R** / 6. HEAD `9c70438` (US30
session defaults). Watch: NAS/XAU mtf live, C1/T1 first fill.
Prior **03.09 10:03** â€” `MICOFX.bat`; income-loop launchers deleted.
Prior **03.09 09:52 EK21+** â€” F4 closed; JPN 01â€“15.
Prior **27.08 22:36** operator income-max. Shakeout floor stays; do not
teach search it. Public WFO/TP/pyramid does not change the exit model.

---

## 03.09 00:50 â€” MASTER AKSIYON LÄ°STESÄ° (EK1-EK18 konsolide, Ã¶ncelik sÄ±rasÄ±)

Bu oturumun tÃ¼m bulgularÄ±. Detay: aÅŸaÄŸÄ±daki EK bloklar. Uygulama = Cursor (kod+commit) +
operatÃ¶r (red). Claude = Ã¶lÃ§Ã¼m/doÄŸrulama (yapÄ±ldÄ±).

### P0 â€” GÃœVENLÄ°K (canlÄ± $ risk, hemen)
- [ ] **C1-shakeout** `engine.py:2651` (+2638): `sl_size` â†’ `sl_dist`. 3stop/10 sonrasÄ±
      %4 risk. 1 satÄ±r. (EK14, 3Ã— doÄŸrulandÄ±)
- [ ] **T1-minlot** `risk.py:556-558`: broker min-lot > 2% cap iken 3Ã—cap'e yukarÄ±
      sized. Clamp-up dalÄ±nÄ± sil (iÅŸlem atla) veya 1.5Ã—'e indir + testi gÃ¼ncelle. (EK15)
- [ ] **C3** `pnl_pct` payda = `start_balance + max(0,cash_flow)` VEYA UTC-rollover bekle
      â€” `daily_loss_pct>0` YAPILMADAN Ã–NCE. (EK12-C3; UTC-gece geÃ§ti mi kontrol et)
- [ ] **operatÃ¶r red:** `daily_loss_pct` %3-4? `max_concurrent_risk_pct` 50â†’~15?

### P1 â€” EXIT GÃœVENLÄ°ÄžÄ° (EK14 HIGH)
- [ ] H2 `engine.py:3299,3349`: stale-clock'ta flatten Ã¶lÃ¼ â†’ `broker_now()` fallback.
- [ ] H1 `engine.py:2754`: fill-verify mid-stop kaybÄ± â†’ send'de persist+`_mark_bar_filled`.
- [ ] H3 `close_all` â†’ tracked close (autopsy/sample).

### P2 â€” KOD SAÄžLIK (EK15 â€” aÄŸaÃ§ kendi pytest+ruff kapÄ±sÄ±nÄ± geÃ§miyor: 4 fail/3 ruff)
- [ ] `app.js:930` ichimoku label sil (2 test) + `test_indicator_edge_inputs.py:124` boundâ†’21.
- [ ] ruff: `scripts/apply_trail_step_queue.py:9` unused sys + 2 test import-sort.
- [ ] Ã¶lÃ¼ fn sil: `indicators.py` parabolic_sar/stochastic_slow/supertrend (~114 sat).
- [ ] `stoch_extreme` C4 kalÄ±ntÄ±sÄ± (SymbolConfig+Params+key()+defaults.json 5 blok).
- [ ] bayat DB: `settings.opt` orphan key sil; `supervisor_state` PLTR-24 verdict sil.

### P3 â€” CONFIG (robust-doÄŸrulanmÄ±ÅŸ, EK17/EK18 â€” EK16 curve-fit'ti)
- [ ] **NAS100**: `cost_rank_max` 0.7â†’0, `adx_min` 0â†’15 (burst/M30). 5/6 robust +168R.
      WFO teyit sonra apply. **TEK net config deÄŸiÅŸikliÄŸi.**
- [ ] **NAS pending `trail_step=1.6` Ä°PTAL** (burst'e âˆ’24R).
- [ ] GER40: burst mi channel_break mi â†’ WFO regime-gate (3/6 mixed).
- [ ] US30 / XAUUSD / JPN225 / BTCUSD: **DOKUNMA** (robust 5-6/6).
- [ ] SpotBrent: burst FRAGILE (2/6) â†’ roc_pace ADAYI veya disabled.
- [ ] GOLD-PERP add: **mtf_pullback** (5/6 +255R; burst/channel_break < bu). mtf_pullback
      aramadan DÃœÅžÃœRÃœLMESÄ°N.

### P4 â€” YAPISAL (EK12/EK13, operatÃ¶r +2 aile onaylÄ±)
- [ ] `band_fade` (mean-reversion) â€” 4 indeks, Ã–NCE. Kod: Params+OPT_FIELDS+key()+
      _FAMILIES+STRATEGIES+grid+test. WFO gate + kill-criteria.
- [ ] `roc_pace` (TSMOM) â€” SpotBrent + BTC/XAU, #2.
- [ ] **48s churn brake â†’ compound gate** (margin+sample+plato+regime-spreadâ‰¥60-70%+dwell)
      + kill-switch (canlÄ± exp<âˆ’0.30R/40tr â†’ sideline). = P1'in asÄ±l parÃ§asÄ±, WFO'nun
      overfit seÃ§mesini durduran ÅŸey.
- [ ] Evrensel pooled param yÃ¶nÃ¼ (sembol-baÅŸÄ±na tuning deÄŸil) â€” research #2, bÃ¼yÃ¼k karar.
- [ ] burst 5 kural: kasÄ±lma Ã¶n-koÅŸulu (NR7/BB-squeeze) + eÄŸim gate + tetik-bar sertleÅŸtir
      + seans + cost-edge. Yeni OPT eksenleri.

### DURUM (03.09 00:50)
Kitap FLAT, opt idle. Cursor ~1s sessiz (commit 73591b3, board 22:58). CanlÄ± config'ler
Ã§oÄŸunlukla robust (Cursor'un apply'larÄ± oturdu). Beklenen aylÄ±k panel +%98 = fantezi;
gerÃ§ekÃ§i hedef P0-P3 sonrasÄ± +$150-250/ay (EK7). AsÄ±l kalan alpha config tuning'de deÄŸil,
P0 bug fix'lerinde.

---

## 02.09 20:20 â€” RE FÄ°LOSU KONSOLÄ°DE (6 paralel salt-okur agent + DB doÄŸrulama)

OperatÃ¶r "tam yetki, kod kod, acÄ±madan" mandate'i. 6 agent: engine+execution,
optimizer+backtest+holdout, risk+supervisor, strategy+indicators, mt5client+web+store,
web/GitHub/X araÅŸtÄ±rma (TR+EN). HiÃ§bir ÅŸey PATCH edilmedi. Anahtar iddialar canlÄ± DB ile
doÄŸrulandÄ± (aÅŸaÄŸÄ±da "âœ“DB").

### Nedensel zincir (Ã¶zet)

Sistemin **Ã¶lÃ§Ã¼len edge'i NEGATÄ°F (avgR âˆ’0.13R)** â†’ Kelly = 0 â†’ risk-optimal stake sÄ±fÄ±r.
Sebep: optimizer kÄ±rÄ±lgan config seÃ§iyor (churn + degradasyon terimi yok + ÅŸanslÄ±-dilim),
bunlar iyimser bir backtest'te (trail ÅŸiÅŸmesi + fill-sÄ±rasÄ± + spread asimetrisi) iyi
gÃ¶rÃ¼nÃ¼p canlÄ±da tutmuyor; Ã¼stÃ¼ne GER40/M5 burst tÃ¼m tasarÄ±m gate'leri kapalÄ± Ã§alÄ±ÅŸÄ±yor,
trail hiÃ§ devreye girmiyor, ve slippage telemetrisi Ã¶lÃ¼ olduÄŸu iÃ§in fark Ã¶lÃ§Ã¼lemiyor.
Riskin bÃ¼yÃ¼klÃ¼ÄŸÃ¼: sizing bug'Ä± iÅŸlem baÅŸÄ±na ~%2 yerine ~%10 risk aldÄ±rÄ±yor, gÃ¼nlÃ¼k
zarar freni yok, olan fren de bozuk, supervisor reaktif katmanÄ± bu frekansta atÄ±l.

---

### A â€” OPTIMIZER: CHURN + KIRILGAN SEÃ‡Ä°M  (agent 2)

* **A1 [CRITICAL]** `_beats_incumbent` (`optimizer.py:1754-1885`): rakip skoru cost-free
  (`walk_forward` `charge_costs=False`), mevcut config skoru `_holdout_costed` â†’
  `charged_holdout` ile HEP maliyetli (`holdout_cost.py:34-51`, charge_costs dalÄ± yok).
  Test `new_score >= old_score` â†’ rakip yapÄ±sal avantajlÄ± â†’ **sÃ¼rekli config deÄŸiÅŸimi.**
  `reject_reason` yorumu (`optimizer.py:1621-1633`) canlÄ± kaybedenleri churn'e baÄŸlÄ±yor.
  **âˆ’41R/+90R'nin en olasÄ± mekanik sebebi.**
* **A2 [CRITICAL]** costed-negatif apply reddi `if ... and charging:` arkasÄ±nda
  (`optimizer.py:2093-2105`); `charge_costs=False` â†’ blok atlanÄ±yor, `costed_negative`/
  `holdout_costed` damgalanmÄ±yor, "maliyetli holdout negatif" reddi hiÃ§ tetiklenmiyor.
  Yorum: "UK100/SpotBrent/JPN225 faturaydÄ±". (= F-D1) `reject_reason` maliyet gate'leri
  + `walk_forward` `rejected_costly` de cost-free'de Ã¶lÃ¼.
* **A3 [MED-HIGH]** Objektif = ham `score` = `net_r Ã— sample_disc Ã— dd_disc`
  (`backtest.py:100-112`). Sortino/degradasyon YOK. `score_consistency` hesaplanÄ±p
  **kasÄ±tlÄ± dÄ±ÅŸlanÄ±yor** (`backtest.py:117-119`). `holdout_retention` 0.25'te pass/fail
  veto, gradyan deÄŸil â€” retention 0.30 olan, 0.95 olanÄ± yener validation bir tÄ±k yÃ¼ksekse.
* **A4 [MED]** holdout 8-yollu seÃ§im vetosu (4 aile Ã— 2 TF/sembol), `as_dict(MIN_TEST_ (arsiv)
  TRADES=12)` ile tam aÄŸÄ±rlÄ±kta puanlanÄ±yor (`backtest.py:1518`) â†’ 12-iÅŸlemlik ÅŸanslÄ±
  dilim `_beats_incumbent`'Ä± tam gÃ¼venle sÃ¼rÃ¼yor.
* **A5 [MED]** apply gate'leri gevÅŸek: `MIN_TEST_TRADES=12`, `MIN_OOS_PF=1.10`,
  `min_positive_ratio` UI'dan 0.3'e inebilir. `_generalises` retention â‰¤ 0 â†’ "Ã¶lÃ§Ã¼lemez"
  â†’ retention kontrolÃ¼ **atlanÄ±yor** (`optimizer.py:1583`).
* **A6 [HIGH]** GER40 canlÄ± TF (M5) otonom re-opt yolunda HÄ°Ã‡ aranmÄ±yor â€” quarantine
  re-opt `SEARCH_TIMEFRAMES` M15/M30'a sabitli (`supervisor.py:1052`, `optimizer.py:631`).
  AranÄ±nca incumbent replay M5 bar'Ä± bulamÄ±yor (`allow_fetch=False`) â†’ bayat apply
  stamp'ine dÃ¼ÅŸÃ¼yor (kod: "+224.2R loglanmÄ±ÅŸ, aynÄ± setup bu geceki pinlerde âˆ’89.1R").
* **A7 [HIGH]** Grid kapsamÄ±: burst ~8.1M grid @ %0.025, mtf_pullback ~1.5M @ %0.13,
  channel_break ~%1, ichimoku ~%15. `coverage_budget` yeniden-daÄŸÄ±tÄ±mÄ± Ã¶lÃ¼ (3/4 grid
  cap'i aÅŸÄ±nca surplus=0). SeÃ§im kÃ¼Ã§Ã¼k-grid'li aileye (ichimoku) yanlÄ±.
* **A8 [HIGH]** burst (scalp) yalnÄ±z swing-geniÅŸliÄŸi stop'la aranabiliyor:
  `uses_swing_exits` M15/M30'da hep true â†’ `SWING_GRID_OVERLAY` `sl_atr_mult` floor 1.0;
  shipped `grid.sl_atr_mult [0.5,0.7,0.9]` default aramada Ã¶lÃ¼. burst/M5 tight-stop
  yapÄ±sal olarak ulaÅŸÄ±lamaz.
* **A9 [MED]** decaying-ama-quarantine-deÄŸil config hiÃ§ yeniden aranmÄ±yor; `combo_seed=7`
  sabit â†’ retry aynÄ± 2000 combo'yu Ã§ekiyor; `reopt_retry_cooldown_hours=1` â†’ aynÄ± Ã§ekim.

### B â€” BACKTEST Ä°YÄ°MSERLÄ°ÄžÄ°  (agent 2 + araÅŸtÄ±rma)

* **B1 [MED]** `min_stop_series` Ã¶lÃ§eksiz bar-spread kullanÄ±yor (`backtest.py:388`);
  canlÄ± `min_stop_distance` tick-spread â†’ `spread_scale Ã—` (CHFJPY'de 3.35'e kadar)
  daha geniÅŸ. Backtest trail'i canlÄ±nÄ±n izin verdiÄŸinden ~scaleÃ— daha sÄ±kÄ± hug ediyor â€”
  tek yÃ¶nlÃ¼, tam da reward-ratio'nun dayandÄ±ÄŸÄ± trailed-winner'larÄ± ÅŸiÅŸiriyor.
* **B2 [araÅŸtÄ±rma #3]** intrabar fill-sÄ±rasÄ±: aynÄ± bar'da hard stop + trail-update
  olunca backtest lehte sÄ±rayÄ± varsayÄ±yor. Stop-first (kÃ¶tÃ¼ durum) varsayÄ±lmalÄ±.
* **B3 [MED]** long/short spread asimetrisi: short non-stop Ã§Ä±kÄ±ÅŸlarda spread'i iki
  uÃ§tan Ã¶dÃ¼yor, eÅŸdeÄŸer long bir kez (`backtest.py:809-811,866-868`). Cost-free'de
  latent ama repo tarihindeki her costed Ã¶lÃ§Ã¼m + her `_beats_incumbent` replay yanlÄ±.
* **B4 [LOW-MED]** `lookback_days=0` â†’ her TF farklÄ± miktar geÃ§miÅŸ (90k M30 â‰ˆ 5.1yÄ±l,
  M15 â‰ˆ 2.6yÄ±l, M5 â‰ˆ 10ay). Kod yorumunun uyardÄ±ÄŸÄ± cross-TF haksÄ±zlÄ±k geri gelmiÅŸ â€”
  M30'a sistematik seÃ§im avantajÄ±.

### C â€” SIZING: HESAP-KATÄ°LÄ°  (agent 3) â€” âœ“DB

* **C1 [CRITICAL]** `lot_for` (`risk.py:459-565`, Ã¶zellikle 542-554): `raw` (risk% tabanlÄ±
  lot) hesaplanÄ±p **atÄ±lÄ±yor**. `r_cap` (gerÃ§ek %2 tavan) broker min-lot'un altÄ±na
  dÃ¼ÅŸÃ¼nce â€” ~$225 hesapta NORMAL durum â€” 543-551 `lot = min(auto, ceiling)` yapÄ±yor;
  `auto` = marj payÄ±. 1:500 kaldÄ±raÃ§ `lev>=100` dalÄ±nÄ± garantiliyor. SonuÃ§: her endeks
  giriÅŸi marj payÄ±na (~5â€“30Ã— hedeflenen risk) sizing yapÄ±yor. KanÄ±t: R baÅŸÄ±na ~$20 /
  ~$225 bakiye â‰ˆ %10/iÅŸlem, %2 deÄŸil. âˆ’$827 kÃ¼mÃ¼latif yalnÄ±z $300+ depozitle ayakta.
* **C2 [CRITICAL]** KÃ¼mÃ¼latif gÃ¼nlÃ¼k zararÄ± hiÃ§bir ÅŸey kapamÄ±yor. âœ“DB `daily_loss_pct=0`.
  `DailyGuard.check` hep `Verdict(True)` dÃ¶nÃ¼yor; `_halt(loss)`/`loss_halted`/
  `daily_loss_flatten` tÃ¼mÃ¼ `daily_loss_pct>0` dalÄ±nÄ±n altÄ±nda â†’ ulaÅŸÄ±lamaz. Tek savunma:
  supervisor `_drawdown_scale` (en kÃ¶tÃ¼ 0.6Ã— kÄ±sma, DUR yok) + `max_concurrent_risk_pct=46`
  (4 korelasyonlu endeks long).
* **C3 [HIGH]** âœ“DB `day_start_balance=100.51`, `day_cash_flow=300.0`, equity ~225 â†’
  `pnl_pct = (225âˆ’300âˆ’100.51)/100.51 â‰ˆ âˆ’%174.7`. `rollover` bugÃ¼n yeniden Ã§Ä±palamÄ±yor.
  SonuÃ§: `_drawdown_scale(âˆ’174%)` â†’ `risk_scale_floor=0.6`; âœ“DB `supervisor_state.
  risk_scale = 0.6` â€” kitap **kazara** 0.6Ã— damperde. VE: operatÃ¶r `daily_loss_pct>0`
  yaparsa `check()` sahte âˆ’%174'te **anÄ±nda + kalÄ±cÄ±** halt + `daily_loss_flatten`
  hepsini kapatÄ±r. **C2'nin Ã§Ã¶zÃ¼mÃ¼ C3 tarafÄ±ndan tuzaklanmÄ±ÅŸ.** DÃ¼zeltme: `pnl_pct`
  paydasÄ± `start_balance + max(0, cash_flow)`.
* **C4 [HIGH]** PF quarantine breaker atÄ±l: `judged_n` yalnÄ±z `opt_updated_at` sonrasÄ±
  iÅŸlemleri sayÄ±yor; configler 4.5s Ã¶nce reopt â†’ `judged_trades` 0-2 â†’ PF arm ateÅŸlenemez;
  quarantine auto-reopt (`quarantine_hours=1`) counter'Ä± sÄ±fÄ±r tutuyor. Streak arm
  `quarantine_losses=11` â†’ 319 iÅŸlemde beklenen en uzun kayÄ±p serisi â‰ˆ 11.3, yani "asla
  zamanÄ±nda deÄŸil"; ateÅŸlenince C1 sizing'de 11 kayÄ±p â‰ˆ **%69 hesap DD**. `hard_block_
  only_quarantine=true` â†’ quarantine = "0.6Ã—'te trade", hard block Ã¶lÃ¼ kod.
* **C5 [HIGH]** supervisor yalnÄ±z KESER, asla yÃ¼kseltmez â€” "MAX INCOME"un throttle-up
  mekanizmasÄ± yok. Bad-hour kurallarÄ± atÄ±l (saatte 80 iÅŸlem gerek, kitap sembol baÅŸÄ±na
  10-30 toplam). Edge-decay atÄ±l (100 iÅŸlem/sembol gerek). Decayed sembol hiÃ§
  re-optimise edilmiyor (yalnÄ±z quarantine kuyruÄŸa alÄ±yor).
* **C6 [MED]** `edge_scale` (EDGE_MIN/MAX 0.6-2.2) canlÄ± sizing'de atÄ±l â€” `raw`'a
  besleniyor, o da atÄ±lÄ±yor (C1). "Tek en yÃ¼ksek kaldÄ±raÃ§lÄ± yapÄ±sal fix" = `raw`/`r_cap`'i
  `min()`'de tut.
* **C7 [stratejik]** Ã–lÃ§Ã¼len expectancy NEGATÄ°F (âˆ’0.13R). Kelly kesri negatif â†’ optimal
  stake sÄ±fÄ±r. `max_concurrent_risk_pct=46` Ã— 4 korelasyonlu endeks long â‰ˆ 9Ã— tek-isim
  %2 â‰ˆ holdout-Kelly'de sepet iÃ§in ~2.4Ã— tam Kelly. Ã–lÃ§Ã¼len ~%10/iÅŸlem sizing'de: 5
  kayÄ±p â†’ %41 DD, 8 â†’ %57, 11 â†’ %69. GerÃ§ek %2'de: %10 / %15 / %20.
* **C8 [INFO]** `remaining_position_risk` muhasebesi DOÄžRU (trailed stop bÃ¼tÃ§e serbest
  bÄ±rakÄ±yor, double-count yok) â€” âœ“ kontrol edildi.

### D â€” ENGINE / EXECUTION  (agent 1 + agent 5)

* **D1 [HIGH]** Shakeout SL tabanÄ±: `lot_for`'a `sl_size` (1 ATR) geÃ§iliyor ama stop
  `sl_dist` (2 ATR floor, 3 kayÄ±p/10) yerleÅŸtiriliyor â†’ shakeout episodlarÄ±nda gerÃ§ek
  risk 2Ã—. `engine.py:2605-2632` / `risk.py:537`. (agent 1 F2 + agent 3 F8 Ã§apraz-doÄŸrulama)
* **D2 [HIGH]** GÃ¼nlÃ¼k-zarar breaker'Ä± `manage_positions`'Ä±n saniyeler sÃ¼ren broker
  Ã§aÄŸrÄ±larÄ±ndan Ã–NCE alÄ±nan equity'ye bakÄ±yor (`engine.py:863` â†’ 916 â†’ 918). HÄ±zlÄ± ters
  harekette fren bir tam cycle geÃ§.
* **D3 [HIGH]** `execution_samples` (canlÄ± slippage) yapÄ±sal aÃ§: `record()` `filled<=0`da
  erken dÃ¶nÃ¼yor; buffer yalnÄ±z graceful shutdown'da flush; 7 satÄ±r/17 gÃ¼n, biri dÃ¼z str.
  Backtestâ†”canlÄ± farkÄ±nÄ± kapatacak tek sinyal birikemiyor â†’ `ExecutionMonitor._verdict`
  neredeyse hiÃ§ ateÅŸlenmiyor.
* **D4 [HIGH]** `entry_blocks` pencereleme/reset yok: `_entry_blocks_since` bir kez
  seed (2026-08-16), yalnÄ±z `POST .../reset` sÄ±fÄ±rlÄ±yor (kimse Ã§aÄŸÄ±rmÄ±yor). `forget_
  entry_blocks` yalnÄ±z sembol DELETE'te. â†’ prune kararlarÄ± bayat, Ã§ok-config kanÄ±tÄ±na
  dayanÄ±yor. (= F-D3, derinleÅŸtirildi)
* **D5 [MED]** `entry_blocks` bloklanÄ±p-sonra-dolan sinyali Ã§ift sayÄ±yor (episode kimliÄŸi
  `(bar_key, reason)`; spread'de reddedilip acildi'de dolan â†’ signals += 2). `fill_rate =
  opened/total` â†’ raporlanan %22-33 fill kÄ±smen artefakt.
* **D6 [MED]** `_broker_now` 48h iÃ§indeki herhangi bir ileri-tarihli tick ile zehirleniyor
  â†’ seans sÄ±nÄ±rlarÄ± + trading gÃ¼nÃ¼ kalÄ±cÄ± kayÄ±yor; tek kurtarma = restart. (agent 1 F6
  + agent 5 F6 Ã§apraz-doÄŸrulama)
* **D7 [MED]** bar-kapanÄ±ÅŸ refetch backoff yok (lag'li sembol her 2sn `copy_rates(400-
  1680)` RLock altÄ±nda); `_probe_book_ticks` koÅŸulsuz N kilit round-trip/cycle.
* **D8 [MED]** bir Ã§Ã¶zÃ¼lemeyen fill sembolÃ¼n TÃœM giriÅŸlerini ~20 dk donduruyor
  (`_orphan_scan`, `stale_after=900s` + `abandon_grace=300s`).
* **D9 [MED latent]** off-127.0.0.1 bind'de: `GET /` herkese `Set-Cookie` token veriyor;
  Origin check yalnÄ±z tarayÄ±cÄ± CSRF'i durduruyor â†’ non-browser client `POST /api/bot/
  panic` vb. Ã§aÄŸÄ±rabilir. Default localhost'ta moot.
* **D10 [LOW]** optimizer patch yolu (`_land_pending_primary`) `trail_mode`'u structure/
  hybrid'e Ã§evirebilir, HTTP'deki widen-only/hands-off guard'Ä± yok. âœ“DB ÅŸu an hepsi `atr`.

### E â€” STRATEGY / SÄ°NYAL  (agent 4) â€” âœ“DB

* **E1 [HIGH]** GER40/M5 burst = âˆ’41R motoru: âœ“DB `brst_close_pct=0.6` (7 burst satÄ±rÄ±nÄ±n
  en gevÅŸeÄŸi; JPN225 0.9), `brst_lookback=40` (en uzun), `cost_rank_max=0` (ailenin M5'te
  taÅŸÄ±mak iÃ§in TASARLANDIÄžI gate), seans 03:15-22:59'a geniÅŸletilmiÅŸ. Ã–lÃ§Ã¼len "kÄ±sa tutuÅŸ
  = saf zarar" profiliyle birebir.
* **E2 [HIGH]** Grid-iÃ§i chop kolu zaten var, no-op'a sabitli: âœ“DB burst'te `brst_close_
  pct`, `cost_rank_max`, `atr_pct_min`, `min_body_ratio` hepsi 0. KardeÅŸ burst satÄ±rlarÄ±
  `cost_rank_max` 0.3-0.7, `atr_pct_min` 0.25 kullanÄ±yor. BunlarÄ± yÃ¼kseltmek pre-open
  ince-range popÃ¼lasyonunu trend-saati giriÅŸlerine dokunmadan filtreler.
* **E3 [MED]** âœ“DB GER40/JPN225/NAS100/US30 `opt_summary.params` YALNIZ sÄ±fÄ±rlanmÄ±ÅŸ
  gate'leri damgalÄ±yor `[adx_max, adx_min, atr_pct_min, cost_rank_max, max_spread_atr,
  min_body_ratio]` â€” trade eden sinyal paramlarÄ±nÄ± (brst_lookback=40, brst_close_pct=0.6,
  htf_factor=3, t3_length) DAMGALAMIYOR. Yani `validated=True` bir gates-disabled pass'i
  belgeliyor; sinyal paramlarÄ± Ã¶nceki bir sweep'ten kalÄ±ntÄ±, zeroed-gate'lerle birlikte
  walk-forward doÄŸrulanmamÄ±ÅŸ. (Kontrast: SpotBrent/XAUUSD/BTCUSD tam set damgalÄ±.)
* **E4 [MED-HIGH]** `adx_max` Ã¶lÃ¼-ve-tehlikeli: reversion-ailesi kalÄ±ntÄ±sÄ±, 4 ailenin (arsiv)
  hiÃ§biri reversion deÄŸil; non-zero `adx_max` bunlarÄ± yalnÄ±z gÃ¼Ã§lÃ¼ trendden Ã‡IKARIR. HÃ¢lÃ¢
  `OPT_FIELDS` + `Params.key()`'de â†’ sweep gÃ¼rÃ¼ltÃ¼de spurious non-zero `adx_max` kazanÄ±p
  `apply()` edebilir. `absent_regime_gates_to_zero` yalnÄ±z kazanan onu adlandÄ±rmayÄ±nca
  sÄ±fÄ±rlÄ±yor. â†’ 4 aile iÃ§in `OPT_FIELDS`'ten Ã§Ä±kar. (arsiv)
* **E5 [MED]** NAS100 mtf_pullback: âœ“DB `htf_factor=3` â†’ trend ayaÄŸÄ± T3(4)/M90, whippy,
  "HTF zaten trend'de olmalÄ±" DEÄžÄ°L (`else 6` yalnÄ±z htf_factorâ‰¤1'de). `pull_depth_atr=0.3`
  saklÄ± ama 0.5 Ã§alÄ±ÅŸÄ±yor (MIN_PULL_DEPTH_ATR floor) â†’ grid `{0.3,0.5}` Ã¶zdeÅŸ sinyal
  Ã¼retiyor, 0.3'Ã¼ kazanan kaydediyor (DB'nin gÃ¶sterdiÄŸi). `required_bars` factor 6
  varsayÄ±yor, sinyal factor 3 koÅŸuyor â€” sessiz tutarsÄ±zlÄ±k.
* **E6 [LOW-MED]** burst `expansion` self-inclusive mean/sd (`sma`/`rolling_std` pencereleri
  i'yi Ä°Ã‡ERÄ°YOR) â†’ `brst_range_z` gÃ¶rÃ¼ndÃ¼ÄŸÃ¼nden katÄ±; her burst holdout distorted
  istatistikte puanlanmÄ±ÅŸ. `channel_break` etkilenmiyor (kanalÄ± bir bar kaydÄ±rÄ±yor).
  MinÃ¶r: `rolling_std` `out=np.zeros` allocate edip kullanmÄ±yor (Ã¶lÃ¼ satÄ±r).
* **E7 [LOW]** Ã¶lÃ¼ kod: `indicators.py` `supertrend`/`parabolic_sar`/`stochastic_slow`
  (~130 LOC, sÄ±fÄ±r Ã§aÄŸÄ±ran), `stoch_extreme` (`Params.key()`'de bile yok), `_GATED_FLIPS
  = frozenset()` â†’ `unstamped_gates_to_zero` koÅŸulsuz `{}` dÃ¶nÃ¼yor (F-D4/C4 kalÄ±ntÄ±).

### F â€” ARAÅžTIRMA: EN YÃœKSEK-ROI DIÅž FÄ°KÄ°RLER  (agent 6, TR+EN)

1. **ATR trail aktivasyonunu dÃ¼zelt.** `trail_start` = veri: **0.3-0.5 Ã— medyan kazanan
   MFE_R** (bizde â‰ˆ 0.2-0.4R), VEYA Chandelier (giriÅŸte arm, 2.5-3Ã— ATR, aktivasyon
   paramÄ± yok). Validation reddi: **trail kazananlarÄ±n <%30'unda devreye giriyorsa** o
   set fixed-stop sistemi, at. = C2-Ã¶lÃ§Ã¼mÃ¼ ve en bÃ¼yÃ¼k gelir kaldÄ±racÄ±.
2. **Deflated Sharpe + CPCV validation gate.** DSR â‰¤ 0 (trial sayÄ±sÄ± = grid boyu) veya
   PBO â‰¥ 0.5 â†’ reddet. Mutlak OOS bar (PF>1.2, â‰¥30 iÅŸlem). Holdout(+)/canlÄ±(âˆ’)'ye
   doÄŸrudan saldÄ±rÄ±. Repo: `eslazarev/purged-cross-validation` (drop-in).
3. **Intrabar fill-sÄ±rasÄ± dÃ¼zelt** (stop-first kÃ¶tÃ¼-durum) = B2.
4. **Aile-spesifik entry gate.** pullback+ichimoku: ADX(14) **22-50 bandÄ±** (+ opsiyonel
   ERâ‰¥0.3). burst+channel_break: **ADX tabanÄ± YOK** â€” yerine volatilite-sÄ±kÄ±ÅŸmasÄ±
   (Bollinger-bandwidth son 100 barÄ±n alt ~%20'si / NR7) + ERâ‰¥0.3 tetik barÄ±nda. ADX
   breakout'a âˆ’0.12R expectancy verdi (test). = C3-Ã¶lÃ§Ã¼mÃ¼ + E2/E4.
5. **Per-sembol seans whitelist + rollover blackout.** burst/channel_break yalnÄ±z
   cash-open + US-overlap (GER40 09:00-11:30 & 14:30-16:00 CET; NAS100/US30 NY ilk 60-90
   dk). Asya Ã¶ÄŸle, Avrupa Ã¶ncesi, Cuma PM, rollover Â±2 bar blok.
6. **TF seÃ§imi R/gÃ¼n + maliyet tavanÄ±.** SembolÃ—aile iÃ§in TF sweep; **R/gÃ¼n = expectancy_R
   Ã— iÅŸlem/gÃ¼n (maliyetli)** maks, `cost_R/gross < ~0.35` ve â‰¥30 validation iÅŸlem ÅŸartÄ±yla,
   eÅŸitlikte yavaÅŸ TF'e. (Maliyet teorisi: maliyet arttÄ±kÃ§a lookback uzat.)
7. **Volatilite-hedefli sizing + katmanlÄ± frenler.** Taban **%1 risk/iÅŸlem** (holdout
   istatistiÄŸinden â‰¤ 0.25Ã— Kelly), ~%0.10/gÃ¼n volatilite katkÄ±sÄ±na sized (4 endeks eÅŸit
   risk); **gÃ¼nlÃ¼k fren %3-4**, **haftalÄ±k %8-10**; **3 ardÄ±ÅŸÄ±k kayÄ±ptan sonra yarÄ±ya**,
   yeni equity zirvesinde tam; **min-lot riski hedefin >1.5Ã—'i ise iÅŸlemi atla**.
   Pyramiding YOK (zaten yok â€” veri onaylÄ±yor: pyramiding max DD %49 vs VT %25).
8. **Cadence + profit_drop supervisor.** SembolÃ¼ **N kapalÄ± iÅŸlem sonrasÄ±** re-opt
   (takvim cap yedek); param yalnÄ±z incumbent'Ä± OOS marjÄ±yla yenerse deÄŸiÅŸtir ("bir kÃ¶tÃ¼
   hafta deÄŸil, istatistiksel kanÄ±t"). CanlÄ±: son-50-iÅŸlem **canlÄ±/holdout expectancy
   oranÄ± < 0.5 â†’ oto de-risk + zorla re-opt**; iki-katmanlÄ± kill switch (equity DD% +
   feed/broker saÄŸlÄ±ÄŸÄ±, >30sn kopukta watchdog flatten).

Repo/thread: `EarnForex/ATR-Trailing-Stop`, `xMattC/mt5-strategy-factory` (staged IS/OOS
WFO orkestrasyon), `eslazarev/purged-cross-validation` (DSR+PBO+CPCV), `polakowo/vectorbt`,
`Concretum` (vol-target 0.10%/gÃ¼n, VT DD %25 vs pyramiding %49), `@macrocephalopod` thread
(vol-norm sinyal, 3-6ay ufuk, no-trade buffer band), NY Fed SR 917 (overnight drift).

---

### Ã–NCELÄ°K â€” P0..P4 (uygulama Cursor lane'inde; red = operatÃ¶r)

**P0 â€” GÃœVENLÄ°K (gelir Ã§alÄ±ÅŸmasÄ±ndan Ã–NCE, kanama hÄ±zÄ±nÄ± kes):**
`C1` sizing bug (`raw`/`r_cap`'i `min()`'de tut = C6 fix) Â· `C3` pnl_pct payda tuzaÄŸÄ±
(bunu dÃ¼zeltmeden C2'ye dokunma) Â· `C2` gÃ¼nlÃ¼k zarar freni %3-4 (operatÃ¶r red, C3 sonrasÄ±)
Â· `D1`/`D2` shakeout sizing + bayat-equity fren Â· `C4` streak `quarantine_losses` ~5-6
Â· `D6` `_broker_now` clamp `â‰ˆ 2Ã—max_tf`.

**P1 â€” KÃ–TÃœ CONFIG SEÃ‡Ä°MÄ°NÄ° DURDUR (âˆ’0.13R'yi costed-holdout'un +0.05..+0.19'una Ã§ek):**
`A1` `_beats_incumbent` simetrik maliyet Â· `A2` costed-negatif reddi charge_costs'tan
baÄŸÄ±msÄ±z Ã§alÄ±ÅŸtÄ±r Â· `A3` objektif = `score Ã— retention` veya DSR terimi Â· `A5` gate'leri
sÄ±kÄ± (`MIN_TEST_TRADES` ~25, `MIN_OOS_PF` ~1.25) Â· `F2` DSR+PBO.

**P2 â€” BACKTEST GERÃ‡EKLÄ°ÄžÄ° (Ã¶lÃ§ebilmek iÃ§in):**
`B1` scaled `min_stop_series` Â· `B2` stop-first Â· `B3` spread simetrisi Â· `D3` slippage
telemetrisini onar (sonra apply gate'i buna kalibre) Â· `D4`/`D5` entry_blocks pencere+reset.

**P3 â€” GELÄ°R KALDIRAÃ‡LARI (asÄ±l optimizasyon):**
`F1`/C2-Ã¶lÃ§Ã¼mÃ¼ per-sembol `trail_start â‰ˆ 0.5Ã—medyan MFE` costed ara Â· `E2` burst
`cost_rank_max`/`atr_pct_min` (kardeÅŸ-satÄ±r deÄŸerleri) Â· `F4`/C3-Ã¶lÃ§Ã¼mÃ¼ `adx_min=15`
YALNIZ NAS100+US30; burst'e volatilite-sÄ±kÄ±ÅŸmasÄ± gate Â· `F5` per-sembol seans whitelist Â·
`F6` TF-by-R/gÃ¼n Â· `E5` NAS100 `htf_factorâ‰¥6` + config-honesty Â· `A6`/`A8` GER40 M5'i
kendi TF'inde + tight-stop grid'iyle ara.

**P4 â€” TEMÄ°ZLÄ°K / OTONOMÄ°:**
`E4` `adx_max` OPT_FIELDS'ten Ã§Ä±kar Â· `E7`+C4-kalÄ±ntÄ± Ã¶lÃ¼ kod Â· `A7` grid kapsam eÅŸitle Â·
`C5`/`F8` supervisor eÅŸiklerini bu frekansa Ã¶lÃ§ekle + decayâ†’reopt trigger Â· `D7` perf Â·
`C4` orphan verdict temizliÄŸi + `supervisor_state.updated_at`.

**OperatÃ¶r (red/yellow):** `daily_loss_pct` deÄŸeri, `max_concurrent_risk_pct` dÃ¼ÅŸÃ¼ÅŸÃ¼
(46â†’~12-15), disabled sembol reopen (XAUUSD/GOLD-PERP/BTCUSD costed gÃ¼Ã§lÃ¼), `claude` /login,
commit.

### EK â€” trail_start / trail_step costed sweep (02.09 20:26, salt-okur) â€” P3 REVÄ°ZYON

`c_trail_sweep.py`, npz + `charged_holdout`, canlÄ± aile/exit, `trail_start_atr âˆˆ
{0.3..2.0}`. Kazanan-iÅŸlem medyan MFE_R (autopsy): GER40 1.74, JPN225 2.19, NAS100 1.45,
US30 1.87 â€” yani **C2'deki 0.47-0.77 "medyan MFE" TÃœM iÅŸlemlerin medyanÄ±ydÄ±; KAZANANlarÄ±n
medyanÄ± 1.45-2.19R**, canlÄ± `trail_start` 2.0-2.5R kabaca kazanan-medyanÄ±nda.

| snapshot | live TS_R | ts=0.3 | ts=0.5 | ts=0.8 | ts=1.2 | ts=2.0 |
|----------|-----------|--------|--------|--------|--------|--------|
| GER40_M30 | 2.00 | +17.5 | +17.5 | +17.2 | +13.4 | **+21.4** |
| JPN225_M15 | 2.50 | +47.7 | +47.7 | +47.7 | +47.7 | **+48.3** |
| NAS100_M30 | 2.50 | +39.2 | +39.2 | +39.2 | +38.8 | **+41.1** |
| US30_M30 | 0.30 | +18.0 | +18.0 | +18.0 | +17.5 | +18.9 |

**Ã–lÃ§Ã¼len sonuÃ§:** `trail_start` sÄ±kÄ±laÅŸtÄ±rmanÄ±n costed net_r'ye faydasÄ± YOK â€” dÃ¼z veya
hafif negatif (4 sembol). Trend-takip literatÃ¼rÃ¼nÃ¼n "mekanik trail sÄ±kÄ±laÅŸtÄ±rma Ã§oÄŸu
testte getiriyi dÃ¼ÅŸÃ¼rÃ¼r" uyarÄ±sÄ±yla tutarlÄ±. â†’ **P3'ten "per-sembol trail_start â‰ˆ 0.5Ã—
medyan MFE" ADAYI DÃœÅžÃœYOR** (araÅŸtÄ±rma agent'Ä±nÄ±n "en bÃ¼yÃ¼k kaldÄ±raÃ§" iddiasÄ± bizim
veriyle desteklenmedi). C2'nin "trail fiilen Ã¶lÃ¼" Ã§erÃ§evesi fazla gÃ¼Ã§lÃ¼ydÃ¼ â€” dÃ¼zeltildi.

**AMA â€” US30 `trail_step` sweep (trail_start=0.4'te) GERÃ‡EK bir kaldÄ±raÃ§:**

| trail_step | net_r | exp | PF | n |
|-----------|-------|-----|-----|---|
| 0.4 | +6.1 | +0.016 | 1.03 | 384 |
| 0.6 | +21.2 | +0.056 | 1.11 | 379 |
| **0.8** | **+30.6** | **+0.082** | **1.16** | 371 |
| 1.2 | +25.3 | +0.071 | 1.12 | 356 |
| 1.6 | +30.0 | +0.087 | 1.14 | 344 |
| 2.2 (canlÄ±) | +18.0 | +0.054 | 1.08 | 334 |

US30 canlÄ± `trail_step=2.2` Ã§ok geniÅŸ; ~0.8'e sÄ±kmak costed +12R, expectancy +0.054â†’+0.082,
PF +0.08. Agent 1/5'in "US30 step Ã§ok geniÅŸ + %80 erken-stop-toparlama" bulgusuyla uyumlu.
â†’ **P3 YENÄ° ADAY: per-sembol `trail_step` costed aramasÄ±, US30 Ã¶nce.** (JPN225/NAS100/GER40
step sweep henÃ¼z yapÄ±lmadÄ± â€” sÄ±radaki.)

UyarÄ±: tek pencere ~18k bar, son segment. Apply = optimizer full WFO/validation (Cursor).

### EK2 â€” trail_step costed sweep, 4 canlÄ± sembol (02.09 20:34, salt-okur)

`c_trailstep_sweep.py`, canlÄ± `trail_start` sabit, `trail_step_atr âˆˆ {0.25..2.5}`.

| sembol / aile | canlÄ± step | canlÄ± net_r (exp / pf) | en iyi step | en iyi net_r (exp / pf) | Î” |
|---------------|-----------|------------------------|-------------|-------------------------|---|
| **US30** channel_break/M30 | 2.2 | +18.0 (.054 / 1.08) | **0.8** | **+33.6 (.090 / 1.18)** | **+15.6** |
| **NAS100** mtf_pullback/M30 | 2.5 | +23.6 (.021 / 1.03) | **1.6** | **+39.6 (.032 / 1.05)** | **+16.0** |
| GER40 burst/M30* | 1.8 | +22.1 (.051 / 1.08) | 1.6 | +26.4 (.060 / 1.09) | +4.3 (gÃ¼rÃ¼ltÃ¼) |
| JPN225 burst/M15 | 2.5 | +48.3 (.192 / 1.28) | 2.2 | +51.0 (.201 / 1.29) | +2.7 (gÃ¼rÃ¼ltÃ¼) |

**Ã–lÃ§Ã¼len sonuÃ§ â€” aile-spesifik (adx_min ile aynÄ± yÃ¶nde):**
- **channel_break (US30) + mtf_pullback (NAS100)** = "yerleÅŸik yapÄ±ya giren" aileler â†’
  DAHA DAR `trail_step` istiyor (US30 ~0.8, NAS100 ~1.6). US30 Ã§ift-doÄŸrulandÄ± (bu run +
  ts=0.4'te step 0.8 = +30.6). NAS100 0.6-1.6 arasÄ± ~+38, 2.2'de dÃ¼ÅŸÃ¼yor.
- **burst (JPN225, GER40)** = range-expansion â†’ GENÄ°Åž `trail_step` istiyor (2.2+);
  0.8 altÄ±na sÄ±kmak yÄ±kÄ±cÄ± (JPN225 stepâ‰¤0.8'de negatife dÃ¼ÅŸÃ¼yor). CanlÄ± deÄŸerleri
  zaten yakÄ±n-optimal.

â†’ **P3 firm:** `trail_step` **US30 2.2â†’~0.8** (en gÃ¼Ã§lÃ¼) + **NAS100 2.5â†’~1.6**; JPN225/GER40
burst step'i geniÅŸ bÄ±rak. adx_min=15 (NAS100+US30 only) ile aynÄ± ikili: iki yapÄ±-giriÅŸ
ailesi daha sÄ±kÄ± yÃ¶netim istiyor, iki burst ailesi istemiyor.

**EK6 â€” adx_min + trail_step STACK ediyor (21:19, apply-ready sayÄ±lar):**

| config | net_r | exp | pf | n |
|--------|-------|-----|-----|---|
| US30 live (adx0/step2.2) | +18.0 | .054 | 1.08 | 334 |
| US30 +adx15 | +23.9 | .075 | 1.12 | 319 |
| US30 +step0.8 | +33.6 | .090 | 1.18 | 372 |
| **US30 +adx15 +step0.8** | **+42.1** | **.118** | **1.24** | 355 |
| NAS100 live (adx0/step2.5) | +23.6 | .021 | 1.03 | 1099 |
| NAS100 +adx15 | +57.0 | .055 | 1.09 | 1033 |
| NAS100 +step1.6 | +39.6 | .032 | 1.05 | 1234 |
| **NAS100 +adx15 +step1.6** | **+65.8** | **.057** | 1.09 | 1162 |
| GER40/M30proxy +cost_rank=0.3 | +35.5 | .087 | 1.13 | 410 |

Ä°ki kaldÄ±raÃ§ ADDITIVE: US30 +24R (exp 2.2Ã—), NAS100 +42R (exp 2.7Ã—) live'a gÃ¶re. Apply
= optimizer full WFO; bu tablo hedef param + beklenen yÃ¶n.

**XAU/BTC (yeniden aÃ§Ä±ldÄ±) canlÄ±-config costed:** XAUUSD_M15 **+128.3** (exp .168, pf 1.27,
n764) Â· BTCUSD_M30 **+52.5** (.158, 1.24, n333). Ä°kisi de gÃ¼Ã§lÃ¼ â€” reopen costed-haklÄ±.

### EK7 â€” Beklenen-aylÄ±k vs holdout vs CANLI sapmasÄ± (21:34, item 4) â€” BEKLENTÄ° YÃ–NETÄ°MÄ°

**Panel projeksiyonu (`/api/state` capacity):** `projected_costed_monthly_pct = 98.3`
(+%98/ay costed!), `projected_monthly_pct = 77.3`. `total_risk_per_trade = $40.01` /
balance $229 = **%17.5/iÅŸlem** â†’ C1 sizing bug HÃ‚LÃ‚ CANLI (fix commit'li ama process
restart olmadÄ±). `projected_costed_negative = False` (canlÄ±nÄ±n negatif olduÄŸunu bile
iÅŸaretlemiyor).

**Holdout â€” DOÄžRU ÅŸekilde aylÄ±ÄŸa normalize (lookback_days=0 â†’ her sembol farklÄ± gÃ¼n):**

| sembol | holdout kÃ¼mÃ¼latif | sÃ¼re | **â†’ R/ay** | canlÄ± R (exp) |
|--------|-------------------|------|-----------|---------------|
| NAS100 | +91.8R / 1029tr | 555g | **+5** | âˆ’18.7R (exp âˆ’0.346) |
| GER40 | +53.6R / 335tr | 107g | +15 | âˆ’6.9R (exp âˆ’0.160) |
| JPN225 | +68.3R / 225tr | 278g | +7 | âˆ’17.4R (exp âˆ’0.232) |
| US30 | +37.6R / 319tr | 557g | +2 | âˆ’3.4R (exp âˆ’0.037) |
| XAUUSD | +66.4R / 426tr | 280g | +7 | +9.8R (exp +0.316) |
| BTCUSD | +67.4R / 286tr | 376g | +5 | âˆ’2.8R (n=4) |
| **KÄ°TAP** | | | **~+41R/ay (gerÃ§ekÃ§i tavan)** | **âˆ’41.2R / 14.3g â†’ âˆ’87R/ay** |

**Ã–lÃ§Ã¼len sapma:**
1. Herkesin alÄ±ntÄ±ladÄ±ÄŸÄ± "+90R holdout" NAS100 iÃ§in **1.5 YIL**. AylÄ±ÄŸa **+5R**. KÃ¼mÃ¼latif
   sayÄ±lar sÃ¼re normalize edilmeden karÅŸÄ±laÅŸtÄ±rÄ±lamaz (B4: `lookback_days=0`).
2. Kitap-geneli gerÃ§ekÃ§i holdout â‰ˆ **+41R/ay**. Panel **+%98/ay** diyor â€” bu, kÄ±rÄ±k
   sizing ($40/R) Ã— iyimser iÅŸlem-frekansÄ± ekstrapolasyonunun artefaktÄ±. UlaÅŸÄ±labilir deÄŸil.
3. **CanlÄ± gerÃ§ek: âˆ’87R/ay trajesi** (âˆ’%38/ay, mevcut sizing). Panel +%98 ile arada
   **~136 puan** fark.
4. Her sembolÃ¼n canlÄ± expectancy'si holdout'unun **~0.25-0.45R ALTINDA** â€” kitap-geneli
   tutarlÄ± ~0.3R/iÅŸlem decay/execution gap'i.

**GerÃ§ekÃ§i hedef (P1-P3 sonrasÄ±):** canlÄ± expectancy âˆ’0.13R â†’ holdout ~+0.15R ortalamaya
Ã§ek. DÃ¼zgÃ¼n-sized $230 hesapta â‰ˆ **+$150-250/ay**, +%98/ay DEÄžÄ°L. `projected_*` alanlarÄ±
gerÃ§ekÃ§i trade-frekansÄ± + doÄŸru sizing ile yeniden hesaplanmalÄ±; `projected_costed_negative`
canlÄ± expectancy'yi de okumalÄ±.

**entry_blocks:** âœ“DB `entry_blocks_since` artÄ±k 09-02 17:57 (F-D3 roll CANLI). SayaÃ§lar
taze. `entry_block_events` (ring, 1474): spread 398 / acildi 376 / risk_sembol_limiti 261
/ risk_ters_yon 223 / bar_bosluk 138 / lot 38 â€” F-E1/E2/E3 profili deÄŸiÅŸmedi.

### EK8 â€” NAS100 htf_factor (E5) + JPN225 burst params (E3) â€” Ä°NTERAKSÄ°YON UYARISI (21:49)

**NAS100 mtf_pullback/M30 â€” `htf_factor` sweep (canlÄ±=3):**

| htf_factor | net_r | exp | pf |
|-----------|-------|-----|-----|
| 2 | âˆ’21.8 | âˆ’.018 | 0.97 |
| **3 (canlÄ±)** | +23.6 | .021 | 1.03 |
| 6 | **+53.0** | .052 | 1.08 |
| 8 | +55.5 | .056 | 1.09 |
| **12** | **+72.3** | **.075** | 1.12 |

E5 DOÄžRULANDI + bÃ¼yÃ¼k: `htf_factor=3` "zorunlu HTF trend ayaÄŸÄ±"nÄ± iÅŸlevsiz bÄ±rakÄ±yor
(T3(4)/M90). 12'ye Ã§Ä±karmak **+49R** â€” NAS100 (en kÃ¶tÃ¼ canlÄ± sembol) iÃ§in bulunan tek
en bÃ¼yÃ¼k kaldÄ±raÃ§. `required_bars` zaten factor 6 varsayÄ±yor.

**AMA Ä°NTERAKSÄ°YON:** htf=12 + adx15 + step1.6 = **+46.7R** < htf=12 tek baÅŸÄ±na (+72.3).
`htf_factor` ve `adx_min` Ã¶rtÃ¼ÅŸÃ¼yor (ikisi de trend filtresi). â†’ **NAS100 iÃ§in P3'Ã¼
revize et: adx15+step1.6 (EK6) DEÄžÄ°L â€” {htf_factor, adx_min, trail_step} BÄ°RLÄ°KTE WFO.**
Tek-eksen delta'larÄ± toplamsal deÄŸil.

**JPN225 burst/M15 â€” signal params (canlÄ± lb=15, rz=1.5, cp=0.9):**
- Baseline +48.3 (exp .192). **lookback=20, range_z=1.0 â†’ +60.9R** (+12.6, modest).
- `brst_close_pct`: canlÄ± **0.9 EN Ä°YÄ°** (+48.3, exp .192); 0.8â†’+40.5, 0.6/0.7â†’+21.
  JPN225'in sÄ±kÄ± close_pct'si DOÄžRU â€” GER40'Ä±n 0.6'sÄ±nÄ±n TERSÄ° (E1). Leftover paramlar
  bÃ¼yÃ¼k Ã¶lÃ§Ã¼de saÄŸlam; lb 15â†’20 + rz 1.5â†’1.0 kÃ¼Ã§Ã¼k kazanÃ§, acil deÄŸil.

**Genel Ã§Ä±karÄ±m:** per-sembol P3 kaldÄ±raÃ§larÄ± BÄ°RBÄ°RÄ°YLE ETKÄ°LEÅžÄ°YOR (htfÃ—adx, adxÃ—step).
Tek-eksen costed delta'larÄ± "aday aralÄ±k" olarak ver, apply = optimizer'Ä±n JOINT WFO'su.
Claude tek-eksen tarÄ±yor; Cursor birlikte aratÄ±p validate ediyor.

### EK9 â€” JOINT mini-grid'ler (21:55) â€” APPLY HEDEFLERÄ° NETLEÅžTÄ°

**US30 (adx_min Ã— trail_step):**

| | step 0.6 | step 0.8 | step 1.2 | step 2.2 |
|---|---|---|---|---|
| adx=0 | +21.2 | +33.6 | +26.1 | +18.0 |
| **adx=15** | +28.5 | **+42.1** | +38.0 | +23.9 |

Ä°ki kaldÄ±raÃ§ her hÃ¼crede ADDITIVE, tepe kÃ¶ÅŸede. **US30 APPLY: {adx_min=15,
trail_step=0.8} â†’ +42.1R (exp .118, pf 1.24).** Firm.

**NAS100 (htf_factor Ã— adx_min, step 2.5 & 1.6):**

| step 2.5 | adx0 | adx15 | adx20 |
|---|---|---|---|
| htf=3 | +23.6 | +57.0 | +46.8 |
| htf=6 | +53.0 | +52.5 | +68.9 |
| **htf=12** | **+72.3** | +57.2 | +68.4 |

`htf_factor` ve `adx_min` **SUBSTITUTE** (tamamlayÄ±cÄ± deÄŸil): htf=12 tek baÅŸÄ±na +72.3;
htf=12 + adx=15 = +57.2 (Ä°KÄ°SÄ° birden DAHA KÃ–TÃœ). Bir gÃ¼Ã§lÃ¼ trend filtresi yeter.
**NAS100 APPLY: {htf_factor=12, adx_min=0 (deÄŸiÅŸme), trail_step=2.5 (deÄŸiÅŸme)} â†’ +72.3R.**
= tek-param deÄŸiÅŸiklik, EK6/EK8'deki "adx15+step1.6" (+65.8) Ã¶nerisinden **BASÄ°T + Ä°YÄ°**.
(htf=6/adx20 = +68.9 de alternatif.)

**GOLD-PERP (mtf_pullback/M30 â€” add adayÄ±):**

| config | net_r | exp | pf |
|--------|-------|-----|-----|
| **baseline (as-is)** | **+114.3** | .219 | 1.35 |
| adx15 | +104.7 | .219 | 1.36 |
| htf6 | +67.2 | .133 | 1.21 |
| htf12 | +74.5 | .147 | 1.23 |
| step1.6 | +115.8 | .219 | 1.35 |

**GOLD-PERP baseline near-optimal â€” AS-IS ekle, ayar yok.** adx_min zarar (commodity),
htf deÄŸiÅŸimi zarar (NAS100'Ã¼n TERSÄ° â€” GOLD'un htf_factor=3'Ã¼ doÄŸru), step marjinal.
+114R costed = kitabÄ±n en gÃ¼Ã§lÃ¼ add adayÄ±.

**GER40 M5 (item 1) â€” KESÄ°N DURUM:** `data/holdout_bars/`'da GER40_M5.npz YOK; panel'de
bulk-bar GET endpoint'i YOK; MT5 sidecar YASAK. GER40 M5 costed doÄŸrulama **Claude
tarafÄ±ndan yapÄ±lamaz** â€” `POST /api/holdout/capture GER40 M5` gerek (flat kitap, 409
ticket varken). **Cursor gÃ¶revi.** M30 proxy: cost_rank=0.3 â†’ +35.5R (+14R), en iyi
mevcut kanÄ±t.

### EK10 â€” Live-vs-holdout 0.3R/iÅŸlem DECAY dekompozisyonu (22:04) â€” SEBEP BULUNDU

319 canlÄ± autopsy dÃ¶kÃ¼mÃ¼:

1. **GiriÅŸ slippage'i SORUN DEÄžÄ°L:** `fill_vs_signal_close_r` medyan +0.014, ort +0.031,
   toplam +7.8R / 252 iÅŸlem. Spread at-fill medyan 0.05 ATR. Toplam ~5-10R aÃ§Ä±klÄ±yor.
2. **Noise-stop DEÄžÄ°L:** 166 `sl` Ã§Ä±kÄ±ÅŸÄ±ndan **%0'Ä±** "MAE 1.00-1.15 + Ã¶nce MFEâ‰¥0.5"
   (kÄ±l payÄ± stop) deÄŸil. Stop yiyenler gerÃ§ekten ters gidip ters kalan iÅŸlemler.
3. **Exit mix:** `sl` %52 (avgR âˆ’0.94, âˆ’156R) Â· `trail` %31 (+0.84) Â· `flatten` %15
   (+0.59). Win rate %48 â€” trend sistemi iÃ§in avgWin +0.84/avgLoss âˆ’0.94 ile ~%53 gerek.
   **KÄ±l payÄ± kaybediyor, sorun %52 sl oranÄ±.**
4. **ASIL SEBEP â€” after_1h:** 129 `sl` iÅŸleminin **%74'Ã¼ 1 saat iÃ§inde entry'yi geri
   geÃ§ti** (medyan recovery +1.28R, ort +1.68R). â‰ˆ95 stop, fiyatÄ±n geri geldiÄŸi iÅŸlem.
5. **TutuÅŸ-sÃ¼resi:** `<15m` n47 avgR **âˆ’0.91** Â· `15-45m` n73 **âˆ’0.67** Â· `45-120m` +0.03
   Â· `120-300m` +0.11 Â· **`300m+` n41 avgR +0.97, sumR +40 (kitabÄ±n TÃœM kÃ¢rÄ±)**.
   120 iÅŸlem (<45m) âˆ’92R kaybediyor; 41 iÅŸlem (300m+) +40R kazanÄ±yor. **Kitap ilk 45
   dakikayÄ± hayatta geÃ§irip geÃ§irmemeye baÄŸlÄ±.**

**sl_atr_mult sweep (canlÄ±=1.0 hepsi):**

| sembol / aile | sl0.9 | sl1.0 | sl1.2 | sl1.5 | sl2.0 |
|---------------|-------|-------|-------|-------|-------|
| **NAS100** mtf_pullback | âˆ’4.7 | +23.6 | +54.9 | **+71.0** | +36.1 |
| **JPN225** burst | **+61.2** | +48.3 | +38.0 | +23.4 | +14.3 |
| US30 channel_break | +16.3 | +18.0 | +19.7 | +17.9 | +15.1 |
| GER40 burst/M30 | +14.6 | +21.4 | +19.5 | +9.3 | +7.5 |

**Aile-spesifik, yine:**
- **NAS100 (mtf_pullback): geniÅŸ stop Ã§ok yardÄ±mcÄ±** (1.0â†’1.5 = +47R). Ama `htf_factor`
  ile SUBSTITUTE: sl1.5+htf12 = +33.8 (< htf12 tek baÅŸÄ±na +72). Ä°kisi de "hÄ±zlÄ± Ã¶lÃ¼m"
  sorununu Ã§Ã¶zÃ¼yor, birlikte over-correct (n 969â†’730). â†’ NAS100 iÃ§in: **htf_factor=12
  VEYA sl_atr_mult=1.5** (~+72 vs +71) â€” BÄ°RÄ°NÄ° seÃ§, htf tercih (stop geometrisine
  dokunmaz, risk profili temiz).
- **JPN225 (burst): DAHA DAR stop** (0.9) â†’ +13R. burst tasarÄ±mÄ± gereÄŸi hÄ±zlÄ± Ã¶lÃ¼r,
  kÄ±sa tasma doÄŸru. NAS100'Ã¼n TERSÄ°.
- US30/GER40: sl 1.0-1.2, mevcuta yakÄ±n.

**Decay sonucu:** 0.3R/iÅŸlem gap'i bÃ¼yÃ¼k Ã¶lÃ§Ã¼de NAS100 (mtf_pullback) kaynaklÄ± â€” 1.0 ATR
ilk stop, pullback-devam hareketi geliÅŸmeden yakalÄ±yor. Fix = `htf_factor=12` (zaten
tespit edildi). burst isimleri sÄ±kÄ± stop'ta zaten doÄŸru. KitabÄ±n kalan gap'i daha yaygÄ±n
(rejim kaymasÄ±, 1.5yÄ±l holdout vs 14g canlÄ± Ã¶rneklem).

### EK11 â€” WFO RUN SONUCU (21:53-22:10) â€” churn freni + NAS100 burst (22:12)

OperatÃ¶r "US30 opt geÃ§emedi, stratejiler karmaÅŸÄ±k" dedi. Log gerÃ§eÄŸi:

| sembol | WFO kazananÄ± | validation | holdout | uygulanmadÄ± Ã‡ÃœNKÃœ |
|--------|--------------|-----------|---------|-------------------|
| **NAS100** | **burst/M30** skor 85.7 | PF 1.51 +189.6R | PF 1.29 **+99.1R** | churn freni (config 7s < 48s) |
| JPN225 | burst/M30 skor 58 | PF 1.41 +93R | PF 1.19 +50.4R | churn freni |
| GER40 | burst/M5 skor 58 | PF 1.23 +52.8R | PF 1.14 +31.4R | churn freni |
| **US30** | YOK | â€” | â€” | hiÃ§bir aday kapÄ±dan geÃ§medi (gate DOÄžRU) |

- **US30:** alternatifler holdout'ta Ã§Ã¶ktÃ¼ (mtf_pullback/M5 val +54R â†’ holdout âˆ’71R PF 0.83).
  Mevcut channel_break/M30 validated + retention 1.12 â†’ US30'un veride en iyisi. A5
  (MIN_TEST=25) + gate overfit'i reddediyor = istenen davranÄ±ÅŸ. "KarmaÅŸÄ±k strateji" deÄŸil.
- **NAS100 aile karÅŸÄ±laÅŸtÄ±rmasÄ± (aynÄ± pencere, costed):** current mtf_pullback/M30 (arsiv)
  **+23.6R** (exp .021) Â· mtf_pullback+htf12 **+72.3R** (exp .075, n969) Â· WFO burst/M30
  **+59.4R** (exp **.110**, PF 1.17, n**538**). burst yarÄ± turnover'da daha yÃ¼ksek
  expectancy + WFO tam-doÄŸrulamadan geÃ§ti (+99R). mtf+htf12 tek-pencere bulgusu,
  doÄŸrulanmadÄ±.

**Reframe:** En hÄ±zlÄ± gelir kaldÄ±racÄ± benim param sweep'lerim DEÄžÄ°L â€” **WFO'nun bulduÄŸu
3 config'i uygulamak** (NAS100 burst +99R, JPN +50R, GER +31R holdout). `reopt_min_age_
hours` 48 â†’ geÃ§ici ~4-6 VEYA bu 3 iÃ§in force-apply (A1 fix yeni; oturunca 48'e geri).
Benim EK8-10 NAS100 tuninglerim mtf_pullback Ã¼zerineydi â†’ NAS100 burst'e geÃ§ince geÃ§ersiz.
Kitap 3/4 burst'e yakÄ±nsÄ±yor (channel_break yalnÄ±z US30, mtf_pullback hiÃ§bir yer, ichimoku 0).

### EK12 â€” HEDEF MÄ°MARÄ° SENTEZ (research agent #2 + Ã¶lÃ§Ã¼mler, 22:24)

AraÅŸtÄ±rma (Carver, Davey, WFO literatÃ¼rÃ¼, ORB replikasyonlarÄ± â€” TR+EN, tam kaynaklar
FOR_CURSOR.md) + bizim Ã¶lÃ§Ã¼mlerimiz aynÄ± yere iÅŸaret ediyor:

**A. AÄ°LE YAPISI**
- **"Tek edge, Ã§ok enstrÃ¼man" > "Ã§ok aile, sembol-baÅŸÄ±na-en-iyi".** Carver: sembol-baÅŸÄ±na
  fit "aÃ§Ä±kÃ§a aptalca" (Sharpe individual 0.60 vs pooled 0.65). `burst` ve `channel_break`
  AYNI edge (range/seviye geniÅŸlemesi) â€” ayrÄ± "aile" saymak sahte Ã§eÅŸitlendirme.
- **Holdout+/canlÄ±âˆ’ aÃ§Ä±ÄŸÄ± = multiple-comparisons makinesi.** "4 aile Ã— TF Ã— grid, sembol (arsiv)
  baÅŸÄ±na en iyi" = Ã§ok sayÄ±da gÃ¼rÃ¼ltÃ¼lÃ¼ tahminin maksimumunu seÃ§mek â†’ garantili iyimser
  holdout + canlÄ± dÃ¼ÅŸÃ¼ÅŸ (bizim âˆ’0.13R). Ã‡Ã¶zÃ¼m: seÃ§imdeki serbestlik derecesini AZALT,
  daha Ã§ok tuning DEÄžÄ°L.
- **KARAR:** `ichimoku` tamamen Ã§Ä±kar. `burst`+`channel_break` â†’ TEK breakout ailesi
  kavramÄ±, birlikte skorla, re-opt baÅŸÄ±na BÄ°R seÃ§. `mtf_pullback` yalnÄ±z metal/emtia
  (GOLD-PERP +114R; indeks aramasÄ±ndan Ã§Ä±k).

**B. PARAMETRELER: EVRENSEL (pooled), sembol-baÅŸÄ±na DEÄžÄ°L**
- 4 indeks iÃ§in TEK {sl_atr, trail_start, trail_step, lookback, close_pct} â€” pooled trade
  set Ã¼zerinde fit. Sembol-baÅŸÄ±na tek knob: volatilite/maliyet skalarÄ± (pozisyon boyutu
  + trail sÄ±kÄ±lÄ±ÄŸÄ± ATR/spread ile Ã¶lÃ§eklenir).
- Fit'in PLATO'da olmasÄ± ÅŸart: Â±%10 / Â±1 grid adÄ±m pozitif + tepenin ~%20'si iÃ§inde.
- **Bu, benim EK2-11 per-sembol sweep'lerimin Ã§oÄŸunu geÃ§ersiz kÄ±lÄ±yor** â€” onlar
  sembol-baÅŸÄ±na tuning. DoÄŸru yÃ¶n: eksenleri POOLED ara.

**C. CHURN FRENÄ° â€” 48s saat brake'i Ã‡Ã–PE, compound gate:**
CanlÄ± config DEÄžÄ°ÅžÄ°R ancak HEPSÄ° saÄŸlanÄ±rsa: (1) challenger OOS expectancy â‰¥ +0.20R/iÅŸlem
VE â‰¥%25-30 rel PF Ã¼stÃ¼n; (2) challenger â‰¥100 kendi-holdout iÅŸlemi; (3) plato testi;
(4) rolling OOS alt-pencerelerin â‰¥%60-70'inde net-pozitif (regime-concentration tuzaÄŸÄ±);
(5) incumbent â‰¥1 tam OOS penceresi canlÄ± Ã§alÄ±ÅŸmÄ±ÅŸ (â‰¥60 gÃ¼n VE â‰¥40 canlÄ± iÅŸlem).
AyrÄ± **kill-switch:** canlÄ± expectancy < âˆ’0.30R / â‰¥40 iÅŸlem â†’ config'i sideline et,
taze backtest'ten OTOMATIK deÄŸiÅŸtirme; Ã§eyreklik dÃ¶ngÃ¼ yeniden tÃ¼retsin.

**D. CANLIYÄ± NEGATÄ°FTEN POZÄ°TÄ°FE Ã‡EKECEK 5 KURAL (burst'e â€” YENÄ° OPT eksenleri):**
1. **KasÄ±lma Ã¶n-koÅŸulu (EN YÃœKSEK KALDIRAÃ‡):** NR7 VEYA `ATR(setup)/ATR(20) â‰¤ ~0.7` VEYA
   BB bandwidth son 50 barÄ±n alt %15-20'sinde â‰¥3 bar. "Her yayÄ±nlanmÄ±ÅŸ versiyonun
   kullandÄ±ÄŸÄ±, bizim ailenin muhtemelen eksik olduÄŸu filtre."
2. **Rejim/eÄŸim gate:** long yalnÄ±z fiyat > HTF EMA + eÄŸim â‰¥ 0. (Bizim `htf_factor` bir
   T3 yÃ¶n bayraÄŸÄ±, eÄŸim gate'i deÄŸil.)
3. **Tetik-barÄ± sertleÅŸtir:** TR â‰¥ 1.5Ã—ATR(20) VE kapanÄ±ÅŸ barÄ±n Ã¼st/alt %15-25'inde;
   inside/outside tetik barÄ± reddet; sonraki-bar giriÅŸ boÅŸluÄŸu > xÂ·ATR ise reddet.
4. **TF + seans:** motoru H1/H4'e taÅŸÄ± (fakeout ~%65â†’~%50); cash-open sonrasÄ± ilk N dk +
   dÃ¼ÅŸÃ¼k-likidite bakÄ±m penceresini blokla. (F5/EK4 ile uyumlu.)
5. **Maliyet-edge gate:** spread > ATR-stop mesafesinin k%'si VEYA ATR alt Ã§eyrekte ise
   atla; beklenen lehte hareket â‰¥ ~3Ã— round-turn maliyet.
Bonus: cross-index teyit (korelasyonlu indeks sinyal anÄ±nda hemfikir olsun â€” replikasyonda
+$0.125/share t=2.05); ATR trail'i GEVÅžET (aÅŸÄ±rÄ±-sÄ±kÄ± trail klasik holdout-iyi/canlÄ±-kÃ¶tÃ¼).

**E. RE-OPT CADENCE:** Ã§eyreklik (â‰ˆ63 iÅŸlem gÃ¼nÃ¼), 6-ay OOS roll, 2-3 yÄ±l IS. Bir config
canlÄ±ya UYGUN olmadan: â‰¥8-15 walk-forward dÃ¶ngÃ¼sÃ¼, dÃ¶ngÃ¼ baÅŸÄ±na â‰¥90 IS iÅŸlem (30Ã—3 param),
WFE â‰¥ 0.5 (ideal â‰¥0.6, â‰¥7 ardÄ±ÅŸÄ±k dÃ¶ngÃ¼).

**Ã–NCELÄ°K:** D1 (kasÄ±lma filtresi) + D2 (eÄŸim gate) = en yÃ¼ksek beklenen canlÄ±-P&L etkisi,
ama YENÄ° kod (`_burst` + OPT_FIELDS + grid + test). C (churn gate) = P1'in parÃ§asÄ±, WFO
overfit seÃ§mesini durdurur. A/B (aile+param sadeleÅŸme) = operatÃ¶r onaylÄ± yÃ¶n. SÄ±ralama
Cursor + operatÃ¶r.

### EK13 â€” 2 YENÄ° AÄ°LE TASARIMI (agent, operatÃ¶r +2 aile onayÄ±, 03.09 00:00)

Tam pseudocode + grid + kanÄ±t + kill-criteria: FOR_CURSOR.md 00:0X bloÄŸu.

**#1 `band_fade` â€” MEAN-REVERSION (kitabÄ±n eksik edge'i):**
- Tez: indeks kendi vol bandÄ±nÄ± (Bollinger N-Ïƒ) delip HEMEN kendi ekstremine karÅŸÄ±
  kapanÄ±rsa (IBS â‰¤ 0.15 = alt banda delip barÄ±n DÄ°BÄ°NE kapandÄ±) â†’ ortalamaya doÄŸru fade.
- Gate: ADX â‰¤ 25 (trend yok) + vol RANK â‰¤ 0.7 (kasÄ±lmÄ±ÅŸ, geniÅŸleyen deÄŸil) + ortalamaya
  mesafe â‰¥ min_atr (lagging trail'in kÃ¢r yazmasÄ± iÃ§in) + seans + cost + HTF hizasÄ±.
- 5 param: `bf_ma_len, bf_band_k, bf_ibs, bf_vol_rank_max, bf_min_room_atr` + reuse `adx_max`.
- **burst ile MEKANÄ°K ANTÄ°-KORELE:** burst barÄ±n Ã¼st %30'una kapanÄ±r; band_fade IBSâ‰¤0.15
  (dibe). AynÄ± bÃ¼yÃ¼klÃ¼ÄŸÃ¼n ters iÅŸareti. burst'Ã¼n en iyi barlarÄ±nÄ± gate B blokluyor.
- **Deploy: YALNIZ GER40/NAS100/US30/JPN225** (indeksler; gold/kripto intraday az revert).
- KanÄ±t: Pagonidis IBS effect (indeks ETF), Connors RSI2, IBS Ã§alÄ±ÅŸmalarÄ± â€” spesifik
  olarak equity indeks. GitHub ref'ler mevcut.

**#2 `roc_pace` â€” TIME-SERIES MOMENTUM (breakout DEÄžÄ°L):**
- Tez: yerleÅŸik Ã§ok-bar drift'i sÃ¼r, ROC rank saÄŸlÄ±klÄ± bandda (0.55-0.97) iken TREND
  ORTASINDA gir â€” yeni ekstremde asla, tek barda asla, parabolikte dur.
- Trigger: ROC(24-96 bar) rank saÄŸlÄ±klÄ± band + T3 eÄŸim uyumu + ADX â‰¥ 15 + HTF hizasÄ± +
  L-bar hareket â‰¥ min_atr. `rp_rank_hi` = exhaustion cap (blow-off barÄ± reddet).
- 5 param: `rp_roc_len, rp_rank_win, rp_rank_lo, rp_rank_hi, rp_min_move_atr` + reuse
  `adx_min, htf_factor`.
- **Deploy: BTCUSD/XAUUSD/SpotBrent/NAS100** â€” burst sembollerinden enstrÃ¼man-ayrÄ±ÅŸmasÄ±.
  â†’ **SpotBrent'in cevabÄ± olabilir** (burst costed âˆ’27, roc_pace trend-takip).
- #2 Ã§Ã¼nkÃ¼ momentum SINIFI'nÄ± burst kÃ¼mesiyle paylaÅŸÄ±yor; "momentum Ã§alÄ±ÅŸmadÄ±" rejiminde
  aynÄ± ÅŸoka aÃ§Ä±k. Slot'u enstrÃ¼man-ayrÄ±ÅŸmasÄ± + exhaustion cap ile hak ediyor.
- KanÄ±t: Moskowitz/Ooi/Pedersen "Time Series Momentum" 2012 (58 futures, indeks+emtia,
  Sharpe ~1.3), Quantpedia, AQR, KÄ±vanÃ§ Ã–zbilgiÃ§ PMax/MOST (TR).

**Ã–neri:** `band_fade` Ã–NCE (en yÃ¼ksek Ã§eÅŸitlendirme, en dÃ¼ÅŸÃ¼k korelasyon riski) â†’ 4
indekste WFO gate'inden geÃ§ir. `roc_pace` #2, band_fade sonucuna gÃ¶re + SpotBrent testi.
Ä°kisi de aynÄ± WFO/validation kapÄ±sÄ±ndan; validate etmezse otomatik retire (kill-criteria
EK13 blok). Kod: `Params` + `OPT_FIELDS` + `Params.key()` + `_FAMILIES` + `STRATEGIES` +
grid + test â€” Cursor lane.

### EK14 â€” SL / TAKÄ°P-SL / GÄ°RÄ°Åž / Ã‡IKIÅž MEKANÄ°K DERÄ°N AUDIT (agent, 03.09 00:01)

**[CRITICAL] C1-shakeout â€” HÃ‚LÃ‚ CANLI, Ã¼Ã§lÃ¼-doÄŸrulandÄ±, 1 satÄ±r fix.**
`engine.py:2626-2678`: shakeout floor stop'u 2Ã—ATR'ye aÃ§Ä±yor ama `lot_for`'a `sl_size`
(1Ã—ATR) geÃ§iliyor â†’ 3 stop/10 sonrasÄ± (kayÄ±p serisi 10-16, rutin) **gerÃ§ek risk %4**
(en kÃ¶tÃ¼ anda). `r_cap` de dar mesafeye bÃ¶lÃ¼yor â†’ o da 2Ã—. `can_open` GENÄ°Åž mesafeyi
gÃ¶rÃ¼yor (iÃ§ Ã§eliÅŸki). `shakeout_size_note` operatÃ¶re "risk ayni" DÄ°YOR (artÄ±k yanlÄ±ÅŸ).
Commit `fe26ace` bunu getirdi. **FIX: `engine.py:2651` (+2638) `sl_size` â†’ `sl_dist`**
(shakeout yokken zaten eÅŸit). Bu, RE-fleet F2/F8 + bu agent = 3. kez. Cursor'un C1 commit'i
sizing'i dÃ¼zeltti ama BU ayrÄ± ve hÃ¢lÃ¢ aÃ§Ä±k.

**[HIGH] H2 â€” stale-clock'ta flatten yollarÄ± Ã–LÃœ.**
`engine.py:3299,3349`: weekend/session/day-end flatten `if server_now is not None`
guard'lÄ±; `decision_now()` 600s stale tick'te None dÃ¶ner. Cuma akÅŸamÄ± feed stall â†’
pozisyon weekend gap'e biner. `_weekend_pending` de yalnÄ±z `server_now` varken eklenebiliyor.
FIX: flatten kararlarÄ± iÃ§in `broker_now()`/`server_now()` fallback (yanlÄ±ÅŸ-saatte flatten
gÃ¼venli; flatten-etmemek deÄŸil). GiriÅŸler strict `decision_now()`'da kalsÄ±n.

**[HIGH] H1 â€” fill-verify sonucu engine mid-verify durursa kaybolur.**
`_try_entry` daemon thread spawn ediyor (~2.1s sleep); sonuÃ§ yalnÄ±z `_cycle` iÃ§inde
drain. Verify sÄ±rasÄ±nda stop â†’ `_mark_bar_filled` Ã§aÄŸrÄ±lmÄ±yor â†’ restart'ta `_filled_bars`
kaydÄ± yok â†’ pozisyon downtime'da kapandÄ±ysa aynÄ± bar sinyali tekrar ateÅŸler (Ã§ift giriÅŸ).
FIX: send anÄ±nda pending-verify persist + `_mark_bar_filled`; startup'ta re-drain.

**[HIGH] H3 â€” daily-loss + panic flatten (`close_all`) autopsy/sample/log BIRAKMIYOR.**
`close_all` â†’ `close_position` doÄŸrudan, `fill=` yok, autopsy yok. `_reap_execution` de
atlÄ±yor (`DEAL_REASON_EXPERT` `_CLOSED_ELSEWHERE` dÄ±ÅŸÄ±nda). En yÃ¼ksek-riskli Ã§Ä±kÄ±ÅŸÄ±n en
zayÄ±f adli izi. FIX: `close_all`'Ä± tracked close'dan geÃ§ir.

**[MED]** M4 ilk `breakeven_at_r` sub-entry stop koyabilir (guard `breakeven_locked`'a
gated, ilk BE'de false) Â· M5 `_fill_time_risk` fallback dar `sl_atr_mult` (shakeout
gÃ¶rmezden) Â· M6 48h ileri-tick toleransÄ± seans kararlarÄ±nÄ± zehirliyor (fix: ~300s) Â·
M7 stale sinyal should_flatten/cooldown pencerelerinde tutuluyor Â· M8 `min_stop_distance`
spread ile ÅŸiÅŸiyor, SL-mesafe gate'i yok.

**[LOW â€” Ä°YÄ° HABER]** Trail geri gidemiyor âœ“ Â· gap-past-trail doÄŸru âœ“ Â· BE(1.5)/
trail_start(2.5) tutarlÄ±, bu config'te trail sub-entry stop koymaz âœ“ Â· giriÅŸ-timing
bug'Ä± (21-30s stale timer) DÃœZELMÄ°Åž âœ“ Â· netting/disconnect saÄŸlam âœ“.

**[LOW-ama-Ã¶nemli] L8:** Hesap-seviyesi zarar freni YOK (`daily_loss_pct=0`). C1-shakeout
(%4 risk) + 10-16 kayÄ±p serisi ile: kÃ¶tÃ¼ NAS100 serisi ile hesap arasÄ±nda tek ÅŸey
per-trade hard stop. OperatÃ¶r kararÄ± ama C1 ile birlikte kritik.

**Ranked fix (Critical/High):** C1 `engine.py:2651` sl_sizeâ†’sl_dist Â· H2 `engine.py:3299,
3349` broker_now fallback Â· H1 `engine.py:2754/1015` persist+mark_bar_filled at send Â·
H3 `close_all` tracked. Hepsi Cursor lane, pytest+ruff.

### EK15 â€” KOD SAÄžLIK SWEEP (agent, 03.09 00:0X) â€” Ã§alÄ±ÅŸma aÄŸacÄ± KENDÄ° gate'ini geÃ§miyor

`pytest`: **4 fail / 2717 pass**. `ruff`: **3 finding**. `import micofx`: temiz.

**[TEST FAIL #1 â€” 3. CANLI SIZING BUG, en yÃ¼ksek]:** `risk.py:555-558`: broker `volume_min`
> `r_cap` (2% 1R cap) iken kod iÅŸlemi ATLAMAK yerine `volume_min`'e **YUKARI sized ediyor**
(`MAX_MIN_LOT_OVERSHOOT=3.0` â†’ 3Ã— cap'e kadar). $230 hesapta 2% cap sÄ±k sÄ±k broker
min-lot'un altÄ±nda â†’ **iÅŸlemler ~3Ã— hedeflenen riskle aÃ§Ä±lÄ±yor**. Commit `fe26ace`
getirdi; C1/C3 fix'i (`8855d65`) DOKUNMADI. C1-shakeout (EK14) + bu = iki ayrÄ± canlÄ±
sizing bug'Ä± hÃ¢lÃ¢ aÃ§Ä±k. FIX seÃ§enek: (a) `risk.py:556-558` clamp-up dalÄ±nÄ± sil â†’ hep
`return 0.0` (iÅŸlem atla), testi geri getir; (b) overshoot'u 1.5Ã—'e indir + testi gÃ¼ncelle.
AraÅŸtÄ±rma (EK12 F7): "min-lot riski hedefin >1.5Ã—'i ise iÅŸlemi atla" â†’ (a) veya (b@1.5).

**[TEST FAIL #2-4]:** `web/static/app.js:930` hÃ¢lÃ¢ `ichimoku` label (2 test); `test_
indicator_edge_inputs.py:124` bayat bound `21>=22` (ichimoku_lines silindi). â†’ 3 satÄ±r fix.

**[RUFF]:** `scripts/apply_trail_step_queue.py:9` unused `sys`; 2 test import-sort. Trivial.

**[Ã–LÃœ KOD â€” production'da 0 referans]:** `indicators.py` `parabolic_sar()` (~54 sat),
`stochastic_slow()` (~20), `supertrend()` (~40). RE-fleet'te de flag'lendi, hÃ¢lÃ¢ duruyor.
`_GATED_FLIPS = frozenset()` boÅŸ â†’ `unstamped_gates_to_zero()` garantili no-op (Ã¶lÃ¼ plumbing).

**[EMEKLI KALINTI â€” load-bearing]:** `stoch_extreme` â€” C4 temizliÄŸini KAÃ‡IRDI. `SymbolConfig`
+ `Params` + `Params.key()` + `defaults.json` 5 preset bloÄŸu. HiÃ§bir aile okumuyor;
optimizer signal-cache'i boÅŸuna bÃ¶lÃ¼yor. â†’ C4 tamamla.

**[BAYAT DB]:** `settings.opt = {"strategy_max_combos":{"stoch_flip":28800}}` â€” **tam Ã¶lÃ¼
orphan key, OKUYAN YOK** (reader `opt_params` kullanÄ±yor, `opt` deÄŸil). Sil. Â·
`supervisor_state.verdicts["PLTR.US-24"]` â€” sÃ¼resi dolmuÅŸ CFD orphan verdict, sil.
`opt_params` blob'u artÄ±k temiz.

**[DOCS]:** AGENTS.md pytest+ruff'Ä± bitiÅŸ kapÄ±sÄ± yapÄ±yor; aÄŸaÃ§ ÅŸu an kendi kapÄ±sÄ±nÄ±
geÃ§miyor (4 test + 3 ruff). Cursor commit Ã¶ncesi yeÅŸile Ã§ekmeli.

**SÄ±ra:** TEST#1 (sizing bug karar) â†’ app.js+test bound (3 sat) â†’ ruff (2 sat) â†’ 3 Ã¶lÃ¼
indikatÃ¶r fn (~114 sat) â†’ stoch_extreme (C4 tamamla) â†’ orphan `opt` key + PLTR verdict.
Hepsi Cursor lane.

UyarÄ±: tek pencere ~18k bar son segment; GER40 M30 proxy (canlÄ± M5); apply = full WFO.

### EK3 â€” burst gates (cost_rank_max / atr_pct_min) costed sweep (02.09 20:40, salt-okur)

| snapshot | canlÄ± (cr=0,ap=0) | cr=0.3 | cr=0.5/0.7 | atr_pct etkisi |
|----------|-------------------|--------|------------|----------------|
| **GER40_M30**\* | +21.4 | **+35.5** (ap=0), +36.3 (ap=0.1) | +21.4 (inert) | apâ†‘ â†’ net_râ†“ |
| GER40_M15\* | âˆ’33.6 | âˆ’22.8 | âˆ’33.6 | hep negatif |
| **JPN225_M15** | +48.3 | **+19.8** (âˆ’28R!) | +48-49 (inert) | apâ†‘ â†’ 48â†’39â†’10 |

**Ã–lÃ§Ã¼len sonuÃ§ â€” burst iÃ§inde bile aile deÄŸil SEMBOL-spesifik:**
- **GER40 burst: `cost_rank_max=0.3`** â†’ +14R costed (M30 proxy). Ailenin M5'te taÅŸÄ±mak
  iÃ§in tasarlandÄ±ÄŸÄ± gate; GER40'Ä±n 03:15 pre-open saatlerindeki ince-range popÃ¼lasyonunu
  filtreliyor. (agent 4 E2 ile birebir.)
- **JPN225 burst: gate DEÄžÄ°ÅžTÄ°RME** â€” `cost_rank_max=0.3` yÄ±kÄ±cÄ± (âˆ’28R), yÃ¼ksek cr inert,
  `atr_pct_min` her seviyede zarar. JPN225/M15 canlÄ± zaten optimal.
- `atr_pct_min` hiÃ§bir burst'te yardÄ±mcÄ± deÄŸil.

### EK4 â€” F5: seans-saati autopsy kÄ±rÄ±lÄ±mÄ± (02.09 20:40, salt-okur)

Broker saati (naive epoch â†’ gmtime, autopsy `fill_time` bucketing). n=319.

**KÄ°TAP GENELÄ° â€” negatif saatler:** `hr 16: âˆ’17.0R / n=28 / %18 win` (tek en kÃ¶tÃ¼, bÃ¼yÃ¼k
Ã¶rnek, 4 sembolde de negatif) Â· hr 12 âˆ’8.7/n10/%0 Â· hr 13 âˆ’8.5/n12/%8 Â· hr 5 âˆ’6.1 Â· hr 6 âˆ’4.7.
**Pozitif:** hr 10 +13.1/n21 Â· hr 14 +9.4/n17 Â· hr 23 +3.3/n11/%64 Â· hr 8 +2.8/%50.

**Per-sembol (kÃ¼Ã§Ã¼k Ã¶rnek â€” WFO doÄŸrulamasÄ± ÅŸart):**
- **US30 (en gÃ¼Ã§lÃ¼):** neg hr 13/16/21/22 (+18) toplam â‰ˆ âˆ’22R; poz hr 10/14/19/23 â‰ˆ +27R.
  Bu 4-5 saati bloklamak tarihsel âˆ’3.4R â†’ **~+22R**.
- **GER40:** tek iyi saat hr 10 (+5.8); pre-open (hr 3-8, geniÅŸletilmiÅŸ 03:15 seansÄ±)
  Ã§oÄŸu negatif/mikro; hr 11/16 âˆ’3R. â†’ cash session'a (~hr 8-15) daralt + hr 16 blok.
- **NAS100:** neg hr 1/4/6/16/17; poz hr 20-22. hr 16-17 bloÄŸu âˆ’6.4R.
- **JPN225:** neg hr 6/10/12-15/19; hr 12-15 bloÄŸu âˆ’11.7R.

**SonuÃ§:** en saÄŸlam sinyal `hr 16` kitap-geneli (n=28, âˆ’17R). Konservatif hamle: **hr 16
kitap-geneli blok + GER40 geniÅŸletilmiÅŸ 03:15 pre-open seansÄ±nÄ± kaldÄ±r** (F-E5). Ä°nce
per-sembol saat blacklist'i curve-fit riski â€” WFO'da doÄŸrula. `hour_risk_scales` kancasÄ±
zaten var (supervisor `bad_hour_min_trades=80` bu frekansta atÄ±l â€” eÅŸiÄŸi ~6-8'e Ã§ek).

### EK5 â€” Disabled sembol reopen tablosu (02.09 20:52, salt-okur â€” OPERATÃ–R kararÄ±)

Costed holdout last-seg, canlÄ±-benzeri config + en iyi adx_min/trail_step.

| sembol | aile/TF | baseline costed | en iyi adx_min | en iyi trail_step |
|--------|---------|-----------------|----------------|-------------------|
| **GOLD-PERP** | mtf_pullback/M30 | **+114.3** (C1 run) | â€” | â€” |
| **XAUUSD** | burst/M15 | **+83.4** | adx=20 â†’ **+94.6** (exp .223) | step=1.0 â†’ +83 |
| **BTCUSD** | burst/M30 | +58.5 | adx=15 â†’ +60.6 (exp .205) | step=2.2 |
| SpotBrent | burst/M30 & M15 | âˆ’27 / âˆ’18 | âˆ’27 / âˆ’15 | âˆ’23 / âˆ’24 |

**SonuÃ§:** GOLD-PERP + XAUUSD + BTCUSD costed holdout'ta **canlÄ± 4'Ã¼n 3'Ã¼nden gÃ¼Ã§lÃ¼**
(JPN225 +48, NAS100 +24, US30 +18, GER40/M30 +21). SpotBrent her TF costed zararda â†’
disabled kalsÄ±n. UyarÄ±: tek pencere, iyimser; canlÄ±da XAUUSD +9.8R / SpotBrent +2.1R
(kÃ¼Ã§Ã¼k Ã¶rnek). Reopen = operatÃ¶r red + full WFO.

**GOLD-PERP mtf_pullback/M30 detay (20:56 sweep):** baseline (adx_min=0, sl 1.5,
trail 3.0/1.8) = **+114.3R / exp +0.219 / PF 1.35 / n=523**. adx_min: **0 en iyi**
(15â†’+104.7, 20â†’+61.9) â€” NAS100 mtf_pullback'in adx_min=15'ten faydalanmasÄ±nÄ±n TERSÄ°.
â†’ desen "aile-spesifik" deÄŸil **enstrÃ¼man+aile**: index yapÄ±-giriÅŸ aileleri ADX
floor'dan fayda gÃ¶rÃ¼yor, commodity (GOLD) gÃ¶rmÃ¼yor. trail_step 1.6 marjinal en iyi
(+115.8), canlÄ± 1.8 zaten yakÄ±n-optimal. **GOLD-PERP en temiz reopen adayÄ± â€” param
ayarÄ± gerekmiyor.**

---


### EK16 â€” PER-SEMBOL BEST-CONFIG SWEEP (03.09 00:14) â€” US30/GER40 YANLIS AILEDE, SpotBrent DUZELIYOR

~400 costed replay, sabit burst/channel base Ã— adx{0,15} Ã— step{0.8,1.6,2.5} Ã— cost_rank{0,0.3,0.5} Ã— close_pct{0.7,0.8,0.9} / chan_lookback{40,60,100}. Tek-pencere, curve-fit riski var -> WFO ADAY tohumu, apply degeri DEGIL.

| sembol | CANLI (aile / costed) | BEST-FOUND | best costed | fark |
|--------|------------------------|------------|-------------|------|
| **US30** | channel_break/M30 adx15 step0.8 / **+42** | **burst** adx0 step0.8 cr0.5 cp0.7 | **+113** | **+71R** aile degisimi |
| **GER40** | channel_break/M30 adx15 / **+8** | **burst** adx0 step2.5 cr0.3 cp0.7 | **+58** | **+50R** aile degisimi |
| **SpotBrent** | burst/M30 adx0 step1.8 cr0.5 / **âˆ’27** | burst adx0 **step2.5 cr0** cp0.7 | **+50** | **+77R** -> POZITIF FLIP (roc_pace gerekmez) |
| NAS100 | burst/M30 adx0 step2.5 cr0.7 / +46 | burst **adx15** step2.5 **cr0** cp0.7 | +72 | +26R (adx15 iyi ama cr0.7 zarar) |
| JPN225 | burst/M15 adx0 step2.5 / +61 | burst adx0 step2.5 **cr0.5 cp0.9** | +66 | +5R (marjinal) |
| BTCUSD | burst/M30 adx0 step2.5 cr0.7 / ~+62 | burst adx0 step2.5 **cr0.3 cp0.9** | +56 (exp .31) | cp0.9+cr0.3 |
| XAUUSD | burst/M15 tuned / **~+91** | sweep base +42 | +42 | CANLI DAHA IYI -> sabit tut |
| GOLD-PERP | (add adayi) | **channel_break** adx0 step2.5 chan60 | +102 (exp .345, pf 1.52) | burst +98 de var |

**Olculen desen:** kitabin neredeyse tamami **burst + GENIS trail_step (2.5)** istiyor.
adx sembol-spesifik (NAS100 15, digerleri 0). cost_rank DUSUK (0-0.3; 0.5-0.7 cogunlukla
zarar). **US30 ve GER40 su an channel_break'te = her biri +50-70R masada.** SpotBrent
"calismiyor" degil -- step 1.8 + cr 0.5 yanlisti; step 2.5 + cr 0 ile +50R.

**Cursor'a:** US30 / GER40 / SpotBrent'i **burst/M30** ile WFO'la (channel_break yerine).
NAS100 cr 0.7->0, adx15 test. XAUUSD sabit. GOLD-PERP add = channel_break veya burst.
Curve-fit uyarisi: bu tablo tek-pencere; WFO plato + regime-spread + DSR ile teyit et.



### EK17 â€” ROBUSTLUK KONTROLU (03.09 00:22) â€” EK16'nÄ±n US30/SpotBrent Ã–NERÄ°LERÄ° CURVE-FIT, GERÄ° ALINIYOR

EK16 tek-pencere costed (yalnÄ±z son segment). 6 alt-pencereye bÃ¶ldÃ¼m (her ~15k bar,
rolling-OOS proxy). Research #2 kriteri: config â‰¥4/6 pencerede pozitif olmalÄ±.

| config | 6 alt-pencere net_r | pozitif | verdict |
|--------|---------------------|---------|---------|
| **US30 burst "BEST"** (EK16 +113) | +46 +30 **âˆ’61 âˆ’59 âˆ’35** +93 | 3/6 | **MIXED â€” +113 TAMAMEN son pencere. REJÄ°M ARTEFAKTI.** |
| **US30 channel_break CANLI** | âˆ’5 +14 +6 +1 +6 +57 | 5/6 | **ROBUST â€” mevcut config zaten doÄŸru.** |
| GER40 burst "BEST" (EK16 +58) | âˆ’14 âˆ’30 âˆ’15 +4 +61 +31 | 3/6 | MIXED â€” ilk yarÄ± negatif, rejim-baÄŸÄ±mlÄ± |
| **SpotBrent burst "BEST"** (EK16 +50 "flip") | **âˆ’230 âˆ’124 âˆ’9 âˆ’93** +14 +20 | 2/6 | **FRAGILE â€” "flip" son 2 pencere ÅŸansÄ±. burst SpotBrent'i Ã‡Ã–ZMÃœYOR.** |
| SpotBrent burst LIVE-ish | âˆ’173 âˆ’83 âˆ’17 âˆ’83 +13 âˆ’16 | 1/6 | FRAGILE |
| **NAS100 burst adx15 cr0** | âˆ’15 +11 +1 +25 +90 +56 | 5/6 | **ROBUST (+168R) â€” bu GERÃ‡EK.** |

**DÃœZELTME (EK16 geri alÄ±nÄ±yor):**
- **US30 â†’ burst YAPMA.** +113 son-pencere rejim artefaktÄ±ydÄ±; burst US30 3/6 pencerede
  derin negatif. **Mevcut channel_break config ROBUST (5/6). US30'a DOKUNMA.**
- **SpotBrent burst'te Ã‡ALIÅžMIYOR.** "+50R flip" 6'da 2 ÅŸanslÄ± pencere; 4/6 pencere
  âˆ’9..âˆ’230R. SpotBrent â†’ `roc_pace` (TSMOM) ADAYI ya da disabled kalsÄ±n. burst DEÄžÄ°L.
- **GER40 burst: temkinli** (3/6). Son rejim lehte ama ilk yarÄ± negatif â€” WFO'nun
  regime-spread gate'i karar versin, tek-pencere "aday" yeterli deÄŸil.
- **NAS100 burst + adx_min=15 + cost_rank_max=0: ROBUST (5/6), +168R.** Bu uygulanabilir.
  cr 0.7â†’0 + adx 0â†’15.

**Ders:** EK2-EK16 tek-pencere costed sweep'lerim multiple-comparisons tuzaÄŸÄ±. "En iyi"
diye bulduÄŸum Ã§oÄŸu config son rejime fit olmuÅŸ. **Robustluk kontrolÃ¼ (â‰¥4/6 alt-pencere)
apply-Ã¶ncesi ZORUNLU** (research #2, P1). Bundan sonra sweep sonuÃ§larÄ±nÄ± sub-window ile
teyit ediyorum.



### EK18 â€” ROBUSTLUK: kalan semboller (03.09 00:35) â€” KÄ°TAP Ã‡OÄžUNLUKLA ZATEN Ä°YÄ°

| config | 6 alt-pencere | pozitif | verdict |
|--------|--------------|---------|---------|
| **XAUUSD CANLI** | +14 +113 +68 +44 +49 +48 | **6/6** | **ROBUST +335R â€” dokunma** |
| **JPN225 CANLI** | +4 +5 +11 âˆ’27 +27 +60 | **5/6** | **ROBUST +79R â€” dokunma** |
| JPN225 +cr0.5+cp0.9 | ~aynÄ± | 5/6 | +2R marjinal â€” deÄŸiÅŸmeye deÄŸmez |
| **BTCUSD CANLI** | +36 +2 +13 +47 +20 +42 | **6/6** | **ROBUST +161R â€” dokunma** |
| BTCUSD cr0.3+cp0.9 | 6/6 ama +101R | 6/6 | canlÄ±dan KÃ–TÃœ â€” deÄŸiÅŸtirme |
| GOLD channel_break | +31 +23 âˆ’27 âˆ’15 +62 +65 | 4/6 | ROBUST +140R |
| GOLD burst | +29 âˆ’4 +27 âˆ’38 +86 +75 | 4/6 | ROBUST +175R |
| **GOLD mtf_pullback (as-is)** | +18 âˆ’2 +43 +16 +76 +104 | **5/6** | **ROBUST +255R â€” GOLD iÃ§in EN Ä°YÄ° + en tutarlÄ±** |

**Robust-doÄŸrulanmÄ±ÅŸ NÄ°HAÄ° tablo (EK17 + EK18):**

| sembol | verdict | AKSIYON |
|--------|---------|---------|
| **NAS100** | burst adx15 cr0 = ROBUST 5/6 +168R | **UYGULA: cost_rank_max 0.7â†’0, adx_min 0â†’15** |
| US30 | channel_break CANLI = ROBUST 5/6 | **dokunma** (EK16 "burst" curve-fitti) |
| GER40 | burst 3/6 MIXED | WFO regime-gate karar versin |
| JPN225 | CANLI = ROBUST 5/6 | dokunma |
| XAUUSD | CANLI = ROBUST 6/6 +335R | dokunma |
| BTCUSD | CANLI = ROBUST 6/6 +161R | dokunma |
| SpotBrent | burst FRAGILE 2/6 | roc_pace (#2 aile) VEYA disabled |
| GOLD-PERP | mtf_pullback ROBUST 5/6 +255R | add = **mtf_pullback** (aile aramada KALMALI) |

**Ã–lÃ§Ã¼len sonuÃ§:** Cursor'un apply'larÄ± oturdu; kitap **Ã§oÄŸunlukla zaten robust config'te**.
"TÃ¼m sembolleri en iyi hale getir" cevabÄ± EK16'nÄ±n sandÄ±ÄŸÄ±ndan Ã§ok DAR:
- Tek net config deÄŸiÅŸikliÄŸi: **NAS100** (cr 0.7â†’0, adx 0â†’15).
- 4 sembol zaten robust â€” bÄ±rak.
- GER40 â†’ WFO. SpotBrent â†’ roc_pace. GOLD-PERP add â†’ mtf_pullback.
- **mtf_pullback aramadan DÃœÅžÃœRÃœLMEMELÄ°** (GOLD-PERP'in tek robust ailesi).
AsÄ±l kalan alpha config tuning'de deÄŸil: **sizing/exit bug fix'leri** (C1-shakeout, T1-minlot,
3 exit HIGH) downside'Ä± upside tuning'den daha Ã§ok etkiliyor.


## 02.09 19:35 â€” Claude Aâ€“Z hard/stres tarama (Ã¶lÃ§Ã¼mlÃ¼, kod YOK)

OperatÃ¶r: API+web+her ÅŸey, Ã§alÄ±ÅŸmayan/Ã¶lÃ¼/bayat/emekli/okunmayan ne varsa ayrÄ± ayrÄ±;
kalkan Ã¶zelliklerden kaynaklÄ± sorunlar; kaÃ§an iÅŸlem/kÃ¢r tek tek; Ã¶lÃ§Ã¼mlÃ¼, Ã¶neri deÄŸil;
bulgular Cursor'a â†’ doÄŸrulayÄ±p plan. HiÃ§bir ÅŸey PATCH edilmedi, arama/flatten/capture/
restart/commit YOK. HEAD `4528b40`. CanlÄ±: 1 ticket (NAS100), marj ~%6.5/70, kasa ~$225.

**Ã‡alÄ±ÅŸma aÄŸacÄ± temiz DEÄžÄ°L:** `micofx/engine.py` (+18) ve `micofx/execution.py` (+87)
commit'siz WIP; untracked `scripts/start_bridge_daemon.ps1`, `tests/test_note_fill_
repairs_poisoned_sl.py`. BazÄ± test kÄ±rÄ±klarÄ± bu WIP'ten olabilir (F-T3).

### 1) Optimization Summary

* **SaÄŸlÄ±k:** Test paketi KIRMIZI â€” `4528b40`'ta **19 fail / 2720 pass** (+2 ruff
  import-sort, test dosyalarÄ±). CanlÄ± defter **âˆ’41.2 R / âˆ’$826.60 / 319 iÅŸlem**
  (14 gÃ¼n), tÃ¼m zarar `sl` kovasÄ±nda (**âˆ’156 R / 166 iÅŸlem / avgR âˆ’0.94**). Cost-free
  mod, "her cost-free apply'Ä±n yanÄ±nda maliyetli sayÄ±" gÃ¼venlik aÄŸÄ±nÄ± (72cbfb1/fba488b)
  sessizce kapatmÄ±ÅŸ â†’ hangi canlÄ± config'in paper-pozitif/charged-negatif olduÄŸu artÄ±k
  Ã–LÃ‡ÃœLMÃœYOR. Auto-pilot 17 gÃ¼nlÃ¼k sÄ±fÄ±rlanmamÄ±ÅŸ `entry_blocks` sayacÄ±na gÃ¶re karar
  veriyor (bayat sinyal).
* **En yÃ¼ksek etkili 3:** (1) F-D1 cost-free apply maliyet damgasÄ±nÄ± + costed-negatif
  reddini kapatÄ±yor (3 test kÄ±rÄ±k, holdoutâ†”canlÄ± ayrÄ±mÄ±nÄ±n kÃ¶r noktasÄ±). (2) F-E1/E2
  yapÄ±sal sinyal kaybÄ±: `risk_sembol_limiti` 259 + `risk_ters_yon` 223 sinyal-barÄ±
  dÃ¼ÅŸÃ¼yor; fill oranlarÄ± US30 %22, GER40 %29. (3) F-D3 `entry_blocks` 2026-08-16'dan
  beri sÄ±fÄ±rlanmÄ±yor â†’ auto-pilot "SPREAD US30 kalibre" Ã¶nerisini kapalÄ± gate + bayat
  sayaÃ§ Ã¼zerine tekrar tekrar Ã¼retiyor.
* **DeÄŸiÅŸmezse en bÃ¼yÃ¼k risk:** kÄ±rmÄ±zÄ± test paketi = regresyon dedektÃ¶rÃ¼ yok; canlÄ±
  âˆ’R Ã¼retmeye devam ederken (avgR âˆ’0.13) devre kesici kapalÄ± (`daily_loss_pct=0`),
  concurrent risk %46, marj tavanÄ± %78, ~$225 hesap 1:500. KayÄ±p motoru frensiz.

### 2) Findings (Ã¶ncelik sÄ±rasÄ±)

Her bulgu Ã¶lÃ§Ã¼mlÃ¼. "Removal Safety" ve "Reuse Scope" verildi. KanÄ±t = dosya:satÄ±r
veya DB anahtarÄ± + sayÄ±.

---

**F-D1 â€” Cost-free mod maliyetli-holdout damgasÄ±nÄ± ve costed-negatif reddini kapatÄ±yor**
* Kategori: Reliability / Cost Â· Severity: **Critical**
* Etki: holdoutâ†”canlÄ± ayrÄ±mÄ± Ã¶lÃ§Ã¼lemez; `--force` ile charged-negatif config canlÄ±ya
  geÃ§ebilir.
* KanÄ±t: `micofx/optimizer.py` `apply()` (~2093â€“2105) â€” `charging = bool(store.system
  and store.system.charge_costs)`; `if detail is not None and charging:` bloÄŸu costed
  eval + `costed_negative` reddini sarÄ±yor. `charge_costs=False` (DB `system`) â†’ blok
  hiÃ§ Ã§alÄ±ÅŸmÄ±yor â†’ `opt_summary` iÃ§inde `holdout_costed` YOK, `costed_negative` YOK.
  KÄ±rÄ±k testler: `tests/test_holdout_costed_on_apply.py::test_negative_costed_holdout_
  is_not_applied` (ok=True bekleniyordu False), `::test_force_still_applies_a_costed_
  negative_candidate` (KeyError `costed_negative`), `::test_positive_costed_holdout_is_
  stamped_without_the_flag` (KeyError `holdout_costed`).
* Neden verimsiz: 72cbfb1 "An applied configuration carries its own held-out record" +
  fba488b "Put a charged number beside every cost-free apply" bilerek eklenmiÅŸti; bu
  gate onu geri alÄ±yor. CanlÄ± 4 config'in kaÃ§Ä±nÄ±n paper-pozitif/charged-negatif olduÄŸu
  bilinmiyor â€” tam da âˆ’41R/+90R ayrÄ±mÄ±nÄ± yakalayacak enstrÃ¼man.
* Removal Safety: **Needs Verification** (bilinÃ§li mi, regresyon mu â€” Cursor).
* Reuse Scope: service-wide (optimizer apply + auto-pilot raporu + supervisor).
* Beklenen etki: charged sayÄ± geri gelirse costed replay ile 4 aile yeniden sÄ±ralanÄ±r; (arsiv)
  M5/M15 burst seÃ§imlerinin ~0.1â€“0.3R/iÅŸlem fantom edge taÅŸÄ±dÄ±ÄŸÄ± hipotezi Ã¶lÃ§Ã¼lebilir.

**F-D2 â€” Fill/trade log satÄ±rÄ±nda canlÄ± maliyet payÄ± boÅŸ**
* Kategori: Reliability Â· Severity: Low
* KanÄ±t: `tests/test_fill_trade_line_carries_magic.py::test_the_fill_trade_line_names_
  magic_and_live_cost_share` â†’ `cost_bit = ""`. Cost-free mod maliyet payÄ±nÄ± kaldÄ±rÄ±yor.
* Removal Safety: Likely Safe (kozmetik) ama F-D1 ile aynÄ± kÃ¶k: "maliyet gÃ¶rÃ¼nÃ¼rlÃ¼ÄŸÃ¼"
  toptan kapanmÄ±ÅŸ.
* Reuse Scope: module (fill logging).

**F-D3 â€” `entry_blocks` sayaÃ§larÄ± 17 gÃ¼ndÃ¼r sÄ±fÄ±rlanmÄ±yor; auto-pilot bayat sayÄ±ya gÃ¶re karar veriyor**
* Kategori: DB / Reliability Â· Severity: **High**
* KanÄ±t: DB `entry_blocks_since = 1786905256` = 2026-08-16 18:34 (16.9 gÃ¼n). Cost-free
  mod ~5 commit Ã¶nce (ced7e08). `entry_blocks.US30.primary.signals.spread = 144`,
  `SpotBrent...spread = 213` â€” cost-free Ã–NCESÄ° dÃ¶neme ait. Enabled index isimlerde
  `max_spread_atr = 0.0` (kapalÄ±). Yine de `scripts/income_dev_loop.py:196-223`
  `spread_recovery_actions` bu kÃ¼mÃ¼latif sayaÃ§tan "SPREAD US30/JPN225/GER40 kalibre"
  Ã¼retiyor; `cursor/FOR_CLAUDE.md` her tick tekrarlÄ±yor.
* Neden verimsiz: karar sinyali gÃ¼rÃ¼ltÃ¼lÃ¼/geÃ§miÅŸe dÃ¶nÃ¼k; auto-pilot no-op iÅŸ Ã¶neriyor,
  `apply_spread_calibration` charge_costs=false'ta zaten atlÄ±yor â†’ sonsuz "atlandÄ±" logu.
* Removal Safety: Needs Verification (sayaÃ§ rotasyonu / pencere ekle).
* Reuse Scope: service-wide (auto-pilot + panel entry-blocks analizi).

**F-D4 â€” 11 Ã¶lÃ¼ `Params`/`SymbolConfig` alanÄ± (emekli aileler)**
* Kategori: Memory / Maintainability (Dead Code) Â· Severity: Low
* KanÄ±t: `micofx/strategy.py:58-82` ve `micofx/models.py:120-141` â€” `t3_fast,
  t3_slow_mult, t3_fast_vf, t3_accel_min, st_period, st_mult, stoch_k_period,
  stoch_k_smooth, stoch_d_smooth, psar_af_step, psar_af_max`. `opt_fields_read`
  Ã§Ä±ktÄ±sÄ± (Ã¶lÃ§Ã¼ldÃ¼) 4 canlÄ± aile iÃ§in bunlarÄ±n HÄ°Ã‡BÄ°RÄ°NÄ° iÃ§ermiyor. HÃ¢lÃ¢:
  `Params.key()` tuple'Ä±nda (satÄ±r 145-150) ve `required_bars()` iÃ§inde
  (satÄ±r 770-773: `int(p.t3_fast*max(1.2,p.t3_slow_mult))*20`, stoch_k toplamÄ±*8)
  her Ã§aÄŸrÄ±da hesaplanÄ±yor.
* Neden verimsiz: her `required_bars` Ã§aÄŸrÄ±sÄ±nda Ã¶lÃ¼ aritmetik; `key()` tuple'Ä± 11
  eleman ÅŸiÅŸik (sinyal cache anahtarÄ±). BaÄŸlanmÄ±yor ama drift riski + kafa karÄ±ÅŸÄ±klÄ±ÄŸÄ±.
* Removal Safety: **Likely Safe** â€” canlÄ± aile okumuyor; `from_config` geriye-uyumlu
  kalÄ±r (eksik alan default). DB payload'da varsa yok sayÄ±lÄ±r.
* Reuse Scope: module (strategy + models + optimizer grid).

**F-D5 â€” DB `opt_params.strategies` emekli aileleri listeliyor + `strategy_max_combos.stoch_flip`**
* Kategori: DB / Cost (Dead Config) Â· Severity: Medium
* KanÄ±t: DB `opt_params.strategies = ['mtf_pullback','burst','dual_t3','t3_flip',
  'stoch_flip','parabolic_flip','ichimoku','channel_break']` â€” 4'Ã¼ emekli (AGENTS.md
  "Leftover DB names fail closed"). DB `opt = {"strategy_max_combos":{"stoch_flip":
  28800}}`. `micofx/optimizer.py:109-110,168` stoch_flip'i Ã¶zel-kÄ±lÄ±f yapÄ±yor;
  ledger'a gÃ¶re `stoch_flip` 28800 â‰ˆ 3.08 M kombinasyon duvarÄ±nÄ±n 2.07 M'i.
* Neden verimsiz: arama bÃ¼tÃ§esinin bÃ¼yÃ¼k kÄ±smÄ± Ã–LÃœ bir aileyi modellemeye ayrÄ±lmÄ±ÅŸ
  (fail-closed olsa da combo tahsisi/coverage_budget hesabÄ± onu sayÄ±yor).
* Removal Safety: Needs Verification (DB yazÄ±mÄ± panel/HTTP 400 â€” `opt_params` write
  yolu AGENTS.md'e gÃ¶re kÄ±sÄ±tlÄ±; nasÄ±l temizleneceÄŸi Cursor).
* Reuse Scope: service-wide (optimizer combo budget).

**F-D6 â€” `ichimoku` artÄ±k htf_factor/adx okuyor ama 4 test eski "unread" halini iddia ediyor**
* Kategori: Maintainability / Reliability Â· Severity: Medium
* KanÄ±t: `_ichimoku` â†’ `_trend_gate(cache,p)` (`strategy.py:579`) `p.htf_factor`/
  `p.htf_mode` okuyor; `_common`â†’`_regime` adx okuyor. `opt_fields_read('ichimoku')`
  (Ã¶lÃ§Ã¼ldÃ¼) = `{adx_max, adx_min, atr_pct_min, htf_factor, min_body_ratio, ...}`.
  KÄ±rÄ±k: `tests/test_kivanc_combo_families.py::test_ichimoku_is_unread_flip_shaped`,
  `tests/test_required_bars_ignores_unread_htf.py::test_unread_htf_factor_does_not_
  inflate_required_bars`, ve `test_kivanc_combo_families` htf_factor varyantÄ±. DeÄŸiÅŸim
  commit `715c32e` "Strengthen ichimoku and pullback families". `absent_regime_gates_
  to_zero` guard'Ä± artÄ±k ichimoku'yu da kapsÄ±yor (bkz. tick-1 audit).
* Removal Safety: N/A â€” testler koda gÃ¶re gÃ¼ncellenmeli (davranÄ±ÅŸ bilinÃ§li gÃ¶rÃ¼nÃ¼yor).
* Reuse Scope: module (strategy + testler + `required_bars`).

**F-D7 â€” `test_enable_requires_optimised` x8: `_Engine` stub'Ä±nda `.supervisor` yok**
* Kategori: Reliability Â· Severity: Medium
* KanÄ±t: 8 test `AttributeError: '_Engine' object has no attribute 'supervisor'`.
  Traceback â†’ `micofx/web/app.py:705` `_on_symbol_newly_enabled` sembol enable
  edilince `engine.supervisor`'Ä± koÅŸulsuz dereference ediyor. Testin sahte Engine'i
  bu attr'Ä± taÅŸÄ±mÄ±yor.
* Neden Ã¶nemli: canlÄ± Engine her zaman `.supervisor` taÅŸÄ±yorsa sadece bayat stub;
  taÅŸÄ±madÄ±ÄŸÄ± bir yol varsa enable sÄ±rasÄ±nda AttributeError (latent).
* Removal Safety: Needs Verification (canlÄ± Engine invariant'Ä± â€” Cursor doÄŸrulasÄ±n:
  `getattr(engine,"supervisor",None)` guard mÄ±, yoksa stub mÄ± dÃ¼zelecek).
* Reuse Scope: module (web enable path + testler).

**F-D8 â€” `kasa_auto` testleri x2: growth-mode hedefleri testle Ã§eliÅŸiyor**
* Kategori: Reliability / Cost Â· Severity: **High** (canlÄ± risk parametrelerini sÃ¼rÃ¼yor)
* KanÄ±t: `tests/test_kasa_auto.py:18` `assert 0.92 == 0.85` (lot_multiplier),
  `:44` `assert 78.0 == 68` (max_margin_usage_pct). Commit `25e6674` "kasa growth mode"
  hedefleri deÄŸiÅŸtirdi, test gÃ¼ncellenmedi. `scripts/kasa_auto.py` canlÄ±ya
  `lot_multiplier` + `max_margin_usage_pct` PATCH'liyor (auto-pilot her tick).
* Neden Ã¶nemli: test ya bayat (bilinÃ§li growth) ya da growth hedefleri fazla agresif
  ve test kanaryasÄ±. Åžu an DB: lot_multiplier 0.92, margin %78 â€” test 0.85 / %68 diyor.
* Removal Safety: Needs Verification â€” operatÃ¶r + Cursor: growth hedefleri onaylÄ± mÄ±?
* Reuse Scope: service-wide (kasa_auto canlÄ± PATCH + auto-pilot).

**F-D9 â€” `execution_samples` telemetrisi Ã¶lÃ¼/bozuk**
* Kategori: Reliability / Observability Â· Severity: Medium
* KanÄ±t: DB `execution_samples` = 17 gÃ¼nde 7 satÄ±r; en az biri dÃ¼z `str` (dict deÄŸil â€”
  `AttributeError: 'str' object has no attribute 'get'` okuma denemesinde). CanlÄ±
  slippage Ã¶lÃ§Ã¼lemiyor â†’ "backtestâ†”canlÄ± slippage farkÄ±" (literatÃ¼r #1 sebep) sayÄ±yla
  gÃ¶sterilemez.
* Removal Safety: Needs Verification (yazÄ±m yolu bozuk mu, yoksa kullanÄ±lmÄ±yor mu).
* Reuse Scope: module (execution + panel).

**F-D10 â€” `supervisor_state` freshness damgasÄ± yok**
* Kategori: Reliability Â· Severity: Low
* KanÄ±t: DB `supervisor_state` anahtarlarÄ± = `['verdicts','risk_scale']`, `updated_at`
  yok. NAS100 net âˆ’36.03 verdict'inin ne kadar gÃ¼ncel olduÄŸu bilinemez.
* Reuse Scope: module (supervisor + auto-pilot ranked tablo).

---

**F-E1 â€” `risk_sembol_limiti` (1 ticket/isim) 259 sinyal-barÄ± dÃ¼ÅŸÃ¼rÃ¼yor**
* Kategori: Algorithm / Cost (kaÃ§an iÅŸlem) Â· Severity: **High**
* KanÄ±t: DB `entry_block_events` (son 1472): `risk_sembol_limiti` 259 â€”
  GER40 82, US30 83, JPN225 54, NAS100 22 (DB `entry_blocks.<sym>.primary.signals`).
  Aile pozisyon aÃ§Ä±kken 2./3. sinyali Ã¼retiyor, hepsi atÄ±lÄ±yor.
* Neden verimsiz: yapÄ±sal sinyal kaybÄ±; en Ã§ok GER40/US30. AGENTS.md "Live count is
  1 ticket per name" bilinÃ§li â€” ama pyramiding/re-entry hiÃ§ Ã¶lÃ§Ã¼lmemiÅŸ.
* KarÅŸÄ±-olgu (Ã¶lÃ§Ã¼lmeli, Faz-1): cap 2'ye Ã§Ä±karsa GER40+82 / US30+83 sinyal-barÄ±
  uygun olur; MEVCUT canlÄ± beklenti avgR âˆ’0.13 / win %34 ile bu **negatif EV** â€”
  rejim filtresi (F-E4) ile eÅŸleÅŸmeden tek baÅŸÄ±na aÃ§ma. SayÄ±: 259 Ã— (âˆ’0.13 R) â‰ˆ
  âˆ’34 R "kaÃ§Ä±rÄ±lan" ama negatif, yani ÅŸu an cap KORUYUCU.
* Removal Safety: Needs Verification â€” costed + regime-filtered replay olmadan dokunma.
* Reuse Scope: service-wide (risk.py + engine entry gate).

**F-E2 â€” `risk_ters_yon` (ters yÃ¶n gate) 223 sinyal-barÄ± dÃ¼ÅŸÃ¼rÃ¼yor; ters sinyal Ã§Ä±kÄ±ÅŸa Ã§evrilmiyor**
* Kategori: Algorithm / Cost (kaybedilen kÃ¢r) Â· Severity: **High**
* KanÄ±t: `entry_block_events` `risk_ters_yon` 223 â€” US30 77, JPN225 56, SpotBrent 48,
  GER40 23. AÃ§Ä±k long dururken short sinyal (veya tersi) â†’ **atÄ±lÄ±yor**, pozisyon
  kapatma/flip iÃ§in kullanÄ±lmÄ±yor.
* Neden verimsiz: `sl` kovasÄ± 166 tam-stop / avgR âˆ’0.94 = tÃ¼m zarar. Bu 166'nÄ±n bir
  kÄ±smÄ± stop yemeden Ã¶nce ters sinyal Ã¼retmiÅŸ olabilir (erken Ã§Ä±kÄ±ÅŸ fÄ±rsatÄ±).
* KarÅŸÄ±-olgu (Ã¶lÃ§Ã¼lmeli, Faz-1): `entry_block_events(risk_ters_yon)` â†’ `trade_
  autopsies` join (symbol + [fill_time, exit_time] penceresi). KaÃ§ `sl` Ã§Ä±kÄ±ÅŸÄ±,
  stoptan Ã¶nce ters sinyal gÃ¶rdÃ¼? Her biri ~(mfe_r âˆ’ (âˆ’1)) R kurtarma potansiyeli.
  Kaba tavan: 166 sl Ã— ort. left_on_table yok ama mae_r ~0.9 â†’ ters-sinyal-Ã§Ä±kÄ±ÅŸ
  bu iÅŸlemleri ~âˆ’1R yerine ~breakeven'a Ã§ekebilseydi â‰ˆ +80â€“120 R aralÄ±ÄŸÄ± (ÃœST SINIR,
  doÄŸrulanacak).
* Removal Safety: Needs Verification â€” "ters sinyalde flat" yeni davranÄ±ÅŸ; costed
  backtest'te Ã¶lÃ§, exit modelini deÄŸiÅŸtirmeden (sadece erken Ã§Ä±kÄ±ÅŸ).
* Reuse Scope: service-wide (engine signal handling + backtest simulate).
* **Ã–LÃ‡ÃœM 02.09 19:40 (join yapÄ±ldÄ±, tez ZAYIFLADI):** 223 `risk_ters_yon` olayÄ±nÄ±n
  131'i bir aÃ§Ä±k-iÅŸlem penceresine dÃ¼ÅŸÃ¼yor. Bu 131'in Ã§Ä±kÄ±ÅŸÄ±: **`trail` 101 (kÃ¢rlÄ±!)**,
  `flatten` 6, `sl` yalnÄ±z 24. Yani ters sinyallerin Ã§oÄŸu, sonradan trail ile kÃ¢ra
  giden iÅŸlemler sÄ±rasÄ±nda geldi â€” "ters sinyalde kapat" 101 kazananÄ± keserdi.
  Ters sinyal gÃ¶rÃ¼p KÃ–TÃœ Ã§Ä±kan farklÄ± iÅŸlem sayÄ±sÄ± **32** (realised âˆ’24.7 R / âˆ’$249),
  yoÄŸunluk JPN225 (14, âˆ’11 R) + US30 (9, âˆ’9 R). Kurtarma tahmini **dÃ¼ÅŸÃ¼k ~+9 R /
  yÃ¼ksek ~+23 R**, medyan 1 ters sinyal/iÅŸlem. **SonuÃ§:** blanket "ters sinyalde flat"
  net NEGATÄ°F/marjinal. KoÅŸullu varyant (yalnÄ±z iÅŸlem >0.5R zararda + ters sinyal,
  JPN225/US30 alt kÃ¼mesi) curve-fit riski â€” costed backtest olmadan canlÄ±ya alÄ±nmaz.
  Severity **High -> Medium**.

**F-E3 â€” Fill oranlarÄ±: US30 %22, GER40 %29, JPN225 %33; SpotBrent %6**
* Kategori: Cost (kaÃ§an iÅŸlem) Â· Severity: Medium (bilgi + F-E1/E2/D3'e baÄŸlÄ±)
* KanÄ±t: DB `entry_blocks.<sym>.primary.signals` `acildi` / toplam:
  GER40 56/191 (%29), JPN225 91/280 (%33), NAS100 62/120 (%52), US30 98/450 (%22),
  XAUUSD 45/70 (%64), SpotBrent 19/335 (%6). BlokÃ¶r daÄŸÄ±lÄ±mÄ± F-E1 (sembol dolu) +
  F-E2 (ters yÃ¶n) + spread (F-D3 bayat) + `bar_bosluk` (M5/M15 gece boÅŸluÄŸu, 138).
* Removal Safety: N/A (Ã¶lÃ§Ã¼m).
* Reuse Scope: service-wide.

**F-E4 â€” Rejim filtresi tamamen kapalÄ± (tÃ¼m canlÄ± isimlerde adx_min=adx_max=0)**
* Kategori: Algorithm Â· Severity: **High**
* KanÄ±t: DB symbols payload â€” GER40/JPN225/NAS100/US30 hepsinde `adx_min=0`,
  `adx_max=0`. `_regime()` (`strategy.py:407-413`) her iki dal da no-op â†’ filtre yok.
  Grid'de `adx_min [0,15,20]` zaten var (`config/defaults.json`). LiteratÃ¼r: ADX
  filtre (eÅŸik 20/25), sinyal deÄŸil.
* KarÅŸÄ±-olgu (Ã¶lÃ§Ã¼lmeli): per-sembol `adx_min>0` costed holdout aramasÄ±. `sl` kovasÄ±
  166 iÅŸlem Ã§oÄŸunlukla chop giriÅŸi hipotezi â€” ADXâ‰¥20 filtresi bunlarÄ±n X'ini eler.
* Removal Safety: N/A (ekleme deÄŸil, mevcut ekseni aramak).
* Reuse Scope: service-wide (optimizer search + strategy compute).

**F-E5 â€” GER40 seansÄ± 03:15â€“22:59'a geniÅŸletilmiÅŸ (defaults 10:00)**
* Kategori: Cost Â· Severity: Medium
* KanÄ±t: DB `symbols.GER40.sessions = [{start:"03:15", end:"22:59"}]`; `config/
  defaults.json` index preset 16:30â€“22:55, GER40 override 10:00â€“22:55.
  GER40 burst/M5 canlÄ± âˆ’6.9 R, fill %29, `bar_bosluk` bloklu.
* Neden verimsiz: burst/M5 nakit-aÃ§Ä±lÄ±ÅŸ Ã¶ncesi ince saatlerde ateÅŸliyor; spread geniÅŸ,
  hacim dÃ¼ÅŸÃ¼k â€” literatÃ¼rde en pahalÄ±/R dilim.
* Removal Safety: Needs Verification (seans daraltma canlÄ± param â€” operatÃ¶r/Cursor).
* Reuse Scope: symbol config.

**F-E6 â€” `lot` bloÄŸu: 38 sinyal-barÄ± undersize (JPN225 23)**
* Kategori: Cost Â· Severity: Low
* KanÄ±t: `entry_block_events` `lot` 38; DB `entry_blocks` signals: JPN225 23,
  US30 6, XAUUSD 6, NAS100 3. ~$225 hesap, 2% risk / SL mesafesi broker min-lot'un
  altÄ±nda â†’ iÅŸlem atlanÄ±yor. Auto-pilot "LOT engeli" alarmÄ± her tick.
* Removal Safety: N/A (hesap bÃ¼yÃ¼klÃ¼ÄŸÃ¼ fonksiyonu; kasa bÃ¼yÃ¼dÃ¼kÃ§e azalÄ±r).
* Reuse Scope: risk.py sizing.

---

**F-T1 â€” CanlÄ± performans: âˆ’41.2 R / âˆ’$826.60 / 319 iÅŸlem (14 gÃ¼n)**
* Kategori: â€” (Ã¶lÃ§Ã¼m, kÃ¶k F-D1/E2/E4) Â· Severity: **Critical**
* KanÄ±t: DB `trade_autopsies` (n=319, 2026-08-19â†’09-02): sumR âˆ’41.2, nakit âˆ’826.60,
  win %34, avgR âˆ’0.129. Cikis: `sl` n=166 avgR **âˆ’0.94** (âˆ’156 R) Â· `trail` n=100
  avgR +0.84 (+84 R) Â· `flatten` n=48 avgR +0.59 (+28 R) Â· `manuel` n=5 +2.3.
  Son 100: âˆ’25.8 R. Son 20: +1.2 R. MFE-capture (`r_realised/mfe_r`, mfeâ‰¥0.3R,
  n=218) medyan **0.00**, ort âˆ’0.41 (saÄŸlÄ±klÄ± > 0.5).
* Yorum: kitabÄ± ayakta tutan tek kova `flatten` (seans/gÃ¼n-sonu zorunlu Ã§Ä±kÄ±ÅŸ).
  `sl` kovasÄ± tÃ¼m zararÄ± yazÄ±yor â†’ sorun giriÅŸ kalitesi + tam-stop sÄ±klÄ±ÄŸÄ±, trail
  deÄŸil (trail kovasÄ± pozitif).

**F-T2 â€” En yÃ¼ksek holdout'lu iki isim canlÄ±da en Ã§ok kaybeden**
* Kategori: â€” (Ã¶lÃ§Ã¼m) Â· Severity: **High**
* KanÄ±t: canlÄ± sumR: NAS100 **âˆ’18.7**, JPN225 **âˆ’17.4**, GER40 âˆ’6.9, US30 âˆ’3.4;
  XAUUSD **+9.8** (disabled), SpotBrent +2.1 (disabled). Holdout net R: NAS100
  **+91.8**, JPN225 +68.3, XAUUSD +113.6, GER40 +53.6, US30 +37.6. Korelasyon ters.
* Yorum: holdout (cost-free, F-D1) canlÄ± geliri Ã¶ngÃ¶rmÃ¼yor. Costed replay ÅŸart.

**F-T3 â€” 19 test fail / 2 ruff hatasÄ± `4528b40`'ta + kirli Ã§alÄ±ÅŸma aÄŸacÄ±**
* Kategori: Reliability (regresyon dedektÃ¶rÃ¼ yok) Â· Severity: **High**
* KanÄ±t: `pytest -q` â†’ `19 failed, 2720 passed, 1 xfailed` (108 s). Gruplar:
  F-D1 (3), F-D6 (3), F-D7 (8), F-D8 (2), `test_fill_trade_line_carries_magic` (1,
  F-D2), `test_original_sl_survives_restart` (1, muhtemel WIP execution.py),
  `test_empty_patch_is_rejected::test_bulk_changed_counts_only_real_diffs` (1),
  `test_install_brings_the_tools_it_configures` (1, KUR.ps1 adÄ±m sayacÄ± /7). Ruff:
  `tests/test_burst_and_channel_honour_body_ratio.py`,
  `tests/test_note_fill_repairs_poisoned_sl.py` import sÄ±ralamasÄ±.
* Removal Safety: N/A â€” testler/kod uzlaÅŸtÄ±rÄ±lmalÄ± (Ã§oÄŸu bayat test, F-D1 gerÃ§ek risk).

---

**F-P1 â€” God-file'lar: engine.py 4712 LOC / 116 fn, web/app.py 2285/80, mt5client 2218/62, optimizer 2305/48**
* Kategori: Maintainability Â· Severity: Medium
* KanÄ±t: `wc -l` + `grep -c "^\s*def"`. engine.py 2 sÄ±nÄ±f, 116 fonksiyon tek dosyada.
* Neden Ã¶nemli: deÄŸiÅŸiklik riski yÃ¼ksek; test izolasyonu zor; F-D6/D7 gibi
  "deÄŸiÅŸtir ama testi/guard'Ä± unut" hatalarÄ± bu yÃ¼zeyde tekrar ediyor.
* Removal Safety: N/A (refactor, davranÄ±ÅŸ korunmalÄ± â€” Cursor kararÄ±).
* Reuse Scope: service-wide.

**F-P2 â€” `_cycle` her 2 sn'de sÄ±ralÄ± MT5 round-trip'leri tek RLock altÄ±nda**
* Kategori: Concurrency / I/O Â· Severity: Low-Medium (likely, Ã¶lÃ§Ã¼m gerek)
* KanÄ±t: `micofx/engine.py:857` `_cycle`; `refresh_account(force=True)` (863),
  `_probe_book_ticks` (867), `_reload_positions` (891) sÄ±ralÄ±. `mt5client.py` 39 lock
  bÃ¶lgesi. `/api/state` (her 3 sn) aynÄ± lock (AGENTS.md gotcha). Ledger `last_cycle_ms`
  geÃ§miÅŸte 3â€“7 ms â†’ ÅŸu an dar deÄŸil ama opt `busy` iken snapshot fallback var.
* Ã–lÃ§Ã¼lecek: yÃ¼k altÄ±nda `last_cycle_ms` p95; `/api/state` latency opt Ã§alÄ±ÅŸÄ±rken.
* Removal Safety: N/A.
* Reuse Scope: engine + web + mt5client.

**F-P3 â€” Arama combo duvarÄ± ~3.08 M'in ~2.07 M'i emekli `stoch_flip`'e ayrÄ±lmÄ±ÅŸ**
* Kategori: Cost / CPU Â· Severity: Medium
* KanÄ±t: `micofx/optimizer.py:109-110` yorum + `:168` `strategy_max_combos.stoch_flip
  = 28800`; DB `opt.strategy_max_combos` aynÄ±. stoch_flip fail-closed ama combo
  bÃ¼tÃ§esi/coverage_budget hesabÄ± onu sayÄ±yor.
* Beklenen etki: dead family combo tahsisi kalkarsa canlÄ± 4 aile daha derin taranÄ±r (arsiv)
  (aynÄ± duvar bÃ¼tÃ§esiyle).
* Removal Safety: Needs Verification (DB opt_params write yolu kÄ±sÄ±tlÄ±).
* Reuse Scope: optimizer.

**F-P4 â€” `required_bars()` her Ã§aÄŸrÄ±da Ã¶lÃ¼ aile lookback terimleri hesaplÄ±yor**
* Kategori: CPU (micro) Â· Severity: Low
* KanÄ±t: `strategy.py:770-773` â€” `int(p.t3_fast*max(1.2,p.t3_slow_mult))*20`,
  `int(p.st_period)*10 if p.st_mult>0`, `(stoch_k_period+stoch_k_smooth+stoch_d_smooth)
  *8`. 4 canlÄ± aile bunlarÄ± okumuyor (F-D4). `max(...)` iÃ§inde, genelde baÄŸlanmÄ±yor.
* Removal Safety: Likely Safe (F-D4 ile birlikte).
* Reuse Scope: module.

### 3) Quick Wins (Ã¶nce bunlar) â€” hepsi Ã¶lÃ§Ã¼m/temizlik, davranÄ±ÅŸ deÄŸiÅŸmez

1. **F-T3 ruff** (2 test dosyasÄ± import sÄ±ralamasÄ±) â€” `ruff --fix`, davranÄ±ÅŸ yok.
2. **F-D6 / F-D7 / F-D8 testleri** koda gÃ¶re gÃ¼ncelle (ichimoku artÄ±k htf okur;
   `_Engine` stub'a `supervisor`; kasa_auto hedefleri) â€” VEYA F-D8'de growth hedefi
   yanlÄ±ÅŸsa kod. Cursor karar.
3. **F-D3** `entry_blocks` pencere/rotasyon â€” auto-pilot bayat sayaÃ§ kararÄ±nÄ± kes, sonsuz
   "SPREAD kalibre atlandÄ±" logunu durdur.
4. **F-D5 / F-P3** DB `opt_params.strategies` + `opt.strategy_max_combos` emekli aile
   temizliÄŸi â€” arama bÃ¼tÃ§esi canlÄ± 4 aileye. (arsiv)
5. **F-D4 / F-P4** 11 Ã¶lÃ¼ Params alanÄ± â€” `Params.key()` + `required_bars` sadeleÅŸir.

### 4) Deeper Optimizations (sonra)

* **F-D1** cost gÃ¶rÃ¼nÃ¼rlÃ¼ÄŸÃ¼nÃ¼ geri getir (charged sayÄ± her apply'da) + Faz-1 costed
  replay (4 aile Ã— aktif+disabled Ã— son 10 pencere) â†’ gerÃ§ek net-R sÄ±rasÄ±. (arsiv)
* **F-E4** per-sembol `adx_min>0` costed holdout aramasÄ±.
* **F-E2** ters-sinyal-Ã§Ä±kÄ±ÅŸ: backtest simulate'e "aÃ§Ä±k pozisyonda ters sinyal â†’ flat"
  Ã¶lÃ§ (exit modelini bozmadan). F-E1 pyramiding'i YALNIZ F-E4 ile birlikte.
* **F-P1** engine.py / app.py modÃ¼lerleÅŸtirme (davranÄ±ÅŸ + WFO honesty korunur).
* Objektif fonksiyon: seÃ§im metriÄŸini ham `score`'dan Sortino/robustluk + `profit_drop`
  (ISâ†’OOS) kolonuna Ã§evir (RESEARCH_QUEUE "walk-forward OOS lock").

### 5) Validation Plan

* **Testler:** `4528b40`'ta 19 fail listesini referans al; her dÃ¼zeltme sonrasÄ±
  `pytest -q` = 0 fail hedef. Fail-first (AGENTS.md).
* **Costed replay:** `charge_costs=True` ile son 10 holdout penceresi, 4 aile Ã— (arsiv)
  {GER40,JPN225,NAS100,US30,XAUUSD,SpotBrent,BTCUSD}. Metrik: net R, expectancy,
  PF â€” cost-free sÄ±ralamasÄ±yla diff. Beklenti: M5/M15 burst dÃ¼ÅŸer.
* **Autopsy join:** `entry_block_events(risk_ters_yon)` Ã— `trade_autopsies` symbol+
  zaman penceresi â†’ kaÃ§ `sl` Ã§Ä±kÄ±ÅŸÄ± stoptan Ã¶nce ters sinyal gÃ¶rdÃ¼, toplam kurtarma R.
* **entry_blocks:** rotasyondan sonra 7 gÃ¼nlÃ¼k pencere ile fill oranÄ± + blokÃ¶r
  daÄŸÄ±lÄ±mÄ±; Ã¶nce/sonra.
* **Perf:** yÃ¼k altÄ±nda `last_cycle_ms` p95, `/api/state` latency (opt busy iken),
  arama sÃ¼resi (emekli-aile temizliÄŸi Ã¶nce/sonra).
* **CanlÄ±:** deÄŸiÅŸiklik sonrasÄ± gÃ¼nlÃ¼k autopsy sumR / avgR / MFE-capture medyan;
  hedef avgR â‰¥ 0 ve MFE-capture medyan â‰¥ 0.4.

### 6) Optimized Code / Patch

Yok â€” operatÃ¶r talimatÄ±: "hiÃ§bir ÅŸeyi dÃ¼zeltme, hepsi OPTIMIZATIONS.md'ye." Bulgular
Cursor'a doÄŸrulama + plan + gÃ¶rev daÄŸÄ±lÄ±mÄ± iÃ§in `claude/FOR_CURSOR.md`'ye Ã¶zetlendi.

---

### EK â€” C1 costed replay Ã–LÃ‡ÃœMÃœ (02.09 19:52, salt-okur)

YÃ¶ntem: `data/holdout_bars/*.npz` (yakalanmÄ±ÅŸ 90k-bar pencereler) â†’ `holdout_cost.
charged_holdout` son segment (~18k bar), CANLI DB config (aile/exits) snapshot TF'ine
zorlanarak, iki kez: **COSTED** = gerÃ§ek `spread_scale` (1.00â€“1.25) + komisyon;
**FREE** = spread_scale 0 + komisyon 0 (canlÄ± aramanÄ±n gÃ¶rdÃ¼ÄŸÃ¼). Script:
scratchpad `c1_costed_replay.py`. PATCH/DB/API yok.

| snapshot | canlÄ± aile/TF | COSTED net_r / exp / PF / n | FREE net_r | Î” (cost drag) |
|----------|---------------|-----------------------------|-----------|---------------|
| GER40_M15 | burst (canlÄ± **M5**) | **âˆ’33.6** / âˆ’0.074 / 0.89 / 457 | âˆ’20.5 | âˆ’13.2 |
| GER40_M30 | burst (canlÄ± **M5**) | **+21.4** / +0.049 / 1.07 / 438 | +42.9 | âˆ’21.5 |
| JPN225_M15 | burst/M15 âœ“ | **+48.3** / +0.192 / 1.28 / 252 | +62.7 | âˆ’14.4 |
| NAS100_M30 | mtf_pullback/M30 âœ“ | **+23.6** / +0.021 / 1.03 / 1099 | +44.0 | âˆ’20.4 |
| US30_M30 | channel_break/M30 âœ“ | **+18.0** / +0.054 / 1.08 / 334 | +19.7 | âˆ’1.8 |
| US30_M5 | (canlÄ± M30) | âˆ’30.8 / âˆ’0.101 / 0.86 | âˆ’30.9 | +0.1 |
| XAUUSD_M15 | burst *(disabled)* | **+83.4** / +0.143 / 1.22 | +98.3 | âˆ’14.8 |
| BTCUSD_M30 | burst *(disabled)* | +58.5 / +0.183 / 1.27 | +81.8 | âˆ’23.4 |
| GOLD-PERP_M30 | mtf_pullback *(disabled)* | **+114.3** / +0.219 / 1.35 | +118.7 | âˆ’4.4 |
| SpotBrent_M15 | burst *(disabled)* | âˆ’18.3 / âˆ’0.032 / 0.95 | +19.8 | âˆ’38.1 |
| SpotBrent_M30 | burst *(disabled)* | âˆ’27.2 / âˆ’0.035 / 0.95 | +41.8 | âˆ’69.0 |

**Ã–lÃ§Ã¼len sonuÃ§lar (F-D1 / lever A iliÅŸkin):**
1. **Maliyet, canlÄ± 4 iÃ§in ANA katil DEÄžÄ°L.** Cost drag 18k-bar pencerede âˆ’2..âˆ’21 R;
   iÅŸareti Ã§evirmiyor. COSTED bile: JPN225 +48, NAS100 +24, US30 +18, GER40/M30 +21.
   â†’ `charge_costs=False` holdout'u ~%15â€“45 ÅŸiÅŸiriyor ama +90R-holdout / âˆ’41R-canlÄ±
   ayrÄ±mÄ± **Ã¶ncelikli olarak cost-modeling artefaktÄ± deÄŸil**. **Lever A: birincil â†’
   ikincil.**
2. **AsÄ±l aÃ§Ä±k holdout(+) â†” canlÄ±(âˆ’).** Costed holdout NAS100 +24 / JPN225 +48 derken
   canlÄ± NAS100 âˆ’19 / JPN225 âˆ’17. Maliyet deÄŸil; iÅŸaret eden yerler: rejim/timing
   (adx=0, F-E4), fill kalitesi %22â€“33 (F-E3), 1-ticket cap iyi 2. sinyali dÃ¼ÅŸÃ¼rÃ¼yor
   (F-E1), veya WFO iyimserliÄŸi / pencere sonrasÄ± rejim kaymasÄ±. **Lever B (rejim
   filtresi) + yapÄ±sal (fill/cap) Ã¶ne Ã§Ä±kÄ±yor.**
3. **GER40 canlÄ± TF (M5) snapshot YOK.** M15 costed âˆ’33.6 (kÃ¶tÃ¼), M30 costed +21.4
   (iyi). CanlÄ± burst/M5. M5, M15 gibiyse GER40 costed zararda. GER40_M5 yakalama
   gerek (flat kitap, operatÃ¶r/Cursor).
4. **US30 canlÄ± M30 doÄŸru seÃ§im** (M30 costed +18 vs M5 costed âˆ’31).
5. **Disabled kazananlar costed bile gÃ¼Ã§lÃ¼:** GOLD-PERP/mtf_pullback **+114**,
   XAUUSD/burst **+83**, BTCUSD/burst **+58** â€” canlÄ± 4'Ã¼n 3'Ã¼nden iyi. Fill/rejim
   sorularÄ± Ã§Ã¶zÃ¼lÃ¼nce yeniden-aÃ§ma adayÄ± (operatÃ¶r red).
6. **SpotBrent her TF'de costed zararda** (âˆ’18..âˆ’27) â€” doÄŸru ÅŸekilde disabled.

UyarÄ±: yÃ¶ntem canlÄ± aile+exit'i snapshot bar-TF'ine zorluyor; GER40 M5â‰ M15/M30.
`block_reverse=True`, son-segment â€” optimizer holdout'una sadÄ±k.

---

### EK â€” C3 / C-next A: per-sembol `adx_min` COSTED sweep (02.09 20:05, salt-okur)

AynÄ± npz + `charged_holdout`, canlÄ± aile/exit, `adx_min âˆˆ {0,15,20}` (0 = mevcut canlÄ±
= filtre yok). Costs ON. Script: scratchpad `c3_adxmin_sweep.py`.

| sembol / aile-TF | adx_min=0 (canlÄ±) | =15 | =20 | en iyi |
|------------------|-------------------|-----|-----|--------|
| **NAS100** mtf_pullback/M30 | +23.6 (exp .021, n1099) | **+57.0** (exp .055, n1033) | +46.8 (exp .057, n823) | **15** (+33 R, exp 2.5Ã—) |
| **US30** channel_break/M30 | +18.0 (exp .054) | **+23.9** (exp .075) | +19.9 (exp .076) | **15** (+6 R) |
| **JPN225** burst/M15 | **+48.3** (exp .192) | +31.1 | +12.6 | **0** (filtre âˆ’17..âˆ’36 R zarar) |
| **GER40** burst/M30 | **+21.4** | +19.1 | +16.3 | **0** (filtre hafif zarar) |
| GER40 burst/M15 | âˆ’33.6 | âˆ’31.8 | âˆ’43.2 | (M15 zaten kÃ¶tÃ¼) |
| XAUUSD burst/M15 *(off)* | +83.4 | +73.4 | +94.6 (exp .223) | 20 (gÃ¼rÃ¼ltÃ¼lÃ¼) |
| BTCUSD burst/M30 *(off)* | +58.5 | +60.6 | +15.1 | 15 |

**Ã–lÃ§Ã¼len sonuÃ§:**
1. **`adx_min` aile-spesifik, evrensel deÄŸil.** `mtf_pullback` (NAS100) ve
   `channel_break` (US30) iÃ§in `adx_min=15` net costed iyileÅŸme (NAS100 +33 R,
   expectancy 2.5Ã—, iÅŸlem sayÄ±sÄ± korunur; US30 +6 R). `burst` (JPN225, GER40) iÃ§in
   HERHANGÄ° bir ADX tabanÄ± zarar veriyor.
2. **Sebep tasarÄ±msal:** burst bir range-*expansion* giriÅŸi, dÃ¼ÅŸÃ¼k-ADX patlamada
   ateÅŸlenir; trend-gÃ¼cÃ¼ filtresi tam da edge'ini siler (burst docstring + ADX
   literatÃ¼rÃ¼: filtre trend-devam setup'Ä±na yarar, expansion'a deÄŸil).
3. **F-E4 / lever B â€” Ã¶lÃ§Ã¼lÃ¼ Ã¶neri:** `adx_min=15` YALNIZ NAS100 (mtf_pullback) +
   US30 (channel_break); burst isimleri (JPN225, GER40) `adx_min=0` kalsÄ±n. ichimoku
   canlÄ±ya girerse ayrÄ± test.
4. **NAS100 en gÃ¼Ã§lÃ¼ aday:** +23.6 â†’ +57.0 costed, ÅŸu ana kadarki en bÃ¼yÃ¼k tekil
   Ã¶lÃ§Ã¼lÃ¼ iyileÅŸme; NAS100 canlÄ±da en kÃ¶tÃ¼ (âˆ’18.7 R). YÃ¼ksek gÃ¼ven.

UyarÄ±: tek pencere (son segment ~18k bar). Apply Ã¶ncesi optimizer'Ä±n tam walk-forward
+ validation gate'i ÅŸart (apply yolu = Cursor, ben deÄŸil). GER40 canlÄ± TF M5 hÃ¢lÃ¢
test edilemiyor.

---

### EK â€” C2 / C-next B: MFE zaman-profili (canlÄ± autopsy, 02.09 20:12, salt-okur)

`trade_autopsies` (n=319). `bars_held` null â†’ `held_min` proxy; `mfe_r` tÃ¼m-iÅŸlem
tepe (bar-indeksli eÄŸri yok). Script: scratchpad `c2_mfe_profile.py`.

**Trail aktivasyon gerÃ§eÄŸi (canlÄ± 4):**

| sembol | trail_start | =R | medyan MFE | trail'e ULAÅžAN % | medyan realised | capture ratio |
|--------|-------------|----|-----------|------------------|-----------------|---------------|
| GER40 | 2.0 ATR | 2.00 R | 0.60 R | **%14** | âˆ’1.00 | 0.11 |
| JPN225 | 2.5 ATR | 2.50 R | 0.77 R | **%11** | âˆ’0.58 | âˆ’0.36 |
| NAS100 | 2.5 ATR | 2.50 R | 0.47 R | **%13** | âˆ’1.00 | 0.17 |
| US30 | 0.3 ATR | 0.30 R | 0.72 R | %68 | âˆ’1.00 | 0.05 |

* GER40/JPN225/NAS100: `trail_start` 2.0â€“2.5 R ama medyan MFE 0.47â€“0.77 R. Ä°ÅŸlemlerin
  yalnÄ±z **%11â€“14'Ã¼** trail eÅŸiÄŸine ulaÅŸÄ±yor; kalan ~%86 sabit âˆ’1R stop'ta trailsiz
  sÃ¼rÃ¼yor â†’ medyan realised tam âˆ’1.00 R (GER40, NAS100). **Trail, ulaÅŸÄ±labilir MFE'nin
  3â€“5 katÄ± Ã¶teye kurularak fiilen devre dÄ±ÅŸÄ±.**
* US30: `trail_start=0.3R` erken, %68 ulaÅŸÄ±yor â€” ama `trail_step=2.2 ATR` Ã§ok geniÅŸ â†’
  korumuyor; capture 0.05; `sl` Ã§Ä±kÄ±ÅŸlarÄ±nÄ±n **%80'i 1 saat iÃ§inde entry'yi geri
  geÃ§ti** (whipsaw / erken stop). medHeld 31 dk (en hÄ±zlÄ±), 92 iÅŸlemin 50'si `sl`.

**MFE, tutuÅŸ-sÃ¼resi Ã§eyreÄŸine gÃ¶re (tÃ¼m semboller):**

| Ã§eyrek | held | ort. MFE_r | ort. realised_r | n |
|--------|------|-----------|-----------------|---|
| Q1 en kÄ±sa | 0â€“24 dk | +0.27 | **âˆ’0.91** | 79 |
| Q2 | 24â€“73 dk | +1.03 | âˆ’0.32 | 79 |
| Q3 | 74â€“179 dk | +1.32 | +0.18 | 79 |
| Q4 en uzun | 180 dk+ | +1.85 | **+0.50** | 82 |

* KÄ±sa iÅŸlem = saf zarar (Q1: MFE +0.27, realised âˆ’0.91). HÄ±zlÄ± Ã¶len iÅŸlemde hareket
  hiÃ§ olmamÄ±ÅŸ. Uzun yaÅŸayan (Q4) para kazanÄ±yor. Klasik trend-takip: edge koÅŸuculardadÄ±r.
* Erken-stop (sl, 1 saatte entry'yi geri geÃ§ti): US30 **%80**, NAS100 %52, GER40 %48,
  JPN225 %44. left_on_table medyan ~1.1â€“1.3 R / iÅŸlem (capture ~0 ile tutarlÄ±).

**Ã–lÃ§Ã¼len sonuÃ§ (exit MODELÄ° deÄŸiÅŸmez â€” sadece grid iÃ§i eÅŸik):**
1. **`trail_start` GER40/JPN225/NAS100 iÃ§in ulaÅŸÄ±labilir MFE'nin Ã§ok Ã¶tesinde.** Aday:
   per-sembol `trail_start_atr` â‰ˆ 0.5 Ã— medyan MFE (â‰ˆ 0.3â€“0.4 ATR) costed holdout ile
   ara. Grid'de `trail_start_atr [0.3,0.4,0.5,...]` zaten var.
2. **US30: trail aktif ama `trail_step=2.2 ATR` Ã§ok geniÅŸ + %80 erken-stop.** Daha dar
   step ara; + F-E4 `adx_min=15` (zaten bulundu) whipsaw giriÅŸlerini keser. US30
   medHeld 31 dk = hÄ±zlÄ± chop'ta aÅŸÄ±rÄ± iÅŸlem.
3. **Edge Q4'te (uzun tutuÅŸ).** HÄ±zlÄ±-Ã¶lÃ¼m oranÄ±nÄ± artÄ±ran (gevÅŸek giriÅŸ, rejim filtresi
   yok) veya Q2/Q3 orta-iÅŸlemleri korumayan (ulaÅŸÄ±lamaz trail) her ÅŸey kitabÄ± akÄ±tÄ±yor.
   Ä°ki Ã¶lÃ§Ã¼lÃ¼ kaldÄ±raÃ§: rejim filtresi (F-E4, NAS100/US30) + ulaÅŸÄ±labilir `trail_start`
   (per-sembol costed arama).
4. UyarÄ±: MFE bar-indeksli deÄŸil; "ilk N bar" kesin deÄŸil â€” Ã§eyrek ayrÄ±mÄ± proxy.
   Apply = optimizer WFO/validation (Cursor).

---

### EK â€” C4: emekli-aile Ã¶lÃ¼ alan temizlik PLANI (02.09 20:22, UYGULAMA YOK)

11 Ã¶lÃ¼ alan: `t3_fast, t3_slow_mult, t3_fast_vf, t3_accel_min, st_period, st_mult,
stoch_k_period, stoch_k_smooth, stoch_d_smooth, psar_af_step, psar_af_max`
(dual_t3/t3_flip/stoch_flip/parabolic_flip â€” 01.09 emekli). CanlÄ± 4 aile (arsiv)
`opt_fields_read` Ã§Ä±ktÄ±sÄ± bunlarÄ±n HÄ°Ã‡BÄ°RÄ°NÄ° okumuyor (Ã¶lÃ§Ã¼ldÃ¼).

**GÃ¼venlik doÄŸrulamasÄ±:**
- `_coerce` (models.py:42) bilinmeyen key'i atlÄ±yor â†’ eski DB payload / fixture'lar
  alan silinince sorunsuz yÃ¼kleniyor. âœ“
- `Params.from_config` (strategy.py:116) `cls.__dataclass_fields__`'e filtreliyor â†’
  alan Params'tan Ã§Ä±kÄ±nca kopyalanmÄ±yor. âœ“
- `Params.key()` deÄŸiÅŸimi â†’ sinyal cache kimliÄŸi deÄŸiÅŸir, bir kez yeniden hesaplanÄ±r
  (kalÄ±cÄ± cache yok). âœ“
- `required_bars()` sadeleÅŸmesi â†’ bazÄ± configlerde fetch boyutu DÃœÅžER (Ã¶lÃ¼ terimler
  yalnÄ±z ÅŸiÅŸiriyordu). âœ“ (F-P4 mikro-kazanÃ§)

**Dokunulacak (Ã¶nerilen diff, Cursor uygular):**

| # | Dosya | DeÄŸiÅŸiklik | SatÄ±r |
|---|-------|-----------|-------|
| 1 | `micofx/strategy.py` | `Params`'tan 11 alanÄ± sil | 58â€“82 |
| 2 | `micofx/strategy.py` | `Params.key()` tuple'Ä±ndan 11 alanÄ± Ã§Ä±kar | 145â€“150 |
| 3 | `micofx/strategy.py` | `required_bars()` 3 Ã¶lÃ¼ terimi sil (`t3_fast*slow_mult*20`, `st_period*10`, `stoch_k toplamÄ±*8`) | 770â€“773 |
| 4 | `micofx/models.py` | `SymbolConfig`'ten 11 alanÄ± sil | 126â€“167 |
| 5 | `micofx/models.py` | `OPT_FIELDS`'ten 11 giriÅŸi sil | 534â€“542 |
| 6 | `micofx/web/app.py` | `_INDICATOR_PERIOD_BOUNDS`'tan `t3_fast, st_period, stoch_k_period, stoch_k_smooth, stoch_d_smooth` Ã§Ä±kar; 190 yorumunu gÃ¼ncelle | 190, 197 |
| 7 | `tests/test_indicator_periods_are_bounded.py` | silinen bound'larÄ± beklemeyi kaldÄ±r (14 ref) | â€” |
| 8 | DB `opt_params.strategies` | 4 emekli aile adÄ±nÄ± Ã§Ä±kar â†’ `[mtf_pullback, burst, ichimoku, channel_break]` | settings |
| 9 | DB `opt` | `strategy_max_combos.stoch_flip` (28800) sil | settings |

**BÄ±rakÄ±lacak:** `tests/fixtures/eski_ikincil_konfig_*.json` (152+21 ref) â€” bunlar
"eski config yÃ¼klenebiliyor mu" regresyon testi; `_coerce` bilinmeyeni atladÄ±ÄŸÄ± iÃ§in
silme sonrasÄ± bu testler tam da doÄŸru ÅŸeyi kanÄ±tlar.

**Kontrol edilecek (Cursor, apply Ã¶ncesi):** `test_every_family_on_every_timeframe.py`,
`test_exit_param_bounds_everywhere.py`, `test_family_grid_only_searches_fields_it_reads.py`
bu alanlara deÄŸiyor mu; canlÄ± sembol `opt_summary.params` stamp'i emekli alan taÅŸÄ±yor mu
(taÅŸÄ±yorsa `unstamped_gates_to_zero` zaten sÄ±fÄ±rlÄ±yor). DB 8â€“9: panel POST `opt_params`
= 400 (AGENTS.md); doÄŸrudan `Store` Ã§aÄŸrÄ±sÄ± veya migration gerek.

**Beklenen etki:** kod âˆ’~40 satÄ±r Ã¶lÃ¼; `OPT_FIELDS` 11 eksen daralÄ±r (emekli-aile
ekseni artÄ±k aranamaz/uygulanamaz â€” F-D5); arama combo bÃ¼tÃ§esi canlÄ± 4 aileye (arsiv)
(`stoch_flip` 28800 â‰ˆ 3.08M duvarÄ±n 2.07M'i â€” F-P3). DavranÄ±ÅŸ deÄŸiÅŸmez.

---

Operator: maximize income, fix gaps, GitHub+web, run opt at 00:06.
No engine PATCH. Live 22:36: 4 tickets (GER40 overnight 2.0 ATR + JPN/XAU/NAS),
day still **âˆ’$186.61 / 38** closes, halt false, opt idle.

* Public WFO/WFE 0.5, ATR-stop blogs (1.0Ã— noise on M30, 2.0Ã— common),
  StockSharp stoch+step trail, ByTamerFX DD-scalp+TP, QTradeX `tp_multiplier`
  â€” none of that enters this tree. Exit model stays hard ATR + ATR trail.
* `size_by_edge` / `daily_loss_pct=0` remain yellow (HTTP 400). Shakeout
  floor already live; do not teach the search it; do not PATCH open SL.
* 00:06 `POST /api/opt/run` `apply_best=true` `force=true` (GER 8.1 h /
  NAS 6.6 h / XAU 17.6 h < 48 h). Saved 8 families (arsiv): dropping the five idle
  ones only saves ~1.01 M; `stoch_flip` 28800 is ~2.07 M. 20:21 died on
  restart-with-tickets. This PID does not restart.

---

Independent Cursor pass after operator: API/web/engine/families/symbols,
stripped-feature leftovers, missed fills, reverse+forward, counterfactuals
**with numbers**. Did **not** PATCH, start a search, flatten, capture,
restart, or commit. 1 GER40 ticket open. Claude given a heavier independent
brief (22:08) â€” this file is Cursor's numbers, not Claude's.

Live GET `/` cookie then `/api/state` `/api/symbols` `/api/system`
`/api/analysis/*` `/openapi.json`. Log `logs/micofx.log` 27.08 only.
Autopsies dated with `gmtime` (naive broker epoch). 82 tests green:
csrf, openapi, cancel-abandon, hands-off HTTP, unused names, shakeout,
panel DOM.

**Live 22:05â€“22:10:** demo 61562752. Balance **$1957.88** / equity **~$1958**
/ floating **âˆ’$0.1**. Day **38** closes WR **26.3%** realised **âˆ’$186.61**
`pnl_pct` **âˆ’8.69%** halt **false**. `opt.state=idle`. `last_cycle_ms` **3â€“7**.
`last_error` empty. 1 open: GER40 #367727827 BUY 0.1 SL **26303.1** (entry
26379.1 â‰ˆ **2.0 ATR**, ATR 38.0). AI `risk_scale` **0.60** enforced
(`Gunluk zarar %8.69`). JPN `ok`; other five `watch`.

### 1) Optimization Summary

* **Health:** No new engine leak vs 20:40. Today's **âˆ’$186.61 / âˆ’13.22 R**
  is GER40 `stoch_flip` 1.0 orig-SL (**8/11**, **âˆ’$138.52 / âˆ’8.89 R**) plus
  JPN225 (**âˆ’$73.79 / âˆ’7.16 R**) with **no daily halt** (`daily_loss_pct=0`)
  and **no ticket cap** (`max_total_positions` **unread**). Idle cycle is
  paid (**3â€“7 ms**). Search is **not** running. Claude 20:50 openapi+cancel
  holes are **closed on this PID** (404 + disk abandon).
* **Top 3 highest-impact (none is a silent CPU patch):**
  1. Keep the open GER40. Restart first-sights stops; 21:20 and 21:43 already
     restarted **with tickets** (5 then 3).
  2. After **flat only**: `daily_loss_pct=0` vs a 3% brake. Start equity
     inferred **$2144** from `pnl_pct`. 3% â‰ˆ **$64**. Realised **$186**.
     Gap **~$122** is the measured extra bleed **if** the 3% halt would have
     fired and flattened; it would also have flattened later US30/XAU winners
     (US30 today **+$21.78 / +2.19 R**, XAU **+$8.97 / +1.37 R**). Yellow/red.
  3. GER40 searched stop **1.0** vs shakeout next-entry **2.0** (this PID,
     22:01 `lot serbest, risk ayni`). Floor is live on **all 6** names
     (last-10 `exit_reason=sl` losers â‰¥3; all of those were `sl==original_sl`).
     Search still prefers 1.0. Do not PATCH SL. Do not disable the floor.
* **Biggest risk if no changes:** Operational, not ms. Next `apply_best`
  of a 1-slot walk-forward onto a book that stacks until **margin 90% /
  reverse / STOPSUZ** is an untested regime. Panel still ranks dead
  `risk_sembol_limiti` **209** as lifetime #2 (producer gone). Day can
  keep bleeding with no halt.

### 2) Findings (Prioritized)

* **Title** `max_total_positions=100` is unread â€” 100-slot / 80% 1R does **not** bind
* **Category** Algorithm / Reliability
* **Severity** High (operator model; corrects 20:40)
* **Impact** Live stacking cap is **margin 90%**, reverse, STOPSUZ, scalp/swing
  only if those leftovers **>0** (live **0/0 = off**). Capacity
  `global_free_slots=237`, `margin_usage_pct=0.39`, `open_risk_pct=0.45`.
* **Evidence** `can_open` `risk.py:570-604` has no total-count check.
  `max_positions` **zero reads** in `risk.py`. Capacity still **dumps**
  `max_total_positions: 100` and leftover `max_concurrent_risk_pct: 30`.
  field_help already says unread.
* **Why itâ€™s inefficient** 20:40 / Claude 20:35 treated 100Ã—0.8%=80% 1R as
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
* **Impact** Day **âˆ’$186.61 / âˆ’13.22 R / 38 closes**. GER40 11 **âˆ’$138.52 /
  âˆ’8.89 R / 8 orig-SL / 2 trail / 1 manuel / 1 win**. JPN225 13 **âˆ’$73.79 /
  âˆ’7.16 R / 6 orig-SL**. US30 7 **+$21.78 / +2.19 R**. XAU 2 **+$8.97**.
  NAS 4 **âˆ’$1.14**. Brent 1 **âˆ’$3.87**. `mfe_râ‰¥1.5` then SL **today: 0**.
* **Evidence** Autopsy `gmtime` 27.08 n=38 matches `/api/state` day.
  `fill_vs_signal_close_r` today n=25 mean **+0.088 R** (min âˆ’0.13, max +1.12)
  â€” not an adverse-fill leak. Window n=237: SL 132, through_entry 87,
  recovery â‰¥0.5 R 135.
* **Why itâ€™s inefficient** Search still offers `sl_atr_mult=1.0` and GER40
  holds it. Shakeout only widens the **next** entry (22:01 GER40 2.0, lot free).
* **Recommended fix** Let a future search finish on a **flat** book. Do not
  PATCH SL on the open ticket. Do not cancel a search that is already idle.
* **Tradeoffs / Risks** `apply_best` may write another 1.0 onto GER40.
* **Expected impact estimate** Floor: losers stay âˆ’1 R in R-space; min-lot
  names **grow dollar risk** (see shakeout finding).
* **Removal Safety** Needs Verification
* **Reuse Scope** `risk.shakeout_sl_atr_mult` + optimizer grid

* **Title** `daily_loss_pct=0` â€” flatten-always is wired but unreachable
* **Category** Reliability / Cost
* **Severity** High (policy)
* **Impact** Counterfactual 3% of ~$2144 â‰ˆ **$64**. Realised **$186**.
  Extra **~$122** if the old 3% halt would have flattened when it first
  crossed. `daily_loss_flatten` **unread** (`models.py` + field_help only);
  engine flattens whenever `loss_halted` (`engine.py:897-899`) **without**
  reading the flag. Halt never trips because `DailyGuard.check` needs
  `daily_loss_pct > 0` (`risk.py:263`).
* **Evidence** Live `system.daily_loss_pct=0`, `halted=false`. CFG 19:28
  `daily_loss_pct 20.0 -> 0.0`. HTTP 400 on POST `daily_loss_pct`.
* **Why itâ€™s inefficient** N/A â€” intentional cancel. Communication: capacity
  / AI still react (`lot carpani 0.60` at âˆ’8.69%) **after** the cash is gone.
* **Recommended fix** None unless the operator wants the brake back.
  Restoring 3% is yellow/red. Do not silently write 3.
* **Tradeoffs / Risks** A halt flattens winners too.
* **Expected impact estimate** Likely capped today near âˆ’$64 vs âˆ’$186
  **if** it had been on from the open. Not a replay.
* **Removal Safety** Needs Verification
* **Reuse Scope** Store leftover + `DailyGuard`

* **Title** Concurrent 30% leftover â€” the cap **was** binding before the strip
* **Category** Algorithm
* **Severity** High (stripped feature, not dead)
* **Impact** Log 27.08 **8** `eszamanli` WARN lines, last `19:18:35 kitap
  %54.56 eszamanli risk istiyor, tavan %30`. After ~20:05 unread, WARNs stop.
  Live 20:39 had **7** opens. Now 1 open, `concurrent_risk_pct` dump **4.91**
  (sum of configured 1R, not a gate).
* **Evidence** Claude TUR 5 + log. `can_open` does not read
  `max_concurrent_risk_pct`. HTTP 400.
* **Why itâ€™s inefficient** Calling it "dead code cleanup" is false â€” it was
  refusing entries at 31â€“54% demand. Operator chose to drop it; record that.
* **Recommended fix** Do not restore unasked. Do not teach search stacking
  tonight.
* **Tradeoffs / Risks** Restoring 30% re-opens a real gate (yellow).
* **Expected impact estimate** Unknown without a stacking walk-forward.
  Cannot attribute today's âˆ’$186 to the strip (no replay).
* **Removal Safety** Needs Verification
* **Reuse Scope** `risk.can_open`

* **Title** Shakeout floor is on for the whole book; min-lot **grows** dollar risk
* **Category** Cost
* **Severity** High (live overlay vs paper)
* **Impact** Last-10 `exit_reason=sl` losers: SpotBrent 3, JPN 5, GER40 7,
  US30 3, NAS 5, XAU 7 â€” **all â‰¥3**, all were `sl==original_sl`. Floor **2.0**.
  Log 6 fires: first five `lot tabanda, gercek risk buyuyor`; GER40 22:01
  `lot serbest, risk ayni`. Capacity `lot_note` `SL x2 shakeout` on five
  names; Brent still `avantaj x0.71` (sl already 2.5 â‰¥ floor).
* **Evidence** `shakeout_sl_atr_mult` window=10 deaths=3 floor=2.0.
  `shakeout_size_note` `risk.py:66-77`. This PID 18:00â€“22:01.
* **Why itâ€™s inefficient** Walk-forward never pays the floor. Winners' R
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
* **Why itâ€™s inefficient** Historical counters look like a live gate.
* **Recommended fix** After quiet: drop needles **or** note suffix
  `(kalkti)` **or** reset (wipes spread/ters too). Do not reset during a
  search (none running, still don't â€” operator-visible).
* **Tradeoffs / Risks** Reset is one-shot irreversible on that blob.
* **Expected impact estimate** Zero latency. Stops a false #2.
* **Removal Safety** Likely Safe (mapping) / Needs Verification (reset)
* **Reuse Scope** engine.py + panel analysis

* **Title** 20:21 `apply_best` 3.08M died at 160k; restart-with-opens cancelled it
* **Category** Concurrency / Reliability
* **Severity** High (operational, now idle)
* **Impact** Log: 20:21 start 144 sweeps / 6 symbols / 8 families (arsiv) / 3 TF
  (`6Ã—8Ã—3=144`). Cancel lines 20:27â€“21:20 stuck **160000/3081600**.
  **21:20:58 restart** (5 tickets) + **21:43:25 restart** (3 tickets).
  No apply line. Last successful apply **15:56** GER40+NAS100.
  Disk now abandons the pool; this PID did not run that job.
* **Evidence** `logs/micofx.log` OPT/WARN. Live `opt.idle`. Tests 4/4
  `test_opt_cancel_is_noticed_mid_sweep`.
* **Why itâ€™s inefficient** Iptal set the event; old harvest waited on
  workers. Restarts with tickets first-sight stops **and** kill the job.
* **Recommended fix** Do not start a new 3.08M unasked. Next search: either
  drop unused families from **that job's** `strategies` (one-off, not persist)
  or leave 8 â€” apply **can** swap (NAS100 `mtf_pullback`â†’`stoch_flip` 15:56).
* **Tradeoffs / Risks** A 3-family one-off cannot discover ichimoku/aroon.
* **Expected impact estimate** 5 unused families = **90/144** sweeps (62.5%)
  if this job had finished. Combo wall dominated by `stoch_flip` cap 28800.
* **Removal Safety** Needs Verification
* **Reuse Scope** optimizer start `strategies=`

* **Title** Restart/shutdown 409 still missing â€” proven twice tonight
* **Category** Reliability
* **Severity** Medium (constitution vs operator)
* **Impact** Two live restarts with open tickets. 21:50 four **Elle
  (terminal)** closes (US30 +9.40, JPN âˆ’3.10, GER40 +3.86, US30 +13.56 =
  **+$23.72** operator, not engine) then IPC **âˆ’10001** Ã—2.
* **Evidence** `app.py:1987-2016` no position check, no `_restarting` lock.
  Log 21:20 / 21:43 `Yeniden baslatma istegi alindi` + `magic ile N acik ticket`.
* **Why itâ€™s inefficient** AGENTS.md forbids restart-with-opens; HTTP allows it.
  Double-submit can spawn two `restart.bat`.
* **Recommended fix** Notes only tonight â€” operator used restart with tickets
  and granted restart authority. A 409 would block that. Do not add unasked.
* **Tradeoffs / Risks** 409 vs operator override.
* **Expected impact estimate** Safety, not ms.
* **Removal Safety** Needs Verification
* **Reuse Scope** `app.py` restart/shutdown

* **Title** `size_by_edge` hidden-but-on; AI 0.60 after the loss
* **Category** Maintainability
* **Severity** Medium
* **Impact** Live True. GER40 capacity `avantaj x1.89`. HTTP 400. AI scale
  0.60 from **today's** âˆ’8.69% â€” haircuts **next** lots, does not unwind
  today's âˆ’$186. GER40 TRADE 22:01 `AI x0.36` with shakeout 2.0 and lot free 0.12.
* **Evidence** `GET /api/system` `size_by_edge=true`. TRADE 22:01:12.
* **Why itâ€™s inefficient** Operator cannot dial it. AI throttle is lagging.
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
  Naive Â±120s unmatched **55** â€” includes reverse, spread, session, restart
  re-SIGNAL (10:03:46 GER40/XAU/NAS same second; 21:20/21:43 `last_bar`
  replay). Lifetime fill 289/956=30.2% mixes the dead 209-slot era.
* **Evidence** Log parser. `filled_bars` / restart SIGNAL design (24.08 15:31).
* **Why itâ€™s inefficient** Counting SIGNALâˆ’TRADE as missed edge overstates.
  Need `entry_block_events` **today** (API totals are lifetime).
* **Recommended fix** Do not open spread / reverse gates unasked (MISS-1 GER40
  reverse holdout âˆ’1001 R still stands).
* **Tradeoffs / Risks** False "we left money on the table".
* **Expected impact estimate** Unmeasured without today's event rows.
* **Removal Safety** n/a
* **Reuse Scope** analysis + log

* **Title** 8 families (arsiv) reverse: 4 live `stoch_flip` + burst + parabolic; 5 empty are search candidates
* **Category** Algorithm
* **Severity** Medium (search cost vs option value)
* **Impact** Live book: GER40/JPN/NAS/US30 `stoch_flip` (HTF **flat**),
  XAU `burst` M15 (HTF used, misses showed HTF=âˆ’1), Brent `parabolic_flip`
  M15 (PSAR flip, HTF flat, sl 2.5). Empty: `mtf_pullback` `dual_t3`
  `t3_flip` `aroon_flip` `ichimoku`. Grids already drop unread axes
  (`test_no_family_grid_axis_is_unread`). Overlays **not** OPT_FIELDS:
  BE 1.5, partial 1.5 on five names, harvest **0**.
* **Evidence** `GET /api/symbols`. `strategy.py` builders + `searchable_axes`.
  20:21 log `144 tarama`.
* **Why itâ€™s inefficient** 90/144 sweeps search families the book does not
  currently trade; `apply_best` **may** swap them in (NAS100 15:56).
* **Recommended fix** F1/F2 stay **won't-do**. One-off `strategies=` on a
  future manual run is allowed and does not persist.
* **Tradeoffs / Risks** Dropping 5 families (arsiv) forever closes NAS100-style swaps.
* **Expected impact estimate** Sweep count âˆ’62.5% on a 144-job; combo wall
  still `stoch_flip` 28800-capped.
* **Removal Safety** Needs Verification (yellow if persistent)
* **Reuse Scope** `POST /api/opt/run` strategies

* **Title** GET leftover asdict + `autostart_mt5=true` vs MASTER_PROMPT Â§19
* **Category** Frontend / Maintainability
* **Severity** Low
* **Impact** `/api/system` still returns unread caps and `daily_loss_flatten`.
  Panel connection card still has `autostart_mt5` (HTTP allowlist).
  MASTER_PROMPT Â§19 says do not port `autostart_mt5`; this tree already has it
  and AGENTS.md lists it as System POST. Not a new port.
* **Evidence** Live GET. `app.py` `_OPERATOR_SYSTEM_FIELDS`.
* **Why itâ€™s inefficient** Agents/panel can *see* dead knobs.
* **Recommended fix** Slim GET after next boot. Do not remove autostart unasked.
* **Tradeoffs / Risks** GET-as-contract readers.
* **Expected impact estimate** Less than 1% payload.
* **Removal Safety** Likely Safe (slim) / Needs Verification (autostart)
* **Reuse Scope** app.py

* **Title** Security live: session/CSRF/openapi/hands-off hold; restart 409 is the hole
* **Category** Reliability / Security
* **Severity** Lowâ€“Medium
* **Impact** See SECURITY AUDIT below. No new injection in the probes.
* **Evidence** Live curl + 82 tests.
* **Why itâ€™s inefficient** `/openapi.json` was the 20:50 hole; **this PID 404**.
* **Recommended fix** Notes. Do not add restart 409 tonight.
* **Tradeoffs / Risks** â€”
* **Expected impact estimate** â€”
* **Removal Safety** â€”
* **Reuse Scope** web middleware

### 3) Quick Wins (Do First)

* Do nothing to the open GER40. No restart, no SL PATCH, no search.
* After flat: decide daily halt (yellow/red) â€” measured gap ~$122 vs 3%.
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
* Restart 409 + single-flight `_restarting` â€” only if operator wants the
  constitution enforced against the panel button.
* Numba simulate / O-1 sqlite split: still won't-do (2.57ms / 6.53ms; 2000-row
  cap unmeasured). Idle cycle already 3â€“7 ms.

### 5) Validation Plan

* Already green this pass: `tests/test_session_csrf_gate.py` (incl. openapi
  404), `test_opt_cancel_is_noticed_mid_sweep.py`,
  `test_hands_off_fields_are_not_api_writable.py`,
  `test_unused_production_names.py`, `test_shakeout_widens_the_next_stop.py`,
  `test_panel_first_screen_shows_positions.py` â€” **82 passed**.
* Before/after any payload slim: `GET /api/state` capacity keys the panel
  actually reads (`test_panel_account_cards_keep_their_fields`,
  `test_unread_payload_keys_are_gone`).
* Before restoring a halt: measure start_balance Ã— pct vs today's deal times
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
  * **The Exploit:** POST `/api/system` no Origin â†’ **403**. POST panic
    `Origin: http://evil.example` â†’ **403**. Cookie-less `/api/state` â†’ **401**.
  * **The Fix:** None. SameSite=Strict + Origin=Host still on.

* **Hands-off allowlist** (Severity: held on this PID; G6 closed)
  * **Location:** `app.py:418-429` `_OPERATOR_*`
  * **The Exploit:** Live POST GER40 `risk_percent` / `sl_atr_mult` / `strategy`
    / `max_positions` â†’ **400**. System `daily_loss_pct` / `size_by_edge` /
    concurrent / total â†’ **400**. `.../reset` 400. `/api/ai` GET **404**.
    `/api/logs/clear` **404**.
  * **The Fix:** None. Claude 20:50 G6 (old PID accepted `risk_percent`)
    does **not** reproduce here.

* **Restart with open tickets** (Severity: Medium, operator-visible)
  * **Location:** `app.py:1987-2016`
  * **The Exploit:** Panel restart does not 409. 21:20 (5 tickets) and
    21:43 (3 tickets) landed. First-sights `open_original_sl` to current
    trail. Killed the 160k search.
  * **The Fix:** 409 if `engine.positions` non-empty **plus** a
    `_restarting` latch. **Not applied** â€” operator used this door tonight.

* **Secrets / pickle / second initialize:** Claude 20:50 dirty-tree grep
  `eval` / `exec` / `pickle` / `shell=True` **0**. Subprocess restart.bat is
  a fixed template. Not re-diffed line-by-line this pass.

#### **Observations:**

* Static `/` 200 without cookie (must â€” sets the cookie). HTML 23122 bytes.
* Panel DOM: day before positions before capacity, no `panel-narrow`, no
  `tabs-spacer`.
* `autostart_mt5` True is an allowlisted connection-card dial, not a new Ai port.

#### AGENTS.md rewrite â€” **not shipped**

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
| Dead `risk_sembol_limiti` 209 still incrementing | **Frozen.** Claude 22:22 live GET: totals 209, sqlite since â‰ˆ16.08, producer gone from `can_open`. Live incrementing: spread 241, ters 148, bar_bosluk 45, emir 12, bar_doldu 8, lot 4. Dormant: `risk_toplam_limit` 0, `risk_kova_limiti` 0. Do not reset unasked. |
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
| alpha_trend / mavilim / st_trend / macd_flip / t3_stoch / wavetrend_flip / micro_rev | Retired. **8 families (arsiv).** |
| `original_sl` RAM-only | **Landed.** `note_fill` writes `open_original_sl`; `track()` restores before first-sight. Pre-patch tickets still first-sight. Do not persist the fallback. |
| Fill-verify blocks `_cycle` | **Landed.** Immediate peek. `defer_verify=True` side thread. Do not delete the sleeps. |
| Supervisor 14d inside `_cycle` | **Landed.** `_kick_supervisor_review` daemon; gate prevents stacking. |
| `/api/state` full `symbol_payload` | **Landed.** `symbols_sig`; panel refetches `/api/symbols`. |
| Scale-out remain / second `info` | **Landed.** Clamp `filled` â‰¤ position. |
| Duplicated trail/BE math | **Landed.** `exits.overlay_stop`. |
| Opt `copy_rates` holds the lock | **Landed (chunked).** `_BAR_FETCH_CHUNK=2500`. No second `initialize()`. |
| Short MFE ask pad / `_merge` `trade_mfes` / LOG CR/LF | **Landed.** |
| Incumbent holdout replayed twice | **Landed.** `_fresh_incumbent_holdout` memo. |
| Origin-less POST | **Landed.** Every mutation needs Origin. |
| Snapshot account / day_stats / capacity TTL | **Landed.** |
| `el({html})` XSS | **Landed.** Branch removed. |
| Incremental IndicatorCache / Numba simulate | **Closed (measured won't-do).** 2.57ms / 6.53ms. |
| Flatten autopsy profit / left_on winners-only | **Landed.** |
| `tf_lock_status` / panel flatten `reason=` / opt npy share | **Landed 12:50â€“13:05.** |
| Calendar reopt / GET `/api/ai` / `POST /api/logs/clear` | **Landed 26.08 strip.** Panel `STATE.ai`; Temizle DOM-only. |
| `backtest.run` / `mae_close` / `_stamp_values_match` / `_tf_seconds` | **Landed.** Pin `tests/test_unused_production_names.py`. |
| Unread payload (`pending_exit_fields`, `tried[]` net_r, walk_forward `raw_score`/`holdout_bars`, info `contract_size`, supervisor `saved_at`, `partial_close_lots`, `primary_max_spread_atr`) | **Landed.** Claude 18:05/18:45: production callers **0**. |
| Harvest-on / trail-to-entry clamp / BE 0.5 | **Won't-do.** Paper off beats harvest shapes; GER40 BE@0.5R = âˆ’32 R. |
| `max_positions` 3â†’1 from one red ticket | **Won't-do.** US30 slot-2 overlap +4.62 R (n=12). Yellow. |
| Adverse-fill entry gate (`fill_vs_signal_close_r`) | **Won't-do.** WF fill-next-open; Claude 18:45 threshold scan is a curve-fit. |
| One-day `blocked_entry_hours` | **Won't-do.** UTC+3 invented a 00:00 SL bucket; gmtime has no 00 hour. |
| `/api/state` during a 14-worker search (148s) | **Landed.** Snapshot serves last cycle book while `optimizer.busy`. Halt/flatten still wait in `_cycle`. No second `initialize()`. |
| F-1 `entry_block_events` skipped 45s debounce | **Landed.** `_flush_entry_blocks` window covers both blobs. `force=True` on reset/delete. |
| MISS-1 `shutdown()` skipped the ring | **Landed.** `shutdown()` force-flushes the ring after join. |
| MISS-2 force-flush before `thread.join` | **Landed.** Ring flush runs after join. |
| MISS-3 `execution.flush()` before `thread.join` | **Landed.** Same place as the ring: after join. Autopsies stay cycle-local (no shutdown flush). |
| 900s integrity full `required_bars` with no new bar | **Landed.** `bar_window_pins` (oldest + last closed). Full copy on mismatch / missing cache. Middle-bar hole with both ends unchanged is the remaining miss. |
| O-1/O-2/O-3 settings blob rewrite | **Won't-do until 2000-row cap is measured.** F-1 closed the hot caller. Live sqlite owner; schema split is a restart-sized migration. |
| Numba `simulate` | **Won't-do until `OPT_FIELDS` grid 3Ã—.** 6.53ms measured. |
| Empty `compute()` series | **Landed.** Fail-closed `_no_signal` before the family builder. Live `bars()` never hands n<2. |
| `_is_improvement` / `_maybe_reoptimize` names | **Landed.** Apply gates are `_slice_ok`, `reject_reason`, `_beats_incumbent`. Calendar auto-queue is gone. Quarantine still uses `_queue_reoptimization`. |
| Family-count docs (11) | **Landed.** `tests/test_docs_match_the_code.py` scans TR `N aile` and EN `N families`. Skip only `(arsiv)`. |
| Deferred fill books live `last_bar` | **Landed.** Pending carries send-time source+bar. Drain marks those; clears live signal only if `last_bar` is still that bar. Pin `tests/test_deferred_fill_keeps_a_newer_bar_signal.py`. |
| Quarantine `last_reopt_attempt` before `start()` | **Landed.** Stamp only when `start()` returns ok (or a non-dict test double). Failed start no longer burns `reopt_retry_cooldown_hours`. |
| Saved `opt_params` kept retired families | **Landed.** `Store.opt_params()` and `save_opt_params()` drop names/grids/caps not in `STRATEGIES`. Live blob POSTed 27.08 00:50 to every family then in `STRATEGIES` (search already skipped them). Pin `tests/test_opt_params_drops_retired_families.py`. |
| Combo bar used global `max_combos` | **Landed.** `run_combo_budget` sums `family_max_combos` Ã— refine. Live `stoch_flip` 28800 made the bar 2.38M against ~5.27M real. Next process; do not PATCH caps mid-run. |
| Hands-off panel / cost toggles off UI | **Landed (UI).** Values stay on Store. MT5 path + backup dir/secondary/keep restored. Exits readout. |
| Shakeout SL floor | **Landed (disk).** Next entry floors SL to 2.0 after 3/10 original-SL deaths. Trail not scaled (option 3, docstring). This PID still old emit. |
| Opt prefetch bars / poll drops `top`/`baseline` | **Landed (disk).** This PID still fat blob + no prefetch log. |
| Dead `SECTIONS` / `optFieldVisible` / `loadSchema` / ghost `ADVANCED_SECTIONS` | **Landed (panel JS).** `GET /api/schema` kept. Pin `test_dead_symbol_guts_ui_is_gone`. Dead AI settings form builder gone; `AI_SETTING_FIELDS` stays for FIELD_HELP. |
| Ad-hoc scripts appending `logs/micofx.log` | **Landed (disk).** `LogBus._disk` off until `run.py` `LOG.enable_disk()`. Pin `test_disk_is_off_until_the_live_launcher_enables_it`. This PID still old always-on write. |
| Unread snapshot crumbs (`day.cash_flow` / `floating` / `bot.poll_interval_sec`) | **Landed (disk).** Panel already used `day.realised` / `account.profit` / Store poll. Pin `test_unread_payload_keys_are_gone`. |
| `STOCH_MID` unused constant | **Landed.** Pin `test_dead_repair_helpers_are_gone`. |
| Hands-off fields still Origin-POST writable | **Landed (disk).** HTTP allowlist = panel dials only (sizing/sessions/enabled; opt lookback/refine/max_combos). Family/TF/exits/magic/grid/reset â†’ 400. Pin `test_hands_off_fields_are_not_api_writable`. Apply() unchanged. |
| Dead opt-grid / `SWING_OVERLAY` / empty `SYS_DANGER_NOTES` | **Landed (disk).** Client + `GET /api/opt/params` `swing_overlay` dropped together. `SYS_FIELDS_ADVANCED = []` stays (FIELD_HELP pin). `saveOptParams` still refuses empty `body.grid = {}`. Pin `test_search_gate_internals_are_not_on_the_panel`. |
| `_FALLBACK_PATHS` empty constant | **Landed.** Gone from `mt5client.py`. Pin `test_unread_payload_keys_are_gone`. |
| `cash_flow_since` every cycle | **Landed (disk).** 30s TTL while balance unchanged; `None` does not stamp TTL; deposit-shaped jump fetches immediately; rollover resets. Pin `test_cash_flow_is_not_fetched_every_cycle`. Two-call merge still won't-do. |
| Unread payload crumbs (`session_clock_skew_hours`, `execution.tracked`, snapshot `day.wins`) | **Landed (disk).** Panel keys only on snapshot `day`. `t3_kind` stays on `as_dict` (status contract). |
| `backup_dir_allow_unc` HTTP-writable | **Landed (disk).** Dropped from `_OPERATOR_SYSTEM_FIELDS`. Same-request latch â†’ 400. Store flag still opens UNC. Pin `test_unc_latch_is_not_http_writable`. Runtime gate in `backup.py` unchanged. |
| F5 unread `opt.results[].tried` | **Landed (disk).** `status()` pops `tried` with `top`/`baseline`. Live job / opt_runs keep it. Pin `test_opt_poll_drops_unread_rankings`. |
| F3 GER40 900-bar / 2023 holdout pin | **Landed (disk).** `capture()` refuses n<5000 or last bar >14d; old file stays. Do **not** recapture while tickets are open. Next gece writes a fat window. |
| F10 Windows spawn orphans | **Landed (disk).** Sweep now matches `spawn_main` as well as `--multiprocessing-fork`. Do **not** kill the live 14 workers while the book is open; next boot/resweep. Pin `test_orphan_sweep_stays_in_its_own_venv`. |
| F14 sweep PowerShell never parsed | **Landed (disk).** Where-Object closer is an f-string; `{`/`}` balanced. rcâ‰ 0 â†’ `gece_restart.say`. Do **not** invoke by hand while tickets are open; next gece/restart actually Stop-Process. |
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
| Capacity NÃ— margin / `_harvest_view` autopsy | **Won't-do until measured.** TTL 3s already; n=23 vs cap 2000. |
| Daily-loss UI + `daily_loss_flatten` unread | **Landed (disk).** Flatten always when stored halt fires. `daily_loss_pct=0` is operator cancel (no halt). Pin `test_daily_loss_halt_actually_flattens`. |
| Concurrent 1R unread + chip gone; margin on Sistem | **Landed (disk).** `can_open` does not read `max_concurrent_risk_pct`. HTTP: `max_margin_usage_pct` writable. `_note_risk_capacity` no-op. |
| Symbol card hours-only; `risk_percent` HTTP 400 | **Landed (disk).** `POSITION_SECTION` gone. Stored % still sizes lots. Pin `test_account_sizes_the_book` / `test_position_sizing_is_not_writable`. |
| AI Global Lot Carpani card | **Landed (panel).** Five AI cards one row. Throttle still on GÃ¼n `lot x` + table. Not system `lot_multiplier`. |
| `_symbol_daily_halt` getattr | **Landed.** `:4168` `getattr(..., 0.0)`. `:4198` still naked (field always on `SymbolConfig`). |

### Still open

Unpaid measured won't-dos: Numba if `OPT_FIELDS` 3Ã—; O-1 if 2000-row autopsy
cap is hot. Harvest-on / BE 0.5 / `max_positions`â†’1 stay **won't-do**
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


**Live (16:40, then Claude 16:46):** day **âˆ’$169.19 / 25 / WR 20%**.
GER40 **8/0 âˆ’$122.66**. Idle `last_cycle_ms` **5.4**. No 27.08 ERROR.

Claude 16:4x: claim 3 JS "Safe delete" list is **wrong** (would
`ReferenceError` / miss Python). `SWING_OVERLAY` is assigned but
unread (`#opt-grid` gone). Cash_flow waste is **every-cycle
frequency**, not the two-call shape. GER40 exits are **6 sl + trail
+ flatten**, not 6/6 orig-SL.

---

## 27.08 20:40 â€” Evening-strip Aâ€“Z (Claude 20:35 + live book + dirty tree)

Independent Cursor pass. Did **not** patch, restart, cancel the search, or
commit. GET `/` then `/api/state` `/api/symbols` `/api/analysis/*`.
Claude 20:35 arithmetic (100 slots / ~80% theoretical 1R) **accepted**.
`last_cycle_ms` **7â€“9** (search busy; snapshot last-cycle book).
`last_error` empty. **No `ERROR` line on 27.08** in `logs/micofx.log`.

**Live (20:39 broker):** demo 61562752. Balance **$1944** / equity **$1966**
/ floating **+$21**. Day realised **âˆ’$200.15** / 30 closes / WR **20%** /
`pnl_pct` **âˆ’8.26%**. Halt **false** (`daily_loss_pct=0`). AI enabled,
`risk_scale` **0.60** enforced. 7 open: NAS100Ã—2 buy, US30Ã—2 sell,
GER40 buy, JPN225 buy, SpotBrent sell. All have broker SL. Reverse
signals on GER40/JPN/NAS blocked (`ters yonde acik pozisyon var`).
**`opt.state=running`** source=manual `apply_best` 160000/3081600.

Book families: 4Ã— `stoch_flip`, XAU `burst` M15, Brent `parabolic_flip`
M15. Unused live: `mtf_pullback` `dual_t3` `t3_flip` `aroon_flip`
`ichimoku`. All `risk_percent=0.8`, `symbol_daily_loss_pct=0`.
GER40 exits **1.0 / 0.3 / 1.2** (pending applied). Harvest off.
Partial on five names. `size_by_edge=True` still read. `lot_multiplier=1.0`.

Today cash: GER40 10/0 **âˆ’$142.38** (8 orig-SL + 2 trail, **âˆ’9.24 R**);
JPN225 11 **âˆ’$64.92** (âˆ’6.68 R, 6 orig-SL); US30 âˆ’$1.18; NAS âˆ’$0.60;
XAU **+$8.97**. Autopsy window n=229: SL 131 / trail 63 / flatten 35.
After-1h on SL: 75/131 through entry, 87 recovery â‰¥0.5 R (shakeout
thesis still live; not a silent patch).

### 1) Optimization Summary

* **Health:** Idle cycle is paid (~8 ms) even under a 14-worker search
  because `/api/state` serves the last cycle book. Today's âˆ’$200 is
  **book + operator cancel of the daily halt**, not a new engine leak.
  GER40 `stoch_flip` 1.00 ATR stop is eating the day (8 orig-SL). Dead
  `risk_sembol_limiti` is a **panel lie**, not a live gate.
* **Top 3 highest-impact (none is a silent CPU patch):**
  1. Keep the open book. Restart first-sights stops **and** would collide
     with a running `apply_best` search.
  2. After **flat only**: decide whether `daily_loss_pct=0` stays (day
     already âˆ’8.26% with no flatten). Restoring 3% is yellow/red.
  3. After quiet: drop or relabel historical `risk_sembol_limiti` /
     `risk_eszamanli` so Eleme Kapilari stops ranking a deleted gate #2
     (209 events / 73k retries). Reset vs mapping delete vs "kalktÄ±".
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
* **Why itâ€™s inefficient** Search scores `max_open_from_cfg` = **1**
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

* **Title** `daily_loss_pct=0` â€” day âˆ’8.26% with no halt
* **Category** Reliability / Cost (capital)
* **Severity** High (policy, not a bug)
* **Impact** Counterfactual: leftover default 3% of ~$2423 start â‰ˆ **$73**.
  Realised already **âˆ’$200**. Flatten-always is wired but never trips.
* **Evidence** `system.daily_loss_pct=0`, `day.halted=false`,
  `DailyGuard.check` `risk.py:263` requires `> 0`. Operator cancelled
  the panel dial 27.08 evening.
* **Why itâ€™s inefficient** N/A â€” intentional. The inefficiency is
  **communication**: capacity/brain still mention a limit that cannot fire.
* **Recommended fix** None unless the operator wants the brake back.
  Do not silently restore 3%.
* **Tradeoffs / Risks** A 3% halt would have flattened winners too
  (US30/NAS/XAU still trading).
* **Expected impact estimate** Would have capped today near âˆ’$73 vs âˆ’$200
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
  Live stacking: NAS100Ã—2 US30Ã—2 with leftover `max_positions` 5/5 unread.
* **Why itâ€™s inefficient** Historical counters look like a live gate.
  Same class as `daily_loss_flatten` visible-but-unread /
  `size_by_edge` hidden-but-on.
* **Recommended fix** Pick one after quiet: drop needles from
  `_RISK_BLOCK_KEYS`; or one-shot `POST /api/analysis/entry-blocks/reset`;
  or panel suffix "(kalktÄ±)". Do not reset during a search.
* **Tradeoffs / Risks** Reset wipes spread/ters history too.
* **Expected impact estimate** Zero latency. Stops a false #2 cause.
* **Removal Safety** Likely Safe (mapping) / Needs Verification (reset)
* **Reuse Scope** engine.py + panel analysis

* **Title** Search vs live stacking (paper 1, live 100)
* **Category** Algorithm
* **Severity** High (edge measurement)
* **Impact** Holdout/net R do not include overlapping same-side tickets.
  Live theoretical 100 Ã— 0.8% = **80% 1R** before AI 0.60 â†’ ~48%;
  `size_by_edge` (on, Ã—2.2 cap) can pull up. Margin 90% binds ~175
  lots at $10/pos â€” **100 binds first**. Claude 20:35.
* **Evidence** `max_open_from_cfg` returns 1. `max_total_positions=100`.
  `max_positions` leftover unread. Open 7 / concurrent risk **1.59%**.
* **Why itâ€™s inefficient** Two different products. Apply() of a 1-slot
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
* **Impact** Today âˆ’$142 / âˆ’9.24 R; window âˆ’$161 / âˆ’8.52 R (n=37).
  Shakeout 3/10 orig-SL â†’ next entry SL **2.0** (this PID has the helper).
  Floor wears winners (Cursor 19:10); does not save 8 already dead.
* **Evidence** Autopsy today GER40 8 `exit_reason=sl` with `sl==original_sl`.
  Live row `sl_atr_mult=1.0` trail 0.3/1.2 BE 1.5 partial 1.5. Open GER40
  SL **above** entry (trail in profit) â€” floor is next-entry only.
* **Why itâ€™s inefficient** Search prefers 1.0. Shakeout is a live overlay
  the grid never paid for. Trail 0.3 starts inside a 1.0 stop.
* **Recommended fix** Let the running search finish. Do not PATCH SL.
  Do not disable the floor. Three-arm diagnostic (gates/floor/both)
  stays designed, not a patch.
* **Tradeoffs / Risks** `apply_best` may write another 1.0 onto GER40
  on first flat.
* **Expected impact estimate** Floor: losers stay âˆ’1 R; winners haircut
  when 2.0 binds (qualitative, 19:10).
* **Removal Safety** Needs Verification
* **Reuse Scope** risk.shakeout_sl_atr_mult

* **Title** `size_by_edge` on, dial gone
* **Category** Maintainability
* **Severity** Medium
* **Impact** Lots still Ã— holdout net R / maxDD (`risk.py:335`).
  Panel has no switch. HTTP 400. Capacity footnote still prints it.
* **Evidence** `GET /api/state` `system.size_by_edge=true`. Claude 20:05
  asked if hiding it is a lie â€” **yes, still-read**.
* **Why itâ€™s inefficient** Operator cannot see the multiplier except
  in a capacity sentence.
* **Recommended fix** After quiet: either force `False` in Store
  (yellow â€” changes lots) or a read-only chip. Do not HTTP-open it.
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
* **Why itâ€™s inefficient** Agents/panel can still *see* dead knobs
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
* **Impact** 8 families (arsiv) in `STRATEGIES`. Live book uses 3
  (`stoch_flip` `burst` `parabolic_flip`). Search still pays the
  other 5 Ã— TF Ã— refine. Running job `strategies=[]` inherits the
  saved list â€” likely all 8.
* **Evidence** `models.py:538-541`. Combo bar 3.08M.
* **Why itâ€™s inefficient** Grid cost on families with no live
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
* **Impact** 131 SL; 75 through entry in 1h; 87 recovery â‰¥0.5 R.
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
* Pin Origin to loopback URLs (security #2) â€” not tonight.
* F1/F2 search-axis shrink only if the operator wants a redesign.

### 5) Validation Plan

* Idle: `last_cycle_ms` before/after any snapshot slim (now 7â€“9
  under search; 5.4 was idle 16:40).
* Book: day realised vs autopsy today cash (GER âˆ’142.38 matches).
* Gates: POST `risk_percent` / `max_positions` / `daily_loss_pct`
  â†’ 400 (this PID may still 200 until restart).
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
  tickets are open â†’ `stop(close_positions=False)` â†’ trail/BE dies;
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
* `aiHoursCell` hour strings unescaped â€” numeric hours only.
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
* `risk_percent` already 400 â€” keep.
* Known gotcha: this PID vs next-boot 400; running search + stacking.
* Do not paste the optimization/security prompts into AGENTS.md.

---

## 27.08 16:40 â€” Aâ€“Z hard test (book, dead surface, lock, HTTP, security)


Independent Cursor pass after HTTP=panel land. Did not re-open the closed
ledger. Live GET `/` then `/api/state` (session). `last_cycle_ms` **5.4**.
`last_error` empty. **No `ERROR` line on 27.08** in `logs/micofx.log`.
AI `risk_scale` **0.60** (daily-loss floor). Opt not busy.

**Live (16:40):** demo book. Day realised **âˆ’$157.75** / 23 closes / WR
21.7% / DD **âˆ’7.36%**. Floating ~flat. 4 open: GER40 buys #367303567
#367334015 #367492600 (live SL 2.0 / 0.5/2.2, pending 1.0/0.3/1.2) and
JPN225 sell #367498872 (+). Shakeout / prefetch / slim poll / HTTP 400
**not in this PID**.

### 1) Optimization Summary

* **Health:** Idle hot path is paid (5.4 ms). Today's losses are **book**,
  not a new engine leak: GER40 6/6 original-SL (âˆ’$111.22) and JPN225
  (âˆ’$63.15). XAU +$18.40 is the only real offset. Dual `history_deals_get`
  and unread `/api/state` crumbs are real code, **not** today's 5.4 ms.
* **Top 3 highest-impact (none is a silent CPU patch):**
  1. Keep the open book. Restart would first-sight stops **and** close the
     HTTP exit door on the same boot.
  2. After **flat + restart only**: confirm shakeout WARN, prefetch log,
     slim payload, HTTP 400 on family/exit, `raw/floor` vs `volume_min`.
  3. Dead opt-grid / `SWING_OVERLAY` / `SYS_DANGER_NOTES` JS â€” Safe delete
     when quiet. Maintainability, not latency.
* **Biggest risk if no changes:** Operational, not CPU. GER40 pending
  1.0/0.3/1.2 lands on flat via `apply()`. Shakeout lifts next-entry SL
  to 2.0; trail 0.3/1.2 has no floor and no HTTP PATCH after next process.
  Harvest-on / BE 0.5 / `max_positions`â†’1 stay won't-do.

### 2) Findings (Prioritized)

* **Title** GER40 original-SL cluster is the day
* **Category** Reliability (book, not code)
* **Severity** High (cash) / Low (code)
* **Impact** Closed âˆ’$111.22 of âˆ’$157.75. 6/6 unmoved ~1.0 ATR stops
  before the 11:29 panel bump to SL 2.0.
* **Evidence** Autopsy 23 rows = `day.closed_trades`. GER40 n=6 WR 0/6
  orig-SL 6/6. Live tickets still on 2.0/0.5/2.2. Pending queued 14:28.
* **Why itâ€™s inefficient** Not CPU. Six signals died on first-sight SL
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
* **Evidence** `_refresh_cash_flow` every `_cycle` â†’ `cash_flow_since`
  `engine.py:843` / `mt5client.py:1149`. `day_stats()` 5s cache miss â†’
  `deals_since` `engine.py:854` / `mt5client.py:1089`. Same day window,
  two filters (external types vs entry types). Older pass already named
  `day_stats` in snapshot; **cash_flow has no TTL**.
* **Why itâ€™s inefficient** Two IPC history pulls overlap. Correctness needs
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
* **Evidence** `_panel_terminal_flags` `engine.py:4061-4070` â€” busy-search
  reuses cache; idle poll always `terminal_flags()` â†’ `mt5.terminal_info()`
  `mt5client.py:571-575`. Positions/account already reuse the cycle book.
* **Why itâ€™s inefficient** Flags change rarely; poll is 3s.
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
* **Why itâ€™s inefficient** Dead branches after HTTP=panel.
* **Recommended fix** Delete the empty advanced loop, overlay flag, grid
  collect, reset click. Keep GET `swing_overlay` until JS gone, or drop
  both together.
* **Tradeoffs / Risks** None if HTML stays grid-free (pinned).
* **Expected impact estimate** Zero runtime.
* **Removal Safety** Safe
* **Reuse Scope** `app.js` + `GET /api/opt/params` flag

* **Title** Unread `/api/state` crumbs after the 15:16 strip
* **Category** Network / Frontend
* **Severity** Lowâ€“Medium
* **Impact** Payload size (this PID still fat; disk already dropped
  `cash_flow`/`floating`/`poll_interval_sec`)
* **Evidence** Panel never reads: `mt5.session_clock_skew_hours` (only
  `session_clock_warning`); `day.wins`/`losses`/`day_key`/`start_balance`;
  `states.*.last_bar`/`t3`/`t3_kind`/`signal_source`/`primary_signal`/
  `spread`/`last_signal_at`; `execution.tracked`. Live table uses
  `atr/adx/t3_rising/htf/k/d/signal/bars_ready/note/session/spread_atr`.
* **Why itâ€™s inefficient** JSON work every 3s for unused keys.
* **Recommended fix** Strip from `as_dict` / payload only. Keep engine attrs.
* **Tradeoffs / Risks** External GET `/api/state` readers (Claude panel
  probe). Pin like `test_unread_payload_keys_are_gone`.
* **Expected impact estimate** Qualifies the 99 KB â†’ ~35 KB claim; leftover
  crumbs are the rest.
* **Removal Safety** Needs Verification
* **Reuse Scope** snapshot

* **Title** `_FALLBACK_PATHS` empty constant + `SYS_DANGER_NOTES={}`
* **Category** Dead Code
* **Severity** Low
* **Impact** None
* **Evidence** `mt5client.py:21` never read. `app.js:1868-1878` `syncSysDangerNotes`
  no-op (empty map).
* **Why itâ€™s inefficient** Leftover scaffolding.
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
* **Why itâ€™s inefficient** Visibility â‰  lock leftover after HTTP=panel.
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
* **Why itâ€™s inefficient** Dead defense, not a leak.
* **Recommended fix** Keep. Apply() and allowlist regression still need them.
* **Tradeoffs / Risks** Deleting them re-opens the hole if allowlist slips.
* **Expected impact estimate** Zero.
* **Removal Safety** Needs Verification (do not delete)
* **Reuse Scope** `web/app.py`

* **Title** Capacity NÃ— `order_calc_margin` / tick under lock
* **Category** Concurrency
* **Severity** Medium (likely) â€” already TTL 3s
* **Impact** Lock vs `_cycle` when ticket/volume sig changes
* **Evidence** `engine.py:4072-4096`, `_CAPACITY_TTL=3s`. Not new; still
  the rebuild path when not `optimizer.busy`.
* **Why itâ€™s inefficient** 6 symbols Ã— margin+tick on sig change.
* **Recommended fix** Measure first. Do not add a second `initialize()`.
* **Tradeoffs / Risks** Stale lot gauges.
* **Expected impact estimate** Likely small on this 6-name book.
* **Removal Safety** Needs Verification
* **Reuse Scope** snapshot / `risk.py`

* **Title** `_harvest_view` full autopsy every poll
* **Category** CPU / Alloc
* **Severity** Low today (n=23; cap 2000)
* **Impact** `/api/state` CPU
* **Evidence** `engine.py:3975-4008` â†’ `trade_autopsy_report()` then drops
  rows, keeps aggregates. Called from snapshot ~3s.
* **Why itâ€™s inefficient** Builds `rows` then throws them away.
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
* Incremental `IndicatorCache` / Numba â€” still won't-do at 2.57 / 6.53 ms
  until grid 3Ã—.

### 5) Validation Plan

* Idle: `bot.last_cycle_ms` (now 5.4) and `/api/state` wall. No `ERROR`
  on the day file.
* After restart (flat only): shakeout WARN on next GER40 entry; prefetch
  log line; opt poll without `top`/`baseline`; HTTP 400 on `sl_atr_mult`
  / `grid` / reset; payload KB; log disk still writes from `run.py`.
* Dual history: count `history_deals_get` per `_cycle` vs per snapshot.
* Correctness: deposit cash_flow â‰  0 still disarms DailyGuard the same way;
  day `closed_trades` still matches autopsy n; fill-next-open WF unchanged.
* Panel: 13 chips / 7 tabs still render after JS delete.

### 6) Optimized Code / Patch

Not applied (operator: notes only). Candidates if asked:

* `saveOptParams` drop `[data-grid-key]` block; drop `SWING_OVERLAY` assign.
* `_OPERATOR_SYSTEM_FIELDS` minus `backup_dir_allow_unc`.
* `cash_flow_since` + `deals_since` share one raw history list.

### Strategy reverse (27.08 closed book)

Masada = winners only. R = `|entry âˆ’ original_sl|`. `mfe_r` not harvestable.
Keep-lines are `taze test`, not a live replay.

| Symbol | Family/TF | n | Cash | Orig-SL | Reverse |
|---|---|---|---:|---:|---|
| GER40 | stoch_flip M30 | 6 | âˆ’111.22 | 6/6 | Skip-all = +111 arithmetic, not WF. Pending 1.0/0.3/1.2 **unverifiable** (six already dead; 3 opens still on 2.0). |
| JPN225 | stoch_flip M15 | 9 | âˆ’63.15 | 5 | Search weaker, **not applied**. |
| US30 | stoch_flip M30 | 5 | âˆ’1.18 | 3 | Afternoon M30. Slot-2 cut stays won't-do. |
| NAS100 | stoch_flip M30 *now* | 2 | âˆ’0.60 | 1 | Both closes were **mtf_pullback**. New family: 0 closes. |
| XAUUSD | burst M15 | 1 | +18.40 | 0 | Kept (age 48h). |
| SpotBrent | parabolic_flip M15 | 0 | 0 | â€” | 4 SIGNAL, **no** today block log. Do not invent misses. |

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
won't-do. Harvest / BE 0.5 / max_positionsâ†’1 won't-do. Adverse-fill gate
won't-do. Calendar reopt gone. `GET /api/schema` kept on purpose.
`AI_SETTING_FIELDS` kept for FIELD_HELP. 409 exit guards kept. Apply()
still writes `OPT_FIELDS`. Fill-verify sleeps stay. No second
`initialize()`.

---

## 27.08 15:16 â€” Aâ€“Z hard test (dead UI, PnL reverse, API, security)

Independent Cursor pass. Did not trust 26.08 21:57: grepped retired
families, unused JS, Origin, live GET `/` then `/api/state`, cycle ms,
today's ERROR lines, dirty-tree mutation surface. Claude 15:03 already
cleared readout+queue and Drive backup; this pass adds leftover UI and
per-symbol reverse.

**Live (15:16):** demo `61562752` @ Pepperstone-Demo. Bot running, MT5
connected, `last_cycle_ms` **4.4**, cycle 9508, `last_error` empty.
4 open, floating **+$22**. Day realised **âˆ’151.15** / 17 closes / WR
17.6% / DD **âˆ’6%**. AI enabled, `risk_scale` **0.71**. `max_margin_usage_pct`
**90**. Harvest off. **No `ERROR` line on 27.08** in `logs/micofx.log`.

### 1) Optimization Summary

* **Health:** Idle hot path is still paid (4.4 ms). Retired families
  fail-closed. Search/snapshot lock reuse already landed. Today's
  losses are **book**, not a new engine leak: GER40 6/6 original SL
  (âˆ’111$), JPN225 âˆ’51$, US30 âˆ’12$; XAU +18, NAS +5. Shakeout floor
  exists on disk for the next GER40 entry; this PID does not load it.
* **Top 3 highest-impact (none is a silent CPU patch):**
  1. Keep the running search and the open book. Restart/cancel would
     drop hours of combo work and first-sight stops.
  2. After **flat + restart only**: confirm shakeout WARN, prefetch
     log, slim opt poll, `raw/floor` vs `volume_min`.
  3. Delete dead panel blobs (`SECTIONS`, `optFieldVisible`) when the
     book is quiet â€” maintainability, not latency.
* **Biggest risk if no changes:** None on the idle path. Operational:
  GER40 pending 1.0/0.3/1.2 lands when two tickets close; floor still
  overlays SL. That mix is **accepted** (option 3). Harvest-on / BE 0.5
  / `max_positions`â†’1 stay won't-do.

### 2) Findings (Prioritized)

* **Title:** Dead symbol-guts UI (`SECTIONS` / `optFieldVisible`)
* **Category:** Frontend / Maintainability
* **Severity:** Medium (agent trap), Low (runtime)
* **Impact:** Smaller `app.js`, fewer false "restore Ileri duzey" PRs
* **Evidence:** `SECTIONS` `1020:1128:micofx/web/static/app.js` â€”
  definition only. `optFieldVisible` `1130:1137` never called.
  `buildSymbolCard` maps POSITION + EXIT readout + sessions only.
* **Why itâ€™s inefficient:** ~50 field defs + schema fetch exist only
  so a removed advanced card can hide axes.
* **Recommended fix:** Delete `SECTIONS`, `optFieldVisible`, and the
  one-shot `loadSchema` if nothing else reads `SCHEMA`. Keep
  `GET /api/schema` for tests.
* **Tradeoffs / Risks:** Help/schema tests scan `SECTIONS` keys â€”
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
* **Why itâ€™s inefficient:** Next agent "completes" the floor/panel.
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
* **Why itâ€™s inefficient:** Not CPU. Confusion: UI hide â‰  API lock.
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
  `2.2 (kuyruk 1.2)`. Today âˆ’111$ / 6 original SL. Docstring option 3.
* **Why itâ€™s inefficient:** Not inefficient â€” temporary overlay.
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
* **Why itâ€™s inefficient:** Tight spread is the real filter; do not
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
* **Why itâ€™s inefficient:** Tiny ints every 3s.
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

* Comment fix: `ADVANCED_SECTIONS` â†’ actual card shape (one line).
* After **flat restart**: measure shakeout WARN on disk, prefetch
  `Barlar indirildi`, opt poll payload drop, `raw/floor`.
* Do not PATCH margin 90, harvest, BE, flatten, cancel.

### 4) Deeper Optimizations (Do Next)

* Delete `SECTIONS` + `optFieldVisible` + unused schema load (panel
  quiet). Update field-help test.
* Numba / O-1 still gated on measured 3Ã— grid / 2000-row autopsy heat.
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
  is the truth (âˆ’151.15).

### 6) Optimized Code / Patch

None this pass. Operator: **do not implement** until Cursor OK after
Claude's independent scan.

### Per-symbol reverse (evidence only)

| Sym | Family/TF | Today $ | Structural note |
|---|---|---|---|
| GER40 | stoch_flip M30 | âˆ’111.22 (6 SL) | Floor ON; pending 1.0/0.3/1.2 |
| JPN225 | stoch_flip M15 | âˆ’51.20 (7) | Slots 3/3; AI ok |
| US30 | stoch_flip M30 | âˆ’12.14 (2) | Spread+slot; overlap slot stays |
| NAS100 | mtf_pullback M30 | +5.01 | Unvalidated stamp; watch PF 0.58 |
| XAUUSD | burst M15 | +18.4 | max_pos 1; partial 0 |
| SpotBrent | parabolic_flip M15 | 0 closed | Fill 13%; spread@cap |

Unused live families: `dual_t3`, `t3_flip`, `aroon_flip`, `ichimoku`.
Won't-do: harvest-on, BE 0.5 (âˆ’32 R GER40), max_positions 1, adverse-fill
gate, cost-toggle off engine (0/909 maliyet blocks).

### SECURITY AUDIT: dirty tree vs HEAD `122e434`

**Risk Assessment:** Low

#### **Findings:**
* None Critical/High. `mt5_terminal_path` â†’ `Popen([exe])` list-form,
  missing file `None` (Claude 14:5x). Origin CSRF unchanged. No
  secrets in backup Drive path. Hands-off keys remain POST-able â€”
  operator asked hide not lock.

#### **Observations:**
* Overlay PATCH mid-trade still allowed (not in `EXIT_RISK_FIELDS`).
* `backup_dir_secondary` Google Drive path contains `Drive'Ä±m` â€”
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
realised **âˆ’213.22$** (59 closes, WR 30.5%). `ai.risk_scale` 0.6
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
     trip (`OPT_FIELDS` 3Ã—; 2000-row autopsy cap actually hot).
  3. Do **not** restart while these 5 tickets are open â€” disk already
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
* **Impact:** Maintenance â€” agents planning work off comments would
  resurrect calendar auto-queue.
* **Evidence:** `optimizer.py` apply-age comment and
  `tests/test_apply_age_guard.py` / `tests/test_scan_skips_disabled.py`
  module docs named `supervisor._maybe_reoptimize`. Function does not
  exist. Live path is `reject_reason` + `reopt_min_age_hours` on apply;
  quarantine queues via `_queue_reoptimization`.
* **Why itâ€™s inefficient:** Copy-paste drift after calendar reopt was
  stripped. Same class as `_is_improvement` (MISS-4).
* **Recommended fix:** Point comments at `reject_reason`. **Done this
  pass.** AGENTS gotcha added.
* **Tradeoffs / Risks:** None â€” comment-only.
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
* **Evidence:** Armed task `MicoFX Gece Opt 0005` â†’
  `cursor/gece_opt.py` (gitignored). Waits for 0 positions, aborts if
  still open after 20 min **or** local hour â‰¥ 01:00. Six names.
  Session flatten historically ~23:54; first fills ~01:05. JPN225
  48h gate will refuse apply (`force=false`).
* **Why itâ€™s inefficient:** 14 workers hold the MT5 `RLock` for
  `copy_rates` chunks. Panel `/api/state` already serves last cycle
  book while `optimizer.busy`. Halt/flatten still serialize on `_cycle`.
* **Recommended fix:** Do not start the search from this chat while
  n_pos > 0. Leave the armed task. Do not `force=true` on JPN225.
* **Tradeoffs / Risks:** Skipping the night search leaves old configs
  (NAS100/GER holdout age already called out). Starting it with opens
  blocks management.
* **Expected impact estimate:** 148s lock hold measured 26.08 on a
  prior search â€” panel hung before snapshot reuse; now it does not.
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
* **Why itâ€™s inefficient:** Full `required_bars` every 900s with no
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
* **Why itâ€™s inefficient:** Two names for one set. Merging would
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
  `GET /api/schema` (was 2.1 KB Ã— 12 `sorted()` on every poll).
  Symbol rows live on `/api/symbols` + `symbols_sig`. Hidden-tab
  poll is 6s (`app.js`).
* **Why itâ€™s inefficient:** `supervisor.status()` rebuilds 6 rows
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
* **Category:** Dead Code (negative finding â€” do not strip)
* **Severity:** n/a
* **Impact:** Stripping these would break tests and CSRF/session
  probes, or hide operator columns.
* **Evidence:**
  * `GET /api/system`, `GET /api/positions`, `GET /api/logs` +
    download â€” tests + panel POST/download. Panel reads
    `STATE.positions`; GET stays for empty-book honesty.
  * `sessions.broker_epoch` â€” inverse of `server_datetime`; 0
    production call sites, 4 tests. Clock helper, not dead.
  * Payload keys `captured`, `raw_lot`, `trail_improves_at_r`,
    `expected_trades`, `actual_trades`, `config_age_days` â€” tests
    and/or panel.
  * `_SYMBOL_RISK_BOUNDS` dict stays; only `partial_close_lots`
    **entry** is gone.
  * Overlay fields `breakeven_at_r` / `partial_at_r` /
    `harvest_at_r` (0 = off) stay. Not `OPT_FIELDS`.
* **Why itâ€™s inefficient:** It isnâ€™t. Earlier unused-name strip
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

* Comment trap `_maybe_reoptimize` â†’ `reject_reason`. **Done.**
* AGENTS: pin identity + calendar-name gotcha. **Done.**
* Do **not**: merge TIMEFRAMES, split `/api/state`, strip
  `broker_epoch`, restart with 5 opens, start the 00:05 search from
  this chat, re-add Numba / O-1 / harvest-on / max_positions 3â†’1.

### 4) Deeper Optimizations (Do Next)

* **Numba `simulate`:** won't-do until `OPT_FIELDS` grid 3Ã—. Measured
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
  tonight â€” compare `bot.last_cycle_ms` after the next restart (disk
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
* Correctness: 8 families (arsiv) Ã— TIMEFRAMES still fail-closed on unknown
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

Working tree vs HEAD is net **âˆ’1213** on `micofx/`+`tests/` (54 files,
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
  * **Location:** `store.purge_orphan_history` â€”
    `DELETE ... NOT IN ({placeholders})` with `keep` bound as params.
  * **The Exploit:** values are `?`-bound; only the count of `?` is
    interpolated. Not SQLi.
  * **The Fix:** none.
* **Secrets:** no new credentials in the diff. Session token is
  `secrets.token_urlsafe(24)`, HttpOnly, SameSite=Strict, not in HTML.

#### Observations:

* `GET /api/system` remains â€” CSRF tests hit it. Account-lock fields
  still refused on `POST /api/system` (door is `/api/account-lock`).
* Web handlers still do not import `MetaTrader5`.
* Pydantic bodies `forbid` extra fields (existing tests).
* Do not restore `GET /api/ai` or ring-wipe `POST /api/logs/clear`.

### AGENTS.md

Not rewritten. Signal density already at the quality bar. Two
gotchas added this pass (pin identity; `_maybe_reoptimize` gone).
Did not duplicate MASTER_PROMPT Â§19, README, or the closed ledger.

---

## 26.08 19:12 â€” live after restart + opt/sec (no further patches)

Operator asked restart then re-test, then this audit into this file.
Restart **19:10:49** â†’ MT5 **19:10:58**. Log: `Restart: magic ile 8 acik
ticket devam ediyor` â€” same eight tickets as pre-restart snapshot.
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
are in the live process (`last_cycle_ms` ~4â€“11, not 148). Dead-route
strip is live (404s). Remaining unpaid items are the same three
measure-first leftovers: 900s full integrity fetch, Numba if grid 3Ã—,
settings-blob rewrite (O-1/2/3).

Top 3 unpaid:

1. 900s no-new-bar still full `copy_rates` (I/O) â€” stamp-only unverified.
2. `Store.set_setting` full JSON blob rewrite (DB) â€” F-1 closed the hot
   caller; leftover is autopsies/execution_samples, not entry events.
3. Visible-tab innerHTML rebuild (Frontend) â€” `viewPulse` skip exists.

Biggest risk if unchanged: a 900s integrity pass on M5 US30 still holds
the MT5 lock for a chunked full window. Idle `last_cycle_ms` stays low.

### 2) Findings (Prioritized)

* **Title:** 900s integrity still copies full `required_bars`
* **Category:** I/O
* **Severity:** Low (idle) / Medium (6 symbols Ã— M5)
* **Impact:** Lock hold, MT5 IPC
* **Evidence:** `_BAR_INTEGRITY_REFRESH = 900`; `due or integrity` then
  `client.bars(..., need)`. Chunked. Live last_cycle_ms 3.7â€“10.6 so this
  is not the current cycle cost.
* **Why:** Stamp/length check would refuse a silent hole; full copy is
  the hammer.
* **Recommended fix:** Stamp-only integrity; full fetch on mismatch.
  Needs a truncated-history test. **Not this pass.**
* **Tradeoffs:** Wrong stamp API â†’ missed holes.
* **Expected impact:** Rare 900s spike gone.
* **Removal Safety:** Needs Verification Â· **Reuse Scope:** `engine.py`

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
* **Removal Safety:** n/a Â· **Reuse Scope:** `store.py`

* **Title:** Search-stale snapshot (landed, now live)
* **Category:** Concurrency / Caching
* **Severity:** n/a (closed)
* **Evidence:** 8 tickets survived restart; idle state 10.6 ms. Not
  re-measured under a 14-worker search this pass (book open â€” do not
  start a search).
* **Removal Safety:** Safe (tests pin) Â· **Reuse Scope:** `engine.snapshot`

### 3) Quick Wins (Do First)

None unpaid that is Safe without identity tests. Do not restore
`POST /api/logs/clear` or `GET /api/ai`.

### 4) Deeper Optimizations (Do Next)

Stamp-only 900s integrity. Own table for entry-block events only if
F-1 p90 still hurts in a blocked session. Numba if `OPT_FIELDS` 3Ã—.

### 5) Validation Plan

* Idle: `bot.last_cycle_ms` already 3.7â€“10.6 post-restart.
* Search stall: flat book, 14-worker job, `GET /api/state` p95. Not
  tonight (8 opens).
* F-1: blocked-entry session â‰¥200 cycles; `entry_block_events` writes
  â‰¤1 per 45s.
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
* 8/8 tickets `managed=True` after restart â€” first-sight did not steal
  trail as original_sl (persisted blob).
* `search_busy` callable is in-process only; not an HTTP knob.

---

## 26.08 18:50 â€” Cursor opt + security (dirty tree, no patches)

Prompt: full optimization + staged-diff security. **No code fixes this
pass** (standing: write here, do not implement unasked). Live book
open (7 tickets). Harvest `0/0` all six. Opt idle.

### 1) Optimization Summary

Health: **good for a 3s-poll localhost bot**. Hot-path TTLs, lock
chunking, symbol_sig, npy mmap, dead-route strip already landed.
Remaining cost is **shared MT5 `RLock` during search** (measured), not
Python loops on `_cycle` (last_cycle_ms 7â€“72 this evening).

Top 3 unpaid (all previously open; no new Critical):

1. `/api/state` stalls 148s under a 14-worker search (Concurrency / I/O).
2. 900s integrity full `copy_rates` even with no new bar (I/O) â€” stamp-only unverified.
3. Panel still rebuilds innerHTML on pulse when the tab is visible (Frontend) â€” `viewPulse` skip exists; remaining cost is the visible tab.

Biggest risk if unchanged: operator panel **looks dead** during a
manual search; they restart mid-book. Not a silent money bug.

### 2) Findings (Prioritized)

* **Title:** `/api/state` shares the MT5 lock with opt workers
* **Category:** Concurrency / I/O
* **Severity:** High (during search only; idle last_cycle_ms ~7)
* **Impact:** Panel latency; operator may restart
* **Evidence:** AGENTS gotcha; SCAN-2 148s; `snapshot()` â†’ `_panel_positions` â†’ `client.positions()` under `RLock`. Workers `copy_rates` in chunks but still the same lock.
* **Why itâ€™s inefficient:** One lock, two audiences (3s UI vs 14 fetchers).
* **Recommended fix:** Serve-stale snapshot / skip-lock when `opt.state==running`. Identity tests first. **Not** a second `mt5.initialize()`.
* **Tradeoffs:** Stale positions for minutes; halt path must stay fresh.
* **Expected impact:** Panel p95 during search: 148s â†’ ~TTL (2â€“3s). Idle: 0.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** `engine.snapshot` / `MT5Client`

* **Title:** 900s no-new-bar still full `required_bars` fetch
* **Category:** I/O
* **Severity:** Low (idle) / Medium (6 symbols Ã— M5)
* **Impact:** Lock hold, MT5 IPC
* **Evidence:** `_BAR_INTEGRITY_REFRESH = 900`; `integrity = now - state.last_fetch > 900` then full bars. Chunked. No compute.
* **Why:** Stamp/length check would refuse a silent hole; full copy is the hammer.
* **Recommended fix:** Stamp-only integrity; full fetch on mismatch. Needs a test that a truncated terminal history is detected.
* **Tradeoffs:** Wrong stamp API â†’ missed holes.
* **Expected impact:** Rare 900s spike gone; correctness-sensitive.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** `engine.py` bar fetch

* **Title:** Dead-code strip this tree (already on disk, not a new patch)
* **Category:** Maintainability / Dead Code
* **Severity:** n/a (landed)
* **Impact:** âˆ’2k lines; fewer lying payloads
* **Evidence:** `git diff --stat` 39 files. Claude 18:05/18:45 callers **0**.
* **Reuse Scope:** repo-wide
* **Removal Safety:** Safe (pinned)

* **Title:** Adverse-fill / expensive-spread entry gates
* **Category:** Algorithm (yield, not runtime)
* **Severity:** Low as a *perf* item; High as a *wrong-fix* risk
* **Evidence:** Claude 18:45. Q4 `fill_vs_signal_close_r>=0.05` n=35 net âˆ’25 R vs Q1â€“Q3 +1.45 â€” but t=0 drops 62% of trades for +2.87 R; t>0.05 remaining set goes negative. `spread_atr` Q2 +9.42, Q1 âˆ’2.46 (non-monotonic). `block_high_cost` already at 18%.
* **Recommended fix:** Do nothing. Holdout cannot see fill_vs.
* **Removal Safety:** n/a
* **Reuse Scope:** do not add

### 3) Quick Wins (Do First)

* None unpaid that is Safe without identity tests. Strip already landed.
* Do not restore `POST /api/logs/clear` or `GET /api/ai`.

### 4) Deeper Optimizations (Do Next)

* Serve-stale `/api/state` during search (finding 1).
* Stamp-only 900s integrity (finding 2).
* Numba only if `OPT_FIELDS` grid 3Ã— (closed until then).

### 5) Validation Plan

* Search stall: start a 14-worker job on a **flat** book; time `GET /api/state` p50/p95 vs idle 7â€“72ms.
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
  * Location: `GET /api/logs/download` â€” cookie/header session, not `?token=`
  * Tests pin query token is **not** accepted on panic. Download is GET + cookie. Same-origin cookie is the session. Fine for bind 127.0.0.1.

* **Secrets:** none in the diff. No new tokens, no `docs_url`.

#### Observations

* Origin middleware still wraps every POST/PUT/PATCH/DELETE (`web/app.py` ~597â€“603). Strip did not punch a hole.
* `compare_digest` on the session cookie stays.
* `from_dict` ignoring unknown keys (`partial_close_lots` leftover DB) is fail-open for *config*, not auth.
* Restart/shutdown still exist; they are red operator doors, Origin-gated.

---

## 26.08 12:50 â€” Cursor SCAN-2 (opt + security + profit/model)

Live `/api/state` (cookie): **0 open**, bot watch+trade on, PID 12:32:15,
demo 61562752, eq=bal 2313.55, day âˆ’2.09% / âˆ’49.44 realised, halt off.
Manual opt **running** `apply_best=true` 0/6 (GER40, JPN225, NAS100 in
flight). Operator raised US30/JPN225/GER40/NAS100/SpotBrent
`max_positions` to 3; `size_by_edge` on; concurrent cap 30%. 12:22
silent flatten of the previous 6 then IPC âˆ’10001.

Constitution (Â§0 / Â§19) **not** reopened: session/day-end flatten,
no TP ladders, `trail_start <= trail_step` legal, 8 families (arsiv),
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
* **Expected impact:** panel 148s â†’ <1s during search
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
* **Recommended fix:** `tf_lock_status(tf_allow)` â€” **landed 12:50**
* **Tradeoffs:** none
* **Expected impact:** log matches the book
* **Removal Safety:** Safe
* **Reuse Scope:** `optimizer.py`

* **Title:** Panel flatten-all left no caller line
* **Category:** Reliability
* **Severity:** High (forensics) / Low (runtime)
* **Impact:** 12:22 six `kar~` closes cannot be distinguished from
  halt/session/panic
* **Evidence:** log 12:22:03â€“04 then IPC; no `Zorunlu flatten` /
  `Gunluk zarar` / `ACIL DURDURMA` / `Bot durduruldu`. Panel
  `POST /api/positions-close-all` called `close_all()` bare.
* **Recommended fix:** `close_all(reason=)` â€” **landed 12:50**
* **Tradeoffs:** none
* **Expected impact:** next silent flatten is greppable
* **Removal Safety:** Safe
* **Reuse Scope:** engine + web doors

### 3) Quick Wins (Do First)

1. Honest TF-lock fragment â€” done.
2. Panel flatten reason â€” done.
3. Do **not** cancel the in-flight search; churn brake (48h /
   `_beats_incumbent`) still gates apply.

### 4) Deeper Optimizations (Do Next)

1. Stale snapshot while opt holds the lock (identity tests).
2. 900s integrity stamp-only fetch (still open).
3. O-1/2/3 blob rewrite â€” measure at 2000-row cap, not today.

### 5) Validation Plan

* `tests/test_tf_lock_status_tells_the_truth.py`
* `tests/test_panel_flatten_names_the_caller.py`
* `tests/test_session_csrf_gate.py` (close_all signature)
* Overlay identity already in `test_backtest_trail_step_mirrors_live.py`
  â€” do not re-open.
* Next search start line must contain `aile TF kilidi kapali`.

### 6) Optimized Code / Patch

See `tf_lock_status` in `optimizer.py` and `Engine.close_all(reason=)`.

### Profit / model (one-by-one)

| Surface | Verdict |
|---|---|
| Hard stop + ATR trail + `overlay_stop` | Identity tests green; live clamp stays in `_update_stop`. Do not split again. |
| `trail_start <= trail_step` | Legal. Live: GER40 0.5/2.2, SpotBrent 2.0/2.2, JPN 0.5/1.6, NAS 1.0/1.8, US30 1.4/1.6. XAUUSD **2.0/0.4** (start>step, tight once armed) is opt-chosen holdout +76 R â€” do not override mid-search. |
| `breakeven_at_r` | All six at **1.5**. Not 0.5. Not an OPT axis. |
| `partial_at_r` | GER40 **1.5** only; others 0. One-shot third. Do not bring ladders back. |
| `trail_mode` | All `atr`. Structure/hybrid remain searchable. |
| 8 families (arsiv) | Live: parabolic_flip, burst, stoch_flipÃ—3, mtf_pullback. No alpha_trend/mavilim/st_trend/macd_flip/t3_stoch/wavetrend_flip/micro_rev. `ichimoku` stays. |
| TFs | SpotBrent M15, XAUUSD M15, GER40 M30, JPN225 M15, NAS100 M30, US30 **M5**. Empty `STRATEGY_TIMEFRAMES` is deliberate; scalp-on-M15 is allowed. |
| Session/day-end flatten | Settled 09.08. Overnight gap risk. Do not file as a bug. |
| Apply / churn | MATCH-1 still stands: strategies directionally correct; churn was the leak. 48h age + `_beats_incumbent` + `_slice_ok` stay. Capture is **not** a gate. `apply_best` default true â€” questioned, not silently changed. |
| Book today | GER40 âˆ’45 (4 trades, sl 1.0 ATR + BE 1.5 + partial 1.5) looks like chop against a tight stop, not a trail bug. Do not PATCH overlays during the running search. |
| `max_positions=3` on correlated indices | Yellow. Operator set it. Nominal book â‰ˆ 0.8% Ã— 3 Ã— EDGE_MAX 2.2 Ã— 5 + gold â‰ˆ 28% vs 30% cap. Selector still ranks; cap refuses the tail. Do not revert unasked. |
| `size_by_edge` | On. Yellow. Leave. |

**Do not code:** new families, TP, time-stop, score/capture-as-gate, Ai extras, second MT5, rewriting historical autopsy rows.

**Refuse:** generic ORM/Redis â€œscansâ€.

### SECURITY AUDIT: SCAN-2 (working tree vs 0c33d72)

**Risk Assessment:** Low (dirty tree is prior landed work + these two log fixes)

#### Findings:
* None new on this pass. Origin-on-every-mutation and `el({html})` removal stay in the closed ledger. Ticket highlight has `test_log_ticket_highlight_is_escape_safe.py`.

#### Observations:
* `apply_best` still defaults True on `OptRun` â€” churn door, gated.
* `/api/state` stall is availability under search, not an auth hole.
* Claude SCAN-2 inbound; they may add findings â€” do not pre-empt.

---

Section 2 below is the **07:50 scan** kept as evidence. Landed items are in the closed ledger â€” do not re-open them from the old wording.

---

---

### 2) Findings (Prioritized)

* **Title:** Fill verifier sleeps ~2.1s on the engine thread
* **Category:** Concurrency / Reliability
* **Severity:** High
* **Impact:** cycle latency; delayed trail/BE/flatten/scale-out on every other symbol
* **Evidence:** `_verify_ambiguous_send` (`mt5client.py:1446-1519`). Loop `for attempt in range(4): time.sleep(0.3 if attempt == 0 else 0.6)` then `with self._lock: mt5.positions_get` (`:1486-1492`). Math: 0.3 + 3Ã—0.6 = **2.1s**. Sleep is **outside** `_lock` (correct). Caller is `open_market` â†’ `_try_entry` under `entry_lock` (`engine.py:2478-2488`) on the `micofx-engine` thread, **after** `manage_positions` in the same `_cycle` (`:842` then `:938-969`).
* **Why itâ€™s inefficient:** The poll loop is single-threaded. One lagging fill blocks every later symbolâ€™s entry and the *next* cycleâ€™s manage until the window ends.
* **Recommended fix:** Return `ambiguous` / pending immediately; finish verify on a side queue; keep fail-closed (no second order until verified). UK100/US30 11.08 storm + comment at `:1468-1476` is the constraint. Do **not** delete the sleeps as a â€œperf fixâ€.
* **Tradeoffs / Risks:** Duplicate-entry protection must stay as strict as today. At `max_positions>1` the comment already warns the empty-book retry is weaker.
* **Expected impact estimate:** High on fill storms (cycle no longer +2s); Low on quiet days.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`mt5client.py` + `engine.py` entry)

* **Title:** `original_sl` lives only in `execution._open` RAM
* **Category:** Reliability
* **Severity:** High (measurement) / n/a CPU
* **Impact:** autopsy R after any restart-with-opens; trail-win `r_realised` tautology
* **Evidence:** `track()` `setdefault("original_sl", current sl)` (`execution.py:278-283`). `note_fill` also `setdefault`s into RAM (`:302-306`). `_persist` writes `execution_samples`, not the open book (`:209-217`). Process death empties `_open`. Next `positions_get` SL is the **trail**.
* **Why itâ€™s inefficient:** N/A CPU. The book is rebuilt from the live stop, which is current, not fill-time.
* **Recommended fix:** Persist `{ticket: original_sl, risk_dist}` via `Store` on `note_fill`; reload before `track()` setdefault. Prune with the same live-set as `scale_out_done`. Do **not** restart while opens exist just to â€œload a patchâ€.
* **Tradeoffs / Risks:** Stale rows if the broker reuses a ticket (rare). Must prune.
* **Expected impact estimate:** High for autopsy truth; zero live PnL.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`execution.py` + store key)

* **Title:** Optimizer bar fetch shares the live MT5 `RLock`
* **Category:** Concurrency / I/O
* **Severity:** High (when a search runs) / Low (opt idle)
* **Impact:** live cycle jitter; search wall time
* **Evidence:** Planner thread `self.client.bars` per symbol/TF (`optimizer.py:717-747`), including a halving retry loop that can `bars()` several times. Workers get numpy payloads only. Public MT5 calls take `self._lock` (`mt5client.py:190`). Panel `/api/state` still calls `snapshot()` every 3s (`app.py:677-687`); fallback `positions_get` if the cycle book is stale.
* **Why itâ€™s inefficient:** One connection is required; the waste is **search using the live client as a history bus** while `_update_stop` needs the same lock.
* **Recommended fix:** Prefetch all search bars once, then detach workers. UI already prefers `_panel_positions`. Lower `opt_max_workers` while `engine.running`. Never a second `mt5.initialize()`.
* **Tradeoffs / Risks:** Snapshot age vs live quote; search must not open a second terminal bind.
* **Expected impact estimate:** High cycle jitter during opt; none when idle. **Likely** â€” measure lock wait, do not guess wall %.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide

* **Title:** Supervisor 14-day `deals_since` inside `_cycle`
* **Category:** I/O / Reliability
* **Severity:** Medium
* **Impact:** occasional multi-second cycle stalls (review ticks)
* **Evidence:** `_cycle` calls `supervisor.review` when `due()` (`engine.py:876-880`) **before** evaluate/entry. Default `review_interval_sec=120`, `lookback_days=14` (`supervisor.py:23-24`). `review` â†’ `_closed_trades` â†’ `client.deals_since` (`supervisor.py:494`) under the same MT5 lock.
* **Why itâ€™s inefficient:** Trading loop waits on a reporting query.
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
* **Why itâ€™s inefficient:** Config rows rarely change; deal history is a reporting query on the web thread when the 5s cache expires. Catalogs already moved; **symbol rows did not**.
* **Recommended fix:** Serve symbols on `/api/symbols` (already exists `:689-691`); state carries ids + dirty stamp. Keep cycle-book reuse. Keep `day_stats` 5s cache; do not drop it.
* **Tradeoffs / Risks:** UI must tolerate slightly stale config rows (already 1.5s).
* **Expected impact estimate:** Medium JSON/CPU; Low lock time while cycle + day cache are fresh.
* **Removal Safety:** Needs Verification (payload consumers)
* **Reuse Scope:** service-wide

* **Title:** Full `IndicatorCache` + `compute()` on every new closed bar
* **Category:** CPU / I/O / Algorithm
* **Severity:** Medium (live CPU) â€” **not** the old â€œevery 45sâ€ claim
* **Impact:** cycle CPU and `copy_rates` IPC on bar close
* **Evidence:** After a fetch, same `last_closed_time` â†’ return False (`engine.py:2253-2254`). New bar â†’ rebuild cache + `compute()` (`:2257-2259`). Fetch itself still pulls `required_bars` (often 400â€“1680+) on due/integrity (`:2186-2187`). Integrity every 900s even with no new bar (`:2182`).
* **Why itâ€™s inefficient:** Live only needs the last closed barâ€™s signal. Full rebuild on **bar close** is honest; a 900s integrity pass is cheap vs the old 45s timer. Incremental indicators would help M5 (12 closes/hour Ã— N symbols), not the idle 900s path.
* **Recommended fix:** Append-one-bar warm start **only** with bit-identical tests vs full `compute()`. Keep 900s integrity. Do **not** re-enable `_STALE_BAR_REFRESH`.
* **Tradeoffs / Risks:** Drift vs walk-forward = live/paper desync.
* **Expected impact estimate:** Medium on M5 books; Low on M30. **Likely**  â€” profile `compute()` share of `last_cycle_ms` first.
* **Removal Safety:** Needs Verification (signal identity)
* **Reuse Scope:** module (`engine.py`, `strategy.py`)
* **Classification:** not Dead Code â€” the unused `_STALE_BAR_REFRESH` **name** is Dead Code (Safe to leave as comment; Needs Verification to delete the constant in case a test imports it).

* **Title:** Duplicated stop math: `_update_stop` vs `simulate` â€” **Reuse Opportunity**
* **Category:** Maintainability (runtime cost Low)
* **Severity:** Medium
* **Impact:** liveâ†”paper drift (costlier than CPU)
* **Evidence:** Live `Engine._update_stop` (`engine.py:3349-3529`) vs Python bar loop in `simulate` (`backtest.py:459+`, trail/BE ~636+, ~1007+). Constitution: change both. Uncommitted MFE tracking did not unify them.
* **Why itâ€™s inefficient:** Two implementations of trail_start / step / hybrid / min_step / BE / `partial_at_r` overlays.
* **Recommended fix:** Pure `desired_sl(closed_bar, params, pos) -> float`; live adds broker clamp + modify only.
* **Tradeoffs / Risks:** Large refactor; keep quote feasibility (`settled` / retry) separate.
* **Expected impact estimate:** Low CPU; High maintenance ROI if exits keep growing.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide

* **Title:** Python `simulate()` bar loop dominates search wall, not live
* **Category:** Algorithm / CPU
* **Severity:** Medium (opt wall) / Low (live)
* **Impact:** search duration; cost of any grid expansion
* **Evidence:** Series converted to lists; sequential loop (`backtest.py:526+`). No Numba. Uncommitted `_mfe_tick` / `trade_mfes` add O(1) per bar inside that loop (`Result.trade_mfes`, `capture` at `:73-93`) â€” not a new bottleneck.
* **Why itâ€™s inefficient:** Branchy exits resist naive vectorization; O(bars Ã— open trades) in CPython.
* **Recommended fix:** `py-spy` one GER40 `walk_forward` in the venv **before** Numba. If >70% of worker time is the loop, compile trail/exit only. Do **not** expand `OPT_FIELDS` until this is paid. Do **not** put `capture` into `score()`.
* **Tradeoffs / Risks:** Bit-identical R vs live is a product invariant.
* **Expected impact estimate:** Mediumâ€“High on search (qualitative until profiled); none on the 2s live cycle.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`backtest.py`)

* **Title:** Scale-out remain unclamped; cash takes a second `info()` path
* **Category:** Reliability / I/O
* **Severity:** Low
* **Impact:** one-poll poisoned `pos["volume"]`; extra `info()` on a rare event
* **Evidence:** `_maybe_scale_out` (`engine.py:3531-3596`). `info()` for min/step (`:3566`); `filled = float(fill.get("volume") or close_vol)` then `remain = volume - filled` with **no** clamp (`:3585-3587`); `pos["volume"] = remain` (`:3595`). Cash: `money_per_price_unit` (`:3590`) â†’ another `info()` (`mt5client.py:960-969`), usually TTL-hit. Gate R uses `max(atr * sl_atr_mult, min_stop)` (`:3563`) â€” **not** `book.original_sl`. `done.add` is one-shot even on IOC `DONE_PARTIAL` (intended).
* **Why itâ€™s inefficient:** Second info is reporting-only. Unclamped remain can go negative until the next `positions_get`.
* **Recommended fix:** `filled = min(filled, pos.volume)`; clamp remain â‰¥ 0; WARN on mismatch. Pass tick_value/tick_size from the existing `info` dict for cash.
* **Tradeoffs / Risks:** Clamping hides a broker lie; WARN is enough. Cash is audit trail, not a deal.
* **Expected impact estimate:** Low (once per scaled ticket; DONE_PARTIAL rare).
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`engine.py`)

* **Title:** Per-ticket `tick` + `min_stop_distance` in `_update_stop`
* **Category:** I/O / Algorithm
* **Severity:** Lowâ€“Medium
* **Impact:** MT5 IPC Ã— open tickets; CPU if `trail_mode` in {structure, hybrid}
* **Evidence:** `_update_stop` (`engine.py:3349+`) takes a fresh tick + `min_stop_distance`. Structure/hybrid can scan swings over the series. Trail already latched per closed bar via `_stop_bar` in `manage_positions`.
* **Why itâ€™s inefficient:** Cycle already has a tick per symbol; backtest precomputes swings once.
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
* **Why itâ€™s inefficient:** 6 cards Ã— 0.3 Hz is fine; 20 symbols is not free.
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
* **Why itâ€™s inefficient:** Trailing index on M30 is fine; a choppy M5 book is chatter.
* **Recommended fix:** Coalesce trail logs (ticket + new SL + bar time); keep first BE lock as TRADE.
* **Tradeoffs / Risks:** Autopsy of intra-bar trail chatter gets coarser.
* **Expected impact estimate:** Low
* **Removal Safety:** Likely Safe
* **Reuse Scope:** module

* **Title:** Stale comments that will re-open closed work â€” **Over-Abstracted / stale docs**
* **Category:** Maintainability
* **Severity:** Low
* **Impact:** agents re-litigate 1.5s poll / â€œWindows dayâ€
* **Evidence:** `/api/schema` docstring still says catalogs rode `/api/state` â€œ1.5s while a search runsâ€ (`app.py:662`). `day_stats` docstring says â€œcurrent local (Windows) dayâ€ (`engine.py:3773`) but `_day_start_epoch` is broker-calendar (`:3742-3750`).
* **Why itâ€™s inefficient:** Dual source of truth; not runtime.
* **Recommended fix:** One-line docstring fixes when next touching those functions. Not this audit.
* **Tradeoffs / Risks:** None
* **Expected impact estimate:** n/a
* **Removal Safety:** Safe
* **Reuse Scope:** local file

* **Title:** `graft/` markdown mirrors â€” **Dead Code** (docs, not executed)
* **Category:** Cost (agent context)
* **Severity:** Low
* **Impact:** grep noise, wrong line maps
* **Evidence:** `graft/micofx/*.md` vs live `micofx/`.
* **Why itâ€™s inefficient:** Stale sourcedump.
* **Recommended fix:** Do not treat as live. Already in AGENTS.md.
* **Tradeoffs / Risks:** Archaeology if dated.
* **Expected impact estimate:** Low
* **Removal Safety:** Needs Verification (if any tool still reads graft)
* **Reuse Scope:** repo

* **Title:** Uncommitted `strategies=` opt filter is not a live hot-path win until used
* **Category:** Cost / Concurrency
* **Severity:** n/a (door, not a bottleneck)
* **Impact:** a one-off sweep can skip families without writing `opt_params`
* **Evidence:** `OptRun.strategies` (`app.py:90-101`) â†’ `optimizer.start(..., strategies=)` (`:2146-2150`). Whitelist against `STRATEGIES` (`optimizer.py:314-339`). Empty = inherit. Comment: a saved subset would stick scheduled reopt (`:314-317`).
* **Why itâ€™s inefficient:** N/A. Full 13-family sweep still hits `client.bars` on the planner when someone starts `/api/opt/run` with no filter.
* **Recommended fix:** When **flat** and asked: pass the family list on the run body; `apply_best` still operator. Do not persist the subset.
* **Tradeoffs / Risks:** `apply_best` default remains `True` on `OptRun`.
* **Expected impact estimate:** High lock time avoided only if the operator actually restricts the run.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide

---

### 3) Quick Wins (Do First)

1. Persist `original_sl` (restart-with-opens stops lying). After a gece load when **flat**, not instead of it.
2. Clamp scale-out `filled` â‰¤ `pos.volume`; compute `kar=` from the `info` dict already in `_maybe_scale_out`.
3. Fix the two stale comments (`app.py:662`, `engine.py:3773`) so the next scan does not re-open 1.5s poll / UTC-day.
4. Do **not** start a live search, holdout-capture, or flatten to â€œmake restart safe.â€

Already done (not wins anymore): hoist `trigger_pad`; `/api/schema`; 3s poll; cycle-book snapshot; 900s integrity; entry_blocks 45s debounce; retire alpha_trend/mavilim in this working tree.

---

### 4) Deeper Optimizations (Do Next)

1. Deferred fill-verify queue (fail-closed). Highest remaining live-cycle item.
2. `/api/state` without full `symbol_payload` every 3s; keep `day_stats` 5s cache.
3. Supervisor review off the `_cycle` critical path.
4. Shared `desired_sl()` liveâ†”paper.
5. Incremental `IndicatorCache` vs 900s full rebuild â€” identity tests required.
6. Optimizer: fetch bars once, CPU-only workers; optional `strategies=` on a **flat** book.
7. Numba/Cython `simulate` inner loop **only after** a worker profile; required before any 3Ã— grid (BE-3).

Do **not:** micro-optimize `secrets.compare_digest` on `/api/state`; unroll ATR; re-enable `_STALE_BAR_REFRESH`; put `capture` into the walk-forward score; reintroduce `tp_atr_mult` / `partial_tp_r` / `max_bars_in_trade`; resurrect `alpha_trend` / `mavilim`.

---

### 5) Validation Plan

* **Benchmarks:** `engine.last_cycle_ms` p50/p95 from `/api/state` over 15 min quiet vs 15 min with panel open vs 15 min with opt running. Count `copy_rates` / `positions_get` / `deals_since` via a thin counter on `MT5Client` (measure first; do not log every call to disk).
* **Profiling:** `py-spy` on the live PID **read-only** (no `mt5.shutdown`). Separate profile of one `walk_forward` GER40 job in `C:\MicoFX-venv\Scripts\python.exe`.
* **Metrics before/after:** cycle_ms, sqlite `set_setting` commits/min, `/api/state` JSON bytes, panel `refresh` duration, opt worker CPU, MT5 lock-acquire time, first post-load trail-win autopsy (`r_realised â‰  1.000`, cash R within 2%).
* **Correctness tests (must stay green):** trail/BE identity suite (`test_engine_breakeven_lock_at_r.py`, `test_breakeven_lock_does_not_give_the_stop_back.py`, `test_trail_breakeven_invariant.py`, `test_backtest_trail_step_mirrors_live.py`, `test_trail_retry_within_bar.py`), `test_core.py` (signal-on-close / fill-next-open), `test_scale_out_once.py`, `test_panel_does_not_fast_poll_during_opt.py`. Uncommitted: `test_simulate_records_per_trade_mfe.py`, `test_keep_log_does_not_quote_a_stale_stamp.py`, `test_opt_run_can_restrict_families.py`, `test_retired_indicators_stay_gone.py`. Any incremental-indicator change needs â€œfull vs append identical last signalâ€.
* **Do not** validate by adding a second MT5 bind or writing `data/micofx.db` from a sidecar.

---

### 6) Optimized Code / Patch (proposals only â€” not applied)

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

**C. Fill verify:** do not delete the 2.1s sleeps until a queue preserves â€œno second order while ambiguousâ€ (`mt5client.py:1457-1480`).

What would change: less MT5/UI coupling; honest autopsy R after restart. What must not change: forming-bar drop, buyâˆ§sellâ†’neither, fail-closed duplicates, liveâ†”paper trail/BE identity, score formula, `capture` as a visible column only.

---

### SECURITY AUDIT: working tree vs HEAD `0c33d72`

**Risk Assessment:** Low

Uncommitted product change is holdout cleanup + observability: retire two families, report `capture`, honest keep-log, one-off `strategies=` on existing `POST /api/opt/run`, tally silent `_evaluate` refuses. No new endpoints, no SQL, no secrets, no `subprocess` change.

#### **Findings:**

* **Authenticated opt family list unbounded before whitelist** (Severity: Low)
* **Location:** `micofx/web/app.py:90-101` (`OptRun.strategies`); `micofx/optimizer.py:317-331`
* **The Exploit:** A session-holding caller POSTs a huge `strategies` array. Names are `str()`â€™d then filtered to `STRATEGIES`. Unknown names drop; all-unknown â†’ 409. Same class as existing `timeframes`. Not RCE/SQLi. Classic CSRF from another site is mitigated by SameSite=Strict cookie; `/api/opt/run` is **not** in `_CRITICAL_MUTATIONS` (`app.py:569-575`) â€” **pre-existing**, not introduced here.
* **The Fix:** Optional `max_length` on the list (same as timeframes if added). Do not apply in this audit.

* **Unauthenticated fill volume trusted for remain** (Severity: Low) â€” **unchanged, still open**
* **Location:** `micofx/engine.py:3585-3595`
* **The Exploit:** Not remote. MT5 `result.volume` (or a stub) larger than `pos.volume` writes negative `pos["volume"]` for one poll. Panel/API cannot inject this field.
* **The Fix:** Clamp as in Â§6 B. Do not apply in this audit.

#### **Observations:**

* `apply_best` still defaults `True` on `OptRun` â€” family subset + apply is an operator write to live configs, same privilege as HEAD.
* Unknown leftover `strategy: alpha_trend|mavilim` in the live DB will not trade (`strategy.py:406-413`); it will WARN once per name. Not a crash, not an auth bypass.
* `capture` is read-only on holdout dicts; not a mutation surface.
* Session cookie + Origin on `_CRITICAL_MUTATIONS` unchanged. Holdout capture stays Origin-gated (`:574`).
* No hardcoded credentials in the diff. Tests only.
* `innerHTML` in `app.js` still goes through `esc()` (`:84`) on the poll path this diff did not widen.

---

### 25.08 book baseline (measurements, not software TODOs)

Do not re-litigate these as CPU findings. Do not ship TP / time-stop / skip_after_loss / BE 0.5 from them.

* UTC day full closes n=38 cash **+14.91**; GER scale-out â‰ˆ**+107.5** extra (not in autopsy `$`). Balance check: 2192.73 + 14.91 + 107.5 â‰ˆ 2315.
* US30 21 closes **âˆ’96.62** (SELL 14 / âˆ’120.33 vs BUY 7 / +23.71). Never-green = **MFE â‰¤ 0.05 R**.
* Winner capture median ~**50%**; book capture is not a score input.
* O-5: five pre-fix autopsy rows with `sl`+`r=+1.0` (GER trio cash **+158**). Do not rewrite. Cash/`kar=` is truth.
* Reverse-after-SL is post-fill cooldown geometry (`max_positions=1` frees the slot). Not a trail bug.
* Keep-line `test net` was the apply stamp; working-tree logs `(taze test â€¦R)` / `(damga â€¦R, dd.mm)`.

---

# 26.08 08:05 UTC+3 â€” Claude diff-level pass (adds to the 07:50 scan, does not replace it)

The 07:50 scan is a **system/hot-path** audit and its closed ledger holds. This
pass re-read the same uncommitted diff for **correctness of the new measurements**
and found five things the 07:50 pass did not carry. Two of them contradict a
conclusion above; both are named as disagreements, not corrections.

Read-only. Live PID 10424, started **26.08 01:38:46**, so the diff is **not
loaded**. Nothing applied.

### 1) Optimization Summary

* The diff's three products (evaluate-refuse tally, per-trade MFE â†’ `capture`,
  opt `strategies=` + fresh incumbent replay) are all pointed the right way.
  The remaining cost is not CPU â€” it is **the numbers themselves**: a new count
  shares a column with an old count of a different unit, and `capture` is biased
  on one side of the book.
* Top 3:
  1. `_mfe_tick` does not pad the short side (**C-2**). `capture` reads low on
     sells only â€” and US30 SELL is the next cohort queued for judgment.
  2. `entry_blocks.attempts` now carries two units in one column (**C-1**),
     measured live: US30 `bar_bosluk` ratio **1.0** against `spread` **104.7**.
  3. `_merge()` drops `trade_mfes` (**C-3**) â€” every pooled Result reports
     `capture: null`, silently.
* Biggest risk: both agents rank symbols off these tables. A column in the wrong
  unit opens the wrong gate. This is a **verdict** risk, not a latency risk.

### 2) Findings (Prioritized)

* **Title:** `_mfe_tick` omits the ASK pad on the short side â€” `capture` is biased on sells
* **Category:** Algorithm (measurement correctness)
* **Severity:** High
* **Impact:** `Result.capture`, `opt_summary.holdout.capture`, any buy-vs-sell capture comparison
* **Evidence:** New helper (`backtest.py:720-723`): `fav = (bar_high - entry) if is_buy else (entry - bar_low)`. Eight lines above, `_mae_tick` (`:704-712`) does pad the same side: `adverse = bar_high + float(trigger_pad[j]) - entry`. `stop_fill_price` (`:424-426`) states the rule: *"short on `bar_high + trigger_pad >= sl` (the pad is the bar's spread so a short covers on the ask)"*. A short's best realisable price is `bar_low + trigger_pad`, not `bar_low`.
* **Why it's inefficient:** Not wrong on the long side â€” a buy enters at `open + s` (ask) and exits at the bid, so no pad is owed and `bar_high - entry` is right. Shorts overstate MFE by exactly one spread, so `capture = net_r / sum(mfe_r)` reads **low on sells only**. Live `maliyet` lines give the scale (US30 2.0%, JPN225 4.7%, SpotBrent 4.8%, GER40 7.4% of risk â€” spread+commission), so roughly 1â€“4% of R per short, one-directional.
* **Recommended fix:** `fav = (bar_high - entry) if is_buy else (entry - (bar_low + float(trigger_pad[j])))`. `j` is already a parameter; `trigger_pad` is already in the closure.
* **Tradeoffs / Risks:** `capture` values go **up** (smaller denominator), so any `opt_summary.holdout.capture` already written is not comparable across the fix. Same stamp-vs-fresh trap the keep-line just paid for â€” date the change.
* **Expected impact estimate:** +1â€“4 percentage points of capture on short-heavy symbols. It is the only change that makes a US30 BUY-vs-SELL capture split legitimate.
* **Removal Safety:** Needs Verification (stored capture stamps)
* **Reuse Scope:** local file (`backtest.py`)
* **Disagreement:** the 07:50 entry "Python `simulate()` bar loop dominates search wall" judged `_mfe_tick` as "O(1) per bar â€” not a new bottleneck". That is correct about **CPU** and says nothing about the pad. Both hold.

* **Title:** `entry_blocks.attempts` now carries two different units in one column
* **Category:** Reliability (measurement integrity)
* **Severity:** High
* **Impact:** the missed-signal table both agents rank symbols with
* **Evidence:** Live DB read-only (`settings.entry_blocks`; `entry_blocks_since` = 1786905256.33 â†’ **16.08 21:34:16**, a **226.2 h** window):

      US30       spread              attempts=11520  signals=110  ratio=104.7
      US30       risk_sembol_limiti  attempts= 7121  signals= 58  ratio=122.8
      US30       risk_ters_yon       attempts=  830  signals= 27  ratio= 30.7
      US30       bar_bosluk          attempts=    7  signals=  7  ratio=  1.0
      GER40      risk_ters_yon       attempts= 7995  signals=  9  ratio=888.3
      SpotBrent  risk_ters_yon       attempts=  772  signals= 37  ratio= 20.9

  Mechanism: `seans_disi` (`engine.py:2007`), `piyasa_kapali` (`:2020`) and `bar_bosluk` (`:2055`) clear the **whole** signal chain (`signal`, `signal_source`, `primary_signal`, `pending_bar_key`). On the next poll `_refresh_signals` has no fresh bar, so `state.signal` stays empty and `_tally_evaluate_refuse` returns early. Those three can therefore tally **at most once per bar**. Every other reason (`spread`, `risk_*`, `bar_doldu`, `sembol_halt`) leaves the signal standing and re-tallies each poll until the bar rolls.
* **Why it's inefficient:** `_tally_entry`'s own docstring defines `attempts` as persistence ("one refused M15 signal shows up as several hundred attempts â€” EURJPY produced 339 from a single sell"). That definition no longer holds for part of the table. The 22:13 missed-signal analysis used exactly this column. `bar_bosluk` at 7/7 today is the mechanism already visible in production; the diff adds `seans_disi` and `piyasa_kapali` to the same one-shot class (`bar_doldu` stays in the persistent class).
* **Recommended fix:** Do not reset the window â€” 226 h of series. Either publish a per-reason `unit: "bar" | "poll"` in `entry_blocks()` and hide `attempts` for the one-shot class, or compare on `signals` only (it is already distinct-episode). Naming the unit is cheaper than changing the counting.
* **Tradeoffs / Risks:** Resetting `entry_blocks_since` would make the two definitions one window and destroy the series. Do not.
* **Expected impact estimate:** Runtime 0. Measured distortion on US30 today spans 1600Ã— (11520/7) to 16Ã— (110/7) depending on which column is read.
* **Removal Safety:** Needs Verification (panel consumers)
* **Reuse Scope:** module (`engine.py`, panel block table)

* **Title:** `_merge()` does not carry `trade_mfes` â€” pooled `capture` is always null
* **Category:** Algorithm / Reliability
* **Severity:** Medium-High
* **Impact:** the `baseline` report block; every multi-segment total
* **Evidence:** `backtest.py:1197-1216` extends `trade_rs` and `trade_cost_rs` but not `trade_mfes`. `Result.capture` (`:86-93`) then sees `total <= 0.0` and returns `None`. `backtest.py:1453` `baseline = _merge(base_parts).as_dict(...)` â†’ `capture: null`, always. The paths that matter still work: `validation` / `holdout` come from `measure()` â†’ a single `simulate`, and `_holdout_costed` â†’ `charged_holdout` (`holdout_cost.py:61-64`) is also a single `simulate`, so `opt_summary.holdout.capture` is real.
* **Why it's inefficient:** A field that is present and permanently empty, where `None` cannot be told apart from "no MFE recorded". It also breaks the AGENTS.md invariant *"Per-trade MFE is `Result.trade_mfes` (same length)"* for pooled results â€” the same class of silently-misread field the keep-line stamp just cost a day.
* **Recommended fix:** `total.trade_mfes.extend(r.trade_mfes)` in `_merge`. `trade_events` is not carried either; if that is deliberate, one comment line, otherwise the same fix.
* **Tradeoffs / Risks:** None. `capture` is not a score input and not an apply gate.
* **Expected impact estimate:** Negligible runtime; report correctness.
* **Removal Safety:** Safe
* **Reuse Scope:** local file (`backtest.py`)

* **Title:** The same charged holdout replay runs twice per kept symbol
* **Category:** CPU / Caching
* **Severity:** Medium
* **Impact:** search wall; MT5 lock time when a search shares the host with live
* **Evidence:** `reject_reason` â†’ `_beats_incumbent` (`optimizer.py:1383`) â†’ `_fresh_incumbent_holdout(cfg)` (`:1530`). Then the keep log at `:1140` calls `_incumbent_kept_tail(cfg)` â†’ `_fresh_incumbent_holdout(cfg)` again (`:1402`). Same `cfg`, same `OPT_FIELDS`, no memo. Separately, the "hicbir aday kapidan gecmedi" path (`:1017`) paid **zero** replays before this diff and now pays one.
* **Why it's inefficient:** `_holdout_costed` is a full `charged_holdout`: `spread_cost_series` + `session_mask` + `flatten_mask` + `compute` + `simulate` over up to `max_bars`. Bars are usually free (`_bar_snap` hit), the simulate is not.
* **Recommended fix:** Run-scoped memo keyed on `(symbol, timeframe, strategy, params)` â€” the params must be in the key because `apply()` can mutate `cfg` inside the same run. Clear it beside `_bar_snap` (`:816`).
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
* **Recommended fix:** `_fresh_incumbent_holdout(cfg, allow_fetch=False)` from the log path, falling back to the stamp â€” the line already distinguishes `(damga â€¦R, dd.mm)`, so it stays honest.
* **Tradeoffs / Risks:** TF-restricted runs print the stamp instead. Acceptable, because the line **says** it is a stamp.
* **Expected impact estimate:** Zero on an unrestricted run; one `client.bars(max_bars)` per kept symbol on a restricted one.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`optimizer.py`)

* **Title:** `state.entry_block` â€” four writers, zero readers â€” **Dead Code**
* **Category:** Dead Code
* **Severity:** Low
* **Impact:** maintenance surface; the field's meaning
* **Evidence:** The diff adds `engine.py:2007` (`seans_disi`), `:2020` (`piyasa_kapali`), `:2098` (`bar_doldu`); `:2055` (`bar_bosluk`) already existed. The field's only reader is `engine.py:958`, the ready-loop tally, which runs strictly after `_try_entry` â€” and all four of these paths `return False`, so the symbol never joins `ready`. `_try_entry` also resets the field to `""` at `:2304`, so nothing carries to a later cycle. `SymbolState.as_dict()` does not publish it, and no handler in `app.py` / `app.js` / `index.html` reads it (the `entry_blocks` counters are a different thing).
* **Why it's inefficient:** Write-only state invites the next reader to assume the panel shows it. `sembol_halt` (`:2072`) is the inverse â€” it tallies but sets nothing â€” so the field is now maintained on 4 of 5 gates and read on none.
* **Recommended fix:** Pick an end, not the middle: delete all four writes (the tally already records the reason), or publish the field in `as_dict()`, show it, and set it on `sembol_halt` too.
* **Tradeoffs / Risks:** Deleting changes no behaviour â€” the single reader is unreachable from these paths.
* **Expected impact estimate:** Runtime 0. Readability.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`engine.py`)

* **Title:** `timeframes` and `strategies` validation blocks are line-for-line twins â€” **Reuse Opportunity**
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

1. `total.trade_mfes.extend(r.trade_mfes)` in `_merge` (C-3) â€” one line, no risk.
2. Pad the short side in `_mfe_tick` (C-2) â€” one line, but it invalidates stored `capture` stamps; date it.
3. Run-scoped memo for `_fresh_incumbent_holdout` (C-4).
4. Delete the four dead `state.entry_block` writes (C-6).

### 4) Deeper Optimizations (Do Next)

* Publish a per-reason unit on `entry_blocks()` and compare on `signals` (C-1). **Do not reset the window.**
* `allow_fetch=False` on the keep-line replay (C-5).
* Extract `_one_off_subset` (C-7) before a third axis lands.

### 5) Validation Plan

* **C-2:** fail-first â€” one synthetic short with a known `trigger_pad`, asserting MFE is `entry - (low + pad)`; a long on the same bar asserting no pad. Then re-run `test_simulate_records_per_trade_mfe.py`.
* **C-3:** two-segment `_merge`, assert `len(total.trade_mfes) == len(total.trade_rs)` and `capture is not None`.
* **C-1:** after the diff loads, at the first session close assert `seans_disi` has `attempts == signals`. `bar_bosluk` at 7/7 today is the expected shape, not an anomaly.
* **C-4:** `opt_runs.elapsed_sec` before/after on the same symbol/TF/family set.
* **C-5:** run with `timeframes=["M5"]` against a symbol whose live TF is not M5; `client.bars` call count from the log path must be 0.
* Standard gate: `pytest tests/<touched>.py -q --tb=short` + `ruff check micofx/`.

### 6) Optimized Code / Patch (proposals only â€” not applied)

```python
# backtest.py _merge â€” C-3
total.trade_mfes.extend(r.trade_mfes)

# backtest.py _mfe_tick â€” C-2: a short covers on the ask, same as _mae_tick
def _mfe_tick(is_buy, entry, mfe_px, j):
    bar_high, bar_low = high[j], low[j]
    fav = ((bar_high - entry) if is_buy
           else (entry - (bar_low + float(trigger_pad[j]))))
    return fav if fav > mfe_px else mfe_px

# optimizer.py â€” C-4: one replay per (symbol, tf, strategy, params) per run
key = (cfg.symbol, cfg.timeframe, cfg.strategy,
       tuple(sorted((k, getattr(cfg, k)) for k in OPT_FIELDS if hasattr(cfg, k))))
# self._incumbent_memo, cleared beside _bar_snap at optimizer.py:816
```

---

### SECURITY AUDIT (Claude): same working tree â€” **raises the 07:50 rating to Medium**

**Risk Assessment:** Medium (the 07:50 pass rated this Low; the disagreement is one finding, below)

#### **Findings:**

* **Log injection â€” forged lines in the audit trail** (Severity: Medium)
* **Location:** `micofx/optimizer.py:319-323` (new, families) and `:302-305` (pre-existing, timeframes); writer `micofx/logbus.py:96`
* **The Exploit:** `POST /api/opt/run` with `{"strategies": ["x\n2026-08-26 07:00:00 TRADE  [US30] #999 BUY 1.0 lot @ ... kar=+500"]}`. The value is not in `STRATEGIES`, so it lands in `dropped_fam` and is interpolated straight into `LOG.emit` via `', '.join(dropped_fam)`. `_write_file` does `fh.write(f"{stamp} {level:6} {sym}{entry['message']}\n")` â€” no escaping â€” so an embedded newline produces a complete, well-formed extra line. In this repo the log **is** the audit trail: scale-out P&L, autopsy R and the keep-line were all read from it on the night of 25.08. `logbus._rotate` cuts on a line boundary, so a forged line survives rotation.
* **The Fix:** One choke point in `LOG.emit` â€” `message = str(message).replace("\r", " ").replace("\n", " ")` â€” plus `', '.join(dropped_fam[:8])` at the call sites to bound the line. **Not applied.**
* **Why this is not Low:** the 07:50 finding treats `strategies` purely as an unbounded-list issue and concludes "names are `str()`'d then filtered". The filtering protects the *sweep*; it does not protect the *log*, because the rejected names are exactly what gets printed.

* **`/api/opt/run` outside `_CRITICAL_MUTATIONS`** (Severity: Low â€” agrees with 07:50, restated for the fix)
* **Location:** `micofx/web/app.py:569-577`
* **The Exploit:** Session-cookie only, no `Origin` check. `HttpOnly` + `SameSite=Strict` means a real cross-site POST will not carry the cookie in a current browser, which is why this stays Low. But the repo already decided the cookie alone was insufficient for `/api/bot/panic` (AS1), and this endpoint now accepts a new field that reaches the log.
* **The Fix:** add `"/api/opt/run"` to `_CRITICAL_MUTATIONS`; the panel already posts same-origin. **Not applied.**

#### **Observations:**

* No hardcoded credentials, keys or tokens in the diff. Confirms 07:50.
* `OptRun` is `_ForbidModel`; extra fields rejected. `_FAMILIES.get` (`strategy.py:406`, `:1243`) warns once on an unknown name rather than raising â€” a leftover `alpha_trend` / `mavilim` in the DB fails closed. Confirms 07:50.
* `strategies` has no length bound, so a 10k-element list becomes one log line. Not a DoS; an unbounded line.
* `capture` remains read-only on holdout dicts; `_slice_ok` / `reject_reason` / `_beats_incumbent` untouched.

---

### Reverse engineering â€” live readings (read-only, 26.08 07:48)

Not code claims. Read from the running system.

* **Process:** PID 10424, started **26.08 01:38:46**, `127.0.0.1:8900` LISTENING. HEAD `0c33d72` was committed after that start, so the live process is **pre-HEAD** and certainly does not carry the uncommitted diff. Any "live behaves like this" claim about the diff is currently **unverifiable**.
* **The keep-line has never fired.** Searching `logs/micofx.log` for `taze test` / `damga` returns three lines â€” all three are `"broker saati ... broker damgasinda, Windows DST sapmasi"` (lines 920, 922, 923). `_incumbent_kept_tail` has not emitted once in this log. The 25.08 keep-line fix is **unproven in production**; first thing to check on the next search.
* **Counter window:** `entry_blocks_since` = 1786905256.33 â†’ **16.08 21:34:16**, 226.2 h. All C-1 ratios come from that window.
* **13 families (arsiv):** the panel reports 13 and post-diff `STRATEGIES` is 13, so the live DB `opt_params.strategies` already dropped `alpha_trend` / `mavilim`. The code constant follows the DB rather than leading it.
* **Book at 07:48:** JPN225 #366201717 still open (04:15 entry, SL fixed at 66139.73815 since 06:00, logged peak 4.92Ã—ATR); SpotBrent #366298271 BUY 0.12 at 07:15; GER40 #366302421 SELL 0.8 at 07:30. Overnight closes: GER40 âˆ’27.53, NAS100 +11.04, NAS100 âˆ’15.36.

---

# 26.08 08:40 UTC+3 â€” Cursor clean scan (this chat)

Read-only. Trust the closed ledger: do **not** re-open fill-verify sleep-on-cycle,
RAM-only `original_sl`, supervisor-inside-`_cycle`, full `symbol_payload` on
`/api/state`, unclamped scale-out, duplicated trail math, or unchunked
`copy_rates`. Those landed on disk. Live PID (started 26.08 01:38) may still
be pre-diff. **No restart while opens exist. No code applied this pass.**

`micofx/exits.py` is **untracked**. Product diff vs HEAD: `micofx/` + tests +
AGENTS/MASTER/OPTIMIZATIONS (~32 files, +1382/âˆ’591). Suite claimed green on
the other page (147 targeted / 2492 full); this pass did not re-run pytest.

AGENTS.md: already dense enough (venv, live-owns-DB, no sidecar MT5, yellow/red
gates, overlay_stop, 8 families (arsiv), gotchas). Do **not** rewrite it here. Only
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
  `simulate()` â€” profile before Numba.
* Top 3 highest-impact remaining:
  1. `day_stats()` still sits in `snapshot()` â€” 5s cache, miss takes
     `history_deals_get` on the same lock as trail/flatten.
  2. Incremental indicators on bar close (M5 especially) â€” identity tests
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
* **Why itâ€™s inefficient:** Deal history is not needed to trail or enter. The
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
* **Evidence:** Same stamp â†’ return False (`engine.py:2420-2421`). New bar â†’
  `IndicatorCache(bars.high, â€¦)` + `compute(cache, params)` (`:2424-2426`).
  Cache memos inside one object (`strategy.py:142-178`) then is discarded.
  Fetch still pulls `required_bars` (400â€“1680+) on due / 900s integrity.
* **Why itâ€™s inefficient:** Live only needs the last closed barâ€™s signal.
  Rebuilding T3/stoch/ATR/ADX/HTF over the whole window on every M5 close
  (12/hour Ã— N symbols) is honest but heavier than an append-one-bar warm start.
* **Recommended fix:** Append-one-bar only with **bit-identical** last-signal
  tests vs full `compute()`. Keep 900s integrity. Do **not** re-enable
  `_STALE_BAR_REFRESH`.
* **Tradeoffs / Risks:** Drift vs walk-forward = live/paper desync. Highest
  correctness cost in the remaining list.
* **Expected impact estimate:** Medium on M5; Low on M30. **Likely** â€” profile
  `compute()` share of `last_cycle_ms` first.
* **Removal Safety:** Needs Verification (signal identity)
* **Reuse Scope:** module (`engine.py`, `strategy.py`)

* **Title:** Supervisor 14d and fill-verify still contend the live MT5 lock
* **Category:** Concurrency
* **Severity:** Medium (contention) â€” **not** the closed â€œblocks `_cycle`â€ bug
* **Impact:** trail/modify latency while a side thread holds `_lock`
* **Evidence:** `_kick_supervisor_review` (`engine.py:983-1004`) daemon +
  non-blocking gate. `review()` â†’ `deals_since` 14d (`supervisor.py:494`) still
  takes `with self._lock`. Fill-verify: first `_look()` is sync; if empty and
  `defer=True`, engine returns pending (`mt5client.py:1541-1543`); side thread
  then sleeps 2.1s **between** `_look()` calls that each take the lock
  (`:1515-1517`, `:1545-1547`). Inflight still blocks a second send (intended).
* **Why itâ€™s inefficient:** Cycle is free of the sleep; the lock is not. A 14d
  `history_deals_get` can stall `modify_position` / `tick` for other symbols.
* **Recommended fix:** Measure lock-hold histograms first. If 14d is the
  spike, snapshot deals on the supervisor thread with a timeout / chunk, or
  reuse the dayâ€™s `day_stats` merge and only extend the lookback when due.
  Do **not** delete verifier sleeps.
* **Tradeoffs / Risks:** Quarantine lag already 120s. Weaker verify = duplicate
  entries (fail-closed is the product rule).
* **Expected impact estimate:** Medium on review ticks / ambiguous fills; Low
  on quiet polls. **Likely**.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`engine.py`, `mt5client.py`, `supervisor.py`)

* **Title:** `_ACCOUNT_TTL` is 1s; panel poll is 3s
* **Category:** I/O / Caching
* **Severity:** Lowâ€“Medium
* **Impact:** extra `account_info` IPC on every `/api/state`
* **Evidence:** `refresh_account` TTL = 1.0s (`engine.py:38`, `:3833-3836`).
  `snapshot()` always calls it (`:4192`). Panel delay 3000ms (`app.js:2325`).
  Every visible poll therefore misses the TTL unless a cycle refreshed <1s ago.
* **Why itâ€™s inefficient:** Positions already reuse `_panel_positions` when the
  cycle book is fresh. Account does not get the same courtesy.
* **Recommended fix:** Raise TTL to ~2s, or reuse cycle account when
  `_cycle_book_is_fresh()`. Keep `force=True` after a fill (`engine.py:972`).
* **Tradeoffs / Risks:** Equity/margin on the panel can lag ~2s (already the
  cycle interval). Daily brake must keep using the cycleâ€™s forced refresh.
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
* **Why itâ€™s inefficient:** Branchy exits resist naive vectorization; O(bars Ã—
  open trades) in CPython.
* **Recommended fix:** `py-spy` one GER40 `walk_forward` in
  `C:\MicoFX-venv\Scripts\python.exe` **before** Numba. If the loop is >70% of
  worker time, compile trail/exit only. Do **not** expand `OPT_FIELDS` until
  paid. Do **not** put `capture` into `score()`.
* **Tradeoffs / Risks:** Bit-identical R vs live is a product invariant.
* **Expected impact estimate:** Mediumâ€“High on search (qualitative until
  profiled); none on the ~2s live cycle.
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module (`backtest.py`, `exits.py`)

* **Title:** `entry_blocks.attempts` still mixes poll persistence and one-shot bar gates
* **Category:** Reliability (measurement) â€” **Reuse Opportunity** (panel)
* **Severity:** Medium (verdict risk, not latency)
* **Impact:** missed-signal ranking if someone sorts on `attempts`
* **Evidence:** `entry_blocks()` already splits `signals`/`blocks` vs
  `attempts`/`retries` (`engine.py:1480-1516`) and the docstring says
  `signals` is the comparable count. Panel `loadBlocks` still prints
  `r.signals / r.attempts deneme` (`app.js:386`) and ignores `retries`.
  Evaluate-refuse for `seans_disi` / `piyasa_kapali` / `bar_bosluk` clears the
  signal chain (`engine.py:2168-2187`, `:2222`) so those tally **once per bar**.
  `spread` / `risk_*` leave the signal standing and re-tally each poll.
  Window `entry_blocks_since` â‰ˆ 16.08 21:34 (do **not** reset).
* **Why itâ€™s inefficient:** Two units in one column. API already has the split;
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
* **Why itâ€™s inefficient:** 6 cards Ã— 0.3 Hz is fine; 20 symbols is not free.
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
* **Why itâ€™s inefficient:** M30 trail is fine; a choppy M5 book is chatter.
* **Recommended fix:** Coalesce trail logs (ticket + SL + bar time); keep first
  BE lock and scale-out as TRADE.
* **Tradeoffs / Risks:** Intra-bar trail autopsy gets coarser.
* **Expected impact estimate:** Low
* **Removal Safety:** Likely Safe
* **Reuse Scope:** module

* **Title:** Per-ticket `tick` + `min_stop_distance` in `_update_stop`
* **Category:** I/O / Algorithm
* **Severity:** Low
* **Impact:** MT5 IPC Ã— open tickets
* **Evidence:** `_update_stop` (`engine.py:3568`, `:3612`) fresh tick +
  `min_stop_distance` per ticket. Structure/hybrid can scan swings
  (`:3639-3650`). Trail already latched per closed bar via `_stop_bar`.
* **Why itâ€™s inefficient:** Cycle already has a tick per symbol.
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
* **Evidence:** `gece_restart.py:13-19` â€” deliberately no health check; midnight
  is outside every session (earliest open 01:00). `track()` still
  `setdefault("original_sl", live sl)` for tickets missing `open_original_sl`
  (`execution.py:321-328`). Persist only runs from `note_fill` of **this**
  process. Tickets opened on the pre-diff PID were never stamped.
* **Why itâ€™s inefficient:** N/A CPU. The 00:00 load is the next time disk code
  becomes live â€” and the next time pre-patch tickets can be first-sighted.
* **Recommended fix:** Do not add a flatten-all. Optional: skip restart if
  `positions_get` non-empty (changes the 22.08-blind-bot contract â€” operator
  call). Until then: know that 00:00 loads this tree; pre-patch opens poison R.
* **Tradeoffs / Risks:** Skipping restart re-opens the â€œprocess up, terminal
  blindâ€ incident the script exists for.
* **Expected impact estimate:** High for those ticketsâ€™ autopsy; zero live PnL.
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
* **Why itâ€™s inefficient:** Defense-in-depth hole, not a measured bottleneck.
* **Recommended fix:** Add `/api/opt/run` (and maybe `/api/opt/cancel`) to the
  set. Optional `max_length` on `strategies` (same class as `timeframes`).
* **Tradeoffs / Risks:** Night/automation callers must send Origin. Panel
  already does.
* **Expected impact estimate:** n/a perf; Low residual CSRF.
* **Removal Safety:** Likely Safe
* **Reuse Scope:** local file (`web/app.py`)

* **Title:** `state.entry_block` writes on evaluate-refuse are RAM-only UI dead weight
* **Category:** Maintainability â€” **Dead Code** (panel) / live state still used by engine
* **Severity:** Low
* **Impact:** none measurable; two sources of â€œwhy didnâ€™t it enterâ€
* **Evidence:** `_evaluate` sets `state.entry_block` for seans/piyasa/bar_bosluk
  (`engine.py:2174+`) then clears the signal. Panel missed-signal table reads
  `GET /api/analysis/entry-blocks`, not `states[].entry_block`. Snapshot
  `_states_view` still serializes it every 3s.
* **Why itâ€™s inefficient:** Duplicate explanation surface. Not a hot loop.
* **Recommended fix:** Keep engine field for TRADE/debug; do not build a second
  panel column. If snapshot JSON is trimmed later, this field is a candidate.
* **Tradeoffs / Risks:** Removing the attribute breaks anything grepping state.
* **Expected impact estimate:** Low (JSON bytes).
* **Removal Safety:** Needs Verification
* **Reuse Scope:** module

* **Title:** `el(..., {html: ...})` sink exists; no current callers
* **Category:** Frontend / Security â€” **Over-Abstracted Code**
* **Severity:** Low (latent)
* **Impact:** next caller can skip `esc()`
* **Evidence:** `el()` (`app.js:154`) assigns `innerHTML` when `k === "html"`.
  Grep finds **no** `html:` call sites. Comment at `:79-86` still claims
  â€œverbatim elsewhereâ€ â€” mostly stale (logs/`scard-live` use `esc()`). Residual
  interpolations: `renderTop` `val` (`:426-427`) from `num`/`signed`/literals;
  AI cards `c.val` (`:1672-1675`) from numbers/times.
* **Why itâ€™s inefficient:** A helper that is unused but XSS-shaped.
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
* **Evidence:** `git status --short` â†’ `?? micofx/exits.py`. `engine.py` and
  `backtest.py` already import it. HEAD `0c33d72` does not contain the file.
* **Why itâ€™s inefficient:** Shared helper is the 08:00 landing; it is not in
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
* **Why itâ€™s inefficient:** One connection is required; search is still a
  history bus on the trading lock. Chunks only bound **hold duration**, not
  total copy_rates volume.
* **Recommended fix:** Prefetch once, detach workers. Use `strategies=` on a
  **flat** book when asked. Never a second terminal bind.
* **Tradeoffs / Risks:** Snapshot age vs live quote.
* **Expected impact estimate:** High jitter only while a search runs (opt is
  idle now â€” do not start one).
* **Removal Safety:** Needs Verification
* **Reuse Scope:** service-wide
* **Classification:** not a re-open of â€œlock held across 10k ratesâ€ â€” that
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
5. Do **not** restart, search, holdout-capture, or flatten to â€œload the scanâ€.

Already done (not wins): persist `original_sl`; deferred fill-verify; supervisor
off `_cycle`; `symbols_sig`; scale-out clamp; `overlay_stop`; chunked bars;
short MFE pad; `_merge` mfes; log CR/LF flatten; incumbent memo.

---

### 4) Deeper Optimizations (Do Next)

1. `day_stats` off the 3s snapshot path (keep 5s cache / halt caller).
2. Incremental `IndicatorCache` â€” identity tests vs full `compute()`.
3. Measure MT5 lock-hold (supervisor 14d vs verify peeks vs `account_info`)
   before more thread splits.
4. Optimizer: prefetch bars once; CPU-only workers; optional `strategies=`
   when **flat**.
5. Numba/Cython `simulate` inner loop **only after** a worker profile;
   required before any 3Ã— grid.
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
  trail-win autopsy (`r_realised â‰  1.000`, cash R within 2%).
* **Correctness (must stay green):** trail/BE identity suite, `test_core.py`,
  `test_scale_out_once.py`, fill-verify / defer tests, `test_simulate_records_per_trade_mfe.py`,
  `test_keep_log_does_not_quote_a_stale_stamp.py`, `test_opt_run_can_restrict_families.py`,
  `test_retired_indicators_stay_gone.py`. Incremental indicators need
  â€œfull vs append identical last signalâ€.
* **Do not** validate with a second MT5 bind, a sidecar sqlite writer, or
  `/api/app/restart` while opens exist.

---

### 6) Optimized Code / Patch (proposals only â€” not applied)

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

What must not change: forming-bar drop, buyâˆ§sellâ†’neither, fail-closed
duplicates, liveâ†”paper `overlay_stop` identity, score formula, `capture` as a
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
  (filtered to `STRATEGIES`; unknown â†’ drop / 409).
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

* **Supervisor / verify daemon vs engine** (Severity: Low â€” race class, not RCE)
* **Location:** `engine.py:983-1004`, `mt5client.py:1515-1547`
* **The Exploit:** Not remote. Two threads take `RLock` (safe). Fail-closed
  inflight is the duplicate-entry control. Risk is missed trail during a 14d
  history call, not privilege escalation.
* **The Fix:** Measure; do not drop the gate.

#### **Observations:**

* Log newline injection from family names / messages is **closed** at
  `logbus.emit` (`\r`/`\n` â†’ space). Do not re-open.
* `apply_best` still defaults `True` on `OptRun` â€” same privilege as HEAD.
* No hardcoded API keys/passwords in the product diff. `api_token` is still
  generated via `secrets.token_urlsafe(24)` when unset.
* `graft/` remains stale sourcedump (agent-context cost, not a vuln).
* AGENTS.md rewrite: skip. Constraints are already must/must-not. Density
  issue is `exits.py` untracked, which a commit fixes.

---

# 26.08 09:15 UTC+3 â€” remaining-opens landing

Independent remaining-opens audit (plus Claude event in `cursor/FOR_CLAUDE.md`).
**No restart.** Live PID still pre-diff while opens exist.

Landed: snapshot `day_stats(fetch=False)` + cycle warm; `_panel_capacity` 3s;
`margin_for` 5s; panel `viewPulse`; Origin on every mutation.

Measured won't-do: incremental cache (2.57ms/1680), Numba simulate (6.53ms/1680),
TRADE-per-SL (already once/bar via `_stop_bar`).

Leftover: 900s integrity full `required_bars` fetch (chunked, no compute).

---

## 26.08 ~09:52 â€” Claude derin tarama (SCAN-1)

Kapsam: canlÄ± aÄŸaÃ§ `micofx/`, `tests/`, `micofx/web/static/`,
`config/defaults.json`. `graft/` hariÃ§. Ãœstteki **kapalÄ± defter** esas
alÄ±ndÄ±; oradaki maddeler yeniden aÃ§Ä±lmadÄ±.

CanlÄ± PID **01:38** yÃ¼klemesinde; diskteki her ÅŸey **restart'a kadar
canlÄ± deÄŸil**. Ã–lÃ§emediÄŸim yerde **"muhtemel"** yazdÄ±m ve neyin
Ã¶lÃ§Ã¼lmesi gerektiÄŸini sÃ¶yledim. KanÄ±tsÄ±z mikro-optimizasyon yok.

---

### 1) Optimizasyon Ã–zeti

**SaÄŸlÄ±k: iyi.** Gecenin landing'leri (capacity TTL, day_stats TTL,
symbols_sig, parÃ§alÄ± bar Ã§ekimi, viewPulse) `/api/state` yolundaki MT5
kilit baskÄ±sÄ±nÄ± gerÃ§ekten dÃ¼ÅŸÃ¼rmÃ¼ÅŸ. Bu taramada **yeni bir sÄ±cak dÃ¶ngÃ¼
bulamadÄ±m**.

BulduÄŸum Ã¼Ã§ ÅŸey **bugÃ¼nÃ¼n darboÄŸazÄ± deÄŸil, yarÄ±nÄ±nki**:

1. `settings` tablosundaki Ã¼Ã§ JSON blobu **tam yeniden yazÄ±lÄ±yor**;
   halka tavanÄ±nda yazma baÅŸÄ±na **~1,1 MB**'a Ã§Ä±kÄ±yor (bugÃ¼n 77 KB).
2. `_CRITICAL_MUTATIONS` **Ã¶lÃ¼ sabit** â€” hem Ã§Ã¶p hem yanÄ±ltÄ±cÄ±.
3. `Engine.__new__` fikstÃ¼r Ã§Ã¼rÃ¼mesi (52 dosya) â€” bugÃ¼n **iki kez**
   regresyon taklidi yaptÄ±.

**DeÄŸiÅŸmezse en bÃ¼yÃ¼k risk:** kÄ±rmÄ±zÄ±nÄ±n anlamÄ±nÄ± yitirmesi. SÃ¼itte
fikstÃ¼r Ã§Ã¼rÃ¼mesi, panelde `left_on_table_r` â€” ikisi de "sÃ¼rekli yanan
uyarÄ±". GerÃ§ek bir arÄ±za bunlarÄ±n arasÄ±nda kaybolur. Bu, CPU'dan pahalÄ±.

---

### 2) Bulgular (Ã¶ncelikli)

#### O-1 â€” `trade_autopsies` tam blob yeniden yazÄ±mÄ±

* **Kategori:** I/O Ã¶lÃ§eklenmesi Â· **Ã–nem:** Orta (bugÃ¼n DÃ¼ÅŸÃ¼k)
* **Etki:** Her kapanÄ±ÅŸta tÃ¼m otopsi defteri tek JSON olarak sqlite'a
  yazÄ±lÄ±yor.
* **KanÄ±t:** `engine.py:1659` `set_setting("trade_autopsies", rows)`;
  `engine.py:90` `TRADE_AUTOPSY_LIMIT = 2000`. Ã–lÃ§Ã¼m (canlÄ± db,
  salt-okunur): **138 satÄ±r = 77.283 bayt â†’ ~560 bayt/satÄ±r**.
* **Neden:** Tavanda **2000 Ã— 560 B â‰ˆ 1,1 MB**, tek satÄ±r eklemek iÃ§in.
  GÃ¼nde ~40 kapanÄ±ÅŸla tavan **~50 gÃ¼nde** dolar.
* **Ã–nerilen dÃ¼zeltme (Ã¶neri):** Ya ayrÄ± bir `autopsies` tablosu +
  `INSERT` + eski satÄ±r budama, ya da tavanÄ± gerÃ§ekten okunan pencereye
  indir. Panel zaten son N satÄ±rÄ± gÃ¶steriyor.
* **Ã–dÃ¼nÃ§:** AyrÄ± tablo = ÅŸema gÃ¶Ã§Ã¼ + `Store` API geniÅŸlemesi. TavanÄ±
  indirmek bedava ama geÃ§miÅŸ kÄ±salÄ±r.
* **Beklenen etki:** Yazma baÅŸÄ±na ~1,1 MB â†’ ~1 KB. BugÃ¼n fark yok;
  50 gÃ¼n sonra kapanÄ±ÅŸ baÅŸÄ±na gÃ¶zle gÃ¶rÃ¼lÃ¼r fsync.
* **KaldÄ±rma gÃ¼venliÄŸi:** DÃ¼ÅŸÃ¼k risk â€” `r_realised`/`mfe_r` okuyan her
  ÅŸey (capture dahil) satÄ±r listesini okur, blob biÃ§imini deÄŸil.
* **Yeniden kullanÄ±m:** AynÄ± desen `entry_block_events` ve
  `execution_samples` iÃ§in de geÃ§erli.
* **Durum: muhtemel** (bugÃ¼n Ã¶lÃ§Ã¼lebilir darboÄŸaz **deÄŸil**). Ã–lÃ§Ã¼lecek:
  2000 satÄ±rlÄ±k defterle bir kapanÄ±ÅŸÄ±n `set_setting` sÃ¼resi.

#### O-2 â€” `entry_block_events` aynÄ± desen, daha sÄ±k

* **Kategori:** I/O Â· **Ã–nem:** DÃ¼ÅŸÃ¼k-Orta
* **KanÄ±t:** `engine.py:1478`; `engine.py:85` `ENTRY_EVENT_LIMIT = 2048`.
  Ã–lÃ§Ã¼m: **613 satÄ±r = 75.144 bayt â†’ ~122 bayt/satÄ±r**.
* **Neden:** 45 sn debounce var (kapalÄ± defter), yani her poll deÄŸil.
  Ama tavanda **~250 KB / 45 sn**.
* **DÃ¼zeltme:** O-1 ile aynÄ±; tek Ã§Ã¶zÃ¼m ikisini birden kapatÄ±r.
* **Not:** Yeni `seans_disi` / `piyasa_kapali` / `bar_bosluk` dallarÄ±
  satÄ±r Ã¼retimini artÄ±rdÄ±. BugÃ¼n **613/2048 â€” taÅŸma yok**, 9 gÃ¼nlÃ¼k
  geÃ§miÅŸ duruyor. Ã–lÃ§tÃ¼m, alarm deÄŸil.

#### O-3 â€” `execution_samples` 59 KB blob

* **Ã–nem:** DÃ¼ÅŸÃ¼k Â· **KanÄ±t:** canlÄ± db, 59.401 bayt.
* AynÄ± desen. ÃœÃ§ blob toplamÄ± **227 KB** ve `settings` tablosunun
  neredeyse tamamÄ±. Tek baÅŸÄ±na iÅŸ deÄŸil; O-1 Ã§Ã¶zÃ¼lÃ¼rse birlikte Ã§Ã¶zÃ¼lÃ¼r.

#### O-4 â€” `_CRITICAL_MUTATIONS` Ã¶lÃ¼ sabit

* **Kategori:** Ã–lÃ¼ kod + yanÄ±ltÄ±cÄ± gÃ¼venlik yÃ¼zeyi
* **Ã–nem:** DÃ¼ÅŸÃ¼k (iÅŸlev) / **Orta (yanÄ±ltma)**
* **KanÄ±t:** `web/app.py:570` tanÄ±mlÄ±; **dosyada baÅŸka referans yok**
  (`grep -n "_CRITICAL_MUTATIONS"` â†’ tek satÄ±r).
* **Neden:** 09:15'te "her mutasyona Origin" inince bu kÃ¼me iÅŸlevsiz
  kaldÄ± ama silinmedi. Okuyan biri **"yalnÄ±z bu yollar korunuyor"**
  sanabilir; daha kÃ¶tÃ¼sÃ¼, yeni bir uÃ§ ekleyip **koruma kazandÄ±ÄŸÄ±nÄ±**
  zannedebilir. Kod doÄŸru, **belge yalan sÃ¶ylÃ¼yor**.
* **Ã–nerilen dÃ¼zeltme:** Sabiti sil. Middleware yorumunda "her mutasyon"
  zaten yazÄ±yor.
* **KaldÄ±rma gÃ¼venliÄŸi:** **ORTA** â€” *(dÃ¼zeltme 26.08 10:14, Cursor
  yakaladÄ±)*. Ä°lk yazdÄ±ÄŸÄ±mda "referans yok, test yok" dedim; **yanlÄ±ÅŸtÄ±**.
  ÃœrÃ¼n kodunda okuyan yok (doÄŸru), ama **testlerde 6 assert** var:
  `tests/test_session_csrf_gate.py:142-146` ve
  `tests/test_holdout_capture_endpoint.py:192`. Bunlar kÃ¼meyi
  **belgelenmiÅŸ kritik liste** olarak doÄŸruluyor. Silmek **Ã¶nce o
  assert'leri yeniden yazmayÄ±** gerektirir â€” tek satÄ±rlÄ±k iÅŸ deÄŸil.
  HatanÄ±n kÃ¶kÃ¼: yalnÄ±z `micofx/web/app.py` iÃ§inde grep'leyip sonucu
  "hiÃ§bir yerde yok" diye genelledim; `tests/` taramadÄ±m.
* **Durum: kesin** (Ã¶lÃ¼ sabit tespiti doÄŸru; kaldÄ±rma maliyeti
  ilk raporda **eksik deÄŸerlendirildi**).

#### O-5 â€” `Engine.__new__` fikstÃ¼r Ã§Ã¼rÃ¼mesi

* **Kategori:** BakÄ±m yapÄ±labilirlik Â· **Ã–nem:** Orta
* **KanÄ±t:** `tests/` iÃ§inde `__new__` kullanan **88 dosya**:
  `Engine` **52**, `Optimizer` **30**, `Supervisor` **14**,
  `RiskManager` 3, `ExecutionMonitor` 1.
* **Neden:** `__init__`'e eklenen her alan bu fikstÃ¼rleri kÄ±rar ve
  kÄ±rÄ±lma **regresyon gibi gÃ¶rÃ¼nÃ¼r**. BugÃ¼n iki kez oldu:
  `ExecutionMonitor._originals` (08:20) ve `Engine._day_cache` (09:52).
  Ä°kisini de canlÄ± sanÄ±p dibine kadar kovalamak zorunda kaldÄ±m; ikisi de
  fikstÃ¼rdÃ¼.
* **AsÄ±l maliyet CPU deÄŸil, dikkat:** bir gÃ¼n yÄ±ÄŸÄ±nÄ±n iÃ§inde **gerÃ§ek**
  bir regresyon duracak ve "yine fikstÃ¼r" diye geÃ§ilecek.
* **Ã–nerilen dÃ¼zeltme:** Ortak `make_engine()` / `make_optimizer()`
  yardÄ±mcÄ±sÄ± `__init__`'in alan kÃ¼mesini **tek yerde** yansÄ±tsÄ±n.
* **Ã–dÃ¼nÃ§:** 88 dosyalÄ±k dokunuÅŸ bÃ¼yÃ¼k ve gÃ¼rÃ¼ltÃ¼lÃ¼. **Bu tarama
  kapsamÄ±nda deÄŸil** â€” TASK-2 yalnÄ±z bir dosyayÄ± gÃ¶Ã§ ettiriyor.
* **Durum: kesin** (iki canlÄ± Ã¶rnek).

---

### 3) HÄ±zlÄ± kazanÄ±mlar

1. **O-4** â€” `_CRITICAL_MUTATIONS` sil. Tek satÄ±r, referanssÄ±z, testsiz.
2. **TASK-1** â€” panel `left_on_table_r` yalnÄ±z kazananda (ayrÄ± gÃ¶rev).
3. **TASK-2** â€” tek fikstÃ¼r dosyasÄ± (ayrÄ± gÃ¶rev).

BunlarÄ±n dÄ±ÅŸÄ±nda **hÄ±zlÄ± kazanÄ±m bulamadÄ±m.** Gecenin landing'leri kolay
olanlarÄ± zaten almÄ±ÅŸ.

---

### 4) Derin optimizasyonlar

* **O-1/O-2/O-3 birlikte:** `settings`'teki Ã¼Ã§ halka blobunu satÄ±r
  tabanlÄ± bir tabloya taÅŸÄ±mak. Tek iÅŸ, Ã¼Ã§ bulguyu kapatÄ±r. **Ã–nce Ã¶lÃ§:**
  2000 satÄ±rlÄ±k defterle bir `set_setting` ne kadar sÃ¼rÃ¼yor? Ã–lÃ§meden
  yapÄ±lmamalÄ± â€” bugÃ¼n 77 KB'lÄ±k bir yazma darboÄŸaz deÄŸil.
* **O-5:** fikstÃ¼r yardÄ±mcÄ±sÄ±. Performans deÄŸil, **yanlÄ±ÅŸ alarm** bÃ¼tÃ§esi.

---

### 5) DoÄŸrulama planÄ±

| DeÄŸiÅŸiklik | DoÄŸrulama |
|---|---|
| O-4 sil | `grep -rn "_CRITICAL_MUTATIONS" micofx/` boÅŸ; `pytest tests/test_session_csrf_gate.py` yeÅŸil (Origin kapÄ±sÄ± baÄŸÄ±msÄ±z) |
| O-1/O-2 gÃ¶Ã§ | GÃ¶Ã§ Ã¶ncesi/sonrasÄ± `trade_autopsy_report()` **bayt-eÅŸ**; `capture` ve `left_total` deÄŸiÅŸmemeli; 2000 satÄ±r sentetik yÃ¼kle sÃ¼re Ã¶lÃ§ |
| O-5 yardÄ±mcÄ± | GÃ¶Ã§ edilen her dosya **Ã¶nce kÄ±rmÄ±zÄ± sonra yeÅŸil**; `Engine.__init__`'e sahte alan ekleyip yardÄ±mcÄ±nÄ±n yakaladÄ±ÄŸÄ±nÄ± gÃ¶ster |

Her biri iÃ§in **fail-first**, sonra `pytest -q` + `ruff check`.

---

### 6) Ã–nerilen yamalar (yalnÄ±zca Ã¶neri â€” uygulanmadÄ±)

**O-4** â€” `micofx/web/app.py` ~570, sil:

    # OLU: 09:15'ten beri okunmuyor. Origin kapisi middleware'de HER
    # mutasyona uygulaniyor. Bu kume "yalniz bunlar korunuyor" izlenimi
    # veriyor - yanlis.
    _CRITICAL_MUTATIONS = frozenset({...})

**O-5** â€” `tests/_engine_fixture.py` (yeni, Ã¶neri):

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

### SECURITY AUDIT: kirli aÄŸaÃ§ (`0c33d72` â†’ Ã§alÄ±ÅŸan aÄŸaÃ§)

Kapsam: **staged + unstaged** Ã¼rÃ¼n diff'i. 39 dosya, **+1227 / âˆ’514**.
Her deÄŸiÅŸen satÄ±r saldÄ±rÄ± yÃ¼zeyi varsayÄ±ldÄ±.

**Risk Assessment: DÃœÅžÃœK.** Kritik veya YÃ¼ksek bulgu **yok**. Kimlik
bilgisi sÄ±zÄ±ntÄ±sÄ± **yok**. Enjeksiyon yÃ¼zeyi **temiz**. Gecenin CSRF
sÄ±kÄ±laÅŸtÄ±rmasÄ± diff'in en gÃ¼Ã§lÃ¼ tarafÄ± â€” her mutasyon artÄ±k Origin
istiyor, sadece adlandÄ±rÄ±lmÄ±ÅŸ bir kÃ¼me deÄŸil.

#### Findings:

* **`Host` baÅŸlÄ±ÄŸÄ± izinli Origin kÃ¼mesini kuruyor** (DÃ¼ÅŸÃ¼k)
  * **Location:** `web/app.py:610-612` â€” `host = request.headers.get("host")`,
    `allowed = {f"http://{host}", f"https://{host}"}`
  * **Exploit:** Ä°stemci hem `Host: evil` hem `Origin: http://evil`
    gÃ¶nderirse kÃ¼me kendi kendini doÄŸrular. DoÄŸrudan 127.0.0.1 bind'de
    istek zaten sunucuya ulaÅŸmaz; araya bir ters vekil girerse anlamlÄ±
    hale gelir.
  * **Fix (Ã¶neri):** Ä°zinli origin'i **bind adresinden** tÃ¼ret
    (`run.py`'deki host/port), istek baÅŸlÄ±ÄŸÄ±ndan deÄŸil.
  * **Not:** `sec-fetch-site == "cross-site"` reddi ve `SameSite=Strict`
    Ã§erez bunu pratikte kapatÄ±yor. **Derinlik savunmasÄ± notu**, aÃ§Ä±k kapÄ±
    deÄŸil.

* **Ã–lÃ¼ `_CRITICAL_MUTATIONS` gÃ¼venlik yÃ¼zeyini yanlÄ±ÅŸ anlatÄ±yor**
  (DÃ¼ÅŸÃ¼k â€” bkz. O-4)
  * **Location:** `web/app.py:570`
  * **Exploit:** DoÄŸrudan sÃ¶mÃ¼rÃ¼ yok. **BakÄ±m riski:** bir sonraki
    geliÅŸtirici yeni uÃ§ noktayÄ± bu kÃ¼meye ekleyip korunduÄŸunu sanabilir.
  * **Fix:** Sil.

* **Ãœretilen token'Ä±n son 6 hanesi loga yazÄ±lÄ±yor** (Bilgilendirme)
  * **Location:** `run.py:244` â€” `...{api_token[-6:]} ile bitiyor`
  * **Exploit:** `token_urlsafe(24)`; 6 karakter aÃ§Ä±ÄŸa Ã§Ä±ksa da kalan
    entropi kaba kuvvete kapalÄ±. Log gitignore'da ve makine yerel.
  * **Fix:** Gerekmez â€” operatÃ¶rÃ¼n token'Ä± ayÄ±rt etmesi iÃ§in bilinÃ§li
    kolaylÄ±k. **Kayda geÃ§iyorum, dÃ¼zeltme Ã¶nermiyorum.**

#### Observations (kontrol edildi â€” temiz):

* **SQL enjeksiyonu:** `Store` yolunda f-string / `%` / `.format` ile
  kurulmuÅŸ `execute` **yok**. Parametrize.
* **XSS:** `app.js`'te 47 `innerHTML` atamasÄ±; hepsi `esc()` / `num()` /
  `signed()` Ã¼zerinden. KaÃ§aksÄ±z tek interpolasyon `app.js:2224` ve deÄŸer
  **sayÄ±** (`res.symbols.length`). `el({html})` kolu kapalÄ± defterde
  silinmiÅŸ â€” **yeni sink eklenmemiÅŸ**, doÄŸruladÄ±m.
* **CSRF:** Her `POST/PUT/PATCH/DELETE` iÃ§in Origin + `sec-fetch-site`.
  Oturum karÅŸÄ±laÅŸtÄ±rmasÄ± `secrets.compare_digest` â€” **sabit zamanlÄ±**.
* **IDOR:** `/api/` altÄ±ndaki her yol oturum istiyor; muaf olanlar
  (`/`, `/static`, `/favicon.ico`) mutasyon deÄŸil.
* **Girdi sÄ±nÄ±rlarÄ±:** `_ForbidModel` (bilinmeyen alan reddi),
  `_validate_risk_bounds`, `_validate_sessions`, `_validate_enum_fields`,
  `OptRun.strategies/timeframes max_length=32`. SÄ±nÄ±rsÄ±z gÃ¶vde bulamadÄ±m.
* **MT5 kilidi yarÄ±ÅŸÄ±:** Bar Ã§ekimi parÃ§alÄ± ve parÃ§alar arasÄ± kilidi
  bÄ±rakÄ±yor. Ä°kinci `initialize()` yok. Diff'te yeni doÄŸrudan
  `MetaTrader5` importu **yok** â€” doÄŸruladÄ±m.
* **Debug yÃ¼zeyi:** `docs_url=None`, `redoc_url=None`. AÃ§Ä±k ÅŸema yok.
* **SÄ±nÄ±rsÄ±z dÃ¶ngÃ¼:** Yeni `while`/kuyruk yok; yeni sayaÃ§ dallarÄ± halka
  tavanÄ±na tabi (2048).

---

**Uygulanan hiÃ§bir ÅŸey yok.** Bu blok not; O-1â€¦O-5 ve gÃ¼venlik bulgularÄ±
Ã¶neri. AGENTS.md Ã¶nerisi ayrÄ± blokta. TASK-1 ve TASK-2 sÄ±rada.

### AGENTS.md proposal (not applied)

> `AGENTS.md`'ye **dokunmadÄ±m**. AÅŸaÄŸÄ±daki metin Ã¶neri; Cursor uygular
> veya reddeder. Mevcut dosyanÄ±n dili Ä°ngilizce olduÄŸu iÃ§in Ã¶neri de
> Ä°ngilizce â€” repo sÃ¶zleÅŸmesi (yorum/commit Ä°ngilizce) korunsun diye.
>
> YoÄŸunluk iÃ§in yaptÄ±klarÄ±m: her satÄ±r **tek** kural; "neden" yalnÄ±z
> davranÄ±ÅŸÄ± deÄŸiÅŸtiriyorsa duruyor; genel yazÄ±lÄ±m tavsiyesi silindi;
> tuzaklar "ne yapma"dan "ne yanlÄ±ÅŸ okunuyor"a Ã§evrildi. Cursor'un
> pazarlÄ±ksÄ±z listesindeki maddelerin hepsi iÃ§eride.

---

# AGENTS.md

Live **fx** bot, `C:\Users\Administrator\MicoFx`. Constitution:
`MASTER_PROMPT.md` Â§19. Do not port `D:\MicoAi` extras unasked.

## Hard rules

- Python is `C:\MicoFX-venv\Scripts\python.exe`. No other interpreter.
- The live process **owns** `data/micofx.db` and the MT5 terminal. No
  second sqlite writer, no `mt5.initialize()` sidecar. `mt5.shutdown()`
  only in the dying process on `/api/app/restart`.
- Live writes go through the running bot: `GET http://127.0.0.1:8900/`
  for the session cookie, then the API. **Every** POST/PUT/PATCH/DELETE
  needs `Origin: http://127.0.0.1:8900` â€” not a named subset. Port busy:
  do not steal 8900.
- No LLM inside engine, optimizer or supervisor. Panel "AI" is the rule
  supervisor.
- Exit model is hard ATR stop + ATR trail. `tp_atr_mult`, `partial_tp_r`
  ladders, `max_bars_in_trade`, `stale_exit_ratio`, `breakeven_atr` do
  not come back. Overlays (0 = off): `breakeven_at_r` (live 1.5, not 0.5
  â€” BE-2 cost GER40 âˆ’32 R) and one-shot `partial_at_r`. Neither is an
  `OPT_FIELDS` axis.
- `exits.overlay_stop` is the single source; `engine._update_stop` and
  `backtest._trail_one` are its two ends. **Do not touch either without
  the identity test.**
- A forming candle never signals. Buy âˆ§ sell on one bar â†’ neither.
- Opt apply writes `OPT_FIELDS` only. Never silently enable
  `ensemble_enabled`. Apply gates are `_slice_ok`, `reject_reason` and
  `_beats_incumbent`. Calendar reopt is gone.
- `EXIT_RISK_FIELDS` mid-trade â†’ **409**. `breakeven_at_r` and
  `partial_at_r` are deliberately **not** in that set: they apply to
  already-open tickets.
- **11 live families.** `alpha_trend` / `mavilim` / `st_trend` /
  `macd_flip` retired 26.08; `test_retired_indicators_stay_gone`
  blocks their return. `ichimoku` stays.
- **No restart while positions are open** â€” `track()` first-sight
  `setdefault`s `original_sl` to the *current trail*, poisoning every R
  derived from it until those tickets die.
- Watch mode never opens. Wrong `broker_symbol` â†’ unavailable, no fuzzy
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
  empty `profit`; summing the ledger gives the wrong **sign** (âˆ’151 USD
  against a real +379 flatten stream). `r_realised` and `mfe_r` are
  complete, so capture is unaffected. **Do not rewrite those 27 rows.**
- Realised cash appears in three log shapes: `kapandi â€¦ kar=`,
  `Pozisyon kapatildi â€¦ kar~ (anlik)`, and `parca kapatildi â€¦ kar NÃ—ATR`
  (old form carries **no** cash). Only the first was ever in the ledger.
- `r_realised` divides by `|entry âˆ’ original_sl|`. **Do not repair
  pre-fix rows** (`sl` + `r=+1.0`); their cash is the truth.
- `mfe_r` is an **intrabar peak**, never harvestable. Summing `mfe_r` and
  calling it "left on the table" is invalid. `left_on_table_r` on a loser
  is mostly the loss itself, not a missed gain.
- Holdout `capture` is a **visible column only** â€” not a score input, not
  an apply gate.
- The keep line reads `(taze test â€¦R)` or `(damga â€¦R, dd.mm)`. A pre-fix
  `test net` figure is not current.
- `_MAX_SIGNAL_BAR_AGE_BARS = 2` Ã— timeframe. US30 is the only M5 symbol,
  so its 600 s threshold trips on overnight tick droughts â€” `bar_bosluk`
  there is **normal**, not a bar-refresh bug.
- `scale_out_done` prunes to live tickets under the same lock as
  `weekend_pending`; `remain` uses `fill["volume"]`.
- The fill verifier sleeps on its **own** thread, not `micofx-engine`.
  Do not "fix" duplicate-entry protection while changing it.

## Locations (non-obvious only)

- Runtime: `data/micofx.db`, `logs/micofx.log` (gitignored).
- Agent bridge (gitignored, never `git add`): `cursor/FOR_CLAUDE.md`,
  `claude/FOR_CURSOR.md`.
- Installer `KUR.bat` â†’ `KUR.ps1`; launchers stay at repo root.
- Audit notes (not executable): `OPTIMIZATIONS.md`.
- `graft/` is a stale source dump â€” its line numbers are not live.

---

**Ã–neri sonu.** UygulanmadÄ±.


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
- 7 families (arsiv) - 8 since 31.08; no restart with opens.
- Fail-first with pytest/ruff. Persist via Store only.
- Yellow/red gates stay operator-only. Holdout capture is not a score input.
- Autopsy gotchas: `open_original_sl` must be tracked, profit-empty rows exist, `gmtime` broker calendar used.
```

---

# 31.08 01:15 â€” full A-Z optimization audit

Read-only pass. Nothing was PATCHed, no search started, no flatten, no
capture, no restart. Evidence is live `/api/state` at 01:15, a full
`pytest tests/ -q` run, `ruff check`, and a line-by-line read of
`engine.py` (4534), `optimizer.py`, `backtest.py`, `strategy.py`,
`indicators.py`, `risk.py`, `supervisor.py`, `mt5client.py`,
`execution.py`, `sessions.py`, `web/app.py`, `store.py`, `models.py`,
`static/app.js`, `config/defaults.json`, `run.py`, `gece_restart.py`.
Grid sizes below were computed with the venv interpreter against the
shipped `defaults.json`, not estimated. HEAD `cf2dcc5`.

## 1) Optimization summary

Health: the trading core is correct where it matters most â€” fill-next-open
is honest, no lookahead in `supertrend`/`parabolic_sar`/`ichimoku`, the
forming candle never signals, clocks are `gmtime` everywhere they should
be, and there is no SQL injection or hardcoded secret. What is broken is
**coverage and throughput**: the search judges six of seven families on a
0.08â€“2.6% fixed random slice of their own grid, the live book is spending
most of its wall clock refusing its own signals, and roughly a fifth of
the settings surface is write-only.

Top 3 by ROI:

1. **Grid coverage collapse.** `dual_t3` has 2,488,320 grid points and a
   2,000 combo budget. Every "best" this book has ever applied for six
   families came out of a `default_rng(7)` lottery ticket.
2. **The bar-age gate is one bar tighter than documented, and it is what
   is blocking the live book right now.** 7 of 9 symbols sat on
   `entry_block = "bar_bosluk"` at 01:15.
3. **`r_cap` is not the 2% ceiling it is described as.** `edge_scale`
   (max 2.2) is inside the multiplier that scales the cap, so a proven
   symbol's automatic 1R ceiling is ~4.4% of balance.

Biggest risk if nothing changes: the book keeps re-applying parameters
selected from a fraction of a percent of the search space while the live
engine refuses the signals those parameters were fitted to produce. The
walk-forward number and the live number will keep diverging and neither
will explain the other.

Live snapshot 31.08 01:15 (`/api/state`, session cookie):
balance 1656.15, 0 positions, trading off, MT5 connected,
`mt5_terminal_path = C:\Program Files\MetaTrader 5` (correct â€” the exe
exists). Entry blocks: `bar_bosluk` Ã—7 (BRENTOIL-PERP, GOLD-PERP, XAUUSD,
JPN225, NAS100, US30, BTCUSD), `spread` Ã—1 (SpotBrent, `spread_atr`
0.184), `seans_disi` Ã—1 (GER40, opens in 117 min). Zero symbols were in a
state where a signal could have been taken.

Test/lint state: `pytest tests/ -q` â†’ **3 failed, 2610 passed, 1 xfailed,
88.60 s**. `ruff check micofx/ tests/ run.py backup.py gece_restart.py` â†’
clean.

## 2) Findings (prioritized)

### F1 â€” Six of seven families search 0.08â€“2.6% of their own grid

* **Category** Algorithm
* **Severity** Critical
* **Impact** Parameter quality, walk-forward/live agreement, every R the book earns
* **Evidence** Computed grid products from `config/defaults.json` at the
  searched timeframes (M15/M30) against `max_combos: 2000`
  (`defaults.json:714`):

  | family | grid points | coverage |
  |---|---|---|
  | dual_t3 | 2,488,320 | 0.080% |
  | burst | 1,492,992 | 0.134% |
  | mtf_pullback | 559,872 | 0.357% |
  | stoch_flip | 259,200 | 0.772% |
  | t3_flip | 144,000 | 1.389% |
  | parabolic_flip | 77,760 | 2.572% |
  | ichimoku | 720 | 100% (exhaustive) |

  Truncation is a uniform random draw, not a stratified or Latin-hypercube
  sample, `backtest.py:980-987`:

```980:987:micofx/backtest.py
    rng = np.random.default_rng(seed)
    seen: set[tuple[int, ...]] = set()
    attempts = 0
    while len(seen) < max_combos and attempts < max_combos * 40:
        attempts += 1
        seen.add(tuple(int(rng.integers(0, s)) for s in sizes))
    return keys, sorted(seen)
```

  Seed is `combo_seed`, default 7 (`optimizer.py:190`, `818-820`), so the
  same 2,000 of 2,488,320 points are drawn on every run of every symbol.
* **Why it's inefficient** The refine rounds walk Â±1 per axis from the top
  12 seeds (`backtest.py:1416-1430`), which cannot bridge a 10-axis space
  sampled at 0.08%. `_plateau_scores` neighbours (`backtest.py:1043-1051`)
  therefore exist almost only because refine manufactured them, and when
  `grounded` comes back empty the code falls back to `list(blended)`
  (`backtest.py:1464`) â€” the plateau requirement silently disappears
  instead of failing loudly.
* **Recommended fix** Three independent levers, in ROI order: (a) give
  `dual_t3` and `burst` a per-family budget â€” `strategy_max_combos` is
  already read by `family_max_combos` (`optimizer.py:54-72`) but has **no
  entry in defaults.json**, so it is a switch that exists and is wired to
  nothing; (b) replace the uniform draw with a Sobol/LHS sample over the
  same budget, which cuts the variance of the coverage without costing a
  single extra simulation; (c) cut axes that cannot pay â€” `st_period`'s 2
  values are inert on the `st_mult: 0.0` third of dual_t3's grid
  (`strategy.py:651`), so ~25% of those 2.49M points are exact duplicates
  under distinct grid indices and are being spent as if they were
  candidates.
* **Tradeoffs / Risks** (a) costs wall clock linearly. (b) is free. (c)
  changes the grid, so past `opt_runs` stamps are not comparable.
* **Expected impact** (c) alone recovers ~25% of dual_t3's effective
  budget at zero cost. (b) is the largest quality-per-second win available
  in this repo.
* **Removal Safety** Needs Verification (grid change invalidates stamps)
* **Reuse Scope** service-wide

### F2 â€” The bar-age gate measures from bar open, so the real slack is one bar

* **Category** Algorithm / Reliability
* **Severity** Critical
* **Impact** Signals taken vs signals refused â€” directly, trades per day
* **Evidence** `engine.py:2163-2177` compares against `state.last_bar`:

```2163:2165:micofx/engine.py
        tf_sec = timeframe_seconds(cfg.timeframe)
        if (state.last_bar > 0
                and (server_now - state.last_bar) > _MAX_SIGNAL_BAR_AGE_BARS * tf_sec):
```

  and `state.last_bar = bars.last_closed_time` (`engine.py:2403`) is the
  **open** stamp of the last closed bar. `_MAX_SIGNAL_BAR_AGE_BARS = 2`
  is documented at `engine.py:58-59` as "the bar that follows it, plus one
  extra bar of poll slack". Arithmetically the signal dies `1 Ã— tf_sec`
  after its bar *closed*, not `2 Ã— tf_sec`.
* **Why it's inefficient** One of the two bars of the budget is consumed
  by the bar's own duration before the poll loop gets a single chance at
  it. Live at 01:15 this was the single most common refusal: 7 of 9
  symbols, including NAS100 and US30 which explicitly showed
  `"sinyal bari gecmis (bosluk)"`.
* **Recommended fix** Measure from bar close: compare
  `server_now - (state.last_bar + tf_sec)`, or set the constant to 3 and
  document that one bar is spent on the bar itself. The first is the
  honest fix; the second preserves the current arithmetic while making the
  comment true.
* **Tradeoffs / Risks** Widening the window admits older signals. The
  Friday-close-to-Monday-open case the comment at `engine.py:2166-2168`
  guards is unaffected â€” that gap is measured in days, not one bar.
* **Expected impact** Doubles the acceptance window. On a book showing 7/9
  symbols blocked on exactly this gate, this is the highest-yield single
  line in the tree.
* **Removal Safety** Needs Verification (cover with a fail-first test on
  an M30 signal at `close + 90 min`)
* **Reuse Scope** local file

### F3 â€” `r_cap` is scaled by the edge multiplier, so the "auto 2%" 1R ceiling is ~4.4%

* **Category** Reliability / Risk
* **Severity** Critical
* **Impact** Actual per-trade risk vs stated per-trade risk
* **Evidence** `risk.py:483-486`:

```483:486:micofx/risk.py
        r_pct = max(stored, self.AUTO_R_PCT)
        r_cap = (balance * r_pct / 100.0 * multiplier
                 / (sl_distance * money_per_unit))
```

  `multiplier` was already built as `lot_multiplier * edge_scale *
  ai_scale` at `risk.py:449-452`, and `EDGE_MAX = 2.2` (`risk.py:279`).
* **Why it's inefficient** The cap is supposed to be the backstop that the
  edge push is measured *against*. Multiplying the backstop by the same
  push it is bounding makes it not a backstop. AGENTS describes this as
  "auto 1R `max(risk_percent, 2%)`"; the code delivers up to 4.4%.
* **Recommended fix** Build `r_cap` from `lot_multiplier` only (or from
  1.0), and apply `edge_scale`/`ai_scale` to the raw lot before the cap,
  not inside it.
* **Tradeoffs / Risks** Live lots on proven symbols shrink. That is the
  point, but it is a real change in position size on a 1656 USD account
  and should be landed while flat.
* **Expected impact** Caps worst-case single-trade risk at the documented
  2% instead of 4.4%.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F4 â€” Lot budget is diluted by names that cannot trade

* **Category** Algorithm / Cost
* **Severity** High
* **Impact** Lot size on every live entry
* **Evidence** `_vacant_enabled_count` (`risk.py:366-374`) counts every
  `enabled` symbol without one of our tickets and the budget is split
  `budget / n` (`risk.py:409`). It never consults the supervisor, and a
  quarantined symbol carries `risk_scale = 0.0` (`supervisor.py:980`).
* **Why it's inefficient** A quarantined name reserves a full share of
  book margin it is forbidden to spend. With 9 enabled names and 2
  quarantined, every real entry is sized at 7/9 of its intended lot.
* **Recommended fix** Exclude symbols whose supervisor verdict is
  `quarantine` from the vacancy count.
* **Tradeoffs / Risks** Lots grow on the surviving names; interacts with
  F3 (fix F3 first or the two compound).
* **Expected impact** Proportional: `enabled / (enabled - quarantined)`.
  At 2 of 9 quarantined that is +28.6% lot per entry.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F5 â€” Whole-history spread median leaks backwards into every in-sample window

* **Category** Algorithm (correctness)
* **Severity** High
* **Impact** Search honesty; the cost the walk-forward charges
* **Evidence** `backtest.py:275-279`:

```275:279:micofx/backtest.py
    pts = np.asarray(spread, dtype=np.float64)
    quoted = pts[pts > 0]
    if quoted.size == 0:
        return pts
    return np.where(pts > 0, pts, float(np.median(quoted)))
```

  Built once at `backtest.py:1211`, **before** the window split at
  `backtest.py:1147-1149`. On GER40 M30 this imputation touches 24% of
  bars (the function's own docstring number).
* **Why it's inefficient** An in-sample bar's trading cost depends on
  spreads quoted in the validation and holdout segments. It is a mild
  leak â€” a median, not a signal â€” but it is the exact class of thing the
  fill-next-open discipline exists to prevent, and it silently makes the
  holdout slightly less independent.
* **Recommended fix** Compute the imputation median per window, from the
  selection segments only, and reuse that scalar for validation/holdout.
* **Tradeoffs / Risks** Scores shift. All stored `opt_runs` scores become
  non-comparable to new ones.
* **Expected impact** Removes the last identified backwards dependency in
  the search.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F6 â€” The shared `grid` block in defaults.json is dead at every searched timeframe

* **Category** Dead Code / Algorithm
* **Severity** High
* **Impact** Four exit axes are not searched at all
* **Evidence** `defaults.json:388-391` searches only `["M15","M30"]`;
  `uses_swing_exits` is True at â‰¥900 s (`models.py:646-647`); the store's
  shared grid equals the factory grid so `overlay_axes_operator_owns`
  returns empty (`optimizer.py:630-636`), and `SWING_GRID_OVERLAY`
  overwrites all four axes for any family that does not name them itself
  (`optimizer.py:661-672`). Net: `sl_atr_mult` 0.5/0.7/0.9
  (`defaults.json:682-684`), `trail_start_atr` 0.4/0.7 (`690`,`693`),
  `trail_step_atr` 0.25 (`699`) and `max_spread_atr` 0.05/0.18
  (`708`,`711`) are never evaluated. What actually runs is
  `models.py:600-603`.
* **Why it's inefficient** ~30 lines of config that an operator can edit,
  that the panel shows, and that changes nothing. It is a trap, not just
  waste.
* **Recommended fix** Either delete the shadowed axes from the shared grid
  block, or make `SWING_GRID_OVERLAY` merge rather than overwrite.
* **Tradeoffs / Risks** Merging changes grid size for six families.
* **Expected impact** Correctness of operator intent; no runtime cost.
* **Removal Safety** Likely Safe (delete); Needs Verification (merge)
* **Reuse Scope** service-wide

### F7 â€” Five OPT_FIELDS axes have no grid anywhere

* **Category** Dead Code / Algorithm
* **Severity** High
* **Impact** `structural` trail mode has never been evaluated
* **Evidence** `models.py:521-538` vs `defaults.json:401-713`:
  `adx_max` (read by every gated family via `strategy.py:425-426`),
  `min_body_ratio` (`strategy.py:528-531`), `trail_mode` and
  `trail_lookback` (`backtest.py:541-542`, `609`), `min_atr_ratio`
  (`backtest.py:836-838`). Additionally `rsi_length`, `stoch_length`,
  `smooth_k`, `smooth_d` are never searched **and** never gate a family â€”
  `_common` computes StochRSI purely for the panel readout
  (`strategy.py:414`, `357`).
* **Why it's inefficient** Because `trail_mode` never varies, `structural`
  is permanently False and the entire structure/hybrid trail path
  (`swing_lows`/`swing_highs`, `backtest.py:543-544`) is code the search
  has never exercised. `adx_max` is a live gate on six families with a
  value nobody tuned.
* **Recommended fix** Add grids for `adx_max` and `min_body_ratio` (cheap,
  small axes). Leave `trail_mode` out until the structural path has a
  fail-first test â€” searching it today would also expose the per-combo
  `swing_lows` rebuild (F13).
* **Tradeoffs / Risks** Adding axes multiplies an already-undersampled
  grid; pair with F1(a) or the coverage gets worse.
* **Expected impact** Medium; `adx_max` is a real regime lever currently
  frozen.
* **Removal Safety** Needs Verification
* **Reuse Scope** service-wide

### F8 â€” `simulate()` rebuilds a full-length Python list per combo per window

* **Category** CPU / Memory
* **Severity** High
* **Impact** Search wall clock
* **Evidence** `backtest.py:514-515`:

```514:515:micofx/backtest.py
    else:
        trigger_pad = np.asarray(trigger_pad, dtype=np.float64).tolist()
```

  `walk_forward` already built `trigger_pad` as a list once
  (`backtest.py:387`, `1211-1212`); `simulate` re-wraps it in an array and
  re-lists it on every call.
* **Why it's inefficient** At ~90k bars Ã— 4 windows Ã— 2000 combos Ã— 6
  rounds this is on the order of 4Ã—10^12 boxed float allocations across a
  full sweep. It is pure overhead â€” the value is identical every time.
* **Recommended fix** `if not isinstance(trigger_pad, list): trigger_pad =
  np.asarray(...).tolist()`. One line.
* **Tradeoffs / Risks** None; the caller already owns the list.
* **Expected impact** Large and free. This is the single best
  effort-to-payoff change in the file.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F9 â€” `_stop_bar`, `_note_risk_capacity` and the TP branch are fully dead

* **Category** Dead Code
* **Severity** Medium
* **Impact** Maintenance surface, misleading docstrings
* **Evidence**
  - `_stop_bar`: declared `engine.py:431`, pruned `engine.py:3114`,
    written `engine.py:3315`, **read nowhere**. The docstrings at
    `engine.py:425-431` and `2030` still describe it as the per-bar trail
    throttle, which `engine.py:3306-3313` explicitly replaced with
    "Always re-run overlay_stop on this closed bar."
  - `_note_risk_capacity` (`engine.py:4405-4407`) is
    `"""Leftover max_concurrent_risk_pct is unread..."""` followed by
    `return`, called unconditionally every cycle at `engine.py:844`. Its
    state field `_risk_capacity_noted` (`engine.py:487`) is never assigned
    or read.
  - `tp_dist = 0.0` at `engine.py:2568` and never reassigned, so
    `engine.py:2614`'s `else` is unreachable, and with it
    `_autopsy_exit_reason`'s `DEAL_REASON_TP` arm (`engine.py:1740-1741`)
    and `execution.reap`'s `"target"` leg (`execution.py:505`, `515`).
    `mt5client.open_market` still carries a full stop-widening ladder for
    that `tp` (`mt5client.py:1227-1228`, `1300-1306`, `1460-1466`).
  - `_tally_entry`'s `source` parameter (`engine.py:1318`) is never read â€”
    `engine.py:1349` hardcodes `leg = "primary"` â€” yet all five call sites
    pass it, and the per-leg nesting of `_entry_blocks` and `_filled_bars`
    can only ever hold one key because `_merge_signals` is two-valued
    (`engine.py:2448`).
* **Recommended fix** Delete `_stop_bar` + its prune + the two stale
  docstring paragraphs; delete `_note_risk_capacity` and its call site;
  collapse `tp` out of the engineâ†’client entry path.
* **Tradeoffs / Risks** The `tp` removal touches `mt5client.open_market`'s
  signature and the invalid-stops retry; do it last and cover with the
  existing ambiguous-send tests.
* **Expected impact** Low runtime, high clarity. `_stop_bar`'s docstring
  actively misinforms about how the trail throttles.
* **Removal Safety** Safe (`_stop_bar`, `_note_risk_capacity`);
  Needs Verification (`tp`)
* **Reuse Scope** module

### F10 â€” ~150 lines of symbol-patch guards are unreachable over HTTP

* **Category** Dead Code
* **Severity** Medium
* **Impact** Maintenance; and one real guard is gone with them
* **Evidence** `_reject_hands_off_fields(patch, _OPERATOR_SYMBOL_FIELDS)`
  runs first at `app.py:879`, and the allowlist is only:

```430:433:micofx/web/app.py
_OPERATOR_SYMBOL_FIELDS = frozenset({
    "use_sessions", "sessions", "trade_days", "flat_before_close_min",
    "enabled", "group", "broker_symbol",
})
```

  So `magic`, `strategy`, `timeframe` and every `EXIT_RISK_FIELDS` key
  400 before anything downstream runs. Unreachable as a result:
  `magic_changing` / `primary_changing` / `exit_fields_changing` and the
  whole `if guarded:` body including the 409s at `app.py:926`, `930`,
  `943`, `953` and the `strategy_allows_timeframe` 400 at `965`;
  `_magic_blocked_by_orphan_state` (`app.py:800-853`); the bulk
  `needs_tf_check`/`rejected` machinery (`app.py:1399-1481`) and the JS
  that renders it (`app.js:120-128`); `_validate_risk_bounds` at
  `app.py:882-883` and `1388-1394`, which match no writable key.
* **Why it's inefficient** The `engine.entry_lock` acquisition at
  `app.py:918` and `1437` is also unreachable, so the requests no longer
  block on the trading cycle â€” but the guard that made those writes safe
  is gone too. If any of these fields is ever re-opened, the protection
  reads as present and is not.
* **Recommended fix** Delete the unreachable branches and leave a single
  comment at `_OPERATOR_SYMBOL_FIELDS` recording that re-opening a field
  means re-adding its guard.
* **Tradeoffs / Risks** None while the allowlist stands.
* **Expected impact** Removes ~150 lines and one false sense of safety.
* **Removal Safety** Likely Safe
* **Reuse Scope** module

### F11 â€” `_INDICATOR_PERIOD_BOUNDS` names two fields that do not exist

* **Category** Reliability
* **Severity** Medium
* **Impact** The ADX/ATR period bound the file was written to enforce is not enforced
* **Evidence** `app.py:187` keys on `"adx_length"` and `"atr_length"`,
  but `SymbolConfig` has `adx_period` (`models.py:268`) and `atr_period`
  (`models.py:243`). The grid-axis check at `app.py:1768-1771` therefore
  never bounds them.
* **Recommended fix** Rename the two keys. `tests/test_indicator_periods_are_bounded.py`
  exists and passes today, which means it is asserting on the wrong names too.
* **Tradeoffs / Risks** None.
* **Expected impact** Closes a silent hole in grid validation.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F12 â€” `GET /` hands out a full-privilege session with no authentication

* **Category** Security / Reliability
* **Severity** High
* **Impact** Anyone who can reach port 8900 gets write access
* **Evidence** The middleware skips `/` entirely (`app.py:601-603`) and
  `index()` sets the cookie carrying the raw API token:

```657:660:micofx/web/app.py
        resp = HTMLResponse(html)
        resp.set_cookie(
            SESSION_COOKIE, api_token,
            httponly=True, samesite="strict", path="/",
        )
```

  No `secure`, no `max_age`, no rotation; the token is process-lifetime
  (`app.py:592-596`). Separately, the Origin allowlist is derived from the
  **client-supplied** `Host` header (`app.py:611-615`), and `sec-fetch-site`
  is only checked for the literal `"cross-site"`.
* **Why it's inefficient** The docstring at `app.py:583-590` defends
  against cross-origin browsers, which it does. It does not defend against
  anything that can open a TCP connection to the port. This audit obtained
  a working session in one unauthenticated GET.
* **Recommended fix** Bind to 127.0.0.1 only (verify `run.py`'s uvicorn
  host), and pin the Origin allowlist to a configured host rather than the
  request's own `Host`.
* **Tradeoffs / Risks** If the operator reaches the panel from another
  machine on the LAN, binding to loopback breaks that access.
* **Expected impact** Removes the only path to unauthenticated writes.
* **Removal Safety** Needs Verification
* **Reuse Scope** service-wide

### F13 â€” `mt5_terminal_path` is an unvalidated, panel-writable executable path

* **Category** Security
* **Severity** High
* **Impact** Authenticated POST â†’ arbitrary local process launch
* **Evidence** It is in `_OPERATOR_SYSTEM_FIELDS` (`app.py:428`) and the
  handler stores it with no validation at all (`app.py:1600-1607` just
  saves and reconnects) â€” in direct contrast to `backup_dir`, which gets
  careful path and UNC checks at `app.py:1572-1597`. Then
  `_exe_from_path` appends `terminal64.exe` (`mt5client.py:246`) and
  `ensure_terminal_process` runs
  `subprocess.Popen([str(exe)], cwd=str(exe.parent), ...)`
  (`mt5client.py:270-291`), with `autostart_mt5` defaulting to True
  (`models.py:772`).
* **Why it's inefficient** Combined with F12 the chain is: one
  unauthenticated GET, one POST, one launched process.
* **Recommended fix** Require the basename to be `terminal64.exe`, require
  the file to exist, and reject UNC â€” the same three checks `backup_dir`
  already performs. (This was already flagged Low at `OPTIMIZATIONS.md:879`
  and is still open; F12 is what raises it to High.)
* **Tradeoffs / Risks** A directory-only path is currently accepted and
  works (live carries `C:\Program Files\MetaTrader 5`); keep that form
  legal.
* **Expected impact** Closes the launch primitive.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F14 â€” `max_combos` / `refine_rounds` accept any finite number

* **Category** Cost / Reliability / Security
* **Severity** High
* **Impact** A single POST can wedge the live trading process
* **Evidence** Both are allowlisted at `app.py:434-437`, and
  `set_opt_params` validates only `timeframes`, finiteness and grid axes
  (`app.py:1731-1772`). `max_combos = 1e9` with `refine_rounds = 1e9` is
  accepted and persisted. Each refine round is charged a full
  `max_combos` sweep (`optimizer.py:95-96`). Same class:
  `flat_before_close_min` (writable at `app.py:431`, no entry in
  `_SYMBOL_RISK_BOUNDS`, UI-only `max: 240` at `app.js:1029` â€” `10**9`
  permanently blocks entries on that symbol) and `backup_keep`
  (`app.py:427`, UI-only bounds at `app.js:1688`).
* **Recommended fix** Add all four to the existing bounds tables. The
  mechanism is already there and already tested.
* **Tradeoffs / Risks** None; AGENTS already names 2000 as the intended cap.
* **Expected impact** Turns a process-wedging input into a 400.
* **Removal Safety** Safe
* **Reuse Scope** module

### F15 â€” Cycle-start position read is fail-open where `_reload_positions` is fail-closed

* **Category** Reliability
* **Severity** High
* **Impact** A transient `positions_get` failure empties the book the panel and the exit patcher read
* **Evidence** `engine.py:857` assigns `self._positions = self.client.positions()`
  **before** the connectivity check at `858-864`. `_reload_positions`
  exists precisely to avoid this â€” its docstring at `engine.py:793-808`
  says "On failure keep the previous snapshot and return False". After the
  bail-out, `self._positions` is left as an unreliable `[]`, and that same
  field feeds `_panel_positions` (`engine.py:4102-4103`) and the
  `open_magics` set `_apply_pending_exits` derives (`engine.py:3467-3469`).
* **Why it's inefficient** `pending_primary_patch` / `pending_exit_patch`
  land "when flat". An empty book from a failed read looks exactly like
  flat.
* **Recommended fix** Route line 857 through `_reload_positions()`.
* **Tradeoffs / Risks** None â€” it is the same call with the correct
  failure semantics.
* **Expected impact** Removes a path where a network blip can land a
  parameter patch under an open ticket.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F16 â€” `entry_lock` is held across `time.sleep` and broker round trips

* **Category** Concurrency
* **Severity** Medium
* **Impact** Panel write latency; `/api/state` stalls
* **Evidence** `engine.py:2649-2782` holds the lock across `open_market`
  (`2656`), up to three `_reload_positions()` round trips with
  `time.sleep(0.2)` between them (`2718-2725`), and `_close_orphan_tickets`
  (`2760`). `_scan_orphan_candidates` takes the same lock (`engine.py:3019`)
  then sends `close_position` per ticket plus `positions()` inside it.
  `manage_positions` documents exactly why this is wrong and keeps only
  the prune inside (`engine.py:3123-3125`: "holding the entry lock across
  those would stall every web write"). Additionally up to five
  `store.set_setting` calls run under the lock at `engine.py:3127-3148`
  and `store.update_symbol` at `3487-3527`.
* **Recommended fix** Narrow to the state mutation; do the sleeps and the
  broker calls outside, re-acquiring to commit.
* **Tradeoffs / Risks** The lock exists to keep two entries off one
  symbol; narrowing it needs the ticket-claim to stay inside.
* **Expected impact** Sub-second panel writes during an entry burst.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F17 â€” `order_send` runs under the global MT5 lock with no timeout

* **Category** Concurrency / Reliability
* **Severity** Medium
* **Impact** Every 3 s `/api/state` tick queues behind each broker round trip
* **Evidence** The comment at `mt5client.py:1271-1277` argues against
  exactly this ("the whole app would stall behind each entry") and the next
  two lines do it:

```1277:1278:micofx/mt5client.py
        with self._lock:
            result = mt5.order_send(request)
```

  Same at `1307-1308`, `1326-1328`, `1647-1648`, `1739-1740`, `1751-1753`.
  The only timeout anywhere in the file is on `tasklist`
  (`mt5client.py:262`).
* **Recommended fix** Leave the lock (removing it is worse), but delete or
  correct the comment, which currently describes behaviour the code does
  not have.
* **Tradeoffs / Risks** Actually releasing the lock reintroduces the race
  the comment describes. Do not.
* **Expected impact** Documentation truth, not throughput.
* **Removal Safety** Safe (comment only)
* **Reuse Scope** local file

### F18 â€” `modify_position` reads "no change" as failure and retries every poll

* **Category** Reliability / Network
* **Severity** Medium
* **Impact** A wasted broker round trip per poll per position, all bar long
* **Evidence** `mt5client.py:1638-1658` is a single `order_send` with no
  widening ladder, and `TRADE_RETCODE_NO_CHANGES` returns `False`
  (`mt5client.py:1655-1657`). `_update_stop` then returns `False`
  (`engine.py:3819`) and retries.
* **Recommended fix** Treat `NO_CHANGES` as success â€” the stop is already
  where the caller wants it.
* **Tradeoffs / Risks** None.
* **Expected impact** Removes a per-poll broker call per open position on
  every bar where the trail does not move, which is most of them.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F19 â€” `normalize_volume` clamps up to `volume_min` after the risk cap

* **Category** Reliability / Risk
* **Severity** Medium
* **Impact** Realized risk can exceed `r_cap`
* **Evidence** `mt5client.py:985-986`:

```985:986:micofx/mt5client.py
        vol = math.floor(float(volume) / step + 1e-9) * step
        vol = max(i["volume_min"], min(i["volume_max"], vol))
```

  The `< floor` guards at `risk.py:486-492` inspect the *pre-normalise*
  value. Related: the min-lot overshoot skip at `risk.py:499-508`
  (`MAX_MIN_LOT_OVERSHOOT = 3.0`, `risk.py:285`) is unreachable in
  production, because `lot_for` returns inside the `auto is not None`
  branch at `risk.py:489-497` and live always has an account snapshot.
* **Recommended fix** Return the overshoot ratio from `normalize_volume`
  (or re-check after it) so the caller can refuse rather than silently
  round up.
* **Tradeoffs / Risks** Some small-balance symbols stop trading entirely.
  On a 1656 USD account that is the correct outcome but it is a visible
  behaviour change.
* **Expected impact** Closes the last path where realized risk exceeds
  the cap.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F20 â€” `min_stop_distance` folds the freeze level into the stop floor

* **Category** Algorithm / Risk
* **Severity** Medium
* **Impact** Wider stops â†’ smaller lots on every entry
* **Evidence** `mt5client.py:996-999`:

```996:999:micofx/mt5client.py
        broker = max(i["stops_level"], i["freeze_level"]) * point
        return max(broker, spread * 1.5, point * 10)
```

  `trade_freeze_level` is a no-modify window near market, not a minimum
  stop distance. It widens `sl_dist = max(atr * sl_mult, min_stop)`
  (`engine.py:2563`). Cached for `_INFO_TTL = 120 s` (`mt5client.py:96`),
  so an intraday widening of `stops_level` is read stale for two minutes.
* **Recommended fix** Use `stops_level` for the stop floor and keep
  `freeze_level` for the modify-eligibility check where it belongs.
* **Tradeoffs / Risks** Tighter stops mean more stop-outs on brokers where
  the freeze zone genuinely is wide. Measure per symbol first.
* **Expected impact** Directly larger lots for the same R.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F21 â€” A symbol below `min_bars` gets no stop management at all

* **Category** Reliability
* **Severity** Medium
* **Impact** An open ticket with no trail or breakeven
* **Evidence** `_refresh_signals` returns early on `len(bars) < min_bars`
  without setting `state.last_bar` (`engine.py:2357-2360`), and
  `manage_positions` only calls `_update_stop` under `if last_bar:`
  (`engine.py:3305-3315`). With `last_bar == 0` the trail, breakeven,
  partial and harvest overlays all skip; only the broker stop protects the
  position.
* **Recommended fix** Manage stops off the last known bar even when the
  fresh fetch is short, or log an explicit WARN when a ticket is open on a
  symbol that failed `bars_ready`.
* **Tradeoffs / Risks** None for the WARN.
* **Expected impact** Closes a silent unmanaged-position window after a
  history gap.
* **Removal Safety** Safe (WARN); Needs Verification (manage)
* **Reuse Scope** local file

### F22 â€” Window boundaries manufacture fake "time" exits that count as trades

* **Category** Algorithm (correctness)
* **Severity** Medium
* **Impact** Trade counts and win rate in every segment
* **Evidence** The replay loop is `for j in range(j0, n)` with `n` the
  window end (`backtest.py:483`, `865`), and anything still open is booked
  at that bar's close as `reason = "time"` (`backtest.py:939-941`). Every
  selection/validation/holdout window ends with one artificial close whose
  R is a boundary artifact, and it counts toward `MIN_TEST_TRADES` and
  `min_trades`. Compounding it, break-even trades are counted as wins
  (`backtest.py:586-588`), so a 0 R boundary exit inflates `win_rate`.
* **Recommended fix** Drop the trailing open trade from the segment's
  statistics, or count it separately.
* **Tradeoffs / Risks** Reduces trade counts slightly; some candidates
  will newly fail `min_trades`.
* **Expected impact** With `segments: 5` this is up to 5 artifact trades
  per candidate per run.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F23 â€” `positive_ratio` is a two-valued step function

* **Category** Algorithm
* **Severity** Medium
* **Impact** Candidate ranking
* **Evidence** With `segments: 5` (`defaults.json:382`) selection is
  `windows[:-2]` = 3 windows (`backtest.py:1149`), so `positive` âˆˆ
  {0, 0.333, 0.667, 1.0}, and the rank key squares it:

```1393:1393:micofx/backtest.py
                        raw[idx] = round(mean_score * positive * positive, 4)
```

  Against `min_positive_ratio: 0.6` only 0.667 and 1.0 survive, so the
  multiplier is **either 0.444 or 1.0** â€” nothing in between exists. A
  candidate that loses one of three segments is discounted 56% in one
  discontinuous step.
* **Recommended fix** Either raise `segments` so the ratio has resolution,
  or replace the squared ratio with a continuous consistency penalty.
* **Tradeoffs / Risks** Raising `segments` costs wall clock linearly.
* **Expected impact** Removes a cliff that currently dominates the
  ranking of otherwise-similar candidates.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F24 â€” Successive-halving prescreen is a recency filter

* **Category** Algorithm
* **Severity** Medium
* **Impact** Candidates are eliminated before `min_positive_ratio` sees them
* **Evidence** `prescreen` scores only `selection[-1]` and kills anything
  â‰¤ 0 outright (`backtest.py:1310`, `1360-1368`). A set that pays on
  segments 1 and 2 but not the most recent is never evaluated, even though
  2/3 clears `min_positive_ratio: 0.6`.
* **Recommended fix** Prescreen on the mean of two segments, or keep the
  cheap screen but raise the kill threshold's sample.
* **Tradeoffs / Risks** More survivors means more full evaluations â€”
  directly more wall clock.
* **Expected impact** The prescreen and the consistency gate currently
  disagree about what "consistent" means; this makes them agree.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F25 â€” Pooled drawdown is a max-of-segments, not an equity curve

* **Category** Algorithm
* **Severity** Medium
* **Impact** Score understates real drawdown
* **Evidence** `backtest.py:1070-1071`:

```1070:1071:micofx/backtest.py
        total.max_dd_r = max(total.max_dd_r, r.max_dd_r)
        total.longest_loss_streak = max(total.longest_loss_streak, r.longest_loss_streak)
```

  and `Result.score` divides by `net_r + max_dd_r` (`backtest.py:111`).
  Also `PF_NO_LOSSES = 99.0` (`backtest.py:42`) lets a 12-trade holdout
  slice with zero losers sail through `MIN_OOS_PF` (`backtest.py:1084-1088`)
  on a fabricated ratio.
* **Recommended fix** Concatenate segment R series and compute one
  drawdown; cap `PF_NO_LOSSES` at the gate value plus epsilon rather than
  99.
* **Tradeoffs / Risks** Scores drop across the board; stamps become
  non-comparable.
* **Expected impact** The selection score becomes a number that survives
  contact with a real equity curve.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F26 â€” Three supervisor rules and two knobs are dead at shipped defaults

* **Category** Dead Code
* **Severity** Medium
* **Impact** The panel shows enforcement that does not happen
* **Evidence** `config/defaults.json` carries **no** `supervisor` block, so
  `supervisor.py:21-93` are the live values, including
  `hard_block_only_quarantine = True`. That gates off: the `blocked_hours`
  hard block (`supervisor.py:342-344`), the `prefer_strong_on_dd`
  weak/unproven refusal (`370-375`), and the `judged_pf < 1.0` drawdown
  refusal (`383-387`). `_bad_hours` is still recomputed and persisted
  every review (`565`, `988-1005`) purely for the `hours_enforced` display
  (`1080`), which makes `bad_hour_pf` a dead knob â€” the live path
  `_hour_risk_scales` hardcodes `pf < 1.0` and a 0.3 floor (`962-964`) and
  never reads it. `_bad_hours` also still contains the un-fixed copy of
  the profit-factor arithmetic `_pf`'s docstring warns about
  (`1001-1002`: dollars compared against a ratio), masked only because the
  same branch requires `sum(values) < 0`.
  Separately, `edge_decay` needs 50 closes in a 14-day window with both
  halves â‰¥ 25 (`753-764`) â€” at this book's frequency it effectively never
  fires. And `edge_health` requires `v.trades >= 25` **and**
  `expected_r > 0` (`971-974`), so it reads 0.0 for every recently
  re-applied symbol and the "saglik %" suffix silently vanishes.
* **Recommended fix** Delete the three gated branches and `bad_hour_pf`,
  or flip `hard_block_only_quarantine` deliberately. Do not leave the
  panel claiming `hours_enforced`.
* **Tradeoffs / Risks** Flipping the flag changes live gating â€” red.
* **Expected impact** Removes the gap between what the AI tab displays and
  what the supervisor does.
* **Removal Safety** Likely Safe (delete); Needs Verification (flip)
* **Reuse Scope** module

### F27 â€” Four endpoints are never called by the panel

* **Category** Dead Code / Cost
* **Severity** Low
* **Impact** One of them costs a forced MT5 round trip
* **Evidence** Verified by grepping every `"/api/â€¦"` in `app.js`:
  - `GET /api/schema` (`app.py:669-687`) â€” its own docstring claims "The
    panel fetches this once on load" (`app.py:678`). It does not;
    `opt_fields` / `engine_opt_fields` / `strategy_opt_fields` appear
    nowhere in `app.js`.
  - `GET /api/system` (`app.py:1551-1553`) â€” panel reads `STATE.system`.
  - `GET /api/positions` (`app.py:1671-1688`) â€” panel reads `STATE.positions`.
  - `GET /api/symbols/lot-mode-check` (`app.py:1367-1373`) â€” and it calls
    `engine.refresh_account(force=True)`, a forced MT5 round trip, for a
    view nobody renders.
  `POST /api/holdout/capture` is night-restart only, which is correct.
  Tombstones that exist only to 400 (`/api/symbols/{s}/reset` at
  `app.py:1361-1365`, `/api/opt/params/reset` at `1774-1778`) are
  intentional â€” but the latter's comment says "JS is gated on
  `#btn-opt-reset`" and that id does not exist in `index.html` at all.
* **Recommended fix** Keep `/api/positions` and `/api/system` (external
  review loops read them, per their comments); delete `/api/schema` and
  `/api/symbols/lot-mode-check`, or wire the latter's `force=True` down to
  a cached read.
* **Removal Safety** Likely Safe
* **Reuse Scope** module

### F28 â€” Panel repaints whole tables on every 3 s poll

* **Category** Frontend
* **Severity** Low
* **Impact** Browser CPU while the panel is open
* **Evidence** `viewPulse()` (`app.js:2217-2234`) string-joins every
  position and every symbol state on every poll just to decide whether to
  repaint â€” and the pulse changes whenever `acc.profit` or any `st.atr`
  ticks, i.e. essentially every poll while the market moves. On a
  difference the panel rebuilds via `innerHTML` per row:
  `renderCapacity` 13 cols Ã— N (`app.js:675-696`), `renderPositions`
  (`767-818`, with `SYMBOLS.find()` **twice per row** â†’ O(rowsÃ—symbols)),
  `renderLive` 14 cols Ã— N (`856-918`), `renderExecution`, `renderDayTable`,
  and `rowsInto` clears `tbody.innerHTML` each time (`174-183`). Only the
  AI and portfolio tables have signature guards. `pruneLogView` calls
  `getBoundingClientRect()` per removed node â€” a forced layout inside the
  removal loop (`app.js:2150-2160`) â€” over up to 1200 nodes, and
  `pollLogs` requests all nine levels at `limit=400` every 3 s while the
  Log tab is open (`2198-2199`).
* **Recommended fix** Give Panel/Tani tables the same signature guard the
  AI table already has; hoist the `SYMBOLS.find()` into a map; batch the
  log prune outside the measure loop.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F29 â€” SQLite write amplification on symbol saves

* **Category** DB
* **Severity** Low
* **Impact** Panel write latency; adding a symbol costs ~2N commits
* **Evidence** `sort_symbols_by_group()` does one `save_symbol()` per
  symbol â€” each its own `SELECT position`, upsert and `commit()` â€” then
  re-reads the whole table (`store.py:473-482`); it is called from
  `add_symbol` (`465`) and `seed_symbols` (`562`). `save_symbol` rebuilds
  the whole dict per write (`store.py:278`:
  `self.symbols = {**self.symbols, cfg.symbol: cfg}`) while the panel
  debounces only 350 ms per key (`app.js:1137-1152`). The only index is
  `idx_opt_symbol ON opt_runs(symbol, created_at DESC)` (`store.py:31`),
  so `opt_history(symbol=None)` â€” exactly what the panel calls
  (`app.js:1431`) â€” is a full scan plus sort (`store.py:772-777`).
  `_recent_deal_magics()` fetches **30 days of broker deals** on every
  `POST /api/symbols` and every soft seed (`app.py:794-798`).
* **Recommended fix** One transaction for the sort; add an index on
  `opt_runs(created_at DESC)`.
* **Removal Safety** Safe
* **Reuse Scope** module

### F30 â€” Dead / unread config surface (consolidated inventory)

* **Category** Dead Code
* **Severity** Low
* **Impact** Operator trust: these render, accept writes, and change nothing
* **Evidence**
  - `SymbolConfig`: `fixed_lot` (`models.py:170`, no sizing path reads it),
    `lot_mode` (`169`, read only by `risk.lot_mode_diagnostics` which is
    served by the dead endpoint in F27), `max_lot` (`172`),
    `max_margin_pct` (`173`, see `risk.py:385`), `max_positions` (`174`),
    `partial_close_frac` (`256` â€” live uses `SCALE_OUT_FRAC`,
    `models.py:478`).
  - `SystemConfig`: `daily_loss_flatten` (`models.py:677`, no reader in
    `micofx/` at all â€” `field_help.js:96` already says so),
    `max_total_positions` (`659`), `max_concurrent_risk_pct` (`680`),
    `max_positions` (`670`), `max_lot` (`671`).
  - `max_scalp_positions` / `max_swing_positions` default to 0
    (`models.py:662-663`) and are **absent from defaults.json**, so the
    scalp/swing bucket cap at `risk.py:671-679` never fires â€” a whole
    branch with no live effect.
  - `can_open` accepts `sl_distance` and discards it (`risk.py:639-640`)
    while callers compute and pass it (`engine.py:2605-2606`).
  - `stoch_extreme` (`strategy.py:83`) is read by no family yet sits in
    the signal cache key (`strategy.py:131`); `IndicatorCache.volume`
    (`strategy.py:176`) is written by three callers and read by none;
    `Result.trade_cost_rs` is appended per trade (`backtest.py:580`) and
    merged (`1074`) with no reader.
  - Unreachable code paths: `max_open > 1` (~120 lines,
    `backtest.py:680-802` â€” `max_open_from_cfg` unconditionally returns 1
    at `428-435`), `reverse_on_signal` (`backtest.py:885-932`, its own
    docstring says search never passes it), and three of four
    `SELECTION_METRICS` (`backtest.py:51`, `176-189` â€” `defaults.json:385`
    ships `"score"` and `rank_for_selection` short-circuits at `201-202`).
  - `MT5Client.broker_utc_offset_hours` (`mt5client.py:817`) and
    `last_session_close_minute` (`858`) are called nowhere; the latter
    returns `None` unconditionally because `mt5.symbol_info_session_trade`
    has no Python binding (`878-879`).
  - JS: `SYS_FIELDS_ADVANCED = []` (`app.js:1676`) never iterated;
    `AI_SETTING_FIELDS` (20 entries, `1491-1510`) read by nothing;
    the `enum` branch of `renderOptForm` (`1178-1185`) unreachable because
    `OPT_SETTING_FIELDS` has no enum entry; `$$("[data-grid-key]")`
    (`1269-1273`) matches nothing in `index.html`; `#day-note`
    (`index.html:51`) is never written.
  - `index()` produces a double query string â€”
    `/static/app.js?v=<mtime>?v=27c` â€” because the template already carries
    `?v=27c` (`index.html:517-518`) and `app.py:652-656` prepends another.
* **Recommended fix** Delete in three batches: JS dead first (zero risk),
  then unreachable backtest paths, then the unread model fields (each of
  those needs a store-migration check).
* **Removal Safety** Safe (JS, `trade_cost_rs`, `volume`, `stoch_extreme`
  cache key); Likely Safe (`max_open>1`, `reverse_on_signal`, unreachable
  metrics); Needs Verification (model fields â€” they persist)
* **Reuse Scope** service-wide

### F31 â€” Documentation drift is failing its own test

* **Category** Reliability
* **Severity** Low
* **Impact** 1 of the 3 red tests
* **Evidence** `tests/test_docs_match_the_code.py::test_the_family_count_matches_the_code`
  asserts every `N families` / `N aile` in README, MASTER_PROMPT, AGENTS
  and this file equals `len(STRATEGIES)` = 7. `OPTIMIZATIONS.md:10` says
  a family count from before `aroon_flip` retired on 28.08, and the
  AGENTS-mirror block near the tail carried the same stale number.
* **Recommended fix** Every stale count in this file is a historical
  record of a past run, and the test already honours an `(arsiv)` marker
  on the line â€” that is the correct escape. The AGENTS-mirror block at the
  tail is not historical and must read the live count.
* **Status** Fixed 31.08: eleven archive lines marked, mirror block
  corrected.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F32 â€” `test_spread_scale_applied.py` produces zero candidates

* **Category** Reliability
* **Severity** Medium
* **Impact** 2 of the 3 red tests; the spread-cost guarantee is unguarded
* **Evidence** Both tests fail with
  `"tutarli kazanan parametre bulunamadi (0 kombinasyon segmentler arasi tutarsizdi)"`
  against a 3-combo fixture whose baseline is 58 trades / 30 wins /
  51.7% win rate, with `rejected_inconsistent: 0`. Zero rejected **and**
  zero survivors means the fixture is being eliminated before the
  consistency check â€” consistent with F24 (prescreen kills on the last
  segment alone) and F23 (only 0.667 and 1.0 survive
  `min_positive_ratio`).
* **Recommended fix** Diagnose against F23/F24 before touching the test.
  If the prescreen is the cause, the test is correctly reporting a real
  behaviour change in the search, not a stale fixture.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

## 3) Quick wins (do first)

Ordered by impact Ã· effort. Every one is a small, local, testable change.

1. **F8** â€” one-line guard on `trigger_pad`. Largest search speedup in the
   repo, zero risk.
2. **F18** â€” treat `NO_CHANGES` as success. Removes a per-poll broker call
   per open position.
3. **F14** â€” put `max_combos`, `refine_rounds`, `flat_before_close_min`,
   `backup_keep` in the existing bounds tables.
4. **F15** â€” route `engine.py:857` through `_reload_positions()`.
5. **F11** â€” rename `adx_length`/`atr_length` to `adx_period`/`atr_period`.
6. **F2** â€” measure bar age from bar close. One expression; fail-first test
   on an M30 signal at close + 90 min.
7. **F9 (partial)** â€” delete `_stop_bar` and `_note_risk_capacity` plus the
   two stale docstrings.
8. **F6** â€” delete the four shadowed axes from the shared `grid` block.
9. **F31** â€” mark `OPTIMIZATIONS.md:10` `(arsiv)`, fix the tail block to 7.
10. **F13** â€” three path checks on `mt5_terminal_path`, copied from
    `backup_dir`.

Also, unrelated to code: [config/defaults.json](config/defaults.json):21
still ships `C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe`,
which does not exist on this machine. Live is correct
(`C:\Program Files\MetaTrader 5`), but a clean install cannot connect.

## 4) Deeper optimizations (do next)

* **F1** â€” per-family combo budgets plus a Sobol/LHS sample. This is the
  one change that moves every future applied parameter set.
* **F3 + F4 + F19 + F20** â€” the sizing chain. Land them together and while
  flat: F3 shrinks lots, F4 and F20 grow them, F19 refuses the residue.
  Landing any one alone changes live position size in a direction the
  others were compensating for.
* **F5 + F22 + F23 + F24 + F25** â€” search-honesty batch. All five change
  scores, so all five invalidate stored stamps; do them in one pass and
  re-baseline the book once, not five times.
* **F16** â€” narrow `entry_lock` to the state mutation.
* **F10 + F26 + F30** â€” the dead-code sweep, in the three batches named in
  F30.
* **F12** â€” session/Origin hardening. Needs an operator decision about LAN
  access first.

## 5) Validation plan

Fail-first, per AGENTS. For each change: write the test, watch it fail,
implement, then:

```
C:\MicoFX-venv\Scripts\python.exe -m pytest tests/<touched>.py -q --tb=short
C:\MicoFX-venv\Scripts\python.exe -m ruff check micofx/ tests/<touched>.py
```

Baseline to beat, captured 31.08 01:12: **3 failed, 2610 passed,
1 xfailed, 88.60 s**; `ruff` clean. Any change that moves the pass count
down, or the failure list to anything other than a subset of
{`test_docs_match_the_code`, `test_spread_scale_applied` Ã—2}, is a
regression.

Per-finding verification:

* **F8** â€” time one `walk_forward` on a fixed symbol/TF/family with a
  pinned `combo_seed` before and after; the returned best combo must be
  **identical** and the wall clock lower. That equality is the whole test.
* **F2** â€” fail-first: an M30 state whose `last_bar` closed 90 minutes ago
  must still be accepted; one at 150 minutes must not. Then watch
  `entry_block` counts in `/api/analysis/entry-blocks` over one full
  session and compare `bar_bosluk` against tonight's 7-of-9.
* **F3/F4/F19/F20** â€” assert on `lot_for` directly with a synthetic
  account: for a symbol at `edge_scale = 2.2`, realized risk must be
  â‰¤ 2% of balance. Then compare `capacity` rows before/after on the live
  book with trading off.
* **F18** â€” assert `modify_position` returns True on a mocked
  `NO_CHANGES` retcode, and that `_update_stop` does not retry.
* **F15** â€” mock `positions()` to raise mid-cycle and assert
  `self._positions` still holds the previous snapshot and no pending patch
  lands.
* **F14** â€” POST `max_combos = 10**9` must be 400.
* **F1/F5/F22/F23/F24/F25** â€” these change scores by design, so the test is
  a *paired* comparison, not an absolute: run the same symbol/TF/family
  before and after on the same history and record `net_r`, `max_dd_r`,
  `trades`, `win_rate`, and holdout PF for both. Accept only if holdout PF
  does not fall. Then hold the old and new parameter sets side by side on
  the same holdout slice.
* **F12/F13** â€” `curl` the panel from a second machine on the LAN and
  confirm refusal; POST an `mt5_terminal_path` of `C:\Windows\System32\calc.exe`
  and confirm 400.

Metrics to compare before/after, book-wide: entries per day, `bar_bosluk`
and `spread` block counts, mean lot per entry, realized R per trade,
holdout PF, and search wall clock per family.

## 6) Optimized code

Only the changes that are unambiguous and local enough to state exactly.

**F8** â€” `backtest.py:514-515`. Skip the round trip when the caller already
passed a list:

```python
    elif not isinstance(trigger_pad, list):
        trigger_pad = np.asarray(trigger_pad, dtype=np.float64).tolist()
```

**F18** â€” `mt5client.py:1655-1657`. The stop is already where we want it:

```python
    if result.retcode == mt5.TRADE_RETCODE_NO_CHANGES:
        return True
```

**F15** â€” `engine.py:857`. Use the fail-closed helper that already exists:

```python
    if not self._reload_positions():
        # keep the previous snapshot; the connectivity check below bails
        ...
```

**F11** â€” `app.py:187`. Two renames:

```python
_INDICATOR_PERIOD_BOUNDS = dict.fromkeys((
    "t3_fast", "t3_length", "st_period", "rsi_length", "stoch_length",
    "stoch_k_period", "stoch_k_smooth", "stoch_d_smooth",
    "adx_period", "atr_period", "trail_lookback",
), (1, 10000, True))
```

**F2** â€” `engine.py:2164`. Measure from the bar's close, not its open:

```python
        bar_close = state.last_bar + tf_sec
        if (state.last_bar > 0
                and (server_now - bar_close) > _MAX_SIGNAL_BAR_AGE_BARS * tf_sec):
```

**F3** â€” `risk.py:483-486`. Build the cap from the operator multiplier only,
and apply the edge/AI push to the raw lot instead:

```python
        r_pct = max(stored, self.AUTO_R_PCT)
        r_cap = (balance * r_pct / 100.0 * lot_multiplier
                 / (sl_distance * money_per_unit))
```

Nothing above was applied. This file is notes.

---

## 31.08 03:xx â€” closed ledger: what actually landed

Operator gave full authority to implement. Suite **2665 passed, 0 failed,
1 xfailed** (was 2610 passed / 3 failed at the start of the session), ruff
clean over `micofx/` and `tests/`. **The live PID is still on the old code:**
it holds 2 tickets, so `/api/app/restart` is 409. Everything below lands on
the next flat restart.

### Landed on the money path

| # | Change | Measured effect |
|---|---|---|
| F2 | Signal bar age measured from the bar's **close**, not its open. Extracted as `engine.signal_bar_expired`. | The window was one bar, not the two `_MAX_SIGNAL_BAR_AGE_BARS` documents. Live 31.08 01:15: 7 of 9 symbols on `bar_bosluk` at once; 03:xx re-measure: 5 of 9 (`BRENTOIL-PERP`, `GOLD-PERP`, `XAUUSD`, `US30`, `BTCUSD`). |
| F3 | `r_cap` is built from `lot_multiplier` and an `ai_scale` clamped at 1.0 â€” **not** from the `multiplier` that carries `edge_scale`. | The "auto 1R, max(risk%, 2%)" ceiling was scaled by the push it exists to bound: up to `EDGE_MAX` 2.2, so ~4.4% of balance on a proven symbol. The supervisor throttle still tightens it; only the edge lift is gone. |
| F4 | `_vacant_enabled_count` skips quarantined names (`Supervisor.is_suspended`, wired from `Engine.__init__`). | A quarantined symbol carries `risk_scale` 0.0 and cannot open, but held a full share of the remaining book margin. Every real entry was sized at `(vacant âˆ’ suspended) / vacant` of its intended lot. |
| F20 | `min_stop_distance` uses `stops_level`, with `freeze_level` only as a fallback when `stops_level` is 0. | `freeze_level` is a no-modify window, not a placement floor. Folding it in widened `sl_dist`, and lot is risk / that distance â€” a permanent size-down on any symbol with a wide freeze zone. |
| F18 | `TRADE_RETCODE_NO_CHANGES` is a success in `modify_position`. | A settled trail read as a refused one and resent the identical request every poll for the rest of the bar â€” one round trip per open position per poll, on the lock every `/api/state` queues behind. |
| F15 | Cycle-start position read routes through `_reload_positions()`. | A failed `positions_get` left an empty book that looks exactly like *flat* â€” which is the condition `_apply_pending_exits` lands patches on. |
| F21 | New `_note_unmanaged_ticket` WARN when an open ticket has `last_bar == 0`. | Under the `min_bars` floor, trail/BE/partial/harvest all skip and the ticket runs on the broker stop alone, previously in total silence. |

### Landed on the API / panel

| # | Change | Measured effect |
|---|---|---|
| F14 | `_OPT_PARAM_BOUNDS` on `max_combos` / `refine_rounds` / `lookback_days`; `flat_before_close_min` and `backup_keep` added to the risk-bound tables. | Every refine round is charged a full `max_combos` sweep, so an unbounded POST wedged the process holding the live book. `flat_before_close_min` was the only writable symbol field with no server-side bound at all â€” a `10**9` POST blocked every entry on that symbol permanently. |
| F13 | `mt5_terminal_path` validated: absolute local or UNC (behind the existing latch), no drive root, and a named `.exe` must be `terminal64.exe`. | The stored value becomes `subprocess.Popen` via `ensure_terminal_process`, and `autostart_mt5` ships True â€” an accepted POST was a launched process. `backup_dir` one screen above already had all three checks. |
| F28 | `viewPulse` no longer includes `bot.last_cycle_at`. | It changes every cycle, so the signature differed on every poll and the "nothing changed, skip the repaint" guard **never fired once**. It is rendered into `#sys-bot-note` by `renderSystem`, which the guard does not cover. A quiet book now stops rebuilding six tables every 3 s. |
| F29 | `idx_opt_created` on `opt_runs(created_at DESC)`. | The panel's own call is `/api/opt/history?limit=80` with no symbol; the existing composite `(symbol, created_at)` cannot serve that, so it was a full scan plus a sort per visit. |
| F27 | `/api/symbols/lot-mode-check` no longer passes `force=True`. | A read-only preview was taking the MT5 lock the trading cycle queues behind, to move a balance the 3 s cycle already refreshed. |
| F8 | `simulate()` skips the `trigger_pad` rebuild when it is already a list. | `walk_forward` builds it once and hands the same object to every combo; re-listing it was a full-length rebuild per combo per window. |
| F11 | `_INDICATOR_PERIOD_BOUNDS` keys corrected to `adx_period` / `atr_period`. | `adx_length` / `atr_length` are fields of nothing. The two periods the table was written to bound were the two it never reached. |

### Dead code removed

* `Engine._stop_bar` â€” written, pruned, never read since `manage_positions`
  moved to "always re-run `overlay_stop` on this closed bar". Bar-close
  discipline is still enforced by `_update_stop`'s own reference-bar check.
* `Engine._note_risk_capacity` / `_risk_capacity_noted` â€” a method whose whole
  body was `return`, called unconditionally every cycle. Its test file now
  pins the absence structurally instead of pinning the silence.

### Chased and **withdrawn** â€” do not re-file these

* **F19 (`normalize_volume` clamping up past the cap).** Unreachable on the
  account path: `floor` *is* `volume_min`, and `lot_for` already refuses when
  the capped lot falls under `floor`, so the clamp cannot raise a lot the
  caller accepted. No guard was added â€” a guard that cannot fire is the thing
  this audit is removing. Pinned by
  `test_a_minimum_lot_above_the_cap_skips_the_trade_rather_than_sizing_up`.
* **F6 (shadowed grid axes in `defaults.json`).** Dead at the *default* search
  timeframes only. `SWING_GRID_OVERLAY` applies at `>= 900 s`; M5 is still
  legal to trade and a one-off `POST /api/opt/run` can still name it, so the
  shared grid is live there. Deleting the axes would break an M5 search.
* **F27 (`GET /api/schema`).** Kept on purpose, as previously decided. Its
  docstring claimed "the panel fetches this once on load"; the JS consumer
  (`loadSchema` / `optFieldVisible`) was deleted with the symbol-guts form.
  Docstring corrected to say what it is actually for. Do not wire it into
  the poll.
* **F28 (panel repaint guard).** Already implemented â€” `viewPulse` plus the
  `activeTab` gate. The defect was not a missing guard but a guard defeated
  by one field, which is what F28 above actually fixes.

### Test debt paid

`tests/test_spread_scale_applied.py` had two long-standing reds. Cause: the
fixture named `stoch_flip`, which gained a mandatory HTF-trend + ADX gate on
30.08 and stopped producing a consistent winner on these synthetic bars at any
scale â€” the same staleness that hit it on 27.08 when `t3_stoch` retired.
Re-measured across all seven live families: `t3_flip` is the only one that
still clears here, and it needs a wider grid than the 2Ã—3 the file carried.
Charged cost is now exactly linear across scale 1/2/3 (0.0015 / 0.0030 /
0.0045), which is the property under test.

Applied, not notes. This section is the closed ledger.

---

## 31.08 10:52 â€” why the book gives profit back, and where opt wall-clock goes

Operator asked why the system loses, why it hands profit back, a hard stress
pass, and continuous watching. Measured against 289 closed autopsies and the
live config, live PID still on pre-31.08 code (5 tickets, restart 409).

### It is a payoff problem, not a hit-rate problem

289 trades: hit rate **34%**, average win **+1.26 R**, average loss
**âˆ’0.85 R**, reward/risk **1.48**. Break-even at that hit rate needs **1.98**.
The 0.50 shortfall is âˆ’0.141 R per trade, **âˆ’40.73 R** in total.

### The give-back sits in one setting

Peak retention on `exit_reason = trail`, against each symbol's trail arm point
(`trail_start_atr / sl_atr_mult`, i.e. the trail's arm expressed in R):

| symbol | family | trail arms (R) | mean MFE â†’ kept | net R |
|---|---|---|---|---|
| JPN225 | stoch_flip | 0.50 | 1.79 â†’ **19%** | âˆ’18.59 |
| NAS100 | stoch_flip | 0.50 | 1.99 â†’ **19%** | âˆ’16.98 |
| US30 | stoch_flip | 1.40 | 3.10 â†’ 44% | âˆ’2.08 |
| XAUUSD | burst | 2.00 | 3.85 â†’ **72%** | +5.52 |

JPN225 + NAS100 are **âˆ’35.57 R, 87% of the book's entire loss**, and they are
the only two symbols with a 0.50 arm. NAS100's average winner (+0.73 R) is
*smaller* than its average loser (âˆ’0.86 R). The comparison is clean because
US30 is the same family with the same `trail_step` (1.6) and 86 trades - the
largest sample in the book - differing only in the arm point. An early trail
on a mean-reverting index does not protect profit, it converts a runner into
a scratch. `models.py:230` already noted the 0.5/1.6 pair giving back 0.10 R
on a replay; this is the same finding at 51 live trades.

### Breakeven cannot fire on the trades that need it

Live `breakeven_at_r` is 1.5 on six of nine symbols. The MFE distribution of
the **189 losing** trades: median 0.31 R, p75 0.75 R, **p90 1.10 R**. The
threshold sits above the 90th percentile of what a losing trade ever reaches,
so it is structurally unable to arm on one. Only 9 of 289 trades (6.70 R) were
ever within its reach.

**This is not an argument for lowering it.** BE at 0.5 is already on the
ledger as costing GER40 âˆ’32 R (BE-2). The evidence points at
`trail_start_atr`, not at BE. Recorded here so the next reader does not
re-derive "BE is doing nothing" and reach for the wrong lever.

Two honesty caveats: `mfe_r` is an intrabar peak while overlays evaluate on
closed bars, so every "would have been saved" figure is an upper bound; and
`left_on_table_r` (110 R) includes losers and is not cash sitting in the till.

### Hard stress pass â€” clean

* **Per-file isolation:** all **312** test files each in their own process,
  **0 failures**, 649 s. No state leaks between files, and no test that only
  passes because an earlier file ran.
* **Adversarial input:** 48 new tests over the paths 31.08 touched - nan/inf/
  negative/1e12 stop distances and balances, corrupt account snapshots, a
  supervisor hook that raises, a broker clock running backwards. Nothing
  throws; a lot is always either 0 with a reason or finite inside
  `[volume_min, volume_max]`; the 1R cap holds across the whole edge range.
  `tests/test_the_sizing_chain_survives_hostile_input.py`.
* **Suite:** 2713 passed, 1 xfailed, ruff clean.
* `pytest-randomly` is **not installed** and nothing was added to the live
  trading venv to shuffle test order. Per-file isolation covers the same
  defect class.

### Opt wall-clock: the budget arithmetic, not the code

A two-symbol manual run reported `combo_total = 979,200`. That number is
exactly reproducible from `sweep_budget = max_combos Ã— (1 + refine_rounds)`:

| item | arithmetic | share |
|---|---|---|
| `stoch_flip` | 2 symbols Ã— 3 TF Ã— (28,800 Ã— 4) = 691,200 | **70.6%** |
| the other six families | 2 Ã— 3 Ã— 6 Ã— (2,000 Ã— 4) = 288,000 | 29.4% |

Three multipliers, all configuration:

1. `strategy_max_combos.stoch_flip = 28800` is the *exact* product of that
   family's grid (`5Ã—4Ã—2` entry Ã— `5Ã—6Ã—6` exit Ã— `4` spread), so the global
   2000 cap does no sampling there at all - the grid is exhaustive.
2. `refine_rounds = 3` multiplies everything by four. Refine rounds are not
   cheap extra passes; each gets its own full budget.
3. A POST that leaves `strategies` / `timeframes` empty inherits the saved
   seven families Ã— three timeframes.

The third is the only waste, and it is operator habit rather than a setting:
this run wanted one family at one timeframe per symbol. Scoped
(`strategies: ["stoch_flip"]`, each symbol at its own TF) the same trail
question costs `2 Ã— 115,200 = 230,400` - **23.5% of what was spent, 4.2x
faster, same grid, same answer**.

**Deliberately not changed:** `refine_rounds` and the `stoch_flip` cap.
Cutting either buys wall-clock by lowering search quality, which is the wrong
trade on a book running âˆ’0.141 R per trade; and `stoch_flip` is the family on
four of nine live symbols including both big losers, so it is the one that
most deserves an exhaustive grid.

The parallel machinery itself is already right and is not the wall: 12 cores,
10 worker processes (one core left for the live poll loop, one for the OS),
bars shared as mmap-able `.npy` per `(symbol, TF)` rather than pickled per
family, BLAS threads pinned. A profile of the inner `simulate` loop is the
only remaining place a *free* win could live; it is deferred until the search
finishes rather than run against ten busy cores.

### Watching

`cursor/watch_flat.py` (gitignored, read-only, 60 s) latches four alarms:
`FLAT` (the restart window), `GERI` (open book has handed back >= 40% of its
own peak), `STOPSUZ`, `RISK` (day halted / MT5 down / cycle error). It caught
the give-back twice on 31.08 - 09:17 at âˆ’45% and 10:19 at âˆ’50% off a +46.54
peak - which is the event that had been passing silently: the panel shows the
current number, never that a peak existed.

## 31.08 (2) - strateji aileleri: arama canlinin reddettigi isi olcuyordu

Operator sorusu: "her sembol bir strateji ile kazanabilir; ailelerimiz buna
uygun mu, hatali ise degistir." Iki bulgu olculdu ve landed edildi, iki iddia
olculunce geri cekildi.

### F33 - simulate takvim boslugunun uzerinden dolduruyordu (landed)

Canli motorda bir barin sinyali, kapanisindan `MAX_SIGNAL_BAR_AGE_BARS = 2`
periyot sonra oluyor (`entry_block = "bar_bosluk"`). `simulate` bu kapiyi hic
tasimiyordu: her sinyali `j0 = i + 1` de dolduruyordu. MT5 bar dizileri
sikisiktir - Cuma 22:45 in bir sonraki bari dogrudan Pazartesi 03:15 - yani
arama her hafta sonunu ve her gecelik seans boslugunu isleme ceviriyordu.
`session_mask`/`tradable` bunu yakalamaz: o, dolum *barinin* seans icinde olup
olmadigini sorar ve Pazartesi acilisi seans icindedir.

Kapi `engine` den `sessions` e tasindi (tek tanim, iki cagiran). `engine`
eski ozel adlari yeniden disa veriyor. `simulate` fill barinda O(n) bir
`stale_fill` maskesi kuruyor; iki dolum yolu da ayni maskeye bakiyor.

Olcum (GER40 takvimi, M15, 400 gun, 22.594 bar, 285 takvim deligi):
sinyallerin **%1,24** u bu tur dolumdu - `dual_t3` %0,97, `stoch_flip` %1,04,
`mtf_pullback` %1,31, `t3_flip` %1,36, `ichimoku` %1,40, `parabolic_flip`
%1,42. Sayica kucuk; agirligi bunlarin boslukli acilista gerceklesen, en
kalin kuyruklu dolumlar olmasindan geliyor. Skoru sismekten cok
gurultulendiriyordu.

Kapak: `tests/test_the_search_cannot_fill_across_a_gap_live_refuses.py` -
hafta sonu, gecelik seans, canli kapiyla ayni sinir, ve bosluktan *sonraki*
barin hala normal sinyal bari oldugu.

### F34 - aile karsilastirmasi adil bir yaris degildi (landed)

Izgara boyutlari cok esitsiz, `max_combos` ise hepsinde 2000:

| aile | izgara | onceki kapsam | yeni kapsam |
|---|---|---|---|
| ichimoku | 180 | %100 | %100 |
| mtf_pullback | 648 | %100 | %100 |
| burst | 1.728 | %100 | %100 |
| dual_t3 | 2.880 | %69,4 | %70,3 |
| parabolic_flip | 19.440 | %10,3 | %13,0 |
| t3_flip | 36.000 | %5,6 | %8,4 |
| stoch_flip | 64.800 | %3,1 | %6,0 |

Optimizer sembol basina kazanani bu ailelerin skorlarini yan yana koyarak
seciyor. Kucuk izgarali aile *gercek* en iyisini sunuyor, `stoch_flip`
rastgele bir %3 lÃ¼k cekilisin en iyisini; beklenen ornek-en-iyisi gercek
en iyinin belirgin altinda. Yani onyargi hangi fikrin daha iyi trade
ettigiyle degil, kimin izgarasinin kucuk oldugu ile ilgiliydi - ve buyuk
izgarali kazananlar `combo_seed` ile degisiyordu.

`coverage_budget()` (optimizer.py): once herkese `min(izgara, cap)`, sonra
kucuk izgaralarin kullanamadigi artigi hala eksigi olanlara kalan alanla
orantili dagit. Iki kasitli ozellik: **toplam buyumuyor** (14.000 -> 13.998,
ayni duvar saati, ayni worker sayisi) ve **hicbir aile duz cap in altina
dusmuyor** (bugune gore ayarlanmis bir arama gerileyemez). Operatorun acik
`strategy_max_combos` tablosu hala ustte.

Bu farki daraltiyor, kapatmiyor. Tam esitlemek ya sisirilmis izgaralari
budamayi ya da daha fazla zaman harcamayi gerektirir; ikisi de kendi
takaslari olan kararlar.

Kapak: `tests/test_the_search_budget_follows_the_grid_size.py`.

### Geri cekilen iddialar

- **"Izgaralarin dortte biri kopya."** Olculdu, tutmadi: tam degerlendirilen
  yapilandirma kimligiyle (sinyal seti + cikis eksenleri) `dual_t3` %7,2.
  `burst` in %27 si sabit spread li test tezgahindan gelen bir yapaylik -
  `cost_rank_max` duz bir maliyet serisinde ayrim yapamaz.
- **"stoch_flip izgarasinda hic sinyal uretmiyor."** Olcum hatasiydi:
  `combos_from_grid` deger degil **indeks** dondurur, indeks dogrudan
  `Params` e yazilinca `stoch_k_period=0` olur. Izgaradaki her gercek deger
  536-1654 sinyal veriyor. Aile saglam.

### Dokunulmayan

`adx_max` hala `OPT_FIELDS` icinde, 7 aileden (arsiv) 5 i okuyor, **hicbir izgarada
yok** - yani kalici olarak varsayilaninda donmus. Bu turda eklenmedi: onu
okuyan aileler (`stoch_flip`, `parabolic_flip`) zaten en kotu kapsanan
izgaralar, ve butce adil hale gelmeden yeni eksen eklemek onu ayni ornekleme
sorununun icine atardi. Kapsam oturunca olculebilir bir soru.

Ayni sekilde donmus ama daha az onemli: `htf_mode` ve `adx_period` hic
`OPT_FIELDS` te degil. `rsi_length` / `stoch_length` / `smooth_k` /
`smooth_d` yalnizca panelin StochRSI serisini besliyor, sinyal uretmiyor -
izgarada olmamalari dogru.

**Not:** F33 bu kod degisikliginden onceki aramalari etkilemez; calisan
arama eski `backtest.py` ile baslamisti.

### F34 DUZELTME (ayni gun) - yukaridaki kapsam tablosu yanlisti

Yukaridaki tabloyu `optimizer.strategy_grids[fam]` uzerinden kurmustum. O,
ailenin **yalnizca kendi** eksenleri. Sweep'in gercekten ornekledigi izgara
`searchable_axes(fam, {**shared, **own})` - paylasilan risk izgarasi
(sl_atr_mult 6 x trail_start_atr 6 x trail_step_atr 5 x max_spread_atr 6 =
1.080) ailenin beyan ettigi her seyi carpiyor. Canli bloktan okunan gercek
degerler:

| aile | gercek izgara | kapsam (cap 2000) |
|---|---|---|
| ichimoku | 1.080 | %100 |
| parabolic_flip | 8.640 | %23,2 |
| stoch_flip | 28.800 | %6,97 |
| t3_flip | 144.000 | %1,41 |
| mtf_pullback | 622.080 | %0,34 |
| burst | 1.244.160 | %0,18 |
| dual_t3 | 2.073.600 | %0,12 |

Yani siralamanin tamami tersineydi: `dual_t3` / `burst` / `mtf_pullback` en
**kotu** kapsananlar, en iyiler degil. Yayilim 190 kat.

`coverage_budget()` implementasyonu dogru - `_run_all` tahsisi zaten
`variant["grid"]` uzerinden, yani birlesik izgaradan hesapliyor. Yanlis olan
yalnizca cevrimdisi olcum betigi ve buraya yazilan tabloydu. Ama etkisi
kucuk: cap'in altinda sadece `ichimoku` var, dolayisiyla yeniden dagitilan
~920 kombinasyon. Gercek israfi kaldiriyor ve dogru sekilde, ama 190 katlik
yayilimi kapatmiyor - onun icin izgaralarin kendisinin kuculmesi gerekir.

### F35 - hicbir aile silinmemeli (olculdu)

206 arama kaydinin kazananlari. Son 60 arama, yalnizca canli 7 aile (arsiv):

| aile | kazandi | kazanan TF dagilimi (tum gecmis) |
|---|---|---|
| burst | 19 | M15x14 M5x12 M30x9 |
| stoch_flip | 12 | M15x16 M30x14 M5x4 |
| dual_t3 | 7 | M15x7 M5x6 M30x2 |
| mtf_pullback | 4 | M5x9 M15x5 M30x2 |
| parabolic_flip | 2 | M5x4 M15x1 |
| t3_flip | 1 | M15x7 M5x7 M30x4 |
| ichimoku | 1 | M30x1 |

Yediisi de son donemde kazaniyor. Hicbiri olu agirlik degil, silinmemeli.
`t3_flip` / `parabolic_flip` / `ichimoku` su an canli hicbir sembolde degil
ama arama onlari secebiliyor - secenegi kaldirmak icin sebep yok.

**Onemli karsi-sinyal:** en kotu kapsanan aileler (`burst` %0,18,
`dual_t3` %0,12) en cok kazananlar. Saf kapsam-onyargisi hikayesinin
ongordugunun tersi. Yani izgara boyutu kimin kazandigini belirleyen baskin
etken **degil**. F34 hala ilkeli ve bedava, ama sonuclari acikladigi iddiasi
geri cekiliyor.

### Siradaki tek yuksek kaldiracli hamle (yapilmadi, operator karari)

`max_spread_atr` paylasilan izgarada 6 degerle duruyor ve **her** ailenin
izgarasini 6 ile carpiyor. Bu bir alfa ekseni degil, bir maliyet/islem
yapilabilirlik kapisi. 6 -> 2 degere inmek her ailenin izgarasini 3 kat
kuculturdu (dual_t3 2.073.600 -> 691.200, kapsam %0,12 -> %0,35) neredeyse
sifir bilgi kaybiyla.

### 31.08 - operator hatasi: tests/conftest.py uzerine yazildi

Aile denetimi sirasinda `tests/conftest.py`'nin var olmadigi varsayildi ve
uzerine yeni bir dosya yazildi. Dosya vardi. Icinde uc sey vardi:

1. `TestClient` alt sinifi (oturum basligi) - kaybolunca 347 test kirildi.
2. `_survive_unreadable_symlinks()` - pytest'in `cleanup_dead_symlinks`
   cagrisini yutan yama. Bu makinede sembolik bag *degerlendirmesi* politika
   ile kapali (WinError 1463), dolayisiyla tamamen yesil bir suite
   `pytest_sessionfinish`'te patlayip non-zero donuyor. Kaybolunca tam olarak
   bu yasandi ve saatlerce "cozulmeye" calisildi - zaten cozulmustu.
3. `no_real_log_file` - **her test icin** `LOG._write_file`'i susturan autouse
   fixture. AGENTS'taki "testler `logs/micofx.log`'a yazmamali" kuralini
   uygulayan sey buydu.

Sonuc: 12:51:18 - 13:07:54 arasinda calisan suite kosumlari canli loga
**27.107 satir** test ciktisi yazdi (`[FUZZ]`, `[TEST]`, `[MYPAIR]`, ayrica
canli sembol adlariyla sahte TRADE satirlari). 13:05:44'te dosya 4096 KB
sinirini asti ve rotasyon **en eski 2048 KB'i dusurdu** - yani o pencereden
onceki gercek islem gecmisi gitti. Geri getirilemez; gece yedegindeki
arsivlerde olabilir.

`git checkout -- tests/conftest.py` ile dosya geri alindi, suite yeniden
2729 passed / exit 0. 13:07:54'ten sonra yeni kirlenme yok. Log dosyasina
elle dokunulmadi: canli surec onu acik tutuyor ve desteklenen bir temizleme
kapisi yok (`POST /api/logs/clear` kasitli olarak kaldirilmis). Cop artik
dosyanin en eski icerigi oldugu icin bir sonraki rotasyon onu dusurecek.

**Ders:** var olmadigi dusunulen bir dosyaya yazmadan once oku. Ve tam
suite'i `Select-Object -Last N` ile degil, ozet satirini gorerek dogrula -
kuyruk `[100%]` gosterirken yukarida 347 `F` vardi.

### F36 - geri verme olculdu (289 otopsi, 31.08)

Temel: 289 kapanmis islem, net **-40,7 R**, kazanma %33,6, ortalama
-0,141 R. **288 islem tepesinin altinda kapandi**, tepeye gore geri verilen
medyan **1,17 R**. Yani geri verme anekdot degil, kitabin varsayilan
davranisi.

Karsi-olgusal tarama. Bir T esigi icin MFE'si T'ye ulasan islemin sonucu T
olur (MFE'nin tanimi fiyatin oraya degmesidir, dolayisiyla T'de bekleyen bir
emir dolardi); T'ye ulasmayan islem gercek sonucunu korur. Bu, "MFE'nin
tamamini yakala" iddiasi **degil** - AGENTS mfe_r'nin bar-ici tepe oldugunu
ve hasat edilemeyecegini soyluyor; fiyatin icinden gectigi sabit bir seviye
farkli ve savunulabilir bir iddia.

| T | harvest net | fark |
|---|---|---|
| 0,5 | -32,1 | +8,6 |
| 0,8 | -28,4 | +12,3 |
| **1,0** | **-28,4** | **+12,4** |
| 1,2 | -41,0 | -0,2 |
| 1,5 | -30,0 | +10,8 |
| 2,5 | -32,9 | +7,8 |

Sembol basina en iyi T: JPN225 1,0 (+16,4 R, n=69), NAS100 2,5 (+11,3 R,
n=51), GER40 0,5 (+3,1 R, n=40), US30 4,0 (+1,6 R, n=86).

**Elle ayarlanmasi onerilmez.** T yuzeyi monoton degil: 1,0 iyi, 1,2 kotu,
1,5 yine iyi. 289 islemde bu, esigin tanimlanabilir olmadiginin isareti -
sirali komsu degerlerin isaret degistirmesi gurultunun imzasidir. Kazanc
buyuklugu gercek, tam degeri degil.

**Breakeven kolonu kasitli olarak raporlanmiyor.** Tarama BE@0,5 icin
-40,7 -> +9,1 (+49,8 R) veriyor ve bu, modelin tam da yaniltici oldugu
yerdir: `max(got, 0)` kazananlarin girise geri cekilip BE stopuna carpip
sonra donme ihtimalini yok sayiyor, yani BE'nin kazananlari oldurme
mekanizmasini hic modellemiyor. AGENTS zaten kayitli: `breakeven_at_r`
canli **1,5**, 0,5 degil - "BE-2 GER40 -32 R". Yani bu tam olarak denenmis
ve canlida kaybettirmis fikir. Tarama basligina uyulmadi.

`harvest_at_r` / `harvest_step_atr` `OPT_FIELDS` ekseni degil, yani arama
bunu kendisi bulamaz; operator ayaridir. Dogru siradaki adim bir sayiyi elle
yazmak degil, esigi olculebilir kilmak.

## F37 - kayip payoff tarafinda, giris tarafinda degil (olculdu, 31.08)

Tersine muhendislik: canli 289 otopsiyi uygulanan damgalarla yan yana koydum
(`cursor/reverse_live_vs_stamp.py`, `reverse_payoff.py`).

**Giris tarafi saglam.** Canli kazanma orani %33,6; damgalarin ongordugu ~%35.
Ortalama kayip 0,85 R, yani stoplar modelden kotu degil. Fill kaymasi medyan
+0,004..+0,040 R - ihmal edilebilir.

**Ayrisan tek sey payoff.** Canli 1,48; damgalarin ima ettigi ~2,1. Kazananlar
yaklasik %30 kisa kesiliyor. Kitap R/islem -0,141; payoff acigi kapansa
**+61 R**.

| sembol | canli payoff | damga payoff | acik | partial_at_r |
|---|---|---|---|---|
| XAUUSD | 2,28 | 2,29 | -0,01 | **0** |
| US30 | 1,70 | 2,09 | -0,39 | 1,5 |
| SpotBrent | 1,54 | 1,85 | -0,31 | 1,5 |
| JPN225 | 1,61 | 2,46 | -0,85 | 1,5 |
| GER40 | 1,13 | 2,19 | -1,06 | 1,5 |
| NAS100 | 0,84 | 2,14 | -1,30 | 1,5 |

Ic kontrol: payoff'u damgasiyla ortusen tek sembol (XAUUSD) canlida net kar
eden tek sembol - ve `partial_at_r`'si kapali tek etkin sembol. Model yanlis
degil, uygulanisi kazananlari buduyor.

**Cikis kovalari.** stop 155 islem **-145,0 R** (ort MFE sadece 0,44 - bu
islemler zaten hic lehe gitmemis), trail 86 islem +75,4, flatten 43 islem
**+26,6** (%74 kazanan). Seans/gun-sonu flatten'i *kar ediyor*; "zorla kapatma
zarar ettiriyor" hipotezimi olctum ve **curuttum**.

### partial_at_r A/B (holdout snapshot, offline)

`partial_at_r` bir `OPT_FIELDS` ekseni degil, dolayisiyla damganin params
sozlugunde hic yok - params diff'i onu goremez. `Params.from_config` canli
satirdan kopyaladigi icin *bugunun* konfigi simule edilince modellenir, ama
overlay acilmadan once kazanilmis bir damga onsuz skorlanmistir.

Kontrollu deney (`reverse_partial_ab.py`, `reverse_partial_paired.py`): ayni
holdout snapshot, ayni konfig, tek degisken rung. Rung girisleri
degistirmedigi icin iki kosu islem-islem eslesiyor.

| sembol | n | fark (kapali-acik) | ilk yari | ikinci yari | ayni yon |
|---|---|---|---|---|---|
| **JPN225** | 1405 | **+26,94** | +13,74 | +13,21 | evet |
| GER40 | 391 | +7,22 | +4,88 | +2,34 | evet |
| US30 | 1664 | +4,43 | +3,71 | +0,72 | evet |
| NAS100 | 1739 | -13,88 | +9,96 | -23,84 | **HAYIR** |
| SpotBrent | 128 | -0,84 | -0,85 | +0,00 | HAYIR |

Mekanizma her sembolde tutarli: rung acikken kazanma orani **her zaman**
yukseliyor, payoff **her zaman** dusuyor. Dokunulan islemlerde medyan negatif
(-0,19..-0,33) ama ortalama pozitif ve sadece ~%37'si kapatmadan yana - yani
scale-out sik sik az kazandiriyor, nadiren buyuk kosani budayarak cok
kaybettiriyor. Payoff sikismasinin kaynagi bu.

**NAS100 yarilar arasi isaret degistiriyor** - oradaki "partial faydali"
sonucu tek pencerelik gurultu, uygulanmadi. Sadece JPN225 iki yarida
neredeyse esit, yani tek savunulabilir aday o.

**Uygulanmadi - kapi kasitli kapali.** `POST /api/symbols/JPN225`
`{"partial_at_r":0}` -> **400 "partial_at_r panelden yazilamaz"**. Tek
alternatif `data/micofx.db`'ye ikinci bir yazici acmak olurdu; AGENTS bunu
yasakliyor. Guard gorevini yapiyor, etrafindan dolasilmadi. Operator karari.

### Yan bulgu: damgalar taze veriyi tutmuyor

Bugunun canli konfigi, bugunun holdout barlarinda US30 icin **-79,7 R / 1664
islem** (-0,048 R/islem). Ayni sembolun damga holdout'u +224,2 R / 2703 islem
(+0,083). Canli gerceklesme -0,024. Yani **taze replay canliyi damgadan cok
daha iyi ongoruyor**. Damgalar iyimser tarafta; apply gate'leri bunu
yakalamiyor. Bu, F37'nin payoff acigindan ayri ve daha genis bir konu.

## F38 - marj kullanilmiyor cunku bagli olan marj degil (olculdu, 31.08)

Operator: "acilabilir pozisyon ve lot buyuklugu marji kullanabilsin."

**Olcum.** equity 1648,21 / kullanilan marj 47,49 -> **%2,88**, izin
**%90**. Dagitilabilir butce 1435,90. Sikayet dogru.

**Bagli olan marj degil.** Canli hesap goruntusu varken `lot_for`
(risk.py:522) `min(auto, r_cap, ceiling)` cozuyor; `auto` marj payi,
`r_cap` otomatik 1R tavani (`max(risk_percent, %2) x bakiye`). Dokuz
sembol birden atese girse marj %40,8 olurdu ama risk %17,2'de tikaniyor -
yani **`r_cap` bagliyor**. Marj bolusumunu (`butce / bostaki ad sayisi`)
gevsetmek tek basina hicbir sey acmaz. Yan bulgu: `risk_percent`'ten
hesaplanan `raw` bu dalda hic kullanilmiyor, sadece nota yaziliyor.

**Olcekleme bekletildi.** F37 kitabin canli beklentisini negatif olctu
(-0,141 R/islem, payoff 1,48 / gereken ~2,1). Boyut negatif beklentiyi de
carpar: 2,2x, mevcut -40,7 R'yi ~-90 R yapardi. Operator karari: once
payoff acigi kapansin.

### Kitap geneli 1R tavani geri takildi

`max_concurrent_risk_pct` 27.08'de **ulasilamaz** oldugu icin kapatilmisti
(lot risk%'ti, kitap ~%17'de kaliyordu). Marji kullanmak icin `r_cap`
yukseltmek, tavani ulasilamaz kilan seyi tam olarak ortadan kaldirir - o
yuzden tavan, olceklemeden **once** geri takildi. Su anki boyutta atil
(%17,2 < canli 30).

`can_open` artik acik ticketlarin `remaining_position_risk` toplamina bu
fill'i ekleyip equity yuzdesiyle karsilastiriyor. STOPSUZ zaten ustte
reddedildigi icin toplama `inf` sizamaz; girise cekilmis trail butceyi
birakir; `sl_distance` bilinmiyorsa yeni fill fiyatlanamaz ama **acik
kitap yine sayilir**.

Ters yone donen 27.08 testleri guncellendi:
`test_concurrent_risk_gate` (artik bagliyor),
`test_capacity_reports_live_open_risk`,
`test_the_book_holds_what_the_walk_forward_validated` (kaynak-tarama
asserti kaldirildi). Yeni: `test_the_book_wide_risk_ceiling_binds_again`.
2735 test gecti, ruff temiz.

**Sembol basina ticket 1 kaldi** - arama `max_open=1` skorluyor.

## F39 - sinyal tarafi olculdu: sembol, aileden daha belirleyici (31.08)

Operator: "sorun tf degil stratejiler". Simdiye kadar giris tarafini hep
*modele gore* olctum (canli WR damgayi tutuyor). Mutlak edge hic sinanmamisti.

**Test 1 - ileri getiri** (`cursor/reverse_entry_edge.py`). Cikis modeli tamamen
cikarildi: sinyal -> sonraki acilistan doldur -> +1/5/10/20 barda ATR cinsinden
hareket, yone gore isaretli. Taban: ayni barlarin aile kendi long/short oraniyla
karilmis hali (yazi-tura girisin bedava aldigi getiri).

`stoch_flip` canli parametreleriyle **kesin sifir**: US30/JPN225/NAS100/SpotBrent
uzerinde her ufukta t = -0,55..+0,51, sinyal sayisi 22k-37k. Bu ince ornek degil,
**guvenli bir null**. Kitabin en buyuk parcasi (US30, 86 canli islem) bu ailede.

**Test 2 - varsayilan parametrelerle matris** (`reverse_family_edge_matrix.py`).
49 hucrede sadece 5 anlamli sonuc - rastlanti beklentisine yakin. Yani Test 1'de
ayarli parametrelerin guclu cikmasi buyuk olcude ayni pencereye uydurmadir.

**Test 3 - kuyruk asimetrisi** (`reverse_tail_asymmetry.py`). Ortalama getiri
breakout ailesini haksiz cezalandirir: stop sol kuyrugu keser, trail sag kuyrugu
birakir - sistemin cikis modeli tam da bunu paraya cevirir. +20 barda MFE/MAE
orani, ayni tabana bolunmus:

| sembol | en iyi aile | oran | canli R/islem |
|---|---|---|---|
| XAUUSD | ichimoku 1,173x | **1,06-1,17 hepsinde** | +0,230 |
| BTCUSD | burst 1,158x | **1,08-1,16 hepsinde** | +0,227 (taze) |
| GER40 | parabolic 1,075x | 1,05-1,08 | -0,188 |
| JPN225 | ichimoku 1,135x | 1,02-1,14 | -0,269 |
| SpotBrent | ichimoku 1,040x | ~1,00 | +0,117 |
| **NAS100** | dual_t3 1,011x | **hicbiri 1,01 ustu degil** | -0,333 |
| **US30** | ichimoku 1,036x | **hicbiri 1,01 ustu degil** | -0,024 |

**Asil bulgu satirlarda, sutunlarda degil.** US30 ve NAS100'de *hicbir aile*
asimetri uretmiyor; XAUUSD ve BTCUSD'de *neredeyse her aile* uretiyor. Ve bu,
canli P&L ile birebir ortusuyor. Yani enstruman secimi, aile seciminden daha
belirleyici.

Aile siralamasi (tabana gore ort): ichimoku 1,071x (6/7 sembol) - **ve hicbir
canli sembolde kullanilmiyor**; parabolic_flip 1,041x; burst 1,036x;
mtf_pullback 1,031x; stoch_flip 1,026x; t3_flip 1,010x; **dual_t3 1,003x
(0/7)** - GER40 canlida bunu kullaniyor.

**Neden damgalar iyimserdi (F37 yan bulgusu simdi aciklandi).** Sifir-edge bir
sinyal uzerinde 489k kombinasyonluk arama yine de bir "kazanan" dondurur -
sadece gurultuye uydurur. US30 damgasi +224 R, ayni konfigin taze barlardaki
replayi -79,7 R. F35'in "her aile kazanan uretti" sonucu da bu yuzden supheli:
o olcut "hangi aile aramayi kazandi" idi, ki tam olarak asiri uydurma metrigi.

**Duzeltme.** 31.08'de "sorun aile seciminde degil, cikista" demistim. Eksikti:
cikis payoff'u sikistiriyor (F37 gecerli), ama altta sinyal edge'i de zaten
cok ince - ve US30/NAS100'de yok. Operator hakliydi.

**Uyarilar.** Asimetri farklari kucuk (%2-8) ve maliyet haric; varsayilan
parametreler; sembol basina tek pencere. Kesin huku degil, yon gostergesi.

---

## F40 - kitapta olmayan sinyal sekli: kanal kirilimi (olculdu + kuruldu, 31.08)

**Soru.** Operator: "sorun TF degil, stratejiler. sifirdan daha iyi
kurabiliriz, kendi gostergemizi de olusturabilirsiniz." F39 stoch_flip'in
giris edge'i olmadigini gostermisti; bu tur onun devami - once *neyin*
ongordugunu bul, sonra yaz.

**Yontem (F39 hatasini tekrarlamamak icin).** Aile degil, *primitif* taradim:
her aday, fiyat hakkinda en fazla iki ayari olan tek bir hipotez. Her pencere
%60 train / %40 test bolundu ve bir primitif ancak **iki yarida da ayni
isaretle** tuttuysa sayildi. Iki metrik: ileri getiri (surukleniyor mu) ve
MFE/MAE asimetrisi (stop+trail'in paraya cevirdigi sekil), her ikisi de
primitifin kendi long/short oraninda karistirilmis bir tabana karsi.

**Olculen (10 pencere, ornek disi yari).**

| primitif | test asim. medyan | iki yarida tutan |
|---|---|---|
| **kanal kirilimi (50 bar)** | **1,051** | **5/10 - test yarisinda 10/10 pozitif** |
| momentum (z>1) | 1,043 | 3/10 |
| kanal kirilimi (20 bar) | 1,052 | 2/10 |
| clv / streak fade | 1,012 / 0,971 | 0/10 |
| **ortalamaya donus (z2/z3)** | **0,943 / 0,947** | **0/10** |

Ortalamaya donus *rastgele giristen kotu* - "endeksler intraday mean-revert
eder" hipotezi olculup reddedildi. Dogru yon tersi.

**Lookback yapisal, sansli parametre degil.** Kritik kontrol: 50 kazandi diye
50 secmek F39'un tarif ettigi asiri uydurmanin ta kendisi olurdu. Eksen
tarandi ve egri duzgun cikti - 10 barda 1,034, 20'de 1,052, 40'ta 1,062,
100'de 1,078, 150'de 1,076. Tek noktada sivrilme yok; etki pencere uzadikca
buyuyor. BTCUSD'de monoton 1,060 -> 1,268.

**Boslugun kendisi.** Bu sekil o gunku 7 ailenin (arsiv) **hicbirinde** yoktu. `burst` menzil
*genislemesi* (barin kendi high-low'u) ve kendi docstring'i farki yaziyor:
"a level-based breakout keys off a price the market has already printed - an
N-bar channel", ki o degil. En yakin sey `ichimoku` (tenkan/kijun N barlik
orta noktalar) - ve F39'da o 7 ailenin (arsiv) en iyisi cikip hicbir canli sembolde
kullanilmiyordu. Eski `donchian` 12.08'de **kaldirildi**, ama para kaybettigi
icin degil: optimizer'in `strategies` listesinde olmadigi icin hic aranamadi.
Yani sekil hakkinda bir hukum hic verilmemisti.

**Kurulan.** `channel_break`: kapanis, kendisinden onceki `chan_lookback`
barin en yuksegini asarsa alis / en dusugunu kirarsa satis. Kanal sinyal
barini **disarida birakir** (kendi settigi zirveyle karsilastirmak burst'un
sorusu olurdu). `chan_buffer_atr` seviyenin kilinda gezinenleri eler;
`first_of_run` trendin her barinda tekrar sinyal uretmesini onler. Izgara
lookback'i 150'ye kadar goturur - `burst`'un 40 tavani olcumun yasadigi yere
ulasamiyordu.

**Holdout (tam maliyetli, ayni barlar/cikislar, tek degisken aile).**

| pencere | mevcut | channel_break | fark |
|---|---|---|---|
| US30_M30 | stoch_flip -79,7 R | +31,1 R (lb20) | **+110,8** |
| US30_M5 | stoch_flip -86,1 R | -7,6 R (lb150) | **+78,5** |
| GER40_M30 | stoch_flip -35,6 R | +20,2 R (lb150) | **+55,7** |
| NAS100_M30 | stoch_flip +8,7 R | +23,8 R (lb150) | +15,0 |
| BTCUSD_M30 | burst +72,1 R | +60,2 R | -11,9 |
| XAUUSD_M15 | burst +54,6 R | +38,8 R | -15,8 |
| GER40_M15 | dual_t3 +48,9 R | +4,8 R | -44,2 |
| JPN225_M15 | stoch_flip +96,8 R | +30,6 R | -66,2 |

**Evrensel bir kazanan degil - ve olmamasi dogru.** Tam olarak kanamanin
oldugu yerde geciyor: gectigi dort pencerenin dordunde de mevcut aile
`stoch_flip`, yani F39'da giris edge'i olmadigini olctugum aile. Saglikli
ailelere (burst, dual_t3) dokunmuyor. Bagimsiz dogrulama: payoff orani
neredeyse her pencerede lookback ile artiyor (BTCUSD 3,68 -> 4,34), ki
asimetri bulgusunun tam olarak ongordugu sey.

**Uyarilar.** Holdout'ta en iyi lookback pencere *icinden* secildi - bu ustten
bir tahmin; gercek arama ayni secimi walk-forward ile ornek disi yapar.
Asimetri farklari kucuk (%3-8). Aile arama listesinde, yani bundan sonrasini
per-sembol arama karara baglar; hicbir sembole elle atanmadi.

**Durum.** `STRATEGIES` 7 -> 8, `defaults.json` izgarasi, panel etiketi ve
alan yardimi, 10 fail-first test. Tam suit 2772 gecti, ruff temiz. Canli
surec eski `defaults.json`'u yuklu tasiyor; restart 4 acik pozisyon nedeniyle
409 - gozcu kitap duzlesince indirecek ve aile o an aranabilir olacak.

### F40 ek - kor secim testi: iddianin duzeltilmesi (31.08)

Yukaridaki holdout tablosunda en iyi lookback pencere *icinden* secilmisti ve
bunu "ustten tahmin" diye isaretlemistim. Testi yaptim: secim ilk %60'ta
korlemesine yapildi, fatura son %40'ta odendi. Mevcut aile de ayni son %40'ta
olculdu.

| pencere | kor secim | test net R | mevcut | fark | en iyi olabilecek |
|---|---|---|---|---|---|
| **NAS100_M30** | lb20 b0,25 | +9,67 | -16,52 | **+26,19** | +9,67 |
| **US30_M5** | lb20 | -3,23 | -47,55 | **+44,32** | +32,37 |
| **GER40_M30** | lb150 | -6,27 | -18,13 | **+11,86** | -6,11 |
| **US30_M30** | lb150 b0,25 | -19,38 | -22,17 | **+2,78** | +9,49 |
| SpotBrent_M15 | lb100 | -4,22 | -3,48 | -0,75 | +4,66 |
| XAUUSD_M15 | lb20 b0,25 | -5,59 | +8,48 | -14,07 | +12,00 |
| GER40_M15 | lb100 | +9,48 | +26,73 | -17,25 | +9,48 |
| JPN225_M15 | lb150 | +9,14 | +41,55 | -32,40 | +41,64 |
| BTCUSD_M30 | lb100 b0,25 | +14,28 | +49,19 | -34,91 | +32,12 |
| **TOPLAM** | | **+3,88** | **+18,10** | **-14,22** | |

**Duzeltme.** `channel_break` kitap capinda bir yukseltme **degil** - kor
secimle toplamda mevcut ailelerin 14,2 R gerisinde. Onceki tablonun
"5 pencerede geciyor" ifadesi hindsight'la sisirilmisti.

**Ayakta kalan sey.** Desen aynen duruyor ve daha da keskin: gectigi dort
pencerenin **dordunde de** mevcut aile `stoch_flip` - F39'da giris edge'i
olmadigini olctugum aile. Kaybettigi dort pencerenin dordunde de mevcut aile
para kazaniyor (burst, dual_t3). Yani bu bir aile *degisimi* onerisi degil,
`stoch_flip` icin bir *yedek* onerisi.

**Asil bulgu: zayif halka secim metrigi, sinyal degil.** Asimetri egrisi
yapisaldi (10 pencerede duzgun, monoton). Ama net R ile lookback secmek
gurultulu: JPN225'te kor secim +9,1 iken ayni yarida en iyi +41,6, US30_M5'te
-3,2 iken +32,4. Sinyalin kendisi saglam, onu *paraya ceviren ayari secmek*
guvenilmez. Bu, F39'un "489k kombinasyon gurultuye uyar" bulgusunun ayni
madalyonun oteki yuzu - ve gercek aramanin 5 segmentli walk-forward + refine
turlari, buradaki kaba 2-parcali bolmeden daha saglam secim yapar.

**Sonuc.** Aile arama listesinde kalir; beklenti kitap capinda kazanc degil,
`stoch_flip` calisan sembollerde (US30, NAS100, GER40/M30) yedek. Hicbir
sembole elle atanmadi.

---

## F41 - geri verme gercek, ama hasat etmek daha pahali (olculdu, 31.08)

**Tetik.** Gozcu 17:01'de canli yakaladi: acik kitap +64,03'e cikip bir saat
icinde +23,33'e dondu - tepeden %64. Ayni sekil 08:30 olayinda da var
(+139,80 -> +36,69). Bunun bariz cozumu "kar bir kere odendiyse trail'i sik"
(harvest_at_r / harvest_step_atr).

**Test.** 10 pencere, tam maliyetli replay, canli konfigler, tek degisken
overlay. `simulate` her iki alani da modelliyor, yani bu kagit uzerinde degil
maliyetli bir olcum.

| harvest | toplam net R | fark |
|---|---|---|
| **kapali** | **+86,38** | - |
| 1,5R / 0,4 | -128,99 | -215,37 |
| 2,0R / 0,5 | -129,39 | -215,77 |
| 1,0R / 0,4 | -434,29 | -520,67 |
| 1,0R / 0,25 | -497,64 | -584,02 |

**Her ayar, her buyuklukte kaybettirdi.** Erken armanan (1,0R) en kotusu.

**Mekanizma sutunlarda gorunuyor.** US30_M30, harvest 1,0R/0,4: islem sayisi
1664 -> 2240, kazanma orani %32,5 -> %35,9 **yukseldi**, ama payoff 1,93 ->
1,55 ezildi. Yani sikilan trail kazananlari erken kesiyor ve bosalan yere
yeniden giris uretiyor. Daha sik kazanip daha az kazanmak, bu kitapta net
zarar.

**Sonuc.** Gozcunun gordugu geri verme *gercek* ama kazananlarin kosmasina
izin vermenin **fiyati**, ve payoff sutunu bu fiyatin odenmeye degdigini
soyluyor. AGENTS'in "harvest live off book-wide" notu artik kagit sonucuna
degil 10 pencerelik maliyetli olcume dayaniyor. `harvest_at_r` /
`harvest_step_atr` kapali kalir; geri verme grafigine bakip bunu acmak
cazip ve yanlis.

**Not.** Bu, F37'nin `partial_at_r` bulgusuyla ayni yonde: kazananin ustunu
tirtiklayan her mekanizma bu kitapta payoff'u tasidigi degerden fazla
yiyor. Cikis tarafinda aranacak sey "kari erken kilitlemek" degil.

---

## F42 - aileleri tek stratejide birlestirmek: olculdu, yapilmamali (31.08)

**Soru (operator).** 8 aile (arsiv) vardi; mantigi tek stratejide toplayabilir miyiz?

**Sekil olarak zaten 4.** trend yonu (dual_t3, t3_flip, parabolic_flip,
ichimoku), trend+geri cekilme (mtf_pullback), osilator (stoch_flip),
patlama/seviye (burst, channel_break).

**Ortusme, sans tabanina karsi.** mtf_pullback barlarin %17,6 sinda atesliyor;
+-2 bar toleransla zaman cizgisinin yarisini kapliyor, yani iki aile hicbir
iliski olmadan da ~%25 ortusur. Bir seriyi rastgele kaydirip (yogunluk ayni,
iliski yok) taban olctum:

| cift | gozlenen | sans | fazla |
|---|---|---|---|
| mtf_pullback / stoch_flip | %53,0 | %24,3 | +%28,7 |
| burst / channel_break | %35,8 | %7,7 | +%28,1 |
| burst / parabolic_flip | %34,4 | %8,1 | +%26,3 |
| dual_t3 / t3_flip | %33,0 | %16,3 | +%16,7 |
| mtf_pullback / t3_flip | %36,7 | %25,3 | +%11,4 |

Gercek iliski **var** (her cift sansin %11-29 ustunde) ama **kopya yok** - en
yuksek ham ortusme %53 ve o da en yogun aileyle. burst/channel_break yakinligi
beklenen: kanal kirilimi cogu zaman bir genisleme barinda olur.

**Neden yine de birlestirilmemeli.** Bu kitabin darbogazi sinyal cesitliligi
degil, **secim**. F40 ek: tek bir ekseni korlemesine secmek bile en iyi secimin
14,2 R gerisinde kaldi. F39: sifir-edge bir sinyal uzerindeki 64.800
kombinasyonluk grid yine de kazanan dondurdu (damga +224 R, taze replay
-79,7 R). Sekiz aileyi tek parametreli gostergede toplamak eksen sayisini
carpar, yani gurultuye uydurma yollarini cogaltir. Bugunku ayrim bir
**duzenleyici**: arama sinirsiz tek hipotez yerine sekiz kisitli hipotez
arasindan seciyor.

**Dogru sadelesme ters yonde.** Birlestirmek degil, olculebilir sekilde olu
olani cikarmak: stoch_flip (F39: giris edge i yok) su an US30, JPN225 ve
SpotBrent te canli.

---

## F43 - "en iyi strateji" aramasi: karmasiklik cevap degil (olculdu, 31.08)

**Gorev.** Operator: sinirsiz yetki, web/X/github arastir, en iyi stratejiyi
kur. Literatur tarandi, uc somut iddia test edildi, ucu de tutmadi.

**Literaturun kirilim tarifi.** Kaynaklar (retail icerik, dogrulanamayan
sayilarla) sunda birlesiyor: ADX > 20-25 filtresi, hacim teyidi (20-ort
ustu), ve "kanal genisligi < 1 ATR ise girme, sikismadir". Sonuncusu klasik
squeeze mantiginin **tersi** - daralmis aralikdan kirilim en iyi kurulum
sayilir. Ikisi ayni anda dogru olamaz.

**Olcum: hicbiri ayirt etmiyor.** channel_break lb=50 sinyalleri her kosula
gore dorttebirlere bolundu, asimetri train/test ayri olculdu (10 pencere):

| dilim | kanal genisligi | hacim/20-ort | seviyeyi asma |
|---|---|---|---|
| Q1 | 1,017 / 1,052 | 1,006 / 1,072 | 0,980 / 1,063 |
| Q2 | 0,960 / 1,074 | 0,959 / **1,114** | 1,012 / 1,102 |
| Q3 | 0,980 / 1,028 | 1,009 / 1,046 | 0,990 / 1,037 |
| Q4 | 1,024 / 1,094 | 1,024 / 1,040 | 1,017 / 1,039 |

Hicbirinde monoton siralama yok ve train'deki sira test'te bozuluyor (hacim
Q2 train'in en kotusu, test'in en iyisi). Dilimler arasi fark, iki donem
arasi farktan kucuk - gorulen sey kosul degil **rejim**. ADX zaten eksen
olarak gridde; hacim ve genislik **eklenmedi**, cunku eklemek gurultuye
uydurmanin iki yolu daha demekti.

**Sonuc 1: v1'in sadeligi dogruymus.** Kirilim filtrelenerek iyilesmiyor.

**Olcum 2: ekseni aramak mi, sabitlemek mi?** Kor secim (train'de sec, test'te
ode) vs her pencerede sabit lookback, hepsi ayni test yarisinda:

| | kor arama | sabit 20 | sabit 40 | sabit 60 | sabit 100 | sabit 150 |
|---|---|---|---|---|---|---|
| toplam test R | +3,88 | +17,66 | -3,25 | **-63,39** | +15,61 | +17,13 |

**Buradaki tuzak.** "En iyi sabit 20" demek sonucu gordukten sonra secmek
olurdu - F40 ek'te duzelttigim hatanin aynisi. Dogru okuma: net R bu
pencerelerde lookback'i **ayirt edemeyecek kadar gurultulu**. Bitisik ayarlar
+17,66 ile -63,39 arasinda savruluyor.

**Ayirt eden sey plato.** lb20'nin +17,66'si hemen yaninda ucurum olan yalniz
bir tepe (lb40 = -3,25). lb100 (+15,61) ve lb150 (+17,13) yan yana duran bir
plato. Ve F40'in asimetri egrisi - bagimsiz, daha yuksek sinyalli istatistik -
zaten uzun tarafi gosteriyordu (10 barda 1,034, 100'de 1,078). Iki bagimsiz
olcum ayni yeri isaret ediyor.

**Zaten dogru mekanizma var.** `opt_params.plateau_weight = 0.7`: arama tepeyi
degil platoyu odullendiriyor, ve 5 segmentli walk-forward buradaki kaba
2-parcali bolmeden saglam. Yani eksen sabitlenmiyor, grid oldugu gibi kaliyor
([20,40,60,100,150]) - net R'ye bakip 20'yi veya 60'i budamak, tam da bu
notun uyardigi hata olurdu.

**Genel sonuc.** Bu turda denenen her *ekleme* (harvest F41, aile birlestirme
F42, kirilim filtreleri F43) olcumde kaybettirdi; kazanan tek sey bir
**eksigi kapatmak** oldu (F40, kitapta hic olmayan sinyal sekli). Bu kitapta
"daha iyi strateji" karmasiklik eklemek degil, edge'i olmayani cikarmak:
`stoch_flip` hala US30, JPN225 ve SpotBrent'te canli.

## F44 - kademeli kar alma: mumkun ile karli ayni sey degil (olculdu + kapi acildi, 31.08)

Operator sorusu: "poz buyuk olsa kademeli kar alsak". Altinda dogru bir sezgi
var ama iki ayri iddiayi birlestiriyor ve ikisi ayni cevabi vermiyor.

**Birinci iddia dogru.** Kademeli cikis kucuk lotta zaten *mumkun degil*:
`partial_at_r` biletin ucte birini kapatir, broker min/adimina yuvarlanarak,
ve kalan min lotun altina duserse hic kapatmaz. 0.01 lotta bolunecek bir sey
yoktur. Boyut bu kapiyi acar.

**Ikinci iddia olculdu ve yanlis cikti.** R matematigi olcege duyarsiz:
0.3 lotun ucte biri ile 0.1 lotun ucte biri ayni R'dir. Yani boyut, kademeli
cikisin *isaretini* degistirmez, sadece uygulanabilirligini. Isaret icin
maliyetli holdout, ayni barlar ayni cikislar tek degisken basamak
(`cursor/partial_scan.py`, `charged_holdout`, tum yakalanmis pencereler):

| basamak | toplam net R | fark |
|---|---|---|
| kapali | **+133.31** | - |
| 1.0R | +30.07 | -103.24 |
| 1.5R | +68.17 | -65.15 |
| 2.0R | +74.94 | -58.37 |
| 3.0R | +70.35 | -62.97 |

Her basamak kaybettirdi, en erkeni en cok. Mekanizma sutunlarda gorunuyor ve
F41'deki harvest ile birebir ayni: US30_M30'da kazanma orani %30.7 -> %33.5
*yukseliyor*, payoff 2.10 -> 1.82 eziliyor. Daha sik kazanip daha az kazanmak.
Bu sistemin cikis modeli sert ATR stop + ATR trail; kar dagilimi az sayida uzun
kazanana yaslanir ve kademeli cikis tam olarak o kuyrugu kirpar.

XAUUSD tek istisna gibi duruyor (+54.62 -> +55.82, 1R'de) ama fark 1.2 R ve
ayni pencerede payoff 2.95 -> 2.11 duserek geliyor; yon degil gurultu.

### Asil bulgu: alan bir mandaldi, koruma degil

Olcumden daha onemlisi bunu uygularken cikti. `partial_at_r` canlida bes
sembolde 1.5'ti (SpotBrent, GER40, JPN225, NAS100, US30) ve **kapatilamiyordu**:

- `OPT_FIELDS` icinde degil, `Optimizer.apply()` ona hic dokunmuyor.
- `EXIT_RISK_FIELDS` icinde degil, `pending_exit_patch` kuyruguna girmiyor.
- Sembol POST kapisinda hands-off, 400 donuyor.
- Degeri yazan PATCH rotasi (25.08) o gunden beri kaldirilmis.

Yani alan acilabiliyor, kapatilamiyor. Bu hands-off degil, mandal. Kapali
olan iki sembol - XAUUSD ve BTCUSD - kitabin para kazanan iki sembolu olmasi
da F37'de gorulen desenin daha genis veriyle tekrari.

Kapi tek yonlu acildi (`_validate_one_way_overlay`): `partial_at_r` yalnizca
0 yazilabilir. Kapatmak islem ortasinda monoton guvenli - parca hic tetiklenmez.
Acmak 25.08 tehlikesinin ta kendisi: basamagi coktan gecmis bir pozisyon deger
inince aninda ucte birini birakir. O yon kapali kaldi. Kardes overlay'ler
(`harvest_at_r`, `harvest_step_atr`, `breakeven_at_r`) kapali; acilan sadece
mandal. Iki kapi da (tekil POST + `symbols-bulk`) ayni kurali cagiriyor.

## F45 - opt hizi: siranin degil, is parcasinin sorunu (olculdu, 31.08)

31.08 US30 aramasi 62 dakika surdu ve hicbir aday kapidan gecmedi. Isci
kullanimi olculdu: 62 dakikanin son on dakikasinda **14 isciden yalnizca 3'u**
CPU yakiyordu (20 saniyede 60 cekirdek-saniye, 11 isci tamamen bos). Takilma
yoktu - kuyruk bosalmisti.

Sebep dagitimda degil, granularitede. Is parcasi bir *sweep* = (sembol, TF,
aile (arsiv)). Tek sembollu arama 3 TF x 8 aile (arsiv) = 24 parca, 14 cekirdek. Parcalar
mertebe farkiyla esitsiz: izgaralar 1080 (ichimoku) ile 2.073.600 (dual_t3)
arasinda, ustune `coverage_budget` buyuk izgaraya daha buyuk butce veriyor.

Gonderim sirasi maliyetle ilgisiz sabit TF x aile sirasiydi, yani uzun bir
sweep kuyrugun sonuna dusebiliyordu. `longest_first` (LPT) eklendi. Ama
**tek sembolde hicbir sey kazandirmadi** ve bunu boyle yazmak gerekiyor:

| sembol | sweep | eski | longest_first | hizlanma | doluluk |
|---|---|---|---|---|---|
| 1 | 24 | 257.333.760 | 257.333.760 | 1.00x | %70 -> %70 |
| 2 | 48 | 423.738.720 | 370.285.200 | 1.14x | %85 -> %97.3 |
| 3 | 72 | 593.192.160 | 556.207.440 | 1.07x | %91.1 -> %97.2 |
| 9 | 216 | 1.678.433.520 | 1.633.144.320 | 1.03x | %96.6 -> %99.3 |

Tek sembolde makespan **tek bir sweep'in suresine cakili**: en pahali is
(dual_t3 M5) tek basina tabani belirliyor, hicbir siralama bunu yenemez. LPT
kitap geneli aramada gercek ama mutevazi bir kazanc (2 sembolde doluluk
%85 -> %97) ve bedava; o yuzden kaldi. Gozlenen sorunu ise **cozmuyor**.

Tek sembolun tabanini indirmenin iki yolu var ve ikisi de ayri bir karar:

1. **En pahali bes sweep'in besi de M5.** M5 gunde 288 bar yuruyor, M30 48 -
   6 kat. 62 dakikanin buyuk kismi oraya gitti. Kayitli `timeframes` listesi
   `['M5','M15','M30']`; `SEARCH_TIMEFRAMES` varsayilani M15/M30. M5'i aramadan
   cikarmak tabani ~3 kat indirir ama M5'te islem yapilabilirligi arama
   disina atar - operatorun ayrica ilgilendigi bir eksen, sessizce alinacak
   bir karar degil.
2. **Sweep'i bolmek**: kaba tarama dilimlere ayrilip isÃ§ilere dagitilabilir.
   Granulariteyi gercekten duzeltecek olan bu, ama refine turlari kaba
   sonuca bagli oldugu icin isci protokolu ve sonuc birlestirme degisir.

Simdilik olculen sey kayit altinda; ikisi de yapilmadi.

## F46 - giris kenari kitap genelinde olculemiyor (olculdu, 31.08)

Operator: "sorunumuz TF degil, stratejilerimizdeki hatalar". Olcum bunu
dogruluyor ama yonunu degistiriyor.

8 aile (arsiv) x 7 sembol, +10 bar ileri getiri t-istatistigi
(`cursor/reverse_family_edge_matrix.py`):

| sembol | mtf_pull | burst | dual_t3 | t3_flip | stoch_flip | parabolic | ichimoku | channel_break |
|---|---|---|---|---|---|---|---|---|
| US30 | -1.52 | -1.55 | -0.39 | -0.03 | **-1.98** | -1.04 | 0.66 | -1.31 |
| JPN225 | 0.05 | 0.78 | 0.93 | 0.82 | -0.37 | 0.38 | 1.92 | -0.32 |
| NAS100 | 0.28 | 0.35 | -0.67 | 0.07 | -0.20 | -0.66 | 0.92 | 0.75 |
| GER40 | **2.74\*** | 0.73 | -0.03 | 0.39 | 1.87 | 1.67 | -0.34 | 0.02 |
| XAUUSD | **2.33\*** | 0.96 | 0.47 | -0.93 | **2.97\*** | 0.92 | **2.39\*** | 0.46 |
| SpotBrent | 0.77 | 0.22 | -0.28 | 1.02 | 0.29 | 0.15 | -0.01 | **-2.98\*** |
| BTCUSD | -0.30 | **2.10\*** | -0.00 | -0.66 | 1.43 | 1.35 | 0.91 | 0.62 |

**56 hucre, 6 anlamli.** 56 testte |t|>=2 esiginden sans eseri ~2.8 hucre
gecer. Yani bulunan sey gurultu tabanindan zar zor ayirt edilebiliyor. Dogru
okuma "yanlis aileyi sectik" degil, **kitap genelinde olculebilir bir giris
kenari yok**.

Uc sonuc:

1. **US30'da tum aileler negatif**, `stoch_flip` -1.98. 31.08 aramasi 62 dakika
   ve 513.504 kombinasyon sonunda "hicbir aday kapidan gecmedi" dedi - kapilar
   bozuk degil, orada bulunacak sey yoktu.
2. **`channel_break` bu metrikte en kotu aile** (ort -0.40, sonuncu) ve
   SpotBrent'te -2.98 ile anlamli *negatif*. F40 MFE/MAE asimetrisini olcup
   olumlu bulmustu; ileri getiri tersini soyluyor. Iki metrik celisiyor, yani
   F40'in iddiasi zayifliyor - savunulacak degil, duzeltilecek bir sey. Aile
   `stoch_flip` yerine gecmeye aday olarak konmustu; bu tabloda o iddianin
   dayanagi yok.
3. **Anlamli hucreler ailede degil enstrumanda kumeleniyor**: XAUUSD'de uc ayri
   aile, GER40'ta mtf_pullback, BTCUSD'de burst. Endeks CFD'lerinde
   (US30/NAS100/JPN225) hicbiri. F39'un sonucu yeni aile dahil edildiginde de
   ayakta.

### Nereye bakmali

Girisler her yerde yaziya-tura yakinsa sistemin parasi giristen gelmiyor
demektir. Ayni gunun iki olcumu bunu destekliyor: cikis tarafindaki
mudahaleler devasa (F41 harvest -129 ila -498 R, F44 kademeli kar -103 R),
giris tarafindaki farklar ise gurultu seviyesinde. Kaldirac cikis modeli ve
pozisyon boyutlandirmasinda; "daha iyi aile ara" hatti bu tabloya gore dusuk
beklentili.

## F47 - scalping yanlis yon: bilgi yavas tarafta (olculdu, 31.08)

Operator: "8 ailenin (arsiv) verimini tart, verimsizse kendimiz yazalim; scalping icin
hangi gosterge daha iyiyse ona gecelim."

Birim olarak R veya ATR degil **spread** kullanildi: "ortalama sinyal kac
spread kazandiriyor". Girise 1 spread odendigi icin 1.0 basabas demektir.
Ufuk suepuru, 8 aile (arsiv) x 10 pencere (`cursor/scalp_floor.py`):

| aile | h=1 | h=3 | h=5 | h=10 | h=20 |
|---|---|---|---|---|---|
| mtf_pullback | +0.06 | +0.10 | +0.18 | +0.56 | **+1.06** |
| burst | +0.40 | +0.57 | +0.63 | +0.78 | **+1.32** |
| dual_t3 | +0.10 | +0.28 | +0.24 | -0.26 | +0.03 |
| t3_flip | +0.13 | +0.34 | +0.26 | +0.20 | +0.60 |
| stoch_flip | +0.01 | +0.14 | +0.18 | +0.46 | +0.81 |
| parabolic_flip | +0.22 | +0.25 | +0.35 | +0.45 | +0.93 |
| ichimoku | +0.01 | +0.34 | +0.89 | +0.77 | **+1.22** |
| channel_break | +0.15 | +0.09 | +0.06 | +0.14 | **+1.24** |

**Scalping ufkunda (h=1..5) sekiz ailenin sekizi de maliyetin altinda.** En
iyisi burst, h=1'de 0.40: 1 spread odeyip 0.40 spread kazaniyorsun. Kendi
gostergemizi yazmak bu tabloyu yon olarak degistirmez, cunku sorun secilen
gosterge degil - sinyalin sordugu ufuk.

### Hareket yok degil, YON yok

Ayni pencerelerde medyan mutlak hareket / spread (yonden bagimsiz):

| pencere | h=1 | h=5 | h=20 |
|---|---|---|---|
| SpotBrent_M5 | 2.00 | 5.00 | 11.00 |
| JPN225_M15 | 2.68 | 6.46 | 14.58 |
| BTCUSD_M30 | 2.93 | 6.38 | 13.86 |
| US30_M30 | 6.34 | 15.31 | 36.67 |
| GER40_M30 | 7.30 | 17.59 | 40.00 |
| XAUUSD_M15 | 10.84 | 24.89 | 54.13 |

Tek barda bile piyasa spread'in 2 ila 11 kati hareket ediyor. Yani "enstruman
scalping icin fazla dar" **yanlis**; yer var. Eksik olan yonu bilebilmek.
Maliyet tabani baglayici degil, tahmin gucu baglayici.

### Asil bulgu: egri monoton yukseliyor

Neredeyse her ailede kenar ufukla birlikte buyuyor ve **1.0'i ilk kez h=20'de
geciyor** (burst 1.32, channel_break 1.24, ichimoku 1.22, mtf_pullback 1.06).
Bu ailelerin tasidigi bilgi yavas. Scalping tam olarak ters yon: kisaldikca
sinyal maliyetin daha da altina duesuyor.

Sonuc: "scalping icin daha iyi gosterge" hatti olculu bir kayip bahsi. Kendi
gostergemizi yazacaksak hedef ufuk 20+ bar olmali, 1-5 degil. h=20'deki
paylarin 1.0'in hemen ustunde oldugunu da not etmek gerekir - genis bir marj
degil, ve bu rakamlar stop/trail'siz ham sinyal ortalamalaridir.

## F48 - olcum aparati bozuk: train/test rejim asimetrisi (olculdu, 31.08)

F47'nin isaret ettigi yavas ufuk arastirildi (`cursor/slow_discover.py`):
12 aday ilkel (zaman serisi momentumu, fiyat-ortalama mesafesi, ortalama
egimi, Kaufman verimliligi) x 4 geriye bakis x 3 ufuk, 10 pencere, %60/40
train/test, birim spread. Kitapta duz momentum yoktu; literaturdeki en
dayanikli bulgu olmasina ragmen 8 ailenin (arsiv) hepsi gosterge turevliydi.

### Birinci tur: kontrol grubu adaylari sildi

Kontrolsuz olcumde **`KONTROL_hep_al` her ufukta her adayi yendi**: h=60'ta
+8.39 spread, 10/10 pencere pozitif; en iyi aday +4.95. Yani pencerelerin test
yarisi yukselen bir rejim ve net uzun kalan her kural surukleme topluyor.

Bu tek basina F47'yi de vuruyor: h=20'de "hep al" +2.74 iken maliyeti gectigi
soylenen dort ailenin en iyisi (burst) 1.32'ydi - hepsi taban cizgisinin
**altinda**. "Yavas ufukta bilgi var" sonucu, surukleme kontrol edilmeden
kurulmustu.

### Ikinci tur: surukleme arindirildi, asil sorun ortaya cikti

Her dilimin kendi ortalama ileri hareketi cikarilarak tekrarlandi (`demean`).
Kontroller beklendigi gibi 0.00'a oturdu, yani arindirma calisiyor. Adaylardan
bazilari rastgeleyi (+0.66) ve 1.0 esigini gecti: h=60'ta `mom20` +2.38 (8/10),
`ma_dist20` +1.89 (8/10), `mom200` +2.00 (7/10).

Ama **18 adayin 15'inde train negatif, test pozitif**:

| aday (h=60) | train | test |
|---|---|---|
| ma_dist50 | -0.82 | +2.91 |
| mom20 | -0.51 | +2.38 |
| mom50 | -1.01 | +2.40 |
| ma_dist200 | -1.24 | +2.29 |
| mom200 | -1.49 | +2.00 |

Gercek bir kenar iki yarida da pozitif olurdu. Isaretin yarilar arasinda
sistematik olarak donmesi adaya ozgu degil - **bolunmenin kendisine ait**. Test
yarisi train yarisindan daha egilimli, o yuzden butun trend takipcisi kurallar
orada iyi gorunuyor. Secim skille degil, rejim farkiyla yapiliyor.

### Sonuc: once aparati duzelt

Bu 10 pencere ustunde tek bir %60/40 bolunmesi, kenar ile rejimi ayirt
edemiyor. Bu kanit uzerine yeni bir aile kurmak, olctugu seyi bilmeyen bir
olcume yaslanmak olur.

**F40 ayni yontemi kullaniyordu.** `channel_break`, "on captured window'un
out-of-sample yarisinda asimetri yukseliyor" gerekcesiyle eklenmisti - ayni
bolunme, ayni "test yarisi iyi gorunuyor" mantigi. F46 zaten ileri getiri
t-istatistiginde onu kitabin en kotu ailesi olarak olcmustu; F48 gerekcenin
neden bu kadar kolay boyle bir sey uretebildigini acikliyor.

Yapilmadi ve yapilmamali: bu bulgular uzerine yeni aile yazmak. Yapilmasi
gereken, sinyal arastirmasindan once olcum aparatini duzeltmek - tek bolunme
yerine coklu kat (walk-forward fold), rejim dengesi kontrol edilmis pencereler,
ve her taramada surukleme kontrolu zorunlu.

## F49 - kayiplarin tersine muhendisligi: maliyet kapisi izgaraya sigmiyor (olculdu, 31.08)

298 canli kapanis, net **-41.4 R**. Kazanma %33.9, payoff 1.47. Bu kazanma
oraninda basabas icin payoff 1.95 gerekir; acik payoff tarafinda, F37 ile ayni
teshis.

| kirilim | n | net R |
|---|---|---|
| stop (`sl`) | 159 | **-149.0** |
| trail | 90 | +77.6 |
| flatten | 44 | +27.7 |
| manuel | 5 | +2.3 |

### Baskin ve eyleme donuk bulgu: giristeki spread/ATR

Kitap genelinde monoton:

| spread/ATR | n | net R | ort |
|---|---|---|---|
| 0.00-0.02 | 110 | **+20.1** | +0.18 |
| 0.02-0.05 | 66 | -15.2 | -0.23 |
| 0.05-0.10 | 93 | -34.4 | -0.37 |
| 0.10-0.20 | 29 | -11.9 | -0.41 |

Sembol etkisinin golgesi olabilirdi (JPN225/NAS100 hem pahali hem zararli), o
yuzden **her sembol kendi medyanindan** bolundu (`cursor/cost_confound.py`):

| sembol | n | medyan | ucuz yari | pahali yari | fark |
|---|---|---|---|---|---|
| XAUUSD | 21 | 0.013 | +8.3 R (+0.83) | -5.2 R (-0.47) | +1.30 |
| JPN225 | 59 | 0.069 | -0.3 R (-0.01) | -17.4 R (-0.58) | +0.57 |
| NAS100 | 42 | 0.017 | -4.4 R (-0.21) | -13.2 R (-0.63) | +0.42 |
| US30 | 73 | 0.072 | -5.0 R (-0.14) | -19.9 R (-0.54) | +0.40 |
| GER40 | 29 | 0.031 | -5.6 R (-0.40) | -0.4 R (-0.03) | -0.38 |
| **toplam** | 224 | | **-7.0 R (-0.06)** | **-56.1 R (-0.49)** | +0.43 |

5 sembolun 4'unde ucuz yari kazaniyor, fark +0.43 R/islem. Sayim tek basina
formal anlamlilik vermez (4/5 sansla %19), ama spread bir **maliyettir**:
etkisi mekanik olarak ters yonludur, egri uydurmasi degil. Ucuz yari zaten
basabasa yakin (-7.0 R), pahali yari kitabin kaybinin tamamindan fazlasi.

**Bu kar ettirmez, kanamayi durdurur.** Ucuz yariya inmek islem sayisini
yariya bolerken -56 R'yi siler ve geriye ~-7 R birakir.

### Neden duzelmemis: izgaranin tabani yanlis yerde

`max_spread_atr` bir `OPT_FIELDS` ekseni ve izgarasi
`[0.05, 0.08, 0.12, 0.18, 0.25, 0.4]` - **en dar secenek 0.05**. Sembollerin
kendi medyanlari 0.013-0.072. Yani XAUUSD (0.013), NAS100 (0.017) ve GER40
(0.031) icin izgaranin en siki degeri bile medyanlarinin ustunde; arama
maliyet kapisini paranin oldugu yere kadar **kisamiyor, oraya erisemiyor**.

Canli degerler zaten 0.08-0.25 ve pratikte hic baglamiyor. F40'takiyle ayni
sekil: etki, izgaranin uzanamadigi yerde yasiyor. Fark su ki bu sefer eksen
zaten var, sadece tabani yanlis.

Yapilmadi: izgara `POST /api/opt/params` uzerinden hands-off (400), yani
`0.01/0.02/0.03` basamaklarini eklemek ayri bir karar ve kapi acmayi gerektirir.

### Ana hikaye olmayanlar (kovalanmamali)

* **Geri verme degil.** 1R+ gorup zararla kapanan 34 islem, toplam -22.2 R -
  kaybedenlerin %17'si. F41 zaten hasat etmenin daha pahali oldugunu olctu.
* **Dolum kalitesi degil.** Sinyal kapanisina gore ortalama **+0.037 R**;
  %6'si -0.1R'den kotu. Burada kovalanacak bir sey yok.
* **Kaybedenler hizli oluyor**: medyan 38 dk / 6 bar, kazananlar 144 dk /
  13.4 bar. Stop, giristeki gurultuye gore yakin duruyor olabilir - ama bu
  ayri bir olcum, burada iddia edilmiyor.
* Saat 16:00 en kotu dilim (-14.0 R, n=25). Sembol/rejim karisimi kontrol
  edilmeden eyleme donusturulmemeli (F48).

## F50 - maliyet kapisi tek yone mandalliydi (olculdu + kapi acildi, 01.09)

F49 canli zararin giris `spread/ATR` tarafinda toplandigini olcmustu (ucuz
yari -7.0 R, pahali yari -56.1 R, 5 sembolun 4'unde ayni yon). Spread bir
*maliyet* oldugu icin bu yon mekanik, uydurulmus bir oruntu degil.

Duzeltmenin neden yapilamadigi, duzeltmenin kendisinden daha onemli cikti.
`max_spread_atr` uzerinde **iki ayri mandal** vardi ve ikisi de ayni yone,
gevsemeye bakiyordu:

1. **Izgara tabani.** Eksenin canli degerleri `[0.05 â€¦ 0.4]`, sembol
   medyanlari ise 0.013-0.072. XAUUSD (0.013), NAS100 (0.017) ve GER40
   (0.031) icin aramanin secebilecegi **en dar** deger bile medyanin
   ustundeydi - yani arama kapiyi hic daraltamiyordu, sadece ne kadar
   gevsetecegini seciyordu. `config/defaults.json`'u duzeltmek de yetmiyor:
   `Store.opt_params` eksen basina `{**shipped, **stored}` birlestiriyor,
   saklanan kopya kazaniyor, bir kez kaydedilmis eksen degerlerini sonsuza
   kadar tutuyor.
2. **Kalibrasyon.** `spread_calibration.cap_from_bands` tasarim geregi tek
   yonlu: "yalnizca genisletmek icin guvenilen bir okuma canli kapiyi
   daraltmasin". Nitelik kazanan bir bant mevcut cap'in altinda kalirsa
   `daraltilmadi` deyip geri donuyor.

Ikisi birlikte bir cirit: kapi zamanla yalnizca gevseyebiliyordu, F49'un
zarari olctugu yone dogru. Bu `partial_at_r` ile ayni sekil - inis rampasi
olmayan bir bilis rampasi.

**Yapilan.** `POST /api/opt/params` yalnizca *maliyet* eksenlerine
(`max_spread_atr`, `cost_rank_max`) acildi; izgaranin geri kalani ve
`strategy_grids` kapali kaldi. Iki incelik teste baglandi:

* Yazma **birlestiriyor**. `Store.save_opt_params` butun degeri atiyor
  (`base[key] = value`), yani tek eksenlik bir gonderim tum paylasilan
  izgarayi silip diger uc ekseni sessizce yok ederdi.
* Deger dogrulamasi burada yapiliyor. Bu eksenler giris kapisi oldugu icin
  `invalid_exit_param` onlari hic gormuyor; negatif ya da sonsuz bir tavan
  dogrudan sweep'e girerdi.

Canli eksen `[0.01, 0.02, 0.03, 0.05, 0.08, 0.15]` yapildi - **ayni deger
sayisi**, yani izgara maliyeti degismedi, ama artik para bolgesine uzaniyor.
Gonderilen varsayilan da 4 degerle `[0.01, 0.02, 0.05, 0.10]` oldu.

**Acik kalan.** Kalibrasyon mandali (2) hala yerinde. Onu cevirmek, "kapi bu
sembolde yanlis olan sey degil" gerekcesini bozar; F49 tam tersini olcuyor
ama bunu tek basina yeterli saymiyorum - kalibrasyonun daraltma yonu ayri ve
kendi olcumuyle acilmali. Simdilik arama daraltabiliyor, kalibrasyon
gevsetebiliyor; en azindan iki yon de temsil ediliyor.

**Not.** Bu bir kazanc iddiasi degil, bir *erisim* duzeltmesi. Aramanin daha
dar bir tavani secip secmeyecegini bir sonraki kosu soyleyecek; F49'un ic
orneklem olcumu secilmesi gerektigini soyluyor, kanit bu kadar.

## F51 - bes aile derinlemesi: sembol eslestirme, aile rolÃ¼ (01.09)

`stoch_flip` / `dual_t3` / `t3_flip` emekli. Kalan bes sinyal sekli:

| aile | ne soruyor | olcumde rol |
|---|---|---|
| **burst** | genisleyen bar, extreme kapanis | kitap geneli kazanan (6/7); F47 h=20'de en iyi spread kazanci |
| **mtf_pullback** | HTF trend + ATR geri cekilme | NAS100 en iyi (55R vs burst 51); GER40 F46 t=2.74 |
| **channel_break** | onceki N bar kanal kirilimi | GER40 stoch yerine (34R); JPN225'te 0.4R â€” sembol secimi sart |
| **ichimoku** | TK cross + bulut | F39 en iyi asimetri (7/7) ama arama cikis eksenleriyle nadiren kazanir |
| **parabolic_flip** | SAR flip | arama adayi; matriste nadiren birinci |

**M5 taramasi sonrasi sembol bazli duzeltme** (kÃ¶r burst degil, matris):

| sembol | atanan | neden |
|---|---|---|
| XAUUSD, BTCUSD, SpotBrent | burst | skor lideri |
| NAS100 | **mtf_pullback M30** | 55 > burst 51 |
| JPN225 | **burst M15** | channel_break 0.4R reddedildi |
| US30 | **burst M30** | 41R > channel_break 21 / M5 29 |
| GER40 | channel_break M30 (kuyruk) | stoch_flip yerine olculen en iyi canli aile |

**Performans icin yapilmadi:** aile birlestirme (F42), yeni aile (F48 olcum
aparati supheli), ichimoku'ya HTF/ADX eklemek (bilerek cikis-only arama).

**Yapildi:** sembol x aile eslestirmesi; zayif kazanan (JPN225 channel_break)
duzeltildi; bes aile M5+M15+M30 taramasi tamam.

## F52 - aile budamasi: parabolic_flip emekli, dort cekirdek (01.09)

300 kosuluk matris: sembol basina en iyi skor `burst` 6/7, `mtf_pullback`
1/7 (NAS100), `ichimoku` / `channel_break` / `parabolic_flip` hicbir sembolde
birinci olmadi (channel_break GER40'ta ikinci, 34 vs burst 37).

`parabolic_flip` SAR flip â€” emekli `stoch_flip` ile ayni sinif, sifir galibiyet.
Arama gÃ¼rÃ¼ltÃ¼sÃ¼nÃ¼ kesmek icin cikarildi.

**Canli dort aile:**

| aile | rol |
|---|---|
| **burst** | kitap omurgasi â€” genisleme + extreme kapanis, cost_rank kapisi |
| **mtf_pullback** | endeks geri cekilme â€” NAS100 olcumu |
| **channel_break** | kanal kirilimi â€” GER40 stoch yerine aday |
| **ichimoku** | TK+bulut â€” F39 en iyi asimetri; arama cikis-only, nadiren kazanir ama ucuz (1080 combo) |

Gelir icin kural: **stoch WF skoru kovalama** (overfit); sembol basina bu
dort aileden olculen en iyiyi uygula.

---

### EK22 â€” GECE OTURUMU (03.09 ~15:00â€“24:00, Claude Ã¶lÃ§Ã¼m + Cursor implement)

**A. Weak-symbol kampanyasÄ± â€” "Ã¶lÃ¼" sanÄ±lan semboller yanlÄ±ÅŸ-seans/yanlÄ±ÅŸ-spread-cap'ti**
`holdout_cost.charged_holdout` (apply-gate modeli) ile Ã¶lÃ§Ã¼ldÃ¼:

| sembol | eski | dÃ¼zeltme | charged sonuÃ§ |
|---|---|---|---|
| US30 | msa 0.02 (bayat), seans 08-16 | msa 0.08 + adx_min 20 | +25R n240 PF1.20 (applied) |
| NAS100 | seans yok, msa 0.06 | sess 15:00-21:00 patch | PF1.05â†’1.19, +57â†’+101R |
| JPN225 | burst/M30 gÃ¼ndÃ¼z seans | 7/24 (session filtresi ZARAR veriyordu) | +143.7R n373 PF1.56 |
| SpotBrent | "disabled FINAL", msa 0.25 | msa **0.05** + mtf/M30 + NY 13-21 | +21.8R PF1.16, re-enabled (probe) |
| XAUUSD | mtf/M15 7/24 | dokunulmadÄ± (zaten en iyi) | +246R PF1.31 |
| GER40 | channel_break/M30 adx0 | adx_min 15 (rutin) | +72.8R PF1.34 |

Agg charged score ~609. KalÄ±p: spread'i seans-baÄŸÄ±mlÄ± equity index'ler (US30/NAS100)
â†’ dar pencere kazandÄ±rÄ±r; seanslar arasÄ± trend / 7-24 enstrÃ¼man (JPN225/XAUUSD/BTC)
â†’ tÃ¼m-saat optimal, kÄ±sÄ±tlamak zarar.

**B. AltyapÄ± fix'leri (Cursor, `52eef9e`/`def4682`/`3ce1513`/`58af8a9`)**
- `_beats_incumbent`: charged aday paper incumbent skoruyla yarÄ±ÅŸÄ±yordu (NAS bar 116
  vs gerÃ§ek charged 32) â†’ `holdout_costed` kullan.
- F6 `positive_ratio` binary â†’ `_f6_holdout_waiver` (net_r>40, PFâ‰¥1.15, dd<net).
- Seans pre-step â†’ WFO fan-out ekseni (`_session_search_shortlist`, max 3) + sticky
  (`_session_sticky_eligible` nâ‰¥25+net>0, DD-escape near-tie).
- `max_spread_atr` WFO ekseni (`spread_cap_search_axis` p40/p55/p70 + 0.04 floor).
- `sl_atr_mult` search floor â‰¥0.9 (`floor_sl_atr_search_axis`); shipped grid
  `[0.9,1.2,1.5,2.0,2.5]`.
- adx_min grid `[0,12,18,25]`.
- **holdout_days bug**: force-measure path `lookback_days/segments`=36 yazÄ±yordu â†’
  gerÃ§ek segment span (`bars.time[hi-1]-bars.time[lo]`). Projeksiyon %202â†’%80-108.
- Projeksiyon min-window guard (MIN_PROJ_DAYS 90) + plausibility note + hover.
- min-lot concurrent overshoot 3.5â†’4.5; priority idle-weight 0.55â†’0.9 + expectancy
  Ã—2â†’Ã—3; MIN_COSTED_N 40 (thin costed stamp bloÄŸu).
- pr=None (force restamp'lerde score_consistency yanlÄ±ÅŸ Ã¶lÃ§ekti â†’ None).

**C. 3 realised-P&L bleed kaynaÄŸÄ± (329 otopsi, never-favorable âˆ’95R ayrÄ±ÅŸtÄ±rÄ±ldÄ±)**
1. **PREMATURE STOP** â€” 59 iÅŸlem, âˆ’58.2R. Stop sonrasÄ± 1 saat iÃ§inde fiyat entry'yi
   geÃ§ip â‰¥0.8R toparlÄ±yor (yÃ¶n doÄŸruydu). Sebep: sl_atr_mult < 1.0 (NAS100 0.5,
   JPN225 0.7, XAU 0.5) â€” M30 gÃ¼rÃ¼ltÃ¼sÃ¼ iÃ§inde stop. + US30 (sl 2.0) spread-gate leak.
   Fix: SL search floor â‰¥0.9 (landed); **live NAS/JPN/XAU SL patch = SABAH** (bar-backtest
   sub-1.0 stop'u Ã¶dÃ¼llendiriyor, canlÄ± otopsi Ã§Ã¼rÃ¼tÃ¼yor â€” Ã§eliÅŸki).
2. **SPREAD-GATE leak** â€” 152 iÅŸlem spread_atr>0.04'te âˆ’52.5R (US30 âˆ’24.4, JPN225 âˆ’14.4).
   `max_spread_atr` gate'in ÃœSTÃœNDE giriyor. KÃ¶k: (i) autopsy ATR-basis vs gate ATR
   uyumsuzluÄŸu, (ii) gate ile order_send arasÄ± spread geniÅŸlemesi. Fix: `def4682`
   send-Ã¶ncesi fresh-tick re-check â†’ abort. Restart'ta iner.
3. **CHOP-DEATH entry** â€” 43 iÅŸlem, âˆ’36.7R. GerÃ§ek false-breakout deÄŸil (0/43'Ã¼ sert
   ters gitti), yÃ¶n-belirsiz chop'ta Ã¶ldÃ¼. KÃ¶k: book-wide saat kalitesi â€”
   9h/11h/14h = âˆ’29.5R PF<0.25; 23h EN Ä°YÄ° (PF 4.44). Lever: `blocked_entry_hours`
   (mekanizma + WFO axis `backtest.py:1263` ZATEN VAR, hiÃ§ populate edilmemiÅŸ).
   **LAND:** OPT_FIELDS + `blocked_hour_search_axis` + otopsi `fill_time` seed
   (`7f00f38`/`b3d9070`). CanlÄ± `[]` â€” restart+WFO apply bekliyor.
   **RETRACT 04.09 00:22 (Claude):** per-symbol charged backtest'te 6/6 sembol
   PF<0.8 & nâ‰¥15 aday **yok** â€” book-wide saat sinyali karisim artefakti / 15g
   varyans. Hours WFO kampanyasi yok; kod idle kalabilir (`[]` hep aday).
   JPN[14,15] charged +3.1R â€” temizlik icin [] demek gerileme, **kalir**.

**SABAH KUYRUÄžU (04.09 01:13 gece kapandi):** Premature kampanya bitti â€”
NAS WFO sl0.9 +103.5R; JPN force sl0.8 +148.3R; XAU BIRAK +256R; US30 RED
+25R. Hours #3 RETRACT. Spread send-recheck canlida. SL floor keep
(live+mid). SpotBrent WFO gece kosuyor (NY oncesi). Izle: XAU premature
blip mi; SpotBrent ilk fill; operator EK22 brifing.

---

### EK22-B â€” EXEC PIPELINE EROZYONU + FREEZE (04.09 03:00â€“04:00)

Gece 2. yarÄ±sÄ± Cursor `session_exec` / `msa_exec` / `trail_exec` / `atr_pct_exec` /
`body_exec` otomasyonlarÄ± kurdu â€” her biri charged `_holdout_costed` (son ~%20
pencere) Ã¼zerinde +5R-gated single-dial auto-upgrade. agg last-seg stamp +609 â†’
+872R'ye Ã§Ä±ktÄ± (+263R / +%43).

**Claude 6-slice denetimi (03:21, 03:36):** composed live config'lerin sub-window
robustness'Ä± erozyona uÄŸruyordu:
- JPN225 **2/6** [-17,-5,0,-3,12,151] â€” tÃ¼m kÃ¢r son dilimde. (Not: JPN225 burst/M30
  7/24 muhtemelen HER ZAMAN ~2/6; inherently rejim-baÄŸÄ±mlÄ±. Re-enable +143R
  last-seg'e dayanÄ±yordu = o +151R recent dilim.)
- SpotBrent **3/6** (probe).
- NAS100 6/6â†’**5/6**, GER40 6/6â†’**5/6**, XAUUSD gittikÃ§e back-loaded â€” exec pipeline
  dokunduÄŸu HER sembolde dilim kaybettiriyordu.
- KÃ¶k: `_holdout_costed` last-segment = favorable rejim; her tune config'i o
  pencereye daha Ã§ok fit ediyor. `â‰¥4/6` binary gate uÃ§urumu durdurur, drift'i
  durdurmaz.

**Aksiyon (03:40 Cursor, Claude sign-off):**
1. **FREEZE** â€” `EXEC_PIPELINE_FROZEN=True` + disk flag. TÃ¼m exec propose/tune â†’ None.
2. **Gate harden** (`upgrade_robust`): full-window Î£net_r +â‰¥5R AND slice-wins
   non-regress (6/6â†’5/6 = RED) AND last-2 share rise â‰¤15pp AND â‰¥4/6. Calibrate
   widen path'e de baÄŸlandÄ± (`test_recalibrate_refuses_six_slice_erosion_widen`).
3. **3 revert:** NAS100 seans 7/24â†’15:00-21:00 (â†’ 6/6 +275, 7/24'ten +59R DAHA Ä°YÄ°),
   GER40 trail_step 2.8â†’2.2 (â†’ 6/6 +181), XAUUSD trail_step 2.8â†’2.5 (5/6 +397).
4. JPN225 (2/6) + SpotBrent (3/6) exec-blocked. JPN225 half-weight = operatÃ¶r yellow.

**Post-revert book 6-slice:** NAS100 6/6, GER40 6/6, XAUUSD 5/6, BTCUSD 5/6,
US30 4/6 (marjinal). Full-window robust toplam ~+1279R / 5 saÄŸlam sembol.

**Kural (Claude):** exec pipeline'Ä±n Ä°ÅžÄ° ilk-turdaydÄ± (yanlÄ±ÅŸ seans/msa/sl/family
DÃœZELTME). Mikro-tune 2.+ turlar erozyon Ã¼retiyor. **Unfreeze SADECE:** spesifik
Ã¶lÃ§Ã¼lmÃ¼ÅŸ hedef + MANUEL Ã§alÄ±ÅŸtÄ±r + hardened gate + Claude 6-slice review. Otonom
sÃ¼rekli tune YOK.











### EK23 — OLCUM METODOLOJISI DERSLERI (04.09 11:00–17:10, Claude olcum + Cursor implement)

Gunun somut ciktisi az (2 aday ayakta), ama **olcum yonteminde 4 kalici ders**
cikti. Onlar burada; tek tek kararlar OPTIMIZATIONS ustundeki "Latest" logunda.

**D1 — 6-dilim GEREKLI ama YETERLI DEGIL.**
6-dilim her dilimi *ayni sabit parametrelerle* puanlar: istikrar olcer,
ornekleme-disi parametre SECIMI olcmez. Anchored walk-forward (parametre sadece
fold i-1'e kadarki veriden secilir, fold i'de test edilir) bugun iki adayi
yikti:
```
                     in-sample (6-dilim)     OOS (walk-forward)   param kararlilik
sweep_fade GER40     +33.0R, 18/18'de 6/6    +11.0R               4 set/5 fold OYNAK
SpotBrent t3 4->12   +19.7R, dilim 3/6->4/6  **-30.9R**           ISARET DONUYOR
XAU min_body 0.3->0.1 +50.3R plato           +26.9R               1 set/5 fold KARARLI
```
SpotBrent satiri ogretici: **6-dilimden GECTI** (3/6 -> 4/6 iyilesme gosterdi)
ama OOS isaretini ters cevirdi. Kapiya eklenmesi onerildi: anchored WF OOS > 0
**VE** parametre secimi kararli (<=2 farkli set / 5 fold). Oynak secim = RED,
cunku canlida o parametreyi secebilecegimizin garantisi yok.

**D2 — Motor sembol basina TEK aile secer; birlesik olcum ULASILAMAZ sayidir.**
`range_fade` ve `sweep_fade` icin verdigim tum rakamlar
`mevcut_aile.buy | fade.buy` birlesimiydi (US30 +208R vb.). Ensemble YOK —
WFO tek aile secer. Cursor yakaladi. Standalone olcum:
```
sym      mevcut OOS   standalone sweep OOS   fark
GER40      +173.0R          +63.0R         -110.0
US30        +64.1R          +53.7R          -10.4
XAUUSD     +408.7R          +28.9R         -379.9
NAS100     +248.8R         -27.4R          -276.2
```
4/4 kaybediyor. `sweep_fade`+`range_fade` **dormant kod** kaldi, `opt_strategies`
3'te durdu. Ensemble ayri bir mimari karar — su an HAYIR (standalone kaybi).
**Kural: bir aday, motorun gercekten secebilecegi bicimde olculmeli.**

**D3 — Snapshot verisi sessizce kirli olabilir; dilim skoru bunu gizler.**
7 sembol x 7 kontrol (ince gun / gun-ici bosluk / sifir aralik / cift damga /
haftasonu / spread yok / aykiri getiri):
```
BTCUSD %0.46 | JPN225 %0.14 | NAS100 %0.21 | Brent %0.53 | US30 %0.17 | XAU %0.17
GER40  %23.34   <-- tek problem: 2020-07 oncesi 20987 barda ham spread YOK
```
GER40'in o segmenti gunde 5.5 bar (digerleri 40-47) ve `spread_cost_series`
eksik spread'i **sabit 1.5750 ile ikame ediyor** — maliyet modeli olcum degil
varsayim. Iki bagimsiz yontem ortusuyor:
```
tum snapshot   +180.9R 6/6      <-- ARTIK KULLANILMAZ
temiz pencere  +156.7R 5/6  (rolling zero-rate yontemi)
cop maskesi    +157.6R 5/6  (bar-bazli maske yontemi)
```
Cursor `slice_quality_ok` land etti (miss>%5 | bar-gun<medyan%50 | trades<15;
skor wins/valid; valid<4 RED). Defter geneli dogrulandi, hic RED yok, ama
**GER40 valid=4 ile tam sinirda** -> recapture MEDIUM.
**Yan ders:** kendi "aykiri getiri >12 sigma" filtrem XAUUSD'de **yanlis
etiketledi** — spread'i normal, H-L tutarli, kumelenen barlar gercek
volatiliteydi (altin 2000->5000, 15dk'da %2-4 olagan). Filtreye konmadi.
**Sisman kuyruklu enstrumanda sabit sigma esigi kullanma.**

**D4 — Kapi metrikleri GUC ANALIZINDEN gecmeli (ikisi de gecemedi).**
`give_back` monitor'e indirildi: n=25'te %90 band +/-0.251, ve **cikis
karisimina duyarli** (sl -0.994 / trail +0.165 / flatten +0.533 — tesadufen
daha cok trail cikisi olan bir ornek, hicbir gercek iyilesme olmadan oran
yukseltir).
Sonra **tuttugumuz** `premature_sl`'i ayni testten gecirdim:
```
gercek payda: 334 autopsy -> 176 sl -> 171 zarar -> 135 after_1h dolu
oran 111/135 = 0.822   ("110 baseline" bir SAYI, oran degil)
25 kapanista beklenen payda ~10 satir, %90 band [0.600, 1.000] = +/-0.200
-> "iyilesme" demek icin oranin %27 dusmesi gerekir
AYIRT EDICILIK: sl %80 | trail %58 | flatten %17 | TUM cikislarda taban %60
-> lift sadece 1.33x; olctugunun buyuk kismi siradan intraday volatilite
per-symbol: BTCUSD 4, Brent 3, GOLD-PERP 1 sayilabilir SL -> n=25'te BOS
```
Oneri: **25 = guvenlik kontrol noktasi (felaket tespiti), 100 = kanit kapisi**
(band +/-0.100). Ham oran yerine **lift** (sl orani / ayni donem sl-disi taban).
Per-symbol floor 100'e kadar kapali.
**Kural: bir metrik kapi olmadan once n'deki bandi olculmeli. Ayni standardi
kendi tuttugumuz metrige de uygulamak zorundayiz.**

**Gunun ayakta kalan adaylari (ikisi de grid ekseni olarak, tek deger dayatmadan):**
1. XAU `min_body_ratio` 0.3 -> WFO sectirsin [0.0..0.3] — OOS +26.9R, 5/5 fold
   ayni secim, plato (0.0/0.1/0.2 hepsi 0.3'ten iyi).
2. NAS100 seans 15-21 -> 14-22 — OOS +49.4R, 4/5 fold, DD verimliligi ayni
   (6.23 vs 6.34), arka yukleme +3pp. Sebep: session sticky retune sonrasi
   resetlenmiyordu (03.09 "14-22 dd91" karari artik var olmayan config'e ait).
   Cursor `sticky=False` + `reevaluate_sessions_after_primary_flip` land etti —
   **ileriye donuk**, NAS100 icin tek seferlik re-eval kuyrukta.

**Reddedilenler:** range_fade (4 sembol), sweep_fade (standalone 4/4 kayip),
SpotBrent t3 (OOS -30.9R), GER40 atr_pct_min (OOS +0.4R gurultu),
TF hizlandirma (7/7 sembolde R/gun duser), UK100/FRA40 (spread ekonomisi),
SpotBrent silme (maxDD degismiyor, slot kitligi yok 1.19/~6), ensemble (D2).

**Duzeltilen eski cerceve:** "6 slota 7 sembol sikisiyor" YANLIS. Beklenen es
zamanli pozisyon **1.19 / ~6 slot** — kapasitenin %20'si. UK100/FRA40 reddi
spread ekonomisiyle ayakta, kapasite gerekcesi dustu.

**D5 — `cooldown_sec` aranabilir gorunur ama yapisal olarak olculemez (Claude 18:34).**
M15/M30 non-scalp'ta backtest `_cooldown_bars` degeri 0 veya 1 bara kirpar,
sonra `resume_signal = … + cooldown_bars - 1` ile gecikmeyi sifirlar; canli
`_cooldown_for` da bar-alti (XAU 120sn / BTC 900sn). Ayni-bar cift-fill
gardiyani — verim kaldiraci degil. Grid'e ekleme; eklesen arama fark olcemez.
`reverse_on_signal` olculdu ve RED (NAS −204R). Non-exit challenger kalmadi.

### EK24 — SIZINTI DEFTERI (04.09 22:00, operator talebi: "hepsini izleyin, tanimlayin, cozun")

Uc sizinti sinifini ayri ayri olctuk ama tek yerde tanimli degillerdi, bu yuzden
her tick'te bastan tartisiliyordu. Bu bolum **kalici tanim**: her sizintinin
olculen maliyeti, durumu, ve onu izleyen monitor. Yeni bir sizinti bulununca
buraya satir eklenir; kapananın durumu guncellenir.

| # | Sizinti | Olculen maliyet | Durum | Monitor |
|---|---|---|---|---|
| 1 | **Kovalama** (sinyal seviyesinin otesinde giris = "gec acilan") | **-49.2R** | ACIK. Gate **YASAK** (`AGENTS.md:179`, Claude 18:45: curve-fit, dogrulanamaz). Sebep aramasi negatif: gecikme/spread/volatilite hicbiri aciklamiyor (gecikme medyani 903sn = tam bir bar, execution patolojisi yok). | `CHASE_R_LOG` (log-only, gate yok) — n>=50 OOS sonra yeniden bak |
| 2 | **Pozisyon yigma** (sembol basina >1 ticket) | **-15.2R** | **COZULDU.** `risk.can_open` `cap=1` sabit (commit 45decd0, 28.08 07:17; canli ~31.08). Kanit: JPN225 08-28'de 8 ayri ticket ayni anda, tek episod -4.65R. Post-kampanya tum sembollerde max 1. | `concurrent_stack_watch` (>1 ticket -> WAKE) |
| 3 | **"Karliyken trail kimildamadi, zararla kapandi"** | **-6.8R gerceklesen** (ulasilan tepe +29.3R) | **TASARIM, ariza degil.** n=14/338 (%4.1). Bunun 3'u intrabar (fitil esigi gecti, bar altina kapandi -3.0R); 8'inde stop oynadi ve yine zarar (-1.5R). Trail esigi gecilince stop 7/7 sembolde **%100** oynuyor. Geometri 12/12 birlesik taramada optimum; sikilastirmak hem getiriyi hem DUSUSU kotulestiriyor. | trail audit (`sl` vs `original_sl`) |
| 4 | **Engellenen giris** ("kacan islemler") | karsi-olgusal, otopsiden olculemez | 1640 engelleme: **spread %88.7 (1454)**, bar_doldu %10.1 (165), acildi 11, seans_disi 10. `max_spread_atr` kampanyada sembol basina WFO ile ayarlandi — bu bir kusur degil, ayarlanmis kapi. | `entry_blocks` / `entry_blocks_cumulative` |
| 5 | **JPN225 + NAS100 artik acik** | charged %90 bandin **ustunde** | ACIK. Temiz hucre (kovalama+yigma yok) 5/7 sembolde charged ile uyumlu; sadece bu ikisinde degil. JPN225 icin on hipotez: charged beklentisi **rejim-bagimli** (net'in %87'si son dilimde; spread 8pt sabit vs yukselen ATR kapiyi ancak son donemde acti). NAS100 icin hipotez **YOK**. | — (post-25 sinyal-eslesmesi, sadece NAS100) |
| 6 | **Land-vs-canli gecikme** (kod land etti, surec almadi) | -4.65R (tek olcülen episod) | **COZULDU** + monitor kuyrukta. 28.08'de `cap=1` commit'i ~3 gun canliya girmedi; o pencerede duzeltilmis hata islemeye devam etti. | `stale_runtime_watch` (boot manifest vs disk mtime) |

**Onemli okuma notu (3 numara):** operatorun en cok hissettigi sizinti bu, ama
**hissedilen** ile **gerceklesen** ayni degil. 14 islem toplam +29.3R tepeye
ulasip -6.8R ile kapandi: ekranda 36R'lik bir geri verme goruluyor, ama fiilen
kaybedilen **-6.8R** (~$100). Cunku o islemlerin cogu zaten kucuk zararla
bitecekti. Trail'i sikilastirarak bu 6.8R'yi kurtarmaya calismak, 12/12 olculdu:
**hem getiriyi hem dususu kotulestiriyor.**

**Ayristirma (bugun):** kovalama VAR + yigma VAR/YOK hucrelerinin toplami -50R
defterin tamami; **kovalama YOK + yigma YOK hucresi +0.016 R/islem POZITIF**
(n=130). Yani sistem, sinyal seviyesinden girip yigmadiginda calisiyor.

### EK24-B — SIZINTI 7: SHAKEOUT SL TABANI (04.09 23:20, ajan denetimi + Claude dogrulamasi)

**Defterin en buyuk tek kalemi bu, ve backtest'te HIC temsil edilmiyor.**

`risk.shakeout_sl_atr_mult` (risk.py:70): bir sembolde son 10 kapanisin 3'u
original-SL zarariysa, **bir sonraki girisin sert stopu** `max(base,
min(base*1.5, 2.0))` ile genisletiliyor. Lot o genisletilmis mesafeye gore
boyutlanıyor (engine.py:2983-3013) ve `original_risk` donuyor — ama
`trail_start_atr` / `trail_step_atr` **aranan degerlerde kaliyor**.
Fonksiyonun kendi docstring'i bunu soyluyor: *"the next entry's hard stop may
not match the searched trio"*.

`backtest.py` now calls the same ``shakeout_sl_atr_mult`` on each entry
(lazy import; BT ``stop`` mapped to autopsy ``sl``; empty close list at
simulate start = apply ``since_ts`` reset). Trail still stays at searched
values. **Landed 04.09 17:38** — next WFO searches with the guard.

**min-lot (Claude 00:18):** mechanical truth that R is fill-time risk distance
stands, but on the live autopsy record winner/loser implied-1R is **0.982x**
(no systematic loser inflation). R×median vs cash ~**2.3%** — today’s R
ledger is dollar-valid; within-symbol 1R span 9.8–32× is variance only.

**Olculen maliyet** (ayni snapshot, ayni pencere, sadece sl_atr_mult shakeout
degerine cekilmis):
```
sembol      base -> shakeout    E base   E shakeout   fark R/islem
NAS100        0.9 -> 1.35        0.266      0.076       -0.190
JPN225        0.8 -> 1.20        0.477      0.299       -0.178
BTCUSD        1.2 -> 1.80        0.488      0.384       -0.104
XAUUSD        0.7 -> 1.05        0.268      0.179       -0.089
GER40         1.5 -> 2.00        0.196      0.122       -0.074
SpotBrent     1.0 -> 1.50        0.200      0.186       -0.014
US30          2.0 (zaten tavan)     —          —         0.000
defter agirlikli: -0.10 .. -0.12 R/islem = **acigin ~%40'i**
```

**IKI BAGIMSIZ YONTEMIN ORTUSMESI (bu bulgunun en guclu yani):**
Claude'un canli otopsilerden yaptigi "temiz hucre vs charged" testi ile
ajanin koddan+snapshot'tan yaptigi shakeout olcumu **ayni iki sembolu ayni
sirayla** isaret ediyor:
```
sembol      shakeout cezasi     temiz-hucre charged testi
US30            0.000           1.00x  BIREBIR
SpotBrent      -0.014           bant icinde
GER40          -0.074           bant icinde
XAUUSD         -0.089           bant icinde
JPN225         -0.178           **BANT DISI**
NAS100         -0.190           **BANT DISI**
```
Tam sira korelasyonu. **EK24'teki 5 numarali acik sizintinin (JPN225+NAS100)
nedeni budur.**

**KOVALAMA HAKKINDA DUZELTME:** ajan kovalamanin *fiyat* maliyetini defter
ortalamasi **~0.03 R** olarak olcuyor. Claude'un buldugu "kovalayan islemler
-0.55 R/islem" ise korelasyon. Ikisi celismiyor: **kovalama bir ISARETCI,
neden degil.** Bu, `AGENTS.md:179`'un curve-fit hukmunu guclendiriyor —
kovalamaya gate koymak semptomu tedavi etmek olurdu.

**Diger olculen farklar (ajan):** yeniden-giris zamanlamasi (replay cikis
barinin sinyalini atiyor, canli aliyor: -0.03 R/islem, NAS100'de islem sayisi
+%28); boyut agirliklandirma + slot tayinlamasi (`edge_scale` 0.60-1.17,
+0.127 esit-agirlikli ama canli boyut-agirlikli — per-trade R'de gorunmez);
min-lot sabitleme (tek fill'de hedeflenen riskin 4.5 katina kadar, R kolonunda
**gorunmez**, sadece dolarda); gunluk-zarar flatten (canli flatten orani
replay'in **3-5 kati**).

**VERI HIJYENI UYARISI:** GER40 trim'i (90k -> 69k bar) ayni config'de E'yi
0.260'tan 0.196'ya dusuruyor (**-%24**). Yani +0.127 referans cizgisi tek
basina pencere secimiyle onlarca yuzde oynuyor — acigin son 0.05 R'sini bir
seye atfetmeden once bu bilinmeli.

**SIRADAKI OLCUM (yapilmadi):** shakeout'un ne KAZANDIRDIGI olculmedi. Ajan
beklenti maliyetini olctu, ama mekanizma muhtemelen kuyruk riskini/dususu
azaltmak icin konuldu. **Kaldirmayi onermeden once "koruyor mu" olculmeli** —
aksi halde beklentiyi duzeltip dususu bozabiliriz.

### EK24-C — SHAKEOUT KORUYOR MU? EVET, 6/6 (04.09 23:50, eksik yarim tamamlandi)

EK24-B shakeout'un **maliyetini** olcmustu (-0.10..-0.12 R/islem). Neyi
**kazandirdigi** olculmemisti — ve bir dusus guard'ini beklenti dustu diye
kaldirmak $700 hesapta tam tersi olurdu. Olctum:

```
sym         dd degisim   netR/DD degisim   en kotu dilim   hukum
BTCUSD         -10.9         +2.26            +24.3        KORUYOR
GER40          -13.1         +1.26             +9.1        KORUYOR
JPN225         -10.2         -1.05             +9.5        KORUYOR
NAS100         -13.6         -0.87             +1.7        KORUYOR
SpotBrent      -22.7         +1.58             +5.5        KORUYOR
XAUUSD         -24.7         -0.83            +26.7        KORUYOR
```
**6/6 sembolde max_dd_r DUSUYOR** (-10.2 .. -24.7R) ve **en kotu dilim
IYILESIYOR** (+1.7 .. +26.7R). SpotBrent'te net_r bile artiyor (+38.4 -> +47.3).

Risk-ayarli (netR/DD) ikiye ayriliyor:
```
shakeout KAZANDIRIYOR : BTCUSD +2.26 | SpotBrent +1.58 | GER40 +1.26
shakeout KAYBETTIRIYOR: JPN225 -1.05 | NAS100 -0.87   | XAUUSD -0.83
```

**DOGRU CERCEVE (EK24-B'yi duzeltir):** shakeout bir hata degil, **modellenmemis
ama bilincli bir risk takasi**. Sorun var olmasi degil, **WFO'nun var oldugunu
BILMEDEN parametre secmesi**: aranan sl/trail ucusu, shakeout'un hic ateslenmedigi
bir dunya icin optimal — sonra shakeout atesleniyor ve trail o genislemis stopla
uyumsuz kaliyor.

**Ucuncu bagimsiz dogrulama:** US30 zaten 2.0 tavaninda, yani shakeout onda HIC
ateslenmiyor — ve US30, canli/charged testinde **birebir tutan (1.00x)** tek
sembol. Uc ayri yontem (otopsi temiz-hucre, kod denetimi, koruma olcumu) ayni
yeri gosteriyor.

**ONERI: kaldirma, MODELLE.** `backtest.simulate` icine kosullu shakeout
(son 10 kapanista 3 original-SL zarari -> sonraki girisin sl_dist'i
`max(base, min(base*1.5, 2.0))`) eklenirse WFO parametreleri **guard ile
birlikte** secer. Beklenen sonuc: BTC/Brent/GER40'ta muhtemelen daha genis bir
taban sl secilir; JPN/NAS/XAU'da trail ayarlari degisir. Kaldirmak ise 6/6
sembolde dususu buyutur — $700 hesapta %15 gunluk fren varken yanlis yon.

### EK24-D — R OLCUMLERI DOLARI SADIK ANLATIYOR (05.09 00:18, dogrulama)

Ajan denetimi "min-lot bozulmasi `r_realised`'da gorunmez, dolar hasarini
eksik gosterir" uyarisi yapmisti. Bugunku her cikarim R cinsinden oldugu icin
test edildi (n=299, `|profit / r_realised|`):
```
KAZANANLAR  n= 87   ima 1R medyan $13.16
KAYBEDENLER n=212   ima 1R medyan $12.92     oran 0.982x -> ASIMETRI YOK
gercek dolar toplami $-898.40 vs R'in ima ettigi $-919.31  -> fark %2.3
```
**Buyutulmus fill'ler sistematik olarak kaybeden DEGIL.** Uyari mekanik olarak
dogru ama kayitta iz birakmamis. **Sizinti defteri, 5/7 temiz-hucre uyumu ve
shakeout koruma olcumu dolar ifadesi olarak gecerli.**

**Ayri gozlem (eksen degil):** sembol ici ima edilen 1R dagilimi cok genis —
GER40 32.0x, NAS100 24.6x, XAUUSD 24.5x (min-max). Sermaye salinimi ~5x
oldugu icin kalan carpan `edge_scale` (0.6-2.2), min-lot sabitleme (1.5x,
es zamanli dialda 4.5x) ve marj tavanindan geliyor. Beklentiyi bozmuyor
(asimetri yok) ama dolar **varyansini** buyutuyor; %15 gunluk fren varken
varyans frene degme olasiligini artirir. Kayitta, aksiyon yok.

### EK24-E — XAU min_body 0.1 ADAYI OLDU (05.09 01:14, model sonrasi yeniden olcum)

BT shakeout modeli land ettikten sonra, otomatik-uygulama kuyrugundaki **tek**
aday yeniden olculdu:
```
                  ESKI (shakeout'suz)      YENI (shakeout modelli)
OOS fark               +26.9R                    **-14.9R**
secim kararliligi   5/5 fold 0.1 secti     **3 farkli set / 5 fold**
tam pencere en iyi     0.1 (+516.3R)         **0.3 = CANLI (+284.4R)**
```
`min_body` girisi filtreliyor, shakeout kaybeden serilerden sonra stopu
genisletiyor — **ayni islemler uzerinde etkilesiyorlar**, bagimsiz olculemez.
Eski dunyadaki "plato" model eklenince dagildi.

**Aksiyon: `unfreeze_actions` XAU body auto-apply KALDIRILDI. Canli 0.3 dogru.**
Kural: **model oncesi olculen hicbir sayi karar tabani olamaz** — keep-line'lar
ve `upgrade_robust` esikleri dahil.

**04.09 gununun aday bilancosu: 11 oneri, 11 RED.**
range_fade / sweep_fade / SpotBrent t3 / GER40 atr_pct_min / NAS100 seans 14-22 /
TF hizlandirma / UK100+FRA40 / SpotBrent silme / ensemble / kovalama gate /
XAU min_body. Canliya giden hicbir sey yok. Bu basarisizlik degil: **sistemin
mevcut konfigurasyonu denenen her alternatiften iyi cikti**, ve kapilar
(6-dilim + anchored WF + secim kararliligi + veri kalitesi + guc analizi)
calisti. Geriye kalan gercek is konfigurasyon degil altyapi: kovalama log'u
ve JPN/NAS artik acigi (siradaki aday burst `_cost_series` imputation farki).

### EK24-F — KOVALAMA ORNEKLEM-DISI TESTTEN GECEMEDI (05.09 04:30)

EK24'te 1 numarali sizinti "kovalama, -49.2R, defterin en buyuk acik kalemi"
diye yazilmisti. O rakam **in-sample**. `AGENTS.md:179` zaten curve-fit
demisti ama gerekcesi walk-forward'di (backtest kovalama uretmiyor).
**Canli kaydin kronolojik bolunmesi** ayri bir testtir ve hic yapilmamisti.
Yapildi:
```
egitim (ilk 160 islem, esik p60 = +0.0299 SADECE egitimden secildi):
  kovalayan n=64 ortR -0.621 | kovalamayan n=96 ortR +0.091 | FARK **-0.712**
test (son 107 islem, ayni esik):
  kovalayan n=37 ortR -0.563 | kovalamayan n=70 ortR -0.310 | FARK **-0.253**
```
Etki **%65 kuculuyor**. Permutasyon kontrolu (test kumesinde etiketler
rastgele karistirilarak): fark dagilimi p5 -0.302 / p50 -0.009 / p95 +0.301,
gozlenen -0.253 icin **p = 0.088 — %5'te ANLAMLI DEGIL**.

**Sonuc: yon korunuyor ama buyukluk cokuyor ve rastgele etiketlemeden
ayirt edilemiyor.** `AGENTS.md:179`'un curve-fit hukmu, yapilmamis olan
testle de dogrulandi. Ajanin "kovalama fiyat maliyeti defter ortalamasi
sadece ~0.03R" olcumuyle de tutarli: korelasyon buyuk olcude **secilim**.

**EK24 GUNCELLEME:** 1 numarali kalem "-49.2R, en buyuk acik" -> **"in-sample
-49.2R; OOS'ta anlamli degil (p=0.088). Isaretci, neden degil."**
`CHASE_R_LOG` log-only devam etsin (ileri veri zarar vermez) ama **oncelik
listesinden dusuruldu**.

**DURUST SONUC:** acik, iddia ettigimden **daha az aciklanmis** durumda.
Elimizde kesin olan: yigma (-15.2R, cozuldu) ve shakeout (JPN %25 / NAS %10,
modellendi). Kalan -50R'nin buyuk kismi **hala atfedilmemis**. Bu bir geri
adim degil, yanlis bir kesinligin kaldirilmasi.

### EK24-G — **CANLI-vs-CHARGED KARSILASTIRMALARIMIZ YANLIS CETVEL KULLANMIS** (05.09 06:10)

Bugun boyunca "canli sembol X, charged beklentisini tutturuyor mu" diye
karsilastirdik. **Karsilastirilan islemlerin cogu, karsilastirildiklari
config'e ait degil.**

`fill_time - signal_bar_time` her islemin **hangi zaman diliminde** kostugunu
veriyor (`signal_bar_time` = son kapali barin ACILIS damgasi, `engine.py:3386`).
Dagilim uc modlu ve temiz: 5dk 72 islem / 15dk 73 / 30dk 94.
```
sym        canli TF   M5   M15   M30   ESLESME    onceki hukmumuz
NAS100        M30      0     0    47     %100     bant USTU  -> GECERLI
BTCUSD        M30      0     0     4     %100     n<5        -> GECERLI
XAUUSD        M15      0    34     1      %97     bant ICI   -> GECERLI
GER40         M30      0     1    29      %91     bant ICI   -> GECERLI
US30          M30     48     6    17      %23     "1.00x BIREBIR" -> **TESADUF**
JPN225        M30     20    36     6      %10     bant USTU  -> **CETVEL HATASI**
SpotBrent     M30      5     6     1       %8     bant ICI   -> **ANLAMSIZ**
```
JPN225'in "temiz hucre"si 15 M5 + 14 M15 + **0 M30**. M15 donemi `stoch_flip`
ailesiyle kosmus — 01.09'da emekli edilen, `_FAMILIES`'te artik **bulunmayan**
bir aile. Mevcut `burst`/M30 config'i 09-03 23:52'de uygulanmis ve **tek bir
islem** uretmis.

**TF-eslesmeli cetvelle JPN225 acigi +0.302 -> +0.064** — yayinladigimiz
+/-0.3 bootstrap bandinin rahatca icinde. **JPN225'te aranacak bir sey yok.**

**Bagimsiz ucuncu kontrol:** mevcut config, canli takvim penceresinde
(554 M30 bar) replay edildiginde **17 islem, -0.010 R/islem** veriyor — tam
pencere beklentisi olan +0.142 degil. Yani +0.142 **555 gunluk holdout'un
ozelligi**, canli takvimde ulasilabilir bir sayi degil. GER40 trim'inde
gordugumuz pencere-duyarliligi (E %24 oynadi) genel bir olguymus.

**GECERLI KALAN:** NAS100 acigi **gercek** (%100 TF-eslesmeli) — ve
yeniden-giris mekanizmasi (islemlerin %33'unde cikis-barinda sinyal) onu
aciklayan tarafta. Yigma (-15.2R) ve shakeout de gercek.

**KURAL (kalici):** canli-vs-charged karsilastirmasi yapmadan once otopsiler
**config donemine gore kovalanmali**. Zaman dilimi `fill_time -
signal_bar_time`'dan bedava geliyor; sinirlar `opt_runs.applied=1`
tarihlerinden. `shakeout_sl_atr_mult` bunu zaten `since_ts=cfg.opt_updated_at`
ile yapiyor — **acik denetimi yapmiyordu.**

**Iptal edilen hukumler:** 22:44 "5/7 sembol charged'i tutturuyor, sadece
JPN225+NAS100 tutturmuyor" -> **iki yonde de yanlis.** Karsilastirilabilir
dort sembolden ucu tutuyor, biri (NAS100) tutmuyor. US30/JPN225/SpotBrent
satirlari **veri yetersizliginden hukumsuz**.

### EK25 — UYGULANANLAR (05.09 06:10–07:00, operator "tam yetki, emin olduklarini uygula")

MOLA sonrasi, Cursor yokken Claude tarafindan uygulandi. **Canli islem/pozisyon/
risk parametresi degismedi; motor yeniden baslatilmadi.**

**1. `backtest.simulate` yeniden-giris modeli** (`backtest.py`)
`resume_signal = max(exit_bar, ...)` -> `max(exit_bar - 1, ...)`. Cikis barinin
kendi kapanisinda slot bostur, canli o barin sinyalini alir (sonraki acilista
dolar); replay atiyordu.
*Iki bagimsiz dogrulama:* (a) replay'de cikis-bari/sinyal cakismasi — NAS100
islemlerin %33'u, BTCUSD %20, digerleri %3-5; (b) **otopside** ardisik ciftlerin
%13.5'inde sonraki islemin sinyal bari onceki cikisi iceriyor (US30 %23,
JPN225 %18, GER40 %13) — yani canli bunu **gercekten yapiyor**.
*Sonuc:* NAS100 1880->2305 islem (+%22.6, ajan +%28 demisti), BTCUSD 1194->1366
(+%14.4, ajan +%14), digerleri +%1.4..2.4. Cooldown kolu **dokunulmadi** ve
calisiyor (cooldown=3600 -> NAS100 2305->1933).
*Yon:* charged beklentileri DUSER (NAS100 E 0.115->0.100, BTCUSD 0.281->0.229).
Bu dogru yon: replay canliya yaklasti. **Tum keep-line'lar yeniden okunmali.**

**2. M5 emekli edildi** (operator karari, olcum EK'lerde)
```
models.py     SymbolConfig.timeframe varsayilani "M5" -> "M30"   (sessiz varsayilan)
models.py     TIMEFRAMES / READABLE_TIMEFRAMES / SEARCH_TIMEFRAMES -> ["M15","M30"]
models.py     is_swing seconds map, M5 satiri
models.py     03.09 M5 gerekcesi yorumu -> bugunku olcumle degistirildi
mt5client.py  bilinmeyen TF fallback: TIMEFRAME_M5 -> TIMEFRAME_M30 (WARN korundu)
mt5client.py  timeframe_seconds fallback 300 -> 1800; TF tablolari
holdout_cost.py docstring ornegi
DB            settings.opt_params.timeframes ['M5','M15','M30'] -> ['M15','M30']
              (store WIDENING yapiyor: kod duzenlemesi TEK BASINA yetmezdi)
              yedek: .bridge/OPT_PARAMS_TIMEFRAMES_BACKUP.json
snapshot      8 adet *_M5.npz -> data/holdout_bars/_retired_M5/ (SILINMEDI)
```
*Dogrulama:* tum moduller import oluyor; `SymbolConfig().timeframe` = M30;
`timeframe_seconds("BILINMEYEN")` = 1800; `strategy_allows_timeframe(...,"M5",{})`
= **False**; **7/7 canli sembol giris gecidinden geciyor** (hepsi M15/M30).
Efektif `store.opt_params()["timeframes"]` = `['M15','M30']` — widening'den
sonra da M5 yok.

**Not — test araci yok:** `pytest`/`ruff` motorun yorumlayicisinda kurulu degil
ve acik pozisyon varken oraya paket kurmak gereksiz risk. Yerine degisen satiri
dogrudan sinayan hedefli bir dogrulama yazildi (islem sayisi yonu + cooldown
kolu + import + canli gecit). **Bu pytest degildir; Cursor dondugunde suite
kosulmali.**

**YAPILMAYANLAR (bilincli):** WFO apply gate WIRE (sira: n=25 safety once —
Cursor'la mutabik kalinan siralama), chase_r/stale_runtime ARM (surec restart
gerektiriyor, **iki acik pozisyon var**), HOLD_ONLY remeasure (once bu iki
degisiklikle referanslar yeniden olculmeli).

### EK25-B — H1 YENIDEN OLCULDU, DUZELTILMIS REPLAY ILE (05.09 07:30)

Operator "1h olcum yapsana" dedi. 03:34'teki ilk olcumun iki kusuru vardi:
(a) **yeniden-giris modeli land etmeden once** kosmustu, yani karsilastirdigi
M30 tarafi artik yok; (b) `cfg.timeframe`'i M30 birakip cache'e 3600sn
veriyordu. Ikisi de duzeltildi (`uses_swing_exits('burst','M30')=True`, yani
H1 de swing tarafinda olurdu — bu alan yaniltmiyor).
```
sym        TF     net_r      n    R/gun       E   maliyet  maxDD  dilim
BTCUSD     M30   +313.0   1366   +0.163  +0.229   0.0456   21.9   6/6
           H1    +108.2    815   +0.056  +0.133   0.0390   48.4   4/6
GER40      M30   +134.0   1017   +0.085  +0.132   0.0157   20.4   6/6
           H1     +47.4    573   +0.030  +0.083   0.0124   20.8   5/6
JPN225     M30    +84.8    500   +0.044  +0.170   0.0450   25.0   3/6
           H1     -75.8    562   -0.039  **-0.135**  0.0453  82.5   1/6
NAS100     M30   +230.3   2305   +0.117  +0.100   0.0212   45.1   6/6
           H1     +97.5   1529   +0.049  +0.064   0.0166   38.0   4/6
SpotBrent  M30    +38.3    446   +0.018  +0.086   0.0251   20.5   3/6
           H1      +3.9    515   +0.002  +0.008   0.0249   29.6   1/6
US30       M30    +81.8    940   +0.042  +0.087   0.0342   57.0   4/6
           H1     +17.3    419   +0.009  +0.041   0.0235   43.8   3/6
DEFTER R/gun:  M30 **+0.469**   H1 **+0.108**   fark **-0.361**
```
**H1, M30'un gunluk hizinin %23'unu veriyor — 4.3 KAT geride.**

**Ilk olcumde gormedigim:** H1 sadece R/gun'de degil, **islem basi beklentide,
dilim saglamliginda VE DUSUSTE de kotu.** BTCUSD maxDD 21.9 -> **48.4**,
JPN225 25.0 -> **82.5** — daha az islemle daha derin dusus. Dilim her sembolde
geriliyor (6/6->4/6, 3/6->1/6...). JPN225'in beklentisi **artiya cikmak yerine
negatife donuyor** (+0.170 -> -0.135).

Yani H1 **maliyet disinda her eksende** kaybediyor. Maliyet avantaji gercek
(-%14..-31) ama `models.py`'nin dedigi cikiyor: *"Throughput is the whole point
at this account size, so the cheaper bar loses."*

**Sentetik sinir (durustce):** H1 barlari M30 ciftlerinden uretildi; OHLC
birlesimi tam, spread ciftin max'i. Gercek broker H1 barlarinin spread kolonu
biraz farkli okunabilir. Ama **4.3 katlik bir R/gun farkini** spread nuansi
ceviremez. **H1 icin bar cekmeye deger yok. KARAR: ALINMIYOR.**

### EK25-C — GUNCEL KEEP-LINE'LAR + HOLD_ONLY KAPANDI (05.09 08:00)

Iki model degisikligi (shakeout tabani + cikis-bari yeniden-girisi) land ettigi
icin bugunden onceki **tum charged referanslari bayat**. Yeniden olculdu.

**DEFTERIN GUNCEL KEEP-LINE'LARI** (bundan sonraki her karar bunlara gore):
```
sym        aile           TF     net_r      n        E    R/gun   maxDD  dilim     OOS
BTCUSD     burst          M30   +313.0   1366   +0.229   +0.163    21.9    6/6  +254.4
GER40      channel_break  M30   +134.0   1017   +0.132   +0.085    20.4    6/6  +131.8
JPN225     burst          M30    +84.8    500   +0.170   +0.044    25.0    3/6   +73.7
NAS100     burst          M30   +230.3   2305   +0.100   +0.117    45.1    6/6  +221.5
SpotBrent  mtf_pullback   M30    +38.3    446   +0.086   +0.018    20.5    3/6   +36.8
US30       channel_break  M30    +81.8    940   +0.087   +0.042    57.0    4/6   +72.9
XAUUSD     mtf_pullback   M15   +273.7   3938   +0.070   +0.278   122.4    4/6  +262.4
DEFTER TOPLAM R/gun                                      **+0.747**
```
Defter beklentisi **+0.967 -> +0.747 (-%23)**. Bu bir kotulesme degil:
replay canliya yaklasti, yani onceki rakam **fazla iyimserdi**.
Dikkat: XAUUSD maxDD **122.4** — defterin acik ara en buyugu, ve ayni zamanda
en buyuk katkisi (+0.278 R/gun). Risk orada yogunlasiyor.

**HOLD_ONLY KUYRUGU KAPANDI — ikisi de RED, canli degerler kaliyor:**
```
GER40 trail_step_atr (challenger 2.8):
   2.2 CANLI +134.0R  6/6  netR/DD 6.55   <-- her eksende EN IYI
   2.5       +127.0   6/6  6.14
   2.8       +121.4   6/6  5.62
   3.2        +93.1   4/6  3.05
   OOS: canli +131.8 vs secilen +118.0 -> **-13.8R**   RED

XAUUSD breakeven_at_r (holdout 1.2/1.0 seviyordu):
   1.0  +305.3R  4/6      1.5 CANLI +273.7R  4/6
   1.2  +275.6R  4/6      2.0       +313.3R  5/6
   tam pencerede 1.0 ve 2.0 CANLIYI GECIYOR — ama OOS'ta secim
   fold'lar arasi 1.0 <-> 2.0 arasinda gidip geliyor (2 set / 5 fold)
   OOS: canli +262.4 vs secilen +241.0 -> **-21.4R**   RED
```
XAUUSD satiri bugunku klasik desen: **tam pencerede daha iyi gorunen bir deger,
fold'lar uzerinde kararli secilemiyor** — XAU min_body'de, SpotBrent t3'te ve
sweep_fade'de gordugumuz imza. Kapi yine tuttu.

**SONUC: canliya aday KALMADI.** auto-on-unfreeze bos, HOLD_ONLY bos.
Sistemin mevcut konfigurasyonu, bugun denenen **14 alternatiften** iyi cikti.

### EK25-D — TRAIL'IN SON EKSENI KAPANDI: `trail_mode` (05.09 08:30)

Izgara denetimi `trail_mode`/`trail_lookback` icin *"structure/hybrid hic
aranmadi, tum semboller atr/5"* demisti; "trail ekseni kapali" mutabakati
yuzunden bakilmamisti. Operator dogrudan sordu, olculdu.

Ozellik **uctan uca calisiyor**: `backtest.py:567-570` swing seviyelerini
onceden hesapliyor, `exits.overlay_stop:62-67` uyguluyor, canlida
`engine.py:4431` ayni sey. Yani aranmamis olmasi, bagli olmamasindan degil.
```
7 sembol x 7 aday (atr/5 CANLI, structure 5/10/20, hybrid 5/10/20)
sonuc: atr/5 her sembolde kazaniyor ya da fiilen berabere.
ham kriteri gecen UC aday, hepsi IZOLE TEPE:
  XAUUSD structure/20  OOS  +4.0R   ama structure/5 -72R, structure/10 -12R
  GER40  hybrid/20     OOS  +3.0R   ama hybrid/5 -100R, hybrid/10 -69R
  Brent  hybrid/10     OOS  +1.7R   ama hybrid/5 -14.7R, hybrid/20 -2.3R
```
Uc aday da kaybeden bir komsulukta tek nokta — bugun 14 kez reddedilen
curve-fit imzasi. Ve buyuklukleri (+1.7..+4.0R) reddedilenlerin yaninda
(-13.8R, -21.4R) gurultu bandinda kaliyor.

**KARAR: `trail_mode=atr`, `trail_lookback=5` — degisiklik YOK.**

**Trail artik TAMAMEN olculdu:** geometri (birlesik sl x step, 12/12),
`trail_start` (Cursor), `trail_step` (komsu taramalari + HOLD_ONLY),
`breakeven_at_r` (BTCUSD kapandi, XAU HOLD_ONLY RED), ve simdi
`trail_mode`/`trail_lookback`. **Her eksende canli deger kazandi.**
Operatorun "trail calismiyor" endisesine verilecek son cevap: mekanizma
%100 atesliyor (19:02 denetimi), geometri optimum, ve simdi modu da optimum.
Geri verme, kosucuyu tutmanin bedeli — olculdu, alternatifi yok.

### EK25-E — "ZARARLI ISLEMLERI INCELE": ANALIZ EDILECEK VERI YOK (05.09 09:00)

Operator zararli ve kacan islemlerin taranmasini istedi. Once metodolojik kural
uygulandi (EK24-G): **canli kayit config donemine gore kovalandi**
(`symbols.opt_updated_at` sonrasi).
```
sym        config uygulandi   toplam otopsi   MEVCUT CONFIG   W   L    netR      net$
BTCUSD     09-04 00:21                    6               1   1   0   +4.08   +17.53
GER40      09-04 00:40                   46               1   0   1   -1.11    -8.08
JPN225     09-03 23:52                   76               1   0   1   -1.00   -10.46
NAS100     09-04 00:21                   60               3   0   3   -2.04   -28.37
SpotBrent  09-04 00:58                   16               0   -   -    0.00     0.00
US30       09-04 00:14                   92               0   -   -    0.00     0.00
XAUUSD     09-04 02:22                   41               5   0   5   -4.11   -31.61
TOPLAM                                  341              11   1  10   -4.19   -60.99
```
**341 otopsinin 330'u artik var olmayan konfigurasyonlara ait.** Onlari
incelemek, calistirmadigimiz bir sistemi incelemek olur.

**Mevcut konfigurasyonlarin tum canli kaydi 11 islem.** Ve o 11 islem
istatistiksel olarak siradan:
```
tarihsel kazanma orani 0.329 -> P(<=1 kazanan / 11) = **%7.9**  (normal bant)
n=11 icin toplam R'in %90 bootstrap bandi: [-7.7, +6.0]
gozlenen -4.2R  ->  BANT ICINDE = GURULTU
```
US30 ve SpotBrent **hic islem uretmedi** (beklenen 0.47 ve 0.24 islem/gun,
~30 saatte sifir olagan).

**SONUC: zararli islemlerde aksiyon alinacak bir sey YOK** — bakmadigim icin
degil, **11 islem bir bulguyu tasiyamadigi icin.** Bunu boyle yazmak, kucuk
bir orneklemden hikaye uretmekten iyidir.

**Gozlenen tek desen (aksiyon degil):** 4 islem anlamli MFE'ye ulasip geri
verdi (XAU 03:30 mfe 2.11 -> -1.03; NAS 19:50 mfe 2.11 -> -0.00; XAU 04:02
1.70 -> -0.05; XAU 13:33 1.18 -> -0.98). Birlikte +7.1R tepeye ulasip -2.06R
kapandilar. Bu, operatorun surekli fark ettigi geri-verme sinifi — ve trail'in
**her ekseni** olculdu (geometri 12/12, mod 7/7, start, step, breakeven):
hepsinde canli deger kazandi. Sikilastirmanin olculen bedeli bu 2.06R'den
buyuk.

**"Kacan islemler":** engellemelerin %89'u spread kapisi ve `max_spread_atr`
sembol basina WFO ile ayarli. Karsi-olgusal otopsiden olculemez; backtest'te
msa sweep'i zaten yapildi. Yeni bir sey yok.

### EK25-F — "BTC DISINDAKILERI GUN SONU/HAFTA SONU TASIMA" (05.09 09:40, operator sorusu)

Operator: *"btc disindakileri gun sonu hatta ozellikle Cuma tasimak
istemiyorum, gun sonu hafta sonu riski gerekli mi?"* Uc ayri kanit toplandi.

**1) HAFTA SONU RISKI ZATEN SIFIR — tasarim geregi**
`sessions.weekend_closed` (sessions.py:101) **acik bir takvim kurali**:
`manage_positions()` hafta sonu her sembolu zorla duzlestiriyor,
`trade_all_hours` bunu gecersiz kilmiyor. `WEEKEND_OPEN_GROUPS = {"crypto"}` —
**sadece BTCUSD acik kaliyor**, ve kripto zaten hafta sonu bosluk vermiyor.
Backtest de ayni sekilde modelliyor (`flatten_mask`, backtest.py:306-308).
```
REPLAY, tam gecmis: haftasonu tasiyan islem
  GER40 0/1017 | JPN225 0/500 | NAS100 0/2305 | Brent 0/446 | US30 0/940 | XAU 0/3938
  BTCUSD 2/1366 (%0.1) — kripto, bosluk yok
CANLI: 340 islemin 0'i haftasonu tasimis
```
Ayrica bir Cuma acigi **zaten bulunup kapatilmis**: kod yorumu
(sessions.py:22) *"Measured 24.08: GER40 BUY 363660277, Friday 22:30 UTC bar,
Monday 03:15 UTC fill, -1R"* — restart sonrasi bayat Cuma damgasinin
Pazartesi dolmasi. Kapatildi.

**2) GECE TASIMA VAR — VE KAR ORADA**
```
sym        gece tasiyan    %     gece ortR   AYNI GUN ortR
BTCUSD          571     41.8%      +1.440       -0.641
NAS100          556     24.1%      +2.174       -0.560
JPN225          109     21.8%      +2.347       -0.437
GER40           214     21.0%      +1.806       -0.314
XAUUSD          466     11.8%      +2.372       -0.240
US30             80      8.5%      +3.289       -0.211
SpotBrent       187     41.9%      +0.868       -0.479
```
**7/7 sembolde ayni gun kapananlar ZARARDA, gece tasiyanlar KARDA.**
Mekanizma: gun sonunda hala acik olan islem, stopunu yememis olandir —
kosucudur. Gun sonu kapatmak **tam da kazandiran islemleri keser.**

**3) OLCUM: gun sonu kapatma ne yapar?**
```
day_end_flatten_min:      0        6dk       15dk
6 sembol toplami:     +842.9R   +842.9R   +825.6R
```
6dk **hicbir sey yapmiyor** (M30 barindan kucuk, hicbir bar bandin icine
tam girmiyor). Isirdigi tek yer XAUUSD 15dk: **+273.7 -> +256.4 (-17.3R)**.

**4) CANLI KAYITTA BOSLUK HASARI YOK**
182 sl cikisi: ort -0.950R, **medyan tam -1.000R**. -1.05R'den kotu sadece 2
(%1.1), -1.5R'den kotu 1, -2.0R'den kotu **0**. Stoplar seviyesinden doluyor.

**KARAR: DEGISIKLIK YOK.** Endise yerinde ama **zaten karsilanmis**: hafta
sonu maruziyeti tasarim geregi sifir. Gun sonu kapatma ise ya etkisiz ya
zararli, cunku kesecegi sey defterin kar getiren tarafi.

**Durust cekince:** backtest stopun stop seviyesinden doldugunu varsayar, yani
gercek bir hafta sonu socunu **fiyatlayamaz**. Ama maruziyet yapisal olarak
sifir oldugu icin bu cekince isirmiyor — tasimadigimiz pozisyonda bosluk
riski olmaz.

### EK25-G — M5 KALINTI TEMIZLIGI: TUM DEPO (05.09 10:20, operator "iz kalmasin")

06:40'taki ilk temizlik `micofx/*.py` + DB ile sinirliydi. Operator tum depoyu
(TR/EN, web, API) istedi. Tarandi ve **uc GERCEK yeniden-bulastirma yolu**
bulundu:
```
1. micofx/web/static/app.js:54   OPT_TF_OPTIONS = ["M5","M15","M30"]
   -> PANEL M5'i hala secenek sunuyordu. Secilse `strategy_allows_timeframe`
      reddeder -> **sessizce olu sembol**. Duzeltildi + neden yorumu eklendi.
2. config/defaults.json group_presets.{forex,index,commodity}.timeframe = "M5"
   -> YENI SEMBOL SABLONU. Forex/endeks/emtia eklenirse M5'te acilir ve
      giris kapisi reddeder. **M30 yapildi.** (crypto/stock zaten M15.)
3. config/defaults.json optimizer.timeframes = ["M5","M15","M30"]
   -> shipped liste. Taze kurulumda M5 aranirdi. **["M15","M30"] yapildi.**
```
**Widening kontrolu (kritik):** `Store._widen_grid_lists` sadece
`strategy_grids`, `grid` ve `strategy_timeframes`'e uygulaniyor —
**`timeframes`'e DEGIL**. Dogrulandi: shipped M5 varken bile efektif deger
`['M15','M30']` idi. Yani 04:02'deki uyarim bu alan icin gecerli degilmis;
yine de shipped liste tutarlilik icin temizlendi.

**AGENTS.md:226** yanlis bilgi tasiyordu: *"M5 stays legal to trade (SpotBrent
stoch/M5) and a one-off POST /api/opt/run can still name it."* Artik yanlis —
kural dosyasi bugun bir yanlis karara zaten yol acti (03.09 M5 gerekcesi).
Guncellendi: M5 hicbir yerde yasal degil, adlandirmak olu sembol uretir,
geri acmak icin **hem** `models.TIMEFRAMES` **hem** `opt_params.timeframes`
gerekiyor.

**Arsivlenen (silinmedi):** `.bridge/_retired_m5_scripts/` — 5 dosya
(`a2_restricted_wfo.py`, `a2_wait_btc.py`, `m5_grid_and_wfo.py`,
`reenable_costs_and_wfo.py`, `m5_capture.json`). Bunlar API'ye
`{"timeframes":["M5","M15","M30"]}` POST eden tek seferlik scriptlerdi —
calistirilsalar M5'i **geri yazarlardi.**

**Dokunulmayanlar (bilincli):** `DEVAM.md`, `OPTIMIZATIONS.md`, `cursor/*`,
kod icindeki tarihsel yorumlar. Bunlar kurumsal hafiza; silmek
`models.py`'nin bizzat uyardigi seyi yapmak olurdu.

**Son dogrulama:** `micofx/`, `config/`, `scripts/` altinda canli M5 izi
**0 adet**. 7/7 canli sembol giris kapisindan geciyor. Yeni sembol sablonlari
M30/M15.

### EK26 — CUMA GIRIS BLOGU + PIYASA-KAPALI LOG KISMASI (05.09 11:00, UYGULANDI)

**Operatorun tespiti dogruydu ve benim 09:40'taki cevabim eksikti.** "Hafta sonu
maruziyeti yapisal olarak sifir" demistim; replay'de 0 hafta sonu tasima
gordugum icin. Ama replay `flatten_mask` ile **her zaman basariyla** duzlestirir;
canli, kapanmis bir venue'ye emir gondermek zorunda.

**CANLI OLAY (04.09):**
```
23:30:04  XAUUSD SELL 0.01 @ 4429.73  <- Cuma, kapanisa 30 dk kala ACILDI
23:59:48  Pozisyon kapatilamadi #325114801 (10018 = MARKET CLOSED)
02:28:10  ...hala deniyor: 2.5 saatte 4409 ozdes ERROR satiri
```
Uc kusur: (a) kapanisa 30 dk kala giris acildi; (b) `weekend_closed`
`day >= 6`'ya bakiyor, yani **Cumartesi** — piyasa Cuma kapandigi icin kural
ancak is isten gectikten sonra atesleyebiliyor; (c) 10018'de geri cekilme yok.

**OLCUM — bedeli var mi? YOK, tersine kazanc:**
```
Cuma kapanisina yakin acilan islemler (BTC haric, 9146 islem icinde):
  son 1 saat:  22 islem  **-0.5R**
  son 2 saat:  36 islem  **-4.5R**
  son 3 saat:  70 islem  **-7.5R**
yogunlasma: XAUUSD (18/32/53) ve JPN225 — yani `use_sessions=False` olan ikisi.
Seansi olanlar (GER40/NAS100/US30) zaten 0.
```
Her pencerede negatif -> **engellemek hem riski hem zarari kesiyor, takas yok.**

**UYGULANAN 1 — `sessions.WEEKEND_WINDDOWN_MIN = 120`**
`_block_weekend_winddown`: Cuma son 120 dk'da **yeni giris reddedilir**, acik
pozisyona **dokunulmaz**. Kritik dogrulama: `should_flatten` state kapaliyken
False donuyor, yani bu blok bir kosucuyu **kesemez** — ki gece tutulan islemler
7/7 sembolde karin geldigi taraf. Kripto muaf (`WEEKEND_OPEN_GROUPS`), tipki
`weekend_closed`'daki gibi. 120 dk **R'ye degil TUTUS SURESINE** gore secildi:
XAUUSD ortalama ~2 saat tutuyor, yani bandin kenarinda acilan bir islem tipik
omrunu yasayip kapanabilir. Yeni tally anahtari: `hafta_sonu_oncesi`.

**UYGULANAN 2 — `mt5client` piyasa-kapali log kismasi**
Retry **degismedi** (kapanamayan pozisyon gercek risktir, denemeye devam
etmeli). Degisen: 10018 artik ERROR degil, ticket basina **15 dakikada bir
WARN**. 4409 satir -> hafta sonu boyunca ~10 satir.

**DOGRULAMA (7 canli sembol x haftanin 5 ani):**
```
sembol      Sal 10:00   Cum 15:00   Cum 21:59   Cum 22:00      Cmt 02:00
BTCUSD           ACIK        ACIK        ACIK        ACIK           ACIK  <- kripto muaf
JPN225           ACIK  saat kapali       ACIK  hafta sonu o  hafta sonu k
XAUUSD           ACIK        ACIK        ACIK  hafta sonu o  hafta sonu k
GER40/NAS/US30/Brent: Cum 22:00'de zaten `seans disi` — etkilenmedi
```
Normal saatler degismedi; kural sadece 24 saat calisan iki sembolde, Cuma'nin
son iki saatinde isiriyor.

**NOT — diskte, canlida DEGIL:** motor calisiyor ve degisiklikler bir sonraki
restart'ta yururluge girer. Su an hafta sonu ve **sikismis bir XAUUSD ticket'i
var** (~$9 maruziyet); restart yapilmadi. Pazartesi acilista pozisyon
kapandiginda ve defter duzlestiginde restart, bugunku tum degisiklikleri
(shakeout modeli, yeniden-giris, M5 kaldirma, bu iki duzeltme) canliya alir.

---

## EK27 — Olu kod / bayat konfig taramasi (05.09, ajan + elle dogrulama)

Operator: "Turkce Ingilizce api Web heyetten m5 tara olu bayat emekli
kalintilari temizle. ayni sekizde genel taramayida yap." ve "oneriye gerek
yok yetki sende hangisi dogru ise teyit et.uygula".

Bir arka plan ajani tum depoyu taradi; her bulgu **uygulanmadan once elle
dogrulandi**. Ajanin kod okuma bulgulari dogru cikti.

### A. Dirilme yollari (emekli bir sey geri gelebilirdi) — KAPATILDI

**A1. `config/defaults.json` gonderilen sembol kitabi ESKI kitapti.**
10 sembol listeliyordu: dordu emekli (FRA40, UK100, US2000, US500) ve
**BTCUSD hic yoktu**. `POST /api/symbols-seed?overwrite=true` ->
`store.replace_with_defaults()` once **tum portfoyu siler**, sonra tam olarak
bu listeyi kurar. Yani panelde "varsayilana don", canli kripto satirini silip
olcumle emekli edilmis bir portfoyu geri kurardi. (Kurulan satirlar `enabled`
False geliyor — islem acmazlardi — ama kitaba, panele ve tarama kumesine
girerlerdi.)

Duzeltme: kitap **canli 7 sembole** cekildi. Magic'ler uydurulmadi, canli
DB'den okundu (besi zaten ayniydi; BTCUSD 990116 canli satirdan). Seanslar ve
`max_spread_atr` de canlidan alindi — boylece "varsayilana don" eski yer
tutuculara degil **bugunku olculmus pencerelere** doner (GER40 gonderilen
10:00-22:55 iken canli 08:00-15:59 idi).

Dogrulama: 7/7 sembolde isim, magic, seans, spread canli kitapla birebir;
sembol blogu disinda **tek satir bile degismedi**.

**A2. `.bridge/OPT_PARAMS_TIMEFRAMES_BACKUP.json`** icinde su yaziyordu:
`"reason": "M5 retirement 05.09; restore by writing this list back"` — yani
iki ajanin da okudugu dizinde duran, **olculmus bir karari geri alma
talimati**. Hicbir kod okumuyor; tek zarar yolu bir ajanin ona uymasiydi.
Tarihsel kayda cevrildi, "DO NOT WRITE BACK" olarak isaretlendi.

**A3. `.bridge/_retired_m5_scripts/`** — arsivlenmisti ama hala **calisir
`.py`** dosyalariydi ve canli API'ye yaziyorlardi
(`m5_grid_and_wfo.py:40` -> `POST /api/opt/params {"timeframes":["M5",...]}`;
ayni liste 3 dosyada daha). `.py.txt` olarak yeniden adlandirildi + README.

**A4. `micofx/holdout_cost.py capture_book()` kendi TF listesini
dogrulamiyordu.** Tek HTTP cagiran dogruluyordu, dogrudan cagri dogrulamiyordu.
"M5" verilse `timeframe_const` M30'a duser ve **M30 barlari
`holdout_bars/<SYM>_M5.npz` dosyasina** yazilirdi: adi icerigiyle celisen bir
snapshot, tek WARN satirinin arkasinda — sonraki her olcum onu gercek M5
sanardi. Bugun kimse o yola girmiyordu; **giremesin diye** reddediliyor artik.
Yeni test: `test_capture_book_refuses_a_retired_bar.py` (reddi *ve* gecerli
barin reddedilmedigini birlikte pinliyor).

**A5. Dirilme AGENTS.md'nin dedigi kadar pahali degil.** Belge "hem
`models.TIMEFRAMES` hem saklanan `opt_params.timeframes` gerekir" diyordu.
Yanlis: `store.opt_params()` gonderilen listeyi her okumada birlestiriyor, yani
`models.TIMEFRAMES` + `config/defaults.json` **yetiyor**. Iki dosyalik bir
degisiklik. AGENTS.md duzeltildi; her iki dosya da canli risk yuzeyi sayilmali.

### B. Hicbir seyi korumayan bekciler — ONARILDI

**B1. `test_ichimoku_is_gone` kalici olarak KIRMIZIYDI.** `len(STRATEGIES) == 3`
pinliyordu; 04.09'da sweep_fade/range_fade **uykuda** eklenince 5 oldu ve
bekci, ilgisiz bir nedenle her zaman kirmizi kaldi. **Her zaman basarisiz olan
bir dirilme bekcisi hicbir sey korumaz**: ichimoku gercekten geri gelse yeni
bir hata cikmazdi. Ayni pin 3 dosyada daha vardi. Hepsi **sayimdan isim
kumesine** cevrildi — yeni bir aile eklemek hala tripwire'i tetikliyor.

**B2. `tests/retired_lexicon.py`'de M5 YOKTU.** Bu demet uzerine kurulu her
iki dilli dokuman/panel bekcisi M5'e karsi kordu. Tek satir eklendi ve
**hemen gercek bayat metin yakaladi** (asagida C).

**B3. Bos calisan iki test.**
`uses_swing_exits(...) is (tf != "M5")` — M5 gidince bu ifade **her zaman
True**, yani ayrim yapmayi birakti ama gecmeye devam etti; canli bir ikilem
gibi gorunup hicbir sey test etmiyordu. Ve `_tables()` regex'i `"M5":` ariyordu
— tablolarda M5 kalmayinca **hicbir sey eslesmedi**, iki modul icin de test
bos gecti. (Bunu `test_at_least_one_table_was_actually_found` yakaladi; o
refakatci tam bunun icin var ve korundu.)

**B4. `test_auto_opt_is_gone.py`: `assert tf in ("M5","M15","M30")`** — hem
simdi geciyordu hem M5 geri gelse geciyor olacakti. Izin listesi degil
**tripwire** olacak sekilde ters cevrildi.

**B5. Iki test M5 icin AKTIF ARGUMAN tasiyordu**
(`test_search_includes_m5_by_default` — docstring'inde "GER40 M5 burst +74 >
live channel/M30 +42"; `test_shipped_timeframes_append` — birlestirme yolunu
bir *garanti* olarak belgeliyordu). Ikisi de silinmedi, **hukmu ters cevrildi**:
kapsadiklari mekanizma gercek ve degerli. Ikincisine yeni bir guvenlik yarisi
eklendi: saklanan blob'daki emekli bar da **geri gelmemeli** (dogrulandi).

**B6. `docs/` HICBIR bekci tarafindan taranmiyordu** — ve depodaki en bayat
dosya oradaydi. `docs/KULLANIM.md` hala "Guncel portfoy (10 sembol)" deyip
dort emekli ismi sayiyor, BTCUSD'yi hic anmiyor ve aranabilir barlari
"M5/M15/M30/H1" diye sunuyordu. Duzeltildi **ve** dosya artik digerleri gibi
taraniyor.

**B7. Iki bekci ayni kurali farkli uyguluyordu** — biri sadece Turkce +
ayni satir (`"emekli" in line`), digeri iki dilli +-2 satir penceresi. Bu yuzden
AGENTS.md'nin "**M5 was RETIRED**" satiri birinden geciyor digerinden
kaliyordu. Tek kurala (pencere surumu) birlestirildi.

**B8. Yeni: emekli SEMBOL sozlugu yoktu** (`RETIRED_SYMBOLS`) — A1'in fark
edilmeden bayatlamasinin sebebi buydu. Eklendi + gonderilen kitabi tarayan
bekci. (Test fixture'lari FRA40/UK100'u sentetik isim olarak kullanmakta
serbest kaliyor; sadece `config/defaults.json` taraniyor.)

### C. Artik dogru olmayan ifadeler — DUZELTILDI

- `optimizer.py:3172` + `web/app.py:1119` hata metni: "scalp yalnizca M5; uzun
  TF swing ailelerine ait". `STRATEGY_TIMEFRAMES` bos — **hicbir aile TF
  kisitli degil** — ve M5 yok. Metin gercege cevrildi.
- `models.uses_swing_exits` artik **her yasal girdide sabit True** (tablo
  `{"M15":900,"M30":1800}`, esik `>=900`). `optimizer.py:1253`'teki
  `if uses_swing_exits(...)` yanlis dalini hic almiyor; `SWING_GRID_OVERLAY`
  kosulsuz uygulaniyor. Bu **kasitli** (kalan her bar swing bari) ama
  fonksiyonun su an sabit oldugu docstring'de acikca yaziyor artik.
- `SCALP_STRATEGIES` yorumu: "yalnizca hizli barlarda anlamli". M5 gidince
  burst sadece M15/M30 kosuyor — yani yorumun kendi onculu artik "burst
  olmamali" diyor. Burst **olculmus sonuclarla** duruyor, o argumanla degil.
- `AGENTS.md:230`: "produces a dead symbol, not an M5 run" — **yanlis**.
  Dogrulandi: optimizer istekten dusuruyor, gecerli bir sey kalmazsa
  `"Aranabilir zaman dilimi yok"` ile bastan reddediyor.
- `field_help.js` (operatorun okudugu panel metni): "6 x M5 = M30" -> "2 x M15
  = M30"; ve `max_bars` yardimindaki "90.000 M5 bari BTCUSD icin 314 gun,
  FRA40 icin 771 gun" — emekli bar + emekli sembol. **Olculerek** degistirildi:
  90.000 bar XAUUSD M15'te ~983 gun, BTCUSD M30'unda ~1925 gun.
- `MASTER_PROMPT.md`: `burst (M5-native scalp)` basligi, `US30 M5` olcumu,
  "M5 is judged on days" satiri.
- `store.py` seed yorumu: "eighteen symbols ... mtf_pullback/M5".

### D. Olu / bayat artefaktlar

- `scripts/income_dev_loop.py`: `FAM = frozenset({... "ichimoku" ...})` — hicbir
  yerde okunmuyordu **ve** 02.09'da emekli olmus bir aileyi adlandiriyordu.
  Silindi.
- `data/holdout_bars/`: `GOLD_PERP_M30.npz` (emekli sembol) ve
  `GER40_M30.npz.bak` -> `_arsiv/`. Once dogrulandi: dizin hicbir yerde
  `glob/iterdir/listdir` ile taranmiyor, yani tasima etkisiz.
- `.bridge/SYMBOL_QUEUE_UK100_FRA40.json`: karari `SIMDI_HAYIR` ama `after`
  listesi **artik saglanamayacak** bir on kosul iceriyordu
  ("Cursor: bar snapshot M5/M15/M30") — yani kuyruk kalici olarak
  cozulemez hale gelmisti. O madde cikarildi, dosya bayat olarak isaretlendi.

### E. Ajanin bir iddiasi duzeltildi

Ajan `partial_at_r`, `partial_close_frac`, `harvest_at_r`, `harvest_step_atr`,
`min_atr_ratio` alanlarinin **okunmayan kalinti olmadigini** gosterdi —
`engine.py:4446-4531`, `backtest.py:659-690` vb. hepsini okuyor; sadece
varsayilanlari 0/kapali. Gercekten okunmayanlar: `max_positions`, `max_lot`,
`max_margin_pct`, `max_total_positions`. Bu, benim onceki brief'imdeki bir
hatayi duzeltiyor.

### F. Kasitli olarak DOKUNULMAYAN

- `GET /api/symbols/lot-mode-check` — cagrisi yok, ama teshis amacli ve salt
  okunur. Operatorun elle vurabilecegi bir uc noktayi kaldirmak, birakmaktan
  daha riskli. Duruyor.
- **Uykudaki ailelerin olu hesabi**: `strategy.py _common` her aile icin stoch
  `k`/`d` hesapliyor ama canli uc aileden hicbiri `k`'yi **okumuyor** (sadece
  `_range_fade` okuyor). `_p_fields_reachable` sozdizimsel taradigi icin
  `opt_fields_read` yine de `rsi_length, stoch_length, smooth_k, smooth_d`
  donduruyor — yani **optimizer canli kitapta tek bir girisi degistiremeyecek
  dort kadrani hala tariyor**. Butce israfi, ve bir "kazanan" sirf bunlarla
  incumbent'i gecebilir. Grid degisikligi bir **olcum karari**; sadece
  isaretleniyor.
- `.pytest_tmp/` (416 giris, kilitli .db), kok dizindeki `nul`, `cookies.txt`,
  `_poll_opt.out/.err` vb. — operatorun verisi, silinmedi.

### G. Sonuc

```
pytest (tam paket):   98 basarisiz -> 66 basarisiz  (3128 gecti)
ruff (dokunulan):     temiz
```

Kalan 66'nin hicbiri bu calismadan gelmiyor. Ikisi geldi ve **ikisi de
duzeltildi**: `test_seed_starts_disabled` XAUUSD seansini "02:00" diye
literal pinliyordu (artik sablonu okuyor — testin niyeti zaten oydu), ve
`test_capture_book_timeframes_override` A4'un yeni reddine takildi (gecerli
bara cevrildi). Geriye kalanlar iki onceden var olan kume: **bayat test
sahteleri** (~27; `'_Store' object has no attribute 'system'` gibi — uretim
arayuzuyle uyusmayan fake'ler) ve **ilgisiz davranissal kayma** (~40). Ikisi de
bu taramanin kapsami disinda.

Ayrica: `ruff`'ta iki onceden var olan import-sirasi hatasi duruyor
(`scripts/apply_trail_step_queue.py`, `tests/test_note_fill_repairs_poisoned_sl.py`) —
dokundugum hicbir dosyada degil, o yuzden birakildi.

**NOT — diskte, canlida DEGIL.** EK26'daki gibi: motor calisiyor, hafta sonu ve
sikismis XAUUSD ticket'i duruyor, restart yapilmadi.

---

## EK28 — Perp adaylari: GOLD-PERP / BRENTOIL-PERP / NAS100-PERP (05.09)

Operator: *"gold-perp xau alternatif / brentoil-perp spotbrent alternatif /
nas100-perp nas100 alternatif bunlara bir baksana perpler 7*24"*.

### 0. Once bir duzeltme (kendi ilk okumam yanlisti)

Ilk olcumum "GOLD-PERP 7/24 degil, hafta sonu payi %1.2" dedi. **Yanlis** —
tum pencere 2019-2026 ve o pencerenin %96'si hafta ici-only. Yila boldugumde:

```
GOLD-PERP hafta sonu bar payi
  2019..2025   %0.0     <- broker hafta sonu islem acmiyordu
  2026-06      %15.7    <- 2026-06-20'de BASLIYOR
  2026-07      %25.8
  2026-08      %32.3
  20.06 sonrasi ortalama: %30.1   (kripto referansi %28.6 = tam 7/24)
```

**Operator hakli: GOLD-PERP bugun gercekten 7/24.** Ama bu tam da olcum
problemini yaratiyor: 7/24 davranisinin sadece **10 haftalik** gecmisi var;
+257R gibi eski rakamlar %96 hafta ici veriden geliyor, yani o edge bir
**hafta ici edge'i**. Ikisi ayri raporlanir, biri digerinin yerine gecmez.
(`sessions.py`'deki "%9.9" rakami da bu yuzden dogruydu — kisa pencerede
olculmustu.)

### 1. GOLD-PERP, XAUUSD'nin ALTERNATIFI (ekleme degil) — dogrulandi

```
fiyat seviyesi korelasyonu   +1.0000
ortalama |kotasyon farki|     2.29   (ortalama fiyat 2909.5 -> %0.08)
bar-bar getiri korelasyonu   +0.58   <- M30 zamanlama gurultusu, varlik farki DEGIL
```
Ayni varlik. Ikisini birden acmak cesitlendirme degil, **tek altin pozisyonunu
iki bagimsiz sinyale ciftlemek** olurdu (kitapta capraz-sembol maruziyet
tavani yok). Yani soru dogru cerceveyle: **takas**.

**Takas olcumu** (ikisi de mtf_pullback — XAUUSD canli ailesi de o):
```
                 aile           TF    net_r      n    R/gun       E   mal/n  maxDD  dilim     OOS
XAUUSD canli     mtf_pullback   M15  +273.7   3938  +0.278  +0.070  0.0331  122.4   4/6  +262.4
GOLD-PERP mtf    mtf_pullback   M30  +167.0   2455  +0.085  +0.068  0.0098   35.5   5/6  +138.5

ORTAK takvim penceresinde:
  XAUUSD      +259.0  n 3931  R/gun +0.264  maxDD 122.4
  GOLD-PERP   +112.8  n 1252  R/gun +0.113  maxDD  26.4
```

Ve asil belirleyici — **7/24 doneminin kendisinde** (2026-06-20 sonrasi):
```
  XAUUSD      +77.7R / 193 islem    (hafta sonu YOK)
  GOLD-PERP   +10.6R /  81 islem    (hafta sonu VAR)
```
GOLD-PERP hafta sonu avantajinin oldugu pencerede bile XAUUSD'nin gerisinde.

**HUKUM: takas RED. XAUUSD kalir.** R/gun 2.5-3 kat farkli ve hafta sonu
kapsamasi bu farki kapatmiyor.

**Dururken kaydedilmeli — GOLD-PERP'in gercek bir ustunlugu var:**
risk-ayarli olarak daha iyi (netR/maxDD **4.70** vs XAUUSD **2.24**) ve islem
basi maliyeti **3.4 kat ucuz** (0.0098 vs 0.0331). Verimde degil, puruzsuzlukte
kazaniyor. Kitap R/gun ile buyudugu icin bu takasi kazandirmiyor; ama hesap
buyuyup drawdown kisiti baglayici olursa **bu sayi tekrar bakilmali**.

**Not:** GOLD-PERP 03.09'da edge yuzunden degil, **$248 hesapta min-lot alti
kaldigi icin** silinmisti (her sinyal SKIP). Hesap bugun $691. O kisit muhtemelen
artik baglamiyor — ama snapshot `volume_min` TASIMIYOR (sadece point/tick_size/
tick_value), yani bunu diskten hesaplayamam. Brokera sorulacak tek soru; ve
takas zaten reddedildigi icin **bloke edici degil**.

### 2. Asil test: perp'in EKLEYECEGI saatlerde edge var mi?

Bir perp yalnizca **saat** satin alir. O saatlerde edge yoksa, yeni enstruman
maliyet ve gurultuden baska bir sey eklemez. Bu, tek bir yeni bar indirmeden
ucunu birden cevap veriyor: her sembolun **kendi** snapshot'i zaten tum
saatleri tasiyor; canli config, seans kapisi ACIK vs KAPALI.

```
sembol      aile           canli seans | seansli net_r    n  R/gun | 24s net_r    n  R/gun | fark R/gun
NAS100      burst          15:00-21:00 |       +230.3  2305 +0.117 |    +195.3  2934 +0.099 |    -0.018
SpotBrent   mtf_pullback   14:00-22:00 |        +38.3   446 +0.018 |     +41.2   570 +0.019 |    +0.001
XAUUSD      mtf_pullback   (zaten 24s) |       +273.7  3938 +0.278 |    +273.7  3938 +0.278 |    +0.000
```

- **NAS100:** perp'in acacagi ~629 ekstra islem toplam **-35.0R** tasiyor —
  islem basi **-0.0557R**. Saat satin almak **zarar**. NAS100'un edge'i
  15:00-21:00 icinde yasiyor; disari cikmak onu seyreltiyor. maxDD de
  duzelmiyor (45.1 -> 40.7 sadece daha az kazanildigi icin).
- **SpotBrent:** ekstra 124 islem **+2.9R** = islem basi +0.023R —
  istatistiksel olarak sifir. Ustelik SpotBrent zaten kitabin en zayifi
  (+0.018 R/gun) ve 03.09 exhaustif taramasinda **BRENTOIL_PERP_M5 her ailede
  negatifti** (burst -10 2/6, channel -47 1/6, mtf -56 2/6).
- **XAUUSD:** seans kapisi zaten kapali, yani perp yalnizca **hafta sonu**
  ekler — ve o karsilastirma yukarida (1) yapildi, kaybediyor.

Bu test **gerekli kosul**, yeterli degil: perp'in kendi spread'i seans disinda
daha genistir, yani gercek perp rakamlari buradakinden **daha kotu** cikar,
daha iyi degil. Ucu de gerekli kosulu geciremiyor.

### 3. Sonuc

| Aday | Hukum | Gerekce (olculmus) |
|---|---|---|
| **GOLD-PERP** (XAU alt.) | **RED** | Ayni varlik (corr +1.0000). Takasta R/gun +0.085 vs +0.278; 7/24 doneminde bile +10.6R/81 vs +77.7R/193 |
| **BRENTOIL-PERP** (Brent alt.) | **RED** | Eklenecek saatler ~sifir (+0.023R/islem). Perp'in kendisi 03.09'da 3 ailede de negatif. SpotBrent zaten kitabin en zayifi |
| **NAS100-PERP** (NAS alt.) | **RED** | Eklenecek saatler **negatif**: 629 islem, -35.0R, islem basi -0.0557R |

Hicbiri icin yeni bar yakalamaya gerek kalmadi — ucu de eldeki veriyle
kapandi. **Kitap 7 sembol olarak kaliyor.**

Kaydedilen tek acik uc: GOLD-PERP'in risk-ayarli ustunlugu (netR/maxDD 4.70 vs
2.24) gercek. Bugun onemli degil cunku kitap R/gun ile buyuyor; drawdown
baglayici hale gelirse tekrar bakilir.

---

## EK29 — Tersine muhendislik taramasi: kapilar, ateslemeyen korumalar (05.09)

Operator: *"tersine muhendislik ile sistemi full tara olu emekli bayat kod tf
ler semboller kablo boru kose kenar kapi herseye bak"* ve *"tam yetkin var ne
gerekiyorsa yap"*.

Uc ajan uc ayri yuzeyi taradi (canli motor yollari / dis API+panel / test+
kopru+script). **Her bulgu uygulanmadan once elle calistirilarak dogrulandi**;
asagida yalnizca dogrulananlar var.

### A. Eszamanli risk tavani — olculdu, sonra buyutulmedi

`live_concurrent_pct` tavani **bos slot sayisindan** turetiyordu, yani defter
doldukca daraliyordu:

```
acik  0 -> %17.6    acik  3 -> %10.0
acik  1 -> %15.0    acik  4 ->  %7.5   <- burada tikaniyor
acik  2 -> %12.5
```

Islem basi %2 riskle defter **7 dogrulanmis sembolun en fazla 4'unu** ayni anda
tutabiliyordu. Red mesaji (`eszamanli risk limiti`) sebebi soylemiyordu, panel
de "%12.09 / max %12.5" yaziyordu — yani yer varmis gibi.

**Ilk hipotezimi olcum kucultttu.** Bunun holdout-canli bosluğunun mekanizmasi
olabilecegini soyledim; yedi sembolu tek zaman cizgisinde oynatip gercek kapiyi
uygulayinca:

```
ortak pencere 2022-11 .. 2026-09, 8124 islem
  esZAMANLI 0-3 pozisyon : %89.3      <- kapinin hic degmedigi bolge
  esZAMANLI 4            :  %6.5
  esZAMANLI 5+           :  %2.1

kapi uygulaninca: 260 islem reddediliyor, +79.8R
  = replay'in gordugu +954.8R'nin %8.4'u
  XAUUSD 111 red +67.7R (kaybin %85'i) | NAS100 51 red -12.0R (reddi KAZANC)
```

Gercek ama **ikinci dereceden**. Sebep degil, sizinti. (Olcumun kusuru: ayni
barda acilip kapanan islemlerde sayac ~%2 negatife dusuyor; ve reddedilen islem
tekrar denenmiyor varsayildi, yani %8.4 bir UST SINIR.)

**Duzeltme dar tutuldu.** Once "operatorun ayarini oku" dusundum — `15.2`.
Ama `kasa_sizing.py:111` o degeri autopilot'un kendi ciktisindan geri yaziyor,
yani ayari okumak dongusel olurdu. Gercek hata cagri yerinde: **bos slot
sayisi, `n_enabled` adli parametreye geciriliyordu.** Yeni `_enabled_count()`
defter boyutunu veriyor; tavan artik %17.6'da sabit ve 7 pozisyonun tamami
acilabiliyor. Lot boyutlandirmadaki bos-slota bolme **dokunulmadan kaldi** —
orada dogru: kalan marj gercekten dolabilecek isimler arasinda paylasilir.

Bir tavanin, kendisine yaklastikca daralmasi tavan degildir.

### B. `broker_symbol` — hicbir korumadan gecmiyordu

Bu alan config'in barlarinin, tick'lerinin, marjinin ve emirlerinin hangi broker
enstrumanindan geldigine karar veriyor — `magic` ile ayni sinif karar, ve
`magic` dort ayri korumadan geciyor. Bu **hicbirinden** gecmiyordu: `guarded`
kumesinde olmadigi icin giris kilidi ve acik-pozisyon kontrolu **hic
girilmiyordu**, format ve benzersizlik kontrolu de yoktu.

Tek PATCH ile canli, acik bir XAUUSD satiri baska bir enstrumana (emekli bir
isim dahil) yonlendirilebilirdi; satir XAUUSD'nin etiketini, seansini, spread
tavanini ve holdout damgasini korurdu. Etkinlestirme kapilari zaten etkin bir
sembolde tekrar calismaz, yani sonraki her R rakami islem gormemis bir isme
yazilirdi. Toplu uc daha kotu: tek deger **tum defteri** bir enstrumana
yonlendirirdi.

Eklendi: `guarded` kumesine dahil, format kontrolu, benzersizlik (iki config
tek enstrumani yonetemez), acik pozisyonda 409, ve toplu ucta cok-hedef reddi.

### C. Uykudaki aileler arama yolundan girebiliyordu

`POST /api/opt/run` `strategies` alani **hic dogrulanmiyordu**, ve optimizer
5'li `models.STRATEGIES`'e gore filtreliyordu — uykudaki `sweep_fade` /
`range_fade` dahil. `defaults.json` hala onlarin grid'lerini gonderiyor, yani
sweep'in oynatacak ekseni de vardi. Tek cagri yeterliydi:

```
POST /api/opt/run {"symbols":["XAUUSD"],"strategies":["sweep_fade"],"apply_best":true}
```

Hicbir sey dogrulamamis bir aile aranip kazanan olarak **canli etkin bir
sembole** mesru gorunumlu bir damgayla uygulanabilirdi. Ajanlar bu uca zaten
komut veriyor (`cursor/max_yield.py`, `cursor/watch_flat_partials.py`).

Iki yerde de aranan kumeye (`store.opt_params()["strategies"]`) baglandi.
Bir aileyi geri acmak bir **olcum karari + defaults.json'a gonderme** isidir,
API argumani degil.

### D. `trade_days` dogrulamasi olu koddu

Dogrulayici `_session_clock_changed` icine tasinmis ve o fonksiyonun
`return False`'unun **altina** dusmustu — hic calismiyordu. Ve model reddetmiyor,
**yerine baska bir sey koyuyor**:

```
[]      -> [1,2,3,4,5]   sembolu kapatmak isterken TAM HAFTA
[0]     -> [1,2,3,4,5]
[1,8]   -> [1]           bir yazim hatasi haftayi Pazartesi'ye indiriyor
```

Hepsi 200 OK donuyordu. Dogrulayici `_validate_sessions`'a (gercekten cagrilan
fonksiyon) tasindi.

**Bunun neden fark edilmedigi ayrica onemli:** tek kapsayan testler 66 bilinen
hatanin icinde kirmiziydi — `_Optimizer` sahtesi `refresh_live_costed_stamp`
tasimadigi icin. Kirmizi bir test hicbir sey kanitlamaz. Sahte onarildi; dosya
19/29 -> 29/29.

### E. Silahsizlandirilan iki kopru scripti

Ikisinde de `if __name__` korumasi yoktu — **import edilmeleri yetiyordu**.

- `force_ger40.py`: `POST /api/app/restart` — canli motoru **acik pozisyon
  kontrolu olmadan** yeniden baslatiyor (`.bridge/NASIL.md` bunu acikca
  yasakliyor), ardindan `force:true` ve `score: 0.0` ile GER40'a damga basiyor.
- `_land_claude_2244.py`: `cursor/FOR_CLAUDE.md`'ye 04.09 tarihli otoriter
  gorunumlu bayat bir brifing ekliyor ve `WAKE.txt` ile bir sonraki oturumu o
  icerikle uyandiriyor. Ledger korumasi en sonda, yani uc kopru yazisi coktan
  olmus oluyor.

`.bridge/_arsiv_silahsiz/` altinda `.py.txt` olarak, iki dilli README ile.

### F. Ateslenemeyen korumalar — dokunulmadi, karar operatorde

- **Supervisor kapali** (`enabled=false`): karantina, drawdown olcekleme, saat
  bloklari hepsi no-op. NAS100/US30/XAUUSD su an `risk_scale 0.6` tasiyor ama
  `effective_scale 1.0` — kazandiklari %40 kesinti uygulanmiyor. Durum
  `risk_scale_enforced: false` ile durust sekilde raporlaniyor, yani gizli hata
  degil; karar verilecek bir durum.
- **`symbol_daily_loss_pct` armlanamiyor**: 7 sembolde de 0 ve **hicbir yol
  yazamiyor** — API alani degil, hicbir script yazmiyor. "Bir enstruman kanarken
  hesap geneli yesil kalirsa" sorusunun cevabi yok. XAUUSD bugunku 12 kapanisin
  7'sini tasidi.
- **Scalp/swing pozisyon kovasi** erisilemez (iki alan da 0, yazan yok), ama
  `risk_kova_limiti` sayaci hala tahsis ediliyor.

### G. Yanlis ifadeler (kayit, henuz duzeltilmedi)

- `risk.py:1298` *"max_concurrent_risk_pct okunmuyor; bu can_open tavani
  degil"* — iki yarisi da yanlis; `can_open` o tavani uyguluyor.
- `test_auto_opt_is_gone.py` docstring'i *"otomatik arama yalnizca operatore
  ait"* — **yanlis**: supervisor karantinaya giren sembolde `apply_best=True`
  ile arama basliyor (`supervisor.py:1145`). Yalnizca takvim ve decay
  tetikleyicileri kaldirilmis.
- `engine.py:66-72` M5 ve H1 uzerine kurulu bar-yasi yorumlari; ikisi de emekli.
- `test_all_timeframes_searchable.py:115` *"burst retired 27.08"* — emekli olan
  `micro_rev`'di; `burst` canli ve araniyor.

### H. Sonuc

```
pytest:  66 basarisiz -> 57  (3137 gecti, once 3128)
ruff  :  dokunulan dosyalarda temiz
```

Dokuz test daha geciyor, yeni kirilan yok. Kalan 57 iki onceden var olan kume:
bayat test sahteleri (~41 test, kirmizi olduklari icin **korumalari da
olu** — gerileme olsa yeni hata uretmezler) ve ilgisiz davranissal kayma (~20,
her biri ayri triyaj isteyen).

**Hepsi diskte, canlida degil.** Motor 12:41'de baglandi ve calisiyor; bu
degisiklikler bir sonraki restart'ta yururluge girer. Aceleye gerek yok.
