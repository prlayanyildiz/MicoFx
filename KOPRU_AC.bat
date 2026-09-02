@echo off
REM Event-triggered persistent bridge (survives chat close).
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File "%~dp0scripts\start_bridge_daemon.ps1"
