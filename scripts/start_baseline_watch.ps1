# Durable book monitor launcher (single-instance).
# Spawns pythonw via WMI so it is NOT a child of a Cursor/agent job object —
# those trees get hard-killed (exit=-1) when the parent shell is swept.
# pythonw.exe (not python.exe): no console, no taskbar flash, survives RDP.
# Soft reload: touch .bridge/BASELINE_WATCH_RELOAD (watch exits 0).
# venv pythonw.exe is a trampoline → expect parent+child pair (2 PIDs = 1 watch).
$ErrorActionPreference = "Continue"
$Root = "C:\Users\Administrator\MicoFx"
$Py = "C:\MicoFX-venv\Scripts\pythonw.exe"
$Script = Join-Path $Root "scripts\baseline_accumulate_watch.py"
$MutexName = "Global\MicoFX.BaselineAccumulateWatch"
$Log = Join-Path $Root "logs\baseline_accumulate.log"
$LastExit = Join-Path $Root ".bridge\BASELINE_WATCH_LAST_EXIT.txt"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root ".bridge") | Out-Null

function Get-BaselineWatchPids {
    # Match the watch script as a run target — not pytest collecting the same path.
    @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match '^python' -and
            $_.CommandLine -and
            $_.CommandLine -like '*baseline_accumulate_watch.py*' -and
            $_.CommandLine -notmatch '(?i)(-m\s+pytest|pytest\.exe|\bpytest\b)'
        } |
        Select-Object -ExpandProperty ProcessId)
}

function Write-LaunchLog([string]$msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $Log -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

function Wait-BaselineWatchGone {
    # Wait until the whole trampoline+child tree is gone. Waiting only on the
    # WMI PID used to return when the venv stub exited and then respawn
    # python.exe every few seconds (taskbar flicker).
    while ($true) {
        $alive = @(Get-BaselineWatchPids)
        if ($alive.Count -eq 0) { return }
        Wait-Process -Id ([int]$alive[0]) -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 400
    }
}

$mutex = New-Object System.Threading.Mutex($false, $MutexName)
if (-not $mutex.WaitOne(0)) {
    Write-Host "baseline_accumulate_watch already running ($MutexName) - exit."
    exit 0
}

# Mutex free but orphan python still ticking (launcher died / task overlap).
$existing = @(Get-BaselineWatchPids)
if ($existing.Count -gt 0) {
    Write-LaunchLog "orphan watch already live pids=$($existing -join ',') - exit without spawn"
    $mutex.ReleaseMutex() | Out-Null
    $mutex.Dispose()
    exit 0
}

try {
    $env:PYTHONIOENCODING = "utf-8"
    Set-Location $Root
    while ($true) {
        $alive = @(Get-BaselineWatchPids)
        if ($alive.Count -gt 0) {
            # Prefer trampoline roots (not the system-python child).
            $roots = @()
            foreach ($wid in $alive) {
                $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$wid" -ErrorAction SilentlyContinue
                if (-not $proc) { continue }
                $parent = [int]$proc.ParentProcessId
                if ($alive -contains $parent) { continue }
                $roots += [int]$wid
            }
            if ($roots.Count -eq 0) { $roots = @([int]$alive[0]) }
            if ($roots.Count -gt 1) {
                $keep = $roots | Sort-Object -Descending | Select-Object -First 1
                $kill = @($roots | Where-Object { $_ -ne $keep })
                Write-LaunchLog "duplicate watch trees keep=$keep kill=$($kill -join ',')"
                foreach ($k in $kill) {
                    Stop-Process -Id $k -Force -ErrorAction SilentlyContinue
                }
                Start-Sleep -Seconds 1
                $roots = @($keep)
            }
            Write-LaunchLog "adopt existing watch pid=$($roots[0]) (no new spawn)"
            Wait-BaselineWatchGone
            $reason = "unknown"
            if (Test-Path $LastExit) {
                $reason = ((Get-Content $LastExit -ErrorAction SilentlyContinue) -join " ").Trim()
            }
            Write-LaunchLog "launcher child exited reason=$reason; retry in 15s"
            Start-Sleep -Seconds 15
            continue
        }

        Write-LaunchLog "launcher start baseline_accumulate_watch (detached pythonw)"
        Remove-Item $LastExit -Force -ErrorAction SilentlyContinue
        $cmd = "`"$Py`" `"$Script`" --interval 900"
        $procId = 0
        try {
            $created = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
                CommandLine      = $cmd
                CurrentDirectory = $Root
            }
            if ([int]$created.ReturnValue -eq 0 -and $created.ProcessId) {
                $procId = [int]$created.ProcessId
            }
        } catch {
            Write-LaunchLog "WMI Create failed: $($_.Exception.Message)"
        }
        if ($procId -le 0) {
            $p = Start-Process -FilePath $Py -ArgumentList @($Script, "--interval", "900") `
                -WorkingDirectory $Root -PassThru -WindowStyle Hidden
            $procId = [int]$p.Id
            Write-LaunchLog "fallback Start-Process pid=$procId"
        } else {
            Write-LaunchLog "watch pid=$procId (WMI detached pythonw)"
        }
        Start-Sleep -Seconds 2
        Wait-BaselineWatchGone
        $reason = "unknown"
        if (Test-Path $LastExit) {
            $reason = ((Get-Content $LastExit -ErrorAction SilentlyContinue) -join " ").Trim()
        }
        Write-LaunchLog "launcher child exited reason=$reason; retry in 15s"
        Start-Sleep -Seconds 15
    }
} finally {
    $mutex.ReleaseMutex() | Out-Null
    $mutex.Dispose()
}
