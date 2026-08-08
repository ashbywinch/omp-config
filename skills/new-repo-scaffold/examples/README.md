# Scaffold examples — general layer

Every repo gets these files, **regardless of language**. Copy them into the
new repo root, then edit the `CHANGE` points.

## Two layers, two example dirs

| Layer | Where the examples live | Copy when |
|---|---|---|
| **General** (this dir) | `skill://new-repo-scaffold/examples/` | always — every repo |
| **Language** | `skill://scaffold-language-layers/examples/<stack>/` (e.g. `python/`) | the repo's stack — copy exactly one |

The general examples here are the language-agnostic skeleton: dotfiles, CI
workflow, review bot, dependabot. The stack-specific files (Makefile,
pyproject.toml, typechecker config, hooks) live in the language layer's
examples — a Python repo never sees `jsts/` files and vice versa. The
general + one stack dir together form the repo's full shape.

## Comment convention

Every file carries a `CHANGE` / `DO NOT CHANGE` header:

- `CHANGE` — per-project values you MUST adjust (package name, ports,
  coverage thresholds, the JS/TS coverage-action swap in ci.yml).
- `DO NOT CHANGE` — house invariants. Deviating is a smell the review bot
  will flag; if you think one is wrong for your repo, it's a standards
  discussion, not a local edit.

The rules these files implement are explained in the owning skill
(`SKILL.md`) — the file comments say *what* and *why*; the skill says
*when* to deviate.
