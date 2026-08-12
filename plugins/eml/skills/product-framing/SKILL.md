---
name: product-framing
description: Use when a rough product or feature idea needs definition before prototyping, experimentation, product design, or system design, or when product intent is unclear in an existing product.
---

# Product Framing

Build the smallest product model downstream work can use without inventing product intent. Operate autonomously. Optimize for **sufficiency, not completeness**.

For new ideas, treat the proposed solution as evidence about intent. For existing products, reconstruct intent from evidence, then derive a proposed MVP by subtraction rather than renaming shipped behavior.

## Output

Maintain:

- **Intent** — actors, situations, jobs, outcomes
- **Core experience** — primary workflow and important scenarios
- **Capabilities** — externally meaningful behavior the product must enable
- **MVP boundary** — inclusions and explicit exclusions
- **Learning agenda** — consequential unresolved questions

For existing products also maintain **Evidence status** and **Current observed boundary**.

Read `references/product-frame.md` when actor roles, subsystem boundaries, capabilities, or product commitments are ambiguous.

**REQUIRED REFERENCE for existing products:** Read `references/existing-product.md`.

## Loop

1. Gather evidence and draft early.
2. Challenge actor, outcome, workflow, capability, scope, and evidence.
3. Identify uncertainties that could materially change the frame.
4. Resolve only uncertainty blocking downstream progress.
5. Incorporate evidence and revise.
6. Derive MVP by subtraction.
7. Stop when the next phase can proceed without inventing product intent.

Do not run exhaustive discovery.

## MVP

**REQUIRED REFERENCE when deriving or disputing scope:** Read `references/mvp.md`.

Current implementation proves what exists, not what is necessary. Keep the current observed boundary separate from the proposed MVP boundary.

## Learning

**REQUIRED REFERENCE when retaining or delegating consequential uncertainty:** Read `references/learning.md`.

Use the cheapest suitable mechanism: reason/inspect existing evidence; **prototype** questions that must be experienced, exercised, or compared; **experiment** empirical behavior/value questions; research/observe factual uncertainty.

**REQUIRED SUB-SKILL:** Use `prototype` when applicable. Use an `experiment` skill when available and applicable.

Delegated work answers one decision-relevant question and does not own the Product Frame.

## Autonomy

Use reversible working assumptions when evidence supports them. Escalate only when a high-impact decision blocks progress, materially different directions remain plausible, available learning mechanisms cannot resolve it, and implicit choice would encode unsupported intent or a costly-to-reverse commitment.

When escalating, present the decision, alternatives, consequences, and evidence considered.

## Exit

Stop when downstream work can determine without inventing product intent:

- actors, situation, job, and intended outcome;
- primary workflow and externally meaningful capabilities;
- proposed MVP inclusions and exclusions;
- consequential unresolved questions and evidence needed.

For existing products, verify the proposed MVP was **derived by subtraction**, not renamed from the current boundary. Framing may finish with unresolved questions.
