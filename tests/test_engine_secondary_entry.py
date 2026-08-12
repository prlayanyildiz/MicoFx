"""_try_entry: secondary fill whose broker ticket cannot be resolved.

open_market() can report ok=True with position=None (the fill's ticket could
not be read back). engine._try_entry then diffs same-magic positions before/
after the fill to find the new ticket. This covers the two ambiguous cases:
zero new tickets, and more than one - neither is the ordinary "exactly one
candidate" path that closes it and retries cleanly.
"""
from __future__ import annotations

import math
import threading
import time
from types import SimpleNamespace

from micofx.engine import Engine, SymbolState
from micofx.models import SymbolConfig
from micofx.risk import Verdict


class _FakeClient:
    def __init__(self, positions_after):
        self._positions_after = list(positions_after)
        self.closed: list[int] = []
        self.close_ok: set[int] = set()
        # DONE_PARTIAL: close_position returns True but ticket stays in the book.
        self.close_partial: set[int] = set()
        self.open_market_calls = 0
        self.connected = True

    def min_stop_distance(self, symbol):
        return 0.0001

    def tick(self, symbol):
        return {"ask": 1.1000, "bid": 1.0998, "spread": 0.0002}

    def server_now(self):
        import time
        return time.time()

    def open_market(self, symbol, side, lot, sl, tp, magic, slippage=0, comment=""):
        self.open_market_calls += 1
        return {"ok": True, "position": None, "requested": 1.1000, "price": 1.1000,
                "volume": lot, "sl": sl, "tp": tp, "partial_fill": False,
                "sl_tp_reanchored": True}

    def positions(self):
        return list(self._positions_after)

    def close_position(self, ticket, slippage_points, comment, volume=None, fill=None):
        self.closed.append(ticket)
        if ticket in self.close_partial:
            return True  # broker said ok, volume still open
        if ticket in self.close_ok:
            self._positions_after = [p for p in self._positions_after if p["ticket"] != ticket]
            return True
        return False

    def info(self, symbol):
        return {"point": 0.0001}

    def money_per_price_unit(self, symbol, volume):
        return 1.0


class _FakeRisk:
    def lot_for(self, cfg, sl_distance, balance, ai_scale=1.0):
        return 0.1, "ok"

    def can_open(self, cfg, side, lot, positions, account, sec_tickets=frozenset()):
        return Verdict(ok=True)


class _FakeSupervisor:
    def gate(self, cfg, server_now):
        return True, "", 1.0


class _FakeExecution:
    def record(self, *a, **kw):
        pass


class _FakeSymbols:
    def __init__(self, cfg):
        self._cfg = cfg

    def get(self, symbol):
        return self._cfg


class _FakeStore:
    def __init__(self, cfg):
        self.system = SimpleNamespace(slippage_points=5, block_high_cost=False,
                                       max_cost_pct_of_risk=0.0, trade_all_hours=True,
                                       daily_loss_flatten=False, day_end_flatten_min=0)
        self.symbols = _FakeSymbols(cfg)
        self.settings: dict = {}

    def opt_params(self):
        return {}

    def set_setting(self, key, value):
        self.settings[key] = value


def _make_engine(cfg, positions_after):
    client = _FakeClient(positions_after)
    store = _FakeStore(cfg)
    eng = object.__new__(Engine)
    eng.store = store
    eng.client = client
    eng.risk = _FakeRisk()
    eng.supervisor = _FakeSupervisor()
    eng.execution = _FakeExecution()
    eng.entry_lock = threading.Lock()
    eng._positions = []
    eng._sec_tickets = set()
    eng._sec_cfgs = {}
    eng._orphan_tickets = set()
    eng._orphan_scan = {}
    eng._link_backoff = {}   # real Engine always has it
    eng.states = {}
    eng._cooldowns = {}          # persisted post-fill cooldown; see Engine.__init__
    return eng, client, store


def _cfg():
    # crypto group so weekend_closed() never blocks the test regardless of
    # the day this runs on.
    return SymbolConfig(symbol="EURUSD", group="crypto", magic=1,
                        secondary_strategy="micro_rev", secondary_timeframe="M5",
                        ensemble_enabled=True)


