"""A startup that fails silently must still leave something to read.

Four places take care to end a startup problem as a line an operator can act on
rather than a traceback: paths.load_defaults, paths.ensure_dirs,
Store.__init__ and, in run.py, the port check and the interpreter-version
guard. Each says so in its own docstring, and the reason each gives is the
same - under pythonw.exe a traceback goes to a stream nobody reads and the app
simply never appears.

ensure_streams then points stdout and stderr at os.devnull whenever there is no
console. That is correct for its own purpose: a print() must not be able to take
the app down, which is what happened before it existed. But start_silent.vbs
launches through pythonw with a hidden window, which is the normal way this runs
on a server - so every one of those carefully written lines went to the void,
and the outcome was the one all of them exist to prevent: nothing appears, and
nothing says why.

Redirecting the streams themselves to a file is the obvious fix and the wrong
one. uvicorn's access logging goes to stderr as well and the panel polls every
second or two, so that file would be thousands of lines an hour and the failure
would be buried rather than missing. Only fatal startup messages are written.

The version guard writes to the same file with plain stdlib rather than through
the helper, because it deliberately runs above the micofx imports and on an old
enough interpreter some of them cannot import at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run as run_module


def _log(tmp_path: Path) -> str:
    f = tmp_path / "baslatilamadi.log"
    return f.read_text(encoding="utf-8") if f.exists() else ""


# ------------------------------------------------------------- the defect

def test_a_fatal_startup_message_is_written_to_disk(monkeypatch, tmp_path):
    monkeypatch.setattr(run_module, "LOG_DIR", tmp_path)
    run_module.startup_fail("[MicoFX] Ayar sablonu bozuk: config/defaults.json")
    assert "Ayar sablonu bozuk" in _log(tmp_path), (
        "konsolsuz baslatmada acilis hatasi hicbir yere yazilmiyor")


def test_it_carries_a_timestamp(monkeypatch, tmp_path):
    """Several failed starts in a row is the normal shape of this; without a
    time they cannot be told apart."""
    monkeypatch.setattr(run_module, "LOG_DIR", tmp_path)
    run_module.startup_fail("ilk")
    run_module.startup_fail("ikinci")
    lines = [ln for ln in _log(tmp_path).splitlines() if ln.strip()]
    assert len(lines) == 2, "ikinci deneme ilkinin uzerine yazmis"
    assert lines[0][:4].isdigit() and lines[1][:4].isdigit()


def test_it_returns_one_so_the_caller_can_just_return_it():
    assert run_module.startup_fail.__doc__
    assert run_module.startup_fail("x") == 1


# --------------------------------------------------- it must never make it worse

def test_an_unwritable_log_dir_does_not_break_the_report(monkeypatch, tmp_path):
    """A startup already failing must not fail differently because the report
    could not be written."""
    def _denied(self, *a, **k):
        raise PermissionError(13, "Erisim reddedildi", str(self))

    monkeypatch.setattr(run_module, "LOG_DIR", tmp_path / "yok")
    monkeypatch.setattr(Path, "mkdir", _denied)
    assert run_module.startup_fail("hala calisir") == 1


def test_the_file_is_capped(monkeypatch, tmp_path):
    """A restart loop must not fill the disk with the same line."""
    monkeypatch.setattr(run_module, "LOG_DIR", tmp_path)
    big = tmp_path / "baslatilamadi.log"
    big.write_text("x" * (300 * 1024), encoding="utf-8")
    run_module.startup_fail("yeni")
    assert big.stat().st_size < 100 * 1024
    assert "yeni" in _log(tmp_path)


def test_it_still_prints_for_a_console_launch(monkeypatch, tmp_path, capsys):
    """The console path is unchanged - this adds a sink, it does not move one."""
    monkeypatch.setattr(run_module, "LOG_DIR", tmp_path)
    run_module.startup_fail("gorunur")
    assert "gorunur" in capsys.readouterr().out


# --------------------------------------------------- the guard above the imports

def test_the_version_guard_writes_to_the_same_file():
    """It cannot use the helper - it runs above the micofx imports on purpose -
    so the two must at least agree on where to write."""
    src = (Path(__file__).resolve().parents[1] / "run.py").read_text(encoding="utf-8")
    guard = src[src.index("MIN_PYTHON = "):src.index("import uvicorn")]
    assert "baslatilamadi.log" in guard
    assert "makedirs" in guard, "logs/ yoksa yazamaz"
    assert "except Exception" in guard, "rapor yazilamazsa acilis farkli sekilde olmemeli"
