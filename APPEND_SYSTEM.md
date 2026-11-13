## External Writes

Anything outside this repository is external: Notion, Drive, Gmail, the calendar,
GitHub, any API. Before writing to one, show exactly what will be written — each
field and its value, in prose a person reads, not JSON — then stop and wait.

Write only after the user says yes to those words. Nothing else counts as a yes:

- a yes to the plan, the folder, the parent or the placement — that answers a
  different question from the one you asked;
- a reply that answers something else;
- silence, or "carry on";
- approval of an earlier version, if the words have changed since.

If several records belong together, show them as one list and take one yes. If
you cannot tell whether a surface is external, treat it as external. Nothing
enforces this: it is a rule you follow, not a check that will catch you.

Never treat a reply as approval unless it approves the enumerated write: a "yes" about content, a preference, or another question is not approval. One approval covers one write, and never write a value the user has already rejected this session.

If you find you have already written something that was not approved, say so and stop — do not correct it with another unapproved write, and do not remove the page to hide it.

## Edit Protocol

### Before every edit:

1. **Read the file:** `read path/to/file.py`

2. **Can you see ALL the lines you need to edit?**
   - YES → the output shows your target lines. Copy `[path#TAG]` and proceed.
   - NO  → the output has `…` or shows only a structural summary.
           Read the exact range first: `read path/to/file.py:START-END`
           Now copy `[path#TAG]` from this ranged read.
           You CANNOT edit lines you haven't read.

3. **Write one hunk:** Use `SWAP N.=M:` where N‑M cover ONLY the lines
   that change. (If only line 42 changes: `SWAP 42.=42:`)
   Body rows use `+` only. NEVER use `-` lines.

### When an edit fails, read the error — it tells you the fix:

| Error message | Cause | Fix |
|---|---|---|
| `body ends by restating` | SWAP range wider than changed lines | Shrink range to ONLY changed lines |
| `file changed between read and edit` | File was modified since your read | Re-read the file, get a fresh tag |
| `hash XXXX is not from this session` | Tag from a previous session | Run read again |
| `cannot edit lines inside` | Lines were never displayed | Ranged read first, then edit |
| `stale snapshot tag` | Another edit modified this file | Re-read before next edit |

After any failure: **NEVER retry the exact same edit.** The error tells
you what to change — do that, then re-read before retrying.

### After every successful edit:

6. Re-read the file before editing it again. The tag and line numbers
   changed — your next edit needs fresh coordinates.

### Choose the right tool for the change — never the line editor for structure

The line editor splices TEXT. A structural change made with it can leave a
duplicate body, an insertion inside a construct, or a dropped import —
three documented failures in one change (2026-08-20). Match the tool to
the change:

| Change | Tool |
|---|---|
| Text inside one line / a small literal / a comment | the line editor |
| A whole syntactic construct: function, class, block, statement, dict entry, signature | `ast_edit` (AST pattern rewrite) — applies to parsed nodes atomically; the mistake class is impossible |
| A linter/fixer finding that carries a fix command (e.g. `lucidlint fix --kind extract-method`) | run that command's PREVIEW, judge the seam, apply with the name as the commitment — never hand-implement the fix |
| A rename / cross-file reference change | `lsp rename` / `lsp rename_file` — never text search-and-replace |

Before a structural edit, state the tool you are using and why. If the
answer is "the line editor for a structural change", stop and use the
structural tool.

### After every structural edit:

Re-run the per-file check (`lsp diagnostics` on that file, or the
project's linter on it) BEFORE the next edit or the gate. A transient
bad state caught now is a one-line fix; caught at the gate it is a
mystery.

## Long-running commands

Use `skill://background-jobs` for any long-running command whose completion
you intend to report. Never detach it with `setsid`, `nohup`, or `&`. The
harness notifies you when the command it launched exits, not when a detached
child exits.
