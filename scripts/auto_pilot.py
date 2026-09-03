"""Manual autopilot tick via the live panel (no second DB writer).

In-process autopilot owns the income loop. This CLI only POSTs
``/api/autopilot/tick`` so writes stay in the running bot.

Usage:
    C:\\MicoFX-venv\\Scripts\\python.exe scripts/auto_pilot.py
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

PANEL = "http://127.0.0.1:8900"


def main() -> int:
    try:
        req = urllib.request.Request(f"{PANEL}/", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            cookies = resp.headers.get_all("Set-Cookie") or []
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"panel kapali ({PANEL}): {exc}", file=sys.stderr)
        print("Autopilot bot icinde — once paneli acin (Sistem > Gelir autopilot).")
        return 1
    headers = {"Origin": PANEL, "Content-Type": "application/json"}
    if cookies:
        headers["Cookie"] = "; ".join(c.split(";")[0] for c in cookies)
    try:
        req = urllib.request.Request(
            f"{PANEL}/api/autopilot/tick",
            data=b"{}",
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(exc.read().decode()[:400], file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for line in body.get("summary") or []:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
