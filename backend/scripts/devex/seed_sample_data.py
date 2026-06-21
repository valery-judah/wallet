from __future__ import annotations

from wallet.api.deps import build_container, get_account_service
from wallet.config import Settings


def main() -> None:
    container = build_container(
        Settings(
            environment="local",
            seed_sample_data=True,
        )
    )
    account_service = get_account_service(container.accounts, container.transactions)
    accounts = account_service.list_accounts()
    transactions = container.transactions.list()

    print("Seeded local sample data")
    print(f"Accounts: {len(accounts)}")
    for snapshot in accounts:
        account = snapshot.account
        print(
            f"- {account.id}: {account.name} ({account.type}) "
            f"{snapshot.current_balance.amount_minor} {snapshot.current_balance.currency}"
            + (" [archived]" if account.archived_at is not None else "")
        )
    print(f"Transactions: {len(transactions)}")
    print("Transaction types: " + ", ".join(transaction.type for transaction in transactions))


if __name__ == "__main__":
    main()
