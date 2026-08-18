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

REPO = Path(__file__).resolve().parents[1]
MICOFX = REPO / "micofx"

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

# Naive fromtimestamp of a real Unix instant (time.time() / log wall), printed
# as this machine's clock. Not an MT5 bar/tick/deal stamp.
_ALLOWED_NAIVE_FROMTIMESTAMP = {
    "datetime.fromtimestamp(since)",
    "datetime.fromtimestamp(ep)",
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


def _iter_scan_roots() -> list[Path]:
    """Product plus bridge scripts. Missing dirs skip — gitignore on other machines."""
    roots = [MICOFX]
    for name in ("claude", "cursor"):
        path = REPO / name
        if path.is_dir():
            roots.append(path)
    return roots


def _fromtimestamp_tz(node: ast.Call) -> ast.AST | None:
    for kw in node.keywords:
        if kw.arg == "tz":
            return kw.value
    if len(node.args) >= 2:
        return node.args[1]
    return None


def _unwrap_int_float(node: ast.AST) -> ast.AST:
    while isinstance(node, ast.Call):
        name = _call_path(node)
        if name in {"int", "float"} and node.args:
            node = node.args[0]
            continue
        break
    return node


def _is_datetime_ctor(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    return _call_path(node) in {"datetime", "datetime.datetime"}


def _ctor_tzinfo_is_utc(node: ast.Call) -> bool:
    for kw in node.keywords:
        if kw.arg == "tzinfo" and _tz_is_utc(kw.value):
            return True
    return False


def _utc_datetime_names(tree: ast.AST) -> set[str]:
    """Names bound to datetime(..., tzinfo=UTC) — the 18.08 START_UTC shape."""
    bound: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        val = _unwrap_int_float(node.value)
        if _is_datetime_ctor(val) and _ctor_tzinfo_is_utc(val):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound.add(target.id)
    return bound


def _is_utc_replace(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if not _call_path(node).endswith("replace"):
        return False
    for kw in node.keywords:
        if kw.arg == "tzinfo" and _tz_is_utc(kw.value):
            return True
    return False


def _is_utc_datetime_timestamp(node: ast.Call, bound: set[str]) -> bool:
    """datetime(..., tzinfo=UTC).timestamp() used as if it were an MT5 epoch."""
    if not _call_path(node).endswith("timestamp"):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    recv = _unwrap_int_float(func.value)
    if _is_datetime_ctor(recv) and _ctor_tzinfo_is_utc(recv):
        return True
    if _is_utc_replace(recv):
        return True
    if isinstance(recv, ast.Name) and recv.id in bound:
        return True
    return False


def _scan_source(src: str, rel: str, *, timestamps: bool = False) -> list[str]:
    tree = ast.parse(src)
    bound = _utc_datetime_names(tree) if timestamps else set()
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_path(node)
        rendered = ast.unparse(node)
        if name.endswith("fromtimestamp"):
            tz = _fromtimestamp_tz(node)
            if tz is None or not _tz_is_utc(tz):
                if rendered not in _ALLOWED_NAIVE_FROMTIMESTAMP:
                    hits.append(f"{rel}:{node.lineno}: {rendered}")
        elif name.endswith("localtime"):
            if rendered not in _ALLOWED_LOCALTIME:
                hits.append(f"{rel}:{node.lineno}: {rendered}")
        elif timestamps and _is_utc_datetime_timestamp(node, bound):
            hits.append(f"{rel}:{node.lineno}: {rendered}")
    return hits


def _scan_tree(root: Path, *, timestamps: bool = False) -> list[str]:
    hits: list[str] = []
    for path in sorted(root.rglob("*.py")):
        src = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO).as_posix()
        hits.extend(_scan_source(src, rel, timestamps=timestamps))
    return hits


def test_broker_epoch_is_the_inverse_of_server_datetime():
    assert sessions.broker_epoch(2026, 8, 17, 15) == BROKER_1500
    dt = sessions.server_datetime(sessions.broker_epoch(2025, 11, 1, 2, 0))
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (2025, 11, 1, 2, 0)


def test_sessions_import_has_no_mt5_barrier():
    """cursor/ already puts ROOT on path. claude/_bt2_select.py does not import
    micofx today; it can, without a new timeutil facade. sessions has no MT5 import.
    """
    src = Path(sessions.__file__).read_text(encoding="utf-8")
    assert "import MetaTrader5" not in src
    assert "import mt5" not in src
    assert callable(sessions.server_datetime)
    assert callable(sessions.broker_epoch)


def test_scan_roots_include_bridge_dirs_when_present():
    names = {p.name for p in _iter_scan_roots()}
    assert "micofx" in names
    for name in ("claude", "cursor"):
        if (REPO / name).is_dir():
            assert name in names
        else:
            assert name not in names


def test_micofx_does_not_decode_mt5_stamps_with_localtime_or_naive_fromtimestamp():
    hits: list[str] = []
    for root in _iter_scan_roots():
        hits.extend(_scan_tree(root, timestamps=True))
    assert hits == [], (
        "MT5 bar/tick/deal times are naive broker epochs; decode with "
        "sessions.server_datetime / gmtime / broker_epoch, not "
        "fromtimestamp, localtime, or datetime(...UTC).timestamp():\n"
        + "\n".join(hits)
    )


_EXAMPLE_18AUG_CUT = """\
from datetime import datetime, timezone
CUT = datetime(2026, 8, 16, 15, 13, tzinfo=timezone.utc).timestamp()
START_UTC = datetime(2026, 8, 16, 18, 34, tzinfo=timezone.utc)
START_UNIX = int(START_UTC.timestamp())
HS = datetime.strptime("2026-05-14 17:55", "%Y-%m-%d %H:%M").replace(
    tzinfo=timezone.utc).timestamp()
"""


def test_utc_datetime_timestamp_as_mt5_epoch_is_caught():
    """Fail-first for the 18.08 cut: real UTC instant compared to MT5 epochs.

    Repair-after numbers were wrong because of this. True post-repair was
    31 trades +$63.94; the bug-loop -$84.46 sat in the wrong bucket.
    """
    hits = _scan_source(_EXAMPLE_18AUG_CUT, "example.py", timestamps=True)
    assert len(hits) >= 3, hits
    assert any("timestamp()" in h for h in hits)
