"""Held-back exit params are re-validated at the moment they land.

Optimizer.apply() validates what it stages, but a pending patch is a value
that sat in the DB across an arbitrary gap: it can predate that check, or come
back from a restored backup or a hand-edited row. _apply_pending_exits is the
one write path that trusted stored data verbatim, so it re-checks and drops
what it cannot use rather than landing it on a live symbol.

Also covers the integration gap the shared validator left open: that
Optimizer.apply() itself really does refuse a poisoned param, not just that
invalid_exit_param() returns a reason for it.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.models import SymbolConfig


class _Store:
    """Minimal store: update_symbol merges a patch like the real one does."""

    def __init__(self, cfg: SymbolConfig) -> None:
        self.symbols = {cfg.symbol: cfg}
        self.writes: list[dict] = []

    def update_symbol(self, symbol, patch, source=""):
        cfg = self.symbols.get(symbol)
        if cfg is None:
            return None
        self.writes.append(dict(patch))
        current = cfg.to_dict()
        for key, value in patch.items():
            if key in current and value is not None:
                current[key] = value
        updated = SymbolConfig.from_dict(current)
        self.symbols[symbol] = updated
        return updated


def _engine(cfg: SymbolConfig) -> tuple[Engine, _Store]:
    eng = Engine.__new__(Engine)          # no MT5 connect / no DB
    store = _Store(cfg)
    eng.store = store
    eng.entry_lock = threading.Lock()
    eng._positions = []                   # nothing open -> pending may land
    eng._sec_tickets = set()
    eng._orphan_tickets = set()
    eng._orphan_scan = {}
    return eng, store


def _cfg(**kw) -> SymbolConfig:
    return SymbolConfig(symbol="XAUUSD", magic=990021, **kw)


# ------------------------------------------------------------------ primary

@pytest.mark.parametrize("bad_patch", [
    {"trail_start_atr": 0.0},     # trail would never arm again
    {"trail_step_atr": 0.0},
    {"sl_atr_mult": 0.0},
    {"sl_atr_mult": -5.0},
    {"trail_step_atr": -3.0},
    {"sl_atr_mult": 9999.0},
])
def test_a_poisoned_pending_patch_is_dropped_not_landed(bad_patch):
    cfg = _cfg(sl_atr_mult=1.5, trail_start_atr=0.5, trail_step_atr=1.6,
               pending_exit_patch=dict(bad_patch))
    eng, store = _engine(cfg)
    eng._apply_pending_exits()

    live = store.symbols["XAUUSD"]
    assert live.pending_exit_patch == {}, "bad patch was left to retry forever"
    # Every previously-validated value survives untouched.
    assert live.sl_atr_mult == 1.5
    assert live.trail_start_atr == 0.5
    assert live.trail_step_atr == 1.6
    for field in bad_patch:
        assert getattr(live, field) != bad_patch[field]


def test_a_valid_pending_patch_still_lands():
    """The gate is the bounds, not "pending patches are suspicious"."""
    cfg = _cfg(sl_atr_mult=1.5, trail_start_atr=0.5, trail_step_atr=1.6,
               pending_exit_patch={"trail_step_atr": 2.4, "sl_atr_mult": 2.0})
    eng, store = _engine(cfg)
    eng._apply_pending_exits()

    live = store.symbols["XAUUSD"]
    assert live.trail_step_atr == 2.4
    assert live.sl_atr_mult == 2.0
    assert live.pending_exit_patch == {}


def test_a_bad_primary_patch_does_not_starve_the_secondary_one():
    """Dropping the primary must not skip the secondary block for that cycle."""
    cfg = _cfg(pending_exit_patch={"trail_start_atr": 0.0},
               secondary_params={"sl_atr_mult": 1.0},
               pending_secondary_exit_patch={"trail_step_atr": 1.8})
    eng, store = _engine(cfg)
    eng._apply_pending_exits()

    live = store.symbols["XAUUSD"]
    assert live.pending_exit_patch == {}
    assert live.pending_secondary_exit_patch == {}
    assert live.secondary_params["trail_step_atr"] == 1.8


# ---------------------------------------------------------------- secondary

def test_a_poisoned_secondary_pending_patch_is_dropped():
    cfg = _cfg(secondary_params={"sl_atr_mult": 1.5, "trail_start_atr": 0.5},
               pending_secondary_exit_patch={"trail_start_atr": 0.0})
    eng, store = _engine(cfg)
    eng._apply_pending_exits()

    live = store.symbols["XAUUSD"]
    assert live.pending_secondary_exit_patch == {}
    assert live.secondary_params["trail_start_atr"] == 0.5, "poison landed"


def test_the_secondary_check_runs_on_the_merged_result():
    """A patch that is fine alone can still merge into an unusable dict.

    The patch itself carries no exit field at all here, so checking the patch
    in isolation would pass it - what has to be usable is what the merge
    produces, since that is the dict the secondary signal's exits come from.
    """
    cfg = _cfg(secondary_params={"trail_start_atr": 0.0},   # already broken
               pending_secondary_exit_patch={"trail_lookback": 8})
    eng, store = _engine(cfg)
    eng._apply_pending_exits()

    live = store.symbols["XAUUSD"]
    assert live.pending_secondary_exit_patch == {}
    assert "trail_lookback" not in live.secondary_params, \
        "merged into a secondary_params whose trail can never arm"


def test_a_valid_secondary_pending_patch_lands_merged():
    cfg = _cfg(secondary_params={"sl_atr_mult": 1.5, "trail_start_atr": 0.5},
               pending_secondary_exit_patch={"trail_step_atr": 1.2})
    eng, store = _engine(cfg)
    eng._apply_pending_exits()

    live = store.symbols["XAUUSD"]
    assert live.secondary_params == {"sl_atr_mult": 1.5, "trail_start_atr": 0.5,
                                     "trail_step_atr": 1.2}
    assert live.pending_secondary_exit_patch == {}


# ------------------------------------------- Optimizer.apply, for real

@pytest.mark.parametrize("params,ok", [
    ({"sl_atr_mult": 1.5, "trail_start_atr": 0.0, "trail_step_atr": 1.6}, False),
    ({"sl_atr_mult": 0.0, "trail_start_atr": 0.5, "trail_step_atr": 1.6}, False),
    ({"sl_atr_mult": 1.5, "trail_start_atr": 0.5, "trail_step_atr": -3.0}, False),
    ({"sl_atr_mult": 1.5, "trail_start_atr": 0.8, "trail_step_atr": 1.6}, True),
])
def test_optimizer_apply_itself_refuses_poisoned_params(params, ok):
    """Closes the gap between "the validator says no" and "apply() says no".

    This is the auto-apply path's real entry point - no HTTP handler in front
    of it - so it is worth asserting on apply() rather than on the validator.
    """
    from micofx.optimizer import Optimizer

    cfg = _cfg(sl_atr_mult=1.5, trail_start_atr=0.5, trail_step_atr=1.6)

    class _S(_Store):
        def opt_params(self):
            return {}

        def get_setting(self, key, default=None):
            return default

    class _C:
        """apply() fails closed on a disconnect, so the happy path needs one."""
        connected = True

        def positions(self, magic=None, symbol=None):
            return []

    store = _S(cfg)
    opt = Optimizer.__new__(Optimizer)
    opt.store = store
    opt.entry_lock = None
    opt.client = _C()

    result = opt.apply("XAUUSD", params, score=1.0, detail=None,
                       timeframe="M15", strategy="t3_stoch")
    assert result.get("ok") is ok, result
    if not ok:
        assert "gecersiz" in result.get("error", "")
        assert store.symbols["XAUUSD"].trail_start_atr == 0.5, "poison was written"
