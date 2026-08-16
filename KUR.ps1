# MicoFX - tek kurulum. Python + sanal ortam + paketler + masaustu kisayollari.
#
# Tek giris noktasi budur. KUR.bat sadece bu dosyayi ExecutionPolicy Bypass ile
# cagirir; baska kurulum scripti yok. Bastan calistirmak guvenli - her adim
# zaten yapilmissa atlanir, yani ayni dosya hem ilk kurulum hem guncelleme
# sonrasi tazeleme icin kullanilir.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

# Sanal ortam bilerek proje klasorunun DISINDA. Bir venv, kuruldugu makinenin
# python.exe yoluna mutlak referans tutar; OneDrive proje klasorunu baska bir
# bilgisayara senkronlarsa oradaki ".venv" bozuk cikar ("No Python at ...") ve
# iki makine ayni klasoru paylasinca hangisi son senkronlarsa digerini bozar.
# Burada her makine kendi venv'ini bir kez kurar, senkron ona hic dokunmaz.
$Venv = "C:\MicoFX-venv"
$VenvPy = Join-Path $Venv "Scripts\python.exe"

function Say([string]$msg, [string]$colour = "Gray") { Write-Host $msg -ForegroundColor $colour }

function Test-PythonRuns([string]$exe) {
    # Bir venv'in calisip calismadigini "dosya var mi" ile degil, gercekten
    # calistirarak anliyoruz. Ama PowerShell 5.1'de yerli bir programin
    # stderr'i yonlendirilince her satir NativeCommandError'a donusuyor ve
    # dosyanin basindaki $ErrorActionPreference="Stop" onu olumcul yapiyor -
    # yani bozuk venv dogru tespit edilir, script tespit ANINDA olurdu.
    # Tercihi bu cagri boyunca gevsetiyoruz.
    if (-not (Test-Path -LiteralPath $exe)) { return $false }
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $null = & $exe -c "import sys" 2>&1
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $prev
    }
}
function Step([int]$n, [string]$msg) { Write-Host ""; Say "[$n/4] $msg" "Cyan" }

Say "============================================" "Cyan"
Say "  MicoFX kurulum" "Cyan"
Say "============================================" "Cyan"
Say "  Klasor      : $Root"
Say "  Sanal ortam : $Venv"

