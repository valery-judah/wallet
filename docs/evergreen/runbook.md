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

The `Makefile` is the entry point for every repository workflow. List the targets with:

```bash
make help
```

Target names start with the part of the system they act on:

| Prefix | Owns | Doesn't own |
| --- | --- | --- |
| `setup-*`, `clean` | Dependency sync, the lock file, Git hooks, local caches | Running services |
| `verify`, `fmt`, `lint`, `type`, `test*` | Backend and frontend checks. Only `fmt` writes files | Services and generated files |
| `backend-*` | The backend process on the host | Docker containers |
| `frontend-*` | Bun commands and the frontend dev server in Docker | The backend |
| `api-*` | The OpenAPI schema and the generated frontend client | Running services |
| `stack-*` | The seeded backend and frontend in Docker (`compose.dev.yml`) | Host processes and Ollama |
| `smoke-*` | Manual checks over real HTTP, some with local Ollama | The automated test suite |

Pass extra arguments with `ARGS`, for example:

```bash
make test ARGS='-k transfer'
make smoke-capture ARGS='--scenario progressive_expense'
make frontend-bun ARGS='run <script>'
```

Backend targets call Poe tasks defined in `backend/poe_tasks.toml`. Use Make in docs and
automation; Poe is the layer below it. The old target names, such as `run-stack` and
`gen-client`, still work as aliases and are listed at the end of `make help`.

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
make backend-run
```

The command starts FastAPI with reload and runs until interrupted with `Ctrl+C`.

- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/api/v1/openapi.json`
- Interactive docs: `http://localhost:8000/docs`
- Sample data: disabled by default

To run the HTTP smoke scenarios against this backend, keep it running and use

another terminal:

```bash
make smoke-api
```

### Split Local Stack

This is the recommended mode for normal full-stack development. The backend runs

on the host for direct reload and debugging, while Bun and the frontend run in

Docker.

Terminal 1:

```bash
make backend-run
```

Terminal 2:

```bash
make frontend-run
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Frontend loopback twin: `http://127.0.0.1:5173`
- Sample data: disabled by default

If the API schema changes, regenerate the frontend client:

```bash
make api-client
```

To keep the host-backend workflow but start with sample data:

```bash
WALLET_SEED_SAMPLE_DATA=true make backend-run
```

### Seeded Docker Stack

Use this mode when you want the complete application with predictable sample

data and minimal manual setup:

```bash
make stack-up
```

It builds and starts the following, and returns once the containers run:

- Docker backend: `http://localhost:8000`
- Docker frontend: `http://localhost:5173`
- Sample data: enabled

Use it for product exploration, demos, manual integration checks, and Docker build validation.
The split stack is usually more convenient for backend debugging.

Check the containers and read their logs:

```bash
make stack-status
make stack-logs
make stack-logs ARGS='--follow'
```

`make stack-logs` prints the last 200 lines and exits. With `ARGS='--follow'` it keeps
following until `Ctrl+C`.

Stop and remove the containers. The frontend dependency volumes are kept:

```bash
make stack-down
```

### Container Logging

Application processes write logs as event streams to standard output. They do

not create log files or manage rotation inside their containers. The backend

emits one JSON object per line, and `make stack-logs` preserves those records

for local inspection.

The repository's Compose services use Docker's `local` logging driver with a

maximum of five 10 MB files per container. Docker owns this storage, rotation,

and default compression, bounding local usage to approximately 50 MB per

container before compression. Do not mount application log directories or

read Docker's internal log files directly; use `make stack-logs`.

Production container platforms must capture the application standard-output

stream and define their own retention, forwarding, indexing, and access

policies. Retention beyond Docker's local rotated window belongs to that

platform rather than to the wallet application.

### Default Recommendation

| Intent | Command |
| --- | --- |
| Backend-only change | `make backend-run` |
| Normal application development | `make backend-run` and `make frontend-run` |
| Demo or integration exploration | `make stack-up` |
| Pre-commit confidence | `make verify` |
| Real HTTP sanity check | `make smoke-api-managed` |

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

