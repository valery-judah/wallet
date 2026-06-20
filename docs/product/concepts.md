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

## UX Concepts

### Display Metadata

Accounts may include optional display metadata:

- `color_key`
- `icon_key`

These are presentation tokens, not financial business logic.

### Manual-First UX

The current UX model assumes manual accounts first:

- The user names the account.
- The user chooses the account type.
- The user sets the currency.
- The user starts from the current balance they want tracked.

### Future Transaction Model

Direct deposits and withdrawals exist in MVP as a bridge.

The target direction is:

- Expenses record outgoing spending
- Incomes record incoming money
- Transfers move money between accounts
- Balances evolve from recorded movements instead of ad hoc mutations
