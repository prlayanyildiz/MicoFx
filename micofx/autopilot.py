"""In-process income autopilot — no HTTP, no PowerShell, no second DB writer.

Runs on a side thread kicked from ``Engine._cycle`` (same shape as the
supervisor review). Safe fixes + evidence-only spread widen + kasa/cost-free
knobs + opt onboarding (never-searched → WFO stamp → enable gate). Does not
run age-based / weekly reopt (AGENTS: auto-search is quarantine-only).
"""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from .entry_pressure import spread_pressure
from .logbus import LOG
from .supervisor import Supervisor

_SPREAD_AUTO_MIN = 10
_ENTRY_BLOCKS_MAX_AGE_SEC = 7 * 86400
# Session/msa charged sweeps are heavier than calibrate — run at most hourly.
_TUNE_MIN_INTERVAL_SEC = 3600.0
_ROOT = Path(__file__).resolve().parents[1]
# Written when live AP is disabled only to bind exec-freeze to an old PID;
# new process loads freeze in tune path then flips AP back on.
_AUTOPILOT_RESUME_FLAG = _ROOT / ".bridge" / "AUTOPILOT_RESUME_AFTER_RESTART"
_XAU_SL_PENDING = _ROOT / ".bridge" / "XAU_SL_07_PENDING"
_XAU_SL_DONE = _ROOT / ".bridge" / "XAU_SL_07_DONE.txt"
_XAU_SL_REENABLE = _ROOT / ".bridge" / "XAU_SL_07_REENABLE"
_XAU_STREAK_STATE = _ROOT / ".bridge" / "XAU_STREAK_STATE.json"
# Holdout net R floor before autopilot flips enabled on a stamped newcomer.
ENABLE_MIN_HOLD_NET_R = 20.0
_OPERATOR_DISABLED_KEY = "operator_disabled_symbols"


def maybe_resume_autopilot_after_freeze_bind(store: Any) -> str | None:
    """Re-enable AP after restart once this PID can honor exec freeze.

    Cursor 04.09: old live bytecode ignored ``pipeline_frozen``; AP was turned
    off to stop micro-tunes. Flag file + this boot hook restore kasa/spread
    ticks while tune stays frozen via ``exec_gates``.
    """
    if not _AUTOPILOT_RESUME_FLAG.is_file():
        return None
    try:
        import sys as _sys
        if str(_ROOT) not in _sys.path:
            _sys.path.insert(0, str(_ROOT))
        from scripts.exec_gates import pipeline_frozen
    except Exception:
        return None
    if not pipeline_frozen():
        return None
    sys = store.system
    if bool(getattr(sys, "autopilot_enabled", True)):
        try:
            _AUTOPILOT_RESUME_FLAG.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    store.update_system(
        {"autopilot_enabled": True}, source="freeze-bind resume")
    try:
        _AUTOPILOT_RESUME_FLAG.unlink(missing_ok=True)
    except OSError:
        pass
    LOG.emit(
        "Autopilot tekrar acildi (freeze-bind resume; exec tune hala frozen).",
        "INFO",
    )
    return "autopilot_enabled=true (freeze-bind resume)"


