# Wallet Concepts

## Core Vocabulary

Use these terms consistently in product copy, docs, and domain naming.

| Concept | Preferred term | Meaning |
| --- | --- | --- |
| Place where money lives | `Account` | Any place the user keeps or spends money from |
| Manual source | `Manual account` | User-managed account without bank sync |
| Synced source | `Connected account` | Reserved for future bank-connected flows |
| General money movement | `Transaction` | Umbrella term for a recorded movement |
| Outgoing user spending | `Expense` | Spending that should count as spending |
| Incoming money | `Income` | Money entering the user’s finances |
| Own-account movement | `Transfer` | Money moved between two user-owned accounts |
| Explicit correction | `Balance adjustment` | Manual correction to a stored balance |
| Expense classification bucket | `Spending category` | A two-level category used to classify spending |
| Missing expense category | `Uncategorized` | UI label for spending with no category assigned |

## Domain Concepts

### Account

The primary product entity is `Account`.

Definition:

> An account is any place you keep or spend money from.

Examples:

- Main card
- Cash wallet
- Bank account
- Savings fund
- Mercado Pago balance
- Payoneer balance

### Account Type

Account type is a category on the account itself, not a separate relation.

For example:

- A card is `Account(type="card")`
- A cash wallet is `Account(type="cash")`
- A bank balance is `Account(type="bank")`

The MVP account type set is:

- `card`
- `cash`
- `bank`
- `wallet`
- `platform`
- `savings`
- `other`

### Balance

The current product model stores one current balance on each account.

Rules:

- Balance is expressed as money in minor units plus currency code.
- One account has one currency.
- Multi-currency ownership is modeled as multiple accounts.
- Negative balances are not allowed in the current MVP model.

### Status

Accounts have lifecycle status:

- `active`
- `closed`

Closed accounts stay visible but no longer accept deposits or withdrawals.

### Spending Category

A spending category classifies expense-like activity.

The current product slice supports:

- A maximum depth of two levels
- Top-level categories and child categories
- Create and update only for now

Examples:

- `Food > Groceries`
- `Transport > Fuel`
- `Health > Pharmacy`

`Uncategorized` is presentation language only. It should not be modeled as a
real category entity.
