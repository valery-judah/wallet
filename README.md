# Wallet

Money tracking for imperfect real-life habits. The MVP focuses on helping users understand what money moved, from where, to where, and why.

## Requirements
- Python 3.11+
- `uv` (recommended)
- Docker with Compose support for frontend workflows

## Quickstart
```bash
make init
make verify
uv --directory backend run poe serve
uv --directory backend run poe export-openapi
make frontend-install
make frontend-generate-client
```

## Development
The backend now lives in `backend/`. Use root-level `make` wrappers or run Poe directly from inside `backend/`.

From the repo root:

```bash
make fmt
make lint
make type
make test
make clean
make verify
```

From inside `backend/`:

```bash
cd backend
uv run poe fmt
uv run poe lint
uv run poe type
uv run poe test
uv run poe serve
uv run poe export-openapi
uv run poe clean
uv run poe verify
```

You can also target the backend explicitly from the root with `uv --directory backend run poe <task>`.

The generated UI client now lives in `frontend/`. Export the backend schema with
`uv --directory backend run poe export-openapi`, then use the root `make`
targets to run Bun inside Docker.

## Dependencies
- Add a runtime dependency: `uv add --package wallet <package>`
- Add a dev dependency: `uv add --package wallet --dev <package>`
- Generate or refresh lockfile: `make lock`
- Sync lockfile + local `.venv`: `make sync`
- Optional smoke check (adds a small runtime dep): `make add-rich`

## Project layout
```text
backend/
  src/wallet/
    domain/
    application/
    ports/
    infrastructure/
  tests/
  scripts/
frontend/
docs/
```

## Product docs
- Primary spec: `docs/product/spec.md`
- Vocabulary and UX concepts: `docs/product/concepts.md`
- Archived exploration: `docs/product/archive/`

The product docs are still being established. The current files are placeholders that define the intended canonical locations.

## Configuration
- Workspace config: `pyproject.toml`
- Backend packaging/tooling: `backend/pyproject.toml`
- App settings come from repo-root `.env` with `WALLET_`-prefixed variables
- Current settings: `WALLET_APP_NAME`, `WALLET_ENVIRONMENT`, `WALLET_DEBUG`, `WALLET_API_V1_PREFIX`, `WALLET_FRONTEND_HOST`, `WALLET_BACKEND_CORS_ORIGINS`

## API
- App factory entrypoint: `wallet.api.app:create_app`
- Singleton ASGI app: `wallet.api.main:app`
- Local dev server: `uv --directory backend run poe serve`
- Export OpenAPI for client generation: `uv --directory backend run poe export-openapi`
- OpenAPI JSON: `/api/v1/openapi.json`
- Interactive docs: `/docs`
- Browser clients are allowed via CORS using `WALLET_FRONTEND_HOST` plus any extra `WALLET_BACKEND_CORS_ORIGINS`

## Frontend
- Frontend workspace: `frontend/`
- Frontend env example: `frontend/.env.example`
- Generated client config: `frontend/src/configure-client.ts`
- Frontend Bun container definition: `compose.frontend.yml`
- Install dependencies: `make frontend-install`
- After exporting `frontend/openapi.json`, generate the client with `make frontend-generate-client`
- Run frontend type checks with `make frontend-type`
- Use `make frontend-bun CMD="run <script>"` for ad hoc Bun commands without installing Bun on the host

## Contributing
See `CONTRIBUTING.md`.

## Security
See `SECURITY.md`.

## License
MIT. See `LICENSE`.
