# Evaluation Trace Viewer Product Frame

## Product boundary

The Evaluation Trace Viewer begins when a domain expert opens a captured evaluation
result package whose identity and integrity can be checked. It ends when the expert
records one attributable pass/fail verdict for a Wallet result or a complete case
trajectory considered as a whole, or records that the selected unit is not
judgeable from the available evidence.

A package may be inspectable without being judge-ready. Aborted runs, invalid
participants, missing telemetry, and partially captured cases can contain useful
diagnostic evidence, but the viewer must establish eligibility for the selected
judgment unit before offering pass/fail. It never produces a partial verdict for an
incomplete result or trajectory.

The viewer consumes evidence produced by the
[evaluation subsystem](evaluation-subsystem-frame.md). It does not execute a case,
call the Wallet system under test (SUT), repair missing evidence, or decide
correctness on the expert's behalf.

"Trace" refers to the captured evaluation trajectory, not only to distributed
spans. The primary object is Wallet behavior. Internal events, model exchanges, and
spans are supporting evidence.

## Status of the implementation evidence

The `eval-harness` branch, its viewer, and its adaptive experiment are disposable
examples examined only to learn about the problem. They have no intended production
future and are not a starting implementation, reference architecture, migration
target, supported input format, or source of backlog commitments.

Nothing in that branch is presumed to survive: not its artifact schemas, filenames,
commands, status strings, Docker or telemetry topology, trace representation,
dependencies, server, browser interface, or code. This frame uses the branch only
as evidence that particular judgment and evidence-handling complexities exist.
Future design is free to discard it completely and is not required to preserve
compatibility with its outputs.

Requirements below must stand on the domain expert's job, the SUT judgment boundary,
and the evidence trust contract. A branch detail is recorded as **Observed** to
inform the reader, not to propose that detail for production.

## Evidence status

### Observed

- The example viewer on the throwaway `eval-harness` branch opens one sealed local
  result package and presents its cases without calling the live SUT.
- It joins case records, final public observations, runtime events, model exchanges,
  and distributed spans by recorded case and trace identity. Timestamps order
  evidence but do not establish identity.
- Its primary case view shows the public SUT input and answer. Separate views expose
  the complete trajectory, HTTP exchanges, final state, model activity, case
  definition, and raw evidence.
- The example fixed-harness package is split across a manifest, case records, a case
  index, runtime logs, a trace-set descriptor, a trace index, raw OTLP records, and
  an observability lifecycle receipt. Judge-readiness depends on identity and
  completeness agreeing across those artifacts.
- A domain expert can inspect a standalone or multi-step case without manually
  reading and correlating several JSON, JSONL, and telemetry artifacts.
- Capture status and correctness are shown separately. `completed` means the
  execution was captured; it does not mean the SUT passed.
- The example viewer derives its summary answer from the last step labelled
  `focal` and its summary route from the last routing event. Those are presentation
  shortcuts, not stable answer or decision identities for a multi-step trajectory.
- The two disposable runners do not share a judgment-facing case shape. Fixed cases
  use phased `steps` and final observation steps; the adaptive experiment uses
  participant steps, a stated choice basis, role adherence, repeated observations,
  and a different artifact entry point. The example viewer cannot open both through
  one contract.
- Failure classification is not reducible to HTTP or trace error status. The fixed
  harness can mark a non-200 turn as a case error, while the repaired adaptive
  experiment preserves a participant-visible HTTP 502 as valid SUT evidence.
  Failed reset, missing runtime events, and incomplete traces are apparatus
  failures instead.
- Interrupted and failed runs preserve case records and drained telemetry when
  possible, but the current verification receipt marks only a completed,
  internally consistent run as judge-ready.
- Distributed spans deliberately omit prompts, messages, account data, and
  transaction bodies. Public exchanges come from case records, while raw model
  content comes from evaluation-only runtime events.
- The example viewer is read-only. It does not select a judgment unit, apply an
  evaluation rubric, record a verdict, or preserve review progress.
