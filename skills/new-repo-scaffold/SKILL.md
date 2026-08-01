---
name: new-repo-scaffold
description: |
  Scaffold a new project repository ("shell repo") using the house best
  practices observed across books_to_anki, chat-workflow, energy_envelope,
  houses, side-by-side, kilocode: Makefile as the single dev entry point,
  CI that delegates to make, gated code coverage, docs standards triplet,
  git hygiene. Splits general (language-agnostic) practices from
  language-specific toolchain layers (Python, JS/TS, other).
---

# New Repo Scaffold

Use when asked to start a new project repository ("shell repo", "scaffold a repo", "set up a new project"). Deliver a working skeleton — build, lint, test, coverage, CI, docs, git hygiene — never an empty `git init`.

Practices below were distilled from the repos under `~/Documents/code` (surveyed 2026-08): books_to_anki, chat-workflow, energy_envelope, houses (Python); side-by-side, houses/frontend, kilocode (TS/JS); cv (LaTeX); spark-local-env (docker-compose).

## Two layers

1. **General layer** — applies to every new repo regardless of language. Non-negotiable.
2. **Language layer** — toolchain specifics (Python: uv/ruff/pytest; JS/TS: npm/vitest/eslint).

Scaffold in this order: Makefile → CI → coverage → git hygiene → entry docs → repo creation + branch protection. Finish with the checklist.

## General layer

### 1. Makefile is the single dev entry point

Every dev action goes through `make`; CI runs make targets, never raw tool commands. energy_envelope states the contract explicitly: "CI runs exactly: `make setup && make lint && make test`".

| Target | Meaning | Notes |
|---|---|---|
| `help` | List targets with one-line descriptions | Colored output; default target |
| `setup` | Install toolchain if missing, sync deps | Idempotent |
| `lint` | Static checks | Depends on `setup` |
| `test` | Test suite | Depends on `setup lint` — lint gates test |
| `coverage` | Tests + coverage report | term-missing / html / xml |
| `format` | Auto-fix lint + formatting | Depends on `setup` |
| `clean` | Remove `.venv`, caches, coverage artifacts | Must never delete user data |
| `run` / `stop` | Dev servers (service repos) | PID files under `.logs/`, port checks |
| `dist` | Build distributable artifacts | CI uploads these |

Rules:
- `.PHONY` every target.
- Tool paths as variables at top: `PYTHON := .venv/bin/python`, `RUFF := .venv/bin/ruff`.
- Colored output via `GREEN/YELLOW/RED/NC` ANSI variables and `@echo`.
- `clean` removes exactly: `.venv`, `htmlcov/`, `.coverage`, `coverage.xml`, `__pycache__`, `*.pyc`.

Python flavor (adapt `<pkg>` and `tests/` per project):

```makefile
# Makefile for <project>
.PHONY: help setup run lint lint-github typecheck test format coverage clean

PYTHON := .venv/bin/python
RUFF := .venv/bin/ruff
BASEDPYRIGHT := .venv/bin/basedpyright

GREEN := \033[0;32m
NC := \033[0m

help:
	@echo "Available commands:"
	@echo "  ${GREEN}make setup${NC}        Create venv, install deps + pre-commit hooks, ensure .env exists"
	@echo "  ${GREEN}make run${NC}          Run the app (loads .env; real env wins)"
	@echo "  ${GREEN}make lint${NC}         Check code quality"
	@echo "  ${GREEN}make typecheck${NC}    Static type check (basedpyright)"
	@echo "  ${GREEN}make test${NC}         Run tests (lint + typecheck gate)"
	@echo "  ${GREEN}make format${NC}       Auto-fix formatting issues"
	@echo "  ${GREEN}make coverage${NC}     Run tests with coverage report"
	@echo "  ${GREEN}make clean${NC}        Remove .venv and generated files"

setup:
	@uv --version >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
	@uv sync
	@uv run pre-commit install
	@[ -f .env ] || cp .env.example .env

run: setup
	@uv run --env-file .env python -m <pkg>

lint: setup
	@$(RUFF) check <pkg>/ tests/

lint-github: setup   # CI only: findings surface as PR annotations
	@$(RUFF) check <pkg>/ tests/ --output-format=github

typecheck: setup     # gate on errorCount from --outputjson: basedpyright's --level is honored
	@$(BASEDPYRIGHT) --outputjson | $(PYTHON) -c "import json,sys; d=json.load(sys.stdin); sys.exit(1 if d['summary']['errorCount'] else 0)"

test: setup lint typecheck
	@$(PYTHON) -m pytest

coverage: setup
	@$(PYTHON) -m pytest --cov=<pkg> --cov-report=term-missing --cov-report=xml

format: setup
	@$(RUFF) check --fix <pkg>/ tests/
	@$(RUFF) format <pkg>/ tests/

clean:
	@rm -rf .venv htmlcov/
	@rm -f .coverage coverage.xml
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
```

