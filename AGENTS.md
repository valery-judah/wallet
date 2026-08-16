# Agent Contract

Wallet is a money tracking app that shows what money moved, from where, to where, and why. The
Python backend is in `backend/` and the React frontend is in `frontend/`. A chat assistant records
expenses, income, and transfers with a local Ollama model.

## Canonical sources

### Repository and infrastructure
- `README.md` - project overview and quick start
- `docs/README.md` - docs index
- `docs/evergreen/runbook.md` - commands, local development modes, and operating procedures
- `backend/README.md` - backend layout and configuration
- `frontend/README.md` - frontend layout, routes, and the Bun container

### Product and architecture
- `docs/product/wallet-frame.md` - product intent, jobs, user needs, and evaluation anchors
- `docs/product/ai-capabilities-frame.md` - AI capability jobs, boundaries, and evaluation anchors
- `docs/product/spec.md` - current product base
- `docs/product/concepts.md` - core Wallet domain language
- `docs/product/assistant-concepts.md` - Assistant supporting-context language
- `docs/evergreen/message-router-contract.md` - LLM routing boundary and lifecycle rules
- `docs/evergreen/transaction-interpretation-contract.md` - transaction interpretation and confirmation boundary
- `docs/evergreen/control-layer-testing.md` - control-layer and capability test matrix

`docs/evergreen/` is canonical and wins when sources disagree. `docs/product/` holds product work in progress. `docs/workstreams/` and `docs/product/archive/` are history only.

## Commands
- Use `make <target>` for repository workflows and `make help` for the current catalog. Pass extra arguments with `ARGS='...'`.
- Make calls Poe for backend tasks and runs Bun in Docker for frontend tasks. If no target exists, use `uv --directory backend run <tool>`.
- Do not use `pip`, `python -m pip`, `poetry`, `pipenv`, `npm`, `npx`, or a host `bun`.
- `backend-run` and `frontend-run` stay in the foreground. To run the app and get the shell back, use `make stack-up`, then `make stack-status`, `make stack-logs`, and `make stack-down`.

## Validation
- Code change: `make verify`.
- Assistant routing or capture change: also run `make smoke-router` or `make smoke-capture`. They need Ollama running locally.
- Docs-only change: check that the commands and links you changed exist.

## Scratch scripts
- Put temporary, exploratory, and devex scripts in `backend/scripts/devex/`.
