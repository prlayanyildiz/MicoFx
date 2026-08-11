from __future__ import annotations

import html as html_escape
import math
import os
import re
import secrets
import signal
import subprocess
import threading
import time
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import APP_NAME, __version__
from ..engine import Engine
from ..logbus import LOG
from ..models import (
    EXIT_PARAM_BOUNDS, EXIT_RISK_FIELDS, GROUPS, STRATEGIES, TIMEFRAMES,
    invalid_exit_param, strategy_allows_timeframe,
)
from ..mt5client import MT5Client
from ..optimizer import Optimizer
from ..paths import ROOT, WEB_DIR
from ..sessions import describe
from ..store import Store
from ..supervisor import DEFAULTS as AI_SETTINGS_DEFAULTS

TEMPLATES = WEB_DIR / "templates"
STATIC = WEB_DIR / "static"


class SymbolPatch(BaseModel):
    model_config = {"extra": "allow"}


class SymbolCreate(BaseModel):
    symbol: str
    group: str = "forex"
    broker_symbol: str = ""
    enabled: bool = True


class BulkPatch(BaseModel):
    symbols: list[str] | None = None
    patch: dict[str, Any] = {}


class SystemPatch(BaseModel):
    model_config = {"extra": "allow"}


class OptRun(BaseModel):
    symbols: list[str] | None = None
    apply_best: bool = True
    bars: int | None = None
    timeframes: list[str] | None = None


class OptApply(BaseModel):
    symbol: str
    run_id: int | None = None
    params: dict[str, Any] | None = None
    score: float = 0.0
    timeframe: str | None = None
    strategy: str | None = None
    force: bool = False


class StopBody(BaseModel):
    close: bool | None = None


# Sanity bounds on the fields that directly control position size/risk.
# ``SymbolPatch``/``SystemPatch`` allow arbitrary keys through (needed for the
# many optimizer-only fields), so nothing before this stopped a client from
# pushing e.g. risk_percent=500 straight to the API with zero pushback - the
# UI's own number-input min/max never protected anything but the UI.
_SYMBOL_RISK_BOUNDS = {
    "risk_percent": (0.0, 20.0, False),   # (min, max, min_inclusive) - % of balance per trade
    "max_lot": (0.0, 20.0, False),
    "fixed_lot": (0.0, 20.0, False),
    "max_positions": (1, 50, True),
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
}

_SYSTEM_RISK_BOUNDS = {
    "lot_multiplier": (0.0, 50.0, False),
    "max_margin_usage_pct": (0.0, 100.0, True),   # 0 = uncapped (falls back to free margin), valid
    "daily_loss_pct": (0.0, 100.0, True),   # 0 = disabled, valid
    "daily_profit_pct": (0.0, 100.0, True),  # 0 = disabled, valid
    "max_total_positions": (1, 200, True),
}


