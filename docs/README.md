# Docs

`evergreen/` is canonical and wins when sources disagree. `product/` holds product work in
progress. `workstreams/` and `product/archive/` record design history and are not
kept up to date.

## Repository and infrastructure
- `evergreen/runbook.md`: commands, local development modes, and operating procedures
- `../backend/README.md`: backend layout and configuration
- `../frontend/README.md`: frontend layout, routes, and the Bun container

## Product
- `product/wallet-frame.md`: product jobs, user needs, desired outcomes, principles, and evaluation anchors
- `product/ai-capabilities-frame.md`: AI-enabled jobs, capability boundaries, trust principles, and evaluation anchors
- `product/spec.md`: Wallet MVP specification
- `product/concepts.md`: Wallet domain language
- `product/assistant-concepts.md`: Assistant supporting-context language
- `../framing/`: assistant framing built step by step from user problems (draft)
- `product/assistant-help-page.md`: proposed in-app Wallet Assistant help page and user guidance

## Architecture
- `evergreen/message-router-contract.md`: LLM routing boundary and lifecycle rules
- `evergreen/transaction-interpretation-contract.md`: model-owned transaction interpretation and deterministic confirmation boundary
- `evergreen/control-layer-testing.md`: control-layer and capability system-test matrix

## Conventions
- `conventions/domain-modeling-and-refactoring.md`: closed domain families and exhaustive routing
- `conventions/commit-message-conventions.md`: commit message format and types

## History
- `workstreams/`: design history of past workstreams
- `product/archive/`: earlier product exploration and supporting notes