# --------------------------------------------------------------- [1] Python
Step 1 "Python kontrol ediliyor..."
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Say "  Python bulunamadi." "Yellow"
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Say "  winget ile Python 3.12 kuruluyor (birkac dakika surebilir)..."
        winget install -e --id Python.Python.3.12 --silent `
            --accept-package-agreements --accept-source-agreements
        Say ""
        Say "  Python kuruldu. PATH'in etkin olmasi icin bu pencereyi KAPATIP" "Yellow"
        Say "  KUR.bat'i YENIDEN calistirin." "Yellow"
        exit 0
    }
    Say "  winget de yok - Python'u elle kurmaniz gerekiyor." "Yellow"
    Say "  Kurulum ekraninin ALT KISMINDAKI 'Add python.exe to PATH'" "Yellow"
    Say "  kutucugunu MUTLAKA isaretleyin, sonra KUR.bat'i tekrar calistirin." "Yellow"
    Start-Process "https://www.python.org/downloads/"
    exit 1
}
Say "  Bulundu: $python" "Green"
Say ("  " + (& python --version 2>&1))

# Surum kontrolu. Bulunan Python'a kendini dogrulatiyoruz - burada bir surum
# ayristirmak, "3.10" ile "3.9.13" gibi durumlarda kendi hatasini uretir.
# Neden gerekli: pydantic modelleri `X | None` kullaniyor ve pydantic v2 bunu
# sinif olusturulurken cozuyor, yani 3.9'da uygulama import aninda olur. Ama
# venv kurulur, pip install da basarili olur (numpy 1.26 3.9'u destekler) -
# kurulum "basarili" der, uygulama hic acilmaz. run.py ayni sayiyi kendi
# basina da uyguluyor; ikisinin ayrismasini bir test engelliyor.
& python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    Say "  Bu Python cok eski - MicoFX 3.10 veya ustunu gerektiriyor." "Yellow"
    Say "  PATH'teki python bu: $python" "Yellow"
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Say "  winget ile Python 3.12 kurmak icin:" "Yellow"
        Say "    winget install -e --id Python.Python.3.12" "Yellow"
    } else {
        Start-Process "https://www.python.org/downloads/"
    }
    Say "  Kurduktan sonra bu pencereyi KAPATIP KUR.bat'i yeniden calistirin." "Yellow"
    exit 1
}

# ---------------------------------------------------------- [2] Sanal ortam
Step 2 "Sanal ortam hazirlaniyor..."
# Varligina degil, CALISTIGINA bakiyoruz. Bir venv kuruldugu makinedeki
# python.exe'ye MUTLAK yol tutar, ve o yol degisince dosyalar yerinde durur
# ama hicbiri calismaz - pip "No Python at '...'" der ve kurulum bir sonraki
# adimda, bambaska bir hata gibi gorunerek olur. Bu tam olarak su yollarla
# olur: kullanici-kurulumu Python'dan tum-kullanicilar kurulumuna gecmek
# (AppData\Local\Programs -> C:\Program Files), Python'u kaldirip yeniden
# kurmak, ya da proje klasorunu baska bir makineye senkronlamak.
$venvOk = Test-PythonRuns $VenvPy
if ($venvOk) {
    Say "  Zaten var ve calisiyor, atlaniyor." "Green"
} else {
    if (Test-Path -LiteralPath $Venv) {
        Say "  Var ama bozuk (Python yolu degismis) - siliniyor." "Yellow"
        Remove-Item -LiteralPath $Venv -Recurse -Force -ErrorAction SilentlyContinue
    }
    & python -m venv $Venv
    if (-not (Test-PythonRuns $VenvPy)) { throw "Sanal ortam kurulamadi/calismiyor: $Venv" }
    Say "  Olusturuldu." "Green"
}

# ----------------------------------------------------------- [3] Paketler
Step 3 "Bagimliliklar kuruluyor (birkac dakika surebilir)..."
& $VenvPy -m pip install --upgrade pip --quiet
& $VenvPy -m pip install -r (Join-Path $Root "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Bagimliliklar kurulamadi - yukaridaki mesaja bakin." }
Say "  Tamam." "Green"

if (Test-Path -LiteralPath (Join-Path $Root ".venv\Scripts\python.exe")) {
    Say "  Not: proje icinde eski bir .venv duruyor, artik kullanilmiyor." "Yellow"
    Say "  Silebilirsiniz; yer kaplamak disinda zarari yok." "Yellow"
}

# --------------------------------------------------------- [4] Kisayollar
Step 4 "Masaustu kisayollari olusturuluyor..."

# TEK masaustune yazilir. Onceki surum "hangisi gercek masaustuyse o olsun"
# diye butun adaylara yaziyordu, ama bunlar alternatif adresler degil: Explorer
# ortak masaustunu (C:\Users\Public\Desktop) her kullanicinin kendi masaustunun
# UZERINE bindirir, yani ikisine birden yazmak tek bir masaustunde her ikonu
# IKI KEZ gosterir - bildirilen "cift kisayol" tam olarak buydu. Ustelik
# Public'e yazmak yonetici hakki ister ve oradaki kopya, kullanici masaustunden
# silindiginde geride kalir.
#
# GetFolderPath("Desktop") zaten OneDrive/klasor yonlendirmesini bilir ve
# kullanicinin GERCEKTEN gordugu klasoru dondurur; digerleri yalnizca o
# okunamazsa devreye giren yedeklerdir.
$Desktop = $null
foreach ($p in @(
    [Environment]::GetFolderPath("Desktop"),
    (Join-Path $env:USERPROFILE "OneDrive\Desktop"),
    (Join-Path $env:USERPROFILE "Desktop")
)) {
    if (-not [string]::IsNullOrWhiteSpace($p) -and (Test-Path -LiteralPath $p)) {
        # GetFullPath, Get-Item'in aksine diske hic bakmaz. Public masaustu
        # gibi GIZLI sistem klasorlerinde Get-Item -Force olmadan "bulunamadi"
        # diyor ve $ErrorActionPreference=Stop yuzunden kurulumu dusuruyordu.
        $Desktop = [IO.Path]::GetFullPath($p)
        break
    }
}

# Eski kurulumlarin diger klasorlere birakmis oldugu kopyalar temizlenir -
# yoksa bu duzeltme yalnizca YENI makinelerde ise yarar, cift ikonu zaten
# olusmus olan makinede kisayollar oldugu gibi durmaya devam ederdi.
function Remove-StaleShortcuts([string]$folder, [string]$keep) {
    if ([string]::IsNullOrWhiteSpace($folder) -or -not (Test-Path -LiteralPath $folder)) { return 0 }
    $full = [IO.Path]::GetFullPath($folder)
    # Yazdigimiz masaustunun kendisine dokunma. Karsilastirma buyuk/kucuk harf
    # duyarsiz: ayni klasor "OneDrive" ve "Onedrive" olarak gelebiliyor ve
    # onceki surumun kullandigi List.Contains bunu ayni saymiyordu.
    if ($keep -and $full.TrimEnd('\') -ieq $keep.TrimEnd('\')) { return 0 }
    $removed = 0
    $probe = New-Object -ComObject WScript.Shell
    foreach ($name in @("MicoFX Baslat", "MicoFX Durdur", "MicoFX Terminal", "MicoFX Klasor")) {
        $lnk = Join-Path $full "$name.lnk"
        if (-not (Test-Path -LiteralPath $lnk)) { continue }
        # Yalnizca gercekten bir MicoFX agacini gosteren kisayol silinir; ayni
        # isimde baska bir sey varsa elimiz surmez.
        $target = ""
        try { $target = $probe.CreateShortcut($lnk).TargetPath } catch { continue }
        if ($target -notmatch '(?i)micofx') { continue }
        try {
            Remove-Item -LiteralPath $lnk -Force -ErrorAction Stop
            $removed++
        } catch {
            # Public masaustu yonetici hakki ister; elde degil, sessizce gec.
            Say "  Silinemedi (yonetici gerekebilir): $lnk" "Yellow"
        }
    }
    return $removed
}

$items = @(
    @{ Name = "MicoFX Baslat";   Rel = "start.bat";         Style = 7; Desc = "MicoFX baslat (sessiz)" },
    @{ Name = "MicoFX Durdur";   Rel = "stop.bat";          Style = 1; Desc = "MicoFX durdur" },
    @{ Name = "MicoFX Terminal"; Rel = "start_console.bat"; Style = 1; Desc = "MicoFX konsol" }
)

$shell = New-Object -ComObject WScript.Shell
$written = 0
if ($Desktop) {
    foreach ($it in $items) {
        $target = Join-Path $Root $it.Rel
        if (-not (Test-Path -LiteralPath $target)) { continue }
        try {
            $lnk = $shell.CreateShortcut((Join-Path $Desktop "$($it.Name).lnk"))
            $lnk.TargetPath = $target
            $lnk.WorkingDirectory = $Root
            $lnk.WindowStyle = [int]$it.Style
            $lnk.Description = "$($it.Desc) ($Root)"
            $lnk.Save()
            $written++
        } catch {
            Say "  Yazilamadi: $Desktop\$($it.Name).lnk" "Yellow"
        }
    }
    try {
        $lnk = $shell.CreateShortcut((Join-Path $Desktop "MicoFX Klasor.lnk"))
        $lnk.TargetPath = $Root
        $lnk.WorkingDirectory = $Root
        $lnk.Description = "MicoFX proje klasoru"
        $lnk.Save()
        $written++
    } catch { }
}
if ($written -gt 0) { Say "  $written kisayol yazildi -> $Desktop" "Green" }
else { Say "  Kisayol yazilamadi - start.bat'i klasorden calistirabilirsiniz." "Yellow" }

# Yazdigimiz masaustu disindaki her yerdeki eski kopyalar temizlenir.
$stale = New-Object System.Collections.Generic.List[string]
foreach ($p in @(
    [Environment]::GetFolderPath("CommonDesktopDirectory"),
    (Join-Path $env:USERPROFILE "Desktop"),
    (Join-Path $env:USERPROFILE "OneDrive\Desktop")
)) { if (-not [string]::IsNullOrWhiteSpace($p)) { [void]$stale.Add($p) } }
Get-ChildItem -Path $env:USERPROFILE -Directory -Filter "OneDrive*" -ErrorAction SilentlyContinue |
    ForEach-Object { [void]$stale.Add((Join-Path $_.FullName "Desktop")) }

$cleaned = 0
foreach ($d in $stale) { $cleaned += Remove-StaleShortcuts $d $Desktop }
if ($cleaned -gt 0) { Say "  $cleaned eski/cift kisayol temizlendi." "Green" }

# --------------------------------------------------- [5] Gece yedegi gorevi
Step 5 "Aksam yedegi gorevi kuruluyor..."
# README yedegi calisan bir sey gibi anlatiyor ("backup.py her aksam Windows
# Gorev Zamanlayici ile calisir"), panel `backup_enabled` ile ana anahtarini
# gosteriyor, models.py "The Windows task still fires" diyor - ve hicbir sey
# o gorevi kurmuyordu. docs/KURULUM.md, sifirdan kurulum klavuzu, yedekten hic
# soz etmiyor. Yani kilavuzu bastan sona uygulayan bir makinede yedek YOKTU ve
# her belge oldugunu soyluyordu.
#
# Bedeli en agir yerde: data/micofx.db Git'e girmez. Her sembol ayari, her
# optimizasyon sonucu ve denetleyicinin ogrendigi her sey yalnizca orada
# durur - README'nin kendi ifadesiyle "GitHub kodu tutar, bunlarin hicbirini
# tutmaz".
#
# Interactive olarak kurulur (README bunu boyle tarif ediyor): yonetici hakki
# istemez, kilit ekraninda calisir, oturum tamamen kapaliysa o gece atlar.
$TaskName = "MicoFX Aksam Yedegi"
$existing = schtasks /query /tn "$TaskName" 2>$null
if ($LASTEXITCODE -eq 0) {
    Say "  Zaten var, atlaniyor." "Green"
} else {
    # Ayni yorumlayici, ayni gerekce: konsolsuz olan, ki gece bir pencere
    # acilmasin. Tirnaklar schtasks'in kendi ayristiricisi icin.
    $backupExe = Join-Path $Venv "Scripts\pythonw.exe"
    if (-not (Test-Path -LiteralPath $backupExe)) { $backupExe = $VenvPy }
    $action = '"' + $backupExe + '" "' + (Join-Path $Root "backup.py") + '"'
    schtasks /create /tn "$TaskName" /tr $action /sc daily /st 22:00 /f 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Say "  Kuruldu - her aksam 22:00." "Green"
        Say "  Hedef klasor ve ana anahtar panelden (Sistem sekmesi) degistirilir."
    } else {
        # Kurulumu dusurmez: yedek olmadan da uygulama calisir, ama bunu
        # sessizce gecmek README'nin verdigi sozu tekrar bosa cikarir.
        Say "  Gorev kurulamadi - yedek OTOMATIK ALINMAYACAK." "Yellow"
        Say "  Gorev Zamanlayici'da elle olusturun:" "Yellow"
        Say "    $action" "Yellow"
    }
}

# ------------------------------------------------------------------- bitti
Write-Host ""
Say "============================================" "Green"
Say "  Kurulum tamam." "Green"
Say "============================================" "Green"
Write-Host ""
Say "Sirada:"
Say "  1) MetaTrader 5'i kurup hesabiniza giris yapin."
Say "  2) MT5 > Araclar > Secenekler > Uzman Danismanlar sekmesinde"
Say "     'Algoritmik alim satima izin ver' kutusunu isaretleyin."
Say "  3) Masaustundeki 'MicoFX Baslat' kisayoluna cift tiklayin."
Write-Host ""
Say "Panel: http://127.0.0.1:8900" "Cyan"
Say "Acilista sistem IZLEME modundadir - emir gonderilmesi icin panelden"
Say "'Bot Baslat' demeniz gerekir."
Write-Host ""
