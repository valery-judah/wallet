# Contribution Processing Research

Status: historical research snapshot

Current contract: [Transaction Interpretation Contract](../evergreen/transaction-interpretation-contract.md)

This research predates the unified model-driven interpreter. Its extraction, grounding, and

dialogue-state alternatives explain the design space but do not describe the current pipeline.

Your problem fits **task-oriented language understanding**: convert conversational text into a typed, grounded, executable transaction candidate while maintaining state across turns.

The closest established fields are:

* **NLU / spoken-language understanding:** intent classification and slot filling.
* **Information extraction:** entity, relation, and event extraction.
* **Semantic parsing:** conversion from text into a formal domain representation.
* **Dialogue state tracking:** maintaining the evolving interpretation across messages.
* **Entity linking / grounding:** resolving textual mentions to records in your system.
* **Dialogue policy:** deciding whether to ask a question, validate, confirm, or execute.

Your current workflow already implements part of the dialogue-state and dialogue-policy layers through `candidate`, `remaining_fields`, and `requested_field`.

## 1. NLP, NLU, and semantic parsing

These terms overlap, but it is useful to distinguish them architecturally.

### NLP

**Natural Language Processing** is the broad field. It includes:

* tokenization;
* part-of-speech tagging;
* syntactic parsing;
* named entity recognition;
* classification;
* information extraction;
* summarization and generation.

Many traditional NLP components produce linguistic structure but do not directly tell the wallet what operation to perform.

For example:

```text
"Transfer $100 from Checking to Savings tomorrow"
```

A linguistic parser might identify:

```text
verb: transfer
direct object: $100
source prepositional phrase: from Checking
destination prepositional phrase: to Savings
temporal modifier: tomorrow
```

That structure is useful, but still needs to be translated into wallet semantics.

### NLU

**Natural Language Understanding** usually refers to producing a task-oriented representation of the user's meaning.

A classic NLU representation is:

```json
{
  "intent": "create_transfer",
  "slots": {
    "amount": "$100",
    "source_account": "Checking",
    "destination_account": "Savings",
    "date": "tomorrow"
  }
}
```

Intent classification and slot filling are commonly treated either as independent models or as a joint prediction problem. Joint models can exploit the relationship between the utterance-level intent and token-level slots. ([ACL Anthology][1])

### Semantic parsing

**Semantic parsing** goes further and maps language into a machine-readable formal representation, such as:

```text
Transfer(
    amount = Money(100, inferred_currency),
    source = AccountRef("Checking"),
    destination = AccountRef("Savings"),
    occurred_on = RelativeDate(TOMORROW)
)
```

Or directly into your domain schema:

```json
{
  "type": "transfer",
  "amount_minor": 10000,
  "source_account_ref": "Checking",
  "destination_account_ref": "Savings",
  "occurred_on": "2026-08-06"
}
```

Semantic parsing is conventionally defined as translating natural-language utterances into machine-readable meaning representations or executable logical forms. ([ACL Anthology][2])

For your use case, semantic parsing is a useful conceptual model, but the parser should generally produce a **proposed interpretation**, rather than immediately modifying persistent transaction state.

## 2. The important distinction: extraction, normalization, and grounding

These are separate problems.

Consider:

```text
"I spent fifty at Starbucks from my daily card yesterday."
```

### Extraction

Find mentions and assign semantic roles:

```json
{
  "transaction_type": "expense",
  "amount_text": "fifty",
  "merchant_text": "Starbucks",
  "account_text": "my daily card",
  "date_text": "yesterday"
}
```

### Normalization

Convert surface forms into canonical values:

```json
{
  "amount_minor": 5000,
  "merchant_name": "Starbucks",
  "relative_date": {
    "operator": "days_before",
    "value": 1
  }
}
```

### Grounding

Resolve mentions against system data and runtime context:

```json
{
  "account_id": "acc_82b17",
  "occurred_on": "2026-08-04",
  "currency": "USD"
}
```

"Daily card" is not a conventional named entity. It is a user-specific reference that must be linked to one of the user's accounts.