def _state():
    st = SymbolState("EURUSD")
    st.signal = "buy"
    st.signal_source = "secondary"
    st.sec_atr = 0.001
    return st


def test_secondary_unresolved_ticket_zero_candidates_does_not_report_success():
    cfg = _cfg()
    # open_market reports ok, but positions() afterward shows nothing new for
    # this magic - zero candidates, even after the in-lock retries.
    eng, client, store = _make_engine(cfg, positions_after=[])
    state = _state()

    eng._try_entry(cfg, state, account={"balance": 1000.0})

    assert client.closed == []
    assert "cozulemedi" in state.note
    # Not treated as a successful fill: no cooldown, no signal-clear.
    assert state.cooldown_until == 0.0
    assert state.signal == "buy"
    # Sticky: persisted so a restart doesn't forget to keep scanning.
    assert "EURUSD" in eng._orphan_scan
    assert eng._orphan_scan["EURUSD"]["magic"] == 1
    assert store.settings["secondary_orphan_scan"] == eng._orphan_scan

    # H1: self._positions is stale (still shows nothing new for this magic -
    # that is exactly why the scan exists), so can_open()'s position-count
    # check cannot be trusted to block a duplicate order on the next poll.
    # The entry-time gate must refuse outright instead of calling
    # open_market() again.
    calls_before = client.open_market_calls
    eng._try_entry(cfg, state, account={"balance": 1000.0})
    assert client.open_market_calls == calls_before
    assert "taramasi devam ediyor" in state.note
    assert state.signal == "buy"  # still held, not consumed


def test_orphan_scan_block_lifts_once_scan_resolves():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[])
    state = _state()
    eng._try_entry(cfg, state, account={"balance": 1000.0})
    assert "EURUSD" in eng._orphan_scan

    # The delayed ticket finally shows up and gets closed by the scan.
    client.close_ok = {701}
    eng._positions = [{"ticket": 701, "magic": 1}]
    eng._scan_orphan_candidates()
    assert "EURUSD" not in eng._orphan_scan

    # Entry is unblocked again - open_market() gets called this time.
    calls_before = client.open_market_calls
    eng._try_entry(cfg, state, account={"balance": 1000.0})
    assert client.open_market_calls == calls_before + 1


def test_orphan_scan_abandon_after_stale_timeout_keeps_entry_blocked():
    # NOT-2: "abandoned" only stops actively re-diffing every cycle - it does
    # NOT reopen entry. The contradiction of "abandoned but entry still
    # open" is exactly what this is closing: the scan entry (and therefore
    # the _try_entry block) stays until it is fully dropped, never merely
    # because the stale timeout fired.
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[])
    eng._orphan_scan = {"EURUSD": {"magic": 1, "known": [], "since": 0.0}}  # ancient -> stale

    eng._scan_orphan_candidates()

    assert "EURUSD" in eng._orphan_scan  # kept around for the grace window
    assert eng._orphan_scan["EURUSD"]["abandoned"] is True

    # Entry stays blocked - abandoned or not, the scan entry is still there.
    state = _state()
    calls_before = client.open_market_calls
    eng._try_entry(cfg, state, account={"balance": 1000.0})
    assert client.open_market_calls == calls_before
    assert "taramasi devam ediyor" in state.note


def test_orphan_scan_entry_unblocked_only_after_final_drop():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[])
    eng._orphan_scan = {"EURUSD": {"magic": 1, "known": [], "since": 0.0,
                                   "abandoned": True, "abandoned_at": 0.0}}  # grace also expired

    eng._scan_orphan_candidates()

    assert "EURUSD" not in eng._orphan_scan  # fully dropped now
    state = _state()
    calls_before = client.open_market_calls
    eng._try_entry(cfg, state, account={"balance": 1000.0})
    assert client.open_market_calls == calls_before + 1


