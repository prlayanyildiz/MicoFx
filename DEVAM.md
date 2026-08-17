# DEVAM — yeni makinede ilk okunacak dosya

Bu dosya git'te. Köprü klasörleri (`claude/`, `cursor/`, `antigravity/`,
`.bridge/`) gitignore'da olduğu için taşınmaz — kalıcı olması gereken ne
varsa buraya yazılır.

Yeni bir oturum açıldığında: önce bunu, sonra `git log` oku. Commit
mesajları neden'leri taşıyor, kod ne'yi.

> 16.08.2026 notu: bu dosya aslında git'te DEĞİLDİ — eski makinede hiç
> commit edilmemişti ve `MicoFxOld` klasörü taşıma sonrası silinince tek
> kopyası kaybolmak üzereydi. İçeriği oturum belleğinden geri yazıldı ve
> commit edildi. Bir daha silinmesin diye artık gerçekten takipte.

---

## 1. Köprü — kim ne yapar

**Claude** teşhis eder, karar verir, diff inceler, commit ve push atar.
Ölçüm tasarlar, sonucu yorumlar, canlı sistemi yönetir.

**Cursor** ölçer ve kodlar. Commit atmaz, push etmez, canlı bota ve DB'ye
dokunmaz.

Yazışma dosyaları:

| yön | dosya |
|---|---|
| Claude → Cursor | `claude/FOR_CURSOR.md` |
| Cursor → Claude | `cursor/FOR_CLAUDE.md` |
| Claude → Antigravity | `claude/FOR_ANTIGRAVITY.md` |
| Antigravity → Claude | `antigravity/FOR_CLAUDE.md` |

Antigravity salt-okuma denetçisiydi; token'ı bitti. Geri gelirse yetkisi
**kod okumak ve bulgu yazmak** ile sınırlı — kod değiştirmez, commit atmaz,
kendi görevini seçmez, okuduğu commit hash'ini raporun başına yazar.

**Sihirli sözcükler:** `MICO MOLA` tüm ajanları duraklatır,
`MICO DEVAM` kaldığı yerden sürdürür.

**Süre sınırı yok.** Köprü sürekli çalışır; Claude boş durmaz, Cursor'a her
zaman yeni ve farklı bir iş bırakır. "Bekleyelim" bir plan değildir.

**İki makine kuralı.** Sunucudaki oturum canlı sistemin sahibidir: botu o
çalıştırır, canlı ayarı o değiştirir, commit'i o atar. Laptop yalnızca
operatör açıkça isterse devreye girer.

16.08'de bu kural yokken ikimiz aynı pytest hatasına aynı anda girdik —
biri ölçüp `DEVAM.md`'ye yazdı, diğeri düzeltti, push çakıştı ve rebase
gerekti. Zararsız atlatıldı ama aynı çakışma canlı ayarda olsaydı biri
diğerinin değişikliğini sessizce ezerdi.

Devralan taraf önce `git fetch` ile ayrışma var mı bakar. **Aynı anda iki
makinede bot çalıştırılmaz** — ikisi de "doğru" hesapta olduğu için hesap
kilidi bunu yakalamaz ve her sinyal iki kez açılır.

---

## 2. Cursor protokolü (bağlayıcı)

**Onay almadan davranış değiştirme.** Canlı emir yolunu, risk kapılarını
veya seans kurallarını değiştiren kod brief'te açıkça istenmedikçe yazılmaz.
İyi fikir yeterli sebep değil — fikirler raporun sonuna `ÖNERİ` başlığı
altında yazılır.

**Önce ölç, sonra bağla.** Bir kapı/filtre eklemeden önce o kuralın geçmişte
neyi eleyeceğini ölç. Elenen kova net R olarak negatif değilse kural
yazılmaz.

**Holdout, seçim dilimi değil.** Bir değişiklik "iyi" ise bunu holdout
söylemeli. Seçim veya validasyon dilimindeki iyileşme kanıt değildir.

**Sayının kaynağını etiketle.** Kaç işlem, hangi dönem, hangi semboller.
`n<30` ise "yetersiz" yaz, bulgu diye sunma. Popülasyon kullanıyorsan kaç
sembol / kaç gün olduğunu başlığa yaz.

