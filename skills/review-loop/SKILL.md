---
name: review-loop
description: Run a local review of uncommitted changes with the same instructions and context the review bot gets, in a subtask; fix uncontroversial findings, ask the user about the rest one at a time, and iterate until another pass is not worth its tokens. Use before opening a PR, or after a round of changes.
---

# Review Loop

Catch review findings locally — same instructions, same context, same diff
the review bot sees — then fix them, ask about the controversial ones, and
stop when the remaining findings are not worth another pass.

## The instruction source — depend, never copy

The review bot's instructions are two artifacts; the loop reads both at
review time and never copies either:

1. **The upstream review prompt** — `pr_reviewer_prompts.toml` in the
   PR-Agent repo, pinned to the SAME version the repo's review action pins
   (read `.github/workflows/pr-agent.yml` for the tag; fall back to
   `v0.41.1`). Read it via the URL reader:
   `https://raw.githubusercontent.com/The-PR-Agent/pr-agent/<tag>/pr_agent/settings/pr_reviewer_prompts.toml`
   It carries the diff-format spec, the flagging rules (thorough on real
   bugs, certain before flagging lower severity, no speculation, no
   design-choice flagging) and the structured output shape.
2. **The repo's `.pr_agent.toml`** — its `extra_instructions` (the
   per-doc Compliance checks) and `repo_context_files` (PRD, TECHSPEC,
   standards). Read the file; do not restate its content here.

If the pinned prompt is unreachable, proceed with `.pr_agent.toml` alone
and say so — degrade honestly, never vendor a copy.

## The loop

### 1. Prepare the review input

- Diff: `git diff <base>...HEAD` (or the working-tree diff pre-commit)
  plus `git diff --stat`; the changed-file list.
- Context: the repo's `repo_context_files` from `.pr_agent.toml`.
- The subtask prompt carries the diff INLINE (the prompt expects the
  diff as input, not as a file to open).

### 2. Review in a subtask

Spawn ONE read-only subtask (scout or worker — never the agent that wrote
the code, to avoid self-review bias). The subtask receives:

- the inline diff and changed-file list,
- the instruction to read the pinned upstream prompt and the repo's
  `.pr_agent.toml` and `repo_context_files`,
- the output contract: a structured findings list, one item per real
  issue, each with file, start/end line, a 1–2 word header, a concise
  description with the realistic trigger scenario, severity, and a
  confidence note ("confident" vs "high impact, uncertain" — the upstream
  prompt's rule: report uncertain high-impact, skip uncertain low-impact).
  Plus a security section and a note on anything the diff alone cannot
  judge.

Tell the subtask it is READ-ONLY and must apply the upstream prompt's
flagging rules exactly, including its output discipline — no filler, no
design-choice flagging, no speculation without a concrete code path.

### 3. Triage the findings

- **Uncontroversial** (clear defect, mechanical, matches a stated rule):
  fix directly, test-first where behavior changes — never suppress a
  finding, and never "fix" by silencing.
- **Controversial** (design tradeoff, requirement conflict, style the
  prompt forbids flagging): ask the user, ONE issue at a time. Present the
  issue, why the reviewer flagged it, your read of the tradeoff, and 2–3
  concrete options. Wait for the decision before moving on. The user's
  call is recorded (accepted as-is / fixed a given way / dismissed with
  reason) — a dismissed finding is dismissed with a stated reason, not
  silently dropped.

### 4. Loop

After the round of fixes, re-run the review on the delta (step 2 with the
new diff). Stop when the remaining findings are not worth the tokens of
another pass — i.e., only trivial, rare, or already-dismissed-with-reason
issues remain. State the stop condition explicitly: what was fixed, what
the user decided, what remains and why another pass was not worth it.

## Guards

- The subtask reviews; the main agent decides. Never let the subtask edit.
- Test-first for every behavioral fix; a fix that changes behavior without
  a test is a finding itself.
- A finding the prompt itself would not raise (design choice, style) is
  NOT fixed silently — it goes to the user (step 3).
- The loop terminates: an explicit cost-benefit statement closes the last
  pass, never an implicit drift.
