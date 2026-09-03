from __future__ import annotations

import math
import statistics
import time
from dataclasses import dataclass
from typing import Any

from .kasa_sizing import NOTIONAL_MARGIN_SOFT_PCT, compute_kasa_targets
from .logbus import LOG
from .models import SymbolConfig, SystemConfig, is_scalp_strategy
from .mt5client import MT5Client, live_stop_level
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
# F8: widen by 1.5× the searched stop, never past the absolute floor, and
# never pull a wider searched stop inward.
_SHAKEOUT_SL_REL = 1.5

# Soft-restart / tiny original_sl stamped NAS flatten at r≈−195. Cash is
# truth; |R| past this is not a trade outcome (F FLAG1 / autopsy stats).
AUTOPSY_R_ABS_MAX = 20.0

# Panel projection only. A 36-day GER40 stamp was 51% of a +$379/mo chip
# while the rest of the book used 280-555 day windows (Claude 03.09). Floor
# the divisor so a short slice cannot annualise a lucky month.
MIN_PROJ_DAYS = 90.0
# Headline chip turns "optimistic" when monthly % of balance exceeds this.
_PROJ_PLAUSIBLE_MONTHLY_PCT = 40.0


def autopsy_r_usable(row: dict[str, Any] | None) -> bool:
    """False when r_realised is an absurd denominator artifact."""
    if not row:
        return True
    raw = row.get("r_realised")
    if raw is None:
        return True
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return True
    if not math.isfinite(value):
        return True
    return abs(value) <= AUTOPSY_R_ABS_MAX


def sanitize_autopsy_r(row: dict[str, Any]) -> dict[str, Any]:
    """Null absurd R; keep cash. Input is not mutated."""
    if autopsy_r_usable(row):
        return row
    out = dict(row)
    out["r_realised"] = None
    out["r_outlier"] = True
    return out


def shakeout_sl_atr_mult(base: float, symbol: str,
                         autopsies: list[dict[str, Any]] | None,
                         since_ts: float = 0.0) -> float:
    """Hard-stop ATR multiple for the NEXT entry, not an open ticket.

    Counts original-SL losers in the last ``_SHAKEOUT_SL_WINDOW`` closes
    for ``symbol``. Trail / flatten / weekend do not count. A searched
    stop already at or above the floor is left alone.

    ``since_ts`` (usually ``cfg.opt_updated_at``) drops closes from before
    the config now running — a fresh apply does not inherit the previous
    family's SL streak (F7). 0 keeps the legacy full-window count.

    While the floor is live the next entry's hard stop may not match the
    searched trio: trail stays at the searched values. When the window
    cools, stored sl/trail are the scored set again — do not scale trail
    with the floor, and do not drop a pending trail because SL was floored.

    F8: the bump is ``max(base, min(base * 1.5, 2.0))`` — relative, not an
    absolute jump to 2.0 ATR (mtf 0.5 stayed sizeable on a small account).
    """
    try:
        floor_base = float(base or 0.0)
    except (TypeError, ValueError):
        floor_base = 0.0
    if floor_base <= 0:
        return floor_base
    try:
        since = float(since_ts or 0.0)
    except (TypeError, ValueError):
        since = 0.0
    mine = []
    for row in (autopsies or []):
        if not row or str(row.get("symbol") or "") != symbol:
            continue
        if since > 0:
            try:
                exit_t = float(row.get("exit_time") or 0.0)
            except (TypeError, ValueError):
                continue
            if exit_t < since:
                continue
        mine.append(row)
    window = mine[-_SHAKEOUT_SL_WINDOW:]
    deaths = 0
    for row in window:
        if str(row.get("exit_reason") or "") != "sl":
            continue
        if not autopsy_r_usable(row):
            continue
        try:
            realised = float(row.get("r_realised") or 0.0)
        except (TypeError, ValueError):
            continue
        if realised < 0:
            deaths += 1
    if deaths < _SHAKEOUT_SL_DEATHS:
        return floor_base
    bumped = min(floor_base * _SHAKEOUT_SL_REL, _SHAKEOUT_SL_FLOOR)
    return round(max(floor_base, bumped), 4)

