# Claude icin inceleme ve gelistirme onerileri

Tarih: 15.08.2026

Bu belge yalnizca inceleme sonucudur. Uygulama kodunda duzeltme yapilmadi.

## Oncelik 0 — yerel panelde istenmeyen POST isteklerini engelle

**Bulgu:** `run.py:226-247`, API tokenini sadece `MICO_HOST` localhost disina
acildiginda zorunlu tutuyor. Token yokken `create_app()` icindeki middleware
hic kurulmaz (`micofx/web/app.py:546-584`). Buna karsin `POST /api/bot/panic`,
`/api/bot/start`, `/api/app/shutdown`, `/api/app/restart` ve diger kritik
endpointler herhangi bir anti-CSRF kontrolu olmadan calisiyor
(`micofx/web/app.py:1887-1896`, `2178-2205`).

Bir kullanici acikken ziyaret edilen kotu niyetli bir web sayfasi, tarayicinin
yerel adrese form POST gonderme ozelligini kullanabilir. CORS ayari bunu
engellemez; form gonderimi cevap okumayi degil, islemi baslatmayi hedefler.
Bu bir finansal islem uygulamasinda kritik bir guvenlik riski.

**Claude'a gorev:**

1. Her calistirmada, localhost dahil, rastgele ve bellekte tutulan bir oturum
   sirri uretin; panel acilirken bu sirri guvenli bicimde baslatma istegine
   verin.
2. Tum durum degistiren endpointlerde (`POST`, `PUT`, `PATCH`, `DELETE`)
   zorunlu `X-Mico-Token` veya ayri bir `X-CSRF-Token` denetimi yapin.
3. `Origin` ve `Sec-Fetch-Site` kontrollerini ikinci savunma hatti olarak
   ekleyin; eksik ya da beklenmeyen Origin'i kritik endpointlerde reddedin.
4. Tokeni URL'de tasimayin. Ilk panel yuklemesinde tek kullanimlik bootstrap
   akisi ya da HttpOnly/SameSite=Strict cookie kullanin.
5. Bu endpointlerin her biri icin, tokensiz ve yabanci Origin'li POST'un 401
   veya 403 dondugunu kanitlayan test ekleyin.

## Oncelik 1 — bos yamalari basarisiz sayin

**Bulgu:** `SymbolPatch` tum alanlari opsiyonel tanimliyor
(`micofx/web/app.py:46-69`). `POST /api/symbols/{symbol}` icin `{}` gonderilirse
`_coerce_symbol_patch()` bos sozluk dondurur (`:504-529`), `Store.update_symbol`
ise ayar degismedigi halde basarili cevap verir (`micofx/store.py:302-327`).
Toplu endpoint daha yaniltici: `POST /api/symbols-bulk` bos `patch` ile tum
sembolleri yeniden kaydeder ve `changed` sayacini gercekte degisim olmadigi
halde arttirir (`micofx/web/app.py:1666-1780`).

Bu, "yama uygulanmali ya da reddedilmeli" ilkesinin bos-yama istisnasidir;
otomasyon istemcileri basarisiz degisiklikleri basarili sanabilir.

**Claude'a gorev:**

1. Tekli ve toplu endpointlerde coercion sonrasinda bos patch'i 400 ile
   reddedin.
2. `changed` degerini yazma denemesiyle degil, onceki ve sonraki ayar arasinda
   gercekten fark varsa arttirin.
3. `{}`, `{ "patch": {} }` ve bos `BulkPatch` icin hata testi; ayni degerin
   tekrar yazilmasi icin `changed: 0` testi ekleyin.

## Oncelik 1 — optimize sonucu ile incumbent karsilastirmasini ayni veri
anlik goruntusune baglayin

