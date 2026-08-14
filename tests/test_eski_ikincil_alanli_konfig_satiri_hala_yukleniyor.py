"""Eski DB satirlarinda ikincil alanlar var; from_dict onlari yok saymali.

A4: SymbolConfig no longer has secondary_* / ensemble_enabled. Live rows
still carry them. If from_dict started rejecting unknown keys the bot
would not start.
"""
from __future__ import annotations

import json
from pathlib import Path

from micofx.models import SymbolConfig

_FIXTURE = (Path(__file__).resolve().parent / "fixtures"
            / "eski_ikincil_konfig_fra40.json")
_BOOK = (Path(__file__).resolve().parent / "fixtures"
         / "eski_ikincil_konfig_kitap.json")

_LEFTOVER = (
    "ensemble_enabled",
    "secondary_strategy",
    "secondary_timeframe",
    "secondary_params",
    "secondary_score",
    "secondary_updated_at",
    "secondary_summary",
    "pending_secondary_exit_patch",
)


def test_eski_ikincil_alanli_konfig_satiri_hala_yukleniyor():
    payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    for key in _LEFTOVER:
        assert key in payload, f"fikstur eski alani kaybetmis: {key}"
    cfg = SymbolConfig.from_dict(payload)
    assert cfg.symbol == "FRA40"
    assert cfg.strategy == "micro_rev"
    assert cfg.timeframe == "M30"
    assert cfg.enabled is True
    for key in _LEFTOVER:
        assert not hasattr(cfg, key)


def test_eski_kitap_on_sembol_hala_yukleniyor():
    book = json.loads(_BOOK.read_text(encoding="utf-8"))
    assert len(book) == 10
    for symbol, payload in book.items():
        cfg = SymbolConfig.from_dict(payload)
        assert cfg.symbol == symbol
        assert cfg.magic > 0
        assert not hasattr(cfg, "secondary_strategy")
        assert not hasattr(cfg, "ensemble_enabled")
