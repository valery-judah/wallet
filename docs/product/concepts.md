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
| Explicit correction | `Balance adjustment` | Manual correction recorded as a ledger transaction |
| Expense classification bucket | `Spending category` | A two-level category used to classify expenses |
| Income classification bucket | `Income category` | A two-level category used to classify income |
| Missing expense category | `Uncategorized` | UI label for spending with no category assigned |
| Conversational context | `Conversation` | Server-created continuity holder returned after the first accepted turn |
| Current unit of work | `Active task` | One opaque running task inside a conversation; absent while the conversation is idle |
| Internal task implementation | `Capability` | Statically registered handler selected while idle and given every non-control message while active |
| Semantic ownership decision | `Route decision` | Closed model result proposing which registered capability should start for one idle message |
| Bounded conversational routing hint | `Routing memory` | Identity of the most recently executed capability; supports explicit references without storing transcript text or domain state |
| One caller interaction | `Turn` | Globally identified input submitted for a new or existing conversation |
| Natural-language draft change | `Transaction interpretation` | Structured model proposal that updates a reviewable capture candidate without executing it |
| Reviewable transaction state | `Transaction draft` | Capture candidate assembled from interpreted contributions and validated before confirmation |
| Current financial snapshot | `Wallet state` | Read-only active-account balances with totals kept separate by currency |

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

- A debit card is `Account(type="debit_card")`
- A credit card is `Account(type="credit_card")`
- A cash wallet is `Account(type="cash")`
- A bank balance is `Account(type="bank_account")`

The MVP account type set is:

- `debit_card`
- `credit_card`
- `cash`
- `bank_account`
- `wallet`

### Balance

The current product model derives the visible balance from account postings.

Rules:

- Balance is expressed as money in minor units plus currency code.
- One account has one currency.
- Multi-currency ownership is modeled as multiple accounts.
- User-facing balances come from summing posted account postings.
- Hidden system-equity accounts may exist internally and are excluded from
  user-facing account views.

### Lifecycle

Accounts have lifecycle status:

- `active`
- `archived`

Archived accounts stay visible but no longer accept new transactions.

### Transaction

A transaction is the top-level record of one money movement.

The current MVP supports:

- `expense`
- `income`
- `transfer`
- `adjustment`

Rules:

- Transactions are created as `posted` only in this phase.
- `pending` and `void` exist as reserved status values, but there are no
  lifecycle operations for them yet.
- Expense transactions may split one negative account posting across one or
  more positive spending-category postings.

### Posting

A posting is one balanced leg of a transaction.

Rules:

- A posting targets exactly one account or one category.
- Transaction postings must sum to zero.
- All postings in one normal transaction use the same currency.
- Transfers use account postings only.
- Expenses use one negative account posting and one or more positive
  spending-category postings.
- Income uses one positive account posting and one negative income-category
  posting.
- Adjustments persist as one user-account posting plus one hidden
  system-equity posting.

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

### Income Category

An income category classifies real income activity.

The current product slice supports:

- A maximum depth of two levels
- Top-level categories and child categories
- Create and update only for now

Examples:

- `Salary > Payroll`
- `Investments > Dividends`
- `Business > Contracts`

`IncomeCategory` is separate from `SpendingCategory`. Income is not modeled as a
kind on the spending-category entity.
