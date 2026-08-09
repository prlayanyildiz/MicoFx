"""Optimizer.apply() (the PRIMARY apply path) must treat a still-open
orphan-scan window the same way it already treats a live position (M1) - the
zero-candidate fill is genuinely invisible to client.positions() (that is the
entire reason the scan exists), so without this the family-swap block and the
exit/risk holdback both silently no-op for a magic that may still turn out to
have an open position.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self, cfg, orphan_scan=None):
        self._cfg = cfg
        self.symbols = {"XAUUSD": cfg}
        self._orphan_scan = orphan_scan or {}
        self.updated_with = None

    def get_setting(self, key, default=None):
        if key == "secondary_orphan_scan":
            return self._orphan_scan
        return default

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch):
        self.updated_with = patch
        for k, v in patch.items():
            if v is not None:
                setattr(self._cfg, k, v)
        return self._cfg


class _Client:
    connected = True

    def __init__(self, positions):
        self._positions = positions

    def positions(self, magic=None, symbol=None):
        return [p for p in self._positions if magic is None or p["magic"] == magic]


def _cfg():
    return SymbolConfig(symbol="XAUUSD", magic=1, strategy="t3_stoch", timeframe="M15",
                        sl_atr_mult=1.0, tp_atr_mult=2.0)


def test_apply_holds_back_exit_fields_when_orphan_scan_pending_and_no_visible_position():
    cfg = _cfg()
    store = _Store(cfg, orphan_scan={"XAUUSD": {"magic": 1, "known": [], "since": 0.0}})
    client = _Client(positions=[])  # nothing visible - exactly why the scan exists
    opt = Optimizer(store=store, client=client)

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0, "t3_length": 10}, score=1.0)

    assert result["ok"] is True
    assert store.updated_with["pending_exit_patch"] == {"sl_atr_mult": 2.0}
    assert "sl_atr_mult" not in store.updated_with
    # Entry-signal param is NOT held back - only exit/risk fields are.
    assert store.updated_with["t3_length"] == 10


def test_apply_refuses_family_swap_when_orphan_scan_pending():
    cfg = _cfg()
    store = _Store(cfg, orphan_scan={"XAUUSD": {"magic": 1, "known": [], "since": 0.0}})
    client = _Client(positions=[])
    opt = Optimizer(store=store, client=client)

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0, strategy="burst", timeframe="M5")

    assert result["ok"] is False
    assert cfg.strategy == "t3_stoch"  # unchanged


def test_apply_unaffected_by_orphan_scan_for_other_symbol():
    cfg = _cfg()
    store = _Store(cfg, orphan_scan={"EURUSD": {"magic": 2, "known": [], "since": 0.0}})
    client = _Client(positions=[])
    opt = Optimizer(store=store, client=client)

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0)

    assert result["ok"] is True
    assert store.updated_with["sl_atr_mult"] == 2.0  # applied immediately, no holdback


def test_apply_clean_when_no_orphan_scan_and_no_position():
    cfg = _cfg()
    store = _Store(cfg)
    client = _Client(positions=[])
    opt = Optimizer(store=store, client=client)

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0)

    assert result["ok"] is True
    assert store.updated_with["sl_atr_mult"] == 2.0


def test_apply_refuses_when_disconnected_before_positions():
    cfg = _cfg()
    store = _Store(cfg)
    client = _Client(positions=[])
    client.connected = False
    opt = Optimizer(store=store, client=client)

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0)

    assert result["ok"] is False
    assert store.updated_with is None


def test_apply_refuses_mid_call_disconnect_after_positions():
    cfg = _cfg()
    store = _Store(cfg)

    class _Flip:
        connected = True

        def positions(self, magic=None):
            self.connected = False
            return []

    opt = Optimizer(store=store, client=_Flip())
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0)

    assert result["ok"] is False
    assert store.updated_with is None


def test_apply_family_swap_aborts_when_secondary_clear_fails():
    # Primary must not land if clearing the stale secondary pairing fails.
    cfg = SymbolConfig(
        symbol="XAUUSD", magic=1, strategy="t3_stoch", timeframe="M15",
        ensemble_enabled=True, secondary_strategy="micro_rev",
        secondary_timeframe="M5", sl_atr_mult=1.0, tp_atr_mult=2.0,
    )
    store = _Store(cfg)
    opt = Optimizer(store=store, client=_Client(positions=[]))

    def _fail_clear(symbol, attempt):
        return {"ok": False, "error": f"{symbol}: secondary clear failed"}

    opt._apply_secondary_locked = _fail_clear  # type: ignore[method-assign]

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0,
                       strategy="burst", timeframe="M5")

    assert result["ok"] is False
    assert cfg.strategy == "t3_stoch"
    assert store.updated_with is None
