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

function Invoke-Native([scriptblock]$block) {
    # PowerShell 5.1'de yerli bir programin stderr'i (yonlendirilse de,
    # yonlendirilmese de) NativeCommandError'a donusur ve dosyanin basindaki
    # $ErrorActionPreference="Stop" onu olumcul yapar. schtasks gorevi
    # bulamayinca stderr'e yazar - yani "gorev henuz yok" gibi TAMAMEN normal
    # bir durum kurulumu oldururdu. Tercihi cagri boyunca gevsetip cikis
    # kodunu geri veriyoruz; karar cagirana ait.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $block 2>&1 | Out-Null; return $LASTEXITCODE }
    catch { return 1 }
    finally { $ErrorActionPreference = $prev }
}

function Test-PythonRuns([string]$exe) {
    # Bir venv'in calisip calismadigini "dosya var mi" ile degil, gercekten
    # calistirarak anliyoruz. Ama PowerShell 5.1'de yerli bir programin
    # stderr'i yonlendirilince her satir NativeCommandError'a donusuyor ve
    # dosyanin basindaki $ErrorActionPreference="Stop" onu olumcul yapiyor -
    # yani bozuk venv dogru tespit edilir, script tespit ANINDA olurdu.
    # Tercihi bu cagri boyunca gevsetiyoruz.
    if (-not (Test-Path -LiteralPath $exe)) { return $false }
    return ((Invoke-Native { & $exe -c "import sys" }) -eq 0)
}
function Step([int]$n, [string]$msg) { Write-Host ""; Say "[$n/8] $msg" "Cyan" }

