from __future__ import annotations

import math
import statistics
import time
from dataclasses import dataclass
from typing import Any

from .logbus import LOG
from .models import SymbolConfig, SystemConfig, is_scalp_strategy
from .mt5client import MT5Client
from .store import Store, as_number
from .supervisor import Supervisor


@dataclass
class Verdict:
    ok: bool
    reason: str = ""


# GER40 27.08: six original-SL deaths, later through_entry. Search still
# prefers 1.0. Last N autopsies of THIS symbol, not the book.
_SHAKEOUT_SL_WINDOW = 10
_SHAKEOUT_SL_DEATHS = 3
_SHAKEOUT_SL_FLOOR = 2.0


def shakeout_sl_atr_mult(base: float, symbol: str,
                         autopsies: list[dict[str, Any]] | None) -> float:
    """Hard-stop ATR multiple for the NEXT entry, not an open ticket.

    Counts original-SL losers in the last ``_SHAKEOUT_SL_WINDOW`` closes
    for ``symbol``. Trail / flatten / weekend do not count. A searched
    stop already at or above the floor is left alone.

    While the floor is live the next entry's hard stop may not match the
    searched trio: trail stays at the searched values. When the window
    cools, stored sl/trail are the scored set again — do not scale trail
    with the floor, and do not drop a pending trail because SL was floored.
    """
    try:
        floor_base = float(base or 0.0)
    except (TypeError, ValueError):
        floor_base = 0.0
    if floor_base <= 0:
        return floor_base
    mine = [row for row in (autopsies or [])
            if str((row or {}).get("symbol") or "") == symbol]
    window = mine[-_SHAKEOUT_SL_WINDOW:]
    deaths = 0
    for row in window:
        if str(row.get("exit_reason") or "") != "sl":
            continue
        try:
            realised = float(row.get("r_realised") or 0.0)
        except (TypeError, ValueError):
            continue
        if realised < 0:
            deaths += 1
    if deaths < _SHAKEOUT_SL_DEATHS:
        return floor_base
    return max(floor_base, _SHAKEOUT_SL_FLOOR)


