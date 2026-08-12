The attached prompt requires the taxonomy to stay query-level, observable from the user input or relevant message sequence, and tied to distinct AI behavior or failure modes. Hidden account/runtime state belongs in fixtures rather than the dimension model. It also explicitly favors a small set of strong, combinable dimensions over a broad communication taxonomy.

## A. Product interaction model
### Supported by the product materials

Wallet Assistant currently exposes five user-facing AI jobs:

1. Check current wallet balances.
2. Capture an expense.
3. Capture income.
4. Capture a transfer.
5. Capture a balance adjustment.

The four transaction jobs share a progressive capture flow. Natural-language turns update a reviewable transaction draft; ambiguous or unresolved fields cause corrective interactions; entity references may be normalized from aliases or typos; and the transaction is executed only through the guarded Confirm action. The wallet-state capability is read-only and returns current active-account balances separated by currency.

The transaction semantics are materially different. Expenses involve one account plus spending classification, income one account plus income classification, transfers two accounts and no categories, and adjustments change an account balance through an adjustment transaction.

Conversation behavior is also part of the AI surface. While idle, an LLM router chooses a capability. While transaction capture is active, ordinary messages continue to belong to that task; capability switching is unavailable until cancellation. Routing memory supports reference-only follow-ups such as `one more time`, while deliberately not authorizing replay of an earlier transaction.

The proposed Help page reinforces the intended user model: users may describe transactions "with as much information as is convenient," answer follow-up questions, and use everyday language. It also documents the important "one request at a time" ownership model. Because that document is explicitly marked **proposed**, I use it as supporting UX evidence rather than authoritative implementation behavior.

### Reasonable user-behavior hypotheses

Users will plausibly omit fields, narrate money movement rather than naming transaction types, use relative dates, shorten account names, make corrections, answer follow-up questions with fragments, repeat prior intentions, and combine requests. These hypotheses follow directly from the progressive conversational design, but individual phrasing distributions are not specified by the product materials.

### Not specified sufficiently

Several behaviors should not be baked into the taxonomy yet: account-specific balance queries versus the full wallet snapshot; unsupported non-wallet intents; whether one message containing two expenses should be split or rejected; exact alias semantics; and the complete set of transaction fields/defaults used to decide when a draft is confirmation-ready.

There is also a documentation boundary worth tracking: the current product spec explicitly names whole-message `help`, `cancel`, and `restart` controls, whereas the **proposed** Help page adds phrases such as `stop`, `never mind`, and `start over`. I would keep deterministic control parsing outside the AI-query dimension set and test it separately until those documents converge.

## B. Initial candidate dimensions

|Dimension|Candidate values|Query property represented|Failure surface|Keep for challenge?|
|---|---|---|---|---|
|User job|wallet state, expense, income, transfer, adjustment|Semantic operation the user wants|Wrong routing or wrong transaction interpretation|**Yes**|
|Transaction subtype|expense, income, transfer, adjustment|Type within capture|Wrong posting/category/account semantics|**Merge into User job**|
|Intent expression|named operation, event/action description, desired outcome/question, fragment|How directly the user exposes intent|Router/interpreter fails on natural indirect formulation|**Yes**|
|Information completeness|complete, incomplete, fragmentary|How much transaction information is supplied|Executes/advances prematurely or asks unnecessary questions|**Yes, refine**|
|Ambiguity|none, intent, field/reference|Whether multiple interpretations remain|Wrong inference instead of clarification|**Yes**|
|Correction / consistency|none, correction, contradiction|Multiple competing values and whether resolved|Uses superseded value or treats contradiction as correction|**Merge with ambiguity into determinacy**|
|Reference form|named, shorthand, noisy|Surface form of account/category references|Failure to normalize or interpret domain references|**Yes**|
|Context dependence|self-contained, contextual, reference-only|Whether meaning requires prior turns|Lost draft/context or invalid replay|**Yes**|
|Goal relation|independent, continue, repeat, switch|Relationship between current goal and previous goal|Wrong active-task ownership or replay behavior|**Yes**|
|Request multiplicity|single, multiple same-job, multiple cross-job|Number/type of requested operations|Router chooses one clause silently or capture merges transactions|**Yes**|
|Temporal expression|omitted, absolute, relative|Date wording|Relative-date normalization|**Query detail**|
|Money formatting|currency explicit/implicit; numeric formats|Amount/currency surface form|Amount normalization|**Query detail**|
|Exact control form|exact control, embedded control-like text|Deterministic command parsing|Wrongly intercepts ordinary text|**Separate deterministic suite**|
|Entity availability|exists, missing, archived|State of referenced entity|Selection/validation failure|**Reject: fixture**|
|Account-currency compatibility|compatible, conflicting|Runtime relationship between selected accounts/currency|Validation failure|**Reject: fixture**|
|Active-task state|idle, capture active|Runtime/conversation state|Routing behavior|**Reject as query dimension**; represent observable turn relation instead|

