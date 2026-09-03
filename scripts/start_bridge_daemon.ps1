# MicoFX bridge daemon — fully automatic both directions.
# - FileSystemWatcher (event) + 60s backup poll
# - Cursor session: AGENT_LOOP_WAKE_claude_bridge on stdout (notify)
# - Claude headless: spawn claude.exe -p when FOR_CLAUDE.md changes
# - Watchdog: if Claude task marked SIMDI and silent >12min, nudge spawn
# Survives chat close. Mutex single-instance.
$ErrorActionPreference = "Continue"
$Root = "C:\Users\Administrator\MicoFx"
$MutexName = "Global\MicoFX.BridgeDaemon"
$Log = Join-Path $Root "logs\bridge_daemon.log"
$WakeFile = Join-Path $Root ".bridge\WAKE.txt"
$Queue = Join-Path $Root ".bridge\wake_queue.jsonl"
$CursorInbox = Join-Path $Root "claude\FOR_CURSOR.md"
$ClaudeInbox = Join-Path $Root "cursor\FOR_CLAUDE.md"
$Board = Join-Path $Root "cursor\GOREV_TAHTASI.md"
$CursorState = Join-Path $Root "cursor\_bridge_watch_hash_claude.txt"
$ClaudeState = Join-Path $Root "claude\_watch_hash.txt"
$PingCursor = Join-Path $Root ".bridge\last_ping_cursor.txt"
$PingClaude = Join-Path $Root ".bridge\last_ping_claude.txt"
$ClaudeBusy = Join-Path $Root ".bridge\claude_spawn.lock"
$ClaudeLog = Join-Path $Root "logs\claude_spawn.log"
$ClaudeExe = "C:\Users\Administrator\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude-code\2.1.258\claude.exe"
$MaxTurns = 40
$WatchdogMinutes = 5
$HeartbeatMinutes = 5
$script:lastHeartbeat = Get-Date

New-Item -ItemType Directory -Force -Path (Join-Path $Root "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root ".bridge") | Out-Null

$mutex = New-Object System.Threading.Mutex($false, $MutexName)
if (-not $mutex.WaitOne(0)) {
    Write-Host "Bridge daemon already running ($MutexName) - exit."
    exit 0
}

function Write-Log([string]$msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $Log -Value $line -Encoding UTF8
}

function Get-SharedPrompt {
    if (Test-Path -LiteralPath $WakeFile) {
        return ((Get-Content -LiteralPath $WakeFile -Raw -ErrorAction SilentlyContinue) -replace "\s+", " ").Trim()
    }
    return "KOPRU. Gelen kutunu oku. Rolunle cevapla. MICO MOLA=dur."
}

function Get-HeadHash([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return "" }
    $head = (Get-Content -LiteralPath $path -TotalCount 1 -ErrorAction SilentlyContinue)
    if (-not $head) { return "" }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes([string]$head)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "")
    } finally { $sha.Dispose() }
}

function Get-FileHashSha([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return "" }
    return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
}

function Emit-Wake([string]$tag, [string]$prompt, [string]$pingPath, [string]$pingMsg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Set-Content -LiteralPath $pingPath -Value "$ts $pingMsg" -Encoding UTF8
    $safe = $prompt.Replace('"', "'")
    $line = "$tag {`"prompt`":`"$safe`"}"
    Write-Output $line
    Write-Log $line
    Add-Content -Path $Queue -Value ((@{ ts = $ts; tag = $tag; prompt = $prompt } | ConvertTo-Json -Compress)) -Encoding UTF8
}

function Test-ClaudeBusy {
    if (-not (Test-Path -LiteralPath $ClaudeBusy)) { return $false }
    try {
        $raw = Get-Content -LiteralPath $ClaudeBusy -Raw
        $procId = 0
        if ($raw -match "pid=(\d+)") { $procId = [int]$Matches[1] }
        if ($procId -gt 0) {
            $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($p) { return $true }
        }
        $age = (Get-Date) - (Get-Item -LiteralPath $ClaudeBusy).LastWriteTime
        if ($age.TotalMinutes -lt 3) { return $true }
        Remove-Item -LiteralPath $ClaudeBusy -Force -ErrorAction SilentlyContinue
        return $false
    } catch { return $false }
}

