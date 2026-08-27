"""Production names that had no reader. Strip them; do not wire them back."""
from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.supervisor import Supervisor

ROOT = Path(__file__).resolve().parents[1]


def test_stale_bar_refresh_constant_is_gone():
    import micofx.engine as engine
    assert not hasattr(engine, "_STALE_BAR_REFRESH")
    src = (ROOT / "micofx" / "engine.py").read_text(encoding="utf-8")
    assert "_STALE_BAR_REFRESH" not in src


def test_edge_decomposition_module_is_gone():
    assert importlib.util.find_spec("micofx.edge_decomposition") is None


def test_opt_complete_line_has_no_scheduled_branch():
    src = (ROOT / "micofx" / "optimizer.py").read_text(encoding="utf-8")
    assert "Zamanlanmis" not in src
    assert 'src == "scheduled"' not in src


def test_ai_status_does_not_ship_an_unread_reopt_queue():
    src = inspect.getsource(Supervisor._status_locked)
    assert "reopt_queue" not in src
    init = inspect.getsource(Supervisor.__init__)
    assert "reopt_queue" not in init


def test_unread_capacity_payload_keys_are_gone():
    src = (ROOT / "micofx" / "risk.py").read_text(encoding="utf-8")
    for key in ("slots_by_margin", "open_volume",
                "total_margin_if_all_open", "margin_used"):
        assert f'"{key}"' not in src, key


def test_execution_does_not_ship_an_unread_median():
    src = (ROOT / "micofx" / "execution.py").read_text(encoding="utf-8")
    assert "median_points" not in src


def test_symbol_state_does_not_ship_cooldown_left():
    from micofx.engine import SymbolState
    src = inspect.getsource(SymbolState.as_dict)
    assert "cooldown_left" not in src
    assert "cooldown" not in SymbolState("X").as_dict()


def test_unread_analysis_routes_are_gone():
    src = (ROOT / "micofx" / "web" / "app.py").read_text(encoding="utf-8")
    for path in (
        "/api/analysis/breakeven",
        "/api/analysis/stamp-drift",
        "/api/analysis/cost-by-hour",
        "/api/analysis/correlation",
        "/api/symbols/broker-audit",
        "/api/opt/job",
    ):
        assert path not in src, path
    # Panel reads STATE.ai from /api/state. The duplicate GET had no caller.
    assert '@app.get("/api/ai")' not in src
    # Panel Temizle is DOM-only. The shared-ring wipe had no caller.
    assert "/api/logs/clear" not in src


def test_states_view_does_not_ship_unread_edge_cover():
    from micofx.engine import Engine
    src = inspect.getsource(Engine._states_view)
    assert "edge_cover" not in src
    assert 'row["cost_r"]' not in src


def test_dead_repair_helpers_are_gone():
    import micofx.holdout_cost as hc
    import micofx.strategy as strategy
    from micofx.models import SymbolConfig
    from micofx.optimizer import Optimizer
    from micofx.web.app import _SYMBOL_RISK_BOUNDS
    assert hasattr(hc, "charged_holdout")
    assert not hasattr(Optimizer, "restamp_from_replay")
    assert not hasattr(Optimizer, "stamp_drift")
    assert not hasattr(Optimizer, "_stamp_values_match")
    assert not hasattr(Supervisor, "damning_max_wins")
    assert not hasattr(hc, "replay")
    assert not hasattr(hc, "cost_share")
    assert not hasattr(hc, "_tf_seconds")
    assert not hasattr(hc, "_TF_SECONDS")
    assert not hasattr(strategy, "stamp_fields")
    assert not hasattr(strategy, "STOCH_MID")
    assert "partial_close_lots" not in SymbolConfig.__dataclass_fields__
    assert "partial_close_lots" not in _SYMBOL_RISK_BOUNDS
    help_js = (ROOT / "micofx" / "web" / "static" / "field_help.js").read_text(
        encoding="utf-8")
    app_js = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(
        encoding="utf-8")
    assert "partial_close_lots" not in help_js
    assert "partial_close_lots" not in app_js


def test_unread_payload_keys_are_gone():
    """Written once, read by neither the panel nor a production caller."""
    opt = (ROOT / "micofx" / "optimizer.py").read_text(encoding="utf-8")
    bt = (ROOT / "micofx" / "backtest.py").read_text(encoding="utf-8")
    mt5 = (ROOT / "micofx" / "mt5client.py").read_text(encoding="utf-8")
    sup = inspect.getsource(Supervisor._persist)
    assert "pending_exit_fields" not in opt
    assert "validation_net_r" not in opt
    assert "holdout_net_r" not in opt
    assert '"raw_score"' not in bt
    assert '"plateau_neighbours"' not in bt
    assert '"screened_out"' not in bt
    assert '"span_days"' not in bt
    assert '"holdout_bars"' not in bt
    assert '"contract_size"' not in mt5
    assert '"currency_profit"' not in mt5
    assert '"saved_at"' not in sup
    from micofx.engine import Engine, SymbolState
    from micofx.execution import ExecutionMonitor
    snap = inspect.getsource(Engine.snapshot)
    # Panel reads day.realised / positions profit / the poll loop reads Store.
    assert '"poll_interval_sec"' not in snap
    assert '"cash_flow"' not in snap
    assert '"floating"' not in snap
    assert '"wins"' not in snap
    assert '"session_clock_skew_hours"' not in inspect.getsource(Engine._session_clock_payload)
    assert '"tracked"' not in inspect.getsource(ExecutionMonitor.stats)
    assert "_FALLBACK_PATHS" not in mt5
    app = (ROOT / "micofx" / "web" / "app.py").read_text(encoding="utf-8")
    # Duplicate of max_spread_atr on the same row; panel reads the latter.
    assert '"primary_max_spread_atr"' not in app
    get_opt = app[app.index("def opt_params"):app.index("def set_opt_params")]
    assert "swing_overlay" not in get_opt
    assert "SWING_GRID_OVERLAY" not in get_opt
    view = inspect.getsource(Engine._states_view)
    assert '"last_bar"' not in view
    assert '"t3_kind"' not in view
    assert '"signal_source"' not in view
    assert '"t3_kind"' in inspect.getsource(SymbolState.as_dict)
    assert "row.pop(\"tried\"" in (ROOT / "micofx" / "optimizer.py").read_text(
        encoding="utf-8")


def test_unused_simulate_wrappers_are_gone():
    """run() had zero callers. mae_close was a measurement switch search
    never passed — live does not exit on MAE, and the kwargs sat in the
    hot loop for a counterfactual only tests invoked.
    """
    from micofx import backtest
    assert not hasattr(backtest, "run")
    sig = inspect.signature(backtest.simulate)
    assert "mae_close_bars" not in sig.parameters
    assert "mae_close_r" not in sig.parameters
    src = inspect.getsource(backtest.simulate)
    assert "mae_close_bars" not in src
    assert "mae_hit" not in src
    wf = inspect.getsource(backtest.walk_forward)
    assert "mae_close" not in wf