Non-Python: same targets, different toolchain lines (see language layers).

### 2. CI delegates to make

One workflow per project; subprojects get path-filtered jobs (energy_envelope splits `android/**` from the Python root via `paths: ['!android/**']`).

```yaml
name: CI
on:
  push:
  workflow_dispatch:
concurrency:
  group: ${{ github.ref }}
  cancel-in-progress: true
permissions:
  contents: read
  pull-requests: write   # the coverage comment step needs it; drop if you drop that step
jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make setup
      - run: make lint-github
      - run: make test
      - run: make coverage
      - name: Coverage summary
        uses: irongut/CodeCoverageSummary@v1.3.0
        with:
          filename: coverage.xml
          badge: true
          fail_below_min: true
          thresholds: '80 90'
          format: markdown
          output: both
      - name: Post coverage comment
        uses: marocchino/sticky-pull-request-comment@v2
        if: github.event_name == 'pull_request'
        with:
          recreate: true
          path: code-coverage-results.md
```

Rules:
- `permissions: contents: read` + `pull-requests: write` — the coverage comment step in the template needs the latter; drop both together if you drop the step.
- `concurrency` group per ref with `cancel-in-progress: true` — every active repo does this.
- CI steps are exactly the make targets; never inline `pip install`/`npm test` logic into the workflow.
- Lint in CI via `make lint-github` (`ruff check --output-format=github`) so findings surface as PR annotations; plain `make lint` stays for local use. The template reflects this.
- API-key-dependent suites: pass `${{ secrets.* }}` as env, run under a timeout wrapper, upload outputs with `if: always()` so failures are diagnosable (chat-workflow evals).

### 3. Code coverage is gated, not decorative

- `make coverage` emits an XML report for CI (`coverage.xml` Python, `coverage/clover.xml` JS) plus a human report.
- CI fails below a hard floor and tracks a higher goal: books_to_anki uses `irongut/CodeCoverageSummary` with `thresholds: '80 90'`, `fail_below_min: true`, posting a sticky PR comment via `marocchino/sticky-pull-request-comment`; side-by-side uses `slavcodev/coverage-monitor-action` on clover.xml.
- `htmlcov/`, `.coverage`, `coverage.xml` are gitignored; reports are generated on demand.

### 4. Git hygiene

