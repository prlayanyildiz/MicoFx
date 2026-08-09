# MicoFX Kullanım Kılavuzu

Web terminal: `http://127.0.0.1:8900`
Başlatma: `start.bat` veya `python run.py`

Uygulama açılınca bot **sadece izler**. Emir için üstteki **Bot Başlat** gerekir.

Güncel portföy (10 sembol): SpotBrent, XAUUSD, GER40, JPN225, NAS100, US500, AUDUSD, EURUSD, USDCHF, USDJPY.

## Son güncellemeler (bu belgeyi okuduğun tarihte geçerli olanlar)

- **Tek çıkış modeli: sert ATR stop + takip eden stop.** Sistemden şunlar
  tamamen kaldırıldı — sabit kâr hedefi (TP), kademeli kâr alma (partial),
  zaman stopu (max bar), bayat-işlem kapanışı ve ayrı başabaş sıçraması.
  Artık bir pozisyonu yalnızca stop kapatır:
  - **Giriş anında** `sl_atr_mult × ATR` mesafesinde sert bir stop broker'a
    gönderilir ve hiçbir koşulda kaldırılmaz. Bilgisayar kapansa, internet
    gitse bile orada durur.
  - **Kâr `trail_start_atr × ATR`'yi geçince** stop, kapanmış bar fiyatının
    `trail_step_atr × ATR` gerisinden takip etmeye başlar. Mandallıdır: asla
    geri gitmez, asla ilk sert stoptan kötüye gitmez.
  - Ayrı bir "başabaşa çek" adımı yok; `trail_start` > `trail_step` olduğunda
    takip eden stop girişi kendiliğinden geçiyor. Tam girişe yapışan eski
    adım, sıradan dalgalanmada kazanan işlemi boşuna sıfırlıyordu.
  - Bu üç sayı (`sl_atr_mult`, `trail_start_atr`, `trail_step_atr`) **her
    sembol için ayrı** ve optimizasyonun aradığı şey de bunlar.
  - Kalan tek zorunlu kapatma sebepleri takvim/risk kaynaklı: seans sonu
    flatten, gün sonu flatten ve günlük zarar limiti.
- **Min-lot risk koruması**: Broker'ın minimum lotu, hesaplanan riskin 2
  katından fazlasını gerektiriyorsa (ör. hesap küçükken JPN225/NAS100 gibi
  pahalı enstrümanlarda), o işlem sessizce büyütülmek yerine **atlanıyor**.
  Panel'de "min lot riski X.Xx aşıyor, işlem atlandı" notunu görebilirsin —
  bu bir hata değil, koruma çalışıyor demektir.
- **AI Denetleyici kapalıyken bile karantina geçerli**: Denetleyiciyi
  kapatsan da, ardışık kayıp serisi veya çökmüş kâr faktörü yüzünden
  karantinaya giren bir sembol yine de engellenir. Kapatınca sadece yumuşak
  katmanlar (saat bloklama, günlük düşüşte lot kısma) devre dışı kalır.
- **Web terminal sadeleşti**: Sistem, Semboller ve Optimizasyon
  sekmelerinde artık sadece gerçekten elle ayarlanan alanlar görünüyor;
  geri kalanı **"İleri düzey"** başlığı altında katlı duruyor (▸'a
  tıklayınca açılır). Hiçbir şey silinmedi, sadece gizlendi.

---

# A. Sayıları nasıl okumalısın?

Bu bölüm Panel ve Optimizasyon'daki en sık karıştırılan alanlar içindir.

## Skor

Optimizasyonun "ne kadar iyi görünüyor" sayısıdır. Kabaca:

> skor ≈ (toplam R kazancı) × (yeterli işlem sayısı) × (düşük drawdown cezası)

| Okuma | Anlam |
|---|---|
| Yüksek pozitif (örn. 5–15) | Arama diliminde tutarlı görünüyor |
| 0'a yakın | Zayıf / gürültü |
| Negatif | Zararlı; uygulanmaz |

**Skor tek başına karar değildir.** Asıl bakılacak yer **Test R** ve **Test PF**'tir. Skor aileler arasında da doğrudan kıyaslanamaz; seçim "Seçmeli" dilimle yapılır.

## Kalıcılık (retention)

Bir adayın test (dokunulmamış) dilimdeki beklentisi, seçim/doğrulama
dilimlerinin zayıf olanına göre ne kadarını koruyor. **%25'in altına
düşerse aday reddedilir** — seçim/doğrulama diliminde harika görünüp
gerçek testte neredeyse sıfıra inen (aşırı uyum/overfit) adayları
yakalayan son kapı budur.

## Avantaj

