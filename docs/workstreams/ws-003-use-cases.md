# Transaction Capture Workflow — Use Cases

## 1. Purpose

These use cases define the observable behavior of the transaction-capture workflow.

The workflow must:

1. Build a transaction candidate from one or more user messages.
2. Default the transaction date to today.
3. Determine which required fields remain missing.
4. Ask for missing fields in a stable order.
5. Interpret short replies using `requested_field`.
6. Validate a complete candidate.
7. Recover from invalid field values.
8. Create the transaction and close the capture session.

The use cases cover the four supported transaction types:

* Expense
* Income
* Transfer
* Balance adjustment

---

# Core Capture Use Cases

## UC-01 — Capture a complete expense in one message

**Goal:** Record an expense without asking follow-up questions.

**Given**

* No capture session is active.
* The referenced account and spending category are valid.

**When**

The user says:

> Spent $40 from Cash on Dining yesterday.

**Then**

The workflow creates a candidate containing:

```text
type: expense
amount_minor: 4000
account_id: Cash
spending_category_id: Dining
occurred_on: yesterday
```

`remaining_fields` is empty.

The workflow validates and records the transaction.

Expected postings:

```text
Cash account:     -4000
Dining category:  +4000
```

The workflow returns a compact summary and closes the session.

---

## UC-02 — Capture a complete income transaction

**Goal:** Record income from a single message.

**When**

The user says:

> Received $2,500 salary into Checking today.

**Then**

The candidate contains:

```text
type: income
amount_minor: 250000
account_id: Checking
income_category_id: Salary
occurred_on: today
```

Expected postings:

```text
Checking account: +250000
Salary category:  -250000
```

The transaction is recorded without a follow-up question.

---

## UC-03 — Capture a complete transfer

**Goal:** Record a transfer when all required information is supplied.

**Given**

* Checking and Savings are active.
* Both accounts use the same currency.
* The accounts are different.

**When**

The user says:

> Transfer $500 from Checking to Savings.

**Then**

The candidate contains:

```text
type: transfer
amount_minor: 50000
source_account_id: Checking
destination_account_id: Savings
occurred_on: today
```

Expected postings:

```text
Checking account: -50000
Savings account:  +50000
```

The transaction is recorded.

---

## UC-04 — Capture a balance adjustment

**Goal:** Record a signed balance change.

**When**

The user says:

> Increase Cash by $50.

**Then**

The candidate contains:

```text
type: adjustment
account_id: Cash
balance_change_minor: 5000
occurred_on: today
```

The workflow creates an account posting of `+5000`.

The transaction service creates the balancing system-equity posting.

### Negative adjustment variant

When the user says:

> Reduce Cash by $20.

The candidate contains:

```text
balance_change_minor: -2000
```

---

# Progressive Capture Use Cases

## UC-05 — Ask for the transaction type

**Goal:** Determine the applicable field set when the type cannot be inferred.

**When**

The initial message supplies transaction information but does not establish a type.

**Then**

The candidate has no `type`.

The workflow computes:

```text
remaining_fields: [type]
requested_field: type
```

The workflow asks the user to identify the transaction type.

After the user answers, the workflow recomputes `remaining_fields` using the selected type.

---

## UC-06 — Ask for one missing expense field

**When**

The user says:

> Spent $40 on dinner.

**Then**

The candidate contains:

```text
type: expense
amount_minor: 4000
spending_category_id: Dining
occurred_on: today
account_id: missing
```

The workflow computes:

```text
remaining_fields: [account_id]
requested_field: account_id
```

The workflow asks:

> Which account did you use?

When the user answers:

> Cash

The workflow assigns `Cash` to `account_id`, recomputes the remaining fields, and records the expense.

---

## UC-07 — Ask for multiple fields in stable order

**Goal:** Ensure missing fields are collected predictably.

**When**

The user says:

> Record an expense.

**Then**

The missing fields are ordered as:

```text
amount_minor
account_id
spending_category_id
```

