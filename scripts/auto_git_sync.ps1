# Polls git status; after two consecutive dirty checks (quiet ~2 min), commit + push.
# post-commit hook (scripts/git-hooks/post-commit) performs origin push.
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PollSec = 45
$Log = Join-Path $Root "logs\auto_git_sync.log"

New-Item -ItemType Directory -Force -Path (Split-Path $Log) | Out-Null

function Write-Log([string]$Msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Msg"
    Add-Content -Path $Log -Value $line -Encoding UTF8
    Write-Host $line
}

function Install-PostCommitHook {
    $src = Join-Path $Root "scripts\git-hooks\post-commit"
    $dst = Join-Path $Root ".git\hooks\post-commit"
    if (-not (Test-Path $src)) { return }
    New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
    Copy-Item -LiteralPath $src -Destination $dst -Force
    Write-Log "post-commit hook installed"
}

function Sync-Repo {
    Set-Location $Root
    if (-not (git status --porcelain 2>$null)) { return }
    git add -A
    if (-not (git diff --cached --name-only 2>$null)) { return }
    $stat = (git diff --cached --stat | Out-String).Trim()
    $subject = "Auto-sync $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    $body = "Automated commit from auto_git_sync.`n`n$stat"
    git commit -m $subject -m $body
    if ($LASTEXITCODE -ne 0) {
        Write-Log "commit failed exit=$LASTEXITCODE"
        return
    }
    $sha = git rev-parse --short HEAD
    Write-Log "committed $sha"
}

Install-PostCommitHook
Write-Log "auto_git_sync started (poll ${PollSec}s, double-check debounce)"

$pending = $false
while ($true) {
    Start-Sleep -Seconds $PollSec
    Set-Location $Root
    $dirty = [bool](git status --porcelain 2>$null)
    if (-not $dirty) {
        $pending = $false
        continue
    }
    if (-not $pending) {
        $pending = $true
        Write-Log "dirty tree — waiting for quiet period"
        continue
    }
    Sync-Repo
    $pending = $false
}
