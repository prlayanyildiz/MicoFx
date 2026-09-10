# MicoFX

MetaTrader 5 uzerinde calisan otomatik islem sistemi ve web paneli.

Cikis mantigi tek ve degismez: **her pozisyon sert bir ATR stop ile acilir,
kar ATR'ye gore belirlenen esigi gectikten sonra takip eden stop devreye girer
ve stop asla geri gitmez.** Hedef (take-profit) yoktur, kademeli kar alma
yoktur, zaman stopu yoktur - trendin ne zaman bittigine takip eden stop karar
verir.

> Once demo hesapta calistirin. Finansal tavsiye degildir.

## Kurulum

**Gereken: Python 3.10 veya ustu** (kurulum 3.12.7 kurar - test edilen surum).
Daha eskisi kurulumu gecer ama uygulama acilmaz: pydantic modelleri `X | None`
sozdizimi kullaniyor ve 3.9 onu import aninda reddediyor.

**Sifir Windows PC** - Python, Git, hicbir sey kurulu olmasa da calisir.
PowerShell'i acip su tek satiri yapistir:

```powershell
irm https://raw.githubusercontent.com/prlayanyildiz/MicoFx/main/GETIR.ps1 | iex
```

`GETIR.ps1` sirayla: Python 3.12'yi kurar (winget yoksa python.org'dan
dogrudan indirir - Windows Server'da winget cogu zaman yoktur), depoyu
getirir (git varsa klonlar, yoksa ZIP indirir), sonra `KUR.bat` ile sanal
ortami ve paketleri kurar.

Python yeni kurulduysa PATH icin pencereyi bir kez kapatip acman ve ayni
satiri tekrar yapistirman gerekebilir - script bunu ekranda soyler ve
kaldigi yerden devam eder.

Ayni satir **guncelleme** icin de kullanilir.

### Git zaten varsa
```powershell
$d="$env:USERPROFILE\MicoFx"; if (Test-Path "$d\.git") { git -C $d pull } else { git clone https://github.com/prlayanyildiz/MicoFx.git $d }; cd $d; .\KUR.bat
```

### ZIP ile (git istemiyorsan)
```powershell
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $d="$env:USERPROFILE\MicoFx"; $z="$env:TEMP\micofx.zip"; $x="$env:TEMP\micofx_x"; Invoke-WebRequest "https://github.com/prlayanyildiz/MicoFx/archive/refs/heads/main.zip" -OutFile $z -UseBasicParsing; Remove-Item $x -Recurse -Force -ErrorAction SilentlyContinue; Expand-Archive $z $x -Force; if (Test-Path $d) { Copy-Item "$x\MicoFx-main\*" $d -Recurse -Force } else { Move-Item "$x\MicoFx-main" $d }; cd $d; .\KUR.bat
```

ZIP yolu git deposu kurmaz; sonraki guncellemeler icin ya git kur ya ayni
satiri tekrar calistir. `data/` ve `logs/` arsivde yok, yani mevcut
veritabani ve gunlukler uzerine yazilmaz.

## Nasil calisir

| Asama | Ne olur |
|---|---|
| Sinyal | 7 strateji ailesinden sembole atanmis olani, kapanmis bar uzerinde calisir |
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
| `MICOFX.bat` · `scripts/micofx.ps1` | Tek komut: start / stop / restart / sync / bridge |
| `KUR.bat` · `KUR.ps1` | Tek kurulum (`MICOFX install`) |
| `start.bat` · `stop.bat` · `start_console.bat` | Kod path'i (restart.bat app.py) |
| `backup.py` | Yedekleyici - **zamanlanmis gorev yok**, yalnizca elle |
| `docs/` | [Kullanim](docs/KULLANIM.md) · [Kurulum ayrintilari](docs/KURULUM.md) |
| `MASTER_PROMPT.md` | Gelistirici / agent kaynagi |

## Yedek — YOK

Yedekleme ozelligi 10.09'da **tamamen kaldirildi** (operator karari):
`backup.py`, zamanlanmis gorev, `SystemConfig.backup_*` alanlari, panelin
Yedek blogu ve kurulum adimi. Geri eklenmemeli.

Bedeli: **`data/micofx.db` Git'e girmez.** Her sembol ayari, her
optimizasyon sonucu ve denetleyicinin ogrendigi her sey yalnizca o
dosyada ve artik **tek kopya** - kod tarafinda ikincisini uretecek
hicbir sey yok. Kopya istiyorsan disaridan al.

## Daha fazla

- Gunluk kullanim: [docs/KULLANIM.md](docs/KULLANIM.md)
- Kurulum ayrintilari, USB/klasor kopyasi: [docs/KURULUM.md](docs/KURULUM.md)
- Strateji, optimizer ve risk kurallari: [MASTER_PROMPT.md](MASTER_PROMPT.md)
