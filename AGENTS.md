
## Canonical sources
- `docs/evergreen/runbook.md` - local commands and operation
- `docs/product/spec.md` - current product base
- `docs/product/concepts.md` - product vocabulary and concepts
- `docs/README.md` - docs index

`docs/evergreen/` is canonical when present. `docs/delivery/` is reference-only. `docs/workstreams/` is history-only.

The product base is currently being built in `docs/product/spec.md` and `docs/product/concepts.md`.

## Commands
- Use `uv` as the Python command entrypoint for this repo.
- From the repo root, prefer `make` for the standard workflow surface such as setup, run, generation, verification, and Docker-based flows.
- Use `uv --directory backend run poe <task>` for direct backend task access from the repo root; from inside `backend/`, use `uv run poe <task>`.
- Otherwise use `uv run <tool>` or `uv --directory backend run <tool>`, depending on which project owns the command.
- Do not use `pip`, `python -m pip`, `poetry`, `pipenv`, `npm`, or `npx` for repo workflows.
- For the full command catalog and operational guidance, use [`docs/evergreen/runbook.md`](docs/evergreen/runbook.md).
- To inspect the current command surface directly, use `make help` and `uv --directory backend run poe --help`.

## Validation
- Docs-only change: no mandatory validation; run targeted checks only if docs affect commands or generated artifacts.
- Code change: `make verify`

## Development Practices
- Save any temporary, exploratory, or developer-experience (devex) scripts into the `backend/scripts/devex/` directory.
