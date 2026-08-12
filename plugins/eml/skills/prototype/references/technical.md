# Technical Prototype

Use a technical prototype to exercise an integration boundary, lifecycle/failure path, or feasibility claim that static inspection cannot resolve.

## Shape

- Build a thin harness around the real boundary using installed SDKs and the repository's normal runner.
- Use a local emulator, sandbox, test account, or fake dependency in that order of preference for the question.
- Tag created resources uniquely, bound their lifetime, and define cleanup before execution.
- Record inputs, observed transitions/events, outputs, timing only when incidental, and deviations from expected behavior.

Exercise only scenarios that discriminate between the meaningful answers: usually one normal path and the relevant cancellation, retry, duplicate, ordering, recovery, or partial-failure path.

Do not use production credentials, production data, or irreversible mutations merely because they are available. If the required safe environment is missing, return a `Prototype Plan`.

Feasibility observed in a thin harness does not establish production performance or reliability. Route claims requiring representative measurement to `experiment`.

End with evidence in this shape:

```text
Observation under tested conditions
→ supports / weakens named HLD alternatives
→ limited by named untested conditions
```

HLD performs the next step. The prototype does not supply a requirement or selected architecture, and its SDK, storage, retry model, and other incidental choices stay out of HLD.

After capturing evidence, delete and verify deletion of every sandbox/test resource the harness created. If cleanup fails, include the resource identifiers, remaining risk, and exact recovery steps in `Confidence / limitations`.
