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

Marj: kitap 1:100'de 1.274 $ marj yiyor, marj seviyesi %166. US2000 ve
XAUUSD ikisi marjın %63'ünü alıp 0.20 R/gün veriyor; GER40 38 $ marjla 0.772
R/gün veriyor. **Backtest marjı hiç bilmiyor** — her sembolü tekil vakumda
optimize ediyor, o yüzden sistematik olarak en dar stopu seçiyor.

Kitap: 10 sembol, hepsi açık, `lot_mode=risk`, sembol başına `max_positions=2`.
Risk yüzdeleri 0.2 (SpotBrent, XAUUSD, US500) ve 0.8 (diğer yedi). Hepsi dolsa
teorik eşzamanlı risk %12.4; sistem kapısı `max_concurrent_risk_pct=15`.

---

## 7. Açık işler, öncelik sırasıyla

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

Bütçe: kalan 1034 × 36 sweep × 6 sn = **62 saat**. Hisse hariç 49 isim =
**2,9 saat**. Sıralama `calmar`; R/gün değil, LEV-1 onu geçersiz kıldı.
Ölçüm betiği `cursor/_bt0_measure.py`, çıktı `cursor/_bt0_result.json`.
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
