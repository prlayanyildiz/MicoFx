"""Find settings that silently switched a mechanism off.

Operator, 11.09: "sistemini engelleyen ne varsa tarayin bulun duzeltin veya
kaldirin". Three of these turned up by hand in two days, each one a stored
value that quietly disabled a whole mechanism while the code around it went on
looking healthy:

  * ``opt_params.min_positive_ratio`` = 0.7. The ratio is
    ``wins / HOLDOUT_ROBUST_PARTS`` over six sub-windows, so it can only take
    seven values and 0.7 is not one of them - it silently meant 5/6 (83%).
    Candidates at 4/6 died against a bar nobody chose.
  * ``opt_params.strategies`` = 5 families while defaults.json shipped 7.
    ``range_fade``, the family that produced the best candidate of the
    evening, was never searched at all.
  * ``supervisor.bad_hour_min_trades`` = 80 against a shipped 6, and
    ``_bad_hours`` buckets PER SYMBOL - two to six trades per hour bucket on
    this book. The bad-hour blocker could not fire at any volume this book
    will ever see, while five hour buckets held 77% of the whole loss.

None of the three raised an error, failed a test, or showed up in a log. They
are only visible by asking "can this number ever be reached by the data it is
applied to?" - so that is what this asks, for every threshold at once.

Two failure directions, both reported:

  DEAD     an evidence bar so high the mechanism can never trigger
  INERT    a protective gate so loose it never binds
  CEILING  a live value above the whole search grid - a search can only
           ever lower it, never restore it
  STRICTER a threshold between rungs that lands most of a step above what
           was typed - what 0.7 did, enforced as 5/6
  ROUNDED  the same shape but a small jump: misleading, not damaging
  OVERRIDE a stored value far from the shipped one; not wrong by itself,
           but every one of the three found by hand looked like this
  THIN     a bar most symbols cannot reach, even if one can

Read-only: the live process owns the database (AGENTS.md), so this opens it
``mode=ro`` and writes nothing. It reports; it does not fix.

    python scripts/dead_gate_scan.py
    python scripts/dead_gate_scan.py --json logs/dead_gates.json
"""
from __future__ import annotations

import argparse
import collections
import json
import sqlite3
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from micofx.backtest import HOLDOUT_ROBUST_PARTS  # noqa: E402
from micofx.paths import DB_PATH, load_defaults  # noqa: E402
from micofx.supervisor import DEFAULTS as SUP_DEFAULTS  # noqa: E402


def _ro_db() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=10.0)


def _setting(db: sqlite3.Connection, key: str) -> Any:
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


class Findings:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, kind: str, where: str, key: str, detail: str,
            stored: Any = None, shipped: Any = None) -> None:
        self.rows.append({"kind": kind, "where": where, "key": key,
                          "detail": detail, "stored": stored,
                          "shipped": shipped})


def scan_overrides(f: Findings, stored: dict, shipped: dict, where: str) -> None:
    """A stored number far from the shipped one is not wrong by itself - but
    every one of the three found by hand looked exactly like this."""
    for key, ship in shipped.items():
        if key not in stored:
            continue
        cur = stored[key]
        if isinstance(ship, bool) or isinstance(cur, bool):
            continue
        if isinstance(ship, (int, float)) and isinstance(cur, (int, float)):
            if ship == 0:
                continue
            ratio = cur / ship
            if ratio >= 4 or ratio <= 0.25:
                f.add("OVERRIDE", where, key,
                      f"stored {cur} is {ratio:.1f}x the shipped {ship}",
                      cur, ship)
        elif isinstance(ship, list) and isinstance(cur, list):
            missing = [x for x in ship if x not in cur]
            if missing:
                f.add("OVERRIDE", where, key,
                      f"stored list is missing shipped entries: {missing}",
                      cur, ship)


