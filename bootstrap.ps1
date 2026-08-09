# MicoFX bulut kurulumu. En kolay: KUR.bat'e cift tikla.
# (Private depo - irm|iex / raw.githubusercontent.com CALISMAZ.)

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
        Write-Host "[1/5] Git zaten kurulu." -ForegroundColor Cyan
        return
    }
    Write-Host "[1/5] Git kuruluyor..." -ForegroundColor Cyan
    Install-ViaWinget "Git.Git" | Out-Null
    if (Get-Command git -ErrorAction SilentlyContinue) { return }

    # winget yok/basarisiz - GitHub'dan son surumun 64-bit kurulumunu dogrudan indir.
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/git-for-windows/git/releases/latest" -UseBasicParsing
    $asset = $release.assets | Where-Object { $_.name -like "*64-bit.exe" } | Select-Object -First 1
    $installer = Download-File $asset.browser_download_url $asset.name
    Start-Process -FilePath $installer -ArgumentList "/VERYSILENT", "/NORESTART", "/NOCANCEL", "/SP-" -Wait
    Refresh-Path
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "Git kurulamadi." }
}

function Ensure-Python {
    if (Get-Command python -ErrorAction SilentlyContinue) {
        Write-Host "[2/5] Python zaten kurulu." -ForegroundColor Cyan
        return
    }
    Write-Host "[2/5] Python kuruluyor..." -ForegroundColor Cyan
    Install-ViaWinget "Python.Python.3.12" | Out-Null
    if (Get-Command python -ErrorAction SilentlyContinue) { return }

    # winget yok/basarisiz - python.org'dan dogrudan indir.
    $url = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
    $installer = Download-File $url "python-installer.exe"
    Start-Process -FilePath $installer -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait
    Refresh-Path
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python kurulamadi." }
}

function Ensure-Node {
    if (Get-Command node -ErrorAction SilentlyContinue) {
        Write-Host "[3/5] Node.js zaten kurulu." -ForegroundColor Cyan
        return
    }
    Write-Host "[3/5] Node.js kuruluyor (Claude Code icin gerekli)..." -ForegroundColor Cyan
    Install-ViaWinget "OpenJS.NodeJS.LTS" | Out-Null
    if (Get-Command node -ErrorAction SilentlyContinue) { return }

    # winget yok/basarisiz - nodejs.org'dan en son LTS surumunu bulup dogrudan indir.
    $index = Invoke-RestMethod -Uri "https://nodejs.org/dist/index.json" -UseBasicParsing
    $lts = $index | Where-Object { $_.lts -ne $false } | Select-Object -First 1
    $url = "https://nodejs.org/dist/$($lts.version)/node-$($lts.version)-x64.msi"
    $installer = Download-File $url "node-installer.msi"
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i", "`"$installer`"", "/quiet", "/norestart" -Wait
    Refresh-Path
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js kurulamadi." }
}

function Ensure-ClaudeCode {
    # npm'in claude.ps1 shim'i Restricted ExecutionPolicy'de patlar
    # (PSSecurityException). CurrentUser RemoteSigned bunu kalici acar.
    # Not: bootstrap "Bypass -File" ile acildiginda Process scope Bypass
    # olur; Set-ExecutionPolicy CurrentUser'i yine yazar ama "overridden by
    # a more specific scope" diye ERROR kaydi dusebilir - bu basarisizlik
    # degil. Sonrasi Get-ExecutionPolicy -Scope CurrentUser ile dogrulanir.
    $pol = Get-ExecutionPolicy -Scope CurrentUser
    if ($pol -eq "Undefined" -or $pol -eq "Restricted" -or $pol -eq "AllSigned") {
        try {
            Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force -ErrorAction SilentlyContinue
        } catch {
            # ignore - verify below
        }
        $polAfter = Get-ExecutionPolicy -Scope CurrentUser
        if ($polAfter -eq "RemoteSigned" -or $polAfter -eq "Unrestricted" -or $polAfter -eq "Bypass") {
            Write-Host "[4/5] PowerShell ExecutionPolicy CurrentUser=$polAfter (claude.ps1 icin)." -ForegroundColor Cyan
        } else {
            Write-Host "[4/5] ExecutionPolicy CurrentUser hala $polAfter - 'claude' yerine 'claude.cmd' kullan." -ForegroundColor Yellow
        }
    }
    if (Get-Command claude -ErrorAction SilentlyContinue) {
        Write-Host "[4/5] Claude Code zaten kurulu." -ForegroundColor Cyan
        return
    }
    Write-Host "[4/5] Claude Code kuruluyor..." -ForegroundColor Cyan
    npm install -g @anthropic-ai/claude-code
    Refresh-Path
}

Write-Host "=== MicoFX bulut kurulumu (tam otomatik) ===" -ForegroundColor Cyan

Ensure-Git
Ensure-Python
Ensure-Node
Ensure-ClaudeCode

Write-Host "[5/5] Kod indiriliyor/guncelleniyor ve MicoFX kuruluyor..." -ForegroundColor Cyan
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

Write-Host ""
Write-Host "Bitti." -ForegroundColor Green
Write-Host "1) MT5: Algoritmik alim satima izin ver" -ForegroundColor Green
Write-Host "2) start.bat ile baslat" -ForegroundColor Green
Write-Host "Claude: cd `"$Dest`"; claude   (olmazsa claude.cmd)" -ForegroundColor Green
