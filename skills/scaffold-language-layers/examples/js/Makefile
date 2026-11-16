# examples/js/Makefile — copy to the repo root, then work through the CHANGE points.
#
# CHANGE: the project name in `help`; add `run`/`stop` for a service or `dist` for build artifacts.
# CHANGE: the `tools` target — keep it only if a script the repo runs needs a toolchain (setting a
#         secret, cutting a release). Delete it and `install`'s dependency on it when nothing does.
#
# DO NOT CHANGE:
# - SHELL + .SHELLFLAGS (the shell pin): make's default /bin/sh is dash on Debian/Ubuntu — including
#   the CI runners — and dash has no `pipefail`, so a bash-ism passes locally and dies in CI.
# - `deps` never depends on `install-hooks`: a hook that calls `make check` would re-run the very
#   install that refuses the hook file — the pre-push deadlock.
# - `check` = deps + lint-check + typecheck + merge-markers, the single gate CI and pre-push both run.
# - Check targets depend on `deps`: `make test` on a fresh clone must install what it needs, not fail.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

NODE := node
NPM := npm

# Toolchain for repo operations. Nothing here uses the system interpreter.
UV ?= uv
PYTHON_VERSION ?= 3.14
TOOLS_BIN ?= .tools/bin
TOOLS_VENV ?= .tools/venv
TOOLS_PYTHON := $(TOOLS_VENV)/bin/python

GREEN := \033[0;32m
NC := \033[0m

.PHONY: help install setup deps tools install-hooks lint lint-check typecheck \
        test coverage format merge-markers clean check

help:
	@printf "Available commands:\n"
	@printf "  ${GREEN}make install${NC}      One shot: deps, .env, hooks, tools — what a clone and CI run\\n"
	@printf "  ${GREEN}make setup${NC}        Dependencies and hooks\\n"
	@printf "  ${GREEN}make check${NC}        lint + typecheck + merge-markers — the gate CI and pre-push run\\n"
	@printf "  ${GREEN}make test${NC}         The gate, then the test suite\\n"
	@printf "  ${GREEN}make lint${NC}         Report lint findings\\n"
	@printf "  ${GREEN}make format${NC}       Rewrite formatting in place\\n"
	@printf "  ${GREEN}make coverage${NC}     Tests with a clover report in coverage/\\n"
	@printf "  ${GREEN}make clean${NC}        Provisioned state only, never user data\\n"

install: setup tools
	@printf "${GREEN}✓ Installed${NC}\n"

setup: deps install-hooks
	@[ -f .env ] || { [ -f .env.example ] && cp .env.example .env; } || true

deps:
	$(NPM) install

# Hooks must be installed, not merely declared: npm's `prepare` runs husky only when husky is a
# declared dependency, and a silent no-op leaves every push ungated.
install-hooks: deps
	@command -v npx >/dev/null 2>&1 || { echo "npx is missing"; exit 1; }
	@npx husky >/dev/null 2>&1 || true
	@git config core.hooksPath >/dev/null 2>&1 || {
		echo "husky did not set core.hooksPath — is husky in devDependencies?"; exit 1; }
	@printf "${GREEN}✓ Hooks installed at %s${NC}\n" "$$(git config core.hooksPath)"

tools:
	@command -v $(UV) >/dev/null 2>&1 || (mkdir -p $(TOOLS_BIN) && curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=$(TOOLS_BIN) sh)
	@test -x $(TOOLS_PYTHON) || ($(UV) venv --python $(PYTHON_VERSION) $(TOOLS_VENV))
	@$(UV) pip install --quiet --python $(TOOLS_PYTHON) pynacl

# A conflict marker that reached a commit is a merge stopped halfway: the file is wrong and nothing
# else reads it. The script ships in the scaffold's examples/tools/.
merge-markers: deps
	@tools/check-merge-markers.sh

# The exact gate a push must pass — run identically by CI and the pre-push hook. No test run: too
# slow for a hook, and CI's `make test` already includes these.
check: deps lint-check typecheck merge-markers

test: check
	$(NPM) run test

lint: deps lint-check

# Shared with the pre-commit hook — one lint scope for both.
lint-check: deps
	$(NPM) run lint:check

# No target here: ESLint 9 removed its extra formatters, so a GitHub-annotation
# formatter is a third-party dependency. CI runs lint-check, which still fails the build.

typecheck: deps
	$(NPM) run typecheck

coverage: deps
	$(NPM) run coverage

format: deps
	$(NPM) run format

clean:
	rm -rf node_modules coverage .vitest dist .tools
