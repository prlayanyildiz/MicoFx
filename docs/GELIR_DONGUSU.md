# Gelir geliştirme döngüsü (bot içi)

Gelir döngüsü **Engine içinde** (`autopilot_enabled`). Dış PowerShell yok.

Tek komut: `MICOFX.bat` → `scripts/micofx.ps1`.

| Parça | Açıklama |
|-------|----------|
| Sistem > Gelir autopilot | Canlı döngü |
| `MICOFX start` / `stop` / `restart` | Bot |
| `MICOFX sync` | `scripts/auto_git_sync.ps1` |
| `MICOFX bridge` | `scripts/start_bridge_daemon.ps1` (çalışıyorsa no-op) |
| `scripts/auto_pilot.py` | Elle AR-GE taraması (opsiyonel) |

`GELIR_DONGUSU.bat` ve `scripts/start_income_loop.ps1` silindi (03.09).
