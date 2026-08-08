from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import APP_NAME, __version__
from ..engine import Engine
from ..logbus import LOG
from ..models import strategy_allows_timeframe
from ..mt5client import MT5Client
from ..optimizer import Optimizer
from ..paths import ROOT, WEB_DIR
from ..sessions import describe
from ..store import Store

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


def create_app(store: Store, client: MT5Client, engine: Engine, optimizer: Optimizer) -> FastAPI:
    app = FastAPI(title=f"{APP_NAME} Terminal", version=__version__, docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

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
        return HTMLResponse((TEMPLATES / "index.html").read_text(encoding="utf-8"))

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
            rows.append({
                "symbol": cfg.symbol, "lot_mode": cfg.lot_mode,
                "fixed_lot": cfg.fixed_lot, "broker_min_lot": floor,
                "lot_mismatch": lot_mismatch,
                "configured_friday_close_min": configured_close,
                "broker_friday_close_min": broker_close,
                "close_mismatch": close_mismatch,
            })
        return {"ok": True, "rows": rows}

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

    def _open_under_magic(magic: int) -> list[dict[str, Any]]:
        return [p for p in client.positions() if p["magic"] == magic]

    def _open_tagged_secondary(magic: int) -> list[dict[str, Any]]:
        tagged = {int(t) for t in (store.get_setting("secondary_tickets", []) or [])}
        if not tagged:
            return []
        return [p for p in client.positions(magic=magic) if p["ticket"] in tagged]

    @app.post("/api/symbols/{symbol}")
    def patch_symbol(symbol: str, body: SymbolPatch) -> dict[str, Any]:
        patch = body.model_dump()
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
        guarded = magic_changing or primary_changing or secondary_changing
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
            if guarded and current is not None:
                if magic_changing or primary_changing:
                    open_here = _open_under_magic(current.magic)
                    if open_here:
                        what = "magic" if magic_changing else "strateji/zaman dilimi"
                        raise HTTPException(
                            409, f"{symbol}: {what} degistirilemedi, {len(open_here)} acik pozisyon var "
                                 f"(once kapatin veya pozisyon kapanmasini bekleyin)")
                if secondary_changing:
                    live_tagged = _open_tagged_secondary(current.magic)
                    if live_tagged:
                        raise HTTPException(
                            409, f"{symbol}: ikincil strateji degistirilemedi, "
                                 f"{len(live_tagged)} acik ikincil-sinyal pozisyonu var "
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
        try:
            cfg = store.add_symbol(
                body.symbol,
                group=body.group or "forex",
                broker_symbol=body.broker_symbol or "",
                enabled=body.enabled,
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
            open_here = [p for p in client.positions() if p["magic"] == cfg.magic]
            if open_here:
                raise HTTPException(
                    409, f"{symbol} silinemedi: {len(open_here)} acik pozisyon var "
                         f"(once kapatin veya 'enabled:false' yapip pozisyon kapanmasini bekleyin)")
            store.delete_symbol(symbol)
        engine.states.pop(symbol, None)
        engine.supervisor.clear(symbol)
        engine.execution.drop_symbol(symbol)
        engine._sec_cfgs.pop(symbol, None)
        LOG.emit(f"{symbol} portfoyden silindi.", "WARN", symbol)
        client.set_overrides({c.symbol: c.broker_symbol for c in list(store.symbols.values())})
        return {"ok": True, "symbols": symbol_payload(force=True), "system": store.system.to_dict()}

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
                updated = store.reset_symbol_to_preset(symbol)
        else:
            updated = store.reset_symbol_to_preset(symbol)
        if updated is None:
            raise HTTPException(404, f"{symbol} icin varsayilan yok")
        LOG.emit("Ayarlar varsayilana dondu.", "INFO", symbol)
        return {"ok": True, "config": updated.to_dict()}

    @app.get("/api/symbols/lot-mode-check")
    def lot_mode_check() -> dict[str, Any]:
        account = engine.refresh_account(force=True)
        rows = engine.risk.lot_mode_diagnostics(float(account.get("balance", 0.0)))
        return {"ok": True, "rows": rows}

    @app.post("/api/symbols/{symbol}/close")
    def close_symbol(symbol: str) -> dict[str, Any]:
        closed = engine.close_all(symbol=symbol)
        return {"ok": True, "closed": closed}

    @app.post("/api/symbols-bulk")
    def bulk_patch(body: BulkPatch) -> dict[str, Any]:
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
        guarded = needs_tf_check or magic_changing or secondary_fields
        if guarded:
            _require_connected()
            engine.entry_lock.acquire()
        try:
            open_magics = ({p["magic"] for p in client.positions()} if guarded else set())
            tagged = {int(t) for t in (store.get_setting("secondary_tickets", []) or [])}
            tagged_magics = ({p["magic"] for p in client.positions()
                              if p["ticket"] in tagged} if secondary_fields and tagged else set())
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
                symbol_changing = (
                    (needs_tf_check and (
                        body.patch.get("strategy", current.strategy) != current.strategy
                        or body.patch.get("timeframe", current.timeframe) != current.timeframe))
                    or (magic_changing and int(body.patch["magic"]) != current.magic)
                ) if guarded else False
                if symbol_changing and current.magic in open_magics:
                    rejected.append(symbol)
                    continue
                if secondary_fields and current is not None:
                    next_sec = body.patch.get("secondary_strategy", current.secondary_strategy)
                    next_stf = body.patch.get("secondary_timeframe", current.secondary_timeframe)
                    sec_changing = (next_sec != current.secondary_strategy
                                    or next_stf != current.secondary_timeframe)
                    if sec_changing and current.magic in tagged_magics:
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
                magics = {c.magic for c in list(store.symbols.values())}
                open_bot = [p for p in client.positions() if p["magic"] in magics]
                if open_bot:
                    raise HTTPException(
                        409, f"portfoy sifirlanamadi: {len(open_bot)} acik bot pozisyonu var "
                             f"(once kapatin veya panic ile duzleyin)")
                count = store.replace_with_defaults()
        else:
            count = store.seed_symbols(overwrite=False)
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
        ok = client.close_position(int(ticket), store.system.slippage_points, "MicoFX manuel")
        return {"ok": ok}

    @app.post("/api/positions-close-all")
    def close_everything() -> dict[str, Any]:
        return {"ok": True, "closed": engine.close_all()}

    # ----------------------------------------------------------- optimizer

    @app.get("/api/opt/params")
    def opt_params() -> dict[str, Any]:
        return {"ok": True, "params": store.opt_params()}

    @app.post("/api/opt/params")
    def set_opt_params(body: dict[str, Any]) -> dict[str, Any]:
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
        # A run_id pull carries the search's own verdict - refuse to apply a
        # candidate the walk-forward itself rejected unless the caller
        # explicitly overrides. Hand-typed params (no run_id, no detail) are
        # a different, pre-existing use case - unrelated to any optimizer
        # run - and are not gated here.
        if detail is not None and detail.get("validated") is False and not body.force:
            raise HTTPException(
                400, f"bu sonuc dogrulanmadi ({detail.get('keep_reason', '')}) - "
                     f"uygulamak icin force:true gonderin")
        result = optimizer.apply(body.symbol, params, float(score), detail, timeframe, strategy)
        if not result.get("ok"):
            raise HTTPException(400, result.get("error", "uygulanamadi"))
        LOG.emit(f"OPT parametreleri uygulandi (skor {score:.2f}).", "OPT", body.symbol)
        return result

    # ------------------------------------------------------------------ ai

    @app.get("/api/ai")
    def ai_status() -> dict[str, Any]:
        return {"ok": True, "ai": engine.supervisor.status()}

    @app.post("/api/ai/settings")
    def ai_settings(body: dict[str, Any]) -> dict[str, Any]:
        settings = engine.supervisor.update_settings(body)
        LOG.emit("AI denetleyici ayarlari guncellendi.", "AI")
        return {"ok": True, "settings": settings}

    @app.post("/api/ai/review")
    def ai_review() -> dict[str, Any]:
        account = engine.refresh_account(force=True)
        pnl = engine.risk.daily.pnl_pct(float(account.get("equity", 0.0)))
        return {"ok": True, "ai": engine.supervisor.review(pnl)}

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