**`n>=30` yeterli demek değil — farkın büyüklüğüne göre güç hesapla.**
17.08'de bütün bir gece, n=173'te ölçülen 3,41 puanlık bir farkın peşinde
koşuldu; o örneklemde standart hata 3,59 puandı, yani fark gürültünün
içindeydi (p=0,34). Oran karşılaştırması yapıyorsan standart hatayı ve
güven aralığını **raporun içine yaz**. Ayırt etmek istediğin fark
biliniyorsa gereken n'i de yaz. `n>=30` kuralı bir taban, bir yeterlilik
kanıtı değil.

**Zaman dilimini ve pencereyi de yaz.** Bu projede aynı sayı farklı zaman
diliminde farklı şey demek: bar çekme sınırı sabit olduğu için M5 ~95 gün,
M30 ~610 gün görüyor. Gün başına ifade edilen her ölçüt (R/gün, işlem/gün)
zaman dilimiyle birlikte verilmezse yanıltıcıdır — LEV-1 tam olarak bu
yüzden oldu. İki sembolü karşılaştırıyorsan pencerelerinin eşit olup
olmadığını önce söyle.

**Fail-first.** Yeni davranışın testi, kod olmadan kırılmalı. Raporda stash
altında alınan hata mesajını göster.

**Ruff + tam suite yeşil olmadan rapor yazma.** Ruff'ın autofix'ine körlemesine
uyma — bu projede iki kez load-bearing kod sildi ve testler yakaladı.

**Negatif sonuç da sonuçtur.** "Bu yol kapalı" demek "belki çalışır"dan daha
değerlidir. İyi haber üretmek için veriyi bükme.

---

## 3. Ortam (yeni makine, 16.08.2026)

| ne | nerede |
|---|---|
| proje | `C:\Users\Administrator\MicoFx` |
| sanal ortam | `C:\MicoFX-venv` — **proje dışında, bilerek**. `python`/`pytest` PATH'te değil |
| test/ruff | `C:\MicoFX-venv\Scripts\python.exe -m pytest -q` ve `... -m ruff check .` |
| panel portu | 8900 (`MICO_PORT` ile değişir) |
| MT5 | `C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe` |

`MicoFxOld` silindi. Git'in getirmediği ne varsa (`data/micofx.db`,
`cursor/_bp.json`, `cursor/_universe_live01.json`) artık sadece bu makinede.
`~/.claude/.../memory/` boş geldi — eski Claude notları taşınmadı, kayıp.

**pytest `WinError 1463` — çözüldü.** Bu makinede sembolik bağlantı takibi
politika gereği kapalı. `tmp_path` her test için `<ad>0` klasörü ve yanına
`<ad>current` bağlantısı üretiyor; pytest oturum sonunda hepsini `resolve()`
ediyor ve orada patlıyordu. Testlerin hepsi geçtiği hâlde exit 1 dönüyor,
özet satırı yutuluyordu — ve `KUR.ps1` adım 7 bunu "testler geçmedi" diye
okuyordu.

Bağlantıyı **oluşturmak** serbest, **izlemek** yasak; o yüzden `2ef2744`'ün
basetemp'i taşıması çökmenin yerini değiştirdi, kendisini değil.
`tests/conftest.py` artık o tek temizlik yürüyüşünü `OSError`'a karşı
toleranslı yapıyor — koşu bittikten sonra, iki modül referansında birden
(`_pytest.tmpdir` fonksiyonu import anında isimle alıyor). Gerçek hatalar
hâlâ hata veriyor.

---

## 4. Ölçülmüş ve kapanmış yollar — tekrar önerme

Hepsi denendi, sayıyla elendi:

