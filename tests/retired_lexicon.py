"""TR + EN keywords for retired-family and stale-code scans.

Agents and tests grep docs, panel JS, and shipped config with the same
vocabulary so a Turkish-only or English-only mention of a removed family
still trips the guard.
"""

from __future__ import annotations

# Every strategy name that must not be presented as selectable/live.
RETIRED_FAMILIES = (
    "trix_flip",
    "flow_rev",
    "t3_ribbon",
    "squeeze_brk",
    "orb",
    "vwap_rev",
    "donchian",
    "liq_sweep",
    "alpha_trend",
    "mavilim",
    "st_trend",
    "macd_flip",
    "t3_stoch",
    "wavetrend_flip",
    "micro_rev",
    "stoch_flip",
    "dual_t3",
    "t3_flip",
    "parabolic_flip",
    "ichimoku",
    "nr_break",
    "roc_pace",
    "band_fade",
)

# M5 joined 05.09: zero holdout win on any live symbol, and the panel's own
# option list was still offering it - a live re-infection path. Every guard
# built on this tuple was blind to M5 until it was named here.
RETIRED_TIMEFRAMES = ("H1", "H4", "M10", "M5", "M1", "M3")

# Symbols that left the traded book. Added 05.09: nothing guarded the shipped
# starter list, and it had gone stale without failing anything - it still named
# four of these and had lost BTCUSD, so "varsayilana don"
# (POST /api/symbols-seed?overwrite=true -> store.replace_with_defaults) would
# have deleted the live crypto row and rebuilt a retired portfolio. Seeded rows
# land disabled, but they land in the book, the panel and the scan set.
#
# Only config/defaults.json is scanned for these. Test fixtures use FRA40 and
# UK100 as ordinary synthetic names on purpose and must stay free to.
RETIRED_SYMBOLS = (
    "FRA40",
    "UK100",
    "US2000",
    "US500",
    "GOLD_PERP",
    "EURUSD",
)

# Nearby window contains any of these → the line is documenting removal, not
# offering the family/timeframe as live.
GONE_WORDS = (
    # Turkish
    "kaldirildi",
    "kaldirilmis",
    "silindi",
    "emekli",
    "bayat",
    "eski",
    "artik yok",
    "artik kullan",
    "kullanilmiyor",
    "geri gelme",
    "canli kitap okumaz",
    "canli dort aile",
    "okumaz",
    # English
    "retired",
    "gone",
    "removed",
    "resurrected",
    "obsolete",
    "deprecated",
    "dead",
    "stale",
    "legacy",
    "no longer",
    "fail closed",
    "archive",
    "do not re-add",
    "do not port",
    "unlike",
)

# The whole family book: searched and dormant, both registries (models
# STRATEGIES and strategy._FAMILIES, which must agree).
#
# It lived as a hand-copied literal in five separate guards. super_trend and
# keltner_break landed 07.09 and only one of the five was updated, so the
# other four went red and stayed red - and a red anti-resurrection guard
# guards nothing: ichimoku could have come back without producing a new
# failure. One name here, five guards that read it, one edit when the book
# changes.
#
# Named rather than counted on purpose: adding any family still trips the
# guards, and adding a *retired* one trips them by name.
#
# sweep_fade / range_fade are DORMANT - present in both registries, absent
# from the shipped opt list, so nothing can select them.
LIVING_FAMILIES = frozenset({
    "mtf_pullback",
    "burst",
    "channel_break",
    "super_trend",
    "keltner_break",
    "sweep_fade",
    "range_fade",
})
