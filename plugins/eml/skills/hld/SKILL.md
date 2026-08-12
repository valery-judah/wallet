---
name: hld
description: Use when product framing is sufficiently defined to begin high-level system design, when an existing-system change needs architectural decisions before implementation, or when prototype/experiment evidence must be incorporated into a system-level design.
---

# High-Level Design

## Overview

Turn a Product Frame plus relevant system context into the **smallest coherent system-level design** that downstream implementation can realize without inventing architecture.

**Core invariant:** Every consequential architectural choice is an explicit decision tied to a design driver. Every architectural element exists because of a requirement, constraint, system property, or selected decision.

**Abstraction invariant:** Stop at the lowest level of detail needed to make the system-level decision. Leave realization choices to implementation.

**REQUIRED REFERENCE:** Read `reference.md` before producing the final HLD.

## Upstream Boundary

Prefer a completed `product-framing` artifact containing intent, core experience, capabilities, MVP boundary, and learning agenda.

- If ambiguity would change externally meaningful product behavior, return it to `product-framing`; do not choose product intent here.
- If a current-system fact is material to architecture, inspect or research it; do not invent it.
- Use a reversible assumption only when the assumption does not silently choose a consequential architecture.

## Workflow

1. Derive **system invariants** and **design drivers** from product commitments, constraints, system context, and relevant scale/operational facts.
2. Build the **simplest coherent architecture** that satisfies the core capabilities.
3. Walk the important end-to-end flows. Identify responsibilities, state ownership, major state transitions, and trust/failure boundaries.
4. Identify **consequential decision points**: places where plausible alternatives materially differ in requirements, system properties, complexity, cost, operability, or future constraints.
5. Resolve each decision against explicit drivers. Use existing evidence first.
6. When evidence is insufficient:
   - use `prototype` for questions that must be exercised, experienced, or compared;
   - use `experiment` for empirical questions whose result could change the HLD decision.
7. Pass delegated work a `Learning Task`: question, candidate answers or alternatives when known, relevant context, decision affected, evidence needed, and established constraints.
8. Consume its `Learning Result` as evidence. Keep the final architectural decision in HLD; do not inherit incidental prototype technologies or implementation choices.
9. If new evidence invalidates an assumption, reopen every dependent decision. Do not patch forward.
10. Remove components or complexity that cannot be traced to a driver or decision.
11. Verify the design against the Product Frame, system invariants, design drivers, and scope.
12. Produce the HLD and an explicit implementation handoff.

## Decision Rule

**REQUIRED SUB-SKILL:** Use `prototype` or `experiment` when the workflow routes a consequential unresolved decision to it.

Record a decision when two or more plausible alternatives materially change a system-level consequence.

Each decision states:

- drivers;
- alternatives;
- decision;
- rationale;
- trade-offs accepted;
- evidence, when relevant;
- conditions that would cause reconsideration.

Do not manufacture alternatives for inconsequential choices.

## HLD Boundary

HLD may decide: component boundaries/responsibilities, logical interfaces, data ownership, major flows, persistence strategy, consistency/processing semantics, scaling strategy, failure strategy, security/trust boundaries, compatibility/migration strategy, and major operational properties.

Leave to implementation: classes/functions/modules, libraries, concrete payloads, physical schema fields/indexes, algorithms, retry/timeout values, concurrency primitives, code organization, exact deployment configuration, and other realization details unless one is itself a system-level constraint.

## Red Flags

Stop and correct the design if any of these occur:

- product behavior changed to simplify architecture;
- a consequential choice appeared without alternatives/drivers;
- an architectural component has no traceable reason to exist;
- an unsupported system claim is treated as fact;
- prototype technology appears in HLD without an architectural decision;
- low-level implementation detail starts determining the design;
- later evidence invalidates an assumption but the design only accumulates patches;
- generic claims such as “scalable” or “highly available” appear without a relevant driver or behavior.

## Downstream Contract

Implementation must preserve the HLD's system invariants, ownership, boundaries, flows, selected decisions, and required system properties.

The HLD must also state what is **intentionally unspecified** so implementation retains freedom where no system-level decision is required.
