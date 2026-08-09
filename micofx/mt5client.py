from __future__ import annotations

import math
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from .logbus import LOG

try:
    import MetaTrader5 as mt5
except ImportError:  # pragma: no cover - the package is Windows only
    mt5 = None  # type: ignore

_FALLBACK_PATHS: list[str] = []  # never auto-pick; path must be set in Sistem

# Rejects that will not clear up by polling the same bar again - a config or
# account-state problem, not a momentary quote/margin blip. Retrying these
# every ~1s poll until the bar closes is pure order_send spam; the caller
# should clear the pending signal instead of re-offering it. Deliberately
# narrow: ambiguous/generic reject codes stay in the retry path, since a false
# positive here throws away a fill that would have gone through.
NON_RETRYABLE_RETCODES: frozenset[int] = frozenset(
    {getattr(mt5, name) for name in
     ("TRADE_RETCODE_TRADE_DISABLED", "TRADE_RETCODE_MARKET_CLOSED",
      "TRADE_RETCODE_INVALID_VOLUME", "TRADE_RETCODE_NO_MONEY")
     if mt5 is not None and hasattr(mt5, name)}
)

# Both mean a position actually exists on the broker afterwards - DONE_PARTIAL
# is an IOC order that filled less than the requested volume, not a rejection.
_FILL_RETCODES: frozenset[int] = frozenset(
    {getattr(mt5, name) for name in
     ("TRADE_RETCODE_DONE", "TRADE_RETCODE_DONE_PARTIAL")
     if mt5 is not None and hasattr(mt5, name)}
)

_INFO_TTL = 120.0
_TICK_TTL = 0.5
_RECONNECT_COOLDOWN = 5.0


def timeframe_const(name: str) -> int:
    if mt5 is None:
        return 0
    table = {
        "M5": mt5.TIMEFRAME_M5, "M10": mt5.TIMEFRAME_M10, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
    }
    return table.get(str(name).upper(), mt5.TIMEFRAME_M5)


def timeframe_seconds(name: str) -> int:
    table = {"M5": 300, "M10": 600, "M15": 900, "M30": 1800, "H1": 3600, "H4": 14400}
    return table.get(str(name).upper(), 300)


class Bars:
    """Closed-bar OHLC window plus the timestamp of the still-forming bar."""

    __slots__ = ("time", "open", "high", "low", "close", "spread", "volume", "forming_time")

    def __init__(self, rates: np.ndarray, forming_time: int) -> None:
        self.time = rates["time"].astype(np.int64)
        self.open = rates["open"].astype(np.float64)
        self.high = rates["high"].astype(np.float64)
        self.low = rates["low"].astype(np.float64)
        self.close = rates["close"].astype(np.float64)
        self.spread = rates["spread"].astype(np.float64)
        self.volume = rates["tick_volume"].astype(np.float64)
        self.forming_time = forming_time

    def __len__(self) -> int:
        return int(self.close.size)

    @property
    def last_closed_time(self) -> int:
        return int(self.time[-1]) if self.time.size else 0


