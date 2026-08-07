# MicoFX

MetaTrader 5 uzerinde calisan otomatik islem sistemi ve web terminali.
(Onceki adi MicoAI; eski `data/micoai.db` ilk aciliste otomatik tasinir.)

Dort bagimsiz strateji ailesi, ATR tabanli stop/hedef/trailing, gunluk zarar
kesici, sembol bazli islem saatleri ve gerceklesmis sonuclara gore karar veren
bir risk denetleyicisi.

## Bu surum: birlestirilmis / genisletilmis surum

Bu agac urun ailesinin (MicoFX / MicoFX Orj / MicoAi / MicoFXAntigravit)
birlestirilmis, tek gecerli surumudur. Temel iskelet FX agacindan gelir
(sıkı MT5 yol kilidi + kurulum dogrulama, dinamik portfoy CRUD, sessiz/konsol
baslatici scriptleri). Bunun uzerine MicoAi denemesinden gelen ve dogru
sekilde walk-forward ile test edilebilen ozellikler eklendi:

- **`trail_mode`** (`atr` | `structure` | `hybrid`) + `trail_lookback`: ATR
  trailing yerine/yaninda swing high/low tabanli yapisal trailing. Backtest
  bu modu simule eder (canliyla ayni mantik), ama optimizer grid'inde
  taranmaz - sembol bazinda elle secilir (varsayilan `atr`, mevcut davranisi
  bozmaz).
- **`orb_retest`**: ORB ailesinde kirilimi kovalamak yerine geri test +
  yeniden kirilim bekler. Optimizer grid'inde taranir (`orb` ailesi).
- **`stale_exit_ratio`**: zaman stopunun bir orani kadar zararda kalan
  islemi erken kapatir. Optimizer grid'inde taranir (paylasilan grid).
