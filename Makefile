.DEFAULT_GOAL := help

UV_RUN := uv run
POE := $(UV_RUN) poe

.PHONY: help
help: ## Show this help message
	@echo "Usage: make <target>"
	@echo ""
	@echo "Repo & Infrastructure Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
	@echo ""
	@echo "Python developer tasks live in Poe."
	@echo "Run 'uv run poe --help' or 'uv run poe <task>' for fmt/lint/type/test/verify."

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
	uv sync --group dev

.PHONY: lock
lock: ensure-uv ## Generate or refresh uv.lock
	uv lock

.PHONY: install
install: sync install-git-hooks ## Install the package in editable mode
	uv pip install --editable .

.PHONY: init
init: sync install ## Bootstrap local dev environment

.PHONY: add-rich
add-rich: ensure-uv ## Add `rich` dependency via uv (updates pyproject + uv.lock)
	uv add rich
	uv sync --group dev

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
