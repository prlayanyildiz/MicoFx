"""tests/test_full_audit.py — Tam denetim modülü birim testleri.

Gerçek DB veya MT5 kullanmaz; Store'u mock'lar.
"""
from __future__ import annotations

import json
import types
from unittest.mock import MagicMock

# ── Yardımcılar ───────────────────────────────────────────────────────────

def _make_symbol_cfg(**overrides):
    """Basit bir SymbolConfig benzeri nesne üretir."""
    defaults = {
        "symbol": "XAUUSD",
        "group": "commodity",
        "magic": 990000,
        "enabled": True,
        "strategy": "burst",
        "sl_atr_mult": 1.2,
        "trail_start_atr": 0.8,
        "trail_step_atr": 0.6,
        "atr_period": 14,
        "breakeven_at_r": 1.5,
        "partial_at_r": 0.0,
        "harvest_at_r": 0.0,
        "harvest_step_atr": 0.0,
        "mfe_lock1_at_r": 1.5,
        "mfe_lock1_to_r": 0.75,
        "mfe_lock2_at_r": 2.0,
        "mfe_lock2_to_r": 1.25,
        "adx_min": 0.0,
        "max_spread_atr": 0.0,
        "trail_mode": "atr",
        "trail_lookback": 5,
    }
    defaults.update(overrides)
    cfg = types.SimpleNamespace(**defaults)
    cfg.to_dict = lambda: {k: v for k, v in vars(cfg).items() if k != "to_dict"}
    return cfg


def _make_system_cfg(**overrides):
    """Basit bir SystemConfig benzeri nesne üretir."""
    defaults = {
        "running": True,
        "max_concurrent_risk_pct": 25.0,
        "lot_multiplier": 1.0,
        "daily_loss_pct": 3.0,
        "charge_costs": True,
        "autopilot_enabled": True,
    }
    defaults.update(overrides)
    cfg = types.SimpleNamespace(**defaults)
    cfg.to_dict = lambda: {k: v for k, v in vars(cfg).items() if k != "to_dict"}
    return cfg


def _make_store(system_overrides=None, symbols=None, opt_overrides=None):
    """Sahte Store nesnesi oluşturur."""
    store = MagicMock()
    store.system = _make_system_cfg(**(system_overrides or {}))
    store.symbols = symbols or {
        "GER40": _make_symbol_cfg(symbol="GER40", strategy="channel_break"),
        "NAS100": _make_symbol_cfg(symbol="NAS100", strategy="burst"),
        "XAUUSD": _make_symbol_cfg(symbol="XAUUSD", strategy="mtf_pullback"),
    }
    opt_defaults = {"max_combos": 2000, "lookback_days": 180, "timeframes": ["M15", "M30"]}
    if opt_overrides:
        opt_defaults.update(opt_overrides)
    store.opt_params.return_value = opt_defaults
    return store


# ── Testler ───────────────────────────────────────────────────────────────

class TestRetiredSymbols:
    def test_pass_no_retired_symbols(self):
        from micofx.audit.full_audit import _check_retired_symbols
        symbols = {
            "GER40": _make_symbol_cfg(symbol="GER40"),
            "NAS100": _make_symbol_cfg(symbol="NAS100"),
        }
        results = _check_retired_symbols(symbols)
        assert all(r["status"] == "PASS" for r in results)

    def test_fail_retired_symbol_present(self):
        from micofx.audit.full_audit import _check_retired_symbols
        symbols = {
            "GER40": _make_symbol_cfg(symbol="GER40"),
            "US30": _make_symbol_cfg(symbol="US30"),
        }
        results = _check_retired_symbols(symbols)
        assert any(r["status"] == "FAIL" and "US30" in r["details"] for r in results)


class TestMaxCombos:
    def test_pass_within_limit(self):
        from micofx.audit.full_audit import _check_max_combos
        result = _check_max_combos({"max_combos": 2000})
        assert result["status"] == "PASS"

    def test_fail_exceeds_limit(self):
        from micofx.audit.full_audit import _check_max_combos
        result = _check_max_combos({"max_combos": 5000})
        assert result["status"] == "FAIL"
        assert "5000" in result["details"]

    def test_fail_missing(self):
        from micofx.audit.full_audit import _check_max_combos
        result = _check_max_combos({})
        assert result["status"] == "FAIL"


class TestConcurrentRisk:
    def test_pass_correct_value(self):
        from micofx.audit.full_audit import _check_concurrent_risk
        cfg = _make_system_cfg(max_concurrent_risk_pct=25.0)
        result = _check_concurrent_risk(cfg)
        assert result["status"] == "PASS"

    def test_fail_wrong_value(self):
        from micofx.audit.full_audit import _check_concurrent_risk
        cfg = _make_system_cfg(max_concurrent_risk_pct=50.0)
        result = _check_concurrent_risk(cfg)
        assert result["status"] == "FAIL"
        assert "50.0" in result["details"]


