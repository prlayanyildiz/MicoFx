"""AL1: remaining footnotes stay in FIELD_HELP, not beside the control."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
HELP = (ROOT / "micofx" / "web" / "static" / "field_help.js").read_text(encoding="utf-8")

# Off the panel: leftover keys stay in FIELD_HELP so a restore cannot
# dump the old paragraph back into a hint: blob.
OFF_PANEL = {
    "symbol_daily_loss_pct": "sadece bu sembolde yeni giris",
    "daily_loss_pct": "yeni giris durur",
    "daily_loss_flatten": "acik pozisyonlar da kapanir",
    "size_by_edge": "holdout net R",
    "max_concurrent_risk_pct": "artik okunmaz",
    "sl_atr_mult": "Stop mesafesi",
    "trail_start_atr": "trail baslamaz",
    "trail_step_atr": "Trail",
    "breakeven_at_r": "stop girise",
    "partial_at_r": "Parca",
    "harvest_at_r": "harvest_step_atr",
    "harvest_step_atr": "Hasat",
    "risk_percent": "Kartta yok",
    "max_total_positions": "Okunmaz",
}


def _field_blob(key: str) -> str:
    if f'k: "{key}"' not in JS:
        return ""
    start = JS.index(f'k: "{key}"')
    nxt = JS.find("{ k:", start + 1)
    return JS[start:nxt if nxt > 0 else start + 800]


def test_remaining_hints_are_in_the_dictionary_not_the_grid():
    for key, snippet in OFF_PANEL.items():
        assert f'k: "{key}"' not in JS, f"{key} still has a panel control"
        assert key in HELP
        assert snippet.lower() in HELP.lower(), f"FIELD_HELP missing old hint fact for {key}: {snippet}"
