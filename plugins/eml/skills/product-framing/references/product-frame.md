# Product Frame Reference

Use this reference when the product boundary, actors, capabilities, or level of abstraction are unclear.

## Product model

A Product Frame describes the value and externally meaningful behavior a product or subsystem is intended to produce.

```text
Product Frame
├── Intent
│   ├── actors and situations
│   ├── jobs to be done
│   └── intended outcomes
├── Core experience
│   ├── primary end-to-end workflow
│   └── important supporting scenarios
├── Capabilities
├── MVP boundary
│   ├── included
│   └── explicitly excluded
└── Learning agenda
```

Existing-product reconstruction additionally records **Evidence status** and **Current observed boundary**.

## Actors

Identify roles by their relationship to value, not by organization title.

- **Operator** — directly operates the product or subsystem.
- **Beneficiary** — receives the intended outcome; may be the operator.
- **Artifact consumer** — consumes an output produced by the subsystem.
- **Affected actor** — is materially affected without necessarily operating or benefiting from it.

Do not multiply roles when one actor fills several of them. Distinguish them when doing so changes the job, workflow, evidence requirements, or product boundary.

## Situation, job, outcome

- **Situation** — the context or trigger in which the actor needs progress.
- **Job** — the progress the actor is trying to make, stated independently of the proposed implementation.
- **Outcome** — the observable result that indicates the job was accomplished.

A proposed feature is evidence about these fields, not a substitute for them.

## Core experience

Describe one coherent end-to-end value path:

`trigger → meaningful actions → product contribution → outcome / handoff`

Supporting scenarios belong here only when they materially affect the product model or MVP boundary.

## Capabilities

A capability states behavior that an actor or downstream consumer can depend on across the product/subsystem boundary.

**Externally meaningful** means observable or consequential outside that boundary. It does not require public user-facing behavior.

Boundary test:

> If the implementation changed completely while this observable behavior remained, would the actor or consumer still receive what it depends on?

If yes, describe the behavior. If no, the statement is probably an implementation mechanism.

Prefer:

- “retain evidence sufficient to diagnose an execution”
- “allow a judge to inspect the inputs, outputs, and resulting state”

Over:

- “capture distributed traces”
- “store artifact-relative references”

A mechanism belongs in the frame only when evidence establishes that the external consumer depends on that mechanism itself.

## Product commitments

Include a constraint or guarantee when it defines externally meaningful product behavior or is a hard external constraint.

Product commitment:

> Users approve generated changes before publication.

Derived system invariant:

> No `DRAFT → PUBLISHED` transition without `APPROVED`.

The first may belong in framing. The second belongs in system design.
