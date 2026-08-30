"""Family/TF apply must queue while a ticket is open, not drop the winner.

Overnight 28.08 NAS100: burst/M30 validated (score 39.41) and apply() returned
the family-swap error. pending_exit_patch is only for same-family exit/risk
holdback, so the winner was discarded and live stayed on stoch_flip/M30
(30d PF 0.57). Same-family refine already stages; family swap did not.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _OptStore:
    def __init__(self, cfg, orphan_scan=None):
        self._cfg = cfg
        self.symbols = {cfg.symbol: cfg}
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
        current = self._cfg.to_dict()
        for key, value in patch.items():
            if key in current and value is not None:
                current[key] = value
        updated = SymbolConfig.from_dict(current)
        self.symbols[symbol] = updated
        self._cfg = updated
        return updated


class _Client:
    connected = True

    def __init__(self, positions):
        self._positions = positions

    def positions(self, magic=None, symbol=None):
        return [p for p in self._positions if magic is None or p["magic"] == magic]


STAMP = {
    "holdout": {"trades": 40, "expectancy": 0.2, "net_r": 8.0, "max_dd_r": 4.0,
                "profit_factor": 1.4, "score": 8.0},
    "holdout_days": 30.0,
    "validated": True,
    "validation": {"trades": 30, "net_r": 4.0, "profit_factor": 1.3},
    "selection": {},
    "positive_ratio": 1.0,
}


def _cfg(**kw):
    return SymbolConfig(symbol="NAS100", magic=1, strategy="stoch_flip",
                        timeframe="M30", sl_atr_mult=1.0, trail_step_atr=0.6,
                        **kw)


def _make_opt(store, client):
    opt = Optimizer(store=store, client=client)
    opt._holdout_costed = lambda *a, **k: None
    return opt


def _engine(cfg: SymbolConfig) -> tuple[Engine, _OptStore]:
    eng = Engine.__new__(Engine)
    store = _OptStore(cfg)
    eng.store = store
    eng.entry_lock = threading.Lock()
    eng._positions = []
    eng._sec_tickets = set()
    eng._orphan_tickets = set()
    eng._orphan_scan = {}
    eng.supervisor = type("S", (), {"optimizer": None})()
    return eng, store


def test_family_swap_with_open_ticket_queues_instead_of_dropping_the_winner():
    cfg = _cfg()
    store = _OptStore(cfg)
    client = _Client(positions=[{"ticket": 9, "magic": 1, "symbol": "NAS100"}])
    opt = _make_opt(store, client)

    result = opt.apply("NAS100", {"sl_atr_mult": 2.0, "t3_length": 10}, score=39.41,
                       detail=STAMP, strategy="burst", timeframe="M30")

    assert result["ok"] is True, result
    assert result.get("deferred") is True
    live = store.symbols["NAS100"]
    assert live.strategy == "stoch_flip"
    assert live.timeframe == "M30"
    assert live.sl_atr_mult == 1.0
    pending = live.pending_primary_patch
    assert pending["strategy"] == "burst"
    assert pending["timeframe"] == "M30"
    assert pending["sl_atr_mult"] == 2.0
    assert pending["t3_length"] == 10
    assert live.pending_exit_patch == {}


def test_family_swap_with_orphan_scan_queues_the_same_way():
    cfg = _cfg()
    store = _OptStore(cfg, orphan_scan={"NAS100": {"magic": 1, "known": [], "since": 0.0}})
    client = _Client(positions=[])
    opt = _make_opt(store, client)

    result = opt.apply("NAS100", {"sl_atr_mult": 2.0}, score=1.0, detail=STAMP,
                       strategy="burst", timeframe="M5")

    assert result["ok"] is True, result
    assert result.get("deferred") is True
    live = store.symbols["NAS100"]
    assert live.strategy == "stoch_flip"
    assert live.pending_primary_patch["strategy"] == "burst"


def test_family_swap_while_flat_still_lands_immediately():
    cfg = _cfg()
    store = _OptStore(cfg)
    opt = _make_opt(store, _Client(positions=[]))

    result = opt.apply("NAS100", {"sl_atr_mult": 2.0}, score=1.0, detail=STAMP,
                       strategy="burst", timeframe="M15")

    assert result["ok"] is True
    assert not result.get("deferred")
    live = store.symbols["NAS100"]
    assert live.strategy == "burst"
    assert live.timeframe == "M15"
    assert live.sl_atr_mult == 2.0
    assert live.pending_primary_patch == {}


def test_a_later_apply_supersedes_a_queued_family_swap():
    cfg = _cfg(pending_primary_patch={"strategy": "burst", "timeframe": "M30",
                                      "sl_atr_mult": 9.0})
    store = _OptStore(cfg)
    opt = _make_opt(store, _Client(positions=[]))

    result = opt.apply("NAS100", {"sl_atr_mult": 1.5, "t3_length": 8}, score=2.0,
                       detail=STAMP)

    assert result["ok"] is True
    live = store.symbols["NAS100"]
    assert live.pending_primary_patch == {}
    assert live.sl_atr_mult == 1.5


def test_engine_lands_queued_family_when_flat():
    cfg = _cfg(pending_primary_patch={
        "strategy": "burst", "timeframe": "M30", "sl_atr_mult": 2.0,
        "opt_score": 39.41, "validated": True,
        "opt_summary": {"holdout": {"net_r": 12.0}, "validated": True,
                        "holdout_days": 30.0},
    })
    eng, store = _engine(cfg)
    eng._apply_pending_exits()

    live = store.symbols["NAS100"]
    assert live.strategy == "burst"
    assert live.timeframe == "M30"
    assert live.sl_atr_mult == 2.0
    assert live.pending_primary_patch == {}


def test_engine_holds_queued_family_while_a_ticket_is_open():
    cfg = _cfg(pending_primary_patch={"strategy": "burst", "timeframe": "M30",
                                      "sl_atr_mult": 2.0})
    eng, store = _engine(cfg)
    eng._positions = [{"ticket": 9, "magic": 1, "symbol": "NAS100"}]
    eng._apply_pending_exits()

    live = store.symbols["NAS100"]
    assert live.strategy == "stoch_flip"
    assert live.pending_primary_patch["strategy"] == "burst"


def test_engine_holds_queued_family_while_orphan_scan_pending():
    cfg = _cfg(pending_primary_patch={"strategy": "burst", "sl_atr_mult": 2.0})
    eng, store = _engine(cfg)
    eng._orphan_scan = {"NAS100": {"magic": 1, "known": [], "since": 0.0}}
    eng._apply_pending_exits()

    live = store.symbols["NAS100"]
    assert live.strategy == "stoch_flip"
    assert live.pending_primary_patch["strategy"] == "burst"


def test_poisoned_queued_family_is_dropped_not_landed():
    cfg = _cfg(pending_primary_patch={"strategy": "burst", "trail_step_atr": 0.0})
    eng, store = _engine(cfg)
    eng._apply_pending_exits()

    live = store.symbols["NAS100"]
    assert live.strategy == "stoch_flip"
    assert live.pending_primary_patch == {}


def test_queued_family_does_not_write_magic_or_enabled():
    cfg = _cfg(enabled=True, pending_primary_patch={
        "strategy": "burst", "magic": 999, "enabled": False, "sl_atr_mult": 2.0,
    })
    eng, store = _engine(cfg)
    eng._apply_pending_exits()

    live = store.symbols["NAS100"]
    assert live.strategy == "burst"
    assert live.magic == 1
    assert live.enabled is True
