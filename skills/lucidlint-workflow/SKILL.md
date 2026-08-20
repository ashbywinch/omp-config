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

## The gate

```bash
python3 lucidlint.py --repo . --baseline lucidlint.json     # the gate
python3 lucidlint.py --repo . --json                        # machine-readable
```

The baseline acknowledges known debt; the gate fails on NEW actions only.
Warnings never fail. Repos wrap the invocation in their own make target.

## Acting on a finding — use the fix engine, never hand-implement

The engine is agent-driven; R27 means it owns its own coordinates — you
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

For a mechanical finding (magic-number, stale-suppression,
positional-literals): the fix command applies deterministically; run it.

## Per-file LSP mode

`lucidlint.py --file <repo-relative>.py` scans ONE file with the full rule
set — use it after every structural edit to catch transient bad states
(duplicate blocks, undefined names, defs mid-import) before they
compound:

```bash
lucidlint --file path/to/file.py
```

## Baseline conventions

- `--update-baseline --baseline lucidlint.json` locks today's debt so the
  gate fails only on NEW actions.
- Prefer a per-site `# lucidlint: ignore <kind> <why>` over a config
  ignore when a finding is a one-off — config ignores are invisible debt
  and grow silently.
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
