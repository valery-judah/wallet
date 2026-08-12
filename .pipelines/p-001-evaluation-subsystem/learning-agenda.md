# Evaluation Subsystem Learning Agenda

**Parent design:** [High-Level Design](hld.md)

Only questions capable of reopening an HLD decision belong here. Ordinary
implementation checks remain in the HLD handoff.

## Priority

| Priority | Learning task | Route | Decision affected | Status |
| --- | --- | --- | --- | --- |
| 1 | Can one active Wallet runtime replace all mutable case state through one fail-closed boundary? | Prototype | D2 — runtime reuse and reset isolation | Executed; result below |
| 2 | Can representative adaptive cases be expressed as mechanically enforceable proposals without semantic role judgment or direct participant access? | Prototype | D3 — runner-mediated bounded participation | Planned; representative adaptive case contracts required |
| 3 | What is the smallest evidence set that preserves reliable verdicts and failure explanations? | Experiment | D5 — provisional diagnostic evidence | Planned; domain experts and representative packages required |
| 4 | Does one model-mediated execution produce a stable downstream verdict for decision-relevant cases? | Experiment | Future run/sampling semantics | Deferred until the runner and judge workflow exist |

## P1 — Reused-runtime reset boundary

### Learning Task

**Question**

Under exclusive serial control, can the active Wallet process replace its mutable
product and conversation state through one application-container boundary without
restarting, while a failed replacement leaves the current state intact?

**Candidate answers**

- A — Candidate-then-swap at the application-container boundary can establish a
  clean baseline within one running process.
- B — State must be cleared independently in each repository or registry.
- C — Reliable isolation requires restarting Wallet per case.

**Decision affected**

D2 — reuse one Wallet runtime with mandatory verified reset.

**Evidence needed**

- Product state created before replacement is unavailable afterward.
- A conversation with an active task is unavailable afterward.
- Reusing a previously consumed global request identity is accepted as new work,
  showing replay state was replaced.
- A replacement-construction failure does not change the current container.

**Established constraints**

- Active checkout only.
- One serial runner has exclusive evaluation control during reset.
- Synthetic local data; no model, network service, production data, or production
  mutation.

### Predeclared verdict rule

- **Supported:** all four observations hold through Wallet's public API under the
  tested conditions.
- **Unsupported:** any prior product/conversation/replay state remains reachable,
  or construction failure changes the current state boundary.
- **Inconclusive:** the artifact cannot exercise both product and conversation
  state through the real active application boundary.

### Learning Result

**Artifact / method and conditions**

A disposable local script used the active FastAPI application, its real
`AppContainer` dependency boundary, in-memory repositories, conversation control
layer, and public HTTP routes. Deterministic local fakes replaced model calls. The
script created an account and a conversation with an active task, constructed a
fresh container, swapped it into the running app, then simulated failure while
constructing a later replacement. The script was removed after execution.

Execution provenance: 2026-08-10; active revision
`22400e0338bafec5241d489a47d1f08c33b6f305`; dirty working tree; local test
environment; no external services. There were no deviations from the predeclared
scenarios or verdict rule.

**Observations**

1. The pre-reset account disappeared from account reads after the swap.
2. The pre-reset conversation and its active task returned not found after the
   swap.
3. The same global request identity was accepted after the swap and produced a new
   conversation rather than replaying the old response.
4. A builder failure before assignment left the installed container and its state
   unchanged.

**Verdict:** supported

**Confidence / limitations**

- Supported only for the active process-local implementation under exclusive
  serial control.
- The prototype demonstrates the replacement boundary, not a production reset
  route, fixture seeding contract, reset receipt, concurrent-request behavior,
  durable external state, or multi-worker operation.
- Implementation still must prove that the actual reset path builds the complete
  fixture before swap and emits verifiable reset evidence.

**Parent-decision implications**

- **Decision affected:** D2.
- **Alternative supported:** one reused runtime with candidate-then-swap reset at
  the complete application-state boundary.
- **Alternatives weakened:** per-store in-place clearing and per-case runtime
  restart are not required by the active process-local architecture.
- **Evidence relationship and limits:** this is feasibility evidence only. D2
  remains owned by the HLD, and the incidental FastAPI/Python swap mechanism is not
  an architectural commitment.

## P2 — Mechanically enforceable adaptive boundary

### Prototype Plan

**Question**

Can representative response-adaptive cases express every valid next choice as a
runner-validated proposal using only declared private role context and Wallet's
public responses, without semantic role judgment or direct participant access?

**Verdict target**

A closed proposal contract is sufficient for the accepted adaptive capability.

**Candidate answers**

- A — A closed set of typed proposal kinds and case-declared constraints covers
  the representative branches and makes violations mechanically detectable.
- B — Some valid branches require open natural-language proposals whose role
  adherence needs a separate semantic assessor.
- C — The participant must control Wallet directly.

**Decision affected**

D3 — runner-mediated bounded participation. A result favoring B would reopen the
validity boundary; a result favoring C would contradict the current HLD.

**Disposable artifact**

A small state-machine harness with a fake Wallet public-response stream, a case
contract, accepted and rejected participant proposals, turn-budget enforcement,
and an evidence transcript. It will contain no model call or production code.

**Smallest consequential scenarios**

