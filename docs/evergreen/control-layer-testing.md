# Control Layer and Capability System Test Design

Status: implemented MVP test baseline
Date: 2026-08-06
Scope: conversation control, `transactions.capture`, and `wallet.current_state`

## Purpose

This document defines how Wallet proves that one public turn is resolved, executed, and
published safely across the HTTP adapter, controller, engine, coordination, capability, and
Wallet application boundaries. It is the acceptance-test matrix for the implemented
control-layer MVP.

The suite must prove observable behavior and safety properties. It must not merely assert
private method calls while leaving the public conversation or ledger result unverified.

## Test topology

The test pyramid has five deliberate layers:

| Layer | What it proves | Primary command |
| --- | --- | --- |
| Contract | Generic DTO, result-shape, registry, fingerprint, and resolver invariants | `make test-control` |
| Engine | Resolution, guards, lifecycle, versioning, projection, and opaque state handling | `make test-control` |
| Coordination/controller | Replay, rollback, locks, atomic publication, validation order, and delegation | `make test-control` |
| In-process system API | Public schema, status, real composition, cross-workflow behavior, and ledger effects | `make test-control` |
| Real-model smoke | Ollama routing and unified transaction interpretation with real HTTP and seeded Wallet data | `make check-capture-smoke` |
| Router-model smoke | Focused real-Ollama idle-ownership corpus | `make check-router-smoke` |

`make verify` remains the required repository gate and includes every deterministic test.
The real-model smoke is an explicit operator gate because it requires local Ollama and is
expected to be slower and model-sensitive.

## Deterministic data profiles

Each system test owns a fresh application container. Tests must not depend on order, another
test's records, wall-clock sample IDs, or a backend left running by a developer.

### D0 — Empty wallet

- Default category trees only.
- No user accounts or transactions.
- Used for idle conversations, unsupported input, schema failures, and empty wallet state.

### D1 — Explicit wallet-state ledger

Seed through public APIs:

- active USD Cash with opening balance `10000`;
- active USD Savings with opening balance `25000`;
- active ARS Pesos wallet with opening balance `7000`;
- archived ARS credit card with opening balance `-3000`;
- one USD expense of `1250` from Cash to a test spending category.

Expected oracle:

- Cash `8750` USD;
- Savings `25000` USD;
- Pesos `7000` ARS;
- archived card absent;
- totals are `33750` USD and `7000` ARS;
- querying state creates no transaction.

### D2 — Controlled capture wallet

- Repository sample accounts and categories provide stable authoritative references.
- A deterministic contribution processor returns explicit candidate patches or failures.
- A deterministic message router returns explicit closed route decisions or failures.
- The processor records received content so tests can prove whether control resolution did or
  did not invoke transaction interpretation.
- No model or network call is permitted in deterministic CI tests.

### D3 — Real-model capture wallet

- The documented sample dataset is loaded into a managed single-process backend.
- Ollama uses the configured model.
- Ten scenarios exercise idle LLM routing plus complete expense, direct progressive short-answer
  continuation, income, transfer, positive adjustment, ambiguity, typo-tolerant reference
  selection, unknown-reference correction, and currency-conflict correction.

## Required oracles

Every accepted system turn should assert the relevant subset of:

1. HTTP status and safe error detail.
2. Conversation version increments exactly once.
3. Opaque active-task identity and task version, or confirmed absence.
4. Outcome kind, deterministic message, view, and opaque task action guards.
5. Resolver/capability call count when branch exclusivity matters.
6. Conversation read-back equals the committed response projection.
7. Transaction IDs and count before and after the turn.
8. Posted transaction shape, zero-sum postings, and derived account balances.
9. Replay equality or conflict without additional work.
10. Absence of prompts, raw model output, processing traces, and private state.

Assertions against only a `200` response are insufficient.

## Control and transport matrix

