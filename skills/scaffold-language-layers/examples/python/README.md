# Python stack examples — copy into a Python repo

The files here are the **Python** toolchain layer of the scaffold. Copy them
into the repo root (they land at their real paths — `Makefile`, `pyproject.toml`,
`pyrefly.toml`, `.pre-commit-config.yaml`, `scripts/`), then edit the `CHANGE`
points.

**Copy the general layer too**: `skill://new-repo-scaffold/examples/` (dotfiles,
CI workflow, review bot, dependabot) — this dir is only the stack half. Both
halves together form the repo's shape.

## What's here and why

| File | Purpose |
|---|---|
| `Makefile` | Single dev entry point: `setup deps install-hooks run test check lint format coverage clean`. Shell pinned to bash (`SHELL := /bin/bash` + `.SHELLFLAGS := -eu -o pipefail -c`) — dash on CI runners has no `pipefail`, so unpinned recipes fail CI but pass macOS. `check` = `lint-check typecheck`, the exact gate CI and the pre-push hook run. `deps` never depends on `install-hooks` (the pre-push deadlock). |
| `pyproject.toml` | uv/ruff/pytest config, PEP 735 dev deps, pyrefly section (or the commented basedpyright alternative). |
| `pyrefly.toml` | Top-level keys only (a `[pyrefly]` wrapper here is silently ignored); `preset = "default"` + the two meaningful default-off `[errors]` rules. |
| `.pre-commit-config.yaml` | Fast checks only: ruff + pyrefly + gitleaks. The basedpyright hook alternative is commented out. |
| `scripts/pre-commit` | Delegates to `make lint-check` — never duplicates the tool invocation. |
| `scripts/pre-push` | Delegates to `make check`; skip logic watches `*.py '*.ts' '*.vue' '*.js' pyrefly.toml`; must not skip unstaged/untracked sources. |
| `scripts/pyrefly-lock.py` | The both-direction baseline lock: new errors AND stale baseline entries fail (pyrefly's own baseline is one-way). |

## Comment convention

`CHANGE` = edit per project (package name, versions). `DO NOT CHANGE` =
house invariants (shell pin, check gate, deps-not-install-hooks, the lock).
See the owning skill `skill://scaffold-language-layers` for the reasoning.
