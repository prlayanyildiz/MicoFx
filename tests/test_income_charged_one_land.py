"""income --auto charged tunes: one land per symbol (compound gate)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import income_dev_loop as loop


def test_run_charged_tunes_stops_after_first_land():
    row = {"symbol": "NAS100", "enabled": True}
    calls: list[str] = []

    class _Sess:
        @staticmethod
        def apply_session_upgrade(headers, *, panel, row):
            calls.append("seans")
            return True, "NAS100 seans -> 14:00-22:00 (+10.0R->+20.0R)"

    class _Msa:
        @staticmethod
        def apply_msa_upgrade(headers, *, panel, row):
            calls.append("msa")
            return True, "NAS100 msa 0.05->0.08 (+10.0R->+20.0R)"

    class _Cr:
        @staticmethod
        def apply_cost_rank_upgrade(headers, *, panel, row):
            calls.append("cr")
            return True, "NAS100 cost_rank 0.5->0.4 (+10.0R->+20.0R)"

    class _Trail:
        @staticmethod
        def apply_trail_upgrade(headers, *, panel, row):
            calls.append("trail_step")
            return True, "NAS100 trail_step degismedi (3.2)"

        @staticmethod
        def apply_trail_start_upgrade(headers, *, panel, row):
            calls.append("trail_start")
            return True, "NAS100 trail_start 0.3->1.8 (+10.0R->+20.0R)"

    mods = {
        "session_exec": _Sess(),
        "msa_exec": _Msa(),
        "cost_rank_exec": _Cr(),
        "adx_exec": type("A", (), {"apply_adx_upgrade": staticmethod(
            lambda headers, *, panel, row: (_ for _ in ()).throw(
                AssertionError("adx should not run"))
        )})(),
        "atr_pct_exec": type("P", (), {"apply_atr_pct_upgrade": staticmethod(
            lambda headers, *, panel, row: (_ for _ in ()).throw(
                AssertionError("atr_pct should not run"))
        )})(),
        "body_exec": type("B", (), {"apply_body_upgrade": staticmethod(
            lambda headers, *, panel, row: (_ for _ in ()).throw(
                AssertionError("body should not run"))
        )})(),
        "trail_exec": _Trail(),
    }

    def fake_load(name, path):
        return mods[name]

    def fake_get(path, headers):
        if path == "/api/state":
            return {"opt": {"busy": False}, "positions": []}
        return {"symbols": [row]}

    with patch("scripts.exec_gates.pipeline_frozen", return_value=False):
        with patch.object(loop, "_api_get", fake_get):
            with patch.object(loop, "_load_exec", fake_load):
                out = loop._run_charged_tunes({})
    assert calls == ["seans"]
    assert any("1 land/sembol" in m for m in out)


def test_run_charged_tunes_falls_through_keeps():
    row = {"symbol": "GER40", "enabled": True}
    calls: list[str] = []

    class _Sess:
        @staticmethod
        def apply_session_upgrade(headers, *, panel, row):
            calls.append("seans")
            return True, "GER40 seans degismedi (08:00-15:59)"

    class _Msa:
        @staticmethod
        def apply_msa_upgrade(headers, *, panel, row):
            calls.append("msa")
            return True, "GER40 msa degismedi (0.05)"

    class _Cr:
        @staticmethod
        def apply_cost_rank_upgrade(headers, *, panel, row):
            calls.append("cr")
            return True, "GER40 cost_rank degismedi (0)"

    class _Adx:
        @staticmethod
        def apply_adx_upgrade(headers, *, panel, row):
            calls.append("adx")
            return True, "GER40 adx_min degismedi (15)"

    class _Atr:
        @staticmethod
        def apply_atr_pct_upgrade(headers, *, panel, row):
            calls.append("atr_pct")
            return True, "GER40 atr_pct_min degismedi (0)"

    class _Body:
        @staticmethod
        def apply_body_upgrade(headers, *, panel, row):
            calls.append("body")
            return True, "GER40 min_body_ratio degismedi (0)"

    class _Trail:
        @staticmethod
        def apply_trail_upgrade(headers, *, panel, row):
            calls.append("trail_step")
            return True, "GER40 trail_step degismedi (2.2)"

        @staticmethod
        def apply_trail_start_upgrade(headers, *, panel, row):
            calls.append("trail_start")
            return True, "GER40 trail_start degismedi (1.5)"

    mods = {
        "session_exec": _Sess(),
        "msa_exec": _Msa(),
        "cost_rank_exec": _Cr(),
        "adx_exec": _Adx(),
        "atr_pct_exec": _Atr(),
        "body_exec": _Body(),
        "trail_exec": _Trail(),
    }

    def fake_get(path, headers):
        if path == "/api/state":
            return {"opt": {"busy": False}, "positions": []}
        return {"symbols": [row]}

    with patch("scripts.exec_gates.pipeline_frozen", return_value=False):
        with patch.object(loop, "_api_get", fake_get):
            with patch.object(loop, "_load_exec", lambda n, p: mods[n]):
                out = loop._run_charged_tunes({})
    assert calls == [
        "seans", "msa", "cr", "adx", "atr_pct", "body",
        "trail_step", "trail_start"]
    assert any("1/1 KEEP" in m for m in out)


def test_run_charged_tunes_respects_freeze():
    with patch("scripts.exec_gates.pipeline_frozen", return_value=True):
        out = loop._run_charged_tunes({})
    assert out == ["tune: exec pipeline FREEZE (Claude 03:36)"]
