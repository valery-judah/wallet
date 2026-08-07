# Message Router Contract

Status: implemented MVP contract
Last reviewed: 2026-08-07

## Decision

Message routing selects new work only while a conversation is idle. Once a capability has an
active task, ownership is sticky: every non-control message goes directly to that capability
until it completes or is cancelled.

This is the central control rule:

> Route at the boundary between tasks, not between turns inside a task.

The rule uses each mechanism where it is strongest:

- deterministic matching recognizes the small closed set of global controls;
- lifecycle state determines whether a workflow already owns the conversation;
- the LLM classifies open-ended language only when new semantic ownership must be chosen;
- the selected capability interprets its own domain language;
- the control engine alone starts, continues, restarts, cancels, and publishes tasks.

The router proposes a capability ID. It cannot execute a capability, mutate conversation state,
switch an active task, extract transaction fields, construct commands, or perform a control.

## Responsibility boundaries

| Component | Authority |
| --- | --- |
| Public input models and control domain | Validate the closed turn-input envelopes and guard fields |
| `ExactControlRecognizer` | Recognize supported whole-message textual controls |
| `TurnResolver` | Apply precedence and produce one closed `TurnInstruction` |
| `MessageRouter` | Classify one idle natural-language message at capability-ownership level |
| `ConversationEngine` | Validate lifecycle and guards, execute one instruction, and project the result |
| Active capability | Interpret every non-control message delivered during its task |
| Turn coordinator and registries | Serialize conversation updates and commit successful request replays |

Capability implementations remain an open registry. Turn inputs, route decisions, controller
instructions, capability inputs, and capability results are closed unions dispatched
exhaustively.

## Resolution algorithm

`TurnResolver` handles one `TurnSubmission` in this order:

```text
TurnSubmission
    |
    +-- typed ControlActionSubmission ---> Help / guarded Cancel / guarded Restart
    |
    +-- typed TaskActionSubmission ------> guarded ContinueCurrent(CapabilityAction)
    |
    `-- MessageSubmission
            |
            +-- exact textual control ---> Help / Cancel / Restart
            |
            +-- active task -------------> ContinueCurrent(CapabilityMessage)
            |
            `-- idle --------------------> LLM MessageRouter
                                               |
                                               +-- Start
                                               +-- Clarify
                                               +-- Unsupported
                                               `-- compound clarification
```

Typed inputs bypass both textual-control recognition and message routing. Exact textual controls
bypass the active capability and the router. Only an idle ordinary message reaches the router.

The resolver chooses a route but executes nothing. The engine validates and executes the
resulting instruction afterward.

## Message normalization and exact controls

`MessageSubmission` accepts 1 to 4,000 characters after trimming surrounding whitespace. The
trimmed content remains otherwise intact. In particular, case, punctuation, and internal
spacing are preserved when the content is sent to a capability or the router.

The exact-control recognizer uses a separate comparison-only normalization:

1. Unicode-aware case folding;
2. collapsing whitespace runs to one space;
3. removing any trailing `.`, `!`, or `?` characters;
4. comparing the entire result with a known phrase.

Supported phrases are:

| Control | Exact phrases |
| --- | --- |
| Cancel | `cancel`, `stop`, `never mind` |
| Restart | `restart`, `start over` |
| Help | `help`, `what can you do` |

`Cancel!` and `Never   mind.` are controls. `don't cancel`, `cancel my membership`, and `cancel
and show my balance` are ordinary messages because the complete normalized message is not an
exact phrase.

Typed cancel and restart inputs carry an expected task ID and conversation version. Their guards
are validated before execution. Textual cancel and restart are deliberately unguarded: they act
on the task current at the time the serialized turn is processed. Help is unguarded in both
forms.

## Active-task ownership

When `conversation.current` exists, every non-control `MessageSubmission` becomes
`ContinueCurrent(CapabilityMessage(content))`. The LLM router is not called and no capability
profiles are consulted.

This includes:

- short answers such as `Cash`, `tomorrow`, or `actually 45`;
- corrections and complete rephrasings;
- text that resembles a request for another capability;
- false controls such as `don't cancel`;
- compound text such as `cancel and show my balance`.

Such a message cannot perform a global control or switch capabilities. It is still real
capability input, however, and the active capability may update its reviewable state from it. To
leave the workflow, the user must complete it or submit an exact or typed cancel/restart control.

