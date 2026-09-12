"""Poll /api/state until optimizer is idle."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.panel_session import opener  # noqa: E402
from micofx.paths import PANEL  # noqa: E402


def main() -> int:
    deadline = time.time() + 7200
    last = ""
    while time.time() < deadline:
        try:
            op = opener()
            st = json.loads(op.open(PANEL + "/api/state").read())
            opt = st.get("opt") or {}
            line = (
                f"state={opt.get('state')} busy={opt.get('busy')} "
                f"cur={opt.get('current')} done={opt.get('done')}/{opt.get('total')} "
                f"combo={opt.get('combo_done')}/{opt.get('combo_total')} "
                f"best={opt.get('best_score')}"
            )
            if line != last:
                print(line, flush=True)
                last = line
            busy = bool(opt.get("busy"))
            state = str(opt.get("state") or "")
            if (not busy) and state in ("idle", "done", "error", ""):
                blob = {k: opt.get(k) for k in (
                    "state", "error", "results", "best_score", "finished_at")}
                print("FINISHED", json.dumps(blob, ensure_ascii=False)[:3000],
                      flush=True)
                return 0
        except Exception as exc:  # noqa: BLE001 - poll tool
            print("poll_err", exc, flush=True)
        time.sleep(20)
    print("TIMEOUT still busy", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