| ID | Situation | Expected system result | Automated evidence |
| --- | --- | --- | --- |
| CT-01 | First message without conversation ID | App creates, routes, and returns version `1` in one call | controller and API tests |
| CT-02 | Continued message with returned ID | Accepted through `POST /turns`; same conversation advances | API tests |
| CT-03 | Unsupported, ambiguous, help, or textual no-op first turn | Version `1` idle conversation is still established | controller and API tests |
| CT-04 | Typed task action | Opaque task target/version checked before capability semantics | controller and capture API tests |
| CT-05 | Typed help | No guard, describes available work without internal IDs or capability work | conversation API tests |
| CT-06 | Guarded input without conversation ID | `422`; no conversation created | controller and API tests |
| CT-07 | Typed cancel/restart without guard | `422`; conversation unchanged | conversation API schema tests |
| CT-08 | Server-derived fields in public input | `422`; no resolver or capability work | conversation API schema tests |
| CT-09 | Removed capability start/action input | `422`; workflow selection remains internal | conversation API tests |
| CT-10 | Unknown supplied conversation ID | `404`; no replacement state created | conversation API tests |
| CT-11 | Old create, nested-turn, and capture lifecycle paths | Absent from OpenAPI | OpenAPI conversation test |
| CT-12 | Invalid IDs, action syntax, blank/oversize content | `422` before work | contract and API boundary tests |

## Resolution precedence matrix

| ID | Situation | Expected system result | Automated evidence |
| --- | --- | --- | --- |
| RS-01 | Any typed input | Bypasses exact recognition and message routing | resolver table tests |
| RS-02 | Exact cancel/stop/never mind | Cancel branch only | resolver table and API tests |
| RS-03 | Exact restart/start over | Restart branch only | resolver table and API tests |
| RS-04 | Exact help/what can you do | Help branch only | resolver table tests |
| RS-05 | Idle model-classified compound control | Clarify; no control or capability partially executes | router/resolver/API tests |
| RS-06 | False control while idle | Router classifies the complete original message | router corpus |
| RS-07 | Any non-control message while current | Continues the current capability without message routing | resolver/controller/API tests |
| RS-08 | New task while idle | Starts exactly one registered capability | resolver and API workflow tests |
| RS-09 | Apparent new-task request while current | Continues the current capability; no automatic switch | cross-workflow API tests |
| RS-10 | Ambiguous ownership while idle | Remains idle and asks for clarification | resolver/API tests |
| RS-11 | Unsupported while idle | Remains idle with unsupported outcome | controller/API tests |
| RS-12 | Unsupported-looking message while current | Continues the current capability without routing | resolver tests |
| RS-13 | Invalid structured route | One validation retry, then safe failure without publication | router/API tests |
| RS-14 | Reference-only follow-up while idle | Starts the recent capability without transcript or private-state context | router smoke and wallet-state API test |

Minimum false-control corpus:

- `don't cancel`
- `the cancellation fee was 10`
- `paid at Cancel Wine Bar`
- `I restarted my subscription yesterday`

## Lifecycle, guards, replay, and failure matrix

| ID | Situation | Expected system result | Automated evidence |
| --- | --- | --- | --- |
| LC-01 | Active first turn | Task version `1`; private state and new conversation publish only on success | engine/coordination tests |
| LC-02 | One-turn completed first turn | No active task; wallet-state snapshot retained in the completed view only | wallet-state API tests |
| LC-03 | Active continuation | Same opaque task ID; task and conversation increment once | engine/controller tests |
| LC-04 | Completed continuation | Active task cleared | controller/capture API tests |
| LC-05 | Failed first turn | No conversation or request receipt; same request ID may retry | coordination/controller/API tests |
| LC-06 | Failed continuation | Prior state retained; request ID not committed | coordination/controller/API tests |
| LC-07 | Successful restart | New opaque task ID and task version `1` | controller/real capture tests |
| LC-08 | Failed restart | Prior active task retained | controller tests |
| LC-09 | Cancel current | Clears active task and invokes no capability hook | controller/API tests |
| LC-10 | Cancel/restart idle | Deterministic no-op outcome, one committed turn | API tests |
| LC-11 | Wrong target, stale version, or no current | `409` before capability/Wallet work | engine/controller/API tests |
| LC-12 | Old action offer after another committed turn | `409`; new bound offer uses current version | engine/controller action-guard tests |
| ID-01 | Same global request ID and canonical target/input | Original response snapshot; no repeat work | registry/coordination/API tests |
| ID-02 | Same request ID with changed target or input | `409` before work | contract/registry/API tests |
| ID-03 | Failed processing then retry | Retry is processed and can commit | registry/coordination/API tests |
| ID-04 | Same Wallet operation and command | Same transaction object; one persisted write | transaction service tests |
| ID-05 | Same Wallet operation with changed command | Rejected | transaction service tests |
| FL-01 | Model/processing failure | Safe `502`; private error absent; state unchanged | conversation API tests |
| FL-02 | Reference changes after preview | Active correction; no write | capture API tests |
| FL-03 | Unknown/premature/malformed task action | Active corrective result; no write | capture API tests |