class TestBannedExitFields:
    def test_pass_no_banned_fields(self):
        from micofx.audit.full_audit import _check_banned_exit_fields
        symbols = {"GER40": _make_symbol_cfg()}
        results = _check_banned_exit_fields(symbols)
        assert all(r["status"] == "PASS" for r in results)

    def test_fail_banned_field_present(self):
        from micofx.audit.full_audit import _check_banned_exit_fields
        symbols = {"GER40": _make_symbol_cfg(tp_atr_mult=2.0)}
        results = _check_banned_exit_fields(symbols)
        assert any(r["status"] == "FAIL" and "tp_atr_mult" in r["details"] for r in results)


class TestBackupFields:
    def test_pass_no_backup(self):
        from micofx.audit.full_audit import _check_backup_fields
        cfg = _make_system_cfg()
        result = _check_backup_fields(cfg)
        assert result["status"] == "PASS"

    def test_fail_backup_present(self):
        from micofx.audit.full_audit import _check_backup_fields
        cfg = _make_system_cfg(backup_enabled=True)
        result = _check_backup_fields(cfg)
        assert result["status"] == "FAIL"
        assert "backup_enabled" in result["details"]


class TestNonFinite:
    def test_pass_all_finite(self):
        from micofx.audit.full_audit import _check_non_finite_system
        cfg = _make_system_cfg()
        result = _check_non_finite_system(cfg)
        assert result["status"] == "PASS"

    def test_fail_nan_in_system(self):
        from micofx.audit.full_audit import _check_non_finite_system
        cfg = _make_system_cfg(lot_multiplier=float("nan"))
        result = _check_non_finite_system(cfg)
        assert result["status"] == "FAIL"

    def test_fail_inf_in_symbol(self):
        from micofx.audit.full_audit import _check_non_finite_symbols
        symbols = {"GER40": _make_symbol_cfg(sl_atr_mult=float("inf"))}
        results = _check_non_finite_symbols(symbols)
        assert any(r["status"] == "FAIL" for r in results)


class TestStrategyFamilies:
    def test_pass_valid_families(self):
        from micofx.audit.full_audit import _check_strategy_families
        symbols = {
            "GER40": _make_symbol_cfg(strategy="channel_break"),
            "NAS100": _make_symbol_cfg(strategy="burst"),
        }
        results = _check_strategy_families(symbols)
        assert all(r["status"] == "PASS" for r in results)

    def test_fail_retired_family(self):
        from micofx.audit.full_audit import _check_strategy_families
        symbols = {"GER40": _make_symbol_cfg(strategy="ichimoku")}
        results = _check_strategy_families(symbols)
        assert any(r["status"] == "FAIL" and "ichimoku" in r["details"] for r in results)


class TestExitParamBounds:
    def test_pass_valid_params(self):
        from micofx.audit.full_audit import _check_exit_risk_consistency
        symbols = {"GER40": _make_symbol_cfg(sl_atr_mult=1.2)}
        results = _check_exit_risk_consistency(symbols)
        assert all(r["status"] == "PASS" for r in results)

    def test_fail_zero_sl(self):
        from micofx.audit.full_audit import _check_exit_risk_consistency
        symbols = {"GER40": _make_symbol_cfg(sl_atr_mult=0.0)}
        results = _check_exit_risk_consistency(symbols)
        assert any(r["status"] == "FAIL" for r in results)


class TestRunFullAudit:
    def test_all_pass_scenario(self, tmp_path, monkeypatch):
        """Tüm kuralların sağlandığı bir senaryo."""
        from micofx.audit.full_audit import run_full_audit
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(exist_ok=True)

        store = _make_store()
        result = run_full_audit(store)

        assert "report" in result
        fails = [r for r in result["report"] if r["status"] == "FAIL"]
        assert len(fails) == 0, f"Beklenmeyen hatalar: {fails}"

    def test_multiple_failures(self, tmp_path, monkeypatch):
        """Birden fazla kural ihlali olan bir senaryo."""
        from micofx.audit.full_audit import run_full_audit
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(exist_ok=True)

        symbols = {
            "GER40": _make_symbol_cfg(strategy="channel_break"),
            "US30": _make_symbol_cfg(symbol="US30", strategy="ichimoku",
                                     tp_atr_mult=2.0, sl_atr_mult=0.0),
        }
        store = _make_store(
            system_overrides={"max_concurrent_risk_pct": 50.0},
            symbols=symbols,
            opt_overrides={"max_combos": 5000},
        )
        result = run_full_audit(store)

        fails = [r for r in result["report"] if r["status"] == "FAIL"]
        fail_rules = {r["rule"] for r in fails}
        assert "retired_symbols" in fail_rules
        assert "max_combos" in fail_rules
        assert "concurrent_risk" in fail_rules

    def test_report_file_written(self, tmp_path, monkeypatch):
        """Raporun JSON dosyasına yazıldığını doğrular."""
        from micofx.audit.full_audit import run_full_audit
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir(exist_ok=True)

        store = _make_store()
        run_full_audit(store)

        report_path = tmp_path / "data" / "full_audit_report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert "report" in data
        assert len(data["report"]) > 0
