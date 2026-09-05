"""Poll until first post-restart close (EU window + buffer).

Prefer the durable path: ``baseline_accumulate_watch`` already calls
``maybe_alert_first_new_close`` each tick (WMI-detached via schtask). This
script is a one-shot sidecar for ad-hoc hunts — do not leave it attached to a
Cursor/agent job object (exit=-1 churn).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.session_open_silence import SESSION_H_HI, SESSION_H_LO, snapshot  # noqa: E402
from scripts.xau_streak_watch import baseline_status, fetch_autopsy_rows  # noqa: E402


def main() -> int:
    deadline = time.time() + 8 * 3600
    while time.time() < deadline:
        try:
            bl = baseline_status(len(fetch_autopsy_rows()))
            sil = snapshot()
            print(
                f"tick new={bl.get('new_trades')} "
                f"silence_fire={sil.get('fire')} "
                f"open_min={sil.get('minutes_open')} "
                f"sig={sil.get('signals')} "
                f"bar={((sil.get('bar_health') or {}).get('overall'))}",
                flush=True,
            )
            if int(bl.get("new_trades") or 0) >= 1:
                print("AGENT_LOOP_WAKE_first_close_poll", flush=True)
                (ROOT / ".bridge" / "WAKE.txt").write_text(
                    "WAKE first close\n", encoding="utf-8")
                return 0
            om = sil.get("minutes_open")
            if (
                om is not None
                and int(om) > (SESSION_H_HI - SESSION_H_LO + 1) * 60
                and not sil.get("in_window")
            ):
                print("poll window ended", flush=True)
                return 0
        except Exception as exc:
            print(f"err {exc}", flush=True)
        time.sleep(60)
    print("poll deadline", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())