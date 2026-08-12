"""A record can be too short to average and still be long enough to read.

The supervisor could judge a symbol two ways, and a gap sat between them:

  * ``quarantine_losses`` (10) is count-independent but wants the losses
    CONSECUTIVE.
  * ``watch_pf`` needs ``watch_min_trades`` (25) before profit factor counts at
    all.

So "few trades, overwhelmingly bad" fell through. USDCHF: eleven trades, one
win, ten losses, PF 0.35, -16.09 - four consecutive, so no quarantine, and
eleven trades, so no watch. It traded at full scale. US500: fifteen trades, two
wins, thirteen losses, PF 0.08, -26.98, same story.

Waiting was not a fix. At their own rate USDCHF reaches twenty-five trades in
thirty-eight days and US500 in twenty, and USDJPY - four trades, four losses -
in a hundred and fifty-eight.

Twenty-five is a sound bar for an AVERAGE: profit factor over a handful of
trades is noise. It is the wrong bar for a COUNT. One win in eleven is not a
noisy average, it is an unlikely sequence: under a coin-flip win rate the odds
of one or fewer wins in eleven are about six in a thousand.

So the count is read the way the rest of the system reads evidence - against its
own sampling noise. ``portfolio-gates`` already does this on expectancy with
``2 * 1.2 / sqrt(n)``; this is the same idea on the win count, whose noise under
a break-even record is ``sqrt(n) / 2``, giving a two-sigma floor of
``n/2 - sqrt(n)``. Below that the record is not thin, it is damning.

Profit factor must still be under ``watch_pf``: a symbol whose few wins are
large enough to carry it is not losing money and is not the thing being caught.

Calibrated against the whole live book: it catches US500 and USDCHF, confirms
XAUUSD (already watch), and touches no symbol that is making money - GER40,
US30, SpotBrent, UK100, US2000, GBPUSD and AUDUSD are all left alone, as are
the genuinely uninformative records (USDJPY at four trades, CHFJPY at seven).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.supervisor import DEFAULTS, Supervisor


class _Store:
    def __init__(self, cfg):
        self.symbols = {cfg.symbol: cfg}
        self.data = {"supervisor": {}}

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def set_setting(self, key, value):
        self.data[key] = value


def _sup() -> Supervisor:
    cfg = SymbolConfig(symbol="TEST", magic=900001)
    sup = Supervisor.__new__(Supervisor)
    sup._lock = threading.RLock()
    sup.store = _Store(cfg)
    sup.risk_scale = 1.0
    sup.verdicts = {}
    sup.notes = []
    sup.reopt_queue = []
    sup.last_review = 0.0
    return sup


# The live book runs watch_min_trades at 25, not the shipped 10 - and that is
# what opened the gap: at 10 the count bar would already have caught USDCHF's
# eleven trades. Tests state it explicitly rather than inheriting whichever
# value ships, since the rule under test has to hold at any setting.
LIVE = dict(DEFAULTS, watch_min_trades=25)


def _judge(nets: list[float], cfgs: dict | None = None):
    sup = _sup()
    trades = [{"profit": float(n), "commission": 0.0, "swap": 0.0,
               "time": float(1_700_000_000 + i * 3600), "symbol": "TEST"}
              for i, n in enumerate(nets)]
    return sup._judge(sup.store.symbols["TEST"], trades, dict(cfgs or LIVE))


def _mix(wins: int, losses: int, win_size: float = 1.0, loss_size: float = 3.0):
    """Wins spread evenly through the losses.

    Deliberately not "all the wins, then all the losses": that buries a
    ten-long losing streak in every thin case and quarantine_losses fires
    first, testing the wrong rule. Evenly spaced keeps the longest streak
    short while leaving the counts exactly as asked.
    """
    total = wins + losses
    if total == 0:
        return []
    at = {round((i + 0.5) * total / wins) - 1 for i in range(wins)} if wins else set()
    out = [win_size if i in at else -loss_size for i in range(total)]
    # Rounding can collide two wins onto one slot; place any shortfall in the
    # remaining gaps so the requested counts hold exactly.
    while sum(1 for x in out if x > 0) < wins:
        out[out.index(-loss_size)] = win_size
    return out


# ------------------------------------------------------------- the live cases

def test_usdchf_one_win_in_eleven_is_throttled():
    v = _judge(_mix(1, 10))
    assert v.trades == 11 and v.wins == 1
    assert v.state == "watch", f"11 islemde 1 kazanc hala tam olcekle isliyor: {v.reason}"
    assert v.risk_scale == LIVE["watch_risk_scale"]


def test_us500_two_wins_in_fifteen_is_throttled():
    v = _judge(_mix(2, 13))
    assert v.trades == 15 and v.wins == 2
    assert v.state == "watch"


# --------------------------------------------- what must NOT be caught

def test_a_record_too_short_to_say_anything_is_left_alone():
    """USDJPY: four trades, four losses. The two-sigma floor is 0 at n=4."""
    v = _judge(_mix(0, 4))
    assert v.trades == 4
    assert v.state == "ok", "dort islem bir sey kanitlamaz"


def test_an_even_win_count_is_left_alone_however_big_the_losses():
    """FRA40: six wins, six losses, PF 0.56. Losing on size, not on frequency -
    that is what watch_min_trades is for and this rule must not pre-empt it."""
    v = _judge(_mix(6, 6, win_size=1.0, loss_size=2.0))
    assert v.trades == 12 and v.wins == 6
    assert v.profit_factor < 1.0
    assert v.state == "ok", "sikliktan degil boyuttan kaybediyor - sayi bari yargilar"


def test_a_thin_record_that_is_making_money_is_left_alone():
    """Few wins, but big enough to carry it: PF over watch_pf, so not this."""
    v = _judge(_mix(1, 10, win_size=40.0, loss_size=3.0))
    assert v.wins == 1 and v.profit_factor >= DEFAULTS["watch_pf"]
    assert v.state == "ok"


@pytest.mark.parametrize("wins,losses", [(15, 9), (12, 16), (12, 17), (3, 2)])
def test_the_live_winners_are_untouched(wins, losses):
    """SpotBrent, GER40, US30, US2000 win-counts, with losing sizes so PF
    cannot be what saves them."""
    v = _judge(_mix(wins, losses, win_size=3.0, loss_size=1.0))
    assert v.state == "ok"


# ------------------------------------------------ the old paths still work

def test_the_trade_count_bar_still_applies_on_its_own():
    # PF has to land between quarantine_pf (0.80) and watch_pf (1.00): below
    # 0.80 the count bar quarantines instead, which is a different branch.
    v = _judge(_mix(12, 13, win_size=1.0, loss_size=1.03))
    assert v.trades >= LIVE["watch_min_trades"]
    assert LIVE["quarantine_pf"] <= v.profit_factor < LIVE["watch_pf"]
    assert v.wins >= v.trades / 2 - 25 ** 0.5, "sayi bariyla yakalanmali, yeni kuralla degil"
    assert v.state == "watch"


def test_a_losing_streak_still_quarantines():
    v = _judge([1.0] * 3 + [-1.0] * LIVE["quarantine_losses"])
    assert v.state == "quarantine"


def test_a_flawless_thin_record_is_not_caught():
    v = _judge([0.05] * 11)
    assert v.wins == 11
    assert v.state == "ok"


def test_no_trades_is_still_idle():
    sup = _sup()
    assert sup._judge(sup.store.symbols["TEST"], [], dict(DEFAULTS)).state == "idle"


def test_the_shipped_bar_would_have_caught_it_anyway():
    """At the shipped watch_min_trades of 10, USDCHF's eleven trades clear the
    count bar on their own. The gap is what raising it to 25 opened, and this
    rule is what makes the outcome independent of where the bar sits."""
    v = _judge(_mix(1, 10), cfgs=dict(DEFAULTS))
    assert DEFAULTS["watch_min_trades"] == 10
    assert v.state == "watch"