def scan_lattice(f: Findings, opt: dict) -> None:
    """min_positive_ratio can only take HOLDOUT_ROBUST_PARTS+1 values."""
    value = opt.get("min_positive_ratio")
    if value is None:
        return
    parts = int(HOLDOUT_ROBUST_PARTS)
    steps = [i / parts for i in range(parts + 1)]
    if any(abs(float(value) - s) < 1e-9 for s in steps):
        return
    eff = next((s for s in steps if s + 1e-9 >= float(value)), 1.0)
    wins = int(round(eff * parts))
    # Severity is the SIZE OF THE JUMP, not which rung you land on. 0.7 sits a
    # fifth of a step above 4/6 and is enforced as 5/6 - four fifths of a step
    # stricter than typed, which is what emptied the book. 0.6 sits well above
    # 3/6 and is enforced as 4/6: the same mechanism, a third of the damage.
    # Grading by "is it the top rung" missed 0.7 entirely, which is the one
    # case this check exists for.
    step = 1.0 / parts
    jump = (eff - float(value)) / step
    if wins >= parts:
        kind, note = "DEAD", "every sub-window must then be positive"
    elif jump >= 0.5:
        kind, note = ("STRICTER",
                      f"that is {jump:.0%} of a whole step above what was "
                      f"typed - the bar nobody chose")
    else:
        kind, note = ("ROUNDED",
                      "reachable, the number just is not the one typed")
    f.add(kind, "opt_params", "min_positive_ratio",
          f"{value:g} is between rungs of a {parts}-part ratio - it really "
          f"means {wins}/{parts} ({eff * 100:.0f}%); {note}",
          value, None)


def scan_evidence_bars(f: Findings, sup: dict, autopsies: list[dict],
                       lookback_days: float) -> None:
    """An evidence bar the book's own volume cannot reach is an off switch."""
    cutoff = time.time() - lookback_days * 86400.0
    recent = [r for r in autopsies
              if float(r.get("exit_time") or 0) >= cutoff]
    per_symbol: dict[str, int] = collections.Counter(
        str(r.get("symbol") or "") for r in recent)
    if not per_symbol:
        return
    typical = statistics.median(per_symbol.values())

    # _bad_hours buckets per symbol per hour.
    per_hour: collections.Counter = collections.Counter()
    for r in recent:
        t = float(r.get("exit_time") or 0)
        if t <= 0:
            continue
        per_hour[(str(r.get("symbol") or ""), time.gmtime(t).tm_hour)] += 1
    busiest_bucket = max(per_hour.values()) if per_hour else 0
    bar = sup.get("bad_hour_min_trades")
    if bar is not None and busiest_bucket < float(bar):
        f.add("DEAD", "supervisor", "bad_hour_min_trades",
              f"needs {bar} trades in one symbol-hour bucket; the busiest "
              f"bucket in {lookback_days:.0f} days holds {busiest_bucket}",
              bar, SUP_DEFAULTS.get("bad_hour_min_trades"))

    # Per-symbol bars.
    for key in ("min_trades", "watch_min_trades", "quarantine_losses",
                "edge_decay_min_trades"):
        bar = sup.get(key)
        if bar is None:
            continue
        reached = sum(1 for n in per_symbol.values() if n >= float(bar))
        if reached == 0:
            f.add("DEAD", "supervisor", key,
                  f"needs {bar} trades per symbol; the busiest symbol has "
                  f"{max(per_symbol.values())} in {lookback_days:.0f} days",
                  bar, SUP_DEFAULTS.get(key))
        elif reached < len(per_symbol) / 2:
            f.add("THIN", "supervisor", key,
                  f"only {reached}/{len(per_symbol)} symbols reach {bar} "
                  f"(median symbol has {typical:.0f})",
                  bar, SUP_DEFAULTS.get(key))


