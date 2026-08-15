istem: 2
emin olmadığım yerler: Her iyileştirme turunun tam 2.000 yeni kombinasyonu tekrar puanlayıp puanlamadığı; bu yüzden iki kaba senaryo verdim.

1. Bir sembol için taban sayı: 12 aile × 3 zaman dilimi × en çok 2.000 = **72.000** aday. "5 tur" her turda bu büyüklükte ek arama ise toplam **432.000** aday; ilk tur dahil 5 toplam tur kastediliyorsa **360.000**. 19 sembol kitabın tamamında bu 1,37–8,21 milyon aday eder. Adaylar parametre komşuluğu nedeniyle bağımsız değildir; etkin aday sayısı daha düşüktür ama yüzlerce/binlerce olması bile yeterince büyüktür.

2. Holdout skoru gerçek kenar + gürültü ise, en yüksek olanın gürültüsü sistematik olarak pozitiftir. Bağımsız aday varsayımında beklenen en büyük standartlaştırılmış gürültü yaklaşık `sqrt(2 ln N)`dir: N=72.000 için ~4,7σ; N=360–432 bin için ~5,1σ. Bu yüzde cinsinden bir vaat değil: skor oynaklığı, holdout işlem sayısı, aday korelasyonu, parametre aralığı ve gün içi tekrar sayısı belirler. Ama "en iyiyi holdout'a göre seçme" kuralı, gerçek kenar sıfır olsa bile en iyinin yüksek görünmesini bekler.

3. Savunmaların etkisi:
   - Doğrulama → holdout sırası ilk filtreyi seçim verisine taşıdığı için faydalı. Fakat holdout sonucu aday/running seçmek veya uygulatmak için kullanılıyorsa holdout artık test değil seçim verisidir; çoklu karşılaştırma orada geri gelir.
   - `%70 pozitif seçim dilimi` yalnızca seçim dilimindeki kırılgan adayları eleyebilir. Eşik aynı seçim verisinde binlerce kez denendiği için kendi seçim yanlılığına maruzdur; holdout winner's curse'ünü düzeltmez.
   - Retention, holdout/selection oranını aynı holdout üzerinde kapı yapıyor. Bu yararlı bir kalite filtresi olabilir ama holdout'ta yüksek rastlantı sonucu alan adayın retention'ı da yapay olarak iyi olabilir. Gün içinde aynı holdout'u yeniden kullanmak bu sızıntıyı büyütür.

4. Ölçüm: Bundan sonraki N optimizasyon dönemi için aday uzayını ve kuralları başlangıçta kilitle. Mevcut holdout'u H1 olarak kullan; H1 ile seçilen/uygulanan her adayın puanını, kararlar görülmeden ayrılmış daha yeni H2'de aynen hesapla. Sembol bazında `score(H1)-score(H2)`, pozitiflik oranı, retention ve canlıya giden adayların H2 başarısını raporla; blok-bootstrap ile ortalama farkın güven aralığını ver. Ek kontrol: aynı H1 üzerinde kaç kez seçim yapıldığını (aday sayısı, tarama sayısı, karar sayısı) kaydet; bu sayaç ile H1→H2 farkının artıp artmadığını test et. H2 de seçime girerse test olmaktan çıkar; yeni, kilitli bir H3 gerekir.

5. Uygulanabilir azaltmalar:
   - **Kilitleme + yürüyen test:** Her karar döneminde seçim/validasyon/H1/H2 tarihleri değişmez; yalnız H2 nihai rapordur ve hiçbir parametre/strateji seçmez. Maliyet: karar gecikir ve her turda daha az eğitim verisi kalır.
   - **Nested walk-forward:** İç pencerede aile/TF/parametre seç, dış pencerede sadece değerlendir; dış pencereleri birleştirip tek karar ver. Maliyet: hesaplama ve veri ihtiyacı ciddi artar; 5 dakikalık sistemde az işlemli semboller daha sık "yetersiz örnek" verir.
   - **Aday bütçesi:** Önceki, yalnız seçim verisine dayalı eleme ile sembol başına sabit sayıda finalist bırak; holdout'a yalnız finalistler geçsin. Maliyet: gerçek iyi aday erken elenebilir; bütçe, geçmiş sonuç bakılmadan sabitlenmeli.
   - **Düzeltilmiş kabul eşiği:** Holdout puanı yerine her adayın blok-bootstrap alt güven sınırını kullan; aday ancak alt sınır pozitif ve mevcut ayarı geçiyorsa kabul edilsin. Aile/TF/parametre taraması için eşik, etkin finalist sayısı büyüdükçe sıkılaşmalı. Maliyet: yanlış negatif artar, özellikle 40 işlem civarında birçok aday bekler.
   - **Tekrar kullanım kotası:** Aynı H1 üzerinde yeniden tarama/uygulama sayısını kaydet ve önceden belirlenmiş kota aşılınca H1'i sadece gözlem ekranına indir, seçimi yeni pencereye taşı. Maliyet: gün içi adaptasyon yavaşlar; karşılığı testin anlamını korumaktır.
