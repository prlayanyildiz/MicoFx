# MicoFX - sifir PC: Git yoksa kur, depoyu cek, KUR.ps1'i calistir.
# PowerShell'de:  irm https://raw.githubusercontent.com/prlayanyildiz/MicoFx/main/GETIR.ps1 | iex
# Klon yokken KUR.bat calisamaz; bu dosya o tavuk-yumurta sorununu kapatir.

$ErrorActionPreference = "Stop"
$Dest = Join-Path $env:USERPROFILE "MicoFx"
$Repo = "https://github.com/prlayanyildiz/MicoFx.git"

function Say([string]$msg, [string]$colour = "Gray") {
    Write-Host $msg -ForegroundColor $colour
}

function Refresh-Path {
    $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
    $gitCmd = "C:\Program Files\Git\cmd"
    if ((Test-Path -LiteralPath (Join-Path $gitCmd "git.exe")) -and ($env:Path -notlike "*$gitCmd*")) {
        $env:Path = "$gitCmd;$env:Path"
    }
}

function Ensure-Git {
    Refresh-Path
    if (Get-Command git -ErrorAction SilentlyContinue) { return $true }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Say "Git yok ve winget de yok. Git for Windows'u kurun (PATH isaretli)," "Yellow"
        Say "PowerShell'i kapatip bu satiri tekrar yapistirin." "Yellow"
        Start-Process "https://git-scm.com/download/win"
        return $false
    }
    Say "Git bulunamadi - winget ile kuruluyor (birkaç dakika)..." "Yellow"
    winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
    Refresh-Path
    if (Get-Command git -ErrorAction SilentlyContinue) { return $true }
    Say "Git kuruldu. PATH icin bu pencereyi KAPATIP su satiri tekrar yapistirin:" "Yellow"
    Say "  irm https://raw.githubusercontent.com/prlayanyildiz/MicoFx/main/GETIR.ps1 | iex" "Cyan"
    return $false
}

Say "============================================" "Cyan"
Say "  MicoFX getir + kur" "Cyan"
Say "============================================" "Cyan"

if (-not (Ensure-Git)) { exit 1 }
Say ("  Git: " + (git --version 2>&1)) "Green"

if (Test-Path -LiteralPath (Join-Path $Dest ".git")) {
    Say "  Depo var, guncelleniyor: $Dest" "Gray"
    git -C $Dest pull
} elseif (Test-Path -LiteralPath $Dest) {
    Say "Klasor var ama git deposu degil: $Dest" "Yellow"
    Say "Tasiyin veya silin, sonra tekrar deneyin." "Yellow"
    Say "  Remove-Item `"$Dest`" -Recurse -Force" "Cyan"
    exit 1
} else {
    Say "  Klonlaniyor: $Dest" "Gray"
    git clone $Repo $Dest
}

$kur = Join-Path $Dest "KUR.ps1"
if (-not (Test-Path -LiteralPath $kur)) {
    throw "Klon tamam ama KUR.ps1 yok: $kur"
}
& powershell -NoProfile -ExecutionPolicy Bypass -File $kur
exit $LASTEXITCODE
