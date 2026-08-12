# State and Workflow Prototype

Use a state/workflow prototype when rules, transitions, data shape, or awkward event sequences are difficult to judge statically.

## Shape

- Build the smallest executable model that represents only the question under examination.
- Use a self-contained page when a non-developer must drive it; otherwise prefer a tiny script or existing project runner.
- Provide resettable guided scenarios and free-play actions when exploration matters.
- Show the full relevant state, action history, rejected transitions, and the last change after every action.
- Label everything in domain language.

Exercise the happy path, a consequential edge case, and an illegal transition. Add more only when they could change the affected decision.

Keep the model inside the disposable artifact. Even a clean reducer, state machine, or data type is evidence—not production code. Return what the exercised cases reveal and let the parent decide what follows.
