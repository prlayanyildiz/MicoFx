"""Engine freeze-bind restart arms only when flag + flat."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine


def test_maybe_freeze_bind_skips_when_positions(tmp_path):
    flag = tmp_path / ".bridge" / "AUTOPILOT_RESUME_AFTER_RESTART"
    flag.parent.mkdir(parents=True)
    flag.write_text("x", encoding="utf-8")
    eng = Engine.__new__(Engine)
    eng._positions = [{"symbol": "BTCUSD"}]
    eng._last_freeze_bind_check = 0.0
    eng._freeze_bind_armed = False
    with patch("micofx.paths.ROOT", tmp_path):
        with patch("threading.Thread") as th:
            eng._maybe_freeze_bind_restart()
    th.assert_not_called()
    assert eng._freeze_bind_armed is False


def test_maybe_freeze_bind_arms_when_flat(tmp_path):
    flag = tmp_path / ".bridge" / "AUTOPILOT_RESUME_AFTER_RESTART"
    flag.parent.mkdir(parents=True)
    flag.write_text("x", encoding="utf-8")
    eng = Engine.__new__(Engine)
    eng._positions = []
    eng._last_freeze_bind_check = 0.0
    eng._freeze_bind_armed = False
    with patch("micofx.paths.ROOT", tmp_path):
        with patch("micofx.engine.LOG"):
            with patch("threading.Thread") as th:
                eng._maybe_freeze_bind_restart()
    th.assert_called_once()
    assert eng._freeze_bind_armed is True
    with patch("micofx.paths.ROOT", tmp_path):
        with patch("threading.Thread") as th2:
            eng._maybe_freeze_bind_restart()
    th2.assert_not_called()


def test_freeze_bind_script_invoked_with_verify():
    src = Path(__file__).resolve().parents[1] / "micofx" / "engine.py"
    text = src.read_text(encoding="utf-8")
    assert '"--verify"' in text or "'--verify'" in text
    assert "timeout=180" in text


def test_maybe_land_pending_xau_sl_throttled(tmp_path):
    from micofx.paths import ROOT as _real_root  # noqa: F401

    flag = tmp_path / ".bridge" / "XAU_SL_07_PENDING"
    flag.parent.mkdir(parents=True)
    flag.write_text("x", encoding="utf-8")
    eng = Engine.__new__(Engine)
    eng.store = object()
    eng.supervisor = type("S", (), {"optimizer": object()})()
    eng._last_xau_sl_land_check = 0.0
    calls: list[str] = []

    def _fake(opt, store):
        calls.append("land")
        return "XAUUSD sl 0.5->0.7"

    with patch("micofx.paths.ROOT", tmp_path):
        with patch("micofx.autopilot.maybe_land_pending_xau_sl", _fake):
            with patch("micofx.engine.LOG"):
                eng._maybe_land_pending_xau_sl()
                eng._maybe_land_pending_xau_sl()  # throttled
    assert calls == ["land"]
