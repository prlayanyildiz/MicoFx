# MicoFX - tek kurulum. Python + sanal ortam + paketler + masaustu kisayollari.
#
# Tek giris noktasi budur. KUR.bat sadece bu dosyayi ExecutionPolicy Bypass ile
# cagirir; baska kurulum scripti yok. Bastan calistirmak guvenli - her adim
# zaten yapilmissa atlanir, yani ayni dosya hem ilk kurulum hem guncelleme
# sonrasi tazeleme icin kullanilir.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Sanal ortam bilerek proje klasorunun DISINDA. Bir venv, kuruldugu makinenin
# python.exe yoluna mutlak referans tutar; OneDrive proje klasorunu baska bir
# bilgisayara senkronlarsa oradaki ".venv" bozuk cikar ("No Python at ...") ve
# iki makine ayni klasoru paylasinca hangisi son senkronlarsa digerini bozar.
# Burada her makine kendi venv'ini bir kez kurar, senkron ona hic dokunmaz.
$Venv = "C:\MicoFX-venv"
$VenvPy = Join-Path $Venv "Scripts\python.exe"

function Say([string]$msg, [string]$colour = "Gray") { Write-Host $msg -ForegroundColor $colour }
function Step([int]$n, [string]$msg) { Write-Host ""; Say "[$n/4] $msg" "Cyan" }

Say "============================================" "Cyan"
Say "  MicoFX kurulum" "Cyan"
Say "============================================" "Cyan"
Say "  Klasor      : $Root"
Say "  Sanal ortam : $Venv"

# --------------------------------------------------------------- [1] Python
Step 1 "Python kontrol ediliyor..."
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Say "  Python bulunamadi." "Yellow"
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Say "  winget ile Python 3.12 kuruluyor (birkac dakika surebilir)..."
        winget install -e --id Python.Python.3.12 --silent `
            --accept-package-agreements --accept-source-agreements
        Say ""
        Say "  Python kuruldu. PATH'in etkin olmasi icin bu pencereyi KAPATIP" "Yellow"
        Say "  KUR.bat'i YENIDEN calistirin." "Yellow"
        exit 0
    }
    Say "  winget de yok - Python'u elle kurmaniz gerekiyor." "Yellow"
    Say "  Kurulum ekraninin ALT KISMINDAKI 'Add python.exe to PATH'" "Yellow"
    Say "  kutucugunu MUTLAKA isaretleyin, sonra KUR.bat'i tekrar calistirin." "Yellow"
    Start-Process "https://www.python.org/downloads/"
    exit 1
}
Say "  Bulundu: $python" "Green"
Say ("  " + (& python --version 2>&1))

# ---------------------------------------------------------- [2] Sanal ortam
Step 2 "Sanal ortam hazirlaniyor..."
if (Test-Path -LiteralPath $VenvPy) {
    Say "  Zaten var, atlaniyor." "Green"
} else {
    & python -m venv $Venv
    if (-not (Test-Path -LiteralPath $VenvPy)) { throw "Sanal ortam olusturulamadi: $Venv" }
    Say "  Olusturuldu." "Green"
}

# ----------------------------------------------------------- [3] Paketler
Step 3 "Bagimliliklar kuruluyor (birkac dakika surebilir)..."
& $VenvPy -m pip install --upgrade pip --quiet
& $VenvPy -m pip install -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Bagimliliklar kurulamadi - yukaridaki mesaja bakin." }
Say "  Tamam." "Green"

if (Test-Path -LiteralPath (Join-Path $Root ".venv\Scripts\python.exe")) {
    Say "  Not: proje icinde eski bir .venv duruyor, artik kullanilmiyor." "Yellow"
    Say "  Silebilirsiniz; yer kaplamak disinda zarari yok." "Yellow"
}

# --------------------------------------------------------- [4] Kisayollar
Step 4 "Masaustu kisayollari olusturuluyor..."

# Birden fazla aday: OneDrive yonlendirmesi, is/okul OneDrive'i ve ortak
# masaustu ayni makinede farkli yerlerde olabilir; hangisi gercek masaustuyse
# kullanicinin gordugu o. Hepsine yazmak, yanlis birini secip "kisayol
# gorunmuyor" demekten iyi.
$candidates = New-Object System.Collections.Generic.List[string]
foreach ($p in @(
    [Environment]::GetFolderPath("Desktop"),
    [Environment]::GetFolderPath("CommonDesktopDirectory"),
    (Join-Path $env:USERPROFILE "Desktop"),
    (Join-Path $env:USERPROFILE "OneDrive\Desktop")
)) {
    if (-not [string]::IsNullOrWhiteSpace($p) -and -not $candidates.Contains($p)) {
        [void]$candidates.Add($p)
    }
}
Get-ChildItem -Path $env:USERPROFILE -Directory -Filter "OneDrive*" -ErrorAction SilentlyContinue |
    ForEach-Object {
        $d = Join-Path $_.FullName "Desktop"
        if (-not $candidates.Contains($d)) { [void]$candidates.Add($d) }
    }

$items = @(
    @{ Name = "MicoFX Baslat";   Rel = "start.bat";         Style = 7; Desc = "MicoFX baslat (sessiz)" },
    @{ Name = "MicoFX Durdur";   Rel = "stop.bat";          Style = 1; Desc = "MicoFX durdur" },
    @{ Name = "MicoFX Terminal"; Rel = "start_console.bat"; Style = 1; Desc = "MicoFX konsol" }
)

$shell = New-Object -ComObject WScript.Shell
$written = 0
foreach ($desk in $candidates) {
    if (-not (Test-Path -LiteralPath $desk)) { continue }   # yoksa olusturma, gercek masaustu degil
    foreach ($it in $items) {
        $target = Join-Path $Root $it.Rel
        if (-not (Test-Path -LiteralPath $target)) { continue }
        try {
            $lnk = $shell.CreateShortcut((Join-Path $desk "$($it.Name).lnk"))
            $lnk.TargetPath = $target
            $lnk.WorkingDirectory = $Root
            $lnk.WindowStyle = [int]$it.Style
            $lnk.Description = "$($it.Desc) ($Root)"
            $lnk.Save()
            $written++
        } catch {
            Say "  Yazilamadi: $desk\$($it.Name).lnk" "Yellow"
        }
    }
    try {
        $lnk = $shell.CreateShortcut((Join-Path $desk "MicoFX Klasor.lnk"))
        $lnk.TargetPath = $Root
        $lnk.WorkingDirectory = $Root
        $lnk.Description = "MicoFX proje klasoru"
        $lnk.Save()
        $written++
    } catch { }
}
if ($written -gt 0) { Say "  $written kisayol yazildi (masaustunde F5)." "Green" }
else { Say "  Kisayol yazilamadi - start.bat'i klasorden calistirabilirsiniz." "Yellow" }

# ------------------------------------------------------------------- bitti
Write-Host ""
Say "============================================" "Green"
Say "  Kurulum tamam." "Green"
Say "============================================" "Green"
Write-Host ""
Say "Sirada:"
Say "  1) MetaTrader 5'i kurup hesabiniza giris yapin."
Say "  2) MT5 > Araclar > Secenekler > Uzman Danismanlar sekmesinde"
Say "     'Algoritmik alim satima izin ver' kutusunu isaretleyin."
Say "  3) Masaustundeki 'MicoFX Baslat' kisayoluna cift tiklayin."
Write-Host ""
Say "Panel: http://127.0.0.1:8900" "Cyan"
Say "Acilista sistem IZLEME modundadir - emir gonderilmesi icin panelden"
Say "'Bot Baslat' demeniz gerekir."
Write-Host ""
