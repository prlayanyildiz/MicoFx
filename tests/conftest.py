"""Shared pytest fixtures for the whole tests/ package."""
from __future__ import annotations

import sys
from pathlib import Path

import fastapi.testclient as _ftc
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.logbus import LOG


class TestClient(_ftc.TestClient):
    """Same as FastAPI's client, plus the in-memory session header.

    create_app always issues a session secret now (AS1). Tests that check the
    gate itself pass ``unauth=True``.
    """

    def __init__(self, app, *args, unauth: bool = False, **kwargs):
        super().__init__(app, *args, **kwargs)
        if unauth:
            return
        token = getattr(getattr(app, "state", None), "api_token", "") or ""
        if token:
            self.headers["x-mico-token"] = token
            self.headers.setdefault("origin", "http://testserver")


_ftc.TestClient = TestClient


def _survive_unreadable_symlinks() -> None:
    """Stop pytest's own temp housekeeping from failing a passing suite.

    ``tmp_path`` names each per-test directory ``<name>0`` and drops a
    ``<name>current`` symlink beside it. At session end pytest walks those and
    calls ``resolve()`` on each, which is where two of the machines this runs
    on refuse: Windows Server raises WinError 1463 (symlink evaluation
    disabled by policy) and the laptop WinError 5. Creating the link is
    allowed on both - only following it is not - so no basetemp, temp root or
    cleanup setting avoids it; the call is simply not permitted here.

    The cost was not cosmetic. Every test passed, pytest raised on the way out,
    the process exited non-zero, and KUR.ps1's install check read that as a
    failing suite on a machine where nothing was wrong.

    Only OSError from the housekeeping walk is swallowed, and only after the
    run is over, so a real failure still fails. Both module references are
    patched: _pytest.tmpdir imported the function by name at import time, so
    patching _pytest.pathlib alone would leave the session-finish call bound
    to the original.
    """
    try:
        from _pytest import pathlib as _pl
        from _pytest import tmpdir as _tmp
    except ImportError:                      # pragma: no cover - pytest internals moved
        return

    original = _pl.cleanup_dead_symlinks

    def tolerant(root) -> None:
        try:
            original(root)
        except OSError:
            pass

    _pl.cleanup_dead_symlinks = tolerant
    if hasattr(_tmp, "cleanup_dead_symlinks"):
        _tmp.cleanup_dead_symlinks = tolerant


_survive_unreadable_symlinks()


@pytest.fixture(autouse=True)
def no_real_log_file(monkeypatch):
    # LOG is a module-level singleton imported directly by engine/risk/
    # optimizer/app.py, not injected - so even a fully-faked store/client/
    # engine still writes through to the REAL logs/micofx.log on disk the
    # moment any code path under test calls LOG.emit() at a persisted level
    # (WARN/ERROR/TRADE/OPT/AI). Silencing only the disk write keeps the
    # in-memory ring buffer (and therefore LOG.emit itself) working normally.
    monkeypatch.setattr(LOG, "_write_file", lambda entry: None)
