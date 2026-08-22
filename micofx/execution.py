"""Execution-quality tracking: what the bot asked for versus what it got.

Everything upstream of this file - the walk-forward, the apply gates, the cost
model - reasons about a trade in R multiples off a *modelled* fill: signal on a
closed bar, filled at the next bar's open, full spread charged. Nothing in that
chain can see slippage, because slippage does not exist in a bar replay. On a
scalp that is a real hole: when the target is one or two ATR of an M5 candle, a
few tenths of a pip of adverse fill on entry and again on exit is a double-digit
percentage of the edge, and it never shows up as a losing backtest - it shows up
as a live account that quietly underperforms its own holdout.

So this module measures it directly, in the same unit the rest of the system
speaks:

  * **entry fills** - the requested price is the tick the order was built from
    and the filled price comes back on the order result, so the comparison is
    exact and is recorded at the moment of the fill;
  * **our own closes** - same thing on the way out (session flatten, day-end
    flatten, daily-loss flatten);
  * **broker-side stop/target fills** - the expected price is the SL or TP that
    was on the position the last time the engine saw it (so a trailed stop is
    compared against where it actually sat, not against where it started), and
    the realised price is the volume-weighted close across the broker's chunks,
    not the last print (that last print is often the stop level itself).

Sign convention: ``adverse`` is positive when the fill was *worse* for the
account. A buy filling higher than requested is adverse; a sell filling lower is
adverse; the same holds for the closing leg, whose direction is the opposite of
the position's side.

Two published-practice readings come out of it. The first is size: mean adverse
slippage expressed as a fraction of that trade's own risk distance, which is
directly comparable to ``MAX_COST_PER_TRADE_R``. The second is *symmetry* -
honest execution produces roughly as many favourable fills as adverse ones, and
a persistent skew is a broker/latency finding rather than a strategy one.

Nothing here gates or blocks a trade. It is measurement: a silent edge leak is
only fixable once it is visible.
"""
from __future__ import annotations

import math
import statistics
import time
from typing import Any

from .logbus import LOG

# MT5 deal reason codes for a close this engine did not order. The first three
# are the server acting on its own (SO is the broker's margin stop-out); the
# rest are a human closing the position by hand, from the terminal, the phone
# or the web client.
#
# Those three used to be absent from the filter below, so a hand-closed
# position produced no report and therefore no log line at all - it simply
# stopped being tracked. The count is what surfaced it: thirty-four closes on
# the panel against twenty-nine in the log for the same day, and the five were
# closes made by hand. Every loss attribution built off that log was quietly
# short by them.
#
# EXPERT (3) stays out on purpose: that is this engine's own close_all/panel
# routes, which already report, and a foreign EA's deals are dropped by the
# magic filter in _log_broker_exit anyway.
DEAL_REASON_CLIENT = 0
DEAL_REASON_MOBILE = 1
DEAL_REASON_WEB = 2
DEAL_REASON_SL = 4
DEAL_REASON_TP = 5
DEAL_REASON_SO = 6

_CLOSED_ELSEWHERE = (DEAL_REASON_SL, DEAL_REASON_TP, DEAL_REASON_SO,
                     DEAL_REASON_CLIENT, DEAL_REASON_MOBILE, DEAL_REASON_WEB)

# Human labels for the exit reports below.
_REASON_LABEL = {
    DEAL_REASON_SL: "stop",
    DEAL_REASON_TP: "hedef",
    DEAL_REASON_SO: "broker marj kapatmasi",
    DEAL_REASON_CLIENT: "elle (terminal)",
    DEAL_REASON_MOBILE: "elle (mobil)",
    DEAL_REASON_WEB: "elle (web)",
}

# Per-symbol rolling sample window. Long enough for the symmetry read below to
# mean something, short enough that a broker that fixed its routing last month
# is not judged forever on last month.
MAX_SAMPLES = 400

# Below this many samples a per-symbol number is noise and is reported but never
# warned on.
MIN_SAMPLES_FOR_VERDICT = 25