- Never commit to main; branch off main, PR required, protected origin/main (rule://session-start; chat-workflow/houses AGENTS.md).
- Atomic commits; reference issues with `Fixes #N`.
- `.gitignore` must cover (each pattern observed in 3+ repos):
  - env/secrets: `.env`, `.env.local`, `*.keystore`
  - envs/deps: `.venv/`, `venv/`, `node_modules/`, `dist/`
  - caches: `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `.coverage`, `htmlcov/`, `coverage.xml`
  - build artifacts: `dist/`, `*.egg-info/` — `uv sync` with the setuptools backend generates `<pkg>.egg-info/`; omit it and verification step 4 fails
  - agent/tool state: `.sisyphus/`, `.opencode/`, `.code-review-graph/`, `.logs/`
  - IDE/OS: `.vscode/`, `.idea/`, `.DS_Store`, `*.log` (to commit `.vscode/extensions.json`, add a `!.vscode/extensions.json` negation — side-by-side's pattern)
  - recreatable data caches only (houses: `data/api_cache/`, `data/houses.db*`) — test fixtures are committed under `tests/fixtures/`
- Lockfiles (`uv.lock`, `package-lock.json`) are committed, never ignored. books_to_anki ignores `uv.lock` — that kills reproducibility; don't copy it. Keep the list curated: books_to_anki ships the kitchen-sink GitHub template (Django/Flask/PyInstaller/poetry sections it doesn't need); the newer repos use a short alphabetized list.
- `.gitattributes`: `* text=auto eol=lf`; mark generated files `linguist-generated` (kilocode).
- `.editorconfig`: `root = true`, `utf-8`, `insert_final_newline = true`, `eol = lf`, 2-space indent default, per-language overrides (kilocode). `max_line_length` must match the formatter (120 for ruff/prettier) — kilocode's editorconfig 80-vs-prettier-120 mismatch is a smell to avoid.
- `.env.example` committed with every env var documented (values blank); `.env` itself is gitignored. The app reads values from the real environment (`os.environ`) — never from a file — so `.env` is not a runtime artifact and never needs distributing. Dev scenario: `make setup` guarantees `.env` exists (`[ -f .env ] || cp .env.example .env`), and env loading is scoped to run-type targets only — `uv run --env-file .env python -m <pkg>` — never on lint/test/coverage, so CI and fresh clones are unaffected. `--env-file` has the correct precedence (real env wins over file values); shell sourcing does NOT (`set -a; . ./.env` clobbers real vars with blank file values, which would blank a real secret). The guarantee lives in the Makefile, not the one-time scaffold — the repo gets cloned forever without re-running the skill. Real secrets live in the shell environment only — never in code, docs, logs, or the example file (chat-workflow AGENTS.md; houses coding-standards). No env vars at all? Ship a comment-only `.env.example` — the setup copy line stays harmless.
- `.vscode/extensions.json` with recommended extensions — only if you want editor parity; it requires the `!.vscode/extensions.json` negation above (side-by-side ships one with `Vue.volar`; kilocode ships eslint/esbuild/direnv). Otherwise `.vscode/` is fully ignored.
- Git hooks (stack-appropriate mechanism, see language layers) run ONLY fast checks — lint and typecheck — never the full test suite; tests stay gated in `make test` + CI. Hooks must finish in seconds or they get bypassed, and they're bypassable with `--no-verify` anyway — so anything critical must ALSO be enforced in make/CI. Python: `pre-commit` framework. JS/TS: husky.

### 5. Entry docs: README for humans, AGENTS.md for agents

- `README.md` (humans): one-line purpose, Quick Start via `make`, usage examples, docs table.
- `AGENTS.md` (agents): quick start (`make setup` / `make test`), a Testing Rules section mandating make targets ("ALWAYS use `make` targets; NEVER construct ad-hoc test commands"), a decision tree routing tasks to `docs/`, tool-selection table, git workflow, secrets rule (`test -n "$VAR"` never `echo $VAR`).
- `docs/` standards triplet, checked by PR-Agent:
  - `docs/coding-standards.md` — design principles, semantic types over primitives, class-per-module, fail fast, never swallow errors, no backward-compat shims, DI over patching.
  - `docs/testing-standards.md` — tests mirror module paths, deterministic (no wall-clock, network, or order dependence; seeded randoms), assert behavior not implementation, DI fakes over `unittest.mock.patch`.
  - `docs/writing-documentation.md` — content = skill://write-documentation (context efficiency, density, ~150–200 line ceiling). Link, don't copy.
- Wire the standards into review: `.pr_agent.toml` `repo_context_files` lists them; `extra_instructions` demands a per-doc Compliance section in every review (houses, books_to_anki).

### 6. PR review & dependency automation

- `.pr_agent.toml` + `.github/workflows/pr-agent.yml`: the-pr-agent action with the house provider, standards docs in `repo_context_files`, a per-doc Compliance instruction, and a "check review succeeded" step that fails the PR when no review comment covers the head commit (books_to_anki's attribution logic). Exact TOML:

```toml
[openai]
custom_llm_provider = "openai"
api_base = "https://opencode.ai/zen/go/v1"

[config]
model = "openai/deepseek-v4-flash"
custom_model_max_tokens = 128000
max_model_tokens = 128000
ai_timeout = 600
fallback_models = []
repo_context_from_default_branch = false
repo_context_files = [
    "docs/coding-standards.md",
    "docs/testing-standards.md",
    "docs/writing-documentation.md",
]

[pr_reviewer]
require_tests_review = true
require_security_review = true
num_max_findings = 5
extra_instructions = "Check the PR against each file in repo_context_files. Add a 'Compliance' section per doc, listing any violations found or 'No violations'."

[github_action_config]
handle_push_trigger = true
push_commands = ["/review", "/improve"]
```

The workflow file, compact (books_to_anki adds an elaborate gh-api attribution check; **pin a real release tag — `@latest` does not resolve**):

```yaml
name: AI Code Review
on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
jobs:
  pr-review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      issues: write
    steps:
      - uses: actions/checkout@v4
      - uses: the-pr-agent/pr-agent@v0.41.1   # pin a real release tag — @latest does not resolve
        id: pr-agent
        env:
          OPENAI_KEY: ${{ secrets.<PROJECT>_API_KEY }}
          OPENAI_BASE_URL: https://opencode.ai/zen/go/v1
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      # Check step: fail the PR when no "PR Reviewer Guide" comment covers the
      # head commit (gh-api attribution; see books_to_anki for the full logic).
```

- `.github/dependabot.yml` — for uv projects the package ecosystem is dependabot's `pip` ecosystem (it reads `uv.lock`):

```yaml
version: 2
updates:
  - package-ecosystem: "pip"   # uv projects map here (uv.lock supported)
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

### 7. Repo creation & branch protection

None of the surveyed repos have protection enforceable from the tree — it's a GitHub setting. The scaffold must create the repo and apply it:

```bash
# git init first: make setup runs `pre-commit install`, which needs a repo
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
- **Set `<PROJECT>_API_KEY` as a repo secret BEFORE the first PR** — the review job fails fast without it (observed: secret created after the PR-open event, run dead in 6s).

## Language layers

### Python (books_to_anki, chat-workflow, energy_envelope, houses)

- Toolchain: **uv** (`uv sync`), `.python-version` pinned to the **current stable** at scaffold time — find it via `uv python list` (cross-check python.org); never guess from training data, never a beta. Pin the newest stable the project's critical deps support (books_to_anki pins `==3.9.*` for spacy — the cautionary tale). Metadata `requires-python` is `>=X.Y` unbounded; ruff `target-version` tracks the pin.
- **ruff** (lint + format): `select = ["E","F","I","UP","B","SIM","N"]`, `line-length = 120`, `quote-style = "double"` — the converged chat-workflow/energy_envelope config, minus one deviation: those repos add `ignore = ["UP046","UP047"]` (PEP 695 type-parameter syntax, for runtime-reflection compat). The scaffold does NOT carry that ignore — it's a constraint inherited from chat-workflow's code, not a general practice, and energy_envelope cargo-culted it. If a new repo hits a real reflection incompatibility, fix the reflection, don't ignore the rule.
- **pytest**: `testpaths = ["tests"]`, tests mirror package layout; `pytest-cov` for coverage. Default for everything — fixtures, `parametrize`, plugins. Deviation is justified only for eval/API harnesses that need module-level discovery with a custom runner: chat-workflow runs `python -m unittest discover tests/evals/` under a timeout wrapper for exactly that. That's a niche — before choosing unittest, check whether a thin wrapper around pytest gives the same control.
- Layout: flat package at repo root `<pkg>/` (newer repos) with `[tool.setuptools.packages.find] include = ["<pkg>*"]`; use `src/` layout only when distributing on PyPI (books_to_anki — it forces `pip install -e .` before tests, catching packaging bugs). Flat is the converged house style for internal tools. A CLI needs `<pkg>/__main__.py` — the run target (`python -m <pkg>`) fails with "No module named <pkg>.__main__" without it.
- Type checker: **basedpyright** (houses, chat-workflow) or **mypy** (books_to_anki); gated via `make typecheck` inside `make test`. Invocation is the BARE command — `basedpyright` is config-driven and has NO `check` subcommand (`basedpyright check` exits 4 treating `check` as a path).

  **basedpyright exits 1 on WARNINGS by default** — "0 errors, 500 warnings" fails the gate and the pre-commit hook. Gate on the ERROR COUNT, not the exit code or `--level`: `basedpyright --outputjson | python -c "import json,sys; sys.exit(1 if json.load(sys.stdin)['summary']['errorCount'] else 0)"` — `--level=error` is ignored in CI because basedpyright has an "actions mode" (triggered by the `GITHUB_ACTIONS` env var) where the `--level` filter does not apply to the exit code: same binary 1.39.9, same command, warnings suppressed + exit 0 locally, warnings printed + exit 1 with `GITHUB_ACTIONS=true`. Known open bug: DetachHead/basedpyright#1481 (also #1351, #1319); the JSON-summary parse is the community-standard fix (see delfianto/the-bannered-mare 0de005b, Foxerine/sqlmodel-ext d3d0bcb). Keep `--level error` only as pre-commit hook args (hooks run locally). Scope analysis with `include` — an `exclude` key REPLACES the implicit `.venv`/cache exclusions and the scan explodes into site-packages (observed: 11k+ errors, 170k warnings).

  **Bringing an existing repo into house shape** (not greenfield): bare `dict` annotations fail basedpyright — use `dict[str, Any]`; pytest fixture params need explicit annotations (`tmp_path: Path`); DI fakes must SUBCLASS the real classes — plain `cast` fails with `reportInvalidCast` when the types don't overlap.
- Dev deps in PEP 735 `[dependency-groups] dev`: pytest, pytest-cov, ruff, pre-commit (+ type checker). `uv sync` installs them by default. No plain-pip support, so extras (`[project.optional-dependencies]`) are not used. Never split deps across both mechanisms — chat-workflow does, which is a smell.
- Git hooks: `pre-commit` framework, installed by `make setup` (`uv run pre-commit install`). Ship this exact config — the basedpyright hook lives in the MIRROR repo `DetachHead/basedpyright-prek-mirror` (unprefixed tags); `DetachHead/basedpyright` itself fails with InvalidManifestError:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.1   # pin a recent tag
    hooks: [id: ruff, id: ruff-format]
  - repo: https://github.com/DetachHead/basedpyright-prek-mirror
    rev: 1.39.9    # UNPREFIXED tag; the mirror, not the main repo
    hooks:
      - id: basedpyright
        args: ["--level", "error"]   # warnings fail by default; errors gate the commit
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1   # pin a recent tag
    hooks: [id: gitleaks]
```

Fast checks only, never a test hook. `.gitleaksignore` whitelists intentional test fixtures (kilocode's pattern). Hooks run on ALL staged files — pyproject `include` scope does not apply, so scratch/legacy dirs need per-hook `exclude: ^dir/`. The ruff hook runs with `--fix`: it edits staged files and pre-commit aborts the commit — expect a re-add + recommit cycle (and `pre-commit run --all-files` skips everything until the first commit exists).

```toml
[project]
name = "<project>"
version = "0.1.0"
description = "<one line>"
readme = "README.md"
requires-python = ">=3.12"  # bump to current stable at scaffold time (uv python list)
dependencies = []

[dependency-groups]
dev = ["pytest>=8.0.0", "pytest-cov>=5.0.0", "ruff>=0.11.0", "pre-commit>=3.0.0", "basedpyright>=1.39.0"]

[build-system]
requires = ["setuptools>=64.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["<pkg>*"]

[tool.ruff]
target-version = "py312"  # match the .python-version pin
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "N"]
# No ignore list: don't cargo-cult chat-workflow/energy_envelope's UP046/UP047
# skip (a reflection constraint there, not a general practice).
fixable = ["ALL"]

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.coverage.run]
omit = ["*/__main__.py"]  # entry points are never imported by tests — omit them or the 80% CI gate fails

[tool.basedpyright]
# config-driven (no subcommand). Scope with `include`, NOT `exclude` — an
# `exclude` key replaces the implicit .venv/cache exclusions and the scan
# explodes into site-packages. --level=error lives in the Makefile + hook.
include = ["<pkg>", "tests"]
```

### JS/TS (side-by-side, houses/frontend, kilocode)

- npm scripts named to mirror make targets: `dev`, `build`, `preview`, `test`, `coverage`, `lint`, `format` — `make test` maps 1:1 to `npm test`.
- Test runner: **vitest**, happy-dom or jsdom; coverage provider **istanbul** with reporters `["text", "clover"]` → CI consumes `coverage/clover.xml`.
- Lint: **ESLint flat config** (`@eslint/js` + `typescript-eslint` + framework plugin, `eslint-config-prettier` LAST so style rules are disabled) — or **oxlint** with `typeAware: true` (kilocode). Prettier separate, defaults.
- TS: `strict: true`, `noUnusedLocals`/`noUnusedParameters`/`noFallthroughCasesInSwitch`; `vue-tsc -b` type-check gate inside `build` (houses/frontend). Solution-style project references for mixed configs.
- Node pinned in CI (`actions/setup-node@v4`, `node-version: 22.x`, `cache: npm`) AND locally via `.nvmrc` containing the same version — local dev must match CI (no repo does this yet; side-by-side/houses pin CI only, kilocode pins bun via `packageManager`). `engines` in package.json is an optional extra.
- Releases (monorepos): `.changeset` with restricted access, baseBranch main (kilocode).
- Git hooks: husky pre-commit running lint + typecheck + **gitleaks** (kilocode's pre-push adds a toolchain-version check against `packageManager`). Fast checks only.

### Other languages

- Apply the general layer verbatim; only the toolchain lines in the Makefile change. cv (LaTeX) is the pattern: Makefile with a real dependency graph (`sample.pdf: sample.tex resume.cls` → `lualatex -halt-on-error`), `install`/`uninstall` targets to `~/.local/bin`, `make` = build + smoke test.
- Services: docker-compose with layered files for optional stacks (core `docker-compose.yml` + optional overlay), per-service Dockerfile, shared `env_file`, version-tagged images (spark-local-env).

## Verification (prove the scaffold works)

Run in order; the checklist below is the final gate, not documentation.

1. **Fresh-clone smoke test** — the single most valuable check. Clone the new repo into a temp dir and run `make setup && make lint && make test` there. This simulates exactly what every future clone and CI run experiences; it fails if anything depends on scaffold-session state (venv, cwd, env, uncommitted files).
2. **Coverage and clean loop** — `make coverage` (emits `coverage.xml` for the CI gate), then `make clean`, then re-run `make test` — proves the clean target doesn't break the loop.
3. **Hooks actually fire** — `uv run pre-commit run --all-files` passes (pre-commit lives in the venv; the bare command is not on PATH). Then prove gitleaks with a REALISTIC key: plain `sk-` + 24 chars matches no default rule (empirically passes); use the OpenAI format `sk-` + 20 alnum + `T3BlbkFJ` + 20 alnum (RuleID `openai-api-key`). Confirm the commit is blocked, revert, confirm it passes.
4. **Gitignore honesty** — after setup, `git status --porcelain` is empty: `.venv/`, `.env`, caches, and agent state never appear.
5. **CI, for real** — push a feature branch, open a PR, `gh pr checks --watch` until green; only then merge. (Branch protection cannot be applied until the check has run once.) No remote yet? Run `actionlint` over the workflow files as the static substitute. Local fresh-clone smoke ≠ CI: the same make recipe passed locally (and in a local clone) but failed on the GitHub runner — budget one CI debug iteration (print `--version`, `--help`, raw exit codes) when standing up a new repo.
6. **Walk the checklist** — every box checked against the actual repo, not from memory.

## Checklist

### General (every repo)
- [ ] Makefile with `help setup lint test coverage format clean` (+ `run`/`stop` for services, `dist` for artifacts); `.PHONY` on all targets
- [ ] `make test` depends on `make lint`; CI runs only make targets
- [ ] `make setup` idempotent — installs toolchain if missing, syncs deps
- [ ] `make clean` removes exactly `.venv`/`node_modules`, `htmlcov/`, `.coverage`, `coverage.xml`, caches — never user data
- [ ] CI workflow: checkout@v4, `permissions: contents: read`, concurrency group with `cancel-in-progress: true`, steps = `make setup` → `make lint` → `make test`
- [ ] Coverage emitted as XML for CI (`coverage.xml` / `coverage/clover.xml`); CI fails below floor (~80%), posts PR comment, tracks 90%. For an EXISTING codebase, set the floor below the measured number first (e.g. 65 floor / 80 goal at 71% measured) and raise it as coverage lands — a hard 80 gate on day one is a broken CI
- [ ] `.gitignore` covers env, venv/node_modules, IDE, caches, agent state, logs, recreatable data
- [ ] `.env.example` committed, all vars documented, values blank; `.env` gitignored; `make setup` ensures `.env` exists (copy from example); run targets load via `--env-file` (real env wins), lint/test never touch it
- [ ] `.editorconfig` (utf-8, lf, final newline) and `.gitattributes` (`* text=auto eol=lf`)
- [ ] README.md: purpose, Quick Start via make, usage, docs table
- [ ] AGENTS.md: quick start, make-target testing rule, decision tree to `docs/`, git + secrets rules
- [ ] `docs/` triplet: coding-standards.md, testing-standards.md, writing-documentation.md (per skill://write-documentation)
- [ ] PR review wired: `.pr_agent.toml` + pr-agent workflow with standards docs in `repo_context_files`; `<PROJECT>_API_KEY` secret set BEFORE the first PR
- [ ] dependabot: weekly for package ecosystem + `github-actions`
- [ ] Branch workflow: never commit to main, PRs required, protected main
- [ ] Git hooks run only fast checks (lint, typecheck), installed by `make setup`; never the full test suite
- [ ] End-to-end green: `make setup && make lint && make test` locally and CI green on push
- [ ] Repo created via `gh repo create --source --push --private`; branch protection applied after first CI run (PR + status check required)

### Python
- [ ] uv + `.python-version` = current stable at scaffold time (via `uv python list`, subject to dep support); ruff `target-version` matches
- [ ] pyproject.toml: ruff `select E,F,I,UP,B,SIM,N`, `line-length 120`, double quotes, no ignore list
- [ ] pytest with `testpaths = ["tests"]`; dev deps in `[dependency-groups] dev` (PEP 735)
- [ ] pytest is the runner; unittest only for eval harnesses needing module-level discovery (documented deviation, not default)
- [ ] Type checker (basedpyright or mypy) configured and gated inside `make test` (`--level=error` in make target AND hook args; scope via `include`, never `exclude`)
- [ ] Flat `<pkg>/` layout with `packages.find` include
- [ ] pre-commit config: ruff + basedpyright + gitleaks hooks, installed by `make setup`

### JS/TS
- [ ] npm scripts mirror make targets: dev/build/preview/test/coverage/lint/format
- [ ] vitest + istanbul, reporters text+clover → `coverage/clover.xml`
- [ ] ESLint flat config with prettier last (or oxlint `typeAware`); prettier defaults
- [ ] `strict: true` TS; type-check gate inside `build`
- [ ] Node pinned in CI (setup-node, 22.x) and locally (`.nvmrc` same version)
- [ ] husky pre-commit: lint + typecheck + gitleaks

### Non-code
- [ ] Docker services: layered compose files, per-service Dockerfile, shared env_file
- [ ] Other languages: Makefile carries the real build dependency graph; `install` to `~/.local` where applicable
