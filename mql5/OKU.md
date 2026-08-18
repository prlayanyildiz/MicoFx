# MQL5 tarafı — takvim köprüsü

MT5'in ekonomik takvimi **yalnız MQL5 dilinden** okunabiliyor; Python
paketinde (`MetaTrader5==5.0.6090`) karşılığı yok. Bu klasör o boşluğu
geçmek için.

## Kurulum — `KUR.ps1` adım 7 yapıyor

Kurulum betiği bu klasördeki bütün `.mq5` dosyalarını bulduğu her MT5 veri
klasörüne kopyalayıp `MetaEditor64.exe /compile` ile derliyor. Terminal
klasörünün adı kurulum yolunun hash'i olduğu için makineden makineye değişir;
elle yol yazılmıyor, taranıyor.

Derleme komut satırından olur, **çalıştırmak olmaz** — betiğin bir grafiğe
iliştirilmesi gerekiyor:

**Gezgin (Ctrl+N) → Komut Dosyaları → `MicoTakvimDisaAktar` → çift tık.**

("Betikler" değil; MT5'in Türkçesinde bölümün adı **Komut Dosyaları**.)

## Ön koşul: takvim açık olmalı

**Araçlar → Seçenekler → Sunucu → "Haberleri etkinleştir"**, ve **Araç Kutusu
→ Takvim** sekmesi bir kez açılmalı — terminal takvimi talep üzerine indiriyor.

## Zaman aşımı (hata 5401)

İlk sürüm 900 günü tek çağrıda istedi ve `5401` ile döndü: terminal aralığı
sunucudan çekerken zaman aşımına uğruyor. Betik artık aralığı **45 günlük
parçalara** bölüyor ve her parçayı **6 kez** deniyor. Boş parça (tatil,
tarih öncesi) hatasız 0 döner ve beklemeden geçilir; alınamayan parça
adıyla birlikte raporlanır, sessizce düşmez.

`MicoTakvimTeshis` takvimin ne durumda olduğunu söyler: ülke sayısı, USD olay
sayısı, dar ve geniş pencere sonuçları, hata kodlarıyla. Dosya yazmaz.

## Çıktı

`MQL5\Files\micofx_takvim.csv`, noktalı virgül ayraçlı. Okuyan taraf
`claude/_takvim_oku.py`.

**Zaman alanı ham MT5 tamsayısı**: sunucunun duvar saati Unix epoch gibi
kodlanmış hâli, bar ve deal damgalarıyla aynı çerçeve. İki tarafta da
dönüştürülmüyor; okurken `sessions.server_datetime` kullanılır. Bu dosyada
`datetime.fromtimestamp` ya da `datetime(...).timestamp()` görürsen yanlıştır
— nedeni DEVAM'ın 2. bölümünde.

`importance`: 0 yok, 1 düşük, 2 orta, 3 yüksek. Açıklanmamış rakam
**boş** yazılır, sıfır değil — `HasActualValue()` ile ayrılıyor, çünkü
"veri 0,0 geldi" ile "veri henüz gelmedi" farklı şeyler.
