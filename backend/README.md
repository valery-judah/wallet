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
uv run poe export-openapi
uv run poe verify
```

From the repo root, the equivalent Poe commands are:

```bash
uv --directory backend run poe serve
uv --directory backend run poe export-openapi
uv --directory backend run poe verify
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

`WALLET_FRONTEND_HOST` is included in the allowed CORS origins automatically. The
`export-openapi` task writes to `frontend/openapi.json` when a `frontend/`
directory exists, otherwise it falls back to repo-root `openapi.json`.

With the current repo layout, the canonical flow is:

```bash
uv run poe export-openapi
cd ..
make frontend-install
make frontend-generate-client
```
