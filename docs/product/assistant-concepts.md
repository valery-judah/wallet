# Wallet Assistant Concepts

Status: canonical Assistant supporting-context language

## Purpose and Authority

This document defines the preferred product and technical terms for the Wallet Assistant

supporting context. The Assistant is downstream of the core Wallet domain and consumes

[Wallet Concepts](concepts.md).

Account, Balance, Currency, Transaction, Expense, Income, Transfer, Balance adjustment, Posting,

Spending category, and Income category keep their Wallet meanings inside the Assistant context.

This document does not redefine them or grant the model authority over them.

The related documents have different responsibilities:

- [Wallet AI Capabilities Frame](ai-capabilities-frame.md) defines the Assistant-enabled jobs, user
  needs, trust conditions, and evaluation anchors.
- [Wallet MVP Spec](spec.md#conversational-control-and-capabilities) defines the Assistant behavior
  supported by the current product slice.
- [Message Router Contract](../evergreen/message-router-contract.md) and
  [Transaction Interpretation Contract](../evergreen/transaction-interpretation-contract.md)
  define implementation mechanics.

## Assistant Product Concepts
### Wallet Assistant

**Wallet Assistant** is the user-facing interaction surface for supported AI capabilities. It lets

the user express a Wallet need in natural language and receive a grounded answer or a reviewable

proposed action.

Wallet Assistant is not a general-purpose chatbot, a financial adviser, or a separate financial

record.

### AI capability

An **AI capability** is a bounded way to help the user complete one Wallet job. It defines the

supported outcome, the context AI may interpret, the authoritative Wallet state it may use, and the

control required before any effect.

AI capability is a product-planning term. Do not expose capability identifiers or runtime handler

language in normal product copy.

### Task

A **task** is the one supported job Wallet Assistant is currently helping the user complete. A task

may collect information across several messages and remains active until it completes, is

cancelled, or is restarted.

Use **task** in user-facing guidance. Do not require users to understand routing, ownership, or

workflow-session mechanics.

### Transaction draft

A **transaction draft** is a reviewable transaction candidate assembled from the user's

contributions and grounded Wallet references. It may be incomplete or awaiting confirmation.

A transaction draft belongs to the Assistant context. It does not change an account balance and is

not a Wallet transaction. After confirmation, the Assistant translates the draft into a request to

the Wallet application boundary. Wallet then revalidates the request and, if valid, records the

core transaction.

### Confirmation

**Confirmation** is the deliberate product action that authorizes Wallet to revalidate and record a

reviewed transaction draft. Use **Confirm** for the displayed action.

Conversational agreement such as `yes`, `okay`, or `do it` is not confirmation. The model does not

own confirmation or transaction execution.

### Grounded answer

A **grounded answer** is based on authoritative Wallet data made available for the supported task.

It must not fill gaps with general model knowledge, invented records, assumed conversions, or

unsupported judgments.

### Current balances

**Current balances** is the preferred user-facing term for a read-only answer about amounts

currently recorded in Wallet accounts. It is a query projection of authoritative Wallet account

and transaction state, not Assistant-owned financial state. Currencies remain separate unless an

explicit exchange model exists.

**Wallet state** may be used in product and engineering documentation for the authoritative

snapshot underlying that answer. It should not appear in normal copy when **current balances** is

clearer, and it must not be presented as net worth, financial health, financial advice, or a

converted multi-currency total.

### Authority boundary

Wallet Assistant may interpret language, connect words to available Wallet references, ask for

missing information, and assemble a proposed answer or action. Wallet data remains authoritative

for recorded facts, and deterministic Wallet rules remain authoritative for validity and financial

effects.

The sequence for a consequential action is therefore:

1. the user expresses an intent;
2. Wallet Assistant interprets and grounds it;
3. the product presents a reviewable draft;
4. the user takes the defined Confirm action; and
5. Wallet revalidates and records the transaction.

## Naming and Distinction Rules

| Use | Avoid | Reason |
| --- | --- | --- |
| Transaction draft before confirmation; transaction after posting | Calling a draft a recorded transaction | A draft belongs to the Assistant context and has no ledger effect |
| Confirm for the guarded product action | Treating natural-language agreement as execution authority | The model cannot authorize a financial write |
| Chat and task in user-facing copy | Conversation versions, capability IDs, routing, or workflow sessions | These are implementation mechanics |
| Current balances for the supported read-only answer | Wallet state, net worth, health, or advice in user-facing copy | The answer is a projection of recorded Wallet balances only |

## Internal Control-Layer Vocabulary

The terms in this section support API and engineering work inside the Assistant context. They are

not preferred user-facing language and do not expand the product concepts above.

| Internal term | Engineering meaning | Detailed authority |
| --- | --- | --- |
| Conversation | Server-side continuity holder for accepted assistant turns; not a durable transcript or general memory | [Message Router Contract](../evergreen/message-router-contract.md) |
| Turn | One identified input submitted to a new or existing conversation and its resulting outcome | [Message Router Contract](../evergreen/message-router-contract.md) |
| Runtime capability | Registered handler that owns a bounded task; represented by `Capability` in code | [Message Router Contract](../evergreen/message-router-contract.md#capability-routing-metadata) |
| Route decision | Model proposal selecting, clarifying, or declining ownership of one idle message | [Message Router Contract](../evergreen/message-router-contract.md#closed-route-decisions) |
| Routing memory | Bounded identity of the most recent capability-associated outcome; not transcript or domain-state memory | [Message Router Contract](../evergreen/message-router-contract.md#bounded-recent-capability-memory) |
| Transaction interpretation | Structured model proposal for changing a transaction draft without executing it | [Transaction Interpretation Contract](../evergreen/transaction-interpretation-contract.md) |

Existing API object names, identifiers such as `transactions.capture` and `wallet.current_state`,

and implementation type names remain unchanged. They should not be copied into user-facing language

merely because they are public or observable in technical interfaces.