- Domain experts are the intended initial judges. The established judgment contract
  is pass or fail, with a short explanatory note when the result is fail.

#### Disposable 20-case inspection

An AI-assisted exploratory inspection on 2026-08-12 ran 20 selected cases against
the throwaway branch at `f12fb61` and reviewed their complete trajectories through
that branch's viewer. This was a learning exercise, not domain-expert adjudication,
a representative sample, a SUT quality estimate, or validation of the example
implementation.

- The successful package reported all 20 cases captured and completed, with all 20
  expected case traces verified. Holistic screening still found an incorrect public
  candidate in one trajectory. This directly confirms that capture completion and
  correctness are independent.
- In that failed trajectory, the friendly preview looked correct while the complete
  structured public result assigned `Groceries` as a merchant even though the user
  supplied it as the purchase and category. A summary string was therefore
  insufficient to judge the result as a whole.
- Another summary looked incorrect in isolation because a balance question received
  the existing transaction preview. The complete sequence showed that a transaction
  task was active, the product contract prohibited capability switching, and the
  draft remained intact and unposted. Trajectory and policy context changed the
  judgment.
- Nineteen of the 20 embedded examples had no explicit `required_condition`.
  Screening relied on the case purpose and failure surface, the product
  specification, the fixture, and reviewer interpretation. The branch did not make
  that combined judgment basis explicit in the review flow.
- The example viewer exposed evidence but could not select the judgment unit, record
  the verdict, require the first-failure note, or preserve progress. The exploratory
  verdict record had to remain a separate sidecar to avoid altering the captured
  package.

### Inferred

- The viewer's primary value is reducing the work required for a domain expert to
  reach and explain a trustworthy SUT judgment.
- Expert review needs two depths. An answer-focused path supports locally judgeable
  behavior, while a complete-trajectory path supports cases whose correctness
  depends on intermediate choices, state transitions, or failure location.
- The common review path should begin with case intent, public behavior, and public
  outcome. Internal telemetry should be available on demand rather than dominate
  the first view.
- Screening produces one holistic verdict for the selected result or trajectory.
  It does not score individual steps, conditions, symptoms, or failure incidents.
- A failed unit should contribute only its first observable failure to the next
  failure-understanding stage. The full trace remains available to understand how
  that failure arose and propagated.
- A judgment must remain traceable to the exact sealed evidence, even when the
  viewer presents a simpler human-readable account.
- Verdicts should be separate artifacts keyed to the evidence package. Writing a
  verdict must not mutate or reseal the captured execution evidence.
- The durable viewer needs its own versioned, judgment-facing trajectory contract.
  The human interface must not encode a throwaway runner's filenames and shapes as
  product semantics, and no legacy adapter is implied.
- A result verdict needs an exact target identity and the complete public response,
  not only a derived message string. A repeated message, typed action, structured
  offer, or public error body can all be part of the result under judgment.
- Run validity, case capture, participant validity, observed SUT behavior, and the
  correctness verdict are independent concerns. The viewer must not collapse them
  into one status badge.
- Final case state supports trajectory judgment, but it does not always establish
  the effect of one result when later turns can also change state. Result-level
  claims require state evidence with an attributable scope.

### Unknown

- Which explicit rubric, reference answer, required conditions, or expert knowledge
  must be visible for consistent judgment.
- When a case should request a result verdict or a complete-trajectory verdict.
- Which canonical trajectory contract can represent fixed, sequence, typed-action,
  response-adaptive, product-error, and partially captured cases without losing
  evidence.
- Which result-level judgments require an observation immediately after the result
  instead of the case's final public state.
- The minimum trajectory evidence a domain expert needs before low-level telemetry
  can be removed from the normal review path.
- Which private participant context and evaluation-only model content a judge may
  inspect, and how it must be distinguished from public SUT behavior.
- Whether review must support multiple experts, blind review, disagreement, or
  adjudication.
- Which later decisions require repeated samples, comparison, or aggregate results.
- At what package size raw-trace loading or large case records make local review too
  slow for the intended cohort.

## Intent

### Actors and situation

