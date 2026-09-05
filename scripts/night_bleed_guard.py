"""Night-bleed guard — detect sole overnight loser dominating 24h PnL.

Report-only by default. Optional auto option-A (temp disable until EU) only when
``.bridge/AUTO_NIGHT_BLEED_A`` is armed (Claude/Cursor joint OK). Does not touch
SL/family/msa. Reuses ``xau_temp_reenable`` flag naming for XAUUSD.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
STATE_PATH = ROOT / ".bridge" / "NIGHT_BLEED_STATE.json"
ARM_PATH = ROOT / ".bridge" / "AUTO_NIGHT_BLEED_A"
# Claude 06:35 veto: even if ARM_PATH appears, refuse unless this second flag.
FORCE_PATH = ROOT / ".bridge" / "AUTO_NIGHT_BLEED_A_FORCE"
XAU_FLAG = ROOT / ".bridge" / "XAU_TEMP_DISABLE_UNTIL_EU"

# Fire when a name's loss streak is eating the book (net share can be diluted
# by one earlier winner — Claude 05:58 XAU had +3R then 7 losers).
MIN_STREAK_R = -5.0
MIN_STREAK = 6  # matches xau_streak_watch REVIEW_AT
LOSS_SHARE = 0.50
NET_SHARE = 0.70  # classic net-R dominance
WINDOW_H = 24
NIGHT_SOLE_H = 12  # sole trader in this window also qualifies


def _load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _r(row: dict[str, Any]) -> float:
    try:
        return float(row.get("r_realised") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _exit_ts(row: dict[str, Any]) -> float | None:
    for key in ("exit_time", "fill_time"):
        v = row.get(key)
        if v is None or v == "":
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def streak_r_sum(
    rows: list[dict[str, Any]],
    *,
    symbol: str,
) -> tuple[int, float]:
    """Absolute consecutive non-winner count + sum R (newest-last)."""
    mine = [r for r in rows if str(r.get("symbol") or "") == symbol]
    streak = 0
    total = 0.0
    for row in reversed(mine):
        rr = _r(row)
        if rr > 0:
            break
        streak += 1
        total += rr
    return streak, total


def snapshot(
    rows: list[dict[str, Any]],
    *,
    now_ts: float | None = None,
    window_h: int = WINDOW_H,
    streaks: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Aggregate last ``window_h`` closes; flag dominant bleed name."""
    now = float(now_ts if now_ts is not None else time.time())
    cutoff = now - max(1, int(window_h)) * 3600
    sole_cut = now - max(1, int(NIGHT_SOLE_H)) * 3600
    by: dict[str, dict[str, Any]] = {}
    recent_syms: set[str] = set()
    for row in rows:
        ts = _exit_ts(row)
        if ts is None or ts < cutoff:
            continue
        sym = str(row.get("symbol") or "")
        if not sym:
            continue
        if ts >= sole_cut:
            recent_syms.add(sym)
        bucket = by.setdefault(
            sym, {"n": 0, "r": 0.0, "profit": 0.0, "loss_r": 0.0})
        bucket["n"] += 1
        rr = _r(row)
        bucket["r"] += rr
        if rr < 0:
            bucket["loss_r"] += rr
        try:
            bucket["profit"] += float(row.get("profit") or 0.0)
        except (TypeError, ValueError):
            pass
    total_r = sum(float(v["r"]) for v in by.values())
    total_loss = sum(float(v["loss_r"]) for v in by.values())
    # Dominant by loss-only R (ignores earlier winners that dilute net share).
    dominant = ""
    dom_loss = 0.0
    for sym, v in by.items():
        lr = float(v["loss_r"])
        if lr < dom_loss:
            dom_loss = lr
            dominant = sym
    loss_share = (
        (abs(dom_loss) / abs(total_loss)) if total_loss < 0 and dominant else 0.0
    )
    dom_net = float(by.get(dominant, {}).get("r") or 0.0) if dominant else 0.0
    net_share = (
        (abs(dom_net) / abs(total_r))
        if total_r < 0 and dominant and dom_net < 0 else 0.0
    )
    if streaks and dominant in streaks:
        streak = int(streaks[dominant])
        _, streak_r = streak_r_sum(rows, symbol=dominant)
    elif dominant:
        streak, streak_r = streak_r_sum(rows, symbol=dominant)
    else:
        streak, streak_r = 0, 0.0
    sole = len(recent_syms) == 1 and dominant in recent_syms
    fire = bool(dominant) and streak >= MIN_STREAK and streak_r <= MIN_STREAK_R and (
        loss_share >= LOSS_SHARE
        or net_share >= NET_SHARE
        or sole
    )
    return {
        "window_h": int(window_h),
        "total_r": round(total_r, 3),
        "total_loss_r": round(total_loss, 3),
        "by_symbol": {
            s: {
                "n": v["n"],
                "r": round(float(v["r"]), 3),
                "loss_r": round(float(v["loss_r"]), 3),
                "profit": round(float(v["profit"]), 2),
            }
            for s, v in sorted(by.items())
        },
        "dominant": dominant,
        "dominant_r": round(dom_net, 3),
        "dominant_loss_r": round(dom_loss, 3),
        "dominant_share": round(net_share, 3),
        "loss_share": round(loss_share, 3),
        "dominant_streak": streak,
        "streak_r": round(streak_r, 3),
        "sole_recent": sole,
        "fire": fire,
        "armed_auto_a": ARM_PATH.is_file(),
    }