The checks do not intentionally rewrite tracked source files. They may still sync local
dependencies and run `bun install` in the frontend Docker environment.

`make verify-backend` runs only the backend checks. The pre-commit hook runs it.

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
make verify
```

Run the deterministic control-layer and real-capability system suite while iterating:

```bash
make test-control
```

Its data profiles, case IDs, expected oracles, and model-smoke boundary are defined in

[`control-layer-testing.md`](control-layer-testing.md).

Run the focused real-model routing corpus when routing profiles or policy change:

```bash
ollama list
make smoke-router
```

It checks idle ownership, recent-capability references, ambiguity, unsupported false controls,

and compound controls without executing capabilities. Active-task ownership is deterministic and

belongs to the focused resolver and cross-workflow tests, not this idle-router corpus.

`make fmt` modifies backend source when formatting or auto-fixes are required.

`make check` is an alias for `make verify`.

## Smoke Testing

Run smoke scenarios against an existing backend:

```bash
# Expects the backend at http://127.0.0.1:8000
make smoke-api
```

Or let the smoke harness manage a temporary backend:

```bash
# Starts a temporary backend at http://127.0.0.1:8010
make smoke-api-managed
```

The smoke harness exercises real HTTP requests and is intended for manual,

operator-style validation. It is separate from the automated test suite.

### Conversation Capture With Ollama

The conversation-capture smoke workflow exercises the public conversation API with

seeded in-memory Wallet data and a locally running Ollama model. By default it starts

a temporary backend at `http://127.0.0.1:8011`, runs all scenarios against that one

process, and stops it afterward:

```bash
ollama list
make smoke-capture
```

Each scenario submits its first input to `/api/v1/turns`, lets the app create the conversation,

select the internal capture capability, and interpret the contribution against the seeded safe

reference catalog. Later active-task messages skip routing and use one interpretation call each.

The corpus includes typo-tolerant account/category selection, unknown-reference correction,

shared-leaf disambiguation, and currency-conflict correction.

It verifies that the transaction list remains unchanged until guarded typed confirmation. After

confirmation it verifies the

returned and persisted transaction, balanced postings, and account balance changes through

the accounts and transactions APIs. Smoke output contains only public task views,

messages, and completion state; model traces remain internal.

To target an already-running seeded, single-process backend instead:

```bash
make smoke-capture ARGS='--existing-backend --api-base-url http://127.0.0.1:8000'
```

The default model is `qwen3.5:9b`. Install it before the first run when needed:

```bash
ollama pull qwen3.5:9b
```

### Conversation Capture HTTP API

Run a seeded backend while Ollama is available:

```bash
WALLET_SEED_SAMPLE_DATA=true make backend-run
```

Read current active-account balances through the control layer. Omitting `conversation_id`

creates the conversation and processes this first input atomically. The message router uses

Ollama once, then wallet-state execution is deterministic and does not change the ledger:

```bash
curl --request POST \
  http://127.0.0.1:8000/api/v1/turns \
  --header 'content-type: application/json' \
  --data '{
    "request_id":"state-request-1",
    "input":{"kind":"message","content":"Show my current balances"}
  }'
```

Start transaction capture with the same single endpoint:

```bash
curl --request POST \
  http://127.0.0.1:8000/api/v1/turns \
  --header 'content-type: application/json' \
  --data '{
    "request_id":"request-1",
    "input":{
      "kind":"message",
      "content":"Spent 40 dollars from USD cash on Groceries today"
    }
  }'
```

After idle routing selects transaction capture, the transaction interpreter receives only the

validated contribution, current draft and interaction, current date, and safe catalog labels with

per-call opaque keys; it does not receive internal entity or request IDs. The separate router call

receives capability routing profiles and bounded recent-capability identity, but no draft or Wallet

catalog. The response contains an opaque `active_task` with a `transaction_capture` view. A

complete candidate has `phase: "awaiting_confirmation"` and has not changed the ledger. Copy the

returned conversation ID for continuation and copy the offered task guard for confirmation:

