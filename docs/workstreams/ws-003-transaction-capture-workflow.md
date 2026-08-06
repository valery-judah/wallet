# Transaction Capture Workflow

The transaction-capture workflow progressively fills the fields required to
record one transaction.

Its objective is:

> Build a complete transaction candidate from the conversation, ask for any
> required fields that are still missing, and record the transaction once the
> candidate is complete.


Related workstream material:

- [`ws-003-use-cases.md`](ws-003-use-cases.md)
- [`transaction_capture_workflow.feature`](transaction_capture_workflow.feature)

## Scope

The first version supports the four MVP transaction types:

- `expense`
- `income`
- `transfer`
- `adjustment`

The workflow tracks only the current value of each field. It does not track
confidence, provenance, previous values, or whether a value was explicit,
inferred, defaulted, or corrected.

Confirmation policy, transaction editing, voiding, refunds, multi-currency
transfers, and split-expense capture are outside this first workflow design.

## Capture Session

An active capture session contains:

```text
CaptureSession
- candidate
- remaining_fields
- requested_field
```

`candidate` contains the transaction information collected so far.

`remaining_fields` is computed from the candidate. It is not maintained as an
independent source of truth.

`requested_field` identifies the field the workflow most recently asked the
user to provide. It helps interpret short answers such as `35` or `Cash`.

## Candidate Fields

The candidate uses user-facing transaction fields rather than signed ledger
postings:

```text
TransactionCandidate
- type
- amount_minor
- occurred_on
- account_id
- spending_category_id
- income_category_id
- source_account_id
- destination_account_id
- balance_change_minor
- description
- merchant_name
- notes
```

Only the fields relevant to the selected transaction type are used.

Money is stored in minor units. `amount_minor` is a positive magnitude for
expenses, income, and transfers. `balance_change_minor` is signed: a positive
value increases an account balance and a negative value decreases it.

Currency is not collected as a separate candidate field. It is obtained from
the selected account. A transfer is allowed only when its source and destination
accounts use the same currency.

## Required Fields

The transaction type determines which fields must be present before recording.

| Transaction type | Required fields |
| --- | --- |
| `expense` | `amount_minor`, `account_id`, `spending_category_id`, `occurred_on` |
| `income` | `amount_minor`, `account_id`, `income_category_id`, `occurred_on` |
| `transfer` | `amount_minor`, `source_account_id`, `destination_account_id`, `occurred_on` |
| `adjustment` | `account_id`, `balance_change_minor`, `occurred_on` |

`type` is required for every candidate because it selects the applicable field
set.

The workflow initializes `occurred_on` to today's date. A date stated by the
user replaces that value. As a result, the workflow normally does not need to
ask for a date.

The following fields are optional for every type:

- `description`
- `merchant_name`
- `notes`

## Computing Remaining Fields

The workflow selects the required field set for the current transaction type
and removes every field already populated on the candidate.

```text
if candidate.type is missing:
    remaining_fields = [type]
else:
    remaining_fields = required_fields[candidate.type]
                       - populated_fields(candidate)
```

The result uses a stable order so the workflow knows which question to ask
next:

```text
expense:   amount_minor, account_id, spending_category_id, occurred_on
income:    amount_minor, account_id, income_category_id, occurred_on
transfer:  amount_minor, source_account_id, destination_account_id, occurred_on
adjustment: account_id, balance_change_minor, occurred_on
```

The first entry in `remaining_fields` becomes `requested_field`.

## Workflow Loop

```text
Enter capture
    ↓
Create candidate with occurred_on = today
    ↓
Apply information from the user's message
    ↓
Compute remaining_fields
    ├── fields remain → ask for the first field
    │                       ↓
    │                 apply the answer
    │                       ↓
    │                 recompute remaining_fields
    │
    └── no fields remain → validate → create transaction → finish
```

Each message may fill or replace one or more candidate fields. After every
change, `remaining_fields` is recomputed from the current candidate.

When `requested_field` is set, a short answer is interpreted as the value of
that field:

```text
requested_field: amount_minor
user: "35"
result: candidate.amount_minor = 3500
```

If the user supplies other transaction information in the same answer, the
workflow applies that information too before recomputing the remaining fields.

## Type-Specific Construction

### Expense

An expense requires:

```text
amount_minor
account_id
spending_category_id
occurred_on
```

It produces:

```text
account posting:           -amount_minor
spending category posting: +amount_minor
```

The posting currency comes from `account_id`.

### Income

Income requires:

```text
amount_minor
account_id
income_category_id
occurred_on
```

It produces:

```text
account posting:        +amount_minor
income category posting: -amount_minor
```

The posting currency comes from `account_id`.

### Transfer

A transfer requires:

```text
amount_minor
source_account_id
destination_account_id
occurred_on
```

It produces:

```text
source account posting:      -amount_minor
destination account posting: +amount_minor
```

The source and destination accounts must be different, active accounts with the
same currency.

### Balance Adjustment

A balance adjustment requires:

```text
account_id
balance_change_minor
occurred_on
```

It produces one posting for the selected account:

```text
account posting: balance_change_minor
```

The transaction service creates the balancing system-equity posting. The
posting currency comes from `account_id`.

This first design captures a balance change, such as `increase Cash by $50`.
Capturing a target balance, such as `set Cash to $500`, requires reading the
current balance and converting the target into a balance change; that can be
added as a later input form without changing the adjustment transaction model.

## Validation Before Recording

A candidate with no remaining fields is complete, but its values must still be
valid:

- monetary amounts must be non-zero and use the sign rules above;
- referenced accounts must exist, be visible, and accept transactions;
- the expense category must be a spending category;
- the income category must be an income category;
- transfer accounts must be different and use the same currency;
- the date must be accepted by the transaction service.

If validation identifies an unusable field, the workflow clears that field,
recomputes `remaining_fields`, and asks for it again.

## Examples

### Expense with one missing field

```text
User: "Spent $40 on dinner"

Candidate:
  type: expense
  amount_minor: 4000
  account_id: missing
  spending_category_id: Dining
  occurred_on: today

Remaining fields:
  account_id

System: "Which account did you use?"
User: "Cash"

Remaining fields: none
Result: record the expense
```

### Transfer collected over two turns

```text
User: "Transfer $100 from Checking"

Candidate:
  type: transfer
  amount_minor: 10000
  source_account_id: Checking
  destination_account_id: missing
  occurred_on: today

Remaining fields:
  destination_account_id

System: "Which account did you transfer it to?"
User: "Savings"

Remaining fields: none
Result: record the transfer
```

## Completion

The workflow finishes when the transaction service returns the created
transaction. It responds with a compact summary and closes the capture session.

```text
Recorded: $40 dinner expense from Cash for today.
```
