# Wallet MVP Spec

Product intent, the primary job, user needs, desired outcomes, and evaluation anchors are defined

in [Wallet Product Frame](wallet-frame.md). This specification defines the current MVP scope and

supported behavior. Core financial meanings are defined in [Wallet Concepts](concepts.md).

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

- **Connected account:** an account whose records are synchronized from a financial provider.
- **Bank sync:** ongoing retrieval of account and transaction records from a financial provider.
- **Import pipeline:** ingestion of account or transaction records from an external source.
- **Pending transaction:** a transaction represented before it becomes posted financial history.
- **Void transaction:** a transaction explicitly invalidated through a supported lifecycle
  operation.

## Conversational Control and Capabilities

The product role, user needs, authority model, principles, and evaluation anchors for AI are

defined in [Wallet AI Capabilities Frame](ai-capabilities-frame.md). Shared assistant and

control-layer terminology is defined in

[Wallet Assistant Concepts](assistant-concepts.md). This section defines the current MVP behavior.

The MVP exposes one process-local conversation control layer. A caller submits every input to

`POST /api/v1/turns`. Omitting `conversation_id` creates and processes a conversation atomically;

supplying the returned ID continues it. `GET /api/v1/conversations/{conversation_id}` reads the

current projection. There is no public empty-conversation or workflow-start operation.

A conversation has zero or one opaque active task. Capability implementations form an open

extension point; the current runtime registry contains:

- `transactions.capture`, which progressively collects and records one expense, income,
  transfer, or balance adjustment;
- `wallet.current_state`, which completes in one turn with active-account balances and
  totals kept separate by currency.

While a conversation is idle, an authoritative LLM message router assigns each ordinary

natural-language message to one registered capability. It receives the complete validated

message, the most recent committed capability-associated identity, and control-level routing

profiles, but no raw transcript, capability-private state, or Wallet catalogs. This bounded

routing memory supports reference-only follow-ups such as `one more time` without authorizing

replay of prior messages, state, or domain effects. The identity is preserved through outcomes

that are not capability-associated, including cancellation.

While a task is active, every non-control message goes directly to its capability; the router is

not called and capability switching is unavailable. Typed task actions and typed cancel/restart

controls carry task and conversation-version guards; typed Help is unguarded. Exact whole-message

`help`, `cancel`, and `restart` controls remain deterministic and bypass both routing and

capability message handling. Textual controls are unguarded and act on the task current when the

serialized turn is processed.

Transaction capture sends every natural-language contribution through one schema-constrained

interpreter. The model sees the current reviewable draft, pending interaction, current date, and

safe account/category labels, and may normalize values or select registered references even when

the user's wording contains typos or aliases. Per-call opaque keys keep internal entity IDs out of

the prompt. Valid partial changes enter the draft; ambiguous, unresolved, unavailable, and

currency-conflicting fields produce corrective interactions.

The interpreter never executes transactions. Deterministic code validates selected references,

account currencies, amounts, transaction-type rules, and transfer compatibility. A complete

candidate enters `awaiting_confirmation` without changing the ledger. Only a guarded typed

`confirm` task action performs authoritative revalidation and creates exactly one posted

transaction. Turn replay and Wallet operation IDs prevent duplicate execution.

Current wallet state is read-only. It derives balances from posted account entries, excludes

archived accounts, returns its snapshot once in the structured view, and leaves the conversation

idle after the turn. Ambiguous routing decisions preserve the current lifecycle state and ask

for clarification.

The web app exposes one lightweight Wallet Assistant at `/assistant`. It supports ordinary

messages, capability action offers, and the help, cancel, and restart lifecycle controls. The

browser keeps one transcript and its current conversation in tab-scoped session storage; there is

no durable conversation list. Friendly capture and wallet-state summaries are projections of the

public capability views, while optional details expose public outcome and version metadata.

Conversations, global request replay records, and active-task state are process-local. They

survive requests handled by the same backend process but not restarts or multiple workers.

The UI discards an expired restored conversation and starts fresh after a backend restart.

Every ordinary idle message requires the configured Ollama service for routing. A message routed

to transaction capture then requires one interpretation call, and each later non-control capture

message requires one interpretation call without re-routing. Current-wallet-state execution remains

deterministic after routing. Exact controls, typed controls, and typed task actions require neither

routing nor interpretation.

Direct manual transaction creation through `/api/v1/transactions` remains immediate.

## Out of Scope

The MVP does not yet include:

- Rich credit-card workflows such as statement cycles and limits
- Investment valuation
- Account merging
- Shared-account permissions
- Bank connections or sync
- Multi-currency FX transactions
- Budget rules based on transaction classification
- Durable or multi-worker conversations
- Asynchronous or streaming capture responses
- External messaging-channel adapters
