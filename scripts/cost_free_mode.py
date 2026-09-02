"""Zero-cost book mode — commission/spread gates off when broker charges none."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

PANEL = "http://127.0.0.1:8900"


def apply_cost_free_mode(headers: dict[str, str]) -> list[str]:
    """Turn off cost charging, live cost gate, spread/cost_rank entry gates."""
    h = {**headers, "Origin": PANEL, "Content-Type": "application/json"}
    done: list[str] = []

    try:
        req = urllib.request.Request(f"{PANEL}/api/state", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            st = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return ["cost_free: state okunamadi"]

    syms = json.loads(urllib.request.urlopen(
        urllib.request.Request(f"{PANEL}/api/symbols", headers=headers), timeout=20).read())

    enabled = [s for s in syms.get("symbols", []) if s.get("enabled")]
    if not enabled:
        return ["cost_free: aktif sembol yok"]

    all_zero_comm = all(float(s.get("commission_per_lot") or 0) <= 0 for s in enabled)
    patch = {
        "charge_costs": False,
        "block_high_cost": False,
        "max_cost_pct_of_risk": 0.0,
    }
    try:
        req = urllib.request.Request(
            f"{PANEL}/api/system", data=json.dumps(patch).encode(), headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            json.loads(resp.read().decode())
        done.append("sistem charge_costs=false block_high_cost=false")
    except urllib.error.HTTPError as exc:
        return [f"cost_free sistem fail: {exc.read().decode()[:120]}"]

    for sym_row in enabled:
        sym = sym_row["symbol"]
        hist = json.loads(urllib.request.urlopen(
            urllib.request.Request(
                f"{PANEL}/api/opt/history?symbol={sym}&limit=40", headers=headers),
            timeout=30).read())
        run = next(
            (r for r in (hist.get("history") or [])
             if r.get("validated") and r.get("strategy") == sym_row.get("strategy")
             and r.get("timeframe") == sym_row.get("timeframe")),
            None,
        )
        if run is None:
            run = next((r for r in (hist.get("history") or []) if r.get("validated")), None)
        if run is None:
            done.append(f"{sym} gate kapatma: opt kayit yok")
            continue
        gate_patch = {"max_spread_atr": 0.0, "cost_rank_max": 0.0}
        payload = json.dumps({
            "symbol": sym,
            "run_id": int(run["id"]),
            "params": gate_patch,
            "force": True,
            "gates_only": True,
        }).encode()
        try:
            req = urllib.request.Request(
                f"{PANEL}/api/opt/apply", data=payload, headers=h, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                json.loads(resp.read().decode())
            done.append(f"{sym} spread/cost_rank kapali (run {run['id']})")
        except urllib.error.HTTPError as exc:
            done.append(f"{sym} gate fail: {exc.read().decode()[:100]}")

    if all_zero_comm:
        done.append("komisyon 0 — maliyet modeli kapali")
    return done


def main() -> int:
    req = urllib.request.Request(f"{PANEL}/", method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        cookies = resp.headers.get_all("Set-Cookie") or []
    headers = {
        "Origin": PANEL,
        "Cookie": "; ".join(c.split(";")[0] for c in cookies) if cookies else "",
    }
    for line in apply_cost_free_mode(headers):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