trail ayarları; trail güncelleme sıklığı; eşzamanlı pozisyon sayısı; aile
seçimi; seçim metriği (`score` dört testte de kazandı); stop genişliği;
spread kapıları; kayıptan sonra atla kuralı; kripto semboller; FX'te M5;
DOM (bu CFD'lerde yok); min lot marj şişmesi (ölçüldü, ~1.00x, yok);
`size_by_edge` (zaten açık).

**Gece saatleri kapısı (01/04/05/22)** — canlı geçmişte 474 işlem, net
−479.66 $, toplam zararın %78'i, beş sembolde birden görünüyordu. Holdout'ta
öldü: net R toplamı 534.43 → 220.36 (dört saat kapalı) / 313.02 (optimizer
kendi arasa), `validated` 6/10 → 3/10 → 0/10. Gömüldü.

**Seçim ölçütüne calmar bağlamak (SEL-1)** — ölçüldü, `score`'dan
**ayırt edilebilir şekilde daha kötü**. Zamansal bölme (ilk 2/3 eğitim, son
1/3 karar; n=88 test), tüm sıralama anahtarları validation diliminden,
holdout'a hiç dokunulmadan. Test diliminde holdout net R ile Pearson:
`score` +0,739, validation `net_r` +0,788 (GA'lar örtüşüyor),
**validation calmar +0,115**, expectancy −0,293, PF −0,318. Calmar kendi
hedefini (holdout calmar) bile öngörmüyor: +0,106.

Sebep anlaşıldı: `score` içinde yumuşak bir DD terimi var
(`net_r / (net_r + max_dd)`) ve hacimli net R'yi koruyor; `net_r / max_dd`
onu siliyor, holdout bilgisini de beraberinde götürüyor. **LEV-1'deki
calmar kazancı boyutlandırmaya özgü, seçime taşınmıyor.**

Ayrıca bu arşiv daha ince soruları **cevaplayamaz**: `score` ile validation
`net_r` arasındaki ~0,05'lik farkı görmek ~1482 bağımsız koşu ister; elde
262 var ve bağımsız değil (11 sembol, 5 gün). Metrik yarışı bu veriyle
kapandı.

**Skorun holdout'u öngörmediği iddiası** — ölçüldü, yanlış çıktı. 262
koşuda skor ↔ holdout net R Pearson 0,67 (uygulanan 58'de 0,81); validation
net R ile 0,72 / 0,81. İlişki zayıf değil. Ama bileşen kırılımı bir şey
öğretti: skorun taşıdığı holdout bilgisi **hacimli net R**; işlem başı
kalite holdout ile **negatif** korele (selection expectancy −0,36, PF −0,39,
validation expectancy −0,35, PF −0,36). Yani seçim çok işlemli toplam R'yi
ödüllendiriyor, işlem başı kaliteyi değil. Ağırlık ölçütü tasarlarken bu
bilinsin.

**Flip ailelerine ADX/body kapısı bağlamak** — sezginin tersi çıktı. GER40'ta
engellenecek kova +20.1R, geçen kova −7.5R. Bağlamak parayı atardı.

---

## 5. Tekrarlayan arıza sınıfları

Bu projede aynı hatalar farklı kılıklarda geri geliyor:

**Açık görünen ama etkisi olmayan ayar.** `lot_mode="fixed"` her sembolü düz
0.1 lota kilitlemişti ve `risk_percent`, `max_lot`, risk kapısı hepsi atıldı.
Flip ailelerinde `adx_min` panelde yazıyordu, kod hiç okumuyordu. Ölçüt: bir
ayarı değiştir, davranış değişmiyorsa ayar ölüdür.

**B konfigürasyonunu A'nın siciliyle yargılamak.** Antigravity 45 günlük 34
sembollü veriyi 27 günlük 10 sembol sanıp iki kaldıracı yanlış ölçtü.

**Aynı kuralın iki kapıda farklı uygulanması.** `min_atr_ratio` engine'de
vardı, backtest'te yoktu. Seans saati canlıda `localtime`, kağıtta broker
damgasıydı.

**Canlı kova bulgusu ≠ kanıt.** Canlı P&L'i saate/güne/koşula göre kırıp
bulunan "güçlü" örüntüler iki kez holdout'ta öldü. Hipotez sayılır, kaldıraç
sayılmaz.

---

## 6. Nerede duruyoruz (16.08.2026)

Hesap: Pepperstone demo 61562752, 2.113,60 $, 1:100.

| kaynak | aylık | özkaynağın % |
|---|---|---|
| holdout | +640 $ | %30 |
| panel projeksiyonu | +1170 $ | %55 |
| canlı gerçekleşen | **−986 $** | −%47 |

Portföy holdout'ta 1.80 R/gün, 26.7 işlem/gün. GER40 tek başına toplamın
%43'ü; üç sembol negatif.

Canlı 626 işlem: kazanma %30.0, başabaş %34.2, ortalama kazanç +8.25,
ortalama kayıp −4.30. **Açık 4.2 puan** ve hâlâ açıklanmadı.

**Uygulama kalitesi elendi (EX-1, 17.08).** Kayma: 10–14.08 penceresinde
515 örnek, giriş bacağı n=269 ortalama **+0,00032 R** (medyan 0). Spread
oranı: sembol başına 78k–121k örnek, medyan 0,95–1,15; dokuz sembolde
ekstra maliyet ortalama **+0,00113 R/işlem**. Toplam **0,00145 R/işlem**,
626 işlemde 0,9 R — holdout işlem başı beklentisinin (0,111 R) **%1,3'ü**.
Açığın ~%0'ı. Negatif sonuç, bu yol da kapandı.

**Stop bacağının sıfırı ölçüm hatası değil, venue raporu (EX-2, 17.08).**
217 örneğin tamamında `adverse`, `points`, `r` sıfırdı. Kod totolojisi
değil: karşılaştırma bilet SL'i ile bildirilen fill arasında, iki ayrı
sayı. Kanıt dump'tan: kitapta **1199 SL kapanışının 1199'unda** bildirilen
fiyat biletin SL'ine eşit ve **hiçbiri birden fazla deal değil**.
Pepperstone-Demo stopları tam SL fiyatından dolduruyor.

**Gerçek hesapta bu böyle olmayacak.** Orada stop, seviyeyi delerek ve
parçalı dolar. Yani bu demo, kayıp bacağını sistematik olarak iyimser
gösteriyor ve 4,2 puanın stop kaynaklı kısmını **ölçemez**. Canlı paraya
geçilirken bu körlük hatırlanmalı.

Bu arada gerçek bir gizli böcek bulundu ve onarıldı (`739e834`): parçalı
stop fill'i son print'e göre puanlanıyordu, son print de çoğu zaman stop
seviyesinin kendisi. VWAP'a bağlandı — bu demoda hiçbir şeyi değiştirmiyor
(parçalı fill yok), gerçek hesapta ölçümün doğru olmasını sağlıyor.

**Ölçülmemiş kalan:** kâğıt orijinal SL'den çıkıldığını varsayar; canlı
skor **son görülen** (trail'lenmiş) SL'ye karşı bakar. Trail sonrası tam
fill, bu bacakta kâğıt/canlı farkını göstermez.

Marj: kitap 1:100'de 1.274 $ marj yiyor, marj seviyesi %166. US2000 ve
XAUUSD ikisi marjın %63'ünü alıp 0.20 R/gün veriyor; GER40 38 $ marjla 0.772
R/gün veriyor. **Backtest marjı hiç bilmiyor** — her sembolü tekil vakumda
optimize ediyor, o yüzden sistematik olarak en dar stopu seçiyor.

**`daily_loss_pct` 22 — geçici ve kasıtlı.** 16.08 22:41'de operatör
panelden 10 → 22 yaptı. Sebep ölçüm: gün freni erken tetiklenirse örnek
kesilir ve BS-3'ün fatura yarısı yine ölçülemez. Bu bir arıza değil, geri
alma. Ölçüm penceresi kapandığında düşürülecek — demo hesapta bile %22
günlük zarar, 2.113 $ üzerinde 465 $ demek.

Kitap: 10 sembol, hepsi açık, `lot_mode=risk`, sembol başına `max_positions=2`.
Risk yüzdeleri 0.2 (SpotBrent, XAUUSD, US500) ve 0.8 (diğer yedi). Hepsi dolsa
teorik eşzamanlı risk %12.4; sistem kapısı `max_concurrent_risk_pct=15`.

---

## 7. Açık işler, öncelik sırasıyla

**BUG — canlı SL/TP güncellemesi sessizce başarısız (OPS-1, 17.08).**
`WARN [JPN225] SL/TP guncellenemedi #359440001 (0)` beş dakikada bir
tekrarlıyor; 17.08 sabahı 18 kez, XAUUSD (8) ve JPN225 (10) üzerinde.
Etkilenen pozisyonlar **kârda** ve trail ilerlemiyor: JPN225 #359440001 /
#359440015 her biri +39 $, SL hâlâ açılıştaki 69039,6'da.

Broker mesafesi sebep **değil**: `trade_stops_level = 0`,
`trade_freeze_level = 0`, SL bid'in 107,7 puan altında. Yani yer var,
istek yine de geçmiyor.

Ayrıca teşhis kapalı: log `(0)` yazıyor. MT5'te 0 bir hata kodu değil —
`order_send` `None` döndüğünde `getattr(result, "retcode", 0)` böyle
okunur. `mt5.last_error()` yazılmadığı için sebep kayıtta yok. Kazanan
pozisyonun stopu ilerlemiyorsa bu doğrudan paradır.

**BUG — gece yedeği hiç çalışmıyor.** `backup.py:45` proje kökünü tararken
`.pytest_tmp` altındaki `*current` bağlantılarına `stat()` atıp `WinError
1463` ile ölüyor; `backup.py:251` hatayı basmaya çalışırken cp1252
konsolunda `UnicodeEncodeError` verip hatanın kendisini yutuyor. Zamanlanmış
görev `Ready` görünüyor ama tek bir arşiv üretmedi. Yürüyüş okunamayan yolu
atlamalı ve sayısını raporlamalı; hata mesajı konsol kod sayfasından
bağımsız basılmalı.

**LEV-1 — kaldıraç ölçütü zaman dilimine bağlı (BUG).** `risk.edge_scale`
her sembolü holdout **R/gün**'üne göre boyutluyor, medyana oranın karekökü,
0,6–2,2 arası. Ama holdout penceresi zaman dilimiyle belirleniyor, çünkü bar
çekme sınırı sabit:

| TF | holdout gün (ortalama) | semboller |
|---|---:|---|
| M5 | 95,5 | JPN225, US2000, SpotBrent, XAUUSD |
| M15 | 277,7 | US500 |
| M30 | 611,9 | FRA40, GER40, NAS100, UK100, US30 |

Aynı toplam R, M5'te altı kat büyük bir R/gün üretiyor. Tavana (2,2)
dayanan iki sembolün ikisi de M5: XAUUSD ve JPN225. GER40 mutlak en iyi
üretici (638 günde +180,2 R) ama 1,43 alıyor; UK100 652 günde ölçüldüğü
için tabana (0,60) düşüyor.

Sonuç: **JPN225 etkin %1,76 risk × 2 pozisyon = özkaynağın %3,52'si**, ve
bu ağırlığı 92 günlük bir pencereden alıyor. Ölçüt edge'i değil, ölçüm
penceresinin kısalığını ödüllendiriyor.

Kaldıracı artırmadan önce bu düzelmeli: kaldıraç işaretimizi büyütür, ve
canlı işaret şu an negatif (−986 $/ay). Karar kuralı: **canlı edge'in
işareti pozitife dönmeden toplam risk artırılmaz**; artırılacaksa da
düzeltilmiş ölçütle ve tek seferde değil.

**EX-3 — sorunun adı kondu: kâğıt kendi konfiginin kazanma oranını
abartıyor.** 58 tenure / 173 işlem / 6,1 gün, 11.08 19:09 UTC sonrası.
Her tenure için canlı sonuç, **o konfigin kendi holdout'uyla** yan yana
konuldu (`opt_runs` payload'ından, yeniden koşulmadan):

| | |
|---|---|
| canlı kazanma oranı | **%30,06** (52/173) |
| aynı konfiglerin holdout'u, canlı n ile ağırlıklı | **%33,47** |
| fark | **−3,42 puan** |
| canlı < holdout olan tenure | 18 / 28 |

**DÜZELTME (17.08, aynı gece): bu fark istatistiksel olarak ayırt
edilemiyor.** n=173'te, beklenen oran %33,47 iken standart hata **3,59
puan**. Gözlenen fark 3,41 puan, yani **bir standart hatanın altında**:
z=−0,95, iki yönlü p=**0,34**, %95 güven aralığı **%23,2 – %36,9**. Bu
örneklem 3,4 puanlık bir farkı göremez. "(A) kâğıt abartıyor" bir **yön**,
bulgu değil — ve ben onu bulgu diye yazmıştım.

3,4 puanı %80 güçle ayırt etmek **~1494 işlem** ister; ölçülen canlı hızda
(28,4 işlem/gün) **~53 gün**. Ölçüm penceresi 16.08 21:34 UTC'de sıfırdan
başladı.

DEVAM §6'nın kendi başlığı ayrı bir karşılaştırma ve o daha güçlü: 626
işlemde %30,0 vs başabaş %34,2 → standart hata 1,90 puan, z=−2,22,
p=**0,027**. Yani "canlı başabaşın altında" savunulabilir; "canlı kendi
holdout'unun altında" **bu veriyle savunulamaz**.

Aşağıdaki tenure karşılaştırması yön olarak duruyor:

**Çalkantı (B) elendi denmişti — o da bu güçle elenmiş sayılmaz:**
tenure'lar kendi holdout'una yakın çıksaydı sorun konfigin yaşamaması
olurdu; çıkmıyorlar. Yaşayan konfig bile kâğıdın söylediğinden kötü
bitiriyor. Çalkantı gerçek ama açığın sebebi değil.

Uygulama kalitesi (EX-1) ve stop kayması (EX-2) bu 3,4 puanı taşımıyor.
Ödeme oranı karşılaştırması yapıldı ama $ ile R karıştığı için bulgu
sayılmadı; her tenure `n<30`, popülasyon olarak sunuldu.

**EX-4 — bar-fill varsayımı da elendi (17.08).** Kâğıt sinyal barının
ertesi barının açılışından giriyor (`open±s`); canlı sinyali bar kapanınca
görüp sonraki tick'ten giriyor. 192 canlı giriş, 11.08 21:00 – 14.08 22:25
UTC: ortalama aleyhte fark **−0,00875 R**, yani canlı fill kâğıdınkinden
hafif **daha iyi**. Aleyhte pay %47,4 — simetrik gürültü. Eşik 0,03 R'ydi;
altında ve işareti ters. Gecikme medyan 28 sn, p90 294 sn (bar sonu
kuyruğu). Giriş tarafı temiz, `backtest.py`'nin giriş varsayımı
değişmeyecek.

**Geriye çıkış tarafı kaldı (EX-5).** İki şüpheli: (1) trail kadansı —
kâğıt bar başına, canlı `poll_interval_sec` başına günceller; (2) bar içi
sıralama — kâğıt trail'i barın kendi `high`/`low`'uyla güncelleyip stop'u
aynı barda kontrol ediyorsa, koruduğu barın bilgisini kullanmış olur ve
kazanma oranını sistematik olarak abartır. Canlı ödeme oranı 1,48 (\$),
holdout ~2,75 (R) — birimler farklı ama yön aynı: **canlı kazançlar
kâğıttakinden kısa kesiliyor**, ki bu tam olarak trail davranışıdır.

**BS-3 — konfig çalkantısı.** `opt_runs`'ta 58
uygulanmış konfig var, 11.08 19:09 – 16.08 09:00 UTC arası. Medyan ömür
**12,8 saat**; %68,8'i 24 saatten kısa yaşamış; en kısası 24 dakika. XAUUSD
dört günde sekiz kez strateji değiştirdi. Holdout aylarca barda ölçülüyor,
canlı yarım günde değiştiriliyor — **ölçülen şey ile işletilen şey aynı
değil.** +640/−986 farkının en güçlü açıklaması bu.

**Mekanizma ölçüldü: fren var, elle aşılıyor.** Apply freni (`c9bd21e`,
12.08 13:34 UTC) 54 aramayı reddetti. Ama fren sonrası 46 apply'ın **40'ı
force ile geçti**, ve `auto_reopt=False` olduğu için force'un tek yolu
panel `/api/opt/run` + `body.force` — yani "zorla uygula" düğmesi.
Çalkantı bir yazılım kusuru değil, bir kullanım örüntüsü.

**Bedel ölçülemedi, n yetersiz.** 10 sembol / ~3,2 gün canlı ufuk / 39
geçiş; hepsi `n<30`. Canlı −40,46 $, kâğıtta önceki konfig (−14,20 R) yeni
konfigden (−41,02 R) daha az negatif — ama örnek ince ve canlı $ ile kâğıt
R aynı birim değil. Hipotez ayakta, kaldıraç değil. Canlı ufuk 14.08
23:50'de bitiyor: o tarihten sonra hiç işlem açılmadı, çünkü gün freni
yanlışlıkla kilitliydi (bkz. `5e18869`).

**BS-1 — ölçüldü, iki kez kapandı.** Canlı sayaçta portföy kapıları
(`max_concurrent_risk_pct`, `max_margin_usage_pct`, `max_total_positions`)
14–16.08 penceresinde **0 kez** ateşledi; ateşleyen canlı-only kapılar
`spread` (%47) ve `ai_gate` (%22). Geriye dönük "kesilen kova"nın net R'si
ölçülemedi: `entry_blocks` yalnız sayaç tutuyordu, bar kimliği yoktu
(`9b20ddd` ile eklendi, pencere 16.08 21:34 UTC'den itibaren doluyor).
Zayıf hâl de yürümedi — bugünkü konfigle kâğıt, Ağustos canlı fill'lerinin
yalnız %11'ini yeniden üretiyor. Sebebi BS-3. Aşağıdaki eski gerekçe
tarihsel kayıt olarak duruyor:

**BS-1 (özgün gerekçe).** `risk.py` portföy kapıları canlıda var,
`backtest.py`'de yok: `max_concurrent_risk_pct`, `max_margin_usage_pct`,
`max_total_positions`, günlük halt, `block_high_cost`, `_symbol_daily_halt`,
supervisor kısıtları. Backtest her sembolü tekil vakumda koşuyor, yani kâğıt
canlının hiç alamadığı işlemleri alıyor. Ölç: aynı dönemde kâğıt kaç işlem
üretti, canlı kaç aldı, sembol başına. Kesilen işlemlerin kâğıttaki net R'si
pozitif mi negatif mi? Holdout +640 ile canlı −986 arasındaki **1600 $/ay**
buradan çıkabilir.

**BS-2 — onarıldı, ama etkisi ölçülmedi.** Asimetri `a5562e9` içinde
kapandı (16.08 18:13): short giriş artık `open-s`, stop ham `high`; long
zaten `open+s` / ham `low`. İki bacak spread'i aynı yerde — girişte —
ödüyor, stop ham bardan okunuyor. Kanıt
`tests/test_short_fill_pays_spread_on_entry.py`. Commit mesajı saat
sapmasından bahsettiği için düzeltme gömülü kaldı ve bu liste dört saat
boyunca yanlış bilgi taşıdı.

**Ölçülmeyen kısım duruyor:** onarım *arama sonucunu* büktü mü? Eski
simülatörle koşulmuş aramalar short ağırlıklı konfigleri haksız
ödüllendiriyordu; aynı arama uzayında onarım öncesi/sonrası hangi aile/TF
kazanıyor, karşılaştırılmadı. Net R farkından daha önemli olan bu.

**BS-2b — holdout beraberlik sızıntısı.** `optimizer.py` aile/TF
beraberliğinde holdout işlem sayısına bakıyor. Küçük ama holdout'a dokunuyor;
beraberliği validation ve deterministik ad sırasıyla çöz.

**BT — evren taraması. Ön eleme yapıldı, hipotezin yarısı çürüdü.**

Broker'da 1729 sembol. Grup dağılımı ilk kez ölçüldü: hisse 1496, forex 95,
kripto 53, emtia 40, endeks 38, other 7. `trade_mode==full` → 1610.
Maliyet kapısı (spread / H1 ATR14, eşik = kitabın en pahalısı FRA40 0,0897)
→ 1040. Min lot 1R > 3×%0,8×bakiye veya marj > %45 → 1034. Seans
örtüşmesi kimseyi elemedi.

**Kalan 1034: forex 28, endeks 8, emtia 13, kripto 0, hisse 985.**

- **"Tavan düşük çünkü üst sıradaki endeksler kitapta yok" — YANLIŞ.**
  Maliyet kapısını geçen 8 endeksin **tamamı zaten kitapta**. AUS200, HK50,
  EUSTX50, SPA35, VIX, USDX, CN50, US400 ve diğerleri kitabın en pahalı
  üyesinden pahalı. Kitap, ucuz-yeterli endeks setinin kendisi.
- **Kripto ölçümle de bitti:** 52 uygun isimden maliyet kapısını geçen 0.
  DEVAM §4 ile aynı yön, artık sayısı da var.
- **Açık kalan:** forex 28 (majors 6, çapraz 16, minor 6) ve emtia 13
  (`SpotCrude`, `XAGUSD`, XAU/XAG çaprazları). İkisi de hiç taranmadı.
- **Hisse 985 sürpriz:** "bu hesapta marj/seans uygun değil" varsayımı üç
  kapıda da tutmadı — min lot 1R çoğu US hissesinde birkaç dolar, marj %45'i
  geçmiyor, seans örtüşüyor. Kenar ölçülmedi. İçinde ~53 tarihli `*.US-24`
  CFD çöp isim var.

**FX kapandı — ölçüldü, kitabı geçmiyor.** 21 FX ismi M5/M15/M30'da
tarandı, 11'i `n>=30`. En iyi yeterli isim **AUDJPY M30 calmar 1,96**;
kitabın dördüncüsü US30 2,35, en iyisi GER40 3,72. Yani FX'in en iyisi
kitabın ilk dördüne giremiyor. `n<30` olan CHFJPY (3,99) ve GBPUSD (2,42)
bulgu sayılmaz. DEVAM §4 "FX'te M5 pahalı" diyordu; **M15/M30 de ölçüldü,
aynı sonuç.** FX yeniden önerilmez.

**Tarama durduruldu (17.08, operatör kararı).** Gerekçe: efor, açıklanmamış
canlı/kâğıt farkını kapatmaya gitsin. Kitap 10 sembolde kalıyor. Karar
mantıklı — açıklayamadığın bir sistemi 49 yeni sembole yaymak, açıklanmamış
sorunu çoğaltmaktır (DEVAM §5'in tamamı bu sınıf).

**Kaybolmasın diye: hisse sürtünme ekonomisi ölçüldü ve çarpıcı.**
Hareket/maliyet (H1 ATR ÷ spread): kitap medyanı **21,5**, kitabın en iyisi
XAUUSD 83,4. Üst hisseler TSLA.US **456,6**, MU.US 399,8, MSFT.US 290,8.
ATR% olarak kitap medyanı %0,20, üst hisseler %1,3–1,9. Yani **8–21 kat**
daha iyi sürtünme, **6–9 kat** daha çok hareket. Bu *kenar değil*,
sürtünme ekonomisi — kenar hiç ölçülmedi (boşluk riski, bilanço günleri,
tek isim riski de ölçülmedi). Seçilmiş 49 isimlik liste
`claude/_bt2_shortlist.json`'da hazır bekliyor, ~3 saat. Canlı/kâğıt farkı
açıklandıktan **sonra** yeniden değerlendirilecek.

Bütçe kaydı: kalan 1034 × 36 sweep × 6 sn = 62 saat; hisse hariç 49 isim
2,9 saat. Sıralama `calmar`. Betikler `cursor/_bt0_measure.py`,
`cursor/_bt1_scan.py`, `claude/_bt2_select.py`; çıktılar
`cursor/_bt0_result.json`, `cursor/_bt1_result.json`.
Hipotez: **tavan düşük çünkü üst sıradaki semboller kitapta yok.** FX'i
atlama — "FX'te M5 pahalı" ölçüldü ve doğru, ama M15/M30 FX hiç ölçülmedi.

**httpx uyarısı (acil değil).** Suite şu uyarıyı veriyor: *"Using httpx with
starlette.testclient is deprecated; install httpx2 instead."* Bugün zararsız
ama bir sürüm yükseltmesinde `TestClient` kullanan her test kırılır —
`tests/conftest.py` onu sarmalıyor, yani tek noktadan çözülebilir. Kırılmadan
önce ele alınsın; kırıldıktan sonra bakılırsa suite tamamen durur.

**Sıraya bağımlı test.** `test_the_new_bar_trigger_uses_the_brokers_clock.py::
test_the_day_boundary_still_uses_the_naive_encoding` tam suite'te bir kez
kırıldı, izole geçiyor. Global durum sızıyor; kaynağı bulunmalı.

**Ruff borcu.** `run.py` E402 x9 (import'lar sürüm kontrolünün altında,
bilerek) ve `backup.py:285-286` F541. İkisi de kasıtlı — `per-file-ignores`'a
gerekçesiyle yazılmalı ki ruff yeniden "temiz = yeşil" olsun.

---

## 8. Yedekleme politikası — iki ayrı kanal

İki farklı şey yedekleniyor ve **aynı yere gitmiyorlar**. Karıştırma:

**Sistem → GitHub.** Kod, testler, `DEVAM.md`. Her değişiklikten sonra
commit + push. `.gitignore` `data/*.db`'yi bilerek dışarıda tutuyor: bu depo
sistemdir, hesap değildir. Klonlayan biri temiz bir kurulum almalı, bizim
bakiyemizi değil. Bu kural değişmez.

**Hesap → C:\MicoFX_Yedek → Google Drive.** Kitap (`data/micofx.db`),
loglar, `cursor/_bp.json`, `cursor/_universe_live01.json`. Bunlar git'in
getirmediği tek nüsha dosyalar; makine giderse gider. `backup.py` bunları
`C:\MicoFX_Yedek`'e yazar, Drive oradan senkronlar.

`backup_dir_secondary` boş bırakıldı. Eskiden `D:/MicoFX_Yedek`'ti; bu
makinede `D:` bir **DVD sürücüsü** (DriveType 5), yani ölü hedef. Drive
masaüstü istemcisi kurulunca ikincil hedef onun klasörü olur — mekanizma
zaten var, sadece yolu doğru olmalı.

Drive'a yükleme sohbet üzerinden yapılmaz: 1,2 MB'lık kitap sıkışınca 139 KB,
base64'e çevrilince 186 KB tutuyor ve her yedekte bunu bağlamdan geçirmek
sürdürülebilir değil. Senkron istemcinin işi.

---

## 9. Operatör tercihleri

Türkçe konuş, kısa yaz. Commit mesajları, kod yorumları ve test docstring'leri
İngilizce kalır. Her değişiklikten sonra commit + push — sormaya gerek yok.
Ajan cevap verdi denince dosyayı sormadan aç. Sembol elemeden önce
düzeltme sonrası veri bekle. `engine`/`optimizer`/`app` değişince canlı süreç
eski kodda kalır — restart gerekir.