`occurred_on` is already populated with today’s date.

The workflow asks for `amount_minor` first.

After each answer, it recomputes the missing fields and asks for the next field in the defined order.

The workflow must not maintain a separate mutable missing-field list that can diverge from the candidate.

---

## UC-08 — Interpret a short answer using `requested_field`

**Given**

```text
requested_field: amount_minor
```

**When**

The user replies:

> 35

**Then**

The workflow interprets the answer as the requested amount:

```text
amount_minor: 3500
```

It does not interpret `35` as a date, account, category, or another transaction field.

---

## UC-09 — Apply additional information from a follow-up answer

**Given**

The workflow has asked for the expense amount.

**When**

The user replies:

> $35 from Cash for groceries.

**Then**

The workflow applies every recognized field from the message:

```text
amount_minor: 3500
account_id: Cash
spending_category_id: Groceries
```

The workflow recomputes `remaining_fields` after applying all extracted information.

It does not stop after assigning the requested amount.

---

## UC-10 — Collect a transfer over multiple turns

**When**

The user says:

> Transfer $100 from Checking.

**Then**

The candidate contains:

```text
type: transfer
amount_minor: 10000
source_account_id: Checking
destination_account_id: missing
occurred_on: today
```

The workflow asks:

> Which account did you transfer it to?

When the user replies:

> Savings

The workflow assigns the destination account and records the transfer.

---

# Date Use Cases

## UC-11 — Default the date to today

**Goal:** Avoid asking for a date in the normal capture flow.

**When**

A capture session is created.

**Then**

The workflow initializes:

```text
occurred_on: today
```

Unless the user provides another date, `occurred_on` is considered populated and is excluded from `remaining_fields`.

---

## UC-12 — Replace the default date

**Given**

The candidate initially contains:

```text
occurred_on: today
```

**When**

The user says:

> This happened last Friday.

**Then**

The workflow replaces the existing date with the resolved date for last Friday.

It recomputes `remaining_fields` from the updated candidate.

---

# Candidate Update Use Cases

## UC-13 — Replace a previously captured field

**Given**

The candidate contains:

```text
account_id: Cash
```

**When**

Before completion, the user says:

> Actually, I used Checking.

**Then**

The workflow replaces the current value:

```text
account_id: Checking
```

The workflow retains only the current field value.

It does not retain field history, correction metadata, provenance, or confidence.

---

## UC-14 — Change the transaction type before recording

**Given**

A partially populated candidate has:

```text
type: expense
```

**When**

The user clarifies:

> This was actually a transfer.

**Then**

The workflow sets:

```text
type: transfer
```

It recomputes `remaining_fields` using the transfer field set.

Expense-specific fields such as `spending_category_id` are no longer relevant to transaction construction.

The specification does not define whether irrelevant values must be physically removed from the candidate or merely ignored. This should be resolved as an implementation rule.

---

## UC-15 — Preserve optional metadata

**When**

The user says:

> Spent $25 from Cash on Dining at Corner Cafe. Team lunch.

**Then**

The candidate may contain:

```text
description: Team lunch
merchant_name: Corner Cafe
```

Optional metadata is preserved but does not affect `remaining_fields`.

The absence of `description`, `merchant_name`, or `notes` must not block transaction creation.

---

# Validation and Recovery Use Cases

## UC-16 — Reject a zero amount

**Given**

A candidate is otherwise complete.

**When**

```text
amount_minor: 0
```

or:

```text
balance_change_minor: 0
```

**Then**

Validation fails.

The workflow clears the invalid monetary field, recomputes `remaining_fields`, and asks the user for that field again.

For example:

```text
amount_minor: cleared
remaining_fields: [amount_minor]
requested_field: amount_minor
```

---

## UC-17 — Reject an unusable account

**Given**

The candidate references an account that:

* Does not exist,
* Is not visible to the user,
* Is inactive, or
* Does not accept transactions.

**Then**

Validation fails.

The workflow clears the corresponding account field.

