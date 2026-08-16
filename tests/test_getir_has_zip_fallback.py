"""GETIR must still install when git and winget are both missing.

The operator's first zero-PC attempt died on `git` not found; Windows Server
often has no winget either. The ZIP of main is public and was measured to
unpack KUR.bat. Removing that branch would recreate the stall.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GETIR = (ROOT / "GETIR.ps1").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_getir_downloads_the_main_zip_when_git_is_missing():
    assert "archive/refs/heads/main.zip" in GETIR
    assert "Expand-Archive" in GETIR
    assert "MicoFx-main" in GETIR


def test_readme_leads_with_the_one_liner_not_a_private_repo_claim():
    assert "irm https://raw.githubusercontent.com/prlayanyildiz/MicoFx/main/GETIR.ps1" in README
    assert "Repo **ozel**" not in README
    assert "ZIP" in README
