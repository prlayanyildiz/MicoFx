"""Who started a search must be greppable after the process is gone.

25.08 06:26 a six-symbol apply_best run began with source=manual in memory.
The OPT start line did not name the source, the complete line only
distinguished scheduled vs not, and last_opt_job was never written, so after
midnight restart the surprise could not be audited from disk.

The start() door is the one that knows. Emit there, persist there, before the
worker thread has a chance to die on MT5.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.models import SymbolConfig, SystemConfig
from micofx.optimizer import Optimizer


class _Store:
    def __init__(self, symbols):
        # Production reads store.system.charge_costs (optimizer.py:1005).
        # The real dataclass, not a stub: a stub only carries the field
        # production happens to touch today and drifts again on the next
        # one. This double was stale enough that every test in the file
        # died on AttributeError before its assertion - so the guard it
        # contains proved nothing. Added 05.09.
        self.system = SystemConfig()
        self.symbols = {c.symbol: c for c in symbols}
        self.settings: dict = {}

    def get_setting(self, key, default=None):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value

    def opt_params(self):
        return {}


def _opt(symbols) -> Optimizer:
    opt = Optimizer.__new__(Optimizer)
    opt._lock = threading.RLock()
    opt.store = _Store(symbols)
    opt.job = {}
    opt._cancel = threading.Event()
    opt._force_apply = False
    opt._thread = None
    opt._run = lambda *a, **k: None
    return opt


def _cfg(symbol):
    return SymbolConfig(symbol=symbol, magic=abs(hash(symbol)) % 10_000)


BOOK = [_cfg("GER40"), _cfg("NAS100")]


def test_a_manual_start_logs_kaynak_on_the_opt_line(monkeypatch):
    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "micofx.optimizer.LOG.emit",
        lambda message, level="INFO", symbol="": seen.append((message, level)))
    _opt(BOOK).start(source="manual", apply_best=True, force=False)
    lines = [m for m, lv in seen if lv == "OPT" and "kaynak=" in m]
    assert lines, "OPT satiri kaynagi soylemedi - 06:26 tekrar edilse yine kor olur"
    assert any("kaynak=manual" in m for m in lines)


def test_a_quarantine_start_is_not_logged_as_manual(monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(
        "micofx.optimizer.LOG.emit",
        lambda message, level="INFO", symbol="": seen.append(message))
    _opt(BOOK).start(source="quarantine", apply_best=False, force=True)
    line = next(m for m in seen if "kaynak=" in m)
    assert "kaynak=quarantine" in line
    assert "apply_best=false" in line
    assert "force=true" in line


def test_start_persists_last_opt_job_before_the_worker_runs():
    opt = _opt(BOOK)
    opt.start(symbols=["GER40"], source="manual", apply_best=True, force=False)
    job = opt.store.settings.get("last_opt_job") or {}
    assert job.get("source") == "manual"
    assert job.get("symbols") == ["GER40"]
    assert job.get("apply_best") is True
    assert job.get("force") is False
    assert job.get("state") == "running"
    assert job.get("started_at")


def test_cancel_persists_so_a_kill_does_not_leave_running():
    opt = _opt(BOOK)
    opt.job = {"state": "running", "source": "manual"}
    opt.store.settings["last_opt_job"] = {"state": "running", "source": "manual"}
    opt.cancel()
    assert opt._cancel.is_set()
    blob = opt.store.settings["last_opt_job"]
    assert blob["state"] == "cancelled"
    assert blob.get("finished_at")


def test_cancel_logs_how_far_the_cut_search_had_got(monkeypatch):
    """Panel restart 05:15: last_opt_job cancelled, no OPT line, 1.776M gone."""
    seen: list[str] = []
    monkeypatch.setattr(
        "micofx.optimizer.LOG.emit",
        lambda message, level="INFO", symbol="": seen.append(f"{level}|{message}"))
    opt = _opt(BOOK)
    opt.job = {
        "state": "running", "current": "GER40, JPN225, NAS100",
        "combo_done": 1776000, "combo_total": 2376000,
    }
    opt.store.settings["last_opt_job"] = {"state": "running"}
    opt.cancel()
    line = next(m for m in seen if "yari da kesiliyor" in m)
    assert line.startswith("OPT|")
    assert "GER40, JPN225, NAS100" in line
    assert "1776000" in line
    assert "2376000" in line
    blob = opt.store.settings["last_opt_job"]
    assert blob.get("combo_done") == 1776000
    assert blob.get("combo_total") == 2376000


def test_idle_cancel_does_not_rewrite_a_finished_job():
    opt = _opt(BOOK)
    opt.job = {"state": "done"}
    opt.store.settings["last_opt_job"] = {"state": "done", "source": "manual"}
    opt.cancel()
    assert opt.store.settings["last_opt_job"]["state"] == "done"
