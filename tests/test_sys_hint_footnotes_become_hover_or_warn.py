"""AL1: seven footnotes leave the grid; two become danger-only lines."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
HELP = (ROOT / "micofx" / "web" / "static" / "field_help.js").read_text(encoding="utf-8")

# Distinctive phrases from the old hint: blocks. After the cut they must
# live in FIELD_HELP, not next to the checkbox.
REMOVED = {
    "symbol_daily_loss_pct": "sadece bu sembolde yeni giris",
    "daily_loss_flatten": "sadece yeni islemi durdurur",
    "day_end_flatten_min": "kripto dahil",
    "auto_reopt_weekday": "cumartesi",
    "max_scalp_positions": "swing",
    "opt_max_workers": "canli motor",
    "backup_enabled": "dosya yazmaz",
}

WARN_ON = "seans kapisi kapali; arama rakamlari seans saatlerinde olculdu."
WARN_OFF = "arama makasi odemiyor; secilen konfig canlida odeyecek."


def _field_blob(key: str) -> str:
    start = JS.index(f'k: "{key}"')
    nxt = JS.find("{ k:", start + 1)
    return JS[start:nxt if nxt > 0 else start + 800]


def test_seven_removed_hints_are_in_the_dictionary_not_the_grid():
    for key, snippet in REMOVED.items():
        blob = _field_blob(key)
        assert "hint:" not in blob, f"{key} still has a hint paragraph"
        assert key in HELP
        assert snippet.lower() in HELP.lower(), f"FIELD_HELP missing old hint fact for {key}: {snippet}"


def test_two_flags_warn_only_in_the_dangerous_state():
    assert WARN_ON in JS
    assert WARN_OFF in JS
    assert "syncSysDangerNotes" in JS
    assert "trade_all_hours" in JS
    assert "charge_costs" in JS
    # Permanent paragraphs must be gone.
    assert "hint:" not in _field_blob("trade_all_hours")
    assert "hint:" not in _field_blob("charge_costs")
    # Safe state hides the line (hidden / display none / empty).
    assert "data-sys-warn" in JS