This means generic NER alone is insufficient. The more relevant tasks are:

* slot filling;
* semantic role extraction;
* entity linking;
* ontology grounding;
* dialogue state tracking.

## 3. Common implementation approaches
### 3.1 Rules, patterns, and grammars

This includes:

* regular expressions;
* keyword tables;
* parsing combinators;
* finite-state grammars;
* dependency-tree rules;
* deterministic date and money parsers.

Example:

```text
transfer <amount> from <account> to <account>
spent <amount> on <category>
increase <account> by <amount>
```

A rule may produce:

```json
{
  "type": "transfer",
  "amount": "$100",
  "source_account": "Checking",
  "destination_account": "Savings"
}
```

**Advantages**

* deterministic and explainable;
* high precision for anticipated expressions;
* inexpensive to run;
* easy to connect to business rules;
* suitable for money, dates, account aliases, and command-like inputs.

**Limitations**

* linguistic coverage grows slowly;
* rules interact in unexpected ways;
* corrections, ellipsis, and indirect phrasing are difficult;
* multilingual support requires substantial additional work;
* maintenance becomes expensive as the grammar grows.

Rules remain valuable inside a larger system, especially for normalization and validation.

### 3.2 Classical statistical NLP

Historically, systems used:

* logistic regression or support vector machines for intent classification;
* hidden Markov models and conditional random fields for sequence labeling;
* hand-designed lexical and syntactic features;
* gazetteers containing known merchants, accounts, or categories.

A slot-filling model assigns labels to tokens:

```text
Transfer    O
$100        B-AMOUNT
from        O
Checking    B-SOURCE_ACCOUNT
to          O
Savings     B-DESTINATION_ACCOUNT
```

This is commonly called **BIO** or **IOB sequence tagging**.

**Advantages**

* relatively lightweight;
* predictable latency;
* can work well with sufficient annotated domain data;
* provides token-level spans.

**Limitations**

* requires feature engineering in older variants;
* weak handling of long-range dependencies;
* usually needs separate normalization and grounding;
* difficult to generalize to new slot types without retraining.

This approach is still reasonable where model size, latency, or deployment constraints dominate.

### 3.3 Neural sequence models

Neural slot-filling systems commonly evolved through:

* recurrent neural networks;
* BiLSTM-CRF models;
* attention-based models;
* pretrained transformer encoders such as BERT-family models.

The model may jointly predict:

```json
{
  "intent": "create_expense",
  "token_labels": [
    ["Spent", "O"],
    ["$40", "B-AMOUNT"],
    ["on", "O"],
    ["dinner", "B-SPENDING_CATEGORY"]
  ]
}
```

Transformer models generally provide stronger contextual representations than traditional feature-based models. Intent classification and slot filling can be trained separately, jointly, or through transfer learning. ([ACL Anthology][1])

**Advantages**

* good accuracy with an appropriate labeled dataset;
* fast and relatively deterministic at inference time;
* easier to calibrate than free-form generative models;
* supports token-level span evaluation;
* can be deployed locally.

**Limitations**

* requires an annotated corpus;
* schema changes typically require training changes;
* awkward for nested, overlapping, or implicit values;
* does not inherently perform entity linking;
* conversation context must be explicitly incorporated.

This is often the strongest approach when the domain is stable and large quantities of representative training data are available.

### 3.4 Generative semantic parsing

A generative model produces a structured meaning representation:

```json
{
  "operation": "capture_transaction",
  "transaction": {
    "type": "expense",
    "amount": {
      "value": 40,
      "currency": null
    },
    "account": null,
    "spending_category": "dinner",
    "occurred_on": {
      "kind": "default",
      "value": "today"
    }
  }
}
```

The representation can be:

* JSON;
* a domain-specific language;
* an abstract syntax tree;
* a function call;
* a logical form;
* a sequence of state-update operations.

**Advantages**

* handles flexible phrasing;
* can emit multiple related fields at once;
* supports implicit semantics;
* adapts more easily to schema descriptions;
* few-shot prompting can reduce initial data requirements.

