# Wallet Concepts

Status: canonical financial product vocabulary

## Purpose and Authority

This document defines the preferred terms and stable financial distinctions used in Wallet
product work. Use it to keep product framing, specifications, designs, evaluations, product copy,
and domain naming aligned.

The related documents have different responsibilities:

- [Wallet Product Frame](wallet-frame.md) defines the underlying user situation, jobs, needs,
  outcomes, and product principles.
- [Wallet AI Concepts](ai-concepts.md) defines assistant-facing and AI control-layer vocabulary.
- [Wallet MVP Spec](spec.md) defines the behavior and constraints supported by the current product
  slice.
- The contracts in `docs/evergreen/` define implementation mechanics.

Concepts in this document describe what something means. They do not imply that every possible
operation on that concept is supported in the current MVP.

## Wallet and Financial Concepts

### Wallet

**Wallet** is the personal money record maintained in the product. It brings together the user's
recorded accounts, balances, transactions, and classifications.

Wallet represents what has been recorded in the product. It is not automatically a complete view
of the user's finances or a substitute for an account provider's records.

Use **Wallet** for the product and the complete record. Use **digital wallet** for an account type
such as Mercado Pago, PayPal, or Wise.

### Account

An **account** is any place the user keeps money or spends money from.

Examples include:

- a debit or prepaid card;
- a credit card;
- physical cash;
- a bank account;
- a digital wallet; and
- a payout or stored-value balance.

Account is the top-level concept. A card, cash holding, bank account, or digital wallet is a kind
of account, not a separate top-level entity.

#### Manual account

A **manual account** is maintained by the user without bank synchronization. Manual does not mean
incomplete or temporary; it is a complete way to use Wallet.

#### Account type

An **account type** describes what kind of place an account represents. The current product
vocabulary is:

| Preferred term | Current identifier | Meaning |
| --- | --- | --- |
| Debit card | `debit_card` | A debit or prepaid card balance |
| Credit card | `credit_card` | A credit-card account and its liability |
| Cash | `cash` | Physical money held in one currency |
| Bank account | `bank_account` | A checking, current, or similar bank balance |
| Digital wallet | `wallet` | A digital wallet, payout balance, or stored-value service |

The [MVP specification](spec.md#mvp-account-types) is authoritative for which types the current
product supports.

### Account lifecycle

An **active account** is an account currently in use and available for new transactions.

An **archived account** is no longer available for new transactions but remains in Wallet so its
identity, balances, and transaction history continue to make sense. Archiving is not deletion.

The specification defines the currently supported lifecycle operations and where archived
accounts appear.

### Balance

A **balance** is the amount currently recorded for one account in that account's currency. It is
derived from the account's posted transaction history rather than maintained as an unrelated
number.

One account has one currency. Amounts in different currencies remain separate unless Wallet has an
explicit exchange model. A combined number without such a model is not a Wallet balance.

### Transaction

A **transaction** is a recorded event that explains why money entered, left, moved within, or was
corrected in Wallet. Transaction is the umbrella term; its type preserves the event's meaning.

The current transaction vocabulary is:

| Preferred term | Current identifier | Meaning |
| --- | --- | --- |
| Expense | `expense` | Spending that leaves the user's finances and counts as spending |
| Income | `income` | Money entering the user's finances from an outside source |
| Transfer | `transfer` | Money moving between two accounts owned by the user |
| Balance adjustment | `adjustment` | An explicit correction that brings a recorded account balance in line with reality |

An expense is not a transfer merely because money leaves one account. A transfer does not count as
spending or income because the money remains within the user's own accounts.

A balance adjustment records the fact that a correction occurred. It does not silently rewrite an
opening balance or an earlier transaction, and it should not be described as a known expense or
income when the cause is unknown.

The [MVP specification](spec.md#transaction-model) defines the transaction shapes and validations
currently supported.

### Classification

A **spending category** classifies an expense. Spending categories form their own category family.

Examples:

- `Food > Groceries`
- `Transport > Fuel`
- `Health > Pharmacy`

An **income category** classifies income. Income categories form a separate category family because
income and spending answer different questions.

Examples:

- `Salary > Payroll`
- `Investments > Dividends`
- `Business > Contracts`

**Uncategorized** is the user-facing label for an expense or income record without a selected
category. It is a presentation state, not a real category entity.

The specification defines the supported category depth and maintenance operations.

## Naming and Distinction Rules

Use these distinctions consistently in product copy, design, evaluation, and product-facing
documentation.

| Use | Avoid | Reason |
| --- | --- | --- |
| Account as the top-level place where money is kept or spent from | Treating cards or digital wallets as separate top-level entities | They are account types |
| Wallet for the product record; digital wallet for an account type | Calling a digital-wallet account “Wallet” without context | The terms refer to different levels |
| Expense for spending | Withdrawal as a synonym for every outgoing amount | An outgoing amount may instead be a transfer or adjustment |
| Transfer for movement between the user's own accounts | Counting a transfer as expense or income | Ownership of the money has not changed |
| Balance adjustment for an explicit correction | Describing a correction as silently setting or rewriting history | The correction remains a recorded event |
| Spending category and income category | One undifferentiated category family | Spending and income answer different questions |

## Internal Ledger Vocabulary

**Posting** is the internal term for one balanced ledger leg targeting an account or category. It
is useful in API and engineering work but is not preferred user-facing language. The
[MVP specification](spec.md#transaction-model) defines current posting rules.

## Reserved Product Language

These terms are recognized for future product work but are not promises of current support:

| Reserved term | Intended meaning |
| --- | --- |
| Connected account | An account whose records are synchronized from a financial provider |
| Pending transaction | A transaction represented before it becomes posted financial history |
| Void transaction | A transaction explicitly invalidated through a supported lifecycle operation |

The specification is authoritative about whether any reserved concept has entered the supported
product scope. Do not present a reserved term as available behavior until that change is specified.
