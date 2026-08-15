# Makefile for <project> — single dev entry point (Rust)
#
# CHANGE: crate name, the toolchain channel (rust-toolchain.toml), the
# coverage threshold; add project-specific targets below `clean`.
#
# DO NOT CHANGE:
# - SHELL + .SHELLFLAGS (the shell pin): make's default /bin/sh is dash on
#   Debian/Ubuntu — including the CI runners — and dash has no `pipefail`.
#   Without the pin, a recipe with bash-isms passes on macOS and dies on CI
#   with "Illegal option -o pipefail" (houses 2026-08: #56/#57 CI failure).
# - `deps` never depends on `install-hooks`: a hook that calls `make check`
#   would re-copy/refuse the very hook file — the pre-push deadlock.
# - `check` = lint-check + typecheck, the single gate CI and pre-push both run.
# - `clean` never touches user data (only target/ + generated reports).
# - The lint gate is `clippy -D warnings`: with the exact toolchain pinned
#   in rust-toolchain.toml, the lint set is deterministic, so failing on any
#   warning is a stable gate — no baseline needed (the Python layer's
#   both-direction baseline exists for checkers whose diagnostics drift
#   across environments; a pinned toolchain does not).

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: help setup deps install-hooks check lint lint-check lint-github typecheck format test coverage dist clean

# CHANGE: tool paths. rustup reads rust-toolchain.toml automatically and
# installs the pinned toolchain + components on first cargo use.
CARGO := cargo
CLIPPY := $(CARGO) clippy --all-targets -- -D warnings
COV := cargo llvm-cov

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m

help:
	@echo "${GREEN}Rust repo — make targets${NC}"
	@echo "  setup          Install toolchain + hooks (idempotent)"
	@echo "  lint           cargo fmt --check + clippy -D warnings"
	@echo "  typecheck      cargo check --all-targets (the borrow-checker gate)"
	@echo "  test           Lint + typecheck + cargo test"
	@echo "  coverage       lcov report via cargo llvm-cov (CI gate)"
	@echo "  format         cargo fmt"
	@echo "  dist           cargo build --release (CI uploads the binary)"
	@echo "  clean          Remove target/ + generated reports"

setup: deps install-hooks

# What the CHECK targets actually need — no hook machinery. A check must
# never depend on install-hooks (see the deadlock note at the top).
deps:
	@rustc --version >/dev/null 2>&1 || { echo "${RED}rustup missing — install it (https://rustup.rs)${NC}"; exit 1; }
	@cargo llvm-cov --version >/dev/null 2>&1 || { echo "${YELLOW}cargo llvm-cov missing — run: cargo install cargo-llvm-cov${NC}"; }

install-hooks:
	@for hook in pre-commit pre-push; do \
		cp scripts/$$hook .git/hooks/$$hook; \
		chmod +x .git/hooks/$$hook; \
	done
	@echo "${GREEN}✓ Hooks installed (pre-commit: lint + gitleaks; pre-push: make check)${NC}"

# The exact gate a push must pass — run identically by CI and the pre-push
# hook (single source of truth; no test run — too slow for a hook, and CI's
# `make test` already includes these).
check: deps lint-check typecheck

test: deps lint-check typecheck
	$(CARGO) test

coverage: deps
	$(COV) --lcov --output-path lcov.info
	@echo "${GREEN}✓ lcov.info written — CI gate: fail below floor, track the goal${NC}"

lint: deps lint-check

lint-check: deps  # Shared with the pre-commit hook — single source of truth for the lint scope
	$(CARGO) fmt -- --check
	$(CLIPPY)

lint-github: deps   # CI only: clippy's JSON messages -> PR annotations
	$(CARGO) fmt -- --check
	$(CLIPPY) --message-format json

# The type gate: rustc's borrow checker is deterministic for a pinned
# toolchain, so this needs no baseline lock (see the header note).
typecheck: deps
	$(CARGO) check --all-targets

format: setup
	$(CARGO) fmt

dist: deps
	$(CARGO) build --release

clean:
	$(CARGO) clean
	rm -rf lcov.info coverage/
