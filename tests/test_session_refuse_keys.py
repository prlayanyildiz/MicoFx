"""Session refuse keys: saat_kapali must not tally as seans_disi."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.sessions import SessionState, refuse_block_key, refuse_note


def test_refuse_block_key_maps_saat_kapali():
    assert refuse_block_key("saat kapali") == "saat_kapali"
    assert refuse_block_key("gun kapali") == "gun_kapali"
    assert refuse_block_key("hafta sonu kapali") == "hafta_sonu"
    assert refuse_block_key("seans disi") == "seans_disi"
    assert refuse_block_key("") == "seans_disi"


def test_refuse_note_keeps_window_label():
    sess = SessionState(
        open=False, reason="saat kapali",
        minutes_to_close=None, minutes_to_open=56, window="7/24",
    )
    assert refuse_note(sess) == "saat kapali (7/24)"
    assert "seans disi" not in refuse_note(sess)
