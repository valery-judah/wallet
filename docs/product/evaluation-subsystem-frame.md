# Evaluation Subsystem Product Frame

## Product boundary

Wallet's evaluation subsystem begins when an evaluation operator selects synthetic
cases and a Wallet/model configuration. It ends when the subsystem hands a
trustworthy execution-evidence package to a human or automated judge.

The subsystem establishes what was exercised, what Wallet did, and whether the
evidence was captured reliably. It does not decide whether the observed behavior
is correct.

## Evidence status

### Observed

- The current harness validates synthetic datasets before execution, runs selected
  or full-corpus cases against an identified Wallet checkout and model, isolates
  case state, and preserves inputs, outputs, final public state, runtime events,
  and execution telemetry.
- It supports standalone and fixed-sequence cases. Cases currently labelled
  `adaptive_sequence_candidate` use a deterministic typed prelude; they do not
  choose later inputs from Wallet's returned public response.
- A completed result package can be checked for identity, completeness, and
  judge-readiness, then inspected locally as a case trajectory.
- Capture status and behavioral correctness are deliberately separate. The
  subsystem does not grade, score, aggregate quality, or gate releases.
- The completed `adaptive-agent-20260810T015012Z` experiment found that three valid
  synthetic participants made outcome-affecting choices from public Wallet
  responses. Two branches could not be represented by the current fixed forms
  without assuming the response. This supports a narrow response-adaptive
  execution capability; it does not establish human usability, prevalence, or
  product value.
- Domain experts are the intended evidence consumers while the subsystem is being
  built. An automated judge is the later intended consumer.
- The judge returns pass or fail, with a short explanatory note when the result is
  fail.

### Inferred

- The primary value is a decision-ready evidence package that lets a downstream
  consumer judge Wallet behavior and investigate failures without rerunning the
  original system.
- Isolation, provenance, and completeness matter because evidence that may contain
  leaked state, unidentified runtime inputs, or missing execution context cannot
  support a trustworthy judgment.
- Detailed telemetry is one current way to supply diagnostic evidence. The product
  need is explainability sufficient for the intended judge, not a commitment to a
  particular tracing mechanism or artifact layout.

### Unknown

- The minimum diagnostic evidence each intended judge needs. Main turns and events
  are the current working set, not yet a proven minimum.
- What repeatability or repeated-sampling guarantees are needed for model-mediated
  behavior; no sampling policy has been chosen.

## Current observed boundary

Today an operator can:

1. validate the dataset, fixtures, and selected cases without running Wallet;
2. execute synthetic standalone, fixed-sequence, and deterministic-prelude cases
   in isolated state;
3. run a targeted cohort or the full dataset against recorded Wallet and model
   identities;
4. retain product responses, case errors, final public state, runtime evidence,
   provenance, and partial evidence from interrupted or failed runs;
5. distinguish successful evidence capture, product-response errors, and failures
   that make the evidence untrustworthy;
6. verify a completed package before handing it to a judge; and
7. inspect a captured case as a local read-only trajectory.

The current supported harness cannot let a participant choose the next valid input
from Wallet's public response. A disposable runner demonstrated that behavior for
the adaptive experiment, but it is not yet part of the permanent harness boundary.

## Intent

### Actors and situation

- **Operator:** an evaluation engineer selecting cases, Wallet/model inputs, and a
  run scope when the team needs behavioral evidence.
- **Beneficiary:** the product and engineering team making a Wallet-quality or
  implementation decision.
- **Artifact consumer:** initially a domain expert and later an automated judge,
  applying the same pass/fail verdict contract to the captured evidence.

The need arises when Wallet behavior must be assessed under controlled synthetic
conditions and a simple request/response transcript is insufficient to establish
what happened or why.

### Job and intended outcome

The operator's job is to exercise decision-relevant Wallet behavior under known,
isolated conditions and hand off evidence another consumer can trust and judge.

The intended outcome is a self-contained result package that identifies the case,
system, model, observed behavior, final public state, capture validity, and enough
diagnostic context for the intended judgment—without presenting capture success as
behavioral correctness.

## Core experience

The primary workflow is:

`define or select cases → validate inputs → execute each case in isolated state → capture behavior and provenance → classify evidence validity → verify the result package → hand it to a judge`

Important supporting scenarios are:

- target a small cohort while developing and run a broader corpus when needed;
- preserve an actual Wallet error response as behavioral evidence and continue
  when isolation remains trustworthy;
- abort or exclude affected evidence when reset, capture, or provenance fails;
- retain inspectable partial evidence after interruption;
- for response-adaptive cases, let an explicitly bounded participant choose the
  next action using only its private role context and Wallet's public responses.

## Product capabilities

The subsystem must enable an operator or downstream consumer to depend on these
externally meaningful behaviors:

- **Reject invalid cases before execution.** Confirm that a case is complete and
  well-formed before spending time starting Wallet and the model. For example,
  reject a case with a missing fixture or unknown action.
- **Run selected synthetic cases against identified inputs.** Let the operator
  choose specific cases and run them against a recorded Wallet version, model, and
  configuration so the result can be attributed and inspected.
- **Isolate evidence between cases.** Give each case clean Wallet state so activity
  from one case cannot affect another case's result. Cases remain runtime inputs to
  a reusable execution environment; isolation does not require building a separate
  Docker image for each case.
