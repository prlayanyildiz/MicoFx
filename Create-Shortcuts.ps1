# MicoFX masaustu kisayollari. KUR.bat / kisayol.bat bunu cagirir.
# Calistir: powershell -ExecutionPolicy Bypass -File .\Create-Shortcuts.ps1

$ErrorActionPreference = "Continue"

$Dest = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not (Test-Path (Join-Path $Dest "start.bat"))) {
    Write-Host "HATA: start.bat bulunamadi: $Dest" -ForegroundColor Red
    exit 1
}

function Get-DesktopDirs {
    $dirs = New-Object System.Collections.Generic.List[string]

    foreach ($p in @(
        [Environment]::GetFolderPath("Desktop"),
        [Environment]::GetFolderPath("CommonDesktopDirectory"),
        (Join-Path $env:USERPROFILE "Desktop"),
        (Join-Path $env:USERPROFILE "OneDrive\Desktop"),
        (Join-Path $env:USERPROFILE "OneDrive - *\Desktop"),
        (Join-Path $env:PUBLIC "Desktop")
    )) {
        if ([string]::IsNullOrWhiteSpace($p)) { continue }
        if ($p -like "*`**") {
            Get-ChildItem -Path (Split-Path $p -Parent) -Directory -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -like "OneDrive*" } |
                ForEach-Object {
                    $d = Join-Path $_.FullName "Desktop"
                    if (-not $dirs.Contains($d)) { [void]$dirs.Add($d) }
                }
            continue
        }
        if (-not $dirs.Contains($p)) { [void]$dirs.Add($p) }
    }

    # Klasor yoksa olustur (bazi sunucularda Desktop henuz yok)
    $ready = @()
    foreach ($d in $dirs) {
        try {
            if (-not (Test-Path -LiteralPath $d)) {
                New-Item -ItemType Directory -Path $d -Force | Out-Null
            }
            if (Test-Path -LiteralPath $d) { $ready += $d }
        } catch {
            Write-Host "[kisayol] Klasor acilamadi: $d ($_)" -ForegroundColor Yellow
        }
    }
    return ($ready | Select-Object -Unique)
}

$items = @(
    @{ Name = "MicoFX Baslat";   Rel = "start.bat";         Style = 7; Desc = "MicoFX baslat (sessiz)" },
    @{ Name = "MicoFX Durdur";   Rel = "stop.bat";          Style = 1; Desc = "MicoFX durdur" },
    @{ Name = "MicoFX Terminal"; Rel = "start_console.bat"; Style = 1; Desc = "MicoFX konsol" }
)

$desktops = @(Get-DesktopDirs)
if ($desktops.Count -eq 0) {
    Write-Host "HATA: Hic masaustu klasoru bulunamadi/yazilamadi." -ForegroundColor Red
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$okCount = 0

foreach ($desk in $desktops) {
    Write-Host "[kisayol] Hedef: $desk" -ForegroundColor Cyan
    try {
        $old = Join-Path $desk "MicoFX.lnk"
        if (Test-Path -LiteralPath $old) { Remove-Item -LiteralPath $old -Force -ErrorAction SilentlyContinue }

        foreach ($it in $items) {
            $target = Join-Path $Dest $it.Rel
            if (-not (Test-Path -LiteralPath $target)) {
                Write-Host "  ATLANDI (yok): $($it.Rel)" -ForegroundColor Yellow
                continue
            }
            $lnkPath = Join-Path $desk "$($it.Name).lnk"
            $sc = $shell.CreateShortcut($lnkPath)
            $sc.TargetPath = $target
            $sc.WorkingDirectory = $Dest
            $sc.WindowStyle = [int]$it.Style
            $sc.Description = "$($it.Desc) ($Dest)"
            $sc.Save()
            if (Test-Path -LiteralPath $lnkPath) {
                Write-Host "  OK: $($it.Name).lnk" -ForegroundColor Green
                $okCount++
            } else {
                Write-Host "  FAIL: $lnkPath yazilamadi" -ForegroundColor Red
            }
        }

        $folderLnk = Join-Path $desk "MicoFX Klasor.lnk"
        $scFolder = $shell.CreateShortcut($folderLnk)
        $scFolder.TargetPath = $Dest
        $scFolder.WorkingDirectory = $Dest
        $scFolder.Description = "MicoFX proje klasoru"
        $scFolder.Save()
        if (Test-Path -LiteralPath $folderLnk) {
            Write-Host "  OK: MicoFX Klasor.lnk" -ForegroundColor Green
            $okCount++
        }
    } catch {
        Write-Host "  HATA: $_" -ForegroundColor Red
    }
}

Write-Host ""
if ($okCount -gt 0) {
    Write-Host "Toplam $okCount kisayol yazildi. Masaustune bak (F5 yenile)." -ForegroundColor Green
    exit 0
}
Write-Host "Hic kisayol yazilamadi." -ForegroundColor Red
exit 1
