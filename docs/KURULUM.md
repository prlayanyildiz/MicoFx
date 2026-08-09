# MicoFX - Sifirdan Kurulum Klavuzu

Bu klavuz, uzerinde daha once Python veya MicoFX calismamis **bos bir Windows
bilgisayara** sistemi kurmak icin. Teknik bilgi gerekmez, adimlari sirayla
takip etmeniz yeterli.

Toplam sure (indirmeler dahil): ~15-20 dakika.

---

## 0) Gerekenler

- Windows 10 veya 11 (64-bit)
- Internet baglantisi
- MicoFX klasorunun tamami (bu dosyanin bulundugu klasor) yeni bilgisayarda
  bir yerde duruyor olmali - USB, OneDrive/Google Drive, veya baska bir
  yontemle kopyalayin. Klasoru **surucu koku** yerine `Belgelerim` veya
  `Masaustu` gibi normal bir yere koyun (`C:\MicoFX` da olur).
- Bir MetaTrader 5 broker hesabi (demo yeterli, ilk denemede gercek para
  hesabi kullanmayin)

---

## 1) Python'u kur

MicoFX bir Python programidir, once Python'un bilgisayarda kurulu olmasi
gerekir.

**Kolay yol:** `KUR.bat` dosyasina cift tiklayin.

- Python bilgisayarda yoksa, otomatik olarak `winget` ile kurmayi dener.
- `winget` de yoksa (cok eski Windows surumlerinde olabilir), tarayicida
  https://www.python.org/downloads/ sayfasini acar. Oradan **Download
  Python** butonuna basip indirilen dosyayi calistirin.
  - **ONEMLI:** Kurulum ekraninin en altinda **"Add python.exe to PATH"**
    kutucugu vardir, bunu MUTLAKA isaretleyin. Isaretlenmezse Python
    calisir ama MicoFX onu bulamaz.
- Python yeni kurulduysa, mevcut pencereyi kapatip `KUR.bat`'i **tekrar**
  calistirin (yeni kurulan Python'un tanmasi icin yeni bir pencere/oturum
  gerekir).

---

## 2) MicoFX'in kendi bagimliliklarini kur

`KUR.bat` Python'u bulduktan sonra otomatik olarak devam eder:

1. `C:\MicoFX-venv` altinda MicoFX'e ozel bir sanal ortam olusturur
   (sisteminizdeki diger Python programlarini etkilemez). Bilerek proje
   klasorunun disinda, sabit bir yerde tutulur: OneDrive gibi bir arac projeyi
   baska bir bilgisayara senkronlarsa/kopyalarsa bile bu klasor oraya
   tasinmaz - bir sanal ortamin icinde kuruldugu makinenin Python yoluna
   mutlak referans var, baska bir bilgisayarda kullanilinca calismaz. Her
   makine burada kendi venv'ini bir kez kurar, bir daha dokunulmaz.
2. Gereken kutuphaneleri kurar (`MetaTrader5`, `fastapi`, `numpy` vb.) -
   bu adim internet hizina gore 1-3 dakika surer.

Sonunda "Kurulum tamamlandi" yazisini gorurseniz bu adim bitmistir. Bir hata
mesaji cikarsa asagidaki **Sorun Giderme** bolumune bakin.

---

## 3) MetaTrader 5'i kur ve hesaba gir

MicoFX kendi basina emir gonderemez; MetaTrader 5 terminali uzerinden
calisir.

1. Brokerinizin (orn. Pepperstone) sitesinden MetaTrader 5 kurulum dosyasini
   indirip kurun.
2. Terminali acin, **Dosya > Hesaba Giris Yap** ile demo veya gercek
   hesabinizin bilgilerini girin.
3. Ust menuden **Araclar > Secenekler > Uzman Danismanlar** sekmesine gidin
   ve **"Algoritmik alim satima izin ver"** kutusunu isaretleyip **Tamam**
   deyin. Bu kapaliysa MicoFX'in gonderdigi her emir broker tarafindan
   reddedilir.
4. Terminali acik birakin (MicoFX arka planda calisirken MT5'in de acik
   olmasi gerekir).

---

## 4) MicoFX'e MT5'in yerini soyleyin

