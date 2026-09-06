"""Calm-band spread cap may step down when allow_narrow is on."""
from __future__ import annotations

from micofx.spread_calibration import BandReading, cap_from_bands


def _band(name, cont, net, upper=0.09):
    return BandReading(name=name, trades=100, upper_ratio=upper,
                       continuation=cont, net_atr=net)


def test_one_way_still_default_when_calm_below_live():
    # Qualifying band under live cap → no narrow without flag (F49 posture).
    bands = [_band("p0-p50", 0.49, 0.05, 0.08),
             _band("p50-p90", 0.50, 0.06, 0.09)]
    cap, reason = cap_from_bands(bands, current=0.11)
    assert cap == 0.11
    assert "daraltilmadi" in reason


def test_allow_narrow_steps_toward_calm_cap():
    bands = [_band("p0-p50", 0.49, 0.05, 0.08),
             _band("p50-p90", 0.50, 0.06, 0.09)]
    cap, reason = cap_from_bands(
        bands, current=0.11, allow_narrow=True, narrow_step=0.02)
    assert cap == 0.09
    assert "daraltildi" in reason
