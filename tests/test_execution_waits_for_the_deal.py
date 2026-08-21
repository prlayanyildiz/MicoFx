"""A close is not forgotten just because its deal has not landed yet.

A position leaves ``positions_get()`` the instant it closes; its deal reaches
``history_deals_get()`` a moment later, and the fill path already documents
that lag and carries a fallback for it. ``reap()`` popped the tracker slot
before checking whether the deal had arrived, so a close caught in that gap
lost its MFE/MAE and fill metadata for good and produced no report at all -
no log line, no autopsy row, no slippage sample. That is a hole in the exact
table the loss analysis reads.

The retry has to discriminate, though: a close the engine ordered itself has
deals in the window, just none with a broker-side reason, and that is the
ordinary exit. Only a position with no deal at all is waiting on history.
"""
from micofx.execution import MAX_REAP_TRIES, ExecutionMonitor


class _Store:
    def __init__(self) -> None:
        self.settings: dict = {}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


class _Client:
    def info(self, symbol):
        return {"point": 0.1}

    def money_per_price_unit(self, symbol, volume):
        return 1.0


def _pos(ticket=901, sl=99.0):
    return {"ticket": ticket, "symbol": "GER40", "side": "buy", "sl": sl,
            "tp": 0.0, "price_open": 100.0, "magic": 7, "time": 0,
            "price_current": 101.0}


def _monitor():
    mon = ExecutionMonitor(_Store())
    mon.track([_pos()])
    mon.note_fill(901, entry_spread=1.25)
    return mon


def _stop_deal(ticket=901, price=99.0):
    return {"position": ticket, "reason": 4, "volume": 0.1, "price": price,
            "symbol": "GER40", "profit": -10.0, "commission": 0.0,
            "swap": 0.0, "time": 5, "magic": 7}


def test_a_close_whose_deal_has_not_propagated_is_retried_not_dropped():
    mon = _monitor()
    gone = mon.track([])                      # position vanished from the book
    assert gone == {901}

    # History is empty this cycle - the deal has not landed.
    assert mon.reap(gone, [], _Client()) == []
    mon.forget(gone)
    assert 901 in mon._open, "eslesmeyen ticket dusurulmemeli"
    assert mon._open[901].get("entry_spread") == 1.25

    # Next cycle it arrives, and the report carries the metadata that would
    # otherwise have been thrown away.
    gone = mon.track([])
    reports = mon.reap(gone, [_stop_deal()], _Client())
    assert len(reports) == 1
    assert reports[0]["label"] == "stop"
    assert reports[0]["book"]["entry_spread"] == 1.25
    mon.forget(gone)
    assert 901 not in mon._open
    # Scored too: the stop had a remembered SL to compare the fill against.
    assert mon._samples["GER40"], "kayma ornegi uretilmeliydi"


def test_an_engine_ordered_close_is_dropped_at_once_not_retried():
    """Deals exist, none broker-side. This is the ordinary exit, not a lag."""
    mon = _monitor()
    gone = mon.track([])
    own = dict(_stop_deal(), reason=3)         # EXPERT: our own close_position
    assert mon.reap(gone, [own], _Client()) == []
    mon.forget(gone)
    assert 901 not in mon._open, "kendi kapanisimiz beklemeye alinmamali"


def test_the_retry_is_bounded_and_says_so_once(monkeypatch):
    lines: list[tuple[str, str]] = []
    monkeypatch.setattr("micofx.execution.LOG.emit",
                        lambda msg, level="INFO", *a, **k: lines.append((msg, level)))
    mon = _monitor()
    for _ in range(MAX_REAP_TRIES + 3):
        gone = mon.track([])
        mon.reap(gone, [], _Client())
        mon.forget(gone)
    assert 901 not in mon._open, "sonsuza kadar beklememeli"
    warned = [m for m, lvl in lines if "eslesmedi" in m and lvl == "WARN"]
    assert len(warned) == 1, "butce bitince tek satir"
