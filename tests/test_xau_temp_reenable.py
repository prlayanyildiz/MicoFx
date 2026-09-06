"""xau_temp_reenable — EU-hour gate for night disable flag."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import xau_temp_reenable as xr
from scripts.xau_temp_reenable import reenable


class _Resp:
    def __init__(self, body: dict):
        self._body = json.dumps(body).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _redirect_notify(tmp_path, monkeypatch):
    monkeypatch.setattr(xr, "INBOX", tmp_path / "FOR_CLAUDE.md")
    monkeypatch.setattr(xr, "WAKE", tmp_path / "WAKE.txt")


def test_reenable_waits_before_eu(tmp_path, monkeypatch):
    flag = tmp_path / "XAU_TEMP_DISABLE_UNTIL_EU"
    flag.write_text("x", encoding="utf-8")
    monkeypatch.setattr(xr, "FLAG", flag)
    _redirect_notify(tmp_path, monkeypatch)
    op = MagicMock()
    with patch.object(xr, "_session", return_value=op):
        with patch.object(xr, "xau_enabled", return_value=False):
            with patch.object(xr, "broker_hour", return_value=6):
                ok, msg = reenable("http://x", eu_hour=8)
    assert ok and "bekliyor" in msg
    assert flag.is_file()
    assert not (tmp_path / "FOR_CLAUDE.md").is_file()


def test_reenable_posts_after_eu(tmp_path, monkeypatch):
    flag = tmp_path / "XAU_TEMP_DISABLE_UNTIL_EU"
    flag.write_text("x", encoding="utf-8")
    monkeypatch.setattr(xr, "FLAG", flag)
    _redirect_notify(tmp_path, monkeypatch)
    posts: list = []
    calls = {"n": 0}

    def open_side(req, timeout=30):
        posts.append(getattr(req, "selector", str(req)))
        return _Resp({"ok": True, "config": {"enabled": True}})

    def en_side(op, panel="http://x"):
        # First gate (still off), then post-verify (on).
        calls["n"] += 1
        return calls["n"] >= 2

    op = MagicMock()
    op.open = open_side
    with patch.object(xr, "_session", return_value=op):
        with patch.object(xr, "xau_enabled", side_effect=en_side):
            with patch.object(xr, "broker_hour", return_value=8):
                with patch(
                    "scripts.xau_post_eu_watch.arm",
                    lambda **k: None,
                ):
                    ok, msg = reenable("http://x", eu_hour=8)
    assert ok and "enabled=true" in msg
    assert posts and not flag.is_file()
    text = (tmp_path / "FOR_CLAUDE.md").read_text(encoding="utf-8")
    assert "enabled=true" in text
    assert (tmp_path / "WAKE.txt").is_file()


def test_reenable_no_notify_without_verified_enable(tmp_path, monkeypatch):
    flag = tmp_path / "XAU_TEMP_DISABLE_UNTIL_EU"
    flag.write_text("x", encoding="utf-8")
    monkeypatch.setattr(xr, "FLAG", flag)
    _redirect_notify(tmp_path, monkeypatch)
    op = MagicMock()
    op.open = lambda req, timeout=30: _Resp({"ok": True})
    with patch.object(xr, "_session", return_value=op):
        with patch.object(xr, "xau_enabled", return_value=False):
            with patch.object(xr, "broker_hour", return_value=8):
                ok, msg = reenable("http://x", eu_hour=8)
    assert not ok and "dogrulanamadi" in msg
    assert flag.is_file()
    assert not (tmp_path / "FOR_CLAUDE.md").is_file()


def test_reenable_arms_post_eu_with_seed_rows(tmp_path, monkeypatch):
    """EU lift must seed known XAU tickets so pre-arm closes cannot false-wake."""
    flag = tmp_path / "XAU_TEMP_DISABLE_UNTIL_EU"
    flag.write_text("x", encoding="utf-8")
    monkeypatch.setattr(xr, "FLAG", flag)
    _redirect_notify(tmp_path, monkeypatch)
    calls = {"n": 0}
    armed: dict = {}

    def en_side(op, panel="http://x"):
        calls["n"] += 1
        return calls["n"] >= 2

    def open_side(req, timeout=30):
        return _Resp({"ok": True, "config": {"enabled": True}})

    seed = [{
        "symbol": "XAUUSD",
        "ticket": 324704274,
        "r_realised": -1.01,
        "exit_time": 1_000_000,
    }]

    def arm_side(**kwargs):
        armed.update(kwargs)

    op = MagicMock()
    op.open = open_side
    with patch.object(xr, "_session", return_value=op):
        with patch.object(xr, "xau_enabled", side_effect=en_side):
            with patch.object(xr, "broker_hour", return_value=8):
                with patch(
                    "scripts.xau_streak_watch.fetch_autopsy_rows",
                    return_value=seed,
                ):
                    with patch(
                        "scripts.xau_post_eu_watch.arm",
                        side_effect=arm_side,
                    ):
                        ok, msg = reenable("http://x", eu_hour=8)
    assert ok and "enabled=true" in msg
    assert armed.get("seed_rows") == seed
    assert armed.get("autopsy_n") == 1


def test_no_flag_is_noop(tmp_path, monkeypatch):
    monkeypatch.setattr(xr, "FLAG", tmp_path / "missing")
    _redirect_notify(tmp_path, monkeypatch)
    ok, msg = reenable("http://x")
    assert ok and "flag yok" in msg
