"""Account risk% sizes the book. Per-symbol lot/slot caps are gone.

Operator 27.08: max_lot, max_positions, fixed lot and the risk% dial leave
the panel and the HTTP door. lot_for still reads stored risk_percent against
balance. Leftover total slot cap is unread. Operator 28.08: same-side stack
on one symbol is the unvalidated 13.08 book (four NAS 0.1). Live is one
ticket per symbol, matching search max_open=1. Leftover max_positions stays
unread so a DB 5/10 cannot return. Min-lot pin may use the 3x overshoot
headroom when an account picture is present — not a second ticket.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_delete_guard import _cfg, _client
from test_hands_off_fields_are_not_api_writable import _client as _hands_off_client

from micofx import backtest as bt
from micofx.models import SymbolConfig, SystemConfig
from micofx.risk import RiskManager

ROOT = Path(__file__).resolve().parents[1]
APP_JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (ROOT / "micofx" / "web" / "templates" / "index.html").read_text(encoding="utf-8")

GONE = ("lot_mode", "fixed_lot", "max_lot", "max_positions", "symbol_daily_loss_pct",
        "risk_percent")


class _LotClient:
    def info(self, symbol):
        return {"volume_min": 0.1, "volume_max": 100.0, "volume_step": 0.1}

    def money_per_price_unit(self, symbol, lot):
        return 10.0

    def min_stop_distance(self, symbol):
        return 0.0

    def normalize_volume(self, symbol, lot):
        return round(lot, 2)

    def resolve(self, symbol):
        return symbol

    def margin_for(self, symbol, lot, side):
        return 1.0

    def tick(self, symbol):
        return None


class _LinearMarginClient(_LotClient):
    """$100 margin per 1.0 lot, linear. leftover max_lot must not win."""

    def margin_for(self, symbol, lot, side):
        return 100.0 * float(lot)


class _LotStore:
    def __init__(self, cfg: SymbolConfig) -> None:
        self.symbols = {cfg.symbol: cfg}
        self.system = SystemConfig(
            size_by_edge=False, lot_multiplier=1.0,
            max_total_positions=20, max_scalp_positions=0, max_swing_positions=0,
            min_free_margin=0.0, max_margin_usage_pct=0.0,
            max_concurrent_risk_pct=8.0,
        )

    def get_setting(self, key, default=None):
        return default

    def set_setting(self, key, value):
        pass


def _risk(cfg: SymbolConfig) -> RiskManager:
    rm = RiskManager.__new__(RiskManager)
    rm.store = _LotStore(cfg)
    rm.client = _LotClient()
    return rm


def test_position_card_does_not_offer_sizing_dials():
    assert "const POSITION_SECTION" not in APP_JS
    assert "Pozisyon Boyutu" not in APP_JS
    for k in GONE:
        assert f'k: "{k}"' not in APP_JS, f"{k} still on the symbol card"


def test_panel_and_html_do_not_offer_the_removed_dials():
    assert "Sembol Basi Islem Limiti" not in HTML
    assert "btn-maxpos-bulk" not in HTML
    assert "sys-symbol-limits" not in HTML
    assert "data-lotmode-bulk" not in HTML
    assert "btn-lotmode-check" not in HTML
    assert "portfolio-minlot" not in HTML
    assert 'data-help="th.cap.Limit"' not in HTML
    assert "renderSymbolLimits" not in APP_JS
    assert "Hepsini Sabit Yap" not in HTML
    assert "Hepsini Risk% Yap" not in HTML


def test_http_refuses_the_removed_symbol_dials():
    tc, store, _ = _hands_off_client()
    before = store.symbols["XAUUSD"]
    for key, value in (
        ("max_lot", 5.0),
        ("max_positions", 3),
        ("lot_mode", "fixed"),
        ("fixed_lot", 0.5),
        ("risk_percent", 1.5),
    ):
        res = tc.post("/api/symbols/XAUUSD", json={key: value})
        assert res.status_code == 400, (key, res.text)
        assert getattr(store.symbols["XAUUSD"], key) == getattr(before, key)


def test_http_refuses_symbol_daily_loss():
    tc, store, _ = _hands_off_client()
    before = store.symbols["XAUUSD"].symbol_daily_loss_pct
    res = tc.post("/api/symbols/XAUUSD", json={"symbol_daily_loss_pct": 5.0})
    assert res.status_code == 400, res.text
    assert store.symbols["XAUUSD"].symbol_daily_loss_pct == before


def test_lot_for_uses_risk_percent_even_when_the_row_says_fixed():
    """Leftover lot_mode=fixed must not pin a constant lot."""
    cfg = SymbolConfig(
        symbol="XAUUSD", magic=1, lot_mode="fixed", fixed_lot=0.01,
        risk_percent=1.0, max_lot=0.01,
    )
    # 10_000 * 1% / (1.0 * 10) = 10 lots, well above leftover max_lot 0.01
    lot, note = _risk(cfg).lot_for(cfg, sl_distance=1.0, balance=10_000.0)
    assert lot == pytest.approx(10.0)
    assert "sabit" not in note
    assert "risk" in note


def test_lot_for_ignores_leftover_max_lot():
    cfg = SymbolConfig(
        symbol="XAUUSD", magic=1, lot_mode="risk", risk_percent=1.0, max_lot=0.2,
    )
    lot, _ = _risk(cfg).lot_for(cfg, sl_distance=1.0, balance=10_000.0)
    assert lot > 0.2


def test_lot_for_caps_to_remaining_margin_like_positions():
    """Operator: lot ceiling auto, same remaining-margin budget as free_slots.

    leftover max_lot=0.2 must not bind. Risk% wants 10 lots; 90% of $1000
    at $100/lot leaves 9.0.
    """
    cfg = SymbolConfig(
        symbol="XAUUSD", magic=1, lot_mode="risk", risk_percent=1.0, max_lot=0.2,
    )
    store = _LotStore(cfg)
    store.system.max_margin_usage_pct = 90.0
    store.system.min_free_margin = 0.0
    risk = RiskManager.__new__(RiskManager)
    risk.store = store
    risk.client = _LinearMarginClient()
    account = {"equity": 1000.0, "margin": 0.0, "margin_free": 1000.0}
    lot, note = risk.lot_for(
        cfg, sl_distance=1.0, balance=10_000.0, account=account)
    assert lot == pytest.approx(9.0)
    assert lot > 0.2
    assert "marj" in note


def test_lot_for_skips_when_margin_ceiling_is_below_broker_min():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, risk_percent=1.0, max_lot=5.0)
    store = _LotStore(cfg)
    store.system.max_margin_usage_pct = 90.0
    store.system.min_free_margin = 0.0
    risk = RiskManager.__new__(RiskManager)
    risk.store = store
    risk.client = _LinearMarginClient()
    # 90% of $8 = $7.20; 0.1 min lot costs $10 → skip, do not send min lot
    account = {"equity": 8.0, "margin": 0.0, "margin_free": 8.0}
    lot, note = risk.lot_for(
        cfg, sl_distance=1.0, balance=10_000.0, account=account)
    assert lot == 0.0
    assert "atlandi" in note


def test_lot_for_uses_overshoot_headroom_when_account_is_present():
    """Min-lot pin with a live account uses the 3x skip bound as size.

    Without account, 0.05 raw still floors to 0.1 (test_core / zero_guard).
    Live NAS 28.08 was four 0.1 tickets of that pin; one ticket at 0.15 is
    the headroom the skip already allowed, not a second hand.
    """
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, risk_percent=0.5, max_lot=0.1)
    store = _LotStore(cfg)
    store.system.max_margin_usage_pct = 90.0
    store.system.min_free_margin = 0.0
    risk = RiskManager.__new__(RiskManager)
    risk.store = store
    risk.client = _LinearMarginClient()
    # 100 * 0.5% / (1 * 10) = 0.05 raw; floor 0.1; 3x headroom 0.15
    account = {"equity": 1000.0, "margin": 0.0, "margin_free": 1000.0}
    lot, note = risk.lot_for(
        cfg, sl_distance=1.0, balance=100.0, account=account)
    assert lot == pytest.approx(0.15)
    assert lot > 0.1
    assert "taban" in note


def test_lot_for_does_not_zero_size_when_account_picture_is_missing():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, risk_percent=1.0, max_lot=0.2)
    lot, _ = _risk(cfg).lot_for(
        cfg, sl_distance=1.0, balance=10_000.0,
        account={"equity": 0.0, "margin": 0.0, "margin_free": 0.0})
    assert lot > 0.2


def test_lot_for_without_a_stop_skips_instead_of_using_fixed_lot():
    cfg = SymbolConfig(
        symbol="XAUUSD", magic=1, lot_mode="fixed", fixed_lot=1.0, risk_percent=0.5,
    )
    lot, note = _risk(cfg).lot_for(cfg, sl_distance=0.0, balance=10_000.0)
    assert lot == 0.0
    assert "atlandi" in note


def test_can_open_refuses_a_second_same_side_ticket():
    """One idea, one ticket. Leftover max_positions=10 must not stack."""
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=10)
    store = _LotStore(cfg)
    risk = RiskManager.__new__(RiskManager)
    risk.store = store
    risk.client = _LotClient()
    existing = [{"ticket": 100, "symbol": "XAUUSD", "magic": 1, "side": "buy"}]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 0.0}
    blocked = risk.can_open(cfg, "buy", 0.1, existing, account)
    assert not blocked.ok
    assert "sembol pozisyon limiti" in blocked.reason


def test_can_open_ignores_leftover_total_slot_cap():
    """Book-wide leftover max_total_positions is unread; another *name* may open."""
    cfg = SymbolConfig(symbol="XAUUSD", magic=1)
    other = SymbolConfig(symbol="GER40", magic=2)
    store = _LotStore(cfg)
    store.symbols[other.symbol] = other
    store.system.max_total_positions = 1
    risk = RiskManager.__new__(RiskManager)
    risk.store = store
    risk.client = _LotClient()
    existing = [{"ticket": 100, "symbol": "GER40", "magic": 2, "side": "buy"}]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 0.0}
    allowed = risk.can_open(cfg, "buy", 0.1, existing, account)
    assert allowed.ok, allowed.reason
    assert "toplam" not in (allowed.reason or "")


def test_can_open_still_refuses_a_hedge():
    cfg = SymbolConfig(symbol="XAUUSD", magic=1, max_positions=10)
    store = _LotStore(cfg)
    risk = RiskManager.__new__(RiskManager)
    risk.store = store
    risk.client = _LotClient()
    existing = [{"ticket": 100, "symbol": "XAUUSD", "magic": 1, "side": "buy"}]
    account = {"equity": 10_000.0, "margin_free": 10_000.0, "margin": 0.0}
    blocked = risk.can_open(cfg, "sell", 0.1, existing, account)
    assert not blocked.ok
    assert "ters yonde" in blocked.reason


def test_search_does_not_read_leftover_max_positions():
    fat = SymbolConfig(symbol="X", magic=1, max_positions=9)
    assert bt.max_open_from_cfg(fat) == 1
    assert bt.max_open_from_cfg(SymbolConfig(symbol="X", magic=1)) == 1


def test_bulk_also_refuses_the_removed_dials():
    cfg = _cfg("XAUUSD", magic=990021)
    tc, store = _client({"XAUUSD": cfg}, [])
    res = tc.post("/api/symbols-bulk", json={"patch": {"max_positions": 3}})
    assert res.status_code == 400
    assert store.symbols["XAUUSD"].max_positions == 1
    res = tc.post("/api/symbols-bulk", json={"patch": {"lot_mode": "fixed"}})
    assert res.status_code == 400
