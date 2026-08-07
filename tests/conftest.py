"""Shared pytest fixtures for the whole tests/ package."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.logbus import LOG


@pytest.fixture(autouse=True)
def no_real_log_file(monkeypatch):
    # LOG is a module-level singleton imported directly by engine/risk/
    # optimizer/app.py, not injected - so even a fully-faked store/client/
    # engine still writes through to the REAL logs/micofx.log on disk the
    # moment any code path under test calls LOG.emit() at a persisted level
    # (WARN/ERROR/TRADE/OPT/AI). Silencing only the disk write keeps the
    # in-memory ring buffer (and therefore LOG.emit itself) working normally.
    monkeypatch.setattr(LOG, "_write_file", lambda entry: None)
