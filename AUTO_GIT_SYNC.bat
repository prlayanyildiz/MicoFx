@echo off
REM Her dosya degisikliginden ~60s sonra otomatik commit + push (post-commit hook).
cd /d "%~dp0"
start "MicoFX Auto Git Sync" /MIN powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\auto_git_sync.ps1"
