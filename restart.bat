@echo off
REM MicoFX - /api/app/restart tarafindan cagirilir.
REM Eski surec kendini kapatiyor olsa da portun serbest kalmasi icin kisa bir
REM bekleme birakip ardindan start_silent.vbs ile yenisini baslatir.
cd /d "%~dp0"
timeout /t 2 >nul
start "" wscript.exe //B //Nologo "%~dp0start_silent.vbs"
exit
