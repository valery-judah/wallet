# Wallet

Money tracking for imperfect real-life habits. The MVP focuses on helping users understand what money moved, from where, to where, and why.

## Requirements
- Python 3.11+
- `uv` (recommended)

## Quickstart
```bash
make init
make verify
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
uv run poe clean
uv run poe verify
```

You can also target the backend explicitly from the root with `uv --directory backend run poe <task>`.

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

## Contributing
See `CONTRIBUTING.md`.

## Security
See `SECURITY.md`.

## License
MIT. See `LICENSE`.
