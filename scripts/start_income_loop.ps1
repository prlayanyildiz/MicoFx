# MicoFX auto-pilot - 15 min: income loop + R&D (single instance)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Python = "C:\MicoFX-venv\Scripts\python.exe"
$Script = Join-Path $Root "scripts\auto_pilot.py"
$Log = Join-Path $Root "logs\auto_pilot.log"
$IntervalMinutes = 15
$Panel = "http://127.0.0.1:8900"
$MutexName = "Global\MicoFX.AutoPilot"

New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null

$mutex = New-Object System.Threading.Mutex($false, $MutexName)
if (-not $mutex.WaitOne(0)) {
    Write-Host "Auto-pilot zaten calisiyor ($MutexName) - cikiliyor."
    exit 0
}

function Test-PanelUp {
    try {
        $r = Invoke-WebRequest -Uri $Panel -UseBasicParsing -TimeoutSec 5
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Trim-Log([string]$Path, [int]$MaxLines) {
    if (-not (Test-Path $Path)) { return }
    try {
        $lines = Get-Content -Path $Path -ErrorAction SilentlyContinue
        if ($lines.Count -le $MaxLines) { return }
        $lines | Select-Object -Last $MaxLines | Set-Content -Path $Path -Encoding UTF8
    } catch {
        # non-fatal
    }
}

Write-Host "Auto-pilot started - every $IntervalMinutes minutes (income + R&D)."
Write-Host "Log: $Log"

try {
    while ($true) {
        $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        if (-not (Test-PanelUp)) {
            $line = "[$ts] panel kapali ($Panel) - auto_pilot atlandi"
            Write-Host $line
            Add-Content -Path $Log -Value $line -Encoding UTF8
        } else {
            Write-Host "[$ts] auto_pilot running..."
            $out = & $Python $Script 2>&1 | Out-String
            $tail = if ($out.Length -gt 2500) { $out.Substring($out.Length - 2500) } else { $out }
            Add-Content -Path $Log -Value "`n=== $ts ===`n$tail" -Encoding UTF8
            Trim-Log -Path $Log -MaxLines 400
        }
        Start-Sleep -Seconds ($IntervalMinutes * 60)
    }
} finally {
    try { $mutex.ReleaseMutex() | Out-Null } catch { }
    $mutex.Dispose()
}