This design avoids reclassifying context-dependent workflow replies. The capability already has
the private state needed to understand them; the idle router intentionally does not.

## Idle router input

`MessageRouter.route()` receives exactly:

1. the complete validated message content, after surrounding whitespace was trimmed;
2. `MessageRoutingContext`, containing `recent_capability_id` or `None`;
3. every registered `CapabilityDefinition`.

`LlmMessageRouter` sends the message alone as untrusted user content. Its trusted system prompt
contains the routing policy, bounded recent-capability context, capability descriptions and
routing profiles, the dynamic output schema, and compact retry feedback when needed.

The router does not receive:

- previous user or assistant messages;
- an active capability ID or active-task state;
- transaction candidates, pending interactions, or Wallet catalogs;
- capability-private prompts or previous model output;
- service or repository objects;
- request, conversation, task, operation, or version identifiers;
- prior reasoning or domain results.

An active capability ID is absent because reaching the router proves that no task is active.

## Bounded recent-capability memory

`Conversation.recent_capability_id` is internal control metadata. After a turn commits, the engine
stores `outcome.capability_id` when the outcome is capability-associated; otherwise it preserves
the previous value.

Consequently, memory is updated after a committed capability start, continuation, completion, or
restart. It is retained through help, clarification, unsupported input, no-op controls, and
cancellation. A cancelled capability can therefore remain the recent capability after the
conversation becomes idle.

The value is not exposed in the public conversation projection and is read by the router only
while idle. The prompt receives the recent capability's ID and description and marks the matching
profile as recent.

The model may use this identity for explicit reference-only requests such as:

- `one more time`;
- `again`;
- `repeat that`;
- `check again`.

For such a message, the router may return `StartRouteDecision(recent_capability_id)`. This starts
the capability with the new message; it does not replay the previous message, restore capability
state, reuse a previous draft, or repeat a domain side effect. Repeating wallet state produces a
fresh deterministic snapshot. Repeating transaction capture starts a fresh capture and may need
new details.

Complete requests must be classified from their own content. Recent identity is not a general
conversation-history bias.

## Capability routing metadata

Every `CapabilityDefinition` contains:

- a stable lowercase capability ID;
- a nonblank user-facing description;
- a required `CapabilityRoutingProfile`.

Each profile has:

- nonempty `routes_when` ownership descriptions;
- nonempty positive `examples`;
- optional `counterexamples` describing boundaries owned elsewhere.

The registry must be nonempty and rejects duplicate IDs. Registered capability IDs are the only
routing ontology; there is no separate global intent enum. Expense, income, transfer, and balance
adjustment are therefore examples owned by `transactions.capture`, not top-level route kinds.

The current production registry contains:

| Capability ID | Ownership |
| --- | --- |
| `transactions.capture` | Collect and record one expense, income, transfer, or balance adjustment |
| `wallet.current_state` | Show current active accounts and balances by currency |

Profiles may contain boundary examples phrased as active-workflow answers. They are prompt
metadata only: runtime ownership of an active message was already decided structurally before
the router could be called.

## Closed route decisions

`RouteDecision` contains exactly four frozen variants:

| Decision | Idle meaning | Resolver output |
| --- | --- | --- |
| `StartRouteDecision(capability_id)` | One registered capability owns the message | `Start(capability_id, content)` |
| `ClarifyRouteDecision(candidate_capability_ids)` | Ownership is ambiguous | `Clarify("idle_route_ambiguous")` |
| `UnsupportedRouteDecision()` | No registered capability owns the message | `Unsupported()` |
| `CompoundControlRouteDecision()` | A global control and domain request were combined | `Clarify("compound_instruction")` |

There is no `ContinueRouteDecision`. Continuation is decided before routing from
`conversation.current`.

Clarification candidate IDs are internal diagnostic metadata. The tuple may be empty or contain
one or more IDs, but every supplied ID must be registered and distinct. Candidate IDs are not
published; the public outcome uses a generic clarification message.

A start decision always creates new capability work. It cannot resume state or replace an active
task because routing is unreachable while active.

## Model schema and application validation

Each attempt makes one `StructuredChatModel.complete()` call. The output schema is built from the
current registry and uses a closed `oneOf`; capability fields enumerate the registered IDs and
every variant forbids additional properties.

