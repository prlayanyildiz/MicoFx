from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
WEB_DIR = Path(__file__).resolve().parent / "web"

DB_PATH = DATA_DIR / "micofx.db"
DEFAULTS_PATH = CONFIG_DIR / "defaults.json"


_LEGACY = [(DATA_DIR / "micoai.db", DB_PATH),
           (LOG_DIR / "micoai.log", LOG_DIR / "micofx.log")]


def ensure_dirs() -> None:
    for d in (CONFIG_DIR, DATA_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)
    # Carry history over from the pre-rename files instead of starting fresh.
    for old, new in _LEGACY:
        if old.exists() and not new.exists():
            old.rename(new)


def load_defaults() -> dict[str, Any]:
    """Read config/defaults.json, or fail with something an operator can read.

    Store.__init__ already refuses to let a broken settings DB reach the
    caller as a bare traceback, because under pythonw.exe that goes to a
    stream nobody sees and the app simply never appears. This file is read
    one line EARLIER than that in run.py, outside any try/except, and had no
    equivalent - so a config problem produced exactly the failure the DB path
    was written to prevent.

    ``utf-8-sig`` rather than ``utf-8``: Notepad and PowerShell's ``>`` both
    write a UTF-8 BOM on Windows, and json.load rejects it outright. Editing
    this file with the most obvious tool on the machine it runs on should not
    stop the app starting.

    The type check matters as much as the parse: ``[1, 2, 3]`` and ``"text"``
    are valid JSON, so they load cleanly and then fail one line later in
    run.py on ``defaults.get(...)`` with an AttributeError - further from the
    cause and harder to read.
    """
    try:
        with DEFAULTS_PATH.open("r", encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Ayar sablonu bulunamadi: {DEFAULTS_PATH}\n"
            f"Depodan bu dosyayi geri alin (git checkout config/defaults.json) "
            f"ya da MicoFX'i yeniden kurun."
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Ayar sablonu bozuk: {DEFAULTS_PATH}\n"
            f"JSON okunamadi (satir {exc.lineno}, sutun {exc.colno}): {exc.msg}\n"
            f"Dosya elle duzenlendiyse geri alin: git checkout config/defaults.json"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"Ayar sablonu okunamadi: {DEFAULTS_PATH}\n{exc}"
        ) from exc
    if not isinstance(data, dict):
        raise RuntimeError(
            f"Ayar sablonu beklenen bicimde degil: {DEFAULTS_PATH}\n"
            f"Dosyanin tamami bir JSON nesnesi olmali, {type(data).__name__} bulundu."
        )
    return data