class MT5Client:
    """Serialised access to the MetaTrader 5 terminal.

    The MT5 python binding is not thread safe, so every call funnels through one
    reentrant lock shared by the trading loop, the optimizer and the web API.
    """

    def __init__(self, terminal_path: str = "") -> None:
        self._lock = threading.RLock()
        self.terminal_path = (terminal_path or "").strip()
        self.connected = False
        self.last_error = ""
        self._last_attempt = 0.0
        self._info_cache: dict[str, tuple[float, Any]] = {}
        self._tick_cache: dict[str, tuple[float, dict[str, float]]] = {}
        self._name_map: dict[str, str] = {}
        self._overrides: dict[str, str] = {}
        self._symbol_names_cache: list[str] = []
        self._symbol_names_at: float = 0.0

    def set_terminal_path(self, path: str) -> None:
        """Pin this process to one terminal64.exe; empty means refuse auto-attach."""
        self.terminal_path = (path or "").strip()

    @staticmethod
    def _exe_from_path(path: str) -> Path | None:
        p = Path(path)
        exe = p if p.suffix.lower() == ".exe" else p / "terminal64.exe"
        return exe if exe.exists() else None

    def terminal_process_running(self) -> bool:
        """Best-effort check whether *any* terminal64.exe process is alive.

        This is a coarse OS-level check (Windows tasklist can't cheaply tell
        us *which* install a running terminal64.exe belongs to), used only to
        decide whether autostart needs to launch a new process. The strict
        path lock in ``connect()``/``_paths_compatible`` still runs afterwards
        and is what actually verifies the attached terminal matches
        ``mt5_terminal_path`` - autostart never substitutes for that check.
        """
        try:
            check = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/NH"],
                capture_output=True, text=True, timeout=15,
            )
            out = ((check.stdout or "") + (check.stderr or "")).lower()
            return "terminal64.exe" in out
        except Exception:
            return False

    def ensure_terminal_process(self) -> bool:
        """Launch the *configured* terminal64.exe if it is not already running.

        Optional convenience (``system.autostart_mt5``, off by default). Only
        ever launches the exe pointed to by ``self.terminal_path`` - it never
        picks a fallback install, so it cannot bypass the strict path lock.
        """
        if self.terminal_process_running():
            return True
        exe = self._exe_from_path(self.terminal_path) if self.terminal_path else None
        if exe is None:
            self.last_error = (
                "MT5 otomatik baslatma icin gecerli bir yol yok - "
                "Sistem sekmesinde mt5_terminal_path alanini doldurun."
            )
            return False
        try:
            subprocess.Popen(
                [str(exe)],
                cwd=str(exe.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            LOG.emit(f"MT5 terminali baslatiliyor: {exe}", "INFO")
            return True
        except Exception as exc:
            self.last_error = f"MT5 baslatilamadi: {exc}"
            LOG.emit(self.last_error, "ERROR")
            return False

    def set_overrides(self, mapping: dict[str, str]) -> None:
        """Pin config symbols to exact broker names, bypassing fuzzy matching."""
        cleaned = {k: v.strip() for k, v in mapping.items() if v and v.strip()}
        if cleaned == self._overrides:
            return
        self._overrides = cleaned
        self._name_map.clear()
        self._info_cache.clear()
        self._tick_cache.clear()
        self._symbol_names_cache = []
        self._symbol_names_at = 0.0

    def _broker_symbol_names(self) -> list[str]:
        """Cached broker symbol names; symbols_get() is expensive on large books."""
        now = time.time()
        if self._symbol_names_cache and now - self._symbol_names_at < 60.0:
            return self._symbol_names_cache
        with self._lock:
            if not self.connected:
                return []
            names = [s.name for s in (mt5.symbols_get() or [])]
        self._symbol_names_cache = names
        self._symbol_names_at = now
        return names

    def search_symbols(self, query: str = "", limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            if not self.connected:
                return []
            everything = mt5.symbols_get() or []
        self._symbol_names_cache = [s.name for s in everything]
        self._symbol_names_at = time.time()
        q = query.strip().upper()
        hits = []
        for s in everything:
            if q and q not in s.name.upper() and q not in (s.description or "").upper():
                continue
            hits.append({"name": s.name, "description": s.description, "path": s.path,
                         "visible": bool(s.visible)})
            if len(hits) >= limit:
                break
        return hits

    # ------------------------------------------------------------- lifecycle

    @staticmethod
    def _read_origin(data_dir: Path) -> Path | None:
        """MT5 data folder origin.txt -> install directory (when path is AppData)."""
        origin = data_dir / "origin.txt"
        if not origin.is_file():
            return None
        raw = origin.read_bytes()
        for enc in ("utf-16", "utf-16-le", "utf-8-sig", "utf-8", "cp1254"):
            try:
                text = raw.decode(enc).replace("\x00", "").strip()
            except Exception:
                continue
            if not text:
                continue
            p = Path(text)
            return p.resolve() if p.exists() else p
        return None

    @classmethod
    def _paths_compatible(cls, expected_exe: str, info: Any) -> tuple[bool, str]:
        """True when the attached terminal belongs to the configured install."""
        exp = Path(expected_exe).resolve()
        exp_dir = exp.parent
        actual = getattr(info, "path", "") or ""
        data_path = getattr(info, "data_path", "") or ""
        hints: list[str] = []
        for candidate in (actual, data_path):
            if not candidate:
                continue
            p = Path(candidate)
            hints.append(str(p))
            try:
                resolved = p.resolve()
            except Exception:
                resolved = p
            if resolved == exp or resolved == exp_dir:
                return True, str(resolved)
            if exp_dir.name and exp_dir.name.lower() in str(resolved).lower():
                return True, str(resolved)
            origin = cls._read_origin(p)
            if origin is None:
                continue
            hints.append(f"origin={origin}")
            try:
                o = origin.resolve()
            except Exception:
                o = origin
            if o == exp or o == exp_dir or (o / "terminal64.exe") == exp:
                return True, str(o)
        return False, " | ".join(hints) or "(bos)"

    def connect(self) -> bool:
        """Attach only to the configured terminal path.

        Bare ``mt5.initialize()`` latches onto whichever MT5 is already running,
        which mixes BIST and FX terminals when both apps are open. Path is
        mandatory; after attach we verify the install matches or we disconnect.
        """
        with self._lock:
            if mt5 is None:
                self.last_error = "MetaTrader5 paketi kurulu degil (pip install MetaTrader5)"
                LOG.emit(self.last_error, "ERROR")
                return False

            try:
                mt5.shutdown()
            except Exception:
                pass
            self.connected = False

            if not self.terminal_path:
                self.last_error = (
                    "MT5 terminal yolu bos. Sistem > MT5 terminal yoluna "
                    "istediginiz terminal64.exe yolunu yazin (kayit otomatik baglar)."
                )
                LOG.emit(self.last_error, "ERROR")
                return False

            exe = self._exe_from_path(self.terminal_path)
            if exe is None:
                self.last_error = f"MT5 yolu bulunamadi: {self.terminal_path}"
                LOG.emit(self.last_error, "ERROR")
                return False
            path = str(exe)

            try:
                mt5.shutdown()
            except Exception:
                pass
            if not mt5.initialize(path=path):
                code, text = mt5.last_error()
                self.last_error = f"MT5 baglantisi kurulamadi ({code}: {text}) | denenen: {path}"
                self.connected = False
                LOG.emit(self.last_error, "ERROR")
                return False
            return self._after_connect(expected=path)

    def _after_connect(self, expected: str | None = None) -> bool:
        info = mt5.terminal_info()
        acc = mt5.account_info()
        if info is None:
            try:
                mt5.shutdown()
            except Exception:
                pass
            self.connected = False
            self.last_error = "MT5 initialize oldu ama terminal_info bos"
            LOG.emit(self.last_error, "ERROR")
            return False

        if expected:
            ok_path, detail = self._paths_compatible(expected, info)
            if not ok_path:
                broker = getattr(info, "company", "?")
                try:
                    mt5.shutdown()
                except Exception:
                    pass
                self.connected = False
                self.last_error = (
                    f"Yanlis MT5 terminaline yapisti (isten: {expected} | "
                    f"baglanan: {detail} | {broker}). "
                    "Dogru terminali acik tutup Yeniden Baglan deyin."
                )
                LOG.emit(self.last_error, "ERROR")
                return False

        self.connected = True
        self.last_error = ""
        self._info_cache.clear()
        self._tick_cache.clear()
        self._name_map.clear()
        self._symbol_names_cache = []
        self._symbol_names_at = 0.0
        broker = getattr(info, "company", "?")
        login = getattr(acc, "login", "?") if acc is not None else "?"
        server = getattr(acc, "server", "?") if acc is not None else "?"
        LOG.emit(f"MT5 baglandi | {broker} | hesap {login} @ {server}", "INFO")
        if expected:
            LOG.emit(f"MT5 terminal: {expected}", "INFO")
        if not getattr(info, "trade_allowed", True):
            LOG.emit("MT5 terminalinde AutoTrading kapali - emirler reddedilir.", "WARN")
        return True

    def ensure(self) -> bool:
        with self._lock:
            if self.connected:
                exc_detail = None
                try:
                    if mt5.terminal_info() is not None:
                        return True
                except Exception as exc:
                    exc_detail = str(exc)
                self.connected = False
                # This is the drop path a running bot actually hits (terminal
                # closed, VPS network blip, MT5 crash) - ensure() runs every
                # cycle and used to flip connected=False here with no log at
                # all, so a live disconnect left only a transient UI flag
                # behind, nothing in the log to say it happened or why.
                try:
                    reason = exc_detail or str(mt5.last_error())
                except Exception:
                    reason = exc_detail or "?"
                self.last_error = f"MT5 baglantisi koptu ({reason})"
                LOG.emit(self.last_error, "ERROR")
            if time.time() - self._last_attempt < _RECONNECT_COOLDOWN:
                return False
            self._last_attempt = time.time()
            return self.connect()

    def reconnect(self) -> bool:
        with self._lock:
            self._last_attempt = 0.0
            return self.connect()

    def shutdown(self) -> None:
        with self._lock:
            try:
                mt5.shutdown()
            except Exception:
                pass
            self.connected = False

    # ---------------------------------------------------------------- account

    def account(self) -> dict[str, Any]:
        with self._lock:
            if not self.connected:
                return {}
            a = mt5.account_info()
        if a is None:
            # Same failure as positions_get() returning None: the call itself
            # broke mid-cycle, not "no account data". Mark disconnected so the
            # next ensure() reconnects instead of engine.refresh_account
            # quietly reusing a stale balance/equity snapshot forever.
            self.connected = False
            LOG.emit(f"account_info basarisiz oldu ({mt5.last_error()}) - "
                     "baglanti koptu olarak isaretlendi.", "WARN")
            return {}
        return {
            "login": a.login, "server": a.server, "currency": a.currency,
            "balance": a.balance, "equity": a.equity, "profit": a.profit,
            "margin": a.margin, "margin_free": a.margin_free,
            "margin_level": a.margin_level, "leverage": a.leverage,
            "name": a.name, "trade_allowed": bool(a.trade_allowed),
            # Every position-count guard in this app (max_positions,
            # max_total_positions, weekend/secondary ticket tracking) assumes
            # one ticket per opened trade - true only under retail hedging.
            # Both retail netting AND exchange-traded accounts auto-merge
            # same-direction trades on a symbol into one ticket, so "not
            # hedging" (not just "is retail-netting") is the actual
            # condition that breaks those assumptions.
            "netting": getattr(a, "margin_mode", None) != getattr(
                mt5, "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING", 2),
        }

    def terminal_flags(self) -> dict[str, Any]:
        with self._lock:
            if not self.connected:
                return {}
            t = mt5.terminal_info()
        if t is None:
            return {}
        return {
            "company": t.company, "connected": bool(t.connected),
            "trade_allowed": bool(t.trade_allowed), "build": t.build, "path": t.path,
            "configured_path": self.terminal_path,
        }

    # ---------------------------------------------------------------- symbols

    def resolve(self, symbol: str) -> str | None:
        """Map a configured name onto the broker's actual symbol name."""
        cached = self._name_map.get(symbol)
        if cached:
            return cached
        with self._lock:
            if not self.connected:
                return None
            override = self._overrides.get(symbol)
            if override:
                if mt5.symbol_info(override) is not None:
                    self._name_map[symbol] = override
                    return override
                return None  # an explicit mapping that is wrong must not fall back
            if mt5.symbol_info(symbol) is not None:
                self._name_map[symbol] = symbol
                return symbol
        want = symbol.upper()
        prefix_candidates: list[str] = []
        for name in self._broker_symbol_names():
            upper = name.upper()
            if upper == want or upper.split(".")[0] == want:
                with self._lock:
                    if mt5.symbol_info(name) is None:
                        continue
                self._name_map[symbol] = name
                LOG.emit(f"{symbol} -> broker sembolu '{name}' olarak eslendi.", "INFO")
                return name
            if upper.startswith(want):
                prefix_candidates.append(name)
        # A prefix match is only safe to guess when it is the SINGLE broker
        # symbol starting with this name - with two or more candidates
        # (e.g. "US30" matching both "US30" and "US30Cash") picking the first
        # one iteration happens to hit is a silent wrong-instrument risk, not
        # a resolution. Ambiguous cases need an explicit broker_symbol override.
        if len(prefix_candidates) == 1:
            name = prefix_candidates[0]
            with self._lock:
                if mt5.symbol_info(name) is None:
                    return None
            self._name_map[symbol] = name
            LOG.emit(f"{symbol} -> broker sembolu '{name}' olarak eslendi (tek onek eslesmesi).", "INFO")
            return name
        if len(prefix_candidates) > 1:
            LOG.emit(f"{symbol} -> birden fazla olasi broker sembolu bulundu ({', '.join(prefix_candidates[:5])}), "
                     f"belirsiz - Sistem'de broker_symbol ile acikca eslestirin.", "WARN")
        return None

    def select(self, symbol: str) -> str | None:
        real = self.resolve(symbol)
        if real is None:
            return None
        with self._lock:
            info = mt5.symbol_info(real)
            if info is not None and not info.visible:
                mt5.symbol_select(real, True)
        return real

    def info(self, symbol: str) -> dict[str, Any] | None:
        now = time.time()
        hit = self._info_cache.get(symbol)
        if hit and now - hit[0] < _INFO_TTL:
            return hit[1]
        real = self.select(symbol)
        if real is None:
            return None
        with self._lock:
            i = mt5.symbol_info(real)
        if i is None:
            return None
        data = {
            "name": real, "description": i.description, "digits": i.digits, "point": i.point,
            "volume_min": i.volume_min, "volume_max": i.volume_max, "volume_step": i.volume_step,
            "tick_value": i.trade_tick_value, "tick_size": i.trade_tick_size,
            "contract_size": i.trade_contract_size, "stops_level": i.trade_stops_level,
            "freeze_level": i.trade_freeze_level, "filling_mode": i.filling_mode,
            "trade_mode": i.trade_mode, "currency_profit": i.currency_profit,
        }
        self._info_cache[symbol] = (now, data)
        return data

    def tick(self, symbol: str) -> dict[str, float] | None:
        now = time.time()
        hit = self._tick_cache.get(symbol)
        if hit and now - hit[0] < _TICK_TTL:
            return hit[1]
        real = self.select(symbol)
        if real is None:
            return None
        with self._lock:
            t = mt5.symbol_info_tick(real)
        if t is None or (t.bid <= 0 and t.ask <= 0):
            return None
        data = {"bid": float(t.bid), "ask": float(t.ask), "time": float(t.time),
                "spread": float(t.ask - t.bid)}
        self._tick_cache[symbol] = (now, data)
        return data

    def market_open(self, symbol: str, max_age_sec: int = 180) -> bool:
        """True when the last tick is fresh relative to broker server time."""
        t = self.tick(symbol)
        if not t:
            return False
        return (self.server_now() - t["time"]) <= max_age_sec

    def last_session_close_minute(self, symbol: str, weekday: int) -> int | None:
        """Broker-configured close time (minutes since midnight) for ``symbol``
        on ``weekday`` (0=Sunday..6=Saturday, matching MQL5's ENUM_DAY_OF_WEEK).

        A symbol can have several sub-sessions in one day (e.g. a lunch break);
        this returns the *last* one's end, i.e. the real close. None means the
        broker reports no session at all that day (already closed, or the
        symbol/terminal does not expose a schedule).
        """
        real = self.select(symbol)
        if real is None:
            return None
        last_to: int | None = None
        try:
            with self._lock:
                for idx in range(8):  # generous cap; brokers rarely define more than 2-3
                    session = mt5.symbol_info_session_trade(real, weekday, idx)
                    if session is None or session == (None, None):
                        break
                    _from, to = session
                    to_minutes = (to.hour * 60 + to.minute) if hasattr(to, "hour") else int(to) // 60
                    last_to = to_minutes
        except Exception as exc:  # some terminal/broker builds do not expose this call
            LOG.emit(f"Seans programi okunamadi ({symbol}): {exc}", "WARN")
            return None
        return last_to

    # ------------------------------------------------------------------ time

    def server_now(self) -> float:
        """The clock every session/day-boundary decision is measured against.

        This is deliberately just the machine's own clock: session windows,
        trade days and the daily PnL anchor are all configured by the user in
        their own local (Windows) time, so that is the clock that must be used
        to evaluate them. An earlier version tried to auto-detect the broker's
        own UTC offset from live tick timestamps and add it on top, but that
        detection could go wrong (e.g. a bad tick, or the machine's own clock
        being off while not yet NTP-corrected) and silently shift every
        time-based gate - keep the Windows clock authoritative and synced via
        Windows' own time service instead of re-deriving it here.
        """
        return time.time()

    # ------------------------------------------------------------------ bars

    def bars(self, symbol: str, timeframe: str, count: int) -> Bars | None:
        real = self.select(symbol)
        if real is None:
            return None
        tf = timeframe_const(timeframe)
        with self._lock:
            rates = mt5.copy_rates_from_pos(real, tf, 0, int(count) + 1)
        if rates is None or len(rates) < 2:
            return None
        return Bars(rates[:-1], int(rates[-1]["time"]))

    # ------------------------------------------------------------- normalise

    def normalize_price(self, symbol: str, price: float) -> float:
        i = self.info(symbol)
        if not i:
            return round(float(price), 5)
        step = i["tick_size"] or i["point"] or 0.00001
        return round(round(float(price) / step) * step, int(i["digits"]))

    def normalize_volume(self, symbol: str, volume: float) -> float:
        """Snap volume down to the broker's lot step so sizing never exceeds risk."""
        i = self.info(symbol)
        if not i:
            return round(float(volume), 2)
        step = i["volume_step"] or 0.01
        vol = math.floor(float(volume) / step + 1e-9) * step
        vol = max(i["volume_min"], min(i["volume_max"], vol))
        decimals = max(0, len(f"{step:.8f}".rstrip("0").split(".")[-1]))
        return round(vol, decimals)

    def min_stop_distance(self, symbol: str) -> float:
        """Smallest legal stop distance in price units, spread included."""
        i = self.info(symbol)
        if not i:
            return 0.0
        point = i["point"] or 0.00001
        broker = max(i["stops_level"], i["freeze_level"]) * point
        tick = self.tick(symbol)
        spread = tick["spread"] if tick else 0.0
        return max(broker, spread * 1.5, point * 10)

    def margin_for(self, symbol: str, volume: float, side: str = "buy") -> float:
        real = self.select(symbol)
        tick = self.tick(symbol)
        if real is None or tick is None:
            return 0.0
        price = tick["ask"] if side == "buy" else tick["bid"]
        order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
        with self._lock:
            m = mt5.order_calc_margin(order_type, real, float(volume), price)
        return float(m or 0.0)

    def money_per_price_unit(self, symbol: str, volume: float) -> float:
        """Account-currency P/L for a one-price-unit move at ``volume`` lots."""
        i = self.info(symbol)
        if not i:
            return 0.0
        tick_size = i["tick_size"] or i["point"]
        tick_value = i["tick_value"]
        if tick_size <= 0 or tick_value <= 0:
            return 0.0
        return (tick_value / tick_size) * float(volume)

    def _filling(self, symbol: str) -> int:
        i = self.info(symbol)
        mode = int(i["filling_mode"]) if i else 0
        if mode & 1:
            return mt5.ORDER_FILLING_FOK
        if mode & 2:
            return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_RETURN

    # ------------------------------------------------------------- positions

    def positions(self, magic: int | None = None, symbol: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            if not self.connected:
                return []
            if symbol:
                real = self.resolve(symbol)
                # A resolve failure must mean "no positions for this symbol",
                # not "no filter" - mt5.positions_get(symbol=None) returns
                # EVERY open position, and close_all() filters only on magic
                # (every enabled symbol's, not just this one's) afterwards.
                # Falling through here turned "close COPPER" into "close
                # everything the bot has open" the moment COPPER's resolve
                # hiccuped.
                if real is None:
                    return []
                raw = mt5.positions_get(symbol=real)
            else:
                raw = mt5.positions_get()
            if raw is None:
                # mt5.positions_get() returns None (not ()) when the call itself
                # failed - a mid-cycle disconnect after ensure() already passed
                # this cycle. Folding that into "no positions" made the engine
                # think a real open position had vanished: management (trail/
                # BE/flatten) silently skipped it for a cycle, and risk.can_open
                # (fed self._positions) saw zero exposure and could stack a
                # fresh entry on top of it. Flip connected so the NEXT ensure()
                # forces a reconnect instead of quietly retrying forever.
                self.connected = False
                LOG.emit(f"positions_get basarisiz oldu ({mt5.last_error()}) - "
                         "baglanti koptu olarak isaretlendi.", "WARN")
                return []
        out = []
        for p in raw or []:
            if magic is not None and p.magic != magic:
                continue
            out.append({
                "ticket": int(p.ticket), "symbol": p.symbol, "magic": int(p.magic),
                "side": "buy" if p.type == mt5.POSITION_TYPE_BUY else "sell",
                "volume": float(p.volume), "price_open": float(p.price_open),
                "price_current": float(p.price_current), "sl": float(p.sl), "tp": float(p.tp),
                "profit": float(p.profit), "swap": float(p.swap),
                "time": int(p.time), "comment": p.comment,
            })
        return out

    def deals_since(self, ts: float) -> list[dict[str, Any]]:
        from datetime import datetime, timezone

        # ``ts`` and deal ``time`` are both plain Unix epochs, same as
        # ``server_now()``. Widening the window end to at least "now" (instead
        # of always ``ts+86400``) matters when ``ts`` is stale.
        end_ts = max(float(ts), self.server_now()) + 86400.0
        with self._lock:
            if not self.connected:
                return []
            raw = mt5.history_deals_get(
                datetime.fromtimestamp(float(ts), tz=timezone.utc),
                datetime.fromtimestamp(end_ts, tz=timezone.utc),
            )
        out = []
        for d in raw or []:
            # DEAL_ENTRY_IN is included too now, so merge_round_trips() can
            # fold its commission into the round-trip total - some brokers
            # split round-turn commission across both legs (or charge it all
            # on entry) rather than only at close, and dropping the IN side
            # entirely undercounted realised cost. Its profit is always 0.0
            # (an entry never itself realises P/L) and it carries no "reason"
            # (SL/TP only ever apply to a closing deal), so nothing else that
            # reads this list needs to change to tolerate it showing up.
            if d.entry not in (mt5.DEAL_ENTRY_IN, mt5.DEAL_ENTRY_OUT,
                               mt5.DEAL_ENTRY_INOUT, mt5.DEAL_ENTRY_OUT_BY):
                continue
            out.append({
                "ticket": int(d.ticket), "position": int(d.position_id), "symbol": d.symbol,
                "magic": int(d.magic), "volume": float(d.volume), "price": float(d.price),
                "profit": float(d.profit), "commission": float(d.commission),
                "swap": float(d.swap), "time": int(d.time), "comment": d.comment,
                "reason": int(d.reason), "entry": int(d.entry),
            })
        return out

    @staticmethod
    def merge_round_trips(deals: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Collapse per-deal OUT/partial fills into one net trade per position.

        A partial-TP ladder closes one position over several OUT deals; counting
        each as its own win/loss fragments a single round-trip's P/L into
        misleading noise - a net winner can show up as "1 win + 1 loss",
        corrupting profit factor, the consecutive-loss streak and quarantine
        judgment downstream (``Supervisor.review``), and the day's win-rate
        (``Engine.day_stats``). Grouped by MT5's ``position_id`` and summed, one
        entry per closed position, timestamped at its last (closing) fill.

        ``deals`` now carries DEAL_ENTRY_IN deals too (see ``deals_since()``),
        so its entry-side commission is folded into the total - but only for
        a position that actually HAS a closing deal in this same list. A
        still-open position's IN deal sitting alone here would otherwise be
        misread as a completed zero-profit "trade" the instant it filled,
        polluting win/loss counts and win-rate before it ever closed.
        """
        CLOSING = (mt5.DEAL_ENTRY_OUT, mt5.DEAL_ENTRY_INOUT, mt5.DEAL_ENTRY_OUT_BY)
        closed_positions = {d["position"] for d in deals if d.get("entry") in CLOSING}
        by_position: dict[int, dict[str, Any]] = {}
        for d in deals:
            pos = d["position"]
            if pos not in closed_positions:
                continue
            row = by_position.get(pos)
            if row is None:
                row = {"position": pos, "symbol": d["symbol"], "magic": d["magic"],
                       "time": d["time"], "profit": 0.0, "commission": 0.0, "swap": 0.0}
                by_position[pos] = row
            row["profit"] += d["profit"]
            row["commission"] += d["commission"]
            row["swap"] += d["swap"]
            row["time"] = max(row["time"], d["time"])
        return sorted(by_position.values(), key=lambda r: r["time"])

    # ----------------------------------------------------------- order entry

    def open_market(self, symbol: str, side: str, volume: float, sl: float, tp: float,
                    magic: int, slippage: int = 20, comment: str = "MicoFX") -> dict[str, Any]:
        real = self.select(symbol)
        if real is None:
            return {"ok": False, "error": f"{symbol}: sembol bulunamadi"}
        tick = self.tick(symbol)
        if tick is None:
            return {"ok": False, "error": f"{symbol}: fiyat alinamadi"}

        volume = self.normalize_volume(symbol, volume)
        if volume <= 0:
            return {"ok": False, "error": f"{symbol}: gecersiz lot"}

        price = tick["ask"] if side == "buy" else tick["bid"]
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": real,
            "volume": float(volume),
            "type": mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL,
            "price": float(price),
            "sl": float(self.normalize_price(symbol, sl)) if sl > 0 else 0.0,
            "tp": float(self.normalize_price(symbol, tp)) if tp > 0 else 0.0,
            "deviation": int(slippage),
            "magic": int(magic),
            "comment": comment[:28],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(symbol),
        }

        # Snapshot taken immediately before the send: the last-resort ticket
        # resolution below (when neither the deal history nor result.order
        # can be matched) needs to know which same-magic tickets already
        # existed, so it can identify the genuinely NEW one instead of
        # guessing by price similarity - a coincidentally close price on an
        # already-open position (tight ATR/spread day) could otherwise match
        # the WRONG, pre-existing ticket instead of this fresh fill.
        with self._lock:
            before_tickets = {int(p.ticket) for p in (mt5.positions_get(symbol=real) or ())
                              if p.magic == magic}

        with self._lock:
            result = mt5.order_send(request)

        if result is None:
            code, text = mt5.last_error()
            return {"ok": False, "error": f"{symbol}: order_send bos dondu ({code}: {text})"}

        if result.retcode == mt5.TRADE_RETCODE_INVALID_STOPS:
            # The broker rejected the level, not the trade's risk. Widen only
            # up to the broker's own minimum distance and keep the strategy's
            # ATR-sized SL/TP otherwise - replacing it with a fixed buffer (the
            # old behaviour) silently substituted a tiny, unvalidated stop for
            # whatever sl_atr_mult/tp_atr_mult actually computed, so a trade
            # that was supposed to risk N x ATR could get stopped out on noise
            # a few points from entry instead.
            min_dist = self.min_stop_distance(symbol)
            sl_dist = max(abs(price - sl), min_dist) if sl > 0 else 0.0
            tp_dist = max(abs(tp - price), min_dist) if tp > 0 else 0.0
            if side == "buy":
                request["sl"] = self.normalize_price(symbol, price - sl_dist) if sl > 0 else 0.0
                request["tp"] = self.normalize_price(symbol, price + tp_dist) if tp > 0 else 0.0
            else:
                request["sl"] = self.normalize_price(symbol, price + sl_dist) if sl > 0 else 0.0
                request["tp"] = self.normalize_price(symbol, price - tp_dist) if tp > 0 else 0.0
            with self._lock:
                result = mt5.order_send(request)

        if result is not None and result.retcode == mt5.TRADE_RETCODE_INVALID_FILL:
            # _filling() reads symbol_info().filling_mode; a transient miss on
            # that call (symbol not yet cached, brief API hiccup) falls back to
            # ORDER_FILLING_RETURN, which raw/ECN brokers routinely refuse -
            # and unlike INVALID_STOPS above, nothing retried this one, so a
            # single bad read silently ate the signal with no recovery. Walk
            # the other two modes once each; IOC first since that is what this
            # account's raw-account symbols actually support.
            tried = {request["type_filling"]}
            for mode in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
                if mode in tried:
                    continue
                tried.add(mode)
                request["type_filling"] = mode
                with self._lock:
                    result = mt5.order_send(request)
                if result is not None and result.retcode in _FILL_RETCODES:
                    break

        if result is None or result.retcode not in _FILL_RETCODES:
            code = getattr(result, "retcode", -1)
            text = getattr(result, "comment", "?")
            return {"ok": False, "retcode": code, "error": f"{symbol}: emir reddedildi ({code} {text})"}
        # DONE_PARTIAL (IOC took less than the requested volume) is a real
        # fill, not a rejection - treating it as ok:False here left a live
        # position on the broker while the caller, seeing ok:False, kept the
        # signal alive to retry next poll: the next order_send stacked a
        # second position on top of the first instead of recognising the
        # entry as already taken. result.volume below already reflects the
        # actual filled amount, not the requested one.
        partial_fill = result.retcode == mt5.TRADE_RETCODE_DONE_PARTIAL

        fill_price = float(result.price)
        final_sl, final_tp = request["sl"], request["tp"]

        # result.order is the ORDER ticket, not necessarily the resulting
        # POSITION ticket - they coincide on a hedging account's fresh open
        # (this system's own account type), but netting mode can fold a fill
        # into an already-open position under a different ticket. Resolved
        # unconditionally (not just when SL/TP needs re-anchoring below) so
        # every caller - including secondary-signal ticket tagging - gets the
        # real position ticket instead of diffing positions() before/after.
        # The fill's own deal carries the authoritative position_id directly;
        # verifying result.order against the live position table is the
        # fallback for the rare case the deal hasn't propagated into history
        # yet, and matching by fill price within the same magic is the last
        # resort when even that comes back empty.
        # history_deals_get(ticket=...) filters on the ORDER ticket (DEAL_ORDER),
        # not the deal ticket - passing result.deal here looked up the wrong
        # id, so this almost always came back empty and fell through to the
        # order/price-match fallbacks below instead of resolving directly.
        pos_ticket = 0
        with self._lock:
            order_deals = mt5.history_deals_get(ticket=int(result.order))
        if order_deals:
            match = [d for d in order_deals if int(d.ticket) == int(result.deal)]
            fill_deal = match or order_deals
            pos_ticket = int(fill_deal[0].position_id)
        if not pos_ticket:
            candidate = int(result.order)
            with self._lock:
                exists = mt5.positions_get(ticket=candidate)
            if exists:
                pos_ticket = candidate
            else:
                with self._lock:
                    others = mt5.positions_get(symbol=real) or ()
                same_magic = [p for p in others if p.magic == magic]
                # Genuinely-new tickets (not present in the before-send
                # snapshot) first - this is a strictly more reliable signal
                # than price similarity, which a pre-existing position at a
                # coincidentally close price (tight ATR/spread day) could
                # satisfy despite being the WRONG, older ticket. Price match
                # only breaks a tie if more than one ticket is new; matching
                # by price alone (the old behaviour) is not attempted at all
                # any more - guessing wrong here doesn't just leave this fill
                # unmanaged, it corrupts the OTHER position's exit tracking.
                new_tickets = [p for p in same_magic if int(p.ticket) not in before_tickets]
                if len(new_tickets) == 1:
                    pos_ticket = int(new_tickets[0].ticket)
                elif len(new_tickets) > 1:
                    price_matches = [p for p in new_tickets
                                     if abs(p.price_open - fill_price) < self.min_stop_distance(symbol) * 0.1]
                    if len(price_matches) == 1:
                        pos_ticket = int(price_matches[0].ticket)
                    # else: still ambiguous even among new tickets - leave
                    # unresolved (0) rather than guess between them.

        # SL/TP above were built from the pre-fill tick; a market order can
        # slip within ``deviation``, and rebuilding them from the tick means
        # the position's realised risk (fill -> SL) is not the R the strategy
        # asked for. Re-anchor both to the actual fill so the position's real
        # risk matches what was sized, then push the correction to the broker.
        min_dist = self.min_stop_distance(symbol)
        reanchor_ok = True
        if abs(fill_price - price) > min_dist * 0.1:
            sl_dist = abs(price - sl) if sl > 0 else 0.0
            tp_dist = abs(tp - price) if tp > 0 else 0.0
            if side == "buy":
                final_sl = self.normalize_price(symbol, fill_price - sl_dist) if sl > 0 else 0.0
                final_tp = self.normalize_price(symbol, fill_price + tp_dist) if tp > 0 else 0.0
            else:
                final_sl = self.normalize_price(symbol, fill_price + sl_dist) if sl > 0 else 0.0
                final_tp = self.normalize_price(symbol, fill_price - tp_dist) if tp > 0 else 0.0
            if pos_ticket and (final_sl, final_tp) != (request["sl"], request["tp"]):
                reanchor_ok = self.modify_position(pos_ticket, final_sl, final_tp, symbol)
            elif not pos_ticket:
                # No ticket to re-anchor at all (deal + order + fallback all
                # came up empty) - the fill happened, the entry succeeded, but
                # this position is running the pre-fill-tick SL/TP rather than
                # the fill-anchored one until the next trail update touches it.
                reanchor_ok = False

        return {
            "ok": True, "order": int(result.order), "deal": int(result.deal),
            "position": pos_ticket, "partial_fill": partial_fill,
            # False only when a re-anchor was needed and didn't land (broker
            # rejected the modify, or no position ticket to send it to) - the
            # fill itself still succeeded, this is purely informational so the
            # caller can log it instead of the discrepancy going unnoticed.
            "sl_tp_reanchored": reanchor_ok,
            # ``requested`` is the tick this order was actually built from, kept
            # alongside the realised fill so entry slippage can be measured
            # exactly. MT5's order history stores 0.0 for a market order's
            # requested price, so this is the only place it is knowable.
            "requested": float(price),
            "price": fill_price, "volume": float(result.volume),
            "sl": final_sl, "tp": final_tp,
        }

    def modify_position(self, ticket: int, sl: float, tp: float, symbol: str) -> bool:
        real = self.resolve(symbol) or symbol
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": int(ticket),
            "symbol": real,
            "sl": float(self.normalize_price(symbol, sl)) if sl > 0 else 0.0,
            "tp": float(self.normalize_price(symbol, tp)) if tp > 0 else 0.0,
        }
        with self._lock:
            result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            code = getattr(result, "retcode", -1)
            if code != mt5.TRADE_RETCODE_NO_CHANGES:
                LOG.emit(f"SL/TP guncellenemedi #{ticket} ({code})", "WARN", symbol)
            return False
        return True

    def close_partial(self, ticket: int, volume: float, slippage: int = 20,
                      comment: str = "MicoFX partial", fill: dict | None = None) -> bool:
        return self.close_position(ticket, slippage, comment, volume=volume, fill=fill)

    def close_position(self, ticket: int, slippage: int = 20, comment: str = "MicoFX close",
                       volume: float | None = None, fill: dict | None = None) -> bool:
        """Close (or partially close) a position.

        ``fill`` is an optional out-parameter: pass a dict and it comes back
        holding ``requested`` / ``price`` / ``symbol`` / ``side`` / ``volume``
        for the closing leg, which is what the execution monitor compares. The
        bool return is left exactly as it was so every existing caller keeps
        working unchanged.
        """
        with self._lock:
            found = mt5.positions_get(ticket=int(ticket))
        if not found:
            return False
        p = found[0]
        tick = self.tick(p.symbol)
        if tick is None:
            return False
        amount = float(p.volume) if volume is None else min(float(volume), float(p.volume))
        if amount <= 0:
            return False
        is_buy = p.type == mt5.POSITION_TYPE_BUY
        requested = tick["bid"] if is_buy else tick["ask"]
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": p.symbol,
            "volume": amount,
            "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
            "position": int(ticket),
            "price": requested,
            "deviation": int(slippage),
            "magic": int(p.magic),
            "comment": comment[:28],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": self._filling(p.symbol),
        }
        with self._lock:
            result = mt5.order_send(request)
        if result is not None and result.retcode == mt5.TRADE_RETCODE_INVALID_FILL:
            # A close that fails leaves real risk open, unlike a missed entry -
            # worth the same fallback ladder as open_market for the same reason
            # (a transient symbol_info() miss defaulted to a filling mode this
            # raw account does not actually support).
            tried = {request["type_filling"]}
            for mode in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
                if mode in tried:
                    continue
                tried.add(mode)
                request["type_filling"] = mode
                with self._lock:
                    result = mt5.order_send(request)
                if result is not None and result.retcode in _FILL_RETCODES:
                    break
        if result is None or result.retcode not in _FILL_RETCODES:
            code = getattr(result, "retcode", -1)
            LOG.emit(f"Pozisyon kapatilamadi #{ticket} ({code})", "ERROR", p.symbol)
            return False
        if result.retcode == mt5.TRADE_RETCODE_DONE_PARTIAL:
            # IOC closed less than requested - the position still has volume
            # left open on the broker, not fully flat. True still, so callers
            # (close_all's counter, panic) count this as "handled" rather than
            # an error; the remainder is picked up by the next close_all/trail
            # pass since positions_get() will report it as still open.
            LOG.emit(f"Pozisyon kismen kapatildi #{ticket}: {result.volume:g} lot "
                     f"(istenen {amount:g}) - kalan hala acik.", "WARN", p.symbol)
        if fill is not None:
            fill.update({
                "symbol": p.symbol, "side": "buy" if is_buy else "sell",
                "requested": float(requested), "price": float(result.price),
                "volume": float(result.volume),
                # Where the stop sat when we closed: lets the monitor express
                # this leg's slippage in R without re-reading the position.
                "risk_dist": abs(float(p.price_open) - float(p.sl)) if p.sl else 0.0,
            })
        if volume is None:
            LOG.emit(f"Pozisyon kapatildi #{ticket} kar={p.profit:.2f}", "TRADE", p.symbol)
        return True

    def close_all(self, magics: set[int] | None = None, symbol: str | None = None) -> tuple[int, int]:
        """Flatten every matching position, retrying what a single pass leaves open.

        close_position() reports TRADE_RETCODE_DONE_PARTIAL as success (the
        remainder is still genuinely open on the broker - see its docstring),
        and one IOC pass can leave several tickets like that. A caller like
        panic() that runs this once and reports "N kapatildi" needs that count
        to mean actually flat, not "handled", so re-check and retry the
        tickets still open instead of leaving them for whatever the next
        unrelated close_all call happens to be.

        Returns ``(closed, remaining)`` - a kill-switch caller must look at
        ``remaining``, not just assume a non-crash means everything is flat.
        ``remaining`` is -1 (never 0, so it always fails a ``remaining == 0``
        success check) when the connection could not even be verified -
        ``positions()`` returns an empty list both when genuinely flat and
        when disconnected, and treating a disconnected "[]" as "0 kaldi" is
        exactly the false "hepsi kapandi" a kill-switch must never report.
        """
        if not self.ensure():
            return 0, -1
        # Per-symbol close filters via positions(symbol=...). If resolve()
        # cannot map the configured name, positions() returns [] WITHOUT
        # flipping connected (resolve miss ≠ disconnect) - that would look
        # identical to "flat" and make close_all report (0, 0) / ok:true
        # while tickets under that magic may still be open. Fail closed.
        if symbol is not None and self.resolve(symbol) is None:
            LOG.emit(
                f"close_all({symbol}): broker sembolu cozulemedi - "
                f"pozisyon listesi guvenilir degil, flatten reddedildi.",
                "ERROR", symbol)
            return 0, -1
        before = {p["ticket"] for p in self.positions(symbol=symbol)
                 if magics is None or p["magic"] in magics}
        if not self.connected:
            # positions() itself can flip this False mid-call (see its own
            # docstring) - the ensure() check above only proves the
            # connection was alive a moment earlier, not through this exact
            # call. An empty ``before`` from a call that just failed is not
            # "flat", so it must not be trusted as one either.
            return 0, -1
        remaining = before
        confirmed_closed = 0
        for _ in range(4):
            if not remaining:
                break
            progressed = False
            for ticket in list(remaining):
                if self.close_position(ticket):
                    progressed = True
                    confirmed_closed += 1
            if not progressed:
                break
            remaining = {p["ticket"] for p in self.positions(symbol=symbol)
                        if p["ticket"] in before and (magics is None or p["magic"] in magics)}
            if not self.connected:
                # Same mid-call failure, now partway through closing. Do NOT
                # report ``len(before) - len(remaining)`` here - remaining
                # just came back [] from the same failed call, which would
                # inflate "closed" to the full original count regardless of
                # how many close_position() calls this pass actually
                # confirmed. confirmed_closed only counts calls that
                # genuinely returned success, so it cannot overstate.
                return confirmed_closed, -1
        return len(before) - len(remaining), len(remaining)
