# Bulut kurulum (en basit)

Depo private: **github.com/prlayanyildiz/MicoFx**  
Masaustu ile GitHub `main` ayni olmali.

---

## Ilk kurulum — 3 adim

### 1) Git kur
[git-scm.com/download/win](https://git-scm.com/download/win) → hep Next → bitince PowerShell’i **kapat / yeniden ac**.

### 2) Kodu al + kur
PowerShell’de (bir kere GitHub girisi isteyebilir):

```powershell
cd $env:USERPROFILE
git clone https://github.com/prlayanyildiz/MicoFx.git
cd MicoFx
.\KUR.bat
```

Klasor zaten varsa clone atma:

```powershell
cd $env:USERPROFILE\MicoFx
.\KUR.bat
```

`KUR.bat` Python / Node / Claude Code yoksa kurar, kodu gunceller, paketleri kurar.
Bitisinde masaustune **MicoFX** (baslat) ve **MicoFX Klasor** kisayollari atar
(nereye kurulursa kurulsun).

### 3) MT5 + baslat
1. MT5’e gir  
2. **Araclar → Secenekler → Uzman Danismanlar → Algoritmik alim satima izin ver**  
3. Masaustundeki **MicoFX** kisayoluna cift tikla  

---

## Kod guncellemesi (sonraki gunler)

```powershell
cd $env:USERPROFILE\MicoFx
git pull
```

Gerekirse `stop.bat` → `start.bat`.  
(Istersen yine `.\KUR.bat` — pull + paket kontrolu yapar.)

---

## Claude Code (opsiyonel)

```powershell
cd $env:USERPROFILE\MicoFx
claude
```

`claude` engellenirse: `claude.cmd`

---

## Kısa kurallar

- Ayni MT5 hesabinda yerelde + bulutta ayni anda bot calistirma.  
- `.venv` / `C:\MicoFX-venv` kopyalama — her makinede `KUR.bat` kurar.  
- `data\micofx.db` Git’e gitmez; ayarlar makinede kalir.
