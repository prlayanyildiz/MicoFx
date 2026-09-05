# Durable book monitor launcher (single-instance).
# Spawns Python via WMI so it is NOT a child of a Cursor/agent job object —
# those trees get hard-killed (exit=-1) when the parent shell is swept.
# Soft reload: touch .bridge/BASELINE_WATCH_RELOAD (watch exits 0).
$ErrorActionPreference = "Continue"
$Root = "C:\Users\Administrator\MicoFx"
$Py = "C:\MicoFX-venv\Scripts\python.exe"
$Script = Join-Path $Root "scripts\baseline_accumulate_watch.py"
$MutexName = "Global\MicoFX.BaselineAccumulateWatch"
$Log = Join-Path $Root "logs\baseline_accumulate.log"
$LastExit = Join-Path $Root ".bridge\BASELINE_WATCH_LAST_EXIT.txt"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "logs") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Root ".bridge") | Out-Null

$mutex = New-Object System.Threading.Mutex($false, $MutexName)
if (-not $mutex.WaitOne(0)) {
    Write-Host "baseline_accumulate_watch already running ($MutexName) - exit."
    exit 0
}

function Write-LaunchLog([string]$msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content -Path $Log -Value $line -Encoding UTF8 -ErrorAction SilentlyContinue
}

try {
    $env:PYTHONIOENCODING = "utf-8"
    Set-Location $Root
    while ($true) {
        Write-LaunchLog "launcher start baseline_accumulate_watch (detached)"
        Remove-Item $LastExit -Force -ErrorAction SilentlyContinue
        $cmd = "`"$Py`" -u `"$Script`" --interval 900"
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
            $p = Start-Process -FilePath $Py -ArgumentList @("-u", $Script, "--interval", "900") `
                -WorkingDirectory $Root -PassThru -WindowStyle Hidden
            $procId = [int]$p.Id
            Write-LaunchLog "fallback Start-Process pid=$procId"
        } else {
            Write-LaunchLog "watch pid=$procId (WMI detached)"
        }
        Wait-Process -Id $procId -ErrorAction SilentlyContinue
        $reason = "unknown"
        if (Test-Path $LastExit) {
            $reason = ((Get-Content $LastExit -ErrorAction SilentlyContinue) -join " ").Trim()
        }
        Write-LaunchLog "launcher child exited reason=$reason; retry in 5s"
        Start-Sleep -Seconds 5
    }
} finally {
    $mutex.ReleaseMutex() | Out-Null
    $mutex.Dispose()
}
