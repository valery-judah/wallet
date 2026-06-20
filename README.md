# Wallet

Money tracking for imperfect real-life habits. The MVP focuses on helping users understand what money moved, from where, to where, and why.

## Requirements
- Python 3.11+
- `uv` (recommended)

## Quickstart
```bash
make init
uv run poe verify
```

## Run
```bash
uv run poe run
```

## Development
Python developer tasks live in Poe. Common commands:

```bash
uv run poe fmt
uv run poe lint
uv run poe type
uv run poe test
uv run poe verify
uv run poe run
```

`make` remains available for bootstrap and wrappers such as `make init`, `make install`, `make verify`, and `make run`.

## Dependencies
- Add a runtime dependency: `uv add <package>`
- Add a dev dependency: `uv add --dev <package>`
- Generate or refresh lockfile: `make lock`
- Sync lockfile + local `.venv`: `make sync`
- Optional smoke check (adds a small runtime dep): `make add-rich`

## Project layout
```text
src/wallet/
tests/
docs/
```

## Product docs
- Primary spec: `docs/product/spec.md`
- Vocabulary and UX concepts: `docs/product/concepts.md`
- Archived exploration: `docs/product/archive/`

## Configuration
- Packaging/config: `pyproject.toml`
- Tooling: `ruff`, `mypy`, `pytest` (configured in `pyproject.toml`)

## Contributing
See `CONTRIBUTING.md`.

## Security
See `SECURITY.md`.

## License
MIT. See `LICENSE`.
