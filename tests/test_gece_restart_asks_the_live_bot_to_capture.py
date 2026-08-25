"""Midnight restart must ask the live bot to pin holdout bars.

capture() lived in holdout_cost.py and was never called. gece_restart used
to return as soon as port 8900 listened, so the pin never existed. The live
process already holds initialize(); this script must not open a second one.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gece_restart


def test_the_script_never_initializes_mt5():
    src = Path(gece_restart.__file__).read_text(encoding="utf-8")
    assert "mt5.initialize" not in src
    assert "MetaTrader5" not in src


def test_request_holdout_capture_posts_the_live_endpoint(tmp_path, monkeypatch):
    """The helper talks to a fake opener. It must not append the live night log.

    25.08: five 'holdout capture: 1 yazildi' lines landed in logs/gece_restart.log
    with no restart wrapper around them. The live bot had no /api/holdout/capture
    yet and data/holdout_bars/ was never created. Those lines were this test
    calling say() against the real file.
    """
    monkeypatch.setattr(gece_restart, "LOG", tmp_path / "gece_restart.log")
    hits = []

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return self._payload

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _Op:
        def open(self, req, timeout=0):
            url = req if isinstance(req, str) else req.full_url
            method = "GET" if isinstance(req, str) else req.get_method()
            hits.append((method, url))
            assert "/api/holdout/capture" in str(url)
            return _Resp(b'{"ok":true,"captured":1,"results":[{"symbol":"GER40","ok":true}]}')

    gece_restart.request_holdout_capture(_Op(), "http://127.0.0.1:8900")
    assert any(m == "POST" and u.endswith("/api/holdout/capture") for m, u in hits)
    logged = (tmp_path / "gece_restart.log").read_text(encoding="utf-8")
    assert "1 yazildi" in logged



def test_a_successful_boot_asks_the_live_bot_to_capture(monkeypatch):
    called = {}
    monkeypatch.setattr(gece_restart, "port_owner", lambda: None)
    monkeypatch.setattr(gece_restart, "start", lambda: None)
    monkeypatch.setattr(gece_restart, "port_open", lambda: True)
    monkeypatch.setattr(gece_restart, "panel_session", lambda base: "op")
    monkeypatch.setattr(
        gece_restart, "wait_mt5_connected", lambda op, base, seconds=60: True)
    monkeypatch.setattr(
        gece_restart, "request_holdout_capture",
        lambda op, base: called.setdefault("yes", (op, base)))
    monkeypatch.setattr(gece_restart, "say", lambda t: None)
    monkeypatch.setattr(gece_restart.time, "sleep", lambda s: None)
    assert gece_restart.main() == 0
    assert called.get("yes") == ("op", "http://127.0.0.1:8900")


def test_a_failed_capture_does_not_fail_the_restart(monkeypatch):
    monkeypatch.setattr(gece_restart, "port_owner", lambda: None)
    monkeypatch.setattr(gece_restart, "start", lambda: None)
    monkeypatch.setattr(gece_restart, "port_open", lambda: True)
    monkeypatch.setattr(gece_restart, "panel_session", lambda base: "op")
    monkeypatch.setattr(
        gece_restart, "wait_mt5_connected", lambda op, base, seconds=60: True)

    def boom(op, base):
        raise RuntimeError("panel 500")

    monkeypatch.setattr(gece_restart, "request_holdout_capture", boom)
    monkeypatch.setattr(gece_restart, "say", lambda t: None)
    monkeypatch.setattr(gece_restart.time, "sleep", lambda s: None)
    assert gece_restart.main() == 0
