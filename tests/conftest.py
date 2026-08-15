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


_ftc.TestClient = TestClient


@pytest.fixture(autouse=True)
def no_real_log_file(monkeypatch):
    # LOG is a module-level singleton imported directly by engine/risk/
    # optimizer/app.py, not injected - so even a fully-faked store/client/
    # engine still writes through to the REAL logs/micofx.log on disk the
    # moment any code path under test calls LOG.emit() at a persisted level
    # (WARN/ERROR/TRADE/OPT/AI). Silencing only the disk write keeps the
    # in-memory ring buffer (and therefore LOG.emit itself) working normally.
    monkeypatch.setattr(LOG, "_write_file", lambda entry: None)
