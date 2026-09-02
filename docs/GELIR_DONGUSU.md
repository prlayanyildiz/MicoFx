# Gelir geliştirme döngüsü (tam otomatik)

Sonsuz iyileştirme hattı: ölç → güvenli düzelt → araştır → kodla → test et → sync.

## Bileşenler

| Parça | Açıklama |
|-------|----------|
| `scripts/auto_pilot.py` | **Ana giriş** — gelir döngüsü + AR-GE taraması |
| `scripts/income_dev_loop.py` | Audit, trust mode, spread, holdout hizala |
| `scripts/holdout_live_sync.py` | Flat aktif sembollerde spread + config |
| `scripts/kasa_auto.py` | Kaldıraç + equity → lot/marj/conc risk otomatik ayar |
| `scripts/start_income_loop.ps1` | 15 dk auto_pilot daemon |
| `GELIR_DONGUSU.bat` | Döngü + auto git sync başlatır |
| `AUTO_GIT_SYNC.bat` | Otomatik commit/push (~90s debounce) |
| `logs/income_loop_latest.md` | Son gelir raporu |
| `logs/research_latest.md` | Son AR-GE raporu |
| `cursor/FOR_CLAUDE.md` | Köprü özeti (agent uyandırma) |
| `cursor/RESEARCH_QUEUE.md` | Uygulanabilir AR-GE kuyruğu |

## Başlatma

```
GELIR_DONGUSU.bat
```

Tek seferlik:

```
C:\MicoFX-venv\Scripts\python.exe scripts\auto_pilot.py
```

## Her 15 dakikada

1. **Gelir audit** — aktif semboller, holdout, entry-blocks, marj
2. **Kasa auto** — equity + kaldıraç (1:500) → lot_multiplier / marj % / eşzamanlı risk
3. **Trust mode** — AI engellemez (sadece lot kısar); spread kalibre
3. **Holdout sync** — flat aktif sembollerde EXEC/DRIFT hizala
4. **AR-GE taraması** — GitHub + web; `RESEARCH_QUEUE.md` güncelle
5. **Köprü** — `FOR_CLAUDE.md` agent için özet
6. **Git sync** — değişiklik varsa otomatik commit/push

## Operator kuralları

- **Kapattığın sembol açılmaz** — otomasyon sadece `enabled=true` olanları işler
- **Kasa auto** — `scripts/kasa_auto.py`: 1:500 + equity → lot_multiplier / marj % / concurrent risk
- **Opt zorla yok** — karantina dışı otomatik search yok (AGENTS.md)
- **partial/harvest kapalı** — F41/F44

## Agent prompt (her tick)

```
auto_pilot tick: logs/income_loop_latest.md, logs/research_latest.md,
cursor/FOR_CLAUDE.md, cursor/RESEARCH_QUEUE.md oku.
Constitution-safe aksiyonlari uygula; pytest+ruff; commit operator isteyince.
```
