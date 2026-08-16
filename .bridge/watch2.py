import os, time, sys, hashlib
def dg(p):
    try:
        with open(p,'rb') as f: return hashlib.sha1(f.read()).hexdigest()
    except OSError: return ""
W={"cursor":"cursor/FOR_CLAUDE.md","chatgpt":"chatgpt/FOR_CLAUDE.md","antigravity":"antigravity/FOR_CLAUDE.md"}
seen={k:dg(p) for k,p in W.items()}
LOG='logs/micofx.log'
def optdone():
    try:
        return 'Optimizasyon tamamlandi' in open(LOG,encoding='utf-8',errors='ignore').read()[-4000:]
    except OSError: return False
base_done = optdone()
deadline=time.time()+3300
while time.time()<deadline:
    time.sleep(20)
    for k,p in W.items():
        d=dg(p)
        if d and d!=seen[k]:
            time.sleep(10)
            with open('.bridge/spool.md','a',encoding='utf-8') as o:
                o.write(f"\n\n===== {k.upper()} — {time.strftime('%d.%m %H:%M')} =====\n")
                o.write(open(p,encoding='utf-8').read())
            print(f"YENI:{k}"); sys.exit(0)
    if not base_done and optdone():
        print("OPT BITTI"); sys.exit(0)
print("ZAMAN ASIMI")
