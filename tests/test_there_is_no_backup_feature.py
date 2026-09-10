"""Operator, 10.09: "backup.py surecini bastan sona iptal edelim lutfen.
bunla alakalida surec calismasin" and then, after seeing the archive still
listed in a terminal, "yedekle alakali tum kalintilari temizle".

The feature was removed whole: the script, the scheduled task, the five
SystemConfig fields, the panel block, the installer step and the docs. It had
been trimmed in pieces twice before and grew back both times from a leftover
default key, so this pins the whole surface instead of one file.

If a backup is ever wanted again it must be a new decision with a new test -
not a resurrection through a stray key nobody noticed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The five fields the feature actually lived on, plus the module name. Prose is
# free to say the word - OPTIMIZATIONS.md is an append-only log of what
# happened on which day, and a comment may cite the removed script as
# precedent for a technique. What must not come back is a field or an import.
_FIELDS = ("backup_enabled", "backup_dir", "backup_dir_secondary",
           "backup_keep", "backup_dir_allow_unc")
_IMPORTS = re.compile(r"^\s*(?:import\s+backup\b|from\s+backup\s+import)"
                      r"|\bbackup\.(?:main|run|make_archive)\b")


def _sources() -> list[Path]:
    out: list[Path] = []
    for pat in ("*.py", "*.js", "*.ps1", "*.bat", "*.vbs", "*.html", "*.css"):
        for p in ROOT.rglob(pat):
            if set(p.parts) & {".git", ".venv", "__pycache__", ".pytest_cache",
                               ".pytest_tmp", "node_modules"}:
                continue
            if p.name == Path(__file__).name:
                continue
            out.append(p)
    return out


def test_the_script_is_gone():
    assert not (ROOT / "backup.py").exists(), "backup.py is back"


def test_no_config_field_carries_a_backup():
    cfg = json.loads((ROOT / "config" / "defaults.json").read_text("utf-8"))

    def walk(node: object, path: str = "") -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                assert "backup" not in str(k).lower(), f"defaults.json{path}.{k}"
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")

    walk(cfg)


def test_no_model_field_carries_a_backup():
    from micofx.models import SymbolConfig, SystemConfig

    for model in (SystemConfig(), SymbolConfig(symbol="XAUUSD", magic=1)):
        named = [f for f in vars(model) if "backup" in f.lower()]
        assert named == [], f"{type(model).__name__}: {named}"


def test_no_code_reads_a_backup_field_or_imports_the_module():
    offenders: list[str] = []
    for p in _sources():
        text = p.read_text("utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(("#", "//", "*", "<!--")):
                continue
            hit = next((f for f in _FIELDS if f in line), None)
            if hit is None and _IMPORTS.search(line):
                hit = "import backup"
            if hit is not None:
                offenders.append(f"{p.relative_to(ROOT)}:{n}: {hit}")
    assert offenders == [], "backup remnant in code:\n" + "\n".join(offenders)


def test_the_installer_registers_no_task():
    ps1 = (ROOT / "KUR.ps1").read_text("utf-8", errors="replace")
    for n, line in enumerate(ps1.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        low = line.lower()
        for token in ("register-scheduledtask", "new-scheduledtask", "schtasks"):
            assert token not in low, f"KUR.ps1:{n} registers a task: {line.strip()}"


def test_no_backup_log_is_written():
    assert not (ROOT / "logs" / "yedek.log").exists(), "yedek.log is back"
