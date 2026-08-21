"""Expected MT5 login+server vs the terminal that is actually attached.

The client talks to whichever account the terminal has open. Demo-tuned
books must not keep sending entries after an accidental live login.
"""
from __future__ import annotations

from dataclasses import dataclass

# MetaTrader5.ACCOUNT_TRADE_MODE_REAL. Kept numeric so tests never import mt5.
ACCOUNT_TRADE_MODE_REAL = 2


@dataclass(frozen=True)
class AccountLockDecision:
    allow_entry: bool
    reason: str = ""
    bind_login: int | None = None
    bind_server: str | None = None


def decide_account_lock(
    expected_login: int,
    expected_server: str,
    login: int,
    server: str,
    trade_mode: int = 0,
) -> AccountLockDecision:
    found_login = int(login or 0)
    found_server = str(server or "").strip()
    if found_login <= 0:
        return AccountLockDecision(
            allow_entry=False,
            reason="hesap kilidi: bagli hesap numarasi yok",
        )
    exp_login = int(expected_login or 0)
    exp_server = str(expected_server or "").strip()
    if exp_login == 0 and not exp_server:
        if is_real_money_account(trade_mode):
            return AccountLockDecision(
                allow_entry=False,
                reason=(
                    "hesap kilidi: gercek para hesabi otomatik baglanmaz, "
                    "operator onayi gerekli"
                ),
            )
        return AccountLockDecision(
            allow_entry=True,
            bind_login=found_login,
            bind_server=found_server,
        )
    if exp_login == found_login and exp_server == found_server:
        # No real-money veto on this branch, and that is deliberate: an
        # already-bound pair IS the operator's approval. The refusal above
        # only stops a real account being adopted *automatically* on first
        # sight, and setting the lock by hand is the one way to say yes to
        # live money. Adding a trade_mode check here would read like a
        # tightening and would in fact remove the only route to going live.
        return AccountLockDecision(allow_entry=True)
    return AccountLockDecision(
        allow_entry=False,
        reason=(
            f"hesap kilidi: beklenen {exp_login} @ {exp_server}, "
            f"bulunan {found_login} @ {found_server}"
        ),
    )


def is_real_money_account(trade_mode: int) -> bool:
    return int(trade_mode or 0) == ACCOUNT_TRADE_MODE_REAL
