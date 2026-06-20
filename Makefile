.DEFAULT_GOAL := help

UV := uv
UV_BACKEND := $(UV) --directory backend
POE := $(UV_BACKEND) run poe
FRONTEND_COMPOSE := HOST_UID=$(shell id -u) HOST_GID=$(shell id -g) docker compose -f compose.frontend.yml

.PHONY: help
help: ## Show this help message
	@echo "Usage: make <target>"
	@echo ""
	@echo "Repo & Infrastructure Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
	@echo ""
	@echo "Backend developer tasks live in Poe."
	@echo "Run 'uv --directory backend run poe --help' or 'uv --directory backend run poe <task>' for fmt/lint/type/test/verify."

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

.PHONY: sync
sync: ensure-uv ## Sync dependencies into the local .venv
	$(UV) sync --package wallet --group dev

.PHONY: lock
lock: ensure-uv ## Generate or refresh uv.lock
	$(UV) lock

.PHONY: install
install: sync install-git-hooks ## Install the backend package in editable mode via uv sync

.PHONY: init
init: sync install ## Bootstrap local dev environment

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

# --- Testing ---

.PHONY: test
test: install ## Run unit tests
	$(POE) test

.PHONY: clean
clean: ensure-uv ## Remove caches and generated local artifacts
	$(POE) clean

.PHONY: verify
verify: install ## Run read-only verification checks
	$(POE) verify

.PHONY: check
check: verify ## Run the full verification suite

# --- Frontend (Bun in Docker) ---

.PHONY: frontend-install
frontend-install: ## Install frontend dependencies inside the Bun container
	$(FRONTEND_COMPOSE) run --rm bun install

.PHONY: frontend-generate-client
frontend-generate-client: ## Generate the frontend API client inside the Bun container
	$(FRONTEND_COMPOSE) run --rm bun run generate-client

.PHONY: frontend-type
frontend-type: ## Run frontend type checks inside the Bun container
	$(FRONTEND_COMPOSE) run --rm bun run typecheck

.PHONY: frontend-bun
frontend-bun: ## Run an arbitrary Bun command inside the frontend container: make frontend-bun CMD="run <script>"
	@test -n "$(CMD)" || (echo "Usage: make frontend-bun CMD='<bun args>'" && exit 2)
	$(FRONTEND_COMPOSE) run --rm bun $(CMD)
