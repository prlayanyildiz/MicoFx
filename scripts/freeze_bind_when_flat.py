"""Restart once flat so freeze-bind code + AP resume flag can load.

Cursor 04.09: live PID kept pre-freeze autopilot; AP was disabled and
``AUTOPILOT_RESUME_AFTER_RESTART`` armed. This helper POSTs
``/api/app/restart`` only when the book is flat (409 otherwise).
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
RESUME_FLAG = ROOT / ".bridge" / "AUTOPILOT_RESUME_AFTER_RESTART"
DONE_FLAG = ROOT / ".bridge" / "FREEZE_BIND_DONE.txt"
XAU_SL_PENDING = ROOT / ".bridge" / "XAU_SL_07_PENDING"
XAU_SL_REENABLE = ROOT / ".bridge" / "XAU_SL_07_REENABLE"


def _session(panel: str = PANEL):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    return op


def book_flat(op, panel: str = PANEL) -> tuple[bool, int]:
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/state", headers={"Origin": panel})
        ).read().decode()
    )
    n = len(body.get("positions") or [])
    return n == 0, n


def request_restart(op, panel: str = PANEL) -> tuple[int, str]:
    req = urllib.request.Request(
        panel + "/api/app/restart",
        data=b"{}",
        headers={"Origin": panel, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with op.open(req, timeout=30) as resp:
            return resp.status, resp.read().decode()[:300]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:300]


def should_restart(*, resume_flag: Path = RESUME_FLAG, flat: bool) -> bool:
    if not resume_flag.is_file():
        return False
    return bool(flat)


def verify_bind(
    panel: str = PANEL,
    *,
    timeout_sec: float = 90.0,
    poll_sec: float = 3.0,
) -> tuple[bool, str]:
    """After restart: AP on, resume flag gone, exec pipeline frozen."""
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    deadline = time.time() + float(timeout_sec)
    last = "panel henuz yok"
    while time.time() < deadline:
        try:
            op = _session(panel)
            st = json.loads(
                op.open(
                    urllib.request.Request(
                        panel + "/api/state", headers={"Origin": panel})
                ).read().decode()
            )
            ap = bool((st.get("system") or {}).get("autopilot_enabled"))
            from scripts.exec_gates import pipeline_frozen
            frozen = bool(pipeline_frozen())
            resume_gone = not RESUME_FLAG.is_file()
            if ap and frozen and resume_gone:
                msg = "bind OK: AP=on frozen=True resume_flag=gone"
                DONE_FLAG.parent.mkdir(parents=True, exist_ok=True)
                DONE_FLAG.write_text(msg + "\n", encoding="utf-8")
                # Claude 04.50 XAU sl 0.7 — best-effort after new PID loads waiver.
                # Bind stays OK even if land fails (income_loop retries).
                try:
                    from scripts.xau_sl_land import land as _xau_land
                    ok_l, msg_l = _xau_land(panel)
                    msg = f"{msg}; {msg_l}"
                    if not ok_l:
                        msg = f"{msg} (land retry later)"
                except Exception as exc:
                    msg = f"{msg}; xau_sl_land fail: {exc} (retry later)"
                return True, msg
            last = (
                f"AP={ap} frozen={frozen} resume_gone={resume_gone}"
            )
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            last = f"panel wait ({exc})"
        time.sleep(float(poll_sec))
    return False, f"bind VERIFY FAIL: {last}"


def wait_note(*, n_open: int) -> str:
    bits = [f"bekleniyor: {n_open} pozisyon acik (resume flag var)"]
    if XAU_SL_PENDING.is_file():
        bits.append("XAU_SL_07_PENDING")
    if XAU_SL_REENABLE.is_file():
        bits.append("REENABLE")
    return " | ".join(bits)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restart when flat to bind exec freeze + AP resume")
    parser.add_argument("--panel", default=PANEL)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--verify", action="store_true",
        help="After successful restart, wait until AP on + freeze bound")
    args = parser.parse_args()
    if not RESUME_FLAG.is_file():
        print("resume flag yok — restart gerekmiyor")
        return 0
    op = _session(args.panel)
    flat, n = book_flat(op, args.panel)
    if not should_restart(flat=flat):
        print(wait_note(n_open=n))
        return 0
    if args.dry_run:
        print("dry-run: restart edilecekti (kitap flat)")
        return 0
    code, body = request_restart(op, args.panel)
    print(f"restart HTTP {code}: {body}")
    if code not in (200, 202):
        return 1
    if args.verify:
        ok, msg = verify_bind(args.panel)
        print(msg)
        return 0 if ok else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
