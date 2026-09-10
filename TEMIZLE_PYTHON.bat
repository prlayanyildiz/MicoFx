@echo off
setlocal enabledelayedexpansion
title MicoFX - Python Surec Temizleyici
cd /d "%~dp0"

echo ======================================================================
echo                 MicoFX - Python Surec Temizleyici                    
echo ======================================================================
echo Bu arac, CPU ve RAM tuketen gereksiz veya yetim Python sureclerini
echo guvenle sonlandirir. MetaTrader 5 (terminal64) ASLA kapatilmaz!
echo ======================================================================
echo.
echo   [1] YALNIZCA YETIM/ZOMBI WORKER SURECLERINI TEMIZLE (Bot acik kalir)
echo       - Bot aciksa calismaya devam eder; calisan bir arama havuzu da
echo         dokunulmadan kalir (ebeveyni yasayan worker yetim degildir).
echo       - Yalnizca bu venv'in birakip gittigi multiprocessing worker'lari
echo         temizlenir. Makinedeki diger Python uygulamalari etkilenmez.
echo.
echo   [2] TUM PYTHON SURECLERINI SONLANDIR (Tam Temizlik - Yuzde 0 CPU)
echo       - MicoFX dahil tum python.exe ve pythonw.exe sureclerini kapatir.
echo       - Bilgisayar aninda rahatlar, CPU yukunu sifirlar.
echo.
echo   [0] Cikis
echo.
echo ======================================================================

if "%~1"=="1" goto clean_orphans
if "%~1"=="yetim" goto clean_orphans
if "%~1"=="2" goto kill_all
if "%~1"=="all" goto kill_all
if "%~1"=="tam" goto kill_all

choice /C 120 /T 10 /D 1 /M "Seciminiz [10 sn icinde secmezseniz otomatik 1 calisir]: "
if errorlevel 3 goto end
if errorlevel 2 goto kill_all
if errorlevel 1 goto clean_orphans
goto end

:clean_orphans
echo.
echo Yetim ve zombi Python worker surecleri araniyor ve temizleniyor...
REM Filtre TEK bir yerde durur: gece_restart.cleanup_orphan_workers. Iki sart
REM da tasiyor - imaj bu venv'e (ya da taban yorumlayicisina) ait olacak, ve
REM ebeveyn olmus olacak. Buradaki eski kopyada ikisi de yoktu: port 8900'un
REM sahibi olmayan HER python.exe'yi vuruyordu, bot kapaliyken ($portPid=0)
REM ise makinedeki tum Python sureclerini - baska projeleri, calisan bir
REM pytest'i, baseline watch'i. Varsayilan secim (10 sn sonra) bu dal.
"C:\MicoFX-venv\Scripts\python.exe" -c "import gece_restart as g; n = g.cleanup_orphan_workers(); print(('[BASARILI] Toplam ' + str(n) + ' adet yetim Python worker sureci temizlendi.') if n else '[BILGI] Kalan yetim veya asili Python worker sureci bulunamadi.')"
goto report_mt5

:kill_all
echo.
echo Tum Python ve Pythonw surecleri sonlandiriliyor...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$procs = Get-Process python, pythonw -ErrorAction SilentlyContinue;" ^
  "if ($procs) {" ^
  "  $procs | ForEach-Object {" ^
  "    Write-Host ('  [SONLANDIRILDI] PID: ' + $_.Id + ' (' + $_.ProcessName + ')') -ForegroundColor Yellow;" ^
  "    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue;" ^
  "  };" ^
  "  Write-Host '';" ^
  "  Write-Host '[BASARILI] Tum Python surecleri sonlandirildi. CPU ve RAM serbest birakildi.' -ForegroundColor Green;" ^
  "} else {" ^
  "  Write-Host '[BILGI] Calisan hicbir Python sureci bulunamadi.' -ForegroundColor Cyan;" ^
  "}"
goto report_mt5

:report_mt5
echo.
echo ----------------------------------------------------------------------
echo MetaTrader 5 Durumu (Guvenli):
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$mt5 = Get-Process terminal64 -ErrorAction SilentlyContinue;" ^
  "if ($mt5) {" ^
  "  $mt5 | ForEach-Object { Write-Host ('  [KORUNDU] MT5 Terminal PID: ' + $_.Id + ' - Sorunsuz Calisiyor') -ForegroundColor Green }" ^
  "} else { Write-Host '  [BILGI] Acik MT5 terminali bulunamadi.' -ForegroundColor Yellow }"
echo ----------------------------------------------------------------------
echo.
if not "%~2"=="--nopause" if not "%~1"=="silent" pause
goto end

:end
exit /b 0
