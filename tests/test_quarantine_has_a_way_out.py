"""A suspended symbol must be able to get out.

Observed live 13-14.08: NAS100 quarantined at 21:38 on ``PF 0.56``, the
re-optimisation it queued landed a fresh ``wavetrend_flip/M15`` at 21:48 - and
it stayed suspended for the full twelve hours anyway, together with XAUUSD.
The streak reset correctly (that was fixed in 948c9af); the 30-day profit
factor, earned by the config that had just been thrown away, re-suspended it
on the very next review. An operator "Serbest birak" could not release it
either: ``clear()`` dropped the verdict, and the next review rebuilt it from
the same history within two minutes.

So the suspension decision now reads only trades inside an *evidence epoch* -
the later of (config applied, record cleared by hand). The bar itself is
unchanged: a replacement is judged on its own record at the same price, so a
healthy config is not suspended on a handful of noisy trades.

The full-window numbers are untouched for the panel and the watch bar: a soft
0.6x sizing cut may remember a long record, a hard stop may not.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, Supervisor, SymbolVerdict

NOW = time.time()
HOUR = 3600.0


class _Store:
    def __init__(self):
        self.symbols = {}

    def get_setting(self, key, default=None):
        return dict(DEFAULTS) if key == "supervisor" else default

    def set_setting(self, key, value):
        pass


def _sup():
    s = object.__new__(Supervisor)
    s._lock = threading.RLock()
    s.store = _Store()
    s.verdicts = {}
    s.notes = []
    s.risk_scale = 1.0
    s.optimizer = None
    return s


def _cfgs(**kw):
    c = dict(DEFAULTS)
    c.update(kw)
    return c


def _losses(start: float, n: int) -> list[dict]:
    return [{"time": start + 60 * i, "profit": -5.0, "commission": 0.0, "swap": 0.0}
            for i in range(n)]


def _wins(start: float, n: int) -> list[dict]:
    return [{"time": start + 60 * i, "profit": +9.0, "commission": 0.0, "swap": 0.0}
            for i in range(n)]


def test_a_suspension_is_capped_at_an_hour():
    """The way out is the re-search, which takes minutes - not half a day."""
    assert DEFAULTS["quarantine_hours"] == 1


class TestAReplacedConfigIsNotJudgedByTheOldRecord:
    def test_the_old_profit_factor_does_not_re_suspend_it(self):
        """The exact NAS100 case: fresh config, 30-day PF 0.56, still suspended."""
        sup = _sup()
        applied = NOW - 10 * 60
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=applied)
        sup.verdicts["NAS100"] = SymbolVerdict(
            symbol="NAS100", state="quarantine",
            quarantine_until=NOW + 30 * 60, quarantined_at=NOW - 30 * 60)
        # A long, bad record - all of it under the config that was replaced.
        trades = _losses(NOW - 20 * HOUR, 40) + _wins(NOW - 19 * HOUR, 10)

        v = sup._judge(cfg, trades, _cfgs())

        assert v.state != "quarantine", "a replaced config must not serve the old sentence"
        assert v.profit_factor < 1.0, "the full-window PF is still reported"

    def test_a_replacement_that_is_genuinely_bad_is_suspended_again(self):
        """Clean slate is not immunity - it just has to be earned on its own trades."""
        sup = _sup()
        applied = NOW - 5 * HOUR
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=applied)
        # 24 losers / 8 winners under the NEW config, never more than three in
        # a row - so this is the PROFIT FACTOR path (0.60), not the streak one.
        trades = []
        for block in range(8):
            trades += _losses(applied + 600 * block, 3)
            trades += _wins(applied + 600 * block + 300, 1)

        v = sup._judge(cfg, trades, _cfgs())

        assert v.state == "quarantine"
        assert "32 islem" in v.reason, f"judged on its own record, got: {v.reason}"

    def test_the_bar_is_not_cheapened(self):
        """Below min_trades of its own, a replacement is not suspended on noise."""
        sup = _sup()
        applied = NOW - 2 * HOUR
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=applied)
        # Five losers - awful, but five trades is not evidence.
        trades = _losses(applied + 60, 5)

        v = sup._judge(cfg, trades, _cfgs(quarantine_losses=99))

        assert v.state != "quarantine"


class TestManualReleaseActuallyReleases:
    def test_clear_stamps_the_epoch_so_history_stops_counting(self):
        sup = _sup()
        sup.verdicts["NAS100"] = SymbolVerdict(
            symbol="NAS100", state="quarantine",
            quarantine_until=NOW + 30 * 60, quarantined_at=NOW - 30 * 60)

        sup.clear("NAS100")
        v = sup.verdicts["NAS100"]

        assert v.state == "ok"
        assert v.quarantine_until == 0.0
        assert v.history_cleared_at > 0.0, "the release has to mean something"

    def test_the_next_review_does_not_undo_the_release(self):
        """What made the button look broken: re-quarantined within one cycle."""
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=0.0)
        sup.verdicts["NAS100"] = SymbolVerdict(
            symbol="NAS100", state="quarantine",
            quarantine_until=NOW + 30 * 60, quarantined_at=NOW - 30 * 60)
        sup.clear("NAS100")

        # Same bad 30-day history the operator just said to disregard.
        trades = _losses(NOW - 20 * HOUR, 40)
        v = sup._judge(cfg, trades, _cfgs())

        assert v.state != "quarantine"

    def test_losses_after_the_release_still_count(self):
        """Clearing forgives the record, it does not disable the breaker."""
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=0.0)
        sup.verdicts["NAS100"] = SymbolVerdict(symbol="NAS100", state="ok")
        sup.clear("NAS100")
        cleared = sup.verdicts["NAS100"].history_cleared_at

        trades = _losses(cleared + 60, 30)
        v = sup._judge(cfg, trades, _cfgs())

        assert v.state == "quarantine"

    def test_clearing_everything_resets_the_portfolio_scale(self):
        sup = _sup()
        sup.risk_scale = 0.4
        sup.verdicts["NAS100"] = SymbolVerdict(symbol="NAS100", state="quarantine")

        sup.clear()

        assert sup.risk_scale == 1.0
        assert sup.verdicts["NAS100"].state == "ok"


def test_a_symbol_with_no_epoch_is_judged_on_its_whole_record():
    """Never optimised, never cleared: nothing changes for it."""
    sup = _sup()
    cfg = SymbolConfig(symbol="NAS100", opt_updated_at=0.0)
    trades = _losses(NOW - 20 * HOUR, 40)

    v = sup._judge(cfg, trades, _cfgs())

    assert v.state == "quarantine"


class TestProbation:
    """Released early is not the same as proved.

    The evidence epoch means the suspension bar reads only the current config's
    own trades, so between a release and its 25th trade only the streak breaker
    is watching. A symbol walking out of a suspension goes back at watch size
    and earns the rest - the graduated response ``watch`` exists for.
    """

    def test_a_released_symbol_goes_back_at_watch_size(self):
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=0.0)
        sup.verdicts["NAS100"] = SymbolVerdict(symbol="NAS100", state="quarantine")
        sup.clear("NAS100")
        cleared = sup.verdicts["NAS100"].history_cleared_at

        # A short, perfectly good record under the new epoch - not enough of it.
        v = sup._judge(cfg, _wins(cleared + 60, 4), _cfgs())

        assert v.state == "watch"
        assert v.risk_scale == DEFAULTS["watch_risk_scale"]
        assert "deneme suresi" in v.reason

    def test_probation_ends_on_its_own_once_the_record_exists(self):
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=0.0)
        sup.verdicts["NAS100"] = SymbolVerdict(symbol="NAS100", state="quarantine")
        sup.clear("NAS100")
        cleared = sup.verdicts["NAS100"].history_cleared_at

        v = sup._judge(cfg, _wins(cleared + 60, 30), _cfgs())

        assert v.probation is False
        assert v.state == "ok"

    def test_probation_does_not_rescue_a_genuinely_bad_config(self):
        """It softens the way back up, it must not soften the way down."""
        sup = _sup()
        cfg = SymbolConfig(symbol="NAS100", opt_updated_at=0.0)
        sup.verdicts["NAS100"] = SymbolVerdict(symbol="NAS100", state="quarantine")
        sup.clear("NAS100")
        cleared = sup.verdicts["NAS100"].history_cleared_at

        v = sup._judge(cfg, _losses(cleared + 60, 30), _cfgs())

        assert v.state == "quarantine"

    def test_a_healthy_symbol_that_was_never_suspended_is_untouched(self):
        """Probation is only for symbols coming out of a suspension."""
        sup = _sup()
        cfg = SymbolConfig(symbol="GER40", opt_updated_at=NOW - 30 * 60)
        v = sup._judge(cfg, _wins(NOW - 25 * 60, 5), _cfgs())

        assert v.probation is False
        assert v.state == "ok"


class TestClearingDoesNotThrottleHealthySymbols:
    """A reset is the operator wiping the slate, not a portfolio-wide throttle.

    Stamping probation on every verdict demoted the whole book: GER40 went to
    watch size at PF 2.17 - the best profit factor in the portfolio - reading
    "deneme suresi 0/50 islem". Probation is the way back up from a suspension,
    so only a symbol that was actually suspended gets it.
    """

    def test_a_healthy_symbol_is_not_put_on_probation_by_a_reset(self):
        sup = _sup()
        sup.verdicts["GER40"] = SymbolVerdict(symbol="GER40", state="ok",
                                              profit_factor=2.17)
        sup.clear()
        assert sup.verdicts["GER40"].probation is False

        cfg = SymbolConfig(symbol="GER40", opt_updated_at=0.0)
        cleared = sup.verdicts["GER40"].history_cleared_at
        v = sup._judge(cfg, _wins(cleared + 60, 3), _cfgs())

        assert v.state == "ok", "a reset must not cut a healthy symbol's size"
        assert v.risk_scale == 1.0

    def test_a_suspended_symbol_still_gets_probation_from_a_reset(self):
        sup = _sup()
        sup.verdicts["NAS100"] = SymbolVerdict(symbol="NAS100", state="quarantine")
        sup.clear()
        assert sup.verdicts["NAS100"].probation is True

    def test_a_watched_symbol_is_not_promoted_to_probation(self):
        """watch is a soft cut it already earned - clearing re-judges it."""
        sup = _sup()
        sup.verdicts["JPN225"] = SymbolVerdict(symbol="JPN225", state="watch")
        sup.clear()
        assert sup.verdicts["JPN225"].probation is False


def test_the_number_the_suspension_is_decided_on_is_visible():
    """The evidence epoch created a question the API could not answer.

    The suspension reads trades inside the epoch, not the full window, so
    "can the profit-factor breaker even fire at this config churn rate"
    depends on a count nothing exposed. Cursor #071 reported it as
    "judged_n yok" - the decision was being made on an invisible number.
    """
    sup = _sup()
    applied = NOW - 3 * HOUR
    cfg = SymbolConfig(symbol="NAS100", opt_updated_at=applied)
    # 20 trades before the config landed, 4 after it.
    trades = _losses(applied - 5 * HOUR, 20) + _wins(applied + 60, 4)

    v = sup._judge(cfg, trades, _cfgs())

    assert v.trades == 24, "the full window is still reported"
    assert v.judged_trades == 4, "the epoch count must be visible"
    assert v.judged_pf > 1.0, "and it must be the epoch's own profit factor"
    assert v.profit_factor < 1.0, "distinct from the full-window figure"
