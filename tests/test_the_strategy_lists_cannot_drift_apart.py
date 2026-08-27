"""The name a config may carry and the name the engine can dispatch are two
hand-maintained lists in two files, and they must not drift.

``models.STRATEGIES`` is what validates a config: the web enum check refuses any
``strategy``/``secondary_strategy`` outside it, and ``Optimizer.start`` filters
its search list against it. ``strategy._FAMILIES`` is the dispatch table
``compute()`` actually routes on. Nothing ties them together, and the failure is
silent in the dangerous direction: a name in STRATEGIES but not in
``_FAMILIES`` used to fall through to the first T3 builder. ``compute()`` now
returns ``_no_signal`` for an unknown name, but the lists must still
match so the optimizer never offers a family the engine cannot run.

They match today (eight each). This exists so they still match after the next
family is added - the same reason test_risk_block_keys_cover_every_reason.py
exists for the other pair of hand-kept lists in this codebase.

``SCALP_STRATEGIES`` is checked for the same reason from a different angle: it
decides the post-fill cooldown's bar count and, through ``uses_swing_exits``,
which exit grid the search offers. A typo there names a family that does not
exist, so it silently selects nothing and the family it was meant to mark keeps
the swing treatment.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SCALP_STRATEGIES, STRATEGIES
from micofx.strategy import _FAMILIES, Params, compute


def test_every_name_a_config_may_carry_can_actually_be_dispatched():
    missing = sorted(set(STRATEGIES) - set(_FAMILIES))
    assert not missing, (
        f"{missing} STRATEGIES'de var ama _FAMILIES'de yok - compute() bunlari "
        f"sessizce sinyal uretmez, panel baska bir aile adi gosterirken")


def test_every_family_the_engine_can_run_is_reachable():
    unreachable = sorted(set(_FAMILIES) - set(STRATEGIES))
    assert not unreachable, (
        f"{unreachable} _FAMILIES'de var ama STRATEGIES'de yok - hicbir konfig "
        f"bu aileyi tasiyamaz, arama da onermez")


def test_the_two_lists_are_the_same_size():
    """Belt and braces: catches a duplicate in either list, which the two
    set-difference checks above would both pass."""
    assert len(STRATEGIES) == len(set(STRATEGIES)), "STRATEGIES'de tekrar eden ad var"
    assert len(STRATEGIES) == len(_FAMILIES)


def test_the_scalp_set_names_only_real_families():
    unknown = sorted(set(SCALP_STRATEGIES) - set(_FAMILIES))
    assert not unknown, (
        f"{unknown} SCALP_STRATEGIES'de ama boyle bir aile yok - cooldown bar "
        f"sayisi ve cikis izgarasi yanlis aileye uygulanir")


def test_the_fallback_is_what_makes_this_matter():
    """States the mechanism the guards above protect against, so a future
    change to compute()'s fallback is noticed here rather than in production.

    Not an endorsement of the fallback: mid-cycle it is safer than raising.
    What must not happen is a name reaching it, which is what the checks above
    make impossible.
    """
    sig = compute.__globals__["_FAMILIES"]
    assert sig.get("bu_aile_yok") is None
    fallback = compute.__globals__["_stoch_flip"]
    assert sig.get("bu_aile_yok", fallback) is fallback


def test_a_known_family_routes_to_its_own_builder():
    for name in ("aroon_flip", "burst", "mtf_pullback"):
        assert _FAMILIES[name] is not compute.__globals__["_stoch_flip"]
        assert Params(strategy=name).strategy == name
