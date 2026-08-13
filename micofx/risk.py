from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from typing import Any

from .logbus import LOG
from .models import SymbolConfig, SystemConfig, is_scalp_strategy
from .mt5client import MT5Client
from .store import Store, as_number


@dataclass
class Verdict:
    ok: bool
    reason: str = ""


class DailyGuard:
    """Balance-anchored daily loss / profit circuit breaker.

    The anchor is persisted so restarting the app mid-session does not silently
    reset a breaker that already tripped.
    """

    def __init__(self, store: Store) -> None:
        self.store = store
        self.day_key: str = str(store.get_setting("day_key", ""))
        # Typed read: a non-numeric value here is valid JSON and raised
        # ValueError straight out of the constructor, which the engine builds
        # during its own __init__ - so a single bad row stopped the app
        # starting rather than degrading anything.
        self.start_balance: float = as_number(store.get_setting("day_start_balance"), 0.0, "day_start_balance")
        self.halted: bool = bool(store.get_setting("day_halted", False))
        self.halt_reason: str = str(store.get_setting("day_halt_reason", ""))
        # Distinguishes *why* halted is True - a profit-target halt should
        # never trigger the loss-side flatten below, and unlike re-deriving
        # that from a live pnl_pct check every cycle (which flaps False the
        # instant floating P/L on some other position bounces equity back
        # above the threshold, even though the day is still halted), this is
        # set once at the moment the loss halt actually fires and stays put
        # until rollover/resume - the same persistence guarantee ``halted``
        # itself already has.
        self.loss_halted: bool = bool(store.get_setting("day_loss_halted", False))
        # Deliberately not persisted: it only throttles the log line below to
        # once per episode, and a restart re-reporting a still-zero balance is
        # useful rather than noise.
        self._zero_balance_warned: bool = False
        # Net external cash movement (deposit/withdrawal/credit/correction)
        # booked since the day's anchor. Subtracted from equity in pnl_pct()
        # so the breaker measures TRADING result, not the operator funding
        # the account. Persisted for the same reason the anchor itself is: a
        # restart must not hand check() an uncorrected equity for the cycles
        # before the first successful history read lands.
        self.cash_flow: float = as_number(store.get_setting("day_cash_flow"), 0.0, "day_cash_flow")

    def rollover(self, server_epoch: float, balance: float) -> bool:
        key = time.strftime("%Y-%m-%d", time.localtime(server_epoch))
        if key == self.day_key and self.start_balance > 0:
            return False
        if balance <= 0:
            # Nothing to anchor against, so refuse the rollover rather than
            # anchor at zero. Anchoring at zero re-armed this same branch on
            # every following cycle (the guard above needs start_balance > 0
            # to say "already rolled over"), and each of those repeats cleared
            # ``halted``/``loss_halted`` - and, via Engine._handle_daily_
            # rollover's return value, wiped every per-symbol sticky halt too.
            # pnl_pct() also returns a flat 0.0 while start_balance <= 0, so
            # check() could never re-trip: the daily loss breaker was off for
            # the rest of the session. Holding the previous day's anchor and
            # halt state is the fail-closed answer; a real balance arriving on
            # any later cycle anchors normally.
            if not self._zero_balance_warned:
                self._zero_balance_warned = True
                LOG.emit(f"Bakiye {balance:.2f} - gun baslangici sabitlenemedi, "
                         f"gunluk limitler onceki durumda tutuluyor.", "WARN")
            return False
        self._zero_balance_warned = False
        self.day_key = key
        self.start_balance = float(balance)
        self.halted = False
        self.halt_reason = ""
        self.loss_halted = False
        # New anchor, so yesterday's cash flow is no longer relative to it.
        self.cash_flow = 0.0
        self.store.set_setting("day_cash_flow", 0.0)
        self.store.set_setting("day_key", key)
        self.store.set_setting("day_start_balance", self.start_balance)
        self.store.set_setting("day_halted", False)
        self.store.set_setting("day_halt_reason", "")
        self.store.set_setting("day_loss_halted", False)
        LOG.emit(f"Yeni islem gunu {key} | baslangic bakiye {balance:.2f}", "INFO")
        return True

    def _halt(self, reason: str, loss: bool = False) -> None:
        if not self.halted:
            LOG.emit(reason, "WARN")
        self.halted = True
        self.halt_reason = reason
        self.store.set_setting("day_halted", True)
        self.store.set_setting("day_halt_reason", reason)
        if loss:
            self.loss_halted = True
            self.store.set_setting("day_loss_halted", True)

    def resume(self) -> None:
        self.halted = False
        self.halt_reason = ""
        self.loss_halted = False
        self.store.set_setting("day_halted", False)
        self.store.set_setting("day_halt_reason", "")
        self.store.set_setting("day_loss_halted", False)

    def set_cash_flow(self, amount: float | None) -> None:
        """Record external cash movement since the anchor.

        ``None`` means the read failed (disconnect) - hold the last known
        value rather than reverting to 0.0, which would re-disarm the breaker
        by exactly the amount that was deposited.
        """
        if amount is None:
            return
        amount = float(amount)
        if amount == self.cash_flow:
            return
        self.cash_flow = amount
        self.store.set_setting("day_cash_flow", amount)
        LOG.emit(f"Gun ici hesap hareketi (yatirim/cekim) {amount:+.2f} - "
                 f"gunluk limit bunu kâr saymayacak.", "INFO")

    def pnl_pct(self, equity: float) -> float:
        if self.start_balance <= 0:
            return 0.0
        # equity - cash_flow: a deposit raises equity without any trade
        # producing it, so counting it as profit let the daily loss breaker
        # sit green through a losing day (and, via Supervisor.review, skipped
        # the drawdown lot damper too).
        return (equity - self.cash_flow - self.start_balance) / self.start_balance * 100.0

    def check(self, equity: float, sys_cfg: SystemConfig) -> Verdict:
        if self.halted:
            return Verdict(False, self.halt_reason or "gunluk limit")
        pct = self.pnl_pct(equity)
        if sys_cfg.daily_loss_pct > 0 and pct <= -abs(sys_cfg.daily_loss_pct):
            self._halt(f"Gunluk zarar limiti asildi ({pct:.2f}%). Yeni islem yok.", loss=True)
            return Verdict(False, self.halt_reason)
        if sys_cfg.daily_profit_pct > 0 and pct >= abs(sys_cfg.daily_profit_pct):
            self._halt(f"Gunluk kar hedefi tamamlandi (+{pct:.2f}%). Yeni islem yok.")
            return Verdict(False, self.halt_reason)
        return Verdict(True)


