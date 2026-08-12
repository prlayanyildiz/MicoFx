from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, fields
from typing import Any

TIMEFRAMES = ["M5", "M15", "M30", "H1"]
GROUPS = ["forex", "index", "commodity", "crypto"]


def _coerce(cls, payload: dict[str, Any]):
    """Build a dataclass from a dict, ignoring unknown keys and casting types.

    Config rows persisted by older versions are missing fields added later, so
    every unknown/absent key falls back to the dataclass default.
    """
    known = {f.name: f for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    for key, value in payload.items():
        f = known.get(key)
        if f is None or value is None:
            continue
        t = f.type if isinstance(f.type, str) else (
            getattr(f.type, "__name__", None)
            or getattr(f.type, "_name", None)
            or getattr(getattr(f.type, "__origin__", None), "__name__", "")
        )
        try:
            if t.startswith("bool"):
                # bool("false") is True in Python - this only ever receives
                # real JSON booleans through the FastAPI routes today (pydantic
                # preserves the type), but this function is also the landing
                # point for anything read back out of the SQLite JSON blobs
                # and any future string-based input path, so the string
                # footgun is worth closing here rather than trusting callers.
                kwargs[key] = value.strip().lower() not in ("false", "0", "", "no")  \
                    if isinstance(value, str) else bool(value)
            elif t.startswith("int"):
                kwargs[key] = int(value)
            elif t.startswith("float"):
                kwargs[key] = float(value)
            elif t.startswith("str"):
                kwargs[key] = str(value)
            else:
                kwargs[key] = value
        except (TypeError, ValueError):
            continue
    return cls(**kwargs)


@dataclass
class SessionWindow:
    """A single intraday trading window, expressed in broker server time."""

    start: str = "00:00"
    end: str = "23:59"

    def minutes(self) -> tuple[int, int]:
        return _hhmm(self.start), _hhmm(self.end)


def _hhmm(value: str) -> int:
    try:
        hh, mm = str(value).split(":")
        return max(0, min(24 * 60 - 1, int(hh) * 60 + int(mm)))
    except (ValueError, AttributeError):
        return 0


@dataclass
class SymbolConfig:
    symbol: str
    group: str = "forex"
    magic: int = 990000
    enabled: bool = True
    timeframe: str = "M5"
    broker_symbol: str = ""          # override when the broker renames an instrument
    # t3_stoch | orb | vwap_rev | donchian | squeeze_brk | flow_rev
    # | mtf_pullback | micro_rev | burst | t3_ribbon | dual_t3 | st_trend
    # | t3_flip
    strategy: str = "t3_stoch"

    # ---- optional second, uncorrelated signal on the same symbol ----
    # The optimizer parks a validated runner-up here (different family, own
    # timeframe, own exit parameters) after every applied run. It is only ever
    # traded when the user flips ``ensemble_enabled`` on for this symbol; the
    # engine then takes entries from either signal and skips the bar entirely
    # when the two disagree.
    ensemble_enabled: bool = False
    secondary_strategy: str = ""     # "" means no secondary candidate stored
    secondary_timeframe: str = ""
    secondary_params: dict = field(default_factory=dict)   # OPT_FIELDS subset
    secondary_score: float = 0.0
    secondary_updated_at: float = 0.0
    secondary_summary: dict = field(default_factory=dict)

    # ---- Bollinger/Keltner squeeze breakout ----
    sqz_length: int = 20             # shared length for both bands
    sqz_bb_sd: float = 2.0           # Bollinger standard deviations
    sqz_kc_atr: float = 1.5          # Keltner ATR multiple
    sqz_momentum_len: int = 12       # linear-regression slope window that picks the side

    # ---- order-flow-proxy exhaustion reversion ----
    flow_length: int = 20            # bars of signed-volume proxy accumulated
    flow_z: float = 2.0              # |z| of that sum that counts as exhaustion
    flow_divergence: bool = True     # also require price/flow disagreement

    # ---- higher-timeframe trend pullback ----
    pull_fast: int = 8               # fast EMA the pullback must reach
    pull_depth_atr: float = 0.5      # how deep the pullback must run, in ATR
    pull_max_bars: int = 6           # pullback must resolve within this many bars

    # ---- cost-scaled micro mean reversion (M5-native scalp) ----
    mr_fast: int = 6                 # fast mean the scalp reverts to, in bars
    mr_stretch_cost: float = 4.0     # displacement required, in ROUND-TURN COST multiples
    mr_confirm: bool = True          # bar must already be turning back toward the mean

    # ---- range-expansion momentum burst (M5-native scalp) ----
    brst_lookback: int = 20          # trailing window the range distribution is built from
    brst_range_z: float = 1.5        # bar range must exceed mean + z * sd of that window
    brst_close_pct: float = 0.7      # close must sit this far into its own bar's extreme

    # ---- Tillson T3 ribbon (fast/slow T3 crossover family) ----
    # T3 is a low-lag curve, so a *pair* of them carries the information a plain
    # moving-average ribbon carries without the lag that makes an EMA ribbon
    # useless intraday. Fast above slow is the bias; the cross is the trigger.
    t3_fast: int = 5                 # fast T3 length
    t3_slow_mult: float = 3.0        # slow T3 length = fast * this
    t3_slope_atr: float = 0.0        # 0 disables; min |slow T3 slope| per bar, in ATR
    # The two lines may run DIFFERENT volume factors. A T3's vf is its curvature
    # knob, not just a smoothing length: the widely shared Tillson scalping
    # template pairs a length-8 / vf-0.7 line with a length-5 / vf-0.618 line, so
    # the fast curve is both shorter and differently damped. 0 inherits
    # ``t3_volume_factor`` and reproduces the old single-vf ribbon exactly.
    t3_fast_vf: float = 0.0

    # ---- T3 slope quality / curvature (t3_stoch + t3_ribbon + t3_flip) ----
    # Second difference of the T3 line in ATR units: "rising" is a one-bar fact,
    # this asks whether the curve is still bending the trade's way instead of
    # decelerating into exhaustion. 0 disables, so the search has to earn it.
    t3_accel_min: float = 0.0

    # ---- optional SuperTrend confirmation (dual_t3 only) ----
    # SuperTrend is an ATR envelope around the bar midpoint whose bands ratchet
    # toward price; its direction flips on a close through the active band. It
    # is the only confirmation layer the minimal dual-T3 core is allowed,
    # because it introduces no new indicator family - it is ATR, the same thing
    # the exits are already made of. 0 multiplier disables it completely.
    st_period: int = 10
    st_mult: float = 0.0

    # ---- adaptive cost-regime gate (scalping families only) ----
    # Percentile ceiling on the bar's cost-to-range ratio inside its own trailing
    # distribution. Unlike ``max_spread_atr`` this is not a fixed number: it
    # follows the symbol and the session, which is what a scalper actually needs
    # since the same spread is cheap at the cash open and ruinous at 23:00.
    cost_rank_max: float = 0.0       # 0 disables

    # ---- opening range breakout ----
    orb_minutes: int = 30
    orb_buffer_atr: float = 0.1
    orb_retest: bool = False         # wait for a pullback + reclaim instead of chasing the break

    # ---- Donchian breakout ----
    don_length: int = 20
    don_buffer_atr: float = 0.0
    don_squeeze: float = 0.0         # 0 disables; only break out of a narrow channel

    # ---- VWAP mean reversion ----
    vwap_sd: float = 2.0
    vwap_reentry: bool = True
    adx_max: float = 0.0             # reversion only; 0 disables

    # ---- liquidity sweep / stop hunt reversal ----
    swp_lookback: int = 20           # bars defining the swing high/low that gets swept
    swp_wick_atr: float = 0.15       # how far past that swing the wick must reach, in ATR

    # ---- MACD histogram zero-cross ----
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # ---- WaveTrend crossover ----
    wt_channel_len: int = 10
    wt_avg_len: int = 21

    # ---- Slow Stochastic crossover (price range, not RSI) ----
    stoch_k_period: int = 10
    stoch_k_smooth: int = 6
    stoch_d_smooth: int = 3

    # ---- Parabolic SAR flip ----
    psar_af_step: float = 0.02
    psar_af_max: float = 0.2

    # ---- TRIX zero-cross (slow, triple-smoothed) ----
    trix_length: int = 14

    # ---- Aroon oscillator zero-cross ----
    aroon_length: int = 14

    # ---- position sizing ----
    lot_mode: str = "fixed"          # "fixed" | "risk"
    fixed_lot: float = 0.01          # broker micro lot: 0.01 FX/commodity, 0.10 index
    risk_percent: float = 0.5        # used when lot_mode == "risk"
    max_lot: float = 0.10            # hard ceiling for risk-based sizing
    max_positions: int = 1           # concurrent positions for this symbol
    # Realised loss on THIS symbol today, as % of the day's start balance, that
    # stops new entries on it for the rest of the broker day - independent of
    # the account-wide daily_loss_pct circuit breaker, so one symbol going bad
    # can't quietly spend the whole account's daily budget while it still has
    # room left on the global number. 0 disables (no per-symbol cap).
    symbol_daily_loss_pct: float = 0.0

    # ---- T3 trend filter ----
    t3_length: int = 6
    t3_volume_factor: float = 0.7

    # ---- Stochastic RSI trigger ----
    rsi_length: int = 9
    stoch_length: int = 9
    smooth_k: int = 3
    smooth_d: int = 3
    stoch_band: float = 20.0         # cross must sit within mid +/- band
    stoch_extreme: float = 80.0      # block entries into an exhausted move

    # ---- higher timeframe trend agreement ----
    htf_factor: int = 6              # base timeframe multiple; 0/1 disables
    htf_mode: str = "t3"             # "t3" | "off"

    # ---- ATR risk model: hard stop, then trail. ----
    #
    # The trade's own exit logic has exactly two parts:
    #
    #   1. a hard stop at ``sl_atr_mult`` x ATR, sent to the broker with the
    #      entry and never removed - it is what is standing there if this
    #      process, the machine, or the internet goes away mid-trade;
    #   2. once open profit reaches ``trail_start_atr`` x ATR, a trailing stop
    #      ``trail_step_atr`` x ATR behind the best closed price seen since
    #      entry, ratcheting forward only.
    #
    # Separately, three flattens can close a position over the top of that:
    # session end (``flat_before_close_min``), day end
    # (``system.day_end_flatten_min``) and the daily-loss halt. They are
    # calendar and account-risk limits, not judgements about the trade, and
    # they do fire on winners - "the trail is the only way out" is true of the
    # trade's own logic, not of the whole system.
    #
    # Deliberately absent: take-profit, scale-out ladders, breakeven jumps,
    # time stops and stale-trade exits. Every one of them caps or truncates a
    # winner, which is the opposite of what a trailing system is for.
    #
    # BREAKEVEN, precisely - the earlier wording of this comment was loose
    # enough to invent a bug out of. The trail sits at
    # ``close - trail_step_atr * ATR``, so it is above entry exactly when open
    # profit exceeds ``trail_step_atr * ATR``. That is unconditional and has
    # nothing to do with ``trail_start_atr``.
    #
    # So ``trail_start_atr <= trail_step_atr`` is LEGAL, common, and often the
    # better setting - it only means the trail begins tightening the stop while
    # it is still below entry, cutting risk earlier instead of waiting. On a
    # ramp-then-collapse replay, NAS100's live 0.5/1.6 pair gives back 0.10R
    # where a "start > step" 2.0/1.6 pair gives back the full 1.00R, and the
    # two are identical once past breakeven. Do NOT add a grid rule or apply
    # validation forbidding it; see test_trail_breakeven_invariant.py.
    atr_period: int = 14
    sl_atr_mult: float = 1.2
    trail_start_atr: float = 0.8
    trail_step_atr: float = 0.6
    trail_mode: str = "atr"          # "atr" | "structure" | "hybrid"
    trail_lookback: int = 5          # bars to look back for swing high/low (structure/hybrid)
    # ---- costs ----
    commission_per_lot: float = 0.0  # round-turn commission in account currency

    # ---- entry filters ----
    adx_period: int = 14
    adx_min: float = 0.0             # 0 disables the regime filter
    max_spread_atr: float = 0.0      # 0 disables; raw accounts rarely need it
    min_atr_ratio: float = 0.0       # ATR / price floor, filters dead markets
    min_body_ratio: float = 0.0      # signal bar body / range floor; 0 disables
    atr_pct_min: float = 0.0         # ATR percentile floor (0-1); skips dead regimes
    cooldown_sec: int = 300          # per-symbol pause after a fill

    # ---- trading hours (broker server time) ----
    use_sessions: bool = True
    sessions: list = field(default_factory=list)
    trade_days: list = field(default_factory=lambda: [1, 2, 3, 4, 5])  # Mon..Sun = 1..7
    flat_before_close_min: int = 0   # close positions N min before the last window ends

    # ---- optimizer bookkeeping ----
    opt_score: float = 0.0
    opt_updated_at: float = 0.0
    opt_summary: dict = field(default_factory=dict)
    # Exit/risk fields from the most recent apply() that were held back
    # because a position was open under this symbol's magic at the time -
    # applied automatically (by the engine) the moment that magic is next
    # seen flat. Empty dict = nothing pending.
    pending_exit_patch: dict = field(default_factory=dict)
    # Same idea, but for a same-identity secondary "refine" (see
    # apply_secondary()): exit/risk keys to merge into secondary_params once
    # no secondary-tagged position is open under this magic.
    pending_secondary_exit_patch: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SymbolConfig":
        if not isinstance(payload, dict):
            # _coerce goes straight to payload.items(), so a non-dict used to
            # surface as AttributeError - a type Store._load_symbols does not
            # catch, even though it explicitly catches JSONDecodeError and
            # TypeError to skip exactly this kind of unreadable row. That call
            # sits outside the sqlite try/except in Store.__init__ and run.py
            # only converts RuntimeError, so one bad row took the whole
            # start-up down as a raw traceback - under pythonw.exe, into a
            # stream nobody sees, with the app simply never appearing.
            #
            # ``null``, a list, a string, a number and a bool are all valid
            # JSON, so they load cleanly and only fail here. TypeError is what
            # the existing handlers already expect.
            raise TypeError(
                f"sembol kaydi bir nesne olmali, {type(payload).__name__} bulundu")
        cfg = _coerce(cls, payload)
        cfg.sessions = [
            {"start": str(s.get("start", "00:00")), "end": str(s.get("end", "23:59"))}
            for s in (payload.get("sessions") or [])
            if isinstance(s, dict)
        ]
        days = payload.get("trade_days")
        if days is not None:
            # Two-sided on purpose. _coerce() assigns list-typed fields
            # verbatim (there is no cast for them), so a non-list that reached
            # here used to survive as an int/str/dict and only fail later, in
            # sessions.evaluate()'s ``day in cfg.trade_days`` - TypeError for
            # every scalar type. That lands inside manage_positions(), whose
            # only guard is the loop-level except in start(), so one corrupt
            # symbol aborted the whole cycle before the risk check and left
            # EVERY open position untrailed, every cycle, permanently.
            #
            # The API rejects all of these outright; this path only ever sees
            # a hand-edited config/defaults.json or a mangled settings blob,
            # where falling back to the dataclass default is what _coerce()
            # does with every other unparseable field. The weekend stays shut
            # regardless - weekend_closed() runs ahead of trade_days.
            valid = (sorted({int(d) for d in days
                             if str(d).isdigit() and 1 <= int(d) <= 7})
                     if isinstance(days, list) else [])
            cfg.trade_days = valid or [1, 2, 3, 4, 5]
        summary = payload.get("opt_summary")
        cfg.opt_summary = summary if isinstance(summary, dict) else {}
        pending = payload.get("pending_exit_patch")
        cfg.pending_exit_patch = pending if isinstance(pending, dict) else {}
        pending_sec = payload.get("pending_secondary_exit_patch")
        cfg.pending_secondary_exit_patch = pending_sec if isinstance(pending_sec, dict) else {}
        sec = payload.get("secondary_params")
        # Only optimiser-owned parameters may ride along in the secondary blob;
        # anything else would let a stored candidate rewrite magic, lots or
        # sessions through the back door when the engine overlays it.
        cfg.secondary_params = ({k: v for k, v in sec.items() if k in OPT_FIELDS}
                                if isinstance(sec, dict) else {})
        sec_summary = payload.get("secondary_summary")
        cfg.secondary_summary = sec_summary if isinstance(sec_summary, dict) else {}
        if cfg.secondary_strategy not in STRATEGIES:
            cfg.secondary_strategy = ""
        if cfg.secondary_timeframe not in TIMEFRAMES:
            cfg.secondary_timeframe = ""
        return cfg

    def has_secondary(self) -> bool:
        """True when a validated second candidate is stored and switched on."""
        return bool(self.ensemble_enabled and self.secondary_strategy
                    and self.secondary_timeframe)

    def session_start_minutes(self) -> int:
        """Minute-of-day the trading session opens; anchors ORB and VWAP."""
        windows = self.session_windows()
        return min(w[0] for w in windows) if windows else 0

    def session_windows(self) -> list[tuple[int, int]]:
        out: list[tuple[int, int]] = []
        for s in self.sessions:
            start, end = _hhmm(s.get("start", "00:00")), _hhmm(s.get("end", "23:59"))
            if start != end:
                out.append((start, end))
        return out


# Fields that engine._update_stop reads live off cfg for a position that is
# ALREADY open - as opposed to entry-signal fields, which only shape NEW
# entries and can't disturb a trade in flight. A "refine" apply (same
# strategy/timeframe, new numbers) must hold these back while a position is
# open, or the stop/trail math for that trade silently changes mid-flight to
# numbers it was never opened or sized against.
#
# ``atr_period`` is here for the same reason even though it is not an
# OPT_FIELD and the optimizer therefore can never write it: every distance
# _update_stop computes is a multiple of the live ATR (trail at
# ``close - trail_step_atr * atr``, the original-risk floor at
# ``atr * sl_atr_mult``), and that ATR is built from cfg.atr_period on every
# cycle rather than snapshotted at entry. Changing it by hand, or from a
# script hitting the API, moves an open position's whole stop geometry just
# as surely as editing trail_step_atr does - it was the one input to that
# math the mid-trade guard did not cover.
EXIT_RISK_FIELDS = frozenset({
    "sl_atr_mult", "trail_start_atr", "trail_step_atr", "trail_mode", "trail_lookback",
    "atr_period",
})

# The three numbers that ARE the exit model, and the range each has to stay
# in. The web layer enforces the same bounds on its own request bodies, but
# that only covers writes a human makes: Optimizer.apply() is also reached
# from the auto-apply path of a search run, which never passes through an
# HTTP handler at all. Since the search grid itself is user-editable, a grid
# axis containing 0 could be searched, "won", and applied straight to a live
# symbol with nothing in between. Kept here, next to OPT_FIELDS, because this
# is the layer both the API and the optimizer already depend on - optimizer.py
# importing the web app to borrow its validator would invert the layering.
EXIT_PARAM_BOUNDS = {
    "sl_atr_mult": (0.0, 20.0),
    "trail_start_atr": (0.0, 20.0),
    "trail_step_atr": (0.0, 20.0),
}


def invalid_exit_param(params: dict) -> str:
    """Reason the exit params are unusable, or "" when they are fine.

    All three bounds are exclusive at the bottom: 0 is not "off" for any of
    them. ``trail_start_atr`` is the one that reads most like it should be -
    both the engine and the simulator arm the trail behind
    ``if trail_start_atr > 0``, so a 0 does not arm it immediately, it stops
    the trail from ever arming and leaves the position on its hard stop for
    its whole life. A 0 ``sl_atr_mult`` collapses that hard stop onto the
    broker's minimum distance, and a negative ``trail_step_atr`` puts the
    trail target on the losing side of price.
    """
    for key, (lo, hi) in EXIT_PARAM_BOUNDS.items():
        if key not in params or params[key] is None:
            continue
        try:
            value = float(params[key])
        except (TypeError, ValueError):
            return f"{key} sayi degil ({params[key]!r})"
        if not math.isfinite(value):
            # NaN loses both comparisons below, so it has to be caught first.
            return f"{key} gecersiz ({value!r})"
        if value <= lo:
            return f"{key} {value:g} - {lo:g}'dan buyuk olmali"
        if value > hi:
            return f"{key} {value:g} - en fazla {hi:g} olabilir"
    return ""


def trail_min_step(min_stop: float, atr: float, trail_step_atr: float) -> float:
    """Smallest stop improvement worth sending to the broker.

    Live needs this so a trade in a slow drift does not put a modify on the
    wire every poll for a fraction of a point. The simulator needs the exact
    same number for the opposite reason: without it the replay ratchets on any
    improvement at all, rides closer behind price than live ever can, and gives
    back less on the reversal that ends the trade - a one-directional optimism
    in every figure the apply gates read.

    Shared rather than written out twice so the two cannot drift apart again;
    engine._update_stop and backtest.simulate are the only callers.
    """
    return max(float(min_stop) * 0.25, float(atr) * float(trail_step_atr) * 0.1)

# Parameters the optimizer is allowed to overwrite on a SymbolConfig.
OPT_FIELDS = [
    "t3_length", "t3_volume_factor", "rsi_length", "stoch_length",
    "smooth_k", "smooth_d", "stoch_band", "htf_factor", "adx_min", "adx_max",
    "sl_atr_mult", "trail_start_atr", "trail_step_atr",
    "trail_mode", "trail_lookback",
    "min_body_ratio", "atr_pct_min",
    "orb_minutes", "orb_buffer_atr", "orb_retest", "vwap_sd",
    "don_length", "don_buffer_atr", "don_squeeze",
    "sqz_length", "sqz_bb_sd", "sqz_kc_atr", "sqz_momentum_len",
    "flow_length", "flow_z", "flow_divergence",
    "pull_fast", "pull_depth_atr", "pull_max_bars",
    "mr_fast", "mr_stretch_cost", "mr_confirm",
    "brst_lookback", "brst_range_z", "brst_close_pct",
    "t3_fast", "t3_slow_mult", "t3_slope_atr", "t3_fast_vf", "t3_accel_min",
    "st_period", "st_mult",
    "cost_rank_max",
    # Spread is a far larger fraction of a scalp's target than of a swing's, so
    # the search is allowed to tune the spread/ATR entry gate per symbol rather
    # than leaving it disabled at the group default.
    "max_spread_atr",
    "swp_lookback", "swp_wick_atr",
    "macd_fast", "macd_slow", "macd_signal",
    "wt_channel_len", "wt_avg_len",
    "stoch_k_period", "stoch_k_smooth", "stoch_d_smooth",
    "psar_af_step", "psar_af_max", "trix_length", "aroon_length",
]

STRATEGIES = ["t3_stoch", "orb", "vwap_rev", "donchian",
              "squeeze_brk", "flow_rev", "mtf_pullback",
              "micro_rev", "burst", "t3_ribbon", "dual_t3", "st_trend",
              "t3_flip", "liq_sweep", "macd_flip", "wavetrend_flip", "stoch_flip",
              "parabolic_flip", "trix_flip", "aroon_flip"]

# True scalps: cost-scaled micro entries that only make sense on fast bars.
# Longer TFs turn them into slow mean-reversion with the wrong cost geometry.
SCALP_STRATEGIES = frozenset({"micro_rev", "burst"})

# Which timeframes each family is allowed to search / trade. An absent family
# means "every configured TF", so an empty map states that no family is
# restricted - which is now the case, deliberately.
#
# This used to keep the scalps on M5 and hand M15+ to the swing families, on
# the budget argument that was written right here: "so the opt budget is not
# wasted pairing micro_rev with H1". That argument does not hold. max_combos
# is spent per sweep - one family on one timeframe - not shared across the
# search, so an extra pairing costs wall-clock and takes nothing away from the
# pairings already running. What the restriction did cost was optionality, and
# the pairings that have actually won were not the predictable ones: XAUUSD
# came back with micro_rev/M5 and NAS100 with stoch_flip/M5. Which bar length
# suits which family on which symbol is exactly the judgement the
# out-of-sample gates exist to make on evidence rather than by assumption.
#
# The mechanism stays. Adding an entry restricts that family again, and an
# explicit empty list still means "nothing" rather than "everything".
STRATEGY_TIMEFRAMES: dict[str, list[str]] = {}

# Exit/risk axes used when searching M15+ (or any non-scalp pairing). A
# multi-hour hold wants a wider hard stop and a looser trail than a five-minute
# scalp does; the shared grid is sized for the latter, so without this overlay
# the search only ever offers H1 candidates a stop tight enough to be noise.
#
# ``trail_step_atr`` reaches 2.0 here on purpose. The whole point of dropping
# take-profit is to stay in a trend until it actually turns, and a trail closer
# than roughly 1 ATR on an hourly bar gets clipped by ordinary retracement long
# before that - a tight trail is just a take-profit that pretends otherwise.
SWING_GRID_OVERLAY: dict[str, list] = {
    "sl_atr_mult": [1.0, 1.2, 1.5, 2.0, 2.5, 3.0],
    "trail_start_atr": [0.6, 0.8, 1.0, 1.4, 2.0, 2.5],
    "trail_step_atr": [0.4, 0.6, 0.8, 1.2, 1.6, 2.0],
    "max_spread_atr": [0.0, 0.08, 0.12, 0.2],
}


def is_scalp_strategy(strategy: str) -> bool:
    return strategy in SCALP_STRATEGIES


def strategy_allows_timeframe(strategy: str, timeframe: str,
                              allow: dict[str, list[str]] | None = None) -> bool:
    """True when this family may be searched/traded on ``timeframe``."""
    table = allow if allow is not None else STRATEGY_TIMEFRAMES
    permitted = table.get(strategy)
    # None (key absent) means "not configured" -> allow every TF, per the
    # module docstring above. `[]` is a different, deliberate statement - a
    # family explicitly restricted to nothing - and `not permitted` treated
    # both the same, so a real empty list silently meant "allow everything"
    # instead of "allow nothing".
    if permitted is None:
        return timeframe in TIMEFRAMES
    return timeframe in permitted


def uses_swing_exits(strategy: str, timeframe: str) -> bool:
    """Longer bars need the wider exit search envelope.

    Decided by the bar, not by the family. The scalp families used to be
    refused this envelope at every bar length, which was harmless only while
    they were pinned to M5. Now that every family may be searched on every
    timeframe, that early return would have handed micro_rev on H1 a stop grid
    sized for five-minute bars - exactly what SWING_GRID_OVERLAY's own comment
    warns about: "the search only ever offers H1 candidates a stop tight enough
    to be noise". A scalp family on hourly bars is holding for hours; what it
    is called does not change how far price travels while it does.

    ``is_scalp_strategy`` still decides position caps and cooldowns elsewhere -
    only the exit-grid question moved to the timeframe.
    """
    # Kept local so models.py never imports the MT5 bridge. This used to carry
    # M10 and H4 as well, so a config stored while those bars were offered
    # still translated to the right number of seconds. Nothing stores them any
    # more - every symbol row uses one of TIMEFRAMES - so the entries were
    # describing a state of the world that no longer exists.
    seconds = {"M5": 300, "M15": 900, "M30": 1800, "H1": 3600}
    return int(seconds.get(timeframe, 0)) >= 900


# Written only by ``Optimizer.apply_secondary`` and only alongside an applied
# primary. ``ensemble_enabled`` is deliberately NOT in this list: storing a
# candidate must never start trading it - that stays a user decision.
SECONDARY_FIELDS = [
    "secondary_strategy", "secondary_timeframe", "secondary_params",
    "secondary_score", "secondary_updated_at", "secondary_summary",
]


@dataclass
class SystemConfig:
    running: bool = False
    autostart_bot: bool = False
    poll_interval_sec: float = 2.0

    # ---- account-level guards ----
    max_total_positions: int = 13
    # Separate sub-caps inside max_total_positions for scalp (micro_rev/burst,
    # M5) vs swing (everything else) positions, so a run of scalp fills
    # cannot use up the whole shared budget and leave no room for a swing
    # setup to open, or vice versa. 0 disables a sub-cap (falls back to being
    # limited only by max_total_positions, the old behaviour).
    max_scalp_positions: int = 0
    max_swing_positions: int = 0
    lot_multiplier: float = 1.0       # scales every symbol's size at once
    size_by_edge: bool = False        # weight each symbol by its validated expectancy
    max_margin_usage_pct: float = 45.0
    daily_loss_pct: float = 3.0
    # When the loss guard trips, force-close what is still open instead of
    # only blocking new entries - otherwise the day's damage keeps floating
    # on whatever stop distance each position already had. Default on: a
    # "daily loss limit" should stop the daily loss, not just further ones.
    daily_loss_flatten: bool = True
    daily_profit_pct: float = 0.0     # 0 disables the profit stop
    min_free_margin: float = 50.0

    # ---- trading hours ----
    # Ignore every symbol's configured session windows and trade days, so the
    # engine evaluates entries around the clock. This only switches off *this
    # app's* calendar: the live market-open / quote-flowing check still runs, and
    # MT5 rejects orders on an instrument that is genuinely closed. Off by
    # default - turning it on trades hours the walk-forward never measured, so
    # the stored holdout numbers no longer describe what the bot is doing.
    trade_all_hours: bool = False
    # Calendar-day flatten, independent of session windows: blocks new entries
    # and closes every bot position in the last N minutes of the broker's day.
    # Session should_flatten() never fires under trade_all_hours (there is no
    # configured close to wind down into), so this is the backstop that keeps
    # trade_all_hours from holding positions overnight. 0 disables it.
    day_end_flatten_min: int = 0

    # ---- backup ----
    # Where the scheduled evening backup (backup.py, run via Windows Task
    # Scheduler) drops its timestamped zip. Read at run time, not baked into
    # the script, so changing it here is the only place that needs editing.
    # Master switch for the nightly backup. The Windows task still fires; it
    # is ``backup.py`` that reads this and exits without writing, which keeps
    # turning backups off a one-click change in the panel instead of a Task
    # Scheduler edit that needs a UAC prompt and cannot be reversed from the
    # UI. Off is a deliberate state, not a failure: the task exits 0.
    backup_enabled: bool = True
    # Deliberately a path that exists on every Windows machine. A drive letter
    # that only exists here (D:, or a USB stick that is not plugged in) turns
    # the nightly backup into a nightly crash on any other install, so the
    # shipped default must never assume one - the operator picks the real
    # destination in the panel.
    backup_dir: str = "C:\\MicoFX_Yedek"
    # A second, independent destination, written in the same run. Empty
    # disables it.
    #
    # This exists because "C: live, D: archive" is not actually two copies
    # when C: and D: are partitions of one SSD, which is the common case and
    # is the case on the machine this was written for - the drive letters look
    # like redundancy and provide none. It matters more here than for most
    # projects: data/micofx.db is gitignored, so every symbol config, every
    # optimizer result and the supervisor's whole learned state live only in
    # that file. GitHub carries the code and none of that.
    #
    # A path under OneDrive (or any synced/removable location) gets the
    # archive off the physical disk without another moving part. Failure to
    # write here is reported but never fails the run - the primary copy still
    # happened, and a backup task that exits non-zero because the cloud folder
    # was briefly locked would just train the operator to ignore it.
    backup_dir_secondary: str = ""
    backup_keep: int = 5              # how many most-recent backups to retain, per destination
    # A UNC destination sends the whole project (code + the settings DB) over
    # the network to whatever share is named - fine for an intentional NAS
    # backup, but a live exfiltration path if something with API access ever
    # gets to set backup_dir without the operator meaning it to. Off by
    # default; local drive-letter paths need no such flag.
    backup_dir_allow_unc: bool = False

    # ---- execution ----
    slippage_points: int = 20
    close_on_stop: bool = False
    # Optional live cost gate (default off — cost is already modelled in the optimizer).
    block_high_cost: bool = False
    max_cost_pct_of_risk: float = 25.0
    # Optimizer parallel process cap: 0 = auto (CPU core count - 2, memory
    # permitting). A weaker/shared cloud VM can set this lower so a walk-forward
    # sweep does not starve the live trading loop and MT5 terminal of CPU.
    opt_max_workers: int = 0

    # ---- scheduled re-optimization ----
    # Markets drift; a parameter set validated three months ago is a different
    # bet today. The scheduler re-runs the *same* walk-forward search on the
    # same interval for every symbol and applies nothing that fails the normal
    # out-of-sample gates, so a stale-but-still-good config simply survives.
    auto_reopt: bool = True
    auto_reopt_days: float = 7.0      # <=0 disables the interval; otherwise clamped to >= 0.5 days
    auto_reopt_hour: int = -1         # local (Windows) hour to prefer; -1 = any hour
    # Local-time weekday gate (time.tm_wday): 0=Mon ... 5=Sat ... 6=Sun; -1 = any day.
    # Default Saturday so the heavy walk-forward runs when markets are quiet.
    auto_reopt_weekday: int = 5

    mt5_terminal_path: str = ""

    # ---- optional terminal autostart (off by default; never bypasses the path lock) ----
    # When enabled, only launches the *configured* terminal64.exe if that exact
    # process isn't already running - it never picks a different install and
    # never substitutes for the mandatory mt5_terminal_path check.
    autostart_mt5: bool = False
    autostart_mt5_wait_sec: int = 90

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SystemConfig":
        return _coerce(cls, payload)
