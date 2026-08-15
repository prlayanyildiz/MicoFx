# Injects the Claude brief when this session starts so "devam" is enough.
$ErrorActionPreference = "SilentlyContinue"
$root = Get-Location
$brief = Join-Path $root "claude\FOR_CURSOR.md"
$reply = Join-Path $root "cursor\FOR_CLAUDE.md"

function Get-Stamp($p) {
    if (-not (Test-Path $p)) { return $null }
    $f = Get-Item $p
    return $f.LastWriteTimeUtc
}

$ctx = "Bridge: read claude/FOR_CURSOR.md now if it exists. That file is the task even if the user only said devam. Write the full answer to cursor/FOR_CLAUDE.md (overwrite). Tables and numbers, no recommendations. Do not write the bot, DB, or claude/. Do not cancel a running optimiser. Re-arm cursor/watch_claude.ps1 before you finish."

$tb = Get-Stamp $brief
$tr = Get-Stamp $reply
if ($tb -and (-not $tr -or $tb -gt $tr)) {
    $ctx = "claude/FOR_CURSOR.md is NEWER than cursor/FOR_CLAUDE.md. Execute that brief immediately. " + $ctx
}

$payload = @{ additional_context = $ctx } | ConvertTo-Json -Compress
[Console]::Out.WriteLine($payload)
exit 0
