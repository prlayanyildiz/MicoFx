# MicoFX bulut kurulumu. En kolay: KUR.bat'e cift tikla.
# (Private depo - irm|iex / raw.githubusercontent.com CALISMAZ.)
# Bot icin yeterli: Git + Python + paketler. Claude Code / Node GEREKMEZ.

$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/prlayanyildiz/MicoFx.git"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
# KUR.bat / bootstrap.ps1 zaten bir clone icinden calisiyorsa o klasoru kullan.
if (Test-Path (Join-Path $ScriptRoot ".git")) {
    $Dest = $ScriptRoot
} else {
    $Dest = "$env:USERPROFILE\MicoFx"
}
$TempDir = "$env:TEMP\micofx_bootstrap"

function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Install-ViaWinget($id) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) { return $false }
    try {
        winget install -e --id $id --silent --accept-package-agreements --accept-source-agreements
        Refresh-Path
        return $true
    } catch {
        return $false
    }
}

function Download-File($url, $outFile) {
    if (-not (Test-Path $TempDir)) { New-Item -ItemType Directory -Path $TempDir -Force | Out-Null }
    $path = Join-Path $TempDir $outFile
    Invoke-WebRequest -Uri $url -OutFile $path -UseBasicParsing
    return $path
}

function Ensure-Git {
    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host "[1/3] Git zaten kurulu." -ForegroundColor Cyan
        return
    }
    Write-Host "[1/3] Git kuruluyor..." -ForegroundColor Cyan
    Install-ViaWinget "Git.Git" | Out-Null
    if (Get-Command git -ErrorAction SilentlyContinue) { return }

    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/git-for-windows/git/releases/latest" -UseBasicParsing
    $asset = $release.assets | Where-Object { $_.name -like "*64-bit.exe" } | Select-Object -First 1
    $installer = Download-File $asset.browser_download_url $asset.name
    Start-Process -FilePath $installer -ArgumentList "/VERYSILENT", "/NORESTART", "/NOCANCEL", "/SP-" -Wait
    Refresh-Path
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git kurulamadi." }
}

function Ensure-Python {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        Write-Host "[2/3] Python zaten kurulu." -ForegroundColor Cyan
        return
    }
    Write-Host "[2/3] Python kuruluyor..." -ForegroundColor Cyan
    Install-ViaWinget "Python.Python.3.12" | Out-Null
    if (Get-Command python -ErrorAction SilentlyContinue) { return }

    $url = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    $installer = Download-File $url "python-installer.exe"
    Start-Process -FilePath $installer -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait
    Refresh-Path
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python kurulamadi." }
}

Write-Host "=== MicoFX bulut kurulumu (tam otomatik) ===" -ForegroundColor Cyan

Ensure-Git
Ensure-Python

Write-Host "[3/3] Kod indiriliyor/guncelleniyor ve MicoFX kuruluyor..." -ForegroundColor Cyan
if (Test-Path "$Dest\.git") {
    Push-Location $Dest
    git pull
    Pop-Location
} else {
    git clone $RepoUrl $Dest
}

Push-Location $Dest
# "< NUL": KURULUM.bat'in sonundaki/hata yollarindaki "pause" komutlari bir
# tus basimi bekler - girdi NUL'dan gelince hemen gecer, script kimseyi
# beklemeden sonuna kadar gider.
cmd /c "KURULUM.bat < NUL"
Pop-Location

# Kisayollar ayri script - bootstrap'i dusurmesin diye try/catch.
$shortcutScript = Join-Path $Dest "Create-Shortcuts.ps1"
if (Test-Path $shortcutScript) {
    try {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $shortcutScript
    } catch {
        Write-Host "[kisayol] Hata (kurulum yine tamam): $_" -ForegroundColor Yellow
        Write-Host "Elle dene: $Dest\kisayol.bat" -ForegroundColor Yellow
    }
} else {
    Write-Host "[kisayol] Create-Shortcuts.ps1 yok - git pull sonrasi kisayol.bat calistir." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Bitti." -ForegroundColor Green
Write-Host "1) MT5: Algoritmik alim satima izin ver" -ForegroundColor Green
Write-Host "2) Masaustu: MicoFX Baslat / Durdur / Terminal" -ForegroundColor Green
Write-Host "   (yoksa: $Dest\kisayol.bat)" -ForegroundColor Green
