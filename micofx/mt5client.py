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

# Outcomes that say nothing about whether the order reached the server. The
# request was already on the wire when the terminal gave up waiting, so the
# broker may well have filled it - reporting these as a plain rejection (the
# old behaviour) let the caller keep the signal alive and fire a SECOND
# order_send on the next poll, stacking a duplicate position on top of a fill
# nobody knew about. Every one of these has to be resolved by looking at the
# position book, never by trusting the return value. ``order_send`` returning
# None (IPC-level failure inside the terminal bridge) is the same class of
# unknown and is routed through the same verification.
# Exported under a public name as well: the engine needs to recognise a
# link-level refusal to know that retrying it on the very next poll is
# pointless (see Engine.LINK_BACKOFF_SEC).
_AMBIGUOUS_RETCODES: frozenset[int] = frozenset(
    {getattr(mt5, name) for name in
     ("TRADE_RETCODE_TIMEOUT", "TRADE_RETCODE_CONNECTION")
     if mt5 is not None and hasattr(mt5, name)}
)

AMBIGUOUS_RETCODES = _AMBIGUOUS_RETCODES

_INFO_TTL = 120.0
_TICK_TTL = 0.5

# How far ahead of this machine's clock a tick timestamp may sit before it is
# treated as corrupt. A tick's ``time`` is the broker's wall clock encoded as
# though it were UTC, so a legitimate reading already runs a whole UTC offset
# ahead - at most +14h anywhere in the world, +3h on this server. 48h leaves
# more than triple the headroom over any real offset plus any plausible NTP
# skew, while still catching the shapes that matter: a millisecond field read
# into a seconds one lands tens of thousands of years out, and a garbled
# struct anywhere at all. One-sided on purpose - a tick in the PAST is the
# exact condition market_open() exists to detect and must never be discarded.
_MAX_TICK_AHEAD_SEC = 48 * 3600.0
_RECONNECT_COOLDOWN = 5.0


def timeframe_const(name: str) -> int:
    if mt5 is None:
        return 0
    # M10 and H4 used to be listed here so a config stored while they were
    # offered still resolved to the right constant. No stored symbol carries
    # either any more, so the entries described a state of the world that had
    # stopped existing - and keeping them made the real hazard easy to miss.
    #
    # That hazard is the fallback, not the retired names. Anything this table
    # does not recognise resolves to M5, which means a symbol trading
    # five-minute bars when it was validated on something else - the quietest
    # possible way to be wrong. Refusing outright would take the engine down
    # over a single bad row, so the fallback stays; it just no longer looks
    # like an ordinary resolution.
    table = {
        "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1,
    }
    key = str(name).upper()
    if key not in table:
        LOG.emit(f"Bilinmeyen zaman dilimi '{name}' - M5 barlarina dusuldu. "
                 f"Sembolun dogrulandigi bar bu degilse sonuclar yaniltici olur.",
                 "WARN")
        return mt5.TIMEFRAME_M5
    return table[key]