```bash
curl http://127.0.0.1:8000/api/v1/conversations/<conversation_id>

curl --request POST \
  http://127.0.0.1:8000/api/v1/turns \
  --header 'content-type: application/json' \
  --data '{
    "request_id":"request-2",
    "conversation_id":"<conversation_id>",
    "input":{"kind":"message","content":"Make it 35"}
  }'

curl --request POST \
  http://127.0.0.1:8000/api/v1/turns \
  --header 'content-type: application/json' \
  --data '{
    "request_id":"request-3",
    "conversation_id":"<conversation_id>",
    "input":{
      "kind":"task_action",
      "expected_task_id":"<active_task_id>",
      "expected_conversation_version":<current_version>,
      "action":"confirm",
      "payload":{}
    }
  }'
```

Confirmation revalidates referenced accounts and categories and creates one posted

transaction. Repeating an exact request with the same globally unique `request_id` replays its

response without creating another transaction. Conversation IDs become unavailable when the

backend restarts

and are not shared between backend workers. Model or structured-response failures return

HTTP `502` without exposing model details.

Configuration uses `WALLET_OLLAMA_BASE_URL`, `WALLET_OLLAMA_MODEL`,

`WALLET_OLLAMA_TIMEOUT_SECONDS`, and `WALLET_OLLAMA_CONTEXT_LENGTH`. The context

length defaults to 8192 tokens and is sent as Ollama's per-request `num_ctx` option.

For example, set `WALLET_OLLAMA_CONTEXT_LENGTH=32768` to test a 32K window without

creating a second Modelfile-derived model. Larger windows consume more memory; use

the privacy-safe `prompt_eval_count` and `eval_count` fields on

`ollama.request.completed` events to size the window from observed traffic.

The Docker development stack reaches host Ollama through

`http://host.docker.internal:11434`; set `WALLET_OLLAMA_BASE_URL` before `make stack-up`

to override it.

Pass scenario and connection overrides with `ARGS`:

```bash
make smoke-capture ARGS='--scenario progressive_expense \
  --ollama-base-url http://127.0.0.1:11434 --ollama-timeout 30 \
  --request-timeout 60 --model qwen3.5:9b'
```

Ollama failures are observed through the product API as safe HTTP `502` responses;

the smoke command does not call Ollama directly for a separate preflight.

This is a manual model-dependent check and is not part of `make verify`.

## API And Client Generation

Export only the backend OpenAPI document:

```bash
make api-schema
```

Export OpenAPI, ensure frontend dependencies, and regenerate the frontend API

client:

```bash
make api-client
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
make setup

# Configure only the Git hooks
make setup-hooks

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
| `make fmt` | No | No | Yes |
| `make verify` | No | No | Not intentionally |
| `make backend-run` | No | Yes | No |
| `make frontend-run` | No | Yes | No |
| `make stack-up` | No | No, the containers keep running | No |
| `make stack-status` | No | No | No |
| `make stack-logs` | Running stack | Only with `ARGS='--follow'` | No |
| `make stack-down` | No | No | No |
| `make smoke-api` | Backend on port 8000 | No | No |
| `make smoke-api-managed` | No | No | No |
| `make smoke-capture` | Ollama on port 11434 | No | No |
| `make smoke-router` | Ollama on port 11434 | No | No |
| `make api-schema` | No | No | Yes |
| `make api-client` | No | No | Yes |
| `make frontend-type` | No | No | No |
| `make frontend-test` | No | No | No |
| `make frontend-build` | No | No | No |
| `make setup-lock` | No | No | Yes |
| `make clean` | No | No | Deletes local artifacts |

## Low-Level Commands

Low-level frontend targets:

```bash
make frontend-install
make frontend-client
make frontend-bun ARGS='run <script>'
```

`make backend-seed` builds and prints the local sample dataset.

Remove backend and frontend caches, build output, and other generated local artifacts with:

```bash
make clean
```

Backend Poe tasks are listed by `uv --directory backend run poe --help`. Each one has a Make
target.
