"""Bridge spool: her degisikligi kaydeder, hicbiri kacmaz.

Tek tur yerine surekli izler ve her yeni yaziyi spool dosyasina ekler.
Claude her uyandiginda spool'u okur - arada yazilan hicbir cevap atlanmaz.
"""
import os, time, sys, hashlib

WATCH = {"cursor": "cursor/FOR_CLAUDE.md",
         "chatgpt": "chatgpt/FOR_CLAUDE.md",
         "antigravity": "antigravity/FOR_CLAUDE.md"}
SPOOL = ".bridge/spool.md"
STATE = ".bridge/seen.txt"

def digest(p):
    try:
        with open(p, "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return ""

seen = {}
if os.path.exists(STATE):
    for line in open(STATE, encoding="utf-8"):
        k, _, v = line.strip().partition("=")
        if k:
            seen[k] = v
else:
    for k, p in WATCH.items():
        seen[k] = digest(p)

deadline = time.time() + 3300
hit = []
while time.time() < deadline:
    time.sleep(15)
    for k, p in WATCH.items():
        d = digest(p)
        if d and d != seen.get(k, ""):
            time.sleep(10)                       # yazma bitsin
            d = digest(p)
            seen[k] = d
            stamp = time.strftime("%d.%m %H:%M:%S")
            with open(SPOOL, "a", encoding="utf-8") as out:
                out.write(f"\n\n===== {k.upper()} — {stamp} =====\n")
                out.write(open(p, encoding="utf-8").read())
            hit.append(f"{k}@{stamp}")
    if hit:
        break
with open(STATE, "w", encoding="utf-8") as f:
    for k, v in seen.items():
        f.write(f"{k}={v}\n")
print("YENI:" + ",".join(hit) if hit else "ZAMAN ASIMI")
