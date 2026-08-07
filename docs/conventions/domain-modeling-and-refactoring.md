# Domain Modeling and Refactoring

This guide defines the repository convention for modeling domain decisions as
explicit types and refactoring conditional code toward exhaustive,
compiler-checked routing. The approach is used by control-layer submissions and
instructions, capability inputs and results, and idle route decisions.

The goal is not to replace every conditional with structural pattern matching.
The goal is to make closed domain alternatives visible in the type system, make
illegal combinations difficult or impossible to construct, and make missing
dispatch branches fail static analysis.

## Core Approach

Begin with the domain decision, not with the syntax used to implement it.

For any branch, ask:

1. Does this branch select between a known, closed set of alternatives?
2. Does each alternative carry different data or enforce different invariants?
3. Should adding an alternative require every dispatcher to be reviewed?

When all three answers are yes, model the alternatives as immutable dataclasses,
combine them in an explicit union, and dispatch with an exhaustive `match` that
ends in `assert_never()`.

For example, the control layer resolves one public submission into exactly one
of seven internal turn instructions. The instruction family is closed:

```python
@dataclass(frozen=True, slots=True)
class ContinueCurrent:
    capability_input: CapabilityInput


@dataclass(frozen=True, slots=True)
class Start:
    capability_id: str
    content: str | None


@dataclass(frozen=True, slots=True)
class Cancel:
    pass


# Restart, Help, Clarify, and Unsupported omitted here for brevity.

TurnInstruction: TypeAlias = (
    ContinueCurrent | Start | Cancel | Restart | Help | Clarify | Unsupported
)
```

The class is the discriminator. A parallel `kind` enum, visitor hierarchy, or
handler registry is unnecessary when matching happens inside the application
and no serialization format requires a separate discriminator.

## Choosing the Modeling Mechanism

Use the smallest mechanism that accurately represents the domain.

| Domain shape | Preferred mechanism | Example |
| --- | --- | --- |
| Closed alternatives with different payloads | Immutable dataclass variants plus a `TypeAlias` union | `TurnInstruction`, capability results |
| Closed alternatives with no variant-specific payload | `Enum` or `StrEnum` | A stable operation or lifecycle label |
| Open set of implementations | `Protocol` plus composition or registration | Capability implementations |
| Open vocabulary owned by individual implementations | Validated string | Capability action and outcome names |
| Presence, validation, ordering, or threshold predicate | Ordinary `if` | Missing conversation, invalid version, empty matches |
| External or untrusted runtime shape | Runtime checks and parsing | JSON-like model output or projection data |

A closed outer family may still contain an open inner vocabulary. For example,
`CapabilityInput` can be closed to `CapabilityMessage | CapabilityAction` while
`CapabilityAction.action` remains a string owned by each capability. Closing the
input channel does not require centralizing every capability-specific action.

### Prefer Variants When Payload Depends on Status

An enum tag combined with several optional fields often hides an algebraic type.
For example:

```python
class ResultStatus(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass
class Result:
    status: ResultStatus
    state: object | None
    view: View | None
    domain_result: dict[str, object] | None
```

This permits combinations that the domain rejects, such as an active result
without state or a completed result with active state. Runtime validation can
reject those combinations, but callers still see optional fields after checking
the status.

Prefer separate shapes:

```python
@dataclass(frozen=True, slots=True)
class ActiveCapabilityResult(Generic[StateT]):
    state: StateT
    view: CapabilityView
    outcome_kind: str
    message: str


@dataclass(frozen=True, slots=True)
class CompletedCapabilityResult:
    view: CapabilityView | None
    outcome_kind: str
    message: str
    domain_result: dict[str, object] | None = None


CapabilityResult: TypeAlias = (
    ActiveCapabilityResult[StateT] | CompletedCapabilityResult
)
```

The variants remove structural invalidity. Their individual constructors should
still validate value-level constraints such as nonblank messages, identifier
syntax, or minimum collection sizes.

### Type Aliases Describe Families; They Do Not Construct Values

A `TypeAlias` union is an annotation, not a compatibility constructor. After
`CapabilityResult` becomes an alias, callers must construct
`ActiveCapabilityResult(...)` or `CompletedCapabilityResult(...)`; calling
`CapabilityResult(...)` is no longer valid.

Treat this conversion as a Python interface change even when HTTP schemas and
user-visible behavior remain unchanged. Update every in-repository producer in
the same change. Preserve an old constructor only when a real external consumer
requires a deliberate migration period.

### Keep Enums When the Alternatives Are Labels

An enum remains appropriate when every alternative carries the same data and the
domain needs a stable label. Matching an enum can also be exhaustive:

```python
match operation:
    case Operation.CREATE:
        ...
    case Operation.UPDATE:
        ...
    case _ as unreachable:
        assert_never(unreachable)
```

Do not split a simple enum into empty dataclasses solely to use class patterns.
The additional types should buy stronger payload modeling or clearer behavior.

## Exhaustive Dispatch