class RiskManager:
    # How far edge weighting may push a single symbol away from the pack.
    # Ceiling raised 1.8->2.2 on request: proven symbols (XAUUSD etc.) get
    # more headroom to size up; the floor stays put so an unproven/decaying
    # symbol doesn't get pulled up with it. Was drifting at 3.0, out of sync
    # with this comment and every doc (README/KULLANIM/MASTER_PROMPT all say
    # 1.80-2.2) - restored to the documented, intentional value.
    EDGE_MIN, EDGE_MAX = 0.6, 2.2
    # Broker minimum lot may force more risk than configured; beyond this
    # multiple of the intended risk the trade is skipped instead of oversized.
    # Tightened back from 10.0x: margin usage (system.max_margin_usage_pct) is
    # a position-count/exposure check, not a per-trade one - it does not catch
    # a single trade quietly running at, say, 8x its configured risk% because
    # the broker's floor forced the lot up. 3.0x still tolerates ordinary
    # broker-granularity rounding (the common case this guard has to let
    # through) while refusing anything that no longer resembles the
    # configured risk at all.
    MAX_MIN_LOT_OVERSHOOT = 3.0

    def __init__(self, store: Store, client: MT5Client) -> None:
        self.store = store
        self.client = client
        self.daily = DailyGuard(store)

    # ------------------------------------------------------------- lot sizing

    @staticmethod
    def _edge_metric(cfg: SymbolConfig) -> float:
        """Validated edge productivity of one symbol, in R per calendar day.

        Per-trade expectancy alone is the wrong yardstick for splitting a shared
        risk budget: a symbol that earns 0.045R six times a day contributes as
        much as one earning 0.35R once a day, yet the per-trade view sizes the
        first at the floor and the second near the ceiling. Holdout net R over
        the holdout window measures what the symbol actually produces per day of
        exposure, which is the quantity the portfolio is buying with its risk.
        Falls back to per-trade expectancy when the window length is unknown.
        """
        summary = cfg.opt_summary or {}
        hold = summary.get("holdout") or {}
        days = float(summary.get("holdout_days", 0.0) or 0.0)
        net_r = float(hold.get("net_r", 0.0) or 0.0)
        if days > 0 and net_r > 0:
            return net_r / days
        return float(hold.get("expectancy", 0.0) or 0.0)

    def edge_scale(self, cfg: SymbolConfig) -> float:
        """Size a symbol relative to how well its validated edge compares.

        Every symbol carries the daily R rate its own held-out slice produced,
        and those numbers differ by an order of magnitude. Splitting risk equally
        therefore spends as much on the weakest instrument as on the strongest.
        The ratio is square-rooted because an edge measured over a few dozen
        trades is a noisy estimate and does not deserve full leverage.
        """
        if not self.store.system.size_by_edge:
            return 1.0
        edges: dict[str, float] = {}
        for c in list(self.store.symbols.values()):
            if not c.enabled:
                continue
            value = self._edge_metric(c)
            if value > 0:
                edges[c.symbol] = value
        mine = edges.get(cfg.symbol, 0.0)
        if mine <= 0 or len(edges) < 3:
            return 1.0
        reference = statistics.median(edges.values())
        if reference <= 0:
            return 1.0
        return max(self.EDGE_MIN, min(self.EDGE_MAX, (mine / reference) ** 0.5))

    def lot_for(self, cfg: SymbolConfig, sl_distance: float, balance: float,
               ai_scale: float = 1.0) -> tuple[float, str]:
        """Resolve the order volume, returning (lot, explanation).

        ``ai_scale`` (the supervisor's watch/hour/drawdown throttle) has to be
        folded in here, before the broker-minimum floor below, not multiplied
        onto the result afterwards - once ``raw`` has already been rounded up
        to the broker's minimum lot, multiplying that floor by a scale <1 and
        re-normalising just rounds straight back up to the same floor, so the
        throttle silently did nothing on any symbol already sitting at its
        minimum (which is most of this portfolio's indices on a small
        account). Applying it pre-floor lets a strong scale-down actually
        shrink the lot, or - via the same overshoot guard everything else
        goes through - skip the trade rather than pretend to have sized it
        down.
        """
        info = self.client.info(cfg.symbol)
        if not info:
            return 0.0, "sembol bilgisi yok"

        floor = float(info["volume_min"])
        ceiling = min(float(info["volume_max"]), max(floor, float(cfg.max_lot)))

        multiplier = max(0.1, float(self.store.system.lot_multiplier or 1.0))
        edge = self.edge_scale(cfg)
        multiplier *= edge
        multiplier *= max(0.0, float(ai_scale))

        if cfg.lot_mode == "fixed" or sl_distance <= 0:
            raw = float(cfg.fixed_lot) * multiplier
            note = "sabit" if multiplier == 1.0 else f"sabit x{multiplier:.2f}"
            if raw <= 0:
                # Nothing below can express "size zero": every branch from here
                # divides by ``raw`` to report the overshoot, and max(floor, 0)
                # would hand back the broker's minimum lot - the largest
                # position this function can produce - as the answer to a
                # config that asked for none at all. Fail closed instead. The
                # API refuses fixed_lot <= 0 and every ai_scale of 0 blocks the
                # entry before this call, so this is the backstop for a value
                # that reached the DB some other way (hand-edited row, restored
                # backup), not a path in normal use.
                return 0.0, f"lot sifir ({note}), islem atlandi"
            if raw < floor:
                # Same floor-vs-overshoot guard as the risk branch below - a
                # fixed lot scaled down by the AI throttle silently got
                # rounded straight back up to the floor otherwise, exactly
                # negating a "size 3x down" decision on any symbol whose
                # fixed_lot already sits at or near the broker's minimum.
                if floor > raw * self.MAX_MIN_LOT_OVERSHOOT:
                    return 0.0, (f"min lot {floor:g} sabit lotu {floor / raw:.1f}x asiyor, "
                                  f"islem atlandi ({note})")
                note += f" (min lot {floor:g} sabit lotu asiyor, {floor / raw:.1f}x)"
            lot = max(floor, raw)
        else:
            raw, multiplier, note_edge_capped, money_per_unit = self._risk_raw_lot(
                cfg, sl_distance, balance, multiplier, edge)
            if money_per_unit <= 0:
                # Fail closed, not "size off fixed_lot instead": that fallback
                # skipped max_lot, edge/AI scaling and the overshoot guard
                # entirely - a missing tick value silently produced a trade
                # with none of this function's other safety checks applied.
                return 0.0, "tick degeri yok, islem atlandi (risk % hesaplanamadi)"
            note = f"risk %{cfg.risk_percent * multiplier:.3g} -> {raw:.3f}"
            if note_edge_capped:
                note += " (SL broker min'e yapisik, avantaj carpani kisildi)"
            if raw <= 0:
                # Same fail-closed backstop as the fixed branch: a zero risk%
                # (or a zero balance on a fresh/blown account) means "risk
                # nothing", and max(floor, 0) would answer that with the
                # broker's minimum lot rather than no trade.
                return 0.0, f"lot sifir ({note}), islem atlandi"
            if raw < floor:
                # Rounding up to the broker's minimum lot silently inflates the
                # real risk taken - a raw of 0.024 forced to a 0.1 floor trades
                # at ~4x the intended risk, not the configured 0.5%. A small
                # overshoot is an unavoidable broker-granularity rounding and
                # still worth taking; past MAX_MIN_LOT_OVERSHOOT the position no
                # longer represents the configured risk at all, so the trade is
                # skipped rather than silently oversized.
                if floor > raw * self.MAX_MIN_LOT_OVERSHOOT:
                    return 0.0, (f"min lot {floor:g} riski {floor / raw:.1f}x asiyor, "
                                  f"islem atlandi ({note})")
                note += f" (min lot {floor:g} riski asiyor, {floor / raw:.1f}x)"
            lot = max(floor, raw)

        if edge != 1.0:
            note += f" | avantaj x{edge:.2f}"
        if ai_scale != 1.0:
            note += f" | AI x{ai_scale:.2f}"
        lot = min(lot, ceiling)
        return self.client.normalize_volume(cfg.symbol, lot), note

    def _risk_raw_lot(self, cfg: SymbolConfig, sl_distance: float, balance: float,
                      multiplier: float, edge: float) -> tuple[float, float, bool, float]:
        """Pre-floor, pre-ceiling lot for a risk-mode symbol.

        Extracted so ``lot_for`` and ``lot_mode_diagnostics`` cannot answer the
        same question differently. The diagnostic carried its own copy of this
        arithmetic - deliberately, to avoid parsing lot_for's free-form note -
        and the copy had drifted in three ways, every one of them understating
        the overshoot it exists to warn about, and worst on exactly the symbols
        where the warning matters most.

        Returns ``(raw, multiplier, edge_capped, money_per_unit)``;
        ``money_per_unit <= 0`` means the symbol has no usable tick value and
        ``raw`` is meaningless.
        """
        money_per_unit = self.client.money_per_price_unit(cfg.symbol, 1.0)
        if money_per_unit <= 0 or sl_distance <= 0:
            return 0.0, multiplier, False, money_per_unit
        # When the broker's own minimum stop distance is what is actually
        # pinning the SL (not the strategy's ATR multiple), the position is
        # already as tight as this symbol allows - a strong edge_scale on top
        # of that stacks two amplifiers (bigger lot from the tight SL, then
        # bigger again from edge) that were never validated together. Clamped
        # to 1.0 rather than dropped, so the risk% itself still applies
        # normally - only the edge multiplier's extra push is held back.
        min_stop = self.client.min_stop_distance(cfg.symbol)
        edge_capped = min_stop > 0 and sl_distance <= min_stop * 1.05 and edge > 1.0
        if edge_capped:
            multiplier /= edge
        risk_money = balance * float(cfg.risk_percent) / 100.0 * multiplier
        return risk_money / (sl_distance * money_per_unit), multiplier, edge_capped, money_per_unit

    def lot_mode_diagnostics(self, balance: float) -> list[dict[str, Any]]:
        """Flag risk-mode symbols whose broker min lot chronically overshoots
        their configured risk%, run against a fresh ATR read so the panel can
        warn before it happens on a real order.

        Shares ``_risk_raw_lot`` with ``lot_for`` rather than restating it. The
        restated copy that used to live here had drifted on all three counts
        that separate a preview from an order - no broker minimum-stop floor on
        the distance, no edge cap when the stop is pinned to that minimum - and
        both errors ran the same way, reporting less overshoot than the order
        would take, worst on precisely the symbols where the stop IS pinned and
        the warning matters.
        """
        from . import indicators as ind

        rows: list[dict[str, Any]] = []
        for cfg in list(self.store.symbols.values()):
            if not cfg.enabled or cfg.lot_mode != "risk":
                continue
            info = self.client.info(cfg.symbol)
            if not info:
                continue
            bars = self.client.bars(cfg.symbol, cfg.timeframe, max(cfg.atr_period + 5, 30))
            if bars is None or len(bars.close) <= cfg.atr_period:
                continue
            atr_series = ind.atr(bars.high, bars.low, bars.close, cfg.atr_period)
            atr_now = float(atr_series[-1]) if len(atr_series) else 0.0
            if atr_now <= 0:
                continue
            # _try_entry hands lot_for ``max(atr * sl_atr_mult, min_stop)``.
            # Without that floor the preview divides by a stop the broker would
            # not accept, so raw comes out larger and the overshoot smaller
            # than the order will actually take.
            sl_distance = max(atr_now * max(cfg.sl_atr_mult, 0.01),
                              self.client.min_stop_distance(cfg.symbol))
            floor = float(info["volume_min"])
            edge = self.edge_scale(cfg)
            multiplier = max(0.1, float(self.store.system.lot_multiplier or 1.0)) * edge
            raw, multiplier, edge_capped, money_per_unit = self._risk_raw_lot(
                cfg, sl_distance, balance, multiplier, edge)
            if money_per_unit <= 0:
                continue
            overshoot = (floor / raw) if raw > 0 else 0.0
            rows.append({
                "symbol": cfg.symbol, "floor": floor, "raw_lot": round(raw, 4),
                "overshoot": round(overshoot, 2), "flagged": overshoot >= 2.0,
                # Says the preview held the edge multiplier back the way a real
                # order would, rather than leaving the reader to wonder why the
                # number moved.
                "edge_capped": edge_capped,
            })
        rows.sort(key=lambda r: -r["overshoot"])
        return rows

    # ------------------------------------------------------------- gatekeeping

    def can_open(self, cfg: SymbolConfig, side: str, lot: float,
                 positions: list[dict[str, Any]], account: dict[str, Any],
                 sec_tickets: frozenset[int] = frozenset()) -> Verdict:
        sys_cfg = self.store.system
        magics = {c.magic for c in list(self.store.symbols.values())}
        mine = [p for p in positions if p["magic"] in magics]

        same_symbol = [p for p in mine if p["symbol"] == self.client.resolve(cfg.symbol)]
        if len(same_symbol) >= cfg.max_positions:
            return Verdict(False, f"sembol pozisyon limiti ({cfg.max_positions})")
        if any(p["side"] != side for p in same_symbol):
            return Verdict(False, "ters yonde acik pozisyon var")

        if len(mine) >= sys_cfg.max_total_positions:
            return Verdict(False, f"toplam pozisyon limiti ({sys_cfg.max_total_positions})")

        # Scalp and swing share the total budget above but are a different bet
        # shape - many small M5 fills vs a few multi-hour holds - so a run of
        # one should not crowd the other out of every remaining slot.
        by_magic = {c.magic: c for c in list(self.store.symbols.values())}
        cap = sys_cfg.max_scalp_positions if is_scalp_strategy(cfg.strategy) else sys_cfg.max_swing_positions
        if cap > 0:
            def _bucket_strategy(p: dict[str, Any], c: SymbolConfig) -> str:
                # store.symbols only ever holds the PRIMARY config; a position
                # actually opened off the secondary signal shares the same
                # magic, so by_magic alone always classified it as primary's
                # family - letting a scalp secondary silently eat the swing
                # bucket (or vice versa) instead of its own.
                if p["ticket"] in sec_tickets and c.secondary_strategy:
                    return c.secondary_strategy
                return c.strategy

            bucket = sum(1 for p in mine
                         if (c := by_magic.get(p["magic"])) is not None
                         and is_scalp_strategy(_bucket_strategy(p, c)) == is_scalp_strategy(cfg.strategy))
            if bucket >= cap:
                kind = "scalp" if is_scalp_strategy(cfg.strategy) else "swing"
                return Verdict(False, f"{kind} pozisyon limiti ({cap})")

        equity = float(account.get("equity", 0.0))
        free = float(account.get("margin_free", 0.0))
        used = float(account.get("margin", 0.0))
        need = self.client.margin_for(cfg.symbol, lot, side)

        if need <= 0:
            return Verdict(False, "marj hesaplanamadi")
        if free - need < sys_cfg.min_free_margin:
            return Verdict(False, f"serbest marj yetersiz ({free:.0f} < {need:.0f}+{sys_cfg.min_free_margin:.0f})")
        if equity > 0 and sys_cfg.max_margin_usage_pct > 0:
            projected = (used + need) / equity * 100.0
            if projected > sys_cfg.max_margin_usage_pct:
                return Verdict(False, f"marj kullanimi limiti (%{projected:.1f} > %{sys_cfg.max_margin_usage_pct:g})")

        return Verdict(True)

    # ------------------------------------------------------------- dashboard

    def capacity(self, positions: list[dict[str, Any]], account: dict[str, Any],
                 atr_by_symbol: dict[str, float] | None = None) -> dict[str, Any]:
        """Per-symbol and account-level 'how many more can I open, at what lot'."""
        sys_cfg = self.store.system
        magics = {c.magic for c in list(self.store.symbols.values())}
        mine = [p for p in positions if p["magic"] in magics]
        equity = float(account.get("equity", 0.0))
        balance = float(account.get("balance", 0.0))
        free = float(account.get("margin_free", 0.0))
        used = float(account.get("margin", 0.0))
        atr_by_symbol = atr_by_symbol or {}

        margin_budget = max(0.0, equity * sys_cfg.max_margin_usage_pct / 100.0 - used) \
            if (equity > 0 and sys_cfg.max_margin_usage_pct > 0) else free
        budget = max(0.0, min(margin_budget, free - sys_cfg.min_free_margin))
        global_slots = max(0, sys_cfg.max_total_positions - len(mine))

        rows = []
        for cfg in list(self.store.symbols.values()):
            broker = self.client.resolve(cfg.symbol) or cfg.symbol
            open_now = [p for p in mine if p["symbol"] == broker]
            atr = float(atr_by_symbol.get(cfg.symbol, 0.0))
            # Route through the engine's own sizing so the table is the real number.
            sl_dist = max(atr * cfg.sl_atr_mult, self.client.min_stop_distance(cfg.symbol)) \
                if atr > 0 else 0.0
            lot, lot_note = self.lot_for(cfg, sl_dist, balance)
            if cfg.lot_mode == "risk" and sl_dist <= 0:
                lot_note = "risk (ATR bekleniyor)"
            margin = self.client.margin_for(cfg.symbol, lot, "buy")
            by_margin = int(budget // margin) if margin > 0 else 0
            symbol_slots = max(0, cfg.max_positions - len(open_now))

            # What one unit of risk (1R) is worth in account currency at this lot.
            r_value = sl_dist * self.client.money_per_price_unit(cfg.symbol, lot)
            cost = cfg.commission_per_lot * lot
            tick = self.client.tick(cfg.symbol)
            if tick:
                cost += tick["spread"] * self.client.money_per_price_unit(cfg.symbol, lot)
            summary = cfg.opt_summary if isinstance(cfg.opt_summary, dict) else {}
            hold = summary.get("holdout") or {}
            expectancy_r = float(hold.get("expectancy", 0.0) or 0.0)
            # Long-run cost per trade in R, straight from the holdout slice.
            expectancy_cost = float(hold.get("cost_per_trade_r", 0.0) or 0.0)
            rows.append({
                "symbol": cfg.symbol,
                "broker_symbol": broker,
                "group": cfg.group,
                "enabled": cfg.enabled,
                "lot_mode": cfg.lot_mode,
                "lot_note": lot_note,
                "lot": round(lot, 2),
                "max_lot": cfg.max_lot,
                "risk_percent": cfg.risk_percent,
                "margin_per_trade": round(margin, 2),
                "open_positions": len(open_now),
                "max_positions": cfg.max_positions,
                "free_slots": min(symbol_slots, global_slots, by_margin) if cfg.enabled else 0,
                "slots_by_margin": by_margin,
                "open_volume": round(sum(p["volume"] for p in open_now), 2),
                "open_profit": round(sum(p["profit"] + p["swap"] for p in open_now), 2),
                "risk_per_trade": round(r_value, 2),
                "cost_per_trade": round(cost, 2),
                "cost_pct_of_risk": round(cost / r_value * 100.0, 1) if r_value > 0 else 0.0,
                # What the walk-forward measured this config costing per trade,
                # averaged over its whole holdout window. ``cost_pct_of_risk``
                # above is a single live tick, and a live tick taken during the
                # broker rollover reads 10-19x the long-run number on FX - wide
                # enough to make a perfectly healthy symbol look structurally
                # unprofitable. Shipping the two side by side is the difference
                # between "expensive right now" and "expensive always"; without
                # it the panel invites exactly the wrong conclusion, which is
                # not hypothetical - it produced one.
                "cost_pct_typical": round(expectancy_cost * 100.0, 1) if expectancy_cost > 0 else 0.0,
                "cost_inflation": round(
                    (cost / r_value) / expectancy_cost, 1)
                if (r_value > 0 and expectancy_cost > 0) else 0.0,
                "expectancy_r": round(expectancy_r, 3),
                "expected_per_trade": round(expectancy_r * r_value, 3),
                "edge_scale": round(self.edge_scale(cfg), 2),
            })

        # Project the validated backtest expectancy onto real money at the live lots.
        active = [r for r in rows if r["enabled"] and r["expectancy_r"] != 0]
        projected_daily = 0.0
        for cfg in list(self.store.symbols.values()):
            row = next((r for r in active if r["symbol"] == cfg.symbol), None)
            if row is None:
                continue
            summary = cfg.opt_summary if isinstance(cfg.opt_summary, dict) else {}
            hold = summary.get("holdout") or {}
            days = float(summary.get("holdout_days", 0) or 0)
            if days > 0 and hold.get("net_r"):
                projected_daily += float(hold["net_r"]) * row["risk_per_trade"] / days

        total_risk = sum(r["risk_per_trade"] for r in rows if r["enabled"])
        total_margin = sum(r["margin_per_trade"] for r in rows if r["enabled"])
        multiplier = max(0.1, float(sys_cfg.lot_multiplier or 1.0))

        # `can_open` hard-caps how many bot positions may exist at once, so the
        # true worst case is the N largest risks, not every enabled symbol at
        # once. Summing all of them understates headroom whenever the position
        # cap is tighter than the portfolio.
        slot_cap = max(1, int(sys_cfg.max_total_positions or 1))
        enabled_risks = sorted((r["risk_per_trade"] for r in rows if r["enabled"]), reverse=True)
        enabled_margins = sorted((r["margin_per_trade"] for r in rows if r["enabled"]), reverse=True)
        concurrent_risk = sum(enabled_risks[:slot_cap])
        concurrent_margin = sum(enabled_margins[:slot_cap])

        # How far size could scale before either the risk budget or margin runs out.
        # The risk budget is one full daily-loss allowance across all open trades.
        risk_budget = equity * max(0.5, sys_cfg.daily_loss_pct) / 100.0
        by_risk = risk_budget / concurrent_risk if concurrent_risk > 0 else 0.0
        margin_room = equity * sys_cfg.max_margin_usage_pct / 100.0
        by_margin_all = margin_room / concurrent_margin if concurrent_margin > 0 else 0.0
        headroom = max(0.0, min(by_risk, by_margin_all))

        return {
            "rows": rows,
            "open_total": len(mine),
            "total_risk_per_trade": round(total_risk, 2),
            "total_risk_pct": round(total_risk / equity * 100.0, 2) if equity > 0 else 0.0,
            "total_margin_if_all_open": round(total_margin, 2),
            "concurrent_risk": round(concurrent_risk, 2),
            "concurrent_risk_pct": round(concurrent_risk / equity * 100.0, 2) if equity > 0 else 0.0,
            "concurrent_margin": round(concurrent_margin, 2),
            "lot_multiplier": multiplier,
            "size_by_edge": bool(sys_cfg.size_by_edge),
            "safe_multiplier": round(headroom * multiplier, 2),
            "projected_daily": round(projected_daily, 2),
            "projected_monthly": round(projected_daily * 21.0, 2),
            "projected_monthly_pct": round(projected_daily * 21.0 / balance * 100.0, 2)
            if balance > 0 else 0.0,
            "max_total_positions": sys_cfg.max_total_positions,
            "global_free_slots": global_slots,
            "margin_used": round(used, 2),
            "margin_budget": round(budget, 2),
            "margin_usage_pct": round(used / equity * 100.0, 2) if equity > 0 else 0.0,
            "max_margin_usage_pct": sys_cfg.max_margin_usage_pct,
        }
