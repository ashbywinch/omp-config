# Makefile for <project> — single dev entry point
#
# CHANGE: `<pkg>` -> your package name; add project-specific targets below
# the `clean` target (keep them behind `deps`, never `install-hooks`).
#
# DO NOT CHANGE:
# - SHELL + .SHELLFLAGS (the shell pin): make's default /bin/sh is dash on
#   Debian/Ubuntu — including the CI runners — and dash has no `pipefail`.
#   Without the pin, a recipe with bash-isms passes on macOS and dies on CI
#   with "Illegal option -o pipefail" (houses 2026-08: #56/#57 CI failure).
# - `deps` never depends on `install-hooks`: a hook that calls `make check`
#   would re-copy/refuse the very hook file — the pre-push deadlock.
# - `check` = lint-check + typecheck, the single gate CI and pre-push both run.
# - `clean` never touches user data (only .venv + generated reports).

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: help setup deps uv-sync install-hooks run test test-e2e check lint lint-check lint-github typecheck typecheck-update-baseline format coverage clean

# CHANGE: tool paths. uv is the package manager (installs itself if missing).
PYTHON := .venv/bin/python
UV := $(shell command -v uv 2>/dev/null || echo $(HOME)/.local/bin/uv)
RUFF := .venv/bin/ruff
PYTEST := .venv/bin/pytest

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

help:
	@echo "Available commands:"
	@echo "  ${GREEN}make setup${NC}        Create venv, install deps + pre-commit hooks, ensure .env exists"
	@echo "  ${GREEN}make check${NC}        Lint + typecheck — the gate CI and the pre-push hook run"
	@echo "  ${GREEN}make test${NC}         Run tests (lint + typecheck gate)"
	@echo "  ${GREEN}make lint${NC}         Check code quality"
	@echo "  ${GREEN}make format${NC}       Auto-fix formatting issues"
	@echo "  ${GREEN}make coverage${NC}     Run tests with coverage report"
	@echo "  ${GREEN}make clean${NC}        Remove .venv and generated files"

setup: deps install-hooks
	@[ -f .env ] || cp .env.example .env
	@echo "${GREEN}✓ Setup complete${NC}"

# What the CHECK targets actually need — no hook machinery. A check must
# never depend on install-hooks (see the deadlock note at the top).
deps: uv-sync

uv-sync:
	@$(UV) --version >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
	@$(UV) sync

install-hooks:
	@mkdir -p .git/hooks
	@for hook in pre-commit pre-push; do \
		if [ -f .git/hooks/$$hook ] && ! cmp -s scripts/$$hook .git/hooks/$$hook; then \
			echo "${YELLOW}An existing $$hook hook differs — move it aside and re-run 'make install-hooks'${NC}"; \
			exit 1; \
		fi; \
		cp scripts/$$hook .git/hooks/$$hook; \
		chmod +x .git/hooks/$$hook; \
	done
	@echo "${GREEN}✓ Hooks installed (pre-commit: lint; pre-push: make check)${NC}"

run: setup
	@$(UV) run --env-file .env python -m <pkg>

# The exact gate a push must pass — run identically by CI and the pre-push
# hook (single source of truth; no test run — too slow for a hook, and CI's
# `make test` already includes these).
check: lint-check typecheck

test: deps lint-check typecheck
	@$(PYTEST) tests/ -q --tb=short

test-e2e: deps lint-check
	@$(PYTEST) tests/e2e/ -m e2e -q

coverage: deps
	@$(UV) run coverage run -m pytest tests/ -q --tb=short
	@$(UV) run coverage report -m
	@$(UV) run coverage xml
	@$(UV) run coverage html
	@echo "${GREEN}Coverage report: htmlcov/index.html${NC}"

lint: deps lint-check

lint-check:  # Shared with the pre-commit hook — single source of truth for the lint scope
	@$(RUFF) check <pkg>/ tests/

lint-github: deps   # CI only: findings surface as PR annotations
	@$(RUFF) check <pkg>/ tests/ --output-format=github

# pyrefly + BOTH-direction baseline lock (new errors AND stale entries fail)
typecheck: deps
	@$(PYTHON) scripts/pyrefly-lock.py check --pyrefly-config pyrefly.toml

# After a deliberate diagnostic change, commit the refresh
typecheck-update-baseline: deps
	@$(PYTHON) scripts/pyrefly-lock.py update-baseline --pyrefly-config pyrefly.toml

format: setup
	@$(RUFF) check --fix <pkg>/ tests/
	@$(RUFF) format <pkg>/ tests/

clean:
	@rm -rf .venv htmlcov/
	@rm -f .coverage coverage.xml
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
