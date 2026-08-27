"""The family list lives in Python and its labels live in JavaScript.

``models.STRATEGIES`` is what the optimiser searches and what a config may
name. ``STRATEGY_LABEL`` in app.js turns those keys into the Turkish names a
human reads on the symbol card header. A family missing from the map
degrades to the raw key; a stale one is a lie about a family that cannot
run. The strategy dropdown left the card 27.08 (hands-off); the map still
has to cover every live family.

Nothing bound the two. It has already drifted once: six flip families were
absent from the map, so four live symbols displayed a raw key like
``wavetrend_flip`` where a name belonged. That was repaired by hand;
nothing stopped it happening again.

Both sides are currently correct - eight keys against eight families - so this adds
no behaviour. It exists because the failure is silent: a missing label
degrades to the raw key rather than raising, and a stale one lies about
a family that cannot run.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import models

APP_JS = (Path(__file__).resolve().parents[1]
          / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")


def _labelled() -> set[str]:
    block = re.search(r"STRATEGY_LABEL\s*=\s*\{(.*?)\n\}", APP_JS, re.S)
    assert block, "app.js icinde STRATEGY_LABEL bulunamadi"
    return set(re.findall(r"^\s*([a-z0-9_]+)\s*:", block.group(1), re.M))


# ------------------------------------------------------------- the binding

def test_every_family_the_optimiser_can_pick_has_a_label():
    missing = sorted(set(models.STRATEGIES) - _labelled())
    assert not missing, (
        f"panelde ham anahtar gorunur: {missing}")


def test_no_label_names_a_family_that_no_longer_exists():
    """The card header reads this map, so a stale key is a lie."""
    extra = sorted(_labelled() - set(models.STRATEGIES))
    assert not extra, f"silinmis aile hala listede: {extra}"


def test_the_two_sides_are_the_same_size():
    assert len(_labelled()) == len(models.STRATEGIES)


# --------------------------------------------------- the test's own footing

def test_the_card_header_really_reads_this_map():
    """If the panel stops printing the label, the tests above are guarding
    a dictionary nobody reads."""
    assert "STRATEGY_LABEL[cfg.strategy]" in APP_JS


def test_the_family_registry_and_the_model_list_agree():
    """The other half of the same class: a key models can name but
    strategy.py cannot dispatch must not silently run a different family."""
    from micofx import strategy
    assert set(models.STRATEGIES) == set(strategy._FAMILIES)


def test_every_family_a_live_config_names_is_dispatchable():
    from micofx import strategy
    for key in models.STRATEGIES:
        assert callable(strategy._FAMILIES[key])
