# Wallet Frontend

This workspace is the starting point for UI-side integration with the Wallet
FastAPI backend. It currently focuses on generated API client consumption rather
than a full application shell.

## Requirements
- Docker with Compose support
- The backend OpenAPI schema exported from this repo
- `uv` for the backend export step

## Workflow
From the repo root:

```bash
uv --directory backend run poe export-openapi
make frontend-install
make frontend-generate-client
make frontend-type
```

This writes the generated TypeScript client into `src/client/` and keeps both
`node_modules` and the Bun package cache inside Docker-managed volumes.

## Bun Container
The Bun tooling container is defined in `../compose.frontend.yml` and built from
`./Dockerfile`. It bind-mounts this `frontend/` directory into the container at
`/workspace/frontend`, so generated code and source edits persist on the host
repo without requiring Bun to be installed locally.

For ad hoc commands, use:

```bash
make frontend-bun CMD="run <script>"
```

## API Base URL
Set `VITE_API_URL` in `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

After client generation, `src/configure-client.ts` applies that value to the
generated OpenAPI runtime config.
