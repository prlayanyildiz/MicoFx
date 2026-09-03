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

from .logbus import LOG
from .supervisor import Supervisor

_SPREAD_AUTO_MIN = 10
_ENTRY_BLOCKS_MAX_AGE_SEC = 7 * 86400
_ROOT = Path(__file__).resolve().parents[1]
# Holdout net R floor before autopilot flips enabled on a stamped newcomer.
ENABLE_MIN_HOLD_NET_R = 20.0
_OPERATOR_DISABLED_KEY = "operator_disabled_symbols"


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
        agg = by_sym.setdefault(sym, {"signals": 0, "opened": 0, "blocks": {}})
        agg["signals"] += int(row.get("signals") or 0)
        agg["opened"] += int(row.get("opened") or 0)
        for k, v in (row.get("blocks") or {}).items():
            agg["blocks"][str(k)] = agg["blocks"].get(str(k), 0) + int(v)
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
        spread_n = int(blocks.get("spread") or 0)
        signals = int(row.get("signals") or 0)
        fill = float(row.get("fill_rate") or 0.0)
        if spread_n < _SPREAD_AUTO_MIN or signals < 5:
            continue
        top = max(blocks.values()) if blocks else 0
        if spread_n >= top and fill < 0.35:
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
        self._gate = threading.Lock()

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
        sys = self.store.system
        if not bool(getattr(sys, "autopilot_enabled", True)):
            return ["autopilot kapali"]

        done.extend(self._apply_safe_fixes())
        done.extend(self._apply_trust_ai())
        done.extend(self._apply_kasa())
        # Spread before cost_free: turning charge_costs off would skip widen.
        done.extend(self._apply_spread())
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
        enabled = list(self._enabled_symbols().values())
        if not enabled:
            return []
        all_zero = all(
            float(getattr(c, "commission_per_lot", 0) or 0) <= 0 for c in enabled)
        if not all_zero:
            return []
        sys = self.store.system
        already = (
            not bool(getattr(sys, "charge_costs", True))
            and not bool(getattr(sys, "block_high_cost", True))
            and float(getattr(sys, "max_cost_pct_of_risk", 0) or 0) <= 0
        )
        if already:
            return []
        self.store.update_system({
            "charge_costs": False,
            "block_high_cost": False,
            "max_cost_pct_of_risk": 0.0,
        }, source="autopilot")
        return ["cost_free: charge_costs=false (komisyon 0)"]

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
