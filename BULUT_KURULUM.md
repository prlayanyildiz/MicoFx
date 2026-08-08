# Bulut Sunucu Kurulumu (Git ile)

Bu dosya, MicoFX'i yeni/sifirlanmis bir bulut sunucuda Git uzerinden
kurmak icin adim adim rehberdir. Kod artik GitHub'da ozel (private) bir
depoda duruyor: **github.com/prlayanyildiz/MicoFx**

---

## Ilk kurulum (bir kerelik)

Depo **ozel (private)** - bu yuzden tek-satirlik anonim bir indirme linki
(`raw.githubusercontent.com`) hicbir zaman calismaz, o linkler sadece
herkese acik depolarda calisir. Git'i once elle kurmak sart, sonrasinin
tamami otomatik.

### 1) Git'i kur (tek manuel adim)
`winget` varsa:
```powershell
winget install -e --id Git.Git
```
`winget` yoksa (bazi Windows Server surumlerinde gelmiyor - bu bize daha
once oldu), tarayicidan
[git-scm.com/download/win](https://git-scm.com/download/win) adresinden
indirip kur - kurulum ekranlarinda hep "Next" demek yeterli.

Kurulumdan sonra PowerShell penceresini **kapat, yeniden ac** (PATH
guncellensin diye), sonra dogrula:
```powershell
git --version
```

### 2) Kodu indir (clone)
```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/prlayanyildiz/MicoFx.git
cd MicoFx
```
Ozel (private) depo oldugu icin GitHub giris istenebilir - tarayici acilir,
hesabinla giris yapip onaylarsin.

### 3) Gerisi tek komutla otomatik
```powershell
powershell -ExecutionPolicy Bypass -File .\bootstrap.ps1
```
(`.\bootstrap.ps1` tek basina calistirinca "calisan script'ler devre disi
birakildi" hatasi verebilir - Windows'un varsayilan PowerShell kisitlamasi
budur, yukaridaki komut sadece bu script icin gecici olarak asar, kalici
bir ayar degistirmez.)

Bu script sirayla: Python, Node.js ve Claude Code yoksa kurar (once
`winget` dener, olmazsa resmi siteden dogrudan indirip sessizce kurar),
sonra `KURULUM.bat`'i calistirip bagimsiz sanal ortami (`C:\MicoFX-venv`)
ve gerekli paketleri (MetaTrader5, fastapi, numpy vb.) hazirlar. Hicbir
soruya cevap vermen gerekmez, sonuna kadar kendi kendine gider.

(Sadece MicoFX'i kurup Node.js/Claude Code'a ihtiyacin yoksa, `bootstrap.ps1`
yerine tek basina `.\KURULUM.bat` de calistirabilirsin.)

### 4) MetaTrader 5
- MT5 terminalini kur, hesabina giris yap.
- Ust menu **Araclar > Secenekler > Uzman Danismanlar** sekmesinde
  **"Algoritmik alim satima izin ver"** kutusunu isaretle.

### 5) Baslat
`start.bat` dosyasina cift tikla (sessiz, tarayicida panel acar) ya da
hata ayiklamak istersen `start_console.bat` (konsol acik kalir).

### 6) Claude Code ile devam etmek istersen
```powershell
cd $env:USERPROFILE\Desktop\MicoFx
claude
```
Yeni bir oturum acilir (bu konusmanin hafizasi otomatik gelmez), ama proje
dosyalari (bu dosya, `MASTER_PROMPT.md`, kod) zaten orada oldugu icin hizli
baglam kazanir.

### 7) Panel ayarlarini kontrol et
Ilk acilista Sistem sekmesinde su yollari **bu makineye gore** guncelle:
- Yedek konumu (`backup_dir`) - varsayilan `C:\MicoFX_Yedek`, farkli bir
  yer istersen degistir.
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
5. **Depo ozel oldugu surece `raw.githubusercontent.com/.../bootstrap.ps1`
   linki hicbir zaman calismaz** (404 doner) - bu linkler sadece herkese
   acik depolarda calisir. Once Git'i elle kur, `git clone` ile depoyu cek,
   sonra `.\bootstrap.ps1`'i klasorun icinden calistir (yukaridaki 1-3.
   adimlar).
