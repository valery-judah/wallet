.DEFAULT_GOAL := help

UV := uv
UV_BACKEND := $(UV) --directory backend
POE := $(UV_BACKEND) run poe
FRONTEND_COMPOSE := HOST_UID=$(shell id -u) HOST_GID=$(shell id -g) docker compose -f compose.frontend.yml
DEV_COMPOSE := HOST_UID=$(shell id -u) HOST_GID=$(shell id -g) docker compose -f compose.dev.yml

PREFERRED_WORKFLOWS := setup run-backend run-stack stop-stack logs-stack gen-client verify check-smoke clean
SETUP_TARGETS := setup setup-sync setup-lock install install-git-hooks
BACKEND_CHECK_TARGETS := gen-openapi fmt lint type test verify check check-smoke check-smoke-managed clean
FRONTEND_DOCKER_TARGETS := run-frontend frontend-install frontend-generate-client frontend-type frontend-build frontend-test frontend-bun run-stack stop-stack logs-stack
COMPAT_ALIAS_TARGETS := init sync lock backend-dev smoke smoke-managed frontend-dev dev-up dev-down dev-logs

.PHONY: help
help: ## Show this help message
	@echo "Usage: make <target>"
	@echo ""
	@print_section() { \
		title="$$1"; \
		targets="$$2"; \
		echo "$$title:"; \
		for target in $$targets; do \
			awk -v target="$$target" 'BEGIN {FS = ":.*## "} $$0 ~ ("^" target ":.*## ") {printf "  %-20s %s\n", target, $$2; exit}' $(MAKEFILE_LIST); \
		done; \
		echo ""; \
	}; \
	print_section "Preferred Workflows" "$(PREFERRED_WORKFLOWS)"; \
	print_section "Setup" "$(SETUP_TARGETS)"; \
	print_section "Backend Checks" "$(BACKEND_CHECK_TARGETS)"; \
	print_section "Frontend / Docker" "$(FRONTEND_DOCKER_TARGETS)"; \
	print_section "Compatibility Aliases" "$(COMPAT_ALIAS_TARGETS)"; \
	echo "Direct backend tasks remain available via Poe:"; \
	echo "  uv --directory backend run poe --help"; \
	echo "  uv --directory backend run poe <task>"

.PHONY: ensure-uv
ensure-uv: ## Check if uv is installed
	@command -v uv >/dev/null 2>&1 || { \
		echo "Error: 'uv' is not installed or not on PATH."; \
		echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		exit 127; \
	}

.PHONY: install-git-hooks
install-git-hooks: ## Configure git to use repo-managed hooks
	@if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then \
		git config core.hooksPath .githooks; \
	else \
		echo "Not in a git repository. Skipping git hooks setup."; \
	fi

.PHONY: setup-sync
setup-sync: ensure-uv ## Sync dependencies into the local .venv
	$(UV) sync --package wallet --group dev

.PHONY: sync
sync: setup-sync ## Compatibility alias for setup-sync

.PHONY: setup-lock
setup-lock: ensure-uv ## Generate or refresh uv.lock
	$(UV) lock

.PHONY: lock
lock: setup-lock ## Compatibility alias for setup-lock

.PHONY: install
install: setup-sync install-git-hooks ## Install the backend package in editable mode via uv sync

.PHONY: setup
setup: install ## Bootstrap local dev environment

.PHONY: init
init: setup ## Compatibility alias for setup

.PHONY: add-rich
add-rich: ensure-uv ## Add `rich` dependency via uv (updates pyproject + uv.lock)
	$(UV) add --package wallet rich
	$(UV) sync --package wallet --group dev

# --- Code Quality ---

.PHONY: fmt
fmt: ensure-uv ## Format and auto-fix lint issues
	$(POE) fmt

.PHONY: lint
lint: ensure-uv ## Run lint checks
	$(POE) lint

.PHONY: type
type: ensure-uv ## Run static type checks
	$(POE) type

# --- Local Run ---

.PHONY: run-backend
run-backend: install ## Run the backend locally with reload
	$(POE) serve

.PHONY: backend-dev
backend-dev: run-backend ## Compatibility alias for run-backend

# --- Testing ---

.PHONY: test
test: install ## Run unit tests
	$(POE) test

.PHONY: check-smoke
check-smoke: install ## Run manual API smoke scenarios against an existing backend
	$(POE) smoke

.PHONY: smoke
smoke: check-smoke ## Compatibility alias for check-smoke

.PHONY: check-smoke-managed
check-smoke-managed: install ## Run manual API smoke scenarios with a managed backend
	$(POE) smoke-managed

.PHONY: smoke-managed
smoke-managed: check-smoke-managed ## Compatibility alias for check-smoke-managed

.PHONY: clean
clean: ensure-uv ## Remove caches and generated local artifacts
	$(POE) clean

.PHONY: verify
verify: install ## Run read-only verification checks
	$(POE) verify

.PHONY: check
check: verify ## Run the full verification suite

# --- Code Generation ---

.PHONY: gen-openapi
gen-openapi: install ## Export the backend OpenAPI schema for client generation
	$(POE) export-openapi

.PHONY: gen-client
gen-client: gen-openapi frontend-install ## Export OpenAPI and regenerate the frontend API client
	$(FRONTEND_COMPOSE) run --rm bun run generate-client

# --- Frontend (Bun in Docker) ---

.PHONY: frontend-install
frontend-install: ## Compatibility alias for the frontend dependency install step
	$(FRONTEND_COMPOSE) run --rm bun install

.PHONY: frontend-generate-client
frontend-generate-client: ## Compatibility alias for frontend client generation only
	$(FRONTEND_COMPOSE) run --rm bun run generate-client

.PHONY: frontend-type
frontend-type: ## Compatibility alias for frontend type checks
	$(FRONTEND_COMPOSE) run --rm bun run typecheck

.PHONY: frontend-build
frontend-build: ## Compatibility alias for the frontend production build
	$(FRONTEND_COMPOSE) run --rm bun run build

.PHONY: frontend-test
frontend-test: ## Compatibility alias for frontend UI tests
	$(FRONTEND_COMPOSE) run --rm bun run test

.PHONY: run-frontend
run-frontend: frontend-install ## Run the frontend dev server in Docker on http://localhost:5173
	$(FRONTEND_COMPOSE) up frontend

.PHONY: frontend-dev
frontend-dev: run-frontend ## Compatibility alias for run-frontend

.PHONY: frontend-bun
frontend-bun: ## Compatibility alias for arbitrary Bun commands in Docker
	@test -n "$(CMD)" || (echo "Usage: make frontend-bun CMD='<bun args>'" && exit 2)
	$(FRONTEND_COMPOSE) run --rm bun $(CMD)

# --- Local Full Stack (Optional Docker Compose) ---

.PHONY: run-stack
run-stack: frontend-install ## Run the optional local Docker Compose stack on http://localhost:8000 and http://localhost:5173
	$(DEV_COMPOSE) up --build

.PHONY: dev-up
dev-up: run-stack ## Compatibility alias for run-stack

.PHONY: stop-stack
stop-stack: ## Stop the optional local Docker Compose stack
	$(DEV_COMPOSE) down

.PHONY: dev-down
dev-down: stop-stack ## Compatibility alias for stop-stack

.PHONY: logs-stack
logs-stack: ## Tail logs for the optional local Docker Compose stack
	$(DEV_COMPOSE) logs -f

.PHONY: dev-logs
dev-logs: logs-stack ## Compatibility alias for logs-stack
