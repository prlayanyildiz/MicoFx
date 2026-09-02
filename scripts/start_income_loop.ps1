# MicoFX auto-pilot - 15 min: income loop + R&D
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = "C:\MicoFX-venv\Scripts\python.exe"
$Script = Join-Path $Root "scripts\auto_pilot.py"
$Log = Join-Path $Root "logs\auto_pilot.log"
$IntervalMinutes = 15

New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null

Write-Host "Auto-pilot started - every $IntervalMinutes minutes (income + R&D)."
Write-Host "Log: $Log"

while ($true) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] auto_pilot running..."
    & $Python $Script 2>&1 | Tee-Object -FilePath $Log -Append
    Start-Sleep -Seconds ($IntervalMinutes * 60)
}
