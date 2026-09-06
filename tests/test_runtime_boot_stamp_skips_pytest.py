"""Engine must not let pytest overwrite the live runtime boot stamp.

stale_runtime_watch trusts ``.bridge/RUNTIME_BOOT_MANIFEST.json``. A test that
constructs a real ``Engine`` with a temp Store still resolved
``Path(__file__)`` into the repo ``.bridge/`` and rewrote the live stamp
(soft-restart 09:40:30 → suite 09:44:09), so the watcher compared disk mtimes
against a fake boot epoch.
"""
from __future__ import annotations

from pathlib import Path

from micofx.engine import Engine


def test_stamp_runtime_boot_skips_repo_bridge_under_pytest(monkeypatch):
    bridge = Path(__file__).resolve().parents[1] / ".bridge" / "RUNTIME_BOOT_MANIFEST.json"
    before = bridge.read_text(encoding="utf-8") if bridge.is_file() else None
    marker = '{"engine_started_at": 1, "source": "test-marker"}'
    bridge.parent.mkdir(parents=True, exist_ok=True)
    bridge.write_text(marker, encoding="utf-8")

    eng = object.__new__(Engine)

    class _Store:
        def set_setting(self, k, v):
            pass

    eng.store = _Store()
    monkeypatch.setenv("PYTEST_CURRENT_TEST",
                       "test_stamp_runtime_boot_skips_repo_bridge_under_pytest")
    try:
        Engine._stamp_runtime_boot(eng)
        assert bridge.read_text(encoding="utf-8") == marker
    finally:
        if before is not None:
            bridge.write_text(before, encoding="utf-8")
        elif bridge.is_file():
            bridge.unlink()
