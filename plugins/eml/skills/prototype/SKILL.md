---
name: prototype
description: Use when a product or architectural decision depends on exercising, experiencing, or comparing an interaction, workflow, state model, data shape, integration boundary, lifecycle, failure path, or technical feasibility.
---

# Prototype

Answer one decision-relevant question with the **smallest credible runnable artifact**. Produce evidence; do not own the parent decision or produce production code.

## Input

If invoked by another skill, consume:

```text
Learning Task
├── Question
├── Candidate answers / alternatives, when known
├── Relevant context
├── Decision affected
├── Evidence needed
└── Established constraints
```

Otherwise reconstruct the same contract from available context.

## Route

| Question | Action |
|---|---|
| Interaction, UI, or end-to-end workflow | Read `references/interaction.md` |
| State transitions, domain rules, or data shape | Read `references/state.md` |
| Integration boundary, lifecycle/failure behavior, or technical feasibility | Read `references/technical.md` |
| Measurable behavior, value, performance, reliability, or outcome in realistic conditions | Use `experiment` |
| Fact about an existing system or workflow | Inspect, research, or observe |
| Product intent, policy, legal, or non-negotiable safety choice | Return to the parent or user |

A prototype may be an instrument inside an experiment. The experiment owns measurement and its decision rule.

## Workflow

1. State the question, verdict target, candidate answers or alternatives, and affected decision without broadening them. For a comparison, make the target a testable proposition such as “candidate A best satisfies the stated evidence need under these conditions.”
2. Before building, define observations that would support, weaken, or leave the question inconclusive.
3. Choose one disposable artifact and the smallest consequential scenarios. Reuse project tooling and installed dependencies.
4. Keep it isolated from production behavior, data, secrets, and irreversible side effects. Use synthetic/local data and sandbox or test integrations.
5. Make it trivial to run and expose the relevant state, behavior, and observations.
6. Execute when the required environment is safely available. Otherwise return a `Prototype Plan` naming the missing dependency.
7. Capture observations, conditions, deviations, and limitations. Never present an unrun plan as evidence.
8. Return the result, then remove the artifact and every external resource the prototype created unless reruns or auditability are explicitly decision-relevant. Verify cleanup; report failures and exact recovery steps in limitations. Never remove pre-existing user resources.
9. Stop when more prototyping is unlikely to change the affected decision.

Add only the validation and error handling needed to keep observations trustworthy. Skip polish, speculative behavior, abstractions, and production infrastructure.

## Result

```text
Learning Result
├── Question
├── Verdict target
├── Artifact / method and conditions
├── Observations
├── Verdict: supported | unsupported | inconclusive
├── Confidence / limitations
└── Parent-decision implications
    ├── Decision affected
    ├── Alternatives supported
    ├── Alternatives weakened
    └── Evidence relationship and limits
```

When execution cannot occur, return a `Prototype Plan` with the question, artifact, scenarios, discriminating observations, missing dependency, safety constraints, and run instructions.

Prototype code and incidental technology choices are **evidence only**. Do not promote them into product intent, architecture, or production code. The parent owns the decision.

`supported | unsupported | inconclusive` always applies to the named verdict target. `Parent-decision implications` contain no selected alternative, new requirement, architecture, or product commitment. The parent makes and records those judgments.
