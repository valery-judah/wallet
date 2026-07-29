# Runbook

Canonical workflows for local development, verification, code generation, and
operator-style checks.

## Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)
- Docker with Compose support for frontend and optional full-stack workflows

Before using a Docker workflow, confirm that the CLI can reach the active engine:

```bash
docker context show
docker info
docker compose version
```

## Command Entry Points

From the repository root, use `make` for the preferred workflow surface:

```bash
make help
```

Use Poe when direct backend task access is useful:

```bash
# From the repository root
uv --directory backend run poe --help
uv --directory backend run poe <task>

# From backend/
uv run poe <task>
```

## First-Time Setup

```bash
make setup
make verify
```

`make setup` syncs the backend development environment and configures Git to use
the hooks in `.githooks/`.

## Choose A Local Development Mode

| Mode | Use when | Backend | Frontend | Initial data |
| --- | --- | --- | --- | --- |
| Backend only | Working on API or domain code | Host with `uv` | Not started | Empty |
| Split local stack | Normal full-stack development | Host with `uv` | Docker | Empty |
| Seeded Docker stack | Exploring, demoing, or checking integration | Docker | Docker | Sample data |

### Backend Only

Use this mode when changing backend behavior, API routes, domain logic, or tests
without needing the UI:

```bash
make run-backend
```

The command starts FastAPI with reload and runs until interrupted with `Ctrl+C`.

- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/api/v1/openapi.json`
- Interactive docs: `http://localhost:8000/docs`
- Sample data: disabled by default

To run the HTTP smoke scenarios against this backend, keep it running and use
another terminal:

```bash
make check-smoke
```

### Split Local Stack

This is the recommended mode for normal full-stack development. The backend runs
on the host for direct reload and debugging, while Bun and the frontend run in
Docker.

Terminal 1:

```bash
make run-backend
```

Terminal 2:

```bash
make run-frontend
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Frontend loopback twin: `http://127.0.0.1:5173`
- Sample data: disabled by default

If the API schema changes, regenerate the frontend client:

```bash
make gen-client
```

To keep the host-backend workflow but start with sample data:

```bash
WALLET_SEED_SAMPLE_DATA=true make run-backend
```

### Seeded Docker Stack

Use this mode when you want the complete application with predictable sample
data and minimal manual setup:

```bash
make run-stack
```

It builds and starts:

- Docker backend: `http://localhost:8000`
- Docker frontend: `http://localhost:5173`
- Sample data: enabled

The command runs in the foreground and displays logs from both services. It is
well suited to product exploration, demos, manual integration checks, and Docker
build validation. The split stack is usually more convenient for backend
debugging.

Stop the foreground process with `Ctrl+C`, then remove the stack resources:

```bash
make stop-stack
```

To follow Compose logs from another terminal:

```bash
make logs-stack
```

`make logs-stack` is also long-running.

### Default Recommendation

| Intent | Command |
| --- | --- |
| Backend-only change | `make run-backend` |
| Normal application development | `make run-backend` and `make run-frontend` |
| Demo or integration exploration | `make run-stack` |
| Pre-commit confidence | `make verify` |
| Real HTTP sanity check | `make check-smoke-managed` |

Verification, generation, and managed smoke commands perform work and exit; they
do not leave a development stack running.

## Verification

Run the standard code verification suite:

```bash
make verify
```

It runs:

- backend formatting checks and lint
- strict backend type checking
- backend tests
- frontend TypeScript checking

The checks do not intentionally rewrite tracked source files. The Make workflow
may still sync local dependencies, configure the repository Git hooks path, and
run `bun install` in the frontend Docker environment.

Frontend tests and the production build are separate checks:

```bash
make frontend-test
make frontend-build
```

Low-level backend checks are also available individually:

```bash
make fmt
make lint
make type
make test
make check
```

`make fmt` modifies backend source when formatting or auto-fixes are required.
`make check` is an alias for `make verify`.

## Smoke Testing

Run smoke scenarios against an existing backend:

```bash
# Expects the backend at http://127.0.0.1:8000
make check-smoke
```

Or let the smoke harness manage a temporary backend:

```bash
# Starts a temporary backend at http://127.0.0.1:8010
make check-smoke-managed
```

The smoke harness exercises real HTTP requests and is intended for manual,
operator-style validation. It is separate from the automated test suite.

## API And Client Generation

Export only the backend OpenAPI document:

```bash
make gen-openapi
```

Export OpenAPI, ensure frontend dependencies, and regenerate the frontend API
client:

```bash
make gen-client
```

Generated artifacts live at:

- `frontend/openapi.json`
- `frontend/src/client/`

These commands can update tracked generated files. Review the result with
`git diff`.

## Dependency Management

```bash
# Sync uv.lock into the local backend environment
make setup-sync

# Generate or refresh uv.lock
make setup-lock

# Sync dependencies and configure repository-managed Git hooks
make install

# Add a backend runtime dependency
uv add --package wallet <package>

# Add a backend development dependency
uv add --package wallet --dev <package>
```

`make setup-lock` and both `uv add` commands can update tracked dependency files.

## API Operations

- App factory: `wallet.api.app:create_app`
- Singleton ASGI app: `wallet.api.main:app`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`
- Interactive docs: `http://localhost:8000/docs`

## Command Behavior Reference

| Command | Existing service required | Long-running | Can modify tracked files |
| --- | --- | --- | --- |
| `make setup` | No | No | No |
| `make verify` | No | No | Not intentionally |
| `make run-backend` | No | Yes | No |
| `make run-frontend` | No | Yes | No |
| `make run-stack` | No | Yes | No |
| `make logs-stack` | Running stack | Yes | No |
| `make stop-stack` | No | No | No |
| `make check-smoke` | Backend on port 8000 | No | No |
| `make check-smoke-managed` | No | No | No |
| `make gen-openapi` | No | No | Yes |
| `make gen-client` | No | No | Yes |
| `make frontend-type` | No | No | No |
| `make frontend-test` | No | No | No |
| `make frontend-build` | No | No | No |
| `make setup-lock` | No | No | Yes |
| `make clean` | No | No | Deletes local artifacts |

## Low-Level Commands

Direct backend tasks are listed by:

```bash
uv --directory backend run poe --help
```

Low-level frontend Docker targets include:

```bash
make frontend-install
make frontend-generate-client
make frontend-bun CMD="run <script>"
```

Remove backend and frontend caches, build output, and other generated local
artifacts with:

```bash
make clean
```
