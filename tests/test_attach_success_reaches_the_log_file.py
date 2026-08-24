"""A successful MT5 attach has to survive in the log file.

``_after_connect`` used to emit ``MT5 baglandi`` at INFO. INFO is not in
``_PERSIST``, so the line never reached disk. The in-memory ring is 1500
entries and is cleared on restart.

That is the audit trail the 22.08 incident needed. The terminal was back in
a minute; the bot stayed blind for 32 hours; the log after the first
``positions_get`` IPC line showed no reconnect attempt. A successful
``connect()`` would have produced exactly one ``MT5 baglandi`` line, at
INFO, which the file cannot hold. Absence of a retry line therefore cannot
tell a failed attach from a successful one.

The attach is not per-poll: it fires once when the client actually binds.
WARN is already persisted. INFO and DEBUG stay in memory.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.logbus import _PERSIST
from micofx.mt5client import MT5Client


def test_attach_success_uses_a_persisted_level():
    src = Path("micofx/mt5client.py").read_text(encoding="utf-8")
    body = src.split("def _after_connect(", 1)[1].split("\n    def ", 1)[0]
    line = next(row for row in body.splitlines() if "MT5 baglandi" in row)
    assert '"INFO"' not in line and "'INFO'" not in line
    assert any(f'"{level}"' in line or f"'{level}'" in line
               for level in _PERSIST), (
        "baglanti basarisi diske ulasmiyor - 22.08 sorusturmasinin "
        "okuyamadigi satir bu")


def test_the_emit_site_still_exists():
    """A rename that drops the needle would silence the test above."""
    src = Path("micofx/mt5client.py").read_text(encoding="utf-8")
    assert "MT5 baglandi" in src
    assert hasattr(MT5Client, "_after_connect")
