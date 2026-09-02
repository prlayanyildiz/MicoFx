@echo off
REM Gelir dongusu (6 saat) + otomatik git commit/push (degisiklik sonrasi).
cd /d "%~dp0"
start "MicoFX Auto Git Sync" /MIN powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\auto_git_sync.ps1"
start "MicoFX Gelir Dongusu" /MIN powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_income_loop.ps1"
