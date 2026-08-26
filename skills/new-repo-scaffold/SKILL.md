---
name: new-repo-scaffold
description: |
  Scaffold a new project repository ("shell repo") using the house best
  practices observed across books_to_anki, chat-workflow, energy_envelope,
  houses, side-by-side, kilocode: Makefile as the single dev entry point,
  CI that delegates to make, gated code coverage, docs standards triplet,
  git hygiene. Splits general (language-agnostic) practices from
  language-specific toolchain layers (Python, JS/TS, Rust, other).
---

# New Repo Scaffold

Use when asked to start a new project repository ("shell repo", "scaffold a repo", "set up a new project"). Deliver a working skeleton — build, lint, test, coverage, CI, docs, git hygiene — never an empty `git init`.

Practices below were distilled from the repos under `~/Documents/code` (surveyed 2026-08): books_to_anki, chat-workflow, energy_envelope, houses (Python); side-by-side, houses/frontend, kilocode (TS/JS); cv (LaTeX); spark-local-env (docker-compose).

## Two layers

1. **General layer** — applies to every new repo regardless of language. Non-negotiable.
2. **Language layer** — toolchain specifics per stack (Python: uv/ruff/pytest; JS/TS: npm/vitest/eslint; Rust: cargo/clippy/rustfmt), in `skill://scaffold-language-layers`.

Scaffold in this order: Makefile → CI → coverage → git hygiene → entry docs → repo creation + branch protection. Finish with the checklist.

## General layer

### 1. Makefile is the single dev entry point

Every dev action goes through `make`; CI runs make targets, never raw tool commands. energy_envelope states the contract explicitly: "CI runs exactly: `make setup && make lint && make test`".

**Template: `skill://scaffold-language-layers/examples/<stack>/Makefile`** — copy it into the new repo, then edit the `CHANGE` points (package name, versions, project targets). Each example file carries a `CHANGE` / `DO NOT CHANGE` comment header — the comments say *what* and *why*; the invariants below say *when* it's OK to deviate. The stack-specific examples (Makefile, pyproject, typechecker config, hooks) live in the language layer's `examples/<stack>/` dir; the general examples (dotfiles, CI, AGENTS.md, review bot) live in `examples/` here. A repo takes the general dir + exactly one stack dir.

Targets (template `help` lists them; meaning fixed by the standard):
- `setup` idempotent toolchain+deps+hooks · `lint` static checks · `test` suite gated by lint · `coverage` XML for CI · `format` auto-fix · `clean` removes only `.venv`/`node_modules`, `htmlcov/`, `.coverage`, `coverage.xml`, `__pycache__`, `*.pyc` — never user data · `run`/`stop` dev servers (service repos) · `dist` build artifacts (CI uploads).