def test_orphan_scan_final_drop_does_a_last_look_and_closes_late_ticket():
    # M3: the exact cycle a scan would finally drop still gets one more
    # fresh positions() check before giving up, so a ticket that only
    # replicates that late is still caught instead of silently running
    # under the primary's exit params from then on.
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[
        {"ticket": 901, "magic": 1},
    ])
    eng._orphan_scan = {"EURUSD": {"magic": 1, "known": [], "since": 0.0,
                                   "abandoned": True, "abandoned_at": 0.0}}
    eng._positions = []  # this cycle's snapshot missed it...
    client.close_ok = {901}  # ...but the fresh client.positions() call sees it

    eng._scan_orphan_candidates()

    assert client.closed == [901]
    assert "EURUSD" not in eng._orphan_scan


def test_orphan_scan_final_drop_keeps_scan_when_positions_get_fails():
    # Mid-call positions_get failure → [] + connected=False must NOT be
    # treated as "never appeared" and drop the scan (would free magic /
    # reopen entry while a live fill may still exist).
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[])
    eng._orphan_scan = {"EURUSD": {"magic": 1, "known": [], "since": 0.0,
                                   "abandoned": True, "abandoned_at": 0.0}}

    def _fail_positions():
        client.connected = False
        return []

    client.positions = _fail_positions  # type: ignore[method-assign]

    eng._scan_orphan_candidates()

    assert "EURUSD" in eng._orphan_scan
    assert eng._orphan_scan["EURUSD"].get("abandoned") is True


def test_orphan_scan_final_drop_last_look_close_fails_goes_to_orphan_tickets():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[
        {"ticket": 902, "magic": 1},
    ])
    eng._orphan_scan = {"EURUSD": {"magic": 1, "known": [], "since": 0.0,
                                   "abandoned": True, "abandoned_at": 0.0}}
    eng._positions = []
    client.close_ok = set()  # close fails

    eng._scan_orphan_candidates()

    assert "EURUSD" not in eng._orphan_scan
    assert eng._orphan_tickets == {902}


def test_orphan_scan_abandoned_entry_still_closes_a_late_ticket():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[
        {"ticket": 801, "magic": 1},
    ])
    eng._orphan_scan = {"EURUSD": {"magic": 1, "known": [], "since": 0.0,
                                   "abandoned": True, "abandoned_at": time.time()}}
    eng._positions = client.positions()
    client.close_ok = {801}

    eng._scan_orphan_candidates()

    assert client.closed == [801]
    assert "EURUSD" not in eng._orphan_scan


def test_orphan_scan_fully_dropped_after_abandon_grace_expires():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[])
    eng._orphan_scan = {"EURUSD": {"magic": 1, "known": [], "since": 0.0,
                                   "abandoned": True, "abandoned_at": 0.0}}  # ancient

    eng._scan_orphan_candidates()

    assert "EURUSD" not in eng._orphan_scan


def test_secondary_single_candidate_found_via_retry_is_tagged_not_closed():
    cfg = _cfg()
    # Exactly one same-magic ticket appears - even though open_market()
    # couldn't resolve it directly, a clean single-candidate diff is now
    # trusted enough to tag rather than close.
    eng, client, store = _make_engine(cfg, positions_after=[
        {"ticket": 301, "magic": 1},
    ])
    state = _state()

    eng._try_entry(cfg, state, account={"balance": 1000.0})

    assert client.closed == []
    assert 301 in eng._sec_tickets
    # Normal successful-fill bookkeeping applies.
    assert state.cooldown_until > 0.0
    assert state.signal == ""
    assert state.note == "islem acildi"


def test_secondary_unresolved_ticket_multiple_candidates_closes_all():
    cfg = _cfg()
    # Two same-magic tickets appear after the fill - ambiguous, both are
    # closed for safety.
    eng, client, store = _make_engine(cfg, positions_after=[
        {"ticket": 101, "magic": 1}, {"ticket": 102, "magic": 1},
    ])
    client.close_ok = {101, 102}
    state = _state()

    eng._try_entry(cfg, state, account={"balance": 1000.0})

    assert set(client.closed) == {101, 102}
    assert "cozulemedi" in state.note
    # Both closed cleanly -> treated like a failed entry, safe to retry.
    assert state.cooldown_until == 0.0
    assert state.signal == ""
    assert state.pending_bar_key == (0, 0)
    assert eng._orphan_tickets == set()


