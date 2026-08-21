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

### 20.08.2026'dan itibaren: eşit yetki, tek yazar

Operatör kararı: **Cursor da Claude ile aynı tam yetkiye sahip.** İnceler,
araştırır, bulur; sonra ikisi konuşup nasıl düzeltileceğini planlar.

**İkisi de yapabilir:** kendi soruşturmasını açmak, öncelik önermek, ölçüm
tasarlamak, kod yazmak, diğerinin kararına **itiraz etmek ve reddetmek**.
"Brief bekliyorum" artık geçerli bir duruş değil — ikisi de kendi işini
seçebilir.

**Değişmeyen tek şey, yetki değil eşzamanlılık:** canlı DB'ye ve git'e
**tek yazar** dokunur (sunucudaki Claude oturumu). Sebebi hiyerarşi değil,
yarış koşulu: iki süreç aynı `micofx.db`'ye yazarsa biri diğerinin üzerine
yazar, ve iki ajan commit atarsa değişikliğin kime ait olduğu kaybolur.
Cursor bir canlı değişiklik isterse yazıp gerekçelendirir; Claude uygular ya
da **gerekçeyle reddeder** — ve o red de tartışmaya açıktır.

**Karşılıklı inceleme zorunlu.** Ürün kodu, iki taraftan hangisi yazarsa
yazsın, diğerinin incelemesinden geçmeden commit edilmez. Bugüne kadar
Claude Cursor'ın diff'ini inceliyordu ama **Claude'unkini kimse
incelemiyordu**; bu asimetri kalktı. Cursor, Claude'un yazdığı koda ve
verdiği hükümlere aynı sertlikte bakar.

**Her rapor üç şeyi taşır:** ne yapıldı, sırada ne var, ve **neden bu**.
Üçüncüsü en önemlisi — bu oturumda en çok değer, birinin diğerinin
gerekçesindeki hatayı görmesinden çıktı (Cursor: ızgara budamasının
kirlenmesi, `atr_period` kesişimi, `max_open` uyumsuzluğunun raporlanması;
Claude: otopsi kaydının kapanışı bozabilmesi, `note` gölgelemesi, holdout'la
seçim yapma tuzağı).

**Anlaşmazlık kaydedilir.** İkisi aynı fikirde değilse hüküm veren taraf
karşı görüşü de yazar. Ölçülebilir bir anlaşmazlık varsa **ölçülür**;
ölçülemiyorsa ikisi de DEVAM'a geçer ve karar sahibi gerekçesini yazar.

### 20.08 ikinci genişletme: Claude yargıç değil, uygulayıcı

Kalan tek darboğaz Claude'un **onayı** idi. Kalkıyor. Cursor bir canlı
değişiklik istediğinde artık ikna etmesi gerekmiyor; **Claude uygular.**

Reddin tek geçerli biçimi **ölçülmüş bir itiraz**: "bence riskli" yetmez,
"şu ölçüme göre şu zararı verir" gerekir, ve red DEVAM'a gerekçesiyle yazılır.
Tercih reddi yoktur.

**Üç kademe** — Cursor talebi hangi kademeye koyduğunu yazar:

| kademe | ne | kim karar verir |
|---|---|---|
| **yeşil** | risk maruziyetini değiştirmeyen her şey: rapor, log, panel, ölçüm betiği, test, arama parametresi (`apply_best=False` ile) | **Cursor.** Claude uygular, tartışmaz. |
| **sarı** | risk profilini değiştiren: `risk_percent`, `max_positions`, kitap kompozisyonu, denetçi eşikleri, `size_by_edge` | **İkisi birden.** Anlaşmazlık ölçülür; ölçülemezse uygulanmaz. |
| **kırmızı** | hesap düzeyinde: kaldıraç, hesap kilidi, günlük fren tavanı, canlı paraya geçiş | **Operatör.** İkisi de öneri yazar, uygulamaz. |

**Sarı kademe neden ikisi birden:** 5e'de ölçüldü — kitaptan bir sembol
çıkarmak kalan beşinin lotunu %12 değiştiriyor. Risk kararları birbirine
bağlı, ve tek kişinin görmediği bir yan etki oluyor.

### 21.08 üçüncü genişletme: commit, restart, ve sarının daralması

Cursor'ı bekleten üç şey daha kalkıyor. Hiçbiri yetki değildi ama sonuçları
aynıydı: her düzeltme Claude'un sırasını bekliyordu.

**1. Cursor kendi işini commit eder.** Şart: **`git add -A` yok** — yalnız
kendi dokunduğu dosyalar, adıyla. Sebebi çalışma ağacının paylaşılması;
`-A` diğerinin yarım işini içeri alır. İnceleme **sonradan** yapılır, ve bu
yeterli: kod otomatik dağıtılmıyor, bot yalnız yeniden başlatılınca alıyor.

**2. Cursor botu yeniden başlatabilir** (§3'teki prosedürle: doğru
yorumlayıcı, sonra **portu doğrula**). Kural: öncesinde ve sonrasında
`FOR_CLAUDE.md`'ye yazar, ki ikisi aynı anda durdurup iki örnek açmasın.
Açık pozisyon varken kozmetik değişiklik için durdurmaz — 20.08'de beş
pozisyon açıkken bunu ikimiz de reddettik, doğru refleksti.

**3. Sarı kademe daraldı: kapsam "risk koduna dokunmak" değil,
"amaçlanan maruziyeti değiştirmek".** `risk.py`'de bir hesap hatası bulup
düzeltmek — kodun zaten yapmayı amaçladığı şeyi yapmasını sağlamak —
**yeşildir**. Sarı olan, maruziyetin kendisini kasıtlı değiştirmektir:
`risk_percent`, `max_positions`, kitap kompozisyonu, denetçi eşikleri,
`size_by_edge`.

Sarı neden duruyor: 5e'de ölçüldü — kitaptan bir sembol çıkarmak kalan
beşinin lotunu %12 değiştiriyor. Maruziyet kararları birbirine bağlı ve tek
okuyucunun kaçırdığı yan etkiler var (20.08'de XAUUSD'yi silip geri alırken
Claude kaçırdı).

### 21.08 dördüncü genişletme: son ayrım da kalktı

Operatör: *"tüm yetkiyi Cursor'a ver, ikinizde tam yetkilisiniz."*

**Cursor canlı `micofx.db`'ye de yazar.** Kalan kısıt yetki değil, aynı anda
iki yazar olmamasıydı — ve bunun çözümü zaten kurulu: **botu durduran, pencereyi
sahiplenir.** Restart protokolü (öncesinde ve sonrasında `FOR_CLAUDE.md`'ye
yaz) DB yazımı için de geçerli. Kim durdurduysa o yazar, o başlatır, o portu
doğrular.

Kural tek cümle: **bot açıkken canlı DB'ye yazılmaz** — motorun bellekteki
kopyası üzerine yazar ve değişiklik sessizce kaybolur. Bu iki gün içinde
öğrenildi, teori değil.

**Sarı kademe duruyor ve simetriktir.** Maruziyeti kasten değiştiren karar
(`risk_percent`, `max_positions`, kitap kompozisyonu, denetçi eşikleri,
`size_by_edge`) **ikisinin de tek başına yapamayacağı** şeydir — Claude da
yapamaz. Bu bir hiyerarşi değil iki anahtar kuralı, ve gerekçesi ölçülmüş:
5e'de bir sembolü çıkarmanın kalan beşinin lotunu %12 değiştirdiği görüldü,
ve o bağlantıyı 20.08'de Claude tek başına kaçırdı.

**Kırmızı operatörde kalır:** kaldıraç, hesap kilidi, günlük fren tavanı,
canlı paraya geçiş.

Bundan sonra ikisi arasında **yetki farkı yoktur.** Kalan her şey sıra ve
koordinasyon.

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

**Bot iki `pythonw.exe` süreci gösterir — bu normaldir.** Venv'in
`Scripts\pythonw.exe`'si Windows'ta bir **yönlendirici**: `pyvenv.cfg`'deki
`home`'dan asıl yorumlayıcıyı başlatır ve venv'in `site-packages`'ını yolda
tutar. Doğrulandı (21.08):

```
PID 3404   C:\MicoFX-venv\Scripts\pythonw.exe run.py    (ebeveyn, soket yok)
PID 15732  C:\Program Files\Python312\pythonw.exe run.py  (cocuk, port 8900)
```

Yani **portu tutan sürecin yolu Program Files görünür** ve bu bir arıza
değildir — `sys.prefix` venv'i, `sys.base_prefix` Python312'yi gösterir,
`import uvicorn` çalışır. Panikleyip öldürmeyin.

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
makas kalibrasyonu. **Denetim çalıştı, alarm gerçek değildi.**

**Onarıldı (19.08 07:20, `c727a35` + `restamp_from_replay`).** Bot durduruldu,
beş replay damgası canlı satırdan yeniden yazıldı, bot kaldırıldı. XAUUSD
atlandı — onun damgası gerçek bir apply ve `params`'ı aramanın kullandığı
değeri taşıyor; canlıya eşitlemek aramanın kaydını silerdi.

Denetim şimdi **tek satır** veriyor: XAUUSD `max_spread_atr` 0,05 → 0,25,
yani makas kalibrasyonunun bilinen müdahalesi. Dört yanlış pozitif sıfırlandı.

**Denetim tasarımı:** karşılaştırma `opt_fields_read(family) |
ENGINE_OPT_FIELDS` ile sınırlanmalı. Damga bütün OPT_FIELDS'i yazıyor ama
`stoch_flip` yalnız 9'unu okuyor; okunmayan alandaki fark davranış
değiştirmez ve uyarı üretmemeli (§5 birinci arıza sınıfının aynısı, denetim
tarafında).

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

## 4m. Tam tarama determinizm verir, kâr vermez (19.08, GER40)

GER40 / `stoch_flip` / M30, aynı donmuş barlar, `grid_total=28800` tam çarpım
(1463 s = 24,4 dk):

| koşu | holdout net R | PF |
|---|---:|---:|
| **tam tarama 28.800** | **+234,04** | 1,32 |
| çekiliş seed 7 | +288,66 | 1,41 |
| çekiliş seed 11 | +142,13 | 1,18 |
| çekiliş seed 23 | +260,36 | 1,36 |
| çekiliş seed 97 | +292,10 | 1,42 |

Çekiliş ortalaması **+245,81**, SD **70,57**, SE 35,28. Tam − çekiliş =
−11,77 R = **0,33 SE → ortada**. Şanslı çekiliş (97) tam taramayı 58 R
geçiyor.

**Determinizm bedava kâr değildir** — ölçüldü, kayda geçti, kimse sonradan
"tam tarama daha iyiydi" diye hatırlamasın. Alınan tek şey: **aynı girdiyle
aynı çıktı**, yani yeniden optimizasyonun rastgele bileşeninin silinmesi.
Barlar ilerlediği için konfig yine değişebilir; silinen rastgelelik, değişimin
tamamı değil.

**Üçüncü bağımsız kanıt, kapı sonucu öngörmüyor:** beş koşudan kapıyı geçen
tek çekiliş seed 11 ve holdout'u **en düşük olanı** (+142 vs +292). Tam
taramanın kazananı da kapıdan geçmiyor (doğrulama PF 1,09 < 1,10). 4l'deki
ρ(skor↔holdout)≈0 ile aynı yer.

Çekiliş gürültüsü aileye göre farklı: GER40'ta beş kazananın çekirdeği aynı
(sl=1,0 / trail_step=2,2 / spread=0,05), yalnız `trail_start` ve `stoch_k`
oynuyor; US30'da kazananlar tamamen değişiyordu.

