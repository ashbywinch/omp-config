---
name: pr-workflow
description: |
  GitHub Pull Request creation and post-creation handling — validate changes,
  create PR description, monitor checks, triage findings from any reviewer
  (AI or human), iterate.
---

# GitHub Pull Request Workflow

Create PRs and handle the review cycle end-to-end. Works for any repo,
with or without automated AI code review.

## Prerequisites

- `gh` CLI installed and authenticated
- All work committed on a feature branch (not default branch)
- Local branch is up to date with base branch

---

## Part 1: Create the PR

### 1. Change Validation

```bash
git status                                    # must be clean
git fetch origin <base-branch>                # get latest base
git diff <base-branch> --name-only            # every file changed
git log --oneline <base-branch>..HEAD         # every commit
```

Never rely on memory — check the actual diff.

### 2. Push Feature Branch

```bash
git branch                     # confirm not on base branch
git push -u origin <branch-name>
```

### 3. Create PR Description

Create a `pr_description.md` with:
- **Theme** — one-line summary of what the PR achieves
- **Key changes** — grouped by file or concern
- **Risk areas** — what to pay attention to in review
- **Testing** — what was verified and how

### 4. Create PR

```bash
gh pr create \
  --title "type: description" \
  --body-file pr_description.md \
  --base <base-branch> \
  --head <branch-name>
rm pr_description.md
```

---

## Part 2: Post-Creation — Monitor Checks

### 5. Wait for Checks to Complete

CI usually takes 1-3 minutes. If AI code review is configured, it takes 3-5 minutes (longer for large PRs).

**Never cancel a running check.**
A run that appears stuck may still be progressing. The GitHub API's `updatedAt` field can lag behind actual progress — treat it as a loose indicator, not a reliable heartbeat.

To check real progress without cancelling:

```bash
# List check statuses — poll every 30s
gh pr view <number> --json statusCheckRollup \
  --jq '.statusCheckRollup[] | "\(.workflowName): \(.status) \(.conclusion)"'

# If you need finer detail, inspect step-level jobs for a specific run
gh api repos/<owner>/<repo>/actions/runs/<run-id>/jobs \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(f'{s[\"name\"]}: {s[\"status\"]}') for j in d['jobs'] for s in j['steps']]"
```

If the AI review is still running after 10+ minutes with no step-level progress for 5+ minutes, something may actually be stuck — but investigate before cancelling:

```bash
# Try to peek at partial logs (may not be available until run completes)
gh run view <run-id> --log 2>&1 | head -30
```

### 5b. Never Push While a Review Is in Flight

A push re-triggers the AI review (`synchronize`). Pushing mid-run discards the
in-flight run's review — a full generation already burned — and splits the
review of its findings from the review of your fixes.

The loop, one push per pass:

1. Push once, then **wait for the run to finish** (poll step-level status).
2. Read the review it posts — it will probably have comments.
3. Fix those findings **together with your local changes**, run lint + tests,
   commit once.
4. Push once — the next review covers the whole change in one pass.

Never push while a pr-review check is in flight: every push costs a full
review generation, so batch fixes.

### 6. When Checks Fail

CI failures:

```bash
# Get failure details
gh run view <run-id> --log 2>&1 | grep -E "FAILED|Error:|error:" | head -20
```

- **Lint failure** — fix locally with `ruff check --fix .`, never guess
- **Test failure** — read the error message, reproduce locally
- Fix locally, run the full suite, push

---

## Part 3: Read and Triage All Findings (AI or Human)

### 7. Collect All Sources of Findings

Findings can come from multiple places. Read **all of them** before deciding what to fix:

| Source | How to access |
|---|---|
| PR review comments (AI)| `gh api repos/<owner>/<repo>/issues/<number>/comments` — filter for bot user |
| PR review thread (human) | `gh pr view <number> --comments` |
| Inline PR review comments | `gh api repos/<owner>/<repo>/pulls/<number>/comments` |

### 8. Parse AI Review Comments Thoroughly

If the repo has an AI code reviewer (PR-Agent or similar), its review comment contains **multiple distinct sections**. Do NOT rely on counting `<details>` elements — you will miss issues.

The typical AI review comment has these sections, all of which can contain findings:

| Section | Location in comment | How it reports issues |
|---|---|---|
| **Security concerns** | Table row with 🔒 icon | Inline text AND/OR `<details>` elements |
| **Recommended focus areas** | Table row with ⚡ icon | `<details>` elements (one per finding) |
| **Compliance: Coding Standards** | Below the table as a link | Text: "Violations found" or "No violations" |
| **Compliance: Testing Standards** | Below the table as a link | Text: "Violations found" or "No violations" |
| **Compliance: Documentation Standards** | Below the table as a link | Text: "Violations found" or "No violations" |

