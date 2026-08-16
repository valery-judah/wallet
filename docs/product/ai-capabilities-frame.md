# Wallet AI Capabilities Frame

Status: working product frame

This document defines where AI can help Wallet users, what value it must create, and the trust and
control conditions it must respect. It is subordinate to the [Wallet Product Frame](wallet-frame.md):
AI supports the same product jobs and must not create a different financial truth.

This frame sits above the current behavior in [the MVP specification](spec.md) and the technical
contracts in `docs/evergreen/`. Shared assistant-facing and technical terms are defined in
[Wallet AI Concepts](ai-concepts.md). This frame is not a model, prompt, conversation, or
architecture specification.

## Frame at a Glance

**AI capability promise:** Let a person express a Wallet need in their own words and receive a
grounded answer or reviewable action with less translation effort, without giving up control of
their financial record.

**Role of AI:** AI interprets variable human language and helps shape it into a bounded Wallet
task. Wallet data and deterministic domain rules remain authoritative for facts, validity, and
financial effects.

**Product thesis:** AI is valuable where the user's intent is easy to say but tedious to translate
into product fields, references, and steps. It is not valuable merely because an interaction can
be conversational. A direct control remains preferable when it is clearer or faster.

**Baseline:** Manual Wallet use is a complete mode. AI must earn its place by reducing effort while
preserving or improving correctness, explainability, and control.

## Primary AI-Enabled Job to Be Done

> When I have a money event to record or a question about my Wallet, but translating it into the
> product's exact structure would slow me down, help me express it naturally and turn it into a
> grounded answer or reviewable action, so I can maintain and understand my Wallet with less effort
> and without surrendering control.

This job has three parts:

- **Situation:** The user understands their real-world intent but may not know the required fields,
  product terms, exact labels, or interaction path.
- **Motivation:** The user wants to capture or understand something while it is present in mind,
  with less navigation and translation work.
- **Desired outcome:** The product correctly connects the user's language to current Wallet state,
  makes uncertainty and consequences visible, and completes only the intended job.

The functional job is to reduce the work between an expressed intent and a valid Wallet outcome.
The desired emotional outcome is to feel assisted and in control, not impressed by fluent behavior
or uncertain about what the system understood.

### Forces around the job to validate

These are hypotheses for discovery, not findings from user research:

- **Push:** Structured forms and navigation make the user translate a familiar money event into the
  product's vocabulary and required fields.
- **Pull:** Natural language can preserve the user's own shorthand, accept details in any order, and
  ask only for what is missing.
- **Anxiety:** A fluent assistant may choose the wrong account, amount, transaction type, category,
  or action while appearing confident.
- **Anxiety:** The user may not know whether an answer came from their Wallet, an assumption, or
  general model knowledge.
- **Existing habits:** The user may prefer a form, postpone capture, rely on memory, or check source
  apps directly when conversation takes too many turns or feels less predictable.

## Supporting Jobs

### Express intent without learning the schema

> When I know what happened in everyday terms, help me state it without translating it into Wallet
> fields first, so capture does not interrupt the activity I am trying to remember.

The user may provide details in any order, use shorthand, make a typo, or omit information that is
not yet known.

### Connect my words to my Wallet

> When I refer to one of my accounts or categories in familiar language, help me connect that
> reference to the right current Wallet entity, so the result reflects my actual setup.

Grounding is part of the product value. A linguistically plausible response that is disconnected
from the user's Wallet has not completed the job.

### Resolve only the uncertainty that matters

> When my request is incomplete or ambiguous, help me understand what is needed and ask a focused
> question, so I can continue without starting over or filling unnecessary fields.

The product should retain valid contributions, expose meaningful ambiguity, and avoid asking for
information that does not affect the outcome.

### Review the understood action

> Before my financial record changes, show me what the product understood and what it will do, so I
> can correct or reject it before it becomes part of my history.

Natural-language agreement is not sufficient authority for a write. Confirmation is a distinct,
guarded product action.

### Ask for a grounded Wallet answer

> When I need to orient myself, let me ask in my own words and receive an answer based on the
> current Wallet record, so I do not have to find and assemble the relevant state myself.

An answer must distinguish recorded facts from limitations or unsupported interpretation.

### Recover without unintended effects

> When I change my mind, correct myself, or the assistant cannot complete the task, let me cancel,
> restart, or retry safely, so conversation failure does not become financial damage.

## User Needs