Panel'deki çarpan: sembolün test dilimindeki beklentisi, diğer sembollerin ortancasına göre ölçeklenir (`x0.60` … `x2.20`).

| Örnek | Okuma |
|---|---|
| `x1.66` | Bu sembol paketin güçlüsü → daha büyük lot hakkı |
| `x1.00` | Ortalama |
| `x0.60` | Zayıf → lot küçültülür (taban) |

**Önemli:** Lot hâlâ broker minimumundaysa (`0.01` / `0.10`), Avantaj görünür ama **Lot sütunu değişmez**. Global lot çarpanını artırınca veya Risk % moduna geçince işler.

Sistem → **Kanıtı güçlü sembole büyük lot** kapalıysa Avantaj hep ~1.00 gibi davranır. Şu an **açık**.

## Lot Modu

| Mod | Anlam |
|---|---|
| **sabit** | Her işlemde aynı lot (`fixed_lot` × global çarpan × avantaj) |
| **risk %** | Bakiyenin %'si stop mesafesine bölünerek lot hesaplanır; `max_lot` tavanı vardır |

Güncel portföyün tamamı **risk %** modunda.

## Marj / İşlem

O lotla **bir pozisyon açmak için gereken teminat** (hesap para biriminde).

- Yüksekse aynı anda daha az sembol açılır.
- Panel özeti: "hepsi açılırsa toplam marj …" bunu toplar.
- Canlıda marj yetmezse not: `marj yetersiz` / `marj kullanım limiti`.

## Risk / İşlem (1R)

Stop'a (SL) gelirse bu işlemde yaklaşık **ne kadar para kaybedersin**.

| Okuma | Anlam |
|---|---|
| Küçük 1R (örn. $0.50) | Stop dar veya lot küçük → maliyet oranı şişebilir |
| Büyük 1R (örn. $10) | Stop geniş veya lot büyük → tek işlem daha ağır |

Günlük zarar limiti ve "güvenli üst sınır" bu 1R'leri topluca hesaba katar.

## Beklenen / İşlem

Kabaca: `beklenen $ ≈ expectancy_R × 1R`

Yani: "Bu sembolde, geçmiş test dilimine göre, **ortalama bir işlem** ne kadar net getirebilir?"

| Okuma | Anlam |
|---|---|
| Yüksek pozitif | Güçlü aday |
| Düşük pozitif | Zayıf ama pozitif |
| ~0 veya negatif | Bu sembolü kapatmayı düşün |

Bu bir **tahmin**, garanti değil. Optimizasyon sonrası Test diliminden gelir.

## Maliyet / İşlem

Spread + komisyon (yaklaşık). Yanındaki % = maliyet / 1R.

- Canlıda **işlem engeli değil** (Sistem → "Yüksek maliyetli girişi engelle" açıksa engel olur; şu an açık, eşik %18).
- %15 üstü kırmızı uyarı.
- Optimizer'da maliyet, riskin belirli bir oranını aşarsa o parametre seti **uygulanmaz**.

## Durum etiketleri (Optimizasyon)

| Etiket | Anlam | Ne yaparsın |
|---|---|---|
| **uygulandı** | Hem Seçmeli hem Test kâr etti (PF ≥ 1.10), kalıcılık %25 üstünde ve mevcut ayardan zayıf değil → canlıya yazıldı | Bir şey yapma; bu canlı parametredir |
| **doğrulandı** | Dilimler teknik olarak geçti ama otomatik uygulanmadı (eski daha iyidir / maliyet eşiği / skor kapısı) | Elle "Uygula" dikkatli; çoğu zaman gerekmez |
| **doğrulanmadı** | Test (veya Seçmeli) dilimi yeterince kâr etmedi, ya da kalıcılık çöktü | **Uygulama.** Eski parametreler kalır |

Kısaca: **güven = Test R / Test PF / Kalıcılık / uygulandı**. Skor tek başına "kazanıyorum" demek değildir.

---

# B. Üst çubuk (her sekmede)

| Öğe | Anlam |
|---|---|
| Hesap özeti (bakiye, equity, marj…) | MT5'ten canlı |
| **Bot Başlat** | Emir açmaya izin ver |
| **Durdur** | Yeni emir yok; izleme sürer |
| **Acil** | Botu durdur + botun pozisyonlarını kapat |
| Sağdaki nabız noktası | Son veri güncellemesi |

---

# C. Sekme sekme kılavuz

## 1) Panel

Günlük "kokpit". İşlem gününde en çok burada kal.

### Hesap kartları
Bakiye, equity, serbest marj, günlük K/Z, bot durumu (çalışıyor / izliyor).

