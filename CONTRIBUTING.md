# Contributing

## Development setup
```bash
make init
```

## Quality checks
```bash
make fmt
make lint
make type
make test
make verify
```

## Adding dependencies
- Runtime: `uv add --package wallet <package>`
- Dev: `uv add --package wallet --dev <package>`

## Pull requests
- Keep changes small and focused.
- Add/update tests for behavior changes.
- Ensure `make verify` passes.