- **Judge:** a domain expert evaluating Wallet behavior against product and domain
  expectations. An automated judge is a later consumer of the same evidence and
  verdict contract, but not of the human interface.
- **Operator:** an evaluation engineer who selects cases and produces the verified
  or partially verified result package handed to the judge.
- **Beneficiary:** the product and engineering team using the verdicts to assess the
  SUT or investigate a behavior.

The need arises after execution evidence has been captured successfully but cannot
be judged reliably from an isolated response string or from raw artifacts alone.

### Job and intended outcome

The domain expert's job is to reach a defensible verdict without learning artifact
formats, manually correlating records, or rerunning the SUT.

The intended outcome is a review record that identifies the evidence package, case,
complete result or trajectory, evaluation-policy basis, judge, and one pass/fail
verdict. A fail includes a short concrete note identifying the first observable
failure and its evidence location. When correctness cannot be judged, a separate
disposition identifies the missing or invalid evidence without manufacturing a
verdict. Another consumer must be able to tell what was judged and return to the
supporting evidence.

## Core experience

The primary workflow is:

`open a captured package → inspect provenance and validity → select an eligible result or complete trajectory → review it as a whole → record pass/fail → if fail, note the first observable failure → hand that failure to downstream analysis → continue through the review set`

Important supporting scenarios are:

- judge a public result as a whole when its input, response, expectations, and
  observable outcome are sufficient;
- expand from a result to the complete trajectory without losing case context;
- inspect a multi-turn or response-adaptive trajectory whose outcome depends on a
  prior SUT response;
- inspect a public error as SUT behavior without mistaking its HTTP or span error
  status for apparatus failure or an automatic fail verdict;
- distinguish an invalid participant from a valid participant who encountered
  incorrect SUT behavior;
- find where behavior diverged by following significant decisions, state changes,
  model attempts, validation retries, and errors grouped under the relevant step;
- compare the declared initial fixture with observations taken at known points,
  without attributing final state to one result when later steps could have changed
  it;
- return from a human-readable summary to the exact captured record;
- inspect preserved evidence from an aborted run for apparatus diagnosis without
  assigning a partial SUT verdict;
- withhold a correctness verdict when evidence required for the selected unit is
  invalid or incomplete rather than turning apparatus failure into SUT failure;
- hand only the first observable failure from a failed unit into deeper error
  analysis while retaining the complete trace as supporting context; and
- resume a targeted review set with judged, judgeable, and remaining work visible.

## Judgment units

### Result

A result is one complete judgeable SUT outcome at an explicitly identified case
step. It includes the public response relevant to the participant and any public
state required by the case's success conditions, not merely the viewer-generated
message preview. It may include an HTTP status, outcome, offered actions,
conversation state, structured error, or other public fields.

The result is considered together with:

- the input that prompted it;
- the case purpose and applicable expectations;
- earlier public interaction needed to interpret it; and
- public state observed at a point that can be attributed to the result.

Result judgment is the fast path. It should not require the expert to read internal
events when the public behavior is already sufficient. When only final case state
exists and later steps may also have changed it, the viewer must narrow the claim,
request trajectory judgment, or mark the result evidence insufficient.

### Complete trajectory

A complete trajectory is one case execution considered from its declared scenario
through its final public state. It includes ordered public interactions,
response-adaptive choices when present, outcome-affecting system behavior, errors,
and the observable result.

The trajectory also preserves evidence roles and phases. Fixture reset and setup
establish initial conditions; participant inputs and public SUT responses form the
interaction; observations establish public state; runtime events, model exchanges,
and spans explain internals. For adaptive cases, the participant's role validity and
stated response-dependent choice basis are trial evidence, not Wallet behavior and
not private chain-of-thought.

Trajectory judgment is required when a single result does not establish whether the
SUT behaved correctly. Diagnostic internals may explain the path, but they do not
replace the public behavior being judged.

### Relationship between units

The selected unit is part of the verdict. Result and trajectory verdicts are not
interchangeable, and the viewer does not silently roll one into the other. A case
may expose several candidate results while still having one complete trajectory,
but each selected unit receives one verdict as a whole.

