"""Spread gate vs autopsy: stamp the send tick, re-check before order_send.

Claude 03.09 night: autopsy spread_atr often sits ABOVE max_spread_atr on
losing US30/JPN225 fills (-38.8R in the >0.04 bucket). Two causes:

1. Autopsy read ``state.spread_atr`` from evaluate-time tick while the gate
   used a later, tighter tick — looks like a leak, is cosmetic.
2. Spread widens between the gate tick and order_send — real leak.

Fix: overwrite ``state.spread_atr`` from the live tick (cost), and re-fetch
before open_market. Gate yardstick is the forming BAR when available
(Claude EK34 / SpotBrent miss) so walk-forward and live agree.
"""
from __future__ import annotations

import threading
from types import SimpleNamespace

import numpy as np

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig
from micofx.risk import Verdict


class _SeqClient:
    def __init__(self, spreads: list[float], *, fill_ticket: int | None = 501):
        self._spreads = list(spreads)
        self._i = 0
        self.open_market_calls = 0
        self.connected = True
        self._fill_ticket = fill_ticket
        self._positions_after: list[dict] = []

    def min_stop_distance(self, symbol):
        return 0.0001

    def tick(self, symbol):
        if self._i < len(self._spreads):
            spread = self._spreads[self._i]
            self._i += 1
        else:
            spread = self._spreads[-1]
        mid = 1.1000
        half = spread / 2.0
        return {"ask": mid + half, "bid": mid - half, "spread": spread}

    def server_now(self):
        import time
        return time.time()

    def open_market(self, symbol, side, lot, sl, tp, magic, slippage=0,
                    comment="", defer_verify=False):
        self.open_market_calls += 1
        ticket = self._fill_ticket
        if ticket:
            self._positions_after = [{
                "ticket": ticket, "magic": magic, "symbol": symbol,
                "volume": lot, "price_open": 1.1000, "sl": sl, "tp": tp,
                "type": 0, "profit": 0.0, "swap": 0.0,
            }]
        return {
            "ok": True, "position": ticket, "requested": 1.1000,
            "price": 1.1000, "volume": lot, "sl": sl, "tp": tp,
            "partial_fill": False, "sl_tp_reanchored": True,
        }

    def positions(self):
        return list(self._positions_after)

    def info(self, symbol):
        return {"point": 0.0001}

    def money_per_price_unit(self, symbol, volume):
        return 1.0


class _Risk:
    def lot_for(self, cfg, sl_distance, balance, ai_scale=1.0, **_):
        return 0.1, "ok"

    def can_open(self, cfg, side, lot, positions, account, sec_tickets=frozenset(),
                 **_kw):
        return Verdict(ok=True)


class _Supervisor:
    def gate(self, cfg, server_now):
        return True, "", 1.0


class _Execution:
    def record(self, *a, **kw):
        pass


def _engine(client, cfg):
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
    eng.risk = _Risk()
    eng.supervisor = _Supervisor()
    eng.execution = _Execution()
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
    eng._reload_positions = lambda: True
    eng._mark_bar_filled = lambda *a, **k: None
    eng._save_cooldown = lambda *a, **k: None
    eng._broker_now_int = lambda: 0
    return eng


def _cfg(**kw):
    base = {
        "symbol": "US30", "group": "crypto", "magic": 1,
        "strategy": "channel_break", "timeframe": "M30",
        "sl_atr_mult": 2.0, "trail_start_atr": 0.5,
        "trail_step_atr": 2.0, "max_spread_atr": 0.08,
    }
    base.update(kw)
    return SymbolConfig(**base)


def _state(cfg, *, atr=100.0, stale_spread_atr=0.12):
    st = SymbolState(cfg.symbol)
    st.signal = "buy"
    st.signal_source = "primary"
    st.atr = atr
    st.spread_atr = stale_spread_atr
    st.last_bar = 1
    return st


