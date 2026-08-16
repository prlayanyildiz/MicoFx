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

pytest bu makinede `sessionfinish`'te `WinError 1463` (sembolik bağlantı
izlenemiyor) ile patlıyor: exit 1 döner, testler bitmiş olsa bile özet
satırı yutulur. `2ef2744` basetemp'i `.pytest_tmp`'e taşıdı ama sebebi
çözmedi. Sonucu öğrenmek için çıktıyı dosyaya alıp ilerleme noktalarını
saymak gerekiyor.

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

**BUG — gün çıpası hesap bilmiyor.** Hesap değişince bakiye farkını zarar
sanıyor: demo çıpası 2.113 $ iken live 0.51 $'a geçilince fren "%99.98 zarar"
deyip kilitlendi ve diske yazdı. Çıpa hesap numarasıyla birlikte tutulmalı.

**BUG — boş kilit gerçek para hesabını otomatik bağlıyor.** Boş kilit ilk
bağlanan hesabı yazıyor; o hesap yanlışlıkla live ise kilit live'a kurulur.
Boş kilit `trade_mode == 2` gördüğünde otomatik bağlamamalı, onay istemeli.

**BS-1 — en büyük kalem.** `risk.py` portföy kapıları canlıda var,
`backtest.py`'de yok: `max_concurrent_risk_pct`, `max_margin_usage_pct`,
`max_total_positions`, günlük halt, `block_high_cost`, `_symbol_daily_halt`,
supervisor kısıtları. Backtest her sembolü tekil vakumda koşuyor, yani kâğıt
canlının hiç alamadığı işlemleri alıyor. Ölç: aynı dönemde kâğıt kaç işlem
üretti, canlı kaç aldı, sembol başına. Kesilen işlemlerin kâğıttaki net R'si
pozitif mi negatif mi? Holdout +640 ile canlı −986 arasındaki **1600 $/ay**
buradan çıkabilir.

**BS-2 — kağıtta al/sat asimetrisi (BUG).** `backtest.py`: long girişte
spread ödeniyor (`open+s`), short'ta stop kontrolünde (`high+s >= sl`). Her
bacak spread'i bir kez ödüyor ama farklı yerde — long'da giriş kötüleşiyor,
short'ta stop kolaylaşıyor. Arama bugüne kadar short ağırlıklı configleri
haksız cezalandırmış olabilir. Onar, 10 sembolde önce/sonra holdout ver.

**BS-2b — holdout beraberlik sızıntısı.** `optimizer.py` aile/TF
beraberliğinde holdout işlem sayısına bakıyor. Küçük ama holdout'a dokunuyor;
beraberliği validation ve deterministik ad sırasıyla çöz.

**BT — evren taraması.** Broker'da 1729 sembol var, kitapta 10. Hepsini
walk_forward'dan geçir, holdout R/gün'e göre sırala, `validated` işaretle.
Hipotez: **tavan düşük çünkü üst sıradaki semboller kitapta yok.** FX'i
atlama — "FX'te M5 pahalı" ölçüldü ve doğru, ama M15/M30 FX hiç ölçülmedi.

**Sıraya bağımlı test.** `test_the_new_bar_trigger_uses_the_brokers_clock.py::
test_the_day_boundary_still_uses_the_naive_encoding` tam suite'te bir kez
kırıldı, izole geçiyor. Global durum sızıyor; kaynağı bulunmalı.

**Ruff borcu.** `run.py` E402 x9 (import'lar sürüm kontrolünün altında,
bilerek) ve `backup.py:285-286` F541. İkisi de kasıtlı — `per-file-ignores`'a
gerekçesiyle yazılmalı ki ruff yeniden "temiz = yeşil" olsun.

---

## 8. Operatör tercihleri

Türkçe konuş, kısa yaz. Commit mesajları, kod yorumları ve test docstring'leri
İngilizce kalır. Her değişiklikten sonra commit + push — sormaya gerek yok.
Ajan cevap verdi denince dosyayı sormadan aç. Sembol elemeden önce
düzeltme sonrası veri bekle. `engine`/`optimizer`/`app` değişince canlı süreç
eski kodda kalır — restart gerekir.
