# Wallet MVP Spec

## Product Scope

Wallet tracks the places where a user keeps or spends money from.

For the current MVP, the product is centered on **manual accounts backed by a transaction ledger**:

- Users can create and view accounts.
- Users can assign an account type, currency, and opening balance.
- Users can update account profile metadata such as display color and icon.
- Users can archive an account without deleting its history.
- Users can record transactions directly against an account.
- Users can manage separate spending and income category trees.

The current account balance remains visible in account read responses, but it is
derived from ledger postings rather than stored as the source of truth.

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
| `debit_card` | Debit card | Debit card and prepaid card balances |
| `credit_card` | Credit card | Credit card balances and liabilities |
| `cash` | Cash | Cash wallet, USD cash, ARS cash |
| `bank_account` | Bank account | Checking and current accounts |
| `wallet` | Digital wallet | Mercado Pago, PayPal, Wise, payout balances |

## Account Lifecycle

An account currently supports these lifecycle actions:

- Open account
- Update account profile
- Record transactions against the account ledger
- Archive account

Archived accounts remain visible for history, but they do not accept new
transactions.

## Balance Model

For MVP, account balances are ledger-derived.

Rules:

- One account has one currency.
- Balances are expressed in minor units plus currency code.
- Multi-currency ownership is modeled as multiple accounts.
- User-visible account balances are derived by summing account postings.
- Hidden system-equity accounts may exist internally to balance adjustment-style
  transactions and must never appear in user-facing account lists.

## Transaction Model

The MVP transaction ledger supports four transaction types:

- `expense`
- `income`
- `transfer`
- `adjustment`

Rules:

- Transactions are created directly as `posted`.
- Every transaction must balance to zero across its postings.
- Every posting targets exactly one account or one category.
- Expense transactions use exactly one account posting and one or more
  spending-category postings.
- Income transactions use exactly one account posting and one income-category
  posting.
- Transfer transactions use exactly two account postings and no categories.
- Adjustment transactions are account-only and persist as one user-account
  posting plus one hidden system-equity posting.

## Category Trees

The MVP includes two manual category trees for transaction classification:

- `SpendingCategory` for expense classification
- `IncomeCategory` for income classification

Rules:

- Spending and income categories are separate in-memory trees for the running
  app instance.
- Each tree supports only two levels: parent category and child category.
- Categories can be created and updated, but not deleted or archived yet.
- Uncategorized spending or income remains a future transaction-level `NULL`
  concept, not a real category row.

## Manual-First Scope

All accounts are manual by default in MVP.

Reserved future concepts:

- Connected account
- Bank sync
- Import pipelines
- Pending and void transaction workflows

## Conversational Transaction Capture

The MVP exposes a synchronous HTTP workflow for progressively capturing one
transaction from natural-language contributions. Capture sessions and wallet
data are process-local: they survive requests handled by the same backend
process but not restarts or multiple workers.

The public resource is `/api/v1/transaction-captures`:

- create a capture with an initial contribution;
- read the current capture state;
- add follow-up contributions or corrections;
- explicitly confirm a complete candidate;
- cancel an active capture.

Capture supports expenses, income, transfers, and balance adjustments. It
defaults the transaction date to today, asks deterministic questions for missing
or unusable fields, and returns structured disambiguation options when a wallet
label is ambiguous.

A complete and valid candidate enters `awaiting_confirmation`. No ledger
transaction or posting is created in that state. The confirm action revalidates
wallet references and creates exactly one posted transaction. Repeated
confirmation of an already completed capture returns the same transaction.
Cancellation is terminal and never creates a transaction.

Confirmation and cancellation are explicit HTTP actions. Natural-language
answers such as `yes` or `cancel` do not perform terminal actions. Direct manual
transaction creation through `/api/v1/transactions` remains immediate.

## Out of Scope

The MVP does not yet include:

- Rich credit-card workflows such as statement cycles and limits
- Investment valuation
- Account merging
- Shared-account permissions
- Bank connections or sync
- Multi-currency FX transactions
- Budget rules based on transaction classification
- Durable or multi-worker capture sessions
- Asynchronous or streaming capture responses
- Conversational capture UI and external messaging-channel adapters