A result target must remain stable even when content repeats. At minimum it binds
the evidence package, case, phase, and step identity. A trajectory target binds the
evidence package and case. Neither target is inferred from "last focal step,"
latest timestamp, response text, or the last routing event.

The viewer does not produce per-step sub-verdicts inside a trajectory, partial
credit, multi-label failure annotations, or a rollup score. If any behavior makes
the selected unit unsuccessful under its evaluation basis, the unit fails.

## Screening and error-analysis handoff

The viewer is the first screening stage. Its judgment contract is deliberately
small:

1. review one eligible result or complete trajectory as a whole;
2. mark it pass or fail;
3. when it fails, write a short concrete note identifying the first observable
   failure and link that note to the relevant evidence; and
4. hand that one failure forward for deeper analysis.

The failure note stays close to what the trace demonstrates. It does not need to
name a taxonomy category, explain the root cause, enumerate downstream symptoms, or
recommend a refactor. The first observable failure may be upstream of many later
symptoms, but it is not automatically the root cause.

Downstream failure understanding uses the full linked trace to investigate that
first failure, compare it with failures from other traces, develop initial and
focused codes, refine a failure model, and inform measurement, regression coverage,
and system refactoring. That analytical workflow is outside the viewer's MVP. The
viewer supplies a stable failed unit, the short first-failure note, and a direct path
back to its evidence.

## Evaluation state model

The branch exposes several independent state axes. The viewer must present them
separately because each answers a different question:

| Concern | Observed examples | Question answered | Effect on judgment |
| --- | --- | --- | --- |
| Run and telemetry validity | completed, aborted, verified, drained partial, failed | Is the package internally coherent and is required telemetry present? | Controls whether units can be admitted for judgment; remains useful for diagnosis. |
| Case capture | completed, error, infrastructure error | How far did case execution and evidence collection get? | Identifies missing evidence and failure location; does not determine correctness. |
| Participant validity | valid, invalid, role-adherence failure, turn-limit breach | Did a synthetic participant follow the declared trial contract? | Invalidates or excludes the trial without making the SUT fail. |
| Public SUT behavior | successful outcome, structured error, HTTP 502, offered action, state change | What did the SUT expose to the participant? | Is evidence to judge, even when transports or spans label it as an error. |
| Correctness review | unjudged, pass, fail, not-judgeable disposition | Did the selected result or trajectory succeed as a whole? | Exists only after eligibility and an explicit judgment action. |

Exact source status strings may evolve. The durable requirement is the separation of
these meanings and an explanation of which evidence caused any eligibility block.

## Judgment-facing trajectory model

The future viewer needs one semantic contract for review. The throwaway layouts are
examples of information and failure modes only; this frame does not require the
future viewer to read, adapt, or migrate them. The durable contract must preserve:

- run provenance, including dataset and selection identity, SUT revision and dirty
  state, image identity, model name and digest when available, configuration, and
  observability verification;
- case intent, dimensions, fixture identity, initial conditions, interaction form,
  applicable expectations, and whole-unit success conditions;
- ordered steps with stable identities, phase, actor or evidence role, public input,
  complete public response, HTTP status, and correlation identities;
- typed actions and response-adaptive participant choices, including the public
  observation cited as the choice basis and role-validity result;
- observations labelled by subject and capture point rather than treated as one
  timeless "final state";
- product responses, participant invalidity, apparatus failures, and missing
  evidence as distinct classifications;
- runtime events and model attempts attached to the relevant step when correlation
  allows, without presenting hidden model content as the public SUT answer;
- distributed trace structure from recorded parentage and service identity; and
- raw source references for every normalized item so unsupported or unknown fields
  remain inspectable.

Any future reader must fail visibly when required semantics cannot be recovered. It
may order timestamped records for display, but it must not guess result identity,
causality, participant validity, or missing joins.

## Product capabilities

The viewer must enable a domain expert to depend on these externally meaningful
behaviors:

