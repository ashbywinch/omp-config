---
name: scaffold-language-layers
description: |
  The per-stack toolchain layers for skill://new-repo-scaffold — Python
  (uv/ruff/pytest), JS/TS (npm/vitest/eslint), other — materialized into a new
  repo's docs/coding-standards.md copy. The generic rules live in the General
  layer of skill://new-repo-scaffold and the standards docs; each layer fills
  in the toolchain implementation of those rules for one stack.
---

## Language layers

Every language layer fills in the toolchain for the **generic rules** — it never
creates a rule with no generic equivalent. The generic rules are in the General
layer of `skill://new-repo-scaffold` and in the standards docs; the language
layer is the toolchain implementation of those rules for one stack. The pattern
each layer covers:
runtime pin (CI + local same version), lint + formatter wired into make
(§1, §1b), **type checker configured and gated** (§1), test runner + coverage
wired into make test/coverage (§1), fast commit hooks with **lint + typecheck
+ secrets scan** (§4), semantic-type library choices (quantities, Money —
the generic rules are in the global standard), repo self-checks (§3b:
docs links + architecture layers), and materialization of the layer's
conventions into the repo's `docs/coding-standards.md` copy. A new language
layer is complete only when every generic rule has its toolchain filled in —
and every toolchain-specific rule it introduces points back at a generic
equivalent.

### Python (books_to_anki, chat-workflow, energy_envelope, houses)

- Toolchain: **uv** (`uv sync`), `.python-version` pinned to the **current stable** at scaffold time — find it via `uv python list` (cross-check python.org); never guess from training data, never a beta. Pin the newest stable the project's critical deps support (books_to_anki pins `==3.9.*` for spacy — the cautionary tale). Metadata `requires-python` is `>=X.Y` unbounded; ruff `target-version` tracks the pin.
- **ruff** (lint + format): `select = ["E","F","I","UP","B","SIM","N"]`, `line-length = 120`, `quote-style = "double"`. The scaffold does NOT carry `ignore = ["UP046","UP047"]` (PEP 695 type-parameter syntax). If a new repo hits a real reflection incompatibility, fix the reflection, don't ignore the rule.
- **pytest**: `testpaths = ["tests"]`, tests mirror package layout; `pytest-cov` for coverage. Default for everything — fixtures, `parametrize`, plugins. Deviation is justified only for eval/API harnesses that need module-level discovery with a custom runner: chat-workflow runs `python -m unittest discover tests/evals/` under a timeout wrapper for exactly that. That's a niche — before choosing unittest, check whether a thin wrapper around pytest gives the same control.
- **Semantic types, the library choices** (the generic rules are in the global standard — `docs/coding-standards.md`): **pint** for quantities (`pint.Quantity`, never bare `float`/`int` for distances, durations, speeds), and a **Money type with currency** for money (houses uses `money.Money`; never bare `float`, never bare `Decimal` in signatures). Houses' conventions: turn numeric literals into quantities by *multiplying by a one-unit `Quantity` constant* (`KM = 1.0 * ureg.km; radius = 4.0 * KM`), never by calling the `Quantity` constructor with a literal unit string; define the constants once per package from a single `UnitRegistry` (pint forbids mixing registries); wire formats stay unit-named bare numbers (pint has no JSON representation).
- **Materialization.** These Python conventions — the library choices above, the ruff/basedpyright gates, pytest conventions, the flat layout — are appended to the repo's `docs/coding-standards.md` as a "Python conventions" section when scaffolding. The review bot reads only `repo_context_files`; a toolchain rule that stays only in this skill is invisible to review (a fresh repo would pass review while violating the semantic-type rules).
- Layout: flat package at repo root `<pkg>/` (newer repos) with `[tool.setuptools.packages.find] include = ["<pkg>*"]`; use `src/` layout only when distributing on PyPI (books_to_anki — it forces `pip install -e .` before tests, catching packaging bugs). Flat is the converged house style for internal tools. A CLI needs `<pkg>/__main__.py` — the run target (`python -m <pkg>`) fails with "No module named <pkg>.__main__" without it.
- Type checker: **basedpyright** (houses, chat-workflow) or **mypy** (books_to_anki); gated via `make typecheck` inside `make test`. Invocation is the BARE command — `basedpyright` is config-driven and has NO `check` subcommand (`basedpyright check` exits 4 treating `check` as a path).

  **basedpyright exits 1 on WARNINGS by default** — "0 errors, 500 warnings" fails the gate and the pre-commit hook. Gate on the ERROR COUNT, not the exit code or `--level`: `basedpyright --outputjson | python -c "import json,sys; sys.exit(1 if json.load(sys.stdin)['summary']['errorCount'] else 0)"` — `--level=error` is ignored in CI because basedpyright has an "actions mode" (triggered by the `GITHUB_ACTIONS` env var) where the `--level` filter does not apply to the exit code: same binary 1.39.9, same command, warnings suppressed + exit 0 locally, warnings printed + exit 1 with `GITHUB_ACTIONS=true`. Known open bug: DetachHead/basedpyright#1481 (also #1351, #1319); the JSON-summary parse is the community-standard fix (see delfianto/the-bannered-mare 0de005b).

  **Bringing an existing repo into house shape** (not greenfield): bare `dict` annotations fail basedpyright — use `dict[str, Any]`; pytest fixture params need explicit annotations (`tmp_path: Path`); DI fakes must SUBCLASS the real classes — plain `cast` fails with `reportInvalidCast` when the types don't overlap.
- Dev deps in PEP 735 `[dependency-groups] dev`: pytest, pytest-cov, ruff, pre-commit (+ type checker), and **archunitpython** for the architecture-layer self-check (§3b). `uv sync` installs them by default. No plain-pip support, so extras (`[project.optional-dependencies]`) are not used. Never split deps across both mechanisms — chat-workflow does, which is a smell.
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
- **Materialization.** These JS/TS conventions — vitest/istanbul, the eslint/oxlint + prettier setup, `strict: true` + `vue-tsc` gate, the Node pin — are appended to the repo's `docs/coding-standards.md` as a "JS/TS conventions" section when scaffolding. The review bot reads only `repo_context_files`; a toolchain rule that stays only in this skill is invisible to review.

### Other languages

- Apply the general layer verbatim; only the toolchain lines in the Makefile change. cv (LaTeX) is the pattern: Makefile with a real dependency graph (`sample.pdf: sample.tex resume.cls` → `lualatex -halt-on-error`), `install`/`uninstall` targets to `~/.local/bin`, `make` = build + smoke test.
- Services: docker-compose with layered files for optional stacks (core `docker-compose.yml` + optional overlay), per-service Dockerfile, shared `env_file`, version-tagged images (spark-local-env).
