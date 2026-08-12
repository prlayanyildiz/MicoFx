from __future__ import annotations

import math
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from .logbus import LOG
from .models import SymbolConfig
from .mt5client import MT5Client
from .store import Store

# What a run with no losing trades at all scores. Imported rather than
# redeclared: this exact defect has now appeared three times in three modules
# (_pf, _judge's inline copy, Result.profit_factor), so the value and the
# reasoning behind it live in one place. Every threshold in this module reads
# it as "excellent" - quarantine_pf 0.8, watch_pf 1.0, bad_hour_pf 0.7 - which
# is what a flawless record deserves.
from .backtest import PF_NO_LOSSES  # noqa: E402  (re-exported; see above)

DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "review_interval_sec": 120,
    "lookback_days": 14,
    # Evidence needed before SUSPENDING a symbol. Quarantine is a 12-hour hard
    # stop, so it has to be paid for with samples: measured against this
    # portfolio's own validated win rates (26-79%) and profit factors, judging
    # on 8 trades false-quarantined a healthy symbol 23% of the time while
    # catching a genuinely broken one only 72% - at 25 it is 11% against 87%,
    # better on both counts.
    "min_trades": 25,
    # Evidence needed to merely SIZE A SYMBOL DOWN. A watch costs 40% of one
    # symbol's lot and reverses itself the moment the numbers recover, so it
    # does not need a suspension's proof. Sharing min_trades left a hole:
    # GER40 at PF 0.62 over 18 trades cleared neither bar and traded at full
    # size, when the graduated response it deserves is exactly the soft one.
    "watch_min_trades": 10,
    # Consecutive losers that trip a suspension. Deliberately far out: with no
    # take-profit, a trend follower loses often by design, and this book's
    # validated win rates run 26-40%. Four in a row therefore has a ~30%
    # probability at any point - XAUUSD's own holdout expects 22 of them, and
    # US30's 73 - so a 4 trigger fires on the shape of the strategy rather
    # than on anything going wrong. It suspended US30 while its live profit
    # factor was 1.55 and it was the best earner in the book.
    "quarantine_losses": 10,
    "quarantine_pf": 0.80,           # profit factor below this is broken, not unlucky
    "watch_pf": 1.00,                # between watch_pf and quarantine_pf: keep trading, smaller
    "quarantine_hours": 12,
    "watch_risk_scale": 0.6,
    "bad_hour_min_trades": 6,
    "bad_hour_pf": 0.7,
    "dd_soft_pct": 1.5,              # daily drawdown where lot scaling starts
    "dd_hard_pct": 3.0,              # ...and where it reaches the floor
    "risk_scale_floor": 0.4,
    "prefer_strong_on_dd": True,     # under daily stress, only let strong symbols enter
    "auto_reoptimize": True,
    "reopt_min_age_hours": 48,
    "reopt_on_decay": True,          # also re-opt when live edge decays vs backtest
    # Trades needed before the live PF-halves decay check runs. Was 20; the
    # false-alarm rate at that bar was measured rather than assumed - 20000
    # Monte Carlo runs of a symbol whose true edge NEVER changes, drawn from
    # win rates and payoffs matching this book:
    #
    #     20 trades   12-17% of the time the rule fires anyway
    #     30 trades    5-10%
    #     40 trades    4-9%
    #     60 trades  1.5-5%
    #
    # At 20 that is roughly one symbol in seven cut to half size on nothing
    # but noise, plus a walk-forward queued behind it by reopt_on_decay. The
    # rule splits the sample in half and compares two 10-trade profit factors,
    # which is why it is that noisy.
    #
    # The trade-off it was lowered to 20 for still stands (reacting to a real
    # regime turn inside ~10-15 trades rather than waiting a week longer), but
    # at this book's frequency 30 trades is about a month, not a quarter, and
    # US30 was sitting at half size off 21 trades while carrying the most
    # precisely measured holdout in the portfolio - 407 trades.
    "edge_decay_min_trades": 30,
    # A re-opt that finds nothing better than the current config never updates
    # opt_updated_at, so without this a "watch" symbol whose decay is a genuine
    # regime shift (not a stale parameter) gets re-queued and re-run in full
    # every single review cycle - hammering the same expensive walk-forward
    # search every couple of minutes for no new result.
    "reopt_retry_cooldown_hours": 1.0,
}