Closed unions should be dispatched with structural pattern matching and a
terminal `assert_never()` branch:

```python
match instruction:
    case Start(capability_id=capability_id, content=content):
        ...
    case ContinueCurrent(capability_input=capability_input):
        ...
    case Cancel():
        ...
    case Restart():
        ...
    case Help():
        ...
    case Clarify(code=code):
        ...
    case Unsupported():
        ...
    case _ as unreachable:
        assert_never(unreachable)
```

This branch is not intended as a normal runtime fallback. Under the declared
type, it is unreachable. Its purpose is to make mypy reject the dispatcher when
a union member is added without a matching branch.

This guarantee applies to typed code that mypy analyzes. It does not validate
objects arriving through `Any`, untyped integrations, or external serialized
data. Validate those values at their boundary before treating them as members
of the closed family. An `assert_never()` branch is a static exhaustiveness
guard, not a substitute for runtime parsing.

Exhaustiveness only works systemically when all route dispatchers follow the
same convention. A dispatcher that ends in a permissive `else`, a catch-all that
returns a default, or an implicit “all remaining variants” branch will not force
review when the family grows.

### Destructure the Data Used by the Branch

Prefer:

```python
case Start(capability_id=capability_id, content=content):
```

over matching only the class and repeatedly reading attributes afterward. Field
patterns show what data the route consumes and keep each branch locally clear.

Match guards are appropriate for value predicates inside a variant, but they do
not turn an open value such as a string into a closed family. Unsupported string
values remain expected runtime inputs, not `assert_never()` cases.

### Narrow Before Reading Variant-Specific Data

Fields that belong to only one variant are intentionally unavailable through
the whole union. Match the value before reading them, or pass the matched value
through a common normalization step.

For example, only a completed capability result carries `domain_result`. The
control engine first converts either result variant into a `TurnOutcome`; code
that needs the normalized view or domain result then reads the outcome instead
of reaching through an unnarrowed `CapabilityResult`.

## Separate Resolution, Validation, and Execution

A useful routing design has three distinct responsibilities:

1. **Resolution** translates public input into one internal instruction.
2. **Validation** rejects instructions that are illegal for the current state.
3. **Execution** performs the behavior associated with the validated instruction.

The resolver should choose a route without executing capability behavior. The
validator should enforce state and guard rules without duplicating execution.
The executor should exhaustively handle every internal instruction.

This separation makes the domain flow easier to understand:

```text
public submission -> resolved instruction -> legality check -> execution outcome
```

Both validation and execution may match the same closed family for different
reasons. That is not accidental duplication: adding a new instruction should
require an explicit decision about both its legality and its behavior.

## Immutability and Invariants

Domain variants should normally use `@dataclass(frozen=True, slots=True)`.

- `frozen=True` prevents variant fields from being rebound after resolution.
- `slots=True` keeps the value shape explicit and avoids accidental attributes.
- `__post_init__` is the boundary for normalization and value validation.

Normalize identifiers and bounded textual values when the variant is created.
Copy mutable input containers, such as action payload dictionaries, so callers
cannot mutate stored data through a retained external reference.

Dataclass freezing is shallow. It prevents attribute reassignment, while a
stored dictionary or list can still be mutated through the domain object. A
defensive copy prevents aliasing with the caller but does not make the copied
container deeply immutable. Use tuples, frozen collections, or read-only
interfaces when the domain requires that stronger guarantee.

Use variants to eliminate shape-level invalidity, and constructor validation to
eliminate value-level invalidity. These are complementary practices.

## Refactoring Method

Apply this style incrementally. A reliable sequence is:

### 1. Inventory the Branches

Search for `isinstance`, status and kind comparisons, implicit `else` routes,
and matches without terminal exhaustiveness guards. Identify every producer and
consumer of the candidate family before changing its representation.

### 2. Classify the Decision

Decide whether each branch is:

- closed route dispatch;
- enum dispatch;
- an open extension point;
- validation or an ordinary predicate;
- external representation parsing or normalization.

Only the first two categories normally receive exhaustive matching.

### 3. Design Variants Around Required Data

Give each alternative exactly the data required by its behavior. Avoid fields
that are meaningful only under a separate status or kind. Put invariants on the
variant that owns them.

Choose names that state the domain decision, not the technical mechanism. A name
such as `StartRouteDecision` communicates more than `RouteVariantA`.

### 4. Change Producers First

Update resolvers, selectors, factories, and capability implementations to create
the new concrete variants. Keeping construction explicit makes incomplete
migrations easy to find.

### 5. Change Consumers to Exhaustive Matches

Replace type-routing `isinstance` or tag chains with `match`. Destructure the
fields used by each branch and end with `assert_never()`.

Keep ordinary predicates inside the branch as conditionals. For example, after
matching `CapabilityAction`, checking whether its open action string is
`"confirm"` remains a normal runtime decision.

Search for attribute access through the old combined representation as well as
status comparisons. Variant-specific fields must move into matched branches or
be read from a common normalized result produced after matching.

