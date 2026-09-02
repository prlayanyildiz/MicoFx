# Gelir geliştirme döngüsü

Sonsuz iyileştirme hattı: ölç → güvenli düzelt → planla → kodla → test et.

## Bileşenler

| Parça | Açıklama |
|-------|----------|
| `scripts/income_dev_loop.py` | DB + panel audit; `partial_at_r=0`, `autostart_bot` güvenli fix |
| `scripts/start_income_loop.ps1` | 6 saatte bir audit (PowerShell döngüsü) |
| `GELIR_DONGUSU.bat` | Döngü + auto git sync başlatır |
| `AUTO_GIT_SYNC.bat` | Sadece otomatik commit/push (~90s debounce) |
| `logs/income_loop_latest.md` | Son rapor (Türkçe) |
| `cursor/FOR_CLAUDE.md` | Köprü özeti (agent uyandırma) |

## Başlatma

```
GELIR_DONGUSU.bat
```

veya tek seferlik:

```
C:\MicoFX-venv\Scripts\python.exe scripts\income_dev_loop.py --apply-safe
```

## Her turda ne olur

1. **Audit** — holdout net R, supervisor, opt yaşı, risk ayarları
2. **Güvenli fix** — `partial_at_r≠0` → 0; `autostart_bot` kapalıysa aç
3. **Koru** — canlı skor > opt adayı ise uygulama yok (churn freni)
4. **Reopt planı** — 48 saat + zayıf retention/watch semboller listelenir
5. **Agent tick** — Cursor agent raporu okur, kod/test/commit (operator onayı)

## Gelir kuralları (değiştirme)

- **XAUUSD / NAS100 (mtf_pullback) / JPN225** — risk bütçesi önceliği (`supervisor.priority` + `size_by_edge`)
- **partial_at_r, harvest** — kapalı (F41/F44)
- **Emekli aileler** — uygulanmaz
- **Opt zorla** — sadece pozisyon yokken, operator veya agent onayıyla
- **Sarı kırmızı** — `size_by_edge`, `daily_loss_pct`, kaldıraç: operator kararı

## Cursor agent prompt (her tick)

```
Gelir dongusu tick: logs/income_loop_latest.md ve cursor/FOR_CLAUDE.md oku.
Onerilen aksiyonlari uygula; guvenli kod iyilestirmeleri yap; pytest+ruff;
commit/push sadece operator isteyince.
```