| Need | Desired user outcome | Product implication |
| --- | --- | --- |
| Natural expression | I can describe the job in familiar words and shorthand | Interpretation accepts varied wording and detail order |
| Grounding | The result refers to my real, current Wallet state | Models may select only available, safely exposed references |
| Progressive help | I supply missing information without repeating valid details | Task state retains valid contributions and asks focused questions |
| Visible understanding | I can tell what the product inferred or selected | Answers and previews expose the material interpretation |
| Control | A financial write occurs only when I deliberately approve it | Drafting and execution are separate, with guarded confirmation |
| Correctness | Convenience never weakens ledger or currency rules | Deterministic Wallet validation remains authoritative |
| Recoverability | I can correct, cancel, restart, or retry safely | Failed or abandoned interactions create no partial financial effect |
| Scope clarity | I know what the assistant can and cannot do | Unsupported jobs are identified without invented answers or actions |
| State freshness | An answer or action uses relevant current state | Read and write paths validate against authoritative state at use time |
| Low effort | Conversation removes more work than it adds | Ask only outcome-relevant questions and avoid unnecessary turns |
| Privacy restraint | Only task-relevant financial context is exposed | Capabilities receive the minimum state needed for their bounded job |
| Channel choice | I can use a direct interaction when it serves me better | AI augments rather than replaces manual Wallet workflows |

## Capability Model

An AI capability is a bounded way to help complete a Wallet job. It is not a general permission for
the model to inspect state or take action. Each capability should define:

1. the user situation and intended outcome;
2. the language or other variable input AI is expected to interpret;
3. the authoritative Wallet state it may use;
4. the inferences it may propose and uncertainty it must expose;
5. whether it reads state, builds a draft, or can lead to a domain effect;
6. the deterministic validation and user-control boundary;
7. its cancellation, retry, and failure behavior; and
8. the evidence used to evaluate whether it completes the job safely.

A capability should be added only when:

- it advances a job in the Wallet Product Frame;
- language interpretation or flexible interaction offers a meaningful advantage;
- the result can be grounded in sufficient authoritative state;
- important rules and effects can be validated outside the model;
- uncertainty, control, and recovery can be made clear; and
- its value is expected to outweigh added latency, unpredictability, and maintenance cost.

## Current Capability Envelope

The current MVP tests two narrow uses of this model:

| User job | Current capability | AI contribution | Authoritative boundary |
| --- | --- | --- | --- |
| Record a money event | Conversational transaction capture | Interpret progressive natural-language contributions and proposed Wallet references | Wallet code validates the draft; only explicit guarded confirmation posts one transaction |
| Orient to current balances | Current Wallet state | Recognize the request as a supported Wallet-state job | Wallet code reads posted entries and returns active-account balances separated by currency |

These capabilities are evidence about the broader product thesis, not proof that a general
financial assistant is desirable. Their value should be compared with the equivalent direct Wallet
workflow.

### Authority levels

AI participation becomes more constrained as consequences increase:

| Level | Allowed role | Required control |
| --- | --- | --- |
| Interpret | Propose meaning, references, normalized values, or a route | Validate against the capability schema and offered state |
| Read | Request and present an authoritative Wallet snapshot | State the supported scope; do not fill gaps with model knowledge |
| Draft | Assemble a reviewable candidate without changing financial state | Make material selections and consequences visible and correctable |
| Execute | No model-owned execution | Deterministic code revalidates current state and requires the defined user action |

External financial execution, such as moving money, is outside the current Wallet product boundary.

## Desired Outcomes

AI capabilities are doing their job when the user can:

- express a supported need without first learning Wallet's internal structure;
- provide details naturally across one or more contributions;
- see that account, category, amount, type, currency, and date references are grounded in current
  Wallet state;
- resolve meaningful ambiguity without losing valid work;
- understand and correct a proposed financial effect before confirmation;
- receive a current Wallet answer without the model inventing or combining facts;
- cancel, restart, or retry without creating partial or duplicate effects; and
- choose a manual workflow when it is more useful or when AI is unavailable.

The strongest AI outcome is not conversational fluency or the number of messages handled. It is a
supported Wallet job completed with less user effort and no loss of financial trust.

## Product Principles

### Use AI for interpretation, not authority

AI may help determine what the user means. It does not define Wallet facts, domain validity, or the
permission to change the ledger.

### Ground before answering or proposing

A capability should operate on explicitly supplied, current Wallet context. It should not invent
accounts, categories, balances, history, conversions, or available actions.

### Match control to consequence

Read-only answers may be returned directly. A proposed financial write must remain reviewable and
ledger-neutral until the user takes the defined confirmation action.

### Treat ambiguity as product state

When more than one materially different result is plausible, preserve what is known and expose the
choice. Do not hide uncertainty behind a fluent response or an arbitrary selection.

### Make correction cheaper than starting over

Users should be able to amend one part of an in-progress task while retaining the rest. Cancel,
restart, stale state, and failure paths are part of the capability, not edge behavior.

### Keep the interaction honest

The product should distinguish a recorded fact, a proposed interpretation, a missing detail, and an
unsupported request. Friendly language must not imply knowledge, memory, or certainty the system
does not have.

### Minimize exposed context

Give each model call only the user contribution and Wallet context needed for its bounded language
task. More context is not automatically better when it increases privacy risk or unintended
inference.

### Preserve channel equivalence

