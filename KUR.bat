@echo off
REM MicoFX - tek kurulum. Cift tikla, bitmesini bekle.
REM Butun is KUR.ps1'de; bu dosya sadece onu ExecutionPolicy engeline
REM takilmadan calistirir.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0KUR.ps1"
if errorlevel 1 (
  echo.
  echo Kurulum tamamlanamadi - yukaridaki mesaja bakin.
  pause
  exit /b 1
)
pause
