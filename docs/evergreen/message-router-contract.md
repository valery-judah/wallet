# Message Router Contract

Status: implemented MVP contract  
Date: 2026-08-06

## Purpose

The message router selects new work for an idle conversation. It does not route messages while a
task is active.

This gives each layer one authority:

| Layer | Authority |
| --- | --- |
| `ExactControlRecognizer` | Recognize supported whole-message textual controls |
| `MessageRouter` | Select a registered capability for one idle natural-language message |
| `ConversationEngine` | Enforce lifecycle, guards, execution, and publication |
| Active capability | Own and interpret every non-control message until completion or cancellation |

The router proposes semantic ownership only. It cannot execute a capability, mutate lifecycle
state, switch an active task, interpret domain fields, or construct domain data.

## Resolution precedence

The controller resolves every turn in this order:

1. Typed task actions and typed controls.
2. Exact whole-message textual controls.
3. Direct continuation of the active capability, when one exists.
4. LLM message routing, only when the conversation is idle.

```text
incoming turn
    |
    +-- typed action/control ------------> controller branch
    |
    +-- exact textual control -----------> controller control branch
    |
    +-- active task ----------------------> active capability
    |
    `-- idle ordinary message -----------> LLM router -> new-task decision
```

The textual controls are normalized for case, surrounding and repeated whitespace, and trailing
`.`, `!`, or `?`. Recognition still requires the entire normalized message to equal a supported
control:

- cancel: `cancel`, `stop`, `never mind`;
- restart: `restart`, `start over`;
- help: `help`, `what can you do`.

Consequently, `Cancel!` is a control, while `don't cancel`, `cancel my membership`, and
`cancel and show my balance` are ordinary messages.

While a task is active, every ordinary message goes directly to that capability. This includes
short answers, corrections, complete rephrasings, apparent requests for another capability,
false controls, and compound phrases. Such messages cannot cancel, restart, or switch the task.
The user must finish the task or send an exact or typed control.

## Router input contract

`MessageRouter.route()` receives:

1. the complete original user message;
2. `MessageRoutingContext`, containing only `recent_capability_id` or `None`;
3. all registered `CapabilityDefinition` values.

The original message is sent as untrusted user content. The system prompt contains the routing
policy, bounded routing context, capability definitions, and output schema.

The router never receives:

- raw previous user or assistant turns;
- an active capability ID or active-task state;
- transaction candidates or Wallet catalogs;
- capability-private prompts or model output;
- service objects, request IDs, task IDs, or versions;
- prior reasoning or raw retry output.

An active capability ID is unnecessary because the router is never called while a task is
active.

## Bounded routing memory

`recent_capability_id` identifies the capability most recently executed successfully in the
conversation. It is retained internally and is not part of the public conversation projection.

The model may use it only to resolve an explicit reference to the preceding operation, such as:

- `one more time`;
- `again`;
- `repeat that`;
- `check again`.

For such a reference, the router may return `StartRouteDecision(recent_capability_id)`. The
recent identity is only an ownership hint. It does not retain or replay the previous message,
capability state, domain result, or side effect. For example, repeating transaction capture
starts a new capture; it cannot duplicate the previous transaction automatically.

Complete unrelated requests must be classified from their own content and must not be biased
toward the recent capability.

## Capability routing metadata

Every registered `CapabilityDefinition` contains a required `CapabilityRoutingProfile`:

- `routes_when`: positive descriptions of requests the capability owns;
- `examples`: representative complete messages;
- `counterexamples`: optional boundary examples owned elsewhere.

Registered capability IDs are the routing ontology. The router does not maintain a second intent
taxonomy. Expense, income, transfer, and balance adjustment therefore remain examples of
`transactions.capture`, rather than global intent identifiers.

The current registry distinguishes:

- `transactions.capture`: record an expense, income, transfer, or balance adjustment;
- `wallet.current_state`: read active-account balances and currency totals.

Capability implementations form an open registry. The router's result envelope remains a closed
union.

## Closed route decisions

`RouteDecision` contains exactly four immutable variants:

| Decision | Meaning while idle | Controller instruction |
| --- | --- | --- |
| `StartRouteDecision(capability_id)` | One registered capability owns the message | `Start` |
| `ClarifyRouteDecision(candidate_capability_ids)` | Ownership is genuinely ambiguous | `Clarify("idle_route_ambiguous")` |
| `UnsupportedRouteDecision()` | No registered capability owns the message | `Unsupported` |
| `CompoundControlRouteDecision()` | A control and domain request were combined | `Clarify("compound_instruction")` |

There is no `ContinueRouteDecision`. Continuation is determined before routing by the presence of
an active task.

Clarification candidates are internal validation and diagnostic metadata. Public responses use
friendly messages and do not expose capability IDs.

## Structured model call and validation

Each `LlmMessageRouter` attempt makes one schema-constrained `StructuredChatModel` call. The JSON
schema is built from the current registry and enumerates the registered capability IDs.

The application validates model output again after parsing:

- selected and candidate capability IDs must be registered;
- clarification candidates must be distinct;
- each variant may contain only its defined fields;
- the response must contain exactly one recognized decision shape.

Malformed, invented, or structurally invalid output receives one retry with compact validation
feedback. The feedback never contains the raw previous output. A second invalid result raises
`MessageRoutingError`.

Transport failures are not retried by the router. They are surfaced through the existing safe
`502` response.

## Lifecycle and failure guarantees

Routing happens before capability execution and conversation publication. If routing fails:

- no capability runs;
- the conversation version and state remain unchanged;
- the request ID is not committed to replay storage;
- the client may retry the identical request ID and payload.

A route decision cannot replace an active task because routing is unreachable while active.
Capability switching is intentionally unsupported.

## Privacy and observability

Successful routing emits `control.routing.completed` with:

- decision kind;
- selected capability ID or clarification candidate IDs;
- recent capability ID;
- attempt count;
- duration.

Exhausted model validation emits `control.routing.failed`. Model transport telemetry remains the
responsibility of the structured-chat adapter.

Routing events never contain message text, prompts, raw model output, capability-private state,
or Wallet data.

## Operational consequences

- Ollama is required for every ordinary message submitted while idle.
- Exact controls and typed inputs do not require message routing.
- Active messages do not incur router latency.
- A capability may independently require Ollama for its own domain interpretation; transaction
  capture currently does, while wallet-state execution is deterministic.
- A compound phrase is recognized by the LLM only while idle. While active, it is harmless
  capability input and cannot partially execute a control.

## Change and test obligations

When adding a capability:

1. define its routing profile;
2. register it in the capability registry;
3. add positive, counterexample, ambiguity, and recent-reference routing cases where relevant.

When adding a route-decision variant, update the closed union, structured schema, parsing,
validation, logging projections, resolver match, and strict-mypy exhaustiveness tests together.

The test suite must continue to prove:

- typed and exact controls bypass routing;
- active ordinary messages bypass routing and reach the current capability unchanged;
- all four idle decisions map to one controller instruction;
- invented IDs, duplicate candidates, extra fields, retry exhaustion, and transport failure are
  safe;
- routing failures publish no state and remain retryable with the same request ID;
- prompts and logs contain only the documented bounded context;
- the real-model idle corpus distinguishes wallet state, transaction capture, ambiguity,
  unsupported requests, compound controls, and recent-capability references.

The executable acceptance matrix lives in
[`control-layer-testing.md`](control-layer-testing.md).
