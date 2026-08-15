from __future__ import annotations

import time
from dataclasses import dataclass

from .models import SymbolConfig

_DAY = 24 * 60

# Groups that genuinely trade through the weekend. Everything else is closed on
# the broker's Saturday and Sunday no matter what the app is configured to do -
# see ``weekend_closed``.
WEEKEND_OPEN_GROUPS = {"crypto"}


@dataclass
class SessionState:
    open: bool
    reason: str
    minutes_to_close: int | None  # None when no window is active
    minutes_to_open: int | None   # None when a window is active
    window: str


def server_clock(server_epoch: float) -> tuple[int, int]:
    """Return (isoweekday 1..7, minute-of-day) for the given epoch, local time.

    Session windows and trade days are configured by the user against their
    own machine's wall clock, so that - not UTC or a guessed broker offset -
    is the calendar this must agree with.
    """
    st = time.localtime(server_epoch)
    weekday = st.tm_wday + 1  # tm_wday: Monday == 0
    return weekday, st.tm_hour * 60 + st.tm_min


def weekend_closed(cfg: SymbolConfig, server_epoch: float) -> bool:
    """True when this symbol must stay flat because it is the weekend.

    An explicit calendar rule, not a side effect of the feed. ``trade_all_hours``
    drops the configured windows, and the only thing left standing between it and
    a Saturday order was MT5 refusing the fill - which depends on the broker
    marking the symbol closed and on the last tick looking stale enough. A stale
    Friday quote that still reads as fresh would walk straight past that. The day
    of week comes from the machine's own local calendar (the same clock the
    session windows below are configured against), not UTC or the broker's.

    Crypto is exempt: those symbols trade 24/7 and are supposed to.

    So are individual symbols marked ``weekend_open``. The group is too coarse
    a place to decide this: BRENTOIL-PERP and GOLD-PERP are commodities that
    print bars through the weekend - 9.9% of their hourly bars fall on a
    Saturday or Sunday, against 28% for crypto (full coverage) and 0% for
    SpotBrent and XAUUSD, which are the same asset classes. Held shut by the
    group rule, they lost every weekend hour they could have traded.
    """
    if getattr(cfg, "weekend_open", False):
        return False
    if str(getattr(cfg, "group", "") or "").strip().lower() in WEEKEND_OPEN_GROUPS:
        return False
    day, _minute = server_clock(server_epoch)
    return day >= 6                      # 6 = Saturday, 7 = Sunday


def _prev_day(day: int) -> int:
    return 7 if day == 1 else day - 1


def evaluate(cfg: SymbolConfig, server_epoch: float,
             all_hours: bool = False) -> SessionState:
    """Decide whether ``cfg`` may trade at the given broker time.

    ``all_hours`` is the system-wide override: it drops this app's configured
    windows and trade days entirely. It says nothing about whether the market is
    open - the engine still checks for live quotes, and MT5 refuses orders on a
    closed instrument regardless.
    """
    day, minute = server_clock(server_epoch)
    windows = cfg.session_windows()

    # Unconditional, and deliberately ahead of the all_hours bypass: the weekend
    # is a market fact, not one of this app's windows, so the override does not
    # get to drop it.
    if weekend_closed(cfg, server_epoch):
        return SessionState(
            open=False, reason="hafta sonu kapali", minutes_to_close=None,
            minutes_to_open=_minutes_to_next_day(day, minute, [1, 2, 3, 4, 5]),
            window="hafta sonu",
        )

    if all_hours:
        return SessionState(open=True, reason="", minutes_to_close=None,
                            minutes_to_open=None, window="tum saatler")

    if not cfg.use_sessions or not windows:
        allowed = day in cfg.trade_days
        return SessionState(
            open=allowed,
            reason="" if allowed else "gun kapali",
            minutes_to_close=None,
            minutes_to_open=None if allowed else _minutes_to_next_day(day, minute, cfg.trade_days),
            window="7/24" if allowed else "gun disi",
        )

    best_close: int | None = None
    active = ""
    for start, end in windows:
        if start < end:
            inside = start <= minute < end and day in cfg.trade_days
            remaining = end - minute
        else:
            # Window rolls over midnight: evening leg belongs to today, morning leg to yesterday.
            evening = minute >= start and day in cfg.trade_days
            morning = minute < end and _prev_day(day) in cfg.trade_days
            inside = evening or morning
            remaining = (end + _DAY - minute) if evening else (end - minute)
        if inside:
            # The LAST window to expire, not the first. While two windows
            # overlap, the earlier one running out closes nothing - the later
            # one still holds this minute - and should_flatten reads this
            # number directly: on 08:00-12:00 plus 09:00-17:00 the smaller
            # value made it force-close every position at 11:55, five hours
            # early, after which the first window expired, the count jumped
            # back to five hours and entries resumed. A flatten and a re-entry
            # from a config that asked for neither.
            #
            # Chosen together with the label so the panel names the window it
            # is actually counting down; they used to be picked by different
            # rules (last match wins vs first to expire) and could disagree.
            if best_close is None or remaining > best_close:
                best_close = remaining
                active = f"{_fmt(start)}-{_fmt(end)}"

    if best_close is not None:
        return SessionState(open=True, reason="", minutes_to_close=best_close,
                            minutes_to_open=None, window=active)

    wait = _minutes_to_next_window(day, minute, windows, cfg.trade_days)
    nxt = min(windows, key=lambda w: w[0])
    return SessionState(open=False, reason="seans disi", minutes_to_close=None,
                        minutes_to_open=wait, window=f"{_fmt(nxt[0])}-{_fmt(nxt[1])}")


def should_flatten(cfg: SymbolConfig, server_epoch: float,
                   all_hours: bool = False) -> bool:
    """True inside the wind-down band before the active window closes.

    With ``all_hours`` there is no configured close to wind down into, so the
    session flatten never fires.
    """
    if cfg.flat_before_close_min <= 0 or all_hours:
        return False
    state = evaluate(cfg, server_epoch)
    if not state.open or state.minutes_to_close is None:
        return False
    return state.minutes_to_close <= cfg.flat_before_close_min


def day_end_close(server_epoch: float, minutes_before_midnight: int) -> bool:
    """True in the last ``minutes_before_midnight`` minutes of the broker's day.

    Independent of session windows and of ``trade_all_hours`` - this is the
    calendar backstop, not a per-symbol wind-down. Applies to every symbol,
    crypto included, since the point is "nothing carries past today", not
    "respect this instrument's normal close".
    """
    if minutes_before_midnight <= 0:
        return False
    _day, minute = server_clock(server_epoch)
    return minute >= (_DAY - minutes_before_midnight)


def _fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _minutes_to_next_day(day: int, minute: int, trade_days: list) -> int:
    for ahead in range(1, 8):
        if ((day - 1 + ahead) % 7) + 1 in trade_days:
            return ahead * _DAY - minute
    return 0


def _minutes_to_next_window(day: int, minute: int, windows: list[tuple[int, int]],
                            trade_days: list) -> int:
    best = None
    for ahead in range(0, 8):
        d = ((day - 1 + ahead) % 7) + 1
        if d not in trade_days:
            continue
        for start, _end in windows:
            delta = ahead * _DAY + start - minute
            if delta > 0 and (best is None or delta < best):
                best = delta
    return best if best is not None else 0


def describe(cfg: SymbolConfig) -> str:
    windows = cfg.session_windows()
    if not cfg.use_sessions or not windows:
        return "7/24"
    return ", ".join(f"{_fmt(s)}-{_fmt(e)}" for s, e in windows)
