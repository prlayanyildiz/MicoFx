"""The automatic size ran wider than the ceiling it advertises.

Three defects in one chain, found 31.08. They point in opposite directions,
which is why none of them showed up as an obviously wrong lot:

1. ``r_cap`` - the "auto 1R, max(risk_percent, 2%)" backstop - was multiplied
   by the same ``multiplier`` that already carries ``edge_scale`` (up to
   EDGE_MAX 2.2) and the supervisor's ``ai_scale``. A proven symbol's ceiling
   was therefore ~4.4% of balance, not 2%. A cap multiplied by the push it is
   supposed to bound is not a cap.

2. ``_margin_lot_ceiling`` splits the remaining book margin across "vacant
   enabled names" and never asked the supervisor. A quarantined symbol carries
   ``risk_scale = 0.0`` and cannot open, but it still reserved a full share of
   the kasa, so every real entry was sized at (vacant - quarantined) / vacant
   of its intended lot.

The ai_scale side of (1) is deliberately kept: it only ever throttles down, and
a throttle belongs inside a ceiling. Only the edge push is removed.

A third suspect - ``normalize_volume`` clamping **up** to ``volume_min`` after
the cap was applied - was chased and found unreachable on the account path, and
the last two tests here pin why: ``floor`` *is* ``volume_min``, and ``lot_for``
already refuses when the capped lot falls under ``floor``, so the clamp can
never raise a lot the caller accepted. No guard was added for it; a guard that
cannot fire is the thing this audit is removing elsewhere.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from micofx.models import SymbolConfig
from micofx.risk import RiskManager

BALANCE = 10000.0
SL_DIST = 10.0
ACCOUNT = {"equity": BALANCE, "margin_free": BALANCE, "margin": 0.0}


class _System:
    size_by_edge = True
    lot_multiplier = 1.0
    max_margin_usage_pct = 0.0
    min_free_margin = 0.0
    max_scalp_positions = 0
    max_swing_positions = 0
    max_positions = 0
    max_lot = 0.0
    daily_loss_pct = 0.0
    daily_profit_pct = 0.0
    max_concurrent_risk_pct = 0.0
    max_total_positions = 0


class _Store:
    def __init__(self, cfgs):
        self.symbols = {c.symbol: c for c in cfgs}
        self.system = _System()

    def get_setting(self, k, default=None):
        return default

    def set_setting(self, k, v):
        pass


class _Client:
    """One price unit per point; margin is 1.0 per 0.01 lot."""

    def info(self, symbol):
        return {"volume_min": 0.01, "volume_max": 100.0, "volume_step": 0.01,
                "point": 1.0, "tick_size": 1.0, "tick_value": 1.0,
                "filling_mode": 1, "digits": 2}

    def money_per_price_unit(self, symbol, volume):
        return 1.0 * float(volume)

    def min_stop_distance(self, symbol):
        return 0.0

    def resolve(self, symbol):
        return symbol

    def normalize_volume(self, symbol, lot):
        step = 0.01
        import math
        vol = math.floor(float(lot) / step + 1e-9) * step
        return round(max(0.01, min(100.0, vol)), 2)

    def tick(self, symbol):
        return None

    def margin_for(self, symbol, lot, side="buy"):
        return 100.0 * float(lot)


def _cfg(symbol, *, enabled=True, net_r=60.0, max_dd_r=10.0):
    c = SymbolConfig(symbol=symbol, magic=abs(hash(symbol)) % 1000 + 1,
                     timeframe="M15", strategy="stoch_flip")
    c.risk_percent = 1.0
    c.enabled = enabled
    # edge_scale is a ranking: it needs three enabled symbols carrying a
    # positive net_r/max_dd_r before it moves off 1.0 at all, and it needs
    # them to differ before the top one earns a push.
    c.opt_summary = {"holdout_days": 30.0, "validated": True,
                     "holdout": {"trades": 300, "net_r": net_r,
                                 "max_dd_r": max_dd_r, "expectancy": 0.2}}
    return c


def _book(n=3, **kw):
    """SYM0 is the strongest name in the book, so it is the one edge lifts."""
    strengths = [60.0, 12.0, 8.0]
    return [_cfg(f"SYM{i}", net_r=strengths[i % len(strengths)], **kw)
            for i in range(n)]


def _rm(cfgs):
    return RiskManager(_Store(cfgs), _Client())


def _risk_pct(lot):
    """What fraction of balance one R actually costs at this lot."""
    return lot * SL_DIST * 1.0 / BALANCE * 100.0


# --------------------------------------------------- 1) the edge-scaled cap

def test_the_r_cap_is_not_inflated_by_the_edge_push():
    cfgs = _book()
    rm = _rm(cfgs)
    edge = rm.edge_scale(cfgs[0])
    assert edge > 1.0, "fixture must actually earn an edge push"
    lot, note = rm.lot_for(cfgs[0], SL_DIST, BALANCE, account=ACCOUNT)
    assert _risk_pct(lot) <= RiskManager.AUTO_R_PCT + 1e-9, note


def test_the_cap_holds_at_the_maximum_edge():
    cfgs = _book()
    rm = _rm(cfgs)
    rm.edge_scale = lambda cfg: RiskManager.EDGE_MAX
    lot, note = rm.lot_for(cfgs[0], SL_DIST, BALANCE, account=ACCOUNT)
    assert _risk_pct(lot) <= RiskManager.AUTO_R_PCT + 1e-9, note


def test_a_supervisor_throttle_still_tightens_the_cap():
    """ai_scale only ever throttles down; a ceiling should honour that."""
    cfgs = _book()
    rm = _rm(cfgs)
    full, _ = rm.lot_for(cfgs[0], SL_DIST, BALANCE, account=ACCOUNT)
    half, _ = rm.lot_for(cfgs[0], SL_DIST, BALANCE, ai_scale=0.5, account=ACCOUNT)
    assert half < full


def test_a_higher_stored_risk_percent_still_wins():
    cfgs = _book()
    cfgs[0].risk_percent = 5.0
    rm = _rm(cfgs)
    lot, note = rm.lot_for(cfgs[0], SL_DIST, BALANCE, account=ACCOUNT)
    assert _risk_pct(lot) <= 5.0 + 1e-9, note
    assert _risk_pct(lot) > RiskManager.AUTO_R_PCT, note


# ------------------------------------------- 2) quarantine dilutes the book

def test_a_quarantined_name_does_not_reserve_a_share_of_the_kasa():
    cfgs = _book(3)
    rm = _rm(cfgs)
    before = rm._vacant_enabled_count([])
    rm.supervisor_blocked = lambda symbol: symbol == "SYM2"
    after = rm._vacant_enabled_count([])
    assert before == 3
    assert after == 2


def test_a_disabled_name_was_already_excluded():
    cfgs = _book(3)
    cfgs[2].enabled = False
    assert _rm(cfgs)._vacant_enabled_count([]) == 2


def test_the_count_never_falls_below_one():
    """Every name quarantined must not divide the budget by zero."""
    cfgs = _book(2)
    rm = _rm(cfgs)
    rm.supervisor_blocked = lambda symbol: True
    assert rm._vacant_enabled_count([]) >= 1


# ------------------------- the clamp-up that turned out to be unreachable

def test_a_minimum_lot_above_the_cap_skips_the_trade_rather_than_sizing_up():
    """This is why normalize_volume's clamp to volume_min cannot overshoot:
    a lot under the broker minimum never reaches it."""
    cfgs = _book()
    rm = _rm(cfgs)

    class _Wide(_Client):
        def info(self, symbol):
            i = super().info(symbol)
            # 4x the ~20-lot 1R cap — above concurrent hard ceiling (3.5x)
            # so unlock cannot fire even when kasa invents a live concurrent %.
            i["volume_min"] = 80.0
            return i

    rm.client = _Wide()
    lot, note = rm.lot_for(cfgs[0], SL_DIST, BALANCE, account=ACCOUNT)
    assert lot == 0.0, note
    assert "islem atlandi" in note


def test_the_normal_case_still_sizes_and_normalises():
    cfgs = _book()
    rm = _rm(cfgs)
    lot, note = rm.lot_for(cfgs[0], SL_DIST, BALANCE, account=ACCOUNT)
    assert lot > 0.0, note
    assert lot == round(lot, 2)


# --------------------------------------- the margin ceiling itself still binds

def test_the_margin_share_still_caps_a_thin_account():
    cfgs = _book(3)
    rm = _rm(cfgs)
    thin = {"equity": 300.0, "margin_free": 300.0, "margin": 0.0}
    lot, note = rm.lot_for(cfgs[0], SL_DIST, BALANCE, account=thin)
    # 300 free / 3 vacant names = 100 of margin, and margin_for is 100 per lot.
    assert lot <= 1.0 + 1e-9, note


def test_max_margin_usage_pct_still_bounds_the_budget():
    cfgs = _book(1)
    rm = _rm(cfgs)
    rm.store.system.max_margin_usage_pct = 10.0
    lot, note = rm.lot_for(cfgs[0], SL_DIST, BALANCE,
                           account={"equity": 10000.0, "margin_free": 10000.0,
                                    "margin": 0.0})
    # 10% of 10000 = 1000 of margin budget, 100 per lot -> 10 lots, but the
    # 2% R cap (200 / (10 * 1.0)) = 20 lots is looser, so margin binds.
    assert lot <= 10.0 + 1e-9, note


assert np is not None  # numpy import kept for parity with the sizing fixtures
