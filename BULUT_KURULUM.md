# Bulut Sunucu Kurulumu (Git ile)

Bu dosya, MicoFX'i yeni/sifirlanmis bir bulut sunucuda Git uzerinden
kurmak icin adim adim rehberdir. Kod artik GitHub'da ozel (private) bir
depoda duruyor: **github.com/prlayanyildiz/MicoFx**

---

## Ilk kurulum (bir kerelik)

### 1) Python kur
Zaten kuruluysa atla. Yoksa `KURULUM.bat` bunu otomatik yapmaya calisir,
calismazsa tarayicidan [python.org/downloads](https://www.python.org/downloads/)
adresinden indirip kur - kurulum ekraninda **"Add python.exe to PATH"**
kutucugunu MUTLAKA isaretle.

### 2) Git kur
`winget` varsa:
```powershell
winget install -e --id Git.Git
```
`winget` yoksa (bazi Windows Server surumlerinde gelmiyor), tarayicidan
[git-scm.com/download/win](https://git-scm.com/download/win) adresinden
indirip kur - kurulum ekranlarinda hep "Next" demek yeterli.

Kurulumdan sonra PowerShell penceresini **kapat, yeniden ac** (PATH
guncellensin diye), sonra dogrula:
```powershell
git --version
```

### 3) Kodu indir (clone)
Istedigin klasore git (orn. `cd Desktop`), sonra:
```powershell
git clone https://github.com/prlayanyildiz/MicoFx.git
cd MicoFx
```
Ozel (private) depo oldugu icin GitHub giris istenebilir - tarayici acilir,
hesabinla giris yapip onaylarsin.

### 4) MicoFX'i kur
```powershell
.\KURULUM.bat
```
Bu, bagimsiz bir sanal ortam (`C:\MicoFX-venv`) kurup gerekli paketleri
(MetaTrader5, fastapi, numpy vb.) indirir.

### 5) MetaTrader 5
- MT5 terminalini kur, hesabina giris yap.
- Ust menu **Araclar > Secenekler > Uzman Danismanlar** sekmesinde
  **"Algoritmik alim satima izin ver"** kutusunu isaretle.

### 6) Baslat
`start.bat` dosyasina cift tikla (sessiz, tarayicida panel acar) ya da
hata ayiklamak istersen `start_console.bat` (konsol acik kalir).

### 7) Panel ayarlarini kontrol et
Ilk acilista Sistem sekmesinde su yollari **bu makineye gore** guncelle:
- Yedek konumu (`backup_dir`) - varsayilan `D:\MicoFX_Yedek`, bu sunucuda
  D: suruculu yoksa degistir.
- MT5 terminal yolu - kurulum yerin farkliysa guncelle.

---

## Gunluk kullanim - kod guncellemesi geldiginde

Ben (Claude) buradan bir degisiklik yaptigimda GitHub'a gonderirim. Sende
sadece su tek komut yeterli:
```powershell
cd MicoFx
git pull
```
`.venv` (`C:\MicoFX-venv`), `data\micofx.db` (sembol/optimizasyon
gecmisin), `logs\` klasoru bu islemden **hic etkilenmez** - sadece kod
dosyalari guncellenir. Botu yeniden baslatman gerekebilir (`stop.bat` ->
`start.bat`) yeni kodun calismaya baslamasi icin.

---

## Onemli kurallar (bugun ogrenilen dersler)

1. **`.venv`'i asla baska bir bilgisayara kopyalama/senkronlama** (OneDrive
   dahil). Icinde o an kuruldugu makinenin Python yoluna mutlak referans
   var, baska makinede "No Python at ..." hatasi verir. Bu yuzden proje
   klasorunun disinda, sabit bir yerde (`C:\MicoFX-venv`) tutuluyor -
   `.gitignore` de zaten `.venv/`'i depoya hic almiyor.
2. **Ayni MT5 hesabinda iki bot'u ayni anda calistirma.** Yerelde ve
   bulutta ayni anda `start.bat` calistirirsan cift islem riski olur -
   hangisi "canli" calisiyorsa sadece o baslatilmali, digeri `stop.bat`.
3. **`data\micofx.db` deponun disinda** (`.gitignore`'da) - sembol
   ayarlarin, optimizasyon gecmisin, AI denetleyici durumun hep orada.
   Git bunu tasimaz; makineler arasi tasimak istersen dosyayi elle
   kopyalamak/gondermek gerekir.
4. Bir `.bat`/`.vbs` dosyasi calistirinca "No Python at ..." hatasi
   verirse: `.venv` baska bir makineden kopyalanmis/senkronlanmis demektir
   - sil, `KURULUM.bat`'i o makinede tekrar calistir.
