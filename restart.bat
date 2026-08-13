@echo off
REM MicoFX - /api/app/restart tarafindan cagirilir.
REM Eski surec kendini kapatiyor; bu betik portun serbest kaldigini DOGRULAYIP
REM ardindan start_silent.vbs ile yenisini baslatir.
cd /d "%~dp0"

REM Portun GERCEKTEN serbest kalmasini bekle, sabit bir sure degil. app.py'deki
REM yorum zaten bunu vaat ediyordu ("restart.bat waits for this process to
REM release the port") ama burada yalnizca "timeout /t 2" vardi. Eski surec iki
REM saniyede portu birakmazsa yenisi port_busy ile cikar, yeniden deneme yoktur,
REM ve bot acik pozisyonlarla tamamen durur - tek izi logs/baslatilamadi.log
REM olur ve ona canli bakan kimse yoktur.
set "PORT=8900"
if defined MICO_PORT set "PORT=%MICO_PORT%"

set /a _tries=0
:waitport
netstat -ano | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 goto portfree
set /a _tries+=1
if %_tries% geq 30 goto portstuck
timeout /t 1 >nul
goto waitport

:portstuck
REM 30 saniye sonra hala tutuluyor: yine de baslat. Yeni surec port_busy ile
REM cikar ve sebebini yazar - bu, hic denememekten iyidir ve davranis en kotu
REM ihtimalle eski haline doner.
goto launch

:portfree
:launch
REM "restart" argumani: eski sekme zaten acik, start_silent.vbs yenisini acmasin.
start "" wscript.exe //B //Nologo "%~dp0start_silent.vbs" restart
exit
