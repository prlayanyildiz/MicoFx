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
    with DEFAULTS_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)
