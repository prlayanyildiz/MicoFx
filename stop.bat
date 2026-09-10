@echo off
setlocal
cd /d "%~dp0"

set "PORT=8900"
if defined MICO_PORT set "PORT=%MICO_PORT%"

echo MicoFX durduruluyor (port %PORT%)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING"') do (
  taskkill /PID %%a /T /F >nul 2>&1
  echo PID %%a sonlandirildi.
)

REM Kalan yetim worker sureclerini de temizle. Filtre TEK bir yerde durur:
REM gece_restart.cleanup_orphan_workers (venv imaji + olu ebeveyn sarti,
REM tests/test_orphan_sweep_stays_in_its_own_venv.py ile korunur). Buradaki
REM eski kopya yalnizca surec adina bakiyordu: makinedeki BASKA bir Python
REM uygulamasinin havuzunu da kapatirdi.
"C:\MicoFX-venv\Scripts\python.exe" -c "import gece_restart; gece_restart.cleanup_orphan_workers()" >nul 2>&1

echo Tamam.
timeout /t 2 >nul

