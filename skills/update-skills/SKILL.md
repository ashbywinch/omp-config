---
name: update-skills
description: |
  Where skills, rules and APPEND_SYSTEM.md live, and how to update them
  correctly — edit the source in the omp-config repo, `make install` the
  symlinks, restart omp.
---

# Update Skills

Skills are the harness's specialised-knowledge files, loaded on demand via
`skill://<name>`. They live in the neighbouring **omp-config** repo, one
folder per skill; the harness reads them through symlinks that `make install`
creates in `~/.omp/agent/`. `skill://<name>` resolves to those installed
links, so an edit is only visible after install + restart.

## Where things live

| What | Source (edit here) | Installed to (by `make install`) |
|---|---|---|
| Skills | `~/Documents/code/omp-config/skills/<name>/SKILL.md` | `~/.omp/agent/skills/<name>/SKILL.md` |
| Rules | `~/Documents/code/omp-config/rules/*.md` | `~/.omp/agent/rules/*.md` |
| System append | `~/Documents/code/omp-config/APPEND_SYSTEM.md` | `~/.omp/agent/APPEND_SYSTEM.md` |
| Companion tools a skill needs to run | `~/Documents/code/omp-config/tools/<name>.sh` | `~/.local/bin/<name>` (PATH) |

## How to update correctly

1. **Edit the source in the repo** — never a file under `~/.omp/agent/` or
   `~/.agent/`. The installed files are symlinks to the repo, so editing
   through them happens to work, but the repo is the canonical, reviewed
   location.
2. **Follow the format**: YAML frontmatter (`name` — kebab-case, matching the
   folder — and `description`) then markdown. One skill per concern. Domain
   skills reference a mechanics skill (e.g. `skill://notion-database-management`)
   rather than inlining its content — a second copy of the same mechanics is
   the anti-pattern.
3. **`make install` in the omp-config repo** to refresh the symlinks, then
   tell the user to **restart omp** — the harness loads skills at startup.
4. **Commit and push** on a branch with a PR, like any repo — never commit to
   main.

## When a lesson becomes a skill

The `skill://learn-from-this-session` flow decides *what* to codify; this
skill is the mechanics for *how*. A lesson earns a skill when it would
prevent a repeated mistake or cut real investigation time. Translate it into
a generic principle first — no codebase-specific file names or project
jargon in the rule itself (a Notion-relational quirk belongs in
`notion-database-management`, not in a repo's standards).

## Anti-patterns

✗ editing `~/.omp/agent/skills/...` directly without `make install` — the
next install refreshes the symlink and the edit is silently lost.
✗ inlining the same mechanics (auth flows, API shapes, property types) into
every domain skill — update the one mechanics skill and reference it.
✗ a skill that tells the reader to `curl <url> | bash` a companion script —
materialise it via `make install` (see the Companion tools row above) and
reference the installed command (docs/writing-documentation.md: distribute
runnable code through the deployment mechanism).
✓ edit `SKILL.md` in omp-config → `make install` → restart omp → branch + PR.
