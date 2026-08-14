"""A new symbol must not open carrying a deleted symbol's record.

``Store.next_magic`` counts up from 990101 and avoids only the magics the book
currently holds, plus orphan scan/ticket magics. A magic freed by deleting a
symbol still owns that symbol's CLOSED deals at the broker, and both readers
resolve a deal to a symbol *through* the magic - ``engine.day_stats`` at
engine.py:2473 and ``supervisor.review`` at supervisor.py:436. So the freed
number hands the new symbol wins and losses it never made, and the supervisor
can suspend it on them.

Measured 15.08 on the live account, before the fix: the book held ten magics,
the first free number next_magic would return was 990101, and 990101 carried
**21 closed deals** in the last thirty days. Nineteen other numbers in the band
it walks were in the same state, and 1082 magics across the window had no symbol
in the book at all.

The per-magic guard for a hand-typed number already existed and reasoned "only
today's deals matter". That is right for day_stats and wrong for the supervisor,
whose window is ``lookback_days`` - thirty by default. Auto-assignment consulted
neither.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

APP = (Path(__file__).resolve().parents[1] / "micofx" / "web" / "app.py").read_text(
    encoding="utf-8")


def _fresh_magic_sites() -> list[str]:
    """Every call that lets Store mint a magic rather than passing one in.

    Read to the end of the line, not to the first ``)``: the sites pass a union
    and stopping at the first bracket hides the half being asserted. Prose
    mentions the same keyword (one docstring quotes the old call), so lines
    inside a string or comment are dropped rather than counted as call sites.
    """
    out = []
    for line in APP.splitlines():
        body = line.split("#", 1)[0]
        if "avoid_magics=" not in body or "``" in line:
            continue
        out.append(body.split("avoid_magics=", 1)[1].strip())
    return out


def test_every_fresh_magic_site_avoids_history():
    """One site left out is one route that can still reissue a dirty number."""
    sites = _fresh_magic_sites()
    assert sites, "no magic-minting call sites found - has the helper been renamed?"
    missing = [s for s in sites if "_recent_deal_magics()" not in s]
    assert not missing, ("these hand out a magic without checking broker history: "
                         + "; ".join(missing))


def test_the_window_is_the_supervisors_not_today():
    """day_stats resets daily; the supervisor's evidence window does not."""
    body = APP[APP.index("def _recent_deal_magics"):]
    body = body[:body.index("def _magic_blocked_by_orphan_state")]
    assert "lookback_days" in body, (
        "a one-day window leaves the supervisor half of the problem open")
    assert "deals_since" in body


def test_a_dropped_connection_refuses_rather_than_answering_clean():
    """An empty deal list means 'quiet month' and 'no link' identically.

    Returning set() on a dropped connection would certify a dirty magic as
    clean - the silent-substitution class this codebase has already been bitten
    by three times (timeframe_seconds, the M1 bars, the unknown family).
    """
    body = APP[APP.index("def _recent_deal_magics"):]
    body = body[:body.index("def _magic_blocked_by_orphan_state")]
    assert "_require_connected()" in body, (
        "disconnected must refuse, not answer with an empty set")
    guard = body.index("_require_connected()")
    read = body.index("deals_since")
    assert guard < read, "the connection has to be established before the read"


def test_the_orphan_checks_are_still_there():
    """This adds a third source of forbidden magics; it replaces neither."""
    sites = _fresh_magic_sites()
    assert all("_orphan_ticket_magics()" in s for s in sites), (
        "the live orphan-ticket half must survive alongside the history half")
