# Existing Product Reconstruction

Use this reference when framing a product, subsystem, or feature that already exists.

The goal is to reconstruct product intent without confusing implementation history with product necessity.

## Evidence status

Record a compact evidence section before the frame:

- **Observed** — behavior or intent directly supported by available evidence.
- **Inferred** — the best current interpretation, supported but not explicitly established.
- **Unknown** — consequential intent that the evidence does not establish.

Keep these categories separate during reasoning even when the final wording is concise.

## Evidence sources

Prefer evidence that is closer to external behavior and explicit decisions:

1. accepted product decisions, canonical product documentation, explicit user commitments;
2. observable interfaces, workflows, outputs, and downstream consumers;
3. tests and call sites that demonstrate relied-upon behavior;
4. implementation structure and mechanisms;
5. names, comments, or incidental historical artifacts.

Lower-level evidence can establish **what exists**. It is weaker evidence for **why it must exist**.

## Conflicting evidence

Do not force evidence into one story.

When sources conflict, preserve the distinction:

- stated intent may differ from current behavior;
- current behavior may be accidental, transitional, or legacy;
- tests may establish a relied-upon contract even when documentation is stale;
- implementation mechanics do not establish product necessity by themselves.

Record the conflict as an uncertainty when resolving it would change a current decision.

## Current boundary vs product boundary

Write the **Current observed boundary** as a neutral inventory of externally meaningful behavior that exists today.

Then derive the **Proposed MVP boundary** separately.

Never use this transformation:

`currently shipped → therefore MVP`

Use:

`currently shipped → reconstruct value path → subtract → proposed MVP`

## Internal subsystems

For internal products, identify operator, beneficiary, and artifact consumer when they differ.

Example:

- operator: evaluation engineer running a harness;
- beneficiary: team making a product-quality decision;
- artifact consumer: human or automated judge consuming the result package.

This distinction often reveals that a diagnostic mechanism used by the operator is not necessarily an MVP requirement for the artifact consumer.

## Reconstruction check

Before exit, ask:

1. Which statements describe observed current behavior?
2. Which statements describe intended product value?
3. Which statements are inference only?
4. Which shipped capabilities survive subtraction, and why?
5. Did any implementation mechanism become a capability without evidence that an external actor depends on it?