### İşlem Kapasitesi

| Sütun | Nasıl okunur |
|---|---|
| Sembol / Grup / Durum | aktif = işlem açabilir; kapalı = motor atlar |
| **Lot** | Gerçek gönderilecek hacim |
| **Avantaj** | Yukarıdaki Avantaj açıklaması |
| **Lot Modu** | sabit / risk % |
| Açık / Limit / Açılabilir | Şu an kaç pozisyon, kaç slot kaldı |
| **Marj / İşlem** | Bir işlem için gereken teminat |
| **Risk / İşlem (1R)** | Stop'a gelirse zarar |
| **Maliyet / İşlem** | Spread+komisyon (+ % risk) |
| **Beklenen / İşlem** | Ortalama işlem tahmini $ |
| Açık K/Z | Bu semboldeki açık pozisyonun anlık kârı |

### Açık Pozisyonlar
Botun pozisyonları. **Tümünü Kapat** hepsini kapatır.

### Günlük Özet
Bugün kapanmış işlemler sembol bazında (aynı pozisyonun parçalı kapanışları tek
işlem olarak birleştirilerek gösterilir, parçalanmış sayım yok).

### Canlı Sembol Durumu

| Sütun | Anlam |
|---|---|
| Strateji / TF | Canlı kullanılan aile ve zaman dilimi |
| Seans | açık / kapalı + kalan süre |
| T3, %K, %D, ADX, ATR | Göstergeler (stratejiye göre anlamlı) |
| ÜST TF | Üst zaman dilimi trend yönü (+1 / 0 / −1) |
| Spread | ATR cinsinden; yüksekse pahalı |
| Sinyal | AL / SAT / − |
| **Not** | Neden işlem yok: `seans dışı`, `sinyal yok`, `cooldown`, `marj…`, `min lot riski X.Xx aşıyor` |

Bot çalışıyorsa ve seans açıksa ama işlem yoksa **Not** sütununa bak. Bir
sinyal geldiyse ve geçici bir engelle (spread/slot/AI) karşılaştıysa, motor
aynı bar içinde engel kalkana kadar otomatik yeniden dener — sinyali hemen
çöpe atmaz.

---

## 2) Semboller

Her sembol bir kart. Tıkla → ayarlar açılır. Değişiklikler anında kaydolur.

### Kartta görünen (elle ayarladığın)

**Pozisyon Boyutu**
- Lot modu, sabit lot, risk %, maks lot, maks pozisyon
- Sembol günlük zarar limiti % (bu sembol bugün bu kadar kaybedince, genel
  günlük limit dolmasa bile sadece bu sembolde giriş durur)

**İşlem Saatleri**
- **Saat filtresi** — kapalıysa hafta içi 7/24 işlem riski (şu an Sistem →
  "Tüm saatlerde işlem" zaten açık olduğu için bu ayrı kontrol devre dışı
  kalıyor, aşağıya bak)
- Aralıklar broker sunucu saatine göre, günler (Pzt–Cum), kapanıştan X dk
  önce flatten

### "İleri düzey / Strateji Parametreleri" (katlı, optimizer ayarlıyor)

Strateji ailesi + zaman dilimi seçimi, sinyalin iç parametreleri (T3
uzunluğu, RSI, ADX eşikleri…), sert stop ve takip ATR çarpanları, giriş
filtreleri, kısmi kâr merdiveni. Bunları elle değiştirmek **mümkün** ama
normalde gerekmez — optimizasyon çalıştırıp sonucu uygulamak yeterli. Aç
bakmak istersen ▸'a tıkla.

Kart altı: **Bu Sembolü Optimize Et**, varsayılana dön, pozisyonları kapat.

---

## 3) Optimizasyon

### Görünen ayarlar
- **Geçmiş penceresi (gün)** — ne kadar geriye bakılıyor
- **Yerel iyileştirme turu** — arama ne kadar derin
- **Maks kombinasyon** — arama ne kadar geniş (yüksek = daha kaliteli ama
  daha yavaş)

### "İleri düzey / Arama Parametreleri" (katlı)
Segment sayısı, min işlem, min pozitif segment oranı, plato ağırlığı, maks
bar, ham parametre ızgarası (virgüllü sayı listeleri). İstatistiksel iç
ayarlar — nadiren dokunulur.

### Zaman dilimi seçici
Boş bırakılırsa kayıtlı ayardaki tüm zaman dilimleri (şu an M5/M15/M30/H1)
taranır. Belirli bir turu sadece bir/birkaç TF'e kısıtlamak istersen
çipleri seç.

