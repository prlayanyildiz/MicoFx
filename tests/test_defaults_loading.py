"""A broken config template must not make the app vanish on start-up.

Store.__init__ already refuses to let a broken settings DB reach the caller
as a bare traceback, because under pythonw.exe that goes to a stream nobody
sees and the app simply never appears. load_defaults() is read one line
EARLIER than Store() in run.py, outside any try/except, and had no
equivalent - so a config problem produced exactly the failure the DB path was
written to prevent.

Two shapes are worth calling out:

  * UTF-8 with a BOM. Notepad and PowerShell's ``>`` both write one on
    Windows, and json.load rejects it outright, so editing this file with the
    most obvious tool on the machine it runs on stopped the app starting.
    Now read with utf-8-sig.
  * ``[1, 2, 3]`` and ``"text"``. Both are valid JSON, so they loaded cleanly
    and failed one line later in run.py on ``defaults.get(...)`` with an
    AttributeError - further from the cause and harder to read.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx import paths

REAL = (Path(__file__).resolve().parents[1] / "config" / "defaults.json").read_text(
    encoding="utf-8")


def _point_at(monkeypatch, tmp_path, content: str | None):
    target = tmp_path / "defaults.json"
    if content is not None:
        target.write_text(content, encoding="utf-8")
    monkeypatch.setattr(paths, "DEFAULTS_PATH", target)
    return target


BROKEN = [
    ("dosya-yok", None),
    ("bos", ""),
    ("bosluk", "   \n  "),
    ("kesik-yazma", REAL[:len(REAL) // 2]),
    ("gecersiz-json", "{bozuk,,,}"),
    ("git-conflict", "<<<<<<< HEAD\n" + REAL[:200]),
    ("liste", "[1, 2, 3]"),
    ("metin", '"merhaba"'),
    ("sayi", "42"),
    ("null", "null"),
]


@pytest.mark.parametrize("name,content", BROKEN, ids=[b[0] for b in BROKEN])
def test_a_broken_template_raises_something_readable(name, content, tmp_path, monkeypatch):
    _point_at(monkeypatch, tmp_path, content)
    with pytest.raises(RuntimeError) as err:
        paths.load_defaults()
    message = str(err.value)
    # Names the file, so the operator knows what to fix.
    assert "defaults.json" in message
    # ...and says something, not just a type name.
    assert len(message.splitlines()[0]) > 20


def test_a_bom_is_tolerated(tmp_path, monkeypatch):
    """Notepad and PowerShell's `>` both write one; json.load rejects it."""
    _point_at(monkeypatch, tmp_path, "﻿" + REAL)
    data = paths.load_defaults()
    assert isinstance(data, dict)
    assert "symbols" in data


def test_the_real_template_still_loads(tmp_path, monkeypatch):
    _point_at(monkeypatch, tmp_path, REAL)
    data = paths.load_defaults()
    assert isinstance(data, dict)
    assert data["symbols"]
    assert data["optimizer"]["lookback_days"] > 0


def test_the_error_survives_into_run_main(tmp_path, monkeypatch, capsys):
    """run.py must turn it into exit 1 and a line, not a traceback."""
    import run

    _point_at(monkeypatch, tmp_path, "{bozuk")
    monkeypatch.setattr(run, "load_defaults", paths.load_defaults)
    monkeypatch.setattr(run, "ensure_dirs", lambda: None)
    monkeypatch.setattr(run, "ensure_streams", lambda: None)
    monkeypatch.setattr(run, "cleanup_orphan_workers", lambda: None)

    assert run.main() == 1
    out = capsys.readouterr().out
    assert "defaults.json" in out
    assert "Traceback" not in out


def test_a_permission_error_is_also_wrapped(tmp_path, monkeypatch):
    """Any OSError, not just the missing-file one."""
    target = _point_at(monkeypatch, tmp_path, REAL)

    def _boom(*a, **k):
        raise PermissionError(13, "Erisim engellendi")

    monkeypatch.setattr(type(target), "open", _boom, raising=False)
    with pytest.raises(RuntimeError) as err:
        paths.load_defaults()
    assert "defaults.json" in str(err.value)


def test_the_shipped_template_is_a_dict_of_the_expected_shape():
    """Guards the file itself - it is edited by hand and by scripts."""
    data = json.loads(REAL)
    assert isinstance(data, dict)
    for key in ("symbols", "system", "optimizer"):
        assert key in data, key
    assert isinstance(data["symbols"], list) and data["symbols"]
    magics = [s["magic"] for s in data["symbols"]]
    assert len(magics) == len(set(magics)), "defaults.json'da magic cakismasi"