Before calling the model, the router checks that:

- at least one capability is registered;
- registered IDs are unique;
- a recent capability ID, when present, is registered.

After parsing, application code validates again that:

- the response matches exactly one known discriminated variant;
- a start ID is registered;
- clarification IDs are registered and distinct;
- no variant contains fields owned by another variant.

Invalid JSON, malformed shapes, invented IDs, duplicated candidates, and context-inconsistent
output receive one retry. Retry feedback describes the validation problem but never reproduces
the raw model output. A second invalid response raises `MessageRoutingError`.

Transport and structured-chat adapter failures are not retried by the router. They propagate to
the control engine and become the existing safe `502` response.

There is no keyword fallback, confidence threshold, shadow classifier, transcript lookup,
embedding search, or partial route execution.

## Lifecycle and failure guarantees

Routing occurs inside the conversation transition, before capability execution is committed.
When routing or later processing fails:

- no new conversation is inserted and no existing conversation is replaced;
- no capability result is published;
- no successful replay snapshot or request fingerprint is stored;
- the failed request ID is not reserved and can be retried;
- the API returns the safe conversation-processing `502` for model-related failures.

Conversation updates are serialized per conversation. Successful request IDs are serialized
globally and replay the stored response only when the request fingerprint matches.

Because the router is unreachable while active, it cannot replace a task. Capability switching
is intentionally unsupported.

## Privacy-safe observability

Successful routing emits `control.routing.completed` with:

- decision kind;
- selected capability ID, when present;
- clarification candidate IDs;
- recent capability ID;
- attempt count;
- duration.

Exhausted model validation emits `control.routing.failed` with recent capability ID, attempt
count, duration, and a stable error code. Transport telemetry is emitted by the structured-chat
adapter.

Routing events never contain message text, prompts, raw model output, capability-private state,
Wallet catalogs, or domain data.

## Operational consequences

- Ollama is required for every ordinary idle message.
- Typed inputs and exact textual controls bypass the router.
- Active ordinary messages incur no router call or router latency.
- Starting transaction capture requires routing and then a separate model interpretation call.
- Continuing transaction capture requires only its interpretation call.
- Wallet-state execution is deterministic after the idle routing call.
- Compound-control classification belongs to the LLM only while idle. During an active task, the
  same text is ordinary capability input and cannot execute a global control.
- Conversation state and recent-capability memory are process-local.

## Change and test obligations

When adding a capability:

1. define its description and routing profile;
2. register it in the capability registry;
3. add positive, counterexample, ambiguity, unsupported, and recent-reference cases where
   relevant;
4. verify active-task messages still bypass routing.

When adding a route-decision variant, update the union, model schema, parser, validation,
logging projections, resolver match, strict-mypy exhaustiveness checks, and tests together.

The suite must continue to prove:

- typed inputs bypass both textual recognition and routing;
- exact controls bypass routing in idle and active states;
- active ordinary messages reach the current capability unchanged after boundary trimming;
- all four route decisions map to their one idle instruction;
- router prompts contain only the documented message, bounded memory, definitions, and schema;
- unknown IDs, duplicate candidates, extra fields, retry exhaustion, and transport failure are
  safe;
- failed turns publish no conversation mutation or successful replay;
- routing logs exclude message and model content;
- the real-model corpus distinguishes wallet state, transaction capture, ambiguity,
  unsupported input, compound controls, and recent-capability references.

The executable acceptance matrix lives in
[`control-layer-testing.md`](control-layer-testing.md).

## Implementation anchors

- [`routing.py`](../../backend/src/wallet/ai/control/routing.py): route union, prompt, schema,
  validation, retry, and routing events;
- [`resolution.py`](../../backend/src/wallet/ai/control/resolution.py): precedence, exact controls,
  active-task bypass, and idle decision mapping;
- [`engine.py`](../../backend/src/wallet/ai/control/engine.py): lifecycle validation, execution,
  bounded memory update, and publication;
- [`contract.py`](../../backend/src/wallet/ai/capabilities/contract.py): capability definitions and
  routing profiles;
- [`test_resolution.py`](../../backend/tests/ai/control/test_resolution.py) and
  [`test_routing.py`](../../backend/tests/ai/control/test_routing.py): executable routing contract.
