# Antigravity (Gemini) Bridge Watcher — Re-armed by Operator 2026-09-07
# Watches: cursor/FOR_GEMINI.md -> Alerts Gemini when Cursor writes.
# Single-instance mutex (08.09 audit: dual PIDs were double-waking Gemini).
$ErrorActionPreference = "Continue"
$root = "C:\Users\Administrator\MicoFx"
$CancelFlag = Join-Path $root ".bridge\BRIDGES_CANCELLED.json"
if (Test-Path -LiteralPath $CancelFlag) {
    Write-Host "[GEMINI_BRIDGE] cancelled (.bridge/BRIDGES_CANCELLED.json) - exit."
    exit 0
}
$inbox = Join-Path $root "cursor\FOR_GEMINI.md"
$state = Join-Path $root "antigravity\_watch_hash.txt"
$pingFile = Join-Path $root ".bridge\last_ping_gemini.txt"
$wakeFile = Join-Path $root ".bridge\WAKE.txt"
$MutexName = "Global\MicoFX.AntigravityWatch"

$mutex = New-Object System.Threading.Mutex($false, $MutexName)
if (-not $mutex.WaitOne(0)) {
    Write-Host "[GEMINI_BRIDGE] already armed ($MutexName) - exit."
    exit 0
}

function Get-FileHashSha([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return "" }
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
}

try {
    $last = ""
    if (Test-Path -LiteralPath $state) {
        $last = (Get-Content -LiteralPath $state -Raw -ErrorAction SilentlyContinue).Trim()
    }
    if (-not $last) {
        $last = Get-FileHashSha $inbox
        if ($last) { Set-Content -NoNewline -LiteralPath $state -Value $last }
    }

    Write-Host "[GEMINI_BRIDGE] Armed: watching cursor/FOR_GEMINI.md (poll 5s) -> Wakes Antigravity"

    while ($true) {
        Start-Sleep -Seconds 5
        $h = Get-FileHashSha $inbox
        if ($h -and $h -ne $last) {
            $last = $h
            Set-Content -NoNewline -LiteralPath $state -Value $h
            $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            Set-Content -LiteralPath $pingFile -Value "$ts Gemini wake on cursor/FOR_GEMINI.md"
            $content = Get-Content -LiteralPath $inbox -Raw -ErrorAction SilentlyContinue
            Write-Output "=== AGENT_LOOP_WAKE_GEMINI ==="
            Write-Output "Cursor guncelleme yapti: $ts"
            Write-Output "Dosya: cursor/FOR_GEMINI.md"
            Write-Output "Icerik ozeti:"
            if ($content) {
                $preview = ($content -split "`n" | Select-Object -First 15) -join "`n"
                Write-Output $preview
            }
            Write-Output "=============================="
        }
    }
}
finally {
    $mutex.ReleaseMutex() | Out-Null
    $mutex.Dispose()
}
