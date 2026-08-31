"""The book-wide 1R ceiling refuses an entry again (operator 31.08).

The 30% ceiling was switched off 27.08 because lot was risk% of balance and
the book could not reach it. Measured 31.08: the live account runs 2.88% margin
against a 90% allowance because ``lot_for`` resolves to
``min(margin share, auto 1R cap)`` and the 2% 1R cap binds first - so raising
that cap is the only way to use the margin, and it removes the very thing that
made the ceiling unreachable. The operator re-armed the ceiling as the backstop
before any scaling.

Inert at today's sizing (book-wide 1R is ~17% of equity against a live 30 cap);
it only bites once size is raised. ``remaining_position_risk`` measures to the
*current* SL, so a trailed ticket frees budget, and a naked ticket is already
refused above this gate so the sum here can never be inf.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.risk import RiskManager


class _Store:
    def __init__(self) -> None:
        self.system = SystemConfig(
            max_total_positions=20,
            max_scalp_positions=0,
            max_swing_positions=0,
            min_free_margin=0.0,
            max_margin_usage_pct=0.0,
        )
        self.system.max_concurrent_risk_pct = 30.0
        self.symbols = {
            "XAUUSD": SymbolConfig(symbol="XAUUSD", magic=1, max_positions=10),
            "GER40": SymbolConfig(symbol="GER40", magic=2, max_positions=10),
        }

    def get_setting(self, key, default=None):
        return default

    def set_setting(self, key, value):
        pass


class _Client:
    def resolve(self, symbol):
        return symbol

    def margin_for(self, symbol, lot, side):
        return 1.0

    def money_per_price_unit(self, symbol, lot):
        return float(lot)


def _pos(sl: float, entry: float = 2000.0, volume: float = 1.0,
         side: str = "buy") -> dict:
    return {
        "ticket": 1, "symbol": "XAUUSD", "magic": 1, "side": side,
        "volume": volume, "price_open": entry, "sl": sl,
    }


def _account(equity: float = 1000.0) -> dict:
    return {"equity": equity, "margin_free": 10_000.0, "margin": 0.0}


def test_an_entry_over_the_ceiling_is_refused():
    """25% already open plus a 10% fill is past a 30 cap."""
    risk = RiskManager(_Store(), _Client())
    cfg = risk.store.symbols["GER40"]
    open_now = [_pos(sl=1750.0)]          # 250 of 1000 equity = 25%

    blocked = risk.can_open(cfg, "buy", 1.0, open_now, _account(),
                            sl_distance=100.0)

    assert not blocked.ok
    assert "eszamanli" in blocked.reason


def test_todays_sizing_still_opens():
    """The cap must be inert where the book actually sits, not a blanket no."""
    risk = RiskManager(_Store(), _Client())
    cfg = risk.store.symbols["GER40"]
    open_now = [_pos(sl=1900.0)]          # 100 of 1000 equity = 10%

    allowed = risk.can_open(cfg, "buy", 1.0, open_now, _account(),
                            sl_distance=100.0)

    assert allowed.ok, allowed.reason


def test_zero_still_disables_the_ceiling():
    """0 is documented as off - it must not read as "no risk allowed"."""
    store = _Store()
    store.system.max_concurrent_risk_pct = 0.0
    risk = RiskManager(store, _Client())
    cfg = store.symbols["GER40"]
    open_now = [_pos(sl=1000.0)]

    assert risk.can_open(cfg, "buy", 1.0, open_now, _account(),
                         sl_distance=500.0).ok


def test_a_trailed_ticket_frees_budget():
    """Risk to the live SL: a stop at entry is not still 1R against the cap."""
    risk = RiskManager(_Store(), _Client())
    cfg = risk.store.symbols["GER40"]
    open_now = [_pos(sl=2000.0)]          # trailed to entry, 0 remaining

    allowed = risk.can_open(cfg, "buy", 1.0, open_now, _account(),
                            sl_distance=250.0)

    assert allowed.ok, allowed.reason


def test_the_open_book_alone_can_close_the_door():
    """An unmeasurable new fill still cannot ignore what is already at risk."""
    risk = RiskManager(_Store(), _Client())
    cfg = risk.store.symbols["GER40"]
    open_now = [_pos(sl=1650.0)]          # 350 of 1000 equity = 35% > 30

    blocked = risk.can_open(cfg, "buy", 1.0, open_now, _account(),
                            sl_distance=0.0)

    assert not blocked.ok
    assert "eszamanli" in blocked.reason