def test_secondary_unresolved_ticket_multiple_candidates_partial_close_failure():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[
        {"ticket": 201, "magic": 1}, {"ticket": 202, "magic": 1},
    ])
    client.close_ok = {201}  # 202 fails to close

    state = _state()
    eng._try_entry(cfg, state, account={"balance": 1000.0})

    assert set(client.closed) == {201, 202}
    assert "cozulemedi" in state.note
    # Not all resolved: must not look like a normal successful fill.
    assert state.cooldown_until == 0.0
    assert state.signal == "buy"
    # Sticky ticket-level retry, persisted.
    assert eng._orphan_tickets == {202}
    assert store.settings["secondary_orphan_tickets"] == [202]


def test_manage_positions_retries_orphan_ticket_close_and_skips_normal_management():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[])
    eng._weekend_pending = set()
    eng._force_flat_pending = set()
    eng._partials = {}
    eng._stop_bar = {}
    # Position 401 is a previously-unresolved secondary ticket, still open.
    eng._positions = [{"ticket": 401, "magic": 1, "side": "buy", "volume": 0.1,
                       "time": 0, "profit": 0, "swap": 0}]
    eng._orphan_tickets = {401}
    client.close_ok = {401}

    # manage_positions() looks configs up via store.symbols.values()
    class _Values:
        def values(self):
            return [cfg]
    eng.store.symbols = _Values()

    eng.manage_positions(server_now=0.0)

    assert client.closed == [401]
    # Same cycle: prune ran before the close attempt - tracking stays until
    # the next cycle's live-book prune confirms the ticket is gone
    # (DONE_PARTIAL-safe sticky, same as weekend_pending).
    assert 401 in eng._orphan_tickets

    eng._positions = []
    eng.manage_positions(server_now=0.0)
    assert eng._orphan_tickets == set()
    assert store.settings["secondary_orphan_tickets"] == []


def test_manage_positions_orphan_retry_done_partial_keeps_tracking():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[])
    eng._weekend_pending = set()
    eng._force_flat_pending = set()
    eng._partials = {}
    eng._stop_bar = {}
    pos = {"ticket": 402, "magic": 1, "side": "buy", "volume": 0.2,
           "time": 0, "profit": 0, "swap": 0}
    eng._positions = [pos]
    eng._orphan_tickets = {402}
    client.close_partial = {402}

    class _Values:
        def values(self):
            return [cfg]
    eng.store.symbols = _Values()

    # Partial close returns True but leaves the ticket in the book.
    def _partial_close(ticket, slippage_points, comment, volume=None, fill=None):
        client.closed.append(ticket)
        if fill is not None:
            fill.update({"symbol": "EURUSD", "side": "buy", "requested": 1.1,
                         "price": 1.1, "volume": 0.05, "risk_dist": 0.0})
        return True

    client.close_position = _partial_close  # type: ignore[method-assign]

    eng.manage_positions(server_now=0.0)

    assert client.closed == [402]
    assert eng._orphan_tickets == {402}  # must NOT drop on DONE_PARTIAL True


