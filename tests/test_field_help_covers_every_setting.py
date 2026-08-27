"""AK1: every editable setting key must have one dictionary entry."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "micofx" / "web" / "static" / "app.js").read_text(encoding="utf-8")
HELP = (ROOT / "micofx" / "web" / "static" / "field_help.js").read_text(encoding="utf-8")


def _block(name: str) -> str:
    start = JS.index(f"const {name}")
    nxt = JS.find("\nconst ", start + 1)
    if nxt < 0:
        nxt = JS.find("\nfunction ", start + 1)
    return JS[start:nxt]


def _keys(block: str) -> list[str]:
    return re.findall(r"""\{ k:\s*"([^"]+)" """, block)


def _help_keys() -> set[str]:
    return set(re.findall(r"""^\s+"([^"]+)":""", HELP, flags=re.M))


def test_field_help_file_exists_as_one_dictionary():
    assert "const FIELD_HELP" in HELP
    assert "FIELD_HELP" in JS


def test_every_setting_key_has_a_help_entry():
    help_keys = _help_keys()
    missing: list[str] = []
    opt = set(_keys(_block("OPT_SETTING_FIELDS")))
    for name in (
        "OPT_SETTING_FIELDS",
        "SYS_FIELDS", "SYS_FIELDS_ADVANCED",
        "BACKUP_FIELDS", "MT5_PATH_FIELDS",
    ):
        for k in _keys(_block(name)):
            if k not in help_keys:
                missing.append(k)
    for k in _keys(_block("AI_SETTING_FIELDS")):
        want = f"ai.{k}" if k in opt else k
        if want not in help_keys and k not in help_keys:
            missing.append(want)
    for extra in ("use_sessions", "flat_before_close_min"):
        if extra not in help_keys:
            missing.append(extra)
    assert missing == [], f"FIELD_HELP missing: {missing}"


def test_builders_read_help_from_the_dictionary():
    assert "helpTitle(" in JS
    assert "applyStaticHelp" in JS


def test_every_data_help_key_is_in_the_dictionary():
    html = (ROOT / "micofx" / "web" / "templates" / "index.html").read_text(encoding="utf-8")
    help_keys = _help_keys()
    used = re.findall(r'data-help="([^"]+)"', html)
    missing = [k for k in used if k not in help_keys]
    assert used, "no data-help attributes"
    assert missing == [], f"FIELD_HELP missing data-help keys: {missing}"
