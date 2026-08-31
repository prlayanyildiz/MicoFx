from __future__ import annotations

import calendar
import time
from dataclasses import dataclass
from datetime import datetime

from .models import SymbolConfig

_DAY = 24 * 60

# Groups that genuinely trade through the weekend. Everything else is closed on
# the broker's Saturday and Sunday no matter what the app is configured to do -
# see ``weekend_closed``.
WEEKEND_OPEN_GROUPS = {"crypto"}

# A closed bar is only an entry candidate while we are still inside the bar
# that follows it, plus one extra bar of poll slack. After a restart the last
# closed stamp can be Friday's: SymbolState is empty, so _refresh_signals
# treats that stamp as a new bar, and the session-close chain-clear never ran
# in this process (there was nothing in memory to clear). Measured 24.08:
# GER40 BUY 363660277, Friday 22:30 UTC bar, Monday 03:15 UTC fill, -1R in
# 12 minutes. The process that stays up across the weekend is already
# protected - this only covers the restart-into-a-gap case.
#
# Lives here rather than in ``engine`` because the walk-forward has to refuse
# the same fills: bar arrays from MT5 are dense, so the bar after Friday's
# close *is* Monday's open and ``simulate`` filled straight across it.
MAX_SIGNAL_BAR_AGE_BARS = 2


def signal_bar_expired(last_bar: float, server_now: float, tf_sec: float) -> bool:
    """True when the closed bar at ``last_bar`` is too old to still act on.

    ``last_bar`` is ``bars.last_closed_time`` - the bar's **open** stamp. The
    budget above is written in bars *after that bar closes*, so the close is
    what the age is measured from. Comparing against the open stamp instead
    spent one of the two bars on the signal bar's own duration before the poll
    loop got a single look at it, which made the real window one bar wide.
    Measured live 31.08 01:15 under the old arithmetic: seven of nine symbols
    were sitting on ``bar_bosluk`` simultaneously.
    """
    if last_bar <= 0 or tf_sec <= 0:
        return False
    return (server_now - (last_bar + tf_sec)) > MAX_SIGNAL_BAR_AGE_BARS * tf_sec


@dataclass
class SessionState:
    open: bool
    reason: str
    minutes_to_close: int | None  # None when no window is active
    minutes_to_open: int | None   # None when a window is active
    window: str


def server_clock(server_epoch: float) -> tuple[int, int]:
    """Return (isoweekday 1..7, minute-of-day) from a naive broker epoch.

    Bar and tick timestamps are the broker's wall clock encoded as Unix time,
    the same numbers ``backtest.session_mask`` reads with ``times % 86400``.
    ``gmtime`` is that reading. ``localtime`` is this machine's timezone and
    is the clock that used to drift an hour off Pepperstone every October.
    """
    st = time.gmtime(server_epoch)
    weekday = st.tm_wday + 1  # tm_wday: Monday == 0
    return weekday, st.tm_hour * 60 + st.tm_min


def server_datetime(server_epoch: float) -> datetime:
    """Naive datetime of the broker's wall clock from a naive broker epoch.

    Same encoding as ``server_clock``: the number looks like Unix time but
    its calendar fields are the broker's clock, recovered with ``gmtime``.
    ``datetime.fromtimestamp`` (this machine's TZ) and ``time.localtime``
    add the Windows offset on top — +3h here, and a different hour after
    European DST — and read every stamp late. Do not use those on MT5
    bar, tick, or deal times. The returned datetime is naive on purpose:
    the broker has no tzinfo in this encoding, and attaching UTC would
    lie about what the number meant.
    """
    st = time.gmtime(server_epoch)
    return datetime(st.tm_year, st.tm_mon, st.tm_mday,
                    st.tm_hour, st.tm_min, st.tm_sec)


def broker_epoch(year: int, month: int, day: int,
                 hour: int = 0, minute: int = 0, second: int = 0) -> int:
    """Inverse of ``server_datetime``: naive broker wall as the MT5 integer.

    Bar, tick and deal stamps are the broker's clock fields stuffed into a
    Unix-looking number. ``calendar.timegm`` of those fields is that number.
    ``datetime(..., tzinfo=UTC).timestamp()`` is a real UTC instant — the
    18.08 analysis cut that compared the two and put the repair-loop loss
    in the wrong bucket. After 1 Nov the two diverge another hour.
    """
    return int(calendar.timegm(
        (year, month, day, hour, minute, second, 0, 0, 0)))


