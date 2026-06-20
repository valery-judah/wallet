# Wallet Backend

Python backend package for the Wallet product.

## Requirements
- Python 3.11+
- `uv`

## Working here
From `backend/`:

```bash
uv sync --group dev
uv run poe verify
```

From the repo root, the equivalent Poe commands are:

```bash
uv --directory backend run poe verify
```

## Layout
```text
src/wallet/
tests/
scripts/devex/
```