AI may reduce interaction effort, but the valid domain result must match an equivalent manual or API
operation. Conversation does not create special ledger semantics.

### Remain useful without AI

Model unavailability must not corrupt Wallet state or turn manual use into a degraded product. A
capability may fail safely while the core Wallet remains usable.

## Evaluation Anchors

Evaluate a capability from the user job through the observable Wallet outcome. Do not evaluate only
the wording of a single model response.

Every scenario should identify:

1. the supported user job and initial Wallet state;
2. the user's expression, including relevant shorthand or ambiguity;
3. the minimum state made available to the capability;
4. the expected interpretation, question, answer, or preview;
5. the required control before any domain effect;
6. the final user-visible and Wallet state; and
7. facts, disclosures, and effects that must not occur.

### Quality dimensions

- **Job completion:** Does the interaction produce the intended supported outcome?
- **Interpretation fidelity:** Does the structured meaning preserve what the user supplied and avoid
  unsupported inference?
- **Grounding:** Are references and answers tied to authoritative current Wallet state?
- **Clarification quality:** Does the product ask only when needed and make the remaining choice
  understandable?
- **Financial correctness:** Does the final effect satisfy transaction, balance, and currency rules?
- **Control:** Can the user see, correct, and deliberately approve a consequential action?
- **Side-effect safety:** Do previews, failures, retries, stale actions, and duplicate inputs avoid
  unintended writes?
- **Recoverability:** Can the user correct, cancel, restart, and retry without losing valid state or
  corrupting Wallet state?
- **Effort:** Does the capability reduce steps, repetition, and schema translation relative to a
  suitable direct workflow?
- **Scope honesty:** Does it decline or redirect unsupported jobs without fabricating capability?
- **Channel consistency:** Does the result have the same meaning as the equivalent manual operation?

Financial correctness, grounding, and absence of unintended effects are gates. Fluency, tone, and
interaction speed cannot compensate for failure at those gates. After they pass, prioritize job
completion, control, recoverability, and reduced effort.

Useful evaluation families include complete requests, incomplete requests, corrections,
ambiguities, unavailable or similarly named references, currency conflicts, state changes before
confirmation, cancellation and restart, repeated inputs, model or transport failure, and
unsupported requests.

## Product Boundaries

The current AI layer is not:

- a general-purpose chatbot;
- an authority on balances, categories, or transaction validity;
- a financial adviser, planner, forecaster, or judge of financial health;
- a payment initiator or autonomous financial agent;
- a source of bank data that has not been recorded in Wallet;
- a background or proactive actor;
- a durable memory of the user, their transcript, or their preferences; or
- a way to bypass review, confirmation, currency, lifecycle, or ledger rules.

These boundaries may be reconsidered as separate product decisions. They should not expand merely
because a model can produce relevant-sounding language.

## Assumptions to Validate

The following claims are working hypotheses:

- Translating everyday money events into structured fields is a meaningful source of capture
  friction.
- Users will provide useful shorthand when the assistant is grounded in their account and category
  labels.
- Progressive capture feels easier than a form for at least some common money events.
- A visible draft and explicit confirmation create enough control without removing the convenience
  gained from interpretation.
- Asking for current Wallet state in natural language is more useful than navigating to the same
  balances for some situations.
- Users understand the difference between an AI interpretation and a recorded Wallet fact when the
  product presents that distinction clearly.
- Narrow, predictable capabilities create more durable trust than a broad assistant with uneven
  behavior.

## Open Product Questions

- Which Wallet jobs produce enough translation or navigation cost for AI to create durable value?
- For which jobs is a direct form or view still faster and more trustworthy?
- What may the product infer safely, and which uncertainties must always be surfaced?
- What evidence makes a user comfortable confirming an interpreted transaction?
- How should the product communicate the source and freshness of a read-only answer?
- How much conversational continuity is useful before it creates false expectations of memory?
- What is the best non-AI path when routing or interpretation is unavailable?
- How should a user correct an already posted transaction without obscuring history?
- Which next capability best supports understanding or reconciliation rather than only capture?
- What user evidence would justify proactive, personalized, or advisory behavior in the future?

Answers should update this frame before becoming capability requirements, evaluation datasets, or
implementation contracts.

## Using This Frame

Use the framing chain in this order:

1. **Wallet Product Frame:** defines the underlying user situation, financial jobs, and product
   principles.
2. **AI Capabilities Frame:** defines where AI may reduce effort and the trust conditions it must
   preserve.
3. **Product specification:** selects the current capabilities and their supported behavior.
4. **Wallet and AI concepts:** define shared financial and assistant-facing meanings.
5. **Technical contracts:** define authoritative control and execution boundaries.
6. **Capability designs and evaluations:** specify an interaction and test the complete outcome.
7. **Implementation:** realizes the capability within those boundaries.

Implementation constraints may narrow a capability, but model behavior alone should not redefine
the user job or expand product authority.
