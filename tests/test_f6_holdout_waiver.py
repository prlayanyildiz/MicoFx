"""F6 waiver: strong full-holdout overrides sub-window fragility gate.

Claude 03.09 charged_holdout analysis:
  XAUUSD +245R PF1.31 dd45 -> waiver (dd < 245/2 = 122.5)
  JPN225 +60R  PF1.35 dd23 -> waiver (dd < 60/2 = 30)
  NAS100 +57R  PF1.05 dd110 -> NO waiver (pf < 1.25 AND dd > 57/2 = 28.5)
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer, _f6_holdout_waiver


def _best(hold_net_r: float, hold_pf: float, hold_dd: float,
          pos_ratio: float = 0.5) -> dict:
    return {
        "score": 20.0,
        "positive_ratio": pos_ratio,
        "selection_positive_ratio": 1.0,
        "min_positive_ratio": 0.7,
        "holdout": {
            "net_r": hold_net_r,
            "trades": 250,
            "profit_factor": hold_pf,
            "expectancy": 0.2,
            "max_dd_r": hold_dd,
            "cost_per_trade_r": 0.05,
        },
        "validation": {
            "net_r": 10.0, "trades": 40, "profit_factor": 1.2,
            "expectancy": 0.2, "cost_per_trade_r": 0.02,
        },
        "selection": {"net_r": 50.0, "trades": 100, "profit_factor": 1.3,
                      "expectancy": 0.3},
    }


def _opt() -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._force_apply = False
    opt.store = MagicMock()
    from micofx.models import SymbolConfig, SystemConfig
    opt.store.system = SystemConfig(charge_costs=True)
    opt.store.opt_params.return_value = {"min_positive_ratio": 0.7}
    opt.store.symbols = {
        "TEST": SymbolConfig(symbol="TEST", magic=1, strategy="burst",
                             timeframe="M30"),
    }
    return opt


# -- waiver function unit tests --

def test_xauusd_waiver():
    """XAUUSD +245R PF1.31 dd45 -> waiver."""
    best = _best(245.0, 1.31, 45.0)
    assert _f6_holdout_waiver(best) is True


def test_jpn225_waiver():
    """JPN225 +60R PF1.35 dd23 -> waiver."""
    best = _best(60.0, 1.35, 23.0)
    assert _f6_holdout_waiver(best) is True


def test_nas100_no_waiver():
    """NAS100 +57R PF1.05 dd110 -> NO waiver (pf too low, dd too high)."""
    best = _best(57.0, 1.05, 110.0)
    assert _f6_holdout_waiver(best) is False


def test_dd_at_net_no_waiver():
    """dd equal to net_r -> no waiver (strict less-than)."""
    best = _best(60.0, 1.35, 60.0)
    assert _f6_holdout_waiver(best) is False


def test_weak_net_no_waiver():
    """net_r=30 below threshold -> no waiver even with good pf/dd."""
    best = _best(30.0, 1.40, 10.0)
    assert _f6_holdout_waiver(best) is False


def test_nas100_session_tight_waiver():
    """NAS100 15-21 M30/mtf +74R PF1.15 dd57 — walk-forward validated.

    Old waiver (PF>1.25 and dd<net/2) dropped it before naming a winner
    (21:26 keep_reason hicbir aday). 24h NAS (+57R PF1.05 dd110) still fails.
    """
    best = _best(73.91, 1.15, 57.7, pos_ratio=0.67)
    assert _f6_holdout_waiver(best) is True


def test_luck_concentrated_holdout_no_waiver():
    """Claude 21:36: net+PF can still be one lucky window. pr < 0.5 blocks."""
    best = _best(80.0, 1.40, 20.0, pos_ratio=0.33)
    assert _f6_holdout_waiver(best) is False


# -- integration: reject_reason honours waiver --

def test_reject_reason_waives_strong_holdout():
    """reject_reason must pass a fragile-ratio config with strong holdout."""
    opt = _opt()
    cfg = opt.store.symbols["TEST"]
    best = _best(245.0, 1.31, 45.0, pos_ratio=0.5)
    reason = opt.reject_reason(cfg, best, strategy="burst", timeframe="M30")
    # Must not be the fragility reason
    if reason:
        assert "kirilgan" not in reason


def test_reject_reason_still_blocks_weak_holdout():
    """reject_reason must still block NAS100-shaped fragile config.

    holdout PF must be >= MIN_OOS_PF (1.10) to reach the F6 gate at all;
    the real NAS100 issue is dd=110 ≈ 2x net with marginal PF.
    """
    opt = _opt()
    cfg = opt.store.symbols["TEST"]
    # PF 1.12 passes _slice_ok but fails F6 waiver (pf < 1.25, dd > net/2)
    best = _best(57.0, 1.12, 110.0, pos_ratio=0.5)
    reason = opt.reject_reason(cfg, best, strategy="burst", timeframe="M30")
    assert reason is not None
    assert "kirilgan" in reason