def test_force_flat_pending_sticky_after_session_window(monkeypatch):
    # should_flatten True once → ticket enters sticky set; later when the
    # window is False, remainder must still retry (not fall into trail).
    from micofx import sessions as sessions_mod

    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[])
    eng._weekend_pending = set()
    eng._force_flat_pending = set()
    eng._partials = {}
    eng._stop_bar = {}
    eng._orphan_tickets = set()
    pos = {"ticket": 701, "magic": 1, "side": "buy", "volume": 0.2,
           "time": 0, "profit": 0, "swap": 0}
    eng._positions = [pos]

    class _Values:
        def values(self):
            return [cfg]
    eng.store.symbols = _Values()

    calls = {"n": 0}

    def _flatten(cfg, server_now, trade_all_hours):
        calls["n"] += 1
        return calls["n"] == 1  # only first cycle is "in window"

    monkeypatch.setattr(sessions_mod, "should_flatten", _flatten)
    monkeypatch.setattr(sessions_mod, "day_end_close", lambda *a, **k: False)
    monkeypatch.setattr(sessions_mod, "weekend_closed", lambda *a, **k: False)

    def _partial(ticket, slippage_points, comment, volume=None, fill=None):
        client.closed.append(ticket)
        if fill is not None:
            fill.update({"symbol": "EURUSD", "side": "buy", "requested": 1.1,
                         "price": 1.1, "volume": 0.05, "risk_dist": 0.0})
        return True

    client.close_position = _partial  # type: ignore[method-assign]

    eng.manage_positions(server_now=0.0)
    assert 701 in eng._force_flat_pending
    assert client.closed == [701]

    # Window expired - sticky set must still force close retry
    eng.manage_positions(server_now=0.0)
    assert client.closed == [701, 701]
    assert 701 in eng._force_flat_pending


def test_scan_orphan_candidates_finds_delayed_ticket_and_closes_it():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[
        {"ticket": 501, "magic": 1},
    ])
    eng._orphan_scan = {"EURUSD": {"magic": 1, "known": [], "since": 0.0}}
    eng._positions = client.positions()
    client.close_ok = {501}

    eng._scan_orphan_candidates()

    assert client.closed == [501]
    assert eng._orphan_scan == {}
    assert eng._orphan_tickets == set()


def test_try_entry_refuses_nan_atr():
    # NaN compares False to everything - a bare ``atr <= 0`` guard would let
    # it through silently and size sl_dist/tp_dist off garbage.
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[])
    state = _state()
    state.sec_atr = math.nan

    eng._try_entry(cfg, state, account={"balance": 1000.0})

    assert state.note == "ATR yok"
    assert client.open_market_calls == 0
    assert state.signal == "buy"  # untouched, not consumed as a failed attempt


def test_manage_positions_skips_secondary_trail_with_nan_sec_atr():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[])
    eng._weekend_pending = set()
    eng._force_flat_pending = set()
    eng._partials = {}
    eng._stop_bar = {}
    eng._orphan_tickets = set()
    eng._sec_tickets = {601}
    eng._positions = [{"ticket": 601, "magic": 1, "side": "buy", "volume": 0.1,
                       "time": 0, "profit": 0, "swap": 0}]

    class _Values:
        def values(self):
            return [cfg]
    eng.store.symbols = _Values()

    state = _state()
    state.sec_atr = math.nan
    state.atr = 0.002  # a healthy primary ATR that must NOT be substituted in
    eng.states = {"EURUSD": state}

    calls = []
    eng._update_stop = lambda *a, **kw: calls.append(a)

    eng.manage_positions(server_now=0.0)

    assert calls == []


def test_symbol_daily_halt_includes_commission_in_floating_side():
    # positions_get() has no live commission field (MT5 API limitation) -
    # the still-open round-turn cost is estimated from commission_per_lot so
    # the floating side lines up with how day_stats() nets realised trades.
    cfg = SymbolConfig(symbol="EURUSD", magic=1, symbol_daily_loss_pct=1.0,
                       commission_per_lot=50.0)
    eng = object.__new__(Engine)
    eng.risk = SimpleNamespace(daily=SimpleNamespace(start_balance=1000.0, day_key="2026-01-01"))
    eng._day_cache = {"per_symbol": []}
    eng._day_cache_at = 1e18  # force day_stats() to serve this cache as-is
    eng._symbol_halted = {}
    eng.store = SimpleNamespace(set_setting=lambda k, v: None)
    # Floating profit alone (before commission) sits just above the 1% cap;
    # 2 lots * 50/lot round-turn commission is what should push it over.
    eng._positions = [{"ticket": 1, "magic": 1, "volume": 2.0, "profit": -9.0, "swap": 0.0}]

    reason = eng._symbol_daily_halt(cfg)

    assert reason != ""
    assert "gunluk sembol zarar limiti" in reason