The last three exclusions are particularly important. Whether `"Main"` actually exists, whether two accounts share a currency, and whether the backend currently has an active task are execution/case conditions. Making them query dimensions would violate the boundary in the supplied prompt.

### Query details to vary without Cartesian-product dimensions

Relative versus absolute dates, currency-code versus symbol wording, numeric separators, merchant/reason phrases, specific category depth, exact account/category names, casing, punctuation, message length, and incidental typos outside references should vary naturally inside generated examples. They do not currently justify independent coverage axes.

## C. Behavioral user models

|User model|Observable behavior|Example queries|Dimensions stressed|
|---|---|---|---|
|Direct operator|Names the intended job|`Record an expense of ARS 4,500.` / `Show my balances.`|User job, expression, completeness|
|Event narrator|Reports what happened rather than naming the operation|`I paid ARS 4,500 for groceries from Cash.` / `Salary landed in Main today.`|Expression, job inference|
|Sparse recorder|Supplies only part of a transaction|`I spent 4,500.` / `Transfer 10,000 from Main.`|Information coverage|
|Uncertain/correcting user|Supplies alternatives or revises a value|`4,500--actually 5,400.` / `Main or Cash, I'm not sure.`|Determinacy|
|Shorthand/noisy referrer|Uses shortened or malformed references|`from MP` / `frm Mn Acct to Csh`|Reference surface|
|Context-heavy contributor|Answers with fragments or anaphora|`Cash.` / `Same category.` / `Make that 5,400.`|Context dependence, information coverage|
|Repeater/switcher|Refers to previous work or changes direction|`One more time.` / `Show my balances instead.`|Goal relation, context|
|Compound requester|Packs multiple operations into a message|`Record lunch and taxi.` / `Record lunch and show balances.`|Multiplicity, routing|

These are challenge models, rather than personas or dimensions themselves, consistent with the supplied methodology.

## D. Dimension-set challenge

| Difficult query                                                        | What it reveals                                                                                                                                                          |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `I spent ARS 4,500 from Cash on Food > Groceries yesterday.`           | Relative time is worth varying, but it does not warrant a separate top-level dimension.                                                                                  |
| `I spent ARS 4,500.`                                                   | Clear semantic intent can still be incomplete. Completeness and ambiguity must remain separate.                                                                          |
| `I spent either ARS 4,500 or ARS 5,400 from Cash on Food > Groceries.` | All major roles can be mentioned while one field remains ambiguous.                                                                                                      |
| `I spent 4,500--actually 5,400--from Cash on groceries.`               | Explicit correction has one final interpretation; classifying it as "contradictory" would lose an important behavior.                                                    |
| `It was definitely 4,500 and definitely 5,400 for the same purchase.`  | Genuine unresolved inconsistency needs different handling from correction.                                                                                               |
| `Mve 10k frm Mn Acct to Csh.`                                          | Semantic job and structure may be clear despite noisy references. Reference surface deserves independent coverage.                                                       |
| Previous capture exists -> `Make that 5,400.`                          | Context dependence and correction are independent: this is both contextual and resolved correction.                                                                      |
| Previous completed capture -> `One more time.`                         | Reference-only context needs routing-memory coverage, but should not imply transaction replay.                                                                           |
| Active expense capture -> `Show my balances instead.`                  | The wording itself is self-contained, yet it changes goals. Context dependence alone cannot represent the active-task failure surface. This motivates **Goal relation**. |
| `Record lunch for 4,500 from Cash and show my balances.`               | Cross-capability compounds stress idle routing differently from a single request.                                                                                        |
| `Record lunch for 4,500 and taxi for 3,000 from Cash.`                 | Multiple same-job operations stress the "one transaction/task" model differently from cross-capability compounds.                                                        |
| `What's my Cash balance?`                                              | The docs do not specify whether wallet-state requests can be scoped to one account. This should currently be an open product question rather than another dimension.     |

The main refinement is therefore to merge generic "ambiguity" and "correction/contradiction" into one **Interpretive determinacy** axis, while keeping completeness independent. I would also retain **Goal relation** separately from **Context dependence**: the active-task switch example demonstrates that a message can be entirely self-contained while still changing direction.