# Mean adverse slippage above this fraction of the trade's own risk is worth
# saying out loud: at 5% of R it is already a fifth of the cost budget the
# optimizer's apply gate allows for spread plus commission combined.
WARN_ADVERSE_R = 0.05

# Execution-fairness read used in practice: on a large sample a fair venue fills
# roughly as often against you as for you. Well past parity - adverse fills more
# than this multiple of favourable ones - points at routing, not at strategy.
MAX_ADVERSE_RATIO = 3.0
MIN_SAMPLES_FOR_SYMMETRY = 100

# Reported when literally every fill came out against us and none for us: the
# most one-sided a venue can be. A finite stand-in rather than inf because this
# is serialised into /api/state and json.dumps writes ``Infinity``.
RATIO_ALL_ADVERSE = 99.0

# How often a repeated finding may be logged again, so a bad venue does not
# flood the log on every review.
_WARN_COOLDOWN = 3600.0

# How many cycles a closed ticket may go unmatched in the deal history before
# its bookkeeping is dropped. A position leaves positions_get() the instant it
# closes, but its deal reaches history_deals_get() a moment later - the fill
# path already documents that lag and carries a fallback for it. reap() used
# to pop the tracker slot before checking whether the deal had arrived, so a
# close caught in that gap lost its MFE/MAE and fill metadata permanently and
# was never reported at all: no log line, no autopsy row, no slippage sample.
# It is the same shape as the hand-closed positions this module already fixed
# once, and it lands in exactly the table the loss analysis reads.
#
# The retry is only armed when the position has NO deal in the window at all.
# A close this engine ordered does have deals, just none with a broker-side
# reason, and that is the normal case - retrying those would query history
# twenty times over for every ordinary exit.
MAX_REAP_TRIES = 20


def _usable_sample(row: Any) -> bool:
    """Whether a restored sample row can survive ``_summarise``.

    ``_summarise`` reads ``row["adverse"]`` and ``row["leg"]`` without a
    default - correctly, because ``record()`` always writes both, and the
    optional fields (``r``, ``money``) are already guarded with ``in`` checks.
    The gap is on the way back in: ``_restore`` filtered rows to ``isinstance(
    r, dict)`` and stopped there, so a row missing either key reached
    ``_summarise`` and raised KeyError.

    That matters more than where it sits: ``stats()`` is called by /api/state
    on every panel poll, so one malformed row does not degrade the execution
    view, it takes the whole panel down with a 500.

    Nothing the current ``record()`` writes can fail this. It is for a blob
    restored from a backup written by an older row shape, or a hand-edited
    row - the same class the store's own shape guards cover for containers,
    applied here to the elements.
    """
    if not isinstance(row, dict):
        return False
    adverse = row.get("adverse")
    if not isinstance(adverse, (int, float)) or isinstance(adverse, bool):
        return False
    if not math.isfinite(float(adverse)):
        # A NaN sorts into neither the adverse nor the favourable bucket and
        # then poisons every mean computed from the set.
        return False
    return isinstance(row.get("leg"), str)


