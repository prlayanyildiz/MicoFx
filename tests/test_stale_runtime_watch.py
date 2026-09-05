"""stale_runtime_watch — land-vs-live mtime alarm (Claude 20:32)."""
from __future__ import annotations

import json
import time
from pathlib import Path

from scripts.stale_runtime_watch import (
    collect_manifest,
    evaluate,
    maybe_alert,
    write_boot_stamp,
)


def test_evaluate_not_armed_without_boot():
    rep = evaluate(boot=None, current={"micofx/engine.py": 1.0})
    assert rep["armed"] is False
    assert rep["fire"] is False
    assert rep["stale"] == []


def test_evaluate_fires_when_disk_newer(tmp_path: Path):
    boot = {
        "engine_started_at": 100.0,
        "manifest": {"micofx/engine.py": 50.0, "micofx/exits.py": 50.0},
    }
    current = {"micofx/engine.py": 80.0, "micofx/exits.py": 50.0}
    rep = evaluate(boot=boot, current=current)
    assert rep["armed"] is True
    assert rep["fire"] is True
    assert rep["stale"][0]["path"] == "micofx/engine.py"
    assert rep["stale"][0]["hours_newer"] > 0


def test_evaluate_silent_when_fresh():
    boot = {
        "engine_started_at": 100.0,
        "manifest": {"micofx/engine.py": 90.0},
    }
    rep = evaluate(boot=boot, current={"micofx/engine.py": 90.0})
    assert rep["fire"] is False
    assert rep["stale"] == []


def test_evaluate_new_file_counts_stale():
    boot = {
        "engine_started_at": 100.0,
        "manifest": {"micofx/engine.py": 90.0},
    }
    current = {"micofx/engine.py": 90.0, "micofx/new_mod.py": 95.0}
    rep = evaluate(boot=boot, current=current)
    assert rep["fire"] is True
    assert any(s["path"] == "micofx/new_mod.py" for s in rep["stale"])


def test_collect_manifest_skips_pycache_and_scripts(tmp_path: Path):
    mic = tmp_path / "micofx"
    mic.mkdir()
    (mic / "engine.py").write_text("x", encoding="utf-8")
    cache = mic / "__pycache__"
    cache.mkdir()
    (cache / "engine.cpython-312.pyc").write_bytes(b"\0")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "stale_runtime_watch.py").write_text("y", encoding="utf-8")
    man = collect_manifest(tmp_path)
    assert "micofx/engine.py" in man
    assert not any("__pycache__" in k for k in man)
    assert not any(k.startswith("scripts/") for k in man)


def test_maybe_alert_noop_when_not_armed(tmp_path: Path):
    state = tmp_path / "st.json"
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    snap = evaluate(boot=None, current={"micofx/engine.py": 1.0})
    assert maybe_alert(
        snap, state_path=state, wake_path=wake, cursor_inbox=inbox,
        n_open=0) == []
    assert not wake.exists()


def test_maybe_alert_once_while_stale_no_restart_when_open(tmp_path: Path):
    state = tmp_path / "st.json"
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    restart_flag = tmp_path / "STALE_RUNTIME_RESTART_WHEN_FLAT"
    boot = {
        "engine_started_at": time.time() - 3600,
        "manifest": {"micofx/engine.py": 10.0},
    }
    snap = evaluate(boot=boot, current={"micofx/engine.py": 99.0})
    notes = maybe_alert(
        snap, state_path=state, wake_path=wake, cursor_inbox=inbox,
        n_open=1, restart_flag=restart_flag)
    assert any("STALE" in n.upper() or "stale" in n.lower() for n in notes)
    assert wake.is_file()
    assert "stale" in inbox.read_text(encoding="utf-8").lower()
    assert not restart_flag.exists()  # positions open — no restart arm
    assert maybe_alert(
        snap, state_path=state, wake_path=wake, cursor_inbox=inbox,
        n_open=1, restart_flag=restart_flag) == []


def test_maybe_alert_arms_restart_flag_only_when_flat(tmp_path: Path):
    state = tmp_path / "st.json"
    wake = tmp_path / "WAKE.txt"
    inbox = tmp_path / "FOR_CLAUDE.md"
    restart_flag = tmp_path / "STALE_RUNTIME_RESTART_WHEN_FLAT"
    boot = {
        "engine_started_at": time.time() - 3600,
        "manifest": {"micofx/engine.py": 10.0},
    }
    snap = evaluate(boot=boot, current={"micofx/engine.py": 99.0})
    notes = maybe_alert(
        snap, state_path=state, wake_path=wake, cursor_inbox=inbox,
        n_open=0, restart_flag=restart_flag)
    assert notes
    assert restart_flag.is_file()
    body = restart_flag.read_text(encoding="utf-8")
    assert "flat" in body.lower() or "restart" in body.lower()


def test_write_boot_stamp_roundtrip(tmp_path: Path):
    mic = tmp_path / "micofx"
    mic.mkdir()
    (mic / "a.py").write_text("1", encoding="utf-8")
    out = tmp_path / "RUNTIME_BOOT_MANIFEST.json"
    payload = write_boot_stamp(tmp_path, out, started_at=123.0)
    assert payload["engine_started_at"] == 123.0
    assert "micofx/a.py" in payload["manifest"]
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["engine_started_at"] == 123.0