Reference _resolution_ should not be represented as `exact match / missing / ambiguous account`, because those labels require the catalog fixture. The retained dimension describes only the **surface form written by the user**.

## E. Revised dimension set

This is the proposed **v1**.

| Dimension                             | Definition                                                                                                              | Values                                                                                                                                                                                                     | Applies when                                                 | Why it matters                                                                                                            |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| **User job**                          | Semantic Wallet job requested by the user.                                                                              | `wallet_state`, `expense`, `income`, `transfer`, `adjustment`. Compound queries may carry a set; unresolved intent may carry candidate labels.                                                             | All ordinary task-oriented inputs                            | Primary router/interpreter distinction. The five values correspond directly to supported user jobs.                       |
| **Intent expression**                 | How the current message linguistically communicates its intended job.                                                   | `job_explicit` -- "Record an expense"; `event_or_action` -- "I paid 20", "Move 20 from A to B"; `outcome_or_question`-- "What are my balances?", "Set Cash to 25k"; `fragment` -- "Cash", "5,400 instead". | All ordinary messages                                        | Exercises routing and interpretation across direct, inferred, and elliptical formulations.                                |
| **Current-turn information coverage** | How much of the job-specific transaction information is explicitly supplied in the current contribution.                | `full`, `partial`, `fragment`. Example: full transfer states amount/source/destination; partial omits destination; fragment supplies only `Cash`.                                                          | Transaction-capture jobs only                                | Exercises progressive collection versus premature inference.                                                              |
| **Interpretive determinacy**          | Whether the input yields one coherent semantic interpretation, and if not, how it fails to do so.                       | `clear`; `resolved_correction` -- "20--actually 30"; `intent_ambiguous`; `field_ambiguous` -- "Main or Cash"; `contradictory` -- incompatible assertions with no winner.                                   | All ordinary messages                                        | Separates clarification behavior from valid correction and prevents silent arbitrary choices.                             |
| **Reference surface**                 | Observable textual form used for account/category references, without judging whether that reference actually resolves. | `none`; `named_phrase` -- "Main account"; `shorthand` -- "MP"; `noisy` -- "Mrcdo Pgo"; `mixed`.                                                                                                            | Queries containing domain references                         | The interpreter explicitly supports normalization/selection from aliases and typos.                                       |
| **Context dependence**                | How much semantic content must be recovered from previous conversation turns.                                           | `self_contained`; `context_linked` -- "same account", "make that 30"; `reference_only` -- "one more time", `Cash`as a follow-up answer.                                                                    | All messages/sequences                                       | Exercises draft continuity and bounded routing memory.                                                                    |
| **Goal relation**                     | Relationship between the current intended job and the preceding conversational goal.                                    | `independent`; `continue`; `repeat`; `switch`.                                                                                                                                                             | Conversational sequences; `independent` for standalone input | Captures repeat semantics and the product rule that ordinary messages cannot switch capabilities while capture is active. |
| **Request multiplicity**              | Whether one message asks for one operation or multiple operations.                                                      | `single`; `multiple_same_job`; `multiple_cross_job`.                                                                                                                                                       | All task-oriented messages                                   | Tests one-task-at-a-time behavior and whether routing/capture silently drops or merges clauses.                           |

I would deliberately avoid adding more dimensions for v1. The attached prompt specifically asks for dimensions that support meaningful combinations and distinct failure surfaces, rather than every property that can vary.

## G. Validation sample

This is a taxonomy stress test, not the evaluation dataset itself.

Abbreviations below: **J** = User job, **X** = Intent expression, **C** = Information coverage, **D** = Determinacy, **R** = Reference surface, **K** = Context dependence, **G** = Goal relation, **M** = Multiplicity.