def _validate_risk_bounds(patch: dict[str, Any], bounds: dict[str, tuple] = _SYMBOL_RISK_BOUNDS,
                          label: str = "") -> None:
    """``label`` names the enclosing blob when checking a nested dict, so the
    400 says which copy of the field was bad - ``secondary_params`` carries
    its own sl_atr_mult/trail_start_atr/trail_step_atr and the message is
    otherwise identical to the top-level one.
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


def _exit_axes(body: dict[str, Any]):
    """Yield (axis_name, values) for every exit-model axis in an opt-params body.

    The search grid comes in two shapes: a flat shared ``grid`` of
    {param: [values]}, and ``strategy_grids`` of {strategy: {param: [values]}}
    that overrides it per family. Both can carry the exit axes, so both are
    walked - checking only the flat one would leave the per-strategy override
    as an open door to the same value.
    """
    def _axes(container: Any):
        if not isinstance(container, dict):
            return
        for axis, values in container.items():
            if axis in EXIT_PARAM_BOUNDS and isinstance(values, (list, tuple)):
                yield axis, values

    yield from _axes(body.get("grid"))
    per_strategy = body.get("strategy_grids")
    if isinstance(per_strategy, dict):
        for sub in per_strategy.values():
            yield from _axes(sub)


# Engine-internal bookkeeping: Optimizer.apply()/_apply_secondary_locked()
# write these to defer exit/risk fields until a position is flat (see
# Engine._apply_pending_exits). They carry no schema of their own, so a
# client PATCHing this field directly could stage ANY symbol field - not
# just exit/risk ones - to land later, bypassing every guard above. Never a
# legitimate thing for a human or external API caller to set.
#
# _apply_pending_exits does now re-check the exit bounds at the moment a
# pending patch lands, so that specific class no longer rides through. That
# is a backstop for stored state (a patch predating the check, a restored
# backup, a hand-edited row), not a reason to open this door: it covers the
# three exit numbers only, and every other field staged here would still
# land without ever meeting the validation on this endpoint.
_INTERNAL_ONLY_FIELDS = ("pending_exit_patch", "pending_secondary_exit_patch")


def _reject_bad_dict_fields(patch: dict[str, Any], keys: tuple) -> None:
    # SymbolConfig.from_dict() silently coerces a non-dict value for these
    # fields to {} (see models.py) - a client sending a string/list/number
    # instead of an object wiped the field to empty with a 200, completely
    # bypassing the exit-field-changing guards above, which only look at the
    # patch when it IS a dict.
    for key in keys:
        if key in patch and patch[key] is not None and not isinstance(patch[key], dict):
            raise HTTPException(400, f"{key} bir nesne (object) olmali, {type(patch[key]).__name__} degil")


# strategy_allows_timeframe() falls back to "allow every timeframe" for a
# strategy name it does not recognise (see its own docstring) - it was never
# meant to double as an enum check, so an arbitrary/garbage strategy string
# sailed straight through the primary_changing guard. group had no check at
# all. Both land verbatim in the frontend as CSS classes / innerHTML
# fragments (Semboller cards, pill badges), so a bogus value here is not
# just a data-integrity problem - it is another XSS entry point.
_ENUM_FIELDS = {"group": (GROUPS, False), "strategy": (STRATEGIES, False),
                "secondary_strategy": (STRATEGIES, True),
                "timeframe": (TIMEFRAMES, False), "secondary_timeframe": (TIMEFRAMES, True),
                "lot_mode": (("fixed", "risk"), False),
                "trail_mode": (("atr", "structure", "hybrid"), False)}


_NON_FINITE_TOKENS = {"nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}


def _reject_non_finite_values(d: dict[str, Any], label: str = "") -> None:
    # Both the top-level patch and the nested secondary_params blob carry
    # plenty of numeric fields (sl_atr_mult, trail_start_atr, adx_min, ...)
    # with no per-field bounds table of their own (unlike the small, named
    # _SYMBOL_RISK_BOUNDS set _validate_risk_bounds checks) - this closes the
    # NaN/Infinity class of bug for all of them, since a NaN reaching
    # engine.py's live trailing/breakeven math corrupts comparisons silently
    # (NaN >= x and NaN <= x are both always False). The raw-float case
    # (json={"x": float("nan")}) never even reaches here in practice -
    # httpx's own encoder refuses to serialise it - but the JSON STRING
    # "NaN"/"Infinity" serialises just fine, and models.py's _coerce() does
    # ``float(value)`` on it for any float-typed field, which happily turns
    # the string right back into a real NaN. Checking only isinstance(...,
    # (int, float)) missed exactly that path.
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


def create_app(store: Store, client: MT5Client, engine: Engine, optimizer: Optimizer,
                api_token: str = "") -> FastAPI:
    """``api_token``: optional shared secret (``MICO_API_TOKEN`` env var, see run.py).

    Empty (the default) means no auth at all - fine for the default 127.0.0.1
    bind, which nothing outside this machine can reach anyway. It exists for
    the one case that default doesn't cover: ``MICO_HOST=0.0.0.0``, where
    every /api/* route (panic, bot start/stop, close-all, symbol edits, MT5
    path) would otherwise be reachable - and controllable - by anyone who can
    reach the port, no login of any kind. Set once it is not just localhost.
    """
    app = FastAPI(title=f"{APP_NAME} Terminal", version=__version__, docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

    if api_token:
        # ``?token=`` is only ever needed where a plain browser navigation
        # can't set a custom header: the bootstrap "/" load, and the
        # <a href> log download link. Every other /api/* route goes through
        # app.js's fetch-based api() helper, which already sets the
        # X-Mico-Token header - letting those also accept a query param
        # would just widen where the token can end up (proxy/access logs,
        # browser history, a Referer header on an outbound request) for no
        # actual usability gain.
        _QUERY_TOKEN_PATHS = {"/", "/api/logs/download"}

        @app.middleware("http")
        async def _require_api_token(request, call_next):
            path = request.url.path
            # ``/`` used to be deliberately left out of this gate on the theory
            # that embedding the token in its (unauthenticated) HTML was safe
            # because "whoever can already fetch this HTML... is exactly who
            # the token is meant to let in" - but on a non-localhost bind
            # ANYONE can fetch "/" with no credentials at all, so that meta
            # tag handed the token to precisely the population it exists to
            # keep out. Gating "/" too is what actually makes that comment true.
            if path.startswith("/api/") or path == "/":
                token = request.headers.get("x-mico-token")
                if not token and path in _QUERY_TOKEN_PATHS:
                    token = request.query_params.get("token")
                # L3: plain `!=` on the token leaks a timing side-channel
                # (early-exit on the first mismatched byte) - irrelevant on
                # the default 127.0.0.1 bind but this whole gate only exists
                # for MICO_HOST=0.0.0.0, where a remote attacker can time it.
                # compare_digest needs two strings; the `not token` guard
                # keeps the missing-header/query-param (None) case from ever
                # reaching it.
                if not token or not secrets.compare_digest(token, api_token):
                    if path == "/":
                        return PlainTextResponse(
                            "MicoFX: token gerekli - ?token=<MICO_API_TOKEN> ile acin.",
                            status_code=401)
                    return JSONResponse({"detail": "gecersiz veya eksik API token"}, status_code=401)
            return await call_next(request)

    _symbol_payload_cache: dict[str, Any] = {"at": 0.0, "rows": []}

    def symbol_payload(force: bool = False) -> list[dict[str, Any]]:
        # /api/state is polled often; reuse a short snapshot so MT5 is not hammered.
        now = time.time()
        if (not force and _symbol_payload_cache["rows"]
                and now - float(_symbol_payload_cache["at"]) < 1.5):
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
        if api_token:
            # Reaching this handler at all means the token middleware above
            # already accepted a matching x-mico-token header or ?token=
            # query param for this exact request - static assets stay
            # unauthenticated (just JS/CSS, no data), but the page itself
            # does not anymore. Embedding the token back into the HTML here
            # is genuinely trusted-origin at this point: whoever is loading
            # this page already had the token to get this far.
            html = html.replace(
                "<head>",
                f'<head>\n<meta name="mico-api-token" content="{html_escape.escape(api_token)}">',
                1)
        return HTMLResponse(html)

    @app.get("/favicon.ico")
    def favicon() -> PlainTextResponse:
        return PlainTextResponse("", status_code=204)

    # --------------------------------------------------------------- state

    @app.get("/api/state")
    def state() -> dict[str, Any]:
        return {
            "ok": True,
            "ts": time.time(),
            "version": __version__,
            **engine.snapshot(),
            "symbols": symbol_payload(),
            "system": store.system.to_dict(),
            "opt": optimizer.status(),
        }

    @app.get("/api/symbols")
    def get_symbols() -> dict[str, Any]:
        return {"ok": True, "symbols": symbol_payload()}

    @app.get("/api/symbols/broker-audit")
    def broker_audit() -> dict[str, Any]:
        """Compare stored min-lot / Friday-close config against live broker data.

        ``friday_close`` is the broker's own last Friday session end (minutes
        since midnight, broker clock); ``configured_close`` is this symbol's
        widest configured session end on Friday (or None if it trades
        ``trade_all_hours``/has no session windows at all).
        """
        rows: list[dict[str, Any]] = []
        for cfg in list(store.symbols.values()):
            if not cfg.enabled:
                continue
            info = client.info(cfg.symbol)
            floor = float(info["volume_min"]) if info else None
            broker_close = client.last_session_close_minute(cfg.symbol, 5)  # Friday
            windows = cfg.session_windows() if cfg.use_sessions else []
            configured_close = max((end for _, end in windows), default=None)
            lot_mismatch = (
                cfg.lot_mode == "fixed" and floor is not None
                and float(cfg.fixed_lot) < floor
            )
            close_mismatch = (
                broker_close is not None and configured_close is not None
                and abs(broker_close - configured_close) > 30
            )
            # "Could not check" is its own answer. close_mismatch is False both
            # when the times agree and when the broker's schedule could not be
            # read at all - and the Python package exposes no schedule, so the
            # second case is the only one that ever happens. Reporting that as
            # a clean result made this audit certify all twenty symbols as
            # aligned while looking at nothing.
            if configured_close is None:
                close_check = "session-yok"
            elif broker_close is None:
                close_check = "okunamadi"
            elif close_mismatch:
                close_check = "kayik"
            else:
                close_check = "uyumlu"
            rows.append({
                "symbol": cfg.symbol, "lot_mode": cfg.lot_mode,
                "fixed_lot": cfg.fixed_lot, "broker_min_lot": floor,
                "lot_mismatch": lot_mismatch,
                "configured_friday_close_min": configured_close,
                "broker_friday_close_min": broker_close,
                "close_mismatch": close_mismatch,
                "close_check": close_check,
            })
        # What is actually measurable about the broker's clock today. Session
        # windows are configured against the Windows clock (Turkey, UTC+3 all
        # year); the broker's server follows European DST and drops an hour at
        # the end of October, which is when every window quietly stops matching
        # the instrument's real session.
        broker_utc = client.broker_utc_offset_hours(
            [c.symbol for c in list(store.symbols.values()) if c.enabled])
        # Turkey has no DST, so this is +3 year round; taken from the machine
        # rather than hardcoded so a move or a changed Windows zone shows up.
        local_utc = -(time.altzone if time.daylight and time.localtime().tm_isdst
                      else time.timezone) // 3600
        drift = None if broker_utc is None else broker_utc - local_utc
        return {
            "ok": True, "rows": rows,
            "broker_utc_offset_hours": broker_utc,
            "local_utc_offset_hours": local_utc,
            "clock_drift_hours": drift,
            "clock_note": (
                "olculemedi - yeterli canli tick yok"
                if drift is None else
                f"broker GMT{broker_utc:+d}, yerel GMT{local_utc:+d} - ayni, "
                f"seans pencereleri enstrumanin gercek seansiyla hizali"
                if drift == 0 else
                f"broker GMT{broker_utc:+d}, yerel GMT{local_utc:+d} - "
                f"{drift:+d} saat KAYMA. Seans pencereleri yerel saate gore "
                f"yazildi, enstrumanin gercek seansi {drift:+d} saat kaydi - "
                f"pencereleri buna gore guncelleyin"
            ),
        }

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

    def _open_tagged_secondary(magic: int) -> list[dict[str, Any]]:
        tagged = {int(t) for t in (store.get_setting("secondary_tickets", []) or [])}
        if not tagged:
            return []
        return [p for p in _positions(magic=magic) if p["ticket"] in tagged]

    def _pending_orphan_scan(magic: int, symbol: str) -> bool:
        """True while engine.py (H1) is still watching this symbol/magic for
        a secondary fill whose ticket was never identified - genuinely
        invisible to client.positions() (that is the entire reason the scan
        exists), so nothing that only checks live positions can see this risk
        on its own. Blocks regardless of whether engine.py has marked it
        "abandoned" - abandoned only means it stopped actively re-diffing
        every cycle (H2), not that the position is confirmed gone. A magic
        this stale/reused ID would otherwise collide with (DELETE, seed
        overwrite, next_magic reassigning it to a brand new symbol) is the
        exact same risk class as touching identity/exit under it directly.
        """
        scan = store.get_setting("secondary_orphan_scan", {}) or {}
        return symbol in scan and int(scan[symbol].get("magic", -1)) == magic

    def _secondary_risk(magic: int, symbol: str) -> tuple[list[dict[str, Any]], bool]:
        """Everything that counts as "cannot safely touch secondary identity/
        exit right now" - live-tagged secondary tickets, PLUS the same
        untracked-fill risk optimizer.apply_secondary() already guards for
        (see engine.py's H1 orphan tracking): a closed-but-still-unresolved
        orphan ticket, or a still-open orphan-scan window where the fill's
        ticket was never even identified.
        """
        tagged = {int(t) for t in (store.get_setting("secondary_tickets", []) or [])}
        orphan_tickets = {int(t) for t in (store.get_setting("secondary_orphan_tickets", []) or [])}
        watch = tagged | orphan_tickets
        live = [p for p in _positions(magic=magic) if p["ticket"] in watch] if watch else []
        return live, _pending_orphan_scan(magic, symbol)

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
                    return (f"magic {new_magic} tanimlanamayan ikincil ticket taramasinda "
                            f"({sym}) - tarama bitmeden atanamaz")
        if int(new_magic) in _orphan_ticket_magics():
            return (f"magic {new_magic} hala acik orphan ticket uzerinde - "
                    f"once kapanmasini bekleyin")
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
                     "ikincil ticket listesi dolu (magic cakisma riski) - MT5'e "
                     "baglanin veya orphan ticket listesinin temizlenmesini bekleyin")

    @app.post("/api/symbols/{symbol}")
    def patch_symbol(symbol: str, body: SymbolPatch) -> dict[str, Any]:
        patch = body.model_dump()
        _reject_internal_fields(patch)
        _reject_bad_dict_fields(patch, ("secondary_params",))
        # _validate_risk_bounds only range-checks the small named set in
        # _SYMBOL_RISK_BOUNDS - sl_atr_mult, trail_start_atr, adx_min and
        # every other numeric field outside that set had no NaN/Infinity
        # check at all, top-level, same class of gap the nested
        # secondary_params check below closes for the secondary blob.
        _reject_non_finite_values(patch)
        if isinstance(patch.get("secondary_params"), dict):
            _reject_non_finite_values(patch["secondary_params"], "secondary_params")
            # trail_mode is the one OPT_FIELD enum value the search can also
            # write here - top-level _validate_enum_fields below never looks
            # inside this nested dict, so a garbage trail_mode landed straight
            # in cfg.secondary_params unchecked.
            _validate_enum_fields(patch["secondary_params"], "secondary_params")
            # Third check the nested blob needs in its own right, for the same
            # reason as the two above: _validate_risk_bounds below only ever
            # looked at top-level keys, and secondary_params carries its own
            # sl_atr_mult/trail_start_atr/trail_step_atr - engine.py builds the
            # secondary signal's exit payload straight from this dict. So the
            # 0/negative/absurd values refused at the top level landed here
            # unchecked and drove the secondary position's real stop.
            _validate_risk_bounds(patch["secondary_params"], label="secondary_params")
        _validate_enum_fields(patch)
        _validate_risk_bounds(patch)
        _validate_sessions(patch)
        current = store.symbols.get(symbol)
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
        next_sec_strat = (patch.get("secondary_strategy", current.secondary_strategy)
                          if current is not None else None)
        next_sec_tf = (patch.get("secondary_timeframe", current.secondary_timeframe)
                       if current is not None else None)
        secondary_changing = (current is not None and (
            ("secondary_strategy" in patch and next_sec_strat != current.secondary_strategy)
            or ("secondary_timeframe" in patch and next_sec_tf != current.secondary_timeframe)
        ))
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
        # secondary_params is a nested blob, not individual top-level fields -
        # the check above only ever looked at top-level keys, so patching
        # {"secondary_params": {"trail_step_atr": ...}} directly bypassed the
        # guard entirely even though engine.py's _secondary_config() overlays
        # this same dict onto live position management every cycle, exactly
        # like the top-level fields do for the primary.
        next_sec_params = patch.get("secondary_params")
        # secondary_params is written as a full replacement, not a merge - a
        # new dict that simply OMITS a previously-set exit key (most
        # obviously {} to wipe it, but any dict missing e.g. trail_step_atr)
        # silently drops that key too, and _secondary_config() then falls
        # back to the PRIMARY's value for it. Only diffing keys present in
        # the new dict missed exactly this "changed by omission" case -
        # compare the union of both dicts' keys instead.
        secondary_exit_changing = (
            current is not None and isinstance(next_sec_params, dict)
            and any(next_sec_params.get(k) != current.secondary_params.get(k)
                    for k in (set(next_sec_params) | set(current.secondary_params)) & EXIT_RISK_FIELDS)
        )
        guarded = (magic_changing or primary_changing or secondary_changing
                  or exit_fields_changing or secondary_exit_changing)
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
                    # pending orphan-scan sits on this magic (M1, prior round)
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
                if secondary_changing:
                    live_tagged, pending_scan = _secondary_risk(current.magic, symbol)
                    if live_tagged or pending_scan:
                        note = " (+ tanimlanamayan ticket taramasi devam ediyor)" if pending_scan else ""
                        raise HTTPException(
                            409, f"{symbol}: ikincil strateji degistirilemedi, "
                                 f"{len(live_tagged)} acik ikincil-sinyal pozisyonu var{note} "
                                 f"(once kapanmasini bekleyin)")
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
                if secondary_exit_changing and not secondary_changing:
                    live_tagged, pending_scan = _secondary_risk(current.magic, symbol)
                    if live_tagged or pending_scan:
                        changed_fields = sorted(
                            k for k in (set(next_sec_params) | set(current.secondary_params)) & EXIT_RISK_FIELDS
                            if next_sec_params.get(k) != current.secondary_params.get(k))
                        note = " (+ tanimlanamayan ticket taramasi devam ediyor)" if pending_scan else ""
                        raise HTTPException(
                            409, f"{symbol}: ikincil cikis/risk parametreleri "
                                 f"({', '.join(changed_fields)}) degistirilemedi, "
                                 f"{len(live_tagged)} acik ikincil-sinyal pozisyonu var{note} "
                                 f"(once kapanmasini bekleyin)")
            if primary_changing:
                tf_allow = store.opt_params().get("strategy_timeframes")
                allow = tf_allow if isinstance(tf_allow, dict) else None
                if not strategy_allows_timeframe(next_strat, next_tf, allow):
                    raise HTTPException(
                        400, f"{next_strat}/{next_tf} eslesmesi yasak "
                             f"(scalp yalnizca M5; uzun TF swing ailelerine ait) - "
                             f"motor bu kombinasyonda hicbir zaman giris denemez")
            updated = store.update_symbol(symbol, patch)
        finally:
            if guarded:
                engine.entry_lock.release()
        if updated is None:
            raise HTTPException(404, f"{symbol} bulunamadi")
        client.set_overrides({c.symbol: c.broker_symbol for c in list(store.symbols.values())})
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
                avoid_magics=_orphan_ticket_magics(),
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        client.set_overrides({c.symbol: c.broker_symbol for c in list(store.symbols.values())})
        return {"ok": True, "config": cfg.to_dict(), "symbols": symbol_payload(force=True),
                "system": store.system.to_dict()}

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
                    409, f"{symbol} silinemedi: tanimlanamayan bir ikincil ticket taramasi "
                         f"devam ediyor (magic {cfg.magic}) - taramanin bitmesini bekleyin")
            store.delete_symbol(symbol)
        engine.states.pop(symbol, None)
        engine.supervisor.clear(symbol)
        engine.execution.drop_symbol(symbol)
        engine._sec_cfgs.pop(symbol, None)
        LOG.emit(f"{symbol} portfoyden silindi.", "WARN", symbol)
        client.set_overrides({c.symbol: c.broker_symbol for c in list(store.symbols.values())})
        return {"ok": True, "symbols": symbol_payload(force=True), "system": store.system.to_dict()}

    @app.get("/api/analysis/breakeven")
    def breakeven_margin() -> dict[str, Any]:
        """How far each symbol's validated win rate sits above its own breakeven.

        The apply gates read profit factor, expectancy, retention and cost
        separately; none of them answers "how much room is there before this
        config stops paying". That distance is what a small execution
        degradation eats, and it is not visible in any single number they do
        check - US30 clears every gate on PF 1.12 while sitting 2.4 points
        above the line.

        Derived from the untouched holdout only, no assumptions bolted on.
        The average win W matters here and is easy to get wrong: this exit
        model has no take-profit, so winners run and W is nothing like 1R -
        USDJPY's is 3.6R against a 26.5% win rate. Assuming 1R puts its
        breakeven at 58% instead of 24% and inverts the verdict.

            PF = (w * W) / ((1 - w) * L)          ->  W/L
            E  = w * W - (1 - w) * L              ->  scale
            breakeven win rate = L / (W + L)
        """
        rows: list[dict[str, Any]] = []
        for cfg in list(store.symbols.values()):
            if not cfg.enabled:
                continue
            hold = (cfg.opt_summary or {}).get("holdout") or {}
            wr = float(hold.get("win_rate", 0.0) or 0.0)
            pf = float(hold.get("profit_factor", 0.0) or 0.0)
            exp = float(hold.get("expectancy", 0.0) or 0.0)
            if wr <= 0 or wr >= 100 or pf <= 0:
                continue
            w = wr / 100.0
            ratio = pf * (1 - w) / w                 # W / L
            denom = w * ratio - (1 - w)
            if denom == 0:
                continue
            loss = exp / denom                       # average loss, in R
            win = ratio * loss
            if win + loss <= 0:
                continue
            breakeven = loss / (win + loss) * 100.0
            rows.append({
                "symbol": cfg.symbol,
                "win_rate": round(wr, 1),
                "profit_factor": round(pf, 2),
                "avg_win_r": round(win, 2),
                "avg_loss_r": round(loss, 2),
                "breakeven_win_rate": round(breakeven, 1),
                "margin_pp": round(wr - breakeven, 1),
                "trades": hold.get("trades"),
            })
        rows.sort(key=lambda r: r["margin_pp"])
        thin = [r["symbol"] for r in rows if r["margin_pp"] < 4.0]
        return {
            "ok": True, "rows": rows, "thin": thin,
            "note": (
                f"{len(thin)} sembol 4 puandan az marjla calisiyor: "
                f"{', '.join(thin)} - kucuk bir icra bozulmasi bunlari negatife cevirir"
                if thin else "her sembol 4 puandan genis marjla calisiyor"
            ),
        }

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
            cost_per_trade_r against the optimizer's own accept ceiling. This
            is deliberately NOT the cost-by-hour median: that view averages
            every bar while the walk-forward only charges cost where a signal
            fired, so it runs 5-14x higher on short timeframes. Comparing its
            level to a gate has already produced wrong calls on which symbols
            are worth trading.

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
        ceiling_r = float(getattr(optimizer, "MAX_COST_PER_TRADE_R", 0.25) or 0.25)
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
            cost_r = float(hold.get("cost_per_trade_r") or 0.0)

            state = engine.states.get(cfg.symbol)
            spread_atr = float(getattr(state, "spread_atr", 0.0) or 0.0) if state else 0.0
            # The ensemble's second leg carries its own max_spread_atr, and it
            # is routinely the TIGHTER of the two - six of thirteen live
            # symbols, up to 3.6x on EURJPY (primary 0.18, secondary 0.05).
            # _try_entry gates whichever leg produced the signal, so reading
            # only the primary reported EURJPY as clear at 0.074/0.18 while
            # its secondary sell was being refused on every poll. Judge
            # against the binding ceiling, and name which leg owns it.
            ceiling = float(cfg.max_spread_atr or 0.0)
            ceiling_leg = "primary"
            if cfg.has_secondary():
                sec_ceiling = (cfg.secondary_params or {}).get("max_spread_atr")
                try:
                    sec_ceiling = float(sec_ceiling) if sec_ceiling is not None else 0.0
                except (TypeError, ValueError):
                    sec_ceiling = 0.0
                if sec_ceiling > 0 and (ceiling <= 0 or sec_ceiling < ceiling):
                    ceiling, ceiling_leg = sec_ceiling, "secondary"

            hold_days = float(summary.get("holdout_days") or 0.0)
            expected = (n / hold_days * window_days) if (n and hold_days > 0) else None
            actual = int((live.get(cfg.symbol) or {}).get("trades") or 0)
            fill = (actual / expected) if expected else None

            fails: list[str] = []
            if se2 is None or abs(edge) <= se2:
                fails.append("olculebilir")
            if cost_r > ceiling_r:
                fails.append("maliyet")
            # A ceiling of 0 disables the filter entirely; only judge a live
            # reading against a ceiling that is actually switched on.
            if ceiling > 0 and spread_atr > 0 and spread_atr > ceiling:
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
                "cost_ceiling_r": ceiling_r,
                "spread_atr_now": round(spread_atr, 4) if spread_atr else None,
                "max_spread_atr": ceiling or None,
                "ceiling_leg": ceiling_leg,
                "primary_max_spread_atr": float(cfg.max_spread_atr or 0.0) or None,
                "expected_trades": round(expected, 1) if expected else None,
                "actual_trades": actual,
                "fill_rate": round(fill, 3) if fill is not None else None,
                "fails": fails,
                "clean": not fails,
            })

        rows.sort(key=lambda r: (-len(r["fails"]), r["symbol"]))
        by_gate = {g: [r["symbol"] for r in rows if g in r["fails"]]
                   for g in ("olculebilir", "maliyet", "tavan", "siklik")}
        thin = [r["symbol"] for r in rows if r["thin_sample"]]
        return {
            "ok": True, "rows": rows, "by_gate": by_gate,
            "window_days": window_days, "min_sample": sample_floor,
            "min_fill_rate": fill_floor,
            "thin_sample": thin,
            "note": (
                f"{sum(1 for r in rows if r['clean'])}/{len(rows)} sembol dort kapiyi da geciyor. "
                f"Orneklemi {sample_floor} altinda kalan: {', '.join(thin) if thin else 'yok'} - "
                f"bu sembollerde 'olculebilir' bayragi tek basina okunmamali."
            ),
        }

    @app.get("/api/analysis/correlation")
    def correlation(timeframe: str = "H1", bars: int = 1500) -> dict[str, Any]:
        """Return correlation between every pair of live symbols. Read-only.

        The portfolio is 8 equity indices out of 13, and whether that is a
        concentration problem or merely a long list has been argued both ways
        without either side measuring it. Stops cap what any ONE trade loses;
        they do nothing about several positions losing at the same time,
        because each one stops out independently at full risk. So the question
        that matters is not how many indices there are, it is how much they
        move together - and that is a number, not an opinion.

        Computed on log returns of the closing series, which is the right
        input: raw prices trend and would report almost everything as
        correlated. Pairs are aligned on their own bar count rather than by
        timestamp; symbols quoting different session lengths therefore compare
        over their shared tail, which is why the count is returned per pair.
        """
        _require_connected()
        tf = timeframe if timeframe in TIMEFRAMES else "H1"
        count = max(200, min(int(bars), 20000))

        series: dict[str, Any] = {}
        skipped: dict[str, str] = {}
        for cfg in list(store.symbols.values()):
            if not cfg.enabled:
                continue
            data = client.bars(cfg.symbol, tf, count)
            if data is None or len(data) < 60:
                skipped[cfg.symbol] = f"yeterli bar yok ({len(data) if data else 0})"
                continue
            close = np.asarray(data.close, dtype=np.float64)
            with np.errstate(divide="ignore", invalid="ignore"):
                rets = np.diff(np.log(np.where(close > 0, close, np.nan)))
            series[cfg.symbol] = rets[np.isfinite(rets)]

        names = sorted(series)
        pairs: list[dict[str, Any]] = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                x, y = series[a], series[b]
                n = min(x.size, y.size)
                if n < 60:
                    continue
                xa, yb = x[-n:], y[-n:]
                if xa.std() <= 0 or yb.std() <= 0:
                    continue
                r = float(np.corrcoef(xa, yb)[0, 1])
                if not math.isfinite(r):
                    continue
                pairs.append({"a": a, "b": b, "r": round(r, 3), "bars": int(n)})
        pairs.sort(key=lambda p: -abs(p["r"]))

        groups = {c.symbol: c.group for c in list(store.symbols.values())}
        same, cross = [], []
        for p in pairs:
            (same if groups.get(p["a"]) == groups.get(p["b"]) else cross).append(p["r"])
        high = [p for p in pairs if abs(p["r"]) >= 0.7]
        return {
            "ok": True, "timeframe": tf, "symbols": names, "pairs": pairs,
            "skipped": skipped,
            "median_same_group": round(float(np.median(same)), 3) if same else None,
            "median_cross_group": round(float(np.median(cross)), 3) if cross else None,
            "high_pairs": high,
            "note": (
                f"{len(high)} cift 0.70 ve uzeri birlikte hareket ediyor"
                + (f" (grup ici medyan {round(float(np.median(same)), 2)}, "
                   f"gruplar arasi {round(float(np.median(cross)), 2)})" if same and cross else "")
                if pairs else "yeterli veri yok"
            ),
        }

    @app.get("/api/analysis/entry-blocks")
    def entry_blocks() -> dict[str, Any]:
        """Which gate refuses entries, counted per symbol. Read-only.

        The portfolio-gates view says every symbol trades far under the
        frequency its holdout implies; this says why. Counted only where a
        signal actually reached the entry stage, so the totals separate the
        two causes that look identical from outside - a gate refusing the
        trade, versus the signal never firing in the first place.

        ``attempts`` is signals that reached _try_entry, not bars. Compare it
        against the holdout's implied trade count: if attempts match and
        ``opened`` does not, a gate is eating them and ``blocks`` names it. If
        attempts themselves are short, the entry gates are innocent and the
        shortfall is upstream, in signal generation.
        """
        data = engine.entry_blocks()
        total = data["attempts"]
        top = next(iter(data["totals"].items()), None)
        data["note"] = (
            "Henuz giris denemesi kaydedilmedi - sayac bu surumle basladi, "
            "bir sinyal gelene kadar bos kalir."
            if not total else
            f"{data['opened']}/{total} deneme islemle sonuclandi"
            + (f"; en cok engelleyen: {top[0]} ({top[1]})" if top else "")
        )
        return {"ok": True, **data}

    @app.post("/api/analysis/entry-blocks/reset")
    def entry_blocks_reset() -> dict[str, Any]:
        engine.reset_entry_blocks()
        return {"ok": True, "message": "Giris engeli sayaclari sifirlandi."}

    @app.post("/api/symbols/{symbol}/reset")
    def reset_symbol(symbol: str) -> dict[str, Any]:
        cfg = store.symbols.get(symbol)
        if cfg is None and not any(
                e.get("symbol") == symbol for e in store.defaults.get("symbols", [])):
            raise HTTPException(404, f"{symbol} icin varsayilan yok")
        # Preset reset rewrites strategy/TF/exits (and clears secondary). Same
        # orphan class as a family PATCH under an open ticket - refuse while
        # anything is still live under this magic.
        if cfg is not None:
            _require_connected()
            with engine.entry_lock:
                open_here = _open_under_magic(cfg.magic)
                if open_here:
                    raise HTTPException(
                        409, f"{symbol}: varsayilana donulemedi, {len(open_here)} acik pozisyon var "
                             f"(once kapatin veya pozisyon kapanmasini bekleyin)")
                if _pending_orphan_scan(cfg.magic, symbol):
                    raise HTTPException(
                        409, f"{symbol}: varsayilana donulemedi, tanimlanamayan bir ikincil "
                             f"ticket taramasi devam ediyor - taramanin bitmesini bekleyin")
                updated = store.reset_symbol_to_preset(symbol)
        else:
            # cfg is None: this symbol was deleted and is being recreated from
            # its preset - a fresh magic is assigned (see Store.next_magic),
            # so the same reuse risk as create_symbol() applies.
            _reject_magic_assignment_if_disconnected_orphans()
            updated = store.reset_symbol_to_preset(
                symbol, avoid_magics=_orphan_ticket_magics())
        if updated is None:
            raise HTTPException(404, f"{symbol} icin varsayilan yok")
        LOG.emit("Ayarlar varsayilana dondu.", "INFO", symbol)
        return {"ok": True, "config": updated.to_dict()}

    @app.get("/api/symbols/lot-mode-check")
    def lot_mode_check() -> dict[str, Any]:
        account = engine.refresh_account(force=True)
        rows = engine.risk.lot_mode_diagnostics(float(account.get("balance", 0.0)))
        return {"ok": True, "rows": rows}

    @app.get("/api/analysis/cost-by-hour")
    def cost_by_hour(symbol: str, timeframe: str = "", bars: int = 5000) -> dict[str, Any]:
        """Cost as a fraction of the ATR stop distance, bucketed by hour of day.

        Read-only. Answers one question the apply gates cannot: the cost share
        that decides whether a config is worth trading is an average over the
        whole day, and it hides the fact that spread and ATR do not move
        together. If a window exists where ATR expands faster than spread, cost
        per unit of risk collapses there - which is the only way a fast config
        can stop giving most of its edge away.

        Same arithmetic ``simulate`` charges: spread from the bar itself, plus
        commission converted to price, over ``atr * sl_atr_mult``.

        NOT comparable to ``opt_summary.holdout.cost_per_trade_r``, and the
        difference is not a rounding one - on M5/M10 configs this figure runs
        5-14x the walk-forward's. Same arithmetic, different population: this
        averages EVERY bar, while the walk-forward only ever charges cost on
        bars where a signal actually fired. Signals fire on movement, so entry
        bars carry a systematically higher ATR than the median bar, and a
        higher ATR is a bigger denominator. On H1 the two land within 10% of
        each other because a long bar's ATR is large either way; the shorter
        the timeframe, the further they diverge.

        So read this for the SHAPE across hours - where in the day cost per
        unit of risk collapses or spikes, which is what no other view answers -
        and read cost_per_trade_r for the LEVEL a config actually pays.
        Comparing the two levels directly has produced wrong calls on which
        symbols are worth trading; the hourly shape has not.
        """
        cfg = store.symbols.get(symbol)
        if cfg is None:
            raise HTTPException(404, f"{symbol} bulunamadi")
        _require_connected()
        tf = timeframe if timeframe in TIMEFRAMES else cfg.timeframe
        count = max(200, min(int(bars), 50000))
        data = client.bars(cfg.symbol, tf, count)
        if data is None or len(data) < cfg.atr_period + 10:
            raise HTTPException(503, f"{symbol}/{tf}: yeterli bar alinamadi")
        info = client.info(cfg.symbol) or {}
        point = float(info.get("point", 0.0) or 0.0)
        if point <= 0:
            raise HTTPException(503, f"{symbol}: point degeri okunamadi")

        from .. import backtest, indicators as ind
        commission = backtest.commission_in_price(
            cfg.commission_per_lot,
            float(info.get("tick_value", 0.0) or 0.0),
            float(info.get("tick_size", 0.0) or 0.0))
        atr = ind.atr(data.high, data.low, data.close, cfg.atr_period)
        buckets: dict[int, list[float]] = {}
        atr_buckets: dict[int, list[float]] = {}
        for i in range(cfg.atr_period + 1, len(data)):
            a = float(atr[i])
            if not (a > 0) or a != a:          # zero or NaN
                continue
            risk = a * max(cfg.sl_atr_mult, 0.01)
            if risk <= 0:
                continue
            cost = float(data.spread[i]) * point + commission
            # gmtime, not localtime: an MT5 bar timestamp is a naive epoch
            # encoding the broker's own wall-clock reading, so gmtime recovers
            # that reading while localtime would add this machine's UTC offset
            # on top of it and report every bar three hours late. Same
            # convention Supervisor._bad_hours/_hour_risk_scales use on deal
            # timestamps, and the reason its gate compares against
            # localtime(server_now) - broker and Windows clock read the same
            # wall time here.
            hour = time.gmtime(int(data.time[i])).tm_hour
            buckets.setdefault(hour, []).append(cost / risk)
            atr_buckets.setdefault(hour, []).append(a)

        rows = []
        for hour in sorted(buckets):
            vals = sorted(buckets[hour])
            atrs = sorted(atr_buckets[hour])
            rows.append({
                "hour": hour,
                "samples": len(vals),
                "cost_over_risk": round(vals[len(vals) // 2], 4),
                "atr": round(atrs[len(atrs) // 2], 6),
            })
        overall = sorted(v for vs in buckets.values() for v in vs)
        return {
            "ok": True, "symbol": symbol, "timeframe": tf,
            "sl_atr_mult": cfg.sl_atr_mult,
            "commission_per_lot": cfg.commission_per_lot,
            "median_cost_over_risk": round(overall[len(overall) // 2], 4) if overall else 0.0,
            "rows": rows,
        }

    @app.post("/api/symbols/{symbol}/close")
    def close_symbol(symbol: str) -> dict[str, Any]:
        closed, remaining = engine.close_all(symbol=symbol)
        return {"ok": remaining == 0, "closed": closed, "remaining": remaining}

    @app.post("/api/symbols-bulk")
    def bulk_patch(body: BulkPatch) -> dict[str, Any]:
        _reject_internal_fields(body.patch)
        _reject_bad_dict_fields(body.patch, ("secondary_params",))
        _reject_non_finite_values(body.patch)
        if isinstance(body.patch.get("secondary_params"), dict):
            _reject_non_finite_values(body.patch["secondary_params"], "secondary_params")
            _validate_enum_fields(body.patch["secondary_params"], "secondary_params")
            # Same nested gap patch_symbol closes - bulk is the other door to
            # the identical write, across every targeted symbol at once.
            _validate_risk_bounds(body.patch["secondary_params"], label="secondary_params")
        _validate_enum_fields(body.patch)
        _validate_risk_bounds(body.patch)
        # Bulk is the other door to the same write, and the one that would
        # apply a malformed window to the whole portfolio at once.
        _validate_sessions(body.patch)
        targets = body.symbols or list(store.symbols)
        needs_tf_check = "strategy" in body.patch or "timeframe" in body.patch
        magic_changing = "magic" in body.patch
        secondary_fields = ("secondary_strategy" in body.patch
                            or "secondary_timeframe" in body.patch)
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
        next_sec_params = body.patch.get("secondary_params")
        secondary_params_present = isinstance(next_sec_params, dict)
        # secondary_params is a full replacement, not a merge, and its exit
        # fields to check depend on each target symbol's OWN current dict
        # (which key omissions matter varies per symbol) - so unlike
        # exit_fields above, this can't be reduced to one static key list
        # up front. Any presence of secondary_params in the patch has to be
        # treated as guard-worthy; the precise per-symbol diff happens below.
        guarded = (needs_tf_check or magic_changing or secondary_fields
                  or bool(exit_fields) or secondary_params_present)
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
            secondary_guarded = secondary_fields or secondary_params_present
            # Same untracked-fill risk class optimizer.apply_secondary() and
            # patch_symbol()'s _secondary_risk() guard for (see engine.py's
            # H1 orphan tracking) - a live-tagged ticket alone missed a
            # closed-but-still-unresolved orphan ticket, and missed a
            # still-open orphan-scan window entirely (that one has no ticket
            # number at all yet, so it cannot be found via client.positions()
            # - it is keyed by symbol, checked separately below).
            tagged = {int(t) for t in (store.get_setting("secondary_tickets", []) or [])}
            orphan_tickets = {int(t) for t in (store.get_setting("secondary_orphan_tickets", []) or [])}
            watch_tickets = tagged | orphan_tickets
            watch_magics = ({p["magic"] for p in all_pos if p["ticket"] in watch_tickets}
                            if secondary_guarded and watch_tickets else set())
            # M1: patch_symbol()'s primary guard already treats a pending
            # secondary_orphan_scan window the same as a visible open position
            # (_pending_orphan_scan) - bulk only ever loaded this dict when a
            # secondary field/param was in the patch, so a primary-only bulk
            # (family/magic/EXIT_RISK) never saw a scan that was watching the
            # very magic it was about to reassign or mutate exits under.
            orphan_scan = store.get_setting("secondary_orphan_scan", {}) or {} if guarded else {}
            for symbol in targets:
                current = store.symbols.get(symbol) if guarded else None
                if guarded and current is None:
                    continue
                if needs_tf_check:
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
                if secondary_fields and current is not None:
                    next_sec = body.patch.get("secondary_strategy", current.secondary_strategy)
                    next_stf = body.patch.get("secondary_timeframe", current.secondary_timeframe)
                    sec_changing = (next_sec != current.secondary_strategy
                                    or next_stf != current.secondary_timeframe)
                    if sec_changing and (current.magic in watch_magics or pending_scan):
                        rejected.append(symbol)
                        continue
                if exit_fields and current is not None:
                    exit_changing = any(body.patch[k] != getattr(current, k) for k in exit_fields)
                    if exit_changing and (current.magic in open_magics or pending_scan):
                        rejected.append(symbol)
                        continue
                if secondary_params_present and current is not None:
                    sec_keys = (set(next_sec_params) | set(current.secondary_params)) & EXIT_RISK_FIELDS
                    sec_exit_changing = any(next_sec_params.get(k) != current.secondary_params.get(k)
                                            for k in sec_keys)
                    if sec_exit_changing and (current.magic in watch_magics or pending_scan):
                        rejected.append(symbol)
                        continue
                if store.update_symbol(symbol, body.patch) is not None:
                    changed += 1
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
                        409, f"portfoy sifirlanamadi: tanimlanamayan ikincil ticket taramasi "
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
                avoid_magics=_orphan_ticket_magics(),
            )
        return {"ok": True, "seeded": count, "symbols": symbol_payload(force=True),
                "system": store.system.to_dict()}

    # -------------------------------------------------------------- system

    @app.get("/api/system")
    def get_system() -> dict[str, Any]:
        return {"ok": True, "system": store.system.to_dict()}

    @app.post("/api/system")
    def patch_system(body: SystemPatch) -> dict[str, Any]:
        patch = body.model_dump()
        patch.pop("running", None)  # bot state is owned by start/stop
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
                # Fine for an intentional NAS backup; not something a plain
                # backup_dir PATCH should be able to flip on by itself, since
                # that is the one field here that turns "misconfigured" into
                # "exfiltration". allow_unc has to already be true (set in a
                # separate, explicit step) or be flipped on in this same
                # request alongside the UNC path.
                allow_unc = patch.get("backup_dir_allow_unc", store.system.backup_dir_allow_unc)
                if not allow_unc:
                    raise HTTPException(
                        400, f"{field} UNC ({path!r}) - once backup_dir_allow_unc:true "
                             f"gonderin (agdaki bir paylasima proje + veritabani kopyalanacak)")
        updated = store.update_system(patch)
        result: dict[str, Any] = {"ok": True, "system": updated.to_dict()}
        if "mt5_terminal_path" in patch:
            client.set_terminal_path(updated.mt5_terminal_path)
            LOG.emit(f"MT5 yolu guncellendi: {updated.mt5_terminal_path or '(bos)'}", "INFO")
            ok = client.reconnect()
            result["mt5_reconnect"] = ok
            result["mt5_error"] = client.last_error
            result["terminal"] = client.terminal_flags()
            result["configured_path"] = updated.mt5_terminal_path
        return result

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
        return {"ok": True, "positions": engine.positions_view()}

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
        closed, remaining = engine.close_all()
        return {"ok": remaining == 0, "closed": closed, "remaining": remaining}

    # ----------------------------------------------------------- optimizer

    @app.get("/api/opt/params")
    def opt_params() -> dict[str, Any]:
        return {"ok": True, "params": store.opt_params()}

    @app.post("/api/opt/params")
    def set_opt_params(body: dict[str, Any]) -> dict[str, Any]:
        # These parameters drive the walk-forward search that ultimately
        # writes live trading params via apply() - same NaN/Infinity class of
        # risk as the symbol-level fields. strategy_grids/grid nest their
        # numeric axes inside {strategy: {param: [values...]}}, so this needs
        # the recursive check, not the flat top-level-only one.
        _reject_non_finite_deep(body)
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
        return {"ok": True, "params": store.save_opt_params(body)}

    @app.post("/api/opt/params/reset")
    def reset_opt_params() -> dict[str, Any]:
        return {"ok": True, "params": store.reset_opt_params()}

    @app.post("/api/opt/run")
    def opt_run(body: OptRun) -> dict[str, Any]:
        result = optimizer.start(body.symbols, body.apply_best, body.bars,
                                 timeframes=body.timeframes)
        if not result.get("ok"):
            raise HTTPException(409, result.get("error", "optimizasyon baslatilamadi"))
        return result

    @app.get("/api/opt/job")
    def opt_job() -> dict[str, Any]:
        return {"ok": True, "job": optimizer.status()}

    @app.post("/api/opt/cancel")
    def opt_cancel() -> dict[str, Any]:
        return optimizer.cancel()

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
        if params is None and body.run_id is not None:
            match = next((r for r in store.opt_history(body.symbol, 40) if r["id"] == body.run_id), None)
            if match is None:
                raise HTTPException(404, "kayit bulunamadi")
            params, score, detail = match.get("params"), match.get("score", 0.0), match
            timeframe = timeframe or match.get("timeframe")
            strategy = strategy or match.get("strategy")
        if not params:
            raise HTTPException(400, "parametre yok")
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
        rejected = detail is not None and detail.get("validated") is False
        if rejected and not body.force:
            raise HTTPException(
                400, f"bu sonuc dogrulanmadi ({detail.get('keep_reason', '')}) - "
                     f"uygulamak icin force:true gonderin")
        result = optimizer.apply(body.symbol, params, float(score), detail, timeframe, strategy)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "uygulanamadi"))

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
        if rejected:
            warning = (f"dogrulanmamis sonuc force ile uygulandi "
                       f"({detail.get('keep_reason', 'sebep yok')})")
            LOG.emit(f"OPT parametreleri DOGRULANMADAN uygulandi (force, skor {score:.2f}): "
                     f"{detail.get('keep_reason', 'sebep belirtilmemis')}", "WARN", body.symbol)
            return {**result, "warning": warning}
        LOG.emit(f"OPT parametreleri uygulandi (skor {score:.2f}).", "OPT", body.symbol)
        return result

    # ------------------------------------------------------------------ ai

    @app.get("/api/ai")
    def ai_status() -> dict[str, Any]:
        return {"ok": True, "ai": engine.supervisor.status()}

    @app.post("/api/ai/settings")
    def ai_settings(body: dict[str, Any]) -> dict[str, Any]:
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

    @app.post("/api/logs/clear")
    def logs_clear() -> dict[str, Any]:
        LOG.clear()
        return {"ok": True}

    @app.get("/api/logs/download")
    def logs_download():
        path = LOG.file_path
        if not path.exists():
            raise HTTPException(404, "log dosyasi yok")
        return FileResponse(str(path), filename="micofx.log", media_type="text/plain")

    @app.post("/api/app/shutdown")
    def app_shutdown() -> dict[str, Any]:
        LOG.emit("Kapatma istegi alindi.", "WARN")
        engine.shutdown()

        def _kill() -> None:
            time.sleep(0.6)
            client.shutdown()
            os.kill(os.getpid(), signal.SIGTERM)

        threading.Thread(target=_kill, daemon=True).start()
        return {"ok": True, "message": "Uygulama kapaniyor."}

    @app.post("/api/app/restart")
    def app_restart() -> dict[str, Any]:
        LOG.emit("Yeniden baslatma istegi alindi.", "WARN")
        engine.shutdown()

        def _restart() -> None:
            time.sleep(0.3)
            try:
                # restart.bat waits for this process to release the port before
                # relaunching, so it must be spawned before this process exits.
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
