"""The OPT start line must not claim a TF lock the map does not have.

STRATEGY_TIMEFRAMES is empty on purpose (every family × every TF, including
scalps on M15+). The start banner still said ``scalp TF kilidi acik``. XAUUSD
is live burst/M15; the log was the opposite of the book.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import STRATEGY_TIMEFRAMES
from micofx.optimizer import Optimizer, tf_lock_status


def test_the_shipped_map_is_unlocked():
    assert STRATEGY_TIMEFRAMES == {}
    assert tf_lock_status(STRATEGY_TIMEFRAMES) == "aile TF kilidi kapali"


def test_a_named_restriction_is_locked():
    assert tf_lock_status({"burst": ["M5"]}) == "aile TF kilidi acik"


def test_an_empty_family_list_still_counts_as_a_lock():
    # models: explicit empty list means "nothing", not "everything".
    assert tf_lock_status({"burst": []}) == "aile TF kilidi acik"


def test_the_start_banner_uses_the_helper_not_a_hardcoded_on():
    src = inspect.getsource(Optimizer._run_unsafe)
    assert "tf_lock_status" in src
    assert "scalp TF kilidi acik" not in src
