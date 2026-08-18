"""A checker that is configured but not installed is not a checker.

pyproject.toml has configured ruff and mypy since 15.08, with per-file ignores
written out and reasons given for each. Neither was in requirements.txt, so a
fresh venv had no ruff, ``python -m ruff`` failed, and the checks were skipped
by whoever hit that first - which lands in exactly the same place as never
having configured them. This pins the two files together.

The installer half is the same argument one level up: KUR.ps1 can report five
green steps on a machine that cannot actually run the app, so it now proves
itself with the suite before saying it is done.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _requirements() -> str:
    return (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()


def _installer() -> str:
    return (ROOT / "KUR.ps1").read_text(encoding="utf-8")


def test_every_configured_static_checker_is_installed():
    """Whatever pyproject configures, requirements.txt must bring."""
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    reqs = _requirements()
    for tool in cfg.get("tool", {}):
        if tool in {"ruff", "mypy"}:
            assert tool in reqs, (
                f"pyproject configures {tool} but requirements.txt never installs it - "
                f"a fresh venv cannot run it"
            )


def test_the_installer_runs_the_suite_before_claiming_success():
    src = _installer()
    assert "pytest" in src, "KUR.ps1 finishes without ever running the tests"
    assert "TESTLER GECMEDI" in src, "a failing suite must be reported, not swallowed"


def test_the_installer_runs_the_static_checkers_it_configures():
    """pyproject.toml named ruff and mypy; a green install must actually invoke them."""
    src = _installer()
    assert "-m ruff" in src, "KUR.ps1 never runs ruff"
    assert "-m mypy" in src, "KUR.ps1 never runs mypy"


def test_the_installer_sets_a_git_identity():
    """Without user.name/user.email git refuses to commit, and it fails later."""
    src = _installer()
    assert "user.name" in src and "user.email" in src


def test_the_installer_does_not_write_a_credential_to_disk():
    """Auth belongs in the credential manager, never in a file we generate."""
    src = _installer().lower()
    for leak in ("ghp_", "github_pat_", "personal access token'i yaz", "password"):
        assert leak not in src, f"KUR.ps1 looks like it handles a secret: {leak}"


def test_the_step_counter_matches_the_steps():
    """A '[3/5]' printed by the sixth step is how a step gets quietly dropped."""
    src = _installer()
    declared = src.count("\nStep ")
    assert f"/{declared}]" in src, (
        f"{declared} Step calls but the counter does not say /{declared}"
    )


def test_pytest_keeps_its_temp_tree_out_of_the_shared_one():
    """The suite must not depend on Windows symlink policy to exit zero.

    pytest's default layout writes a "pytest-current" symlink beside its
    numbered run directories and resolves it during teardown. The laptop
    refuses with WinError 5 and Windows Server with WinError 1463 (symlink
    following disabled by policy). Every test passes and pytest then raises on
    the way out, exiting non-zero - indistinguishable from a failing suite to
    KUR.ps1's install check, which reported exactly that on a healthy machine.
    """
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    addopts = cfg.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("addopts", "")
    assert "--basetemp" in addopts, (
        "without an explicit basetemp the suite exits non-zero on machines that "
        "disable symlink evaluation, even when every test passes"
    )
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".pytest_tmp" in ignored, "pytest clears basetemp at startup; keep it untracked"


def test_symlink_cleanup_survives_a_refused_resolve():
    """conftest must neutralise the teardown walk on both module references.

    _pytest.tmpdir binds cleanup_dead_symlinks by name at import time, so
    patching _pytest.pathlib alone leaves the session-finish call pointing at
    the original - which is the version that raised WinError 1463 on the
    server after every test had already passed.
    """
    from _pytest import pathlib as _pl
    from _pytest import tmpdir as _tmp

    class RefusesToResolve:
        def iterdir(self):
            raise OSError(1463, "symlink evaluation is disabled by policy")

    _pl.cleanup_dead_symlinks(RefusesToResolve())
    _tmp.cleanup_dead_symlinks(RefusesToResolve())
