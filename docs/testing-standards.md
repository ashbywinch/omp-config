# Testing Standards — omp-config

omp-config has no code, so the house testing standard reduces to the repo
self-check — but the rules that apply apply fully.

## The repo self-check (`make test`)

`tools/check_docs_links.py` is the test suite, run via `make test` (never
ad-hoc). Two checks:

1. **Every relative markdown link resolves** — across README, AGENTS,
   APPEND_SYSTEM, `docs/`, `skills/*/SKILL.md`, `rules/`, `profiles/`.
   Harness URIs (`skill://`, `rule://`), anchors, external URLs, template
   variables, and links inside code fences are skipped; everything else must
   point at an existing file inside the repo. A doc that links nowhere is a
   finding.
2. **Every skill is well-formed** — `skills/<name>/SKILL.md` exists with
   frontmatter `name` matching the folder and a `description`. A mismatch
   silently breaks `skill://` resolution.

## Rules

- **Deterministic.** No wall-clock, network, or order dependence — the
  check is pure file scanning.
- **Gated through make.** `make test` is the gate; CI runs `make test`;
  the pre-commit hook runs the same check (fast). Never construct ad-hoc
  test commands.
- **A test that cannot fail on a plausible bug is not a test.** The link
  check fails when a link breaks; the skills check fails when frontmatter
  drifts — both fail on real, observable breakage.
- **The self-check applies to itself.** A change to the checker must keep
  `make test` green (no tautological relaxations).