# Only used to tell the operator how to re-add a missing remote (ZIP installs
# arrive without one). Kept next to the step counter so the two stay in view.
$RepoUrl = "https://github.com/prlayanyildiz/MicoFx.git"

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
$pyOldRc = Invoke-Native { & python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" }
if ($pyOldRc -ne 0) {
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
$queryRc = Invoke-Native { schtasks /query /tn "$TaskName" }
if ($queryRc -eq 0) {
    Say "  Zaten var, atlaniyor." "Green"
} else {
    # Ayni yorumlayici, ayni gerekce: konsolsuz olan, ki gece bir pencere
    # acilmasin. Tirnaklar schtasks'in kendi ayristiricisi icin.
    $backupExe = Join-Path $Venv "Scripts\pythonw.exe"
    if (-not (Test-Path -LiteralPath $backupExe)) { $backupExe = $VenvPy }
    $action = '"' + $backupExe + '" "' + (Join-Path $Root "backup.py") + '"'
    $createRc = Invoke-Native { schtasks /create /tn "$TaskName" /tr $action /sc daily /st 22:00 /f }
    if ($createRc -eq 0) {
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

# ------------------------------------------------------------------ [6] Git
Step 6 "Git kimligi ve GitHub erisimi..."
# Without a name and an email git refuses to commit at all, and the failure
# arrives later - mid-session, after work is already done - rather than here
# where it is one line to fix. Only filled in when missing: an operator who
# already configured their own identity keeps it.
if (Get-Command git -ErrorAction SilentlyContinue) {
    $haveName  = (& git -C $Root config user.name)  2>$null
    $haveMail  = (& git -C $Root config user.email) 2>$null
    if (-not $haveName) { & git -C $Root config user.name  "prlayanyildiz" | Out-Null }
    if (-not $haveMail) { & git -C $Root config user.email "prlayanyildiz@gmail.com" | Out-Null }
    Say ("  Kimlik: " + (& git -C $Root config user.name) + " <" + (& git -C $Root config user.email) + ">") "Green"

    $remote = (& git -C $Root remote get-url origin) 2>$null
    if ($remote) {
        Say "  Uzak depo: $remote" "Green"
        # Push credentials are NOT set up here on purpose. Git Credential
        # Manager ships with Git for Windows and asks on the first push, in
        # the operator's own browser - which is the one place a token should
        # ever be typed. Writing one into a file from an installer would put
        # a live credential on disk in plain text.
        Say "  Ilk 'git push' calistiginda GitHub girisi tarayicida acilir." "Yellow"
        Say "  Tarayici olmayan sunucuda: 'winget install GitHub.cli' sonra" "Yellow"
        Say "  'gh auth login' -> HTTPS -> cihaz kodu ile giris yapin." "Yellow"
    } else {
        Say "  Uzak depo yok (ZIP ile kurulmus olabilir) - push yapilamaz." "Yellow"
        Say "  Eklemek icin: git remote add origin $RepoUrl" "Yellow"
    }
} else {
    Say "  Git yok - surum gecmisi ve push kullanilamaz." "Yellow"
}

# --------------------------------------------------- [7] MQL5 takvim koprusu
Step 7 "MT5 takvim koprusu kuruluyor..."
# MT5'in ekonomik takvimi yalniz MQL5 dilinden okunabiliyor; Python paketinde
# karsiligi yok. Betik terminalin kendi veri klasorunde derli durmali, yoksa
# yeni bir makinede takvim olcumu sessizce calismaz. Derleme komut satirindan
# olur; calistirmak grafik ister ve o adim operatorde kalir.
$MqlSrc = Join-Path $Root "mql5"
if (-not (Test-Path $MqlSrc)) {
    Say "  mql5 klasoru yok - atlaniyor." "Yellow"
} else {
    $editor = Get-ChildItem "C:\Program Files\*MetaTrader 5\MetaEditor64.exe" -ErrorAction SilentlyContinue |
              Select-Object -First 1 -ExpandProperty FullName
    $termRoot = Join-Path $env:APPDATA "MetaQuotes\Terminal"
    $dataDirs = @()
    if (Test-Path $termRoot) {
        $dataDirs = Get-ChildItem $termRoot -Directory -ErrorAction SilentlyContinue |
                    Where-Object { Test-Path (Join-Path $_.FullName "MQL5\Scripts") }
    }
    if (-not $editor) {
        Say "  MetaEditor64.exe bulunamadi - takvim koprusu kurulmadi." "Yellow"
    } elseif ($dataDirs.Count -eq 0) {
        Say "  MT5 veri klasoru bulunamadi - takvim koprusu kurulmadi." "Yellow"
    } else {
        foreach ($d in $dataDirs) {
            $dest = Join-Path $d.FullName "MQL5\Scripts"
            foreach ($f in Get-ChildItem (Join-Path $MqlSrc "*.mq5") -ErrorAction SilentlyContinue) {
                Copy-Item $f.FullName $dest -Force
                $target = Join-Path $dest $f.Name
                # /log writes next to the source; the exit code alone does not
                # distinguish "compiled with warnings" from "did not compile".
                Invoke-Native { & $editor "/compile:$target" "/log" } | Out-Null
                $ex5 = [IO.Path]::ChangeExtension($target, ".ex5")
                if (Test-Path $ex5) { Say ("  derlendi: " + $f.Name) "Green" }
                else { Say ("  DERLENMEDI: " + $f.Name) "Yellow" }
            }
        }
        Say "  Calistirmak icin MT5 > Gezgin > Komut Dosyalari > MicoTakvimDisaAktar (cift tik)." "Gray"
        Say "  Araclar > Secenekler > Sunucu > 'Haberleri etkinlestir' acik olmali." "Gray"
    }
}

# ---------------------------------------------------------- [8] Dogrulama
Step 8 "Kurulum kendini dogruluyor (test suite)..."
# A green suite here is the difference between "the files copied" and "this
# machine can actually run it". Cheap - about a minute - and it has already
# caught a broken venv that every earlier step reported as fine.
$testRc = Invoke-Native { & $VenvPy -m pytest -q --basetemp (Join-Path $Root ".pytest_tmp") }
if ($testRc -eq 0) {
    Say "  Testler gecti." "Green"
} else {
    # Not fatal: the app may still run, and stopping here would leave a
    # half-installed machine with no shortcuts. But it must be loud.
    Say "  TESTLER GECMEDI - kurulum tamamlandi ama bu makinede bir sorun var." "Red"
    Say "  Elle calistirip ciktiya bakin:" "Yellow"
    Say ("    " + $VenvPy + " -m pytest -q") "Yellow"
}
$lintRc = Invoke-Native { & $VenvPy -m ruff check (Join-Path $Root "micofx") (Join-Path $Root "tests") }
if ($lintRc -eq 0) { Say "  Ruff temiz." "Green" } else { Say "  Ruff uyari verdi (engelleyici degil)." "Yellow" }

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
