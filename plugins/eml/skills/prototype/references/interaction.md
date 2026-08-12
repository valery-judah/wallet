# Interaction Prototype

Use an interaction prototype when the question must be experienced or when candidate UI/workflows must be compared.

## Shape

- Prefer an existing read-only surface when it already provides the required context.
- Otherwise build one isolated route or self-contained page using the project's existing UI system.
- When comparing alternatives, default to three structurally different variants and cap at five. Keep data and available actions consistent so the comparison isolates the intended difference.
- Make switching variants or restarting the workflow immediate and obvious.
- Use domain language and production-shaped synthetic data.

## Exercise

Provide guided scenarios for the primary path, one awkward case, and one invalid or recovery path when relevant. Surface current state and the last meaningful change after every action.

Do not use real mutations or production data. If the question requires observed behavior from representative users or measurable outcomes, hand the artifact to `experiment`; do not turn the prototype into an informal usability study.

Return observations about the interaction or comparison, not a product decision or production implementation. After the parent decides, production work implements that decision separately; no prototype code moves forward.
