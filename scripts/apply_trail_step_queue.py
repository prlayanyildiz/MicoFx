"""Report trail_step apply readiness (panel hands-off; needs WFO or in-process apply).

Mutabakat targets: US30 0.8, NAS100 1.6. Symbol POST is 400; opt/apply needs a
matching stamp. This prints open book + live vs target — does not invent stamps.
"""
from __future__ import annotations

import json
import urllib.request

PANEL = "http://127.0.0.1:8900"
TARGETS = {"US30": 0.8, "NAS100": 1.6}


def main() -> int:
    req = urllib.request.Request(f"{PANEL}/", method="GET")
    with urllib.request.urlopen(req, timeout=5) as resp:
        cookies = resp.headers.get_all("Set-Cookie") or []
    h = {"Origin": PANEL}
    if cookies:
        h["Cookie"] = "; ".join(c.split(";", 1)[0] for c in cookies)
    def get(path):
        r = urllib.request.Request(f"{PANEL}{path}", headers=h)
        with urllib.request.urlopen(r, timeout=20) as resp:
            return json.loads(resp.read().decode())
    state = get("/api/state")
    open_syms = sorted({str(p.get("symbol") or "") for p in (state.get("positions") or [])})
    print(f"open={open_syms or '-'}")
    for row in get("/api/symbols").get("symbols") or []:
        sym = row.get("symbol")
        if sym not in TARGETS:
            continue
        cur = float(row.get("trail_step_atr") or 0)
        want = TARGETS[sym]
        status = "OK" if abs(cur - want) < 1e-9 else "NEED_WFO_OR_INPROCESS_APPLY"
        note = "OPEN" if sym in open_syms else "flat"
        print(f"{sym}: live={cur} want={want} {status} ({note})")
    print("note: trail_step_atr panelden yazilamaz; POST /api/opt/apply stamp eslesmesi ister")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
