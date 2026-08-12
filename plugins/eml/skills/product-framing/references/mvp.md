# MVP by Subtraction

Use this reference when deriving the first useful/testable product boundary, especially from an existing implementation.

## Definition

The MVP is the smallest product boundary that lets the primary actor complete the primary job and produce useful evidence about the product thesis.

MVP is a product hypothesis. Current implementation is evidence about what is possible and available, not a default scope.

## Subtraction procedure

1. State the primary actor, job, intended outcome, and end-to-end workflow.
2. List current or proposed **capabilities at the product boundary**.
3. For each capability, remove it hypothetically.
4. Ask whether the primary workflow can still produce the intended outcome and the evidence needed to learn.
5. Classify the capability:
   - **include** — removing it breaks an established requirement of the value path;
   - **exclude/defer** — the value path and required evidence still work;
   - **unknown** — necessity depends on unresolved product intent.
6. Investigate an unknown only when it is consequential and blocking; otherwise put it on the learning agenda.

## Mechanism check

Before testing necessity, normalize mechanisms into the external behavior they support.

Example:

`distributed traces` → `diagnostic evidence sufficient to explain execution failures`

Then test whether the diagnostic evidence is required for the MVP. Do not automatically carry the mechanism into scope.

## Common subtraction targets

Inspect these aggressively because existing products commonly accumulate them:

- diagnostics beyond what the primary consumer needs;
- alternate execution modes;
- bulk/full-corpus operation when targeted operation proves the thesis;
- historical analytics and aggregation;
- scale, parallelism, and performance optimizations;
- administrative or maintainer workflows;
- future-policy hooks and configuration surfaces;
- compatibility behavior whose current necessity is unproven.

Do not remove a capability merely because it is operational or internal. Keep it when an external actor depends on its outcome or a hard constraint requires it.

## Exit check

A proposed MVP is credible when every included capability has a product-level reason to survive subtraction.

Fail the check when the rationale is only:

- “it already exists”;
- “the architecture uses it”;
- “it might be useful later”;
- “it makes the system more complete.”
