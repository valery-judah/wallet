# Runbook

Canonical command surface for local development, verification, and operator-style checks.

## Tooling

- Python: 3.11+
- Package and task runner: `uv`
- Backend task runner: Poe via `uv run poe`
- Frontend and optional full-stack workflows: Docker with Compose support

## Command Entry Points

- From the repo root, use `make` for the preferred workflow-oriented command surface.
- Use `uv --directory backend run poe <task>` only when you want the direct backend task layer.
- From inside `backend/`, use `uv run poe <task>`.
- Inspect the current command surface with `make help` and `uv --directory backend run poe --help`.

## Quickstart

```bash
make setup
make verify
make run-backend
make gen-client
make run-frontend
```

Optional full-stack Docker flow:

```bash
make run-stack
```

`make run-stack` starts the local Docker stack with sample backend data enabled by default.

## Preferred Workflows

```bash
make setup
make run-backend
make run-stack
make stop-stack
make logs-stack
make gen-client
make verify
make check-smoke
make clean
```

- `make run-backend`: run the backend locally with reload on the host
- `make run-frontend`: run the frontend dev server in Docker
- `make run-stack`: run backend and frontend together in Docker with sample data seeded by default
- `make gen-client`: export OpenAPI, ensure frontend dependencies, and regenerate the frontend API client
- `make verify`: run the backend verification suite plus frontend TypeScript validation

## Setup And Dependency Management

```bash
make setup
make setup-sync
make setup-lock
make install
make add-rich
uv add --package wallet <package>
uv add --package wallet --dev <package>
```

- `make setup`: bootstrap the local development environment
- `make setup-sync`: sync the lockfile into the local `.venv`
- `make setup-lock`: generate or refresh `uv.lock`
- `make install`: sync dependencies and install repo-managed git hooks
- `make add-rich`: optional smoke-check command that adds a small runtime dependency

## Backend Workflows

Preferred root commands:

```bash
make run-backend
make gen-openapi
make check-smoke
make check-smoke-managed
make verify
make clean
```

Low-level backend checks remain available at the root:

```bash
make fmt
make lint
make type
make test
make check
```

Direct backend Poe tasks from the repo root:

```bash
uv --directory backend run poe fmt
uv --directory backend run poe fmt-check
uv --directory backend run poe lint
uv --directory backend run poe type
uv --directory backend run poe test
uv --directory backend run poe serve
uv --directory backend run poe smoke
uv --directory backend run poe smoke-managed
uv --directory backend run poe export-openapi
uv --directory backend run poe clean
uv --directory backend run poe verify
uv --directory backend run poe check
```

- `make run-backend` is the preferred root-level command for local backend startup.
- `uv --directory backend run poe serve` remains the direct underlying backend task.

Equivalent backend tasks from inside `backend/`:

```bash
cd backend
uv run poe fmt
uv run poe fmt-check
uv run poe lint
uv run poe type
uv run poe test
uv run poe serve
uv run poe smoke
uv run poe smoke-managed
uv run poe export-openapi
uv run poe clean
uv run poe verify
uv run poe check
```

## Frontend Workflows

The generated UI client lives in `frontend/`.

```bash
make gen-client
make run-frontend
make frontend-type
make frontend-build
make frontend-test
make frontend-bun CMD="run <script>"
```

- `make gen-client` is the preferred client refresh workflow.
- `make run-frontend` starts the frontend dev server on `http://localhost:5173`.
- Frontend dev server: `http://localhost:5173`
- Loopback twin with default CORS settings: `http://127.0.0.1:5173`

## Full-Stack Docker Workflows

```bash
make run-stack
make stop-stack
make logs-stack
```

- `make run-stack` runs the optional local stack on `http://localhost:8000` and `http://localhost:5173`.
- `make run-backend` keeps the backend empty by default unless `WALLET_SEED_SAMPLE_DATA=true` is set explicitly.
- The canonical backend developer flow remains host `uv` plus the frontend Bun container commands.

## API Operations

```bash
make run-backend
make check-smoke
make check-smoke-managed
make gen-openapi
```

- App factory entrypoint: `wallet.api.app:create_app`
- Singleton ASGI app: `wallet.api.main:app`
- OpenAPI JSON: `/api/v1/openapi.json`
- Interactive docs: `/docs`
- `make verify` is the automated read-only verification suite for backend checks plus frontend TypeScript validation.
- The smoke commands are manual HTTP checks for operator-style backend validation.

## Low-Level Frontend Docker Targets

Direct frontend Docker targets such as `frontend-install`, `frontend-generate-client`, and `frontend-bun` remain available for low-level use.