- **Open trustworthy evidence.** Load a captured result package and its verification
  state, preserve its identity, and make capture validity visible before presenting
  correctness work.
- **Inspect without over-admitting.** Open preserved partial or invalid evidence for
  diagnosis while offering pass/fail only for a unit whose required evidence and
  trial validity are established.
- **Consume an explicit evidence contract.** Present fixed and response-adaptive
  cases through one judgment-facing model without discarding their different step,
  participant, observation, or failure semantics. This does not require support for
  the throwaway branch's formats.
- **Establish judgment context.** Show the evaluated SUT, model, dataset, case
  purpose, dimensions, initial conditions, evaluation policy, provenance warnings,
  and required conditions needed to interpret the behavior.
- **Find the next review unit.** Distinguish judgeable, judged, and not-yet-judged
  results and trajectories within the selected review set.
- **Judge a result as a whole.** Present the relevant input, complete public SUT
  response, expectations, and attributable observable outcome together, and bind
  one verdict to the complete result rather than to its individual fields.
- **Reconstruct a complete trajectory.** Present ordered interactions,
  outcome-affecting choices, significant system behavior, errors, and final public
  state as one coherent case narrative that receives one holistic verdict.
- **Separate evidence roles and validity axes.** Keep setup, participant behavior,
  public SUT behavior, observations, internal diagnostics, apparatus state,
  participant validity, and correctness judgment visibly distinct.
- **Preserve public errors as evidence.** Show the complete response and its origin
  even when HTTP or trace status is an error, and do not reclassify it as apparatus
  failure or correctness fail from status alone.
- **Reveal evidence progressively.** Put decision evidence first, then allow
  drill-down into exchanges, state observations, participant choices, model
  attempts, runtime events, spans, and raw artifacts.
- **Correlate without flattening.** Group events, retries, spans, and observations
  under stable steps where identities support it while preserving full case and
  trace order for trajectory review.
- **Keep summaries auditable.** Link every derived or summarized display value back
  to the exact captured record using explicit identities rather than timing
  heuristics.
- **Keep capture and correctness separate.** Never present completed capture as a
  pass, invalid participation as SUT failure, or invalid capture as a fail.
- **Record an attributable verdict.** Record one pass or fail for the complete
  result or trajectory target and identify the evidence, evaluation-policy basis,
  and judge behind the decision.
- **Capture the first observable failure.** On fail, require a short concrete note
  and evidence location for the first observable failure without requiring root
  cause, taxonomy, or exhaustive annotation.
- **Hand failure forward.** Make the failed whole unit, its first-failure note, and
  its complete supporting trace available to the downstream failure-understanding
  and refactoring process.
- **Explain non-judgeability.** Preserve a non-verdict disposition with the exact
  missing, inconsistent, or invalid evidence that blocked judgment.
- **Preserve the evidence package.** Store judgment separately so review cannot
  alter the execution that was judged.

## Evidence presentation order

The default information order should follow the expert's decision, not the storage
layout or telemetry volume:

1. package provenance, capture validity, trial validity, and judgment eligibility;
2. case purpose, scope, initial conditions, and applicable expectations;
3. selected public input and the complete SUT response;
4. attributable state observation and required conditions;
5. ordered public interaction, adaptive choices, and significant trajectory events;
6. diagnostic model attempts, runtime events, and distributed-trace detail; and
7. exact raw evidence and unresolved fields.

The expert may move directly to deeper evidence. The order defines presentation
priority, not a claim that every verdict requires every layer.

## Proposed MVP boundary

### Included

- Local inspection of one evaluation result package at a time. Preserved partial
  evidence remains available for diagnosis, but only a complete eligible result or
  trajectory receives pass/fail.
- A newly designed, versioned judgment-facing contract that represents fixed,
  sequence, typed-action, and response-adaptive semantics.
- Case selection and basic judged, judgeable, and remaining progress.
- Explicit result and complete-trajectory judgment units with stable case and step
  identity and one holistic verdict per selected unit.
- Separate run validity, case capture, participant validity, public SUT behavior,
  and correctness review states with eligibility explanations.
