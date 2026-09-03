# OPTIMIZATIONS.md

Read-only notes. **Not executed by the engine.** Latest:
**04.09 00:22** — Claude **#3 RETRACT**: per-symbol charged'da 6/6 "none"
(kotu-saat yok); chop-death hour mirage. Hours WFO kampanyasi yok. JPN
[14,15] kalir (+3.1R charged; [] gerileme). NAS100 WFO devam (SL floor
asıl hedef). Hybrid force-SL gate `b992d67`. Gercek bleed ~−96R
(premature+spread).
**04.09 00:20** — NAS100 WFO + force SL autopsy≥5 gate. Detay asagida.
**04.09 00:10** — hour-block regresyon revert; charged-beat gate. EK22.
Canli: JPN bh[14,15]; NAS/XAU/US30 []; US30 adx20; BTC re-adopt.
**SABAH:** NAS WFO sonucu (SL); XAU trail; SpotBrent fill. Hours axis idle.
Prior **03.09 23:xx** — weak-symbol + 3 bleed. EK22.
Prior **03.09 11:20** — per-symbol WFO round closed (monitoring). Live book:
NAS/XAU mtf, JPN burst/M30, US30 channel re-stamp hold +43, GER/BTC
incumbent max (no-candidate), SpotBrent **disabled FINAL**. Concurrent
**10%**, daily_loss **3%**, channel trail grid DB through **2.8**.
Holdout sum on stamped configs ~**+698R** / 6. HEAD `9c70438` (US30
session defaults). Watch: NAS/XAU mtf live, C1/T1 first fill.
Prior **03.09 10:03** — `MICOFX.bat`; income-loop launchers deleted.
Prior **03.09 09:52 EK21+** — F4 closed; JPN 01–15.
Prior **27.08 22:36** operator income-max. Shakeout floor stays; do not
teach search it. Public WFO/TP/pyramid does not change the exit model.

---

## 03.09 00:50 — MASTER AKSIYON LİSTESİ (EK1-EK18 konsolide, öncelik sırası)

Bu oturumun tüm bulguları. Detay: aşağıdaki EK bloklar. Uygulama = Cursor (kod+commit) +
operatör (red). Claude = ölçüm/doğrulama (yapıldı).

### P0 — GÜVENLİK (canlı $ risk, hemen)
- [ ] **C1-shakeout** `engine.py:2651` (+2638): `sl_size` → `sl_dist`. 3stop/10 sonrası
      %4 risk. 1 satır. (EK14, 3× doğrulandı)
- [ ] **T1-minlot** `risk.py:556-558`: broker min-lot > 2% cap iken 3×cap'e yukarı
      sized. Clamp-up dalını sil (işlem atla) veya 1.5×'e indir + testi güncelle. (EK15)
- [ ] **C3** `pnl_pct` payda = `start_balance + max(0,cash_flow)` VEYA UTC-rollover bekle
      — `daily_loss_pct>0` YAPILMADAN ÖNCE. (EK12-C3; UTC-gece geçti mi kontrol et)
- [ ] **operatör red:** `daily_loss_pct` %3-4? `max_concurrent_risk_pct` 50→~15?

### P1 — EXIT GÜVENLİĞİ (EK14 HIGH)
- [ ] H2 `engine.py:3299,3349`: stale-clock'ta flatten ölü → `broker_now()` fallback.
- [ ] H1 `engine.py:2754`: fill-verify mid-stop kaybı → send'de persist+`_mark_bar_filled`.
- [ ] H3 `close_all` → tracked close (autopsy/sample).

### P2 — KOD SAĞLIK (EK15 — ağaç kendi pytest+ruff kapısını geçmiyor: 4 fail/3 ruff)
- [ ] `app.js:930` ichimoku label sil (2 test) + `test_indicator_edge_inputs.py:124` bound→21.
- [ ] ruff: `scripts/apply_trail_step_queue.py:9` unused sys + 2 test import-sort.
- [ ] ölü fn sil: `indicators.py` parabolic_sar/stochastic_slow/supertrend (~114 sat).
- [ ] `stoch_extreme` C4 kalıntısı (SymbolConfig+Params+key()+defaults.json 5 blok).
- [ ] bayat DB: `settings.opt` orphan key sil; `supervisor_state` PLTR-24 verdict sil.

### P3 — CONFIG (robust-doğrulanmış, EK17/EK18 — EK16 curve-fit'ti)
- [ ] **NAS100**: `cost_rank_max` 0.7→0, `adx_min` 0→15 (burst/M30). 5/6 robust +168R.
      WFO teyit sonra apply. **TEK net config değişikliği.**