**Bulgu:** Yeni kod, incumbent icin tekrar holdout hesapliyor
(`micofx/optimizer.py:1131-1143`). Bu hesap yeni bir `client.bars()` cagiriyor
ve holdout dilimini o an gelen son bar sayisina gore seciliyor. Adayin sonucu
ise optimizasyon baslarken alinan bar anlik goruntusunden geliyor. Uzun suren
bir optimizasyon sirasinda yeni bar kapanirsa iki skor farkli zaman pencereleri
uzerinden karsilastirilir (`:1145+`).

**Claude'a gorev:**

1. Bir optimizasyon isi baslarken bar verisini ve holdout sinirlarini tek bir
immutable job snapshot'inda saklayin.
2. Aday ve incumbent holdout'unu ayni snapshot, ayni maliyet varsayimi ve ayni
indeks araliginda hesaplayin.
3. Son bara ait zaman damgasini `opt_summary` ve opt-run kaydina yazin; panel
bu bilgiyi gostersin.
4. Yeni bar eklendikten sonra dahi incumbent replay'inin eski snapshot'i
aldigini gosteren deterministik test ekleyin.

## Oncelik 2 — ayar API'leri icin tek, tipli komut siniri olusturun

**Bulgu:** Yeni `_dataclass_patch()` alan listesini sinirliyor ama alan
degerlerinin cogu `Any` (`micofx/web/app.py:46-59`). Tip/range kontrolu ayri
fonksiyonlara dagilmis durumda; farkli yazma yollarinin farkli korumalari
olmasi gecmiste birden cok bypass'a yol acti.

**Claude'a gorev:**

1. `SymbolConfig` ve `SystemConfig` icin Pydantic patch modellerini acik
   tiplerle ve alan seviyesinde sinirlarla tanimlayin.
2. Tekli patch, bulk patch, optimizer apply, seed/reset icin ortak bir
   `validate_and_plan_config_change` servisi kurun.
3. Bu servis degisimin etkisini (`no_change`, `safe_now`, `requires_flat`,
   `requires_optimized`, `rejected`) dondursun; HTTP katmani sadece sonucu
   maplesin.
4. Property-based testlerle her yazma kapisinin ayni gecersiz degeri
   reddettigini kontrol edin.

## Oncelik 2 — isletim ve kalite kapisini onarin

**Bulgu:** Test calistirilamadi. Sistem `python` komutunu bulamiyor; mevcut
`C:\MicoFX-venv\Scripts\python.exe` ise silinmis
`C:\Users\prlay\AppData\Local\Programs\Python\Python312\python.exe` yoluna
bagli oldugundan baslatilamiyor. Bu nedenle pytest, ruff ve mypy sonuclari
alinamadi. `KUR.ps1` venv'i proje disinda tutuyor (`KUR.ps1:16`); ana Python
kurulumu kaldirilinca eski venv'in gecerliligini denetleyen bir onarim akisi
gerekli.

**Claude'a gorev:**

1. Kurulum/guncelleme basinda venv interpreter'ini `--version` ile calistirip
   dogrulayin.
2. Gecersizse operatoru acikca bilgilendirip venv'i tekrar olusturun;
   eski venv'i once geri alinabilir bir adla tasiyin.
3. CI'da Python 3.12 uzerinde `pytest -q`, `ruff check micofx tests` ve
   `mypy` zorunlu kontrol olsun.
4. Python/venv yolunu ve son dogrulama sonucunu panelde salt-okunur saglik
   bilgisi olarak gosterin.

## Uygulama sirasi

1. Yerel POST korumasi ve bunun testleri.
2. Bos-yama davranisi ve dogru `changed` sayaci.
3. Test ortamini onarip tum kalite kontrollerini yesil hale getirme.
4. Optimizer snapshot karsilastirmasi.
5. Ortak, tipli ayar-degisiklik servisi.

## Inceleme siniri

- Calisma agaci zaten degisiklikler iceriyordu; bunlara mudahale edilmedi.
- `git diff --check` bos dondu; gorunur bir whitespace hatasi yok.
- Otomatik bug/security review alt-araclari bu oturumda kullanilabilir
  degildi; bulgular kaynak kodun statik okunmasina dayanir.