def shakeout_size_note(lot: float, lot_note: str) -> str:
    """Dollar-risk side effect of a wider stop, from lot_for's answer.

    Free lot: risk$ stays. Min-lot pin: stop x2 with the same lot is
    risk x2. Skip: MAX_MIN_LOT_OVERSHOOT refused the trade.
    """
    if lot <= 0:
        return "islem atlandi"
    if "min lot" in lot_note and "riski asiyor" in lot_note:
        return "lot tabanda, gercek risk buyuyor"
    return "lot serbest, risk ayni"


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
        # The chip is meaningless without the login it was taken from. A
        # terminal that hops from a 2113 demo onto a 0.51 live account used
        # to treat the gap as a -99.98% trading day and persist the halt.
        self.start_login: int = int(as_number(
            store.get_setting("day_start_login"), 0.0, "day_start_login"))
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

    def observe_account(self, login: int, balance: float) -> bool:
        """Rebuild the chip when the terminal is on a different login.

        Returns True if the chip was replaced. Callers treat that like a
        rollover: per-symbol sticky halts belonged to the previous account.
        """
        login = int(login or 0)
        if login <= 0:
            return False
        current = int(getattr(self, "start_login", 0) or 0)
        if current == login:
            return False
        if float(balance) <= 0:
            return False
        old = current
        self.start_login = login
        self.start_balance = float(balance)
        self.halted = False
        self.halt_reason = ""
        self.loss_halted = False
        self.cash_flow = 0.0
        self._zero_balance_warned = False
        self.store.set_setting("day_start_login", self.start_login)
        self.store.set_setting("day_start_balance", self.start_balance)
        self.store.set_setting("day_halted", False)
        self.store.set_setting("day_halt_reason", "")
        self.store.set_setting("day_loss_halted", False)
        self.store.set_setting("day_cash_flow", 0.0)
        if old:
            LOG.emit(
                f"Gun cipasi hesap degisti ({old} -> {login}) | yeni bakiye "
                f"{balance:.2f} - fark zarar sayilmadi.",
                "WARN",
            )
        else:
            LOG.emit(
                f"Gun cipasi hesaba baglandi ({login}) | bakiye {balance:.2f}",
                "INFO",
            )
        return True

    def rollover(self, server_epoch: float, balance: float, login: int = 0) -> bool:
        rebound = self.observe_account(int(login or 0), float(balance))
        key = time.strftime("%Y-%m-%d", time.gmtime(server_epoch))
        if key == self.day_key and self.start_balance > 0:
            return rebound
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
        if login:
            self.start_login = int(login)
        self.store.set_setting("day_start_balance", self.start_balance)
        self.store.set_setting("day_start_login", int(getattr(self, "start_login", 0) or 0))
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

    def check(
        self,
        equity: float,
        sys_cfg: SystemConfig,
        login: int = 0,
        balance: float | None = None,
    ) -> Verdict:
        if login:
            chip = float(balance) if balance is not None else float(equity)
            self.observe_account(int(login or 0), chip)
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
        """Validated edge productivity: holdout net R per unit of holdout DD.

        Window length used to sit in the denominator (R per calendar day), so
        an M5 symbol whose bar cap filled ~92 days looked six times more
        productive than an M30 symbol with the same total R over ~610 days.
        Net R and max_dd_r are earned on the same slice, so the ratio does not
        care how long the cap happened to run. Unmeasurable input (no DD,
        non-positive DD, non-positive net R) and an unvalidated stamp
        (``validated is False``) return 0 so edge_scale stays the 1.0
        neutral — not EDGE_MIN.
        """
        summary = cfg.opt_summary or {}
        # Docstring says validated. GAP-5 wrote validated=false and a +93 R
        # holdout; size_by_edge still treated that as edge and sized NAS100
        # as a winner while live 30d ran PF 0.50.
        if getattr(cfg, "validated", None) is False:
            return 0.0
        if summary.get("validated") is False:
            return 0.0
        hold = summary.get("holdout") or {}
        net_r = float(hold.get("net_r", 0.0) or 0.0)
        max_dd = float(hold.get("max_dd_r", 0.0) or 0.0)
        if net_r > 0 and max_dd > 0:
            return net_r / max_dd
        return 0.0

    def edge_scale(self, cfg: SymbolConfig) -> float:
        """Size a symbol relative to how well its validated edge compares.

        Every enabled symbol carries holdout net R / holdout max DD, and those
        ratios differ by enough that equal risk spends as much on the weakest
        book member as on the strongest. The ratio is square-rooted because
        maxDD is a single-path statistic and does not deserve full leverage;
        EDGE_MIN/MAX (0.6/2.2) are the same clamp as before.
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

    def _margin_lot_ceiling(self, cfg: SymbolConfig, account: dict[str, Any] | None,
                            side: str, floor: float,
                            broker_ceiling: float) -> float | None:
        """Lots that still fit remaining margin. None = no extra cap.

        Same budget ``capacity`` uses for free_slots: leftover ``max_lot`` is
        unread, so the kasa (equity × max_margin_usage_pct, minus used,
        minus min_free_margin) is the live ceiling. One ticket per symbol;
        this is size, not a second hand. A missing or all-zero account
        picture must not size to zero (MT5 blip).
        """
        if not account:
            return None
        try:
            equity = float(account.get("equity", 0.0) or 0.0)
            free = float(account.get("margin_free", 0.0) or 0.0)
            used = float(account.get("margin", 0.0) or 0.0)
        except (TypeError, ValueError):
            return None
        if equity <= 0 and free <= 0:
            return None
        sys_cfg = self.store.system
        pct = float(sys_cfg.max_margin_usage_pct or 0.0)
        if equity > 0 and pct > 0:
            margin_budget = max(0.0, equity * pct / 100.0 - used)
        else:
            margin_budget = free
        budget = max(0.0, min(margin_budget, free - float(sys_cfg.min_free_margin or 0.0)))
        unit = floor if floor > 0 else 0.01
        try:
            need = float(self.client.margin_for(cfg.symbol, unit, side) or 0.0)
        except (TypeError, ValueError, AttributeError):
            return None
        if need <= 0:
            return None
        return min(broker_ceiling, unit * (budget / need))

    def lot_for(self, cfg: SymbolConfig, sl_distance: float, balance: float,
               ai_scale: float = 1.0, account: dict[str, Any] | None = None,
               side: str = "buy") -> tuple[float, str]:
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
        try:
            ceiling = float(info["volume_max"])
        except (TypeError, ValueError, KeyError):
            ceiling = 0.0
        if ceiling <= 0:
            ceiling = floor

        multiplier = max(0.1, float(self.store.system.lot_multiplier or 1.0))
        edge = self.edge_scale(cfg)
        multiplier *= edge
        multiplier *= max(0.0, float(ai_scale))

        # Account risk% only. Leftover lot_mode/fixed_lot/max_lot on the row
        # are unread: a constant lot cannot see the kasa, and a typed ceiling
        # used to clip the percent the operator still sets.
        if sl_distance <= 0:
            return 0.0, "lot sifir (stop yok), islem atlandi"
        raw, multiplier, note_edge_capped, money_per_unit = self._risk_raw_lot(
            cfg, sl_distance, balance, multiplier, edge)
        if money_per_unit <= 0:
            return 0.0, "tick degeri yok, islem atlandi (risk % hesaplanamadi)"
        note = f"risk %{cfg.risk_percent * multiplier:.3g} -> {raw:.3f}"
        if note_edge_capped:
            note += " (SL broker min'e yapisik, avantaj carpani kisildi)"
        if raw <= 0:
            # A zero risk% (or a zero balance on a fresh/blown account) means
            # "risk nothing", and max(floor, 0) would answer that with the
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
        auto = self._margin_lot_ceiling(cfg, account, side, floor, ceiling)
        if auto is not None:
            if auto + 1e-12 < floor:
                return 0.0, (f"lot sifir ({note}, marj tavani {auto:g} "
                             f"< min {floor:g}), islem atlandi")
            # Live book 28.08: four NAS 0.1 of the same pin. Spend the
            # skip-bound headroom on THIS ticket (account picture required
            # so a blip does not size up). Without account, keep the floor.
            if raw < floor:
                head = min(raw * self.MAX_MIN_LOT_OVERSHOOT, ceiling, auto)
                if head > lot + 1e-12:
                    lot = head
                    note += f" | taban {floor:g}->{lot:.3f}"
            if lot > auto:
                lot = auto
                note += f" | marj tavan {auto:.3f}"
        lot = min(lot, ceiling)
        try:
            sys_lot = float(getattr(self.store.system, "max_lot", 0.0) or 0.0)
        except (TypeError, ValueError):
            sys_lot = 0.0
        if sys_lot > 0:
            if sys_lot + 1e-12 < floor:
                return 0.0, (f"lot sifir ({note}, lot tavan {sys_lot:g} "
                             f"< min {floor:g}), islem atlandi")
            if lot > sys_lot:
                lot = sys_lot
                note += f" | lot tavan {sys_lot:g}"
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

    def lot_mode_diagnostics(self, balance: float,
                             autopsies: list[dict[str, Any]] | None = None
                             ) -> list[dict[str, Any]]:
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
            if not cfg.enabled:
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
            sl_mult = shakeout_sl_atr_mult(
                cfg.sl_atr_mult, cfg.symbol, autopsies)
            sl_distance = max(atr_now * max(sl_mult, 0.01),
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

    def risk_dollars(self, symbol: str, lot: float, sl_distance: float) -> float:
        """Account-currency value of 1R at this lot and stop distance.

        Shared by the dashboard row and the can_open gate so a trail that
        shortens the live stop and a new fill sized off ATR cannot disagree
        about what a dollar of risk is.
        """
        if lot <= 0 or sl_distance <= 0:
            return 0.0
        return sl_distance * self.client.money_per_price_unit(symbol, lot)

    def remaining_position_risk(self, pos: dict[str, Any]) -> float:
        """1R still at risk on an open ticket, from entry to the *current* SL.

        A trail pulled to entry (or into profit) is zero remaining risk and
        must free budget; counting the original stop would keep the gate
        conservative after the danger has already left.

        A missing stop is the opposite: remaining risk cannot be measured,
        and treating it as zero would free the concurrent-risk budget for a
        naked position. That is unbounded so the cap refuses.
        """
        sl = float(pos.get("sl") or 0.0)
        entry = float(pos.get("price_open") or 0.0)
        volume = float(pos.get("volume") or 0.0)
        if entry <= 0 or volume <= 0:
            return 0.0
        if sl <= 0:
            return float("inf")
        dist = (entry - sl) if pos.get("side") == "buy" else (sl - entry)
        if dist <= 0:
            return 0.0
        return self.risk_dollars(str(pos.get("symbol") or ""), volume, dist)

    # ------------------------------------------------------------- gatekeeping

    def can_open(self, cfg: SymbolConfig, side: str, lot: float,
                 positions: list[dict[str, Any]], account: dict[str, Any],
                 sl_distance: float = 0.0) -> Verdict:
        # Callers still pass sl_distance; leftover concurrent 1R unread.
        _ = sl_distance
        sys_cfg = self.store.system
        magics = {c.magic for c in list(self.store.symbols.values())}
        mine = [p for p in positions if p["magic"] in magics]
        if any(float(p.get("volume") or 0.0) > 0 and not float(p.get("sl") or 0.0)
               for p in mine):
            # Report-only STOPSUZ in manage_positions does not close the
            # ticket. Remaining risk used to return 0 for sl=0, so the
            # concurrent-risk cap treated a naked position as free budget.
            # Volume is required so a stub ticket (tests, a partial dict)
            # is not mistaken for a live unprotected fill.
            return Verdict(False, "stopsuz acik pozisyon")

        same_symbol = [p for p in mine if p["symbol"] == self.client.resolve(cfg.symbol)]
        if any(p["side"] != side for p in same_symbol):
            return Verdict(False, "ters yonde acik pozisyon var")
        if same_symbol:
            # Search scores max_open=1. Leftover symbol max_positions (5/10)
            # stays unread so a DB remnant cannot restack. The live cap is
            # SystemConfig.max_positions (panel, default 1).
            # Live cap is SystemConfig.max_positions (sys_cfg.max_positions).
            try:
                cap = int(getattr(sys_cfg, "max_positions", 1) or 1)
            except (TypeError, ValueError):
                cap = 1
            cap = max(1, cap)
            if len(same_symbol) >= cap:
                return Verdict(False, f"sembol pozisyon limiti ({cap})")

        # Leftover max_total_positions is unread. Another *name* may still
        # open until margin / STOPSUZ (and scalp/swing only when those
        # leftover caps are > 0).

        # Scalp and swing share margin but are a different bet shape -
        # many small M5 fills vs a few multi-hour holds - so a run of
        # one should not crowd the other out of remaining headroom.
        by_magic = {c.magic: c for c in list(self.store.symbols.values())}
        cap = sys_cfg.max_scalp_positions if is_scalp_strategy(cfg.strategy) else sys_cfg.max_swing_positions
        if cap > 0:
            bucket = sum(1 for p in mine
                         if (c := by_magic.get(p["magic"])) is not None
                         and is_scalp_strategy(c.strategy) == is_scalp_strategy(cfg.strategy))
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

        # Leftover max_concurrent_risk_pct is unread. Lot is risk% of
        # balance; same-symbol already blocked above.

        return Verdict(True)

    # ------------------------------------------------------------- dashboard

    def _configured_r_dollars(self, cfg: SymbolConfig, balance: float) -> float:
        """1R in account currency from the risk% setting, when ATR/lot is missing."""
        try:
            pct = float(getattr(cfg, "risk_percent", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if balance <= 0 or pct <= 0:
            return 0.0
        return balance * pct / 100.0 * float(self.edge_scale(cfg) or 1.0)

    def fill_holdout_projection(self, rows: list[dict[str, Any]],
                                balance: float) -> dict[str, Any]:
        """Paper holdout in dollars. Does not touch MT5.

        A slim stamp without ``expectancy`` still has net_r / days. A
        search-frozen row with risk_per_trade=0 still has risk_percent.
        """
        by_sym = {r.get("symbol"): r for r in rows if r.get("enabled")}
        projected_daily = 0.0
        projected_costed_daily = 0.0
        stamps: list[bool] = []
        projected_costed_negative = False
        sys_cfg = self.store.system
        for cfg in list(self.store.symbols.values()):
            if not getattr(cfg, "enabled", False):
                continue
            row = by_sym.get(cfg.symbol) or {}
            summary = cfg.opt_summary if isinstance(cfg.opt_summary, dict) else {}
            if "charge_costs" in summary:
                stamps.append(bool(summary.get("charge_costs")))
            if summary.get("costed_negative"):
                projected_costed_negative = True
            hold = summary.get("holdout") or {}
            try:
                days = float(summary.get("holdout_days", 0) or 0)
                net = float(hold.get("net_r") or 0.0)
            except (TypeError, ValueError):
                continue
            if days <= 0 or net == 0:
                continue
            try:
                risk = float(row.get("risk_per_trade") or 0.0)
            except (TypeError, ValueError):
                risk = 0.0
            if risk <= 0:
                risk = self._configured_r_dollars(cfg, balance)
            if risk <= 0:
                continue
            projected_daily += net * risk / days
            costed = summary.get("holdout_costed") or {}
            try:
                cnet = float(costed.get("net_r") or 0.0)
            except (TypeError, ValueError):
                cnet = 0.0
            projected_costed_daily += (cnet or net) * risk / days
        projected_charge_costs = all(stamps) if stamps else bool(
            getattr(sys_cfg, "charge_costs", True))
        monthly = projected_daily * 21.0
        costed_m = projected_costed_daily * 21.0
        return {
            "projected_daily": round(projected_daily, 2),
            "projected_monthly": round(monthly, 2),
            "projected_monthly_pct": round(monthly / balance * 100.0, 2)
            if balance > 0 else 0.0,
            "projected_charge_costs": projected_charge_costs,
            "projected_costed_daily": round(projected_costed_daily, 2),
            "projected_costed_monthly": round(costed_m, 2),
            "projected_costed_monthly_pct": round(costed_m / balance * 100.0, 2)
            if balance > 0 else 0.0,
            "projected_costed_negative": projected_costed_negative,
        }

    def capacity(self, positions: list[dict[str, Any]], account: dict[str, Any],
                 atr_by_symbol: dict[str, float] | None = None,
                 autopsies: list[dict[str, Any]] | None = None) -> dict[str, Any]:
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

        rows = []
        for cfg in list(self.store.symbols.values()):
            broker = self.client.resolve(cfg.symbol) or cfg.symbol
            open_now = [p for p in mine if p["symbol"] == broker]
            atr = float(atr_by_symbol.get(cfg.symbol, 0.0))
            # Route through the engine's own sizing so the table is the real number.
            sl_mult = shakeout_sl_atr_mult(
                cfg.sl_atr_mult, cfg.symbol, autopsies)
            sl_dist = max(atr * sl_mult, self.client.min_stop_distance(cfg.symbol)) \
                if atr > 0 else 0.0
            lot, lot_note = self.lot_for(cfg, sl_dist, balance, account=account)
            if sl_dist <= 0:
                lot_note = "risk (ATR bekleniyor)"
            elif sl_mult > float(cfg.sl_atr_mult or 0) + 1e-9:
                lot_note = f"risk (SL x{sl_mult:g} shakeout)"
            margin = self.client.margin_for(cfg.symbol, lot, "buy")
            by_margin = int(budget // margin) if margin > 0 else 0

            # What one unit of risk (1R) is worth in account currency at this lot.
            r_value = self.risk_dollars(cfg.symbol, lot, sl_dist)
            cost = cfg.commission_per_lot * lot
            tick = self.client.tick(cfg.symbol)
            if tick:
                cost += tick["spread"] * self.client.money_per_price_unit(cfg.symbol, lot)
            summary = cfg.opt_summary if isinstance(cfg.opt_summary, dict) else {}
            hold = summary.get("holdout") or {}
            expectancy_r = float(Supervisor.holdout_expectancy(cfg) or 0.0)
            # Long-run cost per trade in R, straight from the holdout slice.
            expectancy_cost = float(hold.get("cost_per_trade_r", 0.0) or 0.0)
            rows.append({
                "symbol": cfg.symbol,
                "broker_symbol": broker,
                "group": cfg.group,
                "enabled": cfg.enabled,
                "lot_note": lot_note,
                "lot": round(lot, 2),
                "risk_percent": cfg.risk_percent,
                "margin_per_trade": round(margin, 2),
                "open_positions": len(open_now),
                "free_slots": by_margin if cfg.enabled else 0,
                "open_profit": round(sum(p["profit"] + p["swap"] for p in open_now), 2),
                "risk_per_trade": round(r_value, 2),
                "risk_sizing": "risk %",
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

        # Project holdout net R onto dollars. A missing expectancy key is not
        # "no edge" (GAP-5 slim stamps); a zero risk_per_trade (search-frozen
        # ATR) is not "no size" — fall back to configured risk %.
        proj = self.fill_holdout_projection(rows, balance)
        projected_daily = proj["projected_daily"]
        projected_costed_daily = proj["projected_costed_daily"]
        projected_costed_negative = proj["projected_costed_negative"]
        projected_charge_costs = proj["projected_charge_costs"]

        total_risk = sum(r["risk_per_trade"] for r in rows if r["enabled"])
        multiplier = max(0.1, float(sys_cfg.lot_multiplier or 1.0))
        global_slots = max((r["free_slots"] for r in rows), default=0)

        # No ticket-count ceiling. Worst-case concurrent is every enabled
        # name firing at once (search still scores max_open=1).
        enabled_risks = [r["risk_per_trade"] for r in rows if r["enabled"]]
        enabled_margins = [r["margin_per_trade"] for r in rows if r["enabled"]]
        concurrent_risk = sum(enabled_risks)
        concurrent_margin = sum(enabled_margins)

        # How far size could scale before either the risk budget or margin runs out.
        # The risk budget is one full daily-loss allowance across all open trades.
        risk_budget = equity * max(0.5, sys_cfg.daily_loss_pct) / 100.0
        by_risk = risk_budget / concurrent_risk if concurrent_risk > 0 else 0.0
        margin_room = equity * sys_cfg.max_margin_usage_pct / 100.0
        by_margin_all = margin_room / concurrent_margin if concurrent_margin > 0 else 0.0
        headroom = max(0.0, min(by_risk, by_margin_all))

        # Live remaining 1R across the open book. Leftover
        # max_concurrent_risk_pct is unread; this is for STOPSUZ and the
        # panel, not a can_open ceiling. A naked stop is unbounded
        # (remaining_position_risk returns inf). json.dumps would write
        # Infinity and /api/state would 500 the whole panel - the same
        # class as execution's RATIO_ALL_ADVERSE.
        risks = [self.remaining_position_risk(p) for p in mine]
        unbounded = any(not math.isfinite(r) for r in risks)
        if unbounded:
            open_risk = None
            open_risk_pct = None
        else:
            open_risk = round(sum(risks), 2)
            open_risk_pct = (round(open_risk / equity * 100.0, 2)
                             if equity > 0 else 0.0)

        return {
            "rows": rows,
            "open_total": len(mine),
            "open_risk": open_risk,
            "open_risk_pct": open_risk_pct,
            "open_risk_unbounded": unbounded,
            "total_risk_per_trade": round(total_risk, 2),
            "total_risk_pct": round(total_risk / equity * 100.0, 2) if equity > 0 else 0.0,
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
            "projected_charge_costs": projected_charge_costs,
            "projected_costed_daily": round(projected_costed_daily, 2),
            "projected_costed_monthly": round(projected_costed_daily * 21.0, 2),
            "projected_costed_monthly_pct": round(
                projected_costed_daily * 21.0 / balance * 100.0, 2)
            if balance > 0 else 0.0,
            "projected_costed_negative": projected_costed_negative,
            # Leftover ticket-count ceiling. Unread by can_open; GET honesty.
            "max_total_positions": sys_cfg.max_total_positions,
            "max_cost_pct_of_risk": float(sys_cfg.max_cost_pct_of_risk or 0.0),
            "global_free_slots": global_slots,
            "margin_budget": round(budget, 2),
            "margin_usage_pct": round(used / equity * 100.0, 2) if equity > 0 else 0.0,
            "max_margin_usage_pct": sys_cfg.max_margin_usage_pct,
            "max_concurrent_risk_pct": float(
                getattr(sys_cfg, "max_concurrent_risk_pct", 0.0) or 0.0),
        }