def weekend_closed(cfg: SymbolConfig, server_epoch: float) -> bool:
    """True when this symbol must stay flat because it is the weekend.

    An explicit calendar rule, not a side effect of the feed. ``trade_all_hours``
    drops the configured windows, and the only thing left standing between it and
    a Saturday order was MT5 refusing the fill - which depends on the broker
    marking the symbol closed and on the last tick looking stale enough. A stale
    Friday quote that still reads as fresh would walk straight past that. The day
    of week comes from ``server_clock`` (naive broker epoch, ``gmtime``), the
    same yardstick as the session windows below.

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


def _block_entry_hour(cfg: SymbolConfig, minute: int, state: SessionState) -> SessionState:
    """Refuse a new entry in listed clock hours; do not start a flatten."""
    if not state.open:
        return state
    hours = getattr(cfg, "blocked_entry_hours", None) or []
    hour = minute // 60
    blocked = {int(h) for h in hours
               if str(h).lstrip("-").isdigit() and 0 <= int(h) <= 23}
    if hour not in blocked:
        return state
    return SessionState(
        open=False, reason="saat kapali",
        minutes_to_close=None,
        minutes_to_open=60 - (minute % 60),
        window=state.window,
    )


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
        state = SessionState(open=True, reason="", minutes_to_close=None,
                             minutes_to_open=None, window="tum saatler")
        return _block_entry_hour(cfg, minute, state)

    if not cfg.use_sessions or not windows:
        allowed = day in cfg.trade_days
        state = SessionState(
            open=allowed,
            reason="" if allowed else "gun kapali",
            minutes_to_close=None,
            minutes_to_open=None if allowed else _minutes_to_next_day(day, minute, cfg.trade_days),
            window="7/24" if allowed else "gun disi",
        )
        return _block_entry_hour(cfg, minute, state) if allowed else state

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
        state = SessionState(open=True, reason="", minutes_to_close=best_close,
                             minutes_to_open=None, window=active)
        return _block_entry_hour(cfg, minute, state)

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


def local_utc_offset_seconds(epoch: float | None = None) -> int:
    """This machine's UTC offset in seconds east of UTC, at ``epoch``."""
    when = time.time() if epoch is None else float(epoch)
    return -(time.altzone if time.daylight and time.localtime(when).tm_isdst
             else time.timezone)


# No two wall clocks on earth sit more than this far apart. A larger figure
# never means "the broker moved timezone" - it means the reading is stale,
# which is what a closed market produces: MetaTrader5's Python API exposes no
# TimeCurrent(), so the only broker clock available is the newest tick stamp,
# and over a weekend that is two days old. The first version of this check
# lacked the bound and spent Sunday reporting "-42 hours".
MAX_CLOCK_SKEW_HOURS = 14


def session_clock_skew_hours(
    broker_now: float,
    local_epoch: float | None = None,
    *,
    local_utc_offset_sec: int | None = None,
) -> int | None:
    """Whole hours between the broker wall clock and this machine's.

    ``broker_now`` is the naive epoch MT5 stamps on ticks (wall clock encoded
    as if it were UTC). ``local_epoch`` is a true epoch. Their difference
    minus the machine UTC offset is the gap the session windows sit on: 0
    while Pepperstone and Turkey are both UTC+3, -1 when the broker drops
    to UTC+2 in October and Windows does not.

    None when ``broker_now`` is unknown (0) or when the answer exceeds
    ``MAX_CLOCK_SKEW_HOURS``, which says the reading is stale rather than
    shifted. Callers that can tell staleness directly should still gate on
    that - this bound is the backstop, not the test. Does not shift any gate.
    """
    if not (float(broker_now) > 0):
        return None
    local_epoch = time.time() if local_epoch is None else float(local_epoch)
    if local_utc_offset_sec is None:
        local_utc_offset_sec = local_utc_offset_seconds(local_epoch)
    broker_as_utc = int(round((float(broker_now) - local_epoch) / 3600.0))
    local_h = int(round(int(local_utc_offset_sec) / 3600.0))
    skew = broker_as_utc - local_h
    return None if abs(skew) > MAX_CLOCK_SKEW_HOURS else skew


def session_clock_warning(skew_hours: int | None) -> str | None:
    """Visible line when the two clocks disagree. None when equal or unknown."""
    if skew_hours is None or int(skew_hours) == 0:
        return None
    n = int(skew_hours)
    return (
        f"broker saati yerel saatten {n:+d} saat farkli - "
        f"seanslar broker damgasinda, Windows DST sapmasi"
    )


def describe(cfg: SymbolConfig) -> str:
    windows = cfg.session_windows()
    if not cfg.use_sessions or not windows:
        return "7/24"
    return ", ".join(f"{_fmt(s)}-{_fmt(e)}" for s, e in windows)
