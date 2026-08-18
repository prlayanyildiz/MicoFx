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

**Tek saat referansı: SUNUCU.** Makine saatine geçilmeyecek. Sebep ölçüldü:
sunucu ABD DST'siyle birlikte kayıyor (ABD nakit açılışı beş yıl boyunca
her ay 16:30 sunucu), makine ise Türkiye — 2016'dan beri sabit UTC+3.
Bugün ikisi eşit (UTC+3), **1 Kasım 2026'dan itibaren bir saat ayrışıyor**.
Makine saatine geçmek üçüncü bir saat eklemek olur.

Motor zaten doğru: bar damgasını sunucunun kendi çerçevesinde okuyup aynı
çerçevede tanımlı seans penceresiyle karşılaştırıyor, iki taraf birlikte
kaydığı için DST'ye dayanıklı. Kırılgan olan **analiz betikleri**:
`datetime.fromtimestamp` makinenin offsetini ekler ve sessizce üç saat
kaydırır. 18.08'de bu hata iki kez yapıldı — biri operatörün mobil ekranıyla
yakalandı, biri "onarım sonrası zarardayız" diye yanlış bir sonuç üretti
(doğrusu +63,94 $ kârdı).

**Kasım'da tek sembol etkilenecek: GER40.** Günün ilk barı sunucu
çerçevesinde Kasım–Şubat arası **02:00**, Mart–Ekim arası **03:00** —
Avrupa borsası Avrupa DST'sini, sunucu ABD'ninkini izlediği için. Diğer beş
sembol yıl boyunca sabit (JPN225/NAS100/US30/XAUUSD 01:00, SpotBrent 03:00).

**GER40 seansı 03:15–22:59 kalıyor** — 18.08'de kısa süre 02:00'ye açıldı ve
aynı gün geri alındı. Gerekçesi burada, çünkü iki kez yanlış yapıldı:

1. *Yanlış ölçüm.* Seansı açarken buraya bir spread tablosu yazılmıştı —
   "yazın 02:00 barının maliyeti kapının 4,4 katı, kapı kendisi eliyor".
   **O tablo yanlıştı.** Aynı feed sayıldığında GER40'ın yaz aylarında
   02:00 ve 02:30 barı **hiç yok** (kış 160 bar, yaz 0). Var olmayan barın
   maliyeti ölçülemez. Kışın o dilim kapıyı zaten geçiyor (%96,7, medyan
   spread/ATR 0,053) — yani "kapı mevsimi kendi ayarlıyor" hikâyesinin iki
   yarısı da gerçek değildi.
2. *Damga eşleşmesi.* Asıl kural bu. GER40'ın damgası (17.08 22:22) seansı
   03:15 iken ölçüldü; seans 18.08 17:24'te elle 02:00 yapıldı. O andan
   itibaren canlı, **damganın ölçmediği bir konfig** koşuyordu — bu oturumun
   bütün soruşturmasının üzerine yığıldığı arıza sınıfının ta kendisi. Damga
   hem boyutlandırmayı hem denetçinin eşiklerini besliyor.

