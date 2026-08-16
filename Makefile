.DEFAULT_GOAL := help

# Make is the single entry point for repository workflows. Backend targets call
# Poe tasks in backend/poe_tasks.toml; frontend targets run Bun in Docker.
# Target names start with the part of the system they act on: setup-, backend-,
# frontend-, api-, stack-, smoke-. Checks (fmt, lint, type, test, verify) keep
# short names. Pass extra arguments with ARGS='...'.

UV := uv
UV_BACKEND := $(UV) --directory backend
POE := $(UV_BACKEND) run poe
COMPOSE_ENV := HOST_UID=$(shell id -u) HOST_GID=$(shell id -g)
FRONTEND_COMPOSE := $(COMPOSE_ENV) docker compose -f compose.frontend.yml
STACK_COMPOSE := $(COMPOSE_ENV) docker compose -f compose.dev.yml
ARGS ?=

SETUP_TARGETS := setup setup-sync setup-lock setup-hooks clean
CHECK_TARGETS := verify verify-backend fmt fmt-check lint type test test-control
BACKEND_TARGETS := backend-run backend-seed
FRONTEND_TARGETS := frontend-run frontend-install frontend-type frontend-test frontend-build frontend-client frontend-bun
API_TARGETS := api-schema api-client
STACK_TARGETS := stack-up stack-status stack-logs stack-down
SMOKE_TARGETS := smoke-api smoke-api-managed smoke-capture smoke-router
ALIAS_TARGETS := install install-git-hooks check run-backend run-frontend run-stack stop-stack logs-stack gen-openapi gen-client frontend-generate-client check-smoke check-smoke-managed check-capture-smoke check-router-smoke

.PHONY: help
help: ## Show this help message
	@echo "Usage: make <target> [ARGS='<extra arguments>']"
	@echo ""
	@print_section() { \
		title="$$1"; \
		targets="$$2"; \
		echo "$$title:"; \
		for target in $$targets; do \
			awk -v target="$$target" 'BEGIN {FS = ":.*## "} $$0 ~ ("^" target ":.*## ") {printf "  %-26s %s\n", target, $$2; exit}' $(MAKEFILE_LIST); \
		done; \
		echo ""; \
	}; \
	print_section "Setup" "$(SETUP_TARGETS)"; \
	print_section "Checks (read-only except fmt)" "$(CHECK_TARGETS)"; \
	print_section "Backend on the host" "$(BACKEND_TARGETS)"; \
	print_section "Frontend (Bun in Docker)" "$(FRONTEND_TARGETS)"; \
	print_section "API contract (writes generated files)" "$(API_TARGETS)"; \
	print_section "Local Docker stack" "$(STACK_TARGETS)"; \
	print_section "Smoke checks (manual, some need Ollama)" "$(SMOKE_TARGETS)"; \
	print_section "Aliases for old names (use the new names)" "$(ALIAS_TARGETS)"

.PHONY: ensure-uv
ensure-uv:
	@command -v uv >/dev/null 2>&1 || { \
		echo "Error: 'uv' is not installed or not on PATH."; \
		echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		exit 127; \
	}

# --- Setup ---

.PHONY: setup
setup: setup-sync setup-hooks ## Sync dependencies and configure Git hooks

.PHONY: setup-sync
setup-sync: ensure-uv ## Sync dependencies from uv.lock into the local .venv
	$(UV) sync --package wallet --group dev

.PHONY: setup-lock
setup-lock: ensure-uv ## Generate or refresh uv.lock (writes tracked files)
	$(UV) lock

.PHONY: setup-hooks
setup-hooks: ## Configure Git to use the hooks in .githooks/
	if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		git config core.hooksPath .githooks; \
	else \
		echo "Not in a git repository. Skipping git hooks setup."; \
	fi

.PHONY: clean
clean: ensure-uv ## Remove caches and generated local artifacts
	$(POE) clean

# --- Checks ---

.PHONY: verify
verify: verify-backend frontend-type ## Run all read-only checks: backend checks and frontend types

.PHONY: verify-backend
verify-backend: setup-sync ## Run backend format check, lint, types, and tests (used by the pre-commit hook)
	$(POE) verify

.PHONY: fmt
fmt: ensure-uv ## Format backend code and auto-fix lint issues (writes files)
	$(POE) fmt

.PHONY: fmt-check
fmt-check: ensure-uv ## Check backend formatting without changing files
	$(POE) fmt-check

.PHONY: lint
lint: ensure-uv ## Run backend format check and lint
	$(POE) lint

.PHONY: type
type: ensure-uv ## Run strict backend type checks
	$(POE) type

