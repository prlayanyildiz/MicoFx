"""Monday fill-rate pulse — retired with SpotBrent (12.09 merge).

Book fill pressure is watched inside ``baseline_accumulate_watch`` via
``us30_fill_watch`` (GER40 / NAS100 session open). Do not schedule this
script; CLI prints a retired notice only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PANEL = "http://127.0.0.1:8900"
STATE = ROOT / ".bridge" / "FILL_PULSE_STATE.json"
WAKE = ROOT / ".bridge" / "WAKE.txt"
INBOX = ROOT / "cursor" / "FOR_CLAUDE.md"
_RETIRED = (
    "fill_pulse: SpotBrent retired — book fill is baseline us30_fill_watch"
)


def snapshot() -> dict:
    return {
        "retired": True,
        "note": _RETIRED,
        "spot_opened": 0,
        "spot_signals": 0,
        "spot_fill": 0.0,
        "book_opened": 0,
        "book_signals": 0,
        "book_fill": 0.0,
    }


def maybe_alert(cur: dict | None = None) -> list[str]:
    del cur
    return [_RETIRED]


if __name__ == "__main__":
    snap = snapshot()
    print(json.dumps(snap, indent=2))
    for line in maybe_alert(snap):
        print(line)