## Concurrency and atomic-observation matrix

| ID | Situation | Expected system result | Automated evidence |
| --- | --- | --- | --- |
| CC-01 | Two turns in one conversation | Handler calls serialize | coordination/controller concurrency tests |
| CC-02 | Turns in unrelated conversations | Other conversation progresses concurrently | coordination/controller concurrency tests |
| CC-03 | Read during a turn | Read observes complete post-turn value, never partial state | coordination/controller atomic-read tests |
| CC-04 | Two confirmations with one guard version | One `200`, one `409`, exactly one transaction | capture API concurrency test |
| CC-05 | Concurrent duplicate first request | One conversation and one capability execution; both callers receive one snapshot | coordination/controller/API concurrency tests |
| CC-06 | Shared handler across conversations | No per-conversation handler state leaks | controller concurrency test |

These tests intentionally prove process-local locking only. Multi-worker coordination is out
of scope and must not be inferred from this matrix.

## Transaction capture workflow matrix

| ID | Situation | Primary oracle | Coverage |
| --- | --- | --- | --- |
| TX-01 | Complete expense | Preview is ledger-neutral; confirm posts balanced expense | deterministic API + real-model smoke |
| TX-02 | Progressive expense | Stable question order and short-answer continuation | deterministic API + real-model smoke |
| TX-03 | Preview correction | Candidate changes; old preview guard becomes stale | deterministic API |
| TX-04 | Ambiguous category | Safe options only; selection leads to preview | deterministic scenario + real-model smoke |
| TX-05 | Income | Correct account/category posting signs | adapter tests + real-model smoke |
| TX-06 | Transfer | Two account postings, same currency, zero sum | adapter tests + real-model smoke |
| TX-07 | Adjustment | User posting plus hidden system counterparty | adapter/service tests + real-model smoke |
| TX-08 | Authoritative reference invalidated | Candidate field cleared and corrected before write | deterministic API |
| TX-09 | Cancel before confirmation | No transaction; conversation may accept new work | deterministic API |
| TX-10 | Exact confirm replay | Same response and transaction; no duplicate | deterministic API |
| TX-11 | Structured model failure | Safe `502`; trace/raw output absent | interpretation/API tests |
| TX-12 | Cross-currency or archived reference | Corrective result or authoritative rejection | adapter/service tests |
| TX-13 | Misspelled account or category | Model selects only a valid offered reference; draft remains reviewable | interpretation tests + real-model smoke |
| TX-14 | Explicit currency conflicts with account | Currency is preserved, account is cleared, and compatible account is requested | processor/API tests + real-model smoke |
| TX-15 | Active short reply or correction | Exactly one interpretation call; partial update preserves other draft fields | processor tests + real-model smoke |

## Current wallet state workflow matrix

