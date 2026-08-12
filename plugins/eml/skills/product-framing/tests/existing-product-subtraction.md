# Regression: existing product must subtract, not rename current implementation as MVP

## Scenario

Frame an existing internal evaluation harness from repository evidence. The current system validates and runs isolated synthetic cases, captures evidence, exposes diagnostic telemetry, verifies result completeness, and does not grade behavioral correctness.

Current implementation contains mechanisms such as distributed traces, artifact-relative references, targeted/full-corpus execution, serial execution, per-case reset, result sealing, and synthetic-data confinement.

Known product intent is incomplete: correctness policy, primary evidence consumer, repeatability requirements, and minimum evidence required by a future judge remain unresolved.

## Failure observed before this regression

The skill reconstructed the product accurately, but the proposed MVP largely mirrored shipped capabilities. Architecture mechanisms such as distributed traces and artifact-relative references leaked into capabilities/MVP scope even though their necessity had not been established.

## Required behavior

A compliant framing result must:

1. include Evidence status with Observed, Inferred, and Unknown;
2. distinguish the current observed boundary from the proposed MVP boundary;
3. apply subtraction to shipped capabilities rather than treating existing behavior as necessary;
4. distinguish operator, beneficiary, and downstream artifact consumer when those roles differ;
5. describe capabilities as behavior observable outside the subsystem boundary, not implementation mechanisms;
6. keep distributed traces, artifact-relative references, and similar mechanisms out of MVP scope unless evidence establishes that a downstream consumer requires them;
7. represent each learning item with question, decision affected, blocking status, and evidence needed;
8. preserve unresolved judge policy instead of inventing it;
9. stop without invoking a prototype when remaining uncertainty is empirical or policy-related.

## Regression signal

Fail if the frame equates "currently implemented" with "MVP required", or if implementation mechanisms appear as required product capabilities without evidence that they are externally meaningful at the subsystem boundary.
