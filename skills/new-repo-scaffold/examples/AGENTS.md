# AGENTS.md — <project>

Instructions for AI agents working in this repo. This is the bootloader, not
the operating system: it holds only what is genuinely relevant to 100% of
agents here. Anything a subset needs lives in the doc or skill this tree
links to.

## Quick start

- `make setup` — install toolchain + deps, install git hooks.
- `make test` — the gate: lint + typecheck + tests.
- NEVER run ad-hoc commands for these — everything goes through `make`.

## Where things live — decision tree

| Task | Route to |
|---|---|
| What this repo is for — JTBD, personas, constraints | `docs/PRD.md` |
| How the software is built | `docs/TECHSPEC.md` |
| What's being built, in what order | `docs/PLAN.md` |
| Coding standard (design principles, toolchain gates) | `docs/coding-standards.md` |
| Testing standard | `docs/testing-standards.md` |
| UX standard | `docs/ux-standards.md` |
| UX spec | `docs/UX.md` |
| Documentation standard (what good documentation is) | `docs/writing-documentation.md` |
| Doc folder structure | `docs/documentation-structure.md` |

Read the relevant doc before changing behavior.

## Tool selection

| Task | Use |
|---|---|
| Load a skill or rule | `skill://<name>` / `rule://<name>` |
| Read a doc, skill, or directory | `read` |
| Locate files or search text | `glob` / `grep` |
| Edit a file | `edit` (surgical) / `write` (create/replace) |
| Verify the repo | `make test` |

## Testing rules

- ALWAYS use `make` targets; NEVER construct ad-hoc test commands.
- `make test` is the gate.

## Secrets

- Real secrets live in the shell environment — never in code, docs, or logs.
- In shell: `test -n "$VAR"` to check a variable — NEVER `echo $VAR` (leaks).

## Git workflow

- NEVER commit to main. Branch off main, PR required, protected main.
