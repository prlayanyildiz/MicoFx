"""Autopilot resume after exec-freeze bind (old PID had no freeze)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import autopilot as ap_mod
from micofx.autopilot import maybe_resume_autopilot_after_freeze_bind


def test_resume_re_enables_when_flag_and_frozen(tmp_path, monkeypatch):
    flag = tmp_path / "AUTOPILOT_RESUME_AFTER_RESTART"
    flag.write_text("bind", encoding="utf-8")
    monkeypatch.setattr(ap_mod, "_AUTOPILOT_RESUME_FLAG", flag)

    store = MagicMock()
    store.system.autopilot_enabled = False

    with patch("scripts.exec_gates.pipeline_frozen", return_value=True):
        msg = maybe_resume_autopilot_after_freeze_bind(store)

    assert msg is not None and "autopilot_enabled=true" in msg
    store.update_system.assert_called_once_with(
        {"autopilot_enabled": True}, source="freeze-bind resume")
    assert not flag.exists()


def test_resume_noop_when_not_frozen(tmp_path, monkeypatch):
    flag = tmp_path / "AUTOPILOT_RESUME_AFTER_RESTART"
    flag.write_text("bind", encoding="utf-8")
    monkeypatch.setattr(ap_mod, "_AUTOPILOT_RESUME_FLAG", flag)

    store = MagicMock()
    store.system.autopilot_enabled = False

    with patch("scripts.exec_gates.pipeline_frozen", return_value=False):
        assert maybe_resume_autopilot_after_freeze_bind(store) is None
    store.update_system.assert_not_called()
    assert flag.exists()


def test_resume_noop_without_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(
        ap_mod, "_AUTOPILOT_RESUME_FLAG", tmp_path / "missing")
    store = MagicMock()
    store.system.autopilot_enabled = False
    assert maybe_resume_autopilot_after_freeze_bind(store) is None
    store.update_system.assert_not_called()


def test_maybe_land_pending_xau_sl_applies_and_clears(tmp_path, monkeypatch):
    from micofx.autopilot import maybe_land_pending_xau_sl
    from micofx.models import SymbolConfig

    pending = tmp_path / "PENDING"
    pending.write_text("ok", encoding="utf-8")
    done = tmp_path / "DONE.txt"
    streak = tmp_path / "streak.json"
    reenable = tmp_path / "REENABLE"
    monkeypatch.setattr(ap_mod, "_XAU_SL_PENDING", pending)
    monkeypatch.setattr(ap_mod, "_XAU_SL_DONE", done)
    monkeypatch.setattr(ap_mod, "_XAU_STREAK_STATE", streak)
    monkeypatch.setattr(ap_mod, "_XAU_SL_REENABLE", reenable)

    cfg = SymbolConfig(
        symbol="XAUUSD", magic=1, enabled=True,
        strategy="mtf_pullback", timeframe="M15",
        sl_atr_mult=0.5, opt_score=100.0,
    )
    store = MagicMock()
    store.symbols = {"XAUUSD": cfg}
    opt = MagicMock()
    opt._force_apply = False

    def _apply(*a, **k):
        cfg.sl_atr_mult = 0.7
        return {"ok": True}

    opt.apply.side_effect = _apply

    msg = maybe_land_pending_xau_sl(opt, store)
    assert msg and "0.5->0.7" in msg
    assert opt.apply.called
    assert opt._force_apply is False
    assert not pending.exists()
    assert done.is_file()
    assert streak.is_file()


def test_maybe_land_deferred_keeps_pending(tmp_path, monkeypatch):
    from micofx.autopilot import maybe_land_pending_xau_sl
    from micofx.models import SymbolConfig

    pending = tmp_path / "PENDING"
    pending.write_text("ok", encoding="utf-8")
    reenable = tmp_path / "REENABLE"
    reenable.write_text("x", encoding="utf-8")
    monkeypatch.setattr(ap_mod, "_XAU_SL_PENDING", pending)
    monkeypatch.setattr(ap_mod, "_XAU_SL_DONE", tmp_path / "DONE.txt")
    monkeypatch.setattr(ap_mod, "_XAU_STREAK_STATE", tmp_path / "streak.json")
    monkeypatch.setattr(ap_mod, "_XAU_SL_REENABLE", reenable)

    cfg = SymbolConfig(
        symbol="XAUUSD", magic=1, enabled=False,
        strategy="mtf_pullback", timeframe="M15",
        sl_atr_mult=0.5, opt_score=100.0,
    )
    store = MagicMock()
    store.symbols = {"XAUUSD": cfg}
    opt = MagicMock()
    opt._force_apply = False
    opt.apply.return_value = {"ok": True, "deferred": True}

    msg = maybe_land_pending_xau_sl(opt, store)
    assert msg and "kuyrukta" in msg
    assert pending.is_file()
    assert reenable.is_file()
    store.update_symbol.assert_not_called()


def test_maybe_land_noop_without_pending(tmp_path, monkeypatch):
    from micofx.autopilot import maybe_land_pending_xau_sl

    monkeypatch.setattr(ap_mod, "_XAU_SL_PENDING", tmp_path / "nope")
    assert maybe_land_pending_xau_sl(MagicMock(), MagicMock()) is None
