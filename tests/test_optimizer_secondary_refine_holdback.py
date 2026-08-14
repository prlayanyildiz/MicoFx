"""Ikincil sinyal 14.08'de kaldirildi (operator karari), bu davranis artik yok.

This file used to pin Optimizer._apply_secondary_locked's refine-holdback
(orphan ticket / pending scan treated as live tagged). That writer is gone
in A1; a search must not be able to mint or refine a secondary candidate.
The orphan holdback on the *primary* apply path is still covered by
test_optimizer_apply_orphan_guard.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer


def test_secondary_refine_writer_is_gone():
    assert not hasattr(Optimizer, "_apply_secondary_locked")
    assert not hasattr(Optimizer, "apply_secondary")
