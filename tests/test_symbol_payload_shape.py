"""One unreadable symbol row must skip, not take the whole start-up down.

Store._load_symbols already catches JSONDecodeError and TypeError per row and
logs-and-continues, so the intent is explicit: a corrupt row is skipped and
the app still starts. The exception list was just incomplete.

_coerce goes straight to payload.items(), so a payload that is valid JSON but
not an object - ``null``, a list, a string, a number, a bool - raised
AttributeError instead. That is not in the catch list, and _load_symbols()
runs outside the sqlite try/except in Store.__init__ while run.py converts
only RuntimeError. So one such row propagated as a raw traceback and, under
pythonw.exe, into a stream nobody ever sees: the app just never appeared.

Five of the nine corrupt shapes swept bypassed the handler this way. The
settings side, by contrast, came back clean on all 108 combinations tried -
it guards every read with isinstance.

Reachability is a hand-edited database, a backup restored from another
version, or any external tool touching the file; save_symbol itself always
writes a dict. The defence already existed for that scenario, which is the
point - it just did not cover the likeliest shapes.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import store as store_mod
from micofx.models import SymbolConfig

NON_OBJECTS = [None, [1, 2, 3], "merhaba", 42, 3.5, True, (1, 2)]


@pytest.mark.parametrize("payload", NON_OBJECTS, ids=[repr(p) for p in NON_OBJECTS])
def test_a_non_object_payload_raises_type_error(payload):
    """TypeError specifically - it is what the existing handlers catch."""
    with pytest.raises(TypeError) as err:
        SymbolConfig.from_dict(payload)
    assert type(payload).__name__ in str(err.value)


def test_a_real_config_still_round_trips():
    cfg = SymbolConfig(symbol="XAUUSD", magic=990021, strategy="t3_flip")
    again = SymbolConfig.from_dict(cfg.to_dict())
    assert again.symbol == "XAUUSD"
    assert again.magic == 990021
    assert again.strategy == "t3_flip"


# ------------------------------------------------ the start-up consequence

def _db_with(tmp_path, rows):
    path = tmp_path / "corrupt.db"
    con = sqlite3.connect(path)
    con.executescript(store_mod._SCHEMA)
    for i, (symbol, blob) in enumerate(rows):
        con.execute("INSERT INTO symbols(symbol,position,payload) VALUES(?,?,?)",
                    (symbol, i, blob))
    con.commit()
    con.close()
    return path


def _store(tmp_path, monkeypatch, path):
    monkeypatch.setattr(store_mod, "DB_PATH", path)
    monkeypatch.setattr(store_mod, "ensure_dirs", lambda: None)
    return store_mod.Store()


@pytest.mark.parametrize("blob", ["null", "[1,2,3]", '"merhaba"', "42", "true"])
def test_a_corrupt_row_does_not_stop_the_app_starting(tmp_path, monkeypatch, blob):
    good = json.dumps(SymbolConfig(symbol="XAUUSD", magic=990021).to_dict())
    path = _db_with(tmp_path, [("BAD", blob), ("XAUUSD", good)])
    store = _store(tmp_path, monkeypatch, path)
    try:
        # The healthy row survives; the unreadable one is skipped.
        assert "XAUUSD" in store.symbols
        assert "BAD" not in store.symbols
    finally:
        store.close()


def test_every_row_being_corrupt_seeds_defaults_instead_of_crashing(tmp_path, monkeypatch):
    path = _db_with(tmp_path, [("A", "null"), ("B", "[1]"), ("C", "42")])
    store = _store(tmp_path, monkeypatch, path)
    try:
        # Store.__init__ seeds from defaults.json when nothing loads.
        assert store.symbols, "hicbir sembol yuklenmedi ve tohumlama da yapilmadi"
    finally:
        store.close()


def test_the_handler_still_covers_unparseable_json(tmp_path, monkeypatch):
    """The shapes that already worked must keep working."""
    good = json.dumps(SymbolConfig(symbol="XAUUSD", magic=990021).to_dict())
    path = _db_with(tmp_path, [("BAD", "{kirik,,,"), ("XAUUSD", good)])
    store = _store(tmp_path, monkeypatch, path)
    try:
        assert "XAUUSD" in store.symbols
    finally:
        store.close()


def test_the_settings_side_is_still_clean(tmp_path, monkeypatch):
    """Swept separately and came back clean; assert the isinstance guards hold."""
    path = tmp_path / "settings.db"
    con = sqlite3.connect(path)
    con.executescript(store_mod._SCHEMA)
    for key in ("system", "opt_params", "supervisor", "entry_blocks"):
        con.execute("INSERT INTO settings(key,value) VALUES(?,?)", (key, "[1,2,3]"))
    con.commit()
    con.close()
    monkeypatch.setattr(store_mod, "DB_PATH", path)
    monkeypatch.setattr(store_mod, "ensure_dirs", lambda: None)
    store = store_mod.Store()
    try:
        assert isinstance(store.opt_params(), dict)
        assert store.system is not None
    finally:
        store.close()