Deviating from the template is allowed only where the rules say so:
- **Never change the shell pin** (`SHELL := /bin/bash` + `.SHELLFLAGS := -eu -o pipefail -c`) — make's default `/bin/sh` is dash on Debian/Ubuntu and the CI runners; dash has no `pipefail`, so a bash-ism recipe passes on macOS and dies in CI with "Illegal option -o pipefail" (houses 2026-08: PRs #56/#57 CI failures). Pin the shell once; never add `set -o pipefail` inside individual recipes.
- **`deps` never depends on `install-hooks`** — a hook that calls `make check` would re-copy/refuse the very hook file (the pre-push deadlock). Check targets depend on `deps` (uv sync), and `install-hooks` depends on nothing check-related.
- **`check` = `lint-check typecheck`** — the single gate CI and the pre-push hook both run; same command, no drift. No test run in the hook (too slow; CI's `make test` includes the checks).
- **Tool paths as variables** at top (`PYTHON := .venv/bin/python`, `RUFF := .venv/bin/ruff`).
- **Pin the language runtime.** CI (`setup-node`/`setup-python` action) and local dev (`.nvmrc`, `.python-version`) use the **same** version; local dev must match CI — pinning CI only is the smell (side-by-side/houses pin CI only, kilocode pins bun via `packageManager`).
- **Type checking is a first-class gate.** The language's type checker is configured (strict where the toolchain allows), gated inside `make test` on the **error count** (never the bare exit code — a checker that exits nonzero on warnings fails every environment differently), and included in the fast commit checks where the toolchain permits. Rust: the gates are `cargo check --all-targets` (type) + `clippy -D warnings` (lint) — deterministic under the `rust-toolchain.toml` pin, so no baseline (see `skill://scaffold-language-layers`). Errors gate the commit; they are fixed, never suppressed (anti-fragile: a `# type: ignore` needs a comment). **Baseline-locked repos (recommended):** the checker runs against a committed baseline and fails on drift in BOTH directions — a NEW error AND a stale baseline entry (an error the code no longer produces). The stale direction is the one that bites: a fix that removes a diagnostic without refreshing the baseline s…

Hooks (`skill://scaffold-language-layers/examples/python/scripts/pre-commit`, `.../pre-push`, installed by `make install-hooks`):
- pre-commit delegates to `make lint-check` (plus a gitleaks secrets scan); pre-push delegates to `make check` — never duplicate the tool invocations.
- pre-push skip logic scopes to the pushed commits, watching `*.py '*.ts' '*.vue' '*.js' pyrefly.toml` (a config change can alter the diagnostic set) — never the working tree: at push time the worktree is clean, and a worktree-based skip would let the gate silently never run.

Non-Python: same targets, different toolchain lines (see language layers).

### 1b. One formatter per artifact, decided at scaffold time

The scaffold decides each artifact's one formatter, and the decision is
recorded (in the scaffolded Makefile/ignore files and this skill's language
layers). Machine-generated files (a derived projection, a regenerated index,
build output) are formatted **by their generator** — a second formatter run
over generated output churns the diff on every regeneration. Two formatters
fighting over the same file is the failure mode: prettier reformatting JSON
that a Python writer emits with a different indent, so every publish rewrites
the file. Formatters for hand-written code are excluded from generated
directories at scaffold time — ignore files (`.prettierignore`, `exclude`),
not discipline. A "nicer" formatter for generated files is a standards
change, never a local revert.

### 2. CI delegates to make

One workflow per project; subprojects get path-filtered jobs (energy_envelope splits `android/**` from the Python root via `paths: ['!android/**']`).

**Working file: `examples/.github/workflows/ci.yml`** (Python; the Rust variant: `skill://scaffold-language-layers/examples/rust/.github/workflows/ci.yml`) — copy it into the new repo.

Rules:
- `permissions: contents: read` + `pull-requests: write` — the coverage comment step in the template needs the latter; drop both together if you drop the step.
- `concurrency` group per ref with `cancel-in-progress: true` — every active repo does this.
- CI steps are exactly the make targets; never inline `pip install`/`npm test` logic into the workflow. The boundary is pipeline-vs-plumbing, not shell-vs-no-shell: anything that decides what ships or what the run concludes (build, test, lint, the coverage gate, generation) is make-only; tool bootstrap (`actions/checkout`, `setup-*`, rust-toolchain) and result plumbing (`upload-artifact`, the coverage-summary/comment actions) may be workflow steps. Third-party actions pin to a commit SHA, never the mutable tag (the template shows both).
- **System binaries come from a make target, never the environment.** A tool that needs a system binary (tesseract, ImageMagick, …) gets it installed by a make target into the project's gitignored `.tools/` (via a single no-`sudo` package manager chosen once by the scaffold) — never assumed preinstalled on the runner or a dev machine, and never an ad-hoc `ci.yml` step (per the make/CI rule above); a machine that cannot install them fails loudly at that step, not mid-suite.
- Lint in CI via `make lint-github` (`ruff check --output-format=github`) so findings surface as PR annotations; plain `make lint` stays for local use. The template reflects this.
- API-key-dependent suites: pass `${{ secrets.* }}` as env, run under a timeout wrapper, upload outputs with `if: always()` so failures are diagnosable (chat-workflow evals).

### 3. Code coverage is gated, not decorative

- `make coverage` emits an XML report for CI (`coverage.xml` Python, `coverage/clover.xml` JS) plus a human report.
- CI fails below a hard floor and tracks a higher goal: books_to_anki uses `irongut/CodeCoverageSummary` with `thresholds: '80 90'`, `fail_below_min: true`, posting a sticky PR comment via `marocchino/sticky-pull-request-comment`; side-by-side uses `slavcodev/coverage-monitor-action` on clover.xml.
- `htmlcov/`, `.coverage`, `coverage.xml` are gitignored; reports are generated on demand.

### 3b. The repo tests itself: docs links + architecture layers

Every repo carries tests that guard the repo's own invariants — the docs
stay coherent and the architecture layers (as currently imagined) don't
erode. The docs-links pattern ships in houses (`tests/unit/test_docs_links.py`);
the architecture-layer test uses archunitpython — pattern semantics are
`skill://archunitpython-glob-rules` (the vacuous-pass trap made the ./-style
layer test worthless, so follow the skill, not any repo's existing test):

- **Broken doc links are a test failure.** A small runner scans `AGENTS.md`
  + `docs/**/*.md` for markdown links, resolves the relative ones, and fails
  on a target that doesn't exist (or escapes the repo). Skip external URLs,
  anchors (`#…`), and template variables; strip `#fragment` before
  resolving. One regex, one test, no deps — a doc renamed without its links
  updated fails CI instead of 404ing for a reader.
- **Architecture layers are enforced, not hoped.** Define the current
  layering (e.g. `dag/` may only depend on itself; the HTTP layer may not
  import the sheets module directly) and assert it in a test: Python repos
  use **archunitpython** (`project_layers().layer(...).defined_by(...)` +
  `may_only_depend_on_layers()` / `may_not_depend_on_layers()`). Layer
  pattern semantics — including the vacuous-pass trap — are
  `skill://archunitpython-glob-rules`; reference it, never copy it.
  Encode the layers *as they are designed now*; when a deliberate layering
  change lands, the test changes with it (git log records the old rule).

### 4. Git hygiene

- Never commit to main; branch off main, PR required, protected origin/main (rule://session-start; chat-workflow/houses AGENTS.md).
- Atomic commits; reference issues with `Fixes #N`.
- **Working files: `examples/.gitignore`, `examples/.editorconfig`, `examples/.gitattributes`, `examples/.env.example`** — copy them; the rules below say what each guards and when deviation is OK.
- `.gitignore` must cover (each pattern observed in 3+ repos): env/secrets (`.env`, `.env.local`, `*.keystore`); envs/deps (`.venv/`, `venv/`, `node_modules/`, `dist/`); caches (`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.coverage`, `htmlcov/`, `coverage.xml`); build artifacts (`dist/`, `*.egg-info/` — `uv sync` generates `<pkg>.egg-info/`; omit it and verification step 4 fails; `target/` and `cobertura.xml` in a Rust repo — `make coverage` writes cobertura.xml and `cargo build` writes `target/`); agent/tool state (`.sisyphus/`, `.opencode/`, `.code-review-graph/`, `.logs/`); IDE/OS (`.vscode/`, `.idea/`, `.DS_Store`, `*.log` — with a `!.vscode/extensions.json` negation when committing one); recreatable data caches only (houses: `data/api_cache/`) — test fixtures are committed under `tests/fixtures/`
- Lockfiles (`uv.lock`, `package-lock.json`) are committed, never ignored. books_to_anki ignores `uv.lock` — that kills reproducibility; don't copy it. Keep the list curated: books_to_anki ships the kitchen-sink GitHub template (Django/Flask/PyInstaller/poetry sections it doesn't need); the newer repos use a short alphabetized list.
- `.gitattributes`: `* text=auto eol=lf`; mark generated files `linguist-generated` (kilocode).
- `.editorconfig`: `root = true`, `utf-8`, `insert_final_newline = true`, `eol = lf`, 2-space indent default, per-language overrides (kilocode). `max_line_length` must match the formatter (120 for ruff/prettier) — kilocode's editorconfig 80-vs-prettier-120 mismatch is a smell to avoid.
- `.env.example` committed with every env var documented (values blank); `.env` itself is gitignored. `make setup` guarantees `.env` exists (`[ -f .env ] || cp .env.example .env`); run targets load via `--env-file .env` (real env wins), lint/test never touch it. Real secrets live in the shell environment only — never in code, docs, logs, or the example file. No env vars at all? Ship a comment-only `.env.example` — the setup copy line stays harmless.
- `.vscode/extensions.json` with recommended extensions — only if you want editor parity; it requires the `!.vscode/extensions.json` negation above (side-by-side ships one with `Vue.volar`; kilocode ships eslint/esbuild/direnv). Otherwise `.vscode/` is fully ignored.
- Git hooks (stack-appropriate mechanism, see language layers; **working files: `skill://scaffold-language-layers/examples/python/scripts/pre-commit`, `.../pre-push`**) run **lint, type checking, and a secrets scan** — the fast checks — never the full test suite; tests stay gated in `make test` + CI. The hook's contents are an instruction, not a ceiling: lint + typecheck + a leak detector (gitleaks across stacks) are the house hook, wired in at scaffold time. Hooks must finish in seconds or they get bypassed, and they're bypassable with `--no-verify` anyway — so anything critical must ALSO be enforced in make/CI. Python: raw git hooks (`scripts/pre-commit` + `scripts/pre-push`) installed by `make install-hooks` — they delegate to make targets so hook and CI can't drift. JS/TS: husky. **The pre-push hook delegates to `make check`** (like pre-commit → `make lint-check`) so hook and CI can't drift — but check targets depend on `deps`, NEVER `install-hooks` (a hook calling `make check` would re-copy/refuse the very hook file — the pre-push deadlock). A hook running the tools directly instead of make is a smell — fix the make dependency, don't duplicate.

### 5. Entry docs: README for humans, AGENTS.md for agents

- `README.md` (humans): one-line purpose, Quick Start via `make`, usage examples, docs table.
- `AGENTS.md` (agents): **template: `examples/AGENTS.md`** — copy it; it's the bootloader (quick start, decision tree to `docs/`, tool table, testing/secrets/git rules). The bootloader principle and discoverability rule are in the documentation standard — apply them, don't restate them.
- `docs/` standards triplet, checked by PR-Agent:
  - `docs/coding-standards.md` — copy the **canonical global standard** (`standards/coding-standards.md` in the omp-config repo) **in full**, then append the **language layer's conventions** (per `skill://scaffold-language-layers`), then project rules. The reviewer reads only `repo_context_files` — a rule that lives only in this skill is **invisible to review**: language-specific standards must be materialized into the repo copy. The copy must carry the full set: the design principles (separation of concerns, types over primitives, quantities carry units, Money not float, no over-abstraction, anti-fragile, fail fast with user-visible errors, no shims, one-way invariants, UTC datetimes, cache hygiene, batch APIs, real content never in code, derived data regenerated, argv forwarding, AI output as proposed), DI, testing, documentation, language conventions.
  - `docs/testing-standards.md` — tests mirror module paths, deterministic (no wall-clock, network, or order dependence; seeded randoms), assert behavior not implementation, DI fakes over `unittest.mock.patch`.
  - `docs/writing-documentation.md` — copy the **canonical documentation standard** (`docs/writing-documentation.md` in the omp-config repo) **in full** — what good documentation is: context efficiency, density, no-duplication, one topic per file, the quality checklist, AGENTS.md as bootloader — and skills are documentation, subject to it like any doc. The process skill (`skill://write-documentation`) references it.
  - `docs/documentation-structure.md` — copy the **canonical folder-structure standard** (`docs/documentation-structure.md` in the omp-config repo) **in full** — the required doc set: `docs/PRD.md` (or `docs/PRD/` when big — JTBD first, user requirements, personas, cost/longevity/backups/monitoring/auth/scale/hosting constraints), `docs/TECHSPEC.md` (or `docs/TECHSPEC/` — technology choices, spikes, requirement-referencing decisions, architecture-layers mermaid, layer boundaries enforced by the architecture test), `docs/PLAN.md` (or `docs/PLAN/` — phases with the **software's** inputs/outputs, operations, quality gates; no later-phase dependencies; earliest user value), `docs/UX.md` (the UX spec — see documentation-structure.md), plus discoverability (every doc reachable from AGENTS.md).
  - `docs/ux-standards.md` — copy the **canonical UX standard** (`standards/ux-standards.md`) **in full**, then add repo-specific UX baselines alongside it — `docs/UX.md` (the UX spec — see documentation-structure.md) and a UX decisions doc, per skill://ux-process.
- Wire the standards into review: `.pr_agent.toml` `repo_context_files` lists them; `extra_instructions` demands a per-doc Compliance section in every review (houses, books_to_anki).

### 6. PR review, dependency automation & LLM provider config

**Working files: `examples/.pr_agent.toml` + `examples/.github/workflows/pr-agent.yml` + `examples/tools/check_review_posted.py`** — copy them into the new repo, create the `pr-agent-config` branch holding the `.pr_agent.toml`, and set the `<PROJECT>_API_KEY` secret (the Cloudflare AI Gateway token) BEFORE the first PR. The example file comments explain the security invariants and failure modes — read them.

### 6b. LLM provider convention

All code reads LLM provider config from `OPENAI_BASE_URL` + `OPENAI_API_KEY`. See `skill://cloudflare-ai-gateway` for the gateway URL, model names, and configuration. Forkers change these two env vars and model names.

- `.github/dependabot.yml` — **working file: `examples/.github/dependabot.yml`**. For uv projects the package ecosystem is dependabot's `pip` ecosystem (it reads `uv.lock`); weekly is the house cadence.

### 7. Repo creation & branch protection

None of the surveyed repos have protection enforceable from the tree — it's a GitHub setting. The scaffold must create the repo and apply it:

```bash
# git init first: make setup runs `install-hooks`, which needs a repo
git init -b main
make setup                       # generates uv.lock, installs hooks; .venv + *.egg-info are gitignored
# commit AFTER setup so uv.lock lands in the initial commit
git add -A && git commit -m "Initial scaffold"
# private by default; --source pushes the local tree and enables CI on first push
gh repo create <name> --source . --push --private

# Branch protection goes AFTER the first CI run: GitHub refuses to require a
# status check that has never run. The check name must match the CI job name
# ("build-and-test" in the template above).
gh api repos/<owner>/<name>/branches/main/protection -X PUT \
  -H "Accept: application/vnd.github+json" \
  -F required_status_checks='{"strict":true,"contexts":["build-and-test"]}' \
  -F required_pull_request_reviews='{"required_approving_review_count":1}' \
  -F enforce_admins=false
```

Rules:
- Never push to main; the first commit is `main`, everything after is branches + PRs (rule://session-start).
- `--private` is the default for personal repos; go public only deliberately.
- **Set `<PROJECT>_API_KEY` as a repo secret BEFORE the first PR** — the review job fails fast without it (observed: secret created after the PR-open event, run dead in 6s). The secret value is the Cloudflare AI Gateway token (`CLOUDFLARE_AIGATEWAY_TOKEN` in the shell environment).

## Language layers — see `skill://scaffold-language-layers`

Toolchain details per stack materialize into the repo's `docs/coding-standards.md` copy.

## Verification (prove the scaffold works)

Run in order; the checklist below is the final gate, not documentation.

1. **Fresh-clone smoke test** — the single most valuable check. Clone the new repo into a temp dir and run `make setup && make lint && make test` there. This simulates exactly what every future clone and CI run experiences; it fails if anything depends on scaffold-session state (venv, cwd, env, uncommitted files).
2. **Coverage and clean loop** — `make coverage` (emits `coverage.xml` for the CI gate), then `make clean`, then re-run `make test` — proves the clean target doesn't break the loop.
3. **Hooks actually fire** — `make install-hooks` copies the raw hooks; stage a lint-breaking change and confirm the pre-commit hook blocks the commit (or run `.git/hooks/pre-commit` directly on the staged changes). Then prove gitleaks with a REALISTIC key: plain `sk-` + 24 chars matches no default rule (empirically passes); use the OpenAI format `sk-` + 20 alnum + `T3BlbkFJ` + 20 alnum (RuleID `openai-api-key`). Confirm the commit is blocked, revert, confirm it passes. Confirm pre-push fires on the pushed range: a push that touches only docs skips; a push touching `.py` runs `make check`.
4. **Gitignore honesty** — after setup, `git status --porcelain` is empty: `.venv/`, `.env`, caches, and agent state never appear.
5. **CI, for real** — push a feature branch, open a PR, `gh pr checks --watch` until green; only then merge. (Branch protection cannot be applied until the check has run once.) No remote yet? Run `actionlint` over the workflow files as the static substitute. Local fresh-clone smoke ≠ CI: the same make recipe passed locally (and in a local clone) but failed on the GitHub runner — budget one CI debug iteration (print `--version`, `--help`, raw exit codes) when standing up a new repo.
6. **Walk the checklist** — every box checked against the actual repo, not from memory.

## Checklist

### General (every repo)
- [ ] Makefile with `help setup lint test coverage format clean` (+ `run`/`stop` for services, `dist` for artifacts); `.PHONY` on all targets
- [ ] Makefile pins the recipe shell (`SHELL := /bin/bash` + `.SHELLFLAGS := -eu -o pipefail -c`) — recipes can't diverge between macOS and CI
- [ ] `make test` depends on `make lint`; CI runs only make targets
- [ ] Runtime pinned: CI (`setup-*` action) and local dev (`.python-version`/`.nvmrc`) use the SAME version
- [ ] Type checker configured (strict where possible) and gated inside `make test` on the error count; baseline-locked in both directions (new errors AND stale baseline entries fail) — EXCEPT where the toolchain is pinned and deterministic (Rust under `rust-toolchain.toml`: clippy/rustc need no baseline, per the language layer)
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
- [ ] Repo self-checks: a docs-links test (every relative markdown link resolves — houses' `test_docs_links.py` is the pattern) and an architecture-layer test (current layers, archunitpython, patterns per `skill://archunitpython-glob-rules` — never the vacuous `./`-glob form)
- [ ] PR review wired: `.pr_agent.toml` + pr-agent workflow with standards docs **and PRD/TECHSPEC/PLAN/ux-standards** in `repo_context_files`; the `pr-agent-config` branch created holding the `.pr_agent.toml`; `<PROJECT>_API_KEY` secret (Cloudflare AI Gateway token) set BEFORE the first PR
- [ ] First PR proves the review: a "## PR Reviewer Guide" comment posted and the check passed (the check only catches a missing review AFTER a run — an empty/red run on the first PR means the config/key is wrong; see the failure modes above)
- [ ] dependabot: weekly for package ecosystem + `github-actions`
- [ ] Branch workflow: never commit to main, PRs required, protected main
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
- Type checker (pyrefly recommended, or basedpyright/mypy) configured and gated inside `make test`; pyrefly uses the both-direction baseline lock (`scripts/pyrefly-lock.py` — new errors AND stale baseline entries fail; pyrefly's own baseline is one-way and misses stale entries)
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
- [ ] Repo self-checks: std-only `#[test]`s for docs links and for architecture layers (forbidden `use` paths — exact paths, never the vacuous glob form)
- [ ] Cargo.lock committed (reproducible builds); fast-moving crates pinned with a comment why
- [ ] `docs/coding-standards.md` carries the "Rust conventions" section (materialized from the language layer — the bot reads only `repo_context_files`)

### Non-code
- [ ] Docker services: layered compose files, per-service Dockerfile, shared env_file
- [ ] Other languages: Makefile carries the real build dependency graph; `install` to `~/.local` where applicable