Possible fields include:

```text
account_id
source_account_id
destination_account_id
```

The workflow recomputes `remaining_fields` and requests a valid account.

---

## UC-18 — Reject an incorrect expense category type

**Given**

An expense candidate contains an existing category that is not a spending category.

**Then**

Validation fails.

The workflow clears:

```text
spending_category_id
```

It asks the user to select a spending category.

---

## UC-19 — Reject an incorrect income category type

**Given**

An income candidate contains an existing category that is not an income category.

**Then**

Validation fails.

The workflow clears:

```text
income_category_id
```

It asks the user to select an income category.

---

## UC-20 — Reject a transfer to the same account

**Given**

```text
source_account_id: Checking
destination_account_id: Checking
```

**Then**

Validation fails because the source and destination must be different.

The workflow clears at least one account field and requests a replacement.

### Product decision required

The specification does not define which field should be cleared.

A deterministic policy is needed, such as:

```text
Clear destination_account_id and preserve source_account_id.
```

This policy aligns with the stable capture order because the source is collected before the destination.

---

## UC-21 — Reject a cross-currency transfer

**Given**

* The source account uses USD.
* The destination account uses EUR.

**Then**

Validation fails because MVP transfers require matching account currencies.

The workflow clears an account field, recomputes the missing fields, and requests another account.

### Product decision required

The specification does not define which account field should be cleared. Preserving the source and clearing the destination would provide deterministic behavior.

---

## UC-22 — Reject an invalid date

**Given**

A complete candidate contains a date rejected by the transaction service.

**Then**

The workflow clears:

```text
occurred_on
```

It recomputes:

```text
remaining_fields: [occurred_on]
requested_field: occurred_on
```

The workflow asks the user for another date.

---

## UC-23 — Revalidate after correcting a field

**Given**

A complete candidate failed validation and one field was cleared.

**When**

The user provides a replacement value.

**Then**

The workflow:

1. Applies the replacement.
2. Recomputes `remaining_fields`.
3. Validates the complete candidate again.
4. Records the transaction only after all validations pass.

Validation recovery may repeat until the candidate is valid.

---

# Completion Use Cases

## UC-24 — Record only after all required fields are populated

**Given**

At least one required field is missing.

**Then**

The workflow must not call the transaction service to create the transaction.

It asks for the first field in `remaining_fields`.

The transaction service is called only when:

```text
remaining_fields is empty
```

and candidate validation succeeds.

---

## UC-25 — Generate postings only after candidate completion

**Goal:** Keep conversational capture separate from ledger construction.

**Then**

The workflow does not incrementally create or modify ledger postings as messages arrive.

Postings are constructed only after:

* The candidate is complete.
* The candidate is valid.

The conversation operates on transaction-shaped fields rather than signed ledger postings.

---

## UC-26 — Close the session after successful creation

**Given**

The transaction service returns the created transaction.

**Then**

The workflow:

1. Produces a compact transaction summary.
2. Closes the active capture session.
3. Clears `candidate`, `remaining_fields`, and `requested_field` from active capture state.

Example:

> Recorded: $40 dinner expense from Cash for today.

---

## UC-27 — Do not close the session when creation fails

**Given**

The candidate passes workflow validation.

**When**

The transaction service fails to create the transaction.

**Then**

The workflow must not report the transaction as recorded.

### Product decision required

The specification does not define:

* Whether the session remains active.
* Whether the same candidate can be retried.
* Which errors should be exposed to the user.
* Whether service errors can invalidate a specific field.

A recommended baseline is to retain the candidate and keep the session active for retryable failures.

---

# Boundary and Unsupported Use Cases

The following scenarios are explicitly outside the first workflow design or lack defined behavior.

## UC-B01 — Split expense

Example:

> I spent $100 from Checking: $70 on groceries and $30 on household supplies.

Split-expense capture is outside MVP scope.

The workflow should not silently convert this into a single-category expense.

A product-level response policy is required.

---

