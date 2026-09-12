# Claude session leg: wakes THIS chat when claude/FOR_CURSOR.md changes.
#
# Cursor asked for this on purpose (cursor/FOR_CLAUDE.md:112): the bridge
# daemon's stdout is not wired to Cursor's notify path, so a per-session
# watcher is what actually wakes an open chat. That part is sound. What it was
# doing was not: every session armed its own inline `powershell -c "..."`, and
# by 11.09 08:26 three were alive at once, each polling the same file and
# emitting the same AGENT_LOOP_WAKE_claude_bridge token. Killing them is
# pointless - the next session arms another.
#
# So it lives here now, in the shape the other two legs already use
# (cursor/watch_bridges.ps1, antigravity/WATCH.ps1): one script, one mutex,
# reviewable. A second arm exits instead of doubling the wakes.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden `
#       -File C:\Users\Administrator\MicoFx\claude\session_watch.ps1
#
# The inline version also had its state write backwards:
#   Set-Content -NoNewline $state $hash   ->  looks right, binds right
#   Set-Content $hash $state              ->  what some revisions ran
# The second shape makes the 64-character hash the FILE NAME and the state
# path its contents. Five of those landed at the repo root on 10.09, one
# reached a commit, and one came back on 11.09 - so it was never fixed, only
# swept. Named parameters below, because positional binding is how that
# happens silently.

$ErrorActionPreference = 'Continue'
$root  = 'C:\Users\Administrator\MicoFx'
$CancelFlag = Join-Path $root '.bridge\BRIDGES_CANCELLED.json'
if (Test-Path -LiteralPath $CancelFlag) {
    Write-Host '[CLAUDE_SESSION] cancelled (.bridge/BRIDGES_CANCELLED.json) - exit.'
    exit 0
}
$inbox = Join-Path $root 'claude\FOR_CURSOR.md'
$state = Join-Path $root 'cursor\_cursor_session_claude_hash.txt'
$ping  = Join-Path $root '.bridge\last_ping_cursor.txt'

$MutexName = 'Global\MicoFX.ClaudeSessionWatch'
$mutex = New-Object System.Threading.Mutex($false, $MutexName)
if (-not $mutex.WaitOne(0)) {
    Write-Host "[CURSOR_SESSION] already armed ($MutexName) - exit."
    exit 0
}

function Get-H([string]$p) {
    if (Test-Path -LiteralPath $p) {
        return (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
    }
    return ''
}

try {
    $last = ''
    if (Test-Path -LiteralPath $state) {
        $last = (Get-Content -LiteralPath $state -Raw -ErrorAction SilentlyContinue)
        if ($last) { $last = $last.Trim() }
    }
    if (-not $last) {
        # First arm: adopt the current file rather than firing a wake for a
        # message that was already read.
        $last = Get-H $inbox
        if ($last) {
            Set-Content -LiteralPath $state -Value $last -NoNewline -Encoding UTF8
        }
    }
    Write-Host '[CURSOR_SESSION] Claude inbox armed (poll 5s)'

    while ($true) {
        Start-Sleep -Seconds 5
        $h = Get-H $inbox
        if ($h -and $h -ne $last) {
            $last = $h
            Set-Content -LiteralPath $state -Value $h -NoNewline -Encoding UTF8
            $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
            Set-Content -LiteralPath $ping -Value "$ts Cursor session wake on claude/FOR_CURSOR.md" -Encoding UTF8
            $head = (Get-Content -LiteralPath $inbox -TotalCount 1 -ErrorAction SilentlyContinue)
            $payload = @{
                prompt = "$ts Claude yazdi. Oku: claude/FOR_CURSOR.md. Cevap: cursor/FOR_CLAUDE.md. Baslik: $head"
            } | ConvertTo-Json -Compress
            Write-Output "AGENT_LOOP_WAKE_claude_bridge $payload"
        }
    }
} finally {
    try { $mutex.ReleaseMutex() | Out-Null } catch { }
    $mutex.Dispose()
}
