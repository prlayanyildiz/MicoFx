# MicoFX - tek komutla bulut sunucu kurulumu.
# Calistirma: PowerShell'de (Yonetici degil, normal kullanici yeterli):
#   irm https://raw.githubusercontent.com/prlayanyildiz/MicoFx/main/bootstrap.ps1 | iex
#
# Yapar: Git yoksa kurar, Python yoksa kurar, depoyu klonlar/gunceller,
# KURULUM.bat'i calistirir. Zaten klonlanmis bir klasorde tekrar
# calistirilirsa "git pull" ile gunceller, yeniden klonlamaz.

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/prlayanyildiz/MicoFx.git"
$Dest = "$env:USERPROFILE\MicoFx"

function Ensure-Winget {
    if (Get-Command winget -ErrorAction SilentlyContinue) { return $true }
    Write-Host "winget bulunamadi - Git ve Python'u elle kurman gerekecek." -ForegroundColor Yellow
    Write-Host "  Git:    https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "  Python: https://www.python.org/downloads/ (kurulumda 'Add python.exe to PATH' isaretle)" -ForegroundColor Yellow
    return $false
}

Write-Host "=== MicoFX bulut kurulumu ===" -ForegroundColor Cyan

$hasWinget = Ensure-Winget

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    if ($hasWinget) {
        Write-Host "[1/4] Git kuruluyor..." -ForegroundColor Cyan
        winget install -e --id Git.Git --silent --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    } else {
        throw "Git kurulu degil ve winget yok. Once Git'i elle kurup bu scripti tekrar calistir."
    }
} else {
    Write-Host "[1/4] Git zaten kurulu." -ForegroundColor Cyan
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    if ($hasWinget) {
        Write-Host "[2/4] Python kuruluyor..." -ForegroundColor Cyan
        winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    } else {
        throw "Python kurulu degil ve winget yok. Once Python'u elle kurup bu scripti tekrar calistir."
    }
} else {
    Write-Host "[2/4] Python zaten kurulu." -ForegroundColor Cyan
}

Write-Host "[3/4] Kod indiriliyor/guncelleniyor..." -ForegroundColor Cyan
if (Test-Path "$Dest\.git") {
    Push-Location $Dest
    git pull
    Pop-Location
} else {
    git clone $RepoUrl $Dest
}

Write-Host "[4/4] MicoFX kuruluyor (KURULUM.bat)..." -ForegroundColor Cyan
Push-Location $Dest
cmd /c KURULUM.bat
Pop-Location

Write-Host ""
Write-Host "Bitti. Simdi MT5'e giris yap, sonra '$Dest\start.bat' ile baslat." -ForegroundColor Green