| #   | User input / sequence                                                               | J                       | X                   | C        | D                   | R               | K               | G           | M                  |
| --- | ----------------------------------------------------------------------------------- | ----------------------- | ------------------- | -------- | ------------------- | --------------- | --------------- | ----------- | ------------------ |
| 1   | `Show my current balances.`                                                         | wallet_state            | job_explicit        | --       | clear               | none            | self_contained  | independent | single             |
| 2   | `How much money do I have right now?`                                               | wallet_state            | outcome_or_question | --       | clear               | none            | self_contained  | independent | single             |
| 3   | `I spent ARS 4,500 from Cash on Food > Groceries yesterday.`                        | expense                 | event_or_action     | full     | clear               | named_phrase    | self_contained  | independent | single             |
| 4   | `Record an expense of ARS 4,500.`                                                   | expense                 | job_explicit        | partial  | clear               | none            | self_contained  | independent | single             |
| 5   | `I received ARS 120,000 into Main under Salary > Payroll.`                          | income                  | event_or_action     | full     | clear               | named_phrase    | self_contained  | independent | single             |
| 6   | `Move ARS 10,000 from Main to Cash.`                                                | transfer                | event_or_action     | full     | clear               | named_phrase    | self_contained  | independent | single             |
| 7   | `Set Cash balance to ARS 25,000.`                                                   | adjustment              | outcome_or_question | full     | clear               | named_phrase    | self_contained  | independent | single             |
| 8   | `I spent either ARS 4,500 or 5,400 from Cash on Food > Groceries.`                  | expense                 | event_or_action     | full     | field_ambiguous     | named_phrase    | self_contained  | independent | single             |
| 9   | `I spent 4,500--actually 5,400--from Cash on Food > Groceries.`                     | expense                 | event_or_action     | full     | resolved_correction | named_phrase    | self_contained  | independent | single             |
| 10  | `It was definitely 4,500 and definitely 5,400 for the same purchase.`               | expense*                | event_or_action     | partial  | contradictory       | none            | context_linked* | continue*   | single             |
| 11  | `Mve 10k frm Mn Acct to Csh.`                                                       | transfer                | event_or_action     | full     | clear               | noisy           | self_contained  | independent | single             |
| 12  | `Record ARS 4,500 lunch from MP as Food > Dining.`                                  | expense                 | event_or_action     | full     | clear               | mixed/shorthand | self_contained  | independent | single             |
| 13  | Prior expense draft -> `Cash.`                                                      | expense                 | fragment            | fragment | clear               | named_phrase    | reference_only  | continue    | single             |
| 14  | Prior expense amount 4,500 -> `Make that 5,400.`                                    | expense                 | fragment            | fragment | resolved_correction | none            | context_linked  | continue    | single             |
| 15  | Prior completed transfer -> `One more time.`                                        | transfer                | fragment            | fragment | clear               | none            | reference_only  | repeat      | single             |
| 16  | Active expense capture -> `Show my balances instead.`                               | wallet_state            | job_explicit        | --       | clear               | none            | self_contained  | switch      | single             |
| 17  | `Record ARS 4,500 lunch from Cash as Food > Dining and show my balances.`           | {expense, wallet_state} | job_explicit        | full†    | clear               | named_phrase    | self_contained  | independent | multiple_cross_job |
| 18  | `I spent 4,500 from Cash on Food > Dining and 3,000 from Cash on Transport > Taxi.` | expense                 | event_or_action     | full     | clear               | named_phrase    | self_contained  | independent | multiple_same_job  |
| 19  | `I moved ARS 10,000 out of Cash.`                                                   | {expense?, transfer?}   | event_or_action     | partial  | intent_ambiguous    | named_phrase    | self_contained  | independent | single             |

* #10 needs prior context to establish that the values refer to an expense; without it, even the job can become ambiguous. This is expected rather than a taxonomy failure.

† For compound requests, coverage should be assessed per transaction clause during actual dataset construction rather than collapsed into a single boolean.

### Sanity-check result

The examples classify without needing account existence, currency compatibility, archived status, current database contents, or other hidden state. That is the key boundary required by the prompt.

Two overlaps are intentional but independent. `resolved_correction` may coexist with either self-contained input (#9) or contextual input (#14), showing that determinacy and context are separate. Likewise, a self-contained query can still represent a goal switch (#16), demonstrating why Goal relation cannot be replaced by Context dependence.

The least crisp values are `event_or_action` versus `outcome_or_question`, and `shorthand` versus `noisy`. I would keep them for v1 because both correspond to plausible interpretation failures, then collapse them later if empirical eval results show no meaningful separation.

## H. Final assessment

**The set is ready for v1 tuple construction.** Eight dimensions is a reasonable starting size: each has a product-grounded failure surface, and the challenge examples show useful cross-combinations without requiring hidden application state.

The most provisional dimensions are **Intent expression**, **Reference surface**, and **Goal relation**. Their usefulness should be validated empirically once the first synthetic dataset and evaluator failures exist. **User job**, **Information coverage**, **Interpretive determinacy**, **Context dependence**, and **Request multiplicity** have stronger direct grounding in the current interaction architecture.

Before locking the tuple schema, four product questions could materially change it: the exact capture fields/defaults that define `full` versus `partial`; behavior for multiple transactions of the same type in one message; behavior for unsupported or genuinely out-of-scope idle requests; and whether `wallet.current_state` should understand account-scoped questions or always answer with the full snapshot. The current docs also leave the proposed control-synonym expansion unresolved relative to the authoritative spec.
