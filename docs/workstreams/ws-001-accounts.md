# WS-001 Accounts

## Goal

Expand the current cards-only model into a broader accounts model that can represent
the places where a user keeps or spends money from, using the repo's current
simple balance-based backend as the starting point.

This workstream defines the MVP account model, data shape, UX vocabulary, and a
delivery plan. It intentionally does not introduce full credit liability behavior,
bank sync, or a transaction ledger yet.

## Context

Current backend scope:

- `Card` is the only domain aggregate.
- Card balances are stored directly on the aggregate.
- Card behavior assumes asset semantics: same-currency operations only and no
  negative balance.

Product need:

- Users need more than cards.
- We need a model that supports cash, bank accounts, digital wallets, savings,
  and similar money containers.
- We should keep the language and UI broad enough that cards become one account
  type, not the whole product model.

## Product Decisions

### Core concept

Use **Account** as the top-level concept.

Definition:

> An account is any place you keep or spend money from.

Examples:

- Main card
- Cash wallet
- USD cash
- ARS cash
- Mercado Pago
- PayPal
- Wise
- Payoneer
- Savings

### Vocabulary

Use this language in product copy and domain naming:

- `Account`: any place money lives.
- `Manual account`: an account managed by the user without bank sync.
- `Connected account`: reserved for a future synced integration.
- `Transaction`: general money movement record.
- `Expense`: outgoing user spending.
- `Income`: incoming money.
- `Transfer`: movement between two user-owned accounts.
- `Balance adjustment`: explicit correction to an account balance.

For MVP, accounts are manual by default.

### MVP account types

Use practical account types instead of bank-internal taxonomy.

| Type | User-facing label | Examples |
| --- | --- | --- |
| `card` | Card | Debit card, credit card, prepaid card |
| `cash` | Cash | Cash wallet, USD cash, ARS cash |
| `bank` | Bank account | Checking, current account |
| `wallet` | Digital wallet | Mercado Pago, PayPal, Wise |
| `platform` | Money platform | Payoneer |
| `savings` | Savings | Emergency fund, reserve |
| `other` | Other | Anything that does not fit above |

Decision notes:

- Do not split debit and credit card in MVP.
- `card` is broad and keeps the transition from the current model simple.
- Do not add `investment` yet unless we are ready to support different balance and
  reporting semantics.
- If true credit debt semantics are needed later, add them as a separate liability
  capability, not just as another label.

## Domain Model

### Aggregate

Introduce `Account` as the aggregate root and make `Card` a retired model name.

Modeling decision:

- Do **not** model `Card` as a separate relation from `Account`.
- Model it as `Account.type == AccountType.CARD`.
- In other words, card is an account category, not another aggregate attached to an
  account.

Suggested shape:

```python
@dataclass(slots=True)
class Account:
    id: str
    name: str
    type: AccountType
    currency: str
    current_balance: Money
    status: AccountStatus
    color_key: str | None
    opened_on: date
    closed_on: date | None
    created_on: date
    updated_on: date
```

### Supporting types

```python
class AccountType(StrEnum):
    CARD = "card"
    CASH = "cash"
    BANK = "bank"
    WALLET = "wallet"
    PLATFORM = "platform"
    SAVINGS = "savings"
    OTHER = "other"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"
```

If we later need card-only detail, add a scoped optional field set such as
`card_kind`, `last4`, or `issuer_name`, guarded by `type == card`. Do not split
the aggregate unless card behavior becomes materially different from the rest of
the account model.

### Domain invariants

- `id` and `name` are non-blank normalized strings.
- `currency` is a normalized ISO 4217 code.
- `current_balance.currency == currency`.
- For MVP, `current_balance.amount_minor >= 0`.
- One account has one currency.
- Multi-currency ownership is modeled as multiple accounts, for example `USD cash` and `ARS cash`.

### Behavior in MVP

Accounts keep the same asset-style behavior as current cards:

- `open_account`
- `credit_account`
- `debit_account`
- `close_account`
- `update_account_profile`

Notes:

- `credit_account` and `debit_account` are implementation-friendly names for the
  current balance-changing behavior.
- They are a bridge until transaction-driven balance updates exist.
- Future expenses, incomes, and transfers should eventually become the only normal way balances move.

### Cutover from cards

The accounts rollout is a clean replacement, not a backward-compatible layer.

Mapping rule:

- `Card -> Account(type=card, status=active)`
- Existing `balance -> current_balance`
- Existing issue/open date becomes the account open date

Naming rule:

- Replace card-specific ids, routes, schemas, and service names with account-based
  ones.
- Do not preserve `card_*` naming or `/cards` endpoints once the cutover lands.