.PHONY: test
test: setup-sync ## Run backend tests (ARGS='-k <expr>' to filter)
	$(POE) test $(ARGS)

.PHONY: test-control
test-control: setup-sync ## Run deterministic control-layer and capability system tests
	$(POE) test-control $(ARGS)

# --- Backend on the host ---

.PHONY: backend-run
backend-run: setup-sync ## Run the backend on http://localhost:8000 with reload (foreground)
	$(POE) serve

.PHONY: backend-seed
backend-seed: setup-sync ## Build and print the local sample dataset
	$(POE) seed-sample-data

# --- Frontend (Bun in Docker) ---

.PHONY: frontend-run
frontend-run: frontend-install ## Run the frontend dev server on http://localhost:5173 (foreground)
	$(FRONTEND_COMPOSE) up frontend

.PHONY: frontend-install
frontend-install: ## Install frontend dependencies
	$(FRONTEND_COMPOSE) run --rm bun install

.PHONY: frontend-type
frontend-type: frontend-install ## Run frontend type checks
	$(FRONTEND_COMPOSE) run --rm bun run typecheck

.PHONY: frontend-test
frontend-test: ## Run frontend UI tests
	$(FRONTEND_COMPOSE) run --rm bun run test

.PHONY: frontend-build
frontend-build: ## Build the frontend production bundle
	$(FRONTEND_COMPOSE) run --rm bun run build

.PHONY: frontend-client
frontend-client: ## Regenerate the frontend API client from frontend/openapi.json
	$(FRONTEND_COMPOSE) run --rm bun run generate-client

.PHONY: frontend-bun
frontend-bun: ## Run any Bun command (ARGS='<bun args>')
	@test -n "$(ARGS)$(CMD)" || (echo "Usage: make frontend-bun ARGS='<bun args>'" && exit 2)
	$(FRONTEND_COMPOSE) run --rm bun $(ARGS) $(CMD)

# --- API contract ---

.PHONY: api-schema
api-schema: setup-sync ## Export the backend OpenAPI schema to frontend/openapi.json
	$(POE) export-openapi

.PHONY: api-client
api-client: api-schema frontend-install ## Export the OpenAPI schema and regenerate the frontend API client
	$(FRONTEND_COMPOSE) run --rm bun run generate-client

# --- Local Docker stack ---

.PHONY: stack-up
stack-up: frontend-install ## Build and start the seeded backend and frontend in Docker; returns once they run
	$(STACK_COMPOSE) up --build --detach --wait
	@echo "Backend:  http://localhost:8000"
	@echo "Frontend: http://localhost:5173"

.PHONY: stack-status
stack-status: ## Show the state of the local Docker stack
	$(STACK_COMPOSE) ps --all

.PHONY: stack-logs
stack-logs: ## Print recent stack logs (ARGS='--follow' to keep following)
	$(STACK_COMPOSE) logs --tail=200 $(ARGS)

.PHONY: stack-down
stack-down: ## Stop and remove the stack containers; keeps the frontend volumes
	$(STACK_COMPOSE) down

# --- Smoke checks ---

.PHONY: smoke-api
smoke-api: setup-sync ## Run API smoke scenarios against a backend already on port 8000
	$(POE) smoke $(ARGS)

.PHONY: smoke-api-managed
smoke-api-managed: setup-sync ## Run API smoke scenarios against a temporary backend on port 8010
	$(POE) smoke-managed $(ARGS)

.PHONY: smoke-capture
smoke-capture: setup-sync ## Run transaction capture scenarios against local Ollama
	$(POE) capture-smoke $(ARGS)

.PHONY: smoke-router
smoke-router: setup-sync ## Run the message routing corpus against local Ollama
	$(POE) router-smoke $(ARGS)

# --- Aliases for old names ---

.PHONY: $(ALIAS_TARGETS)
install: setup ## Alias for setup
install-git-hooks: setup-hooks ## Alias for setup-hooks
check: verify ## Alias for verify
run-backend: backend-run ## Alias for backend-run
run-frontend: frontend-run ## Alias for frontend-run
run-stack: stack-up ## Alias for stack-up
stop-stack: stack-down ## Alias for stack-down
logs-stack: stack-logs ## Alias for stack-logs
gen-openapi: api-schema ## Alias for api-schema
gen-client: api-client ## Alias for api-client
frontend-generate-client: frontend-client ## Alias for frontend-client
check-smoke: smoke-api ## Alias for smoke-api
check-smoke-managed: smoke-api-managed ## Alias for smoke-api-managed
check-capture-smoke: smoke-capture ## Alias for smoke-capture
check-router-smoke: smoke-router ## Alias for smoke-router
