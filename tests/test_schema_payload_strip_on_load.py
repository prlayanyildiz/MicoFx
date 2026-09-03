"""Retired family knobs and leftover unread ceilings drop from symbol payloads."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import micofx.store as store_module
from micofx.store import RETIRED_PAYLOAD_KEYS, Store


def test_retired_payload_keys_cover_deleted_families():
    for key in ("nr_lookback", "stoch_extreme", "rp_lookback", "kelt_mult"):
        assert key in RETIRED_PAYLOAD_KEYS


def test_load_strips_retired_and_rewrites(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    st = Store()
    fat = {
        "symbol": "TESTNR",
        "magic": 919191,
        "enabled": True,
        "strategy": "channel_break",
        "timeframe": "M30",
        "nr_lookback": 20,
        "stoch_extreme": 80,
        "rp_lookback": 14,
        "kelt_mult": 1.5,
        "cost_rank_max": 0.5,
        "sl_atr_mult": 1.5,
    }
    with st._lock:
        st._db.execute(
            "INSERT INTO symbols(symbol, position, payload) VALUES(?,?,?)",
            ("TESTNR", 99, json.dumps(fat)),
        )
        st._db.commit()
    st._load_symbols()
    cfg = st.symbols["TESTNR"]
    assert cfg.strategy == "channel_break"
    assert float(cfg.cost_rank_max or 0) == 0.0
    row = st._db.execute(
        "SELECT payload FROM symbols WHERE symbol=?", ("TESTNR",)
    ).fetchone()
    blob = json.loads(row["payload"])
    for key in ("nr_lookback", "stoch_extreme", "rp_lookback", "kelt_mult"):
        assert key not in blob
    assert float(blob.get("cost_rank_max") or 0) == 0.0


def test_store_reset_opt_params_was_removed():
    assert "reset_opt_params" not in Store.__dict__
