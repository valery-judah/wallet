# HLD Reference

Use this reference while producing or reviewing an HLD.

## Input Model

```text
Product Frame
  - Intent
  - Core experience
  - Capabilities
  - MVP boundary
  - Learning agenda
+
Current system / environmental context
+
Hard technical constraints
+
Relevant evidence
        ↓
High-Level Design
```

For brownfield changes, current contracts, ownership, dependencies, data, operational assumptions, compatibility constraints, and migration constraints may materially shape the design.

## Design Readiness

Classify missing information before designing:

| Missing information | Action |
|---|---|
| Changes externally meaningful behavior or MVP scope | Return to `product-framing` |
| Changes architecture and can be inspected/researched | Acquire evidence |
| Requires exercising/comparing a candidate | `prototype` |
| Requires empirical measurement | `experiment` |
| Does not materially change HLD | Use a reversible working assumption or leave unspecified |

Do not run exhaustive discovery. Resolve only uncertainty that blocks a consequential system-level decision.

## Derive Architectural Obligations

Translate product commitments into system-level obligations before drawing architecture.

Example:

```text
Product commitment:
Users approve generated changes before publication.

Derived system invariant:
No publication transition may occur without an approved state.

HLD questions:
- Which component owns publication state?
- Where is the invariant enforced?
- What happens under partial failure or duplicate delivery?
```

The HLD owns the derived invariant and architectural consequences. It does not change the upstream commitment.

## Design Drivers

A design driver is a requirement, constraint, or system property that can actually change architecture.

Prefer:

- `Submission acknowledgement must remain available when workers are unavailable.`
- `A publication must never occur without prior approval.`
- `Processing may complete asynchronously after acknowledgement.`

Avoid context-free platitudes:

- `The system should scale.`
- `The system should be secure.`
- `Use high availability.`

Quantify only when the quantity can affect a system-level decision.

## Simplest Coherent Architecture

Start with the minimum architecture that can satisfy core capabilities and invariants.

For every component ask:

> Which requirement, constraint, property, or decision makes this component necessary?

If there is no answer, remove it.

Add complexity only when a design driver or identified weakness requires it. Cache, queue, replication, sharding, extra services, and other machinery are not defaults.

## Walk Key Flows

Use a small number of important end-to-end flows to test the architecture.

For each relevant flow identify:

```text
actor / caller
→ logical interface
→ responsible component(s)
→ state read or changed
→ source of truth
→ asynchronous boundary, if any
→ externally meaningful result
```

Also examine architecturally relevant failure or lifecycle branches when they can change a decision.

Do not expand into detailed endpoint payloads, table schemas, code paths, or algorithms.

## Decision Point Test

A choice is an HLD decision when materially different alternatives affect at least one of:

- correctness or invariant preservation;
- availability or consistency behavior;
- latency/throughput at relevant scale;
- state ownership or coupling;
- failure isolation/recovery;
- security or trust boundaries;
- compatibility/migration;
- operational complexity or cost;
- future constraints that are already known and consequential.

Do not record ordinary implementation choices as HLD decisions.

## Decision Record

```markdown
### D<n> — <decision question>

**Drivers**
- ...

**Alternatives**
- A — ...
- B — ...

**Evidence**
- ...  # omit when no delegated learning was needed

**Decision**
Choose ...

**Why**
...

**Trade-offs accepted**
- ...

**Reconsider if**
- ...
```

The architecture may only rely on consequential choices that are visible in these decisions or are directly forced by a hard constraint.

## Learning Contract

HLD owns:

```text
question
→ alternatives
→ decision criteria
→ interpretation of evidence
→ final architectural decision
```

`prototype` / `experiment` own:

```text
learning method
→ execution
→ observations
→ evidence
→ limitations
```

A spike can use any convenient implementation detail necessary to learn. Those details do not become architecture automatically.

```text
Prototype used Redis
        ≠
HLD chose Redis
```

The justified architectural conclusion may instead be:

```text
The design requires a shared low-latency ephemeral state store.
```

Only promote a concrete technology into the HLD when the technology itself is a system-level constraint or the evidence establishes that materially different technologies would not satisfy the same architectural requirement.

## Assumptions and Evidence

Maintain these only when they are decision-relevant:

```markdown
### Known
Facts supported by product/system evidence.

### Assumed
Reversible assumptions safe enough for HLD.

### Unresolved
Questions that block or may reopen named decisions.
```

Never allow:

```text
guess
→ treated as fact
→ architecture built on guess
→ implementation treats architecture as fact
```

## Reopening Decisions

When new evidence contradicts an assumption:

```text
new fact
→ identify invalid assumption
→ identify dependent decisions
→ reopen those decisions
→ update architecture
→ update downstream constraints
```

Do not preserve a stale architecture by accumulating compensating components or implementation patches.

## Output Contract

```markdown
# <System / Change> High-Level Design

## 1. Problem and Scope
- Outcome this design must enable
- In scope
- Explicitly out of scope

## 2. Design Drivers
- Only requirements/constraints that shape architecture

## 3. System Context
- Relevant actors, existing components, dependencies, hard constraints
- Decision-relevant known / assumed / unresolved items

## 4. Proposed Architecture
- Components and responsibilities
- Logical relationships
- One high-level diagram when useful

## 5. Key System Flows
- Only flows necessary to understand or verify the architecture

## 6. Data and State
- Logical ownership
- Sources of truth
- Major state transitions
- Persistence categories
- Consistency requirements
- No physical schema unless it is itself an architectural constraint

## 7. Design Decisions
- D1...
- D2...

## 8. Failure and Operating Model
- Architecturally relevant failure behavior
- Isolation, recovery, backpressure, availability, security/trust concerns as applicable

## 9. Driver Check
- Show how each design driver is satisfied
- Surface unresolved violations

## 10. Risks and Open Questions
- Only consequential residual risks/unknowns

## 11. Implementation Handoff

### Implementation must preserve
- system invariants
- ownership/boundaries
- logical interfaces/flows
- selected architectural decisions
- required system properties

### Intentionally unspecified
- implementation choices left open because they do not affect HLD
```

## Review Questions

Before finalizing:

1. Did the HLD invent or alter product intent?
2. Which claims about the current system are evidence-backed?
3. Is any actor, dependency, state owner, or important flow missing?
4. Did the design commit to the first plausible architecture?
5. Does every component trace to a driver or decision?
6. Are relevant alternatives and accepted trade-offs explicit?
7. Did any prototype/experiment output get mistaken for a decision?
8. Did the design drift into implementation detail?
9. Did later evidence invalidate an earlier assumption or decision?
10. Can implementation proceed without inventing system-level behavior?
