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
make install    # re-symlink after an edit (OpenCode reloads skills itself)
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
| `tools/check_docs_links.py` | Contract checks, asserted by `tools/tests/` |
| `tools/generate_tree.py` | Notion structure tree generator (mirror-safe, superseded section) |
| `tools/gh-app-shim` | GitHub App auth shim for `gh` — omp uses the app token, your terminal uses your creds (`make install-gh-shim`) |
| `tools/secrets.template` | Template for `~/.secrets` — copy, fill, `chmod 600`; never commit values |
| `.pr_agent.toml` | The review bot's context (`repo_context_files`) and instructions |

## GitHub App auth for gh (omp vs your terminal)

omp shells out to `gh` for GitHub work. The `tools/gh-app-shim` makes an
**agent session** authenticate as the **omp-harness GitHub App**, while your
own terminal keeps your personal credentials:

- **agent session** — any of `PASEO_AGENT_ID`, `OMP_GIT_IDENTITY=bot`,
  `OPENCODE=1`, `AI_AGENT` is set → mint a fresh app installation token,
  override any inherited `GH_TOKEN`/`GITHUB_TOKEN` (a user token must not leak
  into agent calls), export `GH_TOKEN` for that call, exec real `gh`
- **otherwise** (your terminal, scripts, cron) → pass through to real `gh`

The OpenCode markers are load-bearing. Paseo hands an agent its identity
through OpenCode's per-session environment, so a top-level agent carries
`PASEO_AGENT_ID` whichever server serves it. A subagent is a *child* OpenCode
session: OpenCode creates it inside the server and Paseo never sets an
environment for it, so its shells carry `OPENCODE=1` and no agent id. Those
shells fell through to the stored human account and created PRs as the human.
GitHub greys out **Approve** on your own PR, so that PR can never be approved
by that human — the one identity the desk's gate depends on. The same
predicate gates `tools/git-app-shim` (commits and pushes), so both halves of a
session agree.

`OPENCODE=1` is safe to key on because your own shell does not have it: the
Paseo terminal worker sets `PASEO_TERMINAL_ID` and `PASEO_WORKSPACE_ID`, and no
OpenCode marker. Any marker your interactive shell also carried would turn
your own `gh` into the bot's.

**No literal secret, anywhere.** The only secret is the App private key, at the
path in `GITHUB_APP_KEY_FILE` (`chmod 600`, outside the repo). The shim mints a
token per call from it — so no token is stored, none can go stale, and no
tracked file, shell profile or daemon env holds a value to leak. The app id and
installation id are public identifiers and live beside it in `~/.secrets`
(`GITHUB_APP_ID`, `GITHUB_APP_INSTALLATION_ID`), sourced by the shim at runtime
— so it works under the Paseo daemon and a bare terminal alike.

Verify the identity in a shell started the way an agent's is:

```bash
env OPENCODE=1 zsh -c 'gh auth status'   # Active account: omp-harness[bot]
zsh -c 'gh auth status'                  # Active account: you
```

New machine: `make install-gh-shim` symlinks the shim to `~/.local/bin/gh`
and creates `~/.secrets` from `tools/secrets.template` if missing. Fill in
the values and `chmod 600 ~/.secrets`. Keep the private key at the path in
`GITHUB_APP_KEY_FILE`, `chmod 600`, never commit it.

## Updating a skill or rule

1. Edit the file in this repo (never `~/.omp/agent/...` — those are symlinks).
2. `make install` to refresh the symlinks. OpenCode reloads skill content as it changes; restart only if a skill does not appear.
3. Branch + PR, like any repo — never commit to main.

See `skill://update-skills` for the full process, including when a lesson
earns a skill.
