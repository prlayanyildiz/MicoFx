# MicoFX gelir gelistirme dongusu — 6 saatte bir audit + guvenli fix.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = "C:\MicoFX-venv\Scripts\python.exe"
$Script = Join-Path $Root "scripts\income_dev_loop.py"
$Log = Join-Path $Root "logs\income_loop.log"
$IntervalHours = 6

New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null

Write-Host "Gelir dongusu basladi — her $IntervalHours saatte bir."
Write-Host "Log: $Log"

while ($true) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$ts] income_dev_loop calisiyor..."
    & $Python $Script --apply-safe 2>&1 | Tee-Object -FilePath $Log -Append
    Write-Output "AGENT_LOOP_TICK_income_dev_loop {`"prompt`":`"Gelir dongusu tick: logs/income_loop_latest.md ve cursor/FOR_CLAUDE.md oku; onerilen aksiyonlari uygula; guvenli kod iyilestirmeleri yap.`"}"
    Start-Sleep -Seconds ($IntervalHours * 3600)
}
