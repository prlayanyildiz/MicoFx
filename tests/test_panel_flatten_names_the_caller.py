"""Panel flatten-all must leave a reason line, not only per-ticket closes.

26.08 12:22 six tickets closed with ``Pozisyon kapatildi kar~`` and no
``Zorunlu flatten`` / ``Gunluk zarar`` / ``ACIL DURDURMA`` / ``Bot durduruldu``.
That is ``close_all`` from the panel door. Three seconds later IPC died.
Without a caller line the book cannot be autopsied.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.models import SymbolConfig
from micofx.web import app as webapp


def test_close_all_with_a_reason_logs_before_the_broker(monkeypatch):
    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "micofx.engine.LOG.emit",
        lambda message, level="INFO", symbol="": seen.append((message, level)))
    eng = Engine.__new__(Engine)
    cfg = SymbolConfig(symbol="GER40", magic=990011)
    eng.store = SimpleNamespace(symbols={"GER40": cfg})
    called: dict = {}

    def _close_all(magics=None, symbol=None):
        called["magics"] = magics
        called["symbol"] = symbol
        return (2, 0)

    eng.client = SimpleNamespace(close_all=_close_all)
    closed, remaining = eng.close_all(reason="panel tumunu kapat")
    assert (closed, remaining) == (2, 0)
    assert called["magics"] == {990011}
    assert any("panel tumunu kapat" in m and lv == "WARN" for m, lv in seen)


def test_close_all_without_a_reason_stays_quiet(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(
        "micofx.engine.LOG.emit",
        lambda message, level="INFO", symbol="": seen.append(message))
    eng = Engine.__new__(Engine)
    eng.store = SimpleNamespace(symbols={})
    eng.client = SimpleNamespace(close_all=lambda **k: (0, 0))
    eng.close_all()
    assert seen == []


def test_panel_doors_pass_a_reason():
    src = inspect.getsource(webapp)
    assert 'reason="panel tumunu kapat"' in src
    assert 'reason="panel sembol kapat"' in src