def test_symbol_daily_halt_stays_clear_without_commission_push():
    cfg = SymbolConfig(symbol="EURUSD", magic=1, symbol_daily_loss_pct=1.0,
                       commission_per_lot=50.0)
    eng = object.__new__(Engine)
    eng.risk = SimpleNamespace(daily=SimpleNamespace(start_balance=1000.0, day_key="2026-01-01"))
    eng._day_cache = {"per_symbol": []}
    eng._day_cache_at = 1e18
    eng._symbol_halted = {}
    eng.store = SimpleNamespace(set_setting=lambda k, v: None)
    # Tiny position: even with commission included, nowhere near the 1% cap.
    eng._positions = [{"ticket": 1, "magic": 1, "volume": 0.01, "profit": -1.0, "swap": 0.0}]

    assert eng._symbol_daily_halt(cfg) == ""


def test_symbol_daily_halt_is_sticky_across_floating_bounce():
    # NOT-1: once tripped, must not flip back off just because floating P/L on
    # this symbol recovers mid-cycle - only the day rollover clears it. This
    # is what manage_positions()'s flatten trigger now relies on (it just
    # calls _symbol_daily_halt(cfg) again - the stickiness lives here).
    cfg = SymbolConfig(symbol="EURUSD", magic=1, symbol_daily_loss_pct=1.0,
                       commission_per_lot=0.0)
    eng = object.__new__(Engine)
    eng.risk = SimpleNamespace(daily=SimpleNamespace(start_balance=1000.0, day_key="2026-01-01"))
    eng._day_cache = {"per_symbol": []}
    eng._day_cache_at = 1e18
    eng._symbol_halted = {}
    settings = {}
    eng.store = SimpleNamespace(set_setting=lambda k, v: settings.__setitem__(k, v))
    eng._positions = [{"ticket": 1, "magic": 1, "volume": 1.0, "profit": -20.0, "swap": 0.0}]

    first = eng._symbol_daily_halt(cfg)
    assert first != ""
    assert eng._symbol_halted["EURUSD"] == first
    assert settings["symbol_daily_halted"] == eng._symbol_halted

    # Floating recovers well above the -1% line.
    eng._positions = [{"ticket": 1, "magic": 1, "volume": 1.0, "profit": 5.0, "swap": 0.0}]
    second = eng._symbol_daily_halt(cfg)
    assert second == first  # sticky, not recomputed


def test_symbol_daily_halt_disabled_bypasses_existing_sticky_entry():
    cfg = SymbolConfig(symbol="EURUSD", magic=1, symbol_daily_loss_pct=0.0)
    eng = object.__new__(Engine)
    eng._symbol_halted = {"EURUSD": "gunluk sembol zarar limiti (5.00%)"}
    eng.store = SimpleNamespace(set_setting=lambda k, v: None)

    assert eng._symbol_daily_halt(cfg) == ""


def test_daily_rollover_clears_sticky_symbol_halts():
    eng = object.__new__(Engine)
    eng._symbol_halted = {"EURUSD": "gunluk sembol zarar limiti (5.00%)"}
    settings = {}
    eng.store = SimpleNamespace(set_setting=lambda k, v: settings.__setitem__(k, v))
    eng.risk = SimpleNamespace(daily=SimpleNamespace(rollover=lambda now, bal: True))

    eng._handle_daily_rollover(server_now=0.0, balance=1000.0)

    assert eng._symbol_halted == {}
    assert settings["symbol_daily_halted"] == {}


def test_daily_rollover_leaves_sticky_symbol_halts_when_same_day():
    eng = object.__new__(Engine)
    eng._symbol_halted = {"EURUSD": "gunluk sembol zarar limiti (5.00%)"}
    calls = []
    eng.store = SimpleNamespace(set_setting=lambda k, v: calls.append((k, v)))
    eng.risk = SimpleNamespace(daily=SimpleNamespace(rollover=lambda now, bal: False))

    eng._handle_daily_rollover(server_now=0.0, balance=1000.0)

    assert eng._symbol_halted == {"EURUSD": "gunluk sembol zarar limiti (5.00%)"}
    assert calls == []


