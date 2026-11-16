SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# examples/js/Makefile — copy to the repo root, then work through the CHANGE points.
#
# CHANGE: the project name in `help`; add `run`/`stop` for a service or `dist` for build artifacts.
# CHANGE: the `tools` target — keep it only if one of the repo's own scripts needs a toolchain
#         (a maintainer script that sets a secret or cuts a release). Delete it and the `install`
#         dependency on it when nothing does.
# DO NOT CHANGE: the shell pin, the target meanings, and `check`'s composition. CI and the pre-push
#               hook both run `check`; editing it in one place only is how the two drift.

NODE := node
NPM := npm

# Toolchain for repo operations. Nothing here uses the system interpreter.
UV ?= uv
PYTHON_VERSION ?= 3.14
TOOLS_BIN ?= .tools/bin
TOOLS_VENV ?= .tools/venv
TOOLS_PYTHON := $(TOOLS_VENV)/bin/python

.PHONY: help install setup deps tools lint lint-check typecheck test coverage format clean check

help:
	@echo "CHANGE: project name"
	@echo "  make install    one shot: deps, .env, hooks, tools — what a clone and CI both run"
	@echo "  make setup      dependencies only"
	@echo "  make lint       report lint findings"
	@echo "  make typecheck  tsc --noEmit"
	@echo "  make test       typecheck + tests (the gate)"
	@echo "  make coverage   tests with a clover report in coverage/"
	@echo "  make format     rewrite formatting in place"
	@echo "  make check      lint + typecheck, what pre-push runs"
	@echo "  make clean      remove provisioned state, never user data"

install: setup tools
	@echo "Installed. Next: make test."

setup: deps

deps:
	$(NPM) install
	@if [ -f .env.example ] && [ ! -f .env ]; then cp .env.example .env; fi

tools:
	@command -v $(UV) >/dev/null 2>&1 || (mkdir -p $(TOOLS_BIN) && curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=$(TOOLS_BIN) sh)
	@test -x $(TOOLS_PYTHON) || ($(UV) venv --python $(PYTHON_VERSION) $(TOOLS_VENV))
	@$(UV) pip install --quiet --python $(TOOLS_PYTHON) pynacl

lint:
	$(NPM) run lint

lint-check:
	$(NPM) run lint:check

typecheck:
	$(NPM) run typecheck

test: typecheck
	$(NPM) run test

coverage:
	$(NPM) run coverage

format:
	$(NPM) run format

clean:
	rm -rf node_modules coverage .vitest dist .tools

# The single gate CI and the pre-push hook both run: no drift between them.
check: lint-check typecheck
