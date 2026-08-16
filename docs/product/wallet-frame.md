# Wallet Product Frame

Status: working product frame

This document defines the user situation, desired progress, and product principles that sit above

the current Wallet specification. It is intended to guide discovery, prioritization, scenario

design, and evaluation. It does not replace the behavior defined in

[the MVP specification](spec.md) or the vocabulary defined in [Wallet Concepts](concepts.md).

Where AI is used to support these jobs, its role and trust conditions are defined in the

[Wallet AI Capabilities Frame](ai-capabilities-frame.md).

The frame is intentionally independent of interface. A web form, an API, an import flow, and a

conversational assistant are different ways to help with the same product jobs. They should not

create different financial truths.

## Frame at a Glance

**Product promise:** Help a person know where their money is and keep that picture true as money

moves.

**Primary user context:** An individual manages money across several places, such as cash, bank

accounts, cards, and digital wallets. Their financial picture is fragmented, may span currencies,

and is easy to lose track of when records are incomplete.

**Progress the product enables:** The user can build a faithful map of those places, record why

balances changed, correct the record without erasing history, and return later to a state they can

understand and trust.

The current MVP tests whether this value can be delivered with manual accounts and a transaction

ledger before adding bank connections, imports, or richer financial planning.

## Primary Job to Be Done

> When my money is spread across several places and changes through everyday activity, help me
> maintain a trustworthy, current picture of where it is and how it changed, so I can make decisions
> without reconstructing everything from memory.

This job has three parts:

- **Situation:** Money is distributed across physical and digital places that do not provide one
  shared view.
- **Motivation:** The user wants to understand current balances and recent changes with less mental
  bookkeeping.
- **Desired outcome:** The Wallet record matches the user's understood reality and remains
  explainable over time.

The functional job is to maintain an accurate personal money record. The desired emotional outcome

is to feel oriented and in control rather than uncertain or behind. No social job is assumed in the

current frame because shared or public financial use has not been established.

### Forces around the job to validate

These forces are hypotheses for discovery, not findings from user research:

- **Push:** It is difficult to answer where money is or why a balance changed when information is
  split across apps, cash, cards, and memory.
- **Pull:** One understandable view could reduce repeated checking and mental reconstruction.
- **Anxiety:** Manual setup and capture may take more effort than the value returned, and one missing
  event may reduce trust in the whole record.
- **Existing habits:** People may rely on source-app balances, memory, notes, or spreadsheets and may
  return to those habits if Wallet is slower or less trustworthy.

## Supporting Jobs
### Build my money map

> When I start using Wallet or add a new place where money lives, help me represent it in a way I
> recognize, so my financial picture has the right coverage and starting point.

This includes naming an account, selecting its type and currency, setting its opening balance, and

giving it recognizable presentation metadata.

### Keep the record current

> When money enters, leaves, or moves between my accounts, help me record the movement correctly,
> so the balances stay current and I do not need to recalculate them myself.

Expenses, income, transfers, and balance adjustments are distinct events because they have

different meanings even when their effect on one balance looks similar.

### Understand what changed

> When I review an account or transaction, help me see what changed and why, so I can explain the
> current balance rather than merely accept a number.

The transaction history and spending or income classification support this job. The ledger is a

product trust mechanism, not only an implementation detail.

### Reconcile the record with reality

> When Wallet and reality disagree, help me correct the current state without hiding the
> correction, so I can trust both the balance and its history.

A balance adjustment is an explicit correction. It should not silently rewrite an opening balance

or an earlier transaction.

### Retire an account without losing context

> When I stop using an account, help me remove it from active use while preserving its history, so
> old transactions and prior decisions still make sense.

Archiving is therefore different from deletion.

### Shape classifications that fit my life

> When the default classifications do not match how I think about money, help me organize spending
> and income in familiar groups, so later review uses my language and distinctions.

Spending and income are separate classification families because they answer different questions.

## User Needs

| Need | Desired user outcome | Product implication |
| --- | --- | --- |
| Coverage | The places that matter can be represented | Account is broad enough for cash, cards, banks, and wallets |
| Current truth | Visible balances match recorded events | Balances derive from posted ledger entries |
| Meaning | Similar balance changes remain distinguishable | Expense, income, transfer, and adjustment stay separate |
| Explainability | A balance can be traced to understandable events | History is preserved and transaction details remain readable |
| Low maintenance effort | Keeping Wallet current is worth the effort | Common actions should require only necessary information |
| Control | Nothing financially meaningful happens invisibly | Proposed effects are clear and invalid actions fail safely |
| Recoverability | Mistakes can be corrected without corrupting history | Corrections are explicit and failed attempts do not create partial effects |
| Continuity | Inactive accounts do not break historical understanding | Archive instead of delete |
| Currency clarity | Amounts are never combined under a false equivalence | Currency remains explicit and totals stay separate unless FX is modeled |
| Personal fit | Classification reflects how the user reviews money | Spending and income trees can be maintained independently |

## Desired Outcomes

Wallet is doing its job when the user can:

- identify the active places where their money is held or spent from;
- see a current balance for each place in its own currency;
- record a real-world expense, income event, transfer, or correction with the intended effect;
- understand which event caused a balance to change;
- distinguish spending from movement between their own accounts;
- correct a mismatch without losing the fact that a correction happened;
- stop using an account without losing its history; and
- return later without having to reconstruct the Wallet state from memory.

