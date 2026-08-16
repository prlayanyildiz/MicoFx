"""Paper must not trail on a bar's own high/low and then stop out on that bar.

Claude's EX-5 H1 suspicion: simulate updates the trail from the bar it is
processing (seeing that bar's peak) and then checks the stop against the same
bar's dip. That would let the replay lock in a stop the live engine cannot
have, because live trails off a *closed* bar's close and the forming bar can
only hit the stop that already existed.

The actual loop checks the stop against the incoming SL first, then ratchets
off close[j] for the *next* bar. This test is the single-bar trap that turns
red if that order is reversed: a spike whose low sits above the old SL but
below a trail computed from the same bar's high.
"""
from __future__ import annotations

import numpy as np

from micofx import backtest
from micofx.strategy import IndicatorCache, Params, Signals

N = 80
SIGNAL = 30
FILL = SIGNAL + 1   # j0
TRAP = FILL + 1     # first full bar after the fill
TF = 300


def _run():
    close = np.full(N, 100.0)
    high = close + 0.5
    low = close - 0.5
    open_ = np.full(N, 100.0)
    # Fill bar: enough close-profit to arm the trail, not enough to move SL
    # up through the trap bar's low.
    open_[FILL] = 100.0
    close[FILL] = 101.0
    high[FILL] = 101.2
    low[FILL] = 99.8
    # Trap: peak that would trail the stop up to ~108, dip to 103 that would
    # hit that new stop but not the original ~90 or the post-fill trail ~100.
    open_[TRAP] = 101.0
    high[TRAP] = 110.0
    low[TRAP] = 103.0
    close[TRAP] = 108.0
    # After the trap, drift down slowly so a same-bar exit is distinguishable
    # from a later honest trail hit.
    close[TRAP + 1:] = np.linspace(108.0, 104.0, N - TRAP - 1)
    high[TRAP + 1:] = close[TRAP + 1:] + 0.5
    low[TRAP + 1:] = close[TRAP + 1:] - 0.5
    open_[TRAP + 1:] = close[TRAP + 1:]

    buy = np.zeros(N, dtype=bool)
    buy[SIGNAL] = True
    sig = Signals(t3=close, k=close, d=close, atr=np.full(N, 1.0), adx=np.zeros(N),
                  buy=buy, sell=np.zeros(N, dtype=bool),
                  htf_up=np.zeros(N, dtype=bool), htf_down=np.zeros(N, dtype=bool))
    cache = IndicatorCache(high, low, close, times=np.arange(N) * TF,
                           tf_seconds=TF, open_=open_, volume=np.ones(N))
    return backtest.simulate(
        cache, sig, open_, np.zeros(N), point=0.01,
        p=Params(sl_atr_mult=10.0, trail_start_atr=0.5, trail_step_atr=1.0,
                 atr_period=14, trail_mode="atr"),
        entries=np.array([SIGNAL]),
        min_stop=0.1,
    )


def test_trail_does_not_use_this_bars_high_then_stop_on_this_bars_low():
    res = _run()
    assert res.trades == 1, f"trades={res.trades}"
    _entry_ts, exit_ts, _r = res.trade_events[0]
    trap_ts = TRAP * TF
    assert exit_ts != trap_ts, (
        f"cikis tuzagin barinda ({exit_ts}); trail bu barin high'i ile "
        f"cekilip ayni barin low'una karsi kontrol edilmis. reason={res.exits}"
    )
