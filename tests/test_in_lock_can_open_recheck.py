"""In-lock can_open recheck before order_send (parallel-audit HIGH #1).

Outer can_open runs before entry_lock. A deferred fill on another symbol (or
same-magic late book) can land in the gap; without a fresh positions + can_open
under the lock we can breach max_positions / concurrent / scale-in spacing.
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig
from micofx.risk import Verdict


class _Client:
    def __init__(self):
        self.open_market_calls = 0
        self.connected = True
        self._book: list[dict] = []

    def min_stop_distance(self, symbol):
        return 0.0001

    def tick(self, symbol):
        return {"ask": 18000.5, "bid": 18000.0, "spread": 0.5}

    def server_now(self):
        import time
        return time.time()

    def open_market(self, *a, **k):
        self.open_market_calls += 1
        return {"ok": False, "error": "should not send"}

    def positions(self):
        return list(self._book)

    def info(self, symbol):
        return {"point": 0.0001}

    def money_per_price_unit(self, symbol, volume):
        return 1.0

    def account(self):
        return {"balance": 2000.0, "equity": 2000.0, "margin_free": 1800.0,
                "margin": 0.0, "login": 1, "server": "demo"}


class _Risk:
    def __init__(self):
        self.calls = 0
        self.position_counts: list[int] = []

    def lot_for(self, cfg, sl_distance, balance, ai_scale=1.0, **_):
        return 0.1, "ok"

    def can_open(self, cfg, side, lot, positions, account, sec_tickets=frozenset(),
                 **_kw):
        self.calls += 1
        self.position_counts.append(len(positions or []))
        # First call (outside lock) allows; second (inside) sees the late ticket.
        if self.calls >= 2 and positions:
            return Verdict(False, "max pozisyon (test)")
        return Verdict(ok=True)


class _Supervisor:
    def gate(self, cfg, server_now):
        return True, "", 1.0


def _engine(client, cfg, risk):
    store = SimpleNamespace(
        system=SimpleNamespace(
            slippage_points=5, block_high_cost=False,
            max_cost_pct_of_risk=0.0, trade_all_hours=True,
            daily_loss_flatten=False, day_end_flatten_min=0,
        ),
        symbols={cfg.symbol: cfg},
        settings={},
    )
    store.opt_params = lambda: {}
    store.set_setting = lambda k, v: store.settings.__setitem__(k, v)
    store.get_setting = lambda k, d=None: store.settings.get(k, d)

    eng = object.__new__(Engine)
    eng.store = store
    eng.client = client
    eng.risk = risk
    eng.supervisor = _Supervisor()
    eng.execution = SimpleNamespace(record=lambda *a, **k: None)
    eng.entry_lock = threading.Lock()
    eng._positions = []
    eng._sec_tickets = set()
    eng._sec_cfgs = {}
    eng._orphan_tickets = set()
    eng._orphan_scan = {}
    eng._link_backoff = {}
    eng._unfilled_probe = {}
    eng.states = {}
    eng._cooldowns = {}
    eng._trade_autopsies = []
    eng._spread_ratio = {}
    eng._account = {"balance": 2000.0, "equity": 2000.0, "margin_free": 1800.0}
    eng._account_at = 0.0
    eng._mark_bar_filled = lambda *a, **k: None
    eng._save_cooldown = lambda *a, **k: None
    eng._broker_now_int = lambda: 0
    # The account lock is gone (operator 10.09); refresh_account now only
    # logs which account is attached, and needs nothing stubbed.
    eng._attached_account = None
    return eng


def test_in_lock_can_open_recheck_aborts_after_late_fill():
    cfg = SymbolConfig(
        symbol="GER40", group="index", magic=42,
        strategy="channel_break", timeframe="M30",
        sl_atr_mult=1.5, trail_start_atr=0.8, trail_step_atr=1.0,
        max_spread_atr=0.0, chase_max_atr=0.0,
    )
    client = _Client()
    # Book empty for outer gate; under lock reload sees a same-magic ticket.
    risk = _Risk()

    def _reload():
        client._book = [{
            "ticket": 99, "magic": 42, "symbol": "GER40",
            "volume": 0.7, "price_open": 1.1, "sl": 1.0, "tp": 0.0,
            "type": 0, "profit": 0.0, "swap": 0.0, "side": "buy",
        }]
        return Engine._reload_positions(eng)

    eng = _engine(client, cfg, risk)
    eng._reload_positions = _reload

    state = SymbolState(cfg.symbol)
    state.signal = "buy"
    state.signal_source = "primary"
    state.atr = 0.01
    state.last_bar = 1

    eng._try_entry(cfg, state, account=dict(eng._account))
    assert client.open_market_calls == 0
    assert risk.calls >= 2
    assert risk.position_counts[-1] >= 1
    assert state.entry_block  # risk key from verdict
    assert "pozisyon" in (state.note or "").lower() or state.entry_block
