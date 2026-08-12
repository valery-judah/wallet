---
name: experiment
description: Use when a product decision depends on empirical evidence about user behavior, product value, outcome quality, or comparative performance in realistic conditions.
---

# Experiment

Answer one decision-relevant empirical question with the **smallest credible experiment that could change the decision**.

An experiment produces evidence and a verdict. It does not own the broader product decision.

## Input

If invoked by another skill, consume:

```text
Learning Task
├── Question
├── Relevant product context
├── Decision affected
├── Evidence needed
└── Established constraints
```

Otherwise reconstruct the same contract from available context.

## Loop

1. State the empirical question and decision affected.
2. Define the meaningful competing hypotheses or alternatives.
3. Identify the outcome that is actually decision-relevant.
4. Before inspecting results, define what evidence would support, weaken, or leave the question inconclusive.
5. Choose the cheapest method with enough fidelity to produce that evidence.
6. Run it when required participants, data, and environment are available. Otherwise return an executable plan and the missing dependency.
7. Record observations, provenance, material confounds, and deviations.
8. Evaluate evidence against the predeclared decision rule.
9. Return the verdict, limitations, and implications.
10. Stop when more evidence is unlikely to change the affected decision.

## Choose the method

Prefer the lowest-cost credible method:

1. existing or replay data / offline evaluation;
2. manual, concierge, or Wizard-of-Oz trial;
3. instrumented prototype or limited pilot;
4. controlled comparison;
5. production randomized experiment.

A prototype may be an instrument inside an experiment. If the question is primarily about interaction, comprehension, workflow feel, or state/domain behavior, use `prototype` instead.

Do not use an experiment to manufacture stakeholder intent, legal policy, non-negotiable safety policy, or another normative choice.

## Measurement discipline

Measure the intended outcome as directly as practical.

- Treat clicks, usage, engagement, and other proxies as evidence only when their relationship to the intended outcome is justified.
- Separate observed behavior from stated preference.
- Separate association from causal evidence; observational differences alone do not establish treatment effects.
- Predeclare supported, unsupported, and inconclusive conditions before results are known.
- Do not change thresholds or select favorable slices after seeing results.
- If multiple changes are bundled, attribute the result to the bundle unless the design identifies component effects.

Do not build production infrastructure when a cheaper credible test answers the question.

## Result

When evidence was collected, return:

```text
Experiment Result
├── Question
├── Decision affected
├── Method and conditions
├── Decision rule
├── Evidence
├── Verdict: supported | unsupported | inconclusive
├── Confidence / limitations
└── Product implications
```

When execution cannot occur, return an `Experiment Plan` with the same question, decision, method, decision rule, evidence to collect, required dependency, and execution notes.

Never present an unrun plan as evidence.

The caller decides whether and how the result changes product intent, workflow, capabilities, scope, or the learning agenda.