def maybe_alert(
    snap: dict[str, Any],
    *,
    state_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    """One-shot wake while ``fire`` stays true for the same dominant."""
    if not snap.get("fire"):
        return []
    path = state_path if state_path is not None else STATE_PATH
    state = _load_state(path)
    key = f"{snap.get('dominant')}:{snap.get('dominant_streak')}"
    if state.get("alerted_key") == key:
        return []
    wake = wake_path if wake_path is not None else (ROOT / ".bridge" / "WAKE.txt")
    inbox = cursor_inbox if cursor_inbox is not None else (
        ROOT / "cursor" / "FOR_CLAUDE.md")
    lines: list[str] = []
    try:
        wake.parent.mkdir(parents=True, exist_ok=True)
        wake.write_text("WAKE\n", encoding="utf-8")
        lines.append(f"wake -> {wake}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    by = snap.get("by_symbol") or {}
    table = "\n".join(
        f"  {s}: n={v['n']} R={v['r']} $={v['profit']}"
        for s, v in by.items()
    )
    arm = (
        "FORCE-ARMED"
        if snap.get("armed_auto_a") and FORCE_PATH.is_file()
        else "VETOED/report-only (Claude 06:35)"
    )
    body = (
        f"# Cursor -> Claude -- {ts} -- NIGHT BLEED: {snap.get('dominant')} "
        f"loss_share={snap.get('loss_share'):.0%} streak={snap.get('dominant_streak')} "
        f"streak_r={snap.get('streak_r')} (book {snap.get('total_r')}R).\n\n"
        f"Auto-A {arm}. Options: A temp-disable→EU / B size cut / C wait.\n"
        f"```\n{table}\n```\n\n"
        "Config/SL dokunma. MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.parent.mkdir(parents=True, exist_ok=True)
        inbox.write_text(
            body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"night_bleed -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    state["alerted_key"] = key
    state["alerted_at"] = datetime.now().isoformat(timespec="seconds")
    state["last_snap"] = {
        k: snap.get(k) for k in (
            "dominant", "total_r", "dominant_share", "dominant_streak", "fire")
    }
    _save_state(path, state)
    return lines


def maybe_apply_a(
    snap: dict[str, Any],
    panel: str = PANEL,
) -> tuple[bool, str]:
    """Disable path — Claude 06:35 veto unless ARM+FORCE both present."""
    if not ARM_PATH.is_file():
        return True, "auto-A unarmed"
    if not FORCE_PATH.is_file():
        return True, "auto-A Claude-vetoed (need AUTO_NIGHT_BLEED_A_FORCE)"
    if not snap.get("fire"):
        return True, "no night-bleed fire"
    sym = str(snap.get("dominant") or "")
    if sym != "XAUUSD":
        return True, f"auto-A only wired for XAUUSD (got {sym})"
    if XAU_FLAG.is_file():
        return True, "XAU already temp-disabled"
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    payload = json.dumps({"enabled": False}).encode()
    req = urllib.request.Request(
        panel + f"/api/symbols/{sym}",
        data=payload,
        headers={"Origin": panel, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with op.open(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except Exception as exc:
        return False, f"auto-A disable fail: {exc}"
    XAU_FLAG.parent.mkdir(parents=True, exist_ok=True)
    XAU_FLAG.write_text(
        f"auto-A {datetime.now().isoformat(timespec='seconds')} "
        f"total_r={snap.get('total_r')} streak={snap.get('dominant_streak')}\n",
        encoding="utf-8",
    )
    return True, f"auto-A: {sym} enabled=false + flag ({body.get('ok', True)})"


def main() -> int:
    from scripts.xau_streak_watch import (  # noqa: PLC0415
        consecutive_non_winners,
        fetch_autopsy_rows,
    )

    p = argparse.ArgumentParser()
    p.add_argument("--panel", default=PANEL)
    p.add_argument("--apply", action="store_true",
                   help="Honor AUTO_NIGHT_BLEED_A if armed")
    p.add_argument("--alert", action="store_true")
    args = p.parse_args()
    rows = fetch_autopsy_rows(args.panel)
    streaks = {
        s: consecutive_non_winners(rows, symbol=s)["streak"]
        for s in {str(r.get("symbol") or "") for r in rows if r.get("symbol")}
    }
    snap = snapshot(rows, streaks=streaks)
    print(json.dumps(snap, indent=2), flush=True)
    if args.alert:
        for n in maybe_alert(snap):
            print(n, flush=True)
    if args.apply:
        ok, msg = maybe_apply_a(snap, args.panel)
        print(msg, flush=True)
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
