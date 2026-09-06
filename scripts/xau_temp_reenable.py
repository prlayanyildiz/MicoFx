"""Re-enable XAU after temp night disable (Claude 05:58 option A).

Flag: ``.bridge/XAU_TEMP_DISABLE_UNTIL_EU``. Does not touch SL/family/msa.
Uses broker ``decision_now`` / panel clock via /api/state mt5.server_time when
hour >= EU_OPEN_HOUR (default 8).

Wake/inbox writes only after a verified live ``enabled=true`` GET — never on
mocked POSTs (tests must not touch ``cursor/FOR_CLAUDE.md``).
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
FLAG = ROOT / ".bridge" / "XAU_TEMP_DISABLE_UNTIL_EU"
INBOX = ROOT / "cursor" / "FOR_CLAUDE.md"
WAKE = ROOT / ".bridge" / "WAKE.txt"
EU_OPEN_HOUR = 8  # broker wall hour (GER/US30 windows start ~08:00)


def _session(panel: str = PANEL):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    return op


def broker_hour(op, panel: str = PANEL) -> int | None:
    raw = op.open(
        urllib.request.Request(panel + "/api/state", headers={"Origin": panel})
    ).read().decode()
    st = json.loads(raw)
    mt5 = st.get("mt5") or {}
    stamp = str(mt5.get("server_time") or "")
    # "2026-09-04 08:01:02"
    parts = stamp.replace("T", " ").split()
    if len(parts) < 2:
        return None
    try:
        return int(parts[1].split(":")[0])
    except (TypeError, ValueError, IndexError):
        return None


def xau_enabled(op, panel: str = PANEL) -> bool | None:
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/symbols", headers={"Origin": panel})
        ).read().decode()
    )
    for row in body.get("symbols") or []:
        if str(row.get("symbol") or "") == "XAUUSD":
            return bool(row.get("enabled"))
    return None


def _notify_claude(*, hour: int | None) -> None:
    """Live-only wake. INBOX/WAKE are module attrs (tests redirect them)."""
    try:
        WAKE.parent.mkdir(parents=True, exist_ok=True)
        WAKE.write_text("WAKE\n", encoding="utf-8")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        note = (
            f"# Cursor -> Claude -- {ts} -- XAU EU re-enable: enabled=true "
            f"(broker_h={hour}). sl/msa/family dokunulmadi.\n\n"
            "Gece temp-disable kalkti. Streak/baseline izlemeye devam.\n"
            "MICO MOLA yok.\n"
        )
        prev = INBOX.read_text(encoding="utf-8") if INBOX.is_file() else ""
        INBOX.parent.mkdir(parents=True, exist_ok=True)
        INBOX.write_text(
            note + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
    except OSError:
        pass


def reenable(
    panel: str = PANEL,
    *,
    force: bool = False,
    eu_hour: int = EU_OPEN_HOUR,
    notify: bool = True,
) -> tuple[bool, str]:
    if not FLAG.is_file() and not force:
        return True, "XAU temp-disable flag yok"
    op = _session(panel)
    en = xau_enabled(op, panel)
    if en is True:
        try:
            FLAG.unlink(missing_ok=True)
        except OSError:
            pass
        return True, "XAU zaten enabled — flag temiz"
    hour = broker_hour(op, panel)
    if not force and (hour is None or hour < int(eu_hour)):
        return True, f"XAU disable bekliyor (broker_h={hour}, eu>={eu_hour})"
    payload = json.dumps({"enabled": True}).encode()
    req = urllib.request.Request(
        panel + "/api/symbols/XAUUSD",
        data=payload,
        headers={
            "Origin": panel,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with op.open(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except Exception as exc:
        return False, f"XAU re-enable fail: {exc}"
    # Confirm on a fresh GET — POST body alone is not enough (and mocks must
    # not claim live success).
    en_after = xau_enabled(op, panel)
    if en_after is not True:
        return False, f"XAU re-enable dogrulanamadi: enabled={en_after} body={body}"
    try:
        FLAG.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        from scripts.xau_post_eu_watch import arm as arm_post_eu
        from scripts.xau_streak_watch import fetch_autopsy_rows
        rows = fetch_autopsy_rows(panel)
        arm_post_eu(autopsy_n=len(rows), seed_rows=rows)
    except Exception:
        try:
            from scripts.xau_post_eu_watch import arm as arm_post_eu
            arm_post_eu()
        except Exception:
            pass
    if notify:
        _notify_claude(hour=hour)
    return True, f"XAU enabled=true (EU re-enable h={hour})"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--panel", default=PANEL)
    p.add_argument("--force", action="store_true")
    p.add_argument("--eu-hour", type=int, default=EU_OPEN_HOUR)
    p.add_argument("--no-notify", action="store_true")
    args = p.parse_args()
    ok, msg = reenable(
        args.panel,
        force=args.force,
        eu_hour=args.eu_hour,
        notify=not args.no_notify,
    )
    print(msg, flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
