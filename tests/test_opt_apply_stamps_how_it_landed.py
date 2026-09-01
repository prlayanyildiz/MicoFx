"""POST /api/opt/apply must leave the same apply-path stamp G11 put on search.

The panel's history button posts ``run_id``; the results table posts params
and the handler matches a history row. Neither path called record_opt_run, so
force/applied_at/previous were only on Optimizer._finish_symbol rows. The
40/46 young applies in BS-3 were that search path; this is the other door.

Old rows stay key-less. A new stamp always writes the three keys so None is
not False is not missing. Updating the existing run keeps one candidate as
one row; a second insert would double-count applied and split the identity
the panel already shows. Hand-typed params with no matching row have nothing
to update, so those insert.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from micofx.models import SymbolConfig
from micofx.web.app import create_app


def _cfg(symbol="XAUUSD", magic=990021):
    c = SymbolConfig(symbol=symbol, magic=magic)
    c.strategy = "burst"
    c.timeframe = "M5"
    return c


class _FakeSystem:
    slippage_points = 20

    def to_dict(self):
        return {}


class _RecordingStore:
    def __init__(self, symbols, history):
        self.symbols = symbols
        self.system = _FakeSystem()
        self.defaults = {"symbols": [], "group_presets": {}}
        self.history = list(history)
        self.stamps = []
        self.inserts = []

    def get_setting(self, key, default=None):
        return default

    def opt_params(self):
        return {}

    def opt_history(self, symbol, limit):
        return [r for r in self.history if r.get("symbol") == symbol][:limit]

    def update_symbol(self, symbol, patch, source=""):
        cfg = self.symbols.get(symbol)
        if cfg is None:
            return None
        current = cfg.to_dict()
        for key, value in patch.items():
            if key in current and value is not None:
                current[key] = value
        updated = SymbolConfig.from_dict(current)
        self.symbols[symbol] = updated
        return updated

    def stamp_opt_run_apply(self, run_id, force, previous, applied_at):
        self.stamps.append({
            "run_id": run_id, "force": force,
            "previous": previous, "applied_at": applied_at,
        })
        return True

    def record_opt_run(self, symbol, score, payload, applied):
        self.inserts.append({
            "symbol": symbol, "score": score,
            "payload": payload, "applied": applied,
        })
        return 99


class _MutatingOptimizer:
    """apply() rewrites the live family so a late snapshot would lie."""

    def apply(self, symbol, params, score, detail=None, timeframe=None, strategy=None):
        cfg = self.store.symbols[symbol]
        cfg.strategy = strategy or "burst"
        cfg.timeframe = timeframe or "M15"
        return {"ok": True, "applied": True}


class _FakeClient:
    connected = True

    def positions(self, magic=None, symbol=None):
        return []

    def set_overrides(self, mapping):
        pass


class _FakeEngine:
    def __init__(self):
        self.states = {}
        self.entry_lock = threading.Lock()
        self._sec_cfgs = {}


def _history_row(run_id=7, validated=True):
    return {
        "id": run_id, "symbol": "XAUUSD", "score": 12.5,
        "params": {"sl_atr_mult": 1.5, "trail_step_atr": 0.8, "trail_mode": "atr"},
        "timeframe": "M15", "strategy": "channel_break",
        "validated": validated, "holdout": {"net_r": 4.0},
        "applied": False,
    }


def _client(history, optimizer=None):
    symbols = {"XAUUSD": _cfg()}
    store = _RecordingStore(symbols, history)
    opt = optimizer or _MutatingOptimizer()
    opt.store = store
    app = create_app(store, _FakeClient(), _FakeEngine(), opt)
    return TestClient(app), store


def test_run_id_apply_stamps_the_existing_row_not_a_new_one():
    tc, store = _client([_history_row()])
    before = time.time()
    res = tc.post("/api/opt/apply", json={"symbol": "XAUUSD", "run_id": 7, "force": True})
    assert res.status_code == 200, res.text
    assert store.inserts == []
    assert len(store.stamps) == 1
    stamp = store.stamps[0]
    assert stamp["run_id"] == 7
    assert stamp["force"] is True
    assert stamp["applied_at"] >= before
    assert stamp["previous"] == {"strategy": "burst", "timeframe": "M5"}


def test_param_match_apply_stamps_the_matched_row():
    """Results table posts params, not run_id. Same candidate, same row."""
    tc, store = _client([_history_row(run_id=11)])
    res = tc.post("/api/opt/apply", json={
        "symbol": "XAUUSD",
        "params": {"sl_atr_mult": 1.5, "trail_step_atr": 0.8, "trail_mode": "atr"},
        "timeframe": "M15", "strategy": "channel_break",
        "score": 12.5,
    })
    assert res.status_code == 200, res.text
    assert store.inserts == []
    assert store.stamps[0]["run_id"] == 11
    assert store.stamps[0]["force"] is False
    assert store.stamps[0]["previous"]["strategy"] == "burst"


def test_hand_typed_params_with_no_row_insert_a_stamped_run():
    tc, store = _client([])
    res = tc.post("/api/opt/apply", json={
        "symbol": "XAUUSD",
        "params": {"sl_atr_mult": 1.5, "trail_step_atr": 0.8, "trail_mode": "atr"},
        "timeframe": "M15", "strategy": "channel_break",
        "score": 1.0, "force": False,
    })
    assert res.status_code == 200, res.text
    assert store.stamps == []
    assert len(store.inserts) == 1
    payload = store.inserts[0]["payload"]
    assert "force" in payload
    assert payload["force"] is False
    assert payload["applied_at"] is not None
    assert payload["previous"] == {"strategy": "burst", "timeframe": "M5"}
    assert store.inserts[0]["applied"] is True


def test_stamp_merges_into_payload_without_dropping_holdout(tmp_path, monkeypatch):
    """The search row's evidence stays; only the three apply keys are added."""
    import micofx.store as store_module

    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "opt.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    st = store_module.Store()
    run_id = st.record_opt_run(
        "XAUUSD", 12.5,
        {"holdout": {"net_r": 4.0}, "strategy": "channel_break", "timeframe": "M15"},
        applied=False,
    )
    ok = st.stamp_opt_run_apply(
        run_id, force=True,
        previous={"strategy": "burst", "timeframe": "M5"},
        applied_at=1_700_000_000.0,
    )
    assert ok is True
    row = st.opt_history("XAUUSD")[0]
    assert row["applied"] is True
    assert row["score"] == 12.5
    assert row["holdout"] == {"net_r": 4.0}
    assert row["force"] is True
    assert row["applied_at"] == 1_700_000_000.0
    assert row["previous"] == {"strategy": "burst", "timeframe": "M5"}


def test_stamp_of_a_missing_id_returns_false_and_leaves_history_alone(tmp_path, monkeypatch):
    import micofx.store as store_module

    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "opt.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    st = store_module.Store()
    st.record_opt_run("XAUUSD", 1.0, {"strategy": "burst"}, applied=False)
    assert st.stamp_opt_run_apply(999, False, None, 1.0) is False
    row = st.opt_history("XAUUSD")[0]
    assert row["applied"] is False
    assert "force" not in row


def test_a_failed_apply_does_not_stamp():
    class _Refuse:
        store = None

        def apply(self, *a, **k):
            return {"ok": False, "error": "red"}

    tc, store = _client([_history_row()], optimizer=_Refuse())
    res = tc.post("/api/opt/apply", json={"symbol": "XAUUSD", "run_id": 7})
    assert res.status_code == 400
    assert store.stamps == []
    assert store.inserts == []
