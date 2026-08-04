# omp-config — the house conventions

The canonical configuration for the OpenCode/omp agent harness: **skills**
(the specialised-knowledge files loaded via `skill://<name>`), **rules** (the
trigger rules), the **global standards** (`docs/`), and the system prompt
append (`APPEND_SYSTEM.md`). It is the source repo for the house's
conventions — `make install` symlinks everything into `~/.omp/agent/` (and
rules into `~/.agent/rules/`), and the repo-scaffold skill copies the
standards into every new project repo.

## Quick start

```bash
make setup      # symlink rules/skills/APPEND_SYSTEM + install git hooks
make install    # re-symlink after an edit (restart omp to pick up changes)
make test       # repo self-check: every doc link resolves, every skill is well-formed
```

## Where things live

| Path | What it is |
|---|---|
| `skills/<name>/SKILL.md` | Skills — loaded on demand via `skill://<name>`; one folder per skill |
| `rules/*.md` | Trigger rules (greeting, session-start, fail-fast, …) |
| `docs/PRD.md` | Requirements — JTBD, personas, constraints, the overarching goal |
| `docs/coding-standards.md` | The canonical global coding standard (copied into every repo) |
| `docs/ux-standards.md` | The canonical UX standard (copied into every repo) |
| `docs/writing-documentation.md` | The documentation standard — what good documentation is (from `skill://write-documentation`) |
| `docs/documentation-structure.md` | The doc folder-structure standard — the required doc set (PRD/TECHSPEC/PLAN) |
| `docs/testing-standards.md` | The repo's testing standard (the self-check) |
| `profiles/` | User profile |
| `APPEND_SYSTEM.md` | The system-prompt append |
| `tools/check_docs_links.py` | The repo self-check (`make test`) |
| `.pr_agent.toml` | The review bot's context (`repo_context_files`) and instructions |

## Updating a skill or rule

1. Edit the file in this repo (never `~/.omp/agent/...` — those are symlinks).
2. `make install` to refresh the symlinks, then **restart omp**.
3. Branch + PR, like any repo — never commit to main.

See `skill://update-skills` for the full process, including when a lesson
earns a skill.
