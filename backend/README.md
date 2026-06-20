# Wallet Backend

Python backend package for the Wallet product.

## Requirements
- Python 3.11+
- `uv`

## Working here
From `backend/`:

```bash
uv sync --group dev
uv run poe serve
uv run poe smoke
uv run poe smoke-managed
uv run poe export-openapi
uv run poe verify
```

From the repo root, the equivalent Poe commands are:

```bash
make run-backend
make gen-openapi
make check-smoke
make check-smoke-managed
uv --directory backend run poe serve
uv --directory backend run poe smoke
uv --directory backend run poe smoke-managed
uv --directory backend run poe export-openapi
uv --directory backend run poe verify
```

`make run-backend` is the preferred root-level convenience command for running the backend locally with reload. Direct Poe commands remain available when you want the backend task layer.

For an optional all-container local stack, return to the repo root and run:

```bash
make run-stack
```

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
WALLET_BACKEND_CORS_ORIGINS
```

`WALLET_FRONTEND_HOST` is always included in the allowed CORS origins
automatically. When it uses `localhost` or `127.0.0.1`, the matching loopback
twin for the same port is also allowed automatically, so the default local UI
works at both `http://localhost:5173` and `http://127.0.0.1:5173`.

Use `WALLET_BACKEND_CORS_ORIGINS` only for explicit extra origins such as Vite
preview or a staging frontend domain. The `export-openapi` task writes to
`frontend/openapi.json` when a `frontend/` directory exists, otherwise it falls
back to repo-root `openapi.json`.

The optional Docker Compose workflow also reads the repo-root `.env` file and
publishes the backend on `http://localhost:8000`.

With the current repo layout, the canonical flow is:

```bash
cd ..
make gen-client
```

## Manual smoke
Use the smoke harness when you want a real HTTP sanity check instead of the
automated test suite:

```bash
make check-smoke
make check-smoke-managed
```

- `smoke` expects a backend already running at `http://127.0.0.1:8000`
- `smoke-managed` starts a temporary backend at `http://127.0.0.1:8010`
- `uv run poe verify` remains the automated test suite
