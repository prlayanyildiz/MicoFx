okudugum commit: 02fb0d6
okuma zamani: 2026-08-15 22:03 (TSİ)

# Teşhis Raporu: AG1 — `enabled` Yamasının Sessizce Düşmesi

## 1. `enabled` yamasının düştüğü tam satır
- **`micofx/store.py:319-321`** (`Store.update_symbol` içi):
  ```python
  for key, value in patch.items():
      if key in current and value is not None:
          current[key] = value
  ```
- **Tetikleyici Nokta:** `micofx/web/app.py:880` (`patch_symbol` fonksiyonu, `SymbolPatch`).
  İstek gövdesi `{"patch": {"enabled": false}}` olarak geldiğinde, `SymbolPatch` (`extra="allow"`) bunu olduğu gibi kabul eder ve `body.model_dump()` sonucu `patch = {"patch": {"enabled": false}}` olur.
  `store.update_symbol`'a iletilen `patch` sözlüğünün tek anahtarı `"patch"`tir. `current` sözlüğünde (`SymbolConfig` alanları) `"patch"` anahtarı bulunmadığı için (`key in current` -> `False`), döngü bu anahtarı hiçbir işlem yapmadan atlar.

## 2. Neden sessiz düştüğü (`ok: true` dönme sebebi)
1. `micofx/web/app.py:45` adresindeki `SymbolPatch(BaseModel)` sınıfı `model_config = {"extra": "allow"}` kullandığı için gelen bilinmeyen anahtarları (`"patch"` gibi) Pydantic seviyesinde reddetmez.
2. `store.py:320` eşleşmeyen anahtarları sessizce yok sayar; ardından `updated = SymbolConfig.from_dict(current)` ile mevcut (değişmemiş) veriden nesne türetir.
3. `store._log_symbol_change` fonksiyonu `before` ile `updated.to_dict()` arasında fark görmediği için log da basmaz.
4. `patch_symbol` endpoint'i `return {"ok": True, "config": updated.to_dict(), ...}` döndürür. Sonuç: HTTP 200 / `ok: true`, fakat hiçbir alan değişmemiştir.

## 3. Panel arayüzü bunu hangi farklı yoldan yapıyor?
- **Endpoint:** Aynı endpoint (`POST /api/symbols/{symbol}`).
- **Gövde Biçimi (Fark):** Panel arayüzü (`micofx/web/static/app.js:1827-1829` ve `1081`), iç içe `{"patch": {...}}` sarmalayıcısı **kullanmaz**, doğrudan **düz (flat)** JSON gönderir:
  ```json
  {"enabled": false}
  ```
- `{"patch": {"enabled": false}}` şeklindeki sarmalanmış biçim ise sadece `POST /api/symbols-bulk` (`BulkPatch`, `app.py:56`) endpoint'inin kabul ettiği şablondu.

## 4. Aynı sessiz düşüşün geçerli olduğu başka alanlar
1. **Tüm Bilinmeyen / Hatalı Yazılmış Alanlar:**
   `SymbolConfig` dataclass alanları dışında kalan herhangi bir anahtar (örn. `{"enable": false}`, `{"is_enabled": false}`, `{"tp_atr": 1.5}`, `{"leverage": 50}`) `SymbolPatch(extra="allow")` üzerinden geçer ve `store.py:320`'de `key in current` şartını sağlamadığı için sessizce yutulup `ok: true` döner.
2. **`None` / `null` Değerler:**
   `store.py:320`'deki `value is not None` filtresi nedeniyle, örneğin `{"enabled": null}` veya `{"magic": null}` gönderildiğinde de alan güncellenmez ve sessizce `ok: true` döner.