### 6. Remove Transitional Representation

Once all producers and consumers use the new family, remove obsolete base
classes, status enums, duplicate discriminators, optional payload fields, and
fallback branches. Avoid maintaining two representations unless an external
compatibility boundary requires it.

### 7. Verify Behavior and Exhaustiveness

Run targeted tests while migrating, then run the full repository verification
for any code change:

```bash
make verify
```

Strict mypy is part of the design. Passing runtime tests without passing mypy is
not completion for an exhaustive routing refactor.

## Testing Practices

Test the domain contract at three levels.

### Construction Tests

Verify that:

- every intended variant can be constructed;
- immutable variants reject mutation;
- normalization occurs at construction;
- remaining value-level invariants reject invalid values.

When the exact union membership is an important internal contract, a focused
test may assert its members with `typing.get_args`. Do not repeat this for every
small private union; mypy and dispatcher coverage usually provide enough value.

### Route and Outcome Tests

Cover every input-to-variant route and every variant-to-outcome route. Tests
should assert observable behavior and important carried data, not base-class
inheritance or implementation-only control flow.

### Static Exhaustiveness

Every closed dispatcher should end in `assert_never()`. Strict mypy then acts as
the change detector when a new variant is introduced. Runtime tests remain
necessary because type checking cannot validate normalization, persistence, or
domain side effects.

## Commenting and Readability

Comments should explain the modeling decision, not restate Python syntax.

Useful comments include:

- why a union is intentionally closed;
- why a terminal branch calls `assert_never()`;
- why several variants are legal in a validation phase but behave differently
  during execution;
- why an apparently closed value remains open for capability extensibility.

Use a short docstring on central dispatchers to describe their responsibility,
such as “translate one public submission into exactly one internal instruction”
or “execute exactly one validated instruction.”

Avoid comments on every `case`. Well-named variants and destructured fields
should make individual branches readable without narration.

## What Not to Convert

Do not turn the following into algebraic families merely for stylistic
consistency:

- `None` checks;
- input validation and normalization;
- collection length or membership tests;
- stale-version and ownership guards;
- retry and error-recovery logic;
- precedence-based recognition pipelines;
- runtime checks for untrusted dictionaries or model output;
- representation normalization;
- capability-specific action strings and outcome strings;
- registries or protocols whose implementations are intentionally open.

An `if` is not a design smell by itself. The smell is a closed domain choice
whose alternatives and payload rules are hidden across conditionals.

## Established Models

These closed families currently establish the convention in the AI control
layer:

| Family | Variants | Primary exhaustive consumers |
| --- | --- | --- |
| `TurnSubmission` | Message, control action, task action | Fingerprinting and turn resolution |
| `TurnInstruction` | Continue, start, cancel, restart, help, clarify, unsupported | Legality validation and execution |
| `CapabilityInput` | Message and capability action | Capability input handling |
| `CapabilityResult` | Active and completed | Control-engine lifecycle application |
| `RouteDecision` | Start, clarify, unsupported, compound control | Idle message routing and resolver mapping |

The concrete class is the discriminator for each payload-bearing alternative.
Adding a variant should make strict mypy identify every exhaustive consumer that
requires a new decision.

## Remaining Opportunities

The following areas may benefit from the same approach. They should be handled
as focused refactors rather than one repository-wide syntax conversion.

| Area | Current shape | Potential model | Priority |
| --- | --- | --- | --- |
| Candidate assessment | Existing private union with implicit remaining branch | Exhaustive matches with `assert_never()` | High, low effort |
| Pending interaction | Kind enum plus field/options invariants | Request, correct, disambiguate, and clarify variants | Medium, broader impact |
| Transaction capture state | Phase enum plus phase-dependent invariants | Active and awaiting-confirmation state variants | Defer until state-machine complexity grows |

Candidate-field operations and transaction-type routing also use closed enums.
Where behavior genuinely covers every member, terminal `assert_never()` branches
can make future additions visible. For dictionary-based tables, a focused test
that compares table keys with the enum members may be clearer than replacing the
table with a long match.

## Review Checklist

Before accepting a domain-routing refactor, confirm that:

- the family is truly closed at the layer where it is modeled;
- every variant has a clear domain name and only its required data;
- variants prevent field reassignment and copy retained mutable inputs;
- shape-level invalid states are excluded by the declared types where practical;
- all producers create concrete variants directly;
- all closed dispatchers use `match` and terminal `assert_never()`;
- open strings and open implementation sets have not been centralized by
  mistake;
- ordinary validation remains straightforward;
- comments explain intent and boundaries;
- behavior, invariants, and immutability are tested;
- strict mypy and `make verify` pass;
- HTTP schemas, persistence, and public behavior remain unchanged unless their
  migration is explicitly part of the work.

The desired result is not more types or more pattern matching. It is a domain
model where valid alternatives are obvious, invalid combinations are difficult
to express, and the compiler points to every place that must change when the
domain grows.