## UC-B02 — Multi-currency transfer

Example:

> Transfer $100 from my USD account to my EUR account.

Multi-currency transfers are outside MVP scope.

The workflow must not record the transfer using equal minor-unit amounts across currencies.

---

## UC-B03 — Target-balance adjustment

Example:

> Set Cash to $500.

The current adjustment input model accepts a balance change rather than a target balance.

Supporting this request requires:

1. Reading the current account balance.
2. Calculating the difference between the current and target balances.
3. Capturing that difference as `balance_change_minor`.

This input form is deferred.

---

## UC-B04 — Refund, void, or transaction editing

Examples:

> Refund yesterday’s restaurant expense.

> Delete the transaction I just added.

> Change last week’s expense to $45.

Refunds, voiding, editing, and post-completion corrections are outside this workflow.

They should route to separate workflows rather than modifying a completed capture session.

---

## UC-B05 — Confirmation before recording

Example:

> Ask me to confirm every transaction before saving it.

Confirmation policy is outside the first workflow design.

The current completion rule records a valid complete candidate immediately.

---

# Unresolved Interaction Use Cases

The specification does not define the expected behavior for these cases. They should be resolved before finalizing conversational acceptance tests.

## UC-U01 — Cancel an active capture

Example:

> Never mind.

Required decision:

* Close the session without recording.
* Confirm cancellation or cancel immediately.
* Decide whether any candidate state is retained.

---

## UC-U02 — Start another transaction during active capture

Example:

```text
System: Which account did you use?
User: Also record a $500 salary payment.
```

Required decision:

* Replace the current capture.
* Suspend the current capture.
* Reject the new capture until the first finishes.
* Support multiple concurrent capture sessions.

The current `CaptureSession` model implies one active candidate but does not state the interruption policy.

---

## UC-U03 — Ambiguous account or category name

Example:

> Cash

when several accounts contain “Cash” in their names.

Required decision:

* Ask the user to disambiguate.
* Select an exact-name match.
* Apply a deterministic ranking policy.

The specification requires valid referenced entities but does not define entity-resolution behavior.

---

## UC-U04 — Unrecognized or unrelated answer

Example:

```text
System: Which account did you use?
User: What is my current balance?
```

Required decision:

* Answer the unrelated question and resume capture.
* Repeat the pending question.
* Pause or cancel the session.

---

## UC-U05 — Unsupported transaction type

Example:

> Record a loan repayment with principal and interest.

Required decision:

* Reject the request as unsupported.
* Map it to one MVP transaction.
* Route it to another workflow.

The workflow supports only expense, income, transfer, and adjustment.

---

## UC-U06 — Explicit negative expense, income, or transfer amount

Example:

> Record an expense of minus $20.

The model requires positive `amount_minor` magnitudes for expenses, income, and transfers.

Required decision:

* Reject the negative amount and request a positive magnitude.
* Infer a different transaction type.
* Treat the wording as a correction or refund request.

---

# Recommended MVP Acceptance Suite

The minimum acceptance suite should include these use cases:

```text
UC-01  Complete expense
UC-02  Complete income
UC-03  Complete transfer
UC-04  Positive and negative adjustment
UC-06  Expense with missing account
UC-07  Stable missing-field order
UC-08  Short answer interpretation
UC-09  Multi-field follow-up answer
UC-10  Multi-turn transfer
UC-11  Default date
UC-12  Date replacement
UC-13  Field correction
UC-15  Optional metadata
UC-16  Zero amount validation
UC-17  Invalid account validation
UC-18  Wrong spending category
UC-19  Wrong income category
UC-20  Same-account transfer
UC-21  Currency mismatch
UC-22  Invalid date
UC-23  Validation retry
UC-24  No premature recording
UC-25  Deferred posting construction
UC-26  Successful completion and session closure
```

Before implementing the unresolved cases, the product and engineering teams should define policies for cancellation, interruptions, entity ambiguity, transaction-service failures, and unsupported inputs.
