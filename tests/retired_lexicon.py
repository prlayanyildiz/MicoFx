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
)

RETIRED_TIMEFRAMES = ("H1", "H4", "M10", "M1", "M3")

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