- [ ] **NAS pending `trail_step=1.6` İPTAL** (burst'e −24R).
- [ ] GER40: burst mi channel_break mi → WFO regime-gate (3/6 mixed).
- [ ] US30 / XAUUSD / JPN225 / BTCUSD: **DOKUNMA** (robust 5-6/6).
- [ ] SpotBrent: burst FRAGILE (2/6) → roc_pace ADAYI veya disabled.
- [ ] GOLD-PERP add: **mtf_pullback** (5/6 +255R; burst/channel_break < bu). mtf_pullback
      aramadan DÜŞÜRÜLMESİN.

### P4 — YAPISAL (EK12/EK13, operatör +2 aile onaylı)
- [ ] `band_fade` (mean-reversion) — 4 indeks, ÖNCE. Kod: Params+OPT_FIELDS+key()+
      _FAMILIES+STRATEGIES+grid+test. WFO gate + kill-criteria.
- [ ] `roc_pace` (TSMOM) — SpotBrent + BTC/XAU, #2.
- [ ] **48s churn brake → compound gate** (margin+sample+plato+regime-spread≥60-70%+dwell)
      + kill-switch (canlı exp<−0.30R/40tr → sideline). = P1'in asıl parçası, WFO'nun
      overfit seçmesini durduran şey.
- [ ] Evrensel pooled param yönü (sembol-başına tuning değil) — research #2, büyük karar.
- [ ] burst 5 kural: kasılma ön-koşulu (NR7/BB-squeeze) + eğim gate + tetik-bar sertleştir
      + seans + cost-edge. Yeni OPT eksenleri.

### DURUM (03.09 00:50)
Kitap FLAT, opt idle. Cursor ~1s sessiz (commit 73591b3, board 22:58). Canlı config'ler
çoğunlukla robust (Cursor'un apply'ları oturdu). Beklenen aylık panel +%98 = fantezi;
gerçekçi hedef P0-P3 sonrası +$150-250/ay (EK7). Asıl kalan alpha config tuning'de değil,
P0 bug fix'lerinde.

---

## 02.09 20:20 — RE FİLOSU KONSOLİDE (6 paralel salt-okur agent + DB doğrulama)

Operatör "tam yetki, kod kod, acımadan" mandate'i. 6 agent: engine+execution,
optimizer+backtest+holdout, risk+supervisor, strategy+indicators, mt5client+web+store,
web/GitHub/X araştırma (TR+EN). Hiçbir şey PATCH edilmedi. Anahtar iddialar canlı DB ile
doğrulandı (aşağıda "✓DB").

### Nedensel zincir (özet)

Sistemin **ölçülen edge'i NEGATİF (avgR −0.13R)** → Kelly = 0 → risk-optimal stake sıfır.
Sebep: optimizer kırılgan config seçiyor (churn + degradasyon terimi yok + şanslı-dilim),
bunlar iyimser bir backtest'te (trail şişmesi + fill-sırası + spread asimetrisi) iyi
görünüp canlıda tutmuyor; üstüne GER40/M5 burst tüm tasarım gate'leri kapalı çalışıyor,
trail hiç devreye girmiyor, ve slippage telemetrisi ölü olduğu için fark ölçülemiyor.
Riskin büyüklüğü: sizing bug'ı işlem başına ~%2 yerine ~%10 risk aldırıyor, günlük
zarar freni yok, olan fren de bozuk, supervisor reaktif katmanı bu frekansta atıl.

---

### A — OPTIMIZER: CHURN + KIRILGAN SEÇİM  (agent 2)

* **A1 [CRITICAL]** `_beats_incumbent` (`optimizer.py:1754-1885`): rakip skoru cost-free
  (`walk_forward` `charge_costs=False`), mevcut config skoru `_holdout_costed` →
  `charged_holdout` ile HEP maliyetli (`holdout_cost.py:34-51`, charge_costs dalı yok).
  Test `new_score >= old_score` → rakip yapısal avantajlı → **sürekli config değişimi.**
  `reject_reason` yorumu (`optimizer.py:1621-1633`) canlı kaybedenleri churn'e bağlıyor.
  **−41R/+90R'nin en olası mekanik sebebi.**
* **A2 [CRITICAL]** costed-negatif apply reddi `if ... and charging:` arkasında
  (`optimizer.py:2093-2105`); `charge_costs=False` → blok atlanıyor, `costed_negative`/
  `holdout_costed` damgalanmıyor, "maliyetli holdout negatif" reddi hiç tetiklenmiyor.
  Yorum: "UK100/SpotBrent/JPN225 faturaydı". (= F-D1) `reject_reason` maliyet gate'leri
  + `walk_forward` `rejected_costly` de cost-free'de ölü.
* **A3 [MED-HIGH]** Objektif = ham `score` = `net_r × sample_disc × dd_disc`
  (`backtest.py:100-112`). Sortino/degradasyon YOK. `score_consistency` hesaplanıp
  **kasıtlı dışlanıyor** (`backtest.py:117-119`). `holdout_retention` 0.25'te pass/fail
  veto, gradyan değil — retention 0.30 olan, 0.95 olanı yener validation bir tık yüksekse.
* **A4 [MED]** holdout 8-yollu seçim vetosu (4 aile × 2 TF/sembol), `as_dict(MIN_TEST_ (arsiv)
  TRADES=12)` ile tam ağırlıkta puanlanıyor (`backtest.py:1518`) → 12-işlemlik şanslı
  dilim `_beats_incumbent`'ı tam güvenle sürüyor.
* **A5 [MED]** apply gate'leri gevşek: `MIN_TEST_TRADES=12`, `MIN_OOS_PF=1.10`,
  `min_positive_ratio` UI'dan 0.3'e inebilir. `_generalises` retention ≤ 0 → "ölçülemez"
  → retention kontrolü **atlanıyor** (`optimizer.py:1583`).
* **A6 [HIGH]** GER40 canlı TF (M5) otonom re-opt yolunda HİÇ aranmıyor — quarantine
  re-opt `SEARCH_TIMEFRAMES` M15/M30'a sabitli (`supervisor.py:1052`, `optimizer.py:631`).
  Aranınca incumbent replay M5 bar'ı bulamıyor (`allow_fetch=False`) → bayat apply
  stamp'ine düşüyor (kod: "+224.2R loglanmış, aynı setup bu geceki pinlerde −89.1R").
* **A7 [HIGH]** Grid kapsamı: burst ~8.1M grid @ %0.025, mtf_pullback ~1.5M @ %0.13,
  channel_break ~%1, ichimoku ~%15. `coverage_budget` yeniden-dağıtımı ölü (3/4 grid
  cap'i aşınca surplus=0). Seçim küçük-grid'li aileye (ichimoku) yanlı.
* **A8 [HIGH]** burst (scalp) yalnız swing-genişliği stop'la aranabiliyor:
  `uses_swing_exits` M15/M30'da hep true → `SWING_GRID_OVERLAY` `sl_atr_mult` floor 1.0;
  shipped `grid.sl_atr_mult [0.5,0.7,0.9]` default aramada ölü. burst/M5 tight-stop
  yapısal olarak ulaşılamaz.
* **A9 [MED]** decaying-ama-quarantine-değil config hiç yeniden aranmıyor; `combo_seed=7`
  sabit → retry aynı 2000 combo'yu çekiyor; `reopt_retry_cooldown_hours=1` → aynı çekim.

### B — BACKTEST İYİMSERLİĞİ  (agent 2 + araştırma)

* **B1 [MED]** `min_stop_series` ölçeksiz bar-spread kullanıyor (`backtest.py:388`);
  canlı `min_stop_distance` tick-spread → `spread_scale ×` (CHFJPY'de 3.35'e kadar)
  daha geniş. Backtest trail'i canlının izin verdiğinden ~scale× daha sıkı hug ediyor —
  tek yönlü, tam da reward-ratio'nun dayandığı trailed-winner'ları şişiriyor.
* **B2 [araştırma #3]** intrabar fill-sırası: aynı bar'da hard stop + trail-update
  olunca backtest lehte sırayı varsayıyor. Stop-first (kötü durum) varsayılmalı.
* **B3 [MED]** long/short spread asimetrisi: short non-stop çıkışlarda spread'i iki
  uçtan ödüyor, eşdeğer long bir kez (`backtest.py:809-811,866-868`). Cost-free'de
  latent ama repo tarihindeki her costed ölçüm + her `_beats_incumbent` replay yanlı.
* **B4 [LOW-MED]** `lookback_days=0` → her TF farklı miktar geçmiş (90k M30 ≈ 5.1yıl,
  M15 ≈ 2.6yıl, M5 ≈ 10ay). Kod yorumunun uyardığı cross-TF haksızlık geri gelmiş —
  M30'a sistematik seçim avantajı.

### C — SIZING: HESAP-KATİLİ  (agent 3) — ✓DB

* **C1 [CRITICAL]** `lot_for` (`risk.py:459-565`, özellikle 542-554): `raw` (risk% tabanlı
  lot) hesaplanıp **atılıyor**. `r_cap` (gerçek %2 tavan) broker min-lot'un altına
  düşünce — ~$225 hesapta NORMAL durum — 543-551 `lot = min(auto, ceiling)` yapıyor;
  `auto` = marj payı. 1:500 kaldıraç `lev>=100` dalını garantiliyor. Sonuç: her endeks
  girişi marj payına (~5–30× hedeflenen risk) sizing yapıyor. Kanıt: R başına ~$20 /
  ~$225 bakiye ≈ %10/işlem, %2 değil. −$827 kümülatif yalnız $300+ depozitle ayakta.
* **C2 [CRITICAL]** Kümülatif günlük zararı hiçbir şey kapamıyor. ✓DB `daily_loss_pct=0`.
  `DailyGuard.check` hep `Verdict(True)` dönüyor; `_halt(loss)`/`loss_halted`/
  `daily_loss_flatten` tümü `daily_loss_pct>0` dalının altında → ulaşılamaz. Tek savunma:
  supervisor `_drawdown_scale` (en kötü 0.6× kısma, DUR yok) + `max_concurrent_risk_pct=46`
  (4 korelasyonlu endeks long).
* **C3 [HIGH]** ✓DB `day_start_balance=100.51`, `day_cash_flow=300.0`, equity ~225 →
  `pnl_pct = (225−300−100.51)/100.51 ≈ −%174.7`. `rollover` bugün yeniden çıpalamıyor.
  Sonuç: `_drawdown_scale(−174%)` → `risk_scale_floor=0.6`; ✓DB `supervisor_state.
  risk_scale = 0.6` — kitap **kazara** 0.6× damperde. VE: operatör `daily_loss_pct>0`
  yaparsa `check()` sahte −%174'te **anında + kalıcı** halt + `daily_loss_flatten`
  hepsini kapatır. **C2'nin çözümü C3 tarafından tuzaklanmış.** Düzeltme: `pnl_pct`
  paydası `start_balance + max(0, cash_flow)`.
* **C4 [HIGH]** PF quarantine breaker atıl: `judged_n` yalnız `opt_updated_at` sonrası
  işlemleri sayıyor; configler 4.5s önce reopt → `judged_trades` 0-2 → PF arm ateşlenemez;
  quarantine auto-reopt (`quarantine_hours=1`) counter'ı sıfır tutuyor. Streak arm
  `quarantine_losses=11` → 319 işlemde beklenen en uzun kayıp serisi ≈ 11.3, yani "asla
  zamanında değil"; ateşlenince C1 sizing'de 11 kayıp ≈ **%69 hesap DD**. `hard_block_
  only_quarantine=true` → quarantine = "0.6×'te trade", hard block ölü kod.
* **C5 [HIGH]** supervisor yalnız KESER, asla yükseltmez — "MAX INCOME"un throttle-up
  mekanizması yok. Bad-hour kuralları atıl (saatte 80 işlem gerek, kitap sembol başına
  10-30 toplam). Edge-decay atıl (100 işlem/sembol gerek). Decayed sembol hiç
  re-optimise edilmiyor (yalnız quarantine kuyruğa alıyor).
* **C6 [MED]** `edge_scale` (EDGE_MIN/MAX 0.6-2.2) canlı sizing'de atıl — `raw`'a
  besleniyor, o da atılıyor (C1). "Tek en yüksek kaldıraçlı yapısal fix" = `raw`/`r_cap`'i
  `min()`'de tut.
* **C7 [stratejik]** Ölçülen expectancy NEGATİF (−0.13R). Kelly kesri negatif → optimal
  stake sıfır. `max_concurrent_risk_pct=46` × 4 korelasyonlu endeks long ≈ 9× tek-isim
  %2 ≈ holdout-Kelly'de sepet için ~2.4× tam Kelly. Ölçülen ~%10/işlem sizing'de: 5
  kayıp → %41 DD, 8 → %57, 11 → %69. Gerçek %2'de: %10 / %15 / %20.
* **C8 [INFO]** `remaining_position_risk` muhasebesi DOĞRU (trailed stop bütçe serbest
  bırakıyor, double-count yok) — ✓ kontrol edildi.

### D — ENGINE / EXECUTION  (agent 1 + agent 5)

* **D1 [HIGH]** Shakeout SL tabanı: `lot_for`'a `sl_size` (1 ATR) geçiliyor ama stop
  `sl_dist` (2 ATR floor, 3 kayıp/10) yerleştiriliyor → shakeout episodlarında gerçek
  risk 2×. `engine.py:2605-2632` / `risk.py:537`. (agent 1 F2 + agent 3 F8 çapraz-doğrulama)
* **D2 [HIGH]** Günlük-zarar breaker'ı `manage_positions`'ın saniyeler süren broker
  çağrılarından ÖNCE alınan equity'ye bakıyor (`engine.py:863` → 916 → 918). Hızlı ters
  harekette fren bir tam cycle geç.
* **D3 [HIGH]** `execution_samples` (canlı slippage) yapısal aç: `record()` `filled<=0`da
  erken dönüyor; buffer yalnız graceful shutdown'da flush; 7 satır/17 gün, biri düz str.
  Backtest↔canlı farkını kapatacak tek sinyal birikemiyor → `ExecutionMonitor._verdict`
  neredeyse hiç ateşlenmiyor.
* **D4 [HIGH]** `entry_blocks` pencereleme/reset yok: `_entry_blocks_since` bir kez
  seed (2026-08-16), yalnız `POST .../reset` sıfırlıyor (kimse çağırmıyor). `forget_
  entry_blocks` yalnız sembol DELETE'te. → prune kararları bayat, çok-config kanıtına
  dayanıyor. (= F-D3, derinleştirildi)
* **D5 [MED]** `entry_blocks` bloklanıp-sonra-dolan sinyali çift sayıyor (episode kimliği
  `(bar_key, reason)`; spread'de reddedilip acildi'de dolan → signals += 2). `fill_rate =
  opened/total` → raporlanan %22-33 fill kısmen artefakt.
* **D6 [MED]** `_broker_now` 48h içindeki herhangi bir ileri-tarihli tick ile zehirleniyor
  → seans sınırları + trading günü kalıcı kayıyor; tek kurtarma = restart. (agent 1 F6
  + agent 5 F6 çapraz-doğrulama)
* **D7 [MED]** bar-kapanış refetch backoff yok (lag'li sembol her 2sn `copy_rates(400-
  1680)` RLock altında); `_probe_book_ticks` koşulsuz N kilit round-trip/cycle.
* **D8 [MED]** bir çözülemeyen fill sembolün TÜM girişlerini ~20 dk donduruyor
  (`_orphan_scan`, `stale_after=900s` + `abandon_grace=300s`).
* **D9 [MED latent]** off-127.0.0.1 bind'de: `GET /` herkese `Set-Cookie` token veriyor;
  Origin check yalnız tarayıcı CSRF'i durduruyor → non-browser client `POST /api/bot/
  panic` vb. çağırabilir. Default localhost'ta moot.
* **D10 [LOW]** optimizer patch yolu (`_land_pending_primary`) `trail_mode`'u structure/
  hybrid'e çevirebilir, HTTP'deki widen-only/hands-off guard'ı yok. ✓DB şu an hepsi `atr`.

### E — STRATEGY / SİNYAL  (agent 4) — ✓DB

* **E1 [HIGH]** GER40/M5 burst = −41R motoru: ✓DB `brst_close_pct=0.6` (7 burst satırının
  en gevşeği; JPN225 0.9), `brst_lookback=40` (en uzun), `cost_rank_max=0` (ailenin M5'te
  taşımak için TASARLANDIĞI gate), seans 03:15-22:59'a genişletilmiş. Ölçülen "kısa tutuş
  = saf zarar" profiliyle birebir.
* **E2 [HIGH]** Grid-içi chop kolu zaten var, no-op'a sabitli: ✓DB burst'te `brst_close_
  pct`, `cost_rank_max`, `atr_pct_min`, `min_body_ratio` hepsi 0. Kardeş burst satırları
  `cost_rank_max` 0.3-0.7, `atr_pct_min` 0.25 kullanıyor. Bunları yükseltmek pre-open
  ince-range popülasyonunu trend-saati girişlerine dokunmadan filtreler.
* **E3 [MED]** ✓DB GER40/JPN225/NAS100/US30 `opt_summary.params` YALNIZ sıfırlanmış
  gate'leri damgalıyor `[adx_max, adx_min, atr_pct_min, cost_rank_max, max_spread_atr,
  min_body_ratio]` — trade eden sinyal paramlarını (brst_lookback=40, brst_close_pct=0.6,
  htf_factor=3, t3_length) DAMGALAMIYOR. Yani `validated=True` bir gates-disabled pass'i
  belgeliyor; sinyal paramları önceki bir sweep'ten kalıntı, zeroed-gate'lerle birlikte
  walk-forward doğrulanmamış. (Kontrast: SpotBrent/XAUUSD/BTCUSD tam set damgalı.)
* **E4 [MED-HIGH]** `adx_max` ölü-ve-tehlikeli: reversion-ailesi kalıntısı, 4 ailenin (arsiv)
  hiçbiri reversion değil; non-zero `adx_max` bunları yalnız güçlü trendden ÇIKARIR. Hâlâ
  `OPT_FIELDS` + `Params.key()`'de → sweep gürültüde spurious non-zero `adx_max` kazanıp
  `apply()` edebilir. `absent_regime_gates_to_zero` yalnız kazanan onu adlandırmayınca
  sıfırlıyor. → 4 aile için `OPT_FIELDS`'ten çıkar. (arsiv)
* **E5 [MED]** NAS100 mtf_pullback: ✓DB `htf_factor=3` → trend ayağı T3(4)/M90, whippy,
  "HTF zaten trend'de olmalı" DEĞİL (`else 6` yalnız htf_factor≤1'de). `pull_depth_atr=0.3`
  saklı ama 0.5 çalışıyor (MIN_PULL_DEPTH_ATR floor) → grid `{0.3,0.5}` özdeş sinyal
  üretiyor, 0.3'ü kazanan kaydediyor (DB'nin gösterdiği). `required_bars` factor 6
  varsayıyor, sinyal factor 3 koşuyor — sessiz tutarsızlık.
* **E6 [LOW-MED]** burst `expansion` self-inclusive mean/sd (`sma`/`rolling_std` pencereleri
  i'yi İÇERİYOR) → `brst_range_z` göründüğünden katı; her burst holdout distorted
  istatistikte puanlanmış. `channel_break` etkilenmiyor (kanalı bir bar kaydırıyor).
  Minör: `rolling_std` `out=np.zeros` allocate edip kullanmıyor (ölü satır).
* **E7 [LOW]** ölü kod: `indicators.py` `supertrend`/`parabolic_sar`/`stochastic_slow`
  (~130 LOC, sıfır çağıran), `stoch_extreme` (`Params.key()`'de bile yok), `_GATED_FLIPS
  = frozenset()` → `unstamped_gates_to_zero` koşulsuz `{}` dönüyor (F-D4/C4 kalıntı).

### F — ARAŞTIRMA: EN YÜKSEK-ROI DIŞ FİKİRLER  (agent 6, TR+EN)

1. **ATR trail aktivasyonunu düzelt.** `trail_start` = veri: **0.3-0.5 × medyan kazanan
   MFE_R** (bizde ≈ 0.2-0.4R), VEYA Chandelier (girişte arm, 2.5-3× ATR, aktivasyon
   paramı yok). Validation reddi: **trail kazananların <%30'unda devreye giriyorsa** o
   set fixed-stop sistemi, at. = C2-ölçümü ve en büyük gelir kaldıracı.
2. **Deflated Sharpe + CPCV validation gate.** DSR ≤ 0 (trial sayısı = grid boyu) veya
   PBO ≥ 0.5 → reddet. Mutlak OOS bar (PF>1.2, ≥30 işlem). Holdout(+)/canlı(−)'ye
   doğrudan saldırı. Repo: `eslazarev/purged-cross-validation` (drop-in).
3. **Intrabar fill-sırası düzelt** (stop-first kötü-durum) = B2.
4. **Aile-spesifik entry gate.** pullback+ichimoku: ADX(14) **22-50 bandı** (+ opsiyonel
   ER≥0.3). burst+channel_break: **ADX tabanı YOK** — yerine volatilite-sıkışması
   (Bollinger-bandwidth son 100 barın alt ~%20'si / NR7) + ER≥0.3 tetik barında. ADX
   breakout'a −0.12R expectancy verdi (test). = C3-ölçümü + E2/E4.
5. **Per-sembol seans whitelist + rollover blackout.** burst/channel_break yalnız
   cash-open + US-overlap (GER40 09:00-11:30 & 14:30-16:00 CET; NAS100/US30 NY ilk 60-90
   dk). Asya öğle, Avrupa öncesi, Cuma PM, rollover ±2 bar blok.
6. **TF seçimi R/gün + maliyet tavanı.** Sembol×aile için TF sweep; **R/gün = expectancy_R
   × işlem/gün (maliyetli)** maks, `cost_R/gross < ~0.35` ve ≥30 validation işlem şartıyla,
   eşitlikte yavaş TF'e. (Maliyet teorisi: maliyet arttıkça lookback uzat.)
7. **Volatilite-hedefli sizing + katmanlı frenler.** Taban **%1 risk/işlem** (holdout
   istatistiğinden ≤ 0.25× Kelly), ~%0.10/gün volatilite katkısına sized (4 endeks eşit
   risk); **günlük fren %3-4**, **haftalık %8-10**; **3 ardışık kayıptan sonra yarıya**,
   yeni equity zirvesinde tam; **min-lot riski hedefin >1.5×'i ise işlemi atla**.
   Pyramiding YOK (zaten yok — veri onaylıyor: pyramiding max DD %49 vs VT %25).
8. **Cadence + profit_drop supervisor.** Sembolü **N kapalı işlem sonrası** re-opt
   (takvim cap yedek); param yalnız incumbent'ı OOS marjıyla yenerse değiştir ("bir kötü
   hafta değil, istatistiksel kanıt"). Canlı: son-50-işlem **canlı/holdout expectancy
   oranı < 0.5 → oto de-risk + zorla re-opt**; iki-katmanlı kill switch (equity DD% +
   feed/broker sağlığı, >30sn kopukta watchdog flatten).

Repo/thread: `EarnForex/ATR-Trailing-Stop`, `xMattC/mt5-strategy-factory` (staged IS/OOS
WFO orkestrasyon), `eslazarev/purged-cross-validation` (DSR+PBO+CPCV), `polakowo/vectorbt`,
`Concretum` (vol-target 0.10%/gün, VT DD %25 vs pyramiding %49), `@macrocephalopod` thread
(vol-norm sinyal, 3-6ay ufuk, no-trade buffer band), NY Fed SR 917 (overnight drift).

---

### ÖNCELİK — P0..P4 (uygulama Cursor lane'inde; red = operatör)

**P0 — GÜVENLİK (gelir çalışmasından ÖNCE, kanama hızını kes):**
`C1` sizing bug (`raw`/`r_cap`'i `min()`'de tut = C6 fix) · `C3` pnl_pct payda tuzağı
(bunu düzeltmeden C2'ye dokunma) · `C2` günlük zarar freni %3-4 (operatör red, C3 sonrası)
· `D1`/`D2` shakeout sizing + bayat-equity fren · `C4` streak `quarantine_losses` ~5-6
· `D6` `_broker_now` clamp `≈ 2×max_tf`.

**P1 — KÖTÜ CONFIG SEÇİMİNİ DURDUR (−0.13R'yi costed-holdout'un +0.05..+0.19'una çek):**
`A1` `_beats_incumbent` simetrik maliyet · `A2` costed-negatif reddi charge_costs'tan
bağımsız çalıştır · `A3` objektif = `score × retention` veya DSR terimi · `A5` gate'leri
sıkı (`MIN_TEST_TRADES` ~25, `MIN_OOS_PF` ~1.25) · `F2` DSR+PBO.

**P2 — BACKTEST GERÇEKLİĞİ (ölçebilmek için):**
`B1` scaled `min_stop_series` · `B2` stop-first · `B3` spread simetrisi · `D3` slippage
telemetrisini onar (sonra apply gate'i buna kalibre) · `D4`/`D5` entry_blocks pencere+reset.

**P3 — GELİR KALDIRAÇLARI (asıl optimizasyon):**
`F1`/C2-ölçümü per-sembol `trail_start ≈ 0.5×medyan MFE` costed ara · `E2` burst
`cost_rank_max`/`atr_pct_min` (kardeş-satır değerleri) · `F4`/C3-ölçümü `adx_min=15`
YALNIZ NAS100+US30; burst'e volatilite-sıkışması gate · `F5` per-sembol seans whitelist ·
`F6` TF-by-R/gün · `E5` NAS100 `htf_factor≥6` + config-honesty · `A6`/`A8` GER40 M5'i
kendi TF'inde + tight-stop grid'iyle ara.

**P4 — TEMİZLİK / OTONOMİ:**
`E4` `adx_max` OPT_FIELDS'ten çıkar · `E7`+C4-kalıntı ölü kod · `A7` grid kapsam eşitle ·
`C5`/`F8` supervisor eşiklerini bu frekansa ölçekle + decay→reopt trigger · `D7` perf ·
`C4` orphan verdict temizliği + `supervisor_state.updated_at`.

**Operatör (red/yellow):** `daily_loss_pct` değeri, `max_concurrent_risk_pct` düşüşü
(46→~12-15), disabled sembol reopen (XAUUSD/GOLD-PERP/BTCUSD costed güçlü), `claude` /login,
commit.

### EK — trail_start / trail_step costed sweep (02.09 20:26, salt-okur) — P3 REVİZYON

`c_trail_sweep.py`, npz + `charged_holdout`, canlı aile/exit, `trail_start_atr ∈
{0.3..2.0}`. Kazanan-işlem medyan MFE_R (autopsy): GER40 1.74, JPN225 2.19, NAS100 1.45,
US30 1.87 — yani **C2'deki 0.47-0.77 "medyan MFE" TÜM işlemlerin medyanıydı; KAZANANların
medyanı 1.45-2.19R**, canlı `trail_start` 2.0-2.5R kabaca kazanan-medyanında.

| snapshot | live TS_R | ts=0.3 | ts=0.5 | ts=0.8 | ts=1.2 | ts=2.0 |
|----------|-----------|--------|--------|--------|--------|--------|
| GER40_M30 | 2.00 | +17.5 | +17.5 | +17.2 | +13.4 | **+21.4** |
| JPN225_M15 | 2.50 | +47.7 | +47.7 | +47.7 | +47.7 | **+48.3** |
| NAS100_M30 | 2.50 | +39.2 | +39.2 | +39.2 | +38.8 | **+41.1** |
| US30_M30 | 0.30 | +18.0 | +18.0 | +18.0 | +17.5 | +18.9 |

**Ölçülen sonuç:** `trail_start` sıkılaştırmanın costed net_r'ye faydası YOK — düz veya
hafif negatif (4 sembol). Trend-takip literatürünün "mekanik trail sıkılaştırma çoğu
testte getiriyi düşürür" uyarısıyla tutarlı. → **P3'ten "per-sembol trail_start ≈ 0.5×
medyan MFE" ADAYI DÜŞÜYOR** (araştırma agent'ının "en büyük kaldıraç" iddiası bizim
veriyle desteklenmedi). C2'nin "trail fiilen ölü" çerçevesi fazla güçlüydü — düzeltildi.

**AMA — US30 `trail_step` sweep (trail_start=0.4'te) GERÇEK bir kaldıraç:**

| trail_step | net_r | exp | PF | n |
|-----------|-------|-----|-----|---|
| 0.4 | +6.1 | +0.016 | 1.03 | 384 |
| 0.6 | +21.2 | +0.056 | 1.11 | 379 |
| **0.8** | **+30.6** | **+0.082** | **1.16** | 371 |
| 1.2 | +25.3 | +0.071 | 1.12 | 356 |
| 1.6 | +30.0 | +0.087 | 1.14 | 344 |
| 2.2 (canlı) | +18.0 | +0.054 | 1.08 | 334 |

US30 canlı `trail_step=2.2` çok geniş; ~0.8'e sıkmak costed +12R, expectancy +0.054→+0.082,
PF +0.08. Agent 1/5'in "US30 step çok geniş + %80 erken-stop-toparlama" bulgusuyla uyumlu.
→ **P3 YENİ ADAY: per-sembol `trail_step` costed araması, US30 önce.** (JPN225/NAS100/GER40
step sweep henüz yapılmadı — sıradaki.)

Uyarı: tek pencere ~18k bar, son segment. Apply = optimizer full WFO/validation (Cursor).

### EK2 — trail_step costed sweep, 4 canlı sembol (02.09 20:34, salt-okur)

`c_trailstep_sweep.py`, canlı `trail_start` sabit, `trail_step_atr ∈ {0.25..2.5}`.

| sembol / aile | canlı step | canlı net_r (exp / pf) | en iyi step | en iyi net_r (exp / pf) | Δ |
|---------------|-----------|------------------------|-------------|-------------------------|---|
| **US30** channel_break/M30 | 2.2 | +18.0 (.054 / 1.08) | **0.8** | **+33.6 (.090 / 1.18)** | **+15.6** |
| **NAS100** mtf_pullback/M30 | 2.5 | +23.6 (.021 / 1.03) | **1.6** | **+39.6 (.032 / 1.05)** | **+16.0** |
| GER40 burst/M30* | 1.8 | +22.1 (.051 / 1.08) | 1.6 | +26.4 (.060 / 1.09) | +4.3 (gürültü) |
| JPN225 burst/M15 | 2.5 | +48.3 (.192 / 1.28) | 2.2 | +51.0 (.201 / 1.29) | +2.7 (gürültü) |

**Ölçülen sonuç — aile-spesifik (adx_min ile aynı yönde):**
- **channel_break (US30) + mtf_pullback (NAS100)** = "yerleşik yapıya giren" aileler →
  DAHA DAR `trail_step` istiyor (US30 ~0.8, NAS100 ~1.6). US30 çift-doğrulandı (bu run +
  ts=0.4'te step 0.8 = +30.6). NAS100 0.6-1.6 arası ~+38, 2.2'de düşüyor.
- **burst (JPN225, GER40)** = range-expansion → GENİŞ `trail_step` istiyor (2.2+);
  0.8 altına sıkmak yıkıcı (JPN225 step≤0.8'de negatife düşüyor). Canlı değerleri
  zaten yakın-optimal.

→ **P3 firm:** `trail_step` **US30 2.2→~0.8** (en güçlü) + **NAS100 2.5→~1.6**; JPN225/GER40
burst step'i geniş bırak. adx_min=15 (NAS100+US30 only) ile aynı ikili: iki yapı-giriş
ailesi daha sıkı yönetim istiyor, iki burst ailesi istemiyor.

**EK6 — adx_min + trail_step STACK ediyor (21:19, apply-ready sayılar):**

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

İki kaldıraç ADDITIVE: US30 +24R (exp 2.2×), NAS100 +42R (exp 2.7×) live'a göre. Apply
= optimizer full WFO; bu tablo hedef param + beklenen yön.

**XAU/BTC (yeniden açıldı) canlı-config costed:** XAUUSD_M15 **+128.3** (exp .168, pf 1.27,
n764) · BTCUSD_M30 **+52.5** (.158, 1.24, n333). İkisi de güçlü — reopen costed-haklı.

### EK7 — Beklenen-aylık vs holdout vs CANLI sapması (21:34, item 4) — BEKLENTİ YÖNETİMİ

**Panel projeksiyonu (`/api/state` capacity):** `projected_costed_monthly_pct = 98.3`
(+%98/ay costed!), `projected_monthly_pct = 77.3`. `total_risk_per_trade = $40.01` /
balance $229 = **%17.5/işlem** → C1 sizing bug HÂLÂ CANLI (fix commit'li ama process
restart olmadı). `projected_costed_negative = False` (canlının negatif olduğunu bile
işaretlemiyor).

**Holdout — DOĞRU şekilde aylığa normalize (lookback_days=0 → her sembol farklı gün):**

| sembol | holdout kümülatif | süre | **→ R/ay** | canlı R (exp) |
|--------|-------------------|------|-----------|---------------|
| NAS100 | +91.8R / 1029tr | 555g | **+5** | −18.7R (exp −0.346) |
| GER40 | +53.6R / 335tr | 107g | +15 | −6.9R (exp −0.160) |
| JPN225 | +68.3R / 225tr | 278g | +7 | −17.4R (exp −0.232) |
| US30 | +37.6R / 319tr | 557g | +2 | −3.4R (exp −0.037) |
| XAUUSD | +66.4R / 426tr | 280g | +7 | +9.8R (exp +0.316) |
| BTCUSD | +67.4R / 286tr | 376g | +5 | −2.8R (n=4) |
| **KİTAP** | | | **~+41R/ay (gerçekçi tavan)** | **−41.2R / 14.3g → −87R/ay** |

**Ölçülen sapma:**
1. Herkesin alıntıladığı "+90R holdout" NAS100 için **1.5 YIL**. Aylığa **+5R**. Kümülatif
   sayılar süre normalize edilmeden karşılaştırılamaz (B4: `lookback_days=0`).
2. Kitap-geneli gerçekçi holdout ≈ **+41R/ay**. Panel **+%98/ay** diyor — bu, kırık
   sizing ($40/R) × iyimser işlem-frekansı ekstrapolasyonunun artefaktı. Ulaşılabilir değil.
3. **Canlı gerçek: −87R/ay trajesi** (−%38/ay, mevcut sizing). Panel +%98 ile arada
   **~136 puan** fark.
4. Her sembolün canlı expectancy'si holdout'unun **~0.25-0.45R ALTINDA** — kitap-geneli
   tutarlı ~0.3R/işlem decay/execution gap'i.

**Gerçekçi hedef (P1-P3 sonrası):** canlı expectancy −0.13R → holdout ~+0.15R ortalamaya
çek. Düzgün-sized $230 hesapta ≈ **+$150-250/ay**, +%98/ay DEĞİL. `projected_*` alanları
gerçekçi trade-frekansı + doğru sizing ile yeniden hesaplanmalı; `projected_costed_negative`
canlı expectancy'yi de okumalı.

**entry_blocks:** ✓DB `entry_blocks_since` artık 09-02 17:57 (F-D3 roll CANLI). Sayaçlar
taze. `entry_block_events` (ring, 1474): spread 398 / acildi 376 / risk_sembol_limiti 261
/ risk_ters_yon 223 / bar_bosluk 138 / lot 38 — F-E1/E2/E3 profili değişmedi.

### EK8 — NAS100 htf_factor (E5) + JPN225 burst params (E3) — İNTERAKSİYON UYARISI (21:49)

**NAS100 mtf_pullback/M30 — `htf_factor` sweep (canlı=3):**

| htf_factor | net_r | exp | pf |
|-----------|-------|-----|-----|
| 2 | −21.8 | −.018 | 0.97 |
| **3 (canlı)** | +23.6 | .021 | 1.03 |
| 6 | **+53.0** | .052 | 1.08 |
| 8 | +55.5 | .056 | 1.09 |
| **12** | **+72.3** | **.075** | 1.12 |

E5 DOĞRULANDI + büyük: `htf_factor=3` "zorunlu HTF trend ayağı"nı işlevsiz bırakıyor
(T3(4)/M90). 12'ye çıkarmak **+49R** — NAS100 (en kötü canlı sembol) için bulunan tek
en büyük kaldıraç. `required_bars` zaten factor 6 varsayıyor.

**AMA İNTERAKSİYON:** htf=12 + adx15 + step1.6 = **+46.7R** < htf=12 tek başına (+72.3).
`htf_factor` ve `adx_min` örtüşüyor (ikisi de trend filtresi). → **NAS100 için P3'ü
revize et: adx15+step1.6 (EK6) DEĞİL — {htf_factor, adx_min, trail_step} BİRLİKTE WFO.**
Tek-eksen delta'ları toplamsal değil.

**JPN225 burst/M15 — signal params (canlı lb=15, rz=1.5, cp=0.9):**
- Baseline +48.3 (exp .192). **lookback=20, range_z=1.0 → +60.9R** (+12.6, modest).
- `brst_close_pct`: canlı **0.9 EN İYİ** (+48.3, exp .192); 0.8→+40.5, 0.6/0.7→+21.
  JPN225'in sıkı close_pct'si DOĞRU — GER40'ın 0.6'sının TERSİ (E1). Leftover paramlar
  büyük ölçüde sağlam; lb 15→20 + rz 1.5→1.0 küçük kazanç, acil değil.

**Genel çıkarım:** per-sembol P3 kaldıraçları BİRBİRİYLE ETKİLEŞİYOR (htf×adx, adx×step).
Tek-eksen costed delta'ları "aday aralık" olarak ver, apply = optimizer'ın JOINT WFO'su.
Claude tek-eksen tarıyor; Cursor birlikte aratıp validate ediyor.

### EK9 — JOINT mini-grid'ler (21:55) — APPLY HEDEFLERİ NETLEŞTİ

**US30 (adx_min × trail_step):**

| | step 0.6 | step 0.8 | step 1.2 | step 2.2 |
|---|---|---|---|---|
| adx=0 | +21.2 | +33.6 | +26.1 | +18.0 |
| **adx=15** | +28.5 | **+42.1** | +38.0 | +23.9 |

İki kaldıraç her hücrede ADDITIVE, tepe köşede. **US30 APPLY: {adx_min=15,
trail_step=0.8} → +42.1R (exp .118, pf 1.24).** Firm.

**NAS100 (htf_factor × adx_min, step 2.5 & 1.6):**

| step 2.5 | adx0 | adx15 | adx20 |
|---|---|---|---|
| htf=3 | +23.6 | +57.0 | +46.8 |
| htf=6 | +53.0 | +52.5 | +68.9 |
| **htf=12** | **+72.3** | +57.2 | +68.4 |

`htf_factor` ve `adx_min` **SUBSTITUTE** (tamamlayıcı değil): htf=12 tek başına +72.3;
htf=12 + adx=15 = +57.2 (İKİSİ birden DAHA KÖTÜ). Bir güçlü trend filtresi yeter.
**NAS100 APPLY: {htf_factor=12, adx_min=0 (değişme), trail_step=2.5 (değişme)} → +72.3R.**
= tek-param değişiklik, EK6/EK8'deki "adx15+step1.6" (+65.8) önerisinden **BASİT + İYİ**.
(htf=6/adx20 = +68.9 de alternatif.)

**GOLD-PERP (mtf_pullback/M30 — add adayı):**

| config | net_r | exp | pf |
|--------|-------|-----|-----|
| **baseline (as-is)** | **+114.3** | .219 | 1.35 |
| adx15 | +104.7 | .219 | 1.36 |
| htf6 | +67.2 | .133 | 1.21 |
| htf12 | +74.5 | .147 | 1.23 |
| step1.6 | +115.8 | .219 | 1.35 |

**GOLD-PERP baseline near-optimal — AS-IS ekle, ayar yok.** adx_min zarar (commodity),
htf değişimi zarar (NAS100'ün TERSİ — GOLD'un htf_factor=3'ü doğru), step marjinal.
+114R costed = kitabın en güçlü add adayı.

**GER40 M5 (item 1) — KESİN DURUM:** `data/holdout_bars/`'da GER40_M5.npz YOK; panel'de
bulk-bar GET endpoint'i YOK; MT5 sidecar YASAK. GER40 M5 costed doğrulama **Claude
tarafından yapılamaz** — `POST /api/holdout/capture GER40 M5` gerek (flat kitap, 409
ticket varken). **Cursor görevi.** M30 proxy: cost_rank=0.3 → +35.5R (+14R), en iyi
mevcut kanıt.

### EK10 — Live-vs-holdout 0.3R/işlem DECAY dekompozisyonu (22:04) — SEBEP BULUNDU

319 canlı autopsy dökümü:

1. **Giriş slippage'i SORUN DEĞİL:** `fill_vs_signal_close_r` medyan +0.014, ort +0.031,
   toplam +7.8R / 252 işlem. Spread at-fill medyan 0.05 ATR. Toplam ~5-10R açıklıyor.
2. **Noise-stop DEĞİL:** 166 `sl` çıkışından **%0'ı** "MAE 1.00-1.15 + önce MFE≥0.5"
   (kıl payı stop) değil. Stop yiyenler gerçekten ters gidip ters kalan işlemler.
3. **Exit mix:** `sl` %52 (avgR −0.94, −156R) · `trail` %31 (+0.84) · `flatten` %15
   (+0.59). Win rate %48 — trend sistemi için avgWin +0.84/avgLoss −0.94 ile ~%53 gerek.
   **Kıl payı kaybediyor, sorun %52 sl oranı.**
4. **ASIL SEBEP — after_1h:** 129 `sl` işleminin **%74'ü 1 saat içinde entry'yi geri
   geçti** (medyan recovery +1.28R, ort +1.68R). ≈95 stop, fiyatın geri geldiği işlem.
5. **Tutuş-süresi:** `<15m` n47 avgR **−0.91** · `15-45m` n73 **−0.67** · `45-120m` +0.03
   · `120-300m` +0.11 · **`300m+` n41 avgR +0.97, sumR +40 (kitabın TÜM kârı)**.
   120 işlem (<45m) −92R kaybediyor; 41 işlem (300m+) +40R kazanıyor. **Kitap ilk 45
   dakikayı hayatta geçirip geçirmemeye bağlı.**

**sl_atr_mult sweep (canlı=1.0 hepsi):**

| sembol / aile | sl0.9 | sl1.0 | sl1.2 | sl1.5 | sl2.0 |
|---------------|-------|-------|-------|-------|-------|
| **NAS100** mtf_pullback | −4.7 | +23.6 | +54.9 | **+71.0** | +36.1 |
| **JPN225** burst | **+61.2** | +48.3 | +38.0 | +23.4 | +14.3 |
| US30 channel_break | +16.3 | +18.0 | +19.7 | +17.9 | +15.1 |
| GER40 burst/M30 | +14.6 | +21.4 | +19.5 | +9.3 | +7.5 |

**Aile-spesifik, yine:**
- **NAS100 (mtf_pullback): geniş stop çok yardımcı** (1.0→1.5 = +47R). Ama `htf_factor`
  ile SUBSTITUTE: sl1.5+htf12 = +33.8 (< htf12 tek başına +72). İkisi de "hızlı ölüm"
  sorununu çözüyor, birlikte over-correct (n 969→730). → NAS100 için: **htf_factor=12
  VEYA sl_atr_mult=1.5** (~+72 vs +71) — BİRİNİ seç, htf tercih (stop geometrisine
  dokunmaz, risk profili temiz).
- **JPN225 (burst): DAHA DAR stop** (0.9) → +13R. burst tasarımı gereği hızlı ölür,
  kısa tasma doğru. NAS100'ün TERSİ.
- US30/GER40: sl 1.0-1.2, mevcuta yakın.

**Decay sonucu:** 0.3R/işlem gap'i büyük ölçüde NAS100 (mtf_pullback) kaynaklı — 1.0 ATR
ilk stop, pullback-devam hareketi gelişmeden yakalıyor. Fix = `htf_factor=12` (zaten
tespit edildi). burst isimleri sıkı stop'ta zaten doğru. Kitabın kalan gap'i daha yaygın
(rejim kayması, 1.5yıl holdout vs 14g canlı örneklem).

### EK11 — WFO RUN SONUCU (21:53-22:10) — churn freni + NAS100 burst (22:12)

Operatör "US30 opt geçemedi, stratejiler karmaşık" dedi. Log gerçeği:

| sembol | WFO kazananı | validation | holdout | uygulanmadı ÇÜNKÜ |
|--------|--------------|-----------|---------|-------------------|
| **NAS100** | **burst/M30** skor 85.7 | PF 1.51 +189.6R | PF 1.29 **+99.1R** | churn freni (config 7s < 48s) |
| JPN225 | burst/M30 skor 58 | PF 1.41 +93R | PF 1.19 +50.4R | churn freni |
| GER40 | burst/M5 skor 58 | PF 1.23 +52.8R | PF 1.14 +31.4R | churn freni |
| **US30** | YOK | — | — | hiçbir aday kapıdan geçmedi (gate DOĞRU) |

- **US30:** alternatifler holdout'ta çöktü (mtf_pullback/M5 val +54R → holdout −71R PF 0.83).
  Mevcut channel_break/M30 validated + retention 1.12 → US30'un veride en iyisi. A5
  (MIN_TEST=25) + gate overfit'i reddediyor = istenen davranış. "Karmaşık strateji" değil.
- **NAS100 aile karşılaştırması (aynı pencere, costed):** current mtf_pullback/M30 (arsiv)
  **+23.6R** (exp .021) · mtf_pullback+htf12 **+72.3R** (exp .075, n969) · WFO burst/M30
  **+59.4R** (exp **.110**, PF 1.17, n**538**). burst yarı turnover'da daha yüksek
  expectancy + WFO tam-doğrulamadan geçti (+99R). mtf+htf12 tek-pencere bulgusu,
  doğrulanmadı.

**Reframe:** En hızlı gelir kaldıracı benim param sweep'lerim DEĞİL — **WFO'nun bulduğu
3 config'i uygulamak** (NAS100 burst +99R, JPN +50R, GER +31R holdout). `reopt_min_age_
hours` 48 → geçici ~4-6 VEYA bu 3 için force-apply (A1 fix yeni; oturunca 48'e geri).
Benim EK8-10 NAS100 tuninglerim mtf_pullback üzerineydi → NAS100 burst'e geçince geçersiz.
Kitap 3/4 burst'e yakınsıyor (channel_break yalnız US30, mtf_pullback hiçbir yer, ichimoku 0).

### EK12 — HEDEF MİMARİ SENTEZ (research agent #2 + ölçümler, 22:24)

Araştırma (Carver, Davey, WFO literatürü, ORB replikasyonları — TR+EN, tam kaynaklar
FOR_CURSOR.md) + bizim ölçümlerimiz aynı yere işaret ediyor:

**A. AİLE YAPISI**
- **"Tek edge, çok enstrüman" > "çok aile, sembol-başına-en-iyi".** Carver: sembol-başına
  fit "açıkça aptalca" (Sharpe individual 0.60 vs pooled 0.65). `burst` ve `channel_break`
  AYNI edge (range/seviye genişlemesi) — ayrı "aile" saymak sahte çeşitlendirme.
- **Holdout+/canlı− açığı = multiple-comparisons makinesi.** "4 aile × TF × grid, sembol (arsiv)
  başına en iyi" = çok sayıda gürültülü tahminin maksimumunu seçmek → garantili iyimser
  holdout + canlı düşüş (bizim −0.13R). Çözüm: seçimdeki serbestlik derecesini AZALT,
  daha çok tuning DEĞİL.
- **KARAR:** `ichimoku` tamamen çıkar. `burst`+`channel_break` → TEK breakout ailesi
  kavramı, birlikte skorla, re-opt başına BİR seç. `mtf_pullback` yalnız metal/emtia
  (GOLD-PERP +114R; indeks aramasından çık).

**B. PARAMETRELER: EVRENSEL (pooled), sembol-başına DEĞİL**
- 4 indeks için TEK {sl_atr, trail_start, trail_step, lookback, close_pct} — pooled trade
  set üzerinde fit. Sembol-başına tek knob: volatilite/maliyet skaları (pozisyon boyutu
  + trail sıkılığı ATR/spread ile ölçeklenir).
- Fit'in PLATO'da olması şart: ±%10 / ±1 grid adım pozitif + tepenin ~%20'si içinde.
- **Bu, benim EK2-11 per-sembol sweep'lerimin çoğunu geçersiz kılıyor** — onlar
  sembol-başına tuning. Doğru yön: eksenleri POOLED ara.

**C. CHURN FRENİ — 48s saat brake'i ÇÖPE, compound gate:**
Canlı config DEĞİŞİR ancak HEPSİ sağlanırsa: (1) challenger OOS expectancy ≥ +0.20R/işlem
VE ≥%25-30 rel PF üstün; (2) challenger ≥100 kendi-holdout işlemi; (3) plato testi;
(4) rolling OOS alt-pencerelerin ≥%60-70'inde net-pozitif (regime-concentration tuzağı);
(5) incumbent ≥1 tam OOS penceresi canlı çalışmış (≥60 gün VE ≥40 canlı işlem).
Ayrı **kill-switch:** canlı expectancy < −0.30R / ≥40 işlem → config'i sideline et,
taze backtest'ten OTOMATIK değiştirme; çeyreklik döngü yeniden türetsin.

**D. CANLIYı NEGATİFTEN POZİTİFE ÇEKECEK 5 KURAL (burst'e — YENİ OPT eksenleri):**
1. **Kasılma ön-koşulu (EN YÜKSEK KALDIRAÇ):** NR7 VEYA `ATR(setup)/ATR(20) ≤ ~0.7` VEYA
   BB bandwidth son 50 barın alt %15-20'sinde ≥3 bar. "Her yayınlanmış versiyonun
   kullandığı, bizim ailenin muhtemelen eksik olduğu filtre."
2. **Rejim/eğim gate:** long yalnız fiyat > HTF EMA + eğim ≥ 0. (Bizim `htf_factor` bir
   T3 yön bayrağı, eğim gate'i değil.)
3. **Tetik-barı sertleştir:** TR ≥ 1.5×ATR(20) VE kapanış barın üst/alt %15-25'inde;
   inside/outside tetik barı reddet; sonraki-bar giriş boşluğu > x·ATR ise reddet.
4. **TF + seans:** motoru H1/H4'e taşı (fakeout ~%65→~%50); cash-open sonrası ilk N dk +
   düşük-likidite bakım penceresini blokla. (F5/EK4 ile uyumlu.)
5. **Maliyet-edge gate:** spread > ATR-stop mesafesinin k%'si VEYA ATR alt çeyrekte ise
   atla; beklenen lehte hareket ≥ ~3× round-turn maliyet.
Bonus: cross-index teyit (korelasyonlu indeks sinyal anında hemfikir olsun — replikasyonda
+$0.125/share t=2.05); ATR trail'i GEVŞET (aşırı-sıkı trail klasik holdout-iyi/canlı-kötü).

**E. RE-OPT CADENCE:** çeyreklik (≈63 işlem günü), 6-ay OOS roll, 2-3 yıl IS. Bir config
canlıya UYGUN olmadan: ≥8-15 walk-forward döngüsü, döngü başına ≥90 IS işlem (30×3 param),
WFE ≥ 0.5 (ideal ≥0.6, ≥7 ardışık döngü).

**ÖNCELİK:** D1 (kasılma filtresi) + D2 (eğim gate) = en yüksek beklenen canlı-P&L etkisi,
ama YENİ kod (`_burst` + OPT_FIELDS + grid + test). C (churn gate) = P1'in parçası, WFO
overfit seçmesini durdurur. A/B (aile+param sadeleşme) = operatör onaylı yön. Sıralama
Cursor + operatör.

### EK13 — 2 YENİ AİLE TASARIMI (agent, operatör +2 aile onayı, 03.09 00:00)

Tam pseudocode + grid + kanıt + kill-criteria: FOR_CURSOR.md 00:0X bloğu.

**#1 `band_fade` — MEAN-REVERSION (kitabın eksik edge'i):**
- Tez: indeks kendi vol bandını (Bollinger N-σ) delip HEMEN kendi ekstremine karşı
  kapanırsa (IBS ≤ 0.15 = alt banda delip barın DİBİNE kapandı) → ortalamaya doğru fade.
- Gate: ADX ≤ 25 (trend yok) + vol RANK ≤ 0.7 (kasılmış, genişleyen değil) + ortalamaya
  mesafe ≥ min_atr (lagging trail'in kâr yazması için) + seans + cost + HTF hizası.
- 5 param: `bf_ma_len, bf_band_k, bf_ibs, bf_vol_rank_max, bf_min_room_atr` + reuse `adx_max`.
- **burst ile MEKANİK ANTİ-KORELE:** burst barın üst %30'una kapanır; band_fade IBS≤0.15
  (dibe). Aynı büyüklüğün ters işareti. burst'ün en iyi barlarını gate B blokluyor.
- **Deploy: YALNIZ GER40/NAS100/US30/JPN225** (indeksler; gold/kripto intraday az revert).
- Kanıt: Pagonidis IBS effect (indeks ETF), Connors RSI2, IBS çalışmaları — spesifik
  olarak equity indeks. GitHub ref'ler mevcut.

**#2 `roc_pace` — TIME-SERIES MOMENTUM (breakout DEĞİL):**
- Tez: yerleşik çok-bar drift'i sür, ROC rank sağlıklı bandda (0.55-0.97) iken TREND
  ORTASINDA gir — yeni ekstremde asla, tek barda asla, parabolikte dur.
- Trigger: ROC(24-96 bar) rank sağlıklı band + T3 eğim uyumu + ADX ≥ 15 + HTF hizası +
  L-bar hareket ≥ min_atr. `rp_rank_hi` = exhaustion cap (blow-off barı reddet).
- 5 param: `rp_roc_len, rp_rank_win, rp_rank_lo, rp_rank_hi, rp_min_move_atr` + reuse
  `adx_min, htf_factor`.
- **Deploy: BTCUSD/XAUUSD/SpotBrent/NAS100** — burst sembollerinden enstrüman-ayrışması.
  → **SpotBrent'in cevabı olabilir** (burst costed −27, roc_pace trend-takip).
- #2 çünkü momentum SINIFI'nı burst kümesiyle paylaşıyor; "momentum çalışmadı" rejiminde
  aynı şoka açık. Slot'u enstrüman-ayrışması + exhaustion cap ile hak ediyor.
- Kanıt: Moskowitz/Ooi/Pedersen "Time Series Momentum" 2012 (58 futures, indeks+emtia,
  Sharpe ~1.3), Quantpedia, AQR, Kıvanç Özbilgiç PMax/MOST (TR).

**Öneri:** `band_fade` ÖNCE (en yüksek çeşitlendirme, en düşük korelasyon riski) → 4
indekste WFO gate'inden geçir. `roc_pace` #2, band_fade sonucuna göre + SpotBrent testi.
İkisi de aynı WFO/validation kapısından; validate etmezse otomatik retire (kill-criteria
EK13 blok). Kod: `Params` + `OPT_FIELDS` + `Params.key()` + `_FAMILIES` + `STRATEGIES` +
grid + test — Cursor lane.

### EK14 — SL / TAKİP-SL / GİRİŞ / ÇIKIŞ MEKANİK DERİN AUDIT (agent, 03.09 00:01)

**[CRITICAL] C1-shakeout — HÂLÂ CANLI, üçlü-doğrulandı, 1 satır fix.**
`engine.py:2626-2678`: shakeout floor stop'u 2×ATR'ye açıyor ama `lot_for`'a `sl_size`
(1×ATR) geçiliyor → 3 stop/10 sonrası (kayıp serisi 10-16, rutin) **gerçek risk %4**
(en kötü anda). `r_cap` de dar mesafeye bölüyor → o da 2×. `can_open` GENİŞ mesafeyi
görüyor (iç çelişki). `shakeout_size_note` operatöre "risk ayni" DİYOR (artık yanlış).
Commit `fe26ace` bunu getirdi. **FIX: `engine.py:2651` (+2638) `sl_size` → `sl_dist`**
(shakeout yokken zaten eşit). Bu, RE-fleet F2/F8 + bu agent = 3. kez. Cursor'un C1 commit'i
sizing'i düzeltti ama BU ayrı ve hâlâ açık.

**[HIGH] H2 — stale-clock'ta flatten yolları ÖLÜ.**
`engine.py:3299,3349`: weekend/session/day-end flatten `if server_now is not None`
guard'lı; `decision_now()` 600s stale tick'te None döner. Cuma akşamı feed stall →
pozisyon weekend gap'e biner. `_weekend_pending` de yalnız `server_now` varken eklenebiliyor.
FIX: flatten kararları için `broker_now()`/`server_now()` fallback (yanlış-saatte flatten
güvenli; flatten-etmemek değil). Girişler strict `decision_now()`'da kalsın.

**[HIGH] H1 — fill-verify sonucu engine mid-verify durursa kaybolur.**
`_try_entry` daemon thread spawn ediyor (~2.1s sleep); sonuç yalnız `_cycle` içinde
drain. Verify sırasında stop → `_mark_bar_filled` çağrılmıyor → restart'ta `_filled_bars`
kaydı yok → pozisyon downtime'da kapandıysa aynı bar sinyali tekrar ateşler (çift giriş).
FIX: send anında pending-verify persist + `_mark_bar_filled`; startup'ta re-drain.

**[HIGH] H3 — daily-loss + panic flatten (`close_all`) autopsy/sample/log BIRAKMIYOR.**
`close_all` → `close_position` doğrudan, `fill=` yok, autopsy yok. `_reap_execution` de
atlıyor (`DEAL_REASON_EXPERT` `_CLOSED_ELSEWHERE` dışında). En yüksek-riskli çıkışın en
zayıf adli izi. FIX: `close_all`'ı tracked close'dan geçir.

**[MED]** M4 ilk `breakeven_at_r` sub-entry stop koyabilir (guard `breakeven_locked`'a
gated, ilk BE'de false) · M5 `_fill_time_risk` fallback dar `sl_atr_mult` (shakeout
görmezden) · M6 48h ileri-tick toleransı seans kararlarını zehirliyor (fix: ~300s) ·
M7 stale sinyal should_flatten/cooldown pencerelerinde tutuluyor · M8 `min_stop_distance`
spread ile şişiyor, SL-mesafe gate'i yok.

**[LOW — İYİ HABER]** Trail geri gidemiyor ✓ · gap-past-trail doğru ✓ · BE(1.5)/
trail_start(2.5) tutarlı, bu config'te trail sub-entry stop koymaz ✓ · giriş-timing
bug'ı (21-30s stale timer) DÜZELMİŞ ✓ · netting/disconnect sağlam ✓.

**[LOW-ama-önemli] L8:** Hesap-seviyesi zarar freni YOK (`daily_loss_pct=0`). C1-shakeout
(%4 risk) + 10-16 kayıp serisi ile: kötü NAS100 serisi ile hesap arasında tek şey
per-trade hard stop. Operatör kararı ama C1 ile birlikte kritik.

**Ranked fix (Critical/High):** C1 `engine.py:2651` sl_size→sl_dist · H2 `engine.py:3299,
3349` broker_now fallback · H1 `engine.py:2754/1015` persist+mark_bar_filled at send ·
H3 `close_all` tracked. Hepsi Cursor lane, pytest+ruff.

### EK15 — KOD SAĞLIK SWEEP (agent, 03.09 00:0X) — çalışma ağacı KENDİ gate'ini geçmiyor

`pytest`: **4 fail / 2717 pass**. `ruff`: **3 finding**. `import micofx`: temiz.

**[TEST FAIL #1 — 3. CANLI SIZING BUG, en yüksek]:** `risk.py:555-558`: broker `volume_min`
> `r_cap` (2% 1R cap) iken kod işlemi ATLAMAK yerine `volume_min`'e **YUKARI sized ediyor**
(`MAX_MIN_LOT_OVERSHOOT=3.0` → 3× cap'e kadar). $230 hesapta 2% cap sık sık broker
min-lot'un altında → **işlemler ~3× hedeflenen riskle açılıyor**. Commit `fe26ace`
getirdi; C1/C3 fix'i (`8855d65`) DOKUNMADI. C1-shakeout (EK14) + bu = iki ayrı canlı
sizing bug'ı hâlâ açık. FIX seçenek: (a) `risk.py:556-558` clamp-up dalını sil → hep
`return 0.0` (işlem atla), testi geri getir; (b) overshoot'u 1.5×'e indir + testi güncelle.
Araştırma (EK12 F7): "min-lot riski hedefin >1.5×'i ise işlemi atla" → (a) veya (b@1.5).

**[TEST FAIL #2-4]:** `web/static/app.js:930` hâlâ `ichimoku` label (2 test); `test_
indicator_edge_inputs.py:124` bayat bound `21>=22` (ichimoku_lines silindi). → 3 satır fix.

**[RUFF]:** `scripts/apply_trail_step_queue.py:9` unused `sys`; 2 test import-sort. Trivial.

**[ÖLÜ KOD — production'da 0 referans]:** `indicators.py` `parabolic_sar()` (~54 sat),
`stochastic_slow()` (~20), `supertrend()` (~40). RE-fleet'te de flag'lendi, hâlâ duruyor.
`_GATED_FLIPS = frozenset()` boş → `unstamped_gates_to_zero()` garantili no-op (ölü plumbing).

**[EMEKLI KALINTI — load-bearing]:** `stoch_extreme` — C4 temizliğini KAÇIRDI. `SymbolConfig`
+ `Params` + `Params.key()` + `defaults.json` 5 preset bloğu. Hiçbir aile okumuyor;
optimizer signal-cache'i boşuna bölüyor. → C4 tamamla.

**[BAYAT DB]:** `settings.opt = {"strategy_max_combos":{"stoch_flip":28800}}` — **tam ölü
orphan key, OKUYAN YOK** (reader `opt_params` kullanıyor, `opt` değil). Sil. ·
`supervisor_state.verdicts["PLTR.US-24"]` — süresi dolmuş CFD orphan verdict, sil.
`opt_params` blob'u artık temiz.

**[DOCS]:** AGENTS.md pytest+ruff'ı bitiş kapısı yapıyor; ağaç şu an kendi kapısını
geçmiyor (4 test + 3 ruff). Cursor commit öncesi yeşile çekmeli.

**Sıra:** TEST#1 (sizing bug karar) → app.js+test bound (3 sat) → ruff (2 sat) → 3 ölü
indikatör fn (~114 sat) → stoch_extreme (C4 tamamla) → orphan `opt` key + PLTR verdict.
Hepsi Cursor lane.

Uyarı: tek pencere ~18k bar son segment; GER40 M30 proxy (canlı M5); apply = full WFO.

### EK3 — burst gates (cost_rank_max / atr_pct_min) costed sweep (02.09 20:40, salt-okur)

| snapshot | canlı (cr=0,ap=0) | cr=0.3 | cr=0.5/0.7 | atr_pct etkisi |
|----------|-------------------|--------|------------|----------------|
| **GER40_M30**\* | +21.4 | **+35.5** (ap=0), +36.3 (ap=0.1) | +21.4 (inert) | ap↑ → net_r↓ |
| GER40_M15\* | −33.6 | −22.8 | −33.6 | hep negatif |
| **JPN225_M15** | +48.3 | **+19.8** (−28R!) | +48-49 (inert) | ap↑ → 48→39→10 |

**Ölçülen sonuç — burst içinde bile aile değil SEMBOL-spesifik:**
- **GER40 burst: `cost_rank_max=0.3`** → +14R costed (M30 proxy). Ailenin M5'te taşımak
  için tasarlandığı gate; GER40'ın 03:15 pre-open saatlerindeki ince-range popülasyonunu
  filtreliyor. (agent 4 E2 ile birebir.)
- **JPN225 burst: gate DEĞİŞTİRME** — `cost_rank_max=0.3` yıkıcı (−28R), yüksek cr inert,
  `atr_pct_min` her seviyede zarar. JPN225/M15 canlı zaten optimal.
- `atr_pct_min` hiçbir burst'te yardımcı değil.

### EK4 — F5: seans-saati autopsy kırılımı (02.09 20:40, salt-okur)

Broker saati (naive epoch → gmtime, autopsy `fill_time` bucketing). n=319.

**KİTAP GENELİ — negatif saatler:** `hr 16: −17.0R / n=28 / %18 win` (tek en kötü, büyük
örnek, 4 sembolde de negatif) · hr 12 −8.7/n10/%0 · hr 13 −8.5/n12/%8 · hr 5 −6.1 · hr 6 −4.7.
**Pozitif:** hr 10 +13.1/n21 · hr 14 +9.4/n17 · hr 23 +3.3/n11/%64 · hr 8 +2.8/%50.

**Per-sembol (küçük örnek — WFO doğrulaması şart):**
- **US30 (en güçlü):** neg hr 13/16/21/22 (+18) toplam ≈ −22R; poz hr 10/14/19/23 ≈ +27R.
  Bu 4-5 saati bloklamak tarihsel −3.4R → **~+22R**.
- **GER40:** tek iyi saat hr 10 (+5.8); pre-open (hr 3-8, genişletilmiş 03:15 seansı)
  çoğu negatif/mikro; hr 11/16 −3R. → cash session'a (~hr 8-15) daralt + hr 16 blok.
- **NAS100:** neg hr 1/4/6/16/17; poz hr 20-22. hr 16-17 bloğu −6.4R.
- **JPN225:** neg hr 6/10/12-15/19; hr 12-15 bloğu −11.7R.

**Sonuç:** en sağlam sinyal `hr 16` kitap-geneli (n=28, −17R). Konservatif hamle: **hr 16
kitap-geneli blok + GER40 genişletilmiş 03:15 pre-open seansını kaldır** (F-E5). İnce
per-sembol saat blacklist'i curve-fit riski — WFO'da doğrula. `hour_risk_scales` kancası
zaten var (supervisor `bad_hour_min_trades=80` bu frekansta atıl — eşiği ~6-8'e çek).

### EK5 — Disabled sembol reopen tablosu (02.09 20:52, salt-okur — OPERATÖR kararı)

Costed holdout last-seg, canlı-benzeri config + en iyi adx_min/trail_step.

| sembol | aile/TF | baseline costed | en iyi adx_min | en iyi trail_step |
|--------|---------|-----------------|----------------|-------------------|
| **GOLD-PERP** | mtf_pullback/M30 | **+114.3** (C1 run) | — | — |
| **XAUUSD** | burst/M15 | **+83.4** | adx=20 → **+94.6** (exp .223) | step=1.0 → +83 |
| **BTCUSD** | burst/M30 | +58.5 | adx=15 → +60.6 (exp .205) | step=2.2 |
| SpotBrent | burst/M30 & M15 | −27 / −18 | −27 / −15 | −23 / −24 |

**Sonuç:** GOLD-PERP + XAUUSD + BTCUSD costed holdout'ta **canlı 4'ün 3'ünden güçlü**
(JPN225 +48, NAS100 +24, US30 +18, GER40/M30 +21). SpotBrent her TF costed zararda →
disabled kalsın. Uyarı: tek pencere, iyimser; canlıda XAUUSD +9.8R / SpotBrent +2.1R
(küçük örnek). Reopen = operatör red + full WFO.

**GOLD-PERP mtf_pullback/M30 detay (20:56 sweep):** baseline (adx_min=0, sl 1.5,
trail 3.0/1.8) = **+114.3R / exp +0.219 / PF 1.35 / n=523**. adx_min: **0 en iyi**
(15→+104.7, 20→+61.9) — NAS100 mtf_pullback'in adx_min=15'ten faydalanmasının TERSİ.
→ desen "aile-spesifik" değil **enstrüman+aile**: index yapı-giriş aileleri ADX
floor'dan fayda görüyor, commodity (GOLD) görmüyor. trail_step 1.6 marjinal en iyi
(+115.8), canlı 1.8 zaten yakın-optimal. **GOLD-PERP en temiz reopen adayı — param
ayarı gerekmiyor.**

---


### EK16 — PER-SEMBOL BEST-CONFIG SWEEP (03.09 00:14) — US30/GER40 YANLIS AILEDE, SpotBrent DUZELIYOR

~400 costed replay, sabit burst/channel base × adx{0,15} × step{0.8,1.6,2.5} × cost_rank{0,0.3,0.5} × close_pct{0.7,0.8,0.9} / chan_lookback{40,60,100}. Tek-pencere, curve-fit riski var -> WFO ADAY tohumu, apply degeri DEGIL.

| sembol | CANLI (aile / costed) | BEST-FOUND | best costed | fark |
|--------|------------------------|------------|-------------|------|
| **US30** | channel_break/M30 adx15 step0.8 / **+42** | **burst** adx0 step0.8 cr0.5 cp0.7 | **+113** | **+71R** aile degisimi |
| **GER40** | channel_break/M30 adx15 / **+8** | **burst** adx0 step2.5 cr0.3 cp0.7 | **+58** | **+50R** aile degisimi |
| **SpotBrent** | burst/M30 adx0 step1.8 cr0.5 / **−27** | burst adx0 **step2.5 cr0** cp0.7 | **+50** | **+77R** -> POZITIF FLIP (roc_pace gerekmez) |
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



### EK17 — ROBUSTLUK KONTROLU (03.09 00:22) — EK16'nın US30/SpotBrent ÖNERİLERİ CURVE-FIT, GERİ ALINIYOR

EK16 tek-pencere costed (yalnız son segment). 6 alt-pencereye böldüm (her ~15k bar,
rolling-OOS proxy). Research #2 kriteri: config ≥4/6 pencerede pozitif olmalı.

| config | 6 alt-pencere net_r | pozitif | verdict |
|--------|---------------------|---------|---------|
| **US30 burst "BEST"** (EK16 +113) | +46 +30 **−61 −59 −35** +93 | 3/6 | **MIXED — +113 TAMAMEN son pencere. REJİM ARTEFAKTI.** |
| **US30 channel_break CANLI** | −5 +14 +6 +1 +6 +57 | 5/6 | **ROBUST — mevcut config zaten doğru.** |
| GER40 burst "BEST" (EK16 +58) | −14 −30 −15 +4 +61 +31 | 3/6 | MIXED — ilk yarı negatif, rejim-bağımlı |
| **SpotBrent burst "BEST"** (EK16 +50 "flip") | **−230 −124 −9 −93** +14 +20 | 2/6 | **FRAGILE — "flip" son 2 pencere şansı. burst SpotBrent'i ÇÖZMÜYOR.** |
| SpotBrent burst LIVE-ish | −173 −83 −17 −83 +13 −16 | 1/6 | FRAGILE |
| **NAS100 burst adx15 cr0** | −15 +11 +1 +25 +90 +56 | 5/6 | **ROBUST (+168R) — bu GERÇEK.** |

**DÜZELTME (EK16 geri alınıyor):**
- **US30 → burst YAPMA.** +113 son-pencere rejim artefaktıydı; burst US30 3/6 pencerede
  derin negatif. **Mevcut channel_break config ROBUST (5/6). US30'a DOKUNMA.**
- **SpotBrent burst'te ÇALIŞMIYOR.** "+50R flip" 6'da 2 şanslı pencere; 4/6 pencere
  −9..−230R. SpotBrent → `roc_pace` (TSMOM) ADAYI ya da disabled kalsın. burst DEĞİL.
- **GER40 burst: temkinli** (3/6). Son rejim lehte ama ilk yarı negatif — WFO'nun
  regime-spread gate'i karar versin, tek-pencere "aday" yeterli değil.
- **NAS100 burst + adx_min=15 + cost_rank_max=0: ROBUST (5/6), +168R.** Bu uygulanabilir.
  cr 0.7→0 + adx 0→15.

**Ders:** EK2-EK16 tek-pencere costed sweep'lerim multiple-comparisons tuzağı. "En iyi"
diye bulduğum çoğu config son rejime fit olmuş. **Robustluk kontrolü (≥4/6 alt-pencere)
apply-öncesi ZORUNLU** (research #2, P1). Bundan sonra sweep sonuçlarını sub-window ile
teyit ediyorum.



### EK18 — ROBUSTLUK: kalan semboller (03.09 00:35) — KİTAP ÇOĞUNLUKLA ZATEN İYİ

| config | 6 alt-pencere | pozitif | verdict |
|--------|--------------|---------|---------|
| **XAUUSD CANLI** | +14 +113 +68 +44 +49 +48 | **6/6** | **ROBUST +335R — dokunma** |
| **JPN225 CANLI** | +4 +5 +11 −27 +27 +60 | **5/6** | **ROBUST +79R — dokunma** |
| JPN225 +cr0.5+cp0.9 | ~aynı | 5/6 | +2R marjinal — değişmeye değmez |
| **BTCUSD CANLI** | +36 +2 +13 +47 +20 +42 | **6/6** | **ROBUST +161R — dokunma** |
| BTCUSD cr0.3+cp0.9 | 6/6 ama +101R | 6/6 | canlıdan KÖTÜ — değiştirme |
| GOLD channel_break | +31 +23 −27 −15 +62 +65 | 4/6 | ROBUST +140R |
| GOLD burst | +29 −4 +27 −38 +86 +75 | 4/6 | ROBUST +175R |
| **GOLD mtf_pullback (as-is)** | +18 −2 +43 +16 +76 +104 | **5/6** | **ROBUST +255R — GOLD için EN İYİ + en tutarlı** |

**Robust-doğrulanmış NİHAİ tablo (EK17 + EK18):**

| sembol | verdict | AKSIYON |
|--------|---------|---------|
| **NAS100** | burst adx15 cr0 = ROBUST 5/6 +168R | **UYGULA: cost_rank_max 0.7→0, adx_min 0→15** |
| US30 | channel_break CANLI = ROBUST 5/6 | **dokunma** (EK16 "burst" curve-fitti) |
| GER40 | burst 3/6 MIXED | WFO regime-gate karar versin |
| JPN225 | CANLI = ROBUST 5/6 | dokunma |
| XAUUSD | CANLI = ROBUST 6/6 +335R | dokunma |
| BTCUSD | CANLI = ROBUST 6/6 +161R | dokunma |
| SpotBrent | burst FRAGILE 2/6 | roc_pace (#2 aile) VEYA disabled |
| GOLD-PERP | mtf_pullback ROBUST 5/6 +255R | add = **mtf_pullback** (aile aramada KALMALI) |

**Ölçülen sonuç:** Cursor'un apply'ları oturdu; kitap **çoğunlukla zaten robust config'te**.
"Tüm sembolleri en iyi hale getir" cevabı EK16'nın sandığından çok DAR:
- Tek net config değişikliği: **NAS100** (cr 0.7→0, adx 0→15).
- 4 sembol zaten robust — bırak.
- GER40 → WFO. SpotBrent → roc_pace. GOLD-PERP add → mtf_pullback.
- **mtf_pullback aramadan DÜŞÜRÜLMEMELİ** (GOLD-PERP'in tek robust ailesi).
Asıl kalan alpha config tuning'de değil: **sizing/exit bug fix'leri** (C1-shakeout, T1-minlot,
3 exit HIGH) downside'ı upside tuning'den daha çok etkiliyor.


## 02.09 19:35 — Claude A–Z hard/stres tarama (ölçümlü, kod YOK)

Operatör: API+web+her şey, çalışmayan/ölü/bayat/emekli/okunmayan ne varsa ayrı ayrı;
kalkan özelliklerden kaynaklı sorunlar; kaçan işlem/kâr tek tek; ölçümlü, öneri değil;
bulgular Cursor'a → doğrulayıp plan. Hiçbir şey PATCH edilmedi, arama/flatten/capture/
restart/commit YOK. HEAD `4528b40`. Canlı: 1 ticket (NAS100), marj ~%6.5/70, kasa ~$225.

**Çalışma ağacı temiz DEĞİL:** `micofx/engine.py` (+18) ve `micofx/execution.py` (+87)
commit'siz WIP; untracked `scripts/start_bridge_daemon.ps1`, `tests/test_note_fill_
repairs_poisoned_sl.py`. Bazı test kırıkları bu WIP'ten olabilir (F-T3).

### 1) Optimization Summary

* **Sağlık:** Test paketi KIRMIZI — `4528b40`'ta **19 fail / 2720 pass** (+2 ruff
  import-sort, test dosyaları). Canlı defter **−41.2 R / −$826.60 / 319 işlem**
  (14 gün), tüm zarar `sl` kovasında (**−156 R / 166 işlem / avgR −0.94**). Cost-free
  mod, "her cost-free apply'ın yanında maliyetli sayı" güvenlik ağını (72cbfb1/fba488b)
  sessizce kapatmış → hangi canlı config'in paper-pozitif/charged-negatif olduğu artık
  ÖLÇÜLMÜYOR. Auto-pilot 17 günlük sıfırlanmamış `entry_blocks` sayacına göre karar
  veriyor (bayat sinyal).
* **En yüksek etkili 3:** (1) F-D1 cost-free apply maliyet damgasını + costed-negatif
  reddini kapatıyor (3 test kırık, holdout↔canlı ayrımının kör noktası). (2) F-E1/E2
  yapısal sinyal kaybı: `risk_sembol_limiti` 259 + `risk_ters_yon` 223 sinyal-barı
  düşüyor; fill oranları US30 %22, GER40 %29. (3) F-D3 `entry_blocks` 2026-08-16'dan
  beri sıfırlanmıyor → auto-pilot "SPREAD US30 kalibre" önerisini kapalı gate + bayat
  sayaç üzerine tekrar tekrar üretiyor.
* **Değişmezse en büyük risk:** kırmızı test paketi = regresyon dedektörü yok; canlı
  −R üretmeye devam ederken (avgR −0.13) devre kesici kapalı (`daily_loss_pct=0`),
  concurrent risk %46, marj tavanı %78, ~$225 hesap 1:500. Kayıp motoru frensiz.

### 2) Findings (öncelik sırası)

Her bulgu ölçümlü. "Removal Safety" ve "Reuse Scope" verildi. Kanıt = dosya:satır
veya DB anahtarı + sayı.

---

**F-D1 — Cost-free mod maliyetli-holdout damgasını ve costed-negatif reddini kapatıyor**
* Kategori: Reliability / Cost · Severity: **Critical**
* Etki: holdout↔canlı ayrımı ölçülemez; `--force` ile charged-negatif config canlıya
  geçebilir.
* Kanıt: `micofx/optimizer.py` `apply()` (~2093–2105) — `charging = bool(store.system
  and store.system.charge_costs)`; `if detail is not None and charging:` bloğu costed
  eval + `costed_negative` reddini sarıyor. `charge_costs=False` (DB `system`) → blok
  hiç çalışmıyor → `opt_summary` içinde `holdout_costed` YOK, `costed_negative` YOK.
  Kırık testler: `tests/test_holdout_costed_on_apply.py::test_negative_costed_holdout_
  is_not_applied` (ok=True bekleniyordu False), `::test_force_still_applies_a_costed_
  negative_candidate` (KeyError `costed_negative`), `::test_positive_costed_holdout_is_
  stamped_without_the_flag` (KeyError `holdout_costed`).
* Neden verimsiz: 72cbfb1 "An applied configuration carries its own held-out record" +
  fba488b "Put a charged number beside every cost-free apply" bilerek eklenmişti; bu
  gate onu geri alıyor. Canlı 4 config'in kaçının paper-pozitif/charged-negatif olduğu
  bilinmiyor — tam da −41R/+90R ayrımını yakalayacak enstrüman.
* Removal Safety: **Needs Verification** (bilinçli mi, regresyon mu — Cursor).
* Reuse Scope: service-wide (optimizer apply + auto-pilot raporu + supervisor).
* Beklenen etki: charged sayı geri gelirse costed replay ile 4 aile yeniden sıralanır; (arsiv)
  M5/M15 burst seçimlerinin ~0.1–0.3R/işlem fantom edge taşıdığı hipotezi ölçülebilir.

**F-D2 — Fill/trade log satırında canlı maliyet payı boş**
* Kategori: Reliability · Severity: Low
* Kanıt: `tests/test_fill_trade_line_carries_magic.py::test_the_fill_trade_line_names_
  magic_and_live_cost_share` → `cost_bit = ""`. Cost-free mod maliyet payını kaldırıyor.
* Removal Safety: Likely Safe (kozmetik) ama F-D1 ile aynı kök: "maliyet görünürlüğü"
  toptan kapanmış.
* Reuse Scope: module (fill logging).

**F-D3 — `entry_blocks` sayaçları 17 gündür sıfırlanmıyor; auto-pilot bayat sayıya göre karar veriyor**
* Kategori: DB / Reliability · Severity: **High**
* Kanıt: DB `entry_blocks_since = 1786905256` = 2026-08-16 18:34 (16.9 gün). Cost-free
  mod ~5 commit önce (ced7e08). `entry_blocks.US30.primary.signals.spread = 144`,
  `SpotBrent...spread = 213` — cost-free ÖNCESİ döneme ait. Enabled index isimlerde
  `max_spread_atr = 0.0` (kapalı). Yine de `scripts/income_dev_loop.py:196-223`
  `spread_recovery_actions` bu kümülatif sayaçtan "SPREAD US30/JPN225/GER40 kalibre"
  üretiyor; `cursor/FOR_CLAUDE.md` her tick tekrarlıyor.
* Neden verimsiz: karar sinyali gürültülü/geçmişe dönük; auto-pilot no-op iş öneriyor,
  `apply_spread_calibration` charge_costs=false'ta zaten atlıyor → sonsuz "atlandı" logu.
* Removal Safety: Needs Verification (sayaç rotasyonu / pencere ekle).
* Reuse Scope: service-wide (auto-pilot + panel entry-blocks analizi).

**F-D4 — 11 ölü `Params`/`SymbolConfig` alanı (emekli aileler)**
* Kategori: Memory / Maintainability (Dead Code) · Severity: Low
* Kanıt: `micofx/strategy.py:58-82` ve `micofx/models.py:120-141` — `t3_fast,
  t3_slow_mult, t3_fast_vf, t3_accel_min, st_period, st_mult, stoch_k_period,
  stoch_k_smooth, stoch_d_smooth, psar_af_step, psar_af_max`. `opt_fields_read`
  çıktısı (ölçüldü) 4 canlı aile için bunların HİÇBİRİNİ içermiyor. Hâlâ:
  `Params.key()` tuple'ında (satır 145-150) ve `required_bars()` içinde
  (satır 770-773: `int(p.t3_fast*max(1.2,p.t3_slow_mult))*20`, stoch_k toplamı*8)
  her çağrıda hesaplanıyor.
* Neden verimsiz: her `required_bars` çağrısında ölü aritmetik; `key()` tuple'ı 11
  eleman şişik (sinyal cache anahtarı). Bağlanmıyor ama drift riski + kafa karışıklığı.
* Removal Safety: **Likely Safe** — canlı aile okumuyor; `from_config` geriye-uyumlu
  kalır (eksik alan default). DB payload'da varsa yok sayılır.
* Reuse Scope: module (strategy + models + optimizer grid).

**F-D5 — DB `opt_params.strategies` emekli aileleri listeliyor + `strategy_max_combos.stoch_flip`**
* Kategori: DB / Cost (Dead Config) · Severity: Medium
* Kanıt: DB `opt_params.strategies = ['mtf_pullback','burst','dual_t3','t3_flip',
  'stoch_flip','parabolic_flip','ichimoku','channel_break']` — 4'ü emekli (AGENTS.md
  "Leftover DB names fail closed"). DB `opt = {"strategy_max_combos":{"stoch_flip":
  28800}}`. `micofx/optimizer.py:109-110,168` stoch_flip'i özel-kılıf yapıyor;
  ledger'a göre `stoch_flip` 28800 ≈ 3.08 M kombinasyon duvarının 2.07 M'i.
* Neden verimsiz: arama bütçesinin büyük kısmı ÖLÜ bir aileyi modellemeye ayrılmış
  (fail-closed olsa da combo tahsisi/coverage_budget hesabı onu sayıyor).
* Removal Safety: Needs Verification (DB yazımı panel/HTTP 400 — `opt_params` write
  yolu AGENTS.md'e göre kısıtlı; nasıl temizleneceği Cursor).
* Reuse Scope: service-wide (optimizer combo budget).

**F-D6 — `ichimoku` artık htf_factor/adx okuyor ama 4 test eski "unread" halini iddia ediyor**
* Kategori: Maintainability / Reliability · Severity: Medium
* Kanıt: `_ichimoku` → `_trend_gate(cache,p)` (`strategy.py:579`) `p.htf_factor`/
  `p.htf_mode` okuyor; `_common`→`_regime` adx okuyor. `opt_fields_read('ichimoku')`
  (ölçüldü) = `{adx_max, adx_min, atr_pct_min, htf_factor, min_body_ratio, ...}`.
  Kırık: `tests/test_kivanc_combo_families.py::test_ichimoku_is_unread_flip_shaped`,
  `tests/test_required_bars_ignores_unread_htf.py::test_unread_htf_factor_does_not_
  inflate_required_bars`, ve `test_kivanc_combo_families` htf_factor varyantı. Değişim
  commit `715c32e` "Strengthen ichimoku and pullback families". `absent_regime_gates_
  to_zero` guard'ı artık ichimoku'yu da kapsıyor (bkz. tick-1 audit).
* Removal Safety: N/A — testler koda göre güncellenmeli (davranış bilinçli görünüyor).
* Reuse Scope: module (strategy + testler + `required_bars`).

**F-D7 — `test_enable_requires_optimised` x8: `_Engine` stub'ında `.supervisor` yok**
* Kategori: Reliability · Severity: Medium
* Kanıt: 8 test `AttributeError: '_Engine' object has no attribute 'supervisor'`.
  Traceback → `micofx/web/app.py:705` `_on_symbol_newly_enabled` sembol enable
  edilince `engine.supervisor`'ı koşulsuz dereference ediyor. Testin sahte Engine'i
  bu attr'ı taşımıyor.
* Neden önemli: canlı Engine her zaman `.supervisor` taşıyorsa sadece bayat stub;
  taşımadığı bir yol varsa enable sırasında AttributeError (latent).
* Removal Safety: Needs Verification (canlı Engine invariant'ı — Cursor doğrulasın:
  `getattr(engine,"supervisor",None)` guard mı, yoksa stub mı düzelecek).
* Reuse Scope: module (web enable path + testler).

**F-D8 — `kasa_auto` testleri x2: growth-mode hedefleri testle çelişiyor**
* Kategori: Reliability / Cost · Severity: **High** (canlı risk parametrelerini sürüyor)
* Kanıt: `tests/test_kasa_auto.py:18` `assert 0.92 == 0.85` (lot_multiplier),
  `:44` `assert 78.0 == 68` (max_margin_usage_pct). Commit `25e6674` "kasa growth mode"
  hedefleri değiştirdi, test güncellenmedi. `scripts/kasa_auto.py` canlıya
  `lot_multiplier` + `max_margin_usage_pct` PATCH'liyor (auto-pilot her tick).
* Neden önemli: test ya bayat (bilinçli growth) ya da growth hedefleri fazla agresif
  ve test kanaryası. Şu an DB: lot_multiplier 0.92, margin %78 — test 0.85 / %68 diyor.
* Removal Safety: Needs Verification — operatör + Cursor: growth hedefleri onaylı mı?
* Reuse Scope: service-wide (kasa_auto canlı PATCH + auto-pilot).

**F-D9 — `execution_samples` telemetrisi ölü/bozuk**
* Kategori: Reliability / Observability · Severity: Medium
* Kanıt: DB `execution_samples` = 17 günde 7 satır; en az biri düz `str` (dict değil —
  `AttributeError: 'str' object has no attribute 'get'` okuma denemesinde). Canlı
  slippage ölçülemiyor → "backtest↔canlı slippage farkı" (literatür #1 sebep) sayıyla
  gösterilemez.
* Removal Safety: Needs Verification (yazım yolu bozuk mu, yoksa kullanılmıyor mu).
* Reuse Scope: module (execution + panel).

**F-D10 — `supervisor_state` freshness damgası yok**
* Kategori: Reliability · Severity: Low
* Kanıt: DB `supervisor_state` anahtarları = `['verdicts','risk_scale']`, `updated_at`
  yok. NAS100 net −36.03 verdict'inin ne kadar güncel olduğu bilinemez.
* Reuse Scope: module (supervisor + auto-pilot ranked tablo).

---

**F-E1 — `risk_sembol_limiti` (1 ticket/isim) 259 sinyal-barı düşürüyor**
* Kategori: Algorithm / Cost (kaçan işlem) · Severity: **High**
* Kanıt: DB `entry_block_events` (son 1472): `risk_sembol_limiti` 259 —
  GER40 82, US30 83, JPN225 54, NAS100 22 (DB `entry_blocks.<sym>.primary.signals`).
  Aile pozisyon açıkken 2./3. sinyali üretiyor, hepsi atılıyor.
* Neden verimsiz: yapısal sinyal kaybı; en çok GER40/US30. AGENTS.md "Live count is
  1 ticket per name" bilinçli — ama pyramiding/re-entry hiç ölçülmemiş.
* Karşı-olgu (ölçülmeli, Faz-1): cap 2'ye çıkarsa GER40+82 / US30+83 sinyal-barı
  uygun olur; MEVCUT canlı beklenti avgR −0.13 / win %34 ile bu **negatif EV** —
  rejim filtresi (F-E4) ile eşleşmeden tek başına açma. Sayı: 259 × (−0.13 R) ≈
  −34 R "kaçırılan" ama negatif, yani şu an cap KORUYUCU.
* Removal Safety: Needs Verification — costed + regime-filtered replay olmadan dokunma.
* Reuse Scope: service-wide (risk.py + engine entry gate).

**F-E2 — `risk_ters_yon` (ters yön gate) 223 sinyal-barı düşürüyor; ters sinyal çıkışa çevrilmiyor**
* Kategori: Algorithm / Cost (kaybedilen kâr) · Severity: **High**
* Kanıt: `entry_block_events` `risk_ters_yon` 223 — US30 77, JPN225 56, SpotBrent 48,
  GER40 23. Açık long dururken short sinyal (veya tersi) → **atılıyor**, pozisyon
  kapatma/flip için kullanılmıyor.
* Neden verimsiz: `sl` kovası 166 tam-stop / avgR −0.94 = tüm zarar. Bu 166'nın bir
  kısmı stop yemeden önce ters sinyal üretmiş olabilir (erken çıkış fırsatı).
* Karşı-olgu (ölçülmeli, Faz-1): `entry_block_events(risk_ters_yon)` → `trade_
  autopsies` join (symbol + [fill_time, exit_time] penceresi). Kaç `sl` çıkışı,
  stoptan önce ters sinyal gördü? Her biri ~(mfe_r − (−1)) R kurtarma potansiyeli.
  Kaba tavan: 166 sl × ort. left_on_table yok ama mae_r ~0.9 → ters-sinyal-çıkış
  bu işlemleri ~−1R yerine ~breakeven'a çekebilseydi ≈ +80–120 R aralığı (ÜST SINIR,
  doğrulanacak).
* Removal Safety: Needs Verification — "ters sinyalde flat" yeni davranış; costed
  backtest'te ölç, exit modelini değiştirmeden (sadece erken çıkış).
* Reuse Scope: service-wide (engine signal handling + backtest simulate).
* **ÖLÇÜM 02.09 19:40 (join yapıldı, tez ZAYIFLADI):** 223 `risk_ters_yon` olayının
  131'i bir açık-işlem penceresine düşüyor. Bu 131'in çıkışı: **`trail` 101 (kârlı!)**,
  `flatten` 6, `sl` yalnız 24. Yani ters sinyallerin çoğu, sonradan trail ile kâra
  giden işlemler sırasında geldi — "ters sinyalde kapat" 101 kazananı keserdi.
  Ters sinyal görüp KÖTÜ çıkan farklı işlem sayısı **32** (realised −24.7 R / −$249),
  yoğunluk JPN225 (14, −11 R) + US30 (9, −9 R). Kurtarma tahmini **düşük ~+9 R /
  yüksek ~+23 R**, medyan 1 ters sinyal/işlem. **Sonuç:** blanket "ters sinyalde flat"
  net NEGATİF/marjinal. Koşullu varyant (yalnız işlem >0.5R zararda + ters sinyal,
  JPN225/US30 alt kümesi) curve-fit riski — costed backtest olmadan canlıya alınmaz.
  Severity **High -> Medium**.

**F-E3 — Fill oranları: US30 %22, GER40 %29, JPN225 %33; SpotBrent %6**
* Kategori: Cost (kaçan işlem) · Severity: Medium (bilgi + F-E1/E2/D3'e bağlı)
* Kanıt: DB `entry_blocks.<sym>.primary.signals` `acildi` / toplam:
  GER40 56/191 (%29), JPN225 91/280 (%33), NAS100 62/120 (%52), US30 98/450 (%22),
  XAUUSD 45/70 (%64), SpotBrent 19/335 (%6). Blokör dağılımı F-E1 (sembol dolu) +
  F-E2 (ters yön) + spread (F-D3 bayat) + `bar_bosluk` (M5/M15 gece boşluğu, 138).
* Removal Safety: N/A (ölçüm).
* Reuse Scope: service-wide.

**F-E4 — Rejim filtresi tamamen kapalı (tüm canlı isimlerde adx_min=adx_max=0)**
* Kategori: Algorithm · Severity: **High**
* Kanıt: DB symbols payload — GER40/JPN225/NAS100/US30 hepsinde `adx_min=0`,
  `adx_max=0`. `_regime()` (`strategy.py:407-413`) her iki dal da no-op → filtre yok.
  Grid'de `adx_min [0,15,20]` zaten var (`config/defaults.json`). Literatür: ADX
  filtre (eşik 20/25), sinyal değil.
* Karşı-olgu (ölçülmeli): per-sembol `adx_min>0` costed holdout araması. `sl` kovası
  166 işlem çoğunlukla chop girişi hipotezi — ADX≥20 filtresi bunların X'ini eler.
* Removal Safety: N/A (ekleme değil, mevcut ekseni aramak).
* Reuse Scope: service-wide (optimizer search + strategy compute).

**F-E5 — GER40 seansı 03:15–22:59'a genişletilmiş (defaults 10:00)**
* Kategori: Cost · Severity: Medium
* Kanıt: DB `symbols.GER40.sessions = [{start:"03:15", end:"22:59"}]`; `config/
  defaults.json` index preset 16:30–22:55, GER40 override 10:00–22:55.
  GER40 burst/M5 canlı −6.9 R, fill %29, `bar_bosluk` bloklu.
* Neden verimsiz: burst/M5 nakit-açılış öncesi ince saatlerde ateşliyor; spread geniş,
  hacim düşük — literatürde en pahalı/R dilim.
* Removal Safety: Needs Verification (seans daraltma canlı param — operatör/Cursor).
* Reuse Scope: symbol config.

**F-E6 — `lot` bloğu: 38 sinyal-barı undersize (JPN225 23)**
* Kategori: Cost · Severity: Low
* Kanıt: `entry_block_events` `lot` 38; DB `entry_blocks` signals: JPN225 23,
  US30 6, XAUUSD 6, NAS100 3. ~$225 hesap, 2% risk / SL mesafesi broker min-lot'un
  altında → işlem atlanıyor. Auto-pilot "LOT engeli" alarmı her tick.
* Removal Safety: N/A (hesap büyüklüğü fonksiyonu; kasa büyüdükçe azalır).
* Reuse Scope: risk.py sizing.

---

**F-T1 — Canlı performans: −41.2 R / −$826.60 / 319 işlem (14 gün)**
* Kategori: — (ölçüm, kök F-D1/E2/E4) · Severity: **Critical**
* Kanıt: DB `trade_autopsies` (n=319, 2026-08-19→09-02): sumR −41.2, nakit −826.60,
  win %34, avgR −0.129. Cikis: `sl` n=166 avgR **−0.94** (−156 R) · `trail` n=100
  avgR +0.84 (+84 R) · `flatten` n=48 avgR +0.59 (+28 R) · `manuel` n=5 +2.3.
  Son 100: −25.8 R. Son 20: +1.2 R. MFE-capture (`r_realised/mfe_r`, mfe≥0.3R,
  n=218) medyan **0.00**, ort −0.41 (sağlıklı > 0.5).
* Yorum: kitabı ayakta tutan tek kova `flatten` (seans/gün-sonu zorunlu çıkış).
  `sl` kovası tüm zararı yazıyor → sorun giriş kalitesi + tam-stop sıklığı, trail
  değil (trail kovası pozitif).

**F-T2 — En yüksek holdout'lu iki isim canlıda en çok kaybeden**
* Kategori: — (ölçüm) · Severity: **High**
* Kanıt: canlı sumR: NAS100 **−18.7**, JPN225 **−17.4**, GER40 −6.9, US30 −3.4;
  XAUUSD **+9.8** (disabled), SpotBrent +2.1 (disabled). Holdout net R: NAS100
  **+91.8**, JPN225 +68.3, XAUUSD +113.6, GER40 +53.6, US30 +37.6. Korelasyon ters.
* Yorum: holdout (cost-free, F-D1) canlı geliri öngörmüyor. Costed replay şart.

**F-T3 — 19 test fail / 2 ruff hatası `4528b40`'ta + kirli çalışma ağacı**
* Kategori: Reliability (regresyon dedektörü yok) · Severity: **High**
* Kanıt: `pytest -q` → `19 failed, 2720 passed, 1 xfailed` (108 s). Gruplar:
  F-D1 (3), F-D6 (3), F-D7 (8), F-D8 (2), `test_fill_trade_line_carries_magic` (1,
  F-D2), `test_original_sl_survives_restart` (1, muhtemel WIP execution.py),
  `test_empty_patch_is_rejected::test_bulk_changed_counts_only_real_diffs` (1),
  `test_install_brings_the_tools_it_configures` (1, KUR.ps1 adım sayacı /7). Ruff:
  `tests/test_burst_and_channel_honour_body_ratio.py`,
  `tests/test_note_fill_repairs_poisoned_sl.py` import sıralaması.
* Removal Safety: N/A — testler/kod uzlaştırılmalı (çoğu bayat test, F-D1 gerçek risk).

---

**F-P1 — God-file'lar: engine.py 4712 LOC / 116 fn, web/app.py 2285/80, mt5client 2218/62, optimizer 2305/48**
* Kategori: Maintainability · Severity: Medium
* Kanıt: `wc -l` + `grep -c "^\s*def"`. engine.py 2 sınıf, 116 fonksiyon tek dosyada.
* Neden önemli: değişiklik riski yüksek; test izolasyonu zor; F-D6/D7 gibi
  "değiştir ama testi/guard'ı unut" hataları bu yüzeyde tekrar ediyor.
* Removal Safety: N/A (refactor, davranış korunmalı — Cursor kararı).
* Reuse Scope: service-wide.

**F-P2 — `_cycle` her 2 sn'de sıralı MT5 round-trip'leri tek RLock altında**
* Kategori: Concurrency / I/O · Severity: Low-Medium (likely, ölçüm gerek)
* Kanıt: `micofx/engine.py:857` `_cycle`; `refresh_account(force=True)` (863),
  `_probe_book_ticks` (867), `_reload_positions` (891) sıralı. `mt5client.py` 39 lock
  bölgesi. `/api/state` (her 3 sn) aynı lock (AGENTS.md gotcha). Ledger `last_cycle_ms`
  geçmişte 3–7 ms → şu an dar değil ama opt `busy` iken snapshot fallback var.
* Ölçülecek: yük altında `last_cycle_ms` p95; `/api/state` latency opt çalışırken.
* Removal Safety: N/A.
* Reuse Scope: engine + web + mt5client.

**F-P3 — Arama combo duvarı ~3.08 M'in ~2.07 M'i emekli `stoch_flip`'e ayrılmış**
* Kategori: Cost / CPU · Severity: Medium
* Kanıt: `micofx/optimizer.py:109-110` yorum + `:168` `strategy_max_combos.stoch_flip
  = 28800`; DB `opt.strategy_max_combos` aynı. stoch_flip fail-closed ama combo
  bütçesi/coverage_budget hesabı onu sayıyor.
* Beklenen etki: dead family combo tahsisi kalkarsa canlı 4 aile daha derin taranır (arsiv)
  (aynı duvar bütçesiyle).
* Removal Safety: Needs Verification (DB opt_params write yolu kısıtlı).
* Reuse Scope: optimizer.

**F-P4 — `required_bars()` her çağrıda ölü aile lookback terimleri hesaplıyor**
* Kategori: CPU (micro) · Severity: Low
* Kanıt: `strategy.py:770-773` — `int(p.t3_fast*max(1.2,p.t3_slow_mult))*20`,
  `int(p.st_period)*10 if p.st_mult>0`, `(stoch_k_period+stoch_k_smooth+stoch_d_smooth)
  *8`. 4 canlı aile bunları okumuyor (F-D4). `max(...)` içinde, genelde bağlanmıyor.
* Removal Safety: Likely Safe (F-D4 ile birlikte).
* Reuse Scope: module.

### 3) Quick Wins (önce bunlar) — hepsi ölçüm/temizlik, davranış değişmez

1. **F-T3 ruff** (2 test dosyası import sıralaması) — `ruff --fix`, davranış yok.
2. **F-D6 / F-D7 / F-D8 testleri** koda göre güncelle (ichimoku artık htf okur;
   `_Engine` stub'a `supervisor`; kasa_auto hedefleri) — VEYA F-D8'de growth hedefi
   yanlışsa kod. Cursor karar.
3. **F-D3** `entry_blocks` pencere/rotasyon — auto-pilot bayat sayaç kararını kes, sonsuz
   "SPREAD kalibre atlandı" logunu durdur.
4. **F-D5 / F-P3** DB `opt_params.strategies` + `opt.strategy_max_combos` emekli aile
   temizliği — arama bütçesi canlı 4 aileye. (arsiv)
5. **F-D4 / F-P4** 11 ölü Params alanı — `Params.key()` + `required_bars` sadeleşir.

### 4) Deeper Optimizations (sonra)

* **F-D1** cost görünürlüğünü geri getir (charged sayı her apply'da) + Faz-1 costed
  replay (4 aile × aktif+disabled × son 10 pencere) → gerçek net-R sırası. (arsiv)
* **F-E4** per-sembol `adx_min>0` costed holdout araması.
* **F-E2** ters-sinyal-çıkış: backtest simulate'e "açık pozisyonda ters sinyal → flat"
  ölç (exit modelini bozmadan). F-E1 pyramiding'i YALNIZ F-E4 ile birlikte.
* **F-P1** engine.py / app.py modülerleştirme (davranış + WFO honesty korunur).
* Objektif fonksiyon: seçim metriğini ham `score`'dan Sortino/robustluk + `profit_drop`
  (IS→OOS) kolonuna çevir (RESEARCH_QUEUE "walk-forward OOS lock").

### 5) Validation Plan

* **Testler:** `4528b40`'ta 19 fail listesini referans al; her düzeltme sonrası
  `pytest -q` = 0 fail hedef. Fail-first (AGENTS.md).
* **Costed replay:** `charge_costs=True` ile son 10 holdout penceresi, 4 aile × (arsiv)
  {GER40,JPN225,NAS100,US30,XAUUSD,SpotBrent,BTCUSD}. Metrik: net R, expectancy,
  PF — cost-free sıralamasıyla diff. Beklenti: M5/M15 burst düşer.
* **Autopsy join:** `entry_block_events(risk_ters_yon)` × `trade_autopsies` symbol+
  zaman penceresi → kaç `sl` çıkışı stoptan önce ters sinyal gördü, toplam kurtarma R.
* **entry_blocks:** rotasyondan sonra 7 günlük pencere ile fill oranı + blokör
  dağılımı; önce/sonra.
* **Perf:** yük altında `last_cycle_ms` p95, `/api/state` latency (opt busy iken),
  arama süresi (emekli-aile temizliği önce/sonra).
* **Canlı:** değişiklik sonrası günlük autopsy sumR / avgR / MFE-capture medyan;
  hedef avgR ≥ 0 ve MFE-capture medyan ≥ 0.4.

### 6) Optimized Code / Patch

Yok — operatör talimatı: "hiçbir şeyi düzeltme, hepsi OPTIMIZATIONS.md'ye." Bulgular
Cursor'a doğrulama + plan + görev dağılımı için `claude/FOR_CURSOR.md`'ye özetlendi.

---

### EK — C1 costed replay ÖLÇÜMÜ (02.09 19:52, salt-okur)

Yöntem: `data/holdout_bars/*.npz` (yakalanmış 90k-bar pencereler) → `holdout_cost.
charged_holdout` son segment (~18k bar), CANLI DB config (aile/exits) snapshot TF'ine
zorlanarak, iki kez: **COSTED** = gerçek `spread_scale` (1.00–1.25) + komisyon;
**FREE** = spread_scale 0 + komisyon 0 (canlı aramanın gördüğü). Script:
scratchpad `c1_costed_replay.py`. PATCH/DB/API yok.

| snapshot | canlı aile/TF | COSTED net_r / exp / PF / n | FREE net_r | Δ (cost drag) |
|----------|---------------|-----------------------------|-----------|---------------|
| GER40_M15 | burst (canlı **M5**) | **−33.6** / −0.074 / 0.89 / 457 | −20.5 | −13.2 |
| GER40_M30 | burst (canlı **M5**) | **+21.4** / +0.049 / 1.07 / 438 | +42.9 | −21.5 |
| JPN225_M15 | burst/M15 ✓ | **+48.3** / +0.192 / 1.28 / 252 | +62.7 | −14.4 |
| NAS100_M30 | mtf_pullback/M30 ✓ | **+23.6** / +0.021 / 1.03 / 1099 | +44.0 | −20.4 |
| US30_M30 | channel_break/M30 ✓ | **+18.0** / +0.054 / 1.08 / 334 | +19.7 | −1.8 |
| US30_M5 | (canlı M30) | −30.8 / −0.101 / 0.86 | −30.9 | +0.1 |
| XAUUSD_M15 | burst *(disabled)* | **+83.4** / +0.143 / 1.22 | +98.3 | −14.8 |
| BTCUSD_M30 | burst *(disabled)* | +58.5 / +0.183 / 1.27 | +81.8 | −23.4 |
| GOLD-PERP_M30 | mtf_pullback *(disabled)* | **+114.3** / +0.219 / 1.35 | +118.7 | −4.4 |
| SpotBrent_M15 | burst *(disabled)* | −18.3 / −0.032 / 0.95 | +19.8 | −38.1 |
| SpotBrent_M30 | burst *(disabled)* | −27.2 / −0.035 / 0.95 | +41.8 | −69.0 |

**Ölçülen sonuçlar (F-D1 / lever A ilişkin):**
1. **Maliyet, canlı 4 için ANA katil DEĞİL.** Cost drag 18k-bar pencerede −2..−21 R;
   işareti çevirmiyor. COSTED bile: JPN225 +48, NAS100 +24, US30 +18, GER40/M30 +21.
   → `charge_costs=False` holdout'u ~%15–45 şişiriyor ama +90R-holdout / −41R-canlı
   ayrımı **öncelikli olarak cost-modeling artefaktı değil**. **Lever A: birincil →
   ikincil.**
2. **Asıl açık holdout(+) ↔ canlı(−).** Costed holdout NAS100 +24 / JPN225 +48 derken
   canlı NAS100 −19 / JPN225 −17. Maliyet değil; işaret eden yerler: rejim/timing
   (adx=0, F-E4), fill kalitesi %22–33 (F-E3), 1-ticket cap iyi 2. sinyali düşürüyor
   (F-E1), veya WFO iyimserliği / pencere sonrası rejim kayması. **Lever B (rejim
   filtresi) + yapısal (fill/cap) öne çıkıyor.**
3. **GER40 canlı TF (M5) snapshot YOK.** M15 costed −33.6 (kötü), M30 costed +21.4
   (iyi). Canlı burst/M5. M5, M15 gibiyse GER40 costed zararda. GER40_M5 yakalama
   gerek (flat kitap, operatör/Cursor).
4. **US30 canlı M30 doğru seçim** (M30 costed +18 vs M5 costed −31).
5. **Disabled kazananlar costed bile güçlü:** GOLD-PERP/mtf_pullback **+114**,
   XAUUSD/burst **+83**, BTCUSD/burst **+58** — canlı 4'ün 3'ünden iyi. Fill/rejim
   soruları çözülünce yeniden-açma adayı (operatör red).
6. **SpotBrent her TF'de costed zararda** (−18..−27) — doğru şekilde disabled.

Uyarı: yöntem canlı aile+exit'i snapshot bar-TF'ine zorluyor; GER40 M5≠M15/M30.
`block_reverse=True`, son-segment — optimizer holdout'una sadık.

---

### EK — C3 / C-next A: per-sembol `adx_min` COSTED sweep (02.09 20:05, salt-okur)

Aynı npz + `charged_holdout`, canlı aile/exit, `adx_min ∈ {0,15,20}` (0 = mevcut canlı
= filtre yok). Costs ON. Script: scratchpad `c3_adxmin_sweep.py`.

| sembol / aile-TF | adx_min=0 (canlı) | =15 | =20 | en iyi |
|------------------|-------------------|-----|-----|--------|
| **NAS100** mtf_pullback/M30 | +23.6 (exp .021, n1099) | **+57.0** (exp .055, n1033) | +46.8 (exp .057, n823) | **15** (+33 R, exp 2.5×) |
| **US30** channel_break/M30 | +18.0 (exp .054) | **+23.9** (exp .075) | +19.9 (exp .076) | **15** (+6 R) |
| **JPN225** burst/M15 | **+48.3** (exp .192) | +31.1 | +12.6 | **0** (filtre −17..−36 R zarar) |
| **GER40** burst/M30 | **+21.4** | +19.1 | +16.3 | **0** (filtre hafif zarar) |
| GER40 burst/M15 | −33.6 | −31.8 | −43.2 | (M15 zaten kötü) |
| XAUUSD burst/M15 *(off)* | +83.4 | +73.4 | +94.6 (exp .223) | 20 (gürültülü) |
| BTCUSD burst/M30 *(off)* | +58.5 | +60.6 | +15.1 | 15 |

**Ölçülen sonuç:**
1. **`adx_min` aile-spesifik, evrensel değil.** `mtf_pullback` (NAS100) ve
   `channel_break` (US30) için `adx_min=15` net costed iyileşme (NAS100 +33 R,
   expectancy 2.5×, işlem sayısı korunur; US30 +6 R). `burst` (JPN225, GER40) için
   HERHANGİ bir ADX tabanı zarar veriyor.
2. **Sebep tasarımsal:** burst bir range-*expansion* girişi, düşük-ADX patlamada
   ateşlenir; trend-gücü filtresi tam da edge'ini siler (burst docstring + ADX
   literatürü: filtre trend-devam setup'ına yarar, expansion'a değil).
3. **F-E4 / lever B — ölçülü öneri:** `adx_min=15` YALNIZ NAS100 (mtf_pullback) +
   US30 (channel_break); burst isimleri (JPN225, GER40) `adx_min=0` kalsın. ichimoku
   canlıya girerse ayrı test.
4. **NAS100 en güçlü aday:** +23.6 → +57.0 costed, şu ana kadarki en büyük tekil
   ölçülü iyileşme; NAS100 canlıda en kötü (−18.7 R). Yüksek güven.

Uyarı: tek pencere (son segment ~18k bar). Apply öncesi optimizer'ın tam walk-forward
+ validation gate'i şart (apply yolu = Cursor, ben değil). GER40 canlı TF M5 hâlâ
test edilemiyor.

---

### EK — C2 / C-next B: MFE zaman-profili (canlı autopsy, 02.09 20:12, salt-okur)

`trade_autopsies` (n=319). `bars_held` null → `held_min` proxy; `mfe_r` tüm-işlem
tepe (bar-indeksli eğri yok). Script: scratchpad `c2_mfe_profile.py`.

**Trail aktivasyon gerçeği (canlı 4):**

| sembol | trail_start | =R | medyan MFE | trail'e ULAŞAN % | medyan realised | capture ratio |
|--------|-------------|----|-----------|------------------|-----------------|---------------|
| GER40 | 2.0 ATR | 2.00 R | 0.60 R | **%14** | −1.00 | 0.11 |
| JPN225 | 2.5 ATR | 2.50 R | 0.77 R | **%11** | −0.58 | −0.36 |
| NAS100 | 2.5 ATR | 2.50 R | 0.47 R | **%13** | −1.00 | 0.17 |
| US30 | 0.3 ATR | 0.30 R | 0.72 R | %68 | −1.00 | 0.05 |

* GER40/JPN225/NAS100: `trail_start` 2.0–2.5 R ama medyan MFE 0.47–0.77 R. İşlemlerin
  yalnız **%11–14'ü** trail eşiğine ulaşıyor; kalan ~%86 sabit −1R stop'ta trailsiz
  sürüyor → medyan realised tam −1.00 R (GER40, NAS100). **Trail, ulaşılabilir MFE'nin
  3–5 katı öteye kurularak fiilen devre dışı.**
* US30: `trail_start=0.3R` erken, %68 ulaşıyor — ama `trail_step=2.2 ATR` çok geniş →
  korumuyor; capture 0.05; `sl` çıkışlarının **%80'i 1 saat içinde entry'yi geri
  geçti** (whipsaw / erken stop). medHeld 31 dk (en hızlı), 92 işlemin 50'si `sl`.

**MFE, tutuş-süresi çeyreğine göre (tüm semboller):**

| çeyrek | held | ort. MFE_r | ort. realised_r | n |
|--------|------|-----------|-----------------|---|
| Q1 en kısa | 0–24 dk | +0.27 | **−0.91** | 79 |
| Q2 | 24–73 dk | +1.03 | −0.32 | 79 |
| Q3 | 74–179 dk | +1.32 | +0.18 | 79 |
| Q4 en uzun | 180 dk+ | +1.85 | **+0.50** | 82 |

* Kısa işlem = saf zarar (Q1: MFE +0.27, realised −0.91). Hızlı ölen işlemde hareket
  hiç olmamış. Uzun yaşayan (Q4) para kazanıyor. Klasik trend-takip: edge koşuculardadır.
* Erken-stop (sl, 1 saatte entry'yi geri geçti): US30 **%80**, NAS100 %52, GER40 %48,
  JPN225 %44. left_on_table medyan ~1.1–1.3 R / işlem (capture ~0 ile tutarlı).

**Ölçülen sonuç (exit MODELİ değişmez — sadece grid içi eşik):**
1. **`trail_start` GER40/JPN225/NAS100 için ulaşılabilir MFE'nin çok ötesinde.** Aday:
   per-sembol `trail_start_atr` ≈ 0.5 × medyan MFE (≈ 0.3–0.4 ATR) costed holdout ile
   ara. Grid'de `trail_start_atr [0.3,0.4,0.5,...]` zaten var.
2. **US30: trail aktif ama `trail_step=2.2 ATR` çok geniş + %80 erken-stop.** Daha dar
   step ara; + F-E4 `adx_min=15` (zaten bulundu) whipsaw girişlerini keser. US30
   medHeld 31 dk = hızlı chop'ta aşırı işlem.
3. **Edge Q4'te (uzun tutuş).** Hızlı-ölüm oranını artıran (gevşek giriş, rejim filtresi
   yok) veya Q2/Q3 orta-işlemleri korumayan (ulaşılamaz trail) her şey kitabı akıtıyor.
   İki ölçülü kaldıraç: rejim filtresi (F-E4, NAS100/US30) + ulaşılabilir `trail_start`
   (per-sembol costed arama).
4. Uyarı: MFE bar-indeksli değil; "ilk N bar" kesin değil — çeyrek ayrımı proxy.
   Apply = optimizer WFO/validation (Cursor).

---

### EK — C4: emekli-aile ölü alan temizlik PLANI (02.09 20:22, UYGULAMA YOK)

11 ölü alan: `t3_fast, t3_slow_mult, t3_fast_vf, t3_accel_min, st_period, st_mult,
stoch_k_period, stoch_k_smooth, stoch_d_smooth, psar_af_step, psar_af_max`
(dual_t3/t3_flip/stoch_flip/parabolic_flip — 01.09 emekli). Canlı 4 aile (arsiv)
`opt_fields_read` çıktısı bunların HİÇBİRİNİ okumuyor (ölçüldü).

**Güvenlik doğrulaması:**
- `_coerce` (models.py:42) bilinmeyen key'i atlıyor → eski DB payload / fixture'lar
  alan silinince sorunsuz yükleniyor. ✓
- `Params.from_config` (strategy.py:116) `cls.__dataclass_fields__`'e filtreliyor →
  alan Params'tan çıkınca kopyalanmıyor. ✓
- `Params.key()` değişimi → sinyal cache kimliği değişir, bir kez yeniden hesaplanır
  (kalıcı cache yok). ✓
- `required_bars()` sadeleşmesi → bazı configlerde fetch boyutu DÜŞER (ölü terimler
  yalnız şişiriyordu). ✓ (F-P4 mikro-kazanç)

**Dokunulacak (önerilen diff, Cursor uygular):**

| # | Dosya | Değişiklik | Satır |
|---|-------|-----------|-------|
| 1 | `micofx/strategy.py` | `Params`'tan 11 alanı sil | 58–82 |
| 2 | `micofx/strategy.py` | `Params.key()` tuple'ından 11 alanı çıkar | 145–150 |
| 3 | `micofx/strategy.py` | `required_bars()` 3 ölü terimi sil (`t3_fast*slow_mult*20`, `st_period*10`, `stoch_k toplamı*8`) | 770–773 |
| 4 | `micofx/models.py` | `SymbolConfig`'ten 11 alanı sil | 126–167 |
| 5 | `micofx/models.py` | `OPT_FIELDS`'ten 11 girişi sil | 534–542 |
| 6 | `micofx/web/app.py` | `_INDICATOR_PERIOD_BOUNDS`'tan `t3_fast, st_period, stoch_k_period, stoch_k_smooth, stoch_d_smooth` çıkar; 190 yorumunu güncelle | 190, 197 |
| 7 | `tests/test_indicator_periods_are_bounded.py` | silinen bound'ları beklemeyi kaldır (14 ref) | — |
| 8 | DB `opt_params.strategies` | 4 emekli aile adını çıkar → `[mtf_pullback, burst, ichimoku, channel_break]` | settings |
| 9 | DB `opt` | `strategy_max_combos.stoch_flip` (28800) sil | settings |

**Bırakılacak:** `tests/fixtures/eski_ikincil_konfig_*.json` (152+21 ref) — bunlar
"eski config yüklenebiliyor mu" regresyon testi; `_coerce` bilinmeyeni atladığı için
silme sonrası bu testler tam da doğru şeyi kanıtlar.

**Kontrol edilecek (Cursor, apply öncesi):** `test_every_family_on_every_timeframe.py`,
`test_exit_param_bounds_everywhere.py`, `test_family_grid_only_searches_fields_it_reads.py`
bu alanlara değiyor mu; canlı sembol `opt_summary.params` stamp'i emekli alan taşıyor mu
(taşıyorsa `unstamped_gates_to_zero` zaten sıfırlıyor). DB 8–9: panel POST `opt_params`
= 400 (AGENTS.md); doğrudan `Store` çağrısı veya migration gerek.

**Beklenen etki:** kod −~40 satır ölü; `OPT_FIELDS` 11 eksen daralır (emekli-aile
ekseni artık aranamaz/uygulanamaz — F-D5); arama combo bütçesi canlı 4 aileye (arsiv)
(`stoch_flip` 28800 ≈ 3.08M duvarın 2.07M'i — F-P3). Davranış değişmez.

---

Operator: maximize income, fix gaps, GitHub+web, run opt at 00:06.
No engine PATCH. Live 22:36: 4 tickets (GER40 overnight 2.0 ATR + JPN/XAU/NAS),
day still **−$186.61 / 38** closes, halt false, opt idle.

* Public WFO/WFE 0.5, ATR-stop blogs (1.0× noise on M30, 2.0× common),
  StockSharp stoch+step trail, ByTamerFX DD-scalp+TP, QTradeX `tp_multiplier`
  — none of that enters this tree. Exit model stays hard ATR + ATR trail.
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
* **Impact** Log: 20:21 start 144 sweeps / 6 symbols / 8 families (arsiv) / 3 TF
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

* **Title** 8 families (arsiv) reverse: 4 live `stoch_flip` + burst + parabolic; 5 empty are search candidates
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
* **Tradeoffs / Risks** Dropping 5 families (arsiv) forever closes NAS100-style swaps.
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
| Dead `risk_sembol_limiti` 209 still incrementing | **Frozen.** Claude 22:22 live GET: totals 209, sqlite since ≈16.08, producer gone from `can_open`. Live incrementing: spread 241, ters 148, bar_bosluk 45, emir 12, bar_doldu 8, lot 4. Dormant: `risk_toplam_limit` 0, `risk_kova_limiti` 0. Do not reset unasked. |
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
* **Impact** 8 families (arsiv) in `STRATEGIES`. Live book uses 3
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
* Correctness: 8 families (arsiv) × TIMEFRAMES still fail-closed on unknown
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
| 8 families (arsiv) | Live: parabolic_flip, burst, stoch_flip×3, mtf_pullback. No alpha_trend/mavilim/st_trend/macd_flip/t3_stoch/wavetrend_flip/micro_rev. `ichimoku` stays. |
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
- 7 families (arsiv) - 8 since 31.08; no restart with opens.
- Fail-first with pytest/ruff. Persist via Store only.
- Yellow/red gates stay operator-only. Holdout capture is not a score input.
- Autopsy gotchas: `open_original_sl` must be tracked, profit-empty rows exist, `gmtime` broker calendar used.
```

---

# 31.08 01:15 — full A-Z optimization audit

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

Health: the trading core is correct where it matters most — fill-next-open
is honest, no lookahead in `supertrend`/`parabolic_sar`/`ichimoku`, the
forming candle never signals, clocks are `gmtime` everywhere they should
be, and there is no SQL injection or hardcoded secret. What is broken is
**coverage and throughput**: the search judges six of seven families on a
0.08–2.6% fixed random slice of their own grid, the live book is spending
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
`mt5_terminal_path = C:\Program Files\MetaTrader 5` (correct — the exe
exists). Entry blocks: `bar_bosluk` ×7 (BRENTOIL-PERP, GOLD-PERP, XAUUSD,
JPN225, NAS100, US30, BTCUSD), `spread` ×1 (SpotBrent, `spread_atr`
0.184), `seans_disi` ×1 (GER40, opens in 117 min). Zero symbols were in a
state where a signal could have been taken.

Test/lint state: `pytest tests/ -q` → **3 failed, 2610 passed, 1 xfailed,
88.60 s**. `ruff check micofx/ tests/ run.py backup.py gece_restart.py` →
clean.

## 2) Findings (prioritized)

### F1 — Six of seven families search 0.08–2.6% of their own grid

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
* **Why it's inefficient** The refine rounds walk ±1 per axis from the top
  12 seeds (`backtest.py:1416-1430`), which cannot bridge a 10-axis space
  sampled at 0.08%. `_plateau_scores` neighbours (`backtest.py:1043-1051`)
  therefore exist almost only because refine manufactured them, and when
  `grounded` comes back empty the code falls back to `list(blended)`
  (`backtest.py:1464`) — the plateau requirement silently disappears
  instead of failing loudly.
* **Recommended fix** Three independent levers, in ROI order: (a) give
  `dual_t3` and `burst` a per-family budget — `strategy_max_combos` is
  already read by `family_max_combos` (`optimizer.py:54-72`) but has **no
  entry in defaults.json**, so it is a switch that exists and is wired to
  nothing; (b) replace the uniform draw with a Sobol/LHS sample over the
  same budget, which cuts the variance of the coverage without costing a
  single extra simulation; (c) cut axes that cannot pay — `st_period`'s 2
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

### F2 — The bar-age gate measures from bar open, so the real slack is one bar

* **Category** Algorithm / Reliability
* **Severity** Critical
* **Impact** Signals taken vs signals refused — directly, trades per day
* **Evidence** `engine.py:2163-2177` compares against `state.last_bar`:

```2163:2165:micofx/engine.py
        tf_sec = timeframe_seconds(cfg.timeframe)
        if (state.last_bar > 0
                and (server_now - state.last_bar) > _MAX_SIGNAL_BAR_AGE_BARS * tf_sec):
```

  and `state.last_bar = bars.last_closed_time` (`engine.py:2403`) is the
  **open** stamp of the last closed bar. `_MAX_SIGNAL_BAR_AGE_BARS = 2`
  is documented at `engine.py:58-59` as "the bar that follows it, plus one
  extra bar of poll slack". Arithmetically the signal dies `1 × tf_sec`
  after its bar *closed*, not `2 × tf_sec`.
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
  guards is unaffected — that gap is measured in days, not one bar.
* **Expected impact** Doubles the acceptance window. On a book showing 7/9
  symbols blocked on exactly this gate, this is the highest-yield single
  line in the tree.
* **Removal Safety** Needs Verification (cover with a fail-first test on
  an M30 signal at `close + 90 min`)
* **Reuse Scope** local file

### F3 — `r_cap` is scaled by the edge multiplier, so the "auto 2%" 1R ceiling is ~4.4%

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

### F4 — Lot budget is diluted by names that cannot trade

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

### F5 — Whole-history spread median leaks backwards into every in-sample window

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
  leak — a median, not a signal — but it is the exact class of thing the
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

### F6 — The shared `grid` block in defaults.json is dead at every searched timeframe

* **Category** Dead Code / Algorithm
* **Severity** High
* **Impact** Four exit axes are not searched at all
* **Evidence** `defaults.json:388-391` searches only `["M15","M30"]`;
  `uses_swing_exits` is True at ≥900 s (`models.py:646-647`); the store's
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

### F7 — Five OPT_FIELDS axes have no grid anywhere

* **Category** Dead Code / Algorithm
* **Severity** High
* **Impact** `structural` trail mode has never been evaluated
* **Evidence** `models.py:521-538` vs `defaults.json:401-713`:
  `adx_max` (read by every gated family via `strategy.py:425-426`),
  `min_body_ratio` (`strategy.py:528-531`), `trail_mode` and
  `trail_lookback` (`backtest.py:541-542`, `609`), `min_atr_ratio`
  (`backtest.py:836-838`). Additionally `rsi_length`, `stoch_length`,
  `smooth_k`, `smooth_d` are never searched **and** never gate a family —
  `_common` computes StochRSI purely for the panel readout
  (`strategy.py:414`, `357`).
* **Why it's inefficient** Because `trail_mode` never varies, `structural`
  is permanently False and the entire structure/hybrid trail path
  (`swing_lows`/`swing_highs`, `backtest.py:543-544`) is code the search
  has never exercised. `adx_max` is a live gate on six families with a
  value nobody tuned.
* **Recommended fix** Add grids for `adx_max` and `min_body_ratio` (cheap,
  small axes). Leave `trail_mode` out until the structural path has a
  fail-first test — searching it today would also expose the per-combo
  `swing_lows` rebuild (F13).
* **Tradeoffs / Risks** Adding axes multiplies an already-undersampled
  grid; pair with F1(a) or the coverage gets worse.
* **Expected impact** Medium; `adx_max` is a real regime lever currently
  frozen.
* **Removal Safety** Needs Verification
* **Reuse Scope** service-wide

### F8 — `simulate()` rebuilds a full-length Python list per combo per window

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
* **Why it's inefficient** At ~90k bars × 4 windows × 2000 combos × 6
  rounds this is on the order of 4×10^12 boxed float allocations across a
  full sweep. It is pure overhead — the value is identical every time.
* **Recommended fix** `if not isinstance(trigger_pad, list): trigger_pad =
  np.asarray(...).tolist()`. One line.
* **Tradeoffs / Risks** None; the caller already owns the list.
* **Expected impact** Large and free. This is the single best
  effort-to-payoff change in the file.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F9 — `_stop_bar`, `_note_risk_capacity` and the TP branch are fully dead

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
  - `_tally_entry`'s `source` parameter (`engine.py:1318`) is never read —
    `engine.py:1349` hardcodes `leg = "primary"` — yet all five call sites
    pass it, and the per-leg nesting of `_entry_blocks` and `_filled_bars`
    can only ever hold one key because `_merge_signals` is two-valued
    (`engine.py:2448`).
* **Recommended fix** Delete `_stop_bar` + its prune + the two stale
  docstring paragraphs; delete `_note_risk_capacity` and its call site;
  collapse `tp` out of the engine→client entry path.
* **Tradeoffs / Risks** The `tp` removal touches `mt5client.open_market`'s
  signature and the invalid-stops retry; do it last and cover with the
  existing ambiguous-send tests.
* **Expected impact** Low runtime, high clarity. `_stop_bar`'s docstring
  actively misinforms about how the trail throttles.
* **Removal Safety** Safe (`_stop_bar`, `_note_risk_capacity`);
  Needs Verification (`tp`)
* **Reuse Scope** module

### F10 — ~150 lines of symbol-patch guards are unreachable over HTTP

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
  block on the trading cycle — but the guard that made those writes safe
  is gone too. If any of these fields is ever re-opened, the protection
  reads as present and is not.
* **Recommended fix** Delete the unreachable branches and leave a single
  comment at `_OPERATOR_SYMBOL_FIELDS` recording that re-opening a field
  means re-adding its guard.
* **Tradeoffs / Risks** None while the allowlist stands.
* **Expected impact** Removes ~150 lines and one false sense of safety.
* **Removal Safety** Likely Safe
* **Reuse Scope** module

### F11 — `_INDICATOR_PERIOD_BOUNDS` names two fields that do not exist

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

### F12 — `GET /` hands out a full-privilege session with no authentication

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

### F13 — `mt5_terminal_path` is an unvalidated, panel-writable executable path

* **Category** Security
* **Severity** High
* **Impact** Authenticated POST → arbitrary local process launch
* **Evidence** It is in `_OPERATOR_SYSTEM_FIELDS` (`app.py:428`) and the
  handler stores it with no validation at all (`app.py:1600-1607` just
  saves and reconnects) — in direct contrast to `backup_dir`, which gets
  careful path and UNC checks at `app.py:1572-1597`. Then
  `_exe_from_path` appends `terminal64.exe` (`mt5client.py:246`) and
  `ensure_terminal_process` runs
  `subprocess.Popen([str(exe)], cwd=str(exe.parent), ...)`
  (`mt5client.py:270-291`), with `autostart_mt5` defaulting to True
  (`models.py:772`).
* **Why it's inefficient** Combined with F12 the chain is: one
  unauthenticated GET, one POST, one launched process.
* **Recommended fix** Require the basename to be `terminal64.exe`, require
  the file to exist, and reject UNC — the same three checks `backup_dir`
  already performs. (This was already flagged Low at `OPTIMIZATIONS.md:879`
  and is still open; F12 is what raises it to High.)
* **Tradeoffs / Risks** A directory-only path is currently accepted and
  works (live carries `C:\Program Files\MetaTrader 5`); keep that form
  legal.
* **Expected impact** Closes the launch primitive.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F14 — `max_combos` / `refine_rounds` accept any finite number

* **Category** Cost / Reliability / Security
* **Severity** High
* **Impact** A single POST can wedge the live trading process
* **Evidence** Both are allowlisted at `app.py:434-437`, and
  `set_opt_params` validates only `timeframes`, finiteness and grid axes
  (`app.py:1731-1772`). `max_combos = 1e9` with `refine_rounds = 1e9` is
  accepted and persisted. Each refine round is charged a full
  `max_combos` sweep (`optimizer.py:95-96`). Same class:
  `flat_before_close_min` (writable at `app.py:431`, no entry in
  `_SYMBOL_RISK_BOUNDS`, UI-only `max: 240` at `app.js:1029` — `10**9`
  permanently blocks entries on that symbol) and `backup_keep`
  (`app.py:427`, UI-only bounds at `app.js:1688`).
* **Recommended fix** Add all four to the existing bounds tables. The
  mechanism is already there and already tested.
* **Tradeoffs / Risks** None; AGENTS already names 2000 as the intended cap.
* **Expected impact** Turns a process-wedging input into a 400.
* **Removal Safety** Safe
* **Reuse Scope** module

### F15 — Cycle-start position read is fail-open where `_reload_positions` is fail-closed

* **Category** Reliability
* **Severity** High
* **Impact** A transient `positions_get` failure empties the book the panel and the exit patcher read
* **Evidence** `engine.py:857` assigns `self._positions = self.client.positions()`
  **before** the connectivity check at `858-864`. `_reload_positions`
  exists precisely to avoid this — its docstring at `engine.py:793-808`
  says "On failure keep the previous snapshot and return False". After the
  bail-out, `self._positions` is left as an unreliable `[]`, and that same
  field feeds `_panel_positions` (`engine.py:4102-4103`) and the
  `open_magics` set `_apply_pending_exits` derives (`engine.py:3467-3469`).
* **Why it's inefficient** `pending_primary_patch` / `pending_exit_patch`
  land "when flat". An empty book from a failed read looks exactly like
  flat.
* **Recommended fix** Route line 857 through `_reload_positions()`.
* **Tradeoffs / Risks** None — it is the same call with the correct
  failure semantics.
* **Expected impact** Removes a path where a network blip can land a
  parameter patch under an open ticket.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F16 — `entry_lock` is held across `time.sleep` and broker round trips

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

### F17 — `order_send` runs under the global MT5 lock with no timeout

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

### F18 — `modify_position` reads "no change" as failure and retries every poll

* **Category** Reliability / Network
* **Severity** Medium
* **Impact** A wasted broker round trip per poll per position, all bar long
* **Evidence** `mt5client.py:1638-1658` is a single `order_send` with no
  widening ladder, and `TRADE_RETCODE_NO_CHANGES` returns `False`
  (`mt5client.py:1655-1657`). `_update_stop` then returns `False`
  (`engine.py:3819`) and retries.
* **Recommended fix** Treat `NO_CHANGES` as success — the stop is already
  where the caller wants it.
* **Tradeoffs / Risks** None.
* **Expected impact** Removes a per-poll broker call per open position on
  every bar where the trail does not move, which is most of them.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F19 — `normalize_volume` clamps up to `volume_min` after the risk cap

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

### F20 — `min_stop_distance` folds the freeze level into the stop floor

* **Category** Algorithm / Risk
* **Severity** Medium
* **Impact** Wider stops → smaller lots on every entry
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

### F21 — A symbol below `min_bars` gets no stop management at all

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

### F22 — Window boundaries manufacture fake "time" exits that count as trades

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

### F23 — `positive_ratio` is a two-valued step function

* **Category** Algorithm
* **Severity** Medium
* **Impact** Candidate ranking
* **Evidence** With `segments: 5` (`defaults.json:382`) selection is
  `windows[:-2]` = 3 windows (`backtest.py:1149`), so `positive` ∈
  {0, 0.333, 0.667, 1.0}, and the rank key squares it:

```1393:1393:micofx/backtest.py
                        raw[idx] = round(mean_score * positive * positive, 4)
```

  Against `min_positive_ratio: 0.6` only 0.667 and 1.0 survive, so the
  multiplier is **either 0.444 or 1.0** — nothing in between exists. A
  candidate that loses one of three segments is discounted 56% in one
  discontinuous step.
* **Recommended fix** Either raise `segments` so the ratio has resolution,
  or replace the squared ratio with a continuous consistency penalty.
* **Tradeoffs / Risks** Raising `segments` costs wall clock linearly.
* **Expected impact** Removes a cliff that currently dominates the
  ranking of otherwise-similar candidates.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F24 — Successive-halving prescreen is a recency filter

* **Category** Algorithm
* **Severity** Medium
* **Impact** Candidates are eliminated before `min_positive_ratio` sees them
* **Evidence** `prescreen` scores only `selection[-1]` and kills anything
  ≤ 0 outright (`backtest.py:1310`, `1360-1368`). A set that pays on
  segments 1 and 2 but not the most recent is never evaluated, even though
  2/3 clears `min_positive_ratio: 0.6`.
* **Recommended fix** Prescreen on the mean of two segments, or keep the
  cheap screen but raise the kill threshold's sample.
* **Tradeoffs / Risks** More survivors means more full evaluations —
  directly more wall clock.
* **Expected impact** The prescreen and the consistency gate currently
  disagree about what "consistent" means; this makes them agree.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

### F25 — Pooled drawdown is a max-of-segments, not an equity curve

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

### F26 — Three supervisor rules and two knobs are dead at shipped defaults

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
  (`1080`), which makes `bad_hour_pf` a dead knob — the live path
  `_hour_risk_scales` hardcodes `pf < 1.0` and a 0.3 floor (`962-964`) and
  never reads it. `_bad_hours` also still contains the un-fixed copy of
  the profit-factor arithmetic `_pf`'s docstring warns about
  (`1001-1002`: dollars compared against a ratio), masked only because the
  same branch requires `sum(values) < 0`.
  Separately, `edge_decay` needs 50 closes in a 14-day window with both
  halves ≥ 25 (`753-764`) — at this book's frequency it effectively never
  fires. And `edge_health` requires `v.trades >= 25` **and**
  `expected_r > 0` (`971-974`), so it reads 0.0 for every recently
  re-applied symbol and the "saglik %" suffix silently vanishes.
* **Recommended fix** Delete the three gated branches and `bad_hour_pf`,
  or flip `hard_block_only_quarantine` deliberately. Do not leave the
  panel claiming `hours_enforced`.
* **Tradeoffs / Risks** Flipping the flag changes live gating — red.
* **Expected impact** Removes the gap between what the AI tab displays and
  what the supervisor does.
* **Removal Safety** Likely Safe (delete); Needs Verification (flip)
* **Reuse Scope** module

### F27 — Four endpoints are never called by the panel

* **Category** Dead Code / Cost
* **Severity** Low
* **Impact** One of them costs a forced MT5 round trip
* **Evidence** Verified by grepping every `"/api/…"` in `app.js`:
  - `GET /api/schema` (`app.py:669-687`) — its own docstring claims "The
    panel fetches this once on load" (`app.py:678`). It does not;
    `opt_fields` / `engine_opt_fields` / `strategy_opt_fields` appear
    nowhere in `app.js`.
  - `GET /api/system` (`app.py:1551-1553`) — panel reads `STATE.system`.
  - `GET /api/positions` (`app.py:1671-1688`) — panel reads `STATE.positions`.
  - `GET /api/symbols/lot-mode-check` (`app.py:1367-1373`) — and it calls
    `engine.refresh_account(force=True)`, a forced MT5 round trip, for a
    view nobody renders.
  `POST /api/holdout/capture` is night-restart only, which is correct.
  Tombstones that exist only to 400 (`/api/symbols/{s}/reset` at
  `app.py:1361-1365`, `/api/opt/params/reset` at `1774-1778`) are
  intentional — but the latter's comment says "JS is gated on
  `#btn-opt-reset`" and that id does not exist in `index.html` at all.
* **Recommended fix** Keep `/api/positions` and `/api/system` (external
  review loops read them, per their comments); delete `/api/schema` and
  `/api/symbols/lot-mode-check`, or wire the latter's `force=True` down to
  a cached read.
* **Removal Safety** Likely Safe
* **Reuse Scope** module

### F28 — Panel repaints whole tables on every 3 s poll

* **Category** Frontend
* **Severity** Low
* **Impact** Browser CPU while the panel is open
* **Evidence** `viewPulse()` (`app.js:2217-2234`) string-joins every
  position and every symbol state on every poll just to decide whether to
  repaint — and the pulse changes whenever `acc.profit` or any `st.atr`
  ticks, i.e. essentially every poll while the market moves. On a
  difference the panel rebuilds via `innerHTML` per row:
  `renderCapacity` 13 cols × N (`app.js:675-696`), `renderPositions`
  (`767-818`, with `SYMBOLS.find()` **twice per row** → O(rows×symbols)),
  `renderLive` 14 cols × N (`856-918`), `renderExecution`, `renderDayTable`,
  and `rowsInto` clears `tbody.innerHTML` each time (`174-183`). Only the
  AI and portfolio tables have signature guards. `pruneLogView` calls
  `getBoundingClientRect()` per removed node — a forced layout inside the
  removal loop (`app.js:2150-2160`) — over up to 1200 nodes, and
  `pollLogs` requests all nine levels at `limit=400` every 3 s while the
  Log tab is open (`2198-2199`).
* **Recommended fix** Give Panel/Tani tables the same signature guard the
  AI table already has; hoist the `SYMBOLS.find()` into a map; batch the
  log prune outside the measure loop.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F29 — SQLite write amplification on symbol saves

* **Category** DB
* **Severity** Low
* **Impact** Panel write latency; adding a symbol costs ~2N commits
* **Evidence** `sort_symbols_by_group()` does one `save_symbol()` per
  symbol — each its own `SELECT position`, upsert and `commit()` — then
  re-reads the whole table (`store.py:473-482`); it is called from
  `add_symbol` (`465`) and `seed_symbols` (`562`). `save_symbol` rebuilds
  the whole dict per write (`store.py:278`:
  `self.symbols = {**self.symbols, cfg.symbol: cfg}`) while the panel
  debounces only 350 ms per key (`app.js:1137-1152`). The only index is
  `idx_opt_symbol ON opt_runs(symbol, created_at DESC)` (`store.py:31`),
  so `opt_history(symbol=None)` — exactly what the panel calls
  (`app.js:1431`) — is a full scan plus sort (`store.py:772-777`).
  `_recent_deal_magics()` fetches **30 days of broker deals** on every
  `POST /api/symbols` and every soft seed (`app.py:794-798`).
* **Recommended fix** One transaction for the sort; add an index on
  `opt_runs(created_at DESC)`.
* **Removal Safety** Safe
* **Reuse Scope** module

### F30 — Dead / unread config surface (consolidated inventory)

* **Category** Dead Code
* **Severity** Low
* **Impact** Operator trust: these render, accept writes, and change nothing
* **Evidence**
  - `SymbolConfig`: `fixed_lot` (`models.py:170`, no sizing path reads it),
    `lot_mode` (`169`, read only by `risk.lot_mode_diagnostics` which is
    served by the dead endpoint in F27), `max_lot` (`172`),
    `max_margin_pct` (`173`, see `risk.py:385`), `max_positions` (`174`),
    `partial_close_frac` (`256` — live uses `SCALE_OUT_FRAC`,
    `models.py:478`).
  - `SystemConfig`: `daily_loss_flatten` (`models.py:677`, no reader in
    `micofx/` at all — `field_help.js:96` already says so),
    `max_total_positions` (`659`), `max_concurrent_risk_pct` (`680`),
    `max_positions` (`670`), `max_lot` (`671`).
  - `max_scalp_positions` / `max_swing_positions` default to 0
    (`models.py:662-663`) and are **absent from defaults.json**, so the
    scalp/swing bucket cap at `risk.py:671-679` never fires — a whole
    branch with no live effect.
  - `can_open` accepts `sl_distance` and discards it (`risk.py:639-640`)
    while callers compute and pass it (`engine.py:2605-2606`).
  - `stoch_extreme` (`strategy.py:83`) is read by no family yet sits in
    the signal cache key (`strategy.py:131`); `IndicatorCache.volume`
    (`strategy.py:176`) is written by three callers and read by none;
    `Result.trade_cost_rs` is appended per trade (`backtest.py:580`) and
    merged (`1074`) with no reader.
  - Unreachable code paths: `max_open > 1` (~120 lines,
    `backtest.py:680-802` — `max_open_from_cfg` unconditionally returns 1
    at `428-435`), `reverse_on_signal` (`backtest.py:885-932`, its own
    docstring says search never passes it), and three of four
    `SELECTION_METRICS` (`backtest.py:51`, `176-189` — `defaults.json:385`
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
  - `index()` produces a double query string —
    `/static/app.js?v=<mtime>?v=27c` — because the template already carries
    `?v=27c` (`index.html:517-518`) and `app.py:652-656` prepends another.
* **Recommended fix** Delete in three batches: JS dead first (zero risk),
  then unreachable backtest paths, then the unread model fields (each of
  those needs a store-migration check).
* **Removal Safety** Safe (JS, `trade_cost_rs`, `volume`, `stoch_extreme`
  cache key); Likely Safe (`max_open>1`, `reverse_on_signal`, unreachable
  metrics); Needs Verification (model fields — they persist)
* **Reuse Scope** service-wide

### F31 — Documentation drift is failing its own test

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
  on the line — that is the correct escape. The AGENTS-mirror block at the
  tail is not historical and must read the live count.
* **Status** Fixed 31.08: eleven archive lines marked, mirror block
  corrected.
* **Removal Safety** Safe
* **Reuse Scope** local file

### F32 — `test_spread_scale_applied.py` produces zero candidates

* **Category** Reliability
* **Severity** Medium
* **Impact** 2 of the 3 red tests; the spread-cost guarantee is unguarded
* **Evidence** Both tests fail with
  `"tutarli kazanan parametre bulunamadi (0 kombinasyon segmentler arasi tutarsizdi)"`
  against a 3-combo fixture whose baseline is 58 trades / 30 wins /
  51.7% win rate, with `rejected_inconsistent: 0`. Zero rejected **and**
  zero survivors means the fixture is being eliminated before the
  consistency check — consistent with F24 (prescreen kills on the last
  segment alone) and F23 (only 0.667 and 1.0 survive
  `min_positive_ratio`).
* **Recommended fix** Diagnose against F23/F24 before touching the test.
  If the prescreen is the cause, the test is correctly reporting a real
  behaviour change in the search, not a stale fixture.
* **Removal Safety** Needs Verification
* **Reuse Scope** module

## 3) Quick wins (do first)

Ordered by impact ÷ effort. Every one is a small, local, testable change.

1. **F8** — one-line guard on `trigger_pad`. Largest search speedup in the
   repo, zero risk.
2. **F18** — treat `NO_CHANGES` as success. Removes a per-poll broker call
   per open position.
3. **F14** — put `max_combos`, `refine_rounds`, `flat_before_close_min`,
   `backup_keep` in the existing bounds tables.
4. **F15** — route `engine.py:857` through `_reload_positions()`.
5. **F11** — rename `adx_length`/`atr_length` to `adx_period`/`atr_period`.
6. **F2** — measure bar age from bar close. One expression; fail-first test
   on an M30 signal at close + 90 min.
7. **F9 (partial)** — delete `_stop_bar` and `_note_risk_capacity` plus the
   two stale docstrings.
8. **F6** — delete the four shadowed axes from the shared `grid` block.
9. **F31** — mark `OPTIMIZATIONS.md:10` `(arsiv)`, fix the tail block to 7.
10. **F13** — three path checks on `mt5_terminal_path`, copied from
    `backup_dir`.

Also, unrelated to code: [config/defaults.json](config/defaults.json):21
still ships `C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe`,
which does not exist on this machine. Live is correct
(`C:\Program Files\MetaTrader 5`), but a clean install cannot connect.

## 4) Deeper optimizations (do next)

* **F1** — per-family combo budgets plus a Sobol/LHS sample. This is the
  one change that moves every future applied parameter set.
* **F3 + F4 + F19 + F20** — the sizing chain. Land them together and while
  flat: F3 shrinks lots, F4 and F20 grow them, F19 refuses the residue.
  Landing any one alone changes live position size in a direction the
  others were compensating for.
* **F5 + F22 + F23 + F24 + F25** — search-honesty batch. All five change
  scores, so all five invalidate stored stamps; do them in one pass and
  re-baseline the book once, not five times.
* **F16** — narrow `entry_lock` to the state mutation.
* **F10 + F26 + F30** — the dead-code sweep, in the three batches named in
  F30.
* **F12** — session/Origin hardening. Needs an operator decision about LAN
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
{`test_docs_match_the_code`, `test_spread_scale_applied` ×2}, is a
regression.

Per-finding verification:

* **F8** — time one `walk_forward` on a fixed symbol/TF/family with a
  pinned `combo_seed` before and after; the returned best combo must be
  **identical** and the wall clock lower. That equality is the whole test.
* **F2** — fail-first: an M30 state whose `last_bar` closed 90 minutes ago
  must still be accepted; one at 150 minutes must not. Then watch
  `entry_block` counts in `/api/analysis/entry-blocks` over one full
  session and compare `bar_bosluk` against tonight's 7-of-9.
* **F3/F4/F19/F20** — assert on `lot_for` directly with a synthetic
  account: for a symbol at `edge_scale = 2.2`, realized risk must be
  ≤ 2% of balance. Then compare `capacity` rows before/after on the live
  book with trading off.
* **F18** — assert `modify_position` returns True on a mocked
  `NO_CHANGES` retcode, and that `_update_stop` does not retry.
* **F15** — mock `positions()` to raise mid-cycle and assert
  `self._positions` still holds the previous snapshot and no pending patch
  lands.
* **F14** — POST `max_combos = 10**9` must be 400.
* **F1/F5/F22/F23/F24/F25** — these change scores by design, so the test is
  a *paired* comparison, not an absolute: run the same symbol/TF/family
  before and after on the same history and record `net_r`, `max_dd_r`,
  `trades`, `win_rate`, and holdout PF for both. Accept only if holdout PF
  does not fall. Then hold the old and new parameter sets side by side on
  the same holdout slice.
* **F12/F13** — `curl` the panel from a second machine on the LAN and
  confirm refusal; POST an `mt5_terminal_path` of `C:\Windows\System32\calc.exe`
  and confirm 400.

Metrics to compare before/after, book-wide: entries per day, `bar_bosluk`
and `spread` block counts, mean lot per entry, realized R per trade,
holdout PF, and search wall clock per family.

## 6) Optimized code

Only the changes that are unambiguous and local enough to state exactly.

**F8** — `backtest.py:514-515`. Skip the round trip when the caller already
passed a list:

```python
    elif not isinstance(trigger_pad, list):
        trigger_pad = np.asarray(trigger_pad, dtype=np.float64).tolist()
```

**F18** — `mt5client.py:1655-1657`. The stop is already where we want it:

```python
    if result.retcode == mt5.TRADE_RETCODE_NO_CHANGES:
        return True
```

**F15** — `engine.py:857`. Use the fail-closed helper that already exists:

```python
    if not self._reload_positions():
        # keep the previous snapshot; the connectivity check below bails
        ...
```

**F11** — `app.py:187`. Two renames:

```python
_INDICATOR_PERIOD_BOUNDS = dict.fromkeys((
    "t3_fast", "t3_length", "st_period", "rsi_length", "stoch_length",
    "stoch_k_period", "stoch_k_smooth", "stoch_d_smooth",
    "adx_period", "atr_period", "trail_lookback",
), (1, 10000, True))
```

**F2** — `engine.py:2164`. Measure from the bar's close, not its open:

```python
        bar_close = state.last_bar + tf_sec
        if (state.last_bar > 0
                and (server_now - bar_close) > _MAX_SIGNAL_BAR_AGE_BARS * tf_sec):
```

**F3** — `risk.py:483-486`. Build the cap from the operator multiplier only,
and apply the edge/AI push to the raw lot instead:

```python
        r_pct = max(stored, self.AUTO_R_PCT)
        r_cap = (balance * r_pct / 100.0 * lot_multiplier
                 / (sl_distance * money_per_unit))
```

Nothing above was applied. This file is notes.

---

## 31.08 03:xx — closed ledger: what actually landed

Operator gave full authority to implement. Suite **2665 passed, 0 failed,
1 xfailed** (was 2610 passed / 3 failed at the start of the session), ruff
clean over `micofx/` and `tests/`. **The live PID is still on the old code:**
it holds 2 tickets, so `/api/app/restart` is 409. Everything below lands on
the next flat restart.

### Landed on the money path

| # | Change | Measured effect |
|---|---|---|
| F2 | Signal bar age measured from the bar's **close**, not its open. Extracted as `engine.signal_bar_expired`. | The window was one bar, not the two `_MAX_SIGNAL_BAR_AGE_BARS` documents. Live 31.08 01:15: 7 of 9 symbols on `bar_bosluk` at once; 03:xx re-measure: 5 of 9 (`BRENTOIL-PERP`, `GOLD-PERP`, `XAUUSD`, `US30`, `BTCUSD`). |
| F3 | `r_cap` is built from `lot_multiplier` and an `ai_scale` clamped at 1.0 — **not** from the `multiplier` that carries `edge_scale`. | The "auto 1R, max(risk%, 2%)" ceiling was scaled by the push it exists to bound: up to `EDGE_MAX` 2.2, so ~4.4% of balance on a proven symbol. The supervisor throttle still tightens it; only the edge lift is gone. |
| F4 | `_vacant_enabled_count` skips quarantined names (`Supervisor.is_suspended`, wired from `Engine.__init__`). | A quarantined symbol carries `risk_scale` 0.0 and cannot open, but held a full share of the remaining book margin. Every real entry was sized at `(vacant − suspended) / vacant` of its intended lot. |
| F20 | `min_stop_distance` uses `stops_level`, with `freeze_level` only as a fallback when `stops_level` is 0. | `freeze_level` is a no-modify window, not a placement floor. Folding it in widened `sl_dist`, and lot is risk / that distance — a permanent size-down on any symbol with a wide freeze zone. |
| F18 | `TRADE_RETCODE_NO_CHANGES` is a success in `modify_position`. | A settled trail read as a refused one and resent the identical request every poll for the rest of the bar — one round trip per open position per poll, on the lock every `/api/state` queues behind. |
| F15 | Cycle-start position read routes through `_reload_positions()`. | A failed `positions_get` left an empty book that looks exactly like *flat* — which is the condition `_apply_pending_exits` lands patches on. |
| F21 | New `_note_unmanaged_ticket` WARN when an open ticket has `last_bar == 0`. | Under the `min_bars` floor, trail/BE/partial/harvest all skip and the ticket runs on the broker stop alone, previously in total silence. |

### Landed on the API / panel

| # | Change | Measured effect |
|---|---|---|
| F14 | `_OPT_PARAM_BOUNDS` on `max_combos` / `refine_rounds` / `lookback_days`; `flat_before_close_min` and `backup_keep` added to the risk-bound tables. | Every refine round is charged a full `max_combos` sweep, so an unbounded POST wedged the process holding the live book. `flat_before_close_min` was the only writable symbol field with no server-side bound at all — a `10**9` POST blocked every entry on that symbol permanently. |
| F13 | `mt5_terminal_path` validated: absolute local or UNC (behind the existing latch), no drive root, and a named `.exe` must be `terminal64.exe`. | The stored value becomes `subprocess.Popen` via `ensure_terminal_process`, and `autostart_mt5` ships True — an accepted POST was a launched process. `backup_dir` one screen above already had all three checks. |
| F28 | `viewPulse` no longer includes `bot.last_cycle_at`. | It changes every cycle, so the signature differed on every poll and the "nothing changed, skip the repaint" guard **never fired once**. It is rendered into `#sys-bot-note` by `renderSystem`, which the guard does not cover. A quiet book now stops rebuilding six tables every 3 s. |
| F29 | `idx_opt_created` on `opt_runs(created_at DESC)`. | The panel's own call is `/api/opt/history?limit=80` with no symbol; the existing composite `(symbol, created_at)` cannot serve that, so it was a full scan plus a sort per visit. |
| F27 | `/api/symbols/lot-mode-check` no longer passes `force=True`. | A read-only preview was taking the MT5 lock the trading cycle queues behind, to move a balance the 3 s cycle already refreshed. |
| F8 | `simulate()` skips the `trigger_pad` rebuild when it is already a list. | `walk_forward` builds it once and hands the same object to every combo; re-listing it was a full-length rebuild per combo per window. |
| F11 | `_INDICATOR_PERIOD_BOUNDS` keys corrected to `adx_period` / `atr_period`. | `adx_length` / `atr_length` are fields of nothing. The two periods the table was written to bound were the two it never reached. |

### Dead code removed

* `Engine._stop_bar` — written, pruned, never read since `manage_positions`
  moved to "always re-run `overlay_stop` on this closed bar". Bar-close
  discipline is still enforced by `_update_stop`'s own reference-bar check.
* `Engine._note_risk_capacity` / `_risk_capacity_noted` — a method whose whole
  body was `return`, called unconditionally every cycle. Its test file now
  pins the absence structurally instead of pinning the silence.

### Chased and **withdrawn** — do not re-file these

* **F19 (`normalize_volume` clamping up past the cap).** Unreachable on the
  account path: `floor` *is* `volume_min`, and `lot_for` already refuses when
  the capped lot falls under `floor`, so the clamp cannot raise a lot the
  caller accepted. No guard was added — a guard that cannot fire is the thing
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
* **F28 (panel repaint guard).** Already implemented — `viewPulse` plus the
  `activeTab` gate. The defect was not a missing guard but a guard defeated
  by one field, which is what F28 above actually fixes.

### Test debt paid

`tests/test_spread_scale_applied.py` had two long-standing reds. Cause: the
fixture named `stoch_flip`, which gained a mandatory HTF-trend + ADX gate on
30.08 and stopped producing a consistent winner on these synthetic bars at any
scale — the same staleness that hit it on 27.08 when `t3_stoch` retired.
Re-measured across all seven live families: `t3_flip` is the only one that
still clears here, and it needs a wider grid than the 2×3 the file carried.
Charged cost is now exactly linear across scale 1/2/3 (0.0015 / 0.0030 /
0.0045), which is the property under test.

Applied, not notes. This section is the closed ledger.

---

## 31.08 10:52 — why the book gives profit back, and where opt wall-clock goes

Operator asked why the system loses, why it hands profit back, a hard stress
pass, and continuous watching. Measured against 289 closed autopsies and the
live config, live PID still on pre-31.08 code (5 tickets, restart 409).

### It is a payoff problem, not a hit-rate problem

289 trades: hit rate **34%**, average win **+1.26 R**, average loss
**−0.85 R**, reward/risk **1.48**. Break-even at that hit rate needs **1.98**.
The 0.50 shortfall is −0.141 R per trade, **−40.73 R** in total.

### The give-back sits in one setting

Peak retention on `exit_reason = trail`, against each symbol's trail arm point
(`trail_start_atr / sl_atr_mult`, i.e. the trail's arm expressed in R):

| symbol | family | trail arms (R) | mean MFE → kept | net R |
|---|---|---|---|---|
| JPN225 | stoch_flip | 0.50 | 1.79 → **19%** | −18.59 |
| NAS100 | stoch_flip | 0.50 | 1.99 → **19%** | −16.98 |
| US30 | stoch_flip | 1.40 | 3.10 → 44% | −2.08 |
| XAUUSD | burst | 2.00 | 3.85 → **72%** | +5.52 |

JPN225 + NAS100 are **−35.57 R, 87% of the book's entire loss**, and they are
the only two symbols with a 0.50 arm. NAS100's average winner (+0.73 R) is
*smaller* than its average loser (−0.86 R). The comparison is clean because
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
ledger as costing GER40 −32 R (BE-2). The evidence points at
`trail_start_atr`, not at BE. Recorded here so the next reader does not
re-derive "BE is doing nothing" and reach for the wrong lever.

Two honesty caveats: `mfe_r` is an intrabar peak while overlays evaluate on
closed bars, so every "would have been saved" figure is an upper bound; and
`left_on_table_r` (110 R) includes losers and is not cash sitting in the till.

### Hard stress pass — clean

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
exactly reproducible from `sweep_budget = max_combos × (1 + refine_rounds)`:

| item | arithmetic | share |
|---|---|---|
| `stoch_flip` | 2 symbols × 3 TF × (28,800 × 4) = 691,200 | **70.6%** |
| the other six families | 2 × 3 × 6 × (2,000 × 4) = 288,000 | 29.4% |

Three multipliers, all configuration:

1. `strategy_max_combos.stoch_flip = 28800` is the *exact* product of that
   family's grid (`5×4×2` entry × `5×6×6` exit × `4` spread), so the global
   2000 cap does no sampling there at all - the grid is exhaustive.
2. `refine_rounds = 3` multiplies everything by four. Refine rounds are not
   cheap extra passes; each gets its own full budget.
3. A POST that leaves `strategies` / `timeframes` empty inherits the saved
   seven families × three timeframes.

The third is the only waste, and it is operator habit rather than a setting:
this run wanted one family at one timeframe per symbol. Scoped
(`strategies: ["stoch_flip"]`, each symbol at its own TF) the same trail
question costs `2 × 115,200 = 230,400` - **23.5% of what was spent, 4.2x
faster, same grid, same answer**.

**Deliberately not changed:** `refine_rounds` and the `stoch_flip` cap.
Cutting either buys wall-clock by lowering search quality, which is the wrong
trade on a book running −0.141 R per trade; and `stoch_flip` is the family on
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
the give-back twice on 31.08 - 09:17 at −45% and 10:19 at −50% off a +46.54
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
rastgele bir %3 lük cekilisin en iyisini; beklenen ornek-en-iyisi gercek
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
2. **Sweep'i bolmek**: kaba tarama dilimlere ayrilip isçilere dagitilabilir.
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

1. **Izgara tabani.** Eksenin canli degerleri `[0.05 … 0.4]`, sembol
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

## F51 - bes aile derinlemesi: sembol eslestirme, aile rolü (01.09)

`stoch_flip` / `dual_t3` / `t3_flip` emekli. Kalan bes sinyal sekli:

| aile | ne soruyor | olcumde rol |
|---|---|---|
| **burst** | genisleyen bar, extreme kapanis | kitap geneli kazanan (6/7); F47 h=20'de en iyi spread kazanci |
| **mtf_pullback** | HTF trend + ATR geri cekilme | NAS100 en iyi (55R vs burst 51); GER40 F46 t=2.74 |
| **channel_break** | onceki N bar kanal kirilimi | GER40 stoch yerine (34R); JPN225'te 0.4R — sembol secimi sart |
| **ichimoku** | TK cross + bulut | F39 en iyi asimetri (7/7) ama arama cikis eksenleriyle nadiren kazanir |
| **parabolic_flip** | SAR flip | arama adayi; matriste nadiren birinci |

**M5 taramasi sonrasi sembol bazli duzeltme** (kör burst degil, matris):

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

`parabolic_flip` SAR flip — emekli `stoch_flip` ile ayni sinif, sifir galibiyet.
Arama gürültüsünü kesmek icin cikarildi.

**Canli dort aile:**

| aile | rol |
|---|---|
| **burst** | kitap omurgasi — genisleme + extreme kapanis, cost_rank kapisi |
| **mtf_pullback** | endeks geri cekilme — NAS100 olcumu |
| **channel_break** | kanal kirilimi — GER40 stoch yerine aday |
| **ichimoku** | TK+bulut — F39 en iyi asimetri; arama cikis-only, nadiren kazanir ama ucuz (1080 combo) |

Gelir icin kural: **stoch WF skoru kovalama** (overfit); sembol basina bu
dort aileden olculen en iyiyi uygula.

---

### EK22 — GECE OTURUMU (03.09 ~15:00–24:00, Claude ölçüm + Cursor implement)

**A. Weak-symbol kampanyası — "ölü" sanılan semboller yanlış-seans/yanlış-spread-cap'ti**
`holdout_cost.charged_holdout` (apply-gate modeli) ile ölçüldü:

| sembol | eski | düzeltme | charged sonuç |
|---|---|---|---|
| US30 | msa 0.02 (bayat), seans 08-16 | msa 0.08 + adx_min 20 | +25R n240 PF1.20 (applied) |
| NAS100 | seans yok, msa 0.06 | sess 15:00-21:00 patch | PF1.05→1.19, +57→+101R |
| JPN225 | burst/M30 gündüz seans | 7/24 (session filtresi ZARAR veriyordu) | +143.7R n373 PF1.56 |
| SpotBrent | "disabled FINAL", msa 0.25 | msa **0.05** + mtf/M30 + NY 13-21 | +21.8R PF1.16, re-enabled (probe) |
| XAUUSD | mtf/M15 7/24 | dokunulmadı (zaten en iyi) | +246R PF1.31 |
| GER40 | channel_break/M30 adx0 | adx_min 15 (rutin) | +72.8R PF1.34 |

Agg charged score ~609. Kalıp: spread'i seans-bağımlı equity index'ler (US30/NAS100)
→ dar pencere kazandırır; seanslar arası trend / 7-24 enstrüman (JPN225/XAUUSD/BTC)
→ tüm-saat optimal, kısıtlamak zarar.

**B. Altyapı fix'leri (Cursor, `52eef9e`/`def4682`/`3ce1513`/`58af8a9`)**
- `_beats_incumbent`: charged aday paper incumbent skoruyla yarışıyordu (NAS bar 116
  vs gerçek charged 32) → `holdout_costed` kullan.
- F6 `positive_ratio` binary → `_f6_holdout_waiver` (net_r>40, PF≥1.15, dd<net).
- Seans pre-step → WFO fan-out ekseni (`_session_search_shortlist`, max 3) + sticky
  (`_session_sticky_eligible` n≥25+net>0, DD-escape near-tie).
- `max_spread_atr` WFO ekseni (`spread_cap_search_axis` p40/p55/p70 + 0.04 floor).
- `sl_atr_mult` search floor ≥0.9 (`floor_sl_atr_search_axis`); shipped grid
  `[0.9,1.2,1.5,2.0,2.5]`.
- adx_min grid `[0,12,18,25]`.
- **holdout_days bug**: force-measure path `lookback_days/segments`=36 yazıyordu →
  gerçek segment span (`bars.time[hi-1]-bars.time[lo]`). Projeksiyon %202→%80-108.
- Projeksiyon min-window guard (MIN_PROJ_DAYS 90) + plausibility note + hover.
- min-lot concurrent overshoot 3.5→4.5; priority idle-weight 0.55→0.9 + expectancy
  ×2→×3; MIN_COSTED_N 40 (thin costed stamp bloğu).
- pr=None (force restamp'lerde score_consistency yanlış ölçekti → None).

**C. 3 realised-P&L bleed kaynağı (329 otopsi, never-favorable −95R ayrıştırıldı)**
1. **PREMATURE STOP** — 59 işlem, −58.2R. Stop sonrası 1 saat içinde fiyat entry'yi
   geçip ≥0.8R toparlıyor (yön doğruydu). Sebep: sl_atr_mult < 1.0 (NAS100 0.5,
   JPN225 0.7, XAU 0.5) — M30 gürültüsü içinde stop. + US30 (sl 2.0) spread-gate leak.
   Fix: SL search floor ≥0.9 (landed); **live NAS/JPN/XAU SL patch = SABAH** (bar-backtest
   sub-1.0 stop'u ödüllendiriyor, canlı otopsi çürütüyor — çelişki).
2. **SPREAD-GATE leak** — 152 işlem spread_atr>0.04'te −52.5R (US30 −24.4, JPN225 −14.4).
   `max_spread_atr` gate'in ÜSTÜNDE giriyor. Kök: (i) autopsy ATR-basis vs gate ATR
   uyumsuzluğu, (ii) gate ile order_send arası spread genişlemesi. Fix: `def4682`
   send-öncesi fresh-tick re-check → abort. Restart'ta iner.
3. **CHOP-DEATH entry** — 43 işlem, −36.7R. Gerçek false-breakout değil (0/43'ü sert
   ters gitti), yön-belirsiz chop'ta öldü. Kök: book-wide saat kalitesi —
   9h/11h/14h = −29.5R PF<0.25; 23h EN İYİ (PF 4.44). Lever: `blocked_entry_hours`
   (mekanizma + WFO axis `backtest.py:1263` ZATEN VAR, hiç populate edilmemiş).
   **LAND:** OPT_FIELDS + `blocked_hour_search_axis` + otopsi `fill_time` seed
   (`7f00f38`/`b3d9070`). Canlı `[]` — restart+WFO apply bekliyor.
   **RETRACT 04.09 00:22 (Claude):** per-symbol charged backtest'te 6/6 sembol
   PF<0.8 & n≥15 aday **yok** — book-wide saat sinyali karisim artefakti / 15g
   varyans. Hours WFO kampanyasi yok; kod idle kalabilir (`[]` hep aday).
   JPN[14,15] charged +3.1R — temizlik icin [] demek gerileme, **kalir**.

**SABAH KUYRUĞU:** (1) live SL / NAS WFO — **charged + autopsy** (bare force yok;
floor ≥0.9), (2) ~~hours WFO~~ RETRACT, (3) XAUUSD trail_start capture
(18:57 mfe 3.87→−0.01), (4) SpotBrent probe. Adreslenebilir bleed ~−96R
(premature+spread).
