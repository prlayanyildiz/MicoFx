# MQL5 tarafı — takvim köprüsü

MT5'in ekonomik takvimi **yalnız MQL5 dilinden** okunabiliyor; Python
paketinde (`MetaTrader5==5.0.6090`) karşılığı yok. Bu klasör o boşluğu
geçmek için.

## Kurulum

Betik terminalin veri klasöründe derli duruyor. Yeni bir makinede:

```
copy mql5\MicoTakvimDisaAktar.mq5 ^
  "%APPDATA%\MetaQuotes\Terminal\<ID>\MQL5\Scripts\"
"C:\Program Files\Pepperstone MetaTrader 5\MetaEditor64.exe" ^
  /compile:"...\MQL5\Scripts\MicoTakvimDisaAktar.mq5" /log
```

Derleme komut satırından olur, **çalıştırmak olmaz** — betiğin bir grafiğe
iliştirilmesi gerekiyor. Gezgin (Ctrl+N) → Betikler → grafiğe sürükle.

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
