# Cursor bridge watcher — Operator 2026-09-07
# Gemini leg ONLY. The Claude leg (claude/FOR_CURSOR.md) moved out 10.09:
# start_bridge_daemon.ps1 already watches that file with a FileSystemWatcher
# and emits the SAME AGENT_LOOP_WAKE_claude_bridge token, so every Claude
# note woke Cursor twice - once on an event, once on this 5s poll. The
# event-driven one is the better of the two, so this poll gave it up.
# Gemini writes antigravity/FOR_GEMINI.md -> AGENT_LOOP_WAKE_gemini_bridge
# Poll 5s. Do NOT watch cursor/FOR_GEMINI.md (that is Gemini's inbox).
$ErrorActionPreference = "Continue"
$root = "C:\Users\Administrator\MicoFx"
$wakeFile = Join-Path $root ".bridge\WAKE.txt"
$inboxGemini = Join-Path $root "antigravity\FOR_GEMINI.md"
$inboxGeminiAlt = Join-Path $root "antigravity\FOR_CURSOR.md"
$stateGemini = Join-Path $root "cursor\_bridge_watch_hash_gemini.txt"
$pingFile = Join-Path $root ".bridge\last_ping_cursor.txt"
$wakeTagGemini = "AGENT_LOOP_WAKE_gemini_bridge"
$MutexName = "Global\MicoFX.CursorBridgeWatch"

# Single-instance, exactly as antigravity/WATCH.ps1 got on 08.09 after an
# audit found "dual PIDs were double-waking Gemini". This watcher never got
# the same fix, so two of it double-woke Cursor - which is what happened when
# it was restarted on 10.09 while an older instance was still up.
$mutex = New-Object System.Threading.Mutex($false, $MutexName)
if (-not $mutex.WaitOne(0)) {
    Write-Host "[CURSOR_BRIDGES] already armed ($MutexName) - exit."
    exit 0
}

function Get-SharedPrompt {
  if (Test-Path -LiteralPath $wakeFile) {
    return ((Get-Content -LiteralPath $wakeFile -Raw) -replace "\s+", " ").Trim()
  }
  return "KOPRU. Gelen kutunu oku. Roluyle cevapla. MICO MOLA=dur."
}

function Get-FileHashSha([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { return "" }
  return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
}

# Prefer FOR_GEMINI.md; also watch FOR_CURSOR.md (Gemini sometimes writes there).
# Combined hash so either file change wakes Cursor (07.09 miss: only primary watched).
function Get-GeminiInboxHash {
  $a = Get-FileHashSha $inboxGemini
  $b = Get-FileHashSha $inboxGeminiAlt
  return "$a|$b"
}

function Resolve-NewestGeminiInbox {
  $candidates = @()
  if (Test-Path -LiteralPath $inboxGemini) { $candidates += (Get-Item -LiteralPath $inboxGemini) }
  if (Test-Path -LiteralPath $inboxGeminiAlt) { $candidates += (Get-Item -LiteralPath $inboxGeminiAlt) }
  if (-not $candidates.Count) { return $inboxGemini }
  return ($candidates | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
}

# Combined "a|b" format (07.09). Old single-hash state would false-wake on re-arm.
$lastGemini = ""
if (Test-Path -LiteralPath $stateGemini) {
  $lastGemini = (Get-Content -LiteralPath $stateGemini -Raw -ErrorAction SilentlyContinue).Trim()
}
$freshGemini = Get-GeminiInboxHash
if (-not $lastGemini -or ($lastGemini -notmatch '\|')) {
  $lastGemini = $freshGemini
}
if ($lastGemini) { Set-Content -NoNewline -LiteralPath $stateGemini -Value $lastGemini }

Write-Host "[CURSOR_BRIDGES] Armed (poll 5s):"
Write-Host "  antigravity/FOR_GEMINI.md         -> gemini_bridge wake"
Write-Host "  antigravity/FOR_CURSOR.md (also)  -> gemini_bridge wake"
Write-Host "  (Gemini wakes on cursor/FOR_GEMINI.md via antigravity/WATCH.ps1)"
# Banner must NOT contain literal AGENT_LOOP_WAKE_* strings — Cursor notify
# patterns match the whole terminal stream and would false-fire on arm.

try {
while ($true) {
  Start-Sleep -Seconds 5

  $hGemini = Get-GeminiInboxHash
  if ($hGemini -and $hGemini -ne $lastGemini) {
    $lastGemini = $hGemini
    Set-Content -NoNewline -LiteralPath $stateGemini -Value $hGemini
    $geminiPath = Resolve-NewestGeminiInbox
    $rel = $geminiPath.Replace($root + "\", "").Replace($root + "/", "")
    $prompt = (Get-SharedPrompt) + " Gelen: $rel (ayrica antigravity/FOR_GEMINI.md). Cevap: cursor/FOR_GEMINI.md. Oku ve yanitla."
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Set-Content -LiteralPath $pingFile -Value "$ts Cursor wake on $rel"
    Write-Output "AGENT_LOOP_TICK_gemini_inbox"
    Write-Output ($wakeTagGemini + " {`"prompt`":`"" + $prompt.Replace("`"","'") + "`"}")
  }
}
}
finally {
    $mutex.ReleaseMutex() | Out-Null
    $mutex.Dispose()
}
