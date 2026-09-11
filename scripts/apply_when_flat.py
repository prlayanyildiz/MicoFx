"""Land the dead-gate fixes at the first moment the book is flat.

``scripts/dead_gate_scan.py`` found four settings that had switched a
mechanism off, and two of the fixes need the engine reloaded - the AI door
that makes them writable ships in app.py. Restarting while a ticket is open is
avoidable, and the operator should not have to sit and watch for a gap.

So this waits for one: no open positions, no search running, then restarts
through the panel's own door and writes the four values. It gives up rather
than forcing anything - if the book never goes flat inside the window, nothing
happens and it says so.

Read the plan, not the mechanism: every value here is either a shipped default
being restored or a number the measurement in this session justified.

    python scripts/apply_when_flat.py --minutes 180
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from panel_session import opener  # noqa: E402

PANEL = "http://127.0.0.1:8900"

# Each entry: (endpoint, payload, why). Restoring a shipped default counts as
# evidence; a new number needs a measurement behind it.
AI_FIXES = {
    # Shipped 6. Stored 80, against a busiest symbol-hour bucket of 17 - the
    # bad-hour blocker could never fire, while UTC 3/11/12/13/16 carried
    # -60.78R, 77% of the loss on 27% of the trades.
    "bad_hour_min_trades": 6,
    # Shipped 50. Stored 100, against a busiest symbol of 98 trades in the
    # supervisor's own 30-day lookback - edge decay had never once fired.
    "edge_decay_min_trades": 50,
}
# 0.6 sits between rungs of a six-part ratio and is enforced as 4/6. Same
# behaviour, stated honestly, so the next reader is not misled the way 0.7
# misled everyone.
OPT_FIXES = {"min_positive_ratio": round(4 / 6, 4)}
# max_spread_atr: measured this session, 0.25 down to 0.05 return an identical
# +102.36R over 665 holdout trades, so this changes nothing the backtest can
# see - but 0.25 sits above the whole search grid (top 0.15), so a search
# could only ever lower it and never restore it. Inside the grid the axis is
# live again.
# max_positions 0: the per-symbol cap and its 1..5 clip came off on the
# operator's instruction ("max poz limit ve sinirini kaldir"); 0 is the repo's
# idiom for off. The book-wide max_concurrent_risk_pct (25%) governs now.
# adx_min / min_body_ratio: measured jointly on the holdout 11.09, both
# validated. GER40 10->15 with 0->0.4 moves +0.0684 -> +0.0780 R/day at
# PF 1.43 -> 1.59; NAS100 0->10 with 0.2->0.1 moves +0.1452 -> +0.1719 R/day
# at PF 1.16 -> 1.19 and MORE trades (1144 vs 1127). The axes compose better
# than either alone. XAUUSD measured unchanged on all three, so it is left
# alone rather than nudged for symmetry.
SYMBOL_FIXES = {
    "XAUUSD": {"max_spread_atr": 0.05, "max_positions": 0},
    "GER40": {"max_positions": 0, "adx_min": 15.0, "min_body_ratio": 0.4},
    "NAS100": {"max_positions": 0, "adx_min": 10.0, "min_body_ratio": 0.1},
}
# US30 leaves the book for good (operator: "us30 verimsizse sil spread 20
# onda"). It is already disabled, so this only fires once its last ticket has
# closed - deleting a row with an open ticket would orphan the ticket.
DELETE_SYMBOLS = ("US30",)


def _get(op, path: str) -> dict:
    return json.loads(op.open(f"{PANEL}{path}", timeout=15).read())


def _post(op, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{PANEL}{path}", data=json.dumps(payload).encode(), method="POST",
        headers={"Origin": PANEL, "Content-Type": "application/json"})
    return json.loads(op.open(req, timeout=30).read())


def flat(state: dict) -> bool:
    return (not (state.get("positions") or [])
            and str((state.get("opt") or {}).get("state") or "") != "running")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--minutes", type=float, default=180.0)
    ap.add_argument("--poll", type=float, default=60.0)
    args = ap.parse_args(argv)

    deadline = time.time() + args.minutes * 60.0
    while time.time() < deadline:
        try:
            op = opener()
            state = _get(op, "/api/state")
        except Exception as exc:                       # noqa: BLE001 - a tool
            print(f"{time.strftime('%H:%M:%S')} panel okunamadi: {exc}",
                  flush=True)
            time.sleep(args.poll)
            continue
        if not flat(state):
            n = len(state.get("positions") or [])
            print(f"{time.strftime('%H:%M:%S')} bekliyor - pozisyon {n}, "
                  f"opt {(state.get('opt') or {}).get('state')}", flush=True)
            time.sleep(args.poll)
            continue

        print(f"{time.strftime('%H:%M:%S')} kitap bos - yeniden baslatiliyor",
              flush=True)
        _post(op, "/api/app/restart", {})
        time.sleep(30)
        for _ in range(20):
            try:
                op = opener()
                _get(op, "/api/state")
                break
            except Exception:                          # noqa: BLE001 - a tool
                time.sleep(4)
        else:
            print("panel geri gelmedi - elle bakin", flush=True)
            return 1

        ok = True
        try:
            res = _post(op, "/api/ai/settings", dict(AI_FIXES))
            got = res.get("settings") or {}
            for key, want in AI_FIXES.items():
                print(f"  {key}: {got.get(key)} (istenen {want})", flush=True)
                ok = ok and got.get(key) == want
        except urllib.error.HTTPError as exc:
            print(f"  AI ayarlari REDDEDILDI: {exc.code} "
                  f"{exc.read().decode()[:200]}", flush=True)
            ok = False

        try:
            res = _post(op, "/api/opt/params", dict(OPT_FIXES))
            got = res.get("params") or {}
            for key, want in OPT_FIXES.items():
                print(f"  {key}: {got.get(key)} (istenen {want})", flush=True)
            if res.get("note"):
                print(f"  not: {res['note']}", flush=True)
        except urllib.error.HTTPError as exc:
            print(f"  opt params REDDEDILDI: {exc.code} "
                  f"{exc.read().decode()[:200]}", flush=True)
            ok = False

        for sym, patch in SYMBOL_FIXES.items():
            try:
                res = _post(op, f"/api/symbols/{sym}", {"patch": patch})
                row = next((s for s in (res.get("symbols") or [])
                            if s.get("symbol") == sym), {})
                for key, want in patch.items():
                    print(f"  {sym}.{key}: {row.get(key)} (istenen {want})",
                          flush=True)
            except urllib.error.HTTPError as exc:
                print(f"  {sym} REDDEDILDI: {exc.code} "
                      f"{exc.read().decode()[:200]}", flush=True)
                ok = False

        for sym in DELETE_SYMBOLS:
            try:
                state = _get(op, "/api/state")
                if any(str(pos.get("symbol")) == sym
                       for pos in (state.get("positions") or [])):
                    print(f"  {sym}: hala acik bileti var, SILINMEDI", flush=True)
                    ok = False
                    continue
                req = urllib.request.Request(
                    f"{PANEL}/api/symbols/{sym}", method="DELETE",
                    headers={"Origin": PANEL})
                op.open(req, timeout=30).read()
                left = [r.get("symbol") for r in
                        (_get(op, "/api/symbols").get("symbols") or [])]
                print(f"  {sym} silindi - kitap: {left}", flush=True)
                ok = ok and sym not in left
            except urllib.error.HTTPError as exc:
                print(f"  {sym} SILINEMEDI: {exc.code} "
                      f"{exc.read().decode()[:200]}", flush=True)
                ok = False

        print("TAMAM" if ok else "KISMEN - yukaridaki redlere bakin", flush=True)
        return 0 if ok else 1

    print("sure doldu - kitap bosalmadi, hicbir sey degismedi", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
