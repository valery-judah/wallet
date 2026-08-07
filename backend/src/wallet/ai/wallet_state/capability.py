from __future__ import annotations

import logging
from typing import Never, Protocol

from wallet.ai.capabilities.contract import (
    CapabilityContext,
    CapabilityDefinition,
    CapabilityInput,
    CapabilityResult,
    CapabilityRoutingProfile,
    CapabilityView,
    CompletedCapabilityResult,
)
from wallet.application.accounts import AccountSnapshot
from wallet.observability import log_event

logger = logging.getLogger(__name__)


class AccountSnapshotReader(Protocol):
    def list_accounts(self) -> list[AccountSnapshot]: ...


class CurrentWalletStateCapability:
    """Return one deterministic, read-only snapshot of active account balances."""

    definition = CapabilityDefinition(
        id="wallet.current_state",
        description="Show current active accounts and balances by currency.",
        routing=CapabilityRoutingProfile(
            routes_when=(
                "The user wants to see current account balances.",
                "The user wants a current overview or summary of the Wallet.",
            ),
            examples=(
                "Show my balance.",
                "What are my current account balances?",
                "Give me a Wallet overview.",
            ),
            counterexamples=(
                "Set Cash balance to 250.",
                "Increase my Savings balance by 50.",
                "I spent 20 from Cash.",
                "A bare account or category name given as an answer to an active task.",
                "A bare amount or date given as an answer to an active task.",
            ),
        ),
    )

    def __init__(self, *, accounts: AccountSnapshotReader) -> None:
        self._accounts = accounts

    def start(
        self,
        content: str | None,
        context: CapabilityContext,
    ) -> CapabilityResult[Never]:
        snapshot = self._snapshot()
        accounts = snapshot["accounts"]
        totals = snapshot["totals_by_currency"]
        log_event(
            logger,
            logging.INFO,
            "wallet.state.generated",
            data={
                "active_account_count": len(accounts) if isinstance(accounts, list) else 0,
                "currency_count": len(totals) if isinstance(totals, list) else 0,
            },
        )
        return CompletedCapabilityResult(
            view=CapabilityView(kind="wallet_state", data=snapshot),
            outcome_kind="state_shown",
            message=_summary(snapshot),
        )

    def handle(
        self,
        state: Never,
        input: CapabilityInput,
        context: CapabilityContext,
    ) -> CapabilityResult[Never]:
        raise RuntimeError("wallet.current_state never has an active session")

    def _snapshot(self) -> dict[str, object]:
        active = sorted(
            (
                snapshot
                for snapshot in self._accounts.list_accounts()
                if snapshot.account.archived_at is None
            ),
            key=lambda snapshot: (snapshot.account.name.casefold(), snapshot.account.id),
        )
        accounts: list[dict[str, object]] = []
        totals: dict[str, int] = {}
        for snapshot in active:
            account = snapshot.account
            balance = snapshot.current_balance
            accounts.append(
                {
                    "id": account.id,
                    "name": account.name,
                    "type": account.type.value,
                    "currency": balance.currency,
                    "balance_minor": balance.amount_minor,
                }
            )
            totals[balance.currency] = totals.get(balance.currency, 0) + balance.amount_minor
        return {
            "accounts": accounts,
            "totals_by_currency": [
                {"currency": currency, "balance_minor": amount_minor}
                for currency, amount_minor in sorted(totals.items())
            ],
        }


def _summary(snapshot: dict[str, object]) -> str:
    accounts = snapshot["accounts"]
    if not isinstance(accounts, list) or not accounts:
        return "You have no active accounts."
    balances = "; ".join(
        f"{account['name']}: {_format_money(account['balance_minor'], account['currency'])}"
        for account in accounts
        if isinstance(account, dict)
        and isinstance(account.get("name"), str)
        and isinstance(account.get("balance_minor"), int)
        and isinstance(account.get("currency"), str)
    )
    return f"Current balances — {balances}."


def _format_money(amount_minor: object, currency: object) -> str:
    if not isinstance(amount_minor, int) or not isinstance(currency, str):
        raise TypeError("wallet state contains an invalid balance")
    return f"{currency} {amount_minor / 100:,.2f}"
