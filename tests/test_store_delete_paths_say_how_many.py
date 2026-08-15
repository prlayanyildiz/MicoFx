"""Silent opt_runs deletes must return and log the row count when it is > 0."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import micofx.store as store_module
from micofx.logbus import LOG
from micofx.models import SymbolConfig


def _store(tmp_path, monkeypatch):
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "opt.db")
    monkeypatch.setattr(store_module, "ensure_dirs", lambda: None)
    return store_module.Store()


def _cap_logs():
    logs: list[tuple[str, str]] = []
    orig = LOG.emit

    def _cap(msg, level="INFO", symbol=""):
        logs.append((str(msg), str(level)))
        return orig(msg, level, symbol)

    LOG.emit = _cap
    return logs, orig


def test_record_opt_run_returns_trimmed_count_and_logs_only_when_positive(tmp_path, monkeypatch):
    st = _store(tmp_path, monkeypatch)
    logs, orig = _cap_logs()
    try:
        for i in range(40):
            st.record_opt_run("US500", float(i), {"i": i}, applied=False)
        assert not any("kirp" in m.lower() or "opt_runs" in m for m, _ in logs)
        st.record_opt_run("US500", 99.0, {"i": 99}, applied=False)
        assert any(level == "OPT" and "1" in msg for msg, level in logs), logs
    finally:
        LOG.emit = orig
    left = st._db.execute("SELECT COUNT(*) AS n FROM opt_runs WHERE symbol='US500'").fetchone()
    assert int(left["n"]) == 40


def test_delete_symbol_returns_opt_runs_removed_and_warns(tmp_path, monkeypatch):
    st = _store(tmp_path, monkeypatch)
    st.save_symbol(SymbolConfig(symbol="GER40", magic=990001))
    for i in range(3):
        st.record_opt_run("GER40", float(i), {}, applied=False)
    logs, orig = _cap_logs()
    try:
        removed = st.delete_symbol("GER40")
        assert removed == 3
        assert any(level == "WARN" and "3" in msg and "GER40" in msg for msg, level in logs), logs
    finally:
        LOG.emit = orig
    assert st._db.execute("SELECT COUNT(*) AS n FROM opt_runs WHERE symbol='GER40'").fetchone()["n"] == 0


def test_delete_symbol_with_no_runs_is_silent_and_returns_zero(tmp_path, monkeypatch):
    st = _store(tmp_path, monkeypatch)
    st.save_symbol(SymbolConfig(symbol="FRA40", magic=990002))
    logs, orig = _cap_logs()
    try:
        assert st.delete_symbol("FRA40") == 0
        assert not any("opt_runs" in m for m, _ in logs)
    finally:
        LOG.emit = orig


def test_purge_orphan_history_logs_warn_when_it_removes_rows(tmp_path, monkeypatch):
    st = _store(tmp_path, monkeypatch)
    st.save_symbol(SymbolConfig(symbol="US30", magic=990003))
    st.record_opt_run("US30", 1.0, {}, applied=False)
    st.record_opt_run("GONE", 1.0, {}, applied=False)
    st.record_opt_run("GONE", 2.0, {}, applied=False)
    logs, orig = _cap_logs()
    try:
        n = st.purge_orphan_history()
        assert n == 2
        assert any(level == "WARN" and "2" in msg for msg, level in logs), logs
    finally:
        LOG.emit = orig


def test_replace_with_defaults_does_not_swallow_the_purge_count(tmp_path, monkeypatch):
    st = _store(tmp_path, monkeypatch)
    st.record_opt_run("ORPH", 1.0, {}, applied=False)
    logs, orig = _cap_logs()
    try:
        st.replace_with_defaults()
        assert any(level == "WARN" and "1" in msg for msg, level in logs), logs
    finally:
        LOG.emit = orig
