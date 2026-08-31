---
name: lucidlint-workflow
description: |
  How to act on lucidlint findings in any repo — the fix-engine workflow
  (preview the seam, judge, apply with a name), the per-file LSP mode,
  and the baseline conventions. Read this before addressing a lucidlint
  finding.
---

# lucidlint workflow

The deterministic code-health gate (`github.com/ashbywinch/lucidlint`).
Findings carry a fix command; the engine applies structural fixes
deterministically. The fix engine needs `libcst` installed in the running
venv (the engine refuses without it).

## Install

`pip install "git+https://github.com/ashbywinch/lucidlint.git@df20e9238351b7ef84ad822a248d144cf7dbc6c7"` — the
working pip install from the GitHub repo page, pinned to a commit (the
package is not yet on PyPI; once published, `pip install lucidlint` is the
plain form). Re-pin when the package is published or a newer commit is
needed. The pip install gives the `lucidlint` command. If the pip install
does not install everything required, that is a bug in the package — fix
the package, don't document a workaround. `python3 lucidlint.py` in a repo
checkout works without install (its `libcst` need is above).

## The gate

```bash
python3 lucidlint.py --repo . --baseline lucidlint.json     # the gate
python3 lucidlint.py --repo . --json                        # machine-readable
```

The baseline acknowledges known debt; the gate fails on NEW actions only.
Warnings never fail. Repos wrap the invocation in their own make target.

## Acting on a finding — use the fix engine, never hand-implement

The engine is agent-driven; the engine owns its own coordinates — you
do not compute line numbers: pass `--line N` only when the file has multiple findings; omit it when the file has one finding.

For a structural finding (complexity, long-param-list, extract-class,
dispatch-registry, ...):

1. **Preview the seam without a name** — nothing is written:
   ```bash
   lucidlint fix --kind extract-method --file path/to/file.py --line N
   ```
   Read the proposed diff + the seam's first lines.
2. **Judge the seam** — is this the right split? The engine proposes, you
   decide. Wrong → discard the preview (nothing changed).
3. **Apply with the name as the commitment**:
   ```bash
   lucidlint fix --kind extract-method --file path/to/file.py --line N --name _helper --confirm
   ```
4. **Clear dead tails** the move left: `--kind unreachable` (and
   `noop-statement`).
5. Re-run the gate.

The extracted seam is bounded to <=13 decisions (lands under the CC-15
gate) and made private by construction. The exact output is
name-dependent — that is why the preview comes first; never hand-extract
a finding when the engine can show you the seam.

For a mechanical finding, `fix` behavior is **per-kind — and SILENT when it
applies** (verified 0.4.0 probe):

| Kind | What `fix` does |
|---|---|
| `stale-suppression` | **applies** — deletes the stale marker |
| `magic-number --name <CONST>` | **applies** — inserts the constant at module level + rewrites the usage |
| `duplicate-block` | **applies silently, unrecoverable** — judge FIRST: if the parallel structure is intentional, **never run `fix`** (the delete is not recovered) |
| `undeclared-attribute` | **prescribes only** — prints instruction text, edits nothing; hand-annotate |
| `positional-literals` | **prescribes only** — no-op unless `--params` resolves; it mis-binds nested callees (a nested call on the same line gets the outer call's keyword names), so verify any rewrite against the actual call site before acting |

The one-line output reads the same whether it applied or prescribed — you
cannot tell without checking. **Run `git diff` (or hash-check) after every
`fix` invocation.** Never hand-edit a kind the engine applies; never assume
a prescription applied.

## Per-file LSP mode

`python3 lucidlint.py --file <repo-relative>.py` scans ONE file with the
full rule set — use it after every structural edit to catch transient bad
states (duplicate blocks, undefined names, defs mid-import) before they
compound:

```bash
python3 lucidlint.py --file path/to/file.py
```

## Baseline conventions

- `--update-baseline --baseline lucidlint.json` locks today's debt so the
  gate fails only on NEW actions.
- **Never silence a finding without a VALID written justification** —
  the generic rule is in `standards/testing-standards.md` (the canonical;
  in code repos the scaffold copies it to `docs/testing-standards.md`);
  the lucidlint form is `# lucidlint: ignore <kind> <why>` where `<why>`
  must state why THIS occurrence is justified. A config ignore is
  invisible debt and grows silently, and it must carry the same written
  justification (see `standards/testing-standards.md`) — prefer the
  per-site comment, and delete both kinds when the suppression stops
  firing (`stale-suppression`).
- A suppression comment must sit directly above its target; refactoring
  that moves the target orphans the comment, and the `stale-suppression`
  rule catches it — re-run the gate after any move.

## Tool-selection discipline

Structural changes belong in an AST-aware tool, never the line editor
(the rule is in APPEND_SYSTEM.md: "Choose the right tool for the change").
Two lucidlint-specific corollaries: a finding with `fix: <kind>` in its
message means "run the fix", not "hand-implement"; and after every
structural edit, re-run the per-file check on the touched file before the
next edit.
