# Regression: new idea must not become the product definition

## Scenario

A user proposes: “Build an AI PR reviewer that automatically comments on every pull request and stores team-specific review rules.” No customer evidence, workflow research, or usage evidence is provided.

## Failure to detect

The framing agent accepts “AI PR reviewer”, automatic invocation, and stored team rules as fixed requirements, then produces an MVP around implementing them.

## Required behavior

A compliant result must:

1. infer a provisional actor, situation, job, and intended outcome without treating the proposed mechanism as established intent;
2. separate the desired progress from automatic invocation and persistent team rules;
3. establish one coherent primary workflow;
4. subtract capabilities that are not necessary to test the product thesis;
5. place consequential unresolved questions on the learning agenda rather than inventing answers;
6. invoke a prototype only when an experiential question blocks framing;
7. avoid architecture, storage, API, and state-machine commitments.

## Regression signal

Fail if the product frame is essentially a cleaned-up specification of the proposed implementation rather than a model of actor, job, outcome, workflow, minimal capabilities, and uncertainty.
