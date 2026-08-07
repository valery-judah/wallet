# Wallet

Simple money tracking app. The MVP focuses on helping users understand what money moved, from where, to where, and why.

## Requirements
- Python 3.11+
- `uv` (recommended)
- Docker with Compose support for frontend workflows

## Quickstart
See [docs/evergreen/runbook.md](docs/evergreen/runbook.md) for the canonical workflow-first command catalog built around `make setup`, `make run-backend`, `make gen-client`, and `make run-stack`.

## Wallet Assistant

Wallet Assistant is the conversational entry point for checking balances and recording money
movements in everyday language. It supports balance requests, expenses, income, transfers, and
balance adjustments.

The assistant uses a locally running Ollama service. Confirm that Ollama is available and install
the default model before the first run:

```bash
ollama list
ollama pull qwen3.5:9b
```

For the simplest product walkthrough, start the seeded backend and frontend together:

```bash
make run-stack
```

Then open [http://localhost:5173/assistant](http://localhost:5173/assistant). The stack runs in the
foreground; stop it with `Ctrl+C`, then run `make stop-stack` to remove its resources.

For split local development, keep these commands running in separate terminals:

```bash
# Terminal 1: backend with sample Wallet data
WALLET_SEED_SAMPLE_DATA=true make run-backend

# Terminal 2: frontend
make run-frontend
```

Describe a transaction with as much information as you have, answer any follow-up questions, and
use the displayed **Confirm** action to record it. While a transaction task is active, cancel it
before asking about balances or starting different work. The planned in-app help experience and
its complete user guidance are defined in the
[proposed Wallet Assistant help-page specification](docs/product/assistant-help-page.md).

## Development
The backend lives in `backend/`. Use root-level `make` wrappers for the preferred workflow surface, or run Poe directly from inside `backend/` when you want backend-specific task control. For local backend startup from the repo root, use `make run-backend`. The runbook is the canonical source for command usage and environment workflows.

## Product docs

- Primary spec: [docs/product/spec.md](docs/product/spec.md)
- Vocabulary and UX concepts: [docs/product/concepts.md](docs/product/concepts.md)
- Proposed Assistant help page:
  [docs/product/assistant-help-page.md](docs/product/assistant-help-page.md)

## Configuration
- Workspace config: `pyproject.toml`
- Backend packaging/tooling: `backend/pyproject.toml`
- App settings come from repo-root `.env` with `WALLET_`-prefixed variables
- Current settings: `WALLET_APP_NAME`, `WALLET_ENVIRONMENT`, `WALLET_DEBUG`,
  `WALLET_LOG_LEVEL`, `WALLET_API_V1_PREFIX`, `WALLET_FRONTEND_HOST`,
  `WALLET_BACKEND_CORS_ORIGINS`, `WALLET_SEED_SAMPLE_DATA`, `WALLET_OLLAMA_BASE_URL`,
  `WALLET_OLLAMA_MODEL`, `WALLET_OLLAMA_TIMEOUT_SECONDS`, and
  `WALLET_OLLAMA_CONTEXT_LENGTH`

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
- Main routes: `/accounts`, `/accounts/new`, `/accounts/$accountId`, `/categories`,
  `/transactions`, and `/assistant`
- `http://127.0.0.1:5173` also works automatically with the default CORS settings

Frontend workflow commands live in [docs/evergreen/runbook.md](docs/evergreen/runbook.md).

## Contributing
See `CONTRIBUTING.md`.

## Security
See `SECURITY.md`.

## License
MIT. See `LICENSE`.
