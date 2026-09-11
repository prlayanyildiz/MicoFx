"""Four watchers, four legs, and nothing stopped a fifth arming the same one.

11.09 08:26: three `powershell -c "..."` watchers were alive at once, all
polling `claude/FOR_CURSOR.md` and all emitting
`AGENT_LOOP_WAKE_claude_bridge`. Killing them did nothing - the parent was
`claude.exe`, so the next session armed another within seconds. The design was
deliberate (Cursor asked for a per-session watcher because the daemon's stdout
does not reach its notify path, cursor/FOR_CLAUDE.md:112); what was missing was
the single-instance latch the other legs already had.

The inline version also wrote its state file with positional `Set-Content`
arguments. In one revision they were the wrong way round, which makes the
64-character hash the FILE NAME and the state path its contents: five of those
landed at the repo root on 10.09, one reached a commit, and another appeared
11.09 - so it was swept, never fixed. That is why every write here has to name
its parameters.

Each leg gets exactly one script, one distinct mutex, released in a finally.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The watcher scripts and the leg each one owns. A new watcher belongs in this
# table with its own mutex - not as an inline -c command nobody can review.
WATCHERS = {
    "scripts/start_bridge_daemon.ps1": "Global\\MicoFX.BridgeDaemon",
    "cursor/watch_bridges.ps1": "Global\\MicoFX.CursorBridgeWatch",
    "antigravity/WATCH.ps1": "Global\\MicoFX.AntigravityWatch",
    "claude/session_watch.ps1": "Global\\MicoFX.ClaudeSessionWatch",
}


def _src(rel: str) -> str:
    path = ROOT / rel
    assert path.exists(), f"{rel} yok - adi mi degisti?"
    return path.read_text("utf-8", errors="replace")


@pytest.mark.parametrize("rel,mutex", sorted(WATCHERS.items()))
def test_each_watcher_takes_its_own_named_mutex(rel: str, mutex: str):
    src = _src(rel)
    assert mutex in src, f"{rel}: {mutex} yok"
    assert "WaitOne(0)" in src, f"{rel}: mutex alinmadan devam ediyor"
    assert "exit" in src.lower(), f"{rel}: ikinci ornek cikmiyor"


@pytest.mark.parametrize("rel", sorted(WATCHERS))
def test_each_watcher_releases_what_it_took(rel: str):
    src = _src(rel)
    assert "finally" in src, f"{rel}: mutex finally'de birakilmiyor"
    assert "ReleaseMutex" in src, f"{rel}: ReleaseMutex yok"


def test_no_two_legs_share_a_mutex():
    names = list(WATCHERS.values())
    assert len(set(names)) == len(names), f"ayni mutex iki bacakta: {names}"


@pytest.mark.parametrize("rel", sorted(WATCHERS))
def test_state_writes_name_their_parameters(rel: str):
    """A positional Set-Content is how a hash becomes a filename."""
    offenders: list[str] = []
    for n, line in enumerate(_src(rel).splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#") or "Set-Content" not in stripped:
            continue
        if "-LiteralPath" in stripped or "-Path" in stripped:
            continue
        offenders.append(f"{rel}:{n}: {stripped[:70]}")
    assert offenders == [], (
        "Set-Content konumsal yaziyor - hash dosya adi olur:\n"
        + "\n".join(offenders))


def test_the_claude_leg_watches_the_inbox_not_its_own_outbox():
    """cursor/watch_bridges.ps1 carries this warning for the Gemini leg and it
    cost a real mistake on 10.09: FOR_GEMINI.md exists in two folders, one an
    inbox and one an outbox. The Claude leg has the same shape."""
    src = _src("claude/session_watch.ps1")
    assert "claude\\FOR_CURSOR.md" in src, "yanlis dosya izleniyor"
    assert "cursor\\FOR_CLAUDE.md" not in re.sub(
        r"(?m)^\s*#.*$", "", src), "kendi gelen kutusunu izliyor"


def test_no_hash_named_debris_is_lying_around():
    """The symptom of the swapped write. It came back once already."""
    found = [p.name for p in ROOT.iterdir()
             if p.is_file() and re.fullmatch(r"[0-9A-F]{64}", p.name)]
    assert found == [], f"hash adli artik: {found}"


def test_every_watcher_is_actually_in_the_repo():
    """The premise of this whole file, and it was false when it was written.

    All three peer-folder watchers lived in wholesale-ignored directories
    (`claude/`, `cursor/`, `antigravity/`), so the assertions above passed here
    and would have failed on any fresh clone. Worse, the two that predate this
    file had never been reviewable at all - which is how one of them ran for
    days writing a 64-character filename instead of a state file.

    The mailbox messages stay ignored; the code that runs does not. Note the
    ignore patterns had to become `dir/*` rather than `dir/`, because git
    cannot re-include a file whose parent DIRECTORY is excluded - a `!` line
    under `claude/` silently does nothing.
    """
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "--", *WATCHERS],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    assert tracked.returncode == 0, tracked.stderr
    seen = {line.replace("\\", "/") for line in tracked.stdout.split()}
    missing = sorted(set(WATCHERS) - seen)
    assert missing == [], (
        "gitignore'da kalan watcher (temiz klonda bu dosya kirilir): "
        f"{missing}")
