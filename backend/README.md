# Wallet Backend

Python backend package for the Wallet product.

## Requirements
- Python 3.11+
- `uv`

## Working here
Run commands from the repository root with Make. `make help` lists them all:

```bash
make backend-run          # backend on http://localhost:8000 with reload
make verify-backend       # format check, lint, types, and tests
make test ARGS='-k <expr>'
make api-schema           # export the OpenAPI schema
make smoke-api-managed    # HTTP smoke scenarios against a temporary backend
make stack-up             # seeded backend and frontend in Docker
```

Make calls the Poe tasks in `poe_tasks.toml`. `uv run poe --help` lists them from `backend/`.

## Layout
```text
src/wallet/
tests/
scripts/devex/
```

## Configuration
The FastAPI app reads repo-root `.env` using `WALLET_`-prefixed variables:

```text
WALLET_APP_NAME
WALLET_ENVIRONMENT
WALLET_DEBUG
WALLET_API_V1_PREFIX
WALLET_FRONTEND_HOST
WALLET_LOG_LEVEL
WALLET_BACKEND_CORS_ORIGINS
WALLET_SEED_SAMPLE_DATA
WALLET_OLLAMA_BASE_URL
WALLET_OLLAMA_MODEL
WALLET_OLLAMA_TIMEOUT_SECONDS
WALLET_OLLAMA_CONTEXT_LENGTH
```

`WALLET_FRONTEND_HOST` is always included in the allowed CORS origins
automatically. When it uses `localhost` or `127.0.0.1`, the matching loopback
twin for the same port is also allowed automatically, so the default local UI
works at both `http://localhost:5173` and `http://127.0.0.1:5173`.

Use `WALLET_BACKEND_CORS_ORIGINS` only for explicit extra origins such as Vite
preview or a staging frontend domain. `make api-schema` writes to
`frontend/openapi.json` when a `frontend/` directory exists, otherwise it falls
back to repo-root `openapi.json`.

The optional Docker Compose workflow also reads the repo-root `.env` file and
publishes the backend on `http://localhost:8000`. `make stack-up` enables
`WALLET_SEED_SAMPLE_DATA=true` for the backend service, while `make backend-run`
keeps the backend empty by default unless the env var is set explicitly.

Build and print the demo dataset with `make backend-seed`. Regenerate the frontend client after
an API change with `make api-client`.

## Manual smoke
Use the smoke harness when you want a real HTTP sanity check instead of the
automated test suite:

```bash
make smoke-api
make smoke-api-managed
```

- `smoke` expects a backend already running at `http://127.0.0.1:8000`
- `smoke-managed` starts a temporary backend at `http://127.0.0.1:8010`
- `make verify-backend` is the automated test suite
