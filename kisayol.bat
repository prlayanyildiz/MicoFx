@echo off
REM Sadece masaustu kisayollarini yeniden olustur (kurulum gerekmez).
cd /d "%~dp0"
echo MicoFX kisayollari olusturuluyor...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Create-Shortcuts.ps1"
echo.
pause