### Çalışma
1. Altta sembol (ve istersen TF) çiplerini seç (veya hepsi).
2. **En iyiyi otomatik uygula** işaretli kalsın.
3. **Seçilenleri Çalıştır**.
4. İlerleme çubuğunu bekle.

### Sonuç tablosu — sütun sütun

| Sütun | Nasıl okunur |
|---|---|
| Strateji / TF | Kazanan aile ve zaman dilimi |
| **Skor** | Arama kalitesi (yukarıdaki Skor) |
| **Segment +** | Seçim segmentlerinin kaçı pozitif (örn. %75) |
| Seçim İşlem / PF | Arama dilimi özeti |
| **Seçmeli PF / R** | Aile/TF seçen dilim — buradan kazanan seçilir |
| **Test İşlem / PF / R** | Hiç dokunulmayan dilim — **asıl güven burası** |
| **Kalıcılık** | Test beklentisi, zayıf iç örnek dilimin ne kadarını koruyor (%25 altı = reddedilir) |
| **Durum** | uygulandı / doğrulandı / doğrulanmadı |
| Parametreler | Uygulanan sayılar |
| Uygula | Elle zorla uygula (dikkat) |

**Okuma sırası (önerilen):**
1. Durum = uygulandı mı?
2. Test R pozitif mi, Test PF ≥ 1.10 mı?
3. Kalıcılık %25 üstünde mi?
4. Test işlem sayısı yeterince mi (≥ ~12)?
5. Sonra skora bak.

### Geçmiş Sonuçlar
Eski koşular (sembol başına en fazla 40 kayıt tutulur, liste sonsuza
uzamaz). Skora veya zamana göre sırala.

---

## 4) AI Denetleyici

Geçmişe bakıp **canlı koruma** yapar; yeni strateji üretmez.

### Tablo

| Sütun | Anlam |
|---|---|
| Karar | ok / izleme / karantina / idle |
| Gerekçe | Neden bu karar |
| İşlem / Kazanç / PF / Net | Son dönemde gerçekleşenler (aynı pozisyonun parçalı kapanışları tek işlem sayılır) |
| Üst üste zarar | Seri kayıp |
| Lot çarpanı | AI'nin küçülttüğü ölçek (örn. 0.6) |
| Kapalı saatler | O saatte giriş yok |
| **Beklenen R** | Optimizasyon test dilimindeki expectancy |
| **Sağlık** | Canlı PF / plan → %100 ≈ planlandığı gibi |
| **Öncelik** | Slot azken hangi sembolün önce gireceği |

### Akıllı davranış
- Günlük kayıpta lot küçülür; ayrıca zayıf/ispatlanmamış semboller bekler, güçlüler devam eder.
- Kenarı düşen (backtest iyi, canlı PF zayıf) semboller izlemeye alınır ve otomatik yeniden optimize edilebilir.
- **Karantina, Denetleyici kapalıyken bile geçerli** — sadece yumuşak katmanlar (saat bloklama, günlük düşüşte bekletme) kapanır.

### Ne yapmalısın
- **Aktif** kutusu açık kalsın (şu an açık).
- Karantina haklıysa bekle; haksızsa sembol satırından temizleyebilirsin.
- **Tüm Kararları Sıfırla** nadiren; bozulmuş durumu temizler.

---

## 5) Sistem

### Bot Kontrolü
Başlat / Durdur / Durdur+kapat / Acil — üst çubukla aynı işler.

### MT5 Bağlantısı
Bağlı mı, sunucu saati, hesap. **Yeniden Bağlan** kopuklukta yetersiz kalırsa.

### Sistem Ayarları — görünen (elle ayarladığın)

| Ayar | Ne işe yarar | Şu anki değer |
|---|---|---|
| Maks toplam pozisyon | Eşzamanlı işlem tavanı | 10 |
| Global lot çarpanı | Tüm lotları ölçekler | 0.5 |
| Kanıtı güçlü sembole büyük lot | Avantaj ağırlığı | Açık |
| Günlük zarar limiti % | Aşınca gün boyu giriş yok | 4.0 |
| Günlük kâr hedefi % | 0 = kapalı | 0 (kapalı) |
| **Tüm saatlerde işlem** | Sembol seans pencerelerini yok sayar | **Açık** (bilinçli tercih — daha çok örnek/işlem birikmesi için) |
| Gün sonu kapanış (dk) | Gece yarısına N dk kala giriş yok, açık pozisyon kapanır | 15 |
| Durdurunca pozisyonları kapat | Durdur = flatten | Kapalı |
| Açılışta botu başlat | Program açılınca otomatik trade | Kapalı (önerilir) |
| Otomatik yeniden-opt | Periyodik kendi kendine optimize | Açık, 7 günde bir |

