"""freeze_bind_when_flat only restarts when resume flag + flat book."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.freeze_bind_when_flat import should_restart


def test_should_restart_requires_flag_and_flat(tmp_path):
    flag = tmp_path / "AUTOPILOT_RESUME_AFTER_RESTART"
    assert should_restart(resume_flag=flag, flat=True) is False
    flag.write_text("x", encoding="utf-8")
    assert should_restart(resume_flag=flag, flat=False) is False
    assert should_restart(resume_flag=flag, flat=True) is True


def test_verify_bind_ok_when_ap_frozen_resume_gone(tmp_path, monkeypatch):
    from scripts import freeze_bind_when_flat as mod

    monkeypatch.setattr(mod, "RESUME_FLAG", tmp_path / "missing")
    monkeypatch.setattr(mod, "DONE_FLAG", tmp_path / "DONE.txt")

    class _Resp:
        def read(self):
            return json.dumps({
                "system": {"autopilot_enabled": True},
                "positions": [],
            }).encode()

    class _Op:
        def open(self, *a, **k):
            return _Resp()

    monkeypatch.setattr(mod, "_session", lambda panel="": _Op())
    with (
        patch("scripts.exec_gates.pipeline_frozen", return_value=True),
        patch("scripts.xau_sl_land.land", return_value=(True, "pending flag yok")),
    ):
        ok, msg = mod.verify_bind(timeout_sec=2.0, poll_sec=0.2)
    assert ok and "bind OK" in msg
    assert mod.DONE_FLAG.is_file()
