"""L2: Optimizer._apply_secondary_locked's refine-holdback branch (same
family/timeframe, only params changed) only checked live_tagged - the
identity-swap branch right above it already treats live_orphan (an
unresolved orphan ticket) and pending_scan (H1's still-open orphan-scan
window) as the same risk class, but the refine elif did not, so a refine
could write straight through to secondary_params while an untracked fill
was still open under this magic - manage_positions() re-reads that dict
live every cycle via _secondary_config().
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self, cfg, orphan_scan=None, orphan_tickets=None, tagged=None):
        self._cfg = cfg
        self.symbols = {"XAUUSD": cfg}
        self._orphan_scan = orphan_scan or {}
        self._orphan_tickets = orphan_tickets or []
        self._tagged = tagged or []
        self.updated_with = None

    def get_setting(self, key, default=None):
        if key == "secondary_orphan_scan":
            return self._orphan_scan
        if key == "secondary_orphan_tickets":
            return self._orphan_tickets
        if key == "secondary_tickets":
            return self._tagged
        return default

    def opt_params(self):
        return {}

    def update_symbol(self, symbol, patch, source=""):
        self.updated_with = patch
        current = self._cfg.to_dict()
        for k, v in patch.items():
            if v is not None:
                current[k] = v
        self._cfg = SymbolConfig.from_dict(current)
        self.symbols["XAUUSD"] = self._cfg
        return self._cfg


class _Client:
    connected = True

    def __init__(self, positions):
        self._positions = positions

    def positions(self, magic=None, symbol=None):
        return [p for p in self._positions if magic is None or p["magic"] == magic]


def _cfg():
    return SymbolConfig(symbol="XAUUSD", magic=1, secondary_strategy="micro_rev",
                        secondary_timeframe="M5",
                        secondary_params={"trail_start_atr": 1.0})


def _attempt(trail=2.0):
    return {
        "strategy": "micro_rev", "timeframe": "M5",
        "best": {"params": {"trail_start_atr": trail}, "score": 1.0,
                 "holdout": {}, "validation": {}, "selection": {}, "positive_ratio": 0.5},
    }


def test_refine_holds_back_exit_fields_when_live_orphan_ticket_open():
    cfg = _cfg()
    store = _Store(cfg, orphan_tickets=[501])
    client = _Client(positions=[{"ticket": 501, "magic": 1}])
    opt = Optimizer(store=store, client=client)

    result = opt._apply_secondary_locked("XAUUSD", _attempt())

    assert result["ok"] is True
    assert store.updated_with["pending_secondary_exit_patch"] == {"trail_start_atr": 2.0}
    assert "trail_start_atr" not in store.updated_with["secondary_params"]


def test_refine_holds_back_exit_fields_when_orphan_scan_pending():
    cfg = _cfg()
    store = _Store(cfg, orphan_scan={"XAUUSD": {"magic": 1, "known": [], "since": 0.0}})
    client = _Client(positions=[])  # nothing visible - exactly why the scan exists
    opt = Optimizer(store=store, client=client)

    result = opt._apply_secondary_locked("XAUUSD", _attempt())

    assert result["ok"] is True
    assert store.updated_with["pending_secondary_exit_patch"] == {"trail_start_atr": 2.0}
    assert "trail_start_atr" not in store.updated_with["secondary_params"]


def test_refine_applies_immediately_when_clear():
    cfg = _cfg()
    store = _Store(cfg)
    client = _Client(positions=[])
    opt = Optimizer(store=store, client=client)

    result = opt._apply_secondary_locked("XAUUSD", _attempt())

    assert result["ok"] is True
    assert store.updated_with["secondary_params"]["trail_start_atr"] == 2.0
    assert store.updated_with["pending_secondary_exit_patch"] == {}


def test_refine_holdback_still_works_with_live_tagged():
    # Regression: the original live_tagged-only holdback must keep working.
    cfg = _cfg()
    store = _Store(cfg, tagged=[500])
    client = _Client(positions=[{"ticket": 500, "magic": 1}])
    opt = Optimizer(store=store, client=client)

    result = opt._apply_secondary_locked("XAUUSD", _attempt())

    assert result["ok"] is True
    assert store.updated_with["pending_secondary_exit_patch"] == {"trail_start_atr": 2.0}
