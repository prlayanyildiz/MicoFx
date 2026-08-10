@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ==========================================================
echo   GITHUB GECMIS TEMIZLIGI
echo ==========================================================
echo.
echo Ne yapacak:
echo   GitHub'daki eski commit'lerde duran hesap dosyalarini siler.
echo   (veritabani, islem logu, bakiye, sembol parametreleri)
echo.
echo   Yerel temizlik ZATEN yapildi. Bu dosya sadece onu
echo   GitHub'a gonderir ve sonra guvenlik yedegini kaldirir.
echo.
echo DIKKAT: Bu islem GERI ALINAMAZ. GitHub'daki gecmis degisir.
echo         Repo private, bu yuzden acil degil - istedigin zaman calistir.
echo.

REM --- On kontroller: yanlis durumda calismasin -------------------------
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if not "!BRANCH!"=="main" (
  echo [DUR] Su an "!BRANCH!" dalindasin, "main" degil. Islem yapilmadi.
  goto :son
)

REM Bu dosyanin kendisi takip edilmiyor; onu saymadan bak.
for /f "delims=" %%s in ('git status --porcelain ^| findstr /v /c:"TEMIZLE.bat"') do set DIRTY=1
if defined DIRTY (
  echo [DUR] Kaydedilmemis degisiklik var. Once onlari halletmek lazim.
  git status --short
  goto :son
)

git log --oneline main -- snapshot snapshot.py >nul 2>&1
for /f %%c in ('git log --oneline main -- snapshot snapshot.py ^| find /c /v ""') do set LEFT=%%c
if not "!LEFT!"=="0" (
  echo [DUR] Yerel gecmis beklendigi gibi temiz degil ^(!LEFT! commit^).
  echo       Claude'a haber ver, boyle gondermeyelim.
  goto :son
)

echo Kontroller tamam: main dalindasin, calisma agaci temiz,
echo yerel gecmiste hesap dosyasi kalmamis.
echo.
set /p ONAY="Devam edilsin mi? (e / h): "
if /i not "!ONAY!"=="e" (
  echo Iptal edildi. Hicbir sey degismedi.
  goto :son
)

echo.
echo [1/3] GitHub'a gonderiliyor...
REM --force-with-lease: uzakta beklenmeyen bir degisiklik varsa REDDEDER,
REM korlemesine ezmez. Guvenli olan bu.
git push --force-with-lease origin main
if errorlevel 1 (
  echo.
  echo [HATA] Gonderim basarisiz. Guvenlik yedegi DURUYOR, hicbir sey kaybolmadi.
  echo        Claude'a bu ekrani goster.
  goto :son
)

echo.
echo [2/3] GitHub dogrulaniyor...
git fetch origin -q
for /f %%c in ('git log --oneline origin/main -- snapshot snapshot.py ^| find /c /v ""') do set REMOTE=%%c
if not "!REMOTE!"=="0" (
  echo [HATA] GitHub'da hala !REMOTE! commit hesap dosyasi tasiyor.
  echo        Guvenlik yedegi DURUYOR. Claude'a haber ver.
  goto :son
)
echo        Temiz - GitHub'da hesap dosyasi kalmadi.

echo.
echo [3/3] Guvenlik yedegi kaldiriliyor ve disk temizleniyor...
git update-ref -d refs/original/refs/heads/main 2>nul
git tag -d yedek-temizlik-oncesi-2026-08-10 2>nul
git reflog expire --expire=now --all
git gc --prune=now --quiet

echo.
echo ==========================================================
echo   TAMAMLANDI
echo ==========================================================
echo.
echo GitHub'da artik hesabina dair hicbir iz yok:
echo   veritabani yok, log yok, bakiye yok, parametre yok.
echo.
echo Hesap yedegin duruyor - backup.py her aksam
echo C:\MicoFX_Yedek klasorune tam arsiv yaziyor.
echo.
echo Bu dosyayi (TEMIZLE.bat) artik silebilirsin.

:son
echo.
pause
endlocal
