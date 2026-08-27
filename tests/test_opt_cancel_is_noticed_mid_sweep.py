"""Cancel must be noticed while workers are still inside a sweep.

The panel Iptal button looked dead during a 14-worker search: harvest()
waited on FIRST_COMPLETED with no timeout, then `with ProcessPoolExecutor`
shutdown(wait=True) waited for the rest. Child processes never see
Optimizer._cancel. The event was set; apply() of remaining symbols was
blocked; the job stayed `running` until the in-flight sweeps finished.
"""
from __future__ import annotations

import inspect
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.optimizer import Optimizer


def test_harvest_wait_has_a_timeout_so_cancel_is_not_stuck_on_a_worker():
    src = inspect.getsource(Optimizer._search_parallel)
    assert "timeout=" in src
    assert "futures_wait" in src


def test_cancel_abandons_the_pool_instead_of_waiting_out_inflight_sweeps():
    src = inspect.getsource(Optimizer._search_parallel)
    assert "_abandon_search_pool" in src
    abandon = inspect.getsource(Optimizer._abandon_search_pool)
    assert "terminate" in abandon
    assert "shutdown" in abandon
    assert "wait=False" in abandon or "wait = False" in abandon


def test_abandon_search_pool_terminates_worker_processes():
    killed: list[int] = []

    class _Proc:
        def terminate(self):
            killed.append(1)

    class _Pool:
        def __init__(self):
            self._processes = {1: _Proc(), 2: _Proc()}
            self.shutdowns: list[tuple] = []

        def shutdown(self, wait=True, cancel_futures=False):
            self.shutdowns.append((wait, cancel_futures))

    opt = Optimizer.__new__(Optimizer)
    opt._cancel = threading.Event()
    pool = _Pool()
    inflight = {object(): {"symbol": "GER40"}}
    opt._abandon_search_pool(pool, inflight)
    assert inflight == {}
    assert killed == [1, 1]
    assert pool.shutdowns == [(False, True)]


def test_cancel_marks_the_live_job_cancelled_before_workers_die():
    """Panel reads optimizer.status(), not last_opt_job. Three Iptal clicks
    set the event and wrote the store; job.state stayed running at 160000
    until harvest timed out, so the button looked dead.
    """
    opt = Optimizer.__new__(Optimizer)
    opt._cancel = threading.Event()
    opt._lock = threading.Lock()
    opt._thread = type("T", (), {"is_alive": lambda self: True})()
    opt.job = {
        "state": "running", "current": "GER40",
        "combo_done": 160000, "combo_total": 3081600,
    }
    opt.store = type("S", (), {
        "set_setting": staticmethod(lambda *a, **k: None),
        "get_setting": staticmethod(lambda *a, **k: {}),
    })()
    res = opt.cancel()
    assert res["ok"]
    assert opt.job["state"] == "cancelled"
    assert opt._cancel.is_set()
