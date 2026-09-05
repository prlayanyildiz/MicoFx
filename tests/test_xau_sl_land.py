"""xau_sl_land pending flag gating."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import xau_sl_land as mod


def test_land_noop_without_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "PENDING", tmp_path / "nope")
    monkeypatch.setattr(mod, "DONE", tmp_path / "done.txt")
    monkeypatch.setattr(mod, "STREAK_STATE", tmp_path / "streak.json")
    ok, msg = mod.land(panel="http://127.0.0.1:9")
    assert ok and "pending flag yok" in msg


def test_land_clears_when_already_at_target(tmp_path, monkeypatch):
    pending = tmp_path / "PENDING"
    pending.write_text("x", encoding="utf-8")
    done = tmp_path / "done.txt"
    streak = tmp_path / "streak.json"
    monkeypatch.setattr(mod, "PENDING", pending)
    monkeypatch.setattr(mod, "DONE", done)
    monkeypatch.setattr(mod, "STREAK_STATE", streak)
    monkeypatch.setattr(mod, "REENABLE", tmp_path / "no_reenable")

    class _Op:
        def open(self, *a, **k):
            class R:
                def read(self):
                    return json.dumps({
                        "symbols": [{"symbol": "XAUUSD", "sl_atr_mult": 0.7,
                                     "opt_score": 1.0}],
                    }).encode()
            return R()

    monkeypatch.setattr(mod, "_session", lambda panel="": _Op())
    ok, msg = mod.land()
    assert ok and "zaten" in msg
    assert not pending.is_file()
    assert done.is_file()
    assert streak.is_file()


def test_land_deferred_keeps_pending(tmp_path, monkeypatch):
    pending = tmp_path / "PENDING"
    pending.write_text("x", encoding="utf-8")
    reenable = tmp_path / "REENABLE"
    reenable.write_text("x", encoding="utf-8")
    monkeypatch.setattr(mod, "PENDING", pending)
    monkeypatch.setattr(mod, "DONE", tmp_path / "done.txt")
    monkeypatch.setattr(mod, "STREAK_STATE", tmp_path / "streak.json")
    monkeypatch.setattr(mod, "REENABLE", reenable)

    calls = {"n": 0}

    class _Op:
        def open(self, *a, **k):
            calls["n"] += 1

            class R:
                def __enter__(self):
                    return self

                def __exit__(self, *exc):
                    return False

                def read(self):
                    if calls["n"] == 1:
                        return json.dumps({
                            "symbols": [{"symbol": "XAUUSD", "sl_atr_mult": 0.5,
                                         "opt_score": 1.0}],
                        }).encode()
                    if calls["n"] == 2:
                        return json.dumps(
                            {"ok": True, "deferred": True}).encode()
                    return json.dumps({
                        "symbols": [{
                            "symbol": "XAUUSD", "sl_atr_mult": 0.5,
                            "opt_score": 1.0,
                            "pending_exit_patch": {"sl_atr_mult": 0.7},
                        }],
                    }).encode()

            return R()

    monkeypatch.setattr(mod, "_session", lambda panel="": _Op())
    ok, msg = mod.land()
    assert ok and "kuyrukta" in msg
    assert pending.is_file()
    assert reenable.is_file()
