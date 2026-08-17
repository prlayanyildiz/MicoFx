"""MT5 stamps are naive broker wall clock, not this machine's local time.

Bar, tick and deal ``time`` fields look like Unix epochs. ``gmtime`` (and
``sessions.server_datetime``) recover the broker's clock. ``fromtimestamp``
without ``tz=UTC``, or ``time.localtime``, add Windows' offset on top —
+3h here, and a different number after European DST. This project has
done that three times. A comment is not enough; the tree is scanned.
"""
from __future__ import annotations

import ast
import calendar
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import sessions

MICOFX = Path(__file__).resolve().parents[1] / "micofx"

# Machine-clock localtime only. An MT5 bar/tick/deal stamp does not belong
# here — that is what the scan below is for.
_ALLOWED_LOCALTIME = {
    "time.localtime()",
    "time.localtime(now)",
    "time.localtime(when)",
    "time.localtime(ts)",
    "time.localtime(entry['ts'])",
    'time.localtime(entry["ts"])',
    "time.localtime(since_cfg)",
}

# Monday 2026-08-17 15:00 as a naive broker epoch (the number backtest stores).
BROKER_1500 = calendar.timegm((2026, 8, 17, 15, 0, 0, 0, 0, 0))


def test_server_datetime_is_naive_broker_wall_clock():
    dt = sessions.server_datetime(BROKER_1500)
    assert dt.tzinfo is None
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second) == (
        2026, 8, 17, 15, 0, 0,
    )
    day, minute = sessions.server_clock(BROKER_1500)
    assert dt.isoweekday() == day
    assert dt.hour * 60 + dt.minute == minute


def test_server_datetime_is_not_this_machines_fromtimestamp():
    """On UTC+3, naive fromtimestamp(15:00 broker) reads 18:00. Helper must not."""
    naive = datetime.fromtimestamp(BROKER_1500)
    dt = sessions.server_datetime(BROKER_1500)
    utc = datetime.fromtimestamp(BROKER_1500, tz=UTC).replace(tzinfo=None)
    assert dt == utc
    if naive.hour != 15:
        assert dt != naive


def _call_path(node: ast.Call) -> str:
    parts: list[str] = []
    n: ast.AST = node.func
    while isinstance(n, ast.Attribute):
        parts.append(n.attr)
        n = n.value
    if isinstance(n, ast.Name):
        parts.append(n.id)
    return ".".join(reversed(parts))


def _tz_is_utc(node: ast.AST) -> bool:
    if isinstance(node, ast.Name) and node.id == "UTC":
        return True
    if isinstance(node, ast.Attribute) and node.attr in {"utc", "UTC"}:
        return True
    return False


def test_micofx_does_not_decode_mt5_stamps_with_localtime_or_naive_fromtimestamp():
    hits: list[str] = []
    for path in sorted(MICOFX.rglob("*.py")):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        rel = path.relative_to(MICOFX.parent).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_path(node)
            if name.endswith("fromtimestamp"):
                tz = next((kw.value for kw in node.keywords if kw.arg == "tz"), None)
                if tz is None or not _tz_is_utc(tz):
                    hits.append(f"{rel}:{node.lineno}: {ast.unparse(node)}")
            elif name.endswith("localtime"):
                rendered = ast.unparse(node)
                if rendered not in _ALLOWED_LOCALTIME:
                    hits.append(f"{rel}:{node.lineno}: {rendered}")
    assert hits == [], (
        "MT5 bar/tick/deal times are naive broker epochs; decode with "
        "sessions.server_datetime / gmtime, not fromtimestamp or localtime:\n"
        + "\n".join(hits)
    )