def _pending_exits_engine(cfg, positions):
    eng = object.__new__(Engine)
    eng.entry_lock = threading.Lock()
    eng._positions = positions
    eng._sec_tickets = set()
    eng._orphan_tickets = set()
    eng._orphan_scan = {}
    eng._link_backoff = {}   # real Engine always has it
    updates = []
    eng.store = SimpleNamespace(
        symbols=SimpleNamespace(values=lambda: [cfg]),
        update_symbol=lambda symbol, patch: updates.append((symbol, patch)) or cfg,
    )
    return eng, updates


def test_apply_pending_exits_holds_back_primary_while_orphan_scan_pending():
    # M2: self._positions genuinely doesn't show this magic's fill yet (the
    # whole reason the scan exists), so without consulting _orphan_scan too
    # the magic reads as flat and the held-back patch lands prematurely.
    cfg = SymbolConfig(symbol="EURUSD", magic=1, pending_exit_patch={"sl_atr_mult": 2.0})
    eng, updates = _pending_exits_engine(cfg, positions=[])
    eng._orphan_scan = {"EURUSD": {"magic": 1, "known": [], "since": 0.0}}

    eng._apply_pending_exits()

    assert updates == []


def test_apply_pending_exits_lands_once_orphan_scan_clears():
    cfg = SymbolConfig(symbol="EURUSD", magic=1, pending_exit_patch={"sl_atr_mult": 2.0})
    eng, updates = _pending_exits_engine(cfg, positions=[])
    eng._orphan_scan = {}  # resolved/dropped
    eng._link_backoff = {}   # real Engine always has it

    eng._apply_pending_exits()

    assert len(updates) == 1
    assert updates[0][1]["sl_atr_mult"] == 2.0


def test_apply_pending_exits_holds_back_secondary_while_orphan_ticket_open():
    # An orphan ticket is a real MT5 position (untagged, being retried for
    # close) - not in _sec_tickets, so the old sec_open_magics computation
    # missed it entirely.
    cfg = SymbolConfig(symbol="EURUSD", magic=1,
                       pending_secondary_exit_patch={"trail_start_atr": 1.5})
    eng, updates = _pending_exits_engine(cfg, positions=[{"ticket": 401, "magic": 1}])
    eng._orphan_tickets = {401}

    eng._apply_pending_exits()

    assert updates == []


def test_apply_pending_exits_secondary_lands_when_no_orphan_risk():
    cfg = SymbolConfig(symbol="EURUSD", magic=1,
                       pending_secondary_exit_patch={"trail_start_atr": 1.5})
    eng, updates = _pending_exits_engine(cfg, positions=[])

    eng._apply_pending_exits()

    assert len(updates) == 1
    assert updates[0][1]["secondary_params"]["trail_start_atr"] == 1.5


def test_orphan_close_done_partial_keeps_ticket_in_orphan_tracking():
    # close_position True for DONE_PARTIAL must NOT be treated as fully flat -
    # re-diff the live book; still-open tickets go to orphan_tickets.
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[
        {"ticket": 601, "magic": 1},
    ])
    eng._orphan_scan = {"EURUSD": {"magic": 1, "known": [], "since": 0.0}}
    eng._positions = client.positions()
    client.close_partial = {601}

    eng._scan_orphan_candidates()

    assert client.closed == [601]
    assert "EURUSD" not in eng._orphan_scan
    assert eng._orphan_tickets == {601}
    assert store.settings["secondary_orphan_tickets"] == [601]


def test_entry_multi_candidate_done_partial_not_orphan_closed():
    cfg = _cfg()
    eng, client, store = _make_engine(cfg, positions_after=[
        {"ticket": 611, "magic": 1}, {"ticket": 612, "magic": 1},
    ])
    client.close_partial = {611, 612}
    state = _state()

    eng._try_entry(cfg, state, account={"balance": 1000.0})

    assert set(client.closed) == {611, 612}
    assert state.signal == "buy"  # not consumed as "fully flat"
    assert eng._orphan_tickets == {611, 612}
