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
            origin = None if isinstance(req, str) else req.get_header("Origin")
            hits.append((method, url, origin))
            assert "/api/holdout/capture" in str(url)
            return _Resp(b'{"ok":true,"captured":1,"results":[{"symbol":"GER40","ok":true}]}')

    gece_restart.request_holdout_capture(_Op(), "http://127.0.0.1:8900")
    assert any(
        m == "POST" and u.endswith("/api/holdout/capture")
        and o == "http://127.0.0.1:8900"
        for m, u, o in hits
    )
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


def test_a_running_search_is_logged_before_the_tree_dies(tmp_path, monkeypatch):
    """26.08 12:32 search ran 11h then gece killed it with no OPT/gece line.

    The restart is still unconditional (midnight is empty). The miss was
    silence: operators could not tell a 5M-combo job had been cut.
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
            url = req if isinstance(req, str) else getattr(req, "full_url", req)
            hits.append(str(url))
            if str(url).rstrip("/").endswith("/api/state"):
                body = (
                    b'{"ok":true,"opt":{"busy":true,"state":"running",'
                    b'"current":"NAS100","combo_done":900000,'
                    b'"combo_total":5270000}}')
                return _Resp(body)
            return _Resp(b"{}")

    gece_restart.note_in_flight_search(_Op(), "http://127.0.0.1:8900")
    logged = (tmp_path / "gece_restart.log").read_text(encoding="utf-8")
    assert "yari da kesiliyor" in logged
    assert "NAS100" in logged
    assert "900000" in logged
    assert any(u.endswith("/api/state") for u in hits)


def test_orphans_are_swept_after_the_tree_is_killed(monkeypatch):
    """taskkill /T misses multiprocessing children whose parent is already
    dead. The boot sweep used to miss them too (venv vs base pythonw).
    Gece must sweep after stop, not wait for the next process to boot.
    """
    order = []
    monkeypatch.setattr(gece_restart, "port_owner", lambda: 10888)
    monkeypatch.setattr(gece_restart, "note_in_flight_search", lambda *a: None)
    monkeypatch.setattr(
        gece_restart, "stop_tree",
        lambda pid: order.append(("stop", pid)))
    monkeypatch.setattr(
        gece_restart, "cleanup_orphan_workers",
        lambda executable=None: order.append(("sweep", executable)))
    monkeypatch.setattr(gece_restart, "start", lambda: None)
    monkeypatch.setattr(gece_restart, "port_open", lambda: True)
    monkeypatch.setattr(gece_restart, "panel_session", lambda base: "op")
    monkeypatch.setattr(
        gece_restart, "wait_mt5_connected", lambda op, base, seconds=60: True)
    monkeypatch.setattr(gece_restart, "request_holdout_capture", lambda *a: None)
    monkeypatch.setattr(gece_restart, "say", lambda t: None)
    monkeypatch.setattr(gece_restart.time, "sleep", lambda s: None)
    assert gece_restart.main() == 0
    kinds = [step[0] for step in order]
    assert kinds[:2] == ["stop", "sweep"], kinds
    assert order[0] == ("stop", 10888)
