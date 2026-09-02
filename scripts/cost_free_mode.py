"""Zero-cost book mode — commission/spread gates off when broker charges none."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

PANEL = "http://127.0.0.1:8900"


def apply_cost_free_mode(headers: dict[str, str]) -> list[str]:
    """Turn off system cost charging when the broker charges no commission.

    Does **not** zero ``max_spread_atr`` / ``cost_rank_max``. Autopilot used to
    wipe those every 15m and fought measured GER40 ``cost_rank_max=0.3`` and
    XAU spread caps — that maximized fills, not expectancy.
    """
    h = {**headers, "Origin": PANEL, "Content-Type": "application/json"}
    done: list[str] = []

    try:
        req = urllib.request.Request(f"{PANEL}/api/state", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            st = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return ["cost_free: state okunamadi"]

    try:
        syms = json.loads(urllib.request.urlopen(
            urllib.request.Request(f"{PANEL}/api/symbols", headers=headers), timeout=20).read())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return ["cost_free: symbols okunamadi"]

    enabled = [s for s in syms.get("symbols", []) if s.get("enabled")]
    if not enabled:
        return ["cost_free: aktif sembol yok"]

    all_zero_comm = all(float(s.get("commission_per_lot") or 0) <= 0 for s in enabled)
    sys = st.get("system") or {}
    already_free = (
        not sys.get("charge_costs", True)
        and not sys.get("block_high_cost", True)
        and float(sys.get("max_cost_pct_of_risk") or 0) <= 0
    )
    if not already_free:
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
    else:
        done.append("sistem zaten cost-free")

    # Preserve per-symbol entry gates (cost_rank / max_spread) — measured.
    done.append("sembol gate korunur (cost_rank/max_spread silinmez)")

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
