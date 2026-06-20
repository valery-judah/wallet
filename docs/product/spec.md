# Wallet MVP Spec

## Product Scope

Wallet tracks the places where a user keeps or spends money from.

For the current MVP, the product is centered on **manual accounts**:

- Users can create and view accounts.
- Users can assign an account type and currency.
- Users can start an account from a current balance.
- Users can update account profile metadata such as display color and icon.
- Users can close an account without deleting its history.
- Users can move the balance directly through deposit and withdrawal actions.
- Users can manage spending categories for future expense classification.

This MVP intentionally keeps a **single current balance** on each account. It does
not yet require a full transaction ledger to derive balances.

## Primary Concept

The top-level product concept is **Account**.

Definition:

> An account is any place you keep or spend money from.

Examples:

- Main card
- Cash wallet
- USD cash
- ARS cash
- Bank account
- Mercado Pago
- PayPal
- Wise
- Payoneer
- Savings fund

Cards are not a separate top-level concept. A card is one account type.

## MVP Account Types

The approved account taxonomy for MVP is:

| Type | User-facing label | Examples |
| --- | --- | --- |
| `card` | Card | Debit card, credit card, prepaid card |
| `cash` | Cash | Cash wallet, USD cash, ARS cash |
| `bank` | Bank account | Checking and current accounts |
| `wallet` | Digital wallet | Mercado Pago, PayPal, Wise |
| `platform` | Money platform | Payoneer and payout balances |
| `savings` | Savings | Reserve and emergency funds |
| `other` | Other | Anything outside the standard set |

## Account Lifecycle

An account currently supports these lifecycle actions:

- Open account
- Update account profile
- Deposit into account
- Withdraw from account
- Close account

Closed accounts remain visible for history and reporting, but they do not accept
new balance movements.

## Balance Model

For MVP, the current balance is stored directly on the account.

Rules:

- One account has one currency.
- Balances are stored in minor units plus currency code.
- Multi-currency ownership is modeled as multiple accounts.
- Account balances must stay non-negative in the current MVP.

Direct balance mutations are a temporary operating model. Future expenses,
incomes, and transfers should become the normal way balances evolve once the
transaction layer is introduced.

## Spending Categories

The MVP also includes a manual spending-category tree for organizing future
expense classification work.

Rules:

- Spending categories are currently managed as a single in-memory tree for the
  running app instance.
- The hierarchy supports only two levels: parent category and child category.
- Categories can be created and updated, but not deleted or archived yet.
- Uncategorized spending remains a future transaction-level `NULL` concept, not
  a real category row.

This is intentionally setup-only scope for now. The MVP still does not include
transactions, transaction splits, or category-based reporting behavior.

## Manual-First Scope

All accounts are manual by default in MVP.

Reserved future concepts:

- Connected account
- Bank sync
- Import pipelines
- Transaction-derived balances

## Out of Scope

The MVP does not yet include:

- Credit debt semantics such as statement cycles, limits, and liabilities
- Investment valuation
- Account merging
- Shared-account permissions
- Bank connections or sync
- Transfer flows between accounts
- Budget rules based on transaction classification
