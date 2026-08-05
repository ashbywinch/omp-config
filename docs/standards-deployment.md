# Standards Deployment

A concise high-level overview of how the house standards reach new repos and
are enforced.

## Source of truth

All canonical standards live in the `docs/` folder of the **omp-config** repo:
- `coding-standards.md`
- `testing-standards.md`
- `writing-documentation.md`
- `documentation-structure.md`
- `ux-standards.md`

Skills (procedures that apply the standards) live in `skills/` and are loaded
via `skill://<name>`.

## How standards reach repos

The **repo-scaffold skill** (`skill://new-repo-scaffold`) is the single path:
1. It copies every canonical standard doc from omp-config into the new repo's
   `docs/` folder.
2. It appends the relevant language layer's conventions (Python, JS/TS) as a
   language-specific section.
3. It sets up `.pr_agent.toml` with `repo_context_files` pointing at every
   copied standard, so the review bot checks PRs against them.
4. It adds a CI workflow that delegates to `make test`.

Existing repos are refreshed by re-running the relevant parts of the scaffold
or by manually copying updated standard docs from omp-config (the doc headers
state the canonical location).

## The review bot

PR-Agent reads the `repo_context_files` listed in `.pr_agent.toml` and reports
a Compliance section per doc in every review. Its `extra_instructions` tell it
to flag violations as findings, not style notes. The bot sees what the
standards say — so the standards must be written as named anti-patterns with
checkable forms.

## The self-check

Every repo runs `make test` as its gate. The test suite includes a self-check
where the toolchain supports it (omp-config's `tools/check_docs_links.py`
validates discoverability from AGENTS.md, skill well-formedness, and
always-loaded size ceilings). This is the deterministic part of enforcement;
the judgment part stays with the review bot.
