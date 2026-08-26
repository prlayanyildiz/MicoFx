"""Ticket highlighting must not be built by regexing already-escaped text.

`esc()` turns an apostrophe into `&#39;`. A highlighter that escapes first
and then hunts `#\\d+` over the result matches the `#39` *inside that
entity*, wraps it in a span, and renders a broken `&<span>#39</span>;` —
so a log line containing a quote comes out mangled. Every TRADE line the
engine writes is operator-facing, and Turkish log text carries apostrophes.

`ticketHtml` therefore splits the RAW message on the ticket pattern and
escapes each piece separately: at split time no entity exists yet, so none
can be cut in half. These tests pin that ordering, because the broken
version looks identical in a quick read.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def _body() -> str:
    """Code only. The helper's own comment names `esc()` while explaining the
    trap, and a comment is not a call site - scanning raw text fails on prose.
    """
    raw = JS.split("function ticketHtml(", 1)[1].split("\nfunction ", 1)[0]
    return "\n".join(
        ln for ln in raw.splitlines() if not ln.lstrip().startswith("//"))


def test_ticket_html_splits_before_escaping():
    body = _body()
    split_at = body.index(".split(")
    # esc() may only appear after the split - i.e. on the pieces, never on a
    # whole string that is then re-scanned.
    for hit in re.finditer(r"\besc\(", body):
        assert hit.start() > split_at, "esc() runs before the split"


def test_ticket_pattern_never_scans_escaped_output():
    """No regex may be applied to the joined/escaped result."""
    body = _body()
    tail = body[body.index("return"):]
    assert ".replace(/" not in tail, "regex over escaped output"


def test_ticket_pattern_needs_four_digits():
    """`#1` in prose is not a ticket; live tickets are nine digits."""
    body = _body()
    assert "#\\d{4,}" in body


def test_message_span_uses_the_helper_not_bare_esc():
    line = JS.split("function makeLogLine(", 1)[1].split("\nfunction ", 1)[0]
    assert 'class="m">${ticketHtml(e.message)}' in line
    # The other three fields stay on plain esc().
    for field in ("e.time", "e.level"):
        assert f"esc({field})" in line


def test_haystack_still_indexes_the_raw_message():
    """Search must match the ticket even though the span now splits it."""
    line = JS.split("function makeLogLine(", 1)[1].split("\nfunction ", 1)[0]
    assert "dataset.hay" in line
    assert "e.message" in line.split("dataset.hay", 1)[1].split("\n", 1)[0]
