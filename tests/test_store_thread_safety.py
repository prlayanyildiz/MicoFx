"""Hard-scan fixes: Store thread-safety and opt_params None-write.

- update_system(): the read-modify-write used to be two separate lock
  acquisitions (_load_system() then save_system()) with plain Python
  in between - two threads (engine start()/stop() vs a web System PATCH)
  concurrently patching different fields could interleave and have the
  second writer's stale pre-read snapshot silently revert the first one's
  write. Now the whole thing is one critical section.
- save_symbol()/delete_symbol() used to mutate self.symbols in place
  (dict[...]=/pop) AFTER releasing the lock, while every read site elsewhere
  (engine/risk/supervisor) iterates list(store.symbols.values()) on other
  threads without taking that lock - a concurrent add/delete could raise
  "dictionary changed size during iteration". Now symbols is replaced with a
  new dict object (copy-on-write) instead of mutated in place, so an
  in-flight iterator over the old object is never affected.
- save_opt_params(): used to be a raw dict.update(), so a client bug
  serialising a blank numeric field as JSON null persisted None over a
  previously-valid default and crashed the optimizer's background thread
  (int(None)) on the next run. Now follows the same "None means leave this
  field alone" convention as update_symbol()/update_system().
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import store as store_module
from micofx.models import SymbolConfig
from micofx.store import Store


def _fresh_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    return Store()


def test_update_system_concurrent_single_field_writes_both_land(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    assert s.system.running is False
    assert s.system.autostart_bot is False

    errors = []

    def _flip_running():
        for _ in range(200):
            try:
                s.update_system({"running": True})
            except Exception as exc:  # pragma: no cover - surfaced via errors
                errors.append(exc)

    def _flip_autostart():
        for _ in range(200):
            try:
                s.update_system({"autostart_bot": True})
            except Exception as exc:  # pragma: no cover - surfaced via errors
                errors.append(exc)

    t1 = threading.Thread(target=_flip_running)
    t2 = threading.Thread(target=_flip_autostart)
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert not errors
    # Re-read from a second, independent Store instance against the same DB -
    # proves the persisted value, not just this instance's in-memory copy.
    fresh = Store()
    try:
        assert fresh.system.running is True
        assert fresh.system.autostart_bot is True
    finally:
        fresh.close()


def test_symbols_dict_concurrent_mutation_does_not_crash_iteration(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    errors = []
    stop = threading.Event()

    def _writer():
        for i in range(300):
            cfg = SymbolConfig(symbol=f"SYM{i % 20}", magic=990000 + (i % 20))
            try:
                s.save_symbol(cfg)
                if i % 7 == 0:
                    s.delete_symbol(f"SYM{i % 20}")
            except Exception as exc:  # pragma: no cover
                errors.append(exc)
        stop.set()

    def _reader():
        while not stop.is_set():
            try:
                list(s.symbols.values())
                {c.magic for c in s.symbols.values()}
            except RuntimeError as exc:  # the exact crash class being fixed
                errors.append(exc)

    writer = threading.Thread(target=_writer)
    reader = threading.Thread(target=_reader)
    reader.start(); writer.start()
    writer.join(); reader.join()

    assert not errors


def test_save_opt_params_none_does_not_overwrite_existing_default(tmp_path, monkeypatch):
    s = _fresh_store(tmp_path, monkeypatch)
    base = s.opt_params()
    original_lookback = base.get("lookback_days")
    assert original_lookback is not None

    # Simulates the client bug: parseFloat("") -> NaN -> JSON.stringify -> null.
    result = s.save_opt_params({"lookback_days": None, "min_trades": 30})

    assert result["lookback_days"] == original_lookback  # untouched, not None
    assert result["min_trades"] == 30                     # the real value still lands

    fresh = s.opt_params()
    assert fresh["lookback_days"] == original_lookback


def test_next_magic_and_magic_taken_snapshot_iteration(tmp_path, monkeypatch):
    # Defense-in-depth pin: these two must not iterate self.symbols directly
    # (every other call site in the codebase wraps it in list()).
    s = _fresh_store(tmp_path, monkeypatch)
    s.save_symbol(SymbolConfig(symbol="AAA", magic=990101))
    magic = s.next_magic()
    assert magic != 990101
    assert s._magic_taken(990101, avoid_magics=None) is True
    assert s._magic_taken(magic, avoid_magics=None) is False


def test_update_symbol_concurrent_single_field_writes_both_land(tmp_path, monkeypatch):
    """Same lost-update the system config already guarded, for symbols.

    update_symbol() read the config, applied the patch in plain Python, then
    called save_symbol(). Two threads patching DIFFERENT fields of the SAME
    symbol both started from the pre-patch snapshot, so whichever saved second
    wrote back the other's old value - silently reverting a write that had
    already reported success.

    Unlike the copy-on-write rebind (a few bytecodes wide, never observed),
    this window spans a to_dict()/from_dict() round trip and reproduced on
    every single attempt before the fix.
    """
    s = _fresh_store(tmp_path, monkeypatch)
    symbol = next(iter(s.symbols))

    for _ in range(50):
        s.update_symbol(symbol, {"risk_percent": 0.5, "max_positions": 1})
        start = threading.Barrier(2)

        def _patch(field, value):
            start.wait()
            s.update_symbol(symbol, {field: value})

        threads = [threading.Thread(target=_patch, args=("risk_percent", 1.25)),
                   threading.Thread(target=_patch, args=("max_positions", 7))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        cfg = s.symbols[symbol]
        assert cfg.risk_percent == 1.25, "max_positions writer reverted risk_percent"
        assert cfg.max_positions == 7, "risk_percent writer reverted max_positions"


def test_update_symbol_still_returns_the_updated_config(tmp_path, monkeypatch):
    """Holding the lock must not change what callers get back."""
    s = _fresh_store(tmp_path, monkeypatch)
    symbol = next(iter(s.symbols))
    updated = s.update_symbol(symbol, {"risk_percent": 0.75})
    assert updated is not None
    assert updated.risk_percent == 0.75
    assert s.symbols[symbol].risk_percent == 0.75
    assert s.update_symbol("YOK_BOYLE_BIR_SEMBOL", {"risk_percent": 1.0}) is None
