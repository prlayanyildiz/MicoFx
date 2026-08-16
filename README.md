# MicoFX

MetaTrader 5 uzerinde calisan otomatik islem sistemi ve web paneli.

Cikis mantigi tek ve degismez: **her pozisyon sert bir ATR stop ile acilir,
kar ATR'ye gore belirlenen esigi gectikten sonra takip eden stop devreye girer
ve stop asla geri gitmez.** Hedef (take-profit) yoktur, kademeli kar alma
yoktur, zaman stopu yoktur - trendin ne zaman bittigine takip eden stop karar
verir.

> Once demo hesapta calistirin. Finansal tavsiye degildir.

## Kurulum

Sifir Windows PC. Repo **ozel** oldugu icin `irm ... raw.githubusercontent`
404 doner - scripti GitHub'dan cekemezsin. Asagidaki blogu oldugu gibi
yapistir (Git yoksa onu da kurar, sonra klonlar; ozel depo icin GitHub
girisi ister):

```powershell
$ErrorActionPreference="Stop"
function Refresh-Path { $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine")+";"+[Environment]::GetEnvironmentVariable("Path","User"); if (Test-Path "C:\Program Files\Git\cmd\git.exe") { $env:Path = "C:\Program Files\Git\cmd;"+$env:Path } }
Refresh-Path
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { Start-Process "https://git-scm.com/download/win"; throw "Git ve winget yok" }
  winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
  Refresh-Path
  if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Write-Host "Pencereyi kapat, ayni blogu tekrar yapistir." -ForegroundColor Yellow; return }
}
$d="$env:USERPROFILE\MicoFx"
if (Test-Path "$d\.git") { git -C $d pull } elseif (Test-Path $d) { throw "Klasor var ama git degil: $d" } else { git clone https://github.com/prlayanyildiz/MicoFx.git $d }
cd $d; .\KUR.bat
```

Git kurulumundan sonra PATH icin pencereyi kapatip blogu bir kez daha
yapistirman gerekebilir. Hem ilk kurulum hem guncelleme. Repo herkese
aciksa `GETIR.ps1` tek satiri da olur:

```powershell
irm https://raw.githubusercontent.com/prlayanyildiz/MicoFx/main/GETIR.ps1 | iex
```

Git zaten varsa eski tek satir da olur:

```powershell
$d="$env:USERPROFILE\MicoFx"; if (Test-Path "$d\.git") { git -C $d pull } else { git clone https://github.com/prlayanyildiz/MicoFx.git $d }; cd $d; .\KUR.bat
```

Klasor zaten varsa yeniden klonlamak yerine `git pull` eder - `git clone`
bos olmayan bir klasore yazmayi reddeder ve o hatadan sonra `.\KUR.bat` da
bulunamaz.

Hedefi mutlak yolla verir, bu yuzden nereden calistirildigi onemli degil.
Goreli `MicoFx` kullanan bir surumu depo klasorunun ICINDEN calistirmak
`MicoFx\MicoFx` diye ic ice bir klasor aciyordu.

Klasor var ama depo degilse (yarim kalmis bir klonlama, elle acilmis bos
klasor) once onu tasiyin ya da silin: `Remove-Item $env:USERPROFILE\MicoFx
-Recurse -Force`. Icinde eski bir kurulumun `data\` klasoru olabilecegi icin
bu komut kasitli olarak tek satirin disinda birakildi.

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
