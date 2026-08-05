# Standards Deployment

A concise high-level overview of how the house standards reach new repos and
are enforced.

## Source of truth

The canonical standards live in the **omp-config** repo in two homes:

- `standards/` — the **code-repo standards**: `coding-standards.md`,
  `testing-standards.md`, `ux-standards.md`. They are scaffolded into code
  repos and do not govern omp-config itself (no code, no tests, no product).
- `docs/` — the **doc standards that govern omp-config itself**:
  `writing-documentation.md` (what good documentation is — skills are
  documentation, so this standard applies to every skill here) and
  `documentation-structure.md` (the required doc set and discoverability),
  plus omp-config's own `PRD.md` and this overview.

Skills (procedures that apply the standards) live in `skills/` and are loaded
via `skill://<name>`.

## How standards reach repos

The **repo-scaffold skill** (`skill://new-repo-scaffold`) is the single path:
1. It copies every canonical standard from omp-config — from `standards/`
   (coding, testing, UX) and from `docs/` (writing-documentation,
   documentation-structure) — into the new repo's `docs/` folder.
2. It appends the relevant language layer's conventions (Python, JS/TS — see
   `skill://scaffold-language-layers`) as a language-specific section of the
   repo's `docs/coding-standards.md` copy.
3. It sets up `.pr_agent.toml` with `repo_context_files` pointing at every
   copied standard, so the review bot checks PRs against them.
4. It adds a CI workflow that delegates to `make test`.

Existing repos are refreshed by re-running the relevant parts of the scaffold
or by manually copying updated standard docs from omp-config (the doc headers
state the canonical location).

## The review bot

PR-Agent reads the `repo_context_files` listed in `.pr_agent.toml` and reports
a Compliance section per doc in every review. In a code repo, those are the
copied standards in that repo's `docs/`. In omp-config itself, the bot checks
PRs against the set that governs this repo: `docs/PRD.md`,
`docs/writing-documentation.md`, `docs/documentation-structure.md` — the
code-repo standards in `standards/` are outside its scope except when a PR
edits them. Its `extra_instructions` tell it to flag violations as findings,
not style notes. The bot sees what the standards say — so the standards must
be written as named anti-patterns with checkable forms.

## The self-check

Every repo runs `make test` as its gate. The test suite includes a self-check
where the toolchain supports it (omp-config's `tools/check_docs_links.py`
validates discoverability from AGENTS.md, skill well-formedness, and
always-loaded size ceilings). This is the deterministic part of enforcement;
the judgment part stays with the review bot.
