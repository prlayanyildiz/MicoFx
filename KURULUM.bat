@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================
echo   MicoFX - Ilk Kurulum
echo ============================================
echo.

REM Sanal ortam bilerek proje klasorunun DISINDA, sabit bir yerde tutuluyor
REM (C:\MicoFX-venv). OneDrive gibi bir arac bu klasoru (MicoFx) baska bir
REM bilgisayara senkronlarsa bile venv oraya tasinmiyor - bir venv'in icinde
REM o an kuruldugu makinenin Python yoluna mutlak referans var, baska
REM makinede kullanilinca "No Python at ..." hatasi veriyordu (iki
REM bilgisayar OneDrive uzerinden ayni ".venv" klasorunu paylasinca da bunu
REM yasadik - hangisi son senkronlarsa digerini bozuyordu). Her makine burada
REM kendi venv'ini bir kez kurar, bir daha hicbir senkron ona dokunamaz.
set "VENV=C:\MicoFX-venv"

REM ------------------------------------------------------------- [1] Python
where python >nul 2>nul
if errorlevel 1 (
    echo [1/4] Python bulunamadi.
    where winget >nul 2>nul
    if errorlevel 1 (
        echo   winget da bulunamadi, Python'u elle kurmaniz gerekiyor.
        echo   Tarayicida indirme sayfasi aciliyor...
        start "" "https://www.python.org/downloads/"
        echo.
        echo   Kurulum sirasinda pencerenin ALT KISMINDAKI
        echo   "Add python.exe to PATH" kutucugunu MUTLAKA isaretleyin.
        echo   Kurulum bitince bu dosyayi ^(KURULUM.bat^) tekrar calistirin.
        echo.
        pause
        exit /b 1
    ) else (
        echo   winget ile Python 3.12 kuruluyor, bir kac dakika surebilir...
        winget install -e --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
        if errorlevel 1 (
            echo.
            echo   Otomatik kurulum basarisiz oldu. Tarayicida indirme sayfasi
            echo   aciliyor, elle kurup PATH'e ekleyin ^(kurulum ekraninda
            echo   "Add python.exe to PATH" kutusunu isaretleyin^).
            start "" "https://www.python.org/downloads/"
            pause
            exit /b 1
        )
        echo.
        echo   Python kuruldu. PATH'in etkin olmasi icin bu pencereyi kapatip
        echo   KURULUM.bat'i YENIDEN calistirin.
        echo.
        pause
        exit /b 0
    )
) else (
    echo [1/4] Python bulundu:
    REM cmd.exe'nin dogrudan cagirdigi "python" bazen Microsoft Store takma
    REM adini (App Execution Alias) cozemiyor ve "No Python at ..." hatasi
    REM veriyor - ayni ikili PowerShell uzerinden sorunsuz calisiyor, o yuzden
    REM her python cagrisi buradan sonra PowerShell'e sarilarak yapiliyor.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "& python --version; exit $LASTEXITCODE"
)

echo.
echo [2/4] Sanal ortam hazirlaniyor (%VENV%)...
if not exist "%VENV%\Scripts\python.exe" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "& python -m venv '%VENV%'; exit $LASTEXITCODE"
    if errorlevel 1 (
        echo   HATA: sanal ortam olusturulamadi.
        pause
        exit /b 1
    )
) else (
    echo   Zaten var, atlaniyor.
)

echo.
echo [3/4] Bagimliliklar kuruluyor (birkac dakika surebilir)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%VENV%\Scripts\python.exe' -m pip install --upgrade pip; exit $LASTEXITCODE" >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%VENV%\Scripts\python.exe' -m pip install -r requirements.txt; exit $LASTEXITCODE"
if errorlevel 1 (
    echo.
    echo   HATA: bagimliliklar kurulamadi, yukaridaki mesaja bakin.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    echo.
    echo   Not: proje klasorunde eski bir ".venv" bulundu - artik kullanilmiyor
    echo   ^(sanal ortam artik %VENV% altinda^). Istersen elle silebilirsin,
    echo   yer kaplamak disinda bir zarari yok.
)

echo.
echo [4/4] Kurulum tamamlandi.
echo.
echo Sirada yapmaniz gerekenler:
echo   1^) MetaTrader 5 terminalini kurun ve hesabiniza giris yapin.
echo   2^) MT5'te ust menu Araclar ^> Secenekler ^> Uzman Danismanlar sekmesinde
echo      "Algoritmik alim satima izin ver" kutusunu isaretleyin.
echo   3^) start.bat dosyasina cift tiklayarak MicoFX'i baslatin.
echo.
echo Ayrintili anlatim icin KURULUM.md dosyasina bakabilirsiniz.
echo.
pause
