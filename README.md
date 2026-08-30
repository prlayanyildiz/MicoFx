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
| `KUR.bat` · `KUR.ps1` | Tek kurulum |
| `start.bat` · `stop.bat` · `start_console.bat` | Baslat / durdur / konsol |
| `backup.py` | Aksam yedegi (Windows Gorev Zamanlayici) |
| `docs/` | [Kullanim](docs/KULLANIM.md) · [Kurulum ayrintilari](docs/KURULUM.md) |
| `MASTER_PROMPT.md` | Gelistirici / agent kaynagi |

## Yedek

`backup.py` her aksam Windows Gorev Zamanlayici ile calisir ve projeyi
zaman damgali bir zip'e alir. Ayar veritabani (`data/micofx.db`) zip'e ham
kopya olarak degil, sqlite'in kendi online-backup API'siyle **tutarli bir
anlik goruntu** olarak girer - bot yazarken alinsa bile restore edilebilir.

Sistem sekmesinden ayarlanir:

| Ayar | Ne |
|---|---|
| `backup_enabled` | Ana anahtar. Kapatilirsa gece gorevi calisir ama hicbir sey yazmaz |
| `backup_dir` | Birincil hedef. Varsayilan `C:\MicoFX_Yedek` - her makinede var olan bir yol |
| `backup_dir_secondary` | Ikincil hedef; bos birakilirsa kapali. Ayni zip buraya da kopyalanir |
| `backup_keep` | Her iki hedefte tutulacak en yeni yedek sayisi |

Yedek konumu bu makinede olmayan bir surucuyu gosteriyorsa (D: yok, USB
takili degil, ag surucusu kopuk) yedek alinmaz ve gorev **okunabilir bir hata**
verir - once yolu duzeltin, ya da otomatik yedegi kapatin.

**Ikinci hedefi mutlaka farkli bir FIZIKSEL diske ya da bir bulut klasorune
verin.** `C:` ve `D:` cogu makinede tek bir SSD'nin iki bolumudur - surucu
harfleri yedeklilik gibi gorunur ama degildir, disk olurse ikisi de gider.
Bu proje icin onemi ekstra buyuk: `data/micofx.db` Git'e girmez, yani her
sembol ayari, her optimizasyon sonucu ve AI denetleyicinin ogrendigi her sey
sadece o dosyada durur. GitHub kodu tutar, bunlarin hicbirini tutmaz.

Geri yuklerken ayar veritabanini **yalnizca** arsiv icindeki kanonik yoldan,
`data/micofx.db`'den alin. "Adi micofx.db ile biten ilk dosya" diye aramayin:
gecmiste test artigi kopyalar (`.pytest_tmp/...`) alfabetik siralamada once
geliyordu. Yedekleyici bu klasorleri artik disarida birakir ve arsivde ikinci
bir micofx.db gorurse uyarir, ama operatorun kurali sudur - tek dogru yol
`data/micofx.db`.

Gece gorevi **Interactive** olarak calisir: bilgisayar kilit ekranindayken
sorun yok, ama oturumu tamamen kapattiysaniz o gece yedek alinmaz. Isterseniz
Gorev Zamanlayici > "MicoFX Aksam Yedegi" > Ozellikler > **"Kullanici oturum
acmis olsun ya da olmasin calistir"** secebilirsiniz; bu Windows'a sifrenizi
kaydettirir, o yuzden karar sizin.

## Daha fazla

- Gunluk kullanim: [docs/KULLANIM.md](docs/KULLANIM.md)
- Kurulum ayrintilari, USB/klasor kopyasi: [docs/KURULUM.md](docs/KURULUM.md)
- Strateji, optimizer ve risk kurallari: [MASTER_PROMPT.md](MASTER_PROMPT.md)