def size_sl_distance(cfg: SymbolConfig, atr: float, client: MT5Client) -> float:
    """SL distance for lot sizing — searched multiple, not shakeout floor."""
    if not math.isfinite(atr) or atr <= 0:
        return 0.0
    try:
        base = float(cfg.sl_atr_mult or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if base <= 0:
        return 0.0
    return max(atr * base, client.min_stop_distance(cfg.symbol))


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
        trading = equity - self.cash_flow - self.start_balance
        pct = trading / self.start_balance * 100.0
        # C3: a deposit larger than the morning chip can make trading PnL
        # more negative than -100% of start (lost the deposit too). That
        # invented -174% stuck the supervisor at risk_scale_floor and would
        # instant-halt if daily_loss_pct were armed. Cap at -100% of the
        # chip; deposits still do not buy more room (denom stays start).
        if pct < -100.0:
            return -100.0
        return pct

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
    # multiple of the intended risk the trade is skipped instead of oversized
    # when no account picture is present. With an account, remaining-margin
    # share × auto 1R (max stored risk%, 2%) is the size — do not skip a
    # micro raw that the kasa can actually carry.
    # Soft overshoot: broker min vs 1R (granularity). Hard ceiling even when
    # concurrent budget would fund a fatter min-lot fill (C1 / T1).
    MAX_MIN_LOT_OVERSHOOT = 1.5
    # Live US30 at ~$232 / sl 2.5 ATR sits ~4.1x (0.1 / 0.024); 3.5 left it
    # lot-0 while GER/JPN cleared the concurrent door. Still well under
    # absurd broker mins (see skip test at ~6x).
    MAX_MIN_LOT_CONCURRENT_OVERSHOOT = 4.5
    # Floor of the live 1R cap when the account picture is present. Stored
    # risk% still wins if it is already higher. Shakeout SL × full-kasa lots
    # without this bound would blow the account.
    AUTO_R_PCT = 2.0
    _KASA_PIN_LOT = "kasa_pin_lot_until"
    _KASA_PIN_CONC = "kasa_pin_conc_until"
    # Set by the engine to the supervisor's "this name cannot open" predicate.
    # A class attribute rather than an __init__ field so an instance built
    # without running __init__ still answers it.
    supervisor_blocked: Any = None

    def __init__(self, store: Store, client: MT5Client) -> None:
        self.store = store
        self.client = client
        self.daily = DailyGuard(store)

    def _cannot_open(self, symbol: str) -> bool:
        """True when the supervisor has suspended this name outright."""
        hook = self.supervisor_blocked
        if not callable(hook):
            return False
        try:
            return bool(hook(symbol))
        except Exception:
            return False

    def _setting_pin_active(self, key: str) -> bool:
        getter = getattr(self.store, "get_setting", None)
        if not callable(getter):
            return False
        try:
            until = float(getter(key, 0) or 0)
        except (TypeError, ValueError):
            return False
        return until > time.time()

    _MIN_BUDGET_WEIGHT_FLOOR = 0.02

    def _supervisor_edge_health(self, symbol: str) -> float:
        hook = getattr(self, "supervisor_edge_health", None)
        if not callable(hook):
            return 0.0
        try:
            return max(0.0, float(hook(symbol) or 0.0))
        except Exception:
            return 0.0

    def _vacant_enabled_cfgs(
            self, positions: list[dict[str, Any]] | None) -> list[SymbolConfig]:
        magics = {c.magic for c in list(self.store.symbols.values())}
        occupied: set[str] = set()
        for pos in positions or ():
            if pos.get("magic") not in magics:
                continue
            name = pos.get("symbol")
            if name:
                occupied.add(str(name))
        out: list[SymbolConfig] = []
        for cfg in list(self.store.symbols.values()):
            if not getattr(cfg, "enabled", True):
                continue
            broker = self.client.resolve(cfg.symbol) or cfg.symbol
            if broker in occupied:
                continue
            if self._cannot_open(cfg.symbol):
                continue
            out.append(cfg)
        return out

    def _min_budget_weight(self, vacant: list[SymbolConfig]) -> float:
        exps = [max(0.0, float(Supervisor.holdout_expectancy(c) or 0.0))
                for c in vacant]
        pos = [e for e in exps if e > 0]
        if not pos:
            return self._MIN_BUDGET_WEIGHT_FLOOR
        return max(self._MIN_BUDGET_WEIGHT_FLOOR, statistics.median(pos) * 0.15)

    def _symbol_budget_weight(self, cfg: SymbolConfig,
                              vacant: list[SymbolConfig] | None = None) -> float:
        """Holdout expectancy (+ optional live edge_health) for budget share."""
        exp = max(0.0, float(Supervisor.holdout_expectancy(cfg) or 0.0))
        eh = self._supervisor_edge_health(cfg.symbol)
        core = exp
        if eh > 0 and exp > 0:
            core = 0.7 * exp + 0.3 * (eh * exp)
        elif eh > 0:
            core = eh * self._MIN_BUDGET_WEIGHT_FLOOR
        floor = self._min_budget_weight(vacant or [cfg])
        return core + floor

    def _budget_share_frac(self, cfg: SymbolConfig,
                           positions: list[dict[str, Any]] | None) -> float:
        vacant = self._vacant_enabled_cfgs(positions)
        if not vacant:
            return 1.0
        weights = {c.symbol: self._symbol_budget_weight(c, vacant) for c in vacant}
        total = sum(weights.values()) or 1e-9
        if cfg.symbol not in weights:
            return 0.0
        return float(weights[cfg.symbol]) / total

    def live_lot_multiplier(self, account: dict[str, Any] | None = None,
                            positions: list[dict[str, Any]] | None = None) -> float:
        """Inline kasa lot dial from margin%, or stored when OFF / pinned."""
        sys_cfg = self.store.system
        stored = max(0.1, float(getattr(sys_cfg, "lot_multiplier", 1.0) or 1.0))
        if not bool(getattr(sys_cfg, "kasa_auto_enabled", True)):
            return stored
        try:
            equity = float((account or {}).get("equity") or 0.0)
        except (TypeError, ValueError):
            equity = 0.0
        # No account picture (unit tests, pre-connect) → stored; skip pin I/O.
        if equity <= 0:
            return stored
        if self._setting_pin_active(self._KASA_PIN_LOT):
            return stored
        try:
            margin_pct = float(getattr(sys_cfg, "max_margin_usage_pct", 0) or 0)
        except (TypeError, ValueError):
            margin_pct = 0.0
        # Uncapped margin (0) → keep stored mult for the 1R cap identity.
        if margin_pct <= 0:
            return stored
        n = self._vacant_enabled_count(positions)
        plan = compute_kasa_targets(
            equity=equity,
            n_enabled=n,
            max_margin_usage_pct=margin_pct,
            lot_multiplier=stored,
            max_concurrent_risk_pct=float(
                getattr(sys_cfg, "max_concurrent_risk_pct", 0) or 0),
        )
        return float(plan["targets"]["lot_multiplier"])

    def live_concurrent_pct(self, account: dict[str, Any] | None = None,
                            positions: list[dict[str, Any]] | None = None,
                            lot_mult: float | None = None) -> float:
        """Inline concurrent risk %, or stored when OFF / pinned."""
        sys_cfg = self.store.system
        stored = float(getattr(sys_cfg, "max_concurrent_risk_pct", 0.0) or 0.0)
        if not bool(getattr(sys_cfg, "kasa_auto_enabled", True)):
            return stored
        try:
            equity = float((account or {}).get("equity") or 0.0)
        except (TypeError, ValueError):
            equity = 0.0
        if equity <= 0:
            return stored
        if self._setting_pin_active(self._KASA_PIN_CONC):
            return stored
        n = self._vacant_enabled_count(positions)
        plan = compute_kasa_targets(
            equity=equity,
            n_enabled=n,
            max_margin_usage_pct=float(
                getattr(sys_cfg, "max_margin_usage_pct", 0) or 0),
            lot_multiplier=float(lot_mult if lot_mult is not None else
                                 self.live_lot_multiplier(account, positions)),
            max_concurrent_risk_pct=stored,
        )
        return float(plan["targets"]["max_concurrent_risk_pct"])

    # ------------------------------------------------------------- lot sizing

    @staticmethod
    def _live_holdout_block(cfg: SymbolConfig) -> dict:
        """Holdout numbers comparable to live charging: thick costed, else paper.

        Same n floor as ``Supervisor.holdout_expectancy``. Thin charged
        replays (US30 n=17) must not rewrite size or typical-cost readout.
        """
        summary = cfg.opt_summary if isinstance(getattr(cfg, "opt_summary", None), dict) else {}
        hold = summary.get("holdout") or {}
        costed = summary.get("holdout_costed")
        try:
            costed_n = int((costed or {}).get("trades") or 0) if isinstance(costed, dict) else 0
        except (TypeError, ValueError):
            costed_n = 0
        if isinstance(costed, dict) and costed_n >= Supervisor.MIN_COSTED_N:
            return costed
        return hold if isinstance(hold, dict) else {}

    @staticmethod
    def _edge_metric(cfg: SymbolConfig) -> float:
        """Validated edge productivity: holdout net R per unit of holdout DD.

        Prefers ``holdout_costed`` when it clears ``Supervisor.MIN_COSTED_N``
        (same rule as slot/budget expectancy). Paper-only stamps stay on
        ``holdout``. Window length used to sit in the denominator (R per
        calendar day), so an M5 symbol whose bar cap filled ~92 days looked
        six times more productive than an M30 symbol with the same total R
        over ~610 days. Net R and max_dd_r are earned on the same slice, so
        the ratio does not care how long the cap happened to run.
        Unmeasurable input (no DD, non-positive DD, non-positive net R) and
        an unvalidated stamp (``validated is False``) return 0 so edge_scale
        stays the 1.0 neutral — not EDGE_MIN.
        """
        summary = cfg.opt_summary or {}
        # Docstring says validated. GAP-5 wrote validated=false and a +93 R
        # holdout; size_by_edge still treated that as edge and sized NAS100
        # as a winner while live 30d ran PF 0.50.
        if getattr(cfg, "validated", None) is False:
            return 0.0
        if summary.get("validated") is False:
            return 0.0
        hold = RiskManager._live_holdout_block(cfg)
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

    def _vacant_enabled_count(self, positions: list[dict[str, Any]] | None) -> int:
        """Enabled names that do not already hold one of our tickets.

        Remaining book margin is split across that set so the first signal
        does not swallow the kasa. Occupied names are 1-ticket already.
        """
        magics = {c.magic for c in list(self.store.symbols.values())}
        occupied: set[str] = set()
        for pos in positions or ():
            if pos.get("magic") not in magics:
                continue
            name = pos.get("symbol")
            if name:
                occupied.add(str(name))
        n = 0
        for cfg in list(self.store.symbols.values()):
            if not getattr(cfg, "enabled", True):
                continue
            broker = self.client.resolve(cfg.symbol) or cfg.symbol
            if broker in occupied:
                continue
            # A quarantined name carries risk_scale 0.0 and cannot open, but
            # it used to keep a full share of the remaining book margin
            # reserved anyway - so every entry that *could* happen was sized
            # at (vacant - suspended) / vacant of its intended lot.
            if self._cannot_open(cfg.symbol):
                continue
            n += 1
        return max(1, n)

    def _margin_lot_ceiling(self, cfg: SymbolConfig, account: dict[str, Any] | None,
                            side: str, floor: float,
                            broker_ceiling: float,
                            positions: list[dict[str, Any]] | None = None,
                            ai_scale: float = 1.0) -> float | None:
        """Lots that still fit this name's share of remaining margin.

        Book budget is equity × max_margin_usage_pct minus used, then split
        across vacant enabled names by holdout-expectancy weight (not equal
        1/n), then × denetci ``ai_scale``. Broker leverage is inside
        ``margin_for`` (per-instrument). Soft %95 lid when kasa is ON.
        Leftover ``cfg.max_margin_pct`` is unread (operator 28.08). None = no
        extra cap.
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
        # Soft lid only — never multiply by N/broker here (lot_mult owns dial).
        if bool(getattr(sys_cfg, "kasa_auto_enabled", True)) and equity > 0:
            soft = equity * NOTIONAL_MARGIN_SOFT_PCT / 100.0 - used
            margin_budget = max(0.0, min(margin_budget, soft))
        budget = max(0.0, min(margin_budget, free - float(sys_cfg.min_free_margin or 0.0)))
        try:
            scale = max(0.0, float(ai_scale))
        except (TypeError, ValueError):
            scale = 1.0
        whole = budget * scale
        share = whole * self._budget_share_frac(cfg, positions)
        unit = floor if floor > 0 else 0.01
        try:
            need = float(self.client.margin_for(cfg.symbol, unit, side) or 0.0)
        except (TypeError, ValueError, AttributeError):
            return None
        if need <= 0:
            return None
        # Splitting across vacant names must not zero every entry on a small
        # account: if one share cannot fund min lot but the whole book can,
        # size this signal on whole remaining budget. can_open() and
        # max_concurrent_risk_pct still bind when several names fill.
        if share + 1e-12 < need and whole + 1e-12 >= need:
            share = whole
        return min(broker_ceiling, unit * (share / need))

    def lot_for(self, cfg: SymbolConfig, sl_distance: float, balance: float,
               ai_scale: float = 1.0, account: dict[str, Any] | None = None,
               side: str = "buy",
               positions: list[dict[str, Any]] | None = None) -> tuple[float, str]:
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

        multiplier = self.live_lot_multiplier(account, positions)
        edge = self.edge_scale(cfg)
        multiplier *= edge
        multiplier *= max(0.0, float(ai_scale))

        # Account risk% × denetci (edge + ai_scale). Leftover max_lot /
        # max_margin_pct are unread — remaining book margin × auto 1R size.
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
        if edge != 1.0:
            note += f" | avantaj x{edge:.2f}"
        if ai_scale != 1.0:
            note += f" | AI x{ai_scale:.2f}"
        live_mult = self.live_lot_multiplier(account, positions)
        if bool(getattr(self.store.system, "kasa_auto_enabled", True)):
            note += f" | kasa x{live_mult:g}"

        auto = self._margin_lot_ceiling(
            cfg, account, side, floor, ceiling, positions=positions,
            ai_scale=ai_scale)
        if auto is not None:
            try:
                stored = float(getattr(cfg, "risk_percent", 0.0) or 0.0)
            except (TypeError, ValueError):
                stored = 0.0
            r_pct = max(stored, self.AUTO_R_PCT)
            # Deliberately NOT ``multiplier``: that already carries edge_scale
            # (up to EDGE_MAX 2.2), so scaling the ceiling by the same push it
            # exists to bound made the "auto 1R" cap ~4.4% of balance instead
            # of 2%. The operator's lot_multiplier (or inline kasa dial) stays
            # in - it sets the book's overall size - and ai_scale stays in only
            # as a throttle, clamped at 1.0 so the supervisor can tighten the
            # ceiling but never lift it.
            try:
                throttle = min(1.0, max(0.0, float(ai_scale)))
            except (TypeError, ValueError):
                throttle = 1.0
            cap_multiplier = max(0.1, live_mult) * throttle
            r_cap = (balance * r_pct / 100.0 * cap_multiplier
                     / (sl_distance * money_per_unit))
            if auto + 1e-12 < floor:
                return 0.0, (f"lot sifir ({note}, marj payi {auto:g} "
                             f"< min {floor:g}), islem atlandi")
            lot = min(auto, r_cap, ceiling)
            if lot + 1e-12 < floor:
                # Min lot may overshoot the 1R cap by a broker-granularity
                # factor. Past that, skip — do NOT fall through to the full
                # margin share (old ``lev >= 100`` path sized ~10% of a $225
                # book per index fill).
                if floor <= r_cap * self.MAX_MIN_LOT_OVERSHOOT + 1e-12:
                    lot = min(floor, auto, ceiling)
                elif floor + 1e-12 < r_cap * self.MAX_MIN_LOT_CONCURRENT_OVERSHOOT:
                    # Equity-floor names (wide SL × $200 book): 1R wants
                    # sub-min lot. If the operator's concurrent dial still
                    # has room for this fill's dollar 1R, take broker min —
                    # can_open() re-checks the same sum. Concurrent 0 = off
                    # → do not unlock here.
                    try:
                        eq = float((account or {}).get("equity") or 0.0)
                    except (TypeError, ValueError):
                        eq = 0.0
                    fill_r = floor * sl_distance * money_per_unit
                    cap_pct = self.live_concurrent_pct(account, positions)
                    if eq > 0 and cap_pct > 0 and fill_r > 0:
                        magics = {c.magic for c in list(self.store.symbols.values())}
                        mine = [p for p in (positions or ())
                                if p.get("magic") in magics]
                        book = sum(self.remaining_position_risk(p) for p in mine)
                        if math.isfinite(book) and book + fill_r <= eq * cap_pct / 100.0 + 1e-9:
                            lot = min(floor, auto, ceiling)
                            note += (f" | min lot eszamanli "
                                     f"({fill_r / eq * 100:.1f}% / %{cap_pct:g})")
                        else:
                            return 0.0, (f"lot sifir ({note}, 1R tavan {r_cap:g} "
                                         f"< min {floor:g}), islem atlandi")
                    else:
                        return 0.0, (f"lot sifir ({note}, 1R tavan {r_cap:g} "
                                     f"< min {floor:g}), islem atlandi")
                else:
                    return 0.0, (f"lot sifir ({note}, 1R tavan {r_cap:g} "
                                 f"< min {floor:g}), islem atlandi")
            if lot + 1e-12 < floor:
                return 0.0, (f"lot sifir ({note}, tavan {lot:g} "
                             f"< min {floor:g}), islem atlandi")
            if abs(lot - auto) <= abs(lot - r_cap) + 1e-12:
                note += f" | marj pay {auto:.3f}"
            if r_cap + 1e-12 < auto:
                note += f" | 1R tavan {r_cap:.3f}"
            try:
                lev = int((account or {}).get("leverage") or 0)
            except (TypeError, ValueError):
                lev = 0
            if lev >= 100:
                note += f" | kaldirac 1:{lev}"
            return self.client.normalize_volume(cfg.symbol, lot), note

        if raw < floor:
            # No account picture: do not silently size up. A small overshoot
            # is broker granularity; past MAX_MIN_LOT_OVERSHOOT skip.
            if floor > raw * self.MAX_MIN_LOT_OVERSHOOT:
                return 0.0, (f"min lot {floor:g} riski {floor / raw:.1f}x asiyor, "
                              f"islem atlandi ({note})")
            note += f" (min lot {floor:g} riski asiyor, {floor / raw:.1f}x)"
        lot = max(floor, raw)
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
                cfg.sl_atr_mult, cfg.symbol, autopsies,
                since_ts=float(getattr(cfg, "opt_updated_at", 0.0) or 0.0))
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
        sys_cfg = self.store.system
        magics = {c.magic for c in list(self.store.symbols.values())}
        mine = [p for p in positions if p["magic"] in magics]
        if any(float(p.get("volume") or 0.0) > 0
               and live_stop_level(p.get("sl")) <= 0
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
            # Search still scores max_open=1. Leftover DB max_positions 5/10
            # is unread — the 13.08 stack. One ticket per name; lot_for spends
            # the margin share on that ticket instead of restacking.
            cap = 1
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

        # Book-wide 1R ceiling, re-armed by the operator 31.08. It was switched
        # off 27.08 as unreachable: lot was risk% of balance, so the whole book
        # summed to ~17% of equity and a stored 8 or 30 could never bind. What
        # changed is why it exists - lot_for resolves to min(margin share, auto
        # 1R cap), the 2% cap binds first, and it is the only thing standing
        # between the book and the 90% margin allowance. Raising it to use that
        # margin removes exactly what made this ceiling unreachable, so the
        # ceiling goes back in first. Inert at today's sizing.
        #
        # Naked positions already returned above, so no inf reaches this sum.
        # A trailed stop measures to the *current* SL and frees budget. When
        # sl_distance is unknown the new fill cannot be priced, but what is
        # already open still counts - an unmeasurable entry must not read as
        # free room on top of a book that is over the line.
        # cfg.max_margin_pct stays unread.
        cap_pct = self.live_concurrent_pct(account, positions)
        if cap_pct > 0 and equity > 0:
            book_risk = sum(self.remaining_position_risk(p) for p in mine)
            book_risk += self.risk_dollars(cfg.symbol, lot, sl_distance)
            projected = book_risk / equity * 100.0
            if projected > cap_pct:
                return Verdict(False, f"eszamanli risk limiti "
                                      f"(%{projected:.1f} > %{cap_pct:g})")

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
        mult = max(0.1, float(self.store.system.lot_multiplier or 1.0))
        return balance * pct / 100.0 * float(self.edge_scale(cfg) or 1.0) * mult

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
        short_windows: list[str] = []
        fat_1r: list[str] = []
        sys_cfg = self.store.system
        for cfg in list(self.store.symbols.values()):
            if not getattr(cfg, "enabled", False):
                continue
            row = by_sym.get(cfg.symbol) or {}
            summary = cfg.opt_summary if isinstance(cfg.opt_summary, dict) else {}
            if "charge_costs" in summary:
                stamps.append(bool(summary.get("charge_costs")))
            if summary.get("costed_negative") and bool(
                    getattr(sys_cfg, "charge_costs", True)):
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
            # Live min-lot concurrent can make 1R 3-4x the 2% auto cap
            # (US30 $16 on $222). The chip uses that 1R because fills do;
            # name it so "%99 iyimser" is not read as another days bug.
            plain_r = balance * float(self.AUTO_R_PCT) / 100.0
            if plain_r > 0 and risk > plain_r * 3.0 + 1e-12:
                fat_1r.append(cfg.symbol)
            if days + 1e-12 < MIN_PROJ_DAYS:
                short_windows.append(f"{cfg.symbol} {days:.0f}g")
            days_eff = max(days, MIN_PROJ_DAYS)
            projected_daily += net * risk / days_eff
            costed = summary.get("holdout_costed") or {}
            try:
                cnet = float(costed.get("net_r") or 0.0)
            except (TypeError, ValueError):
                cnet = 0.0
            projected_costed_daily += (cnet or net) * risk / days_eff
        projected_charge_costs = all(stamps) if stamps else bool(
            getattr(sys_cfg, "charge_costs", True))
        monthly = projected_daily * 21.0
        costed_m = projected_costed_daily * 21.0
        monthly_pct = round(monthly / balance * 100.0, 2) if balance > 0 else 0.0
        costed_pct = round(costed_m / balance * 100.0, 2) if balance > 0 else 0.0
        note_bits: list[str] = []
        if short_windows:
            note_bits.append("kisa holdout penceresi: " + ", ".join(short_windows))
        if fat_1r:
            note_bits.append("canli 1R min-lot sisirme: " + ", ".join(fat_1r))
        headline_pct = costed_pct if costed_m else monthly_pct
        if headline_pct > _PROJ_PLAUSIBLE_MONTHLY_PCT:
            note_bits.append(f"projeksiyon %{headline_pct:.0f}/ay (iyimser)")
        return {
            "projected_daily": round(projected_daily, 2),
            "projected_monthly": round(monthly, 2),
            "projected_monthly_pct": monthly_pct,
            "projected_charge_costs": projected_charge_costs,
            "projected_costed_daily": round(projected_costed_daily, 2),
            "projected_costed_monthly": round(costed_m, 2),
            "projected_costed_monthly_pct": costed_pct,
            "projected_costed_negative": projected_costed_negative,
            "projected_note": " | ".join(note_bits),
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

        pct = float(sys_cfg.max_margin_usage_pct or 0.0)
        if equity > 0 and pct > 0:
            margin_budget = max(0.0, equity * pct / 100.0 - used)
        else:
            margin_budget = free
        if bool(getattr(sys_cfg, "kasa_auto_enabled", True)) and equity > 0:
            soft = equity * NOTIONAL_MARGIN_SOFT_PCT / 100.0 - used
            margin_budget = max(0.0, min(margin_budget, soft))
        budget = max(0.0, min(margin_budget, free - sys_cfg.min_free_margin))

        rows = []
        for cfg in list(self.store.symbols.values()):
            broker = self.client.resolve(cfg.symbol) or cfg.symbol
            open_now = [p for p in mine if p["symbol"] == broker]
            atr = float(atr_by_symbol.get(cfg.symbol, 0.0))
            sl_mult = shakeout_sl_atr_mult(
                cfg.sl_atr_mult, cfg.symbol, autopsies,
                since_ts=float(getattr(cfg, "opt_updated_at", 0.0) or 0.0))
            sl_dist = size_sl_distance(cfg, atr, self.client)
            lot, lot_note = self.lot_for(cfg, sl_dist, balance, account=account,
                                         positions=mine)
            if sl_dist <= 0:
                lot_note = "risk (ATR bekleniyor)"
            elif sl_mult > float(cfg.sl_atr_mult or 0) + 1e-9:
                lot_note = f"risk (SL x{sl_mult:g} shakeout, lot x{cfg.sl_atr_mult:g})"
            slot_left = max(0, 1 - len(open_now)) if cfg.enabled else 0
            margin = self.client.margin_for(cfg.symbol, lot, "buy")
            if margin <= 0 and slot_left and sl_dist > 0:
                probe = self.client.margin_for(cfg.symbol, float(
                    (self.client.info(cfg.symbol) or {}).get("volume_min") or 0.0), "buy")
                by_margin = int(budget // probe) if probe > 0 else slot_left
            else:
                by_margin = int(budget // margin) if margin > 0 else 0

            # What one unit of risk (1R) is worth in account currency at this lot.
            r_value = self.risk_dollars(cfg.symbol, lot, sl_dist)
            cost = cfg.commission_per_lot * lot
            tick = self.client.tick(cfg.symbol)
            if tick:
                cost += tick["spread"] * self.client.money_per_price_unit(cfg.symbol, lot)
            hold = self._live_holdout_block(cfg)
            expectancy_r = float(Supervisor.holdout_expectancy(cfg) or 0.0)
            # Long-run cost per trade in R, straight from the holdout slice.
            expectancy_cost = float(hold.get("cost_per_trade_r", 0.0) or 0.0)
            vacant = self._vacant_enabled_cfgs(mine)
            b_weight = self._symbol_budget_weight(cfg, vacant) if cfg.enabled else 0.0
            b_share = self._budget_share_frac(cfg, mine) if cfg.enabled else 0.0
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
                "free_slots": min(by_margin, slot_left) if slot_left else 0,
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
                "budget_weight": round(b_weight, 4),
                "budget_share_pct": round(b_share * 100.0, 1),
            })

        # Project holdout net R onto dollars. A missing expectancy key is not
        # "no edge" (GAP-5 slim stamps); a zero risk_per_trade (search-frozen
        # ATR) is not "no size" — fall back to configured risk %.
        proj = self.fill_holdout_projection(rows, balance)
        projected_daily = proj["projected_daily"]
        projected_costed_daily = proj["projected_costed_daily"]
        projected_costed_negative = proj["projected_costed_negative"]
        projected_charge_costs = proj["projected_charge_costs"]
        projected_note = str(proj.get("projected_note") or "")

        total_risk = sum(r["risk_per_trade"] for r in rows if r["enabled"])
        live_mult = self.live_lot_multiplier(account, mine)
        live_conc = self.live_concurrent_pct(account, mine, lot_mult=live_mult)
        multiplier = live_mult
        global_slots = max((r["free_slots"] for r in rows), default=0)

        # No ticket-count ceiling. Worst-case concurrent is every enabled
        # name firing at once (search still scores max_open=1).
        enabled_risks = [r["risk_per_trade"] for r in rows if r["enabled"]]
        enabled_margins = [r["margin_per_trade"] for r in rows if r["enabled"]]
        concurrent_risk = sum(enabled_risks)
        concurrent_margin = sum(enabled_margins)

        # How far size could scale before either the risk budget or margin runs out.
        # When daily_loss_pct is off the risk leg is inert — do not invent a
        # fake 0.5% floor (that made safe_multiplier read 0.04 at 3x lot).
        margin_room = equity * sys_cfg.max_margin_usage_pct / 100.0
        by_margin_all = margin_room / concurrent_margin if concurrent_margin > 0 else 0.0
        try:
            loss_pct = float(sys_cfg.daily_loss_pct or 0.0)
        except (TypeError, ValueError):
            loss_pct = 0.0
        if loss_pct > 0 and concurrent_risk > 0:
            risk_budget = equity * loss_pct / 100.0
            by_risk = risk_budget / concurrent_risk
            headroom = max(0.0, min(by_risk, by_margin_all))
        else:
            headroom = max(0.0, by_margin_all)

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
            "lot_multiplier_stored": max(0.1, float(sys_cfg.lot_multiplier or 1.0)),
            "lot_multiplier_live": live_mult,
            "lot_mult_pinned": self._setting_pin_active(self._KASA_PIN_LOT),
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
            "projected_note": projected_note,
            # Leftover ticket-count ceiling. Unread by can_open; GET honesty.
            "max_total_positions": sys_cfg.max_total_positions,
            "max_cost_pct_of_risk": float(sys_cfg.max_cost_pct_of_risk or 0.0),
            "global_free_slots": global_slots,
            "margin_budget": round(budget, 2),
            "margin_usage_pct": round(used / equity * 100.0, 2) if equity > 0 else 0.0,
            "max_margin_usage_pct": sys_cfg.max_margin_usage_pct,
            "max_concurrent_risk_pct": live_conc,
            "max_concurrent_risk_pct_stored": float(
                getattr(sys_cfg, "max_concurrent_risk_pct", 0.0) or 0.0),
            "conc_pinned": self._setting_pin_active(self._KASA_PIN_CONC),
        }
