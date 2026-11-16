# Scaffold checklist

Run this before reporting a scaffold done, against the actual repo rather than
from memory. General applies to every repo; take exactly one language section.

### General (every repo)
- [ ] Makefile with `help setup lint test coverage format clean` (+ `run`/`stop` for services, `dist` for artifacts); `.PHONY` on all targets
- [ ] Makefile pins the recipe shell (`SHELL := /bin/bash` + `.SHELLFLAGS := -eu -o pipefail -c`) — recipes can't diverge between macOS and CI
- [ ] `make test` depends on `make lint`; CI runs only make targets
- [ ] Runtime pinned: CI (`setup-*` action) and local dev (`.python-version`/`.nvmrc`) use the SAME version
- [ ] Type checker configured (strict where possible) and gated inside `make test` on the error count
- [ ] The baseline is locked in both directions: a new error AND a stale entry fail
- [ ] Exception: a pinned, deterministic toolchain needs no baseline (Rust under `rust-toolchain.toml`)
- [ ] `make setup` idempotent — installs toolchain if missing, syncs deps
- [ ] `make clean` removes exactly `.venv`/`node_modules`, `htmlcov/`, `.coverage`, `coverage.xml`, caches — never user data
- [ ] CI workflow: checkout@v4, `permissions: contents: read`, concurrency group with `cancel-in-progress: true`, steps = `make setup` → `make lint` → `make test`
- [ ] Coverage emitted as XML for CI (`coverage.xml` / `coverage/clover.xml`); CI fails below floor (~80%), posts PR comment, tracks 90%. For an EXISTING codebase, set the floor below the measured number first (e.g. 65 floor / 80 goal at 71% measured) and raise it as coverage lands — a hard 80 gate on day one is a broken CI
- [ ] `.gitignore` covers env, venv/node_modules, IDE, caches, agent state, logs, recreatable data
- [ ] `.env.example` committed, all vars documented, values blank; `.env` gitignored; `make setup` ensures `.env` exists (copy from example); run targets load via `--env-file` (real env wins), lint/test never touch it
- [ ] `.editorconfig` (utf-8, lf, final newline) and `.gitattributes` (`* text=auto eol=lf`)
- [ ] README.md: purpose, Quick Start via make, usage, docs table
- [ ] AGENTS.md: quick start, make-target testing rule, decision tree to `docs/`, git + secrets rules — **bootloader not OS: only 100%-relevant content, and every doc reachable from it**
- [ ] `docs/` standards copied from omp-config in full — coding-standards.md, testing-standards.md, ux-standards.md (from omp-config's `standards/`), writing-documentation.md, documentation-structure.md (from omp-config's `docs/`)
- [ ] Required doc set present (per docs/documentation-structure.md): `docs/PRD.md` (or `docs/PRD/`) with JTBD + personas + cost/longevity/backups/monitoring/auth/scale/hosting constraints; `docs/TECHSPEC.md` (or `docs/TECHSPEC/`) with tech choices, spikes, requirement-referencing decisions, architecture mermaid diagram; `docs/PLAN.md` (or `docs/PLAN/`) with the software's phase inputs/outputs, operations, quality gates and no later-phase dependencies; every doc discoverable from AGENTS.md
- [ ] Repo self-checks: a docs-links test (every relative markdown link resolves — houses' `test_docs_links.py` is the pattern), the merge-marker check (`tools/check-merge-markers.sh`, wired into `check`), and an architecture-layer test (current layers, archunitpython, patterns per `skill://archunitpython-glob-rules` — never the vacuous `./`-glob form)
- [ ] PR review wired: `.pr_agent.toml` + pr-agent workflow with standards docs **and PRD/TECHSPEC/PLAN/ux-standards** in `repo_context_files`; the `pr-agent-config` branch created holding the `.pr_agent.toml`; `<PROJECT>_API_KEY` secret (Cloudflare AI Gateway token) set BEFORE the first PR
- [ ] review workflow placeholders substituted (`{ACCOUNT_ID}/{GATEWAY}`, the secret name) and `push_trigger_ignore_bot_commits = false` in the config branch
- [ ] First PR proves the review: a "## PR Reviewer Guide" comment posted and the check passed (the check only catches a missing review AFTER a run — an empty/red run on the first PR means the config/key is wrong; see the failure modes above)
- [ ] dependabot configured per the 'Dependency updates are automated, with a human boundary' rule in standards/coding-standards.md — grouping and auto-merge as in the examples
- [ ] Branch workflow: never commit to main, PRs required, protected main
- [ ] auto-merge armed by workflow on open and on review; gate = one approval + all checks + all conversations resolved
- [ ] `allow_auto_merge` and `delete_branch_on_merge` set; protection has `required_conversation_resolution`
- [ ] private + free plan: protection and auto-merge are unavailable — public repo, or the convention-only gate recorded
- [ ] Git hooks run the fast checks — lint, typecheck, secrets scan (gitleaks) — installed by `make setup`; never the full test suite
- [ ] End-to-end green: `make setup && make lint && make test` locally and CI green on push
- [ ] Repo created via `gh repo create --source --push --private`; branch protection applied after first CI run (PR + status check required)

### Python
- [ ] uv + `.python-version` = current stable at scaffold time (via `uv python list`, subject to dep support); ruff `target-version` matches
- [ ] pyproject.toml: ruff `select E,F,I,UP,B,SIM,N`, `line-length 120`, double quotes, no ignore list
- [ ] pytest with `testpaths = ["tests"]`; dev deps in `[dependency-groups] dev` (PEP 735) incl. archunitpython
- [ ] Semantic types wired: pint for quantities, a Money type for currency (the generic rules are in the global standard; the library choices are here)
- [ ] `docs/coding-standards.md` carries the "Python conventions" section (materialized from this skill's language layer — the bot reads only `repo_context_files`)
- pytest is the runner; unittest only for eval harnesses needing module-level discovery (documented deviation, not default)
- Type checker (pyrefly recommended, or basedpyright/mypy) configured and gated inside `make test`
- The baseline lock runs both directions via `scripts/pyrefly-lock.py`: new errors AND stale entries fail. Pyrefly's own baseline is one-way and misses stale entries
- `make check` = lint + typecheck — the single gate CI and the pre-push hook both run (same command, no drift); check targets depend on `deps`, never `install-hooks`
- Flat `<pkg>/` layout with `packages.find` include
- [ ] Raw git hooks: `scripts/pre-commit` (lint via `make lint-check` + gitleaks) and `scripts/pre-push` (the full `make check` gate), installed by `make install-hooks` (via `make setup`); gitleaks is a one-time install (`go install github.com/gitleaks/gitleaks/v8@latest` or brew)

### JS/TS
- [ ] npm scripts mirror make targets: dev/build/preview/test/coverage/lint/format
- [ ] vitest + istanbul, reporters text+clover → `coverage/clover.xml`
- [ ] ESLint flat config with prettier last (or oxlint `typeAware`); prettier defaults
- [ ] `strict: true` TS; type-check gate inside `build`
- [ ] `docs/coding-standards.md` carries the "JS/TS conventions" section (materialized from this skill's language layer — the bot reads only `repo_context_files`)
- [ ] Node pinned in CI (setup-node, 22.x) and locally (`.nvmrc` same version)
- [ ] husky pre-commit: lint + typecheck + gitleaks

### Rust
- [ ] `rust-toolchain.toml` pins the exact stable channel at scaffold time; CI (`dtolnay/rust-toolchain@stable` — installs rustup; the file's channel is honored in-dir) and local rustup use the same file — components `clippy`, `rustfmt`, `llvm-tools`
- [ ] `cargo fmt --check` + `cargo clippy --all-targets -- -D warnings` inside `make lint`; rustfmt `max_width = 120` matching `.editorconfig` (one formatter per artifact — generated code excluded, not re-formatted)
- [ ] Type gate = `cargo check --all-targets` inside `make test` (the borrow checker is the type checker; deterministic under the toolchain pin — no baseline needed, stated in the Makefile)
- [ ] `cargo test` runner; coverage via `cargo llvm-cov --cobertura` → `cobertura.xml` for the CI gate (fail below floor, track goal)
- [ ] `target/` and `cobertura.xml` gitignored (Rust build + coverage artifacts — `cargo build` writes `target/`, `make coverage` writes cobertura.xml; the general `.gitignore` set §4 covers the Python/JS artifacts)
- [ ] CI workflow is the Rust variant: `dtolnay/rust-toolchain@stable` + `taiki-e/install-action` (cargo-llvm-cov), steps exactly make targets, `make lint-github` (clippy -D warnings — human-readable output feeds GitHub's built-in matcher for inline annotations)
- [ ] Raw hooks: pre-commit (make lint-check + gitleaks) + pre-push (make check), watch scope `*.rs Cargo.toml Cargo.lock rust-toolchain.toml rustfmt.toml`
- [ ] `#[allow(...)]` carries a reason comment (no blanket `#![allow]`); newtypes over primitives (units in the type name, Money never bare float)
- [ ] Repo self-checks: std-only `#[test]`s for docs links and for architecture layers (forbidden `use` paths — exact paths, never the vacuous glob form), and the merge-marker check (`tools/check-merge-markers.sh`, wired into `check`)
- [ ] Cargo.lock committed (reproducible builds); fast-moving crates pinned with a comment why
- [ ] `docs/coding-standards.md` carries the "Rust conventions" section (materialized from the language layer — the bot reads only `repo_context_files`)

### Non-code
- [ ] Docker services: layered compose files, per-service Dockerfile, shared env_file
- [ ] Other languages: Makefile carries the real build dependency graph; `install` to `~/.local` where applicable