**Çözüldü (19.08 08:15, `cf8c45c`).** `strategy_max_combos` haritası eklendi
(`family_max_combos`, harita yok / okunamaz / ≤0 → küresel değere düşer).
Canlıya bağlandı: **`{"stoch_flip": 28800}`**, diğer her aile 2.000'de.

GER40 kitabın **tek `stoch_flip` sembolü** ve bir sonraki yeniden
optimizasyonunda tam çarpım taranacak — aynı barlar aynı konfigi verecek,
çekiliş yok. Bot 14 paralel süreçle koştuğu için Cursor'un 2 işçiyle ölçtüğü
24,4 dk canlıda ~3,5 dk'ya iner.

Diğer beş sembolün ailesi tam taranamıyor: `t3_stoch` imkânsız (1,43 G),
`dual_t3` 21 saat, `burst` 13 saat, `mtf_pullback` 6,4 saat. Onlar çekiliş
rejiminde kalıyor.

Ayrıca `record_opt_run` artık **ranked ilk 10'u** (params + doğrulama +
holdout) saklıyor. 18–19.08 gecesinde üç ayrı ölçüm için taze arama koşmak
zorunda kalmıştık, her biri ~20 dk.

---

## 4n. Hiçbir iç ölçü dışarıyı öngörmüyor (19.08) — L2 zinciri kapandı

| sıralayan | US30 ρ(holdout) | NAS100 ρ(holdout) |
|---|---:|---:|
| arama blend'i (`score`) | −0,02 | −0,08 |
| doğrulama `net_r` | +0,44 | **−0,64** |
| doğrulama PF | +0,58 | −0,29 |
| doğrulama expectancy | +0,63 | **−0,62** |

İki sembol **ters yön**; n=10, SE 0,33, farklar 1,2–1,4 SE → **ayırt
edilemedi**. Sıralamayı doğrulamaya çevirme önerisi düştü.

**Kavram hatası düzeltildi:** `rank_for_selection` finalistleri **zaten**
doğrulama skoruyla sıralıyor; `score` alanı arama blend'i, seçimi yapan değil.
"Skor yerine doğrulama kullanalım" önerisi NAS100'de zaten canlıydı ve
dar-stop tuzağını **üreten şeyin kendisi** (doğrulama birincisi sl=0,7 /
val +148 / holdout +69; holdout birincisi sl=1,0 / val +82 / holdout +113).

### Dört bağımsız gözlem, tek yön

1. ρ(arama blend ↔ holdout) ≈ 0
2. NAS100'de seçim 44 R daha kötü adayı alıyor
3. GER40'ta kapı, beş adayın **en kötüsünü** geçiriyor (4m)
4. Doğrulama da öngörmüyor, iki sembolde ters işaret

**Kanıtlandı demiyoruz** — her biri n≈10 ve finalistlerle sınırlı, menzil
daralmış. Ama dört kesitte tek karşı örnek yok.

### Bundan çıkan yön: daha iyi seçmek değil, daha az seçmek

Seçim gürültüyse çözüm daha iyi bir seçici değil, **seçim sayısını
azaltmak**. Üç kaldıraç:

* **BUDGET-1** — aile başına tam tarama; aynı girdiye aynı çıktı, rastgele
  yeniden seçim silinir (4m).
* **FAM-1** — aile/TF değişimine ayrı ve yüksek eşik; aile değişimi biriken
  kanıtı yakıyor, gürültüyle yakılmamalı.
* **churn freni** (`reopt_min_age_hours=48`) — zaten var, gerekçesi artık
  ölçülmüş.

Bu yol, "daha iyi skor bul" yolundan sağlam: skorun düzeltilebilir olduğunu
varsaymıyor.

**L2 zinciri kapandı**, genişletilmeyecek.

---

## 4o. Etkisiz ayar — "okunuyor" ile "etkisi var" aynı şey değil (19.08)

AUDIT-A "ölü ayar yok" dedi ve doğruydu: her anahtarın bir okuyucusu var. Ama
`cooldown_sec` altı sembolde de **120 sn** ve girişler bar kapanışında oluyor;
bar M5'te 300, M30'da 1800 sn. Soğuma bir sonraki bar kapanmadan doluyor —
**hiçbir zaman hiçbir şeyi engellemiyor.** `OPT_FIELDS`'te de yok, arama hiç
denemiyor.

Yani §5'in birinci arıza sınıfının daha ince bir hâli: kod okuyor, değer
davranışı değiştiremeyecek kadar küçük. **"Okunuyor mu" testi bunu
yakalayamaz; "etkisi olabilir mi" testi yakalar.** AUDIT-A'yı bu gözle
tekrarlamak gerekiyor.

**`skip_after_loss` yalnız kâğıtta:** `backtest.py` dört yerde işliyor,
`engine.py`'de hiç yok. Zarardan sonra bekleme simülasyonda mümkün, canlıda
değil. İkisi de kapalı olduğu için bugüne kadar zararsızdı (AUDIT-C bunu
"aynı" saymıştı, doğru); ama aranmayan ve canlıda karşılığı olmayan bir
bayrak ileride yanlış karşılaştırma üretir.

**`adx_min` üç sembolde 0** (JPN225 / NAS100 / US30), diğer üçünde 15. Aranmış
değerler, unutulmuş değil — ama 4n'den sonra "arama seçti" eskisi kadar güçlü
bir gerekçe değil.

Üçü de CHOP-1'de ayrı ayrı ölçülecek; **birleştirilmeyecek**, yoksa hangi
etkinin hangisinden geldiği bir daha ayrılamaz.

**Bugünkü yamalar testereye dokunmuyor** — operatörün sorusuna dürüst cevap
bu. Damga onarımı ölçüm doğruluğu, `max_positions` boyutlandırma, tam tarama
tekrarlanabilirlik. Girişin yatay piyasada yön çevirmesini engelleyen hiçbir
şey yapılmadı.

---

## 4p. Flip aileleri canlıda hiç dönmüyor (19.08)