MicoFX, hangi terminali kullandigindan emin olmak icin MT5'in kurulu oldugu
klasoru bilir (`terminal64.exe` dosyasinin tam yolu). Varsayilan deger
Pepperstone icindir; farkli bir broker kullaniyorsaniz veya kurulum yeri
farkliysa degistirmeniz gerekir:

1. MicoFX'i bir kere baslatin (asagidaki 5. adim).
2. Web arayuzunde **Sistem** sekmesine gidin.
3. **MT5 terminal yolu** alanina, MT5'in kurulu oldugu klasordeki
   `terminal64.exe` dosyasinin tam yolunu yazin, orn:
   `C:\Program Files\ICMarkets MetaTrader 5\terminal64.exe`
4. Kaydedin. Baglanti durumunu ayni sekmede gorebilirsiniz.

Yol yanlissa veya MT5 kapaliysa sistem baglanamaz; hesap goruntulenmez ve
emir gonderilmez.

---

## 5) MicoFX'i baslat

`start.bat` dosyasina cift tiklayin.

- Hicbir konsol penceresi acik kalmaz (arka planda sessizce calisir).
- Birkac saniye icinde tarayicinizda otomatik olarak
  `http://127.0.0.1:8900` acilir - bu MicoFX'in web terminalidir.
- Konsol/log gormek isterseniz onun yerine `start_console.bat`'i kullanin;
  o pencereyi kapatirsaniz uygulama durur.
- Uygulamayi durdurmak icin `stop.bat`'i kullanin.

Uygulama ilk acildiginda **izleme modundadir**: fiyatlari, gostergeleri ve
seans durumunu gunceller ama emir acmaz. Emir acmasi icin Panel sekmesinden
**Bot Baslat**'a basmaniz gerekir.

---

## 6) Ilk kontrol listesi

- [ ] Sistem sekmesinde MT5 baglantisi **bagli** gorunuyor
- [ ] Hesap bakiyesi/bilgisi dogru gorunuyor
- [ ] Semboller sekmesinde islem yapmak istediginiz semboller **aktif**
- [ ] Once **demo hesapta** birkac gun calistirip sonuclari izleyin
- [ ] Sistem sekmesinde gunluk zarar limiti gibi risk ayarlarini gozden
      gecirin

Adim adim kullanim (sembol ekleme, optimizasyon, AI denetleyici vb.) icin
[KULLANIM.md](KULLANIM.md) dosyasina bakin (ayni `docs/` klasoru).

---

## Sorun Giderme

**"python bulunamadi" / "'python' is not recognized"**
Python PATH'e eklenmemis. Python'u kaldirip "Add python.exe to PATH"
kutucugunu isaretleyerek yeniden kurun, ya da KUR.bat'i tekrar calistirin.

**`pip install` sirasinda MetaTrader5 kurulamadi**
`MetaTrader5` pip paketi yalnizca Windows icin ve yalnizca 64-bit Python ile
calisir. Python'u 64-bit surumle (python.org indirme sayfasinda varsayilan
budur) yeniden kurun.

**Tarayici acilmiyor / "baglanti reddedildi" hatasi**
Birkac saniye daha bekleyin (ilk acilista bagimliliklar diske ilk kez
yukleniyor olabilir). Hala acilmiyorsa `start_console.bat` ile konsol modunda
baslatip hata mesajini okuyun.

**Sistem sekmesinde "baglanti yok" gorunuyor**
MT5 terminali kapali olabilir, ya da 4. adimdaki `terminal64.exe` yolu
yanlis/eski olabilir. Dosya yolunu Windows Gezgini'nde MT5 kisayoluna sag
tiklayip "Dosya konumunu ac" ile dogrulayin.

**8900 portu kullanimda hatasi**
Baska bir MicoFX ornegi zaten calisiyor olabilir (`stop.bat` ile durdurun),
ya da `MICO_PORT` ortam degiskeniyle farkli bir port secin.

**Emirler "reddedildi" donuyor**
MT5'te Araclar > Secenekler > Uzman Danismanlar > "Algoritmik alim satima
izin ver" kapali olabilir (bkz. adim 3).