- **Support fixed and response-adaptive interactions.** Run predetermined scripts
  and bounded sequences in which the next input depends on Wallet's actual public
  response when the decision path requires it.
- **Preserve observable evidence and provenance.** Record what was sent, what Wallet
  returned, the resulting public state, and which Wallet, model, and configuration
  produced it.
- **Classify outcomes by cause.** Distinguish product evidence, such as a Wallet
  error response, from invalid participation, such as a participant breaking its
  role, and apparatus failure, such as the runner crashing or failing to reset.
- **Retain evidence sufficient for diagnosis.** Keep enough context for the
  intended judge to understand the execution and explain a failure. Main turns and
  significant events are the provisional minimum.
- **Verify package completeness and consistency.** Before handoff, confirm that the
  required case identity, turns, events, final state, and runtime identity are
  present and belong to the same execution.
- **Keep trustworthy partial evidence.** If a run stops midway, preserve evidence
  that remains valid while clearly marking the run incomplete or invalid.
- **Separate evidence capture from judgment.** Hand trustworthy evidence to the
  judge without treating successful execution as a pass or introducing unstated
  correctness rules.

## Proposed MVP boundary

This boundary is derived from the value path above, not copied from the current
implementation.

### Included

- Static validation of case definitions and fixtures.
- Targeted execution of one or more synthetic cases against recorded Wallet and
  model identities.
- A reusable execution environment that accepts case definitions and fixtures at
  runtime rather than packaging each case in its own Docker image.
- Trustworthy isolation between cases.
- Fixed standalone and sequence execution.
- A narrow response-adaptive mode with an explicit participant role, private
  context, allowed actions, turn limit, public-response-only observation, and full
  reset between participants.
- Capture of case inputs, public responses, final public state, provenance, failure
  classification, and diagnostic context required for downstream judgment. Main
  turns and events are the provisional minimum until judge-consumption evidence
  supports further subtraction.
- A verifiable, self-contained handoff package with honest completed, partial, and
  invalid states.

### Explicitly excluded or deferred

- Correctness grading, score aggregation, quality thresholds, and release gating.
- Claims about human preference, usability, prevalence, or product value from
  synthetic participants.
- Parallel case execution, production-scale orchestration, and generalized
  multi-agent simulation.
- Full-corpus execution as an MVP requirement; targeted execution proves the value
  path.
- A particular deployment, tracing, storage-layout, or viewer mechanism. Keep one
  only when it is the cheapest way to meet the evidence contract.
- Historical analytics, cross-run dashboards, and administrative workflows.

## Response-adaptive sequences: capability accepted, mechanism deferred

Fixed cases remain the default. A case needs response-adaptive execution only when
its next valid input depends on Wallet's returned public response and encoding that
input in advance would assume the response being evaluated.

The completed experiment supports this narrow capability: a bounded participant
may choose a later action from its private role context and Wallet's public
responses. The evidence package must preserve the observed responses, choices,
outcome-affecting branches, validity classification, and isolation between cases.
Synthetic participation still cannot support claims about human usability,
preference, prevalence, or product value.

The permanent mechanism is deferred to system design. If Docker is used, a shared,
versioned runner image accepts case definitions and fixtures at runtime; the
subsystem does not build a separate image for every case. This frame does not
otherwise commit to the experiment's Docker topology, coordinator, participant
model, tracing, or artifact layout. Choose the cheapest mechanism that satisfies
the capability and evidence contract when implementation begins.

## Learning agenda

### Expert-to-automated-judge transition

- **Question:** Which evidence used by domain experts must remain available when an
  automated judge becomes the primary consumer?
- **Decision affected:** the stable handoff contract and any inspection interface
  retained for expert review.
- **Blocking status:** not blocking expert-led use; blocking subtraction for the
  automated-judge path.
- **Evidence needed:** observe representative expert pass/fail judgments, including
  their short failure notes, then compare which evidence an automated judge needs
  to reach and explain the same verdicts.

### Minimum diagnostic evidence

- **Question:** What is the least evidence that lets the intended judge reach and
  explain a reliable verdict?
- **Decision affected:** which current runtime events, telemetry, state snapshots,
  and package references survive subtraction.
- **Blocking status:** not blocking the next response-adaptive design; blocking a
  materially thinner permanent artifact contract.
- **Evidence needed:** judge-consumption trials comparing complete packages with
  systematically reduced evidence.

### Repeatability

- **Question:** Which decisions require repeated samples rather than one captured
  model-mediated execution?
- **Decision affected:** repetitions, sampling controls, comparison semantics, and
  future aggregation.
- **Blocking status:** not blocking the MVP's evidence-capture workflow.
- **Evidence needed:** repeated runs of decision-relevant cases showing whether
  observed variation changes downstream verdicts.

## Evidence sources

- [Wallet MVP specification](spec.md) and [concepts](concepts.md) — behavior being
  exercised and canonical product language.
- [Simplest Wallet Evaluation Harness](../workstreams/ws-009-harness.md) — historical
  implementation decisions and explicit v1 exclusions.
- [Evaluation Trajectory Viewer](../workstreams/ws-010-evaluation-trajectory-viewer.md)
  — current human-inspection behavior and judge boundary.
- [Adaptive Agent Evaluation Experiment](../superpowers/specs/2026-08-09-adaptive-agent-evaluation-experiment-design.md)
  — predeclared hypothesis, participant limits, and decision rule; the completed
  run result is summarized above.
