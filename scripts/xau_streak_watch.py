"""XAU consecutive non-winner streak — report-only (Claude 04:35).

Counts autopsy ``r_realised <= 0`` from the last winner. Never lands SL.
Wakes Claude at review (>=5) and escalate (>=8 = Claude's "5+ more" from
the 3-trade flag). Dedups by alert level so the income loop does not spam.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PANEL = "http://127.0.0.1:8900"
STATE_PATH = ROOT / ".bridge" / "XAU_STREAK_STATE.json"
BOOK_STATE_PATH = ROOT / ".bridge" / "BOOK_STREAK_STATE.json"
BASELINE_PATH = ROOT / ".bridge" / "POST_RESTART_BASELINE.json"
DEFAULT_SYMBOL = "XAUUSD"

# Absolute consecutive non-winners from last winner.
WATCH_AT = 3
REVIEW_AT = 5   # hybrid SL scan ready for human/Claude review — no auto land
ESCALATE_AT = 8  # Claude 04:35: 3 flag + 5 more
EXP_WINDOW = 10
EXP_ALERT_R = -0.30  # Claude 04:35: live exp < -0.30R / 10 trades


def is_winner(row: dict[str, Any]) -> bool:
    try:
        return float(row.get("r_realised") or 0.0) > 0.0
    except (TypeError, ValueError):
        return False


def consecutive_non_winners(
    rows: list[dict[str, Any]],
    *,
    symbol: str = DEFAULT_SYMBOL,
) -> dict[str, Any]:
    """Newest-last rows; streak walks backward from the end."""
    mine = [r for r in rows if str(r.get("symbol") or "") == symbol]
    streak = 0
    tail: list[dict[str, Any]] = []
    for row in reversed(mine):
        if is_winner(row):
            break
        streak += 1
        tail.append({
            "exit_time": row.get("exit_time"),
            "r_realised": row.get("r_realised"),
            "exit_reason": row.get("exit_reason"),
            "mfe_r": row.get("mfe_r"),
            "profit": row.get("profit"),
            "ticket": row.get("ticket"),
        })
    level = "ok"
    if streak >= ESCALATE_AT:
        level = "escalate"
    elif streak >= REVIEW_AT:
        level = "review"
    elif streak >= WATCH_AT:
        level = "watch"
    exp = recent_expectancy(rows, symbol=symbol, n=EXP_WINDOW)
    return {
        "symbol": symbol,
        "streak": streak,
        "level": level,
        "n_closed": len(mine),
        "tail": list(reversed(tail)),
        "review_at": REVIEW_AT,
        "escalate_at": ESCALATE_AT,
        "expectancy": exp,
    }


def recent_expectancy(
    rows: list[dict[str, Any]],
    *,
    symbol: str = DEFAULT_SYMBOL,
    n: int = EXP_WINDOW,
) -> dict[str, Any]:
    """Mean ``r_realised`` over the last ``n`` closes for ``symbol``."""
    mine = [r for r in rows if str(r.get("symbol") or "") == symbol]
    tail = mine[-max(1, int(n)):]
    vals: list[float] = []
    for row in tail:
        try:
            vals.append(float(row.get("r_realised") or 0.0))
        except (TypeError, ValueError):
            continue
    exp = (sum(vals) / len(vals)) if vals else 0.0
    return {
        "n": len(vals),
        "window": int(n),
        "expectancy_r": round(exp, 4),
        "alert": bool(vals) and len(vals) >= min(5, int(n)) and exp < EXP_ALERT_R,
        "threshold_r": EXP_ALERT_R,
    }


def fetch_autopsy_rows(panel: str = PANEL) -> list[dict[str, Any]]:
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/analysis/trade-autopsies",
                headers={"Origin": panel},
            )
        ).read().decode()
    )
    return list(body.get("rows") or [])


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


def alerts_suppressed_by_baseline(
    autopsy_n: int,
    *,
    baseline_path: Path | None = None,
) -> tuple[bool, str]:
    """Hold streak/exp wakes until N new closes after a mid-trade re-adopt.

    Claude 05:20: pre-restart book-exp is invalid on the old motor; collect
    20–30 new trades before treating alerts as a config signal.
    """
    path = baseline_path if baseline_path is not None else BASELINE_PATH
    data = _load_state(path)
    if not data:
        return False, ""
    try:
        stamped = int(data.get("autopsy_n_at_stamp") or 0)
        target = int(data.get("target_new_trades") or 25)
    except (TypeError, ValueError):
        return False, ""
    if stamped <= 0 or target <= 0:
        return False, ""
    new = max(0, int(autopsy_n) - stamped)
    if new < target:
        return True, f"post-restart baseline: {new}/{target} new trades"
    return False, ""


def baseline_status(
    autopsy_n: int,
    *,
    baseline_path: Path | None = None,
) -> dict[str, Any]:
    """Progress toward Claude's post-restart sample size."""
    path = baseline_path if baseline_path is not None else BASELINE_PATH
    data = _load_state(path)
    if not data:
        return {"armed": False}
    try:
        stamped = int(data.get("autopsy_n_at_stamp") or 0)
        target = int(data.get("target_new_trades") or 25)
    except (TypeError, ValueError):
        return {"armed": False}
    new = max(0, int(autopsy_n) - stamped) if stamped > 0 else 0
    suppressed, note = alerts_suppressed_by_baseline(
        autopsy_n, baseline_path=path)
    return {
        "armed": True,
        "autopsy_n": int(autopsy_n),
        "stamped_n": stamped,
        "new_trades": new,
        "target": target,
        "suppressed": suppressed,
        "note": note or f"baseline ready {new}/{target}",
        "restart_at": data.get("restart_at"),
    }


