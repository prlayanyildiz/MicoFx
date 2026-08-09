# MicoFX

MetaTrader 5 uzerinde calisan otomatik islem sistemi ve web paneli.

Cikis mantigi tek ve degismez: **her pozisyon sert bir ATR stop ile acilir,
kar ATR'ye gore belirlenen esigi gectikten sonra takip eden stop devreye girer
ve stop asla geri gitmez.** Hedef (take-profit) yoktur, kademeli kar alma
yoktur, zaman stopu yoktur - trendin ne zaman bittigine takip eden stop karar
verir.

> Once demo hesapta calistirin. Finansal tavsiye degildir.

## Kurulum

Tek dosya. [Git](https://git-scm.com/download/win) kurulu degilse once onu
kurun ve PowerShell'i kapatip yeniden acin.

```powershell
cd $env:USERPROFILE
git clone https://github.com/prlayanyildiz/MicoFx.git
cd MicoFx
.\KUR.bat
```

`KUR.bat` Python'u, sanal ortami, paketleri ve masaustu kisayollarini
halleder. Bastan calistirmak guvenli - yapilmis adimlari atlar, bu yuzden
`git pull` sonrasi tazeleme icin de ayni dosyayi kullanin.

Sonra MetaTrader 5'te **Araclar > Secenekler > Uzman Danismanlar > Algoritmik
alim satima izin ver** kutusunu isaretleyin ve masaustundeki **MicoFX Baslat**
kisayoluna cift tiklayin.

Panel: <http://127.0.0.1:8900> (`MICO_PORT` ile degistirilebilir).

**Acilista sistem izleme modundadir.** Emir gonderilmesi icin panelden **Bot
Baslat** demeniz gerekir. Ayni MT5 hesabinda ayni anda iki bot calistirmayin.

## Nasil calisir

| Asama | Ne olur |
|---|---|
| Sinyal | 20 strateji ailesinden sembole atanmis olani, kapanmis bar uzerinde calisir |
| Filtre | Seans saatleri, spread/ATR orani, ADX rejimi, gunluk zarar kesici |
| Boyut | Risk yuzdesi ve ATR stop mesafesinden lot; AI denetleyici gerekirse kucultur |
| Giris | Piyasa emri + sert ATR stop (broker'da durur, hicbir kosulda kaldirilmaz) |
| Takip | Kar `trail_start x ATR`'yi gecince stop `trail_step x ATR` mesafeden mandalli izler |
| Cikis | Yalnizca stop. Ek olarak seans sonu / gun sonu / gunluk zarar flatten'i |

Optimizer, her sembol icin strateji + zaman dilimi + stop/takip parametrelerini
yuruyen-ileri (walk-forward) test ile arar. Bir aday ancak hem secmeli
dogrulama hem de hic dokunulmamis test diliminde mevcut ayardan iyiyse
uygulanir; degilse mevcut ayar korunur.

## Klasor

| Yol | Ne |
|---|---|
| `micofx/` | Kod (motor, strateji, optimizer, risk, web) |
| `config/defaults.json` | Ilk sablon ve optimizer arama gridi |
| `data/` · `logs/` | Runtime DB ve log (Git disi) |
| `KUR.bat` · `KUR.ps1` | Tek kurulum |
| `start.bat` · `stop.bat` · `start_console.bat` | Baslat / durdur / konsol |
| `backup.py` | Aksam yedegi (Windows Gorev Zamanlayici) |
| `docs/` | [Kullanim](docs/KULLANIM.md) · [Kurulum ayrintilari](docs/KURULUM.md) |
| `MASTER_PROMPT.md` | Gelistirici / agent kaynagi |

## Daha fazla

- Gunluk kullanim: [docs/KULLANIM.md](docs/KULLANIM.md)
- Kurulum ayrintilari, USB/klasor kopyasi: [docs/KURULUM.md](docs/KURULUM.md)
- Strateji, optimizer ve risk kurallari: [MASTER_PROMPT.md](MASTER_PROMPT.md)