**Limitations**

* generated structures may be syntactically invalid;
* models may invent values;
* field omission and semantic drift are possible;
* confidence is difficult to calibrate;
* unrestricted output creates execution risk.

Grammar-constrained decoding can guarantee that output follows a defined structural grammar, although structural validity alone does not guarantee semantic correctness. ([arXiv][3])

### 3.5 LLM-based structured extraction

This is the contemporary variant of generative semantic parsing. An LLM receives:

* the current message;
* recent conversation history;
* the transaction schema;
* field descriptions;
* current requested field;
* possibly lists of available accounts and categories.

It emits a schema-constrained object:

```json
{
  "transaction_type": "expense",
  "field_updates": [
    {
      "field": "amount_minor",
      "value": 4000,
      "source_text": "$40"
    },
    {
      "field": "spending_category_ref",
      "value": "dinner",
      "source_text": "dinner"
    }
  ]
}
```

LLMs have become a major generative approach to information extraction, but reliable structured output, factual fidelity, and schema adherence remain explicit engineering concerns. ([arXiv][4])

The main design rule is:

> Treat LLM output as an untrusted interpretation proposal, not as a valid transaction.

The application must still perform:

* schema validation;
* type validation;
* account and category lookup;
* currency checks;
* date validation;
* authorization checks;
* transaction-service validation.

### 3.6 Dialogue state tracking

Single-message NLU is insufficient for your workflow:

```text
System: Which account did you use?
User: Cash
```

"Cash" has little standalone meaning. It becomes `account_id` because the current dialogue state says:

```text
requested_field = account_id
```

Tracking user goals and slot values over conversation history is the established task of **dialogue state tracking**, or DST. DST systems may use fixed ontologies, dynamic schemas, classification, sequence generation, or text-to-text state representations. ([ACL Anthology][5])

Your `CaptureSession` is effectively a compact dialogue state:

```text
DialogueState
- candidate
- remaining_fields
- requested_field
```

The workflow document already specifies several DST behaviors:

* values accumulate across turns;
* new messages may fill multiple fields;
* values may be replaced;
* short answers are interpreted using `requested_field`;
* missing fields determine the next system action.

### 3.7 End-to-end task-oriented dialogue

An end-to-end system attempts to learn the complete mapping:

```text
conversation history
    → transaction state
    → next system response or action
```

This can combine NLU, state tracking, dialogue policy, and response generation in one model.

**Advantages**

* fewer hand-defined boundaries;
* potentially better use of full conversational context;
* less duplicated representation.

**Limitations**

* difficult to inspect and debug;
* business constraints may become implicit;
* harder to guarantee action safety;
* failures cannot be easily attributed to extraction, grounding, state update, or policy;
* training and evaluation are more complex.

Task-oriented dialogue systems are commonly described either as modular pipelines--NLU, state tracking, policy, and generation--or as end-to-end architectures. ([ACL Anthology][6])

For financial transaction capture, a fully end-to-end executable architecture would usually provide insufficient control.

## 4. A phased architecture for the wallet

A useful separation is:

```text
User text
    ↓
1. Linguistic and domain extraction
    ↓
2. Semantic interpretation
    ↓
3. System grounding
    ↓
4. Dialogue-state reduction
    ↓
5. Candidate validation
    ↓
6. Dialogue policy or execution
```

### Phase 1: Extract mentions

Input:

```text
"Move fifty from my main card to cash tomorrow"
```

Output:

```json
{
  "operation_mention": "Move",
  "amount_mention": "fifty",
  "source_mention": "my main card",
  "destination_mention": "cash",
  "date_mention": "tomorrow"
}
```

This phase should preserve the source text. It should avoid committing to account IDs.

### Phase 2: Produce a semantic interpretation

```json
{
  "transaction_type": "transfer",
  "arguments": {
    "amount": {
      "magnitude": 50,
      "currency": null
    },
    "source_account_ref": "my main card",
    "destination_account_ref": "cash",
    "occurred_on_ref": {
      "type": "relative_date",
      "offset_days": 1
    }
  }
}
```