**To get all findings, extract the full comment body and look at every section, not just the `<details>` tags.**

```python
# This regex catches ALL finding types:
import re
body = ...  # the full comment body

# 1. Security concerns (may have text outside <details>)
security_match = re.search(r'🔒.*?</td>', body, re.DOTALL)

# 2. Focus area findings (inside <details><summary>)
focus_findings = re.findall(r'<details><summary>(.*?)</summary>', body)

# 3. Compliance lines (below the table, not in <details>)
compliance = re.findall(r'Compliance:.*?<br>(.*?)(?=\n|$)', body)

# 4. ANY text mentioning "security concern", "violation", "issue" in the body
all_issue_text = re.findall(r'(?:violation|issue|concern|suggestion)[^.]*\.', body, re.I)

# 5. Print the FULL body to inspect manually
print(body)
```

**The `re.findall(r'<summary>(.*?)</summary>', body)` approach is NOT sufficient** — it misses security concerns reported as plain text, compliance violations listed outside `<details>`, and any other non-collapsible sections.

**Always print/save the full comment body and read it yourself.** Do not rely on summary extraction.

### 9. Triage Each Finding

For each finding, classify it:

| Finding | Action |
|---|---|
| Security vulnerability | Fix — highest priority |
| Standards violation (coding, testing, docs) | Fix — align with project conventions |
| Self-referential config issue | Ignore — AI reviewing its own config/workflow |
| Pre-existing issue in unchanged code | Fix if quick; otherwise note for follow-up |
| Design preference, style nit, hypothetical risk | Assess severity — most are ignorable |
| Bug in the diff (logic error, race condition) | Fix |

**Fix all actionable findings in the same session.** If you defer any, track them explicitly.

---

## Part 4: Iterate

### 10. Fix, Commit, Push

```bash
# 1. Fix the issue
# 2. Run lint AND tests before pushing
cd <repo-root>
ruff check .                          # lint
pytest -x                             # tests (or specific test file)
# 3. Commit and push
git add -A
git commit -m "type: description of fix"
git push origin <branch>
```

**Always run lint and tests locally before pushing.** CI takes minutes per cycle. Broken pushes waste time.

### 11. Verify Next Round

After push, checks trigger again automatically (if configured). Wait for completion, then:

1. Re-read the review comments — the persistent review will be updated
2. Confirm the specific finding you fixed is no longer reported
3. Check for ANY new findings that may have been uncovered
4. Repeat until the review reports "No security concerns" and "No major issues/detected"

### 12. Know When to Stop

The AI may keep finding new issues on each round (especially compliance nits). Stop iterating when:

- All **security concerns** are resolved
- All **actual bugs** are fixed
- Remaining findings are stylistic preferences, pre-existing issues, or config self-reviews
- A human reviewer would approve the PR as-is

---

## Common Pitfalls

### Reading only the `<details>` count
The review comment has multiple sections beyond the collapsible `<details>` elements. Security concerns, compliance violations, and other text may appear in the table rows or as standalone links. Always read the **full body** of the review comment, not just extracted summaries.

### Cancelling runs prematurely
Checks take 3-5+ minutes. The GitHub API `updatedAt` can lag. Never cancel without investigating via step-level job status first. A run that shows no progress for 5+ minutes at the step level may still be completing model inference.

### Pushing without local lint/tests
Each CI cycle is 3-5 minutes. A lint error wastes that entire cycle. Always run `ruff check .` and `pytest -x` locally.

### Pushing while a review is in flight
Never push mid-run — the wait-read-fix-push loop is in §5b.

### Assuming all suggestions are from the current run
PR Code Suggestions accumulate across multiple runs and may contain stale suggestions. Always check the PR Reviewer Guide for the current assessment — it's updated on each push.

### Fixing AI config suggestions
The AI will suggest changes to `.pr_agent.toml`, review workflow files, and its own configuration. These are almost never actionable — the config is already working. Focus on code changes.

---

## Constraints

- CAN create PRs, add comments, request reviews
- CANNOT approve or merge PRs
- CANNOT override branch protection rules

## Success Criteria

- PR description captures all changes with context
- All CI checks pass
- All actionable reviewer findings are fixed in the same session
- No dead code, backward compatibility shims, or swallowed exceptions
- Agent does NOT need a follow-up session to address review feedback
