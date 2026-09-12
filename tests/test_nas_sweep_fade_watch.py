"""NAS soft-bleed shim — delegates to xau_streak_watch thresholds."""
from __future__ import annotations

from pathlib import Path

from scripts.nas_sweep_fade_watch import evaluate, maybe_alert, window_stats
from scripts.xau_streak_watch import NET_ALERT_R, recent_expectancy


def test_window_stats_newest_n():
    rows = [
        {"symbol": "NAS100", "exit_time": 1, "r_realised": 1.0},
        {"symbol": "NAS100", "exit_time": 2, "r_realised": -1.0},
        {"symbol": "NAS100", "exit_time": 3, "r_realised": -1.0},
        {"symbol": "GER40", "exit_time": 9, "r_realised": 5.0},
    ]
    st = window_stats(rows, last_n=2)
    assert st["n"] == 2
    assert st["net_r"] == -2.0
    assert st["expectancy"] == -1.0


def test_evaluate_fires_on_soft_exp():
    stats = {"n": 10, "net_r": -4.0, "expectancy": -0.4, "wins": 2, "losses": 8}
    rep = evaluate(stats, strategy="mtf_pullback")
    assert rep["fire"] is True


def test_evaluate_any_family():
    stats = {"n": 10, "net_r": -4.0, "expectancy": -0.4, "wins": 2, "losses": 8}
    assert evaluate(stats, strategy="burst")["fire"] is True


def test_evaluate_needs_min_n():
    stats = {"n": 3, "net_r": -3.0, "expectancy": -1.0, "wins": 0, "losses": 3}
    assert evaluate(stats, strategy="sweep_fade")["fire"] is False


def test_maybe_alert_is_noop(tmp_path: Path):
    """Wakes belong to baseline streak watch — shim stays quiet."""
    state = tmp_path / "st.json"
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_GEMINI.md"
    rep = evaluate(
        {"n": 10, "net_r": -4.0, "expectancy": -0.4, "wins": 2, "losses": 8},
        strategy="mtf_pullback",
    )
    assert maybe_alert(
        rep, state_path=state, wake_path=wake, gemini_inbox=inbox) == []
    assert not wake.exists()


def test_streak_net_floor_merged():
    """Net ≤ −3.0R on 10 closes fires even when mean is above exp floor."""
    # 9 × −0.2 + 1 × −1.4 = −3.2 net, exp = −0.32... wait need exp >= -0.30
    # 9 × −0.25 + 1 × −0.8 = −3.05, exp = −0.305 — still below exp floor
    # Use: 5 × +0.1 + 5 × −0.7 = −3.0 net, exp = −0.3 exactly → need < for exp
    # 6 × 0.0 + 4 × −0.8 = −3.2, exp = −0.32
    # Want net fire with exp NOT below -0.30: 
    # 7 wins of +0.1 and 3 losses of −1.3 → net = 0.7 - 3.9 = −3.2, exp = −0.32
    # Hmm. 8 × +0.05 + 2 × −1.7 = 0.4 - 3.4 = −3.0, exp = −0.30 — alert needs <
    # 8 × +0.1 + 2 × −1.95 = 0.8 - 3.9 = −3.1, exp = −0.31
    #
    # For net-only: need exp >= -0.30 and net <= -3.0
    # 7 × +0.2 + 3 × −1.5 = 1.4 - 4.5 = −3.1, exp = −0.31 still under
    # 9 × +0.05 + 1 × −3.5 = 0.45 - 3.5 = −3.05, exp = −0.305
    # 9 × +0.1 + 1 × −4.0 = 0.9 - 4.0 = −3.1, exp = −0.31
    #
    # Formula: mean m, net = 10*m. Want m >= -0.30 and net <= -3.0
    # → 10*m <= -3 → m <= -0.30. So m >= -0.30 AND m <= -0.30 → m == -0.30
    # And alert uses exp < EXP_ALERT_R (-0.30) OR net <= -3.0
    # At exactly -0.30 exp: exp < -0.30 is False; net = -3.0 → net <= -3.0 True.
    rows = [{"symbol": "NAS100", "r_realised": -0.30} for _ in range(10)]
    exp = recent_expectancy(rows, symbol="NAS100", n=10)
    assert exp["net_r"] == -3.0
    assert exp["expectancy_r"] == -0.3
    assert exp["alert"] is True
    assert NET_ALERT_R == -3.0