This layer interprets:

* "move" as a transfer;
* "from" as the source role;
* "to" as the destination role;
* "fifty" as a monetary magnitude.

### Phase 3: Ground against system context

The resolver receives:

```text
User accounts:
- Everyday Visa, alias "main card", USD
- Cash, USD
- Euro Cash, EUR
```

It resolves:

```json
{
  "source_account_id": "acc_everyday_visa",
  "destination_account_id": "acc_cash_usd",
  "amount_minor": 5000,
  "occurred_on": "2026-08-06"
}
```

Potentially ambiguous links should remain unresolved:

```json
{
  "destination_account": {
    "status": "ambiguous",
    "candidates": [
      "acc_cash_usd",
      "acc_cash_eur"
    ]
  }
}
```

### Phase 4: Apply a state update

Rather than letting the parser construct the authoritative candidate, produce a patch:

```json
{
  "set": {
    "type": "transfer",
    "amount_minor": 5000,
    "source_account_id": "acc_everyday_visa",
    "destination_account_id": "acc_cash_usd",
    "occurred_on": "2026-08-06"
  },
  "clear": []
}
```

A deterministic reducer applies this to the current session.

```text
new_candidate = reduce(old_candidate, interpreted_patch)
```

This gives you explicit overwrite and correction semantics.

### Phase 5: Validate

Validation remains deterministic:

```text
source account exists
destination account exists
source != destination
both accounts active
currencies match
amount > 0
date accepted
```

These checks are already defined in the workflow.

### Phase 6: Choose the next action

```text
if interpretation is ambiguous:
    ask a disambiguation question
else if remaining_fields is non-empty:
    ask for requested_field
else if validation fails:
    clear invalid field and ask again
else:
    create transaction
```

This is dialogue policy, even when implemented as deterministic application logic.

## 5. A useful intermediate representation

The current candidate stores only the accepted field values. The workflow explicitly excludes confidence, provenance, explicit-versus-inferred status, previous values, and correction metadata.

That is reasonable for the authoritative candidate. Those concerns can be represented in a separate interpretation object:

```typescript
type Interpretation = {
  operation: "capture_transaction" | "other";
  proposedType?: TransactionType;

  fieldHypotheses: FieldHypothesis[];

  ambiguities: Ambiguity[];
  unsupportedClaims: UnsupportedClaim[];
};

type FieldHypothesis = {
  field: CandidateField;
  value: unknown;

  sourceSpan?: {
    start: number;
    end: number;
    text: string;
  };

  origin:
    | "explicit"
    | "contextual"
    | "normalized"
    | "defaulted"
    | "inferred";

  confidence?: number;
};

type Ambiguity = {
  field: CandidateField;
  candidates: unknown[];
  reason: string;
};
```

The state reducer decides which hypotheses may be accepted.

This preserves a clean separation:

```text
Interpretation = what the NLU system believes the user meant
Candidate      = values currently accepted by the workflow
Transaction    = validated domain object created by the service
```

## 6. Wallet entity categories

For your schema, I would classify values into four groups.

### Closed-set semantic values

Examples:

```text
type = expense | income | transfer | adjustment
```

Use classification or constrained generation.

### Normalizable scalar values

Examples:

```text
amount_minor
balance_change_minor
occurred_on
```

Use extraction followed by deterministic normalization.

### User-specific references

Examples:

```text
account_id
source_account_id
destination_account_id
spending_category_id
income_category_id
```

Use mention extraction followed by entity linking against the user's accessible records.

### Free-text values

Examples:

```text
description
merchant_name
notes
```

Use span extraction or generative extraction, with length and content constraints.

The distinction matters because each type needs a different evaluation and acceptance policy.

## 7. Recommended implementation family

For this wallet workflow, the most practical architecture is a **hybrid modular system**:

```text
LLM or transformer semantic extractor
        +
deterministic money/date normalization
        +
retrieval-based account/category linking
        +
deterministic dialogue-state reducer
        +
transaction-domain validation
        +
explicit dialogue policy
```