Ölçüm ne diyor: kış replay'inde (Kas 2025 – Şub 2026, 116,85 gün) geniş seans
+60,73 R / calmar 2,04, eski seans +47,95 R / calmar 1,81. Ama erken kova
**n=20, +0,095 R, SE 0,305** — sıfırdan ayırt edilemiyor. Farkın çoğu erken
barların kazanması değil, `max_positions=2` altında **sonraki 31 işlemi
yerinden etmesi** (o 31 işlem −10,88 R idi). Erken kova (0,095) ile geri
kalan (0,303) arasındaki fark da ayırt edilemez (farkın SE'si 0,34). Yani
veri iki yöne de kural taşımıyor; taşımadığında ölçülmüş konfige dönülür.

**Kasım'da yapılacak bir şey yok.** Kışın ilk 75 dakikayı kaçırmak, kazancı
gösterilmemiş bir dilimi kaçırmaktır. 02:00 istenirse elle seans düzenlemesiyle
değil, aramanın kendisiyle gelmeli — ve yeni damgasıyla.

Diğer beş sembolün pencereleri zaten yıl boyu doğru (seans başları sunucu
çerçevesinde sabit).

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

### Ölçüm için bir şeyi değiştirdiysen, değiştiğini doğrula

18.08: D1b'nin tohum tekrarı, `combos_from_grid`'in tohumunu ana süreçte
monkeypatch ile değiştirdi. Arama `ProcessPoolExecutor` ile **alt süreçlerde**
koşuyor (`optimizer.py:774`); yama pickle sınırını geçmez. Altı hücre de
varsayılan tohumla çekti ve "tohum gürültüsü" diye okunan fark aslında bar
penceresinin bir M30 kaymasıydı.

Kural: **manipülasyonun ölçülen şeye ulaştığını ölçümden önce kanıtla.**
En ucuzu, manipülasyonun gözlenebilir bir izini kontrol etmek (farklı tohum →
farklı örneklem). Bu doğrulanmadan üretilen sayı, ölçtüğünü sandığın şeyi
ölçmüyor olabilir.

Süreç sınırını geçmesi gereken her şey **veri** olarak geçmeli
(`combo_seed` artık iş sözlüğünde ve damgada, `762547e`), yama olarak değil.

---

## 3. Ortam (yeni makine, 16.08.2026)

| ne | nerede |
|---|---|
| proje | `C:\Users\Administrator\MicoFx` |
| sanal ortam | `C:\MicoFX-venv` — **proje dışında, bilerek**. `python`/`pytest` PATH'te değil |
| test/ruff | `C:\MicoFX-venv\Scripts\python.exe -m pytest -q` ve `... -m ruff check .` |
| panel portu | 8900 (`MICO_PORT` ile değişir) |
| MT5 | `C:\Program Files\Pepperstone MetaTrader 5\terminal64.exe` |
| **botu başlat** | `C:\MicoFX-venv\Scripts\pythonw.exe run.py` (cwd = proje) |

**Botu `C:\Program Files\Python312` ile başlatmayın.** O yorumlayıcıda
`uvicorn`/`fastapi` yok; `pythonw` ile başlatılınca hata da görünmez, süreç
sessizce ölür. 18.08'de seans düzeltmesi için bot durdurulup yanlış
yorumlayıcıyla başlatıldı ve **üç açık pozisyon birkaç dakika takipsiz
kaldı** (stoplar broker'da duruyordu, ilerlemiyordu). Durdurup başlattıktan
sonra **her zaman portu doğrula**: dinleyen PID yoksa bot ayakta değildir.


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

**Min lot marj şişmesi artık "yok" değil.** O ölçüm ~1,00x demişti; 17.08'de
XAUUSD **1,31x** — minimum lotta bile hedeflenen riskin %131'ini taşıyor ve
aşağı inemiyor. Kat, bakiye düştükçe büyüyor (2.113 → 2.019 $ arasında 1,13
→ 1,31). Kitabın geri kalanı 0,06–0,42 aralığında, yani sorun XAUUSD'ye
özgü. `lot_multiplier` artırılırsa XAUUSD zaten aşırı riskli taraftan daha
da büyür — o gün ayrı ele alınacak.

**Supervisor eşikleri gürültüyle ateşliyordu (HR-2/3, 18.08).** Kodda
yalnız `edge_decay_min_trades` doğrulanmıştı (20.000 MC, 20 işlemde %12–17
yanlış alarm → 100'e çıkarılmış). Aynı test diğerlerine uygulandı; kenarı
**hiç değişmeyen** sembolde yanlış ateşleme oranları:

| eşik | eski bar | yanlış alarm | yeni bar |
|---|---:|---|---:|
| `bad_hour_min_trades` | 12 | %12,8–**39,6** (XAUUSD) | **80** |
| `min_trades` (quarantine_pf) | 25 | %0,9–**23,6** (US30) | **80** |
| `watch_min_trades` | 25 | %2,4–**38,6** (XAUUSD) | **80** |
| `quarantine_losses` | 10 | %5,95 (XAUUSD) | **11** (→%4,4) |

Tavanlar (`quarantine_pf 0,80`, `watch_pf 1,00`) **değişmedi** — 0,40'a
çekmek kuralı körleştirir. Kanıt barı yükseltildi, kural değil.

`watch_pf=1,00` bu kitapta %5'e kalibre **edilemiyor**: XAUUSD'nin gerçek
PF'si 1,13, n=120'de bile örneklem PF'sinin 1'in altına düşme olasılığı
üçte bir. Yumuşak ipucu olarak bırakıldı (yalnız 0,6× ölçekler, blok değil).

**Ve bir kural yanlış kurulmuş: damning-count.** `wins < n/2 − √n` null'ı
**yazı-tura %50** varsayıyor; bu kitabın kazanma oranı %25–37 ve parayı
ödeme oranından kazanıyor. Sağlıklı sembolde n=11'de ateşleme: XAUUSD
**%46,4**, GER40 **%38,3**. Eşik ayarı değil, yanlış hipotez — sembolün
kendi holdout kazanma oranına bağlanacak (SUP-1).

**Sığ saat hipotezi (HR-1) — yarısı duruyor, bağlanmadı.** Sığ 08–10 vs
nakit 16–22 (sunucu): trail'e ulaşma **+8,9 puan (z=2,40)**, stop olma
+1,5 puan (z=0,31), mean R ayırt edilemez. 15 puanlık stop farkını %80
güçle görmek kova başı n≈174 ister; sığ kovada 161 var. "Göremedik" ile
"yok" ayrı şeyler.

**Drawdown ölçekleyici parayı yiyordu (DD-1/DD-2, 18.08).** `dd_soft=1,5`
6 sembollük kitapta 92 günlük kâğıtta **67 günün 50'sinde** lot kesiyordu
(%75), bunların **34'ü günü −%1,5'in üstünde bitiriyordu**. Izgara (soft ×
hard × floor, aynı 6 konfig, aynı pencere):

| soft/hard/floor | kesilen | gereksiz | tam yol neti | 10.07 en kötü gün |
|---|---:|---:|---:|---:|
| **1,5 / 3 / 0,4** (eski) | 50 | 34 | **−1.248 $** | −8,89 → −5,22% |
| 2,5 / 5 / 0,6 | 32 | 21 | −366 $ | −7,06% |
| **3,5 / 7 / 0,6** (yeni) | 23 | 15 | **−123 $** | −7,69% |
| 5,0 / 7 / 0,6 | 8 | 5 | −52 $ | −7,95% |
| 5,0 / 5 (kesme yok) | 0 | 0 | 0 $ | −8,89% |

Eski ayar gridin **en pahalısıydı**: 1.248 $ ödeyip en kötü günü 3,67 puan
yumuşatıyordu. Yeni ayar aynı korumanın çoğunu **onda bir fiyata** veriyor.

Tamamen kapatmadım (5/5 = 0 maliyet) çünkü kuyruk riski gerçek; ölçekleyici
kötü günü hâlâ 1,2 puan yumuşatıyor ve merdiven tutarlı kalıyor:
**ölçekleyici %3,5 → %7 (taban ×0,6), günlük fren %22.**

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

**Korelasyon için pozisyon bölmek** — ölçüldü, takas kötü. Kitabın M30
korelasyon matrisi (son 90 gün, 1777 ortak bar): hisse endeksleri arası
ortalama **0,66**, ama üç çift pratikte tek pozisyon — **NAS100–US500 0,92**,
GER40–FRA40 0,83, JPN225–NAS100 0,82. XAUUSD hisselerle **0,46** (altın bu
pencerede güvenli liman değil), **SpotBrent −0,37** — kitabın tek gerçek
çeşitlendiricisi.

2 birimi 1+1 bölmenin iğne/spike koruması gerçek ama küçük: NAS100+US500'de
**%2,1**, GER40+FRA40'ta %4,3 daha az dalgalanma. Bedeli ise yarım
pozisyonun pahalı ikize kayması — işlem başına **%93** ve **%162** daha
fazla sürtünme. Bölme yapılmayacak.

**Kapı zaten muhafazakâr, düzeltme:** `risk.py:666` `concurrent_risk`
riskleri **topluyor** (ρ=1 varsayımı), bağımsız saymıyor. "Kapılar
korelasyon bilmiyor, riski olduğundan az görüyor" cümlesi yanlıştı.

Korelasyonun kattığı şey yeni bir kapı değil, **bağımsız ikinci kanıt**:
FRA40 (calmar 0,44, GER40'tan 4,2 kat pahalı, ρ 0,83) ve US500 (calmar
0,54, NAS100'den 2,9 kat pahalı, ρ 0,92) daha iyi bir enstrümanın pahalı
ikizi. Yerlerini kendi calmar'larıyla hak etmeliler.

**Broker'ın diğer endeksleri** — 17.08'de canlı fiyatla, üç zaman diliminde,
tek tek ölçüldü. Kitabın M30 spread/ATR aralığı 0,019 (GER40) – 0,084
(FRA40). Kitapta olmayan **en ucuz aday HK50 0,122** — kitabın en
pahalısından %45, GER40'tan 6,4 kat pahalı. Sonrası: NETH25 0,140, AUS200
0,141, TWN 0,159, EUSTX50 0,165, SWI20 0,200, CA60 0,246, SPA35 0,250,
SCI25 0,434, CN50 0,445, HSTECH 0,604, US400 0,757, CHINAH 0,769. En oynak
adaylar (TWN, HSTECH %0,22) JPN225'i geçmiyor ve maliyetleri kat kat fazla.
**Bu broker'da işlem edilebilir endeks seti kitabın kendisi** — aynı sonuç
iki ayrı yöntemle ölçüldü.

**XAGUSD** — marj değil, spread eliyor. M5 spread/ATR **0,495** (ATR'nin
yarısı spread'e gidiyor), M30 0,147; XAUUSD sırasıyla 0,022 ve 0,011, yani
**13–22 kat** pahalı. Min lot marjı 163,24 $ (özkaynağın %8'i) teknik olarak
sığıyor ama aynı marjı GER40'a koymak açık ara iyi takas.

**SpotCrude, SpotBrent'ten ucuz** (M5 0,102 vs 0,125, M30 0,041 vs 0,053,
ATR%% 0,700 vs 0,666, marj 2,08 vs 0,90 $) — ama ikisi de ham petrol.
Eklemek çeşitlendirme değil aynı pozisyonu iki kez almak; portföy kapıları
korelasyon bilmiyor. **Ekleme değil, değiştirme sorusu:** SpotBrent bir
sonraki aramaya girdiğinde SpotCrude aynı arama uzayına konsun.

**Flip ailelerine ADX/body kapısı bağlamak** — sezginin tersi çıktı. GER40'ta
engellenecek kova +20.1R, geçen kova −7.5R. Bağlamak parayı atardı.

---

## 4b. Arama bütçesi ailelere eşit dağılmıyor (18.08)

`combos_from_grid`: ızgara `max_combos`'tan küçükse tam ürün, büyükse
**tekdüze rastgele örnek** (seed 7); ardından top-12 tohumdan ±1 komşu ile
`refine_rounds` tur. Bütçe her aileye aynı (`max_combos=2000`), ızgaralar
aynı değil:

| aile | eksen | ızgara | kapsam |
|---|---:|---:|---:|
| aroon_flip | 5 | 2.880 | %69,4 |
| parabolic_flip / wavetrend_flip | 6 | 8.640 | %23,1 |
| stoch_flip | 7 | 28.800 | %6,9 |
| macd_flip | 7 | 46.080 | %4,3 |
| st_trend | 7 | 57.600 | %3,5 |
| t3_flip | 7 | 144.000 | %1,4 |
| mtf_pullback | 10 | 622.080 | %0,32 |
| burst | 10 | 1.244.160 | %0,16 |
| micro_rev | 10 | 1.555.200 | %0,13 |
| dual_t3 | 10 | 2.073.600 | %0,096 |
| **t3_stoch** | **16** | **1.433.272.320** | **%0,00014** |

**Yarım milyon kat.** Aileyi seçen şey doğrulama skoru olduğu için,
karşılaştırma ızgara boyutuyla karışmış durumda. İki zıt yanlılık aynı anda
çalışıyor: büyük ızgara daha çok aşırı-uyum fırsatı verir (skor şişer), ama
aynı zamanda aile kendi optimumundan uzak kalır (hak ettiğinden düşük
görünür). Hangisi baskın **ölçülmedi** — DEEP-1'in yeni şekli bu.

Kitabın hâli (n=6, **kanıt değil**): GER40 %6,94 kapsam / 3,38 retention ile
en tepede; US30 `t3_stoch` %0,00014 kapsamla en altta — o konfig 700.000'de
bir örneklemin en iyisi, yapısı gereği kitaptaki en az aranmış ayar.

16 boyutta 2000 rastgele nokta arasında komşuluk yoktur; büyük ailelerde
`MIN_PLATEAU_NEIGHBOURS=3` şartını yalnız refine turlarının ürettiği noktalar
sağlıyor, yani plato kontrolü tohumun etrafındaki birkaç adımdan ibaret.

**Ölü eksen bütçe yemiyor** — bunu ben hipotez olarak yazdım, ölçüldü,
`combos_saved=0`. `searchable_axes` aramadan önce zaten buduyor.

---

## 4c. Arama tek pozisyon ölçtü, kitap iki tuttu (18.08) — SORUŞTURMA YENİDEN AÇILDI

`backtest.simulate` imzası `max_open: int = 1`. Dört çağrı yerinin hiçbiri
onu geçmiyor; `optimizer.py`'de `max_open` kelimesi **hiç geçmiyor**. Kitaptaki
altı sembol ise `max_positions=2` ile koşuyordu.

Yani **her damga, koşturduğumuzdan farklı bir portföy süreciyle ölçüldü** —
tek sembolde değil, hepsinde ve baştan beri.

**Teorik değil.** Canlı deal'lerden occupancy (3–15.08, kitap sihriyle
eşleşen 341 pozisyon, 207 ikinci-slot fill):

| sembol | 2. slot fill | açık zamanın %'si ≥2 pozisyon |
|---|---:|---:|
| GER40 | 33 | **92,0** |
| XAUUSD | 48 | 64,1 |
| JPN225 | 32 | 60,3 |
| SpotBrent | 28 | 59,4 |
| US30 | 26 | 57,5 |
| NAS100 | 40 | 29,0 |

Medyan **%59,8**. GER40 açıkken neredeyse sürekli iki pozisyonda.

### Aynı konfig, aynı pencere, tek fark `max_open`

| sembol | n (1→2) | net_r (1→2) | max_dd_r (1→2) | calmar (1→2) | oran |
|---|---|---|---|---|---:|
| GER40 | 1247→2679 | +177,8→+248,4 | 44,9→81,7 | 3,96→3,04 | 0,77 |
| JPN225 | 314→433 | +67,1→+56,2 | 16,9→16,4 | 3,98→3,43 | 0,86 |
| NAS100 | 1041→1550 | +106,8→+115,4 | 47,2→85,5 | 2,26→1,35 | 0,60 |
| US30 | 404→488 | +46,2→+39,9 | 22,8→47,6 | 2,03→0,84 | **0,41** |
| SpotBrent | 119→137 | +21,6→+24,8 | 5,0→3,8 | 4,30→6,60 | **1,53** |
| XAUUSD | 506→655 | +86,3→+69,6 | 43,6→55,7 | 1,98→1,25 | 0,63 |

Net R her yerde düşmüyor; **düşüş kalitesi değil derinliği**: n artıyor, DD
daha hızlı artıyor. Boyutlandırma calmar'a bağlı olduğu için önemli olan bu.

### Neden soruşturma yeniden açıldı

Son 92 günün ortak penceresinde GER40: `max_open=1` **n=185 net +27,82 R**
calmar 1,91 → `max_open=2` **n=410 net −8,95 R** calmar −0,31. **İşaret
değişiyor.**

TF-2'nin "aynı konfig, aynı pencere → kâğıt +189,3 R, canlı −29,4 R, fark
−218,7 R" tablosu **kâğıt tarafını max_open=1 ile** koştu, canlı 2'deydi. Yani
bütün oturum boyunca elemeyle daralttığımız o fark, **yapısal olarak eşleşmeyen
iki süreci** karşılaştırıyordu. "Tek kalan açıklama çalkantı" hükmü erkendi;
çalkantı artık **tek aday değil, ikinci aday**.

MATCH-1 hâlâ geçerli ve mekanizmayı da açıklıyor: eşleşen işlemlerde ΔR≈0
(ikisi de aynı işlemi aldığında sonuç aynı). Fark eşleşen işlemlerde değil,
**canlının kâğıdın hiç almadığı işlemleri alması**nda — FWD-1'in %150 take
rate'i tam olarak bu. `max_open=1`'de açık pozisyon sonraki sinyalleri bloke
eder, 2'de etmez, ve marjinal işlemler ortalamayı aşağı çeker.

### Karar: kitap 1'e indi (18.08 18:36)

Altı sembolde `max_positions` 2 → **1**. İki yön vardı:

* aramayı `max_open=cfg.max_positions` yapmak → **bütün damgalar geçersiz**,
  altı sembol yeniden aranır;
* kitabı 1'e indirmek → **canlı, ölçülmüş olana eşitlenir**, yeniden arama yok.

İkincisi seçildi. Aynı gün GER40 seansı için verilen kuralın aynısı: veri
kural taşımıyorsa ölçülmüş konfige dönülür. SpotBrent 2'de daha iyi (calmar
6,60 vs 4,30) ama bu tek sembolün tek gözlemi ve kendi damgası yok; istenirse
`max_open=2` ile **aranıp kendi damgasıyla** gelir.

Damgaların ayrıca ikinci bir iyimserlik katmanı var: GER40 damga calmar 5,30,
aynı konfigin max_open=1 replay'i 3,96 (DD 34 vs 45). Bu ayrı iş.

---

## 4d. `max_open` boşluğun beşte birini açıkladı, gerisi tek mekanizma değil (18.08)

TF-2 penceresi (92 gün), kâğıt tarafı `max_open=2` ile yeniden koşuldu:

| | R | n |
|---|---:|---:|
| kâğıt max_open=1 | +184,7 | 1032 |
| kâğıt max_open=2 | +139,8 | 1531 |
| canlı | −29,5 | 393 |

Kapanan **44,9 R = boşluğun %21'i**. Kalan −169 R. Sembol kırılımı, toplamdan
çok daha bilgilendirici:

| sembol | boşluk (max_open=1) | boşluk (max_open=2) | kapanan |
|---|---:|---:|---:|
| GER40 | −40,5 | **−3,0** | 37,5 |
| JPN225 | −57,5 | −47,5 | 10,0 |
| XAUUSD | −48,4 | −42,4 | 5,9 |
| US30 | −11,8 | −8,8 | 2,9 |
| SpotBrent | −20,8 | −23,2 | −2,4 (açıldı) |
| NAS100 | −35,3 | −44,3 | −9,0 (açıldı) |

**GER40'ın bütün farkı `max_open`'mış.** NAS100 ve SpotBrent'te ters yön:
`max_open=2` kâğıdı iyileştiriyor, yani canlı ikinci pozisyondan kazanç
bırakıyordu. JPN225 ve XAUUSD kıpırdamadı. **Tek açıklama aramak yanlış** —
farklı sembollerde farklı mekanizma.

**Damga iyimserliği sistematik değil** (MAXOPEN-3): damga/replay calmar oranı
GER40 1,34, diğer beşi 0,88–1,01. Kitap geneli bir boyutlandırma hatası yok;
bu ip kesildi.

### Canlı giriş hunisi — ilk doğrudan ölçüm

`entry_blocks` sayaçları, 16.08 21:34'ten beri (kitap sabit dönem), 104 sinyal:

| neden | sinyal | pay |
|---|---:|---:|
| risk_sembol_limiti | 42 | **%40,4** |
| açıldı | 34 | %32,7 |
| emir_hatasi | 12 | %11,5 |
| spread | 9 | %8,7 |
| risk_ters_yon | 5 | %4,8 |
| lot | 2 | %1,9 |

`emir_hatasi` **tarihî**: son `emir reddedildi` 17.08 11:20, onarım 13:29,
sonrasında sıfır. Sayaç böceğin kalıntısını taşıyor.

### 92 günlük sayı karşılaştırması çürük, kovalanmayacak

Canlı 393, kâğıt1 1032 (%38) — canlı o pencerede `max_positions=2` ile daha
gevşek olmasına rağmen **daha az** işlem aldı. Sebep: o 92 günde canlı bu
konfigleri tutmuyordu (çalkantı). Yani take rate farkı çalkantıyla karışmış
ve o pencereden temizlenemez. **Bu tabloyu kovalamayı bırakıyoruz.**

Yerine FWD-2: 16.08 21:34'ten itibaren kitap sabit, `max_positions=1`, arama
`max_open=1` — **ilk defa canlı ile kâğıt aynı süreci koşuyor**. Pencere her
gün büyüyor. Bugünkü hâli zayıf ama temiz; 92 günlük tablo güçlü ama kirli.

---

## 4e. MT5 ekonomik takvimi bu makinede alınamıyor (18.08) — KAPALI YOL

MT5'in takvimi yalnız MQL5'ten okunuyor (`CalendarValueHistory`); Python
paketinde (`MetaTrader5 5.0.6090`) karşılığı **yok**. Köprü kuruldu
(`mql5/MicoTakvimDisaAktar.mq5`, `KUR.ps1` adım 7 derliyor,
`claude/_takvim_oku.py` okuyor) ve **veri gelmedi**.

Kanıt:

| ne | sonuç |
|---|---|
| `config/common.ini` → `NewsEnable` | **1** (açık) |
| `config/terminal.ini` → `[CalendarList]` | **boş** |
| `CalendarValueHistory` her pencerede | **5401** (zaman aşımı) |
| `CalendarCountries` | çağrı **asılı kalıyor**, dönmüyor |
| terminal log'unda takvim/haber senkronu | **tek satır yok** |

900 günü tek çağrıda istemek de, 45 ve 30 günlük parçalara bölmek de aynı
sonucu verdi. Yani sorun sorgu genişliği değil.

**Ağ engeli de değil** — makineden 443 ile denendi: `mql5.com` 99 ms,
`forge.mql5.io` 135 ms, broker 120 ms, hepsi açık. "MetaQuotes altyapısı
bloke" hipotezi ölçüldü ve öldü.

Geriye kalan tek makul açıklama: **broker takvimi dağıtmıyor.** MT5 takvimi
ticaret sunucusu bağlantısı üzerinden gelir; broker kapattığında terminalde
`[CalendarList]` boş kalır ve çağrılar zaman aşımına düşer — gözlenen tablonun
tamamı bu. Bizim tarafımızdan çözülecek bir şey yok.

**Tekrar denemeyin** — betikler repoda duruyor ve yeni bir makinede
kendiliğinden derleniyor; orada besleme varsa çalışır. Bu makinede yok.

NEWS-1 ön kaydı (T∈{15,30,60}, önem=3, n_iç≥50, içeride mean R<0 ve
fark>2 SE) **yazıldığı gibi duruyor**; veri gelirse ölçüm hazır, karar kuralı
kilitli.

---

## 4f. Yapılandırılmış ama çalıştırılmayan denetleyici (18.08)

`pyproject.toml`'da `[tool.mypy]` var. **Onu koşturan hiçbir şey yok** —
`KUR.ps1` 8. adımda ruff çağrılıyor, mypy çağrılmıyor; CI yok; testte yok.
Kayda "28 bulgu, baseline" diye geçmiş sayı hiç uygulanmadı ve sessizce
**57**'ye çıktı.

Bu, §5'in birinci arıza sınıfının araç versiyonu: panelde/dosyada duran ama
etkisi olmayan ayar. Operatöre "tip kontrolü var" diye görünüyor.

**57'nin tamamı daralma körlüğü; gerçek hata yok.** Üç küme tek tek izlendi:

| yer | n | hüküm |
|---|---:|---|
| `optimizer.py:1562-1627` | 21 | `_apply_stamp_missing` `detail=None`'ı reddediyor, `apply` erken dönüyor | 
| `web/app.py:1764-1768` | 4 | 1753'teki `if guarded and current is None: continue` sonraki kullanımları güvenli kılıyor |
| `web/app.py:2167/2221/2223` | 3 | `rejected` ara değişkeni; mypy takip edemiyor |
| `web/app.py:56/909/1850` | 5 | pydantic dinamik model üretimi |
| `web/app.py:1467` | 2 | gerçek eksik anotasyon, zararsız |

Yani araç şu an **sıfır hata bulup 57 satır gürültü üretiyor**, ki bu bir daha
bakılmayacak araç demektir. Gürültüyü `# type: ignore` ile bastırmak yanlış
yön; daralmayı koda görünür kılmak gerekiyor (AUDIT-E1).

---

## 4g. Zararlı işlemlere tersten bakış (18.08) — yön filtresi ölü, kâr kuyrukta

30 gün, 375 işlem (126 kazanan / 247 kaybeden). `claude/_loss1_anatomy.py`.

**Döngüsellik uyarısı.** Zaten kaybettiği bilinen işlemleri tersine çevirmek
her zaman kârlı görünür — sonuca göre seçimdir. Aynı şekilde **çıkış şekli**,
**tutma süresi** ve **kaybedenlerin MFE'si** sonuca koşulludur: stopla
kapanan işlem tanımı gereği kaybetmiştir. Bu kesitler "sorun burada" demez,
"kaybedenler kaybetti" der.

**Girişte bilinen tek kesit — sembol × yön — sonuç vermedi.** Ham tablo
çarpıcıydı (NAS100 BUY −139,77 net, SpotBrent BUY −100,59) ama hata payıyla:

| kesit | n | ort $ | SE |
|---|---:|---:|---:|
| SpotBrent BUY | 17 | −5,92 | **5,19** |
| NAS100 BUY | 56 | −2,50 | 1,22 |
| GER40 SELL | 25 | −2,74 | 1,66 |
| JPN225 BUY | 26 | +3,50 | 3,25 |

12 hücre test edildi; 2 SE'yi aşan tek hücre (NAS100 BUY, 2,05 SE) çoklu
karşılaştırmada şansın beklediği kadar. **Yön filtresi hipotezi ölü.**

**Gerçek olan teşhis: kâr kuyrukta.**

| tutma | n | net $ | kazanma |
|---|---:|---:|---:|
| 0–5 dk | 56 | −249,19 | %7,1 |
| 5–30 dk | 123 | −729,31 | %13,8 |
| 30–120 dk | 92 | −118,79 | %43,5 |
| **120+ dk** | **104** | **+724,19** | **%62,5** |

Kitabın bütün kârı 2 saatten uzun yaşayan işlemlerden; altındaki her şey net
−1.097. Kural değil (girişte süre bilinmez), ama sistemin nasıl para
kazandığının tarifi: **kazananları koşturarak.**

**Zaman dilimi artefaktı değil** — operatörün sorusu üzerine kontrol edildi.
M5 sembolleri doğal olarak kısa, M30'lar uzun yaşar; desen sadece "M30
kazanıyor" olsaydı tablo çöp olurdu:

| TF | 0–5 dk | 5–30 dk | 30–120 dk | **120+ dk** |
|---|---:|---:|---:|---:|
| M5 | −39,71 | −245,43 | −107,99 | **+357,48** |
| M15 | −66,90 | −203,85 | −11,61 | **+193,10** |
| M30 | −142,58 | −280,03 | +0,81 | **+173,61** |

Üç zaman diliminin üçünde de aynı şekil. M5'te 120 dakika **24 bar**, M30'da
**4 bar** — farklı bar sayısı, aynı para deseni. Mesele bar sayısı değil,
**süre**.

Sembol bazında 120+ kovası: JPN225 +259,41 · XAUUSD +193,10 · SpotBrent
+98,07 · NAS100 +91,59 · US30 +85,22 · **GER40 −3,20**. Altıda beş pozitif;
tek sembolün, tek TF'nin ya da tek ailenin hikâyesi değil.

Buradan `sl_atr_mult`'ı elle genişletmeye **gidilmez** — o zaten arama ekseni.
Doğru soru bir seviye yukarıda ve LOSS-2'de: seçim skoru kuyruğu taşıyan
adayları doğru ödüllendiriyor mu, yoksa DD ağırlığı üzerinden sistematik
olarak dar stop mu seçiyor.

---

## 4h. Stop çarpanı ızgaranın tabanına yığılmış (18.08)

| sembol | `sl_atr_mult` | ızgara | konum |
|---|---:|---|---|
| XAUUSD | 1,0 | [1 .. 4] n=6 | **ALT KENAR** |
| GER40 | 1,0 | [1 .. 3] n=5 | **ALT KENAR** |
| NAS100 | 1,0 | [1 .. 4] n=6 | **ALT KENAR** |
| US30 | 1,0 | [1 .. 4] n=6 | **ALT KENAR** |
| JPN225 | 2,5 | [1 .. 4] n=6 | iç |
| SpotBrent | 4,0 | [1 .. 4] n=6 | **ÜST KENAR** |

**Altı sembolün dördü tabanda, hepsi tam olarak aynı değerde.**

İlk okumam "arama daha darını isteyip soramıyor" idi; **yanlıştı ve aynı gün
düzeltildi.** Saklanmış 174 opt koşusunun stop dağılımı: `0,5` → 14 koşu,
`0,9` → 28, **`1,0` → 100**, `1,2` → 5, `1,5` → 15, `2+` → 12. Yani ızgara
geçmişte 1,0'ın altını sunmuş ve arama 42 koşuda onu seçmiş. Sorabildiği
yerde çoğunlukla yine 1,0'ı seçiyor — taban bir artefakt değil, tercih.

Bu, 4g ile **ters yöne bakıyor**: kârın tamamı 120+ dakika yaşayan
işlemlerden geliyor, ama arama kazananları erken kesen stopu seçiyor. Aynı
sistemin iki ucu çelişiyorsa aradaki şey **seçim skorudur** — skorun düşüş
terimi dar stop satın alıyor olabilir. LOSS-2 bunu ölçüyor (L2a sınır
bağlayıcı mı, L2b skor vs holdout sıralaması, L2c kâğıtta da kuyruk mu).

### Maliyet/R, stop tabanının mekanik açıklaması

Bir gidiş-dönüşün maliyeti riske edilenin yüzdesi olarak = **spread ÷ stop
mesafesi**. Stop yarıya inince aynı spread iki kat pahalı olur.

| sembol | TF | spread/ATR | stop | maliyet/R | 0,25 ATR stopla |
|---|---|---:|---:|---:|---:|
| SpotBrent | M5 | 0,317 | 4,00 | %7,9 | **%127** |
| JPN225 | M5 | 0,184 | 2,50 | %7,4 | **%74** |
| US30 | M30 | 0,030 | 1,00 | %3,0 | %12,0 |
| GER40 | M30 | 0,025 | 1,00 | %2,5 | %9,9 |
| NAS100 | M30 | 0,015 | 1,00 | %1,5 | %5,8 |
| XAUUSD | M15 | 0,013 | 1,00 | %1,3 | %5,3 |

**İki M5 sembolü kitabın en geniş stoplarını taşıyor** (4,0 ve 2,5) ve
spread/ATR oranları da en kötüsü. Arama stopu maliyeti seyreltmek için
genişletmiş. M30'da maliyet zaten %1,5–3 olduğu için stop dar kalabiliyor —
yani "dört sembol tabanda" bulgusunun kısmen mekanik bir açıklaması var ve
skor hipotezi tek açıklama değil.

**Hızlı al-sat (scalp/toplayıcı) sorusu bununla cevaplanır.** Ölçülen kenar
~0,1 R/işlem; 0,25 ATR stopla maliyet SpotBrent'te %127, JPN225'te %74 —
aritmetik olarak imkânsız. NAS100/XAUUSD'de %5-6 ile mümkün ama kenarın
yarısı girişte gider. Zor değil, **pahalı**, ve pahalılık zaman dilimi
küçüldükçe artıyor.

Günlük işlem sayısı ile getiri karşılaştırması (100+ vs <100 işlem/gün)
**yapılamaz**: yoğun günlerin dördü de temmuz, yani 10 sembollü çalkantı
dönemi. Zamanla karışık, kesit geçersiz.

### Skor ile holdout, stop genişliği konusunda aynı şeyi istemiyor

174 koşuda, kazananın `sl_atr_mult`'ı ile iki sıralama arasındaki Spearman
(aile içi, popülasyon düzeyi):

| aile | n | ρ(stop, holdout net_r) | ρ(stop, **skor**) |
|---|---:|---:|---:|
| micro_rev | 11 | −0,43 | **−0,88** |
| dual_t3 | 12 | −0,21 | **−0,80** |
| macd_flip | 7 | −0,43 | **−0,75** |
| t3_flip | 18 | −0,45 | −0,64 |
| burst | 26 | −0,28 | −0,58 |
| stoch_flip | 27 | **+0,45** | +0,16 |
| st_trend | 8 | +0,57 | +0,52 |
| aroon_flip | 6 | +0,37 | +0,31 |
| mtf_pullback | 15 | +0,14 | −0,02 |
| t3_stoch | 21 | +0,03 | +0,37 |
| wavetrend_flip | 19 | −0,12 | +0,24 |

**11 ailenin 9'unda ρ(net_r) > ρ(skor)** — skor geniş stopu, dokunulmamış
testin cezalandırdığından daha sert cezalandırıyor. `dual_t3`'te holdout
neredeyse ilgisiz (−0,21), skor sert negatif (−0,80). `stoch_flip`'te tersi:
geniş stop holdout'u iyileştirmiş (+0,45), skor bunu ödüllendirmemiş (+0,16).

**Bu kanıt değil, gerekçe.** Bunlar ayrı koşuların kazananları (yoğun
seçilmiş), farklı dönemlerden, ızgaralar zamanla değişmiş, ve n aile başına
6–27. Tek yönlü 9/11 binom p≈0,03 — dikkat çeker, karar taşımaz. Karar
L2b'de: **tek bir koşunun ranked adaylarında** skor sıralaması ile holdout
sıralamasının stop sütunu.

Kenarda duran başka eksenler: JPN225 `trail_start` 3 / `trail_step` 2,5 /
`max_spread_atr` 0,18 (üçü de tavan), GER40 `trail_step` 2,2 (tavan).

**Ayrı not:** XAUUSD `max_spread_atr` canlıda **0,25**, ızgara tavanı 0,18 —
ızgarada olmayan bir değer. 17:20 apply'ından sonra makas kalibrasyonu
değiştirmiş (log'da gerekçesiyle). Tasarlanmış davranış ama damganın ölçtüğü
konfig ile canlı o eksende ayrışıyor; GER40 seansıyla aynı sınıf, acil değil.

---

## 4i. Arama bütçesi değil, tekrarlanabilirlik (18.08) — D1b kapandı

US30 / `t3_stoch` / M30, tek donmuş pencere (90000 bar, 557 g holdout),
`combo_seed` dört tohum × iki bütçe:

| bütçe | holdout net R | ortalama | sapma | SE |
|---|---|---:|---:|---:|
| 2.000 | +11,03 / −7,44 / −27,34 / +5,32 | −4,61 | 17,01 | 8,50 |
| 32.000 | +12,09 / +36,01 / +19,67 / −58,05 | +2,43 | **41,54** | 20,77 |

Fark **+7,04 R**, SE(fark) 22,44 → **0,31 SE, ayırt edilemez**. Kilitli kural
gereği `max_combos` **2000'de kalıyor**. Bu ip kapandı.

**Asıl sonuç ikinci ölçütte** (18.08'de eklenen kural: bir bütçenin tohumlar
arası sapması kendi |ortalaması|'ndan büyükse o bütçe ayar seçmek için
yetersizdir): **her iki bütçe de düşüyor**, ve 32k daha kötü — tek bir tohum
(97) −58 R getirip sapmayı ikiye katlıyor.

Yani `t3_stoch`/US30 için arama **ödeyebileceğimiz hiçbir bütçede
tekrarlanabilir değil**. Damgadaki holdout sayısı o konfigin değeri değil, o
gün çekilen biletin değeri — ve `risk._edge_metric` lotu o sayıdan türetiyor.
US30'un pozisyon boyutu bir çekilişe bağlı.

Karar D1b-e'ye bağlandı: ızgarayı küçültmek tekrarlanabilirliği getiriyorsa
çözüm orada ve bedava; getirmiyorsa US30 `t3_stoch`'tan çıkar ve kapsamı
ölçülebilir bir aileye taşınır. D1b-e **dört tohumla** koşulacak; aranan sayı
ortalama değil **sapma**.

**Düzeltme:** "kapıdan geçen konfig daha geniş stop seçiyor" diye not
düşmüştüm — yanlış. Geçen hücre 11/32k ve `sl_atr_mult=1,0`; 1,5 olan
11/2k, yani kaybeden. 4h'deki skor hipotezi bundan bağımsız ayakta (dayanağı
174 koşudaki ρ asimetrisi), ama motive ederken yanlış bir destek kullanılmıştı.

---

## 4j. Damganın `params` alanı replay'i değil, öncesini taşıyor (19.08)

Canlı konfig bugün **iki kez** damgasından ayrıştı (GER40 seansı, kitap
`max_positions`) ve ikisi de tesadüfen yakalandı. Basit bir denetim koşuldu:
her sembolün canlı satırı, kendi damgasının `params` sözlüğüyle uyuşuyor mu?

| sembol | alan | damga | canlı |
|---|---|---:|---:|
| SpotBrent | `max_spread_atr` | 0,18 | 0,15 |
| XAUUSD | `max_spread_atr` | 0,05 | 0,25 |
| GER40 | `max_spread_atr` | 0,05 | 0,08 |
| **NAS100** | `trail_start_atr` | 0,8 | 1,0 |
| **NAS100** | `trail_step_atr` | 2,2 | 1,8 |
| JPN225 / US30 | — | eşleşiyor | |

**Çoğu gerçek sürüklenme değil.** Beş sembolün damgası GAP-5 replay'inden
yeniden yazıldı ve SpotBrent'in damgası kendi içinde çelişiyor:
`stamp_source` metni "cap 0.15" diyor, `params` sözlüğü 0,18, canlı 0,15.
Yani yeniden yazımda **holdout metrikleri güncellendi, `params` eski
bırakıldı** — beş replay damgasında bu alan, replay'in koştuğu konfigi değil
ondan önceki apply'ınkini taşıyor.

Tek gerçek apply damgası XAUUSD (`stamp_source=None`, `validated=True`);
onun tek ayrışması makas kalibrasyonunun log'da gerekçelendirilmiş
müdahalesi — tutarlı.

**NAS100 çözüldü (STAMP-1c):** GAP-5 replay kaydına bakıldı —
`_gap5_run.py` `getattr(cfg, k)` ile o anki canlı satırı kullanmış ve
`trail_start=1,0 / trail_step=1,8` koşmuş. Canlı bugün de **1,0 / 1,8**.
Yani canlı, replay'in ölçtüğü çıkışla eşleşiyor; yalan söyleyen damganın
`params` alanı (0,8 / 2,2 = önceki apply). **Canlıda düzeltilecek bir şey
yok**, sürüklenme yok.

Yani bulunan beş ayrışmanın hepsi ya stale `params` ya da gerekçelendirilmiş
makas kalibrasyonu. **Denetim çalıştı, alarm gerçek değildi** — ve tam da bu
yüzden `params` düzeltilmeli: bu alan güvenilmez olduğu sürece denetim her
seferinde elle kovalanacak bir yanlış pozitif üretir.

Ders: damga "bu konfig şunu ölçtü" iddiasıdır; `params` yalan söylerse iddia
doğrulanamaz hâle gelir ve **bugünkü bütün arıza sınıfı budur**. Damga yeniden
yazan her yol, replay'in gerçekte kullandığı params'ı yazmalı (STAMP-1a), ve
canlı–damga ayrışması elle değil sürekli kontrol edilmeli (STAMP-1b).

---

## 4k. Eşik `max_combos`'un kendisi — hiçbir konfig deterministik değil (19.08)

D1b-e budanmış ızgarayı (1944 kombinasyon) dört tohumla koştu ve sapma **0**
çıktı. Sebep tekrarlanabilirlik değil: 1944 ≤ 2000 olduğu için
`combos_from_grid` **tam çarpımı** döndürüyor, tohum hiç kullanılmıyor.

| | holdout | sapma |
|---|---:|---:|
| küçük ızgara, tam taranmış | +50,46 (üst sınır) | **0** |
| tam ızgara, %0,00014 örneklenmiş | −4,61 | 17,01 |

**Eşik ızgaranın küçüklüğü değil, `max_combos`'un altına inmesi.**

Tam tarama maliyeti (37 ms/kombinasyon, gerçek 32k koşusundan):

| aile | ızgara | tam tarama |
|---|---:|---:|
| aroon_flip | 2.880 | 1,8 dk |
| parabolic_flip / wavetrend_flip | 8.640 | 5,4 dk |
| stoch_flip | 28.800 | **17,8 dk** |
| macd_flip | 46.080 | 28,5 dk |
| st_trend | 57.600 | 35,7 dk |
| t3_flip | 144.000 | 89 dk |
| mtf_pullback | 622.080 | 6,4 saat |
| burst / micro_rev / dual_t3 | 1,2–2,1 M | 13–21 saat |
| t3_stoch | 1,43 G | imkânsız |

**Altı aile yarım saatin altında tam taranabilir**, ama `max_combos=2000`
hepsinin altında olduğu için **kitaptaki altı konfigin altısı da bir
çekilişin sonucu.** Deterministik aramadan gelen tek bir ayarımız yok.

Bu, aile kararsızlığıyla (4? apply başına %40–75 aile değişimi) aynı şeyin
iki yüzü: çekilişler arasında seçim yapıyoruz, konfigler arasında değil — ve
bütün oturum boyunca "çalkantı" dediğimiz şey bu.

**Önerilen tasarım:** `max_combos` aile başına, ızgara boyutuna kadar,
karşılanabildiğinde. Tek küresel sayı küçük ızgaralı aileleri gereksiz yere
çekilişe mahkûm ediyor — `aroon_flip`'in 2.880'ini 2.000 ile örneklemek
anlamsız. Kitapta bugün bunu karşılayabilen tek sembol GER40 (`stoch_flip`,
17,8 dk); ölçüm oradan başlıyor.

**Determinizm daha iyi sonuç demek değildir.** Tam tarama o ızgaranın gerçek
optimumunu bulur; şanslı bir çekiliş daha yüksek sayı verebilir. Alınan şey
**damganın anlamı ve çalkantının bitmesi**: aynı girdiyle aynı çıktı, ve
yeniden arama kendi kendine ayar değiştirmiyor.

---

## 4l. Kâr kuyrukta — kâğıtta da (L2c), ve skor sonucu öngörmüyor (L2b)

**L2c: LOSS-1'in teşhisi canlıya özgü değil.** Altı canlı konfigin arama
holdout diliminde, işlemler tutma süresine göre kovalandı:

| sembol | n | net R | **120+ dk kovası** |
|---|---:|---:|---|
| GER40 | 1247 | +185 | **732 işlem / +680 R** (0–5: −193, 30–120: −302) |
| NAS100 | 1040 | +107 | +537 R |
| US30 | 405 | +45 | +206 R |
| JPN225 | 314 | +66 | 156 işlem / +137 R |
| XAUUSD | 505 | +87 | 125 işlem / +96 R |
| SpotBrent | 119 | +21 | 56 işlem / +7,5 R |

Altıda altı. Kâğıt da canlı da parayı kuyruktan kazanıyor — **sistemin
doğası**, uygulama farkı değil. "Fark çıkışta mı" sorusu kapandı.

(M30'da 5–30 kovası boş: bar 30 dk, aynı-bar çıkış 0–5'e düşer.)

**L2b: seçim skoru dokunulmamış testle ilişkisiz.**

| | skor ilk 5 ort. sl | holdout ilk 5 ort. sl | ρ(skor↔holdout) | ρ(holdout↔sl) |
|---|---:|---:|---:|---:|
| US30 `t3_stoch` | 0,72 | 0,76 | −0,02 | +0,47 |
| NAS100 `mtf_pullback` | **0,70** | **0,94** | −0,08 | **+0,85** |

NAS100'de skorun ilk 5'inin **hepsi** sl=0,7; holdout'un ilk 3'ü sl=1,0 ve
+113/+113/+105 R veriyor. Skorun birincisi +69 R ile holdout sırasında 5.
**44 R fark, tek sembolde.** US30'da bu yanlılık yok.

Ama asıl sayı ρ(skor↔holdout) ≈ **0**: finalistler arasında skor, sonucu
öngörmüyor.

**Düzeltme holdout'la yapılamaz.** "Adayları holdout'a göre sırala" refleksi
holdout'u testlikten çıkarır ve elimizde bağımsız ölçü kalmaz. Doğru soru
L2d'de: **doğrulama dilimi** (seçimde zaten kullanılıyor, holdout'a
dokunmuyor) skordan daha iyi öngörüyor mu? İyiyse düzeltme küçük: finalistleri
doğrulama metriğiyle sırala. Değilse hiçbir iç metrik dışarıyı öngörmüyor
demektir — çok daha büyük bir bulgu.

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

## 6. Nerede duruyoruz

### 18.08.2026 akşamı — güncel

Hesap: Pepperstone demo **61562752**, bakiye **2.066 $**, özkaynak 2.143 $,
1:100. Marj 62,64 $ (seviye %3421) — kaldıraç neredeyse hiç kullanılmıyor,
çünkü lot SL mesafesinden çıkıyor, marjdan değil.

| sembol | aile | TF | risk % | max_positions |
|---|---|---|---:|---:|
| GER40 | stoch_flip | M30 | 0,80 | 1 |
| JPN225 | dual_t3 | M5 | 0,80 | 1 |
| NAS100 | mtf_pullback | M30 | 0,80 | 1 |
| US30 | t3_stoch | M30 | 0,80 | 1 |
| SpotBrent | dual_t3 | M5 | 0,80 | 1 |
| XAUUSD | burst | M15 | 0,20 | 1 |

Nominal toplam risk **%4,2**, eşzamanlı risk kapısı %15. Kitap 6 sembolde
sabit (operatör kararı); Asya–Avrupa–ABD–emtia dağılımı kasıtlı.

**Bugün değişenler:** hesap kilidi demoya alındı · emir yolu onarıldı (0/Done
kabulü) · short stop tetiği ASK'e · boşluklu stop fill'i açılıştan · saat
referansı sunucuya · GER40 seansı 03:15'e geri · **`max_positions` 6 sembolde
2 → 1** · damgalar kapsam taşıyor.

**Soruşturmanın durumu.** "Tek kalan açıklama çalkantı" hükmü **geri
alındı** — bkz. 4c/4d. `max_open` uyumsuzluğu boşluğun %21'ini açıklıyor,
kalanı sembole göre farklı mekanizma. 92 günlük karşılaştırma çalkantıyla
kirlenmiş durumda ve kovalanmıyor; yerine 16.08'den itibaren büyüyen temiz
pencere (FWD-2) var.

**Açık tetikleyiciler:**
* NAS100 — 50 işlem sonra: başabaşın 5 puan altındaysa sil.
* Lot çarpanı — 100 işlem sonra: gerçekleşen R/işlem güven aralığı sıfırı
  dışlıyorsa 1,0 → 1,25. Tavan ×2,02, sınırı risk kapısı koyuyor, marj değil.
* `daily_loss_pct` 22 — ölçüm penceresi kapanınca düşürülecek.
* **XAUUSD — 50 işlem sonra**: kasa onu boyutlandıramıyor. Minimum lot her
  işlemde niyetin **1,1–2,2 katı** risk aldırıyor (`risk %0.144 -> 0.005,
  min lot 0.01 riski asiyor, 2.2x`), yani risk modeli o sembolde devrede
  değil. Kitabın en düşük calmar'ı da onda (1,96). Gerçekleşen R/işlem
  sıfırdan ayırt edilemiyorsa **silinir**; kasa büyüyüp minimum lot niyetin
  içine sığdığında yeniden değerlendirilir.
* `max_positions` — FWD-2, limit yüzünden düşen sinyallerin kâğıtta kârlı
  olup olmadığını söyleyecek. Kârlıysa bu ayrı bir arama ekseni olmalı.

---

### 16.08.2026 — aşağıdaki rakamlar o günün, bulgular hâlâ geçerli


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

**UK100 ve US2000 kapatıldı (17.08).** Spread kapısı ikisini de boğuyordu
ve SPR-1 taraması (M15/M30, M5 kapalı) bir çıkış yolu bulamadı:

| sembol | kitap calmar | aday calmar | kapı geçen % (kitap → aday) |
|---|---:|---:|---|
| US500 | 0,41 | **0,76** | %68,5 → **%100** (taşındı) |
| UK100 | 1,58 | 1,99 | %50,2 → **%30,9** (kapı kötüleşti) |
| US2000 | 0,99 | 0,80 | %7,2 → %9,3 (hâlâ günde ~1 saat) |
| SpotBrent | 1,82 | 0,84 | %11 → %93 (kapı açıldı, kenar kapandı) |

UK100'ün canlı profili ayrıca yapısal olarak kırıktı: 24 işlem, ödeme oranı
**0,77** (kazançları kayıplarından küçük), başabaş için %56,5 kazanma oranı
gerekiyor. Üst zaman dilimi de yok — zaten M30'da ve H1 `ea8d888` ile
emekli edildi.

SpotBrent M5'te bırakıldı: M15 kapıyı açıyor ama net R aynı kalıp (12,7 →
11,7) drawdown ikiye katlanıyor — kapı açılıyor, kenar açılmıyor.

İkisi 17.08'de kitaptan **tamamen silindi** (operatör onayı). Kitap 8
sembol.

**NAS100 silinmedi, taşındı — ve kendi kuralımı bilerek çiğnedim.**
Kurala göre (calmar **ve** ödeme oranı birlikte iyileşmeli) taşınmamalıydı:
holdout calmar 1,33 → **1,95** geçiyor ama ödeme 2,78 → 2,61 geçmiyor.
Yine de `mtf_pullback/M30`'a taşıdım. Gerekçe:

- Kural UK100 için yazılmıştı; oradaki ödeme **0,77** idi, yani yapısal
  olarak kaybettiren. Burada iki aday da 2,6–2,8 aralığında; %6'lık fark
  bu iki konfig arasında ayırt edici değil.
- Aday holdout'ta net R +60,8 → **+92,0**, işlem 960 → 1045, calmar %47
  daha iyi. Boyutlandırma ölçütümüz zaten calmar (LEV-1).
- **Asıl mesele konfig değil.** Kâğıt zaten 2,78 ödeme diyor, canlı 1,12
  veriyor. Bu, bütün kitabı kapsayan açıklanmamış canlı/kâğıt farkı; NAS100'ü
  bunun için silmek, sırayla her sembolü silmek demek olurdu.
- Canlı sicil (n=72, −11,1 puan) bugünün altı onarımından **önce** toplandı.
  Ayrıca güç: n=72'de standart hata 5,9 puan, yani 11,1 puanlık fark ~1,9
  SE (p≈0,06) — sınırda, kesin değil.

**Gözden geçirme şartı:** onarılmış motorla en az 50 işlem sonra NAS100 hâlâ
başabaşın 5 puandan fazla altındaysa silinir. Kural esnetildi, unutulmadı. Yerine ekleme **bugün yapılmayacak**: sabah altı gerçek onarım indi
(giriş yolu başarı kontrolü, SL/TP başarı kontrolü, VWAP stop puanlaması,
short stop tetiği, calmar boyutlandırma, saat çivisi) ve temiz ölçüm
penceresi daha bir günlük. Yeni sembol, açıklanmamış bir farkın üstüne yeni
değişken koymak olur.

**FRA40 ve US500 silindi (18.08), kitap 6 sembole indi.** GAP-5, her sembol
için hem canlı konfigin onarılmış holdout'unu hem aramanın kazananını
verdi; aday barı 1,94 (onarım sonrası medyan):

| sembol | canlı konfig | aramanın kazananı |
|---|---:|---:|
| GER40 | **5,30** | 2,10 |
| SpotBrent | **4,03** | 0,76 |
| JPN225 | **3,74** | 1,68 |
| US30 | **2,00** | 0,72 |
| NAS100 | 1,98 | 1,98 |
| XAUUSD | 1,49 | **2,05** |
| ~~FRA40~~ | 0,44 | 0,82 |
| ~~US500~~ | 0,54 | 0,54 |

FRA40 ve US500'ün ne mevcut konfigi ne de aramanın en iyisi barı geçiyor.
İkisi de daha iyi bir enstrümanın pahalı ve korele ikizi (FRA40–GER40 ρ0,83
ve 4,2 kat pahalı; US500–NAS100 ρ0,92 ve 2,9 kat pahalı). Dört bağımsız
ölçüm aynı yeri gösterdi.

**Damgalar yenilendi.** `opt_summary.holdout` altı sembol için GAP-5
replay'inden yazıldı (`stamp_source` alanı ile işaretli). Boyutlandırma
artık gerçek sayıdan okuyor; toplam teorik eşzamanlı risk **%9,84 → %7,43**
(kapı %15). FRA40'ın 1,8 kat şişkinliği kendiliğinden gitti.

**Kayda değer örüntü: mevcut konfigler aramayı yeniyor.** Sekiz sembolün
altısında canlı konfig, taze aramanın kazananından iyi ya da eşit. Bu,
16.08 turunda da görülmüştü (adaylar holdout'ta toplam 130,7 R daha kötü).
Çalkantı freni ölçülebilir biçimde para kazandırıyor: hayatta kalan konfig
bir eleme geçmiş, aday ise her seferinde seçim dilimine yeniden uyuyor.

**XAUUSD taşınmadı** — aramanın kazananı calmar'da öne geçiyor (1,49→2,05)
ama ödeme oranı 3,43'ten 1,58'e düşüyor, ve altı sembolde arama kaybederken
iki istisnadan birine güvenmek için sebep yok. Kitabın canlıda en çok işlem
yapan sembolü; ölçüm penceresi dolarken karakterini değiştirmiyorum. Bir
sonraki gözden geçirmede canlı veriyle yeniden bakılacak.

**Hisse sınıfı kapandı — marj duvarı (18.08).** PLTR.US-24 eklendi ve
**aynı gün çıkarıldı**; sebep kenar değil, kaldıraç.

Bu broker'da hisse kaldıracı **1:5**; endeksler 1:346–1:400, emtia 1:100.
Riske göre boyutlandırma lotu stop mesafesinden hesaplıyor, ve PLTR'ın M5
ATR'si 0,083 — 170 dolarlık bir hissede stop, fiyatın binde yarımı. Küçük
stop + düşük kaldıraç = devasa nominal:

| sembol | risk bütçesi | SL mesafesi | gereken lot | marj | equity'nin |
|---|---:|---:|---:|---:|---:|
| GER40 | 20,24 $ | 37,36 | 0,468 | 35,54 $ | %1,7 |
| NAS100 | 12,39 $ | 57,52 | 0,215 | 16,01 $ | %0,8 |
| **PLTR.US-24** | **5,46 $** | **0,083** | **65,94** | **2.253,57 $** | **%106** |

Aynı risk için GER40'ın **63 katı marj**. Holdout calmar 6,17 gerçekti ama
**ulaşılamaz**: kenarı ifade edecek pozisyonu hesap taşımıyor, marj kapısı
lotu kırpıyor ve kırpılmış lot hedef riskin onda birini taşıyor.

Daha yüksek TF de kurtarmıyor: H1 ATR'si M5'in ~7 katı, marj ~320 $'a
(equity'nin %15'i) iner ama o zaman konfig M5 olmaz, yani ölçülen 6,17
geçersiz olur.

**Hata nerede yapıldı:** ST-1A raporundaki `margin_min 3,46` rakamına bakıp
"marj sorun değil" denildi. O **minimum lotun** marjıydı; **gereken lotun**
marjı 660 kat fazla. Bir sembolü eklerken bakılacak sayı `order_calc_margin`
ile hesaplanan **risk bazlı lotun** marjıdır.

Sonuç: **`.US-24` dahil bütün hisse tarafı bu hesap büyüklüğünde kapalı.**
117 ismin hiçbirinde risk bazlı boyutlandırma marja sığmaz. Evren
taramasının tek hayatta kalanı marj duvarına çarptı. Hesap büyümedikçe veya
broker hisse kaldıracını artırmadıkça yeniden açılmaz.

PLTR canlıda hiç işlem açmadı (3 sinyal, 0 fill) — seans penceresi dışında
kaldılar. Zarar yok.

Kitap: 6 sembol, `lot_mode=risk`, sembol başına `max_positions=2`.
Risk yüzdeleri 0.2 (SpotBrent, XAUUSD, US500) ve 0.8 (diğer yedi). Hepsi dolsa
teorik eşzamanlı risk %12.4; sistem kapısı `max_concurrent_risk_pct=15`.

---

## 7. Açık işler, öncelik sırasıyla

### 18.08 gece — güncel kuyruk (altındaki eski maddeler tarihî)

Kapanan gün: **2.074,33 → 2.106,47, +32,14 (+%1,55)**, 20 işlem, kitap
gece düz, marj 0, günlük fren tetiklenmedi.

**Koşan / sıradaki ölçümler:**

| iş | soru |
|---|---|
| D1b-e (koşuyor) | budanmış `t3_stoch` ızgarası **tekrarlanabilirlik** getiriyor mu? 4 tohum, aranan sayı sapma |
| L2b | tek koşunun adaylarında skorun ilk 5'i, holdout'un ilk 5'inden sistematik daha **dar stopta** mı? |
| L2c | kâğıtta da kâr 120+ dk'da mı toplanıyor? Değilse fark **çıkışta** ve MATCH-1 yeniden okunur |
| D1b-f | budanmış ızgara, budamanın türetilmediği sembolde (NAS100/GER40) tutuyor mu? |
| FAM-1 | aile/TF değişimi sonrası canlı performans, yalnız parametre değişiminden ayrılıyor mu? |
| FWD-2 | her sabah bir kez; kitap sabit + `max_positions=1` + arama `max_open=1` penceresi büyüyor |
| M1-1 | XAUUSD M1 ailesi taraması (tek M1 kapısını geçen sembol) |

**Kapanan sorular (yeniden açma):** arama bütçesi (`max_combos` 2000'de
kalır, 0,31 SE) · yön filtresi (12 hücre, hiçbiri ayakta kalmıyor) · aile
eklemek (12 aile zaten ayırt edilemiyor, değişim oranı %40–75) · MT5 takvimi
(broker dağıtmıyor) · damga iyimserliği (yalnız GER40) · ölü ayar (yok).

**Karara bağlı bekleyenler:**
* **US30** — D1b-e tekrarlanabilirlik getirmezse `t3_stoch`'tan çıkar;
  kapsamı ölçülebilir bir aileye taşınır.
* **XAUUSD** — 50 işlem sonra: kasa onu boyutlandıramıyor (min lot niyetin
  1,1–2,2 katı), calmar kitabın en düşüğü. R/işlem sıfırdan ayırt
  edilemiyorsa silinir.
* **NAS100** — 50 işlem sonra: başabaşın 5 puan altındaysa silinir.
* **Lot çarpanı** — 100 işlem sonra: gerçekleşen R/işlem GA sıfırı
  dışlıyorsa 1,0 → 1,25. Tavanı risk kapısı koyuyor (×2,02), marj değil.
* **`daily_loss_pct` 22** — ölçüm penceresi kapanınca düşürülecek.
* **Aile/TF değişim eşiği** — FAM-1 destekliyorsa parametre değişiminden
  ayrı ve yüksek bir bar (aile değişimi biriken kanıtı yakar).

---

### Tarihî maddeler (çoğu 17–18.08'de kapandı)


**BUG — SL/TP başarı kontrolü bu broker'da yanlış (OPS-1, 17.08).**
Teşhis logu (`726364d`) açılır açılmaz sebep göründü ve ilk teşhisim
**yanlıştı**:

```
retcode=0 comment=Done last_error=(1, 'Success')
request=TradeRequest(action=6, ..., sl=69062.0, tp=0.0, position=359440001)
```

Pepperstone-Demo, başarılı bir `TRADE_ACTION_SLTP` için **`retcode=0` ve
`comment="Done"`** dönüyor; `TRADE_RETCODE_DONE` (10009) değil. Kod yalnız
10009'u başarı sayıyor, dolayısıyla **geçen isteği başarısız sanıyor**.

Doğrulandı: "başarısız" denen istek `sl=69062.0` istedi, pozisyonun SL'i
şu an **69062,0**. Trail çalışıyor. "Kazanan pozisyonun stopu ilerlemiyor,
bu doğrudan paradır" cümlesi hatalıydı — para kaybı yok.

Gerçek zararı ikisi: (1) log gürültüsü, (2) **motorun kendi kitabındaki SL
bayat kalıyor** — modify'ı başarısız sayınca yeni seviyeyi yazmıyor. Bu
sadece kozmetik değil: `execution.py` stop kaymasını `book["sl"]`'e karşı
ölçüyor, yani EX-2'nin "stop bacağı tam sıfır" bulgusu bayat referansla
alınmış olabilir. Onarımdan sonra EX-2 yeniden koşulmalı.

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

**MATCH-1 — soruşturma kapandı: uygulama farkı yok (18.08).**

FWD-1 ve MATCH-1 birlikte zinciri tamamladı.

**Aynı sinyalleri alıyor muyuz?** Evet. Kitap 16.08'den beri sabit; o
tarihten bugüne kâğıt 34 işlem, canlı 51, eşleşen 27 → eşleşme **%79,4**
(SE %6,9), sayı oranı **%150**. Kaçan işlemlerin kâğıt net R'si +2,76
(SE 0,55, sıfırdan ayırt edilemez) — kapılar kârlı işlemi kesmiyor.

Tarihsel "canlı kâğıdın %28'ini alıyor" bulgusu **çalkantı artefaktıydı**:
92 günde canlı onlarca konfig çalıştırdı, tek sabit konfigin 1399 işlemiyle
kıyaslamak baştan geçersizdi. BS-1 kapandı.

**Aynı sonuçları mı alıyoruz?** Evet. 27 eşleşen işlem bar bar
karşılaştırıldı — giriş fiyatı, çıkış fiyatı, 1R mesafesi, çıkış sebebi,
sonuç R, tutma süresi:

| | değer |
|---|---|
| ΔR ortalama (n=25, aykırı hariç) | **−0,009 R** |
| ΔR toplam | −0,21 R — sıfırdan ayırt edilemez |
| trail/SL çiftleri (n=6) | ΔR −0,17 … +0,12 |
| XAUUSD −1R satırları | canlı sistematik **~0,02 R** kötü (maliyet) |

Tek aykırı: NAS100 17.08 19:00, kâğıt `time` ile **örneklem sonunda**
çıkmış (+11,02 R, 21 saat), canlı seans sonu flatten yapmış (+3,41 R,
4,9 saat). ΔR −7,61 — bu bir uygulama farkı değil, **örneklem sınırı
artefaktı**.

**Sonuç: motor, backtest'in modellediği şeyi sadakatle uyguluyor.**
Kalan gerçek uygulama maliyeti ~0,02 R/işlem — EX-1'in bağımsız ölçtüğü
0,00145 R ile aynı mertebede.

Dolayısıyla tarihsel **−218,7 R**'lik fark ne sinyalden ne uygulamadan
geliyor. Geriye tek açıklama kalıyor: **canlıda çalışan konfigler, ölçtüğümüz
konfigler değildi.** Çalkantı. Ve bu artık çıkarım değil, iki bağımsız
ölçümün dışladığı tek seçenek.

**İleriye dönük test zaten koşuyor:** 16.08'den beri zorla uygulama yok,
fren 48 saatte, kitap sabit. FWD-1/MATCH-1 iskeleti günlük koşulabilir.

**TF-2 — projenin en keskin ölçümü (18.08). Aynı konfig, aynı pencere.**

Altı canlı konfig, ortak 92 günlük pencerede (18.05 12:10 → 18.08 12:10
sunucu), onarılmış simülatörle koşuldu ve canlı sicille yan yana konuldu:

| sembol | canlı n | canlı ~R | kâğıt R | fark |
|---|---:|---:|---:|---:|
| JPN225 | 66 | +7,9 | +64,4 | −56,5 |
| XAUUSD | 99 | −9,9 | +43,1 | −53,0 |
| GER40 | 66 | −13,7 | +27,2 | −40,9 |
| NAS100 | 75 | −14,8 | +21,0 | −35,8 |
| SpotBrent | 40 | −0,2 | +20,6 | −20,8 |
| US30 | 47 | +1,2 | +13,0 | −11,8 |
| **toplam** | **393** | **−29,4 R** | **+189,3 R** | **−218,7 R** |

**Altı sembolün altısı da kâğıdının altında.** Tek sembole ya da tek yöne
toplanmamış: long %36,3, short %36,5 kazanma oranı — ikisi de kaybediyor.

Bu iki hipotezi birden öldürüyor:

- **"Son 92 gün kötü rejim"** — hayır, kâğıt aynı pencerede +189 R diyor.
  (TF-1'deki eksi hücreler *aramanın kazananlarıydı*, kitapta çalışan
  konfigler değil.)
- **"Uygulama kusuru"** — kayma, spread, stop fill'i, giriş fiyatı, bar
  sırası, trail kadansı, boşluk hediyesi hepsi ölçüldü ve toplamı bu farkın
  yanında küçük kaldı.

**Kalan tek büyük konfound: çalkantı.** Kâğıttaki +189 R "bu konfigi 92 gün
tut" demek. Canlıda hiçbir konfig 92 gün tutulmadı — BS-3: medyan ömür
**12,8 saat**, %68,8'i 24 saatin altında, 11–16.08'de 58 uygulama.
Karşılaştırma "konfig A vs konfig A" değil, **"bir konfig 92 gün" vs
"onlarca konfig 13'er saat"**.

BS-3'ü "sebep değil" diye kaydetmiştim; o karar n=173'lük güçsüz bir
karşılaştırmaya dayanıyordu ve bu ölçüm onu geçersiz kılıyor.

**İleriye dönük test kuruldu.** 16.08'den beri zorla uygulama yok, fren 48
saatte duruyor, kitap sabit. Çalkantı sebepse canlı sicil kâğıda
yaklaşmalı. Yaklaşmazsa çalkantı da elenir ve geriye kâğıdın kendisi kalır.

**TF taşıması yok:** canlı konfigler aramanın her önerisini yeniyor —
GER40 +27,2 vs M15 −0,04; NAS100 +21,0/1,50 vs M15 +7,8/0,75; US30 calmar
1,75 vs M5 0,68. Dördüncü bağımsız doğrulama.

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

**GAP-1 — kâğıt, boşluğun tamamını hediye ediyor (17.08, ÖLÇÜLDÜ).**
`backtest.py` `_exit_check` stop dalında çıkışı **SL fiyatına** yazıyor.
Bar açılışı zaten SL'nin ötesindeyse canlı fill açılışa yakın olur; aradaki
fark kâğıdın hediyesidir. Kitabın 8 sembolünde holdout dilimi üzerinde
ölçüldü (replay `simulate` ile 8/8 net R eşleşti):

| sembol | hediye n | extraR | holdout net R'nin %'si |
|---|---:|---:|---:|
| **FRA40** | 27 | 18,41 | **%48,73** |
| **GER40** | 19 | 21,12 | %10,41 |
| NAS100 | 4 | 2,28 | %2,48 |
| US30 | 2 | 0,65 | %1,45 |
| US500 / SpotBrent / JPN225 | 1 | ≤0,06 | <%0,6 |
| XAUUSD | 0 | 0 | %0 |
| **toplam** | | **42,54 / 527,06** | **%8,07** |

Eşik %5'ti; **geçti, onarılacak**: stop dalında açılış SL'nin ötesindeyse
fill `open` olmalı (short'ta pad ile), SL değil.

Hediyenin neredeyse tamamı **Avrupa endeks seans açılışı** (FRA40 09:00,
GER40 02:00 sunucu saati) — hafta sonu boşluğu değil. Canlı sicilin en
kötüleri (NAS100, JPN225) bu tablonun başında **değil**; yani boşluk
hediyesi 3,42 puanlık farkın tamamını açıklamıyor, ama **FRA40'ın kâğıt
kenarının yarısı** bu iyimserlikten geliyor.

**Yan bulgu, ayrı ve rahatsız edici:** FRA40'ın kayıtlı `opt_summary`
holdout net R'si **102,53**, aynı konfigin replay'i **37,78** — 2,7 kat.
`edge_scale` (LEV-1) boyutlandırmayı bu kayıtlı sayıdan okuyor, yani FRA40
şişik bir calmar ile boyutlandırılıyor olabilir. Ölçülmeden dokunulmayacak.

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
  geçmiyor, seans örtüşüyor. Kenar ölçülmedi.

**`*.US-24` çöp değil — 24 saat işlem gören US hisseleri.** İlk elemede
"tarihli CFD" sanıp attırdım, yanlıştı. Broker yolu
`Markets\Stocks\USA\24 Hour\`, açıklama "(24 Hours)", **117 isim**
(AAPL, AMZN, GOOG, NVDA, TSLA, AMD, BABA, BAC, CAT, CVX…). Normal
versiyonlarından biraz pahalılar — TSLA 6 vs 4 puan, AAPL 18 vs 13, NVDA
5 vs 3 — bu 24 saat erişimin bedeli. Sürekli çalışan bir bot için seans
boşluğu olmaması gerçek bir avantaj; kenar hâlâ ölçülmedi.

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
