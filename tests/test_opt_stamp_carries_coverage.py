"""D1c: opt_summary carries grid_total / max_combos / coverage.

Coverage is max_combos / grid_total, capped at 1 — the search budget
against the family grid, not evaluated-combos / grid. ``combos`` is the
evaluated count (one-run MinBTL K). Old complete stamps without these
keys still apply; absence is None, not a refusal.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_apply_without_detail_stamp import NEW, _opt

from micofx.backtest import coverage_of, grid_total_of


def test_coverage_is_budget_over_grid_not_evaluated():
    assert coverage_of(2880, 2000) == 2000 / 2880
    assert coverage_of(1000, 2000) == 1.0
    assert coverage_of(0, 2000) is None
    grid = {"a": [1, 2, 3], "b": [10, 20], "empty": []}
    assert grid_total_of(grid) == 6


def test_old_complete_stamp_without_coverage_still_applies():
    """GAP-4 stamp (holdout / days / validated) is enough. Coverage is new."""
    opt, store, cfg = _opt()
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=NEW)
    assert result["ok"] is True, result
    assert cfg.sl_atr_mult == 2.4
    summary = cfg.opt_summary or {}
    assert summary.get("holdout", {}).get("net_r") == 92.0
    assert summary.get("coverage") is None
    assert summary.get("grid_total") is None
    assert summary.get("max_combos") is None


def test_apply_does_not_refuse_missing_coverage():
    opt, _store, cfg = _opt()
    assert opt._apply_stamp_missing(NEW) == ""
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=NEW)
    assert result["ok"] is True, result
    assert cfg.validated is True


def test_new_apply_writes_coverage_from_detail():
    opt, _store, cfg = _opt()
    detail = dict(NEW)
    detail["grid_total"] = 28800
    detail["max_combos"] = 2000
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=detail)
    assert result["ok"] is True, result
    summary = cfg.opt_summary or {}
    assert summary.get("grid_total") == 28800
    assert summary.get("max_combos") == 2000
    assert summary.get("coverage") == coverage_of(28800, 2000)


def test_old_stamp_without_combos_still_applies():
    opt, _store, cfg = _opt()
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=NEW)
    assert result["ok"] is True, result
    assert (cfg.opt_summary or {}).get("combos") is None


def test_new_apply_writes_combos_from_detail():
    opt, _store, cfg = _opt()
    detail = dict(NEW)
    detail["combos"] = 278
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=detail)
    assert result["ok"] is True, result
    assert (cfg.opt_summary or {}).get("combos") == 278


def test_new_apply_computes_coverage_if_only_grid_and_budget_present():
    opt, _store, cfg = _opt()
    detail = dict(NEW)
    detail["grid_total"] = 1000
    detail["max_combos"] = 2000
    # coverage omitted on purpose — apply fills it from the two integers.
    result = opt.apply("XAUUSD", {"sl_atr_mult": 2.4}, score=9.9, detail=detail)
    assert result["ok"] is True, result
    assert (cfg.opt_summary or {}).get("coverage") == 1.0


def test_finish_symbol_stamps_combos_from_the_sweep():
    """apply() writing the key is not enough if _finish_symbol never sends it."""
    from test_closed_symbol_scan_does_not_apply import _finish_opt, _finish_plan

    opt, store = _finish_opt()
    plan, _ = _finish_plan(enabled=True)
    plan["attempts"][0]["combos"] = 278
    store.symbols[plan["cfg"].symbol] = plan["cfg"]
    report = opt._finish_symbol(plan, apply_best=True)
    assert report.get("applied") is True, report
    assert (plan["cfg"].opt_summary or {}).get("combos") == 278
    assert store.runs[-1]["payload"].get("combos") == 278