| ID | Situation | Primary oracle | Coverage |
| --- | --- | --- | --- |
| ST-01 | Empty wallet | Empty arrays and deterministic message | deterministic API |
| ST-02 | Multiple active accounts | Stable name ordering and posting-derived balances | deterministic seeded API |
| ST-03 | Multiple currencies | Separate per-currency totals; never sum unlike currencies | deterministic seeded API |
| ST-04 | Archived and system accounts | Excluded from public state | deterministic seeded API |
| ST-05 | Read-only execution | Transaction list byte-for-byte unchanged | deterministic seeded API |
| ST-06 | Replay after external ledger change | Replay returns old snapshot; new turn returns fresh state | deterministic API |
| ST-07 | State/capture ambiguity | Router clarifies while idle; a later clear message selects state | deterministic API |
| ST-08 | State request during capture | Preserves capture and asks the user to finish or cancel it | cross-workflow API test |
| ST-09 | State after confirmed capture | Reports the newly derived balance in the same conversation | cross-workflow API test |

## Privacy and presentation checks

Public bodies and smoke output must not contain:

- model prompts or raw model responses;
- interpretation or processing traces;
- complete Wallet catalogs;
- private capability state;
- exception stack text or transport details.

Deterministic API tests inspect successful and failed serialized responses. Interpretation and
processing tests separately prove that only safe labels, account currencies, and per-call opaque
keys reach model prompts and public projections.

## Chat UI acceptance matrix

Run these cases in order at `http://localhost:5173/assistant` against the seeded stack. Start
a new chat where noted and correlate each turn with one `trace_id` in the backend event stream.

| ID | UI input or action | Visible oracle | Log oracle |
| --- | --- | --- | --- |
| UI-01 | New chat: `show balance` | Wallet balance card; no active task | `start` → `wallet.current_state`; one Ollama call; `state_shown` |
| UI-02 | New chat: `I need to do something with my balance` | Friendly task clarification | `clarify` with both capability candidates; one Ollama call |
| UI-03 | New chat: `cancel my gym membership` | Unsupported message; no task | `unsupported`; one Ollama call; no control instruction |
| UI-04 | New chat: `cancel and show my balance` | Request to split the control and domain work | `compound_control`; one Ollama call; no partial execution |
| UI-05 | New chat: `Increase Pocket wallet balance by ARS 700` | Adjustment preview with Confirm | one routing call, then one interpretation call; capture reaches `preview` |
| UI-06 | While UI-05 is active: `show balance` | Adjustment remains active and handles the message within capture | direct `ContinueCurrent`; one interpretation call; no routing or wallet-state execution |
| UI-07 | While UI-05 is active: `actually 750` | Preview changes to ARS 750 | direct `ContinueCurrent`; one interpretation call; no routing call |
| UI-08 | Help, Restart, and Cancel buttons | Matching lifecycle response; task preserved/reset/cleared | Typed control input; no routing or Ollama event |
| UI-09 | Complete expense, then Confirm | Recorded response; task completes; withdrawal appears on Transactions page | Confirm is typed task action; no routing/Ollama event; exactly one balanced transaction |
| UI-10 | After UI-01: `one more time` | Wallet balance card is shown again; no active task | `start` → recent `wallet.current_state`; one Ollama call; `state_shown` |

The matrix verifies the user-visible projection and the architectural boundary together. A
correct-looking response is not sufficient when the log path contradicts it, and a correct
route event is not sufficient when the UI loses the active task or exposes stale actions.

## Commands and acceptance gates

Fast deterministic feedback:

```bash
make test-control
```

Required before handoff:

```bash
make verify
```

Model-dependent acceptance when Ollama is available:

```bash
make check-router-smoke
make check-capture-smoke
```

A control-layer change is accepted only when deterministic tests pass, changed public schemas
are regenerated and checked when applicable, the test matrix remains accurate, and any
model-facing behavior change passes the real-model smoke suite.

## Extension rule

Every new capability must add:

1. a deterministic data profile;
2. routing profiles plus start, continuation, ambiguity, unsupported, and active-conflict cases;
3. active/completed lifecycle cases as applicable;
4. action guard and replay cases for every offered action;
5. authoritative read/write oracles against Wallet services;
6. cross-workflow isolation cases with every existing foreground capability;
7. safe public projection and failure cases;
8. real-router coverage for representative ownership boundaries, plus a real-service scenario
   when capability execution itself depends on a model or external service.
