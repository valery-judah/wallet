Use a **transaction + postings** model. Avoid storing every transaction as one flat row with `account_id`, `category_id`, and `amount`, because that breaks down for transfers, split expenses, refunds, and card payments.

## Core entities

```text
Account
- id
- user_id
- name              // "Cash", "Visa", "Mastercard", "Apple Wallet"
- type              // cash, debit_card, credit_card, bank_account, wallet
- currency_code     // USD, EUR, ARS, etc.
- archived_at
```

```text
Category
- id
- user_id
- name              // "Groceries", "Restaurants", "Transport"
- kind              // expense, income
- parent_id         // optional, for nested categories
- archived_at
```

```text
Transaction
- id
- user_id
- occurred_at
- posted_at
- description
- merchant_name
- notes
- status            // pending, posted, void
- type              // expense, income, transfer, adjustment
```

```text
Posting
- id
- transaction_id
- account_id        // nullable
- category_id       // nullable
- amount_minor      // signed integer: cents, kopeks, etc.
- currency_code
- memo
```

A `Posting` should point to **exactly one** of:

```text
account_id
category_id
```

So either it changes an account balance, or it classifies money into a category.

## Sign convention

Use one consistent rule:

```text
Positive amount = increases that target
Negative amount = decreases that target
```

For account balances:

```text
Cash / bank / debit account: positive balance means money owned.
Credit card account: negative balance means money owed.
```

For categories:

```text
Expense category: positive amount means spending.
Income category: negative amount means income.
```

Each transaction should balance:

```text
sum(postings.amount_minor) = 0
```

## Examples

### Cash spending

You spend $12 cash on food.

```text
Transaction: Lunch

Postings:
- Cash account:      -1200
- Food category:     +1200
```

The cash balance decreases by $12. Food expense increases by $12.

---

### Credit card spending

You spend $50 on groceries using a credit card.

```text
Transaction: Groceries

Postings:
- Visa card account:     -5000
- Groceries category:    +5000
```

The card balance becomes more negative, meaning you owe more. Groceries expense increases.

---

### Paying off a credit card

You pay $200 from your bank account to your credit card.

```text
Transaction: Credit card payment

Postings:
- Bank account:      -20000
- Visa card account: +20000
```

No category is involved. This is a transfer, not spending.

---

### Cash withdrawal

You withdraw $100 from a bank account into cash.

```text
Transaction: ATM withdrawal

Postings:
- Bank account:  -10000
- Cash account:  +10000
```

Again, no category. Your total money did not change; it just moved between accounts.

---

### Split transaction

You spend $100 at a supermarket: $70 groceries, $30 household items.

```text
Transaction: Supermarket

Postings:
- Visa card account:      -10000
- Groceries category:      +7000
- Household category:      +3000
```

This is why a postings model is better than a single `category_id` column on `transactions`.

## Suggested SQL shape

```sql
create table accounts (
  id uuid primary key,
  user_id uuid not null,
  name text not null,
  type text not null check (type in (
    'cash',
    'debit_card',
    'credit_card',
    'bank_account',
    'wallet'
  )),
  currency_code char(3) not null,
  archived_at timestamp null
);
```

```sql
create table categories (
  id uuid primary key,
  user_id uuid not null,
  name text not null,
  kind text not null check (kind in ('expense', 'income')),
  parent_id uuid null references categories(id),
  archived_at timestamp null
);
```

```sql
create table transactions (
  id uuid primary key,
  user_id uuid not null,
  occurred_at timestamp not null,
  posted_at timestamp null,
  description text null,
  merchant_name text null,
  notes text null,
  status text not null check (status in ('pending', 'posted', 'void')),
  type text not null check (type in (
    'expense',
    'income',
    'transfer',
    'adjustment'
  )),
  created_at timestamp not null default now(),
  updated_at timestamp not null default now()
);
```

```sql
create table postings (
  id uuid primary key,
  transaction_id uuid not null references transactions(id) on delete cascade,

  account_id uuid null references accounts(id),
  category_id uuid null references categories(id),

  amount_minor bigint not null,
  currency_code char(3) not null,
  memo text null,

  check (
    (account_id is not null and category_id is null)
    or
    (account_id is null and category_id is not null)
  )
);
```

## Derived values

Do not store account balances as the primary source of truth. Compute them from postings:

```sql
select
  account_id,
  sum(amount_minor) as balance_minor
from postings
where account_id is not null
group by account_id;
```

For category spending:

```sql
select
  category_id,
  sum(amount_minor) as spent_minor
from postings
where category_id is not null
group by category_id;
```

For monthly spending:

```sql
select
  p.category_id,
  sum(p.amount_minor) as spent_minor
from postings p
join transactions t on t.id = p.transaction_id
where p.category_id is not null
  and t.occurred_at >= date_trunc('month', now())
  and t.status = 'posted'
group by p.category_id;
```

## Important invariants

At the domain layer, enforce:

```text
1. Every transaction has at least 2 postings.
2. Sum of postings for one transaction must be 0.
3. All postings in a normal transaction use the same currency.
4. Transfers should have only account postings.
5. Expenses usually have one account posting and one or more expense category postings.
6. Income usually has one account posting and one income category posting.
```

For multi-currency support, treat currency exchange as a special case with exchange metadata or separate balancing rules. Do not casually mix currencies in the same zero-sum transaction unless you explicitly model FX conversion.