def maybe_alert_first_new_close(
    autopsy_n: int,
    *,
    baseline_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    """One-shot wake on the first post-restart close (evidence clock starts)."""
    status = baseline_status(autopsy_n, baseline_path=baseline_path)
    if not status.get("armed"):
        return []
    if int(status.get("new_trades") or 0) < 1:
        return []
    path = baseline_path if baseline_path is not None else BASELINE_PATH
    data = _load_state(path)
    if data.get("first_close_alerted"):
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
    body = (
        f"# Cursor -> Claude -- {ts} -- FIRST POST-RESTART CLOSE "
        f"({status['new_trades']}/{status['target']}; autopsy {status['autopsy_n']}).\n\n"
        "Kanit saati basladi. Config/unfreeze YOK — 25/25 + US30 fill + XAU post-EU.\n"
        "MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.write_text(body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"first close -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    data["first_close_alerted"] = True
    data["first_close_alerted_at"] = datetime.now().isoformat(timespec="seconds")
    _save_state(path, data)
    print("AGENT_LOOP_WAKE_first_post_restart_close", flush=True)
    return lines


def maybe_alert_baseline_ready(
    autopsy_n: int,
    *,
    baseline_path: Path | None = None,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
) -> list[str]:
    """One-shot wake when 25 new closes land (Claude TEMIZ WAIT exit)."""
    status = baseline_status(autopsy_n, baseline_path=baseline_path)
    if not status.get("armed") or status.get("suppressed"):
        return []
    path = baseline_path if baseline_path is not None else BASELINE_PATH
    data = _load_state(path)
    if data.get("ready_alerted"):
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
    body = (
        f"# Cursor -> Claude -- {ts} -- BASELINE READY "
        f"{status['new_trades']}/{status['target']} new closes post-restart.\n\n"
        "Pre-restart book-exp artık geçersiz sayılmamalı. Config review açılabilir "
        "(hâlâ FROZEN — unfreeze manuel+senin review).\n"
        "US30 fill oranı / XAU 0.7 live / book-exp taze örnek.\n\n"
        "MICO MOLA yok.\n"
    )
    try:
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.write_text(body + ("\n---\n\n" + prev if prev else ""), encoding="utf-8")
        lines.append(f"baseline ready -> {inbox}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    data["ready_alerted"] = True
    data["ready_alerted_at"] = datetime.now().isoformat(timespec="seconds")
    _save_state(path, data)
    return lines


def should_alert(report: dict[str, Any], state: dict[str, Any]) -> bool:
    level = str(report.get("level") or "ok")
    if level in ("review", "escalate"):
        if str(state.get("alerted_level") or "") != level:
            return True
    exp = report.get("expectancy") or {}
    if exp.get("alert") and not state.get("exp_alerted"):
        return True
    return False


def alert_streak(
    report: dict[str, Any],
    *,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
    state_path: Path | None = None,
    force: bool = False,
    run_hybrid_review: bool = True,
) -> list[str]:
    """Wake Claude when streak hits review/escalate. Report-only — no land."""
    state_p = state_path if state_path is not None else STATE_PATH
    state = _load_state(state_p)
    if not force and not should_alert(report, state):
        return []
    level = str(report.get("level") or "ok")
    exp = report.get("expectancy") or {}
    exp_fire = bool(exp.get("alert")) and not state.get("exp_alerted")
    streak_fire = level in ("review", "escalate") and (
        force or str(state.get("alerted_level") or "") != level
    )
    if not force and not streak_fire and not exp_fire:
        return []
    lines: list[str] = []
    streak = int(report.get("streak") or 0)
    sym = str(report.get("symbol") or DEFAULT_SYMBOL)
    wake = wake_path if wake_path is not None else (ROOT / ".bridge" / "WAKE.txt")
    try:
        wake.parent.mkdir(parents=True, exist_ok=True)
        wake.write_text("WAKE\n", encoding="utf-8")
        lines.append(f"wake -> {wake}")
    except OSError as exc:
        lines.append(f"wake fail: {exc}")
    inbox = cursor_inbox if cursor_inbox is not None else (
        ROOT / "cursor" / "FOR_CLAUDE.md")
    review_md = ""
    if run_hybrid_review and level == "escalate":
        try:
            from scripts.xau_hybrid_sl_review import (
                load_symbol_row,
                markdown_table,
                review_sl,
            )
            row = load_symbol_row(sym)
            hrep = review_sl(row, autopsy_rows=fetch_autopsy_rows())
            review_md = "\n\n## Hybrid SL gate table\n\n" + markdown_table(hrep)
            lines.append("hybrid_sl_review attached")
        except Exception as exc:
            review_md = f"\n\n(hybrid SL review fail: {exc})"
            lines.append(f"hybrid review fail: {exc}")
    try:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        tail_lines = []
        for t in (report.get("tail") or [])[-8:]:
            try:
                r = float(t.get("r_realised") or 0.0)
            except (TypeError, ValueError):
                r = 0.0
            tail_lines.append(
                f"- ticket {t.get('ticket')} r={r:+.3f} "
                f"{t.get('exit_reason')} mfe={t.get('mfe_r')}"
            )
        bits = []
        if streak_fire:
            bits.append(f"STREAK {level.upper()}: {streak} ardisik non-winner")
        if exp_fire:
            bits.append(
                f"EXP ALERT: last{exp.get('n')} "
                f"exp={exp.get('expectancy_r')}<{exp.get('threshold_r')}"
            )
        title = f"{sym} " + " + ".join(bits or [f"streak={streak}"])
        exp_line = (
            f"Last-{exp.get('n')}/{exp.get('window')} exp="
            f"{exp.get('expectancy_r')}R "
            f"(alert<{exp.get('threshold_r')})."
        )
        block = (
            f"# Cursor -> Claude -- {ts} -- {title}\n\n"
            f"Claude 04:35 XAU izleme. Absolute streak (son winner'dan) "
            f"**{streak}** (review>={REVIEW_AT}, escalate>={ESCALATE_AT}). "
            f"{exp_line}\n\n"
            + ("\n".join(tail_lines) if tail_lines else "(tail yok)")
            + "\n\n"
            "**Land yok.** Exec FROZEN. Hybrid SL sadece escalate + premature "
            "+ upgrade_robust + manuel Claude review.\n"
            + review_md
            + "\n\nMICO MOLA yok.\n"
        )
        prev = inbox.read_text(encoding="utf-8") if inbox.is_file() else ""
        inbox.write_text(block + "\n---\n\n" + prev, encoding="utf-8")
        lines.append(f"inbox -> {inbox.name}")
    except OSError as exc:
        lines.append(f"inbox fail: {exc}")
    if streak_fire:
        state["alerted_level"] = level
    if exp_fire:
        state["exp_alerted"] = True
    state["streak"] = streak
    state["ts"] = datetime.now().isoformat(timespec="seconds")
    _save_state(state_p, state)
    lines.append(f"{sym} streak={streak} level={level}")
    return lines


def fetch_enabled_symbols(panel: str = PANEL) -> list[str]:
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.open(panel + "/")
    body = json.loads(
        op.open(
            urllib.request.Request(
                panel + "/api/symbols", headers={"Origin": panel})
        ).read().decode()
    )
    out: list[str] = []
    for row in body.get("symbols") or []:
        if not isinstance(row, dict) or not row.get("enabled"):
            continue
        sym = str(row.get("symbol") or "")
        if sym:
            out.append(sym)
    return out


def scan_book(
    rows: list[dict[str, Any]],
    symbols: list[str],
) -> list[dict[str, Any]]:
    return [consecutive_non_winners(rows, symbol=s) for s in symbols]


def alert_book(
    reports: list[dict[str, Any]],
    *,
    wake_path: Path | None = None,
    cursor_inbox: Path | None = None,
    state_path: Path | None = None,
    baseline_path: Path | None = None,
    autopsy_n: int | None = None,
) -> list[str]:
    """Alert per-symbol review/escalate; XAU escalate still attaches hybrid table."""
    if autopsy_n is not None:
        suppressed, why = alerts_suppressed_by_baseline(
            int(autopsy_n), baseline_path=baseline_path)
        if suppressed:
            return [why]
    state_p = state_path if state_path is not None else BOOK_STATE_PATH
    book_state = _load_state(state_p)
    by_sym = (
        book_state.get("symbols")
        if isinstance(book_state.get("symbols"), dict) else {}
    )
    notes: list[str] = []
    for report in reports:
        sym = str(report.get("symbol") or "")
        if not sym:
            continue
        if sym == DEFAULT_SYMBOL:
            notes.extend(alert_streak(
                report,
                wake_path=wake_path,
                cursor_inbox=cursor_inbox,
                state_path=STATE_PATH,
                run_hybrid_review=True,
            ))
            continue
        sub = by_sym.get(sym) if isinstance(by_sym.get(sym), dict) else {}
        fired = _alert_symbol(
            report, sub,
            wake_path=wake_path,
            cursor_inbox=cursor_inbox,
        )
        by_sym[sym] = sub
        notes.extend(fired)
    book_state["symbols"] = by_sym
    book_state["ts"] = datetime.now().isoformat(timespec="seconds")
    _save_state(state_p, book_state)
    return notes


def _alert_symbol(
    report: dict[str, Any],
    state: dict[str, Any],
    *,
    wake_path: Path | None,
    cursor_inbox: Path | None,
) -> list[str]:
    """Non-XAU streak alert using an in-memory per-symbol state dict."""
    if not should_alert(report, state):
        return []
    level = str(report.get("level") or "ok")
    exp = report.get("expectancy") or {}
    exp_fire = bool(exp.get("alert")) and not state.get("exp_alerted")
    streak_fire = level in ("review", "escalate") and (
        str(state.get("alerted_level") or "") != level
    )
    if not streak_fire and not exp_fire:
        return []
    # Reuse alert_streak with a temp state file under .bridge.
    tmp = ROOT / ".bridge" / f"_streak_tmp_{report.get('symbol')}.json"
    _save_state(tmp, state)
    try:
        lines = alert_streak(
            report,
            wake_path=wake_path,
            cursor_inbox=cursor_inbox,
            state_path=tmp,
            run_hybrid_review=False,
        )
        state.clear()
        state.update(_load_state(tmp))
        return lines
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def run_book(
    panel: str = PANEL,
    *,
    alert: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows = fetch_autopsy_rows(panel)
    symbols = fetch_enabled_symbols(panel)
    # XAU may be disabled while SL land pending — still watch it.
    if DEFAULT_SYMBOL not in symbols:
        symbols = list(symbols) + [DEFAULT_SYMBOL]
    reports = scan_book(rows, symbols)
    notes: list[str] = []
    if alert:
        notes = alert_book(reports, autopsy_n=len(rows))
    return reports, notes


def run(
    panel: str = PANEL,
    *,
    alert: bool = False,
    symbol: str = DEFAULT_SYMBOL,
) -> tuple[dict[str, Any], list[str]]:
    rows = fetch_autopsy_rows(panel)
    report = consecutive_non_winners(rows, symbol=symbol)
    notes: list[str] = []
    if alert:
        suppressed, why = alerts_suppressed_by_baseline(len(rows))
        if suppressed:
            notes = [why]
        else:
            notes = alert_streak(report)
    return report, notes


def main() -> int:
    p = argparse.ArgumentParser(description="XAU non-winner streak watch")
    p.add_argument("--panel", default=PANEL)
    p.add_argument("--symbol", default=DEFAULT_SYMBOL)
    p.add_argument(
        "--alert", action="store_true",
        help="Wake bridge at review/escalate (deduped)")
    p.add_argument(
        "--book", action="store_true",
        help="Scan all enabled symbols (plus XAU even if disabled)")
    args = p.parse_args()
    if args.book:
        reports, notes = run_book(args.panel, alert=args.alert)
        for r in reports:
            exp = r.get("expectancy") or {}
            print(
                f"{r['symbol']} streak={r['streak']} level={r['level']} "
                f"exp={exp.get('expectancy_r')}",
                flush=True,
            )
        for n in notes:
            print(n, flush=True)
        worst = max(
            (r.get("level") or "ok" for r in reports),
            key=lambda lv: {"ok": 0, "watch": 1, "review": 2, "escalate": 3}.get(lv, 0),
            default="ok",
        )
        return {"escalate": 2, "review": 1}.get(worst, 0)
    report, notes = run(args.panel, alert=args.alert, symbol=args.symbol)
    print(
        f"{report['symbol']} streak={report['streak']} "
        f"level={report['level']} closed={report['n_closed']}",
        flush=True,
    )
    for n in notes:
        print(n, flush=True)
    if report["level"] == "escalate":
        return 2
    if report["level"] == "review":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
