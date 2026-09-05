"""Land pending XAU sl widen after freeze-bind restart (Claude 04:50 explicit OK).

Live pre-restart PID refused last-seg regression; new PID loads the
upgrade_robust waiver. This helper is idempotent: no flag → no-op;
already at target → clears flag.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
PENDING = ROOT / ".bridge" / "XAU_SL_07_PENDING"
DONE = ROOT / ".bridge" / "XAU_SL_07_DONE.txt"
REENABLE = ROOT / ".bridge" / "XAU_SL_07_REENABLE"
STREAK_STATE = ROOT / ".bridge" / "XAU_STREAK_STATE.json"
SYMBOL = "XAUUSD"
TARGET_SL = 0.7


def _session(panel: str = PANEL):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    return op


def _symbol_row(op, panel: str = PANEL) -> dict:
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/symbols", headers={"Origin": panel})
        ).read().decode()
    )
    for row in body.get("symbols") or []:
        if str(row.get("symbol") or "") == SYMBOL:
            return dict(row)
    raise KeyError(SYMBOL)


def land(panel: str = PANEL) -> tuple[bool, str]:
    if not PENDING.is_file():
        return True, "pending flag yok"
    op = _session(panel)
    row = _symbol_row(op, panel)
    try:
        cur = float(row.get("sl_atr_mult") or 0.0)
    except (TypeError, ValueError):
        cur = 0.0
    if abs(cur - TARGET_SL) < 1e-9:
        PENDING.unlink(missing_ok=True)
        DONE.write_text(f"already sl={TARGET_SL:g}\n", encoding="utf-8")
        _reset_streak()
        re_msg = _reenable_if_armed(op, panel)
        return True, f"{SYMBOL} zaten sl={TARGET_SL:g}" + (
            f"; {re_msg}" if re_msg else "")

    pend = row.get("pending_exit_patch") or {}
    try:
        pend_sl = float(pend.get("sl_atr_mult") or 0.0) if isinstance(pend, dict) else 0.0
    except (TypeError, ValueError):
        pend_sl = 0.0
    if abs(pend_sl - TARGET_SL) < 1e-9:
        return True, f"{SYMBOL} sl {TARGET_SL:g} kuyrukta (flat bekleniyor)"

    try:
        score = float(row.get("opt_score") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    payload = json.dumps({
        "symbol": SYMBOL,
        "params": {"sl_atr_mult": TARGET_SL},
        "score": score,
        "force": True,
    }).encode()
    req = urllib.request.Request(
        panel + "/api/opt/apply",
        data=payload,
        headers={"Origin": panel, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with op.open(req, timeout=180) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return False, f"apply HTTP {exc.code}: {exc.read().decode()[:300]}"
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return False, f"apply fail: {exc}"
    row2 = _symbol_row(op, panel)
    try:
        landed = float(row2.get("sl_atr_mult") or 0.0)
    except (TypeError, ValueError):
        landed = 0.0
    deferred = bool(isinstance(body, dict) and body.get("deferred"))
    pend2 = row2.get("pending_exit_patch") or {}
    try:
        pend2_sl = float(pend2.get("sl_atr_mult") or 0.0) if isinstance(pend2, dict) else 0.0
    except (TypeError, ValueError):
        pend2_sl = 0.0
    if abs(landed - TARGET_SL) > 1e-9:
        if deferred or abs(pend2_sl - TARGET_SL) < 1e-9:
            # Keep PENDING + REENABLE until live sl is 0.7.
            return True, f"{SYMBOL} sl {cur:g}->{TARGET_SL:g} kuyrukta"
        return False, f"apply returned but sl={landed:g} body={body!r}"[:300]
    PENDING.unlink(missing_ok=True)
    DONE.parent.mkdir(parents=True, exist_ok=True)
    DONE.write_text(f"landed sl {cur:g}->{TARGET_SL:g}\n", encoding="utf-8")
    _reset_streak()
    re_msg = _reenable_if_armed(op, panel)
    return True, f"{SYMBOL} landed sl {cur:g}->{TARGET_SL:g}" + (
        f"; {re_msg}" if re_msg else "")


def _reenable_if_armed(op, panel: str = PANEL) -> str:
    if not REENABLE.is_file():
        return ""
    payload = json.dumps({"enabled": True}).encode()
    req = urllib.request.Request(
        panel + f"/api/symbols/{SYMBOL}",
        data=payload,
        headers={"Origin": panel, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = op.open(req, timeout=30)
        try:
            raw = resp.read()
        finally:
            close = getattr(resp, "close", None)
            if callable(close):
                close()
        json.loads(raw.decode() if isinstance(raw, (bytes, bytearray)) else raw)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError,
            json.JSONDecodeError, TypeError, AttributeError) as exc:
        return f"re-enable fail: {exc}"
    REENABLE.unlink(missing_ok=True)
    return "enabled=true"


def _reset_streak() -> None:
    try:
        STREAK_STATE.write_text(
            json.dumps({
                "alerted_level": "ok",
                "streak": 0,
                "exp_alerted": False,
                "ts": "reset-after-sl-land",
                "note": "new sl baseline; streak recount from next closes",
            }, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def main() -> int:
    p = argparse.ArgumentParser(description="Pending XAU sl 0.7 land")
    p.add_argument("--panel", default=PANEL)
    args = p.parse_args()
    ok, msg = land(args.panel)
    print(msg, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
