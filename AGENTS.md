# AGENTS.md — omp-config

Instructions for AI agents working in this repo. This is the bootloader, not
the operating system: it holds only what is genuinely relevant to 100% of
agents here. Anything a subset needs lives in the doc or skill the tree
links to.

## Quick start

- `make setup` — provisions everything: symlinks skills/rules/APPEND_SYSTEM into `~/.omp/agent/`, the lucidlint bundle into `.tools/`, git hooks (pre-commit + pre-push), gh/git shims.
- `make install` — re-symlink after an edit. **Restart omp to pick up changes** (skills load at startup).
- `make install-gh-shim` — symlink `tools/gh-app-shim` → `~/.local/bin/gh`; create `~/.secrets` from `tools/secrets.template` if missing.
- `make test` — repo self-check: every relative doc link resolves + every skill is well-formed + the lucidlint gate. Provisions lucidlint on first run; pre-push runs it.
- NEVER run ad-hoc commands for these — everything goes through `make`.

## Where things live — decision tree

| Task | Route to |
|---|---|
| What this repo is for — JTBD, personas, constraints | `docs/PRD.md` |
| Load/understand a skill | `skill://<name>` → `skills/<name>/SKILL.md` |
| Update a skill, or turn a lesson into one | `skill://update-skills` (edit here → `make install` → restart omp → branch + PR) |
| Canonical coding standard (scaffolded into code repos) | `standards/coding-standards.md` |
| Canonical testing standard (scaffolded into code repos) | `standards/testing-standards.md` |
| Canonical UX standard (scaffolded into code repos) | `standards/ux-standards.md` |
| Documentation standard (what good documentation is) | `docs/writing-documentation.md` |
| Doc folder structure (the required doc set) | `docs/documentation-structure.md` |
| How the standards deploy to new repos | `docs/standards-deployment.md` |
| Trigger rules | `rules/*.md` |
| System prompt append | `APPEND_SYSTEM.md` |
| GitHub App auth for gh (omp vs terminal) | `tools/gh-app-shim` + `tools/secrets.template` (README section) |
| Agent git auth (bot identity, contract) | `tools/git-app-shim` + `tools/gen-agent-gitconfig.py` (contract in the tool headers) |
| The repo scaffold (how new repos are built) | `skills/new-repo-scaffold/SKILL.md` |

Read the relevant doc before changing behavior. **Before writing or editing any doc, skill, or APPEND_SYSTEM.md, read `docs/writing-documentation.md` first** — skills are documentation, and every rule there (single source of truth, density, one topic per file) applies to them. The canonical standards are the source — a repo's `coding-standards.md` doc is a copy of `standards/coding-standards.md` that must be refreshed when the canonical changes (the scaffold skill says so).

## Tool selection

| Task | Use |
|---|---|
| Load a skill or rule | `skill://<name>` / `rule://<name>` |
| Read a doc, skill, or directory | `read` |
| Locate files or search text | `glob` / `grep` |
| Edit a doc, skill, or standard | `edit` (surgical) / `write` (create/replace) |
| Verify the repo self-checks | `make test` |
| Make a skill/rule/append edit live | `make install` + restart omp → PR (see `skill://update-skills`) |

## Testing rules

- ALWAYS use `make` targets; NEVER construct ad-hoc test commands.
- `make test` is the gate: doc links resolve, skill frontmatter matches
  folder names. A skill whose frontmatter name drifts from its folder
  silently breaks `skill://` resolution — the check exists so that never
  ships.

## Secrets

- Real secrets live in the shell environment — never in code, docs, logs, or
  this repo (it is the conventions source, not a config store).
- In shell: `test -n "$VAR"` to check a variable — NEVER `echo $VAR` (leaks).
- `.pr_agent.toml` templates and examples in skills use placeholders only.

## Git workflow

- NEVER commit to main. Branch off main, PR required, protected main.
- Agent commits are authored `omp-harness[bot]` (the git shim enforces it) —
  never the user's identity. Mechanics: the `Agent git auth` row above.
- A skills/standards change is not live until `make install` + omp restart
  (the fact, stated here — nobody reads the PR description; 2026-08-08).
