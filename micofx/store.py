from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any

from .logbus import LOG
from .models import OPT_FIELDS, STRATEGIES, TIMEFRAMES, SymbolConfig, SystemConfig
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
-- The panel's own history call passes no symbol (/api/opt/history?limit=80),
-- and the composite above cannot serve an unfiltered ORDER BY created_at:
-- that query was a full table scan plus a sort on every visit to the tab.
CREATE INDEX IF NOT EXISTS idx_opt_created ON opt_runs(created_at DESC);
"""


# Shape guards for values read back out of the settings table.
#
# get_setting() guards the stored value being unparseable JSON. It does not
# guard it being the wrong TYPE, and every caller assumes one: the engine's
# restore block calls .items() on five settings and int()/float() on two more,
# all inside __init__. A list where a dict belongs is valid JSON, so it sails
# past the decode guard and takes the constructor down with an AttributeError -
# which under pythonw.exe goes to a stream nobody reads, so the app simply
# never appears. Store.__init__ already refuses to allow exactly that for a
# corrupt DB *file*, raising a readable RuntimeError instead; the settings
# inside the file had no equivalent.
#
# The element-level guards already at the call sites (``if str(t).isdigit()``,
# ``if isinstance(v, dict)``) show the intent was there - it stopped one level
# short, at the container.
#
# Deliberately module functions rather than Store methods: DailyGuard, Engine
# and Supervisor are all constructed with duck-typed fakes in the tests, and
# growing the Store interface makes every one of those a required update for a
# guard that has nothing to do with what they are testing.

def as_dict(value: Any, key: str = "") -> dict:
    if isinstance(value, dict):
        return value
    if value is not None:
        _warn_shape(key, value, "dict")
    return {}


def as_list(value: Any, key: str = "") -> list:
    if isinstance(value, list):
        return value
    if value is not None:
        _warn_shape(key, value, "list")
    return []


def as_number(value: Any, default: float = 0.0, key: str = "") -> float:
    # bool is an int subclass; a True stored where an epoch belongs is a shape
    # error, not the number 1.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if value is not None:
        _warn_shape(key, value, "sayi")
    return float(default)


def _warn_shape(key: str, value: Any, expected: str) -> None:
    LOG.emit(f"Ayar '{key or '?'}' beklenen tipte degil "
             f"({type(value).__name__}, {expected} bekleniyordu) - "
             f"varsayilana donuldu.", "WARN")


class Store:
    """SQLite-backed configuration store. All public methods are thread safe."""

    def __init__(self) -> None:
        ensure_dirs()
        self._lock = threading.RLock()
        try:
            self._db = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15.0)
            self._db.row_factory = sqlite3.Row
            with self._lock:
                # A second process holding the DB for a moment (backup.py's
                # own Store, a OneDrive/antivirus scan touching the file) used
                # to surface as an immediate "database is locked" that took
                # down whatever thread was writing. Waiting is the correct
                # answer to contention this short; only a genuinely stuck
                # writer should ever reach the caller as an error.
                self._db.execute("PRAGMA busy_timeout=15000")
                self._db.executescript(_SCHEMA)
                self._db.commit()
        except sqlite3.Error as exc:
            # Corrupt file, unreadable path, disk full at boot. Raised as a
            # plain RuntimeError so run.py can report it in Turkish and exit
            # cleanly - under pythonw.exe an uncaught sqlite3 traceback goes
            # to a stream nobody ever sees and the app just vanishes.
            LOG.emit(f"Ayar veritabani acilamadi ({DB_PATH}): {exc}", "ERROR")
            raise RuntimeError(
                f"Ayar veritabani acilamadi: {DB_PATH}\n{exc}\n"
                f"Disk dolu olabilir veya dosya bozulmus olabilir. Dosyayi "
                f"yeniden adlandirip programi tekrar baslatirsaniz varsayilan "
                f"ayarlarla temiz bir veritabani olusturulur."
            ) from exc

        self.defaults = load_defaults()
        self.system = self._load_system()
        self.symbols: dict[str, SymbolConfig] = {}
        self._load_symbols()
        if not self.symbols:
            self.seed_symbols()
        # Panel /api/state stamp. Names alone stayed put when apply_best
        # rewrote OPT_FIELDS, so the 3s poll never refetched /api/symbols.
        self.symbols_rev = 0

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

    # ``running`` flips on every bot start/stop - several times a day under
    # this project's own restart-after-commit habit - and engine.start()/
    # stop() already emit their own "Bot baslatildi"/"Bot durduruldu" INFO
    # line for it. Diffing it here would not add information, only noise
    # that buries the field a human is actually auditing for.
    _SYSTEM_CHANGE_LOG_SKIP = ("running",)

    def _log_system_change(self, before: dict[str, Any], after: dict[str, Any],
                           source: str) -> None:
        """Record which system settings changed, and through which door.

        Same reasoning as ``_log_symbol_change``: ``daily_loss_pct``,
        ``block_high_cost`` and ``charge_costs`` have all been flipped live
        today (13.08 - #21/#25/#29) with nothing but a chat message saying so.
        Unlike the symbol config, ``update_system`` had no audit call at all -
        not even the two-panel-door version ``_log_symbol_change`` started
        from - so every one of those flips was as unattributable as
        ``max_positions`` was before dcd3bb4.
        """
        diff = [f"{k} {before.get(k)!r} -> {after.get(k)!r}"
                for k in sorted(after)
                if k not in self._SYSTEM_CHANGE_LOG_SKIP and before.get(k) != after.get(k)]
        if diff:
            LOG.emit(f"sistem ayari degisti ({source}): {'; '.join(diff)}", "CFG")

    def update_system(self, patch: dict[str, Any], source: str = "bilinmeyen") -> SystemConfig:
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
        # The whole read-modify-write has to be one critical section - two
        # threads (engine poll loop calling start()/stop(), a web request
        # handling a System PATCH) each doing their own separate _load_system()
        # + save_system() around this loop could interleave and have the
        # second writer's stale pre-read snapshot silently revert whatever
        # the first one just wrote. RLock is reentrant, so the get_setting()/
        # set_setting() calls inside _load_system()/save_system() nest fine.
        with self._lock:
            before = self._load_system().to_dict()
            current = dict(before)
            for key, value in patch.items():
                if key in current and value is not None:
                    current[key] = value
            self.system = SystemConfig.from_dict(current)
            self.save_system()
            # Diffed against what actually landed, same as update_symbol():
            # a field submitted at its existing value is not a change, and
            # from_dict()'s own coercion is what should be reported.
            self._log_system_change(before, self.system.to_dict(), source)
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
        from .strategy import opt_fields_read
        dirty: list[SymbolConfig] = []
        with self._lock:
            rows = self._db.execute(
                "SELECT symbol, payload FROM symbols").fetchall()
        known = set(SymbolConfig.__dataclass_fields__)
        for row in rows:
            try:
                raw = json.loads(row["payload"])
            except (json.JSONDecodeError, TypeError):
                continue
            extra = set(raw) - known if isinstance(raw, dict) else set()
            cfg = loaded.get(row["symbol"])
            unread_cost = (
                cfg is not None
                and float(getattr(cfg, "cost_rank_max", 0.0) or 0.0)
                and "cost_rank_max" not in opt_fields_read(cfg.strategy)
            )
            if cfg is not None and (extra or unread_cost):
                dirty.append(cfg)
        for cfg in dirty:
            self.save_symbol(cfg)

    def save_symbol(self, cfg: SymbolConfig, position: int | None = None) -> None:
        from .strategy import opt_fields_read
        if (float(getattr(cfg, "cost_rank_max", 0.0) or 0.0)
                and "cost_rank_max" not in opt_fields_read(cfg.strategy)):
            cfg.cost_rank_max = 0.0
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
            # Replace the dict object rather than mutate it in place. Every
            # engine/risk/supervisor read site takes a reference via
            # list(store.symbols.values()) without holding self._lock (locking
            # every one of those hot-path reads would be its own cost) -
            # mutating the same dict object a concurrent iterator is walking
            # can raise "dictionary changed size during iteration" mid-cycle.
            # Rebinding self.symbols to a brand-new dict never touches the old
            # object, so any iterator already holding a reference to it keeps
            # working against a now-stale-but-internally-consistent snapshot
            # instead of crashing - a single attribute reassignment is atomic
            # under the GIL.
            #
            # Held INSIDE the lock: copy-on-write is what makes unlocked
            # READERS safe, but building the new dict is itself a
            # read-modify-write of self.symbols and only the final assignment
            # is atomic. Two concurrent WRITERS could both read the pre-write
            # dict, and the loser's symbol would be missing from memory while
            # the DB kept both - so it silently reappeared on the next
            # restart. Not reproducible under load here (the window is a few
            # bytecodes wide), but the sequence is genuinely unsynchronised
            # and the lock is already held for the write above, so closing it
            # costs nothing.
            self.symbols = {**self.symbols, cfg.symbol: cfg}
            self.symbols_rev = int(getattr(self, "symbols_rev", 0) or 0) + 1

    # Bulk blobs and their timestamps: they change on every optimizer apply and
    # say nothing a human is auditing for. The fields that actually decide what
    # gets traded - strategy, timeframe, the exit/risk numbers, max_positions,
    # risk_percent - are all outside this set and always reported.
    _CHANGE_LOG_SKIP = ("opt_summary", "opt_updated_at")

    def _log_symbol_change(self, symbol: str, before: dict[str, Any],
                           after: dict[str, Any], source: str) -> None:
        """Record which symbol settings changed, and through which door.

        Lives here rather than in the web layer because this method is the one
        choke point every door goes through: the panel patch, the bulk patch,
        ``Optimizer.apply``/``apply_secondary`` and the engine's own pending
        exit writes. Logging it in web/app.py covered only the two panel doors,
        so the optimizer rewrote strategy, timeframe and the exit numbers on
        four symbols with CFG silent - the audit trail read "nothing changed"
        while the live book was being replaced. One choke point, so a future
        caller cannot get in without leaving a record.
        """
        diff = [f"{k} {before.get(k)!r} -> {after.get(k)!r}"
                for k in sorted(after)
                if k not in self._CHANGE_LOG_SKIP and before.get(k) != after.get(k)]
        if diff:
            LOG.emit(f"{symbol} ayar degisti ({source}): {'; '.join(diff)}", "CFG", symbol)

    def update_symbol(self, symbol: str, patch: dict[str, Any],
                      source: str = "bilinmeyen") -> SymbolConfig | None:
        # The whole read-modify-write is one critical section, for the same
        # reason update_system() already is: two threads patching DIFFERENT
        # fields of the same symbol both start from the config they read here,
        # and the second one to call save_symbol() writes a snapshot that
        # still carries the first one's pre-patch value - silently reverting a
        # write that reported success. Most callers happen to hold
        # engine.entry_lock as well, but not all of them do, and that lock is
        # about positions rather than about this dict. self._lock is an RLock,
        # so the save_symbol() call below re-entering it is fine.
        with self._lock:
            cfg = self.symbols.get(symbol)
            if cfg is None:
                return None
            before = cfg.to_dict()
            current = dict(before)
            for key, value in patch.items():
                if key in current and value is not None:
                    current[key] = value
            current["symbol"] = symbol
            updated = SymbolConfig.from_dict(current)
            self.save_symbol(updated)
            # Diffed against what actually landed, not against the patch: a
            # field submitted at its existing value is not a change, and a
            # field the coercion in from_dict() rewrote reads as what was
            # really stored. A trail that reports writes which never happened
            # is worse than no trail.
            self._log_symbol_change(symbol, before, updated.to_dict(), source)
            return updated

    def delete_symbol(self, symbol: str) -> int:
        """Remove a symbol and the search history keyed to it.

        Returns the number of ``opt_runs`` rows that went with it, NOT whether
        the symbol existed - callers check that upstream (web 404s before
        getting here). Zero therefore means "no search history", not "nothing
        deleted". The count exists because this is an irreversible deletion the
        log used to describe only as "portfoyden silindi": symbols in this book
        carry 11 to 33 rows each, and 196 of them were lost on 14.08 before
        anyone could say how many there had been.
        """
        with self._lock:
            self._db.execute("DELETE FROM symbols WHERE symbol=?", (symbol,))
            gone = self._db.execute("DELETE FROM opt_runs WHERE symbol=?", (symbol,))
            removed = int(gone.rowcount or 0)
            self._db.commit()
            # Same copy-on-write reasoning as save_symbol() above, and held
            # inside the lock for the same reason: a delete racing a save
            # could otherwise resurrect the deleted symbol in memory.
            if symbol in self.symbols:
                self.symbols = {k: v for k, v in self.symbols.items() if k != symbol}
                self.symbols_rev = int(getattr(self, "symbols_rev", 0) or 0) + 1
        if removed > 0:
            LOG.emit(f"{symbol} silindi: {removed} opt_runs kaydi gitti.", "WARN", symbol)
        return removed

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
            removed = int(cur.rowcount or 0)
        if removed > 0:
            LOG.emit(f"yetim opt_runs silindi: {removed} kayit.", "WARN")
        return removed

    def next_magic(self, avoid: set[int] | None = None) -> int:
        # list() snapshot: a concurrent save_symbol()/delete_symbol() now
        # rebinds self.symbols to a new dict object rather than mutating it
        # (see save_symbol()'s comment), so this is defense-in-depth, not
        # load-bearing on its own - but every other iteration site in the
        # codebase already takes this same snapshot, and this one shouldn't
        # be the odd one out.
        used = {c.magic for c in list(self.symbols.values())}
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
        enabled: bool = False,
        avoid_magics: set[int] | None = None,
    ) -> SymbolConfig:
        """Add a product from a group preset; raises ValueError on bad/duplicate names.

        Always born disabled. The caller (and the group preset) may ask for
        enabled=True; that is the hole that put nine unsearched symbols live
        on factory mtf_pullback. Enable is a later, guarded write.
        """
        name = str(symbol or "").strip().upper().replace(" ", "_")
        # The hyphen is not decoration: this broker names 158 tradeable
        # instruments with one - every dated equity CFD (AAPL.US-24) and the
        # perpetuals (BRENTOIL-PERP). Refusing it rejected real symbols with a
        # message that reads like the operator mistyped. Kept deliberately
        # narrow beyond that: the name is a settings key, a dict key and a URL
        # path segment, so no slashes, spaces or punctuation that would change
        # what those mean.
        if not name or not all(ch.isalnum() or ch in "._-" for ch in name):
            raise ValueError("Gecerli bir sembol adi yazin (harf/rakam/_/./-)")
        if name in self.symbols:
            raise ValueError(f"{name} zaten portfoyde")
        presets = self.defaults.get("group_presets", {})
        allowed = set(presets) or {"forex"}
        group = group if group in allowed else next(iter(allowed))
        payload: dict[str, Any] = {
            "symbol": name,
            "group": group,
            "enabled": False,
            "broker_symbol": str(broker_symbol or "").strip(),
        }
        payload.update(presets.get(group, {}))
        payload["symbol"] = name
        payload["group"] = group
        # Risk-based sizing is the live product. A missing/preset-less
        # ``lot_mode`` used to inherit SymbolConfig's old "fixed" default, so
        # every operator-added name sized 0.1 lot and ignored risk_percent.
        payload.setdefault("lot_mode", "risk")
        # Preset / caller True is ignored - same force seed_symbols uses.
        payload["enabled"] = False
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
        self.sort_symbols_by_group()
        cfg = self.symbols[name]
        LOG.emit(f"{name} portfoye eklendi (kapali; optimizasyon sonrasi acilabilir).",
                 "INFO", name)
        return cfg

    GROUP_LABEL = {"forex": "Forex", "index": "Endeks", "commodity": "Emtia",
                   "crypto": "Kripto", "stock": "Hisse"}

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
        if magic in {c.magic for c in list(self.symbols.values())}:
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
            payload.setdefault("lot_mode", "risk")
            # A seeded symbol has no searched config, whatever the template
            # says about ``enabled``. defaults.json carries symbol, group,
            # magic, sessions and the enabled flag; strategy, timeframe and
            # every exit parameter live only in the database, so a fresh
            # install would otherwise start eighteen symbols live on the
            # dataclass default - mtf_pullback/M5, which nothing has validated and
            # which on an FX symbol pays 25-28% of risk in spread against an
            # 18% live ceiling.
            #
            # That is the exact state EURUSD reached tonight, and the API
            # guards added for it (patch_symbol, symbols-bulk) do not cover
            # this path: seeding writes the config directly. So the flag is
            # forced off here and the operator switches a symbol on once it
            # has a config the search chose - which those guards then enforce.
            payload["enabled"] = False
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
            "enabled": False,
            "broker_symbol": cfg.broker_symbol if cfg else "",
        }
        payload.update(self.defaults.get("group_presets", {}).get(group, {}))
        payload.setdefault("lot_mode", "risk")
        if entry:
            payload.update({k: v for k, v in entry.items() if k != "group"})
        payload["symbol"] = symbol
        payload["group"] = group
        payload["broker_symbol"] = cfg.broker_symbol if cfg else ""
        # Unsearched defaults - same force as seed / add_symbol.
        payload["enabled"] = False
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

    # ------------------------------------------------------------- optimizer

    @staticmethod
    def _widen_grid_lists(shipped_val: Any, stored_val: Any) -> Any:
        """Stored list wins order; shipped-only values append (grid widen)."""
        if isinstance(shipped_val, list) and isinstance(stored_val, list):
            out = list(stored_val)
            for item in shipped_val:
                if item not in out:
                    out.append(item)
            return out
        return stored_val

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

        for key in ("strategy_grids", "grid", "strategy_timeframes"):
            ship_map, have = shipped.get(key), base.get(key)
            if isinstance(ship_map, dict) and isinstance(have, dict):
                if key == "strategy_grids":
                    # Per-family axis merge: stored axes win, shipped-only axes
                    # back-fill. List values widen (shipped extras append) so
                    # editing defaults.json trail_step 2.8 reaches a live blob.
                    merged_fams: dict[str, Any] = dict(ship_map)
                    for fam, axes in have.items():
                        if isinstance(axes, dict) and isinstance(merged_fams.get(fam), dict):
                            merged = dict(merged_fams[fam])
                            for axis, val in axes.items():
                                if axis in merged:
                                    merged[axis] = self._widen_grid_lists(
                                        merged[axis], val)
                                else:
                                    merged[axis] = val
                            merged_fams[fam] = merged
                        else:
                            merged_fams[fam] = axes
                    base[key] = merged_fams
                elif key == "grid":
                    merged_grid = dict(ship_map)
                    for axis, val in have.items():
                        if axis in merged_grid:
                            merged_grid[axis] = self._widen_grid_lists(
                                merged_grid[axis], val)
                        else:
                            merged_grid[axis] = val
                    base[key] = merged_grid
                else:
                    base[key] = {**ship_map, **have}

        # A saved blob outlives the code that wrote it. Because the merge above
        # lets the stored copy win, a grid axis that has since been REMOVED from
        # the system would be handed straight back to the optimizer and searched
        # again - which is exactly how a deleted exit parameter (take-profit,
        # scale-out rungs, the time stop) could quietly come back to life on a
        # machine that had pressed Save once, long after the code stopped
        # supporting it. Anything the search cannot legally write to a
        # SymbolConfig has no business being an axis, so filter to OPT_FIELDS.
        allowed = set(OPT_FIELDS)
        if isinstance(base.get("grid"), dict):
            base["grid"] = {k: v for k, v in base["grid"].items() if k in allowed}
        known_fam = set(STRATEGIES)
        if isinstance(base.get("strategy_grids"), dict):
            base["strategy_grids"] = {
                fam: {k: v for k, v in axes.items() if k in allowed}
                for fam, axes in base["strategy_grids"].items()
                if fam in known_fam and isinstance(axes, dict)
            }
        # Same reasoning, one axis over: a stored family->timeframe map outlives
        # the timeframes it was written against. The live blob still carried
        # "M10" for micro_rev and burst, a bar this system stopped offering -
        # inert only because the search never asks about a timeframe outside
        # TIMEFRAMES, which makes it exactly the kind of crumb that reads as
        # configuration when someone opens the panel. Drop what can no longer
        # be searched; a family left with nothing keeps an empty list, which
        # strategy_allows_timeframe already reads as a deliberate "nothing".
        if isinstance(base.get("strategy_timeframes"), dict):
            base["strategy_timeframes"] = {
                fam: [t for t in tfs if t in TIMEFRAMES]
                for fam, tfs in base["strategy_timeframes"].items()
                if fam in known_fam and isinstance(tfs, list)
            }
        if isinstance(base.get("timeframes"), list):
            base["timeframes"] = [t for t in base["timeframes"] if t in TIMEFRAMES]
        # Same class as the TF/axis filters: a saved strategies list outlives
        # the families it named. Drop here so GET and the next merge stay
        # honest; save_opt_params applies the same drop so a POST cannot
        # write them back.
        self._drop_unsearchable_families(base)
        # Same reasoning for the whole exit-style block: the optimizer no longer
        # splits a family into targeted/trail sweeps because there is only one
        # exit regime left, so a stored block is dead weight, not configuration.
        base.pop("exit_styles", None)
        return base

    def save_opt_params(self, params: dict[str, Any]) -> dict[str, Any]:
        base = self.opt_params()
        # Same "None means leave this field alone" convention as
        # update_symbol()/update_system() - a raw dict.update() let a client
        # bug that serialises a blank numeric input as JSON null overwrite a
        # previously-valid default with None, which then crashes the
        # optimizer's background thread the next time it runs (int(None)).
        for key, value in params.items():
            if value is not None:
                base[key] = value
        self._drop_unsearchable_families(base)
        self.set_setting("opt_params", base)
        return base

    @staticmethod
    def _drop_unsearchable_families(base: dict[str, Any]) -> None:
        """Leftover family names are not configuration. They cannot be searched."""
        known = set(STRATEGIES)
        if isinstance(base.get("strategies"), list):
            base["strategies"] = [s for s in base["strategies"] if s in known]
        for key in ("strategy_grids", "strategy_max_combos", "strategy_timeframes"):
            blob = base.get(key)
            if isinstance(blob, dict):
                base[key] = {fam: val for fam, val in blob.items() if fam in known}

    def reset_opt_params(self) -> dict[str, Any]:
        self.set_setting("opt_params", {})
        return self.opt_params()

    def stamp_opt_run_apply(self, run_id: int, force: bool, previous: dict[str, Any] | None,
                            applied_at: float) -> bool:
        """Merge G11's apply-path fields into an existing search row.

        The panel's history/results apply does not go through
        ``Optimizer._finish_symbol``, so without this the search row stayed
        ``applied=0`` and key-less while the live book changed. Updating the
        row keeps one candidate as one identity; a second insert would
        double-count ``applied`` and split what the panel already shows.

        Returns False when ``run_id`` is gone (retention already trimmed it)
        so the caller can insert instead of pretending the stamp landed.
        """
        with self._lock:
            row = self._db.execute(
                "SELECT payload FROM opt_runs WHERE id=?", (int(run_id),)
            ).fetchone()
            if row is None:
                return False
            try:
                blob = json.loads(row["payload"]) if row["payload"] else {}
            except json.JSONDecodeError:
                blob = {}
            if not isinstance(blob, dict):
                blob = {}
            blob["force"] = bool(force)
            blob["applied_at"] = float(applied_at)
            blob["previous"] = previous
            self._db.execute(
                "UPDATE opt_runs SET payload=?, applied=1 WHERE id=?",
                (json.dumps(blob, ensure_ascii=False), int(run_id)),
            )
            self._db.commit()
            return True

    def record_opt_run(self, symbol: str, score: float, payload: dict[str, Any], applied: bool) -> int:
        blob = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO opt_runs(symbol, created_at, score, applied, payload) VALUES(?,?,?,?,?)",
                (symbol, time.time(), float(score), 1 if applied else 0, blob),
            )
            trimmed = self._db.execute(
                "DELETE FROM opt_runs WHERE symbol=? AND id NOT IN "
                "(SELECT id FROM opt_runs WHERE symbol=? ORDER BY created_at DESC LIMIT 40)",
                (symbol, symbol),
            )
            self._db.commit()
            n_trim = int(trimmed.rowcount or 0)
        if n_trim > 0:
            LOG.emit(f"{symbol}: opt_runs kirpildi ({n_trim} kayit).", "OPT", symbol)
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
            # Columns last. They are the authoritative copy - the retention
            # sweep keeps the newest 40 by created_at and the ordering above
            # uses it - so a payload key of the same name must not be able to
            # report a different number than the one the database ranks by.
            # The blob still supplies everything the columns do not.
            out.append({
                **payload,
                "id": row["id"], "symbol": row["symbol"], "created_at": row["created_at"],
                "score": row["score"], "applied": bool(row["applied"]),
            })
        return out
