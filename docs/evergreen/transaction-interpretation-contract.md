# Transaction Interpretation Contract

Status: implemented MVP contract
Last reviewed: 2026-08-07
Scope: natural-language contributions handled by `transactions.capture`

## Purpose

Transaction interpretation converts one user contribution into a reviewable transaction-draft
change. A schema-constrained language model owns this language task because amounts, references,
dates, corrections, and short answers may be expressed indirectly or imprecisely.

Interpretation is not transaction execution. The model may propose normalized values and select
only references offered for the current call. Wallet code remains authoritative for draft
application, reference validity, currency compatibility, confirmation guards, ledger invariants,
idempotency, and persistence.

## Processing flow

For an idle conversation, the message router first selects `transactions.capture`; the capture
capability then makes one interpretation call. While capture is active, every non-control message
goes directly to the capability and makes one interpretation call. Exact textual controls, typed
controls, and typed task actions bypass interpretation.

The application performs these steps:

1. Build a safe, per-call reference catalog with opaque keys.
2. Ask the model to interpret the complete validated contribution, after surrounding whitespace
   trimming, against the current draft.
3. Validate and map the structured response back to registered Wallet references.
4. Apply valid partial updates and explicit clears to the draft.
5. Deterministically identify missing, ambiguous, unresolved, or invalid fields.
6. Present the draft for review or ask one corrective question.
7. Execute only after a guarded typed `confirm` action and authoritative revalidation.

No natural-language contribution can execute a transaction.

## Model input boundary

The interpreter provides:

- the complete validated contribution, after surrounding whitespace trimming, as untrusted user
  content;
- the current date;
- the current transaction candidate, using values and safe reference labels;
- the current pending interaction;
- selectable account labels and currencies;
- selectable spending- and income-category paths;
- trusted instructions describing the structured interpretation contract.

The interpreter does not provide:

- internal account or category IDs;
- repositories, services, or other application objects;
- request, conversation, task, operation, or version identifiers;
- transcript history;
- prior raw model output;
- message-router prompts or capability-private prompts unrelated to interpretation.

The application creates deterministic keys such as `account_0`, `spending_3`, and `income_1`
for each call. The prompt maps those keys to safe labels and account currencies. Keys are neither
stable domain identifiers nor valid outside that call.

## Structured interpretation

One successful interpretation contains:

- `updates`: supplied normalized values, including transaction type, minor-unit amounts, ISO date,
  currency code, opaque reference keys, and optional descriptive text;
- `clear_fields`: fields the user explicitly asked to remove;
- `ambiguities`: a reference field plus at least two offered keys when more than one catalog item
  remains plausible;
- `unresolved_fields`: fields the user supplied but the model could not map safely;
- `clarification_needed`: whether the contribution is contradictory or generally uninterpretable;
- optional field-level `evidence` used only for internal diagnostics.

Omitted update fields preserve the current draft. Update values are never `null`; explicit removal
uses `clear_fields`. One field cannot be updated and cleared in the same result. Reference keys must
belong to the field's catalog family, ambiguity candidates must be distinct, and all returned fields
must be relevant to the proposed transaction type.

Evidence is advisory. It need not be an exact source span, does not authorize a value, and never
blocks an otherwise valid interpretation.

## Draft application and validation

A valid model-selected reference is accepted into the draft even when its label does not literally
appear in the message. This permits useful interpretation of typos, aliases, and colloquial wording.
There is no second fuzzy matcher, confidence threshold, or suggestion-confirmation step. The entire
transaction still requires final confirmation.

Valid partial updates are retained even when another field is ambiguous or unresolved. Ambiguous,
unresolved, unavailable, or currency-conflicting references are cleared and surfaced through the
existing interaction mechanism.

As an application-side consistency rule, an unqualified category leaf shared by multiple offered
paths cannot silently select one path. If the model selects one such key without a parent qualifier,
the interpreter projects all matching offered keys as a disambiguation. It still does not choose a
category, perform fuzzy matching, or introduce a second extraction pipeline.

`currency_code` is capture-only context. It is normalized only from an explicitly stated currency,
preserved across later contributions that omit currency, and is not persisted as an independent
ledger field. Deterministic validation requires:

- a selected account to remain active, non-system, and available;
- an explicit currency to match its selected account;
- transfer source and destination accounts to share a currency;
- an explicit transfer currency to match both accounts;
- spending and income references to belong to their correct catalogs;
- amounts, adjustments, and transfer-account combinations to satisfy local domain rules.

On an explicit currency conflict, the application preserves the currency, clears the conflicting
account reference, and asks for a compatible account. Cross-currency transfers remain unsupported.

## Failure, retry, and publication

The interpreter retries once after malformed JSON, an invented or wrong-family key, conflicting
operations, an invalid field combination, or other context-inconsistent structured output. The
retry contains compact validation feedback. Transport failures are not retried.

If validation still fails, the turn returns the existing safe `502`. No successful replay
snapshot or request fingerprint is stored, and the conversation, task candidate, and ledger
remain uncommitted, so the caller may retry the identical request ID.

## Privacy and observability

Interpretation events may record attempt count, duration, applied field names, ambiguity and
unresolved field names, currency-conflict field names, and whether clarification was requested.
Internal evidence may be retained only where explicitly needed for diagnostics.

Logs, public views, and serialized processing traces must never contain user text, prompts, raw
model output, evidence text, opaque-key mappings, full reference catalogs, or internal identifiers.

## Acceptance obligations

Deterministic tests use an injected interpreter and cover every result and failure shape. Real-model
smoke tests cover complete and progressive transaction types, typo-tolerant catalog selection,
ambiguity, unknown references, currency conflicts, corrections, clears, and short active replies.
All tests must prove that preview is ledger-neutral and only guarded confirmation can persist one
balanced, idempotent transaction.

## Implementation anchors

- [`interpretation.py`](../../backend/src/wallet/ai/transaction_capture/interpretation.py): model
  input, opaque keys, schema, application validation, and retry;
- [`processing.py`](../../backend/src/wallet/ai/transaction_capture/processing.py): partial draft
  application, unavailable references, ambiguity, unresolved fields, and currency conflicts;
- [`capability.py`](../../backend/src/wallet/ai/transaction_capture/capability.py): active-message
  handling, corrective interactions, preview, and guarded confirmation;
- [`test_interpretation.py`](../../backend/tests/ai/transaction_capture/test_interpretation.py) and
  [`test_processing.py`](../../backend/tests/ai/transaction_capture/test_processing.py): executable
  interpretation boundary.
