from __future__ import annotations

import math
import os
import re
import secrets
import signal
import subprocess
import threading
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, create_model

from .. import APP_NAME, __version__
from ..engine import Engine
from ..holdout_cost import capture_book
from ..logbus import LOG
from ..models import (
    EXIT_PARAM_BOUNDS,
    EXIT_RISK_FIELDS,
    GROUPS,
    OPT_FIELDS,
    STRATEGIES,
    TIMEFRAMES,
    SymbolConfig,
    SystemConfig,
    invalid_exit_param,
    strategy_allows_timeframe,
)
from ..mt5client import MT5Client
from ..optimizer import Optimizer
from ..paths import ROOT, WEB_DIR
from ..sessions import describe, server_datetime
from ..store import Store
from ..strategy import _FAMILIES, ENGINE_OPT_FIELDS, opt_fields_read
from ..supervisor import DEFAULTS as AI_SETTINGS_DEFAULTS

TEMPLATES = WEB_DIR / "templates"
STATIC = WEB_DIR / "static"


def _dataclass_patch(name: str, src: type, extra_fields: dict | None = None) -> type[BaseModel]:
    """Optional-field PATCH model whose keys are exactly ``src``'s fields.

    extra=allow plus update_* copying only known keys was how
    {\"patch\": {\"enabled\": false}} returned ok:true and changed nothing.
    extra=forbid makes that a 422 at the door. ``patch`` is an optional
    wrapper so the bulk envelope still works on the single-symbol route.
    """
    # src is a dataclass by contract; mypy only sees ``type``.
    fields: dict[str, Any] = dict.fromkeys(
        src.__dataclass_fields__, (Any | None, None))  # type: ignore[attr-defined]
    if extra_fields:
        fields.update(extra_fields)
    return create_model(name, __config__=ConfigDict(extra="forbid"), **fields)


class _ForbidModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


SymbolPatch = _dataclass_patch(
    "SymbolPatch", SymbolConfig,
    extra_fields={"patch": (dict[str, Any] | None, None)},
)


class SymbolCreate(_ForbidModel):
    symbol: str
    group: str = "forex"
    broker_symbol: str = ""
    enabled: bool = False


class BulkPatch(_ForbidModel):
    symbols: list[str] | None = None
    patch: dict[str, Any] = {}


SystemPatch = _dataclass_patch("SystemPatch", SystemConfig)


class OptRun(_ForbidModel):
    symbols: list[str] | None = None
    apply_best: bool = True
    bars: int | None = None
    timeframes: list[str] | None = Field(default=None, max_length=32)
    # One-off family subset for this run. Does not persist into opt_params.
    # None/empty = inherit the saved list. Bound so a session cookie
    # cannot POST a 10k-name list into the parser / keep-log.
    strategies: list[str] | None = Field(default=None, max_length=32)
    # Waives the settling-time hold: a config normally has to run for
    # reopt_min_age_hours before a scan may replace it.
    force: bool = False


class OptApply(_ForbidModel):
    symbol: str
    run_id: int | None = None
    params: dict[str, Any] | None = None
    score: float = 0.0
    timeframe: str | None = None
    strategy: str | None = None
    force: bool = False
    # Entry-gate retune only — keep live family/TF; use run_id for stamp evidence.
    gates_only: bool = False


class StopBody(_ForbidModel):
    close: bool | None = None


class AccountLockBody(_ForbidModel):
    confirm_login: int
    confirm_server: str


# Sanity bounds on the fields that directly control position size/risk.
# Patch models list every config field (see ``_dataclass_patch``) so a
# client can still send optimizer-only keys; unknown keys are 422. The
# numeric bounds below still catch e.g. risk_percent=500 on a known field.
_SYMBOL_RISK_BOUNDS = {
    "risk_percent": (0.0, 20.0, False),   # (min, max, min_inclusive) - % of balance per trade
    # The whole exit model is these three numbers, so all three are
    # strictly-positive. ``trail_start_atr`` is the one that actually needed
    # a gate: engine._update_stop and backtest both arm the trail behind
    # ``if trail_start_atr > 0``, so a 0 written here does not mean "arm
    # immediately" the way it reads - it means the trail NEVER arms and the
    # position runs on its hard stop alone for its whole life. The optimizer
    # can never produce that (no shipped grid contains 0), so the only way in
    # was a hand-typed value, and a UI ``min`` protects nothing but the UI.
    "sl_atr_mult": (0.0, 20.0, False),
    "trail_start_atr": (0.0, 20.0, False),
    "trail_step_atr": (0.0, 20.0, False),
    # Zero disables the lock (trail is the only way the stop crosses entry).
    # 1.5 is the BE-1 holdout threshold; 5 R is past any trail the book runs.
    "breakeven_at_r": (0.0, 5.0, True),
    "partial_at_r": (0.0, 5.0, True),
    "partial_close_frac": (0.0, 0.9, True),
    "harvest_at_r": (0.0, 5.0, True),
    "harvest_step_atr": (0.0, 20.0, True),
    # The per-symbol daily loss gate, and the only live-risk field the panel
    # let through unbounded (found 15.08, audit slice 7). Zero disables it, so
    # the minimum is inclusive; above 100 it can never fire, which reads as
    # "set" while behaving as "off" - the shape this codebase keeps paying for.
    "symbol_daily_loss_pct": (0.0, 100.0, True),
    # Zero is valid (many CFD accounts charge none); negative is not, and it
    # was accepted. A rebate is a plausible reason someone would try it, and
    # the consequence is that two live risk controls stop working:
    #
    #   engine._try_entry's block_high_cost gate computes
    #   ``cost = commission_per_lot * lot + spread * money_per_price``. A
    #   negative commission drags that below zero, so ``cost / r_value >
    #   max_cost_pct_of_risk`` can never be true and the gate passes every
    #   entry no matter how wide the spread has gone. Measured at -50: a trade
    #   whose spread alone eats 90% of R sails straight through.
    #
    #   _symbol_daily_halt estimates floating P/L as
    #   ``profit + swap - commission_per_lot * volume``. A negative commission
    #   adds to it, so the sticky per-symbol loss halt trips late or not at
    #   all. Measured at -50: two positions 30 dollars down each reported as
    #   40 dollars up.
    #
    # The walk-forward is already safe here - commission_in_price() returns
    # 0.0 for a non-positive value - which is exactly why nothing caught this:
    # the backtest looked fine while the live gates were off.
    "commission_per_lot": (0.0, 10000.0, True),
    "max_lot": (0.0, 100.0, True),
    "max_margin_pct": (0.0, 100.0, True),
    "max_positions": (1, 10, True),
    # Panel-writable and, until 31.08, the only writable symbol field with no
    # bound here at all - the ``max: 240`` on the card is UI-only, so a POST
    # carrying 10**9 was accepted and blocked every entry on that symbol for
    # good. Zero disables the wind-down; a day is the ceiling.
    "flat_before_close_min": (0.0, 1440.0, True),
}

# Indicator lengths. Separate from the table above because that one guards
# money - a bad sl_atr_mult sizes a live trade - while these guard the config
# telling the truth about itself. indicators.py clamps every length with
# ``max(1, int(length))``, so nothing here crashes or diverges from the
# backtest; what a negative period produces is a symbol trading a T3 of length
# 1 while the panel, the stored config and the opt grid all say -5.
#
# Integer periods only. The float axes beside them use zero as a switch -
# adx_max and cost_rank_max carry "0 disables" in models.py - and bounding
# those at 1 would refuse a live config. A length has no such reading: an
# average over no bars is a mistake, not a disabled filter.
# ``adx_length`` / ``atr_length`` sat here until 31.08 and are not fields of
# anything - SymbolConfig carries ``adx_period`` and ``atr_period``. The two
# periods this table was written to bound were the two it never reached.
_INDICATOR_PERIOD_BOUNDS = dict.fromkeys(("t3_length", "rsi_length", "stoch_length", "adx_period", "atr_period", "trail_lookback"), (1, 10000, True))

# The search budget drives the walk-forward that ultimately writes live
# trading params. Every refine round is charged a full ``max_combos`` sweep
# (optimizer.sweep_budget), so an unbounded pair here is a POST that wedges
# the process holding the live book. AGENTS names 2000 as the intended cap;
# the ceiling below leaves headroom for a deliberate wide run without
# admitting 1e9.
_OPT_PARAM_BOUNDS = {
    "max_combos": (1, 100000, True),
    # 0 = coarse sweep only (no local refine). Matches field_help + panel min.
    "refine_rounds": (0, 20, True),
    # 0 = no calendar cap; bar_cap alone binds (optimizer._plan_symbol).
    "lookback_days": (0, 3650, True),
}


_SYSTEM_RISK_BOUNDS = {
    "lot_multiplier": (0.0, 50.0, False),
    "max_margin_usage_pct": (0.0, 100.0, True),   # 0 = uncapped (falls back to free margin), valid
    "max_positions": (1, 20, True),
    "max_lot": (0.0, 100.0, True),   # 0 = off
    "daily_loss_pct": (0.0, 100.0, True),   # 0 = disabled, valid
    "max_concurrent_risk_pct": (0.0, 100.0, True),  # 0 = disabled, valid
    "daily_profit_pct": (0.0, 100.0, True),  # 0 = disabled, valid
    "max_total_positions": (1, 200, True),
    # Panel-writable with UI-only bounds; backup.py prunes to this count.
    "backup_keep": (1, 365, True),
}


def _validate_risk_bounds(patch: dict[str, Any], bounds: dict[str, tuple] = _SYMBOL_RISK_BOUNDS,
                          label: str = "") -> None:
    """Range-check named numeric fields. ``label`` names a nested blob when
    one is being checked, so the 400 says which copy of the field was bad.
    """
    for key, (lo, hi, lo_inclusive) in bounds.items():
        if key not in patch or patch[key] is None:
            continue
        name = f"{label}.{key}" if label else key
        try:
            value = float(patch[key])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            # NaN compares False against everything (< and > both), so it
            # would otherwise sail straight through both bound checks below
            # undetected - json does accept NaN/Infinity by default.
            raise HTTPException(400, f"{name} gecersiz ({value!r})")
        if (value < lo) if lo_inclusive else (value <= lo):
            raise HTTPException(400, f"{name} gecersiz ({value}) - {lo}'dan buyuk olmali")
        if hi is not None and value > hi:
            raise HTTPException(400, f"{name} gecersiz ({value}) - en fazla {hi} olabilir")


_HHMM_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def _validate_sessions(patch: dict[str, Any]) -> None:
    """Reject session windows and trade days that silently mean 24/7.

    models._hhmm is deliberately lenient - it returns 0 for anything it cannot
    parse - and session_windows() then drops any window whose start equals its
    end. Those two reasonable behaviours combine into an unreasonable one: a
    window typed as "9"-"17" instead of "09:00"-"17:00" parses to (0, 0), gets
    dropped as zero-length, and evaluate() falls through to its "no windows"
    branch, which trades every minute of every trade day. The operator asked
    for eight hours and got twenty-four, on a live account, with the panel
    showing "7/24" as the only clue.

    Nothing validated this field at all, so every malformed spelling reached
    the config: "abc", "9", "09:00:00", an empty string, or a deliberate
    zero-length 09:00-09:00. trade_days had the same gap - [] or [0, 9] was
    accepted and left the symbol permanently shut with the panel reporting it
    opens in 0 minutes.
    """
    sessions = patch.get("sessions")
    if sessions is not None:
        if not isinstance(sessions, list):
            raise HTTPException(400, "sessions bir liste olmali")
        for i, item in enumerate(sessions):
            if not isinstance(item, dict):
                raise HTTPException(400, f"sessions[{i}] bir nesne olmali")
            for key in ("start", "end"):
                value = item.get(key)
                if not isinstance(value, str) or not _HHMM_RE.match(value.strip()):
                    raise HTTPException(
                        400, f"sessions[{i}].{key} gecersiz ({value!r}) - "
                             f"SS:DD bicimi gerekli, ornegin 09:00")
            if item["start"].strip() == item["end"].strip():
                # Dropped by session_windows(), and a config left with no
                # windows at all trades around the clock - the opposite of
                # what a zero-length window reads as.
                raise HTTPException(
                    400, f"sessions[{i}] baslangic ve bitis ayni ({item['start']}) - "
                         f"sifir uzunluklu pencere 7/24 islem anlamina gelir; "
                         f"seansi kapatmak icin use_sessions yerine trade_days kullanin")

    days = patch.get("trade_days")
    if days is not None:
        if not isinstance(days, list) or not days:
            raise HTTPException(400, "trade_days bos olamaz (1=Pazartesi .. 7=Pazar)")
        for d in days:
            if not isinstance(d, int) or isinstance(d, bool) or not 1 <= d <= 7:
                raise HTTPException(
                    400, f"trade_days gecersiz gun ({d!r}) - 1..7 arasi olmali "
                         f"(1=Pazartesi, 7=Pazar)")