- **AI Denetleyici**: saatlik yumusak risk olcegi (`hour_risk_scales`,
  sert saat blogundan farkli - sadece lotu kisar) ve canli PF gerilemesi
  tespiti (eski/yeni islem yarisi PF karsilastirmasi, gerileme varsa
  durumu `watch`'a dusurup lotu yarilar).
- **`autostart_mt5`** (varsayilan kapali): sadece yapilandirilan
  `terminal64.exe` calismiyorsa baslatir; sıkı yol kilidini asla atlamaz -
  `connect()` yine de yapilandirilan kurulumla eslesmeyi dogrular.

MicoFXAntigravit'ten gelen `ema_scalp` stratejisi **bilerek alinmadi**: hem
UI'da tam kablolanmamisti hem de kendi `_orb`/`_donchian`/`_vwap_rev`
degisiklikleri ayni-bar buy/sell catismasini temizlemiyordu (degismezlik
ihlali). Skor formulu, OOS kapilari (`MIN_TEST_TRADES=12`, `MIN_OOS_PF=1.10`,
`MAX_COST_PER_TRADE_R=0.25`) ve backtest durustluk kurallari MASTER_PROMPT.md
§8/§17'de tanimlandigi gibi degistirilmeden korunmustur. MicoAi'nin
farkli skor formulu yalnizca ek bir **tanı** alani olarak eklendi
(`score_consistency`, opt sonuc ozetinde gorunur) - secim/dogrulama/apply
kapisi hala paylasilan `score()` formulunu kullanir.

## Strateji aileleri

Hangi ailenin hangi sembole uydugu tahmin edilmez; optimizer her sembol icin
dort aileyi de ayri ayri test eder ve **secmeli dogrulama** diliminde kazanani
secer (asagidaki uclu bolme).

| Aile | Mantik | Ne zaman calisir |
|---|---|---|
| `t3_stoch` | Tillson T3 trend yonu + Stochastic RSI %K/%D kesisimi | Trendli, momentumun donus yaptigi piyasalar |
| `orb` | Seansin ilk N dakikasinin araligi kirilinca, **kapanis onayiyla** | Endeks acilislari ve Londra acilisi gibi hacim patlamalari |
| `vwap_rev` | Seans VWAP'inden N standart sapma uzaklasan fiyati geri doner diye satin/sat | Yatay, ADX'in dusuk oldugu gunler |
| `donchian` | Onceki N barin en yuksek/en dusuk seviyesinin kapanisla kirilmasi; istege bagli **sikisma filtresi** | Seans acilisina bagli olmayan, gun icinde herhangi bir saatte gelen volatilite genislemeleri |

Aile secimleri kanita dayali: acilis araligi kirilimlarinda kapanis onayinin
wick onayindan belirgin sekilde ustun oldugu ve ilk kirilim yonunun seans
sonucunu ucte iki oranda belirledigi genis endeks calismalarinda olculmus;
VWAP tarafinda ise ortalamaya donusun tek istatistiksel olarak saglam kurulum
oldugu, crossover kurulumlarinin ise hicbir anlamli sonuc uretmedigi
gosterilmistir. Bu yuzden VWAP ailesi bilerek yalnizca ortalamaya donus
yonunde calisir. Donchian ailesindeki `don_squeeze`, volatilitenin genislemeden
once daraldigi gozlemine dayanir: kirilim yalnizca kanal alisilmadik derecede
daralmisken alinir, boylece zaten uzamis bir hareketin pesine takilinmaz.

### Denenip cikarilan: ters sinyalde cikis

Pozisyonu strateji ters sinyal verdiginde kapatmak makul bir fikirdi ve
uygulandi, ama olculdugunde islemlerin yalnizca **%0-1.6**'sinda tetiklendi:
islemler ortalama 3-6 barda ATR trailing stop ile kapaniyor, ters sinyal ise
cok daha sonra geliyor. Islemeyen bir anahtar birakmak yaniltici olacagi icin
kod tamamen kaldirildi. Cikis tarafinda gercek is yapan sey trailing stop,
maliyete cekme ve kismi kar seviyesidir.

---

Adim adim kullanim icin bakiniz: **[KULLANIM.md](KULLANIM.md)**.
Sifir bilgisayara ilk kurulum icin bakiniz: **[KURULUM.md](KURULUM.md)**
(`KURULUM.bat`'a cift tiklamak yeterli).

## Kurulum

```powershell
cd C:\Users\prlay\OneDrive\Desktop\MicoFX
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

MetaTrader 5 terminali kurulu ve hesaba giris yapmis olmali. Terminalde
**Araclar > Secenekler > Uzman Danismanlar > Algoritmik alim satima izin ver**
acik olmalidir; kapaliysa emirler reddedilir.

## Calistirma

```powershell
.\start.bat
```

Terminal `http://127.0.0.1:8900` adresinde acilir. Port `MICO_PORT` ortam
degiskeni ile degistirilebilir.

Motor uygulama acilir acilmaz **izleme modunda** calisir: gostergeleri, seans
durumunu ve fiyatlari surekli gunceller ama emir acmaz. Emir acmasi icin
terminalden **Bot Baslat** demek gerekir.

---

## Web Terminali

| Sekme | Icerik |
|---|---|
| **Panel** | Hesap ozeti, islem kapasitesi (hangi sembolde kac lotla kac islem acilabilir), acik pozisyonlar, gunluk sonuc, canli sembol durumu |
| **Semboller** | Sembol bazli tum ayarlar: lot, sinyal parametreleri, ATR risk ayarlari, giris filtreleri ve **islem saatleri** |
| **Optimizasyon** | Parametre izgarasi, uclu bolmeli ileri test, sonuclar (skora gore sirali) ve gecmis |
| **AI Denetleyici** | Sembol bazli saglik karari, karantina, lot carpani, zararli saatler ve ayarlari |
| **Sistem** | Bot kontrolu, hesap limitleri, **MT5 terminal yolu**, acil islemler |
| **Log** | Canli terminal kaydi (seviye filtreli, indirilebilir) |

Ayarlar degistirildigi anda SQLite veritabanina yazilir; ayri bir kaydet
adimi yoktur.

---

## Semboller ve lot adimlari

Broker minimum lotlari sistemin tabanidir:

| Grup | Semboller | Micro lot | Seans |
|---|---|---|---|
| Forex | EURUSD, GBPUSD, AUDUSD, USDCAD, USDCHF | 0.01 | Pzt-Cum |
| Endeks | GER40, FRA40, UK100, NAS100, US30, US500 | 0.10 | Borsa saatleri |
| Emtia | XAUUSD, SpotBrent | 0.01 | Pzt-Cum |

**Global lot carpani** (Sistem sekmesi) tum sembollerin lotunu tek sayiyla
olcekler. Panel'deki "guvenli ust sinir", 13 pozisyonun tamami acikken ve
hepsi stop olursa gunluk zarar limitini asmayacak en yuksek carpandir.

### Avantaja gore lot agirliklandirma

`size_by_edge` acikken her sembolun lotu, kendi test diliminde olculen islem
basi beklentisinin sembollerin ortancasina oranina gore olceklenir. Semboller
arasindaki beklenti farki kucuk degil - en iyi ile en kotu arasinda kat kat
fark cikiyor - dolayisiyla riski esit bolmek en zayif enstrumana en guclusu
kadar butce ayirmak demek. Oran **karekoku alinarak** uygulanir (birkac
duzine islemle olculmus bir beklenti gurultulu bir tahmindir, tam kaldirac
hak etmez) ve `x0.60` ile `x1.80` arasina sikistirilir. Panel'deki **Avantaj**
sutunu her sembolun aldigi carpani gosterir.

Onemli sinir: broker lot adimi 0.01 oldugu icin lotlar minimumdayken
(`0.01` forex/emtia, `0.10` endeks) carpanin yuvarlanacak yeri yoktur -
`0.01 x 1.35` yine `0.01` eder. Agirliklandirma ancak lotlar minimumun
uzerine cikinca, yani global lot carpani buyutuldugunde veya risk modunda
bakiye yeterken devreye girer. Avantaj sutunu carpani gosterir, **Lot**
sutunu gercekten gonderilecek hacmi gosterir; ikisini karsilastirarak
carpanin isleyip islemedigi gorulur.

### Broker sembol adlari

Brokerlar ayni enstrumani farkli adlandirabilir (`EURUSD`, `EURUSD.r`,
`EURUSD_i` gibi). Sistem once tam eslesme, sonra benzer ad arar; bulamazsa
**Sistem > Sembol Isim Eslemesi** tablosundan elle yazabilirsiniz:

- Bos birakilirsa otomatik eslestirme calisir.
- Bir ad yazilirsa yalnizca o kullanilir; yanlissa sembol islem yapmaz ve
  tabloda "bulunamadi" olarak isaretlenir (sessizce baska bir enstrumana
  kaymaz).
- Ustteki arama kutusu brokerin sembol listesinde arama yapar; sonuca
  tiklayinca ad panoya kopyalanir.

Her sembol icin iki lot modu vardir:

- **Sabit lot** - her islemde ayni lot kullanilir (varsayilan).
- **Risk yuzdesi** - lot, bakiyenin belirlenen yuzdesi ATR stop mesafesine
  bolunerek hesaplanir ve `Maks lot` ile sinirlanir.

**Panel > Islem Kapasitesi** tablosu her sembol icin lotu, islem basina
gereken marji, acik pozisyon sayisini, kalan slot sayisini ve serbest marjin
kac islem daha kaldirabilecegini gosterir.

---

## Risk kontrolleri

Islem acilmadan once sirayla su kontroller gecilir:

1. Sembol seansi acik mi, kapanisa `flat_before_close_min` dakikadan fazla var mi
2. Piyasa fiyat akitiyor mu (hafta sonu / tatil korumasi)
3. AI denetleyici karari - karantina veya zararli saat engeli
4. Spread filtresi (`max_spread_atr`; raw hesapta varsayilan olarak **kapali**)
5. Sembol pozisyon limiti ve ters yonde acik pozisyon var mi
6. Toplam pozisyon limiti
7. Serbest marj ve maksimum marj kullanim yuzdesi
8. Gunluk zarar / kar limiti (asilirsa gun sonuna kadar yeni islem yok)

Semboller birbirinden bagimsizdir; korelasyon kisiti yoktur, 13 sembolun
tamami ayni anda pozisyon acabilir.

Acik pozisyonlarda maliyete cekme (breakeven), ATR trailing stop, sure stopu
ve seans kapanisinda otomatik kapatma calisir.

---

## Optimizasyon ve asiri ogrenme kontrolu

Bir parametre setinin gecmiste iyi gorunmesi kolaydir; zor olan bunun gelecege
tasinmasidir.

### Uclu bolme: secen dilim olcemez

Temel kural su: **bir seyi secen veri parcasi, ayni seyi durust olcemez.** Bu
yuzden gecmis uc isi ayri parcalara dagitilir (`segments`, varsayilan 5):

| Parca | Isi | Kullanildigi yer |
|---|---|---|
| **Secim** (ilk 3 segment) | Parametreleri arar | Izgara taramasi, plato harmani |
| **Secmeli** (sondan ikinci) | Kazanan adayi *ve* hangi strateji/zaman diliminin calisacagini secer | Aileler arasi siralama |
| **Test** (son segment) | Hicbir seye karar vermez | Rapor edilen sayi, uygulama esigi |

Bu ayrimin neden onemli oldugu olculdu. Aileler arasi secim onceden **arama
skoruna** gore yapiliyordu; oysa her aile farkli buyuklukte bir arama uzayina
sahiptir ve skorlar birbiriyle kiyaslanamaz. Secim, kendi arama diliminde
degil ayri bir dogrulama diliminde yapildiginda dokunulmamis test diliminde
islem basi beklenti **+0.184R'den +0.202R'ye** cikti; Donchian ailesi de
eklenince **+0.203R** ve dogrulanan sembol sayisi 9/13'ten 10/13'e yukseldi.

Ayni olcum onceki raporlanan sayilarin bir kismini da duzeltti: eski "holdout"
dilimi hem siralamada hem raporda kullaniliyordu, dolayisiyla kendi lehine
sapmisti. Simdi raporlanan Test sayisi hicbir secime katilmiyor.

### Diger savunmalar

1. **Segmentli degerlendirme.** Her aday her secim segmentinde ayri ayri
   olculur. Tek bir sansli donemde kazanan parametre elenir;
   `min_positive_ratio` (varsayilan %60) segmentin kacinin pozitif olmasi
   gerektigini belirler. Skor `ortalama x tutarlilik^2` ile hesaplanir.
2. **Cift esik.** Bir parametre seti ancak **hem** secmeli **hem** test
   diliminde kar ederse (PF >= 1.10, en az 12 islem) otomatik uygulanir.
   Aksi halde sonuc gosterilir ama uygulanmaz.
3. **Parametre platosu.** Her adayin skoru izgaradaki komsularinin skoruyla
   harmanlanir (`plateau_weight`). Etrafi zararla cevrili tek bir zirve neredeyse
   her zaman egri uydurmadir; komsulari da calisan bir bolge gercek bir avantajdir.
4. **Zaman dilimi ve strateji taramasi.** Ayni sembol M5'te kar, M15'te zarar
   edebiliyor; ayni sekilde bir sembolde ORB, digerinde momentum kazaniyor. Her
   (zaman dilimi x strateji) ciftinin kendi arama turu var. Butun zaman dilimleri
   **ayni takvim penceresinde** (`lookback_days`) olculur - yoksa H4 yillarca
   veriyle, M5 birkac gunle degerlendirilir ve karsilastirma anlamsiz olur.
5. **Yerel iyilestirme.** Rastgele ornekleme buyuk bir izgaranin sadece kucuk bir
   kismini gorur. En iyi noktalarin izgara komsulari ayrica taranir
   (`refine_rounds`), boylece iyi bir bolgenin tepesi kacirilmaz.
6. **Az parametre.** Izgaraya eklenen her eksen ayni sabit arama butcesini
   boler, yani bedava eksen yoktur. Yeni bir parametre once A/B ile olculur;
   test diliminde islem basi beklentiyi artirmiyorsa izgaraya alinmaz.

Backtest canli motorla ayni kurallari kullanir: sinyal kapanan barda uretilir,
emir bir sonraki barin acilisinda gerceklesir, spread **ve komisyon** her islemde
tahsil edilir, ayni bar icinde hem stop hem hedefe deginiliyorsa stop gecerli
sayilir. Sonuclar `R` cinsindendir (1R = o islemin baslangic stop mesafesi),
boylece farkli semboller karsilastirilabilir.

### Maliyet neden zaman dilimini belirler

Pepperstone raw hesapta forex komisyonu **1 lot gidis-donus 8 USD**, yani 0.01
lotta 0.08 USD. Bu sabit maliyetin onemi, islemin stop mesafesine gore degisir:

| Zaman dilimi | EURUSD ATR | 0.01 lot riski | Maliyet / risk |
|---|---|---|---|
| M5 | ~4 pip | ~0.43 USD | **%26** |
| M15 | ~8 pip | ~0.85 USD | %12 |
| M30 | ~13 pip | ~1.40 USD | %7 |

M5'te her islem daha ilk saniyede riskinin dortte birini maliyete veriyor;
hicbir gosterge bunu telafi edemez. Bu yuzden optimizer maliyeti modelleyince
forex sembollerini kendiliginden daha genis stop'a ve daha yuksek zaman dilimine
tasidi. Panel'deki **Maliyet / Islem** sutunu bu orani her sembol icin canli
gosterir; %25'i asan bir kurulum optimizer tarafindan otomatik reddedilir.

---

## AI Denetleyici

Denetleyici bir dil modeli degildir; MT5'ten okudugu **gerceklesmis islem
sonuclarina** gore karar veren uyarlanabilir bir risk kontrolcusudur. Avantaj
uretmez, var olan avantazi korur. Verdigi her karar loglanir ve geri alinabilir.

| Kural | Tetik | Aksiyon |
|---|---|---|
| Karantina (seri) | `quarantine_losses` kadar ust uste zarar | Sembol `quarantine_hours` boyunca islem acmaz |
| Karantina (PF) | Yeterli islemde PF < `quarantine_pf` | Ayni sekilde askiya alinir |
| Izleme | PF < `watch_pf` | Islem devam eder, lot `watch_risk_scale` ile kisilir |
| Zararli saat | Bir saatte yeterli islem + negatif net + dusuk PF | O saat o sembol icin kapatilir |
| Gunluk kayip | Gun zarari `dd_soft_pct` ile `dd_hard_pct` arasinda | Lot carpani kademeli olarak `risk_scale_floor` seviyesine iner |
| Yeniden optimize | Karantinaya giren ve parametreleri eskimis sembol | Arka planda otomatik optimizasyon kuyruguna alinir |

Kararlar veritabaninda saklanir, uygulama yeniden baslasa da karantina devam
eder. `AI Denetleyici` sekmesinden her sembol tek tek serbest birakilabilir.

---

## Proje yapisi

```
micofx/
  paths.py        dizinler ve varsayilan yapilandirma
  logbus.py       bellek ici + dosya log akisi
  models.py       SymbolConfig / SystemConfig veri modelleri
  store.py        SQLite kalicilik katmani
  mt5client.py    MT5 baglantisi, semboller, barlar, emirler (thread-safe)
  indicators.py   T3, Stochastic RSI, ATR, ADX, VWAP, acilis araligi, Donchian
  strategy.py     sinyal uretimi ve gosterge onbellegi
  sessions.py     islem saatleri mantigi
  risk.py         lot hesabi, kapasite, gunluk limit
  supervisor.py   AI denetleyici: karantina, lot olcekleme, zararli saatler
  engine.py       izleme ve islem dongusu
  backtest.py     bar bazli simulasyon
  optimizer.py    arka plan segmentli ileri test isi
  web/            FastAPI arayuzu + terminal (HTML/CSS/JS)
config/defaults.json   ilk kurulum degerleri
data/micofx.db         calisma zamani ayarlari (git disi)
logs/                  log dosyalari (git disi)
```

---

## Uyari

Bu yazilim finansal tavsiye degildir. Once demo hesapta calistirin, sonuclari
dogrulayin. Gecmis performans gelecegi garanti etmez.