function Start-ClaudeTick([string]$reason) {
    if (-not (Test-Path -LiteralPath $ClaudeExe)) {
        Write-Log "Claude spawn SKIP: exe missing ($ClaudeExe)"
        return
    }
    if (Test-ClaudeBusy) {
        Write-Log "Claude spawn SKIP: busy ($reason)"
        return
    }
    # Pause only via flag file — WAKE.txt may mention "MICO MOLA=dur" as docs.
    if (Test-Path -LiteralPath (Join-Path $Root ".bridge\MOLA")) {
        Write-Log "Claude spawn SKIP: .bridge/MOLA present"
        return
    }
    $wake = Get-SharedPrompt
    $prompt = @"
MicoFx KOPRU INCOME tick ($reason). Aktif + agresif ol.
1) Oku: cursor/GOREV_TAHTASI.md (SIMDI satirlar) + cursor/FOR_CLAUDE.md ust blok + logs/income_loop_latest.md.
2) Her tick en az bir somut is: costed sweep, holdout vs canli fark, trail/adx/cost_rank kuyruk olcumu, entry-block analizi, veya GOLD_PERP add adayi. Bos 'bekliyorum' yazma.
3) Mutabakat + sayi: Claude -> Cursor basligi ile claude/FOR_CURSOR.md USTUNE yaz. Cursor apply eder.
4) Yasak: yeni aile, daily_loss_pct acma, SpotBrent acma, commit/push (Cursor yapar), MT5 sidecar initialize.
5) Python: C:\MicoFX-venv\Scripts\python.exe. Repo: C:\Users\Administrator\MicoFx.
$wake
"@
    $promptOne = ($prompt -replace "\s+", " ").Trim()
    Set-Content -LiteralPath $ClaudeBusy -Value "pid=0`nreason=$reason`nats=$(Get-Date -Format o)" -Encoding UTF8
    Write-Log "Claude spawn START ($reason)"
    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $ClaudeExe
        $psi.Arguments = "-p `"$($promptOne.Replace('"','\"'))`" --max-turns $MaxTurns"
        $psi.WorkingDirectory = $Root
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.CreateNoWindow = $true
        $proc = New-Object System.Diagnostics.Process
        $proc.StartInfo = $psi
        [void]$proc.Start()
        Set-Content -LiteralPath $ClaudeBusy -Value "pid=$($proc.Id)`nreason=$reason`nats=$(Get-Date -Format o)" -Encoding UTF8
        # Async drain so we don't block the watcher loop forever
        Start-Job -ScriptBlock {
            param($p, $log, $lock)
            try {
                $out = $p.StandardOutput.ReadToEnd()
                $err = $p.StandardError.ReadToEnd()
                $p.WaitForExit()
                $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
                Add-Content -Path $log -Value "`n=== $ts exit=$($p.ExitCode) ===`n$out`n$err" -Encoding UTF8
            } finally {
                Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue
            }
        } -ArgumentList $proc, $ClaudeLog, $ClaudeBusy | Out-Null
    } catch {
        Write-Log "Claude spawn FAIL: $_"
        Remove-Item -LiteralPath $ClaudeBusy -Force -ErrorAction SilentlyContinue
    }
}

function Test-ClaudeOverdue {
    if (-not (Test-Path -LiteralPath $Board)) { return $false }
    $board = Get-Content -LiteralPath $Board -Raw -ErrorAction SilentlyContinue
    if ($board -notmatch "CLAUDE" -or $board -notmatch "\*\*SIMDI\*\*|\*\*ŞİMDİ\*\*|ŞİMDİ|SIMDI") {
        # Turkish/ASCII variants
        if ($board -notmatch "SIMDI|\u015e\u0130MD\u0130") { return $false }
    }
    if (-not (Test-Path -LiteralPath $ClaudeInbox)) { return $false }
    if (-not (Test-Path -LiteralPath $CursorInbox)) { return $true }
    $tClaude = (Get-Item -LiteralPath $ClaudeInbox).LastWriteTime
    $tCursor = (Get-Item -LiteralPath $CursorInbox).LastWriteTime
    # Cursor wrote a task, Claude has not replied after
    if ($tClaude -gt $tCursor) {
        $age = (Get-Date) - $tClaude
        return ($age.TotalMinutes -ge $WatchdogMinutes)
    }
    return $false
}

function Load-State([string]$path, [scriptblock]$compute) {
    if (Test-Path -LiteralPath $path) {
        $v = (Get-Content -LiteralPath $path -Raw -ErrorAction SilentlyContinue)
        if ($v) { return $v.Trim() }
    }
    $h = & $compute
    if ($h) { Set-Content -NoNewline -LiteralPath $path -Value $h }
    return $h
}

function Handle-CursorMail {
    $h = Get-HeadHash $CursorInbox
    if ($h -and $h -ne $script:lastCursor) {
        $script:lastCursor = $h
        Set-Content -NoNewline -LiteralPath $CursorState -Value $h
        Emit-Wake "AGENT_LOOP_WAKE_claude_bridge" ((Get-SharedPrompt) + " Gelen: claude/FOR_CURSOR.md. Cevap: cursor/FOR_CLAUDE.md. GOREV: cursor/GOREV_TAHTASI.md.") $PingCursor "Cursor wake on claude/FOR_CURSOR.md"
    }
}