def test_pre_send_spread_recheck_aborts_when_tick_widens():
    """No bars → tick path: gate under, send over → no order_send."""
    atr = 0.001
    msa = 0.08
    client = _SeqClient([0.05 * atr, 0.12 * atr], fill_ticket=None)
    cfg = _cfg(max_spread_atr=msa, sl_atr_mult=2.0)
    eng = _engine(client, cfg)
    state = _state(cfg, atr=atr, stale_spread_atr=0.05)
    eng._try_entry(cfg, state, account={"balance": 1000.0})
    assert client.open_market_calls == 0
    assert state.entry_block == "spread"
    assert "genis" in state.note or "spread" in state.note.lower()


def test_gate_tick_overwrites_stale_evaluate_spread_atr():
    """Cost stamp is the live tick even when evaluate-time was wider."""
    atr = 0.001
    msa = 0.08
    gate_spread = 0.05 * atr
    client = _SeqClient([gate_spread, gate_spread], fill_ticket=501)
    cfg = _cfg(max_spread_atr=msa, sl_atr_mult=2.0)
    eng = _engine(client, cfg)

    def _reload():
        eng._positions = list(client.positions())
        return True

    eng._reload_positions = _reload
    state = _state(cfg, atr=atr, stale_spread_atr=0.12)
    eng._try_entry(cfg, state, account={"balance": 1000.0})
    assert client.open_market_calls == 1
    assert abs(state.spread_atr - 0.05) < 1e-9


def test_tick_over_cap_bar_under_allows_fill():
    """Claude EK34: tick breaches msa but forming bar is under → fill."""
    atr = 0.001
    msa = 0.08
    point = 0.0001
    tick_wide = 0.20 * atr
    bar_ok = 0.05 * atr
    client = _SeqClient([tick_wide, tick_wide], fill_ticket=502)
    cfg = _cfg(max_spread_atr=msa, sl_atr_mult=2.0)
    eng = _engine(client, cfg)

    def _reload():
        eng._positions = list(client.positions())
        return True

    eng._reload_positions = _reload
    state = _state(cfg, atr=atr, stale_spread_atr=0.20)
    state.bars = SimpleNamespace(
        spread=np.array([bar_ok / point]),
        close=np.array([1.1]),
    )
    eng._try_entry(cfg, state, account={"balance": 1000.0})
    assert client.open_market_calls == 1, f"{state.entry_block} {state.note}"
    assert state.entry_block != "spread"
    assert abs(state.spread_atr - 0.20) < 1e-9


def test_bar_over_cap_blocks_even_if_tick_tight():
    atr = 0.001
    msa = 0.08
    point = 0.0001
    tick_ok = 0.04 * atr
    bar_wide = 0.20 * atr
    client = _SeqClient([tick_ok, tick_ok], fill_ticket=None)
    cfg = _cfg(max_spread_atr=msa, sl_atr_mult=2.0)
    eng = _engine(client, cfg)
    state = _state(cfg, atr=atr)
    state.bars = SimpleNamespace(spread=np.array([bar_wide / point]))
    eng._try_entry(cfg, state, account={"balance": 1000.0})
    assert client.open_market_calls == 0
    assert state.entry_block == "spread"


def test_bar_under_raw_but_scale_pushes_over_cap():
    """Claude 06.09: live bar gate must apply _spread_scale like replay."""
    atr = 0.001
    msa = 0.08
    point = 0.0001
    tick_ok = 0.04 * atr
    # raw bar 0.07xATR under cap; *1.25 → 0.0875xATR over
    bar_raw = 0.07 * atr
    client = _SeqClient([tick_ok, tick_ok], fill_ticket=None)
    cfg = _cfg(max_spread_atr=msa, sl_atr_mult=2.0)
    eng = _engine(client, cfg)
    # Force scale=1.25 via enough fake histogram buckets
    from micofx.engine import SPREAD_RATIO_BUCKETS
    # Bucket centres: idx 12 → (12+0.5)*0.1 = 1.25
    counts = [0] * SPREAD_RATIO_BUCKETS
    counts[12] = 500
    eng._spread_ratio = {cfg.symbol: counts}
    state = _state(cfg, atr=atr)
    state.bars = SimpleNamespace(spread=np.array([bar_raw / point]))
    eng._try_entry(cfg, state, account={"balance": 1000.0})
    assert client.open_market_calls == 0
    assert state.entry_block == "spread"