- Case intent, public input and result, captured public-state observations, and
  significant ordered behavior in the main review experience, with the scope of
  each state observation made explicit.
- Response-adaptive choices and their stated public-response basis, labelled as
  participant evidence rather than SUT behavior.
- On-demand inspection of captured exchanges, runtime and model events, distributed
  spans, and raw records when present.
- Provenance visibility for dataset selection, SUT source and dirty state, runtime
  image, model identity, configuration, and observability verification.
- One pass/fail verdict for the selected whole unit, with a required short note and
  evidence location for the first observable failure.
- A separate verdict artifact that identifies the evidence package, case, judgment
  unit, exact result step when applicable, evaluation-policy basis, and judge.
- A first-failure handoff that links the failed whole unit and short note to the
  complete trace used by downstream failure understanding.
- A non-judgeable disposition that records why pass/fail was withheld.
- Honest empty, missing, incomplete, and invalid evidence states.

### Explicitly excluded or deferred

- Case definition, dataset editing, SUT execution, replay, and rerun controls.
- Reconstruction of state, participant choices, or trace joins that were not
  captured by the upstream evaluation system.
- Reuse, migration, or compatibility support for the `eval-harness` branch's code,
  artifact layouts, commands, or viewer behavior.
- Automatic correctness grading, numeric scoring, aggregation, thresholds, and
  release gating.
- Per-step sub-verdicts inside a trajectory, partial credit, multi-label failure
  annotation, and exhaustive enumeration of downstream failure symptoms.
- Initial coding, focused coding, failure-taxonomy development, root-cause analysis,
  refactoring, and regression design inside the viewer. These consume the viewer's
  first-failure handoff downstream.
- Cross-run and cross-model comparison, historical dashboards, and trend analysis.
- Multi-expert assignment, blind review, disagreement resolution, and adjudication.
- Editing, repairing, annotating, or resealing the execution evidence package.
- Treating raw model output, participant-private context, or span error status as a
  public SUT answer or correctness rule.
- A particular UI framework, tracing vendor, telemetry layout, or deployment model.
- Remote publication, collaboration, and administrative access control.

## Trust and decision boundary

- The captured result package and its verification receipt remain the source of
  execution truth and evidence-validity status.
- The viewer does not call, replay, enrich, or mutate the SUT or its evidence.
- Artifact references and case identifiers must resolve inside the selected package;
  malformed or escaping references fail visibly.
- Recorded run, case, phase, step, request, trace, span, and artifact identities
  establish joins. Timestamps may determine display order only, and span depth comes
  from recorded parentage.
- Public SUT responses, participant evidence, evaluation-only model content, and
  apparatus diagnostics are labelled by origin. The viewer does not imply that an
  expert or participant observed hidden evidence.
- Capture validity and the judge's correctness verdict remain separate facts in the
  interface and output.
- Product-response errors remain behavioral evidence. Reset, isolation, capture,
  correlation, telemetry, and teardown failures remain apparatus evidence.
- A verdict is a new judgment artifact, not a correction applied to the evidence.
- The viewer does not invent a rubric. The basis for judgment comes from the case,
  an attached evaluation policy, or explicit domain expertise and must be visible
  enough for another consumer to interpret the verdict.
- An automated judge may later read the same evidence and produce the same verdict
  contract without using this interface.
- The local MVP binds to loopback and assumes synthetic evaluation data. Any move to
  remote or non-synthetic review requires a new access and privacy boundary.

## Learning agenda

### Canonical trajectory contract

- **Question:** What minimum semantic contract represents fixed sequences, typed
  actions, response-adaptive choices, product errors, observations, and partial
  capture without forcing all runners into one storage layout?
- **Decision affected:** result-package versioning, stable result identity, future
  evidence producers, and automated-judge compatibility.
- **Blocking status:** blocking one future viewer from judging both fixed and
  adaptive behavior.
- **Evidence needed:** use representative branch records only as disposable test
  cases, design a new contract from the product requirements, and prove every
  displayed item traces to its source without requiring legacy ingestion.