The strongest product outcome is not the number of records created. It is whether the user can rely

on Wallet as a faithful, understandable representation of their money.

## Product Principles
### Financial truth before convenience

The product must not create a plausible but incorrect financial record. A blocked or corrective

interaction is better than a silently wrong balance or classification.

### Preserve causes, not only totals

A current balance is useful, but a balance whose causes are visible is more trustworthy and easier

to correct. Transactions remain the source of balance changes.

### Use user concepts at the product boundary

Users act on accounts, expenses, income, transfers, adjustments, and categories. Postings and

system-equity accounts support those concepts internally and should not become required user

knowledge.

### Make currency boundaries explicit

Amounts in different currencies are not one total unless an exchange model exists. The product

should preserve separate currency contexts rather than imply a conversion.

### Treat manual use as a complete mode

Manual accounts are the current product, not broken connected accounts. Future automation should

reduce maintenance effort without weakening control, explainability, or history.

### Keep channels consistent

The same user intent should produce the same valid domain effect regardless of whether it enters

through a form, API, import, or conversation. Channel-specific convenience must not change ledger

meaning.

### Do not manufacture confidence

The product should show recorded facts, state, and limitations. It should not label an account or a

financial situation as healthy, safe, or advisable without a defined and supported basis.

## Evaluation Anchors

Evaluations should begin with a user job and an observable outcome, not with the current screen,

endpoint, or model behavior. Each evaluation scenario should identify:

1. the user situation and intended job;
2. the relevant Wallet state before the action;
3. the minimum information available to the product;
4. the expected user-visible result;
5. the expected ledger or lifecycle effect, if any; and
6. effects that must not occur.

Cross-channel evaluations should use the same expected financial outcome even when the interaction

steps differ.

Useful evaluation dimensions derived from this frame are:

- **Coverage:** Can the product support the relevant account and money-movement situation?
- **Correctness:** Does it produce the intended balanced and currency-safe effect?
- **State fidelity:** Is the result grounded in the current accounts, categories, balances, and
  lifecycle state?
- **Meaning preservation:** Does it distinguish expense, income, transfer, and correction?
- **Effort:** Does the user provide only information needed for the job?
- **Control:** Is the effect understandable before or when it occurs?
- **Recoverability:** Can ambiguity, invalid input, and mistakes be resolved without unintended
  financial effects?
- **Continuity:** Do history and account identity remain understandable over time?
- **Scope honesty:** Does the product avoid implying unsupported advice, FX conversion, sync, or
  financial health judgments?

Financial correctness and absence of unintended effects are gates, not dimensions to trade against

polish. After those gates pass, evaluation should prioritize job completion and state fidelity,

then control and recoverability, then effort and presentation quality.

These are product-level anchors. A later evaluation design can turn them into weighted dimensions,

task suites, fixtures, and pass criteria for a particular surface.

## Product Boundaries

Wallet is currently a personal money record. It is not yet:

- a bank or payment initiator;
- an accounting system for a business;
- an investment valuation product;
- a credit-card statement and limit manager;
- a budgeting or financial advice system;
- a shared household permission system; or
- a currency conversion engine.

These boundaries prevent adjacent needs from silently redefining the primary job.

## Assumptions to Validate

The domain model is established in the current product base. The following product claims remain

working hypotheses until supported by user evidence:

- People with fragmented money locations experience enough uncertainty to maintain a separate
  Wallet record.
- A broad account abstraction matches how they think about cash, banks, cards, and digital wallets.
- Explainable ledger history creates enough trust to justify manual capture effort.
- Separate totals by currency are useful without a converted net-worth total.
- Separate two-level spending and income trees provide enough classification value for the MVP.
- Balance correction is a frequent and important part of maintaining a manual wallet.

## Open Product Questions

- Is the first durable value current balance awareness, transaction history, classification, or a
  combination of them?
- Which subset of accounts does a user consider important enough to maintain manually?
- How much transaction detail is useful before capture effort becomes too high?
- Should archived balances contribute to summaries and totals, or appear only in history?
- How should credit-card debt be presented before statement and limit workflows exist?
- When does a balance adjustment solve reconciliation, and when does it hide a missing transaction?
- Which category defaults and customization depth are sufficient for continued use?
- Which future automation reduces effort without reducing user understanding or control?

Answers to these questions should update this frame before they are converted into implementation

requirements or evaluation expectations.

## Using This Frame Upstream and Downstream

Use the documents in this order:

1. **Product frame:** establishes the user situation, jobs, needs, outcomes, and principles.
2. **AI capabilities frame, when applicable:** defines where AI may reduce effort and the trust
   conditions it must preserve.
3. **Product specification:** selects a product slice and defines its supported behavior.
4. **Concepts:** provides the shared vocabulary and domain meanings.
5. **Use cases and designs:** define how a particular surface helps complete the selected jobs.
6. **Evaluations:** test whether observable behavior produces the intended outcomes and respects the
   boundaries.
7. **Implementation:** realizes the behavior and provides evidence about feasibility and gaps.

Implementation can reveal that a frame or specification is incomplete, but current implementation

behavior alone should not become product intent.
