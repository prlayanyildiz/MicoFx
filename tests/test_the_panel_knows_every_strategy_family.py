"""The family list lives in Python and its labels live in JavaScript.

``models.STRATEGIES`` is what the optimiser searches and what a config may
name. ``STRATEGY_LABEL`` in app.js turns those keys into the Turkish names a
human reads - and it is not only cosmetic: line 639 builds the strategy
dropdown itself from ``Object.entries(STRATEGY_LABEL)``, so a family missing
from the map cannot be selected in the panel at all, and one appearing only in
the map offers a choice the search does not know.

Nothing bound the two. It has already drifted once: six flip families were
absent from the map, so four live symbols displayed a raw key like
``wavetrend_flip`` where a name belonged and could not be picked from the
dropdown. That was repaired by hand; nothing stopped it happening again.

Both sides are currently correct - 14 keys against 14 families - so this adds
no behaviour. It exists because the failure is silent on both ends: a missing
label degrades to the raw key rather than raising, and a stale one just offers
a dead option.
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
        f"panelde ham anahtar gorunur ve acilir listeden secilemez: {missing}")


def test_no_label_names_a_family_that_no_longer_exists():
    """The dropdown is built from this map, so a stale key is a dead option."""
    extra = sorted(_labelled() - set(models.STRATEGIES))
    assert not extra, f"silinmis aile hala listede: {extra}"


def test_the_two_sides_are_the_same_size():
    assert len(_labelled()) == len(models.STRATEGIES)


# --------------------------------------------------- the test's own footing

def test_the_dropdown_really_is_built_from_this_map():
    """If the panel stops deriving its options here, the tests above are
    guarding something that no longer decides anything."""
    assert "Object.entries(STRATEGY_LABEL)" in APP_JS


def test_the_family_registry_and_the_model_list_agree():
    """The other half of the same class: a key models can name but
    strategy.py cannot dispatch falls back to _t3_stoch without a word."""
    from micofx import strategy
    assert set(models.STRATEGIES) == set(strategy._FAMILIES)


def test_every_family_a_live_config_names_is_dispatchable():
    from micofx import strategy
    for key in models.STRATEGIES:
        assert callable(strategy._FAMILIES[key])