def _require_optimised_before_enabling(patch: dict[str, Any], cfg) -> None:
    """A symbol may not be switched on until the optimizer has chosen its config.

    EURUSD reached ``enabled`` carrying nothing but the dataclass defaults -
    ``opt_updated_at`` 0.0, ``opt_score`` 0.0, an empty ``opt_summary`` and
    ``mtf_pullback/M5``. That is not a config the search picked; it is the factory
    setting, and the search had in fact already refused this symbol outright
    (365 days, four timeframes, fourteen families, no candidate cleared the
    accept gate). On M5 an FX symbol pays 25-28% of risk in spread against an
    18% live ceiling, so it would either be refused at the gate on every
    signal or fill on parameters nothing has ever validated.

    The same state is one restore away for the whole book: config/defaults.json
    seeds symbol, group, magic, sessions and enabled, while the strategy and
    every exit parameter live only in the gitignored database. A fresh install
    would otherwise start eighteen symbols in exactly EURUSD's position.

    ``opt_updated_at`` is the test rather than the summary, because that is the
    single field apply() stamps when it writes a searched config.
    """
    if not patch.get("enabled"):
        return
    if cfg is None or float(getattr(cfg, "opt_updated_at", 0.0) or 0.0) > 0:
        return
    raise HTTPException(
        400,
        f"{getattr(cfg, 'symbol', '?')} optimize edilmeden acilamaz - su an "
        f"tasidigi {getattr(cfg, 'strategy', '?')}/{getattr(cfg, 'timeframe', '?')} "
        f"aramanin sectigi konfig degil, dokunulmamis varsayilan. Once bu sembol "
        f"icin optimizasyon calistirip uygulayin.")


def _require_current_cost_basis_before_enabling(patch: dict[str, Any], cfg,
                                                optimizer) -> None:
    """A symbol may not be switched on carrying a config priced too cheaply.

    The rule above catches a config the optimizer never chose. This catches
    one it DID choose, under a spread assumption since measured to be wrong in
    the dangerous direction.

    EURJPY is the case. Its recalibrated search produced a candidate that an
    absolute gate refused - cost 0.045R against a gross edge of 0.088 - so the
    config still stored is the pre-calibration one, selected at 57% of the
    symbol's measured spread. Switching it back on would restore a config
    whose selection basis we have measured to be false, and ``opt_updated_at``
    cannot see that: it is set, so the first rule waves it through.

    Directional on purpose. Only a config selected CHEAPER than reality is
    refused; one selected more expensively is conservative and stays
    enableable. CHFJPY shows why that matters - stamped at 3.35, measuring
    3.05 an hour later - because the histogram keeps moving as samples
    accumulate, and a symmetric check would refuse symbols over ordinary
    drift in the safe direction.

    Self-clearing: a fresh search stamps the current scale, and the symbol
    becomes enableable the moment it has a config priced against reality.
    """
    if not patch.get("enabled") or cfg is None or optimizer is None:
        return
    try:
        measured = float(optimizer._spread_scale(cfg.symbol))
    except Exception:
        return
    summary = getattr(cfg, "opt_summary", None) or {}
    # Same convention as Optimizer._beats_incumbent: nothing recorded means
    # the config predates the field, and every one of those WAS measured at
    # 1.0 - walk_forward's default, with no scale passed at all.
    stamped = float(summary.get("spread_scale", 0.0) or 0.0) or 1.0
    if round(measured - stamped, 2) <= 0.05:
        return
    raise HTTPException(
        400,
        f"{cfg.symbol} acilamaz - tasidigi konfig spread'i {stamped:.2f}x "
        f"varsayarak secildi, olculen ise {measured:.2f}x. Yani gercekte "
        f"odedigi maliyetten ucuza secilmis. Once bu sembol icin optimizasyon "
        f"calistirin; kabul edilen bir aday cikarsa kendiliginden acilabilir "
        f"hale gelir.")


def _enforced_cost_ceiling(optimizer: Any, store: Any) -> float:
    """The cost ceiling entries are actually refused at, in R.

    Optimizer.MAX_COST_PER_TRADE_R is the search's own absolute bound. The
    engine refuses on system.max_cost_pct_of_risk, which ships at 25.0 to agree
    with it and sits lower once an operator tightens it. Optimizer.reject_reason
    already takes the minimum of the two for exactly this reason; the panel used
    the constant alone, so it reported - and judged "maliyet" against - a
    ceiling nothing enforces.

    Tighter only. A live gate above the constant does not raise it, and a
    disabled or zeroed gate refuses nothing, so there is nothing to align with.
    """
    ceiling = float(getattr(optimizer, "MAX_COST_PER_TRADE_R", 0.25) or 0.25)
    system = getattr(store, "system", None) if store is not None else None
    if system is not None and getattr(system, "block_high_cost", False):
        live_pct = float(getattr(system, "max_cost_pct_of_risk", 0.0) or 0.0)
        if live_pct > 0:
            ceiling = min(ceiling, live_pct / 100.0)
    return ceiling


def _exit_axes(body: dict[str, Any], names: Any = None):
    """Yield (axis_name, values) for every exit-model axis in an opt-params body.

    The search grid comes in two shapes: a flat shared ``grid`` of
    {param: [values]}, and ``strategy_grids`` of {strategy: {param: [values]}}
    that overrides it per family. Both can carry the exit axes, so both are
    walked - checking only the flat one would leave the per-strategy override
    as an open door to the same value.

    ``names`` selects which axes to yield, so the same two-shape walk serves
    the exit bounds and the indicator-period bounds rather than being written
    twice - the per-strategy override is exactly the door a second copy would
    forget to close.
    """
    def _axes(container: Any):
        if not isinstance(container, dict):
            return
        for axis, values in container.items():
            if axis in names and isinstance(values, (list, tuple)):
                yield axis, values

    if names is None:
        names = EXIT_PARAM_BOUNDS
    yield from _axes(body.get("grid"))
    per_strategy = body.get("strategy_grids")
    if isinstance(per_strategy, dict):
        for sub in per_strategy.values():
            yield from _axes(sub)


# Engine-internal bookkeeping: Optimizer.apply() writes pending_exit_patch
# to defer exit/risk fields until a position is flat, and
# pending_primary_patch to defer a family/TF swap the same way (see
# Engine._apply_pending_exits). pending_secondary_exit_patch is a leftover
# key from the retired second leg - still rejected so an old client cannot
# stage it. They carry no schema of their own, so a client PATCHing this
# field directly could stage ANY symbol field to land later.
_INTERNAL_ONLY_FIELDS = ("pending_exit_patch", "pending_secondary_exit_patch",
                         "pending_primary_patch")

# Panel-visible writes. Search apply() / Store still own the rest; this is
# not _INTERNAL_ONLY_FIELDS (that tuple is pending-exit staging). Family,
# TF, magic, exits and overlays left the card as controls 27.08 - GET still
# returns them for the readout / pending_exit_patch kuyruk.
_OPERATOR_SYSTEM_FIELDS = frozenset({
    "max_margin_usage_pct",
    "lot_multiplier",
    "max_concurrent_risk_pct",
    "charge_costs",
    "block_high_cost",
    "max_cost_pct_of_risk",
    "backup_dir", "backup_dir_secondary", "backup_keep",
    "mt5_terminal_path", "autostart_mt5", "autostart_bot",
})
_OPERATOR_SYMBOL_FIELDS = frozenset({
    "use_sessions", "sessions", "trade_days", "flat_before_close_min",
    "enabled", "group", "broker_symbol",
    # 0 = off. POST accepts 0 only (F44). harvest stays hands-off (F41).
    "partial_at_r",
})
_OPERATOR_OPT_FIELDS = frozenset({
    "lookback_days", "refine_rounds", "max_combos", "timeframes",
    # Cost axes only - see _validate_cost_axis_grid. The rest of the grid,
    # and all of strategy_grids, stay hands-off.
    "grid",
})
# The search cannot fix what its own grid cannot reach. F49 measured the live
# loss concentrating in entry spread/ATR (cheap half -7.0 R, expensive half
# -56.1 R, 4 of 5 symbols agreeing) while ``max_spread_atr``'s shipped floor
# was 0.05 and the per-symbol medians were 0.013-0.072. Editing defaults.json
# does not reach a live book either: Store.opt_params merges {**shipped,
# **stored} per axis, so a stored axis keeps its values forever.
_OPERATOR_GRID_AXES = frozenset({"max_spread_atr", "cost_rank_max"})
_OPERATOR_AI_FIELDS = frozenset({"enabled", "prefer_strong_on_dd", "hard_block_only_quarantine"})


# strategy_allows_timeframe() falls back to "allow every timeframe" for a
# strategy name it does not recognise (see its own docstring) - it was never
# meant to double as an enum check, so an arbitrary/garbage strategy string
# sailed straight through the primary_changing guard. group had no check at
# all. Both land verbatim in the frontend as CSS classes / innerHTML
# fragments (Semboller cards, pill badges), so a bogus value here is not
# just a data-integrity problem - it is another XSS entry point.
_ENUM_FIELDS = {"group": (GROUPS, False), "strategy": (STRATEGIES, False),
                "timeframe": (TIMEFRAMES, False),
                "trail_mode": (("atr", "structure", "hybrid"), False)}


_NON_FINITE_TOKENS = {"nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}


def _reject_non_finite_values(d: dict[str, Any], label: str = "") -> None:
    # Numeric leaves with no per-field bounds table of their own (unlike the
    # small named _SYMBOL_RISK_BOUNDS set). NaN reaching engine.py's live
    # trailing math corrupts comparisons silently.
    for key, value in d.items():
        bad = ((isinstance(value, (int, float)) and not math.isfinite(value))
              or (isinstance(value, str) and value.strip().lower() in _NON_FINITE_TOKENS))
        if bad:
            name = f"{label}.{key}" if label else key
            raise HTTPException(400, f"{name} gecersiz ({value!r})")


def _reject_non_finite_deep(value: Any, path: str = "", depth: int = 0) -> None:
    """Recursive counterpart to ``_reject_non_finite_values``.

    opt_params' numeric leaves (``strategy_grids``/``grid`` search axes) sit
    two levels down - {strategy: {param: [values...]}} - so the flat,
    top-level-only check used for symbol/system patches would walk right past
    a NaN buried in one of those lists. Walks dicts and lists to every leaf
    instead.
    """
    # Depth cap: this walks a client-supplied body, and Python's own recursion
    # limit is ~1000 frames, so a deeply nested payload raised RecursionError
    # inside the handler at roughly 1500 levels. The consequence was only an
    # opaque 500 (Starlette catches it, the bot keeps trading) and the panel
    # binds to 127.0.0.1 with a token required off-localhost, so this was never
    # a live risk - but a request that is refused should say why. No legitimate
    # opt-params body is more than three levels deep
    # ({strategy: {param: [values]}}), so 60 is far above anything real.
    if depth > 60:
        raise HTTPException(400, f"{path or 'govde'} fazla ic ice (60 seviye siniri)")
    if isinstance(value, dict):
        for key, sub in value.items():
            _reject_non_finite_deep(sub, f"{path}.{key}" if path else str(key), depth + 1)
        return
    if isinstance(value, (list, tuple)):
        for i, sub in enumerate(value):
            _reject_non_finite_deep(sub, f"{path}[{i}]", depth + 1)
        return
    bad = ((isinstance(value, (int, float)) and not math.isfinite(value))
          or (isinstance(value, str) and value.strip().lower() in _NON_FINITE_TOKENS))
    if bad:
        raise HTTPException(400, f"{path or 'deger'} gecersiz ({value!r})")


def _reject_wrong_type_against(patch: dict[str, Any], reference: dict[str, Any]) -> None:
    # Supervisor.update_settings() is a raw dict.update() with no type check
    # of its own - a string/list/bool sent for what should be a number (e.g.
    # {"quarantine_hours": "abc"}) got stored verbatim, then crashed
    # supervisor.review()/due() the next time they ran (float("abc"),
    # comparing a float against a str) - and due() is called every engine
    # cycle un-try/excepted, silently killing new-entry evaluation for the
    # rest of that cycle, every cycle, until fixed. bool is checked before
    # (int, float) since bool is a subclass of int in Python.
    for key, value in patch.items():
        if key not in reference or value is None:
            continue
        expected = reference[key]
        if isinstance(expected, bool):
            ok = isinstance(value, bool)
        elif isinstance(expected, (int, float)):
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        else:
            ok = isinstance(value, type(expected))
        if not ok:
            raise HTTPException(
                400, f"{key} gecersiz tip ({value!r}) - {type(expected).__name__} bekleniyor")


def _validate_enum_fields(patch: dict[str, Any], label: str = "") -> None:
    for key, (allowed, empty_ok) in _ENUM_FIELDS.items():
        if key not in patch or patch[key] is None:
            continue
        value = patch[key]
        if empty_ok and value == "":
            continue
        if value not in allowed:
            name = f"{label}.{key}" if label else key
            raise HTTPException(400, f"{name} gecersiz ({value!r}) - izin verilenler: {', '.join(allowed)}")


def _reject_internal_fields(patch: dict[str, Any]) -> None:
    found = [k for k in _INTERNAL_ONLY_FIELDS if k in patch]
    if found:
        raise HTTPException(400, f"{', '.join(found)} disaridan yazilamaz (motor ici alan)")


def _reject_hands_off_fields(patch: dict[str, Any], allowed: frozenset[str]) -> None:
    found = sorted(k for k in patch if k not in allowed)
    if found:
        raise HTTPException(400, f"{', '.join(found)} panelden yazilamaz")


def _cost_axis_grid(body: dict[str, Any], current: dict[str, Any]) -> None:
    """Let the operator retune cost axes, and nothing else, in the shared grid.

    Refuses the whole body if any other axis is present, so one bad key cannot
    smuggle a good half through.

    The merge is the part that matters. ``Store.save_opt_params`` assigns whole
    values (``base[key] = value``), so a one-axis post would replace the entire
    shared grid and silently delete every other axis with it - the search would
    then run on a grid nobody chose. Fold the submission onto the stored grid
    here, where the stored copy is still readable.
    """
    grid = body.get("grid")
    if grid is None:
        return
    if not isinstance(grid, dict):
        raise HTTPException(400, "grid gecersiz - eksen->degerler bekleniyor")
    bad = sorted(k for k in grid if k not in _OPERATOR_GRID_AXES)
    if bad:
        raise HTTPException(
            400, f"{', '.join(bad)} izgara ekseni panelden yazilamaz - "
                 f"yalnizca {', '.join(sorted(_OPERATOR_GRID_AXES))}")
    # These axes sit outside invalid_exit_param (they are entry-cost gates, not
    # exit params), so nothing downstream would catch a poisoned value: the
    # optimizer would take a negative or NaN ceiling straight into a sweep.
    for axis, values in grid.items():
        if not isinstance(values, list) or not values:
            raise HTTPException(400, f"{axis} bos olamaz - deger listesi bekleniyor")
        for raw in values:
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise HTTPException(400, f"{axis} sayisal olmali")
            if not math.isfinite(float(raw)) or float(raw) < 0:
                raise HTTPException(
                    400, f"{axis} degerleri sonlu ve negatif olmamali ({raw})")

    stored = current.get("grid")
    body["grid"] = {**stored, **grid} if isinstance(stored, dict) else dict(grid)


def _validate_one_way_overlay(patch: dict[str, Any]) -> None:
    """``partial_at_r``: 0 to disable. No writer turns it back on.

    F44 measured every rung as net-negative vs off. 23:58 bulk write put
    1.5 on every live symbol; POST now accepts 0 only. Turning off
    mid-trade is monotone safe. ``harvest_at_r`` / ``harvest_step_atr`` /
    ``breakeven_at_r`` stay hands-off.
    """
    value = patch.get("partial_at_r")
    if value is None:
        return
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, "partial_at_r sayi olmali") from exc
    if v == 0.0:
        return
    raise HTTPException(
        400, "partial_at_r yalnizca 0 (kapali) yazilabilir")


