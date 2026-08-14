"""A score earned with costs off can never be beaten by one earned honestly.

``_beats_incumbent`` compares a candidate's holdout score against the live
config's. ``charge_costs=False`` makes the sweep fill at the printed price and
charge nothing, which is strictly the larger number - the same trades, minus
the drag. So an incumbent stamped under that assumption sits above every
candidate priced with costs back on, and the symbol freezes on it.

The summary already stamps ``spread_scale`` for precisely this reason, and says
so: every number beside it "is only meaningful against that assumption, and
_beats_incumbent compares scores across runs". The cost switch is the same kind
of assumption and was not being recorded at all.

SpotBrent reached the state this describes. Auto-reopt applied a config at
13.08 12:36, inside the window where costs were off, and it carries
``cost_per_trade_r`` 0.0 while the other nine symbols carry 0.011 to 0.105.
With costs back on, nothing could have replaced it.

Unstamped reads as charging, because the switch shipped defaulting to True -
every config written before it existed was measured with costs on.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer

OPTIMIZER_SRC = (Path(__file__).resolve().parents[1]
                 / "micofx" / "optimizer.py").read_text(encoding="utf-8")


class _System:
    def __init__(self, charge):
        self.charge_costs = charge


class _Store:
    def __init__(self, charge):
        self.system = _System(charge)


def _cfg(stamp):
    class _C:
        symbol = "SpotBrent"
        opt_updated_at = time.time()
        opt_summary = dict({"spread_scale": 1.0, "holdout": {"score": 59.43}},
                           **({} if stamp is None else {"charge_costs": stamp}))
    return _C()


def _optimizer(charge):
    opt = object.__new__(Optimizer)
    opt.store = _Store(charge)
    opt._spread_scale = lambda symbol: 1.0            # type: ignore[assignment]
    return opt


# ------------------------------------------------------------- the defect

def test_a_cost_free_incumbent_does_not_block_an_honestly_priced_candidate():
    """Stamped cost-free, costs now charged: the scores are not comparable."""
    opt = _optimizer(charge=True)
    assert opt._beats_incumbent(_cfg(stamp=False), {"score": 5.0}) is True, (
        "maliyetsiz kazanilmis skor, maliyetli aday tarafindan asilamaz - "
        "sembol o konfige kilitlenir")


def test_the_other_direction_keeps_comparing():
    """Stamped with costs, now measuring without: the CANDIDATE is the
    inflated one, and the incumbent's honest score is the stricter bar.
    Waiving here would wave a cost-free candidate onto a live symbol."""
    opt = _optimizer(charge=False)
    assert opt._beats_incumbent(_cfg(stamp=True), {"score": 5.0}) is False
    assert opt._beats_incumbent(_cfg(stamp=True), {"score": 99.0}) is True


# --------------------------------------------------- what must keep working

def test_the_same_assumption_still_compares_scores():
    for charge in (True, False):
        opt = _optimizer(charge=charge)
        assert opt._beats_incumbent(_cfg(stamp=charge), {"score": 5.0}) is False
        assert opt._beats_incumbent(_cfg(stamp=charge), {"score": 99.0}) is True


def test_an_unstamped_incumbent_reads_as_charging():
    """The switch shipped defaulting to True, so anything written before it
    existed was measured with costs on."""
    opt = _optimizer(charge=True)
    assert opt._beats_incumbent(_cfg(stamp=None), {"score": 5.0}) is False


def test_apply_stamps_the_assumption_it_measured_under():
    # The stamp used to be read off store.system at write time, which answers
    # the wrong question when the flag is flipped mid-run - see
    # test_cost_regime_stamp_describes_the_sweep. It now comes off the sweep's
    # own report, with the store only as a fallback for older results.
    assert '"charge_costs": bool(detail["charge_costs"])' in OPTIMIZER_SRC, (
        "ozete damga yazilmiyor - kiyas bir sonraki turda yine kor kalir")
    stamp = OPTIMIZER_SRC.index('"charge_costs": bool(detail["charge_costs"])')
    scale = OPTIMIZER_SRC.index('"spread_scale": round(float(detail["spread_scale"])')
    # Both stamps carry long comments explaining why they exist, so this bound
    # is about them sharing one summary block, not about line count.
    assert abs(stamp - scale) < 1600, "damga spread_scale ile ayni blokta olmali"


def test_the_spread_scale_escape_is_still_there():
    """This adds a second escape; it must not have replaced the first."""
    assert "farkli spread olcegiyle olculmus" in OPTIMIZER_SRC
    assert "farkli maliyet varsayimiyla olculmus" in OPTIMIZER_SRC
