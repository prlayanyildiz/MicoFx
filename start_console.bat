@echo off
setlocal
cd /d "%~dp0"

REM KURULUM.bat ile ayni yer: proje klasorunun disinda, sabit, senkron
REM araclarinin (OneDrive vs.) hicbir zaman dokunamayacagi bir konum.
set "VENV=C:\MicoFX-venv"

if not exist "%VENV%\Scripts\python.exe" goto :system_python
set "PY=%VENV%\Scripts\python.exe"
goto :run

:system_python
set "PY=python"

:run
echo Starting MicoFX Terminal (konsol modu)...
echo Bu pencereyi kapatirsaniz uygulama durur.
echo.
REM cmd.exe'nin dogrudan cagirdigi venv python'i bazen Microsoft Store takma
REM adini cozemiyor (KURULUM.bat'te de gorulen "No Python at ..." hatasi) -
REM PowerShell uzerinden cagirmak bunu guvenilir sekilde asiyor.
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%PY%' run.py; exit $LASTEXITCODE"
if errorlevel 1 pause
endlocal
