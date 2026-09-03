# MicoFX operator dispatcher. Hardcoded callers (restart.bat, stop.bat,
# start_silent.vbs, KUR.bat, start_bridge_daemon.ps1) stay; this is the
# single typed entry. Do not kill the running bridge mutex from here.
param(
    [Parameter(Position = 0)]
    [string]$Cmd = "help"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

function Invoke-Bat([string]$name) {
    $path = Join-Path $Root $name
    if (-not (Test-Path -LiteralPath $path)) { throw "eksik: $name" }
    & cmd.exe /c "`"$path`""
    exit $LASTEXITCODE
}

switch ($Cmd.ToLowerInvariant()) {
    "install" { Invoke-Bat "KUR.bat" }
    "start" { Invoke-Bat "start.bat" }
    "console" { Invoke-Bat "start_console.bat" }
    "stop" { Invoke-Bat "stop.bat" }
    "restart" { Invoke-Bat "restart.bat" }
    "sync" {
        $ps = Join-Path $Root "scripts\auto_git_sync.ps1"
        Start-Process -FilePath "powershell.exe" -WindowStyle Minimized -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ps)
        Write-Host "MicoFX: auto git sync arka planda."
        exit 0
    }
    "bridge" {
        $ps = Join-Path $Root "scripts\start_bridge_daemon.ps1"
        # Same one-liner as KOPRU_AC.bat. Mutex in the daemon no-ops if live.
        Start-Process -FilePath "powershell.exe" -WindowStyle Minimized -ArgumentList @(
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ps)
        Write-Host "MicoFX: kopru daemon (zaten calisiyorsa no-op)."
        exit 0
    }
    default {
        Write-Host @"
MicoFX <cmd>

  install   KUR.bat
  start     sessiz (start.bat / start_silent.vbs)
  console   start_console.bat
  stop      stop.bat (port 8900)
  restart   restart.bat (app.py bunu dogrudan cagirir)
  sync      scripts/auto_git_sync.ps1
  bridge    scripts/start_bridge_daemon.ps1 (Task Scheduler yolu ayni)

Gelir dongusu bot icinde (Sistem > Gelir autopilot). GELIR_DONGUSU.bat yok.
"@
        exit 0
    }
}
