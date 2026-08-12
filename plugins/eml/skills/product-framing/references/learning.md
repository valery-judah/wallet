# Product Learning

Use this reference when a Product Frame contains consequential uncertainty, when deciding whether to investigate now, or when delegating to a prototype or experiment.

## Learning agenda item

Record each consequential uncertainty as:

- **Question** — one decision-relevant unknown.
- **Decision affected** — what changes depending on the answer.
- **Blocking status** — blocking now or not blocking now.
- **Evidence needed** — what observation would distinguish meaningful answers.

Do not use the learning agenda as a list of everything unknown.

## Triage

Judge uncertainty by:

- **Impact** — could different answers materially change the product?
- **Blocking** — is the answer required for the next product decision?
- **Resolvable** — can useful evidence be obtained at reasonable cost now?

Use this policy:

| Condition | Action |
|---|---|
| high impact + blocking + resolvable | investigate now |
| high impact + not blocking | retain on learning agenda |
| low impact | defer or ignore |
| high impact + blocking + not autonomously resolvable | escalate |

## Choose the evidence mechanism

- **Reason / inspect** when available evidence can resolve the distinction.
- **Prototype** when the question must be experienced, exercised, or compared: interaction, UI, workflow, state/domain behavior.
- **Experiment** when the answer depends on empirical behavior, value, or outcomes in reality.
- **Research / observe** when the uncertainty is factual or concerns an existing workflow/product.
- **Escalate** when the unknown is product intent or policy that available evidence cannot legitimately determine.

Do not prototype an empirical value question. Do not run an experiment to manufacture a stakeholder policy decision.

## Delegation contract

Pass a learning skill only:

```text
Learning Task
├── Question
├── Relevant product context
├── Decision affected
├── Evidence needed
└── Established constraints
```

The delegated skill answers the question. It does not own the Product Frame or broaden the development workflow.

Consume its result as:

```text
Learning Result
├── Evidence
├── Verdict: supported | unsupported | inconclusive
├── Confidence / limitations
└── Product implications
```

Product framing decides whether and how those implications change intent, workflow, capabilities, scope, or the learning agenda.

## Inconclusive evidence

An inconclusive result does not automatically require human input.

Ask whether:

1. the question can be sharpened;
2. another inexpensive evidence source would discriminate better;
3. the decision can proceed under a reversible working assumption;
4. the question can become non-blocking and remain on the learning agenda.

Escalate only when none of these paths is adequate and implicit choice would encode unsupported product intent or a costly-to-reverse commitment.

## Stop learning

Stop investigating when additional evidence is unlikely to change the current frame or next downstream decision.
