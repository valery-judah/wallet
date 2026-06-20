# Wallet

Simple money tracking app. The MVP focuses on helping users understand what money moved, from where, to where, and why.

## Requirements
- Python 3.11+
- `uv` (recommended)
- Docker with Compose support for frontend workflows

## Quickstart
See [docs/evergreen/runbook.md](docs/evergreen/runbook.md) for the canonical workflow-first command catalog built around `make setup`, `make run-backend`, `make gen-client`, and `make run-stack`.

## Development
The backend lives in `backend/`. Use root-level `make` wrappers for the preferred workflow surface, or run Poe directly from inside `backend/` when you want backend-specific task control. For local backend startup from the repo root, use `make run-backend`. The runbook is the canonical source for command usage and environment workflows.

## Dependencies
Dependency management commands are documented in [docs/evergreen/runbook.md](docs/evergreen/runbook.md).

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

The product docs are still being established. The current files are placeholders that define the intended canonical locations.

## Configuration
- Workspace config: `pyproject.toml`
- Backend packaging/tooling: `backend/pyproject.toml`
- App settings come from repo-root `.env` with `WALLET_`-prefixed variables
- Current settings: `WALLET_APP_NAME`, `WALLET_ENVIRONMENT`, `WALLET_DEBUG`, `WALLET_API_V1_PREFIX`, `WALLET_FRONTEND_HOST`, `WALLET_BACKEND_CORS_ORIGINS`

## API
- App factory entrypoint: `wallet.api.app:create_app`
- Singleton ASGI app: `wallet.api.main:app`
- OpenAPI JSON: `/api/v1/openapi.json`
- Interactive docs: `/docs`
- Browser clients are allowed via CORS using `WALLET_FRONTEND_HOST`, its loopback twin when applicable, plus any extra `WALLET_BACKEND_CORS_ORIGINS`

Run and verification commands live in [docs/evergreen/runbook.md](docs/evergreen/runbook.md).

## Frontend
- Frontend workspace: `frontend/`
- Frontend env example: `frontend/.env.example`
- Generated client config: `frontend/src/configure-client.ts`
- Frontend Bun container definition: `compose.frontend.yml`
- Optional full-stack local Compose definition: `compose.dev.yml`
- Main routes: `/cards`, `/cards/new`, `/cards/$cardId`
- `http://127.0.0.1:5173` also works automatically with the default CORS settings

Frontend workflow commands live in [docs/evergreen/runbook.md](docs/evergreen/runbook.md).

## Contributing
See `CONTRIBUTING.md`.

## Security
See `SECURITY.md`.

## License
MIT. See `LICENSE`.