def maybe_land_pending_xau_sl(optimizer: Any, store: Any) -> str | None:
    """Claude 04.50 explicit OK: XAUUSD sl 0.5→0.7 after new PID loads waiver.

    Flag-armed while the pre-freeze PID refused last-seg regression. In-process
    apply (no second sqlite writer). Idempotent.

    Deferred while a ticket is open: keep PENDING + do not re-enable (else a
    new fill could open on live sl 0.5 before ``pending_exit_patch`` lands).
    """
    if not _XAU_SL_PENDING.is_file() or optimizer is None or store is None:
        return None
    cfg = store.symbols.get("XAUUSD")
    if cfg is None:
        return None
    target = 0.7
    try:
        cur = float(getattr(cfg, "sl_atr_mult", 0.0) or 0.0)
    except (TypeError, ValueError):
        cur = 0.0
    if abs(cur - target) < 1e-9:
        _finish_xau_sl_pending(f"already sl={target:g}")
        re_msg = _reenable_xau_after_sl_land(store)
        out = f"XAUUSD zaten sl={target:g}"
        return f"{out}; {re_msg}" if re_msg else out

    pend = getattr(cfg, "pending_exit_patch", None) or {}
    try:
        pend_sl = float(pend.get("sl_atr_mult") or 0.0) if isinstance(pend, dict) else 0.0
    except (TypeError, ValueError):
        pend_sl = 0.0
    if abs(pend_sl - target) < 1e-9:
        return f"XAUUSD sl {target:g} kuyrukta (flat bekleniyor)"

    try:
        score = float(getattr(cfg, "opt_score", 0.0) or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    prev = bool(getattr(optimizer, "_force_apply", False))
    optimizer._force_apply = True
    try:
        res = optimizer.apply(
            "XAUUSD",
            {"sl_atr_mult": target},
            score=score,
            detail=None,
            timeframe=str(getattr(cfg, "timeframe", "") or ""),
            strategy=str(getattr(cfg, "strategy", "") or ""),
        )
    except Exception as exc:
        LOG.emit(f"XAUUSD sl land exception: {exc}", "WARN")
        return None
    finally:
        optimizer._force_apply = prev
    if not isinstance(res, dict) or not res.get("ok"):
        err = (res or {}).get("error") if isinstance(res, dict) else res
        LOG.emit(f"XAUUSD sl land fail: {err}", "WARN")
        return None

    cfg2 = store.symbols.get("XAUUSD") or cfg
    try:
        landed = float(getattr(cfg2, "sl_atr_mult", 0.0) or 0.0)
    except (TypeError, ValueError):
        landed = 0.0
    deferred = bool(res.get("deferred"))
    if deferred or abs(landed - target) > 1e-9:
        # Keep PENDING / REENABLE until live sl is actually 0.7.
        LOG.emit(
            f"XAUUSD sl {cur:g}->{target:g} kuyruga alindi "
            f"(pozisyon acik; re-enable yok).",
            "OPT", "XAUUSD",
        )
        return f"XAUUSD sl {cur:g}->{target:g} kuyrukta"

    _finish_xau_sl_pending(f"landed sl {cur:g}->{target:g}")
    re_msg = _reenable_xau_after_sl_land(store)
    LOG.emit(
        f"XAUUSD sl {cur:g}->{target:g} (Claude 04:50 pending land)"
        + (f"; {re_msg}" if re_msg else "") + ".",
        "OPT", "XAUUSD",
    )
    out = f"XAUUSD sl {cur:g}->{target:g}"
    if re_msg:
        out = f"{out}; {re_msg}"
    return out


def _reenable_xau_after_sl_land(store: Any) -> str | None:
    if not _XAU_SL_REENABLE.is_file():
        return None
    cfg = store.symbols.get("XAUUSD")
    if cfg is None:
        return None
    if bool(getattr(cfg, "enabled", False)):
        try:
            _XAU_SL_REENABLE.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    updated = store.update_symbol(
        "XAUUSD", {"enabled": True}, source="xau-sl-07-land")
    try:
        _XAU_SL_REENABLE.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        mark_operator_disabled(store, "XAUUSD", disabled=False)
    except Exception:
        pass
    if updated is not None and bool(getattr(updated, "enabled", False)):
        LOG.emit("XAUUSD tekrar acildi (sl 0.7 land sonrasi).", "INFO", "XAUUSD")
        return "enabled=true"
    return "re-enable fail"


def _finish_xau_sl_pending(note: str) -> None:
    try:
        _XAU_SL_PENDING.unlink(missing_ok=True)
    except OSError:
        pass
    try:
        _XAU_SL_DONE.parent.mkdir(parents=True, exist_ok=True)
        _XAU_SL_DONE.write_text(note + "\n", encoding="utf-8")
    except OSError:
        pass
    try:
        import json
        _XAU_STREAK_STATE.write_text(
            json.dumps({
                "alerted_level": "ok",
                "streak": 0,
                "exp_alerted": False,
                "ts": "reset-after-sl-land",
                "note": note,
            }, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def kasa_leverage(sys: Any, account: dict[str, Any] | None) -> float:
    """Leverage kasa should size against: dial capped to the live broker.

    ``target_leverage`` 0 = use ``account.leverage``. A positive dial is an
    intent knob only — never above what MT5 reports for this login.
    """
    try:
        acc_lev = float((account or {}).get("leverage") or 1.0)
    except (TypeError, ValueError):
        acc_lev = 1.0
    acc_lev = max(1.0, acc_lev)
    try:
        want = float(getattr(sys, "target_leverage", 0.0) or 0.0)
    except (TypeError, ValueError):
        want = 0.0
    if want <= 0:
        return acc_lev
    return min(want, acc_lev)


def _aggregate_entry_blocks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge buy/sell legs per symbol (same shape as income_dev_loop)."""
    by_sym: dict[str, dict[str, Any]] = {}
    for row in rows:
        sym = str(row.get("symbol") or "")
        if not sym:
            continue
        agg = by_sym.setdefault(
            sym, {"signals": 0, "opened": 0, "blocks": {}, "retries": {}})
        agg["signals"] += int(row.get("signals") or 0)
        agg["opened"] += int(row.get("opened") or 0)
        for k, v in (row.get("blocks") or {}).items():
            try:
                agg["blocks"][str(k)] = (
                    int(agg["blocks"].get(str(k), 0)) + int(v or 0))
            except (TypeError, ValueError):
                continue
        for k, v in (row.get("retries") or {}).items():
            try:
                agg["retries"][str(k)] = (
                    int(agg["retries"].get(str(k), 0)) + int(v or 0))
            except (TypeError, ValueError):
                continue
    out: list[dict[str, Any]] = []
    for sym, agg in sorted(by_sym.items()):
        total = int(agg["signals"])
        opened = int(agg["opened"])
        out.append({
            "symbol": sym,
            "signals": total,
            "opened": opened,
            "fill_rate": round(opened / total, 3) if total else 0.0,
            "blocks": agg["blocks"],
            "retries": agg["retries"],
        })
    return out


def spread_auto_targets(
    entry_rows: list[dict[str, Any]],
    open_symbols: set[str],
    active: set[str],
) -> list[str]:
    """Flat enabled symbols where spread is the dominant blocker with evidence."""
    out: list[str] = []
    for row in entry_rows:
        sym = str(row.get("symbol") or "")
        if sym not in active or sym in open_symbols:
            continue
        blocks = row.get("blocks") or {}
        spread_n = spread_pressure(row)
        signals = int(row.get("signals") or 0)
        fill = float(row.get("fill_rate") or 0.0)
        if spread_n < _SPREAD_AUTO_MIN or signals < 5:
            continue
        top = max(int(v or 0) for v in blocks.values()) if blocks else 0
        # Retries can outrank unique blocks (US30 seans_disi=6 vs spread
        # blocks=2 but pressure=17 from retries).
        if spread_n >= max(top, _SPREAD_AUTO_MIN) and fill < 0.35:
            out.append(sym)
        elif spread_n >= _SPREAD_AUTO_MIN and fill < 0.25:
            out.append(sym)
    return out


def _load_compute_kasa():
    try:
        from .kasa_sizing import compute_kasa_targets
        return compute_kasa_targets
    except Exception:
        return None


def mark_operator_disabled(store: Any, symbol: str, disabled: bool) -> None:
    """Panel disable must block autopilot re-enable until the operator opens it."""
    getter = getattr(store, "get_setting", None)
    setter = getattr(store, "set_setting", None)
    if not callable(getter) or not callable(setter):
        return
    raw = getter(_OPERATOR_DISABLED_KEY, {}) or {}
    if not isinstance(raw, dict):
        raw = {}
    blob = dict(raw)
    if disabled:
        blob[str(symbol)] = True
    else:
        blob.pop(str(symbol), None)
    setter(_OPERATOR_DISABLED_KEY, blob)


class AutoPilot:
    """Periodic book-health tick owned by the live Engine process."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.last_tick_at = 0.0
        self.last_summary: list[str] = []
        self._last_tune_at = 0.0
        self._gate = threading.Lock()
        maybe_resume_autopilot_after_freeze_bind(self.store)
        # Optimizer may still be None at Engine.__init__; tick() retries.
        maybe_land_pending_xau_sl(self.optimizer, self.store)

    @property
    def store(self):
        return self.engine.store

    @property
    def client(self):
        return self.engine.client

    @property
    def optimizer(self):
        sup = getattr(self.engine, "supervisor", None)
        return getattr(sup, "optimizer", None) if sup is not None else None

    def due(self) -> bool:
        sys = self.store.system
        if not bool(getattr(sys, "autopilot_enabled", True)):
            return False
        interval = float(getattr(sys, "autopilot_interval_sec", 900) or 0.0)
        if interval <= 0:
            return False
        return (time.time() - float(self.last_tick_at or 0.0)) >= interval

    def status(self) -> dict[str, Any]:
        sys = self.store.system
        return {
            "enabled": bool(getattr(sys, "autopilot_enabled", True)),
            "interval_sec": float(getattr(sys, "autopilot_interval_sec", 900) or 900),
            "last_tick_at": self.last_tick_at,
            "last_summary": list(self.last_summary[-16:]),
            "busy": self._gate.locked(),
        }

    def tick(self) -> list[str]:
        if not self._gate.acquire(blocking=False):
            return ["autopilot: onceki tick devam ediyor"]
        try:
            summary = self._tick_body()
            self.last_summary = summary
            self.last_tick_at = time.time()
            if summary:
                LOG.emit("Autopilot: " + "; ".join(summary[:8]), "INFO")
            return summary
        except Exception as exc:
            msg = f"autopilot hata: {exc}"
            self.last_summary = [msg]
            self.last_tick_at = time.time()
            LOG.emit(msg, "ERROR")
            return [msg]
        finally:
            self._gate.release()

    def _tick_body(self) -> list[str]:
        done: list[str] = []
        landed = maybe_land_pending_xau_sl(self.optimizer, self.store)
        if landed:
            done.append(landed)
        sys = self.store.system
        if not bool(getattr(sys, "autopilot_enabled", True)):
            return done + ["autopilot kapali"]

        done.extend(self._apply_safe_fixes())
        done.extend(self._apply_trust_ai())
        done.extend(self._apply_kasa())
        # Spread before cost_free: turning charge_costs off would skip widen.
        done.extend(self._apply_spread())
        done.extend(self._apply_session_msa_trail_tune())
        done.extend(self._apply_cost_free())
        done.extend(self._apply_opt_lifecycle())
        if not done:
            done.append("autopilot: degisiklik yok")
        return done

    def _enabled_symbols(self) -> dict[str, Any]:
        return {
            sym: cfg for sym, cfg in list(self.store.symbols.items())
            if getattr(cfg, "enabled", False)
        }

    def _open_symbols(self) -> set[str]:
        out: set[str] = set()
        for p in list(getattr(self.engine, "_positions", None) or []):
            sym = str(p.get("symbol") or "")
            if sym:
                out.add(sym)
        return out

    def _entry_rows(self) -> list[dict[str, Any]]:
        getter = getattr(self.engine, "entry_blocks", None)
        if not callable(getter):
            return []
        data = getter() or {}
        since = float(data.get("since") or 0.0)
        if since > 0 and (time.time() - since) > _ENTRY_BLOCKS_MAX_AGE_SEC:
            return []
        return _aggregate_entry_blocks(list(data.get("rows") or []))

    def _apply_safe_fixes(self) -> list[str]:
        done: list[str] = []
        sys = self.store.system
        if not bool(getattr(sys, "autostart_bot", False)):
            self.store.update_system({"autostart_bot": True}, source="autopilot")
            done.append("autostart_bot=true")
        for sym, cfg in self._enabled_symbols().items():
            partial = getattr(cfg, "partial_at_r", 0)
            if partial in (0, 0.0, None):
                continue
            self.store.update_symbol(sym, {"partial_at_r": 0}, source="autopilot")
            done.append(f"{sym} partial_at_r=0")
        return done

    def _apply_trust_ai(self) -> list[str]:
        sup = getattr(self.engine, "supervisor", None)
        if sup is None:
            return []
        settings = getattr(sup, "settings", None) or {}
        patch: dict[str, Any] = {}
        if settings.get("prefer_strong_on_dd"):
            patch["prefer_strong_on_dd"] = False
        if not settings.get("hard_block_only_quarantine", True):
            patch["hard_block_only_quarantine"] = True
        if not patch:
            return []
        updater = getattr(sup, "update_settings", None)
        if callable(updater):
            updater(patch)
        return [f"AI trust {patch}"]

    def _apply_cost_free(self) -> list[str]:
        """No longer auto-disables ``charge_costs`` when commission is 0.

        CFD rows often ship ``commission_per_lot=0`` while spread is the real
        fill cost. Autopilot used to flip ``charge_costs``/``block_high_cost``
        off in that case; WFO then ranked paper-optimal SL and the live book
        mis-tuned (Claude 03.09 autopsy: GER40/BTC; cost-free force-WFO kept
        both incumbents). Operator owns the cost toggles.
        """
        return []

    def _apply_kasa(self) -> list[str]:
        """Slow tick: no lot/conc/margin patches. Dial is max_margin_usage_pct."""
        sys = self.store.system
        if not bool(getattr(sys, "kasa_auto_enabled", True)):
            return ["kasa: operator kapali"]
        # Lot + concurrent are inline in RiskManager; margin% is the operator
        # dial. Autopilot only keeps autostart_bot if somehow off.
        if not bool(getattr(sys, "autostart_bot", True)):
            self.store.update_system({"autostart_bot": True}, source="autopilot")
            return ["kasa autostart_bot ac"]
        return []

    def _apply_spread(self) -> list[str]:
        try:
            import sys
            if str(_ROOT) not in sys.path:
                sys.path.insert(0, str(_ROOT))
            from scripts.exec_gates import pipeline_frozen
            if pipeline_frozen():
                return ["spread: exec pipeline FREEZE (Claude 03:36)"]
        except Exception:
            pass
        opt = self.optimizer
        if opt is not None and bool(getattr(opt, "busy", False)):
            return ["spread: opt calisiyor - atlandi"]
        if not bool(getattr(self.client, "connected", False)):
            return ["spread: MT5 bagli degil - atlandi"]
        if not bool(getattr(self.store.system, "charge_costs", True)):
            return ["spread: charge_costs=false - atlandi"]
        if opt is None or not hasattr(opt, "_recalibrate_spread_cap"):
            return ["spread: optimizer yok"]

        active = set(self._enabled_symbols())
        open_syms = self._open_symbols()
        targets = spread_auto_targets(self._entry_rows(), open_syms, active)
        if not targets:
            return []

        done: list[str] = []
        for sym in targets:
            if sym in open_syms:
                continue
            cfg = self.store.symbols.get(sym)
            if cfg is None:
                continue
            before = float(getattr(cfg, "max_spread_atr", 0.0) or 0.0)
            opt._recalibrate_spread_cap(sym, cfg.timeframe)
            cfg = self.store.symbols.get(sym)
            after = float(getattr(cfg, "max_spread_atr", 0.0) or 0.0) if cfg else before
            if abs(after - before) >= 1e-9:
                done.append(f"{sym} spread {before:g}->{after:g}")
            else:
                done.append(f"{sym} spread degismedi")
        return done

    def _apply_session_msa_trail_tune(self) -> list[str]:
        """Hourly charged session/msa/cost_rank/trail self-tune via snapshots.

        Same pickers as ``scripts/*_exec``. Fixed axis order; **one successful
        land per symbol per cycle** so axes cannot compound in one hour.
        Skips open tickets for EXIT_RISK (trail_*).
        """
        now = time.time()
        if (now - float(self._last_tune_at or 0.0)) < _TUNE_MIN_INTERVAL_SEC:
            return []
        opt = self.optimizer
        if opt is not None and bool(getattr(opt, "busy", False)):
            return ["tune: opt calisiyor - atlandi"]
        try:
            import sys
            if str(_ROOT) not in sys.path:
                sys.path.insert(0, str(_ROOT))
            from scripts.exec_gates import pipeline_frozen
            if pipeline_frozen():
                self._last_tune_at = now
                return ["tune: exec pipeline FREEZE (Claude 03:36)"]
            from scripts.adx_exec import propose_adx_upgrade
            from scripts.atr_pct_exec import propose_atr_pct_upgrade
            from scripts.body_exec import propose_body_upgrade
            from scripts.cost_rank_exec import propose_cost_rank_upgrade
            from scripts.msa_exec import propose_msa_upgrade
            from scripts.session_exec import propose_session_upgrade
            from scripts.trail_exec import (
                propose_trail_start_upgrade,
                propose_trail_upgrade,
            )
        except Exception as exc:
            return [f"tune: import fail ({exc})"]

        open_syms = self._open_symbols()
        done: list[str] = []
        scanned = 0
        kept = 0
        self._last_tune_at = now
        for sym, cfg in self._enabled_symbols().items():
            if sym in open_syms:
                continue
            try:
                row = cfg.to_dict() if hasattr(cfg, "to_dict") else dict(cfg)
            except Exception:
                continue
            if not isinstance(row, dict):
                continue
            row["symbol"] = sym
            scanned += 1

            sess_pick = None
            msa_pick = None
            cr_pick = None
            adx_pick = None
            atr_pct_pick = None
            body_pick = None
            trail_pick = None
            trail_start_pick = None
            try:
                sess_pick = propose_session_upgrade(row)
            except Exception as exc:
                done.append(f"{sym} seans olcum fail: {exc}")
            try:
                msa_pick = propose_msa_upgrade(row)
            except Exception as exc:
                done.append(f"{sym} msa olcum fail: {exc}")
            try:
                cr_pick = propose_cost_rank_upgrade(row)
            except Exception as exc:
                done.append(f"{sym} cost_rank olcum fail: {exc}")
            try:
                adx_pick = propose_adx_upgrade(row)
            except Exception as exc:
                done.append(f"{sym} adx olcum fail: {exc}")
            try:
                atr_pct_pick = propose_atr_pct_upgrade(row)
            except Exception as exc:
                done.append(f"{sym} atr_pct olcum fail: {exc}")
            try:
                body_pick = propose_body_upgrade(row)
            except Exception as exc:
                done.append(f"{sym} body olcum fail: {exc}")
            try:
                trail_pick = propose_trail_upgrade(row)
            except Exception as exc:
                done.append(f"{sym} trail olcum fail: {exc}")
            try:
                trail_start_pick = propose_trail_start_upgrade(row)
            except Exception as exc:
                done.append(f"{sym} trail_start olcum fail: {exc}")

            # Fixed order; at most ONE successful land per symbol per tune
            # cycle so session→msa→trail cannot compound-overfit in one hour
            # (Claude 04.09 03:05).
            landed = False
            if sess_pick is not None:
                updated = self.store.update_symbol(
                    sym,
                    {
                        "sessions": sess_pick["sessions"],
                        "use_sessions": bool(sess_pick["use_sessions"]),
                    },
                    source="autopilot seans",
                )
                if updated is not None and opt is not None:
                    try:
                        opt.refresh_live_costed_stamp(sym)
                    except Exception:
                        pass
                win = (sess_pick["sessions"] or [{}])[0]
                done.append(
                    f"{sym} seans -> {win.get('start')}-{win.get('end')} "
                    f"({sess_pick['live_net_r']:+.1f}R->"
                    f"{sess_pick['net_r']:+.1f}R)"
                )
                landed = True
            elif msa_pick is not None and opt is not None:
                cap = float(msa_pick["max_spread_atr"])
                try:
                    score = float(getattr(cfg, "opt_score", 0.0) or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                prev_force = bool(getattr(opt, "_force_apply", False))
                opt._force_apply = True
                try:
                    result = opt.apply(
                        sym, {"max_spread_atr": cap}, score, None, None, None)
                finally:
                    opt._force_apply = prev_force
                if result.get("ok"):
                    try:
                        opt.refresh_live_costed_stamp(sym)
                    except Exception:
                        pass
                    forget = getattr(self.engine, "forget_entry_blocks", None)
                    if callable(forget):
                        forget(sym)
                    done.append(
                        f"{sym} msa {msa_pick['live_msa']:g}->{cap:g} "
                        f"({msa_pick['live_net_r']:+.1f}R->"
                        f"{msa_pick['net_r']:+.1f}R)"
                    )
                    landed = True
                else:
                    done.append(
                        f"{sym} msa fail: {result.get('error', 'uygulanamadi')}")
            elif cr_pick is not None and opt is not None:
                cr = float(cr_pick["cost_rank_max"])
                try:
                    score = float(getattr(cfg, "opt_score", 0.0) or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                prev_force = bool(getattr(opt, "_force_apply", False))
                opt._force_apply = True
                try:
                    result = opt.apply(
                        sym, {"cost_rank_max": cr}, score, None, None, None)
                finally:
                    opt._force_apply = prev_force
                if result.get("ok"):
                    try:
                        opt.refresh_live_costed_stamp(sym)
                    except Exception:
                        pass
                    done.append(
                        f"{sym} cost_rank {cr_pick['live_cr']:g}->{cr:g} "
                        f"({cr_pick['live_net_r']:+.1f}R->"
                        f"{cr_pick['net_r']:+.1f}R)"
                    )
                    landed = True
                else:
                    done.append(
                        f"{sym} cost_rank fail: "
                        f"{result.get('error', 'uygulanamadi')}")
            elif adx_pick is not None and opt is not None:
                adx = float(adx_pick["adx_min"])
                try:
                    score = float(getattr(cfg, "opt_score", 0.0) or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                prev_force = bool(getattr(opt, "_force_apply", False))
                opt._force_apply = True
                try:
                    result = opt.apply(
                        sym, {"adx_min": adx}, score, None, None, None)
                finally:
                    opt._force_apply = prev_force
                if result.get("ok"):
                    try:
                        opt.refresh_live_costed_stamp(sym)
                    except Exception:
                        pass
                    done.append(
                        f"{sym} adx_min {adx_pick['live_adx']:g}->{adx:g} "
                        f"({adx_pick['live_net_r']:+.1f}R->"
                        f"{adx_pick['net_r']:+.1f}R)"
                    )
                    landed = True
                else:
                    done.append(
                        f"{sym} adx_min fail: "
                        f"{result.get('error', 'uygulanamadi')}")
            elif atr_pct_pick is not None and opt is not None:
                ap = float(atr_pct_pick["atr_pct_min"])
                try:
                    score = float(getattr(cfg, "opt_score", 0.0) or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                prev_force = bool(getattr(opt, "_force_apply", False))
                opt._force_apply = True
                try:
                    result = opt.apply(
                        sym, {"atr_pct_min": ap}, score, None, None, None)
                finally:
                    opt._force_apply = prev_force
                if result.get("ok"):
                    try:
                        opt.refresh_live_costed_stamp(sym)
                    except Exception:
                        pass
                    done.append(
                        f"{sym} atr_pct_min {atr_pct_pick['live_atr_pct']:g}"
                        f"->{ap:g} "
                        f"({atr_pct_pick['live_net_r']:+.1f}R->"
                        f"{atr_pct_pick['net_r']:+.1f}R)"
                    )
                    landed = True
                else:
                    done.append(
                        f"{sym} atr_pct_min fail: "
                        f"{result.get('error', 'uygulanamadi')}")
            elif body_pick is not None and opt is not None:
                bv = float(body_pick["min_body_ratio"])
                try:
                    score = float(getattr(cfg, "opt_score", 0.0) or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                prev_force = bool(getattr(opt, "_force_apply", False))
                opt._force_apply = True
                try:
                    result = opt.apply(
                        sym, {"min_body_ratio": bv}, score, None, None, None)
                finally:
                    opt._force_apply = prev_force
                if result.get("ok"):
                    try:
                        opt.refresh_live_costed_stamp(sym)
                    except Exception:
                        pass
                    done.append(
                        f"{sym} min_body_ratio {body_pick['live_body']:g}"
                        f"->{bv:g} "
                        f"({body_pick['live_net_r']:+.1f}R->"
                        f"{body_pick['net_r']:+.1f}R)"
                    )
                    landed = True
                else:
                    done.append(
                        f"{sym} min_body_ratio fail: "
                        f"{result.get('error', 'uygulanamadi')}")
            elif trail_pick is not None and opt is not None:
                step = float(trail_pick["trail_step_atr"])
                try:
                    score = float(getattr(cfg, "opt_score", 0.0) or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                prev_force = bool(getattr(opt, "_force_apply", False))
                opt._force_apply = True
                try:
                    result = opt.apply(
                        sym, {"trail_step_atr": step}, score, None, None, None)
                finally:
                    opt._force_apply = prev_force
                if result.get("ok"):
                    try:
                        opt.refresh_live_costed_stamp(sym)
                    except Exception:
                        pass
                    done.append(
                        f"{sym} trail_step {trail_pick['live_step']:g}->{step:g} "
                        f"({trail_pick['live_net_r']:+.1f}R->"
                        f"{trail_pick['net_r']:+.1f}R)"
                    )
                    landed = True
                else:
                    done.append(
                        f"{sym} trail_step fail: "
                        f"{result.get('error', 'uygulanamadi')}")
            elif trail_start_pick is not None and opt is not None:
                start = float(trail_start_pick["trail_start_atr"])
                try:
                    score = float(getattr(cfg, "opt_score", 0.0) or 0.0)
                except (TypeError, ValueError):
                    score = 0.0
                prev_force = bool(getattr(opt, "_force_apply", False))
                opt._force_apply = True
                try:
                    result = opt.apply(
                        sym, {"trail_start_atr": start}, score, None, None, None)
                finally:
                    opt._force_apply = prev_force
                if result.get("ok"):
                    try:
                        opt.refresh_live_costed_stamp(sym)
                    except Exception:
                        pass
                    done.append(
                        f"{sym} trail_start {trail_start_pick['live_start']:g}"
                        f"->{start:g} "
                        f"({trail_start_pick['live_net_r']:+.1f}R->"
                        f"{trail_start_pick['net_r']:+.1f}R)"
                    )
                    landed = True
                else:
                    done.append(
                        f"{sym} trail_start fail: "
                        f"{result.get('error', 'uygulanamadi')}")
            if not landed:
                kept += 1
        if scanned:
            done.append(
                f"tune: {kept}/{scanned} KEEP "
                f"(seans/msa/cr/trail; 1 land/sembol)"
            )
        return done

    # -------------------------------------------------------- opt lifecycle

    def _operator_disabled(self) -> set[str]:
        raw = {}
        getter = getattr(self.store, "get_setting", None)
        if callable(getter):
            raw = getter(_OPERATOR_DISABLED_KEY, {}) or {}
        if not isinstance(raw, dict):
            return set()
        return {str(k) for k, v in raw.items() if v}

    def _onboarding_candidates(self) -> list[Any]:
        skip = self._operator_disabled()
        out: list[Any] = []
        for cfg in list(self.store.symbols.values()):
            if getattr(cfg, "enabled", False):
                continue
            if cfg.symbol in skip:
                continue
            if float(getattr(cfg, "opt_updated_at", 0.0) or 0.0) > 0:
                continue
            out.append(cfg)
        return out

    def _enable_candidates(self) -> list[Any]:
        """Stamped, still disabled, not operator-blocked, holdout clears floor."""
        skip = self._operator_disabled()
        out: list[Any] = []
        for cfg in list(self.store.symbols.values()):
            if getattr(cfg, "enabled", False):
                continue
            if cfg.symbol in skip:
                continue
            if float(getattr(cfg, "opt_updated_at", 0.0) or 0.0) <= 0:
                continue
            hold = (getattr(cfg, "opt_summary", None) or {}).get("holdout") or {}
            try:
                net_r = float(hold.get("net_r") or 0.0)
            except (TypeError, ValueError):
                net_r = 0.0
            if net_r < ENABLE_MIN_HOLD_NET_R:
                continue
            try:
                pr = float((getattr(cfg, "opt_summary", None) or {}).get(
                    "positive_ratio") or 0.0)
            except (TypeError, ValueError):
                pr = 0.0
            if pr > 0 and pr < 0.6:
                continue
            # Prefer holdout expectancy when present (same yardstick as budget).
            exp = float(Supervisor.holdout_expectancy(cfg) or 0.0)
            if exp < 0:
                continue
            out.append(cfg)
        return out

    def _apply_opt_lifecycle(self) -> list[str]:
        """Queue one never-searched WFO; enable stamped newcomers that clear the floor."""
        done: list[str] = []
        done.extend(self._lifecycle_enable())
        done.extend(self._lifecycle_queue_onboarding())
        return done

    def _lifecycle_queue_onboarding(self) -> list[str]:
        opt = self.optimizer
        if opt is None:
            return []
        if bool(getattr(opt, "busy", False)):
            return []
        cands = self._onboarding_candidates()
        if not cands:
            return []
        # Stable order: one symbol per tick.
        cands.sort(key=lambda c: str(c.symbol))
        sym = cands[0].symbol
        starter = getattr(opt, "start", None)
        if not callable(starter):
            return []
        started = starter([sym], apply_best=True, source="onboarding")
        if isinstance(started, dict) and not started.get("ok", True):
            err = started.get("error") or "red"
            return [f"onboarding {sym} WFO red: {err}"]
        return [f"onboarding {sym} WFO kuyruk"]

    def _lifecycle_enable(self) -> list[str]:
        done: list[str] = []
        for cfg in self._enable_candidates():
            hold = (getattr(cfg, "opt_summary", None) or {}).get("holdout") or {}
            net_r = float(hold.get("net_r") or 0.0)
            pr = float((getattr(cfg, "opt_summary", None) or {}).get(
                "positive_ratio") or 0.0)
            self.store.update_symbol(
                cfg.symbol, {"enabled": True}, source="autopilot onboarding")
            msg = (f"onboarding {cfg.symbol} acildi "
                   f"(hold {net_r:+.1f}R, pr {pr:.2f})")
            done.append(msg)
            LOG.emit(msg, "INFO", cfg.symbol)
        return done