@dataclass
class SymbolVerdict:
    symbol: str
    state: str = "ok"                # ok | watch | quarantine | idle
    reason: str = ""
    trades: int = 0
    wins: int = 0
    losses: int = 0
    net: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0          # realised $ per closed trade
    expected_r: float = 0.0          # backtest holdout expectancy in R
    expected_per_trade: float = 0.0  # expected_r projected to recent $ risk (approx)
    edge_health: float = 0.0         # live / expected; 1.0 = on plan, <0.35 = decayed
    consecutive_losses: int = 0
    quarantine_until: float = 0.0
    risk_scale: float = 1.0
    blocked_hours: list = field(default_factory=list)
    hour_risk_scales: dict = field(default_factory=dict)  # hour -> soft multiplier (PF-based, not a hard block)
    last_trade_at: float = 0.0
    priority: float = 0.0            # higher = prefer when slots are scarce
    last_reopt_attempt: float = 0.0  # queued-for-reopt timestamp, whether or not it improved

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Supervisor:
    """Adaptive risk controller sitting between the signal engine and the broker.

    It reads closed-trade history from MT5 and decides, per symbol, whether the
    strategy is still working: suspending instruments that break down, shrinking
    size while the day is bleeding, blocking hours that repeatedly lose, and
    queueing a re-optimization when a symbol's edge has clearly decayed.

    Everything it does is derived from realised results, so it cannot invent an
    edge - it only protects one. All decisions are logged and reversible.
    """

    def __init__(self, store: Store, client: MT5Client) -> None:
        self.store = store
        self.client = client
        self.optimizer = None                      # wired late to avoid a cycle
        self.verdicts: dict[str, SymbolVerdict] = {}
        self.last_review = 0.0
        self.risk_scale = 1.0
        self.notes: list[str] = []
        self.reopt_queue: list[str] = []
        # Guards self.verdicts (and the state that travels with it) against the
        # engine's background poll thread and an HTTP request thread (clear/
        # status/settings) touching it at the same time - the actual source of
        # the "dictionary changed size during iteration" crash seen in the log.
        # Reentrant: review() calls _judge()/priority(), which read verdicts
        # too, all on the same thread while already holding it.
        self._lock = threading.RLock()
        self._restore()

    # -------------------------------------------------------------- settings

    @property
    def settings(self) -> dict[str, Any]:
        stored = self.store.get_setting("supervisor", {})
        merged = dict(DEFAULTS)
        if isinstance(stored, dict):
            merged.update({k: v for k, v in stored.items() if k in DEFAULTS})
        return merged

    def update_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        current = self.settings
        for key, value in patch.items():
            if key in DEFAULTS and value is not None:
                current[key] = value
        self.store.set_setting("supervisor", current)
        return current

    @property
    def enabled(self) -> bool:
        return bool(self.settings["enabled"])

    # ------------------------------------------------------------ persistence

    def _restore(self) -> None:
        saved = self.store.get_setting("supervisor_state", {})
        if not isinstance(saved, dict):
            return
        for symbol, payload in (saved.get("verdicts") or {}).items():
            if isinstance(payload, dict):
                known = {k: v for k, v in payload.items() if k in SymbolVerdict.__dataclass_fields__}
                known["symbol"] = symbol
                # hour_risk_scales is keyed by hour-of-day as an int, and JSON
                # has no integer keys - set_setting() serialises {9: 0.62} and
                # get_setting() hands back {"9": 0.62}. _gate_locked() looks it
                # up with an int hour, so a restored map never matched and the
                # per-hour size throttle silently did nothing. Narrow in
                # practice (last_review starts at 0.0, so the first cycle's
                # review() recomputes every verdict with int keys again), but
                # the restored state should be faithful rather than rely on
                # being overwritten quickly to stay harmless.
                known["hour_risk_scales"] = self._coerce_hour_map(
                    known.get("hour_risk_scales"))
                self.verdicts[symbol] = SymbolVerdict(**known)
        self.risk_scale = float(saved.get("risk_scale", 1.0) or 1.0)

    @staticmethod
    def _coerce_hour_map(raw: Any) -> dict[int, float]:
        """Restore an hour->multiplier map to the int keys the gate looks up.

        Anything unparseable is dropped rather than kept as a key that can
        never match: a silently inert entry in a size-throttle map reads as
        "this hour is fine" and is the failure this exists to prevent.
        """
        if not isinstance(raw, dict):
            return {}
        out: dict[int, float] = {}
        for key, value in raw.items():
            try:
                hour = int(key)
                scale = float(value)
            except (TypeError, ValueError):
                continue
            if 0 <= hour <= 23:
                out[hour] = scale
        return out

    def _persist(self) -> None:
        # Snapshot before iterating: self.verdicts can be mutated from another
        # thread (e.g. /api/ai/clear on a request thread) while review() is
        # mid-cycle on the engine's background thread and about to persist -
        # this is the "dictionary changed size during iteration" crash seen in
        # the log, same class of race already fixed on the store.symbols loops.
        self.store.set_setting("supervisor_state", {
            "verdicts": {s: v.to_dict() for s, v in list(self.verdicts.items())},
            "risk_scale": self.risk_scale,
            "saved_at": time.time(),
        })

    def clear(self, symbol: str | None = None) -> None:
        with self._lock:
            if symbol:
                self.verdicts.pop(symbol, None)
            else:
                self.verdicts.clear()
                self.risk_scale = 1.0
            self._persist()
        LOG.emit(f"AI denetleyici sifirlandi{f' ({symbol})' if symbol else ''}.", "AI")

    # ---------------------------------------------------------------- gating

    def gate(self, cfg: SymbolConfig, server_now: float) -> tuple[bool, str, float]:
        """Return (allowed, reason, lot multiplier) for a prospective entry."""
        with self._lock:
            return self._gate_locked(cfg, server_now)

    def _gate_locked(self, cfg: SymbolConfig, server_now: float) -> tuple[bool, str, float]:
        verdict = self.verdicts.get(cfg.symbol)
        now = time.time()
        # Quarantine is a hard circuit breaker earned by realised results (a
        # losing streak or a collapsed profit factor), not a discretionary AI
        # opinion - it stays enforced even with the AI advisory layer turned
        # off. review() also keeps running regardless of ``enabled`` (see
        # ``due()``) so this state is never a stale snapshot from before AI
        # was disabled. Turning AI off only waives the *soft* layers below
        # (blocked hours, drawdown throttling, per-hour scaling).
        if verdict is not None and verdict.state == "quarantine":
            # Gate on the *state*, not the clock. quarantine_until firing does
            # not itself lift a quarantine - review() does, by reclassifying
            # away from "quarantine" once it re-checks the symbol. Between the
            # deadline passing and the next review the stored risk_scale is
            # still 0.0 from _quarantine(), and the floor below would have
            # turned that back into a live 10% entry the instant the clock
            # ticked over, before anything had actually re-earned the size.
            left = max(0, int((verdict.quarantine_until - now) / 60))
            return False, f"AI karantina {left}dk ({verdict.reason})", 0.0

        if not self.enabled:
            return True, "", 1.0
        if verdict is None:
            return True, "", self.risk_scale

        # Local time, not UTC: blocked_hours/_hour_risk_scales are bucketed
        # from deal timestamps via gmtime() too, but those raw MT5 deal times
        # are the broker's own clock reading (not true UTC) - and the broker
        # here runs on the same clock the user configures everything else
        # against (Windows/TR local). server_now() is now plain time.time()
        # with no offset applied, so gmtime() here would compare against true
        # UTC instead and silently gate the wrong hour of day.
        hour = time.localtime(server_now).tm_hour
        if hour in (verdict.blocked_hours or []):
            return False, f"AI: {hour:02d}:00 saati zararli", 0.0

        # Soft drawdown: keep watching every symbol, but only let the stronger
        # ones open new risk while the day is bleeding.
        if (self.settings.get("prefer_strong_on_dd") and self.risk_scale < 1.0
                and verdict.state in ("watch", "idle")):
            return False, "AI: gunluk kayipta zayif/ispatlanmamis sembol bekliyor", 0.0
        if (self.settings.get("prefer_strong_on_dd") and self.risk_scale < 1.0
                and verdict.trades >= int(self.settings["min_trades"])
                and verdict.expectancy < 0):
            return False, "AI: gunluk kayipta negatif sembol bekliyor", 0.0

        # Soft per-hour PF scaling: unlike blocked_hours this never refuses the
        # entry outright, it just shrinks size in hours that have run weak.
        hour_scale = float((verdict.hour_risk_scales or {}).get(hour, 1.0))
        return True, "", max(0.1, min(1.0, self.risk_scale * verdict.risk_scale * hour_scale))

    def priority(self, cfg: SymbolConfig, verdict: "SymbolVerdict | None" = None) -> float:
        """Higher score wins when several symbols race for the last free slots."""
        with self._lock:
            return self._priority_locked(cfg, verdict)

    def _priority_locked(self, cfg: SymbolConfig, verdict: "SymbolVerdict | None" = None) -> float:
        v = verdict if verdict is not None else self.verdicts.get(cfg.symbol)
        hold = (cfg.opt_summary or {}).get("holdout") or {}
        expected_r = float(hold.get("expectancy", 0.0) or 0.0)
        state_w = {"ok": 1.0, "idle": 0.55, "watch": 0.25, "quarantine": 0.0}
        live = 0.0
        if v and v.trades >= max(3, int(self.settings["min_trades"]) // 2):
            # Realised $/trade is noisy; compress into a small bonus/penalty.
            live = max(-1.0, min(2.0, v.expectancy / max(0.5, abs(v.expectancy) + 1.0)))
        score = expected_r * 2.0 + live + state_w.get(v.state if v else "idle", 0.5)
        if v:
            v.priority = round(score, 3)
        return score

    # ---------------------------------------------------------------- review

    def due(self) -> bool:
        # Reviews keep running - quarantine is a hard circuit breaker enforced
        # regardless of ``enabled`` (see ``gate()``), so its state must stay
        # live rather than freezing at whatever it was when AI was turned off.
        # Called directly from engine._cycle(), OUTSIDE the try/except that
        # wraps review() - web/app.py's /api/ai/settings now type-checks
        # against DEFAULTS before this can be reached, but a value that
        # somehow ends up non-numeric anyway (stale DB row from before that
        # check existed) must not raise here: that would silently cancel the
        # rest of THIS cycle too (new-entry evaluation included), every
        # single cycle, since the outer per-cycle handler only logs and
        # moves on rather than restoring the loop's later steps.
        try:
            interval = float(self.settings["review_interval_sec"])
        except (TypeError, ValueError):
            interval = float(DEFAULTS["review_interval_sec"])
        return (time.time() - self.last_review) >= interval

    def review(self, day_pnl_pct: float) -> dict[str, Any]:
        """Recompute every verdict from realised MT5 history."""
        cfgs = self.settings
        # MT5 round-trip stays outside the lock - it touches no shared state,
        # and holding the lock across a network call would stall clear()/
        # status()/settings requests for however long MT5 takes to answer.
        history = self._closed_trades(cfgs["lookback_days"])
        by_symbol: dict[str, list[dict[str, Any]]] = {}
        magic_map = {c.magic: c.symbol for c in list(self.store.symbols.values())}
        for deal in history:
            symbol = magic_map.get(deal["magic"])
            if symbol:
                by_symbol.setdefault(symbol, []).append(deal)

        with self._lock:
            self.last_review = time.time()
            self.notes = []

            self.risk_scale = self._drawdown_scale(day_pnl_pct, cfgs)
            if self.risk_scale < 1.0:
                self.notes.append(
                    f"Gunluk zarar %{abs(day_pnl_pct):.2f} -> lot carpani {self.risk_scale:.2f}")

            for cfg in list(self.store.symbols.values()):
                trades = sorted(by_symbol.get(cfg.symbol, []), key=lambda d: d["time"])
                self.verdicts[cfg.symbol] = self._judge(cfg, trades, cfgs)

            self._queue_reoptimization(cfgs)
            self._persist()
            return self._status_locked()

    def _closed_trades(self, lookback_days: int) -> list[dict[str, Any]]:
        since = self.client.server_now() - max(1, int(lookback_days)) * 86400
        # One entry per closed position, not per partial-TP fill - see
        # ``MT5Client.merge_round_trips``.
        return self.client.merge_round_trips(self.client.deals_since(since))

    def _drawdown_scale(self, day_pnl_pct: float, cfgs: dict[str, Any]) -> float:
        loss = -min(0.0, float(day_pnl_pct))
        soft, hard = float(cfgs["dd_soft_pct"]), float(cfgs["dd_hard_pct"])
        floor = float(cfgs["risk_scale_floor"])
        if loss <= soft or hard <= soft:
            return 1.0
        if loss >= hard:
            return floor
        span = (loss - soft) / (hard - soft)
        return round(1.0 - span * (1.0 - floor), 3)

    def _judge(self, cfg: SymbolConfig, trades: list[dict[str, Any]],
               cfgs: dict[str, Any]) -> SymbolVerdict:
        previous = self.verdicts.get(cfg.symbol)
        v = SymbolVerdict(symbol=cfg.symbol)
        if previous:
            v.quarantine_until = previous.quarantine_until
            v.blocked_hours = list(previous.blocked_hours or [])
            v.last_reopt_attempt = previous.last_reopt_attempt

        if not trades:
            v.state = "idle"
            v.reason = "gecmis islem yok"
            self._attach_expectation(cfg, v)
            v.priority = self.priority(cfg, v)
            if v.quarantine_until > time.time():
                v.state = "quarantine"
                v.reason = previous.reason if previous else "karantina"
            return v

        nets = [d["profit"] + d["commission"] + d["swap"] for d in trades]
        v.trades = len(nets)
        v.wins = sum(1 for x in nets if x >= 0)
        v.losses = v.trades - v.wins
        v.net = round(sum(nets), 2)
        # Through _pf, not a second copy of its arithmetic. The inline version
        # that used to live here returned the raw win SUM when nothing had
        # lost, so a flawless record was scored in account currency while
        # quarantine_pf and watch_pf below are ratios - and the fix applied to
        # _pf never reached the path that actually classifies live symbols.
        v.profit_factor = round(self._pf(nets), 2)
        v.expectancy = round(v.net / v.trades, 3)
        v.last_trade_at = float(trades[-1]["time"])

        streak = 0
        for x in reversed(nets):
            if x < 0:
                streak += 1
            else:
                break
        v.consecutive_losses = streak
        v.blocked_hours = self._bad_hours(trades, nets, cfgs)
        v.hour_risk_scales = self._hour_risk_scales(trades, nets, cfgs)
        self._attach_expectation(cfg, v)

        now = time.time()
        # Same "don't let a corrupted stored value crash the safety feature
        # that's supposed to protect the account" reasoning as due() above -
        # web/app.py's type check now blocks this at the door, this is only
        # for a row already bad before that existed.
        try:
            quarantine_secs = float(cfgs["quarantine_hours"]) * 3600.0
        except (TypeError, ValueError):
            quarantine_secs = float(DEFAULTS["quarantine_hours"]) * 3600.0

        if streak >= int(cfgs["quarantine_losses"]):
            self._quarantine(v, f"{streak} ust uste zarar", quarantine_secs, now)
        elif v.trades >= int(cfgs["min_trades"]) and v.profit_factor < float(cfgs["quarantine_pf"]):
            self._quarantine(v, f"PF {v.profit_factor:.2f} cok dusuk", quarantine_secs, now)
        elif v.quarantine_until > now:
            v.state = "quarantine"
            v.reason = previous.reason if previous else "karantina"
        # Two ways in, because a record can be too short to average and still
        # be long enough to read.
        #
        # The trade-count bar is right for an AVERAGE: profit factor over a
        # handful of trades is noise. It is the wrong bar for a COUNT. One win
        # in eleven is not a noisy average, it is an unlikely sequence - under a
        # coin-flip win rate the odds of one or fewer wins in eleven are about
        # six in a thousand. Between quarantine_losses, which is
        # count-independent but wants the losses consecutive, and this bar,
        # which wants twenty-five trades, "few trades and overwhelmingly bad"
        # fell through: USDCHF sat at one win in eleven, PF 0.35, -16.09, four
        # consecutive, trading at full scale, and would not have reached
        # twenty-five trades for another thirty-eight days.
        #
        # So the win count is read against its own sampling noise, the way
        # portfolio-gates already reads expectancy against 2*1.2/sqrt(n). Under
        # a break-even record the win count's standard deviation is sqrt(n)/2,
        # so two sigma below even is n/2 - sqrt(n). Under that, the record is
        # not thin - it is damning.
        #
        # profit_factor still has to be under watch_pf either way: a symbol
        # whose few wins are large enough to carry it is not losing money, and
        # a symbol losing on SIZE rather than frequency (FRA40: six wins, six
        # losses) is what the trade-count bar is there to judge.
        elif (v.profit_factor < float(cfgs["watch_pf"])
                and (v.trades >= int(cfgs.get("watch_min_trades", cfgs["min_trades"]))
                     or v.wins < v.trades / 2.0 - math.sqrt(v.trades))):
            v.state = "watch"
            v.risk_scale = float(cfgs["watch_risk_scale"])
            # Same PF gate as watch; richer reason when backtest still promised edge
            # so auto-reopt can pick these up under reopt_on_decay.
            if cfgs.get("reopt_on_decay") and v.expected_r >= 0.12:
                v.reason = (
                    f"kenar dustu (beklenen {v.expected_r:+.2f}R, "
                    f"canli PF {v.profit_factor:.2f})"
                )
            else:
                v.reason = f"PF {v.profit_factor:.2f} < 1.00, lot kisildi"
        else:
            v.state = "ok"
            if v.trades:
                v.reason = f"PF {v.profit_factor:.2f}"
                if v.edge_health > 0:
                    v.reason += f" | saglik %{v.edge_health * 100:.0f}"

        # Live PF edge-decay: only meaningful once a symbol was otherwise "ok" -
        # never upgrades out of quarantine and never overwrites the watch/quarantine
        # reason already picked above, it only downgrades a clean verdict.
        # Lowered from a hardcoded 30 to a tunable 20 (GER40: the regime clearly
        # turned inside its last ~10-15 trades, well before 30 would accumulate -
        # waiting the extra week+ to react cost more than the noisier smaller
        # halves below cost in false positives).
        if v.state == "ok" and len(nets) >= int(cfgs["edge_decay_min_trades"]):
            mid = len(nets) // 2
            older, recent = nets[:mid], nets[mid:]
            older_pf = self._pf(older)
            recent_pf = self._pf(recent)
            if older_pf > 0 and recent_pf < older_pf * 0.5 and recent_pf < 1.0:
                v.state = "watch"
                v.risk_scale = min(v.risk_scale, 0.5)
                v.reason = f"kenar zayifliyor (PF {older_pf:.2f} -> {recent_pf:.2f})"

        v.priority = self.priority(cfg, v)
        return v

    @staticmethod
    def _pf(nets: list[float]) -> float:
        """Profit factor of a run of trades, in money.

        With no losing trades the ratio is undefined, and returning the raw
        win SUM there - what this used to do - silently changes the unit of
        the answer. ``nets`` is currency (profit + commission + swap), so a
        loss-free run reported dollars while every caller compares the result
        against a ratio threshold of 1.0.

        The consequence is backwards, and reachable at the live settings:

          * _hour_risk_scales buckets an hour's trades over the whole lookback
            window and scales the hour down when ``pf < 1.0``. Six winning
            trades in that hour totalling $0.60 returned 0.60 and earned a
            size cut; the same six winners totalling $3.60 returned 3.60 and
            did not. Nothing but the dollar size of the wins decided it.
          * The edge-decay check fires on ``recent_pf < older_pf * 0.5 and
            recent_pf < 1.0``. A recent half of fifteen trades, ALL of them
            winners, totalling $0.75 returned 0.75 and tripped both halves -
            a perfect winning streak cut to half size.

        A loss-free run is the best possible outcome, so it returns a large
        finite value. Finite rather than ``inf`` on purpose: this number is
        serialised into /api/ai, and json.dumps writes ``Infinity``, which is
        not valid JSON and would break the panel that reads it.
        """
        win = sum(x for x in nets if x > 0)
        loss = -sum(x for x in nets if x < 0)
        if loss > 0:
            return win / loss
        return PF_NO_LOSSES if win > 0 else 0.0

    def _hour_risk_scales(self, trades: list[dict[str, Any]], nets: list[float],
                          cfgs: dict[str, Any]) -> dict[int, float]:
        """Soft per-hour PF-based size multiplier (never a hard block; see _bad_hours).

        Same evidence bar as _bad_hours (bad_hour_min_trades) - a lighter bar here
        just meant an isolated bad hour could earn a size cut off fewer trades than
        it would take to earn an outright block, which is backwards.
        """
        buckets: dict[int, list[float]] = {}
        for deal, net in zip(trades, nets):
            hour = time.gmtime(deal["time"]).tm_hour if deal["time"] > 0 else 0
            buckets.setdefault(hour, []).append(net)
        scales: dict[int, float] = {}
        for hour, values in buckets.items():
            if len(values) < int(cfgs["bad_hour_min_trades"]):
                continue
            pf = self._pf(values)
            if pf < 1.0:
                scales[hour] = round(max(0.3, pf), 3)
        return scales

    def _attach_expectation(self, cfg: SymbolConfig, v: SymbolVerdict) -> None:
        """Attach backtest expectancy and a simple live-health ratio (PF / 1.2)."""
        hold = (cfg.opt_summary or {}).get("holdout") or {}
        v.expected_r = float(hold.get("expectancy", 0.0) or 0.0)
        v.expected_per_trade = v.expected_r  # kept in R units for the AI table
        if v.trades >= int(self.settings["min_trades"]) and v.expected_r > 0:
            v.edge_health = round(max(0.0, min(3.0, v.profit_factor / 1.2)), 2)
        else:
            v.edge_health = 0.0

    def _quarantine(self, v: SymbolVerdict, reason: str, seconds: float, now: float) -> None:
        already = v.quarantine_until > now
        v.state = "quarantine"
        v.reason = reason
        v.risk_scale = 0.0
        if not already:
            v.quarantine_until = now + seconds
            hours = seconds / 3600.0
            LOG.emit(f"AI karantina: {reason} -> {hours:.0f} saat islem yok", "AI", v.symbol)
            self.notes.append(f"{v.symbol}: karantina ({reason})")

    def _bad_hours(self, trades: list[dict[str, Any]], nets: list[float],
                   cfgs: dict[str, Any]) -> list[int]:
        """Server-clock hours that lose persistently for this symbol."""
        buckets: dict[int, list[float]] = {}
        for deal, net in zip(trades, nets):
            hour = time.gmtime(deal["time"]).tm_hour if deal["time"] > 0 else 0
            buckets.setdefault(hour, []).append(net)

        blocked = []
        for hour, values in buckets.items():
            if len(values) < int(cfgs["bad_hour_min_trades"]):
                continue
            win = sum(x for x in values if x > 0)
            loss = -sum(x for x in values if x < 0)
            pf = win / loss if loss > 0 else (win if win > 0 else 0.0)
            if sum(values) < 0 and pf < float(cfgs["bad_hour_pf"]):
                blocked.append(hour)
        return sorted(blocked)

    def _queue_reoptimization(self, cfgs: dict[str, Any]) -> None:
        if not cfgs["auto_reoptimize"] or self.optimizer is None:
            return
        min_age = float(cfgs["reopt_min_age_hours"]) * 3600.0
        retry_cooldown = float(cfgs["reopt_retry_cooldown_hours"]) * 3600.0
        now = time.time()
        stale = []
        for v in list(self.verdicts.values()):
            cfg = self.store.symbols.get(v.symbol)
            if cfg is None or not cfg.enabled:
                continue
            age = now - (cfg.opt_updated_at or 0)
            if age < min_age:
                continue
            # A prior attempt that found nothing better never touches
            # opt_updated_at, so age alone would re-queue this symbol every
            # review cycle - wait out the cooldown before trying again.
            if now - v.last_reopt_attempt < retry_cooldown:
                continue
            broken = v.state == "quarantine"
            decayed = (cfgs.get("reopt_on_decay") and v.state == "watch"
                       and v.expected_r >= 0.12)
            if broken or decayed:
                stale.append(v.symbol)
        self.reopt_queue = stale
        if not stale or self.optimizer.busy:
            return
        for symbol in stale:
            v = self.verdicts.get(symbol)
            if v is not None:
                v.last_reopt_attempt = now
        LOG.emit(f"AI: kenari dusen semboller yeniden optimize ediliyor -> {', '.join(stale)}", "AI")
        self.optimizer.start(stale, apply_best=True)

    # ---------------------------------------------------------------- status

    def status(self) -> dict[str, Any]:
        with self._lock:
            return self._status_locked()

    def _status_locked(self) -> dict[str, Any]:
        now = time.time()
        rows = []
        for cfg in list(self.store.symbols.values()):
            v = self.verdicts.get(cfg.symbol)
            if v is None:
                v = SymbolVerdict(symbol=cfg.symbol, state="idle", reason="henuz degerlendirilmedi")
            row = v.to_dict()
            row["quarantine_left_min"] = max(0, int((v.quarantine_until - now) / 60))
            row["enabled"] = cfg.enabled
            # Ask the gate itself rather than recomputing its arithmetic here.
            # The old line multiplied risk_scale * verdict.risk_scale without
            # consulting self.enabled, so with the AI advisory layer switched
            # OFF - when _gate_locked returns a flat 1.0 for every symbol that
            # is not quarantined - the panel still showed every row throttled
            # to 0.4x/0.24x, complete with "kenar dustu" and "lot kisildi"
            # reasons. That reads as "the AI is holding the portfolio back"
            # when nothing is being held back at all. It also skipped the
            # gate's own [0.1, 1.0] clamp and its per-hour scaling, so the
            # number was wrong in the enabled case too. Deriving it from the
            # one function that decides means the display cannot drift from
            # the behaviour again.
            allowed, reason, scale = self._gate_locked(cfg, now)
            row["effective_scale"] = round(scale, 3)
            row["gate_allowed"] = allowed
            # Whether the per-hour rules below are actually in force. Both
            # blocked_hours and hour_risk_scales are consulted in _gate_locked
            # only AFTER the ``enabled`` check, so with the AI layer off they
            # are inert - but the panel listed them the same either way, which
            # reads as "this symbol is restricted at 10:00" when nothing is
            # restricting it. They are also re-derived from the trailing deal
            # window on every review() rather than counted down, so there is
            # no timer to show: the hour clears when its own trades stop
            # justifying it, not when a clock runs out.
            row["hours_enforced"] = self.enabled
            # Why an entry would be refused RIGHT NOW - distinct from
            # ``reason``, which explains the classification, not the block.
            row["gate_reason"] = reason
            rows.append(row)
        rows.sort(key=lambda r: ({"quarantine": 0, "watch": 1, "ok": 2, "idle": 3}[r["state"]], r["symbol"]))
        return {
            "enabled": self.enabled,
            "risk_scale": self.risk_scale,
            "last_review": self.last_review,
            "settings": self.settings,
            "notes": self.notes,
            "reopt_queue": self.reopt_queue,
            "symbols": rows,
            "counts": {
                state: sum(1 for r in rows if r["state"] == state)
                for state in ("ok", "watch", "quarantine", "idle")
            },
        }
