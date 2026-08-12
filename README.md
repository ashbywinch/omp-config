# omp-config — the house conventions

The canonical configuration for the OpenCode/omp agent harness: **skills**
(the specialised-knowledge files loaded via `skill://<name>`), **rules** (the
trigger rules), the **standards** (`standards/` — the canonical code-repo
standards — and `docs/` — the standards that govern omp-config itself), and
the system prompt append (`APPEND_SYSTEM.md`). It is the source repo for the
house's conventions — `make install` symlinks everything into `~/.omp/agent/`
(and rules into `~/.agent/rules/`), and the repo-scaffold skill copies the
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
| `docs/writing-documentation.md` | The documentation standard — what good documentation is (from `skill://write-documentation`) |
| `docs/documentation-structure.md` | The doc folder-structure standard — the required doc set (PRD/TECHSPEC/PLAN) |
| `docs/standards-deployment.md` | How the standards reach new repos |
| `standards/coding-standards.md` | The canonical coding standard — scaffolded into code repos, not applicable to omp-config itself |
| `standards/testing-standards.md` | The canonical testing standard — scaffolded into code repos, not applicable to omp-config itself |
| `standards/ux-standards.md` | The canonical UX standard — scaffolded into code repos, not applicable to omp-config itself |
| `profiles/` | User profile |
| `APPEND_SYSTEM.md` | The system-prompt append |
| `tools/check_docs_links.py` | The repo self-check (`make test`) |
| `tools/generate_tree.py` | Notion structure tree generator (mirror-safe, superseded section) |
| `tools/gh-app-shim` | GitHub App auth shim for `gh` — omp uses the app token, your terminal uses your creds (`make install-gh-shim`) |
| `tools/secrets.template` | Template for `~/.secrets` — copy, fill, `chmod 600`; never commit values |
| `.pr_agent.toml` | The review bot's context (`repo_context_files`) and instructions |

## GitHub App auth for gh (omp vs your terminal)

omp shells out to `gh` for GitHub work. The `tools/gh-app-shim` makes omp
authenticate as the **omp-harness GitHub App** while your own terminal `gh`
keeps your personal credentials:

- **stdin is a TTY** (you in a terminal) → pass through to real gh (your creds)
- **`GH_TOKEN`/`GITHUB_TOKEN` set** (your scripts) → pass through untouched
- **neither** (omp, no TTY) → mint a fresh app installation token, export `GH_TOKEN`, exec real gh

The app id, key file path, and installation id live in `~/.secrets`
(`GITHUB_APP_ID`, `GITHUB_APP_KEY_FILE`, `GITHUB_APP_INSTALLATION_ID`), sourced
by the shim at runtime — so it works under the Paseo daemon and a bare
terminal alike, without the daemon holding a stale token.

New machine: `make install-gh-shim` symlinks the shim to `~/.local/bin/gh`
and creates `~/.secrets` from `tools/secrets.template` if missing. Fill in
the values and `chmod 600 ~/.secrets`. Keep the private key at the path in
`GITHUB_APP_KEY_FILE`, `chmod 600`, never commit it.

## Updating a skill or rule

1. Edit the file in this repo (never `~/.omp/agent/...` — those are symlinks).
2. `make install` to refresh the symlinks, then **restart omp**.
3. Branch + PR, like any repo — never commit to main.

See `skill://update-skills` for the full process, including when a lesson
earns a skill.
