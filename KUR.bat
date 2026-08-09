@echo off
REM MicoFX - tek tikla kurulum / guncelleme (Python, Node, Claude, paketler).
cd /d "%~dp0"
echo MicoFX kuruluyor... Birak, bitene kadar bekle.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0bootstrap.ps1"
echo.
if errorlevel 1 (
  echo BIR SEY TERS GITTİ - yukaridaki kirmizi satirlara bak.
  pause
  exit /b 1
)
echo Tamam. Kapatabilirsin. Sonra start.bat ile baslat.
pause
