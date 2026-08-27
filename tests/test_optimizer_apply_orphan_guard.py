"""Optimizer.apply() (the PRIMARY apply path) must treat a still-open
orphan-scan window the same way it already treats a live position (NOT-1) - the
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

    def update_symbol(self, symbol, patch, source=""):
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
    return SymbolConfig(symbol="XAUUSD", magic=1, strategy="stoch_flip", timeframe="M15",
                        sl_atr_mult=1.0, trail_step_atr=0.6)


STAMP = {
    "holdout": {"trades": 40, "expectancy": 0.2, "net_r": 8.0, "max_dd_r": 4.0},
    "holdout_days": 30.0,
    "validated": True,
    "validation": {},
    "selection": {},
    "positive_ratio": 1.0,
}


def _make_opt(store, client):
    opt = Optimizer(store=store, client=client)
    opt._holdout_costed = lambda *a, **k: None
    return opt


def test_apply_holds_back_exit_fields_when_orphan_scan_pending_and_no_visible_position():
    cfg = _cfg()
    store = _Store(cfg, orphan_scan={"XAUUSD": {"magic": 1, "known": [], "since": 0.0}})
    client = _Client(positions=[])  # nothing visible - exactly why the scan exists
    opt = _make_opt(store, client)

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0, "t3_length": 10}, score=1.0,
                       detail=STAMP)

    assert result["ok"] is True
    assert store.updated_with["pending_exit_patch"] == {"sl_atr_mult": 2.0}
    assert "sl_atr_mult" not in store.updated_with
    # Entry-signal param is NOT held back - only exit/risk fields are.
    assert store.updated_with["t3_length"] == 10


def test_apply_refuses_family_swap_when_orphan_scan_pending():
    cfg = _cfg()
    store = _Store(cfg, orphan_scan={"XAUUSD": {"magic": 1, "known": [], "since": 0.0}})
    client = _Client(positions=[])
    opt = _make_opt(store, client)

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0, detail=STAMP,
                       strategy="burst", timeframe="M5")

    assert result["ok"] is False
    assert cfg.strategy == "stoch_flip"  # unchanged


def test_apply_unaffected_by_orphan_scan_for_other_symbol():
    cfg = _cfg()
    store = _Store(cfg, orphan_scan={"EURUSD": {"magic": 2, "known": [], "since": 0.0}})
    client = _Client(positions=[])
    opt = _make_opt(store, client)

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0, detail=STAMP)

    assert result["ok"] is True
    assert store.updated_with["sl_atr_mult"] == 2.0  # applied immediately, no holdback


def test_apply_clean_when_no_orphan_scan_and_no_position():
    cfg = _cfg()
    store = _Store(cfg)
    client = _Client(positions=[])
    opt = _make_opt(store, client)

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0, detail=STAMP)

    assert result["ok"] is True
    assert store.updated_with["sl_atr_mult"] == 2.0


def test_apply_refuses_when_disconnected_before_positions():
    cfg = _cfg()
    store = _Store(cfg)
    client = _Client(positions=[])
    client.connected = False
    opt = _make_opt(store, client)

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0, detail=STAMP)

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

    opt = _make_opt(store, _Flip())
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0, detail=STAMP)

    assert result["ok"] is False
    assert store.updated_with is None


def test_apply_family_swap_does_not_depend_on_secondary_clear():
    """Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok.

    apply() used to refuse a primary family swap when clearing a stored
    secondary pairing failed. That writer is gone; a leftover secondary_*
    row must not block the primary apply. The fields stay on the row until
    a later stage clears them.
    """
    cfg = SymbolConfig(
        symbol="XAUUSD", magic=1, strategy="stoch_flip", timeframe="M15", sl_atr_mult=1.0, trail_step_atr=0.6,
    )
    store = _Store(cfg)
    opt = _make_opt(store, _Client(positions=[]))

    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.0}, score=1.0, detail=STAMP,
                       strategy="burst", timeframe="M5")

    assert result["ok"] is True
    assert cfg.strategy == "burst"
    assert not hasattr(cfg, "secondary_strategy")
    assert not hasattr(opt, "_apply_secondary_locked")
