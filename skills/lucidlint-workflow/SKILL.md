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

`pip install "git+https://github.com/ashbywinch/lucidlint.git@v0.8.0"`
— the install from the GitHub repo page, pinned to the v0.8.0 tag (the
package is not on PyPI). It provides the `lucidlint` command. Re-pin when a
newer release lands. An incomplete install is a package bug to fix there, not
something to work around here.

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

The extracted seam stays under the CC-15 gate (<=13 decisions) and is private
by construction. Its exact output depends on the name you choose, which is why
the preview comes first: never hand-extract a finding the engine can show you.

### What `fix` prints

The build announces one of three outcomes; there is no sideband to check.

- **applied** — `fix: applied <kind> at <file>:<line> — <description>`. The
  edit landed. `duplicate-block` has no engine undo, so judge it before
  running: an intentional parallel structure must never be fixed.
- **needs input** — the fix is real but needs a parameter: `--name` for
  semantic names, `--params entries` for callees it cannot resolve. Retrying
  with the parameter is still an auto-fix. For `positional-literals`, check
  the rewrite against the call site: nested same-line calls can mis-bind.
- **silence** — no finding of that kind remains. Move on.

An `applied` line can carry a prefix: when the finding's anchor moved, the tool
prints `anchor moved — <kind> now at <file>:<line>` above it and writes at the
finding's current coordinates.

To undo an applied write, `git restore <file>` works only before that file is
committed — run `git status` first, and never discard unrelated uncommitted
work.

## Per-file LSP mode

`python3 lucidlint.py --file <repo-relative>.py` scans ONE file with the
full rule set — use it after every structural edit to catch transient bad
states (duplicate blocks, undefined names, defs mid-import) before they
compound:

```bash
python3 lucidlint.py --file path/to/file.py
```

## When the gate fails with no findings

`make lucidlint` exits above 1 while printing no action list when the scanner
itself failed — a crash or a bad flag.

Read the reason in the stderr file the Makefile writes, `lucidlint-dist/.last.err`.

**A corrupt baseline does not fail the gate.** The loader logs `baseline <path>
unreadable — ignoring`, then runs with an empty baseline: no keys, empty ledger.
`[]`, `{}`, a truncated file and a missing file are all accepted, and the run
still exits 0. It also prints `config-ignored '<rule>' grew 0 -> N` for every
rule the missing ledger cannot compare. Treat those lines as warnings, never as
the failure. Restore the file with `--update-baseline --baseline lucidlint.json`.
That command writes `{actions, config_ignored}`, so read what the new baseline
acknowledges. Then trace the crash, not the file.

Under the pre-commit hook the tree is transient: the hook stashes unstaged
changes, runs, then restores them, so a scan can read a half-applied edit. Rule
that out before blaming the baseline: re-run `make lucidlint` on a clean tree.

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
