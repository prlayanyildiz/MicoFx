# MicoFX - sifir PC kurulumu. Hicbir sey kurulu olmasa da calisir.
#
# PowerShell'i ACIP su tek satiri yapistir:
#   irm https://raw.githubusercontent.com/prlayanyildiz/MicoFx/main/GETIR.ps1 | iex
#
# Gereken Python: **3.10 veya ustu**. Bu script 3.12.7 kurar (test edilen
# surum). 3.9 ve oncesi kurulumu gecer ama uygulama acilmaz - run.py bunu
# MIN_PYTHON=(3,10) ile en basta reddeder.
#
# Ne yapar, sirayla:
#   1. Python 3.12.7 (yoksa: winget -> python.org'dan dogrudan indir -> elle)
#   2. Depoyu getirir (git varsa klonlar, yoksa ZIP indirir)
#   3. KUR.bat'i calistirir (sanal ortam + paketler + kisayollar)
#
# Neden ZIP yedegi var: Windows Server'da cogu zaman winget YOKTUR, ve
# winget yoksa git de kurulamaz. Klon yapilamayinca "KUR.bat'i calistir"
# tavsiyesi de bosa duser - dosyalar makinede degildir. ZIP yolu bu
# tavuk-yumurta dongusunu git'e hic dokunmadan kirar.

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Dest    = Join-Path $env:USERPROFILE "MicoFx"
$RepoGit = "https://github.com/prlayanyildiz/MicoFx.git"
$RepoZip = "https://github.com/prlayanyildiz/MicoFx/archive/refs/heads/main.zip"
$PyUrl   = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"

function Say([string]$m, [string]$c = "Gray") { Write-Host $m -ForegroundColor $c }
function Head([string]$m) { Write-Host ""; Say "== $m" "Cyan" }

function Refresh-Path {
    # Kurulumdan sonra PATH ayni pencerede gecerli olsun diye makine+kullanici
    # degiskenlerini yeniden okuyoruz. Git ve Python kendi klasorlerini oraya
    # yaziyor ama acik oturum eski kopyayi tasiyor.
    $m = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $u = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$m;$u"
    foreach ($p in @("C:\Program Files\Git\cmd",
                     "C:\Program Files\Python312",
                     "C:\Program Files\Python312\Scripts")) {
        if ((Test-Path -LiteralPath $p) -and ($env:Path -notlike "*$p*")) {
            $env:Path = "$p;$env:Path"
        }
    }
}

Say "=============================================" "Cyan"
Say "  MicoFX - sifir PC kurulumu" "Cyan"
Say "=============================================" "Cyan"
Say "  Hedef klasor : $Dest"
Say "  Gereken      : Python 3.10+ (kurulacak surum 3.12.7)"

# ------------------------------------------------------------------ Python
Head "1/3  Python"
Refresh-Path
$havePy = $false
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $havePy = $true
        Say ("  Var: " + (& python --version 2>&1)) "Green"
    } else {
        Say "  Python var ama 3.10'dan eski - MicoFX 3.10+ ister, yenisi kurulacak." "Yellow"
    }
}

if (-not $havePy) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Say "  winget ile Python 3.12 kuruluyor..." "Yellow"
        winget install -e --id Python.Python.3.12 --silent `
            --accept-package-agreements --accept-source-agreements
    } else {
        # winget yok (Windows Server'da normal). Kurulumu python.org'dan
        # dogrudan cekip sessiz kuruyoruz. PrependPath=1 sart: onsuz
        # "python" komutu PATH'te olusmaz ve KUR.ps1 ilk adimda durur.
        Say "  winget yok - Python 3.12 python.org'dan indiriliyor (~26 MB)..." "Yellow"
        $exe = Join-Path $env:TEMP "python-3.12.7-amd64.exe"
        Invoke-WebRequest -Uri $PyUrl -OutFile $exe -UseBasicParsing
        Say "  Sessiz kurulum basladi (birkac dakika)..."
        $p = Start-Process -FilePath $exe -Wait -PassThru -ArgumentList @(
            "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_pip=1",
            "Include_launcher=1", "Include_test=0")
        if ($p.ExitCode -ne 0) {
            Say "  Python kurulumu hata verdi (kod $($p.ExitCode))." "Red"
            Say "  Elle kurun, 'Add python.exe to PATH' kutusunu isaretleyin:" "Yellow"
            Start-Process "https://www.python.org/downloads/"
            throw "Python kurulamadi"
        }
        Remove-Item $exe -Force -ErrorAction SilentlyContinue
    }
    Refresh-Path
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Say ""
        Say "  Python kuruldu ama bu pencere eski PATH'i tasiyor." "Yellow"
        Say "  Bu pencereyi KAPATIN, yenisini acin ve ayni satiri" "Yellow"
        Say "  bir kez daha yapistirin. Kalan adimlar otomatik devam eder." "Yellow"
        exit 0
    }
    Say ("  Kuruldu: " + (& python --version 2>&1)) "Green"
}

# -------------------------------------------------------------------- Depo
Head "2/3  Depo"
$haveGit = [bool](Get-Command git -ErrorAction SilentlyContinue)

if (Test-Path (Join-Path $Dest ".git")) {
    if ($haveGit) {
        Say "  Mevcut klon guncelleniyor..."
        git -C $Dest pull
    } else {
        Say "  Klon var ama git yok - guncelleme atlandi." "Yellow"
    }
} elseif ($haveGit) {
    if (Test-Path $Dest) {
        Say "  Klasor var ama git deposu degil - ZIP ile uzerine yazilacak." "Yellow"
        $haveGit = $false
    } else {
        Say "  git ile klonlaniyor..."
        git clone $RepoGit $Dest
    }
}

if (-not (Test-Path (Join-Path $Dest "KUR.bat"))) {
    # git yok ya da klon basarisiz: ZIP. Guncelleme icin git kadar iyi degil
    # (versiyon gecmisi gelmez) ama calisan bir kurulum uretir.
    Say "  git yok - ZIP indiriliyor (~4 MB)..." "Yellow"
    $zip = Join-Path $env:TEMP "micofx.zip"
    $tmp = Join-Path $env:TEMP "micofx_zip"
    Invoke-WebRequest -Uri $RepoZip -OutFile $zip -UseBasicParsing
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive -Path $zip -DestinationPath $tmp -Force
    $src = Join-Path $tmp "MicoFx-main"
    if (Test-Path $Dest) {
        # Uzerine yaziyoruz ama data/ ve logs/ arsivde yok, yani mevcut
        # veritabani ve gunlukler oldugu gibi kalir.
        Copy-Item (Join-Path $src "*") $Dest -Recurse -Force
    } else {
        Move-Item $src $Dest
    }
    Remove-Item $zip, $tmp -Recurse -Force -ErrorAction SilentlyContinue
    Say "  ZIP ile kuruldu. NOT: guncelleme icin ya git kurun ya bu satiri" "Yellow"
    Say "  tekrar calistirin." "Yellow"
}

if (-not (Test-Path (Join-Path $Dest "KUR.bat"))) { throw "Depo getirilemedi: $Dest" }
Say "  Hazir: $Dest" "Green"

# ------------------------------------------------------------------- Kurul
Head "3/3  Ortam kurulumu"
Set-Location $Dest
& (Join-Path $Dest "KUR.bat")
