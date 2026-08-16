# Wallet

A money tracking app that shows what money moved, from where, to where, and why. Wallet
Assistant, the chat entry point, checks balances and records expenses, income, transfers, and
balance adjustments from everyday language.

## Requirements
- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/)
- Docker with Compose, for the frontend and the local stack
- [Ollama](https://ollama.com/) with the `qwen3.5:9b` model, for Wallet Assistant

## Quick start

```bash
make setup
make verify
```

Start the seeded backend and frontend in Docker:

```bash
ollama pull qwen3.5:9b
make stack-up
```

Open [http://localhost:5173/assistant](http://localhost:5173/assistant). Check the stack with
`make stack-status` and `make stack-logs`, and stop it with `make stack-down`.

For day-to-day development, run the backend on the host and the frontend in Docker, each in its
own terminal:

```bash
WALLET_SEED_SAMPLE_DATA=true make backend-run
make frontend-run
```

`make help` lists every command. The [runbook](docs/evergreen/runbook.md) explains when to use
each one.

## Using Wallet Assistant

Describe a transaction with as much information as you have, answer any follow-up questions, and
use the **Confirm** action to record it. While a transaction task is active, cancel it before
asking about balances or starting different work. The
[proposed help page](docs/product/assistant-help-page.md) has the complete user guidance.

## Repository layout

```text
backend/            Python package, tests, and devex scripts (Poe tasks in poe_tasks.toml)
frontend/           React app and generated API client
docs/               Docs index in docs/README.md
compose.dev.yml     Local Docker stack: backend and frontend
compose.frontend.yml  Bun tooling container
Makefile            Command catalog
```

## Docs
- [Docs index](docs/README.md)
- [Runbook](docs/evergreen/runbook.md): commands and local development
- [Product frame](docs/product/wallet-frame.md) and [spec](docs/product/spec.md)
- [Domain concepts](docs/product/concepts.md)
- [Backend](backend/README.md) and [frontend](frontend/README.md) notes

## Configuration
- App settings come from the repository-root `.env` with `WALLET_`-prefixed variables. See
  `.env.example` and the [backend README](backend/README.md#configuration).
- Workspace config: `pyproject.toml`. Backend packaging and tools: `backend/pyproject.toml`.

## Contributing
See `CONTRIBUTING.md`.

## Security
See `SECURITY.md`.

## License
MIT. See `LICENSE`.