A reasonable first implementation would be:

1. Use schema-constrained LLM extraction to generate field hypotheses.
2. Parse money and dates again with deterministic normalizers.
3. Resolve account and category references against user-specific data.
4. apply updates through a deterministic state reducer;
5. compute `remaining_fields` using the existing workflow;
6. validate exclusively through application and transaction-service rules;
7. ask questions for missing or ambiguous values;
8. execute only once the candidate is complete and valid.

Rules can handle common high-confidence forms before invoking a larger model:

```text
"35" when requested_field = amount_minor
"Cash" when requested_field = account_id
"today", "yesterday", "tomorrow"
"$45", "45 dollars", "forty-five"
```

The semantic model handles the broader language:

```text
"I grabbed dinner for 40 using cash"
"Move a hundred out of checking and into savings"
"My cash balance should go up by fifty"
```

## 8. Evaluation should be layered

A single end-to-end success metric will make diagnosis difficult.

Measure at least:

| Layer                    | Useful metric                       |
| ------------------------ | ----------------------------------- |
| Transaction type         | Classification accuracy             |
| Mention extraction       | Span precision, recall, F1          |
| Field extraction         | Per-field precision, recall, F1     |
| Complete interpretation  | Exact-match accuracy                |
| Account/category linking | Top-1 and top-k accuracy            |
| Dialogue state           | Joint state or joint goal accuracy  |
| Clarification            | Unnecessary-question rate           |
| Execution                | Correctly recorded transaction rate |
| Safety                   | Incorrect automatic-execution rate  |
| Calibration              | Accuracy by confidence band         |

For a financial workflow, **precision at the execution boundary** should receive more weight than raw extraction recall. An uncertain interpretation should produce a clarification question rather than an incorrect transaction.

The conceptual model I would use going forward is:

```text
NLP extraction
    → semantic frame
    → system-grounded interpretation
    → proposed candidate patch
    → dialogue-state update
    → deterministic validation and execution
```

This gives you a modular path from existing NLU techniques to the `TransactionCandidate` and `CaptureSession` abstractions already defined in your workflow.

[1]: https://aclanthology.org/2020.coling-main.42/?utm_source=chatgpt.com "Recent Neural Methods on Slot Filling and Intent Classification for Task-Oriented Dialogue Systems: A Survey - ACL Anthology"

[2]: https://aclanthology.org/N19-2003/?utm_source=chatgpt.com "Practical Semantic Parsing for Spoken Language Understanding - ACL Anthology"

[3]: https://arxiv.org/abs/2305.13971?utm_source=chatgpt.com "Grammar-Constrained Decoding for Structured NLP Tasks without Finetuning"

[4]: https://arxiv.org/abs/2312.17617?utm_source=chatgpt.com "Large Language Models for Generative Information Extraction: A Survey" ([[xu-2024-llms-generative-information-extraction-survey.pdf|PDF]])

[5]: https://aclanthology.org/2022.sigdial-1.33/?utm_source=chatgpt.com ""Do you follow me?": A Survey of Recent Approaches in Dialogue State Tracking - ACL Anthology"

[6]: https://aclanthology.org/anthology-files/anthology-files/pdf/emnlp/2023.emnlp-main.363.pdf?utm_source=chatgpt.com "End-to-end Task-oriented Dialogue: A Survey of ..."

## Library sources

- [[jurafsky-2025-speech-and-language-processing-3e-draft.pdf|Jurafsky and Martin 2025]], *Speech and Language Processing, 3rd Edition*
- [[jurafsky-2026-slp3-appendix-k-frame-based-dialogue.pdf|Jurafsky and Martin 2026]], *SLP3 Appendix K: Frame-Based Dialogue Systems*
- [[lee-2025-nlp-textbook-with-python.pdf|Lee 2025]], *Natural Language Processing* ([doi:10.1007/978-981-96-3208-4](https://doi.org/10.1007/978-981-96-3208-4))