def _coerce_symbol_patch(raw: dict[str, Any]) -> dict[str, Any]:
    """Accept the panel's flat body or the bulk door's ``{\"patch\": {...}}``.

    ``SymbolPatch`` is extra=allow and ``update_symbol`` only copies keys that
    already exist on the config. A nested ``patch`` wrapper is not one of
    those keys, so POST {\"patch\": {\"enabled\": false}} used to return
    ok:true and change nothing. Unwrap, then refuse unknown keys - silent
    drop is the third option this codebase is not allowed.
    """
    patch = dict(raw)
    if "patch" in patch:
        nested = patch.pop("patch")
        if not isinstance(nested, dict):
            raise HTTPException(400, "patch bir nesne olmali")
        if patch:
            raise HTTPException(
                400,
                "yamayi duz {\"enabled\": false} veya {\"patch\": {...}} "
                "gonderin, ikisini birden degil")
        patch = nested
    known = set(SymbolConfig.__dataclass_fields__)
    unknown = sorted(k for k in patch if k not in known)
    if unknown:
        raise HTTPException(
            400, f"bilinmeyen alan: {', '.join(unknown)} - yama yok sayilmaz")
    if not patch:
        raise HTTPException(400, "bos yama - degisecek bir alan yok")
    return patch


SESSION_COOKIE = "mico_session"
_holdout_capture_lock = threading.Lock()