1. A public response causes a valid message choice.
2. A public response exposes a valid typed Wallet action with guards.
3. A participant proposes an undeclared action.
4. A participant exceeds its turn budget.
5. A proposed action is structurally allowed but violates the declared role.

**Discriminating observations**

- **Support A:** every valid representative branch is expressible and the runner
  rejects all invalid scenarios from the case contract alone.
- **Weaken A / support B:** scenario 5 cannot be distinguished without semantic
  interpretation, or a valid branch cannot be represented by the closed contract.
- **Inconclusive:** the supplied cases do not include both free-message and typed
  action branches or lack agreed validity labels.

**Missing dependency**

Case authors must supply a small representative set of accepted adaptive cases,
including expected valid and role-breaking proposals. The current product frame
summarizes the capability but does not contain those permanent case contracts.

**Safety and cleanup**

Use synthetic in-memory data and fake public responses. Delete the harness after
recording observations.

## E1 — Minimum judge evidence

### Experiment Plan

**Question**

What is the smallest evidence set that lets the intended judge reach the same
pass/fail verdict and, on failure, identify the same material cause as when using
the full package?

**Decision affected**

D5 — whether main turns, significant events, final state, or other diagnostic
evidence can be removed from the stable handoff contract.

**Competing hypotheses**

- H1 — Inputs, public responses, final public state, and provenance are sufficient;
  main turns and significant events can be removed.
- H2 — Main turns and/or significant events change at least one reliable verdict
  or material failure explanation and must remain.
- H3 — The full provisional package is still insufficient for reliable judgment.

**Decision-relevant outcome**

Blinded verdict and material failure-cause agreement between full and reduced
evidence for representative captured cases.

**Method and conditions**

1. Select a small stratified set of trustworthy packages containing passes,
   product-response failures, participant violations, and apparatus failures.
2. Have domain experts judge the full package first and adjudicate disagreements.
3. After a washout, present blinded variants that remove one evidence category at
   a time.
4. Compare verdicts, failure causes, confidence, and requests for missing evidence.
5. Repeat the same offline ablation with the automated judge when it exists.

**Predeclared decision rule**

- **Support removing a category:** every case retains the adjudicated verdict and
  material failure cause, and no judge requests the hidden category.
- **Weaken removal / support retention:** any representative case changes verdict,
  loses the material failure cause, or requires the hidden category.
- **Inconclusive:** experts disagree on the full package, the case set omits a
  major cause class, or the automated judge is not yet available for claims about
  its contract.

**Evidence to collect**

- Full and reduced package variant identities.
- Per-judge verdict, failure note, confidence, and requested missing evidence.
- Adjudicated full-package verdict and cause.
- Order/randomization and any unblinding or deviations.

**Required dependency**

Representative verified packages and at least two available domain experts. The
automated-judge phase additionally requires the implemented judge. These are not
available to this task, so this is a plan, not evidence.

**Execution notes**

Use offline copies; never mutate source packages. Test one evidence category at a
time so a changed judgment is attributable to that subtraction.

## E2 — Single-run verdict stability

### Experiment Plan

**Question**

For decision-relevant model-mediated cases, does one trustworthy execution produce
the same downstream verdict and material failure cause as repeated executions
under the same recorded configuration?

**Decision affected**

Future run semantics: whether one capture per selected case remains sufficient or
whether repetitions and comparison semantics must be added.

**Competing hypotheses**

- H1 — One captured execution is adequate within the tested case/configuration
  boundary because repeated valid captures do not change the verdict.
- H2 — At least one case has valid captures with different verdicts or materially
  different failure causes, so a single capture can mislead the downstream
  decision.

**Decision-relevant outcome**

Within-case verdict and material failure-cause stability across repeated valid
captures, not text similarity or model-token variation.

**Method and conditions**

Run a targeted cohort of decision-relevant fixed and adaptive cases ten times each
with Wallet, Wallet-model, participant, fixtures, and configuration held fixed.
Blind the judge to repetition number and compare only captures whose apparatus
evidence verifies successfully.

**Predeclared decision rule**

- **Support H1 within tested conditions:** no case changes pass/fail verdict or
  material failure cause across ten valid captures.
- **Support H2:** at least one case changes verdict or material failure cause while
  capture remains valid and judge instability has been ruled out.
- **Inconclusive:** configuration drifts, too few valid captures remain, or repeated
  judgment of identical evidence shows the judge itself is unstable.

**Evidence to collect**

- Run, case, Wallet/model/participant, fixture, and configuration identities.
- Capture validity and cause classification.
- Blinded verdicts and failure causes by repetition.
- A duplicate-evidence judgment control for judge stability.

**Required dependency**

The implemented serial runner and reset contract, a representative targeted case
cohort, stable model access, and the intended judge workflow. Until those exist,
this remains a plan and does not block the MVP architecture.

## Not separate learning tasks

The following are implementation acceptance checks because failure would indicate
an incorrect realization of an already selected decision, not uncertainty between
architectural alternatives:

- reset receipt identity and fail-closed sequencing;
- incremental partial-package persistence;
- explicit run/case/provenance joins and final package verification;
- evaluation-only reset access control; and
- captured product-error versus apparatus-failure classification.

Promote one to a prototype only if implementation exposes a concrete competing
system design that the current HLD cannot resolve.
