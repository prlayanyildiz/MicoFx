"""cost_free_mode is a no-op for system cost toggles.

Broker commission_per_lot=0 does not mean fills are free — spread is the
live cost. Disabling charge_costs (04.09 income --auto) paper-optimized the
book and family_audit then swapped SpotBrent/NAS off measured incumbents.
"""
from __future__ import annotations

import urllib.error
import urllib.request

PANEL = "http://127.0.0.1:8900"


def apply_cost_free_mode(headers: dict[str, str]) -> list[str]:
    """Report commission shape; never write charge_costs / block_high_cost."""
    done: list[str] = []
    try:
        req = urllib.request.Request(f"{PANEL}/api/state", headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            import json
            st = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError):
        return ["cost_free: state okunamadi"]

    try:
        import json
        syms = json.loads(urllib.request.urlopen(
            urllib.request.Request(f"{PANEL}/api/symbols", headers=headers), timeout=20).read())
    except (urllib.error.URLError, TimeoutError, OSError):
        return ["cost_free: symbols okunamadi"]

    enabled = [s for s in syms.get("symbols", []) if s.get("enabled")]
    if not enabled:
        return ["cost_free: aktif sembol yok"]

    all_zero_comm = all(float(s.get("commission_per_lot") or 0) <= 0 for s in enabled)
    sys = st.get("system") or {}
    done.append(
        f"sistem charge_costs={bool(sys.get('charge_costs', True))} "
        f"block_high_cost={bool(sys.get('block_high_cost', True))} "
        f"(cost_free dokunulmadi — charge_costs korundu)"
    )
    done.append("sembol gate korunur (cost_rank/max_spread silinmez)")
    if all_zero_comm:
        done.append("komisyon 0 — spread hâlâ maliyet; charge_costs acik kalsin")
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