function Handle-ClaudeMail {
    $h2 = Get-FileHashSha $ClaudeInbox
    if ($h2 -and $h2 -ne $script:lastClaude) {
        $script:lastClaude = $h2
        Set-Content -NoNewline -LiteralPath $ClaudeState -Value $h2
        Emit-Wake "AGENT_LOOP_WAKE_claude_inbox" ((Get-SharedPrompt) + " Gelen: cursor/FOR_CLAUDE.md. Cevap: claude/FOR_CURSOR.md. Python C:\MicoFX-venv\Scripts\python.exe.") $PingClaude "Claude wake on cursor/FOR_CLAUDE.md"
        Start-ClaudeTick "FOR_CLAUDE_changed"
    }
}

$script:lastCursor = Load-State $CursorState { Get-HeadHash $CursorInbox }
$script:lastClaude = Load-State $ClaudeState { Get-FileHashSha $ClaudeInbox }

Get-EventSubscriber -ErrorAction SilentlyContinue | Where-Object {
    $_.SourceIdentifier -like "MicoBridge*"
} | ForEach-Object { Unregister-Event -SourceIdentifier $_.SourceIdentifier -Force -ErrorAction SilentlyContinue }
Get-Event -ErrorAction SilentlyContinue | Where-Object {
    $_.SourceIdentifier -like "MicoBridge*"
} | ForEach-Object { Remove-Event -EventIdentifier $_.EventIdentifier -ErrorAction SilentlyContinue }

$wCursor = New-Object System.IO.FileSystemWatcher
$wCursor.Path = (Join-Path $Root "claude")
$wCursor.Filter = "FOR_CURSOR.md"
$wCursor.NotifyFilter = [IO.NotifyFilters]::LastWrite -bor [IO.NotifyFilters]::Size -bor [IO.NotifyFilters]::FileName
$wCursor.EnableRaisingEvents = $true

$wClaude = New-Object System.IO.FileSystemWatcher
$wClaude.Path = (Join-Path $Root "cursor")
$wClaude.Filter = "FOR_CLAUDE.md"
$wClaude.NotifyFilter = [IO.NotifyFilters]::LastWrite -bor [IO.NotifyFilters]::Size -bor [IO.NotifyFilters]::FileName
$wClaude.EnableRaisingEvents = $true

Register-ObjectEvent -InputObject $wCursor -EventName Changed -SourceIdentifier MicoBridgeCursor | Out-Null
Register-ObjectEvent -InputObject $wClaude -EventName Changed -SourceIdentifier MicoBridgeClaude | Out-Null

Write-Log "Bridge daemon FULL-AUTO STARTED (FSW + claude.exe spawn + watchdog ${WatchdogMinutes}m + heartbeat ${HeartbeatMinutes}m)."
Write-Output 'AGENT_LOOP_WAKE_bridge_daemon {"prompt":"Kopru full-auto income: Claude spawn + Cursor notify + 5m heartbeat."}'

# Kick Claude if a SIMDI task is already hanging
if (Test-ClaudeOverdue) {
    Start-ClaudeTick "startup_overdue"
}
Start-ClaudeTick "startup_heartbeat"
$script:lastHeartbeat = Get-Date

try {
    while ($true) {
        $ev = Wait-Event -Timeout 60
        if ($null -eq $ev) {
            Handle-CursorMail
            Handle-ClaudeMail
            if (Test-ClaudeOverdue) {
                Start-ClaudeTick "watchdog_overdue"
            }
            $hbAge = (Get-Date) - $script:lastHeartbeat
            if ($hbAge.TotalMinutes -ge $HeartbeatMinutes) {
                Start-ClaudeTick "heartbeat"
                $script:lastHeartbeat = Get-Date
                Emit-Wake "AGENT_LOOP_WAKE_claude_bridge" ((Get-SharedPrompt) + " Heartbeat ${HeartbeatMinutes}m - tahta + FOR_CURSOR oku, SIMDI ilerle.") $PingCursor "Bridge heartbeat"
            }
            continue
        }
        $sid = $ev.SourceIdentifier
        Remove-Event -EventIdentifier $ev.EventIdentifier
        Start-Sleep -Milliseconds 250
        Get-Event -SourceIdentifier $sid -ErrorAction SilentlyContinue | ForEach-Object {
            Remove-Event -EventIdentifier $_.EventIdentifier -ErrorAction SilentlyContinue
        }
        if ($sid -eq "MicoBridgeCursor") {
            Handle-CursorMail
        } elseif ($sid -eq "MicoBridgeClaude") {
            Handle-ClaudeMail
        }
    }
} finally {
    $wCursor.EnableRaisingEvents = $false
    $wClaude.EnableRaisingEvents = $false
    Unregister-Event -SourceIdentifier MicoBridgeCursor -Force -ErrorAction SilentlyContinue
    Unregister-Event -SourceIdentifier MicoBridgeClaude -Force -ErrorAction SilentlyContinue
    $wCursor.Dispose()
    $wClaude.Dispose()
    try { $mutex.ReleaseMutex() | Out-Null } catch { }
    $mutex.Dispose()
    Write-Log "Bridge daemon STOPPED"
}
