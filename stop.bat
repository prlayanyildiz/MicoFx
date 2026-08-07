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
echo Tamam.
timeout /t 2 >nul