def create_app(store: Store, client: MT5Client, engine: Engine, optimizer: Optimizer,
                api_token: str = "") -> FastAPI:
    """Session secret is always on, including 127.0.0.1.

    A missing token used to skip the middleware entirely, so a page on
    another origin could POST /api/bot/panic at the local panel (AS1).
    The secret lives in an HttpOnly SameSite=Strict cookie set on GET /,
    not in the URL and not in the HTML. Every POST/PUT/PATCH/DELETE also
    needs Origin matching this Host (defense in depth on top of SameSite).
    """
    if not api_token:
        api_token = secrets.token_urlsafe(24)
    app = FastAPI(title=f"{APP_NAME} Terminal", version=__version__,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.api_token = api_token
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

    def _on_symbol_newly_enabled(symbol: str) -> None:
        """Operator turned a name on — no AI baggage, spread cap widened if needed."""
        cfg = store.symbols.get(symbol)
        if cfg is None or not cfg.enabled:
            return
        engine.supervisor.update_settings({
            "prefer_strong_on_dd": False,
            "hard_block_only_quarantine": True,
        })
        engine.supervisor.clear(symbol)
        if client.connected:
            try:
                optimizer._recalibrate_spread_cap(symbol, cfg.timeframe)
            except Exception:
                pass

    @app.middleware("http")
    async def _require_session(request, call_next):
        path = request.url.path
        if path.startswith("/static") or path == "/favicon.ico" or path == "/":
            return await call_next(request)
        if not path.startswith("/api/"):
            return await call_next(request)
        offered = request.headers.get("x-mico-token") or request.cookies.get(SESSION_COOKIE)
        if not offered or not secrets.compare_digest(str(offered), api_token):
            return JSONResponse({"detail": "gecersiz veya eksik oturum"}, status_code=401)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            site = (request.headers.get("sec-fetch-site") or "").lower()
            host = request.headers.get("host") or ""
            allowed = {f"http://{host}", f"https://{host}"}
            if site == "cross-site" or not origin or origin not in allowed:
                return JSONResponse({"detail": "istenmeyen kaynak"}, status_code=403)
        return await call_next(request)

    _symbol_payload_cache: dict[str, Any] = {"at": 0.0, "rows": []}

    def symbol_payload(force: bool = False) -> list[dict[str, Any]]:
        # /api/state is polled often; reuse a short snapshot so MT5 is not hammered.
        now = time.time()
        if (not force and _symbol_payload_cache["rows"]
                and now - float(_symbol_payload_cache["at"]) < 3.0):
            return list(_symbol_payload_cache["rows"])
        if not force and optimizer.busy and _symbol_payload_cache["rows"]:
            return list(_symbol_payload_cache["rows"])
        symbols_snapshot = list(store.symbols.values())
        client.set_overrides({c.symbol: c.broker_symbol for c in symbols_snapshot})
        rows = []
        for cfg in symbols_snapshot:
            info = client.info(cfg.symbol) if client.connected else None
            row = cfg.to_dict()
            row["session_text"] = describe(cfg)
            row["resolved_symbol"] = info["name"] if info else None
            row["volume_min"] = info["volume_min"] if info else None
            row["volume_step"] = info["volume_step"] if info else None
            row["digits"] = info["digits"] if info else 5
            row["description"] = info["description"] if info else ""
            row["available"] = info is not None
            rows.append(row)
        _symbol_payload_cache["at"] = now
        _symbol_payload_cache["rows"] = rows
        return list(rows)

    # --------------------------------------------------------------- pages

    @app.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        html = (TEMPLATES / "index.html").read_text(encoding="utf-8")
        # Bust the browser cache when the file on disk changes. Operators
        # were Ctrl+F5'ing after every panel landing; a query stamp is the
        # same GET the StaticFiles mount already serves.
        for name in ("style.css", "field_help.js", "app.js"):
            path = STATIC / name
            stamp = int(path.stat().st_mtime_ns) if path.is_file() else 0
            html = html.replace(f"/static/{name}", f"/static/{name}?v={stamp}", 1)
        resp = HTMLResponse(html)
        resp.set_cookie(
            SESSION_COOKIE, api_token,
            httponly=True, samesite="strict", path="/",
        )
        return resp

    @app.get("/favicon.ico")
    def favicon() -> PlainTextResponse:
        return PlainTextResponse("", status_code=204)

    # --------------------------------------------------------------- state

    @app.get("/api/schema")
    def schema() -> dict[str, Any]:
        """Which OPT axes each family actually reads. Static per process.

        These three blocks used to ride on every /api/state, which the panel
        polls every ~3s. They are built from module
        constants - OPT_FIELDS and _FAMILIES cannot change while the process is
        up - so 2155 bytes and twelve sorted() calls were repeating for a
        payload that never differed.

        Nothing in the panel calls this: the JS consumer (loadSchema /
        optFieldVisible) was deleted with the symbol-guts form. It is kept
        deliberately, as the machine-readable answer to "which axes does this
        family read", which the axis tests and the review loops assert
        against - not as an endpoint waiting for a caller. Do not wire it back
        into the poll.
        """
        return {
            "ok": True,
            "opt_fields": list(OPT_FIELDS),
            "engine_opt_fields": sorted(ENGINE_OPT_FIELDS),
            "strategy_opt_fields": {
                name: sorted(opt_fields_read(name)) for name in _FAMILIES
            },
        }

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        return {
            "ok": True,
            "ts": time.time(),
            "version": __version__,
            **engine.snapshot(),
            "symbols_sig": ",".join(sorted(store.symbols)) + ":" + str(
                int(getattr(store, "symbols_rev", 0) or 0)),
            "system": store.system.to_dict(),
            "opt": optimizer.status(),
        }

    @app.get("/api/symbols")
    def get_symbols() -> dict[str, Any]:
        return {"ok": True, "symbols": symbol_payload()}

    @app.get("/api/broker-symbols")
    def broker_symbols(q: str = "", limit: int = 50) -> dict[str, Any]:
        """Browse the broker's instrument list so names can be mapped by hand."""
        return {"ok": True, "connected": client.connected,
                "symbols": client.search_symbols(q, limit)}

    def _require_connected() -> None:
        # client.positions() returns [] both when nothing is open AND when
        # MT5 is disconnected - the guards below read that as "clear to
        # delete/reset/patch". Disconnected must fail closed (refuse the
        # mutation) instead of silently agreeing there's nothing to protect.
        if not client.connected:
            raise HTTPException(
                503, "MT5 baglantisi yok: acik pozisyonlar dogrulanamiyor, "
                     "islem guvenlik icin reddedildi")

    def _positions(magic: int | None = None) -> list[dict[str, Any]]:
        """Live positions for mutate/ownership guards.

        ``positions()`` returns ``[]`` both when the account is flat AND when
        ``positions_get`` failed mid-call (which flips ``connected`` False -
        see mt5client.py). Optimizer.apply() already re-checks connected
        after the call; web guards that only ``_require_connected()`` *before*
        would treat that empty list as "clear" and fail open (DELETE /
        seed-overwrite / primary exit-family PATCH / orphan-ticket avoid).
        Refuse instead - same fail-closed stance as the optimizer.
        """
        pos = client.positions(magic=magic) if magic is not None else client.positions()
        if not client.connected:
            raise HTTPException(
                503, "MT5 baglantisi koptu: acik pozisyonlar dogrulanamiyor, "
                     "islem guvenlik icin reddedildi")
        return pos

    def _open_under_magic(magic: int) -> list[dict[str, Any]]:
        return [p for p in _positions() if p["magic"] == magic]

    def _pending_orphan_scan(magic: int, symbol: str) -> bool:
        """True while engine.py is still watching this symbol/magic for a
        fill whose ticket was never identified - genuinely invisible to
        client.positions() (that is the entire reason the scan exists).

        Settings key is the historical ``secondary_orphan_scan`` name; the
        machine is for any unresolved fill, primary included.
        """
        scan = store.get_setting("secondary_orphan_scan", {}) or {}
        return symbol in scan and int(scan[symbol].get("magic", -1)) == magic

    def _orphan_ticket_magics() -> set[int]:
        """Live magics of still-open orphan_tickets (H1) - Store.next_magic()
        already avoids orphan_scan's magics on its own (no client needed
        there), but this half needs client.positions() to resolve, which the
        storage layer has no access to. Callers that hand out a fresh magic
        (add/reset) pass this in so a new symbol cannot land on a magic an
        unresolved secondary fill is still sitting on.
        """
        tickets = {int(t) for t in (store.get_setting("secondary_orphan_tickets", []) or [])}
        if not tickets:
            return set()
        return {p["magic"] for p in _positions() if p["ticket"] in tickets}

    def _recent_deal_magics() -> set[int]:
        """Magics that closed a trade inside the supervisor's evidence window.

        A magic freed by deleting a symbol still owns that symbol's closed
        deals, and both readers resolve a deal to a symbol *through* the magic
        - engine.day_stats() and supervisor.review(). Hand the number to a new
        symbol and it opens carrying wins and losses it never made.

        Measured 15.08 on the live account: the book holds ten magics, the
        first free number next_magic would return is 990101, and 990101 has 21
        closed deals in the last thirty days. Nineteen other numbers in the
        band it walks are in the same state, and 1082 magics across the window
        have no symbol in the book at all.

        The window is the supervisor's ``lookback_days``, not today. The
        per-magic guard below reasoned "only today's deals matter"; that is
        wrong for the half of the problem the supervisor owns, whose window is
        thirty days by default.

        Refuses rather than answering ``set()`` while disconnected: a dropped
        link returns an empty deal list exactly as a quiet month does, so a
        silent empty answer here would certify a dirty magic as clean. That is
        the same silent-substitution failure this codebase has already been
        bitten by three times, and the one direction this guard must never be
        wrong in. ``_reject_magic_assignment_if_disconnected_orphans`` does not
        cover it - that gate only fires when orphan tickets exist.
        """
        _require_connected()
        days = float((store.get_setting("supervisor", {}) or {}).get("lookback_days") or 30)
        since = time.time() - max(1.0, days) * 86400.0
        return {int(d.get("magic", 0)) for d in client.deals_since(since)
                if int(d.get("magic", 0)) > 0}

    def _magic_blocked_by_orphan_state(new_magic: int) -> str | None:
        """Human message if ``new_magic`` is still owned by orphan scan/tickets.

        Manual magic PATCH/bulk only checked portfolio clash - next_magic /
        soft-seed already avoid scan (+ live orphan-ticket) magics, so a
        user-typed magic could land on a ghost scan entry (e.g. deleted
        symbol's window still in settings) and have _scan_orphan_candidates
        force-close that symbol's fills as "delayed secondary".
        """
        scan = store.get_setting("secondary_orphan_scan", {}) or {}
        if isinstance(scan, dict):
            for sym, meta in scan.items():
                if isinstance(meta, dict) and int(meta.get("magic", -1)) == int(new_magic):
                    return (f"magic {new_magic} tanimlanamayan ticket taramasinda "
                            f"({sym}) - tarama bitmeden atanamaz")
        if int(new_magic) in _orphan_ticket_magics():
            return (f"magic {new_magic} hala acik orphan ticket uzerinde - "
                    f"once kapanmasini bekleyin")
        # A magic freed by deleting a symbol still owns that symbol's CLOSED
        # deals in broker history. engine.day_stats() and supervisor.review()
        # both attribute a deal to a symbol through its magic, so handing the
        # number straight to a new symbol books the deleted one's wins and
        # losses against it - the new symbol starts the day carrying a P/L and
        # a profit factor it never earned, and the supervisor can suspend it
        # on them. Only today's deals matter: day_stats reads from the day
        # anchor, and the supervisor's window is measured in days, so anything
        # older can no longer be misread.
        # Fail closed. deals_since() answers [] on a dropped connection exactly
        # as it does for "nothing traded today", so checking it while
        # disconnected would clear a magic that may well have traded - the one
        # direction this guard must never be wrong in. Cursor's #075 flagged
        # this as still open after the guard landed.
        if not client.connected:
            return (f"magic {new_magic} dogrulanamadi - MT5 baglantisi yok, "
                    f"bugun islem gormus olabilir (baglanti gelince tekrar deneyin)")
        # The same window auto-assignment uses. These two drifted apart: the
        # automatic path avoids anything traded inside the supervisor's
        # lookback, while this one only looked at today - so a magic freed four
        # days ago passed the hand-typed check and failed the automatic one.
        # The supervisor reads thirty days; a number it can still misattribute
        # is not free to reuse whoever typed it.
        if int(new_magic) in _recent_deal_magics():
            return (f"magic {new_magic} son 30 gunde kapanmis bir isleme ait "
                    f"(silinmis bir sembolden kalmis olabilir) - bu numara "
                    f"verilirse o islemlerin kâr/zarari yeni sembole yazilir")
        day_start = engine._day_start_epoch()
        for deal in client.deals_since(day_start):
            if int(deal.get("magic", 0)) == int(new_magic):
                when = server_datetime(float(deal.get("time", 0) or 0)).strftime("%H:%M")
                return (f"magic {new_magic} bugun {when}'de kapanmis bir isleme ait "
                        f"(silinmis bir sembolden kalmis olabilir) - bu numara "
                        f"verilirse o islemin kâr/zarari yeni sembole yazilir; "
                        f"yarin serbest kalir")
        return None

    def _reject_magic_assignment_if_disconnected_orphans() -> None:
        """Refuse fresh magic assignment while disconnected with orphan tickets.

        Callers always pass ``avoid_magics=_orphan_ticket_magics()`` (which
        503s on mid-call disconnect when tickets are non-empty). This gate
        covers the complementary case: already disconnected before the call,
        so ``_orphan_ticket_magics`` short-circuits to ``set()`` without a
        positions() round-trip and cannot see live orphan magics. Fail closed
        until reconnected or the orphan ticket list is cleared.
        """
        if client.connected:
            return
        tickets = store.get_setting("secondary_orphan_tickets", []) or []
        if tickets:
            raise HTTPException(
                409, "MT5 baglantisi yokken yeni magic atanamiyor: tanimlanamayan "
                     "ticket listesi dolu (magic cakisma riski) - MT5'e "
                     "baglanin veya orphan ticket listesinin temizlenmesini bekleyin")

    @app.post("/api/symbols/{symbol}")
    def patch_symbol(symbol: str, body: SymbolPatch) -> dict[str, Any]:  # type: ignore[valid-type]
        patch = _coerce_symbol_patch(
            body.model_dump(exclude_unset=True))  # type: ignore[attr-defined]
        _reject_internal_fields(patch)
        _reject_hands_off_fields(patch, _OPERATOR_SYMBOL_FIELDS)
        _validate_one_way_overlay(patch)
        _reject_non_finite_values(patch)
        _validate_enum_fields(patch)
        _validate_risk_bounds(patch)
        _validate_risk_bounds(patch, _INDICATOR_PERIOD_BOUNDS)
        _validate_sessions(patch)
        current = store.symbols.get(symbol)
        was_enabled = bool(current.enabled) if current is not None else False
        _require_optimised_before_enabling(patch, current)
        _require_current_cost_basis_before_enabling(patch, current, optimizer)
        # Same hazard as DELETE: the magic number is the only thing that maps
        # an open position back to its managing config. Changing it out from
        # under an open position orphans that position exactly like deleting
        # the symbol would - trail/BE stop, only the broker's own SL is left.
        # A strategy/timeframe change is the same hazard from a different
        # angle: the open position was sized and its exits picked under the
        # OLD family's ATR - optimizer.apply() already refuses this while a
        # position is open (see Optimizer.apply), this endpoint is the other
        # door to the same field and had no such guard. Both are held across
        # the check so a fill landing in this exact instant (engine thread,
        # same lock) cannot slip through as a fresh orphan.
        magic_changing = (current is not None and "magic" in patch
                          and int(patch["magic"]) != current.magic)
        next_strat = patch.get("strategy", current.strategy) if current is not None else None
        next_tf = patch.get("timeframe", current.timeframe) if current is not None else None
        primary_changing = (current is not None
                            and (next_strat != current.strategy or next_tf != current.timeframe))
        # optimizer.apply() holds back exit/risk fields while a position is
        # open (see EXIT_RISK_FIELDS there) because manage_positions()/
        # _update_stop() re-read cfg live every cycle, not a
        # snapshot from entry - this endpoint is the other door to those same
        # fields and had no equivalent guard, so a manual edit (or a script
        # hitting the API directly) could change an open position's stop/
        # trail/partial-ladder math mid-trade. Reject outright rather than
        # replicate optimizer's hold-and-defer machinery a second time here.
        exit_fields_changing = current is not None and any(
            key in patch and patch[key] != getattr(current, key) for key in EXIT_RISK_FIELDS)
        guarded = (magic_changing or primary_changing or exit_fields_changing)
        if guarded:
            _require_connected()
            engine.entry_lock.acquire()
        try:
            if magic_changing:
                new_magic = int(patch["magic"])
                clash = next((s for s, c in store.symbols.items()
                             if s != symbol and c.magic == new_magic), None)
                if clash is not None:
                    raise HTTPException(
                        409, f"magic {new_magic} zaten {clash} tarafindan kullaniliyor - "
                             f"ayni magic iki sembole ayni pozisyonu yonetiyormus gibi karistirir")
                blocked = _magic_blocked_by_orphan_state(new_magic)
                if blocked:
                    raise HTTPException(409, blocked)
            if guarded and current is not None:
                if magic_changing or primary_changing:
                    open_here = _open_under_magic(current.magic)
                    # optimizer.apply() already refuses a family swap while a
                    # pending orphan-scan sits on this magic (NOT-1, prior round)
                    # - this endpoint is the other door to primary_changed,
                    # and had no equivalent: a fill genuinely invisible to
                    # client.positions() would otherwise let the swap through.
                    pending_scan = _pending_orphan_scan(current.magic, symbol)
                    if open_here or pending_scan:
                        what = "magic" if magic_changing else "strateji/zaman dilimi"
                        note = " (+ tanimlanamayan ticket taramasi devam ediyor)" if pending_scan else ""
                        raise HTTPException(
                            409, f"{symbol}: {what} degistirilemedi, {len(open_here)} acik pozisyon var{note} "
                                 f"(once kapatin veya pozisyon kapanmasini bekleyin)")
                if exit_fields_changing and not (magic_changing or primary_changing):
                    open_here = _open_under_magic(current.magic)
                    pending_scan = _pending_orphan_scan(current.magic, symbol)
                    if open_here or pending_scan:
                        changed_fields = sorted(k for k in EXIT_RISK_FIELDS
                                                if k in patch and patch[k] != getattr(current, k))
                        note = " (+ tanimlanamayan ticket taramasi devam ediyor)" if pending_scan else ""
                        raise HTTPException(
                            409, f"{symbol}: cikis/risk parametreleri ({', '.join(changed_fields)}) "
                                 f"degistirilemedi, {len(open_here)} acik pozisyon var{note} "
                                 f"(once kapatin veya pozisyon kapanmasini bekleyin)")
            if primary_changing:
                tf_allow = store.opt_params().get("strategy_timeframes")
                allow = tf_allow if isinstance(tf_allow, dict) else None
                # patch.get("strategy") can be None; the allows table takes str.
                # None already failed the old call (table.get(None) then
                # `None in READABLE_TIMEFRAMES` is False) and 400'd. Keep that.
                if not (isinstance(next_strat, str) and isinstance(next_tf, str)
                        and strategy_allows_timeframe(next_strat, next_tf, allow)):
                    raise HTTPException(
                        400, f"{next_strat}/{next_tf} eslesmesi yasak "
                             f"(scalp yalnizca M5; uzun TF swing ailelerine ait) - "
                             f"motor bu kombinasyonda hicbir zaman giris denemez")
            updated = store.update_symbol(symbol, patch, source="panel")
        finally:
            if guarded:
                engine.entry_lock.release()
        if updated is None:
            raise HTTPException(404, f"{symbol} bulunamadi")
        client.set_overrides({c.symbol: c.broker_symbol for c in list(store.symbols.values())})
        if updated.enabled and not was_enabled:
            _on_symbol_newly_enabled(symbol)
        # Every other mutation endpoint forces the cache fresh; this one didn't,
        # so a poll landing inside the old 1.5s window could hand the rest of
        # the UI (Panel, opt picker) the pre-edit row right after a save - the
        # field the user just changed looked like it had silently reverted.
        return {"ok": True, "config": updated.to_dict(), "symbols": symbol_payload(force=True)}

    @app.post("/api/symbols")
    def create_symbol(body: SymbolCreate) -> dict[str, Any]:
        _reject_magic_assignment_if_disconnected_orphans()
        try:
            cfg = store.add_symbol(
                body.symbol,
                group=body.group or "forex",
                broker_symbol=body.broker_symbol or "",
                enabled=body.enabled,
                # Always resolve avoid via _positions() (503 on mid-call
                # disconnect) - the previous ``if connected else None`` ternary
                # dropped avoid_magics on a TOCTOU disconnect and let next_magic
                # land on a live orphan-ticket magic.
                avoid_magics=_orphan_ticket_magics() | _recent_deal_magics(),
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        client.set_overrides({c.symbol: c.broker_symbol for c in list(store.symbols.values())})
        return {"ok": True, "config": cfg.to_dict(), "symbols": symbol_payload(force=True),
                "system": store.system.to_dict(),
                "message": f"{cfg.symbol} eklendi - kapali; optimizasyon sonrasi acabilirsiniz"}

    @app.delete("/api/symbols/{symbol}")
    def remove_symbol(symbol: str) -> dict[str, Any]:
        cfg = store.symbols.get(symbol)
        if cfg is None:
            raise HTTPException(404, f"{symbol} bulunamadi")
        # Deleting drops the magic -> symbol mapping the engine uses to manage
        # (trail/close) a position, orphaning anything still open under this
        # symbol's magic - the broker's own SL still fires, but active
        # management stops silently. Force disable-and-flat first.
        # A live query, not engine._positions: that cache only refreshes once
        # per poll cycle and goes stale (or empty) the moment the bot is
        # stopped - exactly when a symbol is most likely to be cleaned up.
        # Locked against the engine's own entry path (same lock patch_symbol
        # uses for a magic change) so a fill cannot land in the instant
        # between this check and delete_symbol() and come out orphaned.
        _require_connected()
        with engine.entry_lock:
            open_here = [p for p in _positions() if p["magic"] == cfg.magic]
            if open_here:
                raise HTTPException(
                    409, f"{symbol} silinemedi: {len(open_here)} acik pozisyon var "
                         f"(once kapatin veya 'enabled:false' yapip pozisyon kapanmasini bekleyin)")
            if _pending_orphan_scan(cfg.magic, symbol):
                # No visible position, but engine.py is still watching this
                # exact symbol/magic for a secondary fill it could not
                # identify yet - deleting now frees the magic for reuse
                # (see Store.next_magic) while that fill may still turn up,
                # letting a brand new symbol collide with it.
                raise HTTPException(
                    409, f"{symbol} silinemedi: tanimlanamayan bir ticket taramasi "
                         f"devam ediyor (magic {cfg.magic}) - taramanin bitmesini bekleyin")
            store.delete_symbol(symbol)
        engine.states.pop(symbol, None)
        # forget(), not clear(): clear() keeps the row so a release epoch
        # survives a review, which is right for an operator releasing a symbol
        # and wrong for one leaving the book. Left in place, the verdict, its
        # epoch and its probation flag are inherited whole by the next symbol
        # added under the same name.
        engine.supervisor.forget(symbol)
        engine.execution.drop_symbol(symbol)
        # The tally is pruned against the live book on flush, which drops these
        # only while the name is absent - re-add before the next flush and the
        # deleted symbol's block counts come back as the new one's.
        engine.forget_entry_blocks(symbol)
        engine.forget_spread_ratio(symbol)
        engine.forget_filled_bars(symbol)
        LOG.emit(f"{symbol} portfoyden silindi.", "WARN", symbol)
        client.set_overrides({c.symbol: c.broker_symbol for c in list(store.symbols.values())})
        return {"ok": True, "symbols": symbol_payload(force=True), "system": store.system.to_dict()}

    @app.get("/api/analysis/portfolio-gates")
    def portfolio_gates(min_sample: int = 100, min_fill_rate: float = 0.25) -> dict[str, Any]:
        """Which gate each live symbol fails, in one view. Read-only.

        Pruning decisions kept being made on whichever number was in front of
        us, and twice they were made on the wrong one - a symbol dropped for
        low productivity that was actually a ceiling set under its own normal
        spread, and three dropped on a month of data collected under a session
        regime that had been fixed twenty minutes earlier. This puts every gate
        beside every symbol so the failing one is visible before anything gets
        cut.

        Four gates, each answering a different question:

        ``olculebilir``  Do we KNOW the edge is positive? Holdout expectancy
            against 2 standard errors, SE = 1.2/sqrt(n) on this book's R
            spread. ``min_sample`` is separate and matters: n=30 with a 0.5R
            edge clears 2 SE while telling us very little, and n=407 with
            0.107R fails it while telling us a great deal - that the edge is
            small, precisely. Read the two together, never the flag alone.

        ``maliyet``      Does the config give its edge away? holdout
            cost_per_trade_r against the optimizer's own accept ceiling.
            Walk-forward only charges cost where a signal fired, so a
            bar-average cost series is the wrong comparison (it runs 5-14x
            higher on short timeframes and has already produced wrong
            prune calls).

        ``tavan``        Can the symbol pass its own spread ceiling? The live
            spread/ATR the engine is gating on right now against
            max_spread_atr. One instant, not a distribution - a symbol sitting
            just over the line here may still trade when the tick dips, which
            is exactly how a strangled config looks busy enough to keep.

        ``siklik``       Is it taking the trades the holdout promised? Live
            trades over the supervisor's window against the rate the holdout
            implies. Everything in this book runs far under its modelled
            frequency; this says by how much, per symbol.

        No verdict is returned, on purpose. The gates are evidence for a
        decision a human makes, and a symbol whose config changed hours ago
        has not yet earned any of these numbers - ``config_age_note`` says so
        where it applies.
        """
        sample_floor = max(1, int(min_sample))
        fill_floor = max(0.0, float(min_fill_rate))
        ceiling_r = _enforced_cost_ceiling(optimizer, store)
        window_days = 14
        try:
            window_days = max(1, int(engine.supervisor.settings.get("lookback_days", 14)))
        except Exception:
            pass
        live = {}
        try:
            live = {r["symbol"]: r for r in (engine.supervisor.status().get("symbols") or [])}
        except Exception:
            live = {}

        rows: list[dict[str, Any]] = []
        for cfg in list(store.symbols.values()):
            if not cfg.enabled:
                continue
            summary = cfg.opt_summary or {}
            hold = summary.get("holdout") or {}
            n = int(hold.get("trades") or 0)
            edge = float(hold.get("expectancy") or 0.0)
            se2 = (2 * 1.2 / (n ** 0.5)) if n > 0 else None
            _sl = float(getattr(cfg, "sl_atr_mult", 0.0) or 0.0)
            _ts = float(getattr(cfg, "trail_start_atr", 0.0) or 0.0)
            _st = float(getattr(cfg, "trail_step_atr", 0.0) or 0.0)
            # Two different thresholds, and conflating them is easy - I did.
            #
            # The trail places ``close - trail_step * ATR`` and only writes it
            # when it beats the CURRENT stop, which starts at ``entry -
            # sl_atr_mult * ATR``. So the stop begins improving once the gain
            # clears ``trail_step - sl_atr_mult`` - still a losing stop, just a
            # smaller loss. That is the number that cuts losers.
            #
            # It sits ABOVE entry, i.e. actually protects profit, only once the
            # gain clears ``trail_step`` outright. That is the number that
            # keeps winners.
            #
            # Both are floored by trail_start_atr, which gates the block at all.
            trail_improves = (max(_ts, _st - _sl) / _sl) if (_sl > 0 and (_ts or _st)) else None
            trail_arms = (max(_ts, _st) / _sl) if (_sl > 0 and (_ts or _st)) else None
            cost_r = float(hold.get("cost_per_trade_r") or 0.0)

            state = engine.states.get(cfg.symbol)
            spread_raw = float(getattr(state, "spread", 0.0) or 0.0) if state else 0.0
            primary_atr = float(getattr(state, "atr", 0.0) or 0.0) if state else 0.0
            spread_atr = float(getattr(state, "spread_atr", 0.0) or 0.0) if state else 0.0
            # ``state.spread_atr`` is rewritten every cycle from the last tick,
            # with no session gate in front of it, so outside a symbol's own
            # hours it holds a pre-open quote rather than a spread anything
            # will ever pay.
            session = getattr(state, "session", None) if state else None
            session_open = session.get("open") if isinstance(session, dict) else None
            ceiling = float(cfg.max_spread_atr or 0.0)
            ceiling_leg = "primary"
            if spread_raw > 0 and primary_atr > 0:
                spread_atr = spread_raw / primary_atr

            hold_days = float(summary.get("holdout_days") or 0.0)
            expected = (n / hold_days * window_days) if (n and hold_days > 0) else None
            actual = int((live.get(cfg.symbol) or {}).get("trades") or 0)

            # ``expected`` projects THIS config's holdout rate across the whole
            # review window; ``actual`` counts every trade in that window, most
            # of them made by whatever configs ran before this one. The two only
            # describe the same population once the config has been live for the
            # full window, and nine of the ten live configs are younger than
            # forty-eight hours - so that is the normal state here, not an edge
            # case. US2000's config was three and a half hours old while the
            # ratio was being read as "5% of the promised trades" and flagged;
            # scaled to the age it had actually run, the same numbers say it
            # traded ten times faster than the holdout rate, not twenty times
            # slower. Neither figure is trustworthy, because ``actual`` is not
            # restricted to the config's lifetime either, and the supervisor
            # hands over an aggregate count with no per-trade times to restrict
            # it with. So the reading is withheld rather than repaired.
            #
            # thin_sample, the settling hold in optimizer.reject_reason and the
            # supervisor's watch_min_trades all already refuse to judge a config
            # on evidence it did not produce. This is that same rule on the one
            # path still missing it.
            cfg_age_days = ((time.time() - cfg.opt_updated_at) / 86400.0
                            if cfg.opt_updated_at else None)
            fill_measurable = cfg_age_days is not None and cfg_age_days >= window_days
            fill = (actual / expected) if (expected and fill_measurable) else None

            # Which review layer this symbol falls in. Classification only -
            # nothing here switches anything off. Capital allocation is a
            # decision to take deliberately, and the supervisor is already the
            # one automatic actor on sizing; a second one would fight it.
            #
            # The split that matters is between a weak edge measured on a thick
            # sample and one measured on a thin one. US30 sits at 1.80 sigma on
            # 407 trades - that is "the edge is small, and we know it precisely"
            # - while CHFJPY's 0.28 on 39 is "we cannot tell yet". Treating
            # those the same is how half a book gets cut in one evening.
            #
            # The reverse trap is worth naming too: USDJPY passes at 2.75 sigma
            # on 21 trades and carries the book's highest cost. A sigma earned
            # on a thin sample is the least trustworthy kind of pass.
            thin = n < sample_floor // 2
            if se2 is None or abs(edge) <= se2:
                layer = "soft_aday" if thin else "izle_zayif"
            else:
                layer = "izle_ince_sigma" if thin else "normal"

            fails: list[str] = []
            if se2 is None or abs(edge) <= se2:
                fails.append("olculebilir")
            if cost_r > ceiling_r and bool(getattr(store.system, "charge_costs", True)):
                fails.append("maliyet")
            # A ceiling of 0 disables the filter entirely; only judge a live
            # reading against a ceiling that is actually switched on.
            #
            # And only while the symbol's own session is open. _try_entry never
            # consults this ceiling outside the session - the session gate
            # refuses the entry first - so a breach reported there describes a
            # cost no config can pay. At 08:53 UK100 read 0.3727 against a
            # 0.080 ceiling and GER40 0.1627 against 0.120, both shut until
            # 10:00, and both were reported as failing. That is what made
            # scan-007 record GER40 as having "dropped to a ceiling failure",
            # reading a config regression into the hour of day. Only an
            # explicit "shut" waives it: a state the engine has not filled in
            # yet must not become somewhere a real breach can hide.
            if (ceiling > 0 and spread_atr > 0 and spread_atr > ceiling
                    and session_open is not False):
                fails.append("tavan")
            if fill is not None and fill < fill_floor:
                fails.append("siklik")

            rows.append({
                "symbol": cfg.symbol,
                "strategy": cfg.strategy, "timeframe": cfg.timeframe,
                "trades": n,
                "expectancy_r": round(edge, 3),
                "needs_r": round(se2, 3) if se2 is not None else None,
                "sigma": round(abs(edge) / (se2 / 2), 2) if se2 else None,
                "thin_sample": n < sample_floor,
                "cost_per_trade_r": round(cost_r, 3),
                # Where the trail can FIRST lock anything, in R. Not
                # trail_start_atr, which is what everyone reads and is not the
                # answer: the level the trail places is ``close - trail_step *
                # ATR``, and that only beats the original stop once the gain
                # exceeds trail_step. So the effective point is
                # max(trail_start, trail_step) / sl_atr_mult.
                #
                # SpotBrent advertises trail_start 0.5 and cannot lock anything
                # before 2.2 R. Live winners average 1.08 R, so six of ten
                # symbols could never protect a typical winner - and the single
                # trail move on 13.08 landed on UK100, the lowest at 0.40.
                "trail_arms_at_r": round(trail_arms, 2) if trail_arms else None,
                # Where the stop first moves at all - a reduced loss, not yet a
                # profit. Lower than trail_arms_at_r whenever the step exceeds
                # the stop width.
                "trail_improves_at_r": round(trail_improves, 2) if trail_improves else None,
                "cost_ceiling_r": ceiling_r,
                "spread_atr_now": round(spread_atr, 4) if spread_atr else None,
                # The reading stays visible either way; this says whether it was
                # taken from a market that was actually trading.
                "session_open": session_open,
                "max_spread_atr": ceiling or None,
                "ceiling_leg": ceiling_leg,
                "expected_trades": round(expected, 1) if expected else None,
                "actual_trades": actual,
                "fill_rate": round(fill, 3) if fill is not None else None,
                # Says why fill_rate is missing: too young to compare, not
                # "nothing traded". Without this the blank reads as a zero.
                "config_age_days": round(cfg_age_days, 2) if cfg_age_days is not None else None,
                "fill_measurable": fill_measurable,
                "fails": fails,
                "clean": not fails,
                "layer": layer,
            })

        rows.sort(key=lambda r: (-len(r["fails"]), r["symbol"]))
        by_layer: dict[str, list[str]] = {}
        for row in rows:
            by_layer.setdefault(row["layer"], []).append(row["symbol"])
        by_gate = {g: [r["symbol"] for r in rows if g in r["fails"]]
                   for g in ("olculebilir", "maliyet", "tavan", "siklik")}
        thin_symbols = [r["symbol"] for r in rows if r["thin_sample"]]
        return {
            "ok": True, "rows": rows, "by_gate": by_gate,
            "by_layer": by_layer,
            "window_days": window_days, "min_sample": sample_floor,
            "min_fill_rate": fill_floor,
            "thin_sample": thin_symbols,
            "note": (
                f"{sum(1 for r in rows if r['clean'])}/{len(rows)} sembol dort kapiyi da geciyor. "
                f"Orneklemi {sample_floor} altinda kalan: "
                f"{', '.join(thin_symbols) if thin_symbols else 'yok'} - "
                f"bu sembollerde 'olculebilir' bayragi tek basina okunmamali."
            ),
        }

    @app.get("/api/analysis/spread-ratio")
    def spread_ratio() -> dict[str, Any]:
        """How much wider the live tick's spread runs than the bar's. Read-only.

        The walk-forward gates on the entry BAR's recorded spread; the live
        engine gates on the CURRENT TICK's. A ceiling chosen against the first
        is enforced against the second, which is how FRA40 ended up unable to
        trade a single hour of its own session and USDCHF was nearly deleted
        for it.

        Sampled continuously by the engine rather than estimated, because a
        spot reading is worthless here: 2.5 minutes of one liquid hour put the
        median at 1.28x while reporting sub-1.0 ratios for symbols whose own
        bar median spans hours that sample never touched. Nothing is reported
        as usable until the sample count clears the threshold.
        """
        return {"ok": True, **engine.spread_ratio()}

    @app.get("/api/analysis/entry-blocks")
    def entry_blocks() -> dict[str, Any]:
        """Which gate refuses entries, counted per symbol. Read-only.

        The portfolio-gates view says every symbol trades far under the
        frequency its holdout implies; this says why. Counted only where a
        signal actually reached the entry stage, so the totals separate the
        two causes that look identical from outside - a gate refusing the
        trade, versus the signal never firing in the first place.

        ``signals`` is distinct episodes (the number that compares to a
        holdout trade count). ``attempts`` is poll persistence on the same
        episode and must not be the note's denominator.
        """
        data = engine.entry_blocks()
        total = data["signals"]
        top = next(iter(data["totals"].items()), None)
        data["note"] = (
            "Henuz giris denemesi kaydedilmedi - sayac bu surumle basladi, "
            "bir sinyal gelene kadar bos kalir."
            if not total else
            f"{data['opened']}/{total} sinyal islemle sonuclandi"
            + (f"; en cok engelleyen: {top[0]} ({top[1]})" if top else "")
        )
        return {"ok": True, **data}

    @app.get("/api/analysis/trade-autopsies")
    def trade_autopsies() -> dict[str, Any]:
        """Every close, with fill-vs-signal, MFE/MAE and what was left on the table.

        Read-only. A cell with n<30 is a count, not a finding. Does not change
        entries or exits.
        """
        data = engine.trade_autopsy_report()
        n = int(data.get("n") or 0)
        left = data.get("left_on_table_r")
        data["note"] = (
            "Henuz kapanis otopisi yok - sayac bu surumle basladi."
            if not n else
            f"{n} kapanis"
            + (f"; kazananlarda masada birakilan {left:.2f} R"
               if left is not None else "")
        )
        return {"ok": True, **data}

    @app.post("/api/analysis/entry-blocks/reset")
    def entry_blocks_reset() -> dict[str, Any]:
        engine.reset_entry_blocks()
        return {"ok": True, "message": "Giris engeli sayaclari sifirlandi."}

    @app.post("/api/symbols/{symbol}/reset")
    def reset_symbol(symbol: str) -> dict[str, Any]:
        # Card button left 27.08. Preset rewrite of strategy/TF/exits stays
        # on Store.reset_symbol_to_preset for seed/create; HTTP is shut.
        raise HTTPException(400, f"{symbol}: varsayilana don panelden yazilamaz")

    @app.get("/api/symbols/lot-mode-check")
    def lot_mode_check() -> dict[str, Any]:
        # Not force=True: this is a read-only preview and the forced refresh
        # took the MT5 lock that /api/state and the trading cycle queue behind,
        # to move a balance figure that the 3s cycle has already refreshed.
        account = engine.refresh_account()
        rows = engine.risk.lot_mode_diagnostics(
            float(account.get("balance", 0.0)),
            getattr(engine, "_trade_autopsies", None))
        return {"ok": True, "rows": rows}

    @app.post("/api/symbols/{symbol}/close")
    def close_symbol(symbol: str) -> dict[str, Any]:
        closed, remaining = engine.close_all(
            symbol=symbol, reason="panel sembol kapat")
        return {"ok": remaining == 0, "closed": closed, "remaining": remaining}

    @app.post("/api/symbols/{symbol}/spread-calibrate")
    def spread_calibrate(symbol: str) -> dict[str, Any]:
        """Re-read ``max_spread_atr`` off the symbol's live timeframe.

        One-way widen only (``spread_calibration.cap_from_bands``). Safe while
        a position is open — entry gate only, not mid-trade exit math.
        """
        cfg = store.symbols.get(symbol)
        if cfg is None:
            raise HTTPException(404, f"{symbol} bulunamadi")
        if not client.connected:
            raise HTTPException(409, "MT5 baglantisi yok")
        before = float(getattr(cfg, "max_spread_atr", 0.0) or 0.0)
        optimizer._recalibrate_spread_cap(symbol, cfg.timeframe)
        cfg = store.symbols.get(symbol)
        after = float(getattr(cfg, "max_spread_atr", 0.0) or 0.0) if cfg else before
        changed = abs(after - before) >= 1e-9
        return {
            "ok": True,
            "symbol": symbol,
            "timeframe": cfg.timeframe if cfg else None,
            "before": before,
            "after": after,
            "changed": changed,
            "reason": "kalibre" if changed else "degismedi",
        }

    @app.post("/api/symbols-bulk")
    def bulk_patch(body: BulkPatch) -> dict[str, Any]:
        body.patch = _coerce_symbol_patch(body.patch)
        _reject_internal_fields(body.patch)
        _reject_hands_off_fields(body.patch, _OPERATOR_SYMBOL_FIELDS)
        _validate_one_way_overlay(body.patch)
        _reject_non_finite_values(body.patch)
        _validate_enum_fields(body.patch)
        _validate_risk_bounds(body.patch)
        # The single PATCH checks these and this door did not, so the same
        # field was accepted at two different strictnesses depending on which
        # button the operator used - the same two-callers-two-rules shape as
        # backtest's stop floor.
        _validate_risk_bounds(body.patch, _INDICATOR_PERIOD_BOUNDS,
                              label="toplu duzenleme")
        # Bulk is the other door to the same write, and the one that would
        # apply a malformed window to the whole portfolio at once.
        _validate_sessions(body.patch)
        targets = body.symbols or list(store.symbols)
        needs_tf_check = "strategy" in body.patch or "timeframe" in body.patch
        magic_changing = "magic" in body.patch
        tf_allow = store.opt_params().get("strategy_timeframes") if needs_tf_check else None
        allow = tf_allow if isinstance(tf_allow, dict) else None
        if magic_changing:
            # The same fixed value would land on every target - fine for one
            # symbol, an instant magic collision for more than one.
            new_magic = int(body.patch["magic"])
            if len(targets) > 1:
                raise HTTPException(
                    409, f"magic {new_magic} birden fazla sembole ayni anda atanamaz "
                         f"(her sembolun magic'i benzersiz olmali)")
            clash = next((s for s, c in store.symbols.items()
                         if s not in targets and c.magic == new_magic), None)
            if clash is not None:
                raise HTTPException(
                    409, f"magic {new_magic} zaten {clash} tarafindan kullaniliyor")
        changed = 0
        rejected: list[str] = []
        # Same hazard patch_symbol guards per-symbol: a strategy/TF/magic
        # change under an open position orphans it from trail/BE. Bulk went
        # through update_symbol directly with no such check at all. One lock
        # for the whole batch (bulk edits are rare, not hot-path) rather than
        # acquiring per symbol.
        # Same gap patch_symbol() closes per-symbol: bulk went through
        # update_symbol directly with no exit/risk-field holdback at all.
        exit_fields = [k for k in EXIT_RISK_FIELDS if k in body.patch]
        # Bulk is the other door to enabling a symbol - "Tumunu Ac" walks the
        # whole book - so it has to refuse an unsearched config exactly as the
        # per-symbol route does. Checked before the lock: nothing is written
        # yet, and refusing the whole batch is right when part of it is unsafe.
        for target in targets:
            _require_optimised_before_enabling(body.patch, store.symbols.get(target))
            _require_current_cost_basis_before_enabling(
                body.patch, store.symbols.get(target), optimizer)
        guarded = (needs_tf_check or magic_changing or bool(exit_fields))
        if guarded:
            _require_connected()
            engine.entry_lock.acquire()
        try:
            # Orphan-state magic block under the same lock as apply (matches
            # patch_symbol) - checking outside left a window where engine
            # could open a scan on new_magic between the check and the write.
            if magic_changing:
                blocked = _magic_blocked_by_orphan_state(new_magic)
                if blocked:
                    raise HTTPException(409, blocked)
            # One positions() snapshot for the whole batch - and the
            # post-call connected re-check inside _positions() - so a
            # mid-request positions_get failure cannot make open_magics /
            # watch_magics look empty while a second raw call might disagree.
            all_pos = _positions() if guarded else []
            open_magics = {p["magic"] for p in all_pos} if guarded else set()
            # Historical settings key; the scan is for any unresolved fill.
            orphan_scan = store.get_setting("secondary_orphan_scan", {}) or {} if guarded else {}
            for symbol in targets:
                current = store.symbols.get(symbol)
                if current is None:
                    continue
                if needs_tf_check and current is not None:
                    next_strat = body.patch.get("strategy", current.strategy)
                    next_tf = body.patch.get("timeframe", current.timeframe)
                    if not strategy_allows_timeframe(next_strat, next_tf, allow):
                        rejected.append(symbol)
                        continue
                pending_scan = (
                    symbol in orphan_scan
                    and int(orphan_scan[symbol].get("magic", -1)) == current.magic
                ) if current is not None else False
                symbol_changing = (
                    (needs_tf_check and (
                        body.patch.get("strategy", current.strategy) != current.strategy
                        or body.patch.get("timeframe", current.timeframe) != current.timeframe))
                    or (magic_changing and int(body.patch["magic"]) != current.magic)
                ) if guarded else False
                if symbol_changing and (current.magic in open_magics or pending_scan):
                    rejected.append(symbol)
                    continue
                if exit_fields and current is not None:
                    exit_changing = any(body.patch[k] != getattr(current, k) for k in exit_fields)
                    if exit_changing and (current.magic in open_magics or pending_scan):
                        rejected.append(symbol)
                        continue
                current = store.symbols.get(symbol)
                was_enabled = bool(current.enabled) if current is not None else False
                material = current is not None and any(
                    getattr(current, k, None) != body.patch[k]
                    for k in body.patch if hasattr(current, k))
                updated = store.update_symbol(symbol, body.patch, source="panel toplu")
                if updated is not None and material:
                    changed += 1
                if updated is not None and updated.enabled and not was_enabled:
                    _on_symbol_newly_enabled(symbol)
        finally:
            if guarded:
                engine.entry_lock.release()
        result = {"ok": True, "changed": changed, "symbols": symbol_payload(force=True)}
        if rejected:
            result["rejected"] = rejected
        return result

    @app.post("/api/symbols-sort")
    def sort_symbols() -> dict[str, Any]:
        order = store.sort_symbols_by_group()
        return {"ok": True, "order": order, "symbols": symbol_payload(force=True)}

    @app.post("/api/symbols-seed")
    def seed(overwrite: bool = False) -> dict[str, Any]:
        if overwrite:
            # replace_with_defaults deletes every symbol row - same orphan class
            # as DELETE, but for the whole portfolio at once. Refuse while any
            # bot-owned position is still open.
            _require_connected()
            with engine.entry_lock:
                symbols_snapshot = list(store.symbols.values())
                magics = {c.magic for c in symbols_snapshot}
                open_bot = [p for p in _positions() if p["magic"] in magics]
                if open_bot:
                    raise HTTPException(
                        409, f"portfoy sifirlanamadi: {len(open_bot)} acik bot pozisyonu var "
                             f"(once kapatin veya panic ile duzleyin)")
                scanning = sorted(c.symbol for c in symbols_snapshot
                                  if _pending_orphan_scan(c.magic, c.symbol))
                if scanning:
                    raise HTTPException(
                        409, f"portfoy sifirlanamadi: tanimlanamayan ticket taramasi "
                             f"devam eden semboller var: {', '.join(scanning)} - taramalarin "
                             f"bitmesini bekleyin")
                count = store.replace_with_defaults()
                # replace_with_defaults clears persisted orphan settings; keep
                # the live engine maps in sync so a stale in-memory window
                # cannot force-close fills under freshly seeded default magics.
                if hasattr(engine, "_orphan_scan"):
                    engine._orphan_scan.clear()
                if hasattr(engine, "_orphan_tickets"):
                    engine._orphan_tickets.clear()
                if hasattr(engine, "_save_orphan_scan"):
                    engine._save_orphan_scan()
                if hasattr(engine, "_save_orphan_tickets"):
                    engine._save_orphan_tickets()
        else:
            # H1: soft-seed can silently reassign a stale defaults.json magic
            # onto whatever it collides with (portfolio/scan handled inside
            # Store.seed_symbols already) - the live-orphan-ticket half still
            # needs client.positions() to resolve, same as create/reset (L1).
            _reject_magic_assignment_if_disconnected_orphans()
            count = store.seed_symbols(
                overwrite=False,
                avoid_magics=_orphan_ticket_magics() | _recent_deal_magics(),
            )
        return {"ok": True, "seeded": count, "symbols": symbol_payload(force=True),
                "system": store.system.to_dict()}

    # -------------------------------------------------------------- system

    @app.get("/api/system")
    def get_system() -> dict[str, Any]:
        return {"ok": True, "system": store.system.to_dict()}

    @app.post("/api/system")
    def patch_system(body: SystemPatch) -> dict[str, Any]:  # type: ignore[valid-type]
        patch = body.model_dump(exclude_unset=True)  # type: ignore[attr-defined]
        patch.pop("running", None)  # bot state is owned by start/stop
        lock_keys = [k for k in ("account_lock_login", "account_lock_server") if k in patch]
        if lock_keys:
            raise HTTPException(
                400,
                f"{', '.join(lock_keys)} buradan yazilamaz - "
                "bagli hesabi kilitlemek icin /api/account-lock kullanin",
            )
        _reject_hands_off_fields(patch, _OPERATOR_SYSTEM_FIELDS)
        _reject_non_finite_values(patch)
        _validate_risk_bounds(patch, _SYSTEM_RISK_BOUNDS)
        # Both destinations go through the identical gate: the secondary one
        # receives the same archive, settings DB and all, so "it is only a
        # copy" buys it no leniency.
        for field in ("backup_dir", "backup_dir_secondary"):
            if field not in patch or not patch[field]:
                continue
            path = str(patch[field]).strip()
            is_unc = path.startswith("\\\\") or path.startswith("//")
            # Not a full path-safety audit - just enough to catch a typo/blank
            # value silently pointing the nightly backup at nothing. Must be a
            # local absolute path (drive letter) or a UNC share, and not the
            # bare drive root (never want backups written directly to C:\).
            valid = (
                (len(path) >= 3 and path[1] == ":" and path[2] in "\\/" and len(path) > 3)
                or is_unc
            )
            if not valid:
                raise HTTPException(
                    400, f"{field} gecersiz: {path!r} - tam bir yol olmali "
                         f"(orn. C:\\MicoFX_Yedek), surucu koku olamaz")
            if is_unc:
                # A UNC destination sends the whole project - code AND the
                # settings DB - over the network to whatever share is named.
                # Fine for an intentional NAS backup; the latch is Store-only
                # (not an HTTP key) so a panel POST cannot flip it on.
                if not store.system.backup_dir_allow_unc:
                    raise HTTPException(
                        400, f"{field} UNC ({path!r}) - backup_dir_allow_unc kapali "
                             f"(agdaki bir paylasima proje + veritabani kopyalanacak)")
        # Same threat shape as backup_dir one screen up, and until 31.08 this
        # one had no check at all: the value is handed to _exe_from_path and
        # then to subprocess.Popen by ensure_terminal_process, with
        # autostart_mt5 shipping True. An accepted POST is a launched process.
        if "mt5_terminal_path" in patch:
            raw = str(patch["mt5_terminal_path"] or "").strip()
            if raw:
                is_unc = raw.startswith("\\\\") or raw.startswith("//")
                absolute = (len(raw) >= 4 and raw[1] == ":"
                            and raw[2] in "\\/") or is_unc
                if not absolute:
                    raise HTTPException(
                        400, f"mt5_terminal_path gecersiz: {raw!r} - tam bir yol "
                             f"olmali (orn. C:\\Program Files\\MetaTrader 5)")
                if is_unc and not store.system.backup_dir_allow_unc:
                    raise HTTPException(
                        400, f"mt5_terminal_path UNC ({raw!r}) - agdaki bir "
                             f"paylasimdan terminal calistirilmaz")
                # A directory is legal and is what the live book carries;
                # _exe_from_path appends the name. Naming a file is legal only
                # when it is the terminal - not MetaEditor, not anything else.
                tail = raw.replace("/", "\\").rstrip("\\").rsplit("\\", 1)[-1]
                if tail.lower().endswith(".exe") and tail.lower() != "terminal64.exe":
                    raise HTTPException(
                        400, f"mt5_terminal_path gecersiz: {tail!r} - yalnizca "
                             f"terminal64.exe veya kurulum klasoru yazilabilir")
            patch["mt5_terminal_path"] = raw
        updated = store.update_system(patch, source="panel sistem")
        result: dict[str, Any] = {"ok": True, "system": updated.to_dict()}
        if "mt5_terminal_path" in patch:
            client.set_terminal_path(updated.mt5_terminal_path)
            LOG.emit(f"MT5 yolu guncellendi: {updated.mt5_terminal_path or '(bos)'}", "INFO")
            ok = client.reconnect()
            result["mt5_reconnect"] = ok
            result["mt5_error"] = client.last_error
            result["terminal"] = client.terminal_flags()
            result["configured_path"] = updated.mt5_terminal_path
        if "autostart_mt5" in patch:
            client.autostart = bool(updated.autostart_mt5)
        return result

    @app.post("/api/account-lock")
    def confirm_account_lock(body: AccountLockBody) -> dict[str, Any]:
        # The only door that retargets the lock. /api/system refuses those
        # two fields so a typo in a bulk PATCH cannot silently follow the
        # terminal onto a live login.
        account = engine.refresh_account(force=True)
        login = int(account.get("login") or 0)
        server = str(account.get("server") or "").strip()
        confirm_login = int(body.confirm_login)
        confirm_server = str(body.confirm_server or "").strip()
        if login <= 0:
            raise HTTPException(400, "bagli hesap yok - once MT5 baglanin")
        if confirm_login != login or confirm_server != server:
            raise HTTPException(
                400,
                f"onay eslesmedi: yazilan {confirm_login} @ {confirm_server}, "
                f"bagli {login} @ {server}",
            )
        updated = store.update_system(
            {"account_lock_login": login, "account_lock_server": server},
            source="panel hesap-kilidi",
        )
        enforce = getattr(engine, "_enforce_account_lock", None)
        if callable(enforce):
            enforce(account)
        LOG.emit(f"hesap kilidi onaylandi: {login} @ {server}", "WARN")
        return {"ok": True, "system": updated.to_dict()}

    @app.post("/api/bot/start")
    def bot_start() -> dict[str, Any]:
        return engine.start()

    @app.post("/api/bot/stop")
    def bot_stop(body: StopBody | None = None) -> dict[str, Any]:
        return engine.stop(close_positions=body.close if body else None)

    @app.post("/api/bot/panic")
    def bot_panic() -> dict[str, Any]:
        return engine.panic()

    @app.post("/api/mt5/reconnect")
    def mt5_reconnect() -> dict[str, Any]:
        client.set_terminal_path(store.system.mt5_terminal_path)
        ok = client.reconnect()
        return {
            "ok": ok,
            "error": client.last_error,
            "terminal": client.terminal_flags(),
            "configured_path": store.system.mt5_terminal_path,
        }

    @app.post("/api/day/resume")
    def day_resume() -> dict[str, Any]:
        engine.risk.daily.resume()
        LOG.emit("Gunluk limit kilidi manuel olarak kaldirildi.", "WARN")
        return {"ok": True}

    # ----------------------------------------------------------- positions

    @app.get("/api/positions")
    def positions() -> dict[str, Any]:
        # positions_view() reads client.positions(), which returns [] both when
        # the account is flat AND when positions_get failed mid-call. Every
        # MUTATING path already refuses to confuse those two (_require_connected
        # / _positions, both stating it in as many words), and /api/state carries
        # mt5.connected beside its own copy of the list. This endpoint carried
        # neither, so an empty answer here was indistinguishable from a clean
        # book - and this is the endpoint the review loops read to assert "every
        # open position has a stop". A dropped connection would have produced
        # "no positions, nothing unprotected" rather than "cannot tell".
        #
        # Reported rather than refused: unlike the mutating guards there is
        # nothing here to fail closed ON, and 503-ing a display route would
        # blank the dashboard on a blip. The caller is told which of the two it
        # is and can decide.
        return {"ok": True, "connected": client.connected,
                "positions": engine.positions_view()}

    @app.post("/api/positions/{ticket}/close")
    def close_ticket(ticket: int) -> dict[str, Any]:
        # Without this, any ticket number - including a manually/externally
        # opened position sharing this account - could be closed through
        # this route; the ticket itself carries no notion of "ours".
        pos = next((p for p in _positions() if p["ticket"] == int(ticket)), None)
        if pos is None:
            raise HTTPException(404, "pozisyon bulunamadi (zaten kapanmis olabilir)")
        owned_magics = {c.magic for c in store.symbols.values()}
        if pos["magic"] not in owned_magics:
            raise HTTPException(
                403, f"bu pozisyon MicoFX'e ait degil (magic {pos['magic']}) - buradan kapatilamaz")
        fill: dict[str, Any] = {}
        ok = client.close_position(int(ticket), store.system.slippage_points,
                                   "MicoFX manuel", fill=fill)
        if not ok:
            return {"ok": False}
        # close_position True includes DONE_PARTIAL - re-diff so the UI does
        # not treat a still-open remainder as fully closed.
        still = next((p for p in _positions() if p["ticket"] == int(ticket)), None)
        if still is not None:
            return {
                "ok": False,
                "partial": True,
                "closed_volume": float(fill.get("volume", 0.0)),
                "remaining_volume": float(still.get("volume", 0.0)),
            }
        return {"ok": True, "closed_volume": float(fill.get("volume", pos["volume"]))}

    @app.post("/api/positions-close-all")
    def close_everything() -> dict[str, Any]:
        closed, remaining = engine.close_all(reason="panel tumunu kapat")
        return {"ok": remaining == 0, "closed": closed, "remaining": remaining}

    # ----------------------------------------------------------- optimizer

    @app.get("/api/opt/params")
    def opt_params() -> dict[str, Any]:
        return {"ok": True, "params": store.opt_params()}

    @app.post("/api/opt/params")
    def set_opt_params(body: dict[str, Any]) -> dict[str, Any]:
        # Panel only offers lookback / refine / max_combos / timeframes, plus
        # the cost axes of the shared grid (F49). min_trades and the rest stay
        # in the saved blob; apply() still reads them.
        _reject_hands_off_fields(body, _OPERATOR_OPT_FIELDS)
        _cost_axis_grid(body, store.opt_params())
        if "timeframes" in body:
            raw = body["timeframes"]
            if not isinstance(raw, list) or not raw:
                raise HTTPException(400, "timeframes bos olamaz")
            unknown = [str(t) for t in raw if str(t) not in TIMEFRAMES]
            if unknown:
                raise HTTPException(400, f"timeframes gecersiz: {', '.join(unknown)}")
            body["timeframes"] = [str(t) for t in raw]
        # These parameters drive the walk-forward search that ultimately
        # writes live trading params via apply() - same NaN/Infinity class of
        # risk as the symbol-level fields. strategy_grids/grid nest their
        # numeric axes inside {strategy: {param: [values...]}}, so this needs
        # the recursive check, not the flat top-level-only one.
        _reject_non_finite_deep(body)
        _validate_risk_bounds(body, _OPT_PARAM_BOUNDS)
        metric = body.get("selection_metric")
        if metric is not None and metric not in (
                "score", "money_per_day", "gap_freq", "costed_e"):
            raise HTTPException(400, "selection_metric gecersiz")
        # The grid is the upstream of every applied parameter: an axis holding
        # a 0 gets searched, can win on score, and is then written to a live
        # symbol by the auto-apply path. Optimizer.apply refuses it at the far
        # end, but a grid that can only produce rejected candidates is a
        # silently broken search - better to refuse the axis at the point it
        # is set, while there is a human to read the message.
        for axis, values in _exit_axes(body):
            for value in values:
                bad = invalid_exit_param({axis: value})
                if bad:
                    raise HTTPException(400, f"optimizer grid: {bad}")
        # Same argument one axis over. An indicator length of 0 or below is
        # clamped to 1 by indicators.py, so the search would quietly evaluate
        # a point that is not the point the grid names - and if it wins, the
        # applied config records the value nobody ran.
        for axis, values in _exit_axes(body, _INDICATOR_PERIOD_BOUNDS):
            for value in values:
                _validate_risk_bounds({axis: value}, _INDICATOR_PERIOD_BOUNDS,
                                      label="optimizer grid")
        return {"ok": True, "params": store.save_opt_params(body)}

    @app.post("/api/opt/params/reset")
    def reset_opt_params() -> dict[str, Any]:
        # HTML button is gone; JS is gated on #btn-opt-reset. Store.reset
        # still exists for tests / a future operator restore.
        raise HTTPException(400, "opt izgara varsayilani panelden yazilamaz")

    @app.post("/api/opt/run")
    def opt_run(body: OptRun) -> dict[str, Any]:
        result = optimizer.start(body.symbols, body.apply_best, body.bars,
                                 timeframes=body.timeframes, force=body.force,
                                 strategies=body.strategies)
        if not result.get("ok"):
            raise HTTPException(409, result.get("error", "optimizasyon baslatilamadi"))
        return result

    @app.post("/api/opt/cancel")
    def opt_cancel() -> dict[str, Any]:
        return optimizer.cancel()

    def _refuse_if_bot_open(detail: str) -> None:
        """409 while this process's magics still have tickets.

        Capture must not pin across live fills. Restart/shutdown with opens
        first-sights the trail and killed tonight's search (21:20 / 21:43 /
        ~21:59). A wedged MT5 bind (connected False) skips the check so the
        recovery POST can still run.
        """
        if not client.connected:
            return
        magics = {c.magic for c in list(store.symbols.values())}
        pos = client.positions()
        if not client.connected:
            return
        n = sum(1 for p in pos if p.get("magic") in magics)
        if n:
            raise HTTPException(409, f"acik pozisyon var ({n}) - {detail}")

    @app.post("/api/holdout/capture")
    def holdout_capture() -> dict[str, Any]:
        """Pin holdout bars through the live client. Night restart calls this.

        A second process calling initialize() would drop the trading bind.
        Optimizer busy is a 409: the search already holds the terminal for
        tens of thousands of bars per combo.
        """
        if optimizer.busy:
            raise HTTPException(409, "optimizasyon calisirken holdout capture yok")
        if not client.connected:
            raise HTTPException(409, "MT5 baglantisi yok")
        _refuse_if_bot_open("holdout capture yok")
        if not _holdout_capture_lock.acquire(blocking=False):
            raise HTTPException(409, "holdout capture zaten calisiyor")
        try:
            return capture_book(client=client, store=store)
        finally:
            _holdout_capture_lock.release()

    @app.get("/api/opt/history")
    def opt_history(symbol: str | None = None, limit: int = 60) -> dict[str, Any]:
        return {"ok": True, "history": store.opt_history(symbol, limit)}

    @app.delete("/api/opt/history")
    def opt_history_clear(symbol: str | None = None) -> dict[str, Any]:
        deleted = store.clear_opt_history(symbol)
        LOG.emit(f"Optimizasyon gecmisi temizlendi{f' ({symbol})' if symbol else ''} "
                 f"({deleted} kayit).", "OPT")
        return {"ok": True, "deleted": deleted, "history": store.opt_history(symbol, 80)}

    @app.post("/api/opt/apply")
    def opt_apply(body: OptApply) -> dict[str, Any]:
        params = body.params
        score = body.score
        detail: dict[str, Any] | None = None
        timeframe, strategy = body.timeframe, body.strategy
        gate_axes = {"max_spread_atr", "cost_rank_max", "min_atr_ratio"}
        if body.run_id is not None:
            match = next((r for r in store.opt_history(body.symbol, 40) if r["id"] == body.run_id), None)
            if match is None:
                raise HTTPException(404, "kayit bulunamadi")
            score = float(match.get("score", 0.0))
            detail = match
            if body.gates_only:
                if not body.params:
                    raise HTTPException(400, "gates_only icin params gerekli")
                bad = sorted(k for k in body.params if k not in gate_axes)
                if bad:
                    raise HTTPException(
                        400, f"{', '.join(bad)} gates_only'de yazilamaz - "
                             f"yalnizca {', '.join(sorted(gate_axes))}")
                live_cfg = store.symbols.get(body.symbol)
                params = dict(body.params)
                if "max_spread_atr" in params and live_cfg is not None:
                    cur = float(getattr(live_cfg, "max_spread_atr", 0.0) or 0.0)
                    nxt = float(params["max_spread_atr"])
                    # 0 = gate off (operator). Positive values: widen-only.
                    if nxt > 0 and nxt < cur - 1e-9:
                        raise HTTPException(
                            400, f"max_spread_atr daraltamaz ({cur:g} -> {nxt:g})")
                timeframe, strategy = None, None
            else:
                params = dict(match.get("params") or {})
                timeframe = timeframe or match.get("timeframe")
                strategy = strategy or match.get("strategy")
                if body.params:
                    # Without force: entry-gate retunes only (spread/cost_rank).
                    # With force: any OPT_FIELDS overlay on the stamped run —
                    # measured exit/adx retunes (US30 trail_step 0.8) that WFO
                    # will not beat an optimistic incumbent to land.
                    allow = set(OPT_FIELDS) if body.force else gate_axes
                    bad = sorted(k for k in body.params if k not in allow)
                    if bad:
                        hint = ("OPT_FIELDS (force:true)" if body.force
                                else ", ".join(sorted(gate_axes)))
                        raise HTTPException(
                            400, f"{', '.join(bad)} run_id uzerine yazilamaz - "
                                 f"yalnizca {hint}")
                    params.update(body.params)
        if not params:
            raise HTTPException(400, "parametre yok")
        if detail is None:
            # The results table applies by posting the params themselves rather
            # than the run they came from, so the search's own record of this
            # candidate - holdout, validation, the spread scale it was measured
            # under - was simply dropped on the floor while the parameters went
            # live. The row is still in opt history; match it back rather than
            # let optimizer.apply() void a summary it could have had. Nothing is
            # invented: an exact parameter match, on this symbol, or nothing.
            detail = next(
                (r for r in store.opt_history(body.symbol, 40)
                 if (r.get("params") or {}) == params
                 and (timeframe is None or r.get("timeframe") == timeframe)
                 and (strategy is None or r.get("strategy") == strategy)),
                None)
        # Covers both the hand-typed path (params come straight off the
        # request body) and the run_id path (params come from stored opt
        # history) - the same NaN-string / bad-enum bypass _validate_symbol
        # closes for PATCH /api/symbols/{symbol} exists here too, since
        # optimizer.apply() writes straight into the same SymbolConfig via
        # store.update_symbol(), unvalidated field-by-field.
        _reject_non_finite_values(params)
        _reject_non_finite_values({"score": score})
        enum_check = dict(params)
        if timeframe is not None:
            enum_check["timeframe"] = timeframe
        if strategy is not None:
            enum_check["strategy"] = strategy
        _validate_enum_fields(enum_check)
        # The finite/enum checks above stop garbage, not out-of-range numbers,
        # and OPT_FIELDS carries sl_atr_mult/trail_start_atr/trail_step_atr -
        # the exact three _SYMBOL_RISK_BOUNDS makes strictly positive. Without
        # this line those bounds only guarded PATCH /api/symbols/{symbol}:
        # this endpoint's own hand-typed path (params straight off the request
        # body) wrote them into the same SymbolConfig unchecked, so a
        # trail_start_atr of 0 landed here and switched that symbol's trail
        # off for good - the failure test_trail_breakeven_invariant.py
        # documents as "deliberately unreachable from outside". A negative
        # trail_step_atr put the trail target on the losing side of price, and
        # sl_atr_mult 0 collapsed the hard stop onto the broker's minimum.
        # Applied to the run_id path too: no shipped grid produces a 0 or a
        # negative, so nothing the optimizer can legitimately propose is lost.
        _validate_risk_bounds(params)
        # A run_id pull carries the search's own verdict - refuse to apply a
        # candidate the walk-forward itself rejected unless the caller
        # explicitly overrides. Hand-typed params (no run_id, no detail) are
        # a different, pre-existing use case - unrelated to any optimizer
        # run - and are not gated here.
        if detail is not None and detail.get("validated") is False and not body.force:
            raise HTTPException(
                400, f"bu sonuc dogrulanmadi ({detail.get('keep_reason', '')}) - "
                     f"uygulamak icin force:true gonderin")
        # Snapshot before apply() mutates the live row. Same three keys
        # _finish_symbol writes: a later read of cfg would report the
        # candidate as its own predecessor.
        live = store.symbols.get(body.symbol)
        previous = ({"strategy": live.strategy, "timeframe": live.timeframe}
                    if live is not None else None)
        prev_force = bool(getattr(optimizer, "_force_apply", False))
        if body.force:
            optimizer._force_apply = True
        try:
            result = optimizer.apply(body.symbol, params, float(score), detail,
                                     timeframe, strategy)
        finally:
            optimizer._force_apply = prev_force
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "uygulanamadi"))
        applied_at = time.time()
        run_id = None
        if isinstance(detail, dict) and detail.get("id") is not None:
            try:
                run_id = int(detail["id"])
            except (TypeError, ValueError):
                run_id = None
        stamped = False
        if run_id is not None and hasattr(store, "stamp_opt_run_apply"):
            stamped = bool(store.stamp_opt_run_apply(
                run_id, bool(body.force), previous, applied_at))
        if not stamped and hasattr(store, "record_opt_run"):
            # Hand-typed params, or the matched row was already trimmed.
            # A new row is the only way this door leaves the same trace
            # search-apply does. Search rows with an id were updated above.
            store.record_opt_run(
                body.symbol, float(score),
                {
                    "timeframe": timeframe or (live.timeframe if live is not None else ""),
                    "strategy": strategy or (live.strategy if live is not None else ""),
                    "params": params,
                    "force": bool(body.force),
                    "applied_at": applied_at,
                    "previous": previous,
                },
                applied=True,
            )

        # force stays ALLOWED - it is a deliberate override - but it used to
        # leave no trace: it logged the same success line a fully-validated
        # apply did, so afterwards nothing distinguished "the walk-forward
        # approved this" from "someone overrode the walk-forward". That is the
        # one thing a bypass has to record, since it is the version now
        # trading real money.
        #
        # Only this case is flagged. ``detail is None`` looks like the other
        # bypass ("hand-typed params, never validated") but it is not a usable
        # signal: the panel's own results-table apply also posts params
        # without a run_id, so every ordinary apply from that table would
        # warn. A real hand-typed call is indistinguishable from it here, and
        # a warning that fires on the normal path teaches people to ignore it.
        if detail is not None and detail.get("validated") is False:
            warning = (f"dogrulanmamis sonuc force ile uygulandi "
                       f"({detail.get('keep_reason', 'sebep yok')})")
            LOG.emit(f"OPT parametreleri DOGRULANMADAN uygulandi (force, skor {score:.2f}): "
                     f"{detail.get('keep_reason', 'sebep belirtilmemis')}", "WARN", body.symbol)
            return {**result, "warning": warning}
        LOG.emit(f"OPT parametreleri uygulandi (skor {score:.2f}).", "OPT", body.symbol)
        return result

    # ------------------------------------------------------------------ ai
    # Panel reads STATE.ai from /api/state. No duplicate GET.

    @app.post("/api/ai/settings")
    def ai_settings(body: dict[str, Any]) -> dict[str, Any]:
        _reject_hands_off_fields(body, _OPERATOR_AI_FIELDS)
        _reject_non_finite_values(body)
        _reject_wrong_type_against(body, AI_SETTINGS_DEFAULTS)
        settings = engine.supervisor.update_settings(body)
        LOG.emit("AI denetleyici ayarlari guncellendi.", "AI")
        return {"ok": True, "settings": settings}

    @app.post("/api/ai/review")
    def ai_review() -> dict[str, Any]:
        account = engine.refresh_account(force=True)
        pnl = engine.risk.daily.pnl_pct(float(account.get("equity", 0.0)))
        try:
            result = engine.supervisor.review(pnl)
        except Exception as exc:
            raise HTTPException(500, f"AI denetleyici hatasi: {exc}") from exc
        return {"ok": True, "ai": result}

    @app.post("/api/ai/clear")
    def ai_clear(symbol: str | None = None) -> dict[str, Any]:
        engine.supervisor.clear(symbol)
        return {"ok": True, "ai": engine.supervisor.status()}

    # ---------------------------------------------------------------- logs

    @app.get("/api/logs")
    def logs(after: int = 0, limit: int = 400, levels: str = "") -> dict[str, Any]:
        wanted = [x for x in levels.split(",") if x] or None
        return {"ok": True, "entries": LOG.recent(after, limit, wanted)}

    @app.get("/api/logs/download")
    def logs_download():
        path = LOG.file_path
        if not path.exists():
            raise HTTPException(404, "log dosyasi yok")
        return FileResponse(str(path), filename="micofx.log", media_type="text/plain")

    @app.post("/api/app/shutdown")
    def app_shutdown() -> dict[str, Any]:
        _refuse_if_bot_open("kapatma yok")
        LOG.emit("Kapatma istegi alindi.", "WARN")
        optimizer.cancel()
        engine.shutdown()

        def _kill() -> None:
            time.sleep(0.6)
            client.shutdown()
            os.kill(os.getpid(), signal.SIGTERM)

        threading.Thread(target=_kill, daemon=True).start()
        return {"ok": True, "message": "Uygulama kapaniyor."}

    @app.post("/api/app/restart")
    def app_restart() -> dict[str, Any]:
        # Operator 02.09: restart with open tickets is allowed — MT5 keeps
        # the fills; track()/open_original_sl reattach after bind. Holdout
        # capture and shutdown stay refused while tickets are open.
        if client.connected:
            magics = {c.magic for c in list(store.symbols.values())}
            pos = client.positions()
            if client.connected:
                n = sum(1 for p in pos if p.get("magic") in magics)
                if n:
                    LOG.emit(
                        f"Yeniden baslatma acik {n} ticket ile - MT5 tutuyor, "
                        f"process yeniden baglanacak.",
                        "WARN")
        LOG.emit("Yeniden baslatma istegi alindi.", "WARN")
        # Kill used to skip this: last_opt_job stayed "running" and the OPT
        # cancel line never landed. Persist happens inside cancel() so a
        # 0.3s race to SIGTERM still leaves an honest blob.
        optimizer.cancel()
        engine.shutdown()

        def _restart() -> None:
            time.sleep(0.3)
            try:
                # restart.bat polls until the port is actually free before
                # relaunching, so it must be spawned before this process exits.
                # It used to sleep a flat two seconds while this comment claimed
                # it waited - and a shutdown slower than that left the new
                # instance refused on port_busy, with no retry behind it.
                subprocess.Popen(
                    ["cmd", "/c", str(ROOT / "restart.bat")],
                    cwd=str(ROOT),
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    close_fds=True,
                )
            except Exception as exc:
                LOG.emit(f"Yeniden baslatma tetiklenemedi: {exc}", "ERROR")
            client.shutdown()
            os.kill(os.getpid(), signal.SIGTERM)

        threading.Thread(target=_restart, daemon=True).start()
        return {"ok": True, "message": "Uygulama yeniden baslatiliyor."}

    return app
