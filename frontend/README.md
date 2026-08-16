# Wallet Frontend

This workspace contains the wallet UI that consumes the FastAPI backend through
the generated OpenAPI client.

## Requirements
- Docker with Compose support
- The backend OpenAPI schema exported from this repo
- `uv` for the backend export step

## Workflow
From the repo root:

```bash
make backend-run      # terminal 1
make frontend-run     # terminal 2
make api-client       # after an API change
make frontend-type
make frontend-test
```

`make api-client` writes the generated TypeScript client into `src/client/`. `node_modules` and
the Bun package cache live in Docker volumes. The dev server runs on
[http://localhost:5173](http://localhost:5173). `make verify` runs the backend checks and the
frontend type check.

Optional full-stack Compose mode:

```bash
make stack-up
```

That starts the seeded backend and the frontend in containers and returns once they run. Use
`make stack-status`, `make stack-logs`, and `make stack-down` to check and stop them. The host
backend flow above is the main developer workflow.

## Routes
- `/accounts` lists accounts and links to the create flow or a selected account
- `/accounts/new` creates an account using the backend contract directly
- `/accounts/$accountId` shows the selected account and lists recent activity
- `/categories` manages categories
- `/transactions` records expense transactions through a withdraw-oriented flow
- `/assistant` opens Wallet Assistant

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
make frontend-bun ARGS='run <script>'
```

Useful commands:

```bash
make frontend-build
make frontend-type
make frontend-test
make frontend-run
```

## API Base URL
Set `VITE_API_URL` in `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

After client generation, `src/configure-client.ts` applies that value to the
generated OpenAPI runtime config.