def scan_inert_gates(f: Findings, symbols: list[dict],
                     autopsies: list[dict]) -> None:
    """A protective ceiling far above what the symbol actually does."""
    spreads: dict[str, list[float]] = collections.defaultdict(list)
    for r in autopsies:
        if r.get("spread_atr") is not None:
            spreads[str(r.get("symbol") or "")].append(float(r["spread_atr"]))
    for cfg in symbols:
        sym = str(cfg.get("symbol") or "")
        seen = sorted(spreads.get(sym) or [])
        gate = cfg.get("max_spread_atr")
        if not seen or gate is None or float(gate) <= 0:
            continue
        worst = seen[-1]
        if float(gate) >= worst * 3:
            f.add("INERT", f"symbol/{sym}", "max_spread_atr",
                  f"gate {gate} sits {float(gate) / max(worst, 1e-9):.0f}x "
                  f"above the widest spread this symbol ever traded "
                  f"({worst:.4f}); it has never refused an entry",
                  gate, None)
        elif float(gate) < statistics.median(seen):
            f.add("BINDING", f"symbol/{sym}", "max_spread_atr",
                  f"gate {gate} is below the median spread actually traded "
                  f"({statistics.median(seen):.4f}) - entries are being "
                  f"refused more often than not, or the gate is not enforced",
                  gate, None)


def scan_search_reach(f: Findings, opt: dict, symbols: list[dict]) -> None:
    """A live value the search grid cannot produce is frozen forever."""
    grid = {**(opt.get("grid") or {})}
    for _name, per_fam in (opt.get("strategy_grids") or {}).items():
        for axis, values in (per_fam or {}).items():
            grid.setdefault(axis, values)
    for cfg in symbols:
        sym = str(cfg.get("symbol") or "")
        for axis, values in grid.items():
            if not isinstance(values, list) or not values:
                continue
            cur = cfg.get(axis)
            if cur is None or isinstance(cur, (bool, list, dict, str)):
                continue
            try:
                nums = [float(v) for v in values]
            except (TypeError, ValueError):
                continue
            if float(cur) > max(nums) + 1e-12:
                f.add("CEILING", f"symbol/{sym}", axis,
                      f"live {cur} is above the whole search grid "
                      f"(max {max(nums)}) - a search can only ever lower it",
                      cur, None)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", default="")
    args = ap.parse_args(argv)

    shipped = load_defaults()
    f = Findings()
    with _ro_db() as db:
        stored_sys = _setting(db, "system") or {}
        stored_opt = _setting(db, "opt_params") or {}
        stored_sup = _setting(db, "supervisor") or {}
        autopsies = _setting(db, "trade_autopsies") or []
        symbols = [json.loads(r[0]) for r in
                   db.execute("SELECT payload FROM symbols").fetchall()]

    opt = {**(shipped.get("optimizer") or {}), **stored_opt}
    sup = {**SUP_DEFAULTS, **stored_sup}

    scan_overrides(f, stored_sys, shipped.get("system") or {}, "system")
    scan_overrides(f, stored_opt, shipped.get("optimizer") or {}, "opt_params")
    scan_overrides(f, stored_sup, SUP_DEFAULTS, "supervisor")
    scan_lattice(f, opt)
    scan_evidence_bars(f, sup, autopsies,
                       float(sup.get("lookback_days") or 30))
    scan_inert_gates(f, symbols, autopsies)
    scan_search_reach(f, opt, symbols)

    order = {"DEAD": 0, "STRICTER": 1, "INERT": 2, "CEILING": 3,
             "BINDING": 4, "ROUNDED": 5, "OVERRIDE": 6, "THIN": 7}
    f.rows.sort(key=lambda r: (order.get(r["kind"], 9), r["where"], r["key"]))

    if not f.rows:
        print("temiz: hicbir esik olu veya atil gorunmuyor")
    for row in f.rows:
        print(f"[{row['kind']:<8}] {row['where']}.{row['key']}")
        print(f"           {row['detail']}")
        if row.get("shipped") is not None:
            print(f"           gonderilen varsayilan: {row['shipped']}")
    print()
    counts = collections.Counter(r["kind"] for r in f.rows)
    print("ozet: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
          if counts else "ozet: bulgu yok")

    if args.json:
        Path(args.json).write_text(json.dumps(f.rows, indent=2, default=str),
                                   encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
