@echo off
REM Tek operator girisi. Gercek is scripts\micofx.ps1; restart/stop/start
REM hardcoded path'leri oldugu gibi durur.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\micofx.ps1" %*
