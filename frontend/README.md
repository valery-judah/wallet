# Wallet Frontend

This workspace contains the wallet UI that consumes the FastAPI backend through
the generated OpenAPI client. The current slice covers three user flows:
- list accounts
- create a new account
- open an account and withdraw money

## Requirements
- Docker with Compose support
- The backend OpenAPI schema exported from this repo
- `uv` for the backend export step

## Workflow
From the repo root:

```bash
make verify
uv --directory backend run poe serve
uv --directory backend run poe export-openapi
make frontend-install
make frontend-generate-client
make frontend-type
make frontend-test
make frontend-dev
```

This writes the generated TypeScript client into `src/client/` and keeps both
`node_modules` and the Bun package cache inside Docker-managed volumes. The dev
server runs on [http://localhost:5173](http://localhost:5173). `make verify`
from the repo root now includes frontend TypeScript validation in addition to
the backend verification suite.

Optional full-stack Compose mode:

```bash
make dev-up
```

That starts both the backend and the frontend in containers. The host-`uv`
backend flow above remains the primary developer workflow.

## Routes
- `/accounts` lists accounts and links to the create flow or a selected account
- `/accounts/new` creates an account using the backend contract directly
- `/accounts/$accountId` shows the selected account and supports withdrawals

## Bun Container
The Bun tooling and dev-server containers are defined in
`../compose.frontend.yml` and built from `./Dockerfile`. They bind-mount this
`frontend/` directory into the container at `/workspace/frontend`, so generated
code and source edits persist on the host repo without requiring Bun to be
installed locally.

The optional combined local stack lives in `../compose.dev.yml`. It reuses the
same frontend image and volumes, but also starts the backend container on
`http://localhost:8000`.

For ad hoc commands, use:

```bash
make frontend-bun CMD="run <script>"
```

Useful commands:

```bash
make frontend-build
make frontend-type
make frontend-test
make frontend-dev
```

## API Base URL
Set `VITE_API_URL` in `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

After client generation, `src/configure-client.ts` applies that value to the
generated OpenAPI runtime config.
