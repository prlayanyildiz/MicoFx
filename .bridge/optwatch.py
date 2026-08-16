import time, sys
LOG='logs/micofx.log'
def tail():
    try: return open(LOG,encoding='utf-8',errors='ignore').read()[-3000:]
    except OSError: return ''
base = tail().count('Optimizasyon tamamlandi')
deadline = time.time()+3000
while time.time() < deadline:
    time.sleep(30)
    if tail().count('Optimizasyon tamamlandi') > base:
        time.sleep(5); print('OPT BITTI'); sys.exit(0)
print('ZAMAN ASIMI')
