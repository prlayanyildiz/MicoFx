from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any

from .logbus import LOG
from .models import SymbolConfig, SystemConfig
from .paths import DB_PATH, ensure_dirs, load_defaults

_SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS symbols (
    symbol   TEXT PRIMARY KEY,
    position INTEGER NOT NULL DEFAULT 0,
    payload  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opt_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol     TEXT NOT NULL,
    created_at REAL NOT NULL,
    score      REAL NOT NULL,
    applied    INTEGER NOT NULL DEFAULT 0,
    payload    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opt_symbol ON opt_runs(symbol, created_at DESC);
"""


class Store:
    """SQLite-backed configuration store. All public methods are thread safe."""

    def __init__(self) -> None:
        ensure_dirs()
        self._lock = threading.RLock()
        self._db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.executescript(_SCHEMA)
            self._db.commit()

        self.defaults = load_defaults()
        self.system = self._load_system()
        self.symbols: dict[str, SymbolConfig] = {}
        self._load_symbols()
        if not self.symbols:
            self.seed_symbols()

    # ------------------------------------------------------------------ misc

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return default

    def set_setting(self, key: str, value: Any) -> None:
        blob = json.dumps(value, ensure_ascii=False)
        with self._lock:
            self._db.execute(
                "INSERT INTO settings(key, value) VALUES(?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, blob),
            )
            self._db.commit()

    # ---------------------------------------------------------------- system

    def _load_system(self) -> SystemConfig:
        stored = self.get_setting("system")
        base = dict(self.defaults.get("system", {}))
        if isinstance(stored, dict):
            base.update(stored)
        return SystemConfig.from_dict(base)

    def save_system(self) -> None:
        self.set_setting("system", self.system.to_dict())

    def update_system(self, patch: dict[str, Any]) -> SystemConfig:
        """Merge ``patch`` onto the *persisted* system config, not the in-memory copy.

        Two ``Store`` instances (the live app process and any one-off script or
        second process touching the same DB) each hold their own in-memory
        ``self.system``. Basing the merge on ``self.system.to_dict()`` meant
        whichever instance saved *last* - even for an unrelated field, e.g.
        ``engine.start()``/``stop()`` only ever meaning to flip ``running`` -
        overwrote every other field with its own stale snapshot, silently
        reverting changes made through the other instance. Re-reading the
        stored blob fresh here makes concurrent single-field writes commute
        instead of clobbering each other.
        """
        current = self._load_system().to_dict()
        for key, value in patch.items():
            if key in current and value is not None:
                current[key] = value
        self.system = SystemConfig.from_dict(current)
        self.save_system()
        return self.system

    # --------------------------------------------------------------- symbols

    def _load_symbols(self) -> None:
        with self._lock:
            rows = self._db.execute("SELECT payload FROM symbols ORDER BY position, symbol").fetchall()
        loaded: dict[str, SymbolConfig] = {}
        for row in rows:
            try:
                cfg = SymbolConfig.from_dict(json.loads(row["payload"]))
            except (json.JSONDecodeError, TypeError) as exc:
                LOG.emit(f"Sembol kaydi okunamadi: {exc}", "ERROR")
                continue
            loaded[cfg.symbol] = cfg
        self.symbols = loaded

    def save_symbol(self, cfg: SymbolConfig, position: int | None = None) -> None:
        blob = json.dumps(cfg.to_dict(), ensure_ascii=False)
        with self._lock:
            if position is None:
                row = self._db.execute(
                    "SELECT position FROM symbols WHERE symbol=?", (cfg.symbol,)
                ).fetchone()
                position = int(row["position"]) if row else len(self.symbols)
            self._db.execute(
                "INSERT INTO symbols(symbol, position, payload) VALUES(?, ?, ?) "
                "ON CONFLICT(symbol) DO UPDATE SET payload=excluded.payload, position=excluded.position",
                (cfg.symbol, position, blob),
            )
            self._db.commit()
        self.symbols[cfg.symbol] = cfg

    def update_symbol(self, symbol: str, patch: dict[str, Any]) -> SymbolConfig | None:
        cfg = self.symbols.get(symbol)
        if cfg is None:
            return None
        current = cfg.to_dict()
        for key, value in patch.items():
            if key in current and value is not None:
                current[key] = value
        current["symbol"] = symbol
        updated = SymbolConfig.from_dict(current)
        self.save_symbol(updated)
        return updated

    def delete_symbol(self, symbol: str) -> bool:
        with self._lock:
            cur = self._db.execute("DELETE FROM symbols WHERE symbol=?", (symbol,))
            self._db.execute("DELETE FROM opt_runs WHERE symbol=?", (symbol,))
            self._db.commit()
        self.symbols.pop(symbol, None)
        return cur.rowcount > 0

    def purge_orphan_history(self) -> int:
        keep = list(self.symbols)
        with self._lock:
            if keep:
                placeholders = ",".join("?" * len(keep))
                cur = self._db.execute(
                    f"DELETE FROM opt_runs WHERE symbol NOT IN ({placeholders})", keep
                )
            else:
                cur = self._db.execute("DELETE FROM opt_runs")
            self._db.commit()
            return int(cur.rowcount or 0)

    def next_magic(self, avoid: set[int] | None = None) -> int:
        used = {c.magic for c in self.symbols.values()}
        # A magic still tied to a pending secondary_orphan_scan window
        # (engine.py's H1 tracking) has a fill that may not be visible in
        # client.positions() yet - handing it straight back out here would
        # let a brand new symbol's own fill land under the same magic the
        # scan is still watching, and _scan_orphan_candidates() would then
        # force-close it as the "delayed orphan ticket" it is not. Readable
        # from settings alone, no client needed, so every caller gets this
        # protection for free. ``avoid`` additionally covers still-open
        # orphan_tickets' live magics - that needs client.positions() to
        # resolve, which this storage-layer method has no access to, so
        # callers that can see the broker connection pass it in.
        scan = self.get_setting("secondary_orphan_scan", {}) or {}
        if isinstance(scan, dict):
            used |= {int(v.get("magic", -1)) for v in scan.values() if isinstance(v, dict)}
        if avoid:
            used |= {int(m) for m in avoid}
        magic = 990101
        while magic in used:
            magic += 1
        return magic

    def add_symbol(
        self,
        symbol: str,
        group: str = "forex",
        broker_symbol: str = "",
        magic: int | None = None,
        enabled: bool = True,
        avoid_magics: set[int] | None = None,
    ) -> SymbolConfig:
        """Add a product from a group preset; raises ValueError on bad/duplicate names."""
        name = str(symbol or "").strip().upper().replace(" ", "_")
        if not name or not all(ch.isalnum() or ch in "._" for ch in name):
            raise ValueError("Gecerli bir sembol adi yazin (harf/rakam/_/.)")
        if name in self.symbols:
            raise ValueError(f"{name} zaten portfoyde")
        presets = self.defaults.get("group_presets", {})
        allowed = set(presets) or {"forex"}
        group = group if group in allowed else next(iter(allowed))
        payload: dict[str, Any] = {
            "symbol": name,
            "group": group,
            "enabled": bool(enabled),
            "broker_symbol": str(broker_symbol or "").strip(),
        }
        payload.update(presets.get(group, {}))
        payload["symbol"] = name
        payload["group"] = group
        payload["enabled"] = bool(enabled)
        payload["broker_symbol"] = str(broker_symbol or "").strip()
        if magic is not None:
            payload["magic"] = int(magic)
        else:
            wanted = payload.get("magic")
            if wanted is None or self._magic_taken(int(wanted), avoid_magics):
                payload["magic"] = self.next_magic(avoid=avoid_magics)
            else:
                payload["magic"] = int(wanted)
        cfg = SymbolConfig.from_dict(payload)
        self.save_symbol(cfg, position=len(self.symbols))
        if self.system.max_total_positions < len(self.symbols):
            self.update_system({"max_total_positions": len(self.symbols)})
        self.sort_symbols_by_group()
        cfg = self.symbols[name]
        LOG.emit(f"{name} portfoye eklendi.", "INFO", name)
        return cfg

    GROUP_LABEL = {"forex": "Forex", "index": "Endeks", "commodity": "Emtia", "crypto": "Kripto"}

    def sort_symbols_by_group(self) -> list[str]:
        """Reorder the portfolio alphabetically by group label, then by symbol name within each group."""
        ordered = sorted(
            self.symbols.values(),
            key=lambda c: (self.GROUP_LABEL.get(c.group, c.group), c.symbol),
        )
        for idx, cfg in enumerate(ordered):
            self.save_symbol(cfg, position=idx)
        self._load_symbols()
        return [c.symbol for c in ordered]

    def replace_with_defaults(self) -> int:
        """Wipe user portfolio and reload the shipped starter list."""
        for symbol in list(self.symbols):
            self.delete_symbol(symbol)
        # Drop persisted orphan windows before writing fixed default magics.
        # Web already refuses overwrite while any scan is pending on the
        # portfolio; clearing here also covers a stale settings entry for a
        # symbol that is no longer in the book, so defaults.json magics
        # cannot collide with a ghost scan (L-R1).
        self.set_setting("secondary_orphan_scan", {})
        self.set_setting("secondary_orphan_tickets", [])
        seeded = self.seed_symbols(overwrite=True)
        self.purge_orphan_history()
        return seeded

    def _magic_taken(self, magic: int, avoid_magics: set[int] | None) -> bool:
        if magic in {c.magic for c in self.symbols.values()}:
            return True
        scan = self.get_setting("secondary_orphan_scan", {}) or {}
        if isinstance(scan, dict) and magic in {
            int(v.get("magic", -1)) for v in scan.values() if isinstance(v, dict)
        }:
            return True
        if avoid_magics and magic in {int(m) for m in avoid_magics}:
            return True
        return False

    def seed_symbols(self, overwrite: bool = False, avoid_magics: set[int] | None = None) -> int:
        """Create symbol rows from config/defaults.json group presets.

        Soft-seed (``overwrite=False``) only ever adds symbols missing from
        the portfolio, but defaults.json ships each entry with a *fixed*
        magic - if that magic was since freed (its symbol deleted) and handed
        out again by next_magic() to something else, or is still owned by a
        pending secondary_orphan_scan window or a live orphan ticket, writing
        it back verbatim collides. engine.py's by_magic lookup is last-write-
        wins, so two symbols sharing a magic silently means one manages the
        other's position (H1). ``overwrite=True`` wipes the whole portfolio
        first (see replace_with_defaults) so no such clash is possible there.
        """
        presets = self.defaults.get("group_presets", {})
        seeded = 0
        for idx, entry in enumerate(self.defaults.get("symbols", [])):
            symbol = entry.get("symbol")
            if not symbol or (not overwrite and symbol in self.symbols):
                continue
            group = entry.get("group", "forex")
            payload: dict[str, Any] = {"symbol": symbol, "group": group, "enabled": True}
            payload.update(presets.get(group, {}))
            payload.update({k: v for k, v in entry.items() if k != "group"})
            if not overwrite:
                wanted = payload.get("magic")
                if wanted is None or self._magic_taken(int(wanted), avoid_magics):
                    new_magic = self.next_magic(avoid=avoid_magics)
                    if wanted is not None and int(wanted) != new_magic:
                        LOG.emit(
                            f"{symbol}: soft-seed magic {int(wanted)} -> {new_magic} "
                            f"(cakisma onlendi)", "INFO", symbol)
                    payload["magic"] = new_magic
            self.save_symbol(SymbolConfig.from_dict(payload), position=idx)
            seeded += 1
        if seeded:
            self.sort_symbols_by_group()
            LOG.emit(f"{seeded} sembol varsayilan ayarlarla yuklendi.", "INFO")
        return seeded

    def reset_symbol_to_preset(self, symbol: str, avoid_magics: set[int] | None = None) -> SymbolConfig | None:
        entry = next((e for e in self.defaults.get("symbols", []) if e.get("symbol") == symbol), None)
        cfg = self.symbols.get(symbol)
        if cfg is None and entry is None:
            return None
        group = (entry or {}).get("group") or (cfg.group if cfg else "forex")
        payload: dict[str, Any] = {
            "symbol": symbol,
            "group": group,
            "enabled": True,
            "broker_symbol": cfg.broker_symbol if cfg else "",
        }
        payload.update(self.defaults.get("group_presets", {}).get(group, {}))
        if entry:
            payload.update({k: v for k, v in entry.items() if k != "group"})
        payload["symbol"] = symbol
        payload["group"] = group
        payload["broker_symbol"] = cfg.broker_symbol if cfg else ""
        # Existing symbol keeps its magic. Recreate (cfg is None) must use the
        # same clash avoid soft-seed does - defaults.json ships a fixed magic
        # that may already be owned by another symbol / orphan scan / ticket.
        if cfg is not None:
            payload["magic"] = cfg.magic
        else:
            wanted = payload.get("magic")
            if wanted is None or self._magic_taken(int(wanted), avoid_magics):
                new_magic = self.next_magic(avoid=avoid_magics)
                if wanted is not None and int(wanted) != new_magic:
                    LOG.emit(
                        f"{symbol}: reset-recreate magic {int(wanted)} -> {new_magic} "
                        f"(cakisma onlendi)", "INFO", symbol)
                payload["magic"] = new_magic
            else:
                payload["magic"] = int(wanted)
        updated = SymbolConfig.from_dict(payload)
        self.save_symbol(updated)
        return updated

    def enabled_symbols(self) -> list[SymbolConfig]:
        return [c for c in self.symbols.values() if c.enabled]

    # ------------------------------------------------------------- optimizer

    def opt_params(self) -> dict[str, Any]:
        """Shipped optimizer defaults with the user's saved overrides on top.

        Saving from the UI persists the whole merged blob, so a plain update()
        would freeze the search at whatever families and grid axes existed the
        day the user last pressed save - a newly shipped strategy family or grid
        axis would never be searched again. Anything the user has an opinion
        about still wins; only keys they have never seen get back-filled.
        """
        stored = self.get_setting("opt_params")
        shipped = dict(self.defaults.get("optimizer", {}))
        base = dict(shipped)
        if not isinstance(stored, dict):
            return base
        base.update(stored)

        families = shipped.get("strategies")
        if isinstance(base.get("strategies"), list) and isinstance(families, list):
            known = set(base["strategies"])
            base["strategies"] = list(base["strategies"]) + [f for f in families if f not in known]

        for key in ("strategy_grids", "exit_styles", "grid", "strategy_timeframes"):
            ship_map, have = shipped.get(key), base.get(key)
            if isinstance(ship_map, dict) and isinstance(have, dict):
                base[key] = {**ship_map, **have}
        return base

    def save_opt_params(self, params: dict[str, Any]) -> dict[str, Any]:
        base = self.opt_params()
        base.update(params)
        self.set_setting("opt_params", base)
        return base

    def reset_opt_params(self) -> dict[str, Any]:
        self.set_setting("opt_params", {})
        return self.opt_params()

    def record_opt_run(self, symbol: str, score: float, payload: dict[str, Any], applied: bool) -> int:
        blob = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO opt_runs(symbol, created_at, score, applied, payload) VALUES(?,?,?,?,?)",
                (symbol, time.time(), float(score), 1 if applied else 0, blob),
            )
            self._db.execute(
                "DELETE FROM opt_runs WHERE symbol=? AND id NOT IN "
                "(SELECT id FROM opt_runs WHERE symbol=? ORDER BY created_at DESC LIMIT 40)",
                (symbol, symbol),
            )
            self._db.commit()
            return int(cur.lastrowid or 0)

    def clear_opt_history(self, symbol: str | None = None) -> int:
        with self._lock:
            if symbol:
                cur = self._db.execute("DELETE FROM opt_runs WHERE symbol=?", (symbol,))
            else:
                cur = self._db.execute("DELETE FROM opt_runs")
            self._db.commit()
            return int(cur.rowcount or 0)

    def opt_history(self, symbol: str | None = None, limit: int = 60) -> list[dict[str, Any]]:
        sql = "SELECT id, symbol, created_at, score, applied, payload FROM opt_runs"
        args: tuple = ()
        if symbol:
            sql += " WHERE symbol=?"
            args = (symbol,)
        sql += " ORDER BY created_at DESC LIMIT ?"
        args += (int(limit),)
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
        out = []
        for row in rows:
            try:
                payload = json.loads(row["payload"])
            except json.JSONDecodeError:
                payload = {}
            out.append({
                "id": row["id"], "symbol": row["symbol"], "created_at": row["created_at"],
                "score": row["score"], "applied": bool(row["applied"]), **payload,
            })
        return out