class ExecutionMonitor:
    """Rolling requested-vs-filled statistics, per symbol and overall.

    Thread confinement: every mutating call is made from the engine's single
    poll thread. ``stats()`` is read from the web thread and only ever copies.
    """

    def __init__(self, store) -> None:
        self.store = store
        # symbol -> list of sample dicts (newest last)
        self._samples: dict[str, list[dict[str, Any]]] = {}
        # ticket -> what the engine last knew about an open position, so a
        # server-side stop/target fill can be scored after the position is gone
        self._open: dict[int, dict[str, Any]] = {}
        self._warned_at: dict[str, float] = {}
        self._dirty = 0
        self._restore()

    # ------------------------------------------------------------ persistence

    def _restore(self) -> None:
        blob = self.store.get_setting("execution_samples") or {}
        # Symbols that have left the portfolio are dropped, the same way
        # engine._flush_spread_ratio drops them from its histogram and for the
        # same reason: stats() aggregates every row into one portfolio number,
        # so samples from instruments nobody trades any more keep shaping the
        # figure that answers "is our execution any good". Measured 22.08 -
        # four deleted symbols held 96 of 575 rows, 17% of the whole sample.
        # (The effect on the number was 0.0002 R against a 0.05 R warning
        # threshold, so nothing was ever misjudged; the share is the problem,
        # not today's answer.) drop_symbol already prunes on the delete path;
        # this covers rows that arrived before it did, or a book edited around
        # the API.
        #
        # Guarded on a non-empty book: Store.__init__ loads symbols and seeds
        # them when the table is empty, so this cannot normally be blank - but
        # wiping every stored sample because a lookup came back empty is not a
        # failure worth risking for a tidy-up.
        live = set(getattr(self.store, "symbols", None) or ())
        if isinstance(blob, dict):
            for symbol, rows in blob.items():
                if live and str(symbol) not in live:
                    continue
                if isinstance(rows, list):
                    kept = [r for r in rows[-MAX_SAMPLES:] if _usable_sample(r)]
                    if kept:
                        self._samples[str(symbol)] = kept

    def _persist(self, force: bool = False) -> None:
        # Writing every sample would put an SQLite round trip on the fill path;
        # a batch of twenty is still at most twenty lost samples after a crash.
        self._dirty += 1
        if not force and self._dirty < 20:
            return
        self._dirty = 0
        self.store.set_setting("execution_samples",
                               {s: rows[-MAX_SAMPLES:] for s, rows in self._samples.items()})

    # --------------------------------------------------------------- recording

    @staticmethod
    def _adverse(requested: float, filled: float, deal_is_buy: bool) -> float:
        """Signed price slippage, positive when the fill was worse for us."""
        return (filled - requested) if deal_is_buy else (requested - filled)

    def record(self, symbol: str, leg: str, requested: float, filled: float,
               deal_is_buy: bool, risk_dist: float = 0.0, point: float = 0.0,
               volume: float = 0.0, money_per_price: float = 0.0) -> None:
        """Store one requested-vs-filled observation.

        ``risk_dist`` is the trade's stop distance in price units; when it is
        known the sample also carries the slippage in R, which is the only form
        comparable across symbols. ``leg`` is one of ``entry`` / ``exit`` /
        ``stop`` / ``target`` and is kept so entry and exit quality can be read
        apart - they have different causes.
        """
        if requested <= 0 or filled <= 0:
            return
        adverse = self._adverse(float(requested), float(filled), bool(deal_is_buy))
        row: dict[str, Any] = {
            "t": round(time.time(), 1), "leg": str(leg),
            "adverse": float(adverse),
            "points": round(adverse / point, 2) if point > 0 else 0.0,
        }
        if risk_dist > 0:
            row["r"] = round(adverse / risk_dist, 5)
        if money_per_price > 0 and volume > 0:
            row["money"] = round(-adverse * money_per_price, 4)
        rows = self._samples.setdefault(symbol, [])
        rows.append(row)
        if len(rows) > MAX_SAMPLES:
            del rows[:-MAX_SAMPLES]
        self._persist()
        self._maybe_warn(symbol)

    # ------------------------------------------------ server-side exit tracking

    def track(self, positions: list[dict[str, Any]]) -> set[int]:
        """Refresh the open-position snapshot; return tickets that just closed.

        The snapshot carries the *current* SL/TP, so a stop that has been
        trailed forward is later compared against where it actually stood.
        ``risk_dist`` is deliberately written only on first sight - that is the
        cycle right after the fill, while the stop is still the original one the
        position was sized against - so trailing cannot shrink the R the sample
        is later expressed in.
        """
        seen: set[int] = set()
        for pos in positions:
            ticket = int(pos["ticket"])
            seen.add(ticket)
            book = self._open.setdefault(ticket, {})
            book.update({
                "symbol": pos["symbol"], "side": pos["side"], "sl": float(pos["sl"]),
                "tp": float(pos["tp"]), "entry": float(pos["price_open"]),
                "magic": int(pos["magic"]),
            })
            book.setdefault("risk_dist", abs(float(pos["price_open"]) - float(pos["sl"]))
                            if pos["sl"] else 0.0)
            # First-sight stop, frozen the same way as risk_dist: a later trail
            # must not rewrite "did this close at the original SL or a moved
            # one". 0 means the broker had no stop on first sight.
            book.setdefault("original_sl", float(pos["sl"]) if pos["sl"] else 0.0)
            book.setdefault("opened_at", int(pos.get("time") or 0))
            # Peak excursion from entry, in price. Divided by this trade's own
            # frozen risk_dist at close. Trailing must not shrink that R.
            cur = float(pos.get("price_current") or 0)
            entry = float(pos.get("price_open") or 0)
            if cur > 0 and entry > 0:
                fav = (cur - entry) if pos["side"] == "buy" else (entry - cur)
                book["mfe"] = max(float(book.get("mfe") or 0.0), max(0.0, fav))
                book["mae"] = max(float(book.get("mae") or 0.0), max(0.0, -fav))
        return set(self._open) - seen

    def note_fill(self, ticket: int, **meta: Any) -> None:
        """Attach fill-time facts the close path will not see again.

        Called from the engine on a successful open, while signal-bar close,
        spread and ADX are still on the symbol state. ``track()`` later
        refreshes SL/TP/MFE but never overwrites these keys.
        """
        book = self._open.setdefault(int(ticket), {})
        for key, value in meta.items():
            if value is None:
                continue
            book.setdefault(key, value)

    def snapshot(self, ticket: int) -> dict[str, Any] | None:
        """Copy of the open book for one ticket, or None. Does not pop."""
        book = self._open.get(int(ticket))
        return dict(book) if book else None

    def reap(self, gone: set[int], deals: list[dict[str, Any]],
             client) -> list[dict[str, Any]]:
        """Report every close this engine did not order, and score the ones
        that can be scored.

        Two scopes, and they are no longer the same one. What is MEASURED is
        unchanged: only a server-generated stop or target builds a slippage
        sample, because that is the only case with a price of ours to compare
        the fill against. A close the engine sent was already recorded against
        its own requested tick, and counting it twice would double the sample.

        What is REPORTED is wider. A position closed by hand - from the
        terminal, the phone or the web client - used to match nothing here and
        left no record at all, which is how a day showed thirty-four closes on
        the panel against twenty-nine in the log. It is reported now and scored
        never: there is no requested price behind it to measure. That report is the *only* record a stop exit leaves: the
        engine logs its own closes at the moment it sends them, but a hard SL
        firing at the broker happens with nothing running here - and since a
        stop is this system's one and only intended exit, without this the
        normal way a trade ends is the one event the log never mentions.
        Reported even when the slippage sample below cannot be built (no
        remembered SL/TP), because "the trade is gone" is the part the operator
        needs regardless.
        """
        # All the broker-generated closing deals per position, not just one: a
        # stop can fill in chunks, and keeping only the last of them reported a
        # fraction of the lot beside a P/L covering the whole position - a log
        # line internally inconsistent with itself. Volume is summed and the
        # price is volume-weighted across the chunks.
        closers: dict[int, list[dict[str, Any]]] = {}
        for deal in deals:
            if int(deal.get("reason", -1)) in _CLOSED_ELSEWHERE:
                closers.setdefault(int(deal["position"]), []).append(deal)
        # Net realised P/L is the whole round trip, not the closing deals'
        # ``profit`` alone - commission (which some brokers charge on the entry
        # leg) and accumulated swap are just as real to the balance.
        net: dict[int, float] = {}
        for deal in deals:
            pos = int(deal["position"])
            net[pos] = net.get(pos, 0.0) + float(deal.get("profit", 0.0)) \
                + float(deal.get("commission", 0.0)) + float(deal.get("swap", 0.0))

        reports: list[dict[str, Any]] = []
        for ticket in gone:
            chunks = closers.get(int(ticket))
            if not chunks:
                # No broker-side closing deal. Two very different reasons, and
                # popping the slot for both is what lost the report.
                book = self._open.get(int(ticket))
                if book is not None and int(ticket) not in net:
                    # Not a single deal for this position in a two-hour
                    # window: the close is real (it left positions_get) but
                    # history has not caught up. Keep the slot and try again
                    # next cycle - ``track`` re-lists it in ``gone`` for as
                    # long as it stays here.
                    tries = int(book.get("reap_tries", 0)) + 1
                    book["reap_tries"] = tries
                    if tries < MAX_REAP_TRIES:
                        continue
                    LOG.emit(f"#{ticket} kapandi ama {MAX_REAP_TRIES} dongu boyunca "
                             f"islem gecmisinde eslesmedi - kayit dusuruldu "
                             f"(otopsi/kayma ornegi yok)", "WARN")
                # Either the engine ordered this close itself (deals exist,
                # none broker-side - the ordinary case, already recorded
                # against its own requested tick) or the budget ran out.
                self._open.pop(int(ticket), None)
                continue
            book = self._open.pop(int(ticket), None)
            deal = chunks[-1]
            reason = int(deal["reason"])
            volume = sum(float(d.get("volume", 0.0)) for d in chunks)
            if volume > 0:
                price = sum(float(d["price"]) * float(d.get("volume", 0.0))
                            for d in chunks) / volume
            else:
                price = float(deal["price"])
            reports.append({
                "ticket": int(ticket),
                "symbol": (book or {}).get("symbol") or deal["symbol"],
                "magic": int((book or {}).get("magic", deal.get("magic", 0))),
                "reason": reason,
                "label": _REASON_LABEL.get(reason, "broker"),
                "price": price,
                "volume": volume,
                "profit": round(net.get(int(ticket), float(deal.get("profit", 0.0))), 2),
                "time": int(deal.get("time") or 0),
                # Copy, not the live dict: this report is the last moment the
                # close path can still see MFE/MAE/fill metadata. The pop
                # above already dropped the tracker slot.
                "book": dict(book) if book else {},
            })
            if not book:
                continue
            is_stop = reason == DEAL_REASON_SL
            expected = book["sl"] if is_stop else book["tp"]
            if reason == DEAL_REASON_SO or expected <= 0:
                # A margin stop-out has no requested price of ours to compare
                # against, so it is reported but never scored as slippage.
                continue
            info = client.info(book["symbol"]) or {}
            # Score the same VWAP the log already reports. The last chunk's
            # print is often the stop level itself; using it made every
            # multi-print stop look like a perfect fill.
            self.record(
                book["symbol"], "stop" if is_stop else "target",
                expected, float(price),
                # The closing leg trades the opposite way to the position.
                deal_is_buy=(book["side"] == "sell"),
                risk_dist=float(book.get("risk_dist", 0.0)),
                point=float(info.get("point", 0.0) or 0.0),
                volume=float(volume),
                money_per_price=client.money_per_price_unit(book["symbol"],
                                                            float(volume)),
            )
        return reports

    def forget(self, gone: set[int]) -> None:
        """Drop bookkeeping for closes we could not attribute to a deal.

        Skips the ones ``reap`` is still waiting on. Those left positions_get
        without any deal reaching history yet, and dropping them here would
        undo the retry a line after it was armed - the engine calls this
        immediately after reap, with the same set.
        """
        for ticket in gone:
            book = self._open.get(int(ticket))
            if book is not None and 0 < int(book.get("reap_tries", 0)) < MAX_REAP_TRIES:
                continue
            self._open.pop(int(ticket), None)

    def drop_symbol(self, symbol: str) -> None:
        """Discard slippage samples for a symbol removed from the portfolio."""
        self._samples.pop(symbol, None)
        self._warned_at.pop(symbol, None)
        self._persist(force=True)

    # ----------------------------------------------------------------- reading

    @staticmethod
    def _summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {"samples": 0}
        adverse = [r for r in rows if r["adverse"] > 0]
        favourable = [r for r in rows if r["adverse"] < 0]
        points = [float(r.get("points", 0.0)) for r in rows]
        r_vals = [float(r["r"]) for r in rows if "r" in r]
        money = [float(r.get("money", 0.0)) for r in rows if "money" in r]
        # A fill landing exactly on the requested price is neither adverse nor
        # favourable, so with no favourable fills at all there is no multiple to
        # take and the count alone would say nothing about one-sidedness - it
        # would only grow with the window. Compare instead against everything
        # that did not go against us, which is the same question the ratio asks.
        if favourable:
            ratio = len(adverse) / len(favourable)
        elif not adverse:
            ratio = 0.0
        elif len(adverse) < len(rows):
            ratio = len(adverse) / (len(rows) - len(adverse))
        else:
            ratio = RATIO_ALL_ADVERSE
        return {
            "samples": len(rows),
            "adverse": len(adverse),
            "favourable": len(favourable),
            "adverse_ratio": round(ratio, 2),
            "mean_points": round(statistics.fmean(points), 3) if points else 0.0,
            "median_points": round(statistics.median(points), 3) if points else 0.0,
            "worst_points": round(max(points), 3) if points else 0.0,
            "mean_r": round(statistics.fmean(r_vals), 4) if r_vals else 0.0,
            "money": round(sum(money), 2) if money else 0.0,
            "legs": {leg: sum(1 for r in rows if r["leg"] == leg)
                     for leg in sorted({r["leg"] for r in rows})},
        }

    def stats(self) -> dict[str, Any]:
        """Per-symbol and portfolio-wide execution quality, JSON safe."""
        # Snapshot before iterating: read from the web thread, mutated from the
        # engine thread (record() can setdefault() a brand-new symbol key) -
        # confinement on writes doesn't make a concurrent structural mutation
        # safe to iterate over on the reader's side. Same race already fixed
        # on supervisor.verdicts / store.symbols.
        samples = list(self._samples.items())
        per_symbol = {s: self._summarise(rows) for s, rows in samples if rows}
        every = [r for _, rows in samples for r in rows]
        total = self._summarise(every)
        total["flagged"] = sorted(s for s, v in per_symbol.items() if self._verdict(v))
        return {"total": total, "per_symbol": per_symbol, "tracked": len(self._open)}

    @staticmethod
    def _verdict(summary: dict[str, Any]) -> str:
        """Why this symbol's execution is worth a look; "" when it is fine."""
        n = int(summary.get("samples", 0))
        if n >= MIN_SAMPLES_FOR_VERDICT and float(summary.get("mean_r", 0.0)) > WARN_ADVERSE_R:
            return (f"ortalama kayma riskin %{float(summary['mean_r']) * 100:.1f}'i "
                    f"({n} ornek)")
        if (n >= MIN_SAMPLES_FOR_SYMMETRY
                and float(summary.get("adverse_ratio", 0.0)) > MAX_ADVERSE_RATIO):
            return (f"kayma tek yonlu: aleyhte/lehte {summary['adverse_ratio']:.1f}x "
                    f"({n} ornek)")
        return ""

    def _maybe_warn(self, symbol: str) -> None:
        reason = self._verdict(self._summarise(self._samples.get(symbol) or []))
        if not reason:
            return
        if time.time() - self._warned_at.get(symbol, 0.0) < _WARN_COOLDOWN:
            return
        self._warned_at[symbol] = time.time()
        LOG.emit(f"Gerceklesme kalitesi dusuk - {reason}. Backtest bu kaymayi "
                 f"modellemez; canli sonuc test segmentinin altinda kalabilir.",
                 "WARN", symbol)

    def flush(self) -> None:
        self._persist(force=True)