def timeframe_seconds(name: str) -> int:
    table = {"M5": 300, "M15": 900, "M30": 1800, "H1": 3600}
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
        # Newest tick timestamp seen across every symbol, in the broker's own
        # naive clock. market_open() measures staleness against this rather
        # than the wall clock, so the broker's UTC offset cancels instead of
        # landing in the answer.
        self._broker_now: float = 0.0
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
        if t is None or t.bid <= 0 or t.ask <= 0:
            # Either side <=0 (not just both) is a bad/partial quote - a
            # one-sided zero (illiquid instrument, rollover gap, feed
            # glitch) used to pass this check, letting open_market() build
            # an order at price=0.0 and min_stop_distance() compute a
            # nonsense spread from it. The broker would reject the zero
            # price anyway, but there's no reason to spend a live order
            # attempt finding that out.
            return None
        if float(t.time) > now + _MAX_TICK_AHEAD_SEC:
            # Same stance as the bid/ask guard above, for the timestamp - and
            # this one is worse than a rejected order. ``_broker_now`` below is
            # a monotonic max over every symbol that is never reset, not even
            # by reconnect(), so ONE tick dated into the future raises the
            # yardstick permanently. market_open() then measures every other
            # symbol against it, and instruments quoting perfectly fresh ticks
            # read as stale for the life of the process.
            #
            # engine._evaluate turns that into "piyasa kapali / fiyat akmiyor"
            # and clears the signal chain for every symbol in the book, so all
            # entries stop while the panel shows a reason that reads like a
            # market condition rather than a fault. Open positions keep being
            # managed - manage_positions() does not consult this gate - so
            # nothing is left unprotected, but nothing new is ever taken again
            # until someone restarts the process.
            return None
        data = {"bid": float(t.bid), "ask": float(t.ask), "time": float(t.time),
                "spread": float(t.ask - t.bid)}
        self._tick_cache[symbol] = (now, data)
        # Newest broker-clock reading seen anywhere in the book - see
        # market_open() for why this, and not the wall clock, is the yardstick.
        self._broker_now = max(self._broker_now, data["time"])
        return data

    def market_open(self, symbol: str, max_age_sec: int = 180) -> bool:
        """True when this symbol's last tick is fresh against the live feed.

        Measured against the newest tick timestamp seen across the whole book,
        not against this machine's clock. A tick's ``time`` is a naive epoch
        holding the broker's wall-clock reading, while ``server_now()`` is a
        true epoch, so subtracting one from the other leaves the broker's whole
        UTC offset in the answer - a constant -10800 on this GMT+3 server.
        Every tick up to three hours stale therefore satisfied a 180 second
        freshness test, making the one gate that stops entries on a dead feed
        61x more permissive than it reads.

        Comparing two readings of the same clock cancels the offset entirely
        and needs no detection - which matters, because this codebase already
        removed an auto-detected offset for silently shifting every time-based
        decision when the detection went wrong.

        Degrades safely: with only one symbol ever read, its own tick is also
        the newest, the age is zero and the answer is "open" - the behaviour
        this had before. It can never wrongly report a live market closed; it
        can only stop being blind to a frozen one.
        """
        t = self.tick(symbol)
        if not t:
            return False
        return (self._broker_now - t["time"]) <= max_age_sec

    def broker_utc_offset_hours(self, symbols: list[str]) -> int | None:
        """The broker server's own UTC offset in whole hours, or None.

        A tick's ``time`` is a naive epoch holding the broker's wall-clock
        reading encoded as though it were UTC, so subtracting a true epoch
        yields the broker's own offset from UTC - +3 for a GMT+3 server. It is
        NOT the difference against this machine's clock; that is the caller's
        subtraction, and confusing the two turns an aligned setup into a
        permanent false alarm.

        This is the one number that actually moves under daylight saving here.
        Session windows are configured against the Windows clock, which in
        Turkey is UTC+3 all year, while the broker's server follows European
        DST and drops to GMT+2 at the end of October. Every configured window
        then sits an hour off the instrument's real session, silently, and the
        audit meant to catch it cannot (see ``last_session_close_minute``).

        Taken as the median across several symbols and rounded to a whole
        hour, because one stale or odd quote must not move the answer.

        Deliberately only *reported*, never used to shift a gate. An earlier
        version of this codebase auto-corrected times from a detected offset
        and it was removed precisely because a bad detection silently moved
        every time-based decision; a number on a dashboard cannot do that.
        """
        now = time.time()
        deltas: list[float] = []
        for symbol in symbols:
            tick = self.tick(symbol)
            if not tick or not tick.get("time"):
                continue
            delta = float(tick["time"]) - now
            # Anything further out than half a day is a closed market's last
            # quote, not a live one, and says nothing about the clock.
            if abs(delta) < 12 * 3600:
                deltas.append(delta)
        if len(deltas) < 3:
            return None
        deltas.sort()
        return int(round(deltas[len(deltas) // 2] / 3600.0))

    def last_session_close_minute(self, symbol: str, weekday: int) -> int | None:
        """Broker-configured close time (minutes since midnight) for ``symbol``
        on ``weekday`` (0=Sunday..6=Saturday, matching MQL5's ENUM_DAY_OF_WEEK).

        A symbol can have several sub-sessions in one day (e.g. a lunch break);
        this returns the *last* one's end, i.e. the real close.

        None means "could not determine", and callers must never read it as
        "nothing wrong". On the current MetaTrader5 package that is the only
        answer it can give: ``symbol_info_session_trade`` is an MQL5 function
        with no Python binding (checked against 5.0.6090). That absence is a
        static property of the installed package, not a fault, so it returns
        quietly - warning about it once per symbol per call buried the log
        under 20 identical lines every time the audit ran, and those lines go
        to disk. The audit surfaces it as "okunamadi" instead, which is where
        it belongs. A genuine runtime failure on a build that *does* expose
        the call still warns.

        See ``broker_utc_offset_hours`` for what is actually measurable today.
        """
        if not hasattr(mt5, "symbol_info_session_trade"):
            return None
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
            if raw is None:
                # Same class as positions_get None - failed call, not empty history.
                self.connected = False
                LOG.emit(f"history_deals_get basarisiz oldu ({mt5.last_error()}) - "
                         "baglanti koptu olarak isaretlendi.", "WARN")
                return []
        out = []
        for d in raw:
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
        # positions_get None is a failed call (same as positions()) - folding
        # it to () via ``or ()`` hid the disconnect and made before_tickets
        # look empty. Refuse the send rather than open blind.
        with self._lock:
            before_raw = mt5.positions_get(symbol=real)
        if before_raw is None:
            self.connected = False
            LOG.emit(f"positions_get basarisiz oldu (open_market before, "
                     f"{mt5.last_error()}) - baglanti koptu olarak isaretlendi.", "WARN")
            return {"ok": False,
                    "error": f"{symbol}: acik pozisyon listesi dogrulanamadi "
                             f"(MT5 baglantisi koptu) - emir gonderilmedi"}
        before_tickets = {int(p.ticket) for p in before_raw if p.magic == magic}

        # This snapshot and the send below are deliberately NOT one critical
        # section, which looks like an ambiguous-ticket race and mostly is not:
        #
        # * open_market has exactly one caller (Engine._open), it runs on the
        #   single trading-cycle thread, and it is already inside entry_lock -
        #   so no second entry from this process can land in the gap.
        # * before_tickets is only consulted by the THIRD resolution fallback.
        #   The deal's own position_id and then positions_get(result.order)
        #   are both authoritative and neither looks at this snapshot.
        # * that third path filters on p.magic == magic (as does this line),
        #   so a manual trade or another EA - different magic - cannot be
        #   mistaken for this fill. Only a second MicoFX on the same account
        #   and magic could, which the README already forbids outright.
        #
        # Closing the gap means holding self._lock across order_send, and that
        # lock serialises EVERY MT5 call in the process - ticks, positions,
        # the panel's own reads. order_send is a broker round trip that can
        # take seconds, so the whole app would stall behind each entry. That
        # is a real, recurring cost against a residual risk already covered
        # three ways over. Left open on purpose; this note is the record.
        with self._lock:
            result = mt5.order_send(request)

        if result is None:
            code, text = mt5.last_error()
            return self._verify_ambiguous_send(
                symbol, real, magic, before_tickets, float(price),
                f"{symbol}: order_send bos dondu ({code}: {text})",
                side=side, req_sl=request["sl"], req_tp=request["tp"],
                retcode=code)

        if result.retcode == mt5.TRADE_RETCODE_INVALID_STOPS:
            # The broker rejected the level, not the trade's risk. Widen only
            # up to the broker's own minimum distance and keep the strategy's
            # ATR-sized levels otherwise - replacing them with a fixed buffer
            # (the old behaviour) silently substituted a tiny, unvalidated stop
            # for whatever sl_atr_mult actually computed, so a trade that was
            # supposed to risk N x ATR could get stopped out on noise a few
            # points from entry instead. This function keeps a generic ``tp``
            # parameter because it is the broker API wrapper, not the strategy;
            # the engine always passes 0.
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
            # A retry inside the INVALID_STOPS/INVALID_FILL ladders above can
            # itself come back None or time out - same unknown outcome as the
            # first send, and the earlier attempts in the ladder may have
            # filled too, so this must go through verification rather than be
            # reported as a clean reject.
            if result is None or code in _AMBIGUOUS_RETCODES:
                # When result is None inside the INVALID_* ladder, last_error
                # is the only code we have; prefer that over the sentinel -1
                # from getattr(None, "retcode", -1) so the engine's link
                # backoff can still recognise a connection-class refusal.
                if result is None:
                    code, text = mt5.last_error()
                return self._verify_ambiguous_send(
                    symbol, real, magic, before_tickets, float(price),
                    f"{symbol}: emir sonucu belirsiz ({code} {text})",
                    # request["sl"]/["tp"] not the sl/tp params: the
                    # INVALID_STOPS ladder above may have widened them, and
                    # the widened pair is what the broker actually holds.
                    side=side, req_sl=request["sl"], req_tp=request["tp"],
                    retcode=code)
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
            if exists is None:
                # None = API failure, not "no such ticket" - folding it into
                # the else branch below silently treated a disconnect as
                # "candidate ticket not found" and fell through to the
                # symbol-wide lookup, which (if that call happened to
                # succeed) masked the drop entirely instead of flipping
                # connected like every other positions_get() failure here.
                self.connected = False
                LOG.emit(f"positions_get(ticket={candidate}) basarisiz oldu (open_market "
                         f"candidate, {mt5.last_error()}) - baglanti koptu olarak isaretlendi.",
                         "WARN")
            elif exists:
                pos_ticket = candidate
            else:
                with self._lock:
                    others = mt5.positions_get(symbol=real)
                if others is None:
                    # Fill already landed; mark disconnect so callers fail closed
                    # on the next positions() rather than resolving against an
                    # empty fabricated book.
                    self.connected = False
                    LOG.emit(f"positions_get basarisiz oldu (open_market after, "
                             f"{mt5.last_error()}) - baglanti koptu olarak isaretlendi.",
                             "WARN")
                    others = ()
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
            # Distances from request["sl"]/["tp"] - the levels actually SENT
            # and accepted by the broker - not the original sl/tp params.
            # When INVALID_STOPS widened the request above, recomputing from
            # the original (already-rejected) tight distance re-sent exactly
            # what the broker just refused; modify_position() has no retry/
            # widening ladder of its own, so it silently failed a second time
            # and this function still reported the rejected values as the
            # position's real SL/TP.
            sl_dist = abs(price - request["sl"]) if request["sl"] > 0 else 0.0
            tp_dist = abs(request["tp"] - price) if request["tp"] > 0 else 0.0
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
            if not reanchor_ok:
                # The correction did not land, so the broker is still holding
                # the levels that were actually sent and accepted. Report
                # those, not the ones we wanted: the caller writes this SL
                # straight into the TRADE log, and reporting the intended
                # level would put a stop in the audit trail that no longer
                # exists anywhere on the broker - the log would say the trade
                # risked what it was sized for while the live position risked
                # the pre-fill distance. _verify_ambiguous_send's recovery
                # path already reverts for exactly this reason; the normal
                # fill path is the one that did not.
                final_sl, final_tp = request["sl"], request["tp"]

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

    def _verify_ambiguous_send(self, symbol: str, real: str, magic: int,
                               before_tickets: set[int], requested: float,
                               reason: str, side: str = "", req_sl: float = 0.0,
                               req_tp: float = 0.0,
                               retcode: int | None = None) -> dict[str, Any]:
        """Decide what actually happened after an unconfirmed ``order_send``.

        Timeouts and IPC failures are not rejections: the request may already
        be executing at the broker. The only trustworthy answer is the
        position book, diffed against the snapshot ``open_market`` took just
        before the send.

        Three outcomes, and the caller must be able to tell them apart:

        * **one new same-magic ticket** - the order DID fill. Returned as a
          normal success so the entry is booked once and the signal is
          consumed, instead of being retried into a duplicate position.
        * **no new ticket after the whole retry window** - genuinely never
          reached the market. Plain failure, safe to retry on the next poll.
          ``retcode`` is forwarded so Engine can park the symbol for
          ``LINK_BACKOFF_SEC`` on connection-class codes (10031/10012) -
          without it the 2.1s verifier would be re-run every poll for the
          whole outage (see 2026-08-11 UK100/US30 storm).
        * **anything we cannot see** (positions_get failing, or more than one
          new ticket) - flagged ``ambiguous`` so the caller refuses to send
          another order for this symbol rather than guessing. Fail closed: a
          missed entry costs a signal, a duplicate costs double risk.

        Broker replication can lag the fill by a beat, so the book is
        re-checked a few times over ~2s before "no new ticket" is believed.
        """
        adopted = None
        for attempt in range(4):
            # Sleep first: a fill that has not propagated into positions_get
            # yet is exactly the case this is here to catch, and the very
            # first read is the least likely to see it.
            time.sleep(0.3 if attempt == 0 else 0.6)
            with self._lock:
                after = mt5.positions_get(symbol=real)
            if after is None:
                self.connected = False
                LOG.emit(f"{reason} - pozisyon listesi de okunamadi ({mt5.last_error()}), "
                         f"emrin acilip acilmadigi BILINMIYOR. Yeni emir gonderilmeyecek, "
                         f"MT5'i elle kontrol edin.", "ERROR", symbol)
                return {"ok": False, "ambiguous": True, "retcode": retcode,
                        "error": f"{reason} - pozisyon durumu dogrulanamadi"}
            new = [p for p in after
                   if p.magic == magic and int(p.ticket) not in before_tickets]
            if len(new) > 1:
                LOG.emit(f"{reason} - ayni magic altinda {len(new)} yeni pozisyon var, "
                         f"hangisinin bu emir oldugu belirlenemedi. Yeni emir "
                         f"gonderilmeyecek, MT5'i elle kontrol edin.", "ERROR", symbol)
                return {"ok": False, "ambiguous": True, "retcode": retcode,
                        "error": f"{reason} - birden fazla yeni pozisyon, cozulemedi"}
            if len(new) == 1:
                adopted = new[0]
                break

        if adopted is None:
            # verified_unfilled: the book was readable and nothing landed. Safe
            # to retry later - but Engine must see this flag (not only retcode)
            # so IPC/None sends (retcode -10001 etc., outside AMBIGUOUS_RETCODES)
            # still get LINK_BACKOFF_SEC instead of re-paying the 2.1s sleep
            # every poll.
            return {"ok": False, "retcode": retcode, "verified_unfilled": True,
                    "error": f"{reason} - dogrulandi: yeni pozisyon olusmamis, emir gecmemis"}

        LOG.emit(f"{reason} - ancak pozisyon #{int(adopted.ticket)} gercekten acilmis; "
                 f"tekrar emir gonderilmedi, pozisyon sahiplenildi.", "WARN", symbol)

        ticket = int(adopted.ticket)
        fill_price = float(adopted.price_open)
        final_sl, final_tp = float(adopted.sl), float(adopted.tp)
        # The levels the broker is holding were built from the pre-fill tick,
        # because there was no confirmed fill price to anchor them to at send
        # time. On a fast symbol that gap is real - a live BTCUSD probe of
        # this exact path filled 27 price units away from the tick, which
        # would have left the position risking 527 instead of the 500 it was
        # sized for. Same re-anchor the normal fill path does, off the same
        # requested-vs-filled distances.
        reanchor_ok = True
        min_dist = self.min_stop_distance(symbol)
        if side and (req_sl > 0 or req_tp > 0) and abs(fill_price - requested) > min_dist * 0.1:
            sl_dist = abs(requested - req_sl) if req_sl > 0 else 0.0
            tp_dist = abs(req_tp - requested) if req_tp > 0 else 0.0
            if side == "buy":
                final_sl = self.normalize_price(symbol, fill_price - sl_dist) if req_sl > 0 else 0.0
                final_tp = self.normalize_price(symbol, fill_price + tp_dist) if req_tp > 0 else 0.0
            else:
                final_sl = self.normalize_price(symbol, fill_price + sl_dist) if req_sl > 0 else 0.0
                final_tp = self.normalize_price(symbol, fill_price - tp_dist) if req_tp > 0 else 0.0
            reanchor_ok = self.modify_position(ticket, final_sl, final_tp, symbol)
            if not reanchor_ok:
                # Broker refused the correction - the position keeps the
                # tick-anchored levels it already has, so report those rather
                # than the ones we wanted.
                final_sl, final_tp = float(adopted.sl), float(adopted.tp)

        return {
            "ok": True, "recovered": True,
            "order": 0, "deal": 0, "position": ticket,
            "partial_fill": False,
            "sl_tp_reanchored": reanchor_ok,
            "requested": float(requested), "price": fill_price,
            "volume": float(adopted.volume),
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
        if found is None:
            # None = API failure (same as positions()); empty tuple = gone.
            self.connected = False
            LOG.emit(f"positions_get(ticket={ticket}) basarisiz oldu "
                     f"({mt5.last_error()}) - baglanti koptu olarak isaretlendi.",
                     "WARN")
            return False
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
        partial = result.retcode == mt5.TRADE_RETCODE_DONE_PARTIAL
        if partial:
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
        # Full-close log only when not DONE_PARTIAL - otherwise the "kismen"
        # line above already told the truth and a second "kapatildi" lied.
        if volume is None and not partial:
            realised = self._closing_deal_pnl(result, int(ticket))
            if realised is None:
                # History has not caught up (or the call failed). Fall back to
                # the position's own floating figure, swap folded in, and say
                # which one this is rather than quietly printing a different
                # quantity under the same label.
                LOG.emit(f"Pozisyon kapatildi #{ticket} "
                         f"kar~{float(p.profit) + float(p.swap):.2f} (anlik)",
                         "TRADE", p.symbol)
            else:
                LOG.emit(f"Pozisyon kapatildi #{ticket} kar={realised:.2f}",
                         "TRADE", p.symbol)
        return True

    def _closing_deal_pnl(self, result: Any, position: int) -> float | None:
        """Realised P/L of the close we just sent, or None if not readable yet.

        ``p.profit`` from positions_get is the *floating* figure read a moment
        BEFORE the order went out, and carries no commission - so logging it as
        ``kar=`` reported neither the price we actually got nor the full cost of
        the round trip. The broker-side exit path already reports true realised
        P/L (see ExecutionMonitor.reap), and two lines in the same log wearing
        the same label must not be different quantities.

        Read the same way open_market resolves its fill: history_deals_get
        filters on the ORDER ticket, not the deal ticket. Called only after the
        close has already succeeded, so a slow or failed lookup can never hold
        up the close itself - it just falls back.
        """
        order = int(getattr(result, "order", 0) or 0)
        if not order:
            return None
        try:
            with self._lock:
                deals = mt5.history_deals_get(ticket=order)
        except Exception:
            return None
        if not deals:
            return None
        total = 0.0
        seen = False
        for d in deals:
            if int(getattr(d, "position_id", 0)) != position:
                continue
            seen = True
            total += float(d.profit) + float(d.commission) + float(d.swap)
        return total if seen else None

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
                # inflate "closed" to the full original count. confirmed_closed
                # counts True returns (including DONE_PARTIAL) - remaining=-1
                # still makes kill-switch ok:false; callers must not treat
                # confirmed_closed as "fully flat volume".
                return confirmed_closed, -1
        return len(before) - len(remaining), len(remaining)
