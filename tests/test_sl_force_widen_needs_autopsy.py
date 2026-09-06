"""Force SL widen needs autopsy premature evidence + charged non-regression.

Charged-alone still flattered 0.5 stops; autopsy-alone wants 1.0 and
collapses the stamp. Morning live patch: both, or WFO with the >=0.9 floor.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import (
    Optimizer,
    premature_sl_count_from_autopsy,
)


def _premature_rows(symbol: str, n: int) -> list[dict]:
    return [
        {
            "symbol": symbol,
            "after_1h_bars": 12,
            "after_1h_through_entry": True,
            "after_1h_recovery_r": 1.2,
            "exit_reason": "sl",
            "r_realised": -1.0,
        }
        for _ in range(n)
    ]


def _opt(cfg: SymbolConfig, measured: dict, autopsies=None) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = True
    store = MagicMock()
    store.symbols = {cfg.symbol: cfg}
    store.system = SystemConfig(charge_costs=True)
    store.opt_params.return_value = {"lookback_days": 180, "segments": 5}
    store.update_symbol = MagicMock(return_value=cfg)
    store.get_setting = MagicMock(return_value=autopsies if autopsies is not None else [])
    opt.store = store
    opt.client = MagicMock()
    opt.client.connected = True
    opt.client.positions.return_value = []
    opt.entry_lock = None
    opt._spread_scale = lambda sym: 1.0
    opt._holdout_costed = lambda *a, **k: dict(measured)
    return opt


def test_premature_sl_count_counts_through_entry_or_strong_recovery():
    rows = [
        {"symbol": "NAS100", "after_1h_bars": 8, "exit_reason": "sl",
         "after_1h_through_entry": True, "after_1h_recovery_r": 0.1},
        {"symbol": "NAS100", "after_1h_bars": 8, "exit_reason": "sl",
         "after_1h_through_entry": False, "after_1h_recovery_r": 0.9},
        {"symbol": "NAS100", "after_1h_bars": 8, "exit_reason": "sl",
         "after_1h_through_entry": False, "after_1h_recovery_r": 0.2},
        {"symbol": "XAUUSD", "after_1h_bars": 8, "exit_reason": "sl",
         "after_1h_through_entry": True, "after_1h_recovery_r": 2.0},
        {"symbol": "NAS100", "after_1h_bars": 0, "exit_reason": "sl",
         "after_1h_through_entry": True, "after_1h_recovery_r": 2.0},
        # Trail/flatten bounce must not inflate premature_n (US30 live 65>50 SL).
        {"symbol": "NAS100", "after_1h_bars": 8, "exit_reason": "trail",
         "after_1h_through_entry": True, "after_1h_recovery_r": 2.0},
        {"symbol": "NAS100", "after_1h_bars": 8, "exit_reason": "flatten",
         "after_1h_through_entry": False, "after_1h_recovery_r": 1.5},
        # Winning SL (BE/trail mislabel) is not a premature hard-stop death.
        {"symbol": "NAS100", "after_1h_bars": 8, "exit_reason": "sl",
         "r_realised": 1.0, "after_1h_through_entry": True,
         "after_1h_recovery_r": 2.0},
    ]
    assert premature_sl_count_from_autopsy(rows, "NAS100") == 2
    assert premature_sl_count_from_autopsy(rows, "XAUUSD") == 1
    assert premature_sl_count_from_autopsy(rows, "US30") == 0


def test_force_sl_widen_refuses_without_autopsy_even_if_charged_up():
    cfg = SymbolConfig(
        symbol="NAS100", magic=1, enabled=True,
        strategy="mtf_pullback", timeframe="M30",
        sl_atr_mult=0.5, trail_start_atr=0.3, trail_step_atr=2.5,
        blocked_entry_hours=[],
        opt_summary={"holdout": {"net_r": 100.0, "trades": 700, "score": 60.0},
                     "holdout_days": 500.0, "validated": True},
    )
    opt = _opt(cfg, {
        "trades": 500, "net_r": 105.0, "expectancy": 0.21, "score": 62.0,
        "profit_factor": 1.2, "cost_per_trade_r": 0.03, "cost_r": 15.0,
        "wins": 200, "losses": 300, "win_rate": 40.0, "max_dd_r": 40.0,
        "capture": 0.1, "exits": {}, "holdout_days": 500.0,
    }, autopsies=[])
    res = opt.apply(
        "NAS100", {"sl_atr_mult": 1.0},
        score=0.0, detail=None, timeframe="M30", strategy="mtf_pullback",
    )
    assert res.get("ok") is False
    assert "otopsi" in (res.get("error") or "").lower()
    opt.store.update_symbol.assert_not_called()


def test_force_sl_widen_lands_with_autopsy_and_charged_up():
    cfg = SymbolConfig(
        symbol="GER40", magic=1, enabled=True,
        strategy="channel_break", timeframe="M30",
        sl_atr_mult=1.0, trail_start_atr=1.5, trail_step_atr=2.2,
        adx_min=0.0, blocked_entry_hours=[],
        opt_summary={"holdout": {"net_r": 71.0, "trades": 400, "score": 55.0},
                     "holdout_days": 500.0, "validated": True},
    )
    opt = _opt(cfg, {
        "trades": 374, "net_r": 72.8, "expectancy": 0.19, "score": 58.0,
        "profit_factor": 1.34, "cost_per_trade_r": 0.03, "cost_r": 11.0,
        "wins": 140, "losses": 234, "win_rate": 37.0, "max_dd_r": 18.0,
        "capture": 0.1, "exits": {}, "holdout_days": 500.0,
    }, autopsies=_premature_rows("GER40", 5))
    res = opt.apply(
        "GER40", {"sl_atr_mult": 1.5, "adx_min": 15.0},
        score=0.0, detail=None, timeframe="M30", strategy="channel_break",
    )
    assert res.get("ok") is True, res


def test_force_sl_widen_waives_last_seg_when_upgrade_robust(monkeypatch):
    """Claude 04.50 XAU: last-seg drop OK if premature + 6-slice gate pass."""
    from unittest.mock import patch

    cfg = SymbolConfig(
        symbol="XAUUSD", magic=1, enabled=True,
        strategy="mtf_pullback", timeframe="M15",
        sl_atr_mult=0.5, trail_start_atr=0.3, trail_step_atr=2.5,
        blocked_entry_hours=[],
        opt_summary={"holdout": {"net_r": 272.0, "trades": 1000, "score": 200.0},
                     "holdout_days": 500.0, "validated": True},
    )
    opt = _opt(cfg, {
        "trades": 900, "net_r": 239.0, "expectancy": 0.26, "score": 180.0,
        "profit_factor": 1.4, "cost_per_trade_r": 0.03, "cost_r": 20.0,
        "wins": 300, "losses": 600, "win_rate": 33.0, "max_dd_r": 40.0,
        "capture": 0.1, "exits": {}, "holdout_days": 500.0,
    }, autopsies=_premature_rows("XAUUSD", 11))
    live_nets = [10.0, 20.0, 30.0, 40.0, 50.0, 250.0]
    chal_nets = [12.0, 22.0, 32.0, 42.0, 55.0, 308.0]  # +71 full, same wins

    def fake_slices(row, field=None, value=None, parts=6):
        if field == "sl_atr_mult":
            return chal_nets
        return live_nets

    with patch("scripts.exec_gates.charged_slice_nets", side_effect=fake_slices):
        with patch("scripts.exec_gates.upgrade_robust", return_value=True) as up:
            res = opt.apply(
                "XAUUSD", {"sl_atr_mult": 0.7},
                score=0.0, detail=None, timeframe="M15", strategy="mtf_pullback",
            )
    assert res.get("ok") is True, res
    assert up.called


def test_force_sl_widen_still_refuses_last_seg_without_robust(monkeypatch):
    from unittest.mock import patch

    cfg = SymbolConfig(
        symbol="XAUUSD", magic=1, enabled=True,
        strategy="mtf_pullback", timeframe="M15",
        sl_atr_mult=0.5, trail_start_atr=0.3, trail_step_atr=2.5,
        blocked_entry_hours=[],
        opt_summary={"holdout": {"net_r": 272.0, "trades": 1000, "score": 200.0},
                     "holdout_days": 500.0, "validated": True},
    )
    opt = _opt(cfg, {
        "trades": 800, "net_r": 141.0, "expectancy": 0.18, "score": 100.0,
        "profit_factor": 1.2, "cost_per_trade_r": 0.03, "cost_r": 20.0,
        "wins": 250, "losses": 550, "win_rate": 31.0, "max_dd_r": 50.0,
        "capture": 0.1, "exits": {}, "holdout_days": 500.0,
    }, autopsies=_premature_rows("XAUUSD", 11))
    with patch("scripts.exec_gates.upgrade_robust", return_value=False):
        res = opt.apply(
            "XAUUSD", {"sl_atr_mult": 1.0},
            score=0.0, detail=None, timeframe="M15", strategy="mtf_pullback",
        )
    assert res.get("ok") is False
    assert "geriledi" in (res.get("error") or "")
