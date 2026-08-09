# MicoFX

MetaTrader 5 uzerinde otomatik islem sistemi + web paneli.  
Dort strateji ailesi, ATR risk, gunluk zarar kesici, sembol saatleri, AI risk denetleyici.

> Once demo. Finansal tavsiye degildir.

## Klasor

| Yol | Ne |
|---|---|
| `micofx/` | Kod |
| `config/defaults.json` | Ilk sablon |
| `data/` / `logs/` | Runtime DB + log (Git disi) |
| `docs/` | [Kullanim](docs/KULLANIM.md) · [Yerel kurulum](docs/KURULUM.md) |
| `MASTER_PROMPT.md` | Gelistirici / agent kaynagi |
| `KUR.bat` | Bulut kurulum (Git + Python + paket + kisayol) |
| `KURULUM.bat` | Sadece venv + pip |
| `start.bat` / `stop.bat` / `start_console.bat` | Baslat / durdur / konsol |
| `kisayol.bat` | Masaustu kisayollari |
| `backup.py` | Aksam yedegi (Task Scheduler) |
| `requirements.txt` / `run.py` | Bagimlilik + giris |

## Bulut kurulum

Private depo — tek satir indirme calismaz.

1. [Git kur](https://git-scm.com/download/win) → Next → PowerShell kapat/ac  
2.
```powershell
cd $env:USERPROFILE
git clone https://github.com/prlayanyildiz/MicoFx.git
cd MicoFx
.\KUR.bat
```
3. MT5: **Algoritmik alim satima izin ver** → masaustu **MicoFX Baslat**

Gunluk: `git pull` → gerekirse `.\KUR.bat` / `.\kisayol.bat`.  
USB / klasor kopyasi: [docs/KURULUM.md](docs/KURULUM.md).

## Calistirma

```powershell
.\start.bat
```

Panel: `http://127.0.0.1:8900` (`MICO_PORT` ile degisir).  
Acilista **izleme** modu — emir icin panelden **Bot Baslat**.

**Ayni MT5 hesabinda yerelde + bulutta ayni anda bot acma.**

## Daha fazla

- Kullanim: [docs/KULLANIM.md](docs/KULLANIM.md)  
- Strateji / optimizer / risk kurallari: [MASTER_PROMPT.md](MASTER_PROMPT.md)  
- Yerel kurulum: [docs/KURULUM.md](docs/KURULUM.md)
