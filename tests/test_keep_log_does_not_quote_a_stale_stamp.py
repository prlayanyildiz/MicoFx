"""The keep-line must not quote a two-day-old apply stamp as if it were fresh.

26.08 00:56 US30: no candidate passed, log said "mevcut ayar korundu
(test net +224.2R)". That number is opt_summary.holdout from the 24.08
20:52 apply. The same live config on tonight's pins is -89.1 R. The apply
gate already replays via _fresh_incumbent_holdout; the keep log does not.
An operator (and Claude) then managed the symbol as if +224 were current.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


class _Store:
    """Just enough store for the keep-line path.

    ``object.__new__`` skips ``__init__``, so the instance carries none of the
    attributes production sets. That was fine until the keep-line path started
    reading ``self.store`` directly, at which point every test in this file
    died on AttributeError before its assertion - and the guard here (a keep
    line must quote the FRESH replay, not a stale stamp) stopped guarding
    anything. Attached explicitly rather than reaching for a real Optimizer,
    which would want a DB and an MT5 client. (05.09)
    """

    system = SystemConfig()
    symbols: dict = {}

    def get_setting(self, key, default=None):
        return default

    def set_setting(self, key, value):
        pass

    def opt_params(self):
        return {}


def _opt(*, fresh):
    opt = object.__new__(Optimizer)
    opt.store = _Store()
    if fresh is not None:
        opt._holdout_costed = lambda *a, **k: fresh
    return opt


def _cfg(stamp_r=224.2, when=None):
    cfg = SymbolConfig(symbol="US30", magic=1, strategy="burst",
                       timeframe="M30")
    cfg.opt_summary = {"holdout": {"net_r": stamp_r, "score": 40.0}}
    cfg.opt_updated_at = float(when if when is not None else time.time() - 2 * 86400)
    return cfg


def test_fresh_holdout_is_what_the_keep_line_quotes():
    opt = _opt(fresh={"net_r": -89.1, "score": 0.0})
    tail = opt._incumbent_kept_tail(_cfg())
    assert "taze test -89.1R" in tail, tail
    assert "224.2" not in tail, tail
    assert "test net" not in tail, tail


def test_when_replay_fails_the_stamp_is_named_as_a_stamp():
    opt = _opt(fresh=None)

    def _boom(*a, **k):
        raise RuntimeError("no bars")

    opt._holdout_costed = _boom
    # 24.08 17:52 UTC == 20:52 UTC+3 apply
    when = time.mktime((2026, 8, 24, 20, 52, 0, 0, 0, -1))
    tail = opt._incumbent_kept_tail(_cfg(when=when))
    assert "damga +224.2R" in tail, tail
    assert "test net" not in tail, tail
    assert "24.08" in tail, tail
