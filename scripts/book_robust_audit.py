"""Composed-config 6-slice audit — report-only erosion detector (Claude 04.09).

Micro-tune freeze stays; this watches the live book so a last-seg illusion
cannot silently re-land (SpotBrent msa 0.08 pattern).
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.exec_gates import (  # noqa: E402
    ROBUST_PARTS,
    charged_slice_report,
    slice_wins,
)

PANEL = "http://127.0.0.1:8900"

# Fragile probes — floor below the exec ≥4/6 bar (operator-accepted).
FRAGILE_FLOOR: dict[str, int] = {
    "JPN225": 2,
    "SpotBrent": 3,
}
DEFAULT_FLOOR = 4


def floor_for(symbol: str) -> int:
    return int(FRAGILE_FLOOR.get(str(symbol), DEFAULT_FLOOR))


def audit_row(row: dict[str, Any]) -> dict[str, Any]:
    sym = str(row.get("symbol") or "")
    rep = charged_slice_report(row)
    if rep is None:
        return {
            "symbol": sym,
            "ok": False,
            "wins": None,
            "parts": ROBUST_PARTS,
            "floor": floor_for(sym),
            "sum_r": None,
            "nets": None,
            "note": "slice yok",
        }
    wins = int(rep.get("wins_valid") if rep.get("wins_valid") is not None
               else slice_wins(rep["nets"]))
    nets = list(rep["nets"])
    floor = floor_for(sym)
    valid_n = int(rep.get("valid_n") or ROBUST_PARTS)
    # Dual granularity readout only (Claude 16:38) — gate stays 6-slice.
    rep12 = charged_slice_report(row, parts=12)
    wins12 = valid_n12 = None
    if isinstance(rep12, dict):
        wins12 = int(rep12.get("wins_valid") or 0)
        valid_n12 = int(rep12.get("valid_n") or 0)
    return {
        "symbol": sym,
        "ok": wins >= floor and valid_n >= 4,
        "wins": wins,
        "parts": ROBUST_PARTS,
        "valid_n": valid_n,
        "wins_12": wins12,
        "valid_n_12": valid_n12,
        "floor": floor,
        "sum_r": round(sum(nets), 1),
        "nets": [round(n, 1) for n in nets],
        "note": (
            "OK" if wins >= floor and valid_n >= 4
            else f"ALTINDA ({wins}/{valid_n} valid < {floor})"
        ),
    }


def audit_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or not row.get("enabled"):
            continue
        out.append(audit_row(row))
    return out


def markdown_table(results: list[dict[str, Any]]) -> str:
    lines = [
        "| Sembol | wins6 | wins12 | floor | sumR | 6-slice | durum |",
        "|--------|-------|--------|-------|------|---------|-------|",
    ]
    for r in results:
        nets = r.get("nets")
        nets_s = ",".join(str(n) for n in nets) if isinstance(nets, list) else "-"
        wins = r.get("wins")
        sum_r = r.get("sum_r")
        v6 = r.get("valid_n")
        w12 = r.get("wins_12")
        v12 = r.get("valid_n_12")
        w6_s = "-" if wins is None else f"{wins}/{v6 or r['parts']}"
        w12_s = "-" if w12 is None else f"{w12}/{v12 or 12}"
        lines.append(
            f"| {r['symbol']} | "
            f"{w6_s} | {w12_s} | "
            f"{r['floor']} | "
            f"{'-' if sum_r is None else f'{sum_r:+.1f}'} | "
            f"{nets_s} | {r.get('note')} |"
        )
    return "\n".join(lines)


def audit_from_panel(panel: str = PANEL) -> list[dict[str, Any]]:
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/symbols", headers={"Origin": panel})
        ).read().decode()
    )
    return audit_rows(list(body.get("symbols") or []))




EVIDENCE_PATH = ROOT / ".bridge" / "GATE_EVIDENCE.jsonl"


def append_evidence_ledger(
    results: list[dict[str, Any]],
    *,
    path: Path | None = None,
    meta: dict[str, Any] | None = None,
    min_interval_sec: int = 0,
    force: bool = False,
) -> Path | None:
    """Append one frozen-era 6-slice snapshot (unfreeze evidence trail).

    `min_interval_sec` skips quiet identical `ok_all` rows so the baseline
    watch (60s EU poll) does not flood the ledger; breaches / flips always land.
    """
    from datetime import datetime

    out = path if path is not None else EVIDENCE_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    ok_all = all(bool(r.get("ok")) for r in results) if results else False
    if not force and int(min_interval_sec) > 0 and out.is_file():
        try:
            last_line = ""
            with out.open("r", encoding="utf-8") as fh:
                for line in fh:
                    last_line = line
            if last_line.strip():
                prev = json.loads(last_line)
                prev_ts = str(prev.get("ts") or "")
                age = (
                    datetime.now() - datetime.fromisoformat(prev_ts)
                ).total_seconds() if prev_ts else 1e9
                if age < int(min_interval_sec) and bool(prev.get("ok_all")) == ok_all:
                    return None
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            pass
    row = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "ok_all": ok_all,
        "rows": [
            {
                "symbol": r.get("symbol"),
                "ok": r.get("ok"),
                "wins": r.get("wins"),
                "floor": r.get("floor"),
                "sum_r": r.get("sum_r"),
                "note": r.get("note"),
            }
            for r in results
        ],
    }
    if meta:
        row["meta"] = dict(meta)
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return out

def alert_erosion(
    results: list[dict[str, Any]],
    *,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    """Wake Claude bridge when composed floors breach (MONITOR defense)."""
    from datetime import datetime

    bad = [r for r in results if not r.get("ok")]
    if not bad:
        return []
    names = ", ".join(str(r.get("symbol") or "?") for r in bad)
    lines = [f"6-slice EROZYON: {names}"]
    wake = wake_path if wake_path is not None else (ROOT / ".bridge" / "WAKE.txt")
    try:
        wake.parent.mkdir(parents=True, exist_ok=True)
        wake.write_text("WAKE\n", encoding="utf-8")
        lines.append(f"wake -> {wake}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")
    inbox = cursor_inbox if cursor_inbox is not None else (
        ROOT / "cursor" / "FOR_CLAUDE.md")
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        block = (
            f"# Cursor -> Claude -- {ts} -- 6-slice EROZYON ALERT: {names}\n\n"
            f"{markdown_table(bad)}\n\n"
            "MICO MOLA yok — incele / revert.\n"
        )
        prev = ""
        if inbox.is_file():
            prev = inbox.read_text(encoding="utf-8")
        inbox.write_text(block + "\n---\n\n" + prev, encoding="utf-8")
        lines.append(f"inbox -> {inbox.name}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Composed 6-slice book audit")
    parser.add_argument("--panel", default=PANEL)
    parser.add_argument(
        "--alert", action="store_true",
        help="On breach: write .bridge/WAKE.txt + cursor/FOR_CLAUDE.md alert")
    args = parser.parse_args()
    results = audit_from_panel(args.panel)
    append_evidence_ledger(results, meta={"source": "cli"})
    print(markdown_table(results))
    bad = [r for r in results if not r.get("ok")]
    if bad:
        print("EROZYON:", ", ".join(r["symbol"] for r in bad), flush=True)
        if args.alert:
            for line in alert_erosion(results):
                print(line, flush=True)
        return 1
    print("book 6-slice: OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
