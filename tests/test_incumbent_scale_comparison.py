"""A score measured under one spread assumption cannot veto one measured under another.

_beats_incumbent stops a weaker candidate replacing a stronger live config,
and it does that by comparing holdout scores. That is sound only while both
numbers were produced the same way.

They are not, once the spread calibration lands. The engine measures live tick
spread against bar spread continuously; the moment a symbol clears its sample
threshold the search starts charging a higher - and truer - cost than the
incumbent was ever scored against. An honest candidate then trades less and
earns less in total, so it loses the comparison to a config whose score was
inflated by a cost model we have since measured to be wrong:

    XAUUSD   79.4 at scale 1.00   vs   45.1 at the measured 1.25
    CHFJPY   10.4 at scale 1.00   vs    7.4 at the measured 3.00
    EURJPY    9.0 at scale 1.00   vs    2.2 at the measured 1.55

All three were kept with "mevcut ayardan zayif". The calibration was
unreachable by construction: it can only ever lower a score, and the gate
only ever admits a higher one.

The veto is now skipped when the assumption moved. Nothing else is relaxed -
validation, the consistency ratio, both cost gates and the retention check are
all absolute, and a candidate still has to clear every one of them.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self, blob=None):
        self.saved = {"spread_ratio": blob} if blob is not None else {}

    def get_setting(self, key, default=None):
        return self.saved.get(key, default)


def _optimizer(scale=1.0):
    opt = object.__new__(Optimizer)
    opt.store = _Store()
    opt._spread_scale = lambda symbol: scale
    return opt


def _cfg(symbol="XAUUSD", *, score, scale, age_days=1.0):
    cfg = SymbolConfig(symbol=symbol, magic=1)
    holdout = {"score": score, "trades": 584, "expectancy": 0.168}
    summary = {"holdout": holdout}
    if scale is not None:
        summary["spread_scale"] = scale
    cfg.opt_summary = summary
    cfg.opt_updated_at = time.time() - age_days * 86400
    return cfg


WEAKER = {"score": 45.098, "trades": 180, "expectancy": 0.301}
STRONGER = {"score": 95.0, "trades": 600, "expectancy": 0.30}


# ------------------------------------------------- the veto that blocked us

def test_a_weaker_score_under_a_changed_scale_is_no_longer_vetoed():
    """XAUUSD: 45.1 at the measured 1.25 against 79.4 at the old 1.00."""
    opt = _optimizer(scale=1.25)
    cfg = _cfg(score=79.389, scale=1.0)
    assert opt._beats_incumbent(cfg, WEAKER) is True


@pytest.mark.parametrize("old,new", [(1.0, 3.0), (1.0, 1.55), (2.0, 1.0), (1.25, 1.6)])
def test_any_material_move_in_the_assumption_skips_the_comparison(old, new):
    opt = _optimizer(scale=new)
    assert opt._beats_incumbent(_cfg(score=79.389, scale=old), WEAKER) is True


def test_an_unrecorded_scale_is_read_as_the_1_0_it_was_measured_at():
    """Everything applied before this field existed WAS measured at 1.0 -
    walk_forward defaults to it and the optimizer passed nothing. Treating it
    as unknown would drop the incumbent guard for the whole book on the next
    run, including the ~10 symbols whose measured scale is 1.0 anyway."""
    opt = _optimizer(scale=1.0)
    assert opt._beats_incumbent(_cfg(score=79.389, scale=None), WEAKER) is False


def test_an_unrecorded_scale_still_yields_when_the_measurement_has_moved():
    """CHFJPY and XAUUSD are exactly this case: nothing recorded, and a
    measured scale that is nowhere near 1.0."""
    for scale in (1.15, 1.55, 3.00):
        opt = _optimizer(scale=scale)
        assert opt._beats_incumbent(_cfg(score=79.389, scale=None), WEAKER) is True


# ------------------------------------------- the veto that must still work

def test_a_weaker_score_under_the_SAME_scale_is_still_vetoed():
    """The guard's real job: it went in after weaker candidates auto-applied
    over strictly stronger incumbents."""
    opt = _optimizer(scale=1.25)
    cfg = _cfg(score=79.389, scale=1.25)
    assert opt._beats_incumbent(cfg, WEAKER) is False


def test_a_stronger_candidate_still_wins_under_the_same_scale():
    opt = _optimizer(scale=1.25)
    assert opt._beats_incumbent(_cfg(score=79.389, scale=1.25), STRONGER) is True


def test_a_negligible_drift_does_not_count_as_a_changed_assumption():
    """The measurement wobbles by a bucket; that is not a new assumption."""
    opt = _optimizer(scale=1.02)
    assert opt._beats_incumbent(_cfg(score=79.389, scale=1.0), WEAKER) is False


# ------------------------------------------------ the pre-existing bypasses

def test_no_incumbent_still_passes():
    assert _optimizer()._beats_incumbent(None, WEAKER) is True


def test_a_stale_incumbent_still_passes():
    opt = _optimizer(scale=1.0)
    cfg = _cfg(score=79.389, scale=1.0, age_days=Optimizer.INCUMBENT_GUARD_DAYS + 1)
    assert opt._beats_incumbent(cfg, WEAKER) is True


def test_a_zero_scored_incumbent_still_passes():
    opt = _optimizer(scale=1.0)
    assert opt._beats_incumbent(_cfg(score=0.0, scale=1.0), WEAKER) is True


# -------------------------------------------------------- what gets stored

def test_the_applied_summary_records_the_scale_it_was_measured_under():
    """Without it every future comparison is between unlike numbers."""
    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "optimizer.py").read_text(encoding="utf-8")
    body = src.split('patch["opt_summary"] = {', 1)[1][:1200]
    assert '"spread_scale"' in body
    assert "_spread_scale(symbol)" in body


def test_the_scale_is_read_back_from_the_level_it_is_written_at():
    """It is written at the summary root; reading it from the nested holdout
    block leaves old_scale permanently 0, which skips the comparison for every
    symbol instead of only the recalibrated ones. That is how this landed the
    first time, and only this test caught it."""
    src = (Path(__file__).resolve().parents[1] / "micofx"
           / "optimizer.py").read_text(encoding="utf-8")
    beats = src.split("def _beats_incumbent(", 1)[1].split("\n    def ", 1)[0]
    assert 'summary.get("spread_scale"' in beats
    assert 'previous.get("spread_scale"' not in beats