**"Tüm saatlerde işlem" hakkında bilmen gereken**: optimizasyon sadece
sembolün tanımlı seans pencerelerinde ölçüm yapıyor. Bu ayar açıkken canlı
o pencerelerin dışında da işlem açabilir — yani bazı saatlerde
doğrulanmamış davranış sergiliyor olabilirsin. Bilerek açık tutuyorsan
sorun değil, sadece bunu bilerek yap.

### "İleri düzey" (katlı) — bağlantı ve teknik eşikler
Scalp/swing ayrı pozisyon limitleri, maliyet/marj eşikleri, slippage,
döngü aralığı, sunucu saat farkı, MT5 bağlantı ayarları. Varsayılan
haliyle bırakabilirsin.

### Ürün Portföyü
Sembol ekle/sil/aç-kapa, broker isim eşleme. Broker `EURUSD.r` diyorsa
buraya yaz. Boş = otomatik. Yanlış yazarsan sembol işlem yapmaz; Durum
"bulunamadı" olur.

---

## 6) Log

Canlı olay akışı.

| Seviye | Ne görürsün |
|---|---|
| INFO | Genel durum |
| SIGNAL | Yeni AL/SAT sinyali |
| TRADE | Emir açıldı / SL güncellendi / kapatıldı |
| OPT | Optimizasyon |
| AI | Denetleyici kararları |
| ERROR / WARN | Hata ve uyarı |

Filtrele, indir. Sorun olursa Log + Panel Not birlikte bak.

---

# D. İlk kurulum (bir kez)

1. MT5 açık, hesaba giriş yapılmış.
2. MT5: **Algoritmik alım satıma izin ver** açık.
3. `start.bat` → `http://127.0.0.1:8900`
4. Sistem → MT5 yolu doğru mu.
5. Sistem → Sembol İsim Eşlemesi (gerekirse).
6. Semboller → **Saat filtresi** / Sistem → **Tüm saatlerde işlem** tercihini bilerek seç.
7. AI → **Aktif** açık mı.
8. Demo'da Bot Başlat ile dene.

---

# E. Günlük akış

```
MT5 açık → MicoFX açık → Panel (bağlantı + seans)
→ Bot Başlat
→ Panel + Log izle
→ Gün sonu Durdur
→ Sorun varsa Acil
```

---

# F. Sık durumlar

| Görünen | Anlam | Ne yap |
|---|---|---|
| `seans dışı (09:00-23:30)` | Saat penceresi dışında | Bekle / saatleri düzenle |
| Hafta sonu / gün dışı | Trade günü değil | Pazartesi |
| `broker sembolu bulunamadi` | İsim yok | Sistem → eşleme |
| `marj yetersiz` | Teminat yetmiyor | Lot düşür / pozisyon kapat |
| `gunluk zarar limiti` | Günlük kesici | Ertesi gün |
| `sinyal yok` | Kurulum yok | Normal; bekle |
| `cooldown …sn` | Son işlemden sonra bekleme | Bekle |
| `min lot riski X.Xx asiyor, islem atlandi` | Broker minimum lotu riski çok şişiriyor | Normal koruma; küçük hesapta bazı sembollerde beklenir |
| `AI karantina …dk` | Sembol ardışık kayıp/düşük PF yüzünden askıda | AI kapalıyken bile geçerli; bekle veya haklı değilse sıfırla |
| **doğrulanmadı** | Test dilimi zayıf veya kalıcılık düşük | Uygulama; sembolü kapatmayı düşün |
| Bot izliyor, işlem yok | Bot kapalı veya seans/sinyal yok | Bot Başlat + Not sütunu |

---

# G. Önerilen düzen

**Haftada bir / rejim değişince**
1. Optimizasyon (hepsi veya sorunlular)
2. `doğrulanmadı` / düşük Beklenen sembolleri kapat
3. AI açık mı bak

**Her işlem günü**
1. MT5 + MicoFX
2. Panel kontrol
3. Bot Başlat
4. Günlük zarar limitine saygı
5. Durdur

**Dokunma**
- Her gün parametre kurcalama
- Slippage'ı "daha çok kazansın" diye şişirme
- Demo görmeden lot'u agresif büyütme
- `doğrulanmadı` sonucu zorla uygulama

---

# H. Acil durum

1. **Acil** (üst çubuk veya Sistem)
2. MT5'te pozisyon kaldı mı kontrol et
3. Gerekirse MT5'ten elle kapat
4. Log'u indir

---

## Uyarı

Bu yazılım finansal tavsiye değildir. Önce demo hesapta çalıştırın. Geçmiş performans geleceği garanti etmez.