### Result completeness

- **Question:** When is the final case observation sufficient for a result verdict,
  and when is a per-step observation required?
- **Decision affected:** result-level claim scope, upstream capture points, and when
  the viewer must direct the expert to trajectory judgment.
- **Blocking status:** blocking result verdicts that depend on state effects in a
  multi-step case.
- **Evidence needed:** review cases with several state-affecting turns and determine
  whether experts can attribute the observed outcome to the selected result.

### Judgment basis and unit

- **Question:** Which expectations let experts judge consistently, and when should
  a case request a result verdict or a complete-trajectory verdict?
- **Decision affected:** case authoring, the default review path, and stable verdict
  identity.
- **Blocking status:** not blocking further read-only inspection; blocking a stable
  expert-judgment contract.
- **Evidence needed:** representative experts judge a targeted cohort while
  recording the basis used, selected whole unit, evidence opened, and short
  first-failure notes. Include cases like the disposable inspection where a
  friendly summary and the complete structured result support different judgments,
  and record which source resolved the decision.

### Minimum evidence

- **Question:** What is the least evidence that lets an expert reach and explain a
  reliable whole-result or whole-trajectory verdict?
- **Decision affected:** default presentation, artifact contract, and which runtime
  and telemetry details survive subtraction.
- **Blocking status:** not blocking the MVP with full evidence; blocking a thinner
  permanent evidence contract.
- **Evidence needed:** judge-consumption trials comparing complete packages with
  systematically reduced views. Preserve the two disposable contrast cases where
  summary-only review would respectively miss an incorrect structured field and
  misread policy-conforming active-task behavior.

### First-failure handoff

- **Question:** What minimum identity and evidence locator must accompany the short
  first-observable-failure note so downstream analysts can begin failure
  understanding without repeating screening?
- **Decision affected:** verdict artifact fields and the boundary between viewer,
  failure understanding, and later refactoring work.
- **Blocking status:** not blocking pass/fail screening; blocking a reliable handoff
  into error analysis.
- **Evidence needed:** hand failed results and trajectories to analysts and confirm
  they can locate the first observable failure, distinguish it from inferred root
  cause, and follow its propagation through the complete trace.

### Review continuity

- **Question:** What persistence and identity are needed to resume review and make
  a verdict attributable without introducing a full administrative system?
- **Decision affected:** verdict artifact fields, local persistence, and review
  progress behavior.
- **Blocking status:** blocking verdict capture beyond a disposable trial.
- **Evidence needed:** one expert reviews a targeted cohort across multiple sessions
  and hands the result to another consumer.

### Expert-to-automated-judge transition

- **Question:** Which evidence and judgment context used by domain experts must
  remain available to an automated judge?
- **Decision affected:** the stable evidence and verdict contracts and any human
  interface retained for investigation.
- **Blocking status:** not blocking expert-led use; blocking evidence subtraction
  for the automated path.
- **Evidence needed:** compare expert and automated verdicts for the same explicit
  whole judgment units, including their short first-failure notes.

## Evidence sources

- [Evaluation Subsystem Product Frame](evaluation-subsystem-frame.md) — upstream
  evidence boundary, judge contract, and current learning agenda.
- [Wallet MVP specification](spec.md) and [concepts](concepts.md) — SUT behavior and
  canonical product language.
- The `eval-harness` branch at `f12fb61` — a purely throwaway observation source.
  Its example result format, viewer, and tests inform edge cases only; none is a
  production candidate or compatibility obligation.
- The `adaptive-agent-20260810T015012Z` experiment materials on the throwaway
  `eval-harness` branch — evidence that response-adaptive trajectories introduce
  additional judgment and validity semantics, not a proposed coordinator design.
- *Failure Understanding: Discovering and Structuring How LLM Systems Fail*
  (`/Users/val/notes/ai-engineering/evaluation/20-error-analysis.md`) — downstream
  method for carrying the first observable failure into initial coding, focused
  coding, failure-model development, measurement, and system improvement.