Recommendation:

- Refactor the domain boundary to `Account` now.
- Avoid keeping both `Card` and `Account` as first-class aggregates.
- Treat cards as an account subtype from the beginning of this workstream.

## Data Model

Use a single account record for MVP. Do not introduce subtype tables.

Suggested storage shape:

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Stable account id |
| `name` | string | User-facing account name |
| `type` | enum | `card`, `cash`, `bank`, `wallet`, `platform`, `savings`, `other` |
| `currency` | string | ISO 4217 |
| `current_balance_minor` | integer | Current balance |
| `status` | enum | `active`, `closed` |
| `color_key` | string nullable | UI token, not business logic |
| `opened_on` | date | User-facing account start date |
| `closed_on` | date nullable | Only for closed accounts |
| `created_on` | timestamp/date | System creation time |
| `updated_on` | timestamp/date | Last write time |

Why keep a single balance in MVP:

- It matches the current cards implementation.
- It keeps account creation and persistence simple.
- It avoids introducing setup-history semantics before a real transaction model exists.
- When transaction records land, the balance can later become a derived value or a
  cached projection.


## API and Type Direction

Backend naming should move from card-specific to account-specific:

- `wallet.domain.cards -> wallet.domain.accounts`
- `CardRepository -> AccountRepository`
- `CardService -> AccountService`
- `/api/v1/cards -> /api/v1/accounts`

Suggested request/response direction:

- `CreateAccountRequest`
- `AccountResponse`
- `ListAccountsResponse`
- `CreditAccountRequest`
- `DebitAccountRequest`

Recommended create payload fields:

- `name`
- `type`
- `currency`
- `current_balance_minor`
- `opened_on`
- `color_key`

## UI Model

The reference screenshots are useful mainly for structure and presentation, not
for account taxonomy.

Keep these ideas:

- Accounts list with card-like tiles
- Type badge plus currency badge
- Strong visual identity through icon + accent color
- Account creation flow with type selector and live preview
- A clear initial balance field during account setup

Do not copy directly:

- Separate `credit` account type in MVP
- `investment` type in MVP

Recommended default icon mapping:

| Type | Default icon direction |
| --- | --- |
| `card` | card |
| `cash` | banknote or wallet |
| `bank` | bank/building |
| `wallet` | phone wallet or app wallet |
| `platform` | briefcase or payout |
| `savings` | piggy bank or shield/vault |
| `other` | generic account/grid |

Recommended UX rules:

- Require account name, type, and currency.
- Allow optional color choice.
- Show initial balance during creation.
- Use the same account card component for all types, with icon and accent driven
  by type and color.

## Out of Scope for This Workstream

- Bank sync
- Import pipelines
- Credit debt / statement / limit semantics
- Investments and mark-to-market valuation
- Multi-owner/shared-account permissions
- Merge-account flows
- Transaction ledger redesign beyond the account-facing hooks needed now

## Delivery Plan

### Phase 0: Documentation and naming lock

- Approve `Account` as the primary concept.
- Approve MVP account types.
- Approve the manual-account-first scope.
- Promote accepted vocabulary into `docs/product/concepts.md`.
- Promote accepted account scope into `docs/product/spec.md`.

### Phase 1: Backend refactor from cards to accounts

- Add `wallet.domain.accounts`.
- Replace `Card` aggregate with `Account`.
- Add `AccountType` with `card` as the default and `AccountStatus` with `active`
  as the default.
- Rename repositories, services, schemas, and routes to account-based names.
- Preserve current balance behavior with non-negative asset semantics.
- Map all existing card tests to account tests.

Exit criteria:

- Account lifecycle behavior works through `/api/v1/accounts`.
- The backend no longer exposes card-specific aggregate or route names.

### Phase 2: Account type support and account profile metadata

- Support all approved MVP account types in validation and persistence.
- Support account create, list, get, update profile, and close operations.
- Return account type and display metadata in API responses.

Exit criteria:

- API supports `card`, `cash`, `bank`, `wallet`, `platform`, `savings`, and
  `other` accounts.
- User can create `card`, `cash`, `bank`, `wallet`, `platform`, `savings`, and
  `other` accounts through backend flows.

### Phase 3: Frontend account creation and listing

- Replace cards-only screens with accounts screens.
- Add account type picker based on the approved taxonomy.
- Add icon and color defaults by type.
- Add initial balance input and preview card.
- Update list screens so total balance and grouping are account-based.

Exit criteria:

- A user can create and view multiple account types end to end.
- UI can render type-specific account cards without special-casing cards.
- The UI uses account terminology throughout.
