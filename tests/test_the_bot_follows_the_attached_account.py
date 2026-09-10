"""The account lock is gone: the bot trades whatever the terminal has open.

Operator decision 10.09 - "hesap kilit olayini da kaldir, hedefteki mt5 hesap
neyse o olsun". What used to sit in ``Engine._enforce_account_lock`` bound an
expected login+server on first sight and blocked every new entry while the
terminal was on anything else; ``/api/account-lock`` was the only way to
retarget it, and a real-money account was refused automatically on first
sight.

All of that is removed. These tests pin what replaced it, because "we deleted
it" is not a behaviour anyone can check:

  * an account change never blocks an entry, on any account type;
  * it is still written down once per change, loudly for real money - a bot
    that follows the terminal silently would make a fill the first evidence
    that the account moved;
  * the two settings keys are gone from SystemConfig, and an old DB row that
    still carries them loads anyway.
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from micofx.engine import Engine
from micofx.models import SystemConfig


def _engine(monkeypatch, emitted):
    monkeypatch.setattr("micofx.engine.LOG.emit",
                        lambda msg, level="INFO", *a, **k: emitted.append((level, msg)))
    eng = Engine.__new__(Engine)
    eng.entry_lock = threading.Lock()
    eng._attached_account = None
    return eng


DEMO = {"login": 61592524, "server": "Pepperstone-Demo", "trade_mode": 0}
OTHER = {"login": 99999999, "server": "Baska-Broker", "trade_mode": 0}
REAL = {"login": 51501624, "server": "PepperstoneBS-MT5-Live01", "trade_mode": 2}


# ------------------------------------------------------- the lock itself

def test_the_module_is_gone():
    """A leftover import would keep the old refusal reachable."""
    import importlib

    for name in ("micofx.account_lock", "account_lock"):
        try:
            importlib.import_module(name)
        except ImportError:
            continue
        raise AssertionError(f"{name} hala import edilebiliyor")


def test_the_engine_has_no_enforcement_left():
    assert not hasattr(Engine, "_enforce_account_lock")


def test_the_settings_keys_are_gone_but_an_old_row_still_loads():
    """The two keys sit in the live settings blob. _coerce drops unknown keys,
    so removing the fields must not make an existing row unreadable."""
    assert "account_lock_login" not in SystemConfig.__dataclass_fields__
    assert "account_lock_server" not in SystemConfig.__dataclass_fields__
    cfg = SystemConfig.from_dict({
        "account_lock_login": 61562752,
        "account_lock_server": "Pepperstone-Demo",
        "poll_interval_sec": 3.0,
    })
    assert cfg.poll_interval_sec == 3.0


# ------------------------------------------------------ what replaced it

def test_a_changed_account_is_logged_once(monkeypatch):
    emitted: list[tuple[str, str]] = []
    eng = _engine(monkeypatch, emitted)

    eng._note_attached_account(DEMO)
    eng._note_attached_account(DEMO)          # same pair, no second line
    assert len(emitted) == 1
    assert "61592524" in emitted[0][1]
    assert emitted[0][0] == "WARN"

    eng._note_attached_account(OTHER)         # moved: say so again
    assert len(emitted) == 2
    assert "99999999" in emitted[1][1]


def test_a_real_money_account_is_loud(monkeypatch):
    """Nothing refuses it any more, so the line is the only warning there is."""
    emitted: list[tuple[str, str]] = []
    _engine(monkeypatch, emitted)._note_attached_account(REAL)
    assert emitted[0][0] == "ERROR"
    assert "GERCEK PARA" in emitted[0][1]
    assert "51501624" in emitted[0][1]


def test_an_unreadable_account_says_nothing(monkeypatch):
    emitted: list[tuple[str, str]] = []
    eng = _engine(monkeypatch, emitted)
    eng._note_attached_account({})
    eng._note_attached_account({"login": 0, "server": ""})
    assert emitted == []


def test_the_note_never_blocks_an_entry(monkeypatch):
    """The old method returned a reason string that the cycle fed into
    ``allow_entry``. This one returns nothing and gates nothing."""
    emitted: list[tuple[str, str]] = []
    eng = _engine(monkeypatch, emitted)
    assert eng._note_attached_account(REAL) is None
    src = Path(Engine.__module__.replace(".", "/") + ".py")
    text = src.read_text(encoding="utf-8")
    cycle = text.split("allow_entry = (", 1)[1].split("\n\n", 1)[0]
    assert "lock" not in cycle.lower(), cycle
