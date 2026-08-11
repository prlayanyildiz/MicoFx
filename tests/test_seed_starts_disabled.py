"""A fresh install must not start symbols live on a config nobody chose.

config/defaults.json carries symbol, group, magic, sessions and the enabled
flag. Strategy, timeframe and every exit parameter live only in the gitignored
database, so seeding from the template produces symbols with opt_updated_at
0.0, an empty opt_summary and the dataclass default of t3_stoch/M5.

Before this, all eighteen template symbols marked enabled came up live in
exactly that state - the same position EURUSD reached tonight, at book scale.
On an FX symbol M5 pays 25-28% of risk in spread against an 18% live ceiling,
so those configs are either refused at the gate on every signal or fill on
parameters nothing has validated.

The API guards added for EURUSD do not cover this path: seed_symbols writes
the config directly rather than going through patch_symbol or symbols-bulk.
So the flag is forced off at the seed, and the operator enables a symbol once
it has a searched config - which those guards then enforce.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import store as store_mod

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(store_mod, "DB_PATH", tmp_path / "fresh.db")
    monkeypatch.setattr(store_mod, "ensure_dirs", lambda: None)
    store = store_mod.Store()
    yield store
    store.close()


def test_a_fresh_install_seeds_every_symbol_switched_off(fresh):
    assert fresh.symbols, "hic sembol tohumlanmadi"
    live = [c.symbol for c in fresh.symbols.values() if c.enabled]
    assert live == [], f"optimize edilmemis sembol acik geldi: {live}"


def test_the_seeded_symbols_are_otherwise_intact(fresh):
    """Only the enabled flag is overridden - everything else still seeds."""
    template = json.loads((ROOT / "config" / "defaults.json")
                          .read_text(encoding="utf-8-sig"))
    wanted = {e["symbol"] for e in template["symbols"]}
    assert set(fresh.symbols) == wanted
    xau = fresh.symbols["XAUUSD"]
    assert xau.group == "commodity"
    assert xau.sessions[0]["start"] == "02:00"


def test_no_seeded_symbol_carries_a_searched_config(fresh):
    """The reason they must not be live: there is nothing behind them yet."""
    for cfg in fresh.symbols.values():
        assert not cfg.opt_updated_at
        assert cfg.opt_summary == {}


def test_the_template_enabled_flag_cannot_switch_one_on(tmp_path, monkeypatch):
    """Even a template that insists on enabled:true is overridden."""
    monkeypatch.setattr(store_mod, "DB_PATH", tmp_path / "x.db")
    monkeypatch.setattr(store_mod, "ensure_dirs", lambda: None)
    store = store_mod.Store()
    try:
        store.defaults = {"symbols": [
            {"symbol": "ZZZTEST", "group": "forex", "magic": 991234,
             "enabled": True},
        ], "group_presets": {}}
        store.symbols = {}
        store.seed_symbols()
        assert store.symbols["ZZZTEST"].enabled is False
    finally:
        store.close()


def test_the_shipped_template_still_records_intent(tmp_path):
    """The flag stays meaningful in git - it says what SHOULD be on once
    optimised - it just cannot switch anything on by itself."""
    template = json.loads((ROOT / "config" / "defaults.json")
                          .read_text(encoding="utf-8-sig"))
    flags = {e["symbol"]: e.get("enabled", True) for e in template["symbols"]}
    assert flags.get("EURUSD") is False
    assert flags.get("EURJPY") is False
    assert any(v for v in flags.values()), "sablon tum sembolleri kapali gosteriyor"