Giriş hunisi, kitap sabit dönem (16.08 21:34'ten, 126 sinyal):

| neden | sinyal | pay |
|---|---:|---:|
| **risk_sembol_limiti** | 52 | **%41,3** |
| açıldı | 43 | %34,1 |
| emir_hatasi (tarihî, onarıldı) | 12 | %9,5 |
| spread | 11 | %8,7 |
| risk_ters_yon | 5 | %4,0 |
| lot | 3 | %2,4 |

**GER40: 58 sinyal, 7 işlem (%12)**, 39'u pozisyon limitinden.

`risk.py:501` pozisyon sayısını **yön kontrolünden önce** bakıyor:

```
501: if len(same_symbol) >= cfg.max_positions:   -> "sembol pozisyon limiti"
503: if any(p["side"] != side for p in same_symbol): -> "ters yonde acik pozisyon"
```

`max_positions=1` iken açık pozisyon varken gelen **her** sinyal 501'e takılır,
ters yönlüler dahil — bu yüzden `risk_ters_yon` sayacı artık dolmuyor ve
52'nin içinde kaç dönüş sinyali olduğu **bilinmiyor**.

`backtest.py:636` aynısını yapıyor (`len(opens) >= max_open: continue`), yani
**canlı/kâğıt tutarsızlığı yok**; holdout sayıları bugünkü davranışı doğru
yansıtıyor.

**Sonuç: flip aileleri canlıda hiç dönmüyor.** `stoch_flip` "dön" dediğinde
pozisyon kapanıp ters açılmıyor, stopa kadar bekliyor. Strateji "çık" derken
stop yeniyor. REV-1 bunu ölçüyor: sinyal dönünce kapat-ve-ters-aç, altı
konfigin holdout'unda. İki yönlü etki beklenir — erken çıkış gereksiz stopu
azaltır, ama testerede iki kat işlem ve iki kat maliyet demektir. Ölçülmeden
bağlanmayacak.

---

## 4r. Yerel model: akıl yürütme değil, talimat (19.08)

Makinede Ollama var; **GPU yok** (12 çekirdek, 24 GB RAM). Üretim hızı hangi
model olursa olsun **~3 tok/s** — yani seçim "hangi model daha büyük" değil,
**"kaç token harcıyor"** sorusudur.

Aynı işte (bir ölçüm cümlesi `n` ve hata payı taşıyor mu, tek kelime cevap):

| model | doğruluk | süre/madde |
|---|---:|---:|
| deepseek-r1:8b, düşünme açık | 3/4 | **121 s** |
| deepseek-r1:8b, düşünme kapalı | 4/8 (**ayırt etmiyor**, hepsine aynı cevap) | 3,5 s |
| deepseek-r1:14b | 8b ile aynı kalite, 1,5 kat yavaş | — |
| **qwen2.5:7b-instruct** | **7/8** | **~3 s** |

R1 her cevaptan önce zorunlu olarak yüzlerce token düşünüyor; GPU'suz bir
makinede o düşünme dakikalara mal oluyor ve bastırılınca model **yargı
yeteneğini tamamen kaybediyor**. Talimat modeli doğrudan cevap veriyor:
**25 kat hızlı ve daha doğru.**

Zor akıl yürütmede hiçbiri işe yaramadı: "kâr kuyrukta" iddiasına en güçlü
itirazı sorduğumda ikisi de olmayan bir kurgu hatası uydurdu, asıl itirazı
(tutma süresi sonucun kendisi tarafından belirlenir) bulamadı.

**Her iki deepseek modeli silindi** (19.08, operatör kararı; 14,2 GB yer
açıldı). Kalan: `qwen2.5:7b-instruct`.

**Kullanım:** `claude/_ollama.py` istemcisi, `claude/_rigor_check.py` aracı.
Yalnız elle, bitmiş metinde, **asla arama koşarken** — yüklü model ~5 GB tutar
ve `optimizer.py` işçi sayısını boştaki RAM'e göre hesaplar. Hiçbir otomatik
akışa bağlı değil.

**Ayıklayıcı düzeltildi (20.08).** İlk sürüm "iki sayı geçen her satırı"
alıyordu ve ilk gerçek koşusunda beşte beş yanlış alarm verdi — model değil,
regex kusuruydu. Artık üç şart birden aranıyor: bir sayı, onu *ölçüm* yapan
bir belirteç (`R`, `%`, `$`, `n=`, `PF`, `calmar`, `SE`, beklenti…), ve tarih
/ saat / bölüm numarasının işi yapmıyor olması.

Yeniden koşuldu: 120 satırdan **4 iddia**, üçü isabetli yakalama, biri sınırda
(ayar cümlesi). Ve üç isabetin üçü de **kendi brief'imden** — sayıyı yazıp
örneklemi ve hata payını yazmadığım satırlar. Aracın var oluş sebebi tam
olarak buydu.

---

## 4s. Flip aileleri dönmedikleri için çalışıyor (19.08) — REV-1 ve FLAT-2

Operatörün hedefi: "getiri eğrisini artıralım, gereksiz stop yiyip işlem
kaçırmayalım." İki aday ölçüldü, **ikisi de reddedildi**.

### REV-1 — ters sinyalde kapat ve dön: felaket

Gerekçe sağlam görünüyordu: `stoch_flip` dönmek için var, canlı motor dönüş
sinyalini pozisyon limiti diye düşürüyor (4p), pozisyon da stratejinin zaten
karşı çıktığı bir stopa kadar bekliyor.

| sembol | A (bugün) | B (dön) | B−A |
|---|---:|---:|---:|
| **GER40** | +184,01 R | **−817,01 R** | **−1001** |
| JPN225 | +67,15 | +41,77 | −25,4 |
| NAS100 | +108,55 | +78,51 | −30,0 |
| US30 | +46,16 | +40,77 | −5,4 |
| XAUUSD | +83,33 | +80,98 | −2,4 |
| SpotBrent | +20,80 | +23,59 | +2,8 |

GER40: işlem 1248 → **3629** (2028 dönüş), medyan tutma **180 → 60 dk**,
30–120 dk kovası tek başına **−1362 R**.

**Bu, 4g/4l'yi tersine çeviriyor:** 120+ dakikada duran kâr, stratejilerin
karşı sinyallere rağmen başardığı bir şey değil — **onlara rağmen beklemenin
ürettiği** şey. Flip aileleri **dönmedikleri için** çalışıyor, ve dönüş
sinyali stopun zaten süzdüğü gürültü. **4p'de "kaçan işlem" saydığım 52
sinyal, kaçan fırsat değilmiş.**

### FLAT-2 — seans sonu flatten: etkisi yok denecek kadar az

| sembol | B−A |
|---|---:|
| GER40 / NAS100 / US30 / XAUUSD | **0** (flatten sayısı değişmiyor — o kapanışlar hafta sonu boşluğu) |
| JPN225 | +3,82 R |
| SpotBrent | +1,52 R |

Kitap geneli ~**+5,3 R**, ve yalnız M5'te. JPN225'in 120+ kovası 158→169
işlem, +139,9→+145,3 R — seans sonu M5'te biraz kuyruk kesiyor ama miktar
önemsiz. **Kural çıkmıyor.**

### Kalan

Getiri eğrisi için kuyrukta CHOP-1 kaldı (`cooldown_sec` etkisiz,
`skip_after_loss` yalnız kâğıtta, `adx_min` üç sembolde 0 — 4o). Bayrak
(`reverse_on_signal`) varsayılan kapalı birleşti; soru cevaplanabilir kalsın
diye duruyor.

---

## 4t. CHOP-1 — üç kol, uygulanacak hiçbir şey (19.08)

Getiri eğrisi kuyruğunun son adayı. Üçü **ayrı ayrı** ölçüldü.

**1a `cooldown_sec`:** beş sembolde **bit-özdeş**. Tek hareket XAUUSD 2 bar
(n −7, **+1,81 R**, maxDD 43,6→40,4). Sebep 4o'da yazılıydı ve doğrulandı:
`max_open=1` iken soğuma fill'den başlıyor, tutma süresi çoğu zaman tavandan
uzun, yani soğuma pozisyon açıkken bitiyor. **Etkisiz kalıyor.**

**1b `skip_after_loss`: altı sembolde de zararlı.**

| sembol | A (kapalı) | B (açık) | B−A |
|---|---:|---:|---:|
| GER40 | +176,67 | +27,65 | **−149** |
| NAS100 | +109,19 | +36,06 | −73 |
| XAUUSD | +83,33 | +30,67 | −53 |
| JPN225 | +67,15 | +31,57 | −36 |
| SpotBrent | +20,71 | +11,99 | −9 |
| US30 | +46,16 | +38,46 | −8 |

Zarardan sonra beklemek işlem sayısını düşürüyor ve **kuyruğu kesiyor** —
REV-1'in aynası. Kâğıtta duran bu bayrak canlıda karşılığı olmadığı için
bugüne kadar zararsızdı; artık **ölçülmüş biçimde zararlı**, yani silinmeli.

**1c `adx_min` (JPN225/NAS100/US30'da 0):**

| | 0 | 10 | 15 | 20 | 25 |
|---|---|---|---|---|---|
| JPN225 net/calmar | **+67,15**/3,98 | +63,47/3,37 | +48,37/2,45 | +21,40/1,57 | +18,03/2,20 |
| NAS100 | +109,19/2,31 | +111,97/2,40 | +107,44/**2,84** | +70,97/1,78 | +16,44/0,41 |
| US30 | +46,16/2,03 | +50,96/2,24 | +47,90/**2,52** | +27,79/1,71 | +25,93/1,88 |

NAS100 ve US30'da `adx_min=15` calmar'ı ~%23 iyileştiriyor. **Uygulanmıyor** —
bu, **dokunulmamış testi seçim için kullanmak** olurdu ve holdout'u testlikten
çıkarırdı. Aynı red 18.08 gecesi L2b'de stop genişliği için verildi; tutarlı
olmazsa o red de anlamsızlaşır. Ayrıca `adx_min` zaten arama ekseni ve arama
0 seçti — arama ile holdout'un anlaşmaması 4n'de dört kesitte ölçülmüş
durumda, yeni bilgi değil.

### Getiri eğrisi kuyruğu kapandı, uygulanan sıfır

REV-1 (felaket), FLAT-2 (~+5 R, yalnız M5), CHOP-1a (etkisiz), 1b (zararlı),
1c (holdout'a dokunmadan uygulanamaz). **Beş aday, uygulanabilir tek kural
yok.**

Geriye kalan dürüst kaldıraçlar ölçüm değil **sabır**: FWD-2 penceresi
(sistem kâr ediyor mu, hâlâ bilmiyoruz), 100 işlemde lot çarpanı tetikleyicisi,
ve ızgara küçültmenin getireceği tekrarlanabilirlik (D1b-f).

---

## 4u. XAUUSD devre dışı, SpotBrent kalıyor (19.08)

Operatör ikisini de sordu. Kararlar **ayrı**, çünkü sorunları aynı değil.

### Canlı sicil, riske normalize edilince

XAUUSD ve SpotBrent %0,20 riskle koştu, diğerleri %0,80. Aynı ölçeğe
getirince:

| sembol | gerçek risk | n | net $ | %0,80'e normalize |
|---|---:|---:|---:|---:|
| **SpotBrent** | 0,20 | 38 | −122 | **−489** |
| XAUUSD | 0,20 | 98 | −89 | −357 |
| GER40 | 0,80 | 65 | −151 | −151 |
| NAS100 | 0,80 | 75 | −94 | −94 |
| US30 | 0,80 | 45 | −33 | −33 |
| JPN225 | 0,80 | 68 | +39 | +39 |

**Riske göre en kötüsü SpotBrent.** Canlı performansa bakarak karar
verilseydi yanlış sembol silinirdi.

### XAUUSD — silindi, sonra geri alındı (19.08). Gerekçem yanlıştı.

**Yazdığım gerekçe:** minimum lot niyetin 1,1–2,2 katını aldırıyor, kasa bu
sembolü boyutlandıramıyor.

**Ölçüldü, yanlıştı.** Bakiye 2.001 $, %0,80 niyet = 16,01 $. Minimum lot
riskleri: XAUUSD **9,29** · JPN225 14,93 · NAS100 6,58 · US30 6,03 · GER40
5,78 · SpotBrent 0,94. **Altısı da sığıyor.** Taşma enstrümandan değil,
XAUUSD'nin **%0,20'de koşmasından** geliyordu — SpotBrent'inki gibi eskiden
kalma bir ayar.

Silindikten sonra kalan gerekçeler de tutmadı. Kitapla karşılaştırma:

| sembol | beklenti (R/işlem) | calmar | holdout n |
|---|---:|---:|---:|
| JPN225 | +0,201 | 3,74 | 315 |
| SpotBrent | +0,182 | 4,35 | 120 |
| **XAUUSD** | **+0,169** | 1,96 | **504** |
| GER40 | +0,139 | 5,30 | 1294 |
| US30 | +0,113 | 2,00 | 403 |
| NAS100 | +0,090 | 1,98 | 1045 |

Beklentide **altıda üçüncü**, örneklemde ikinci, ve kitaptaki **tek gerçek
doğrulanmış damga** onda (`validated=True`, retention 1,158). Düşük calmar
zayıf kenardan değil derin düşüşten (maxDD 43,6); NAS100 aynı calmar'da ve
daha kötü beklentide. **"Kitabın en zayıfı" hiç doğru değildi.**

Canlı sicili de bozuk bir sürümden geliyor: %0,20 riskle ve minimum lot
taşmasıyla koştu, yani bu konfig **hiç düzgün çalıştırılmadı**.

**Geri alındı (19.08), %0,80 ile** — kitabın geri kalanıyla aynı seviye, ve
lot tabanının riski belirlemesini bitiren şey. Arşivden konfig + 40 `opt_runs`
birlikte döndü.

**Ders:** yapısal görünen bir gerekçe (`kasa boyutlandıramıyor`) ölçülmeden
kullanıldı ve bir sembol yanlış yere silindi. Aynı gün içinde ölçülüp geri
alındı; kalıcı zarar arşiv sayesinde olmadı. **Yapısal iddia da ölçüm ister.**

### SpotBrent — kalıyor, ama izlemede

Riske normalize edilmiş en kötü sicil onda, **ama n=38** ve o dönemin çoğu
çalkantı dönemi. Kâğıtta kitabın **en iyi calmar'ı** (4,35), boyutlandırması
temiz (min lot sorunu yok), ve riski **19.08 sabahı 0,20 → 0,80'e çıkarıldı** —
o değişiklik henüz hiç test edilmedi.

**Tetikleyici: 30 işlem.** Bu sabahki risk artışından sonraki 30 işlemde
gerçekleşen R/işlem sıfırın anlamlı altındaysa risk 0,20'ye döner ya da sembol
kapanır. En zayıf canlı sicile sahip sembolün riskini dört katına çıkarmış
olmak, sıkı bir gözden geçirmeyi hak ediyor.

Kitap artık **5 aktif sembol**: GER40, JPN225, NAS100, US30, SpotBrent.

---

## 4v. Damga sapması artık sürekli kontrol ediliyor (19.08)

18.08 gecesi elle koşulan denetim (4j) kalıcı hâle geldi:
`Optimizer.stamp_drift()` + `GET /api/analysis/stamp-drift`.

İki tasarım kararı raporu gürültüden kurtardı:

1. **Yalnız ailenin okuduğu alanlar** karşılaştırılıyor
   (`opt_fields_read | ENGINE_OPT_FIELDS`, `OPT_FIELDS` ile kesişim).
   `stoch_flip` dokuz alan okuyor, damga kırk tane taşıyordu — hepsini
   karşılaştırmak §5'in birinci arıza sınıfını denetim tarafında yeniden
   kurardı. **Kesişim de şart:** `atr_period` motor alanı ve damgaya hiç
   yazılmıyor; kesişim olmasa **her satır kırmızı** olurdu (Cursor yakaladı).
2. **Makas kalibrasyonu artık kendi kaydını bırakıyor**
   (`spread_recalibrated_from/to`). Kayıt varsa ve canlı `to` ile uyuşuyorsa
   `calibrated`, yoksa `unexpected`. "Kalibrasyon değiştirdi" ile "biri elle
   değiştirdi" farklı şeyler ve ikincisi 18.08'de iki kez oldu.

**XAUUSD'nin kaydı geriye dönük yazıldı** — kalibrasyon 18.08 17:20:14'te
oldu, kayıt özelliği 19.08'de eklendi. Log iki ucu da taşıyor
(`max_spread_atr 0.05 -> 0.25`, gerekçesiyle), o yüzden uydurma değil
aktarma. Yapılmasaydı rapor açıklanmış bir şey için kalıcı kırmızı taşırdı, ve
**hep kırmızı gösteren kontrol okunmayan kontroldür**.

Bugünkü durum: **açıklanmamış sapma 0.** Beş sembol tamamen temiz, XAUUSD'nin
tek farkı `calibrated` olarak işaretli.

Ayrıca `skip_after_loss` `simulate`'ten **silindi** (4t/CHOP-1d): aramada
yoktu, `engine.py`'de yoktu, altı holdoutta da R kaybettiriyordu. Duran bayrak
bir sonraki "bir deneyelim" karşılaştırmasını kâğıt ≠ canlı yapardı.

---

## 4w. Başabaş kilidi yok — üç sembol +2 R'yi geri verebiliyor (19.08)

Otopsi halkası ilk dört kaydında operatörün "aldığımızı veriyoruz" cümlesini
ölçülebilir hâle getirdi:

```
GER40    MFE +1,42 R  ->  kapanis -1,00 R   masada 2,42 R
JPN225   MFE +0,91 R  ->  kapanis -1,00 R   masada 1,91 R
```

**Mekanik sebep:** trail en iyi fiyatın `trail_step_atr` ATR gerisinden gelir,
yani trailing stop entry'yi ancak kâr `trail_step_atr`'yi aşınca geçer.

| sembol | sl_atr | trail_step | stop başabaşa gelir |
|---|---:|---:|---:|
| **GER40** | 1,00 | 2,20 | **+2,20 R** |
| **NAS100** | 1,00 | 1,80 | **+1,80 R** |
| **US30** | 1,00 | 1,60 | **+1,60 R** |
| JPN225 | 2,50 | 2,50 | +1,00 R |
| XAUUSD | 1,00 | 0,40 | +0,40 R |
| SpotBrent | 4,00 | 1,50 | +0,38 R |

Üç sembolde trail adımı stop mesafesinden **geniş**: bir işlem +2,19 R kâra
çıkıp yine tam stop yiyebilir. `backtest.py:792` bunu kendi yorumunda
söylüyor — *"There is no separate breakeven step"*. **Sistemde başabaş kilidi
yok**, tek koruma trail.

Not: bu ayarlar aramanın seçtiği değerler (GER40 `trail_step` ızgara
**tavanında**), yani unutulmuş değil — arama gevşek trail istiyor, ki 4g/4l
ile tutarlı: kâr kuyrukta.

BE-1 ölçüldü (`9fe64ea`, bayrak varsayılan kapalı, arama geçirmiyor).
Altı canlı holdout, `breakeven_at_r` ∈ {0, 0,5, 1,0, 1,5, 2,0}:

| eşik | calmar iyileşen | 120+ kuyruk kaybı |
|---|---|---|
| 0,5 | 3 | JPN225 −%22, SpotBrent −%21 |
| 1,0 | 3 | yok |
| **1,5** | **5** (biri eşit, hiçbiri kötü değil) | **hepsi <%1** |
| 2,0 | 3 | yok |

`1,5` **kilitli kuralı geçiyor**. GER40 calmar 3,91 → **4,36** (net R
+175,49 → +178,52), XAUUSD 1,90 → **2,23** (+82,99 → +86), NAS100 2,33 →
2,39, US30 2,15 → 2,21, JPN225 3,81 → 3,87, SpotBrent değişmiyor (trail
zaten ~0,38 R'de entry'yi geçiyor).

**Uygulanmadı.** Beş değeri holdout'ta deneyip en iyisini seçmek, holdout'u
seçici hâline getirir; ön kayıt cherry-picking'i engeller ama **seçimin
nerede yapıldığını** değiştirmez. Aynı red 18.08'de L2b'de (stop genişliği) ve
19.08'de CHOP-1c'de (`adx_min`, calmar +%23) verildi — üçüncüsünde "ama bu
sefer sonuç çok iyi" demek önceki ikisini anlamsız kılar.

**BE-2 ölçüldü — doğrulama seçemedi.** Altı sembol için **altı ayrı eşik**:

| sembol | doğrulamanın seçtiği | holdout'ta |
|---|---:|---|
| GER40 | 0,5 | **−32 R / −0,89 calmar** |
| JPN225 | 1,0 | −4 R / +0,95 |
| NAS100 | 1,5 | +1 R / +0,07 |
| US30 | 0 | değişmiyor |
| SpotBrent | 0 | değişmiyor |
| XAUUSD | 1,0 | +22 R / +1,74 |

Holdout'un temiz kazananı (1,5) doğrulamada yalnız NAS100'de birinci; üç
sembolde canlıdan **kötü**. GER40 doğrulamada **her eşikte negatif** — o dilim
ayırt edemiyor. **4n'in beşinci bağımsız doğrulaması.**

**Uygulanmadı**, ve cazip çıkış da reddedildi: `1,5` işlem sayısını neredeyse
değiştirmiyor (GER40 +24) oysa `0,5` şişiriyor (+279), buradan "en az yan
etkili müdahale" diye dilimlerden bağımsız bir gerekçe kurulabilirdi — ama o
gerekçe **holdout sonucu görüldükten sonra** kuruldu. Sonradan bulunan
bağımsız gerekçe bağımsız değildir.

**BE-3:** `breakeven_at_r` **arama eksenine** eklenecek ({0, 1.0, 1.5}) —
sistemin bu soruyu cevaplamak için zaten sahip olduğu mekanizma; her parametre
böyle seçiliyor. Bedeli: ızgara 3× (stoch_flip 28.800 → 86.400), yani GER40'ın
tam tarama bütçesi yetmez. Süre ölçülüp determinizmi kaybetmeden ödenebilir mi
bakılacak.

---

## 4x. Endeks eforu: deterministik ailelerle arama (19.08)

Operatör kararı: endeksler kitapta kalıcı, emtia Claude'un takdirinde, efor
**endeks verimine**.

**D1b-f kapandı:** US30 budaması NAS100/GER40'ta geride, budanmış GER40
kapıdan düşüyor. Izgara küçültmeyi **transferle** yaymak çalışmıyor; her aile
için ayrı budama türetmek aynı kirlenmeyi geri getirir.

**Asıl kaldıraç:** dört endeksin üçü çekiliş rejiminde — NAS100
(mtf_pullback, 622k), US30 (t3_stoch, **1,43 G**, tam tarama imkânsız),
JPN225 (dual_t3, 2,07 M). Yalnız GER40 deterministik (19.08 sabahı,
`strategy_max_combos: {stoch_flip: 28800}`).

**IDX-1:** dört endeksi **yalnız tam taranabilir altı ailede** ara
(aroon_flip 2.880 · parabolic_flip 8.640 · wavetrend_flip 8.640 ·
stoch_flip 28.800 · macd_flip 46.080 · st_trend 57.600), her aile kendi
ızgara boyutunda. Altısı birden 95 dk (2 işçi) → botun 14 işçisiyle
**~14 dk sembol/TF**. Dört endeks tek TF'de ~1 saat. Ödenebilir.

**Neden bu uygulanabilir, öncekiler değildi:** seçimi Claude yapmıyor.
Normal `walk_forward` çalışıyor — seçim arar, doğrulama sıralar, holdout
yargılar, mevcut kapı karar verir. Ve sonuç **deterministik** olduğu için
yarın tekrar koşulduğunda aynı çıkar. Bugün üç aday (L2b stop genişliği,
CHOP-1c `adx_min`, BE-1/2 başabaş) tam da bu yüzden reddedildi.

Beklenti önden: küçük ızgaralı ailelerin ortalama retention'ı daha iyi
(aroon_flip 1,13 / macd_flip 1,11 vs t3_stoch 0,68) ama popülasyon gözlemi ve
karşı örneği var (wavetrend_flip 0,39). Kazanan çıkmayabilir; o da sonuçtur.

---

## 4y. M1 fiyat dışı, ve verimsizlik TF'den gelmiyor (19.08) — KAPALI

Operatör sordu: performans kaybı zaman diliminden mi, M1 iş görür mü?

**Maliyet/R = spread / stop mesafesi**, ve stop ATR cinsinden. ATR bar
küçüldükçe küçülür, yani aynı spread hızlandıkça riskin daha büyük bir payına
denk gelir. Ölçüm (sl = 1 ATR varsayımıyla):

| sembol | M1 | M5 | M15 | M30 |
|---|---:|---:|---:|---:|
| SpotBrent | **%42,0** | %14,6 | %9,3 | %7,1 |
| JPN225 | %23,9 | %7,8 | %3,2 | %2,5 |
| GER40 | %21,7 | %5,9 | %2,8 | %2,3 |
| US30 | %12,7 | %4,6 | %2,1 | %2,2 |
| NAS100 | %6,6 | %3,0 | %1,1 | %1,0 |
| XAUUSD | %4,7 | %1,8 | %0,6 | %0,5 |

Ölçülen kenar ~0,1–0,2 R/işlem. M1'de SpotBrent'te maliyet kenarın **iki-dört
katı**, GER40/JPN225'te kenarın tamamı, en ucuz ikisinde bile üçte biri.
**M1 aritmetik olarak kapalı** — M1-1 görevi de bu yüzden konusuz kaldı
(öznesi XAUUSD'ydi).

**Verimsizlik TF seçiminden gelmiyor:** `timeframes` zaten `M5/M15/M30` ve
`strategy_timeframes` haritası **boş**, yani her aile üçünü de deneyebiliyor.
Mevcut TF'ler varsayılan değil, aramanın kararı. Ve maliyet aritmetiği
aramadan bağımsız: hızlanmak mekanik olarak pahalılaşmaktır.

Yön tersine bakıyor: en ucuz uç **M30**. JPN225 ve SpotBrent M5'te koşuyor ve
M30'un 2–3 katı maliyet ödüyor — arama orada yeterli ek kenar bulmuş olmalı.
IDX-1 endeksleri bütün TF'lerde yeniden arayacağı için JPN225'in TF'si o
turda kendiliğinden sınanacak. Bu, 4g/4l ile de tutarlı: kâr uzun tutulanda.

---

## 4z. Otomatik yeniden optimizasyon durduruldu (19.08) — pencereyi korumak için

`auto_reoptimize` **False** yapıldı. Sebep operasyonel ve acildi: dört sembol
48 saatlik freni çoktan aşmıştı (US30 **93 saat**, JPN225 81, SpotBrent 81,
NAS100 80), yani denetçi herhangi bir anda konfiglerini **değiştirebilirdi**.

Değiştirseydi FWD-2'nin 16.08'den beri biriken penceresi sıfırlanırdı — ve o
pencere, sistemin kâr edip etmediğini söyleyebilecek **tek** ölçüm (n=33, hâlâ
sıfırdan ayırt edilemiyor).

**Gerekçe yalnız pencere değil.** 4n/BE-2 ile beş bağımsız ölçüm gösterdi ki
hiçbir iç ölçü dışarıyı öngörmüyor. Dolayısıyla otomatik bir apply, "onarım"
kılığında **bilgisiz bir konfig değişimi**ne yakın. 18.08'de XAUUSD'yi bu
mekanizma M5/`t3_stoch`'tan M15/`burst`'e taşıdı; damgası geçerliydi ama
pencerenin ortasında oldu.

**Korumalar duruyor.** `auto_reoptimize` yalnız `_queue_reoptimization`'ı
kapatıyor (`supervisor.py:1007`). Ayrı ve açık kalanlar: karantina (11 ardışık
zarar → 1 saat), izleme risk ölçeği (PF<1 → ×0,6), düşüş ölçeklemesi
(soft %3,5 / hard %7, taban 0,6).

**Geri açma tetikleyicisi:** FWD-2 kesin bir örnekleme ulaştığında (R/işlem
güven aralığı sıfırı dışlayacak kadar), ya da bir sembol tekrar tekrar
karantinaya girerse. **Bu ayar unutulmamalı** — kapalı bırakılmış bir
otomatik onarım, açık bırakılmış kadar tehlikelidir; farkı, hangisinin
unutulduğunu bilmemektir.

---

## 5a. Arama tarafında ölçülecek şey kalmadı (20.08) — IDX-1 ve BE-3

**IDX-1 sonucu: hayır.** Dört endeks, altı deterministik aile, canlı TF:

| endeks | kazanan | kapı | kazanan holdout | mevcut |
|---|---|---|---:|---:|
| GER40 | st_trend/M30 | ✗ | −0,43 | +174,49 |
| JPN225 | macd_flip/M5 | ✗ | −12,58 | +65,46 |
| NAS100 | parabolic_flip/M30 | ✓ | +75,62 | **+108,31** |
| US30 | stoch_flip/M30 | ✗ | −7,56 | +49,09 |

Dördün üçünde kazanan kapıdan geçemedi; geçen tek aday mevcut konfigden
**−32,7 R**. Deterministik ailelerle arama daha iyi konfig üretmiyor.

**DÜZELTME (20.08, Cursor denetimi).** Yukarıdaki tabloyu "boru hattı
+256,92'lik `stoch_flip`'i eleyip −0,43'lük `st_trend`'i seçti" diye okumuştum.
**Yanlış.** `optimizer.py:880-882`:

```
usable = [a for a in attempts if a.get("ok") and a.get("validated")]
if not usable:
    usable = [a for a in attempts if a.get("ok")]      # teselli dali
```

GER40'ta altı ailenin **altısı da** `validated=false`. Apply yolu
`report.get("validated")` şartına bağlı, dolayısıyla **hiçbiri uygulanmazdı**;
kitap incumbent'ta kalırdı. Raporlanan "kazanan", kapı herkesi reddedince
`ok` olanlar arasından **adlandırma** yapan teselli dalının çıktısı — aramanın
önerisi değil. **Boru hattı hiçbir şey seçmedi.**

Doğru okuma: `stoch_flip` hem arama blend'inde hem holdout'ta birinci,
doğrulamada ikinci; `validated=false` büyük olasılıkla doğrulama `_slice_ok`
(PF < 1,10). Bu 4n'in bir satırı, **yeni bir kanıt değil**.

**BE-3 iptal edildi.** Süre sorun değildi (86.400 tam tarama 73 dk / 2 işçi,
botun işçileriyle ~10 dk). Mantık çöktü: `breakeven_at_r`'yi ızgaraya koymanın
tek anlamı değeri **boru hattının seçmesiydi**, ve altı ölçüm o boru hattının
seçemediğini gösteriyor. Seçemeyen bir seçiciye eksen eklemek hatayı büyütür;
üstelik `stoch_flip` bütçesini 3× artırıp GER40'ın determinizmini riske atardı.

BE-1 bayrağı kodda, varsayılan kapalı, arama geçirmiyor — soru cevaplanabilir
kalsın diye.

### Sonuç — ve bu da düzeltildi

Önce "altı bağımsız kesitte aynı sınır, arama tarafında ölçülecek şey kalmadı"
diye yazmıştım. **İkisi de fazla genişti** (Cursor denetimi, 20.08):

**"Altı bağımsız" değil.** Altısında da *eksen* değişti, **seçici hiç
değişmedi** — hepsi aynı `walk_forward` kesiti, aynı `rank_for_selection`
doğrulama skoru, aynı `MIN_OOS_PF = 1.10`. Altı ayrı yargıç değil, **tek
makinenin altı kez sondalanması**. Üstelik L2b/L2d zaten 4n'de "kanıtlandı
demiyoruz" diye kayıtlıydı (n=10, SE 0,33, iki sembolde ters işaret); onları
ayrı kanıt saymak aynı zayıf ρ'yu iki kez tartmak.

**"Arama tükendi" değil, "bu seçici tükendi".** Tükenen şey `walk_forward` +
doğrulamayla aile seçimi + 1,10 eşiği. Makineyi değiştirmeden başka yerde
aramak da aynı sonucu üretir; makineyi değiştirmeden "arama bitti" demek de
aynı sonucu **gizler**.

**Sızıntı, ayrıca:** `validated = _slice_ok(validation) and _slice_ok(holdout)`
— yani holdout PF'si apply kapısının **içinde**. Muhafazakâr yönde (kötü
holdout uygulanmaz) ama "holdout yalnız yargılar" cümlesi bu yüzden tam doğru
değil, ve "bağımsız yargıçlar" iddiasını da çürütüyor: hepsi aynı dilim
tanımını ve aynı 1,10'u paylaşıyor.

**IDX-1'in kendi kurgusunda iki eksik daha:** yalnız *canlı* TF koşuldu (4y
JPN225'in M5'ini M30 ile sınayacağını yazmıştı, sınanmadı), ve incumbent
aileler (`mtf_pullback`, `t3_stoch`, `dual_t3`) taramaya **dahil edilmedi**.
Dolayısıyla tablo "küçük ızgaralı aileler, bu seçiciyle, canlı TF'de,
incumbent'ı geçmedi" der — "dört endekste arama tükendi" demez. Ayrıca
dilim uzunlukları kıyaslanamaz (JPN225 ~92 gün vs GER40 638 gün).

**Ayakta kalan dar hâli:** 4n'in kendi cümlesi — *daha iyi seçmek değil, daha
az seçmek*. Ve FWD penceresi hâlâ tek dış doğruluk kaynağı. Ve donanım tarafında ölçülen tek somut
kazanç determinizm: ~32-36 çekirdek / 64 GB ile altı sembolün beşi tek çalışma
gününde tam taranabilir (US30 hariç, ızgarası 1,43 G).

---

## 5b. FWD haftalık raporu — "ne zaman bileceğiz" artık bir sayı (20.08)

`cursor/_fwd_weekly.py` → her sabah tek satır, aynı sütunlar. Pencere
`entry_blocks_since` = 16.08 18:34 sunucu; bar damgaları `gmtime`;
`max_open=1`.

İlk satır (20.08, pencere **3,75 gün**):

| | n | değer | SE | sıfırdan ayırt | **gereken n** |
|---|---:|---:|---:|---|---:|
| kâğıt | 57 | +0,4606 R/işlem | 0,339 | hayır | **124** |
| canlı kapalı | 87 | −1,50 $/işlem | 1,87 | hayır | **538** |

Take 0,75 (43/57, SE 0,057). Kâğıt net +26,25 R, canlı **−130,68 $**.
Otopsi halkası n=20 (<50, tablo yok).

**`n→ayırt` sütunu raporun asıl değeri:** mean/SE oranı sabit kalırsa canlı
tarafta `|mean| > 2 SE` için **~538 işlem** gerekiyor. Günde ~23 işlemle
bu **~23 gün**, yani **eylül ortası**.

Bu, "sistemin kâr edip etmediğini bilmiyoruz" cümlesini plan yapılabilir bir
şeye çeviriyor. Ve şunu da söylüyor: bu tarihten önce alınacak "sistem
çalışmıyor" ya da "çalışıyor" kararı **veriye değil sabırsızlığa** dayanır.

Not: canlı 87 işlem, kâğıt 57 üretmiş — canlı hâlâ ~1,5 katı alıyor. Pencerenin
ilk iki günü `max_positions=2` dönemiydi (1'e iniş 18.08 18:36); pencere
ilerledikçe bu oran düzelmeli. Düzelmezse giriş kapısında ayrıca bakılacak.

---

## 5c. Teselli dalı kaldırıldı, ve eşit-yetki protokolü ilk gününde işledi (20.08)

`_finish_symbol`, hiçbir aday kapıdan geçmediğinde **doğrulanmamışlar
arasından bir kazanan adlandırıyordu**. Apply onu almıyordu (zaten `validated`
şart) ama **rapor alıyordu**, ve okunan şey rapor. IDX-1'de bu, "GER40'ın
araması −0,43'lük adayı +256,92'lik olana tercih etti" satırını üretti;
Claude onu DEVAM'a yazdı ve operatöre söyledi. **Seçilen şey hiçbir şeydi.**

Artık reddedilen tarama bunu söylüyor: `ok: True`, `best: None`,
`keep_reason`, ve `opt_runs`'a **kazanansız bir satır** — yani "arama koştu,
hiçbiri geçmedi" görünür oluyor, eskiden sessizdi. `tried` her iki yolda da
duruyor (bugünkü denetim onu okuyarak yapıldı). Panel `keep_reason` gösteriyor.
(`4848e31`, fail-first: `test_unvalidated_pool_does_not_name_a_winner.py`.)

**Bunu Cursor buldu**, kendi ölçümüne dair Claude'un okumasını denetlerken —
eşit yetki protokolünün (§1, `686ba8f`) ilk çıktısı. Aynı denetimde iki hüküm
daha daraltıldı: "altı bağımsız kanıt" → tek seçicinin altı sondası, ve
"arama tükendi" → **bu seçici tükendi**. Ayrıca `validated`'ın holdout PF'sini
apply kapısına soktuğu sızıntı da orada yakalandı.

Küçük borç: `opt_runs`'a artık `strategy: None` / `params: {}` satırları
girebiliyor. Bugünkü altı analiz `.get()` kullandığı için kırılmıyor; doğrudan
indeksleyen bir okuyucu patlar.

---

## 5d. ROLL-1: seçim başarısızlığı rejime bağlı değil (20.08)

5b'nin daralttığı hüküm — *"arama değil, **bu seçici** tükendi"* — bir soru
bırakmıştı: bu, son pencereye mi özgü, yoksa iç ölçü **hiçbir** dilimi
öngörmüyor mu? Cursor ölçtü (arama yok, ızgara yok, konfig seçilmiyor;
yalnız altı canlı damganın 6 genişleyen kesitte yeniden puanlanması).

| kesit | ρ(doğrulama sırası, sonraki dilim) | SE | 2 SE'yi aşıyor |
|---|---:|---:|---|
| 0 | −0,26 | 0,48 | hayır |
| 1 | **−0,83** | 0,28 | evet |
| 2 | +0,20 | 0,49 | hayır |
| 3 | **+0,89** | 0,23 | evet |
| 4 | −0,03 | 0,50 | hayır |
| 5 | +0,14 | 0,49 | hayır |

**Ortalama 0,019.** Aşan iki kesit **ters işaretli**; en yeni iki kesit (bugüne
en yakın) sıfıra en yakın. **"Yalnız son dilim bozuldu" deseni yok.**

Sembol içi (aynı damga, 6 kesitte doğrulama↔sonraki dilim): GER40 −0,14,
JPN225 −0,60, NAS100 −0,20, US30 −0,66, XAUUSD −0,60, SpotBrent +0,66.
**Beşinin nokta tahmini negatif**, hiçbiri ayırt edilebilir değil.

**Ne kurar, ne kurmaz.** Kurduğu: seçim başarısızlığının yalnız güncel rejime
ait olduğuna dair **kanıt yok** — yani "bu seçiciye güvenebileceğimiz bir
dönem" aramanın dayanağı kalmadı. Kurmadığı: başarısızlığın evrensel olduğu.
Her ρ **n=6**, hepsi güçsüz, ve Cursor bunu her satırda yazdı.

Kurgu notu: eşit *bar* payı eşit *takvim* değil — GER40 M30 7579 gün, JPN225
M5 463 gün kapsıyor, yani kesit 0'da GER40'ın doğrulaması 2019, JPN225'inki
2025. Kaba, ve Cursor kabalığı işaretledi (IDX-1'de aynı hatayı yapmıştık).
Yine de ortalama ~0.

**Sonuç:** 5b'nin dar hâli ayakta. Arama tarafında yapılacak yeni ölçüm yok
**ve bu sefer hüküm ikimizin denetiminden geçti.**

---

## 5e. `edge_scale` göreli — kitabı değiştirmek herkesin lotunu değiştirir (20.08)

Canlı boyutlandırma yolunu denetlerken bulundu. `RiskManager.edge_scale`:

```
edges = {enabled sembollerin holdout net_r / max_dd_r}
return clamp(sqrt(mine / median(edges)), 0.6, 2.2)
```

Medyan **kitabın kendisinden** geliyor, yani bir sembol eklemek ya da çıkarmak
**diğer beşinin lot çarpanını da** değiştiriyor.

Bugünkü calmar'lar: GER40 5,30 · SpotBrent 4,35 · JPN225 3,74 · US30 2,00 ·
NAS100 1,98 · XAUUSD 1,96 → medyan **2,868**.

XAUUSD (medyan altı) silindiğinde medyan **3,74**'e çıkıyor ve:

| sembol | 6 sembolle | XAUUSD silinince |
|---|---:|---:|
| GER40 | 1,36 | **1,19** (−%12) |
| JPN225 | 1,14 | **1,00** (−%12) |
| NAS100 | 0,83 | **0,73** (−%12) |

**Medyan altı bir sembolü çıkarmak, geri kalan herkesin pozisyonunu
küçültüyor.** Tasarım gereği (göreli boyutlandırma) ama sonucu şu: 19–20.08'de
kitap üç kez değişti (SpotBrent riski, XAUUSD sil, XAUUSD geri al) ve her
seferinde **altı sembolün altısının lotu** değişti — kimse istemeden.

**Kural olarak kaydediliyor:** kitaptan sembol eklemek/çıkarmak, kalan
sembollerin risk profilini de değiştiren bir karardır ve öyle sunulmalıdır.
NAS100'ün 50 işlemlik tetikleyicisi dolduğunda bu, kararın açık bir parçası
olacak — "NAS100'ü sil" aynı zamanda "GER40'ın lotunu %12 küçült" demek.

**Yan not, dürüstlük kaydı:** bu, bir uyuşmazlık kovalarken bulundu ve
uyuşmazlık **benim hatamdı** — altı elemanlı listenin medyanını ortadaki tek
elemandan aldım (3,74), gerçek medyan 2,868. Kodun değerleri log'la birebir
tutuyor. Denetleyenin de denetlenmesi gerekiyor; bu sefer denetleyen bendim.

---

## 5f. "Etkisi var mı" süpürmesi — kapı bizden bir adım ötede (20.08)

AUDIT-A "okunuyor mu" diye sormuştu; bu süpürme **"mevcut değeriyle davranışı
değiştirebilir mi"** diye sordu (4o'da bulunan sınıf). Cursor koştu.

### Kapıya ulaşamayan üç ayar

| ayar | değer | neden ulaşılmıyor |
|---|---|---|
| `cooldown_sec` | altıda 120 | M5 barı 300 s; soğuma sonraki kapanıştan önce doluyor |
| `max_total_positions` | 100 | kitabın açabileceği en fazla 6 |
| **`max_concurrent_risk_pct`** | **15** | 6 × %0,80 × EDGE_MAX 2,2 = **%10,56** |

**Üçüncüsü önemli ve "ölü" demek yanlış olur.** Kapı %1,136 sembol riskinden
itibaren bağlayıcı oluyor. Bekleyen lot çarpanı tetikleyicisi 1,25× ile bizi
%1,0'e taşır (hâlâ altında); **1,5× ile %1,2 ve kapı devreye girer.** Yani
sistemin kendi freni, bir sonraki ölçeklenme kararının **tam bir adım
ötesinde** duruyor — bu, ölçeklenirken bilinmesi gereken bir şey.

Kayda geçsin: bu oturumda operatöre defalarca "nominal risk %4,80, kapı %15"
dendi, sanki kapı koruyormuş gibi. **Koruyamazdı.**
(`tests/test_current_values_do_not_reach_these_gates.py` ikisini kilitliyor.)

### Belge yalanı: `_dual_t3` docstring'i

*"There is no ... ADX regime gate"* diyordu. Kod `adx_min`/`adx_max` okuyup
`_regime` uyguluyor ve **SpotBrent'te ikisi de canlı** (15 ve 25). Düzeltildi.
Çalışan bir kapıyı inkâr eden docstring, okuyanı o ayarı akıl yürütmesinden
çıkarmaya iter — damganın ölçmediği konfigi tarif etmesiyle ve yedeğin
"her akşam çalışır" demesiyle **aynı sınıf**.

### Okunmayan ama dolu on alan

GER40 `adx_min=15` / `st_mult=1,5`, SpotBrent `htf_factor=12` /
`t3_accel_min=0,04` / `min_body_ratio=0,25` / `cost_rank_max=0,5`, US30
`st_mult=2,0` / `cost_rank_max=0,3`, NAS100 `t3_accel_min=0,01`, JPN225
`cost_rank_max=0,5`. Aileleri okumuyor (AUDIT-D bit-özdeşliği kanıtladı),
davranış değişmiyor — ama panelde duruyor.

**Sıfırlanacak (Cursor'ın yeşil kararı, kitap düzleşince uygulanacak).**
Uygulama anı zamanlama meselesi: canlı kitaba yazmak bot durdurmayı
gerektiriyor ve kozmetik bir düzeltme için açık pozisyonların trail'i
kesilmez.

**Ve bir bağlantı, unutulmasın:** bu alanlar bugün ölü çünkü *o aile* onları
okumuyor. **Aile değişirse canlanırlar** — ve o gün `adx_min`'in 0 mı 15 mi
olduğu fark eder. 0 model varsayılanı ve tarafsız, 15 önceki ailenin artığı;
yani sıfırlamak daha güvenli. Ama **"artık okunmuyor" ile "bir daha hiç
okunmayacak" aynı şey değil.** `auto_reoptimize` kapalı olduğu için
kendiliğinden aile değişmiyor ve her apply zaten aranan params'ı yazıyor —
bu iki koşuldan biri değişirse not tekrar okunmalı.

### Bulunamayanlar (boş liste de sonuç)

min>max klemp yok · birbirini geçersiz kılan iki *okunan* ayar yok ·
`daily_loss_pct=22` gevşek ama ulaşılabilir · marj kapıları bu hesapta nadir
ama imkânsız değil.

---

## 5g. Kaybedenler girişte ayırt edilmiyor (21.08) — LOSS-1'in temiz hâli

18.08'in kayıp anatomisi (4g) yalnız **sonuca koşullu** alanları
kullanabiliyordu ve bunu yazmıştı. Otopsi halkası (POST-1) girişteki kapı
değerlerini de tutuyor; n=36'da (16 kazanan / 20 kaybeden) ilk kez
**döngüsel olmayan** kesit çekildi.

| girişte bilinen | kazanan | kaybeden | fark / SE |
|---|---:|---:|---|
| `spread_atr` | 0,0446 | 0,0448 | −0,0003 / 0,0157 |
| `atr_pct` | 0,0018 | 0,0018 | ~0 |
| `fill_vs_signal_close_r` | +0,0028 | +0,0178 | −0,0150 / 0,0173 |
| `adx` | 32,1 (n=3) | 19,4 (n=4) | +12,7 / 10,5 |

**Hiçbiri ayırt edilemiyor.** İşleme girildiği anda kaybedenle kazanan aynı
görünüyor — yani giriş kapılarına eklenecek bir şey yok, ve bu CHOP-1c'yi
(ADX filtresi işe yaramadı) işlem verisinden bağımsız doğruluyor.

Yan gözlem: 36 kaydın yalnız **7'sinde ADX var**, çünkü üç sembolde
`adx_min=0` olduğu için seri hiç hesaplanmıyor. 5f'nin ölü ayarı veride
görünüyor.

**Ayıran şey sonradan:** MAE kazananda 0,33 R, kaybedende **0,91 R**
(ayırt edilir). Çıkış: `sl` n=19 **−15,00 R**, `flatten` n=9 +6,90,
`trail` n=8 **+20,99** — sekiz trail çıkışı kitabın kârını taşıyor.

MAE farkı sonuca koşullu, ama **zamana bağlanırsa koşullu olmaktan çıkar**:
girişten N bar sonraki MAE, o anda bilinen bir sayıdır. LOSS-3 bunu ölçüyor
(N ∈ {1,2,3,5}, erken kapatma eşiği X ∈ {0,5, 0,75, 1,0}), ve BE-1'in
kuralıyla korunuyor: **120+ tutma kovasının net R'si %10'dan fazla düşerse
aday elenir** — kârın tamamı orada.

---

## 5h. Kaybedeni erken tanıyoruz, kesmek daha pahalı (21.08) — LOSS-3

5g "girişte fark yok" demişti. **Zamanlanmış MAE farkı buluyor** ve döngüsel
değil: girişten N bar sonraki aleyhe gidiş, o anda bilinen bir sayı.

GER40, N=1 bar, holdout n=1247:

| MAE₁ | n | nihai R/işlem | SE |
|---|---:|---:|---:|
| <0,25 | 366 | **+0,61** | 0,14 |
| 0,25–0,5 | 354 | +0,48 | 0,12 |
| 0,5–0,75 | 217 | +0,03 | 0,15 |
| >0,75 | 310 | **−0,73** | 0,08 |

Aynı eğim NAS100 / US30 / XAUUSD'de de var. **Kaybedeni bir bar sonra
tanıyabiliyoruz** — giriş alanlarının hiç yapamadığı şey.

**Ama kesmek daha pahalı.** GER40 N=1 X=0,5'te holdout **−94,7 R**
(+173,8 → +79). Sebep 4g/4l'nin aynası: erken aleyhe giden işlemler,
döndüklerinde kuyruğu üretenlerle **aynı işlemler**. GER40'ın 120+ kovası
n=732 / **+668,7 R** taşıyor ve erken çıkış tam oraya nişan alıyor.

Kapıyı geçen 2/6 sembol de okunduğunda düşüyor: NAS100 **+1,09 R / 1045
işlem** (gürültü), SpotBrent'te `mae` çıkışı **n=1–2** (yok hükmünde).
Cursor `_slice_ok`'ın minimum ΔR istemediğini kendisi işaretledi; eşik
kararı bana bırakıldı ve **ikisi de reddedildi**.

**X=1,0 eksen değil kapı:** stop ~1 R'de ve önce ateşliyor, MAE>1 R'ye hiç
ulaşılmıyor — 6×4 dilimin hepsinde `mae` çıkışı sıfır.

**Sistemin doğası hakkında en net cümle bu:** *hangi işlemin kaybedeceğini
erken söyleyebiliyoruz, ve onu kesmek tutmaktan daha pahalıya mal oluyor.*
REV-1 (dönüş), CHOP-1b (zarar sonrası bekleme) ve şimdi LOSS-3 — üçü de
işlemi kısaltıyor, üçü de kuyruğu kesiyor, üçü de zarar veriyor.

Bayrak (`mae_close_bars` / `mae_close_r`) varsayılan kapalı birleşti
(`a9ba721`), arama geçirmiyor.

---

## 5i. Aile azaltma: hiçbiri gitmiyor, ve gerekçe performans değil (21.08)

Operatör sordu, Cursor araştırdı, **cevap hayır**. Üç gerekçe, üçü de
retention/performanstan bağımsız:

**1. Bugünkü kazanç sıfır.** `auto_reoptimize` kapalı (4z), yani hiçbir tarama
kendiliğinden koşmuyor. 12 aile de 5 aile de duvar saati **aynı: sıfır**.
Listeyi şimdi kesmek çalışmayan makineyi hızlandırmaktır.

**2. Azaltma zaten ölçüldü ve işe yaramadı.** IDX-1 tam olarak buydu: 12
aileden **6'ya** inip dört endeksi aradı, sonuç **0/4 validated apply**.
"Daha az aday = daha kararlı seçim" teorik olarak doğru, **bu seçicide
gösterilmedi**. Daha da kesmek yalnız challenger havuzunu yok eder.

**3. Canlı olmayan aileler tek dürüst challenger.** IDX-1'in altısı
`aroon_flip` · `parabolic_flip` · `wavetrend_flip` · **`stoch_flip`** ·
`macd_flip` · `st_trend` idi; bunlardan **canlı olmayan beşi** tam taranabilir
tek alternatif havuz (`stoch_flip` GER40'ta incumbent, yani hem challenger hem
mevcut).

`t3_flip` (144.000) ve `micro_rev` (1,55 M) o havuzda **değil** — ızgaraları
`max_combos=2000`'in üstünde, yani çekiliş aileleri. Silinmemelerinin gerekçesi
ayrı: `t3_flip` 18 kazanmış 5 apply almış, `micro_rev` canlı olmuş (XAUUSD M5).
Gerekçeleri IDX-1 setine bağlanmasın.
`macd_flip` apply=0: kapı çalışıyor, aile ölü değil. `micro_rev` canlı olmuş
(XAUUSD M5). `STRATEGY_TIMEFRAMES = {}` kasıtlı — hangi TF hangi aileye uyar
diye önden kesmiyoruz; aile silmek o kararı geri alır.

Karşılaştırma noktası: `flow_rev` / `trix_flip` 14.08'de **gerçek bir boşlukla**
silindi (162 adayda apply 0, holdout 2,7 ve 5,0 vs sonraki en kötü 23,2).
Bugünkü adaylarda o boşluk **yok**.

**`t3_stoch` ayrı ve doğru ayrım:** aranamazlığı (1,43 G, D1b'de sapma
ortalamadan büyük) bir **arama politikası** sorunu, aile silme sorunu değil.
Silinirse US30'un gideceği yer ölçülü: IDX-1'de `stoch_flip` holdout
**−7,56** vs incumbent **+49,09**. Taşımak daha kötü. US30 `t3_stoch`'ta
kalır, ve **yeni bilet çekmek için yeniden örneklenmez** (D1b'nin kapattığı
şey).

**Ölçülemeyen açıkça yazıldı:** aile sayısı düşürüldüğünde `validated` oranı
ve apply başına aile değişimi **bu seçicide ölçülemez, çünkü seçici apply
etmiyor.** Uydurma sayı üretilmedi.

### Kararın koşulu — unutulmasın

Bu **"asla"** değil, **"şimdi değil"**. Kararı değiştirecek tek şey:
`auto_reoptimize` geri açılırsa ya da seçici yenilenirse aile listesi tekrar
maliyet ve çoklu-karşılaştırma taşımaya başlar. O gün bu kayıt yeniden
okunmalı; bugünkü gerekçelerin **ikisi de** (sıfır maliyet, ölçülmüş
etkisizlik) o koşula bağlı.

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

### 20.08.2026 akşamı — güncel

Hesap: Pepperstone demo **61562752**, bakiye **2.262,89 $**, özkaynak 2.269 $.
Oturum 16.08'de 2.113 ile başladı. Gün: 9 işlem, **+233,42 $** (US30 +82,
GER40 +55, JPN225 +51, XAUUSD +49, NAS100 −3). **Bu gürültü** — `n→ayırt`
canlıda hâlâ 538; dokuz işlem onu değiştirmiyor. İyi gün kötü günden daha
ikna edici görünür, tehlikesi orada.

Kitap **6 sembol**, hepsi `risk_percent 0,80` / `max_positions 1`:
GER40 `stoch_flip`/M30 · JPN225 `dual_t3`/M5 · NAS100 `mtf_pullback`/M30 ·
US30 `t3_stoch`/M30 · SpotBrent `dual_t3`/M5 · XAUUSD `burst`/M15.
Nominal risk %4,80, kapı %15.

**Açık denetimler ve durumları:**

| kontrol | durum |
|---|---|
| damga sapması | **0 açıklanmamış** (XAUUSD `calibrated`) |
| otopsi halkası | dolmakta, tablo n≥50'de |
| gece yedeği | kendiliğinden dönüyor (19.08 22:00 ✓) |
| test / ruff / mypy | **2220 / temiz / 0** |
| auto_reoptimize | **kapalı** — FWD penceresi korumada (4z) |

**Bekleyen tetikleyiciler:** NAS100 50 işlem · lot çarpanı 100 işlem ·
SpotBrent 30 işlem (risk 4× arttı, test edilmedi) · auto-reopt geri açma ·
XAUUSD (iki kez silinmeye kalkıldı, ikisinde de gerekçe ölçümde çöktü).

**Nerede duruyoruz:** arama tarafı kapandı (5b/5d, iki imzalı). Kalan tek
bilgi kaynağı FWD penceresi; `n→ayırt` **538**, günde ~23 işlemle **~12
Eylül**. O tarihten önce verilecek "çalışıyor / çalışmıyor" hükmü veriye
değil sabırsızlığa dayanır.

**Protokol 20.08'de değişti (§1):** Cursor eşit yetkili. İlk gününde üç şey
buldu — teselli dalı, iki hükmün fazla genişliği, `validated` sızıntısı.

---

### 18.08.2026 akşamı — o günün rakamları

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

## 5j · SWEEP-1: satır satır ortak tarama (21.08)

Operatör: *"her kodun altına, her satıra bakın: hata, köşe, ölü kod."*
15.785 satır, sorumluluk hattına bölündü — canlı para hattı Claude (6.269),
araştırma hattı Cursor (6.356), ortak modüller (3.160) sonra. Gerekçe:
**hangi hattı düzeltecekse onu okusun.** Canlı hatta yanlış düzeltme para
kaybettirir, araştırma hattında yanlış düzeltme ölçümü sessizce bozar.

### Bulunan kesin hatalar

**1. Kitapsız magic sessizce yönetimsiz kalıyordu** (`engine.py:2456`,
`0d6d681`). `manage_positions` pozisyonu magic ile arıyor; kitapta karşılığı
yoksa çıplak `continue` — trail yok, stop yönetimi yok, flatten yok, log da
yok. O döngüdeki diğer bütün atlamalar yapışkan ve tekrarlı; bu biri kalıcı
ve görünmezdi. API bu durumu üretemiyor (silme ve magic değişimi açık
pozisyonda 409, orphan taraması da kapalı) — **ama o kapıların hepsi web
katmanında** ve elle yazılmış bir DB satırı hepsinin yanından geçiyor. O yol
bugün, ikimize de canlı DB yazma yetkisi verilmesiyle gerçek oldu. Pozisyon
kapatılmıyor (config yoksa ne olduğu bilinemez; tanımlanamayanı kapatmak
brokerin stopunda bırakmaktan kötü) — yalnız sessizlik bitti: ticket başına
bir WARN, ticket kitaptan düşünce mandal serbest.

**2. MACD ters dönemde klasiğin negatifi** (`indicators.py:165`, `3dc3b4f` +
`add6ad4`, Cursor). `macd_fast=26, macd_slow=12` panelden HTTP 200 geçiyor;
takas olmadan histogram klasik MACD'nin **tam negatifi**, yani `macd_flip`
**satması gereken yerde alıyor**. Bağımsız doğrulandı: 12/26, 6/18, 16/34
bit-özdeş kaldı; eski 26/12 gerçekten `-1 ×` klasik; eşit dönem çizgiyi
sıfıra yığıyordu. Shipped ızgara (fast 6..16, slow 18..34) hiç çarpışmıyor,
`macd_flip` kitapta yok — yani canlı davranış değişmedi.
İkinci tur: takas `macd()` içindeydi, **warmup ham `macd_slow` okuyordu**;
ters ızgarada 8 hücre 1–4 bar eksik ısınıyordu. `macd_periods()` tek kaynak
oldu (hesap, warmup, `required_bars`, cache anahtarı).

**3. Bozulan teşhis yazımı sessizdi** (`engine.py`, `397824f`). Üç `_flush_*`
istisnayı kasten yutuyor — geçici sqlite kilidinde sessiz retry doğru ve
dirty biti True kalıyor. Kalıcı bozulma da aynı şekilde yutuluyordu. Zarar
işlem değil, **iki okuyucunun ayrışması**: panel bu tabloları bellekten
okuyup taze görünmeye devam ederken, FWD raporları / otopsi tablosu /
`_spread_scale` aynı tabloları sqlite'tan okuyor ve **donmuş sayıyı canlı
diye yayınlar**. Gerekçenin bu keskin hali Cursor'undur. Aynı mandal
`optimizer._spread_scale`'e de kondu (`add6ad4`).

### Sarı kapıya çakılan mayın — `max_positions` artırılamaz, önce bu düzelecek

`backtest.walk_forward` → `simulate()` çağrısı `max_open` **geçirmiyor**
(varsayılan 1); `optimizer._holdout_costed` de aynı. Bugün `max_positions=1`
olduğu için bit-özdeş, **ölçüm doğru**. `max_positions` 2'ye çıktığı gün arama
ve apply kapısı hâlâ 1'i ölçer: canlı iki pozisyon taşırken seçici tek
pozisyonluk bir dünyaya göre karar verir.

İkimiz bunu **bağımsız iki yoldan** bulduk (Claude'un ölü-parametre taraması,
Cursor'un çağrı-zinciri taraması). Bugün kasten düzeltilmedi — bugün
düzeltmek sessiz bir davranış değişikliği olurdu, ve bu projede sessiz
davranış değişikliği tam olarak kovaladığımız şey.

**Kural:** `max_positions` artırma kararı sarı kapıdan (ikimizin onayı)
geçer, ve **bu düzeltilmeden o kapı açılmaz.**

### Temiz çıkan sınıflar (sonuçsuz değil — sonuç bunlar)

* Yutulan istisna, canlı para hattı: 18/18 savunulabilir. Hiçbiri emir yolunu
  yutmuyor; hepsi teşhis kalıcılığı, yeniden bağlanma öncesi `mt5.shutdown()`,
  encoding fallback, kapanış sonrası deal araması.
* Sıfıra bölme, canlı para hattı: taranan 20 bölmenin hepsi korumalı
  (`start_balance` 3061, `r_value` 1954, `raw` 325, `equity` 532/540,
  `days` 648, `max_dd` 256).
* `_t3_flip` docstring'i "ADX yok" **doğru** — gövde ADX okumuyor. 5f'deki
  `_dual_t3` yalanının kardeşi değil.

### Kayıt: sessiz onarım damganın kör noktası

`ema()` kırpıyor, `macd()` takas ediyor, `wilder()` kırpıyor — üçü de girdiyi
sessizce onarıyor. Panel 26/12 gösterir, motor 12/26 koşar, **damga 26/12
yazar**, ve `stamp_drift()` sıfır sapma raporlar: damga ile canlı satır
birbirine uyar, ikisi de koşulandan farklı olduğu halde. Bugün ulaşılamaz
(ızgara çarpışmıyor, `macd_flip` kitapta yok). Düzeltme değil **kayıt**:
ızgara elle değişirse ya da `/api/opt/params` ters dönem alırsa sapma raporu
sessiz kalır — ve biz o rapora güveniyoruz.

### Ortak çalışma tehlikesi (yeni, ölçüldü)

Aynı çalışma dizinini paylaşıyoruz. Cursor `add6ad4`'ü 14:39:25'te yazdı,
benim tam suite koşumun ortasında; 3 test dosya altımdan değişti diye
düştü, temiz koşumda 2235 geçti. **Test sonucu, koşum sırasında öbürünün
commit'i varsa geçersizdir** — düşen testi kendi değişikliğine yazmadan önce
`git log --date=format:%H:%M:%S` ile zamana bak.

**Ve testi commit'in kapısı yapmak istiyorsan çıktıyı borulama.**
`pytest ... | tail -2 && git commit` **kapı değildir**: boru hattının çıkış
kodu `tail`'ındır, yani pytest kırmızı olsa da zincir devam eder. 21.08'de
tam böyle kırmızı suite üstüne commit atıldı (`f62b6b8`; düşenler yarıştan
kaynaklıydı, ama kapı yine de açıktı). Doğrusu:
`pytest -q > out.txt 2>&1; echo $?` — sonra oku, sonra commit et.

### 5j-ek · Otopsi tablosundaki 4 eksik kapanış — reap hatası DEĞİL

Cursor 19–21.08 penceresinde otopsi tablosunda 45 satıra karşı brokerde 49
kapanış ölçtü; eksik dördü de `DEAL_REASON_SL`. İlk atıf `a94bdd5`'e
(deal gecikmesinde kaybolan kapanış) yapıldı. **Tutmuyor**, ve kaydı düzelten
taraf bu atıftan çıkarı olan taraftı — yani en dikkatli okunması gereken yer.

**Ayırt eden kanıt: dördünün de log satırı var.** O satırları
`_log_broker_exit` yazıyor, onu besleyen `reap()`. `reap` düşürseydi log
satırı da olmazdı — düzeltilen hatanın tanımı zaten "log satırı yok, otopsi
satırı yok, kayma örneği yok". Üstelik `_log_broker_exit` otopsiyi log
satırından **önce** yazıyor. Log varsa reap çalışmıştır.

`_autopsy_safe` istisna yutsa WARN atardı; logda sıfır tane var.

Geriye tek açıklama: o aralıkta `_log_broker_exit` içindeki `_autopsy_safe`
çağrısı **henüz yoktu**. Tabloya ilk satır 19.08 15:19:58'de düşüyor, logdaki
o anki kapanış 15:19:59 — aynı kapanış. 09:43–15:19 arası tabloda **sıfır**
satır, aynı aralıkta 4 kapanış loglanmış. Kesintili değil, hiç yok.

**Asıl bulgu — `trade_autopsies_since` yanlış payda.** `_restore`
(`engine.py:1265`) `since`'i halka boş olsa da DB'den geri yüklüyor
(`since or time.time()`), böylece 09:43:11 damgası bütün restart'lardan sağ
çıkmış ve tablonun gerçek başlangıcından **5 sa 37 dk** önceyi gösteriyor.
Bu paydaya göre hesaplanan her tamlık/oran — ve n≥50 eşiğine kalan mesafe —
eksik sayar. FWD raporu bu paydadan okuyor.

**`a94bdd5` hakkındaki kayıt değişmiyor: yapısal olarak ulaşılabilir,
gerçekleştiği gözlenmedi.** Onu doğrulayan kanıt aranırsa pencere `since`
yerine ilk satırın zamanından başlatılmalı.

Bu, ikimizin birbirinin **kaydını** (ölçümünü değil) düzelttiği üçüncü vaka.
Sınıf tekrar ediyor: sayı doğru, cümle yanlış. Ölçen taraf sayının ne
anlattığını, ölçmeyen taraf cümlenin ne iddia ettiğini görüyor.

### 5j-2 · Ortak modül turu, Claude payı (21.08)

`run` 279, `backup` 419, `logbus` 168, `paths` 105, `account_lock` 64,
`spread_calibration` 191, `edge_decomposition` 134.

**Kesin hata yok.** Bu dosyalar zaten sertleştirilmiş: `paths` her açılış
hatasını operatörün okuyabileceği bir satıra çeviriyor, `run`'ın yetim işçi
temizliği bu yorumcuya daraltılmış (öldürmesi imkânsız olan tarafta hata
yapıyor), `logbus` dosya yazımını kilitliyor ve OSError'da bellekteki halkaya
düşüyor.

**Kayıt 1 — `account_lock`'taki asimetri kasıtlı.** Gerçek para vetosu yalnız
**bağlanmamış** dalda çalışıyor; kilit zaten kuruluysa `trade_mode` sorulmuyor.
Bu bir açık değil: **kilidi elle kurmak, operatörün onayının ta kendisi.**
Eşleşen dala bir `is_real_money_account` kontrolü eklemek sıkılaştırma gibi
görünür ve aslında canlıya geçmenin tek yolunu kapatır. Koda yorum olarak
yazıldı, çünkü bunu "düzeltmek" fazlasıyla davetkâr.

**Kayıt 2 — log dosyası makine saatiyle damgalanıyor.** `logbus`
`time.localtime(entry["ts"])` kullanıyor ve bu **doğru**: `ts` makinenin
ürettiği bir epoch, MT5 damgası değil. Ama sonucu şu: log satırları **makine
yerel**, bar/deal/otopsi damgaları **sunucu**. Bugün ikisi çakışıyor (makine
UTC+3, broker GMT+3) ve 5j-ek'teki kanıtın tamamı bu çakışmaya dayanıyordu —
log satırlarını `exit_time` ile eşleştirdim. Bu bir garanti değil,
yapılandırma tesadüfü. Saat kayması uyarısı (`8b876aa`) bu riski örtüyor, ama
log ile sunucu damgası karşılaştıran **herkes** bu varsayımı bilmeli.

**Bulgu — `edge_decomposition` üretimde çağrılmıyor.** Modül yön becerisini
çıkış geometrisinden ayırıyor (GER40 14.08: holdout E +0,153 gerçek yönle,
+0,048 aynı çıkışlar + yazı tura). Docstring "her config için üretilebilir
olmalı, tek seferlik defter değil" diyor. Bugün **tek çağıranı testler**.
Yani: sorduğumuz soruya cevap veren, yazılmış ve testli bir araç var ve hiçbir
yere bağlı değil. Ölü kod değil — **kullanılmayan yetenek**, ki performans
arayışında bundan daha doğrudan bir soru yok: *kenarımız yön seçmekte mi,
çıkışlarda mı?* Cursor'a ölçüm olarak devredildi.

**Küçük not:** `_side_stats` `x >= 0` ile sıfır R'yi **kazanan** sayıyor.
Başabaş çıkış (trail tam girişte) bunu üretebilir. WR'yi yukarı, `avg_win`'i
aşağı çeker — iki yanlış ters yönde. Maliyet yüklüyken tam sıfır nadir; kanıt
görülmeden düzeltilmedi.

### 5j-3 · `max_positions` kapısına üçüncü koşul

`_verify_ambiguous_send` belirsiz bir emirden sonra pozisyon defterini ~2,1 sn
izliyor; hiçbir şey düşmezse `verified_unfilled` dönüyor ve docstring bunu
*"genuinely never reached the market"* diye yazıyordu. **2,1 sn kanıt değil.**
Defter okunabildi ve boş kaldı — o kadar.

Geç düşen bir dolumun ikinci pozisyona dönüşmesini engelleyen şey, o
fonksiyon değil: **sembol başına pozisyon limiti retry'ı reddediyor**
(`risk.py:501-504`, sayı kontrolü yön kontrolünden önce). Yani sözü veren
altsistem ile sözü tutan altsistem farklı.

`max_positions` 1'in üstüne çıkarsa o reddetme kalkar ve **tek sinyal iki
giriş** taşıyabilir — modülün var oluş sebebi olarak yazdığı duplikasyonun
ta kendisi ("a missed entry costs a signal, a duplicate costs double risk").

**Kapının koşulları artık üç:**
1. `walk_forward` → `simulate` `max_open` geçirmiyor (5j) — arama tek
   pozisyonluk dünyayı ölçüyor.
2. `optimizer._holdout_costed` aynı.
3. `_verify_ambiguous_send`'in "dolmadı" sözü, limitin 1 olmasına yaslanıyor.

Docstring düzeltildi: artık ne ölçtüğünü ve neyin koruduğunu söylüyor.

## 5k · MISS-1: kaçırılan işlemler ölçüldü (21.08)

Operatör `max_positions=10` sordu; istediği limit değil, **"işlem
kaçırmayalım"**. Limiti tartışmak yerine kaçırma ölçüldü — `entry_blocks`
`signals` sayacı, 16.08 18:34'ten beri:

**Açılan 95, engellenen 150 → kaçırma oranı %61.**

| sebep | n | pay |
|---|---|---|
| `risk_sembol_limiti` | 101 | %67 |
| `spread` | 28 | %19 |
| `emir_hatasi` | 12 | %8 |
| `risk_ters_yon` | 5 | %3 |
| `lot` | 4 | %3 |

| sembol | açılan | engel | kaçırma | en büyük sebep |
|---|---|---|---|---|
| GER40 | 18 | 91 | **%83** | limit=68 |
| SpotBrent | 6 | 12 | %67 | **spread=12** |
| XAUUSD | 23 | 19 | %45 | limit=11 |
| JPN225 | 25 | 18 | %42 | limit=12 |
| NAS100 | 14 | 9 | %39 | limit=9 |
| US30 | 9 | 1 | %10 | limit=1 |

**Üç sonuç, üçü de hedefi daraltıyor:**

1. **Bu bir GER40 sorusu.** 101 limit engelinin 68'i tek sembolde. Kitap
   geneline limit açmak, sorunun üçte ikisini çözmek için tamamını riske
   atmak.
2. **SpotBrent'in kaçırması makastan.** 12/12 `spread`. Limit orada hiçbir
   şey değiştirmez — ayrı iş.
3. **101'in içi karışık, ve bu belirleyici.** `risk.py:501-504`'te sayı
   kontrolü yön kontrolünden **önce** çalışıyor: `max_positions=1` iken ters
   yön sinyalleri de `risk_sembol_limiti` olarak yazılıyor. Görünen
   `risk_ters_yon=5` gerçek sayı **değil**. Ters işlemler ölçüldü:
   GER40'ta **−1001 R**. Limiti açmak, zararlı olduğu ölçülmüş işlemleri de
   içeri alır — payı bilinmiyor.

**Sonuç: %61 kaçırma gerçek, ama "kaçırılan = kazanç" değil.** Kararı
verebilmek için iki ölçüm gerekiyor (Cursor'a devredildi): o 101'in kaç
tanesinin aynı yön olduğu, ve aynı yönde ikinci girişin holdout'ta ne
kazandırdığı. İkincisi `max_open` geçişini **ön koşul** yapıyor — mayın
artık yalnız engel değil, kararı almanın yolu.

Uyarı: `signals` mandalı bellekte, restart yeni epizot başlatır; sayı hafif
yukarı sapabilir, yön değil büyüklük etkilenir.
