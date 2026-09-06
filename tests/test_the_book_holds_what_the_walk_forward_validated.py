"""The walk-forward validates one position at a time. Live allowed ten.

``simulate`` scans for the next entry only after the current trade closes::

    resume_signal = max(exit_bar - 1, j0 + cooldown_bars - 1)
    while ptr < entries.size and entries[ptr] <= resume_signal:
        ptr += 1

The first signal it will take is the one ON the exit bar, which fills at the
NEXT bar's open - after the trade closed - so the simulation still never holds
two positions on a symbol at once.

(That was ``max(exit_bar, ...)`` until 05.09, which also skipped the exit bar's
own signal. The slot is free at that bar's close, so live took those entries
and the replay did not - 13.5% of live consecutive pairs land exactly there.
The `- 1` closed a gap that flattered the replay; it did not open an overlap.)

Every number the search produces - profit factor, expectancy, and above all
``max_dd_r`` - describes that system.

Live carried ``max_positions = 10`` on all ten symbols. On 13.08 JPN225 opened
eight SELLs between 04:00 and 14:30 while price rose, and four of them died at
their original stop; the two older positions that had been trailed returned
+16.90 and +17.90 while the five stacked on top gave back 38.44. NAS100 held
seven BUYs, GER40 five.

That is not ten times the risk, it is ten times the *same* risk: one symbol,
one direction, one leg, one idea. The holdout's drawdown never saw it.

Set to 1, which is the only count the search actually validated. Two would be a
reasonable compromise - one position per leg - but the two legs running
together are not validated anywhere either.

This test pins the property the limit is derived from. If ``simulate`` ever
starts overlapping trades, the reasoning behind a live limit of 1 is gone and
this fails rather than leaving the old number sitting there unexplained.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

BACKTEST = (Path(__file__).resolve().parents[1] / "micofx" / "backtest.py").read_text(
    encoding="utf-8")
RISK = (Path(__file__).resolve().parents[1] / "micofx" / "risk.py").read_text(
    encoding="utf-8")


# ------------------------------------------- what the search actually validates

def _run(cooldown_sec: int = 0, n: int = 400):
    """Replay a synthetic zig-zag with a BUY signal on every bar.

    The signal array is handed in directly rather than produced by a family.
    What this file guards is the entry SCHEDULING - when simulate is willing to
    open the next trade - and routing that through a family's indicators only
    adds a way for the test to go quiet: the first attempt used ``burst`` on a
    smooth series, which produced zero trades, and a test that takes no trades
    proves nothing about overlap. A signal on every bar is also the hardest
    case for the invariant: if anything could double up, this would.
    """
    import numpy as np

    from micofx.backtest import simulate
    from micofx.models import SymbolConfig
    from micofx.strategy import IndicatorCache, Params, Signals

    t = np.arange(n, dtype=np.int64) * 1800
    close = 100.0 + np.cumsum(np.sin(np.arange(n) / 5.0)) * 0.8
    high, low = close + 1.0, close - 1.0
    open_ = np.concatenate(([close[0]], close[:-1]))
    spread = np.full(n, 1.0)
    cache = IndicatorCache(high, low, close, t, 1800, open_,
                           np.ones(n), np.zeros(n))
    cfg = SymbolConfig(symbol="X", magic=1, strategy="burst", timeframe="M30",
                       cooldown_sec=cooldown_sec, sl_atr_mult=1.0,
                       use_sessions=False)
    p = Params.from_config(cfg)
    ones = np.ones(n)
    sig = Signals(t3=close, k=ones * 50, d=ones * 50, atr=ones,
                  adx=ones * 30, buy=np.ones(n, dtype=bool),
                  sell=np.zeros(n, dtype=bool),
                  htf_up=np.ones(n, dtype=bool),
                  htf_down=np.zeros(n, dtype=bool))
    res = simulate(cache, sig, open_, spread, 0.01, p,
                   np.ones(n, dtype=bool), 0, n, 0.0, max_open=1,
                   block_reverse=True)
    return list(res.trade_events)


def test_the_simulation_never_holds_two_positions_at_once():
    """The whole basis for a per-symbol limit of 1.

    Asserted on BEHAVIOUR, not on the spelling of the line that produces it.
    This used to grep backtest.py for ``resume_signal = max(exit_bar,`` and so
    it failed on 05.09 for a change that did not touch the property at all
    (``exit_bar`` -> ``exit_bar - 1``, which lets the exit bar's own signal
    fill on the NEXT bar). A test that cannot tell a real overlap from a
    reworded line is not guarding the invariant it is named after.
    """
    events = _run()
    assert len(events) >= 5, f"replay uretmedi ({len(events)} islem) - test bos"
    for prev, nxt in zip(events, events[1:], strict=False):
        assert prev[1] <= nxt[0], (
            f"ust uste islem: {prev[0]}..{prev[1]} kapanmadan {nxt[0]} acildi - "
            f"canli 1-pozisyon limitinin gerekcesi gitti")


def test_the_cooldown_only_ever_pushes_the_resume_later():
    """A cooldown can delay the next entry, never bring it forward.

    Also behavioural: with a pause armed, every gap between one exit and the
    next entry must be at least as long as it was without one, and the run
    cannot take MORE trades than the un-paused run.
    """
    free = _run(cooldown_sec=0)
    paused = _run(cooldown_sec=3600)
    assert len(free) >= 5, "temel kosu bos - test hicbir sey kanitlamiyor"
    assert len(paused) <= len(free), (
        f"cooldown islem sayisini ARTIRDI ({len(free)} -> {len(paused)}) - "
        f"bir duraklama girisi one cekemez")
    for prev, nxt in zip(paused, paused[1:], strict=False):
        assert prev[1] <= nxt[0], "cooldown kolu ust uste islem uretti"


# ------------------------------------------------- what enforces it live

def test_the_live_gate_reads_the_symbol_slot_cap():
    """One ticket per name. Leftover cfg.max_positions is unread.

    The book-wide 1R ceiling used to be asserted absent here; the operator
    re-armed it 31.08 and it is covered by test_concurrent_risk_gate.
    """
    assert "sembol pozisyon limiti (" in RISK
    assert "sys_cfg.max_positions" not in RISK
    # Binding leftover 5/10 is the 13.08 stack.
    assert "getattr(cfg, \"max_positions\"" not in RISK


def test_the_opposite_direction_block_is_still_there():
    """With one position per symbol this rarely fires, but it is the guard that
    stops a hedge appearing if the limit is ever raised again."""
    assert 'if any(p["side"] != side for p in same_symbol):' in RISK


def test_the_leftover_total_slot_cap_is_unread():
    """Book-wide leftover max_total_positions stays unread."""
    assert "len(mine) >= sys_cfg.max_total_positions" not in RISK
    assert "toplam pozisyon limiti" not in RISK
