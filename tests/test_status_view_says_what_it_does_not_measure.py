"""An indicator a family never computes must not read as a real zero.

The live status view carried one ``t3`` column filled by three different
things:

  * most families put the T3 level itself there (a price - 89.48 on SpotBrent,
    68464 on JPN225);
  * ``_st_trend`` and ``_parabolic_flip`` put a -1/0/+1 DIRECTION in the same
    field, so GER40 showed "t3 = -1.0" against a 26,400 instrument and UK100
    showed 1.0 against 10,800;
  * the flip families pass ``zeros`` and never populate it at all.

``Signals.last()`` then applied one rule to all three: ``t3[i] > t3[i-1]``. On
an all-zero series that is ``0 > 0``, permanently False - so NAS100, running
``wavetrend_flip``, reported a BUY signal beside "t3 falling" while computing no
T3 whatsoever. Read literally that says the bot is buying against its own trend
filter. It was read that way, which is how this was found. The same held for
``adx``/``k``/``d``: 0.0 for "this family does not measure it", identical to a
genuine flat reading, in the panel and in every SIGNAL log line the loss reviews
read back afterwards.

So an unmeasured reading is None, ``t3_kind`` says whether the number is a level
or a direction, and ``t3_rising`` is only claimed for a level - on a direction
series the same comparison would report a -1 -> +1 flip as "t3 rising", which is
a different statement in the same words.

Nothing trades on any of this. ``t3``, ``t3_rising``, ``k``, ``d`` and ``adx``
are assigned in _refresh_signal and read only by as_dict() and the SIGNAL log;
entries gate on ``buy``/``sell``/``atr``/``htf``, which are untouched. This is
the status view catching up with what the strategies actually compute.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import SymbolState
from micofx.strategy import Signals

N = 8


def _flat(v=0.0):
    return np.full(N, float(v))


def _sig(t3, *, adx=None, k=None, d=None, kind="level"):
    z = np.zeros(N)
    return Signals(t3=np.asarray(t3, dtype=np.float64),
                   k=z if k is None else np.asarray(k, dtype=np.float64),
                   d=z if d is None else np.asarray(d, dtype=np.float64),
                   atr=_flat(1.5),
                   adx=z if adx is None else np.asarray(adx, dtype=np.float64),
                   buy=np.zeros(N, dtype=bool), sell=np.zeros(N, dtype=bool),
                   htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool),
                   t3_kind=kind)


# ------------------------------------------------------------- the defect

def test_a_family_that_computes_no_t3_does_not_report_it_falling():
    """NAS100's shape: wavetrend_flip, t3 never populated."""
    snap = _sig(np.zeros(N)).last()
    assert snap["t3"] is None
    assert snap["t3_rising"] is None, "hesaplanmayan t3 'dusuyor' diye okunuyor"
    assert snap["t3_kind"] is None


def test_an_unmeasured_adx_is_not_reported_as_zero():
    snap = _sig(np.arange(N, dtype=float)).last()
    assert snap["adx"] is None
    assert snap["k"] is None and snap["d"] is None


def test_a_direction_flag_is_labelled_as_one():
    """GER40/UK100's shape: -1/0/+1 in the same field a price lives in."""
    snap = _sig([0, 1, 1, -1, -1, -1, -1, -1], kind="direction").last()
    assert snap["t3"] == -1.0
    assert snap["t3_kind"] == "direction"


def test_a_direction_flip_is_not_announced_as_a_rising_t3():
    """-1 -> +1 satisfies t3[i] > t3[i-1]; it is a flip, not a rise."""
    snap = _sig([0, 0, 0, 0, 0, 0, -1, 1], kind="direction").last()
    assert snap["t3"] == 1.0
    assert snap["t3_rising"] is None


# --------------------------------------------------- what must keep working

def test_a_real_t3_level_still_reports_its_direction():
    rising = _sig(np.linspace(100.0, 107.0, N)).last()
    assert rising["t3"] == 107.0
    assert rising["t3_kind"] == "level"
    assert rising["t3_rising"] is True

    falling = _sig(np.linspace(107.0, 100.0, N)).last()
    assert falling["t3_rising"] is False


def test_measured_readings_are_still_reported():
    snap = _sig(np.linspace(1.0, 8.0, N), adx=np.full(N, 21.7),
                k=np.full(N, 33.4), d=np.full(N, 26.3)).last()
    assert snap["adx"] == 21.7 and snap["k"] == 33.4 and snap["d"] == 26.3


def test_the_decision_fields_are_untouched():
    """Entries gate on these; the change must not reach them."""
    snap = _sig(np.zeros(N)).last()
    assert snap["atr"] == 1.5
    assert snap["buy"] is False and snap["sell"] is False
    assert snap["htf"] == 0


def test_a_series_too_short_still_reports_nothing():
    z = np.zeros(1)
    s = Signals(t3=z, k=z, d=z, atr=z, adx=z,
                buy=np.zeros(1, dtype=bool), sell=np.zeros(1, dtype=bool),
                htf_up=np.zeros(1, dtype=bool), htf_down=np.zeros(1, dtype=bool))
    assert s.last() == {}


# ------------------------------------------------- the view carries it out

def test_the_state_payload_carries_the_blanks_without_raising():
    """as_dict() rounds these; rounding None raises, and defaulting it back to
    0.0 there would undo the whole change."""
    st = SymbolState("NAS100")
    payload = st.as_dict()
    assert payload["t3"] is None
    assert payload["adx"] is None
    assert payload["k"] is None and payload["d"] is None
    assert payload["t3_rising"] is None
    assert payload["t3_kind"] is None


def test_the_state_payload_still_rounds_a_real_reading():
    st = SymbolState("JPN225")
    st.t3, st.t3_rising, st.t3_kind = 68464.771851234, True, "level"
    st.adx, st.k, st.d = 21.64, 54.02, 58.21
    payload = st.as_dict()
    assert payload["t3"] == 68464.771851
    assert payload["adx"] == 21.6
    assert payload["k"] == 54.0 and payload["d"] == 58.2
    assert payload["t3_rising"] is True
