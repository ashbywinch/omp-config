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

## Always give the link

Every PR, issue, commit, run or file you mention is a **link**, with its number
as the text:

- `[#9](https://github.com/ashbywinch/inbox/pull/9)` — not `#9`, and not the bare
  URL either. The number is what a reader recognises; the link is what makes it
  one click.
- A commit: `[a1b2c3d](https://github.com/<owner>/<repo>/commit/<sha>)`.
- A run: `[run 4242](https://github.com/<owner>/<repo>/actions/runs/<id>)`.
- A file outside the repo: its Drive or Notion URL, with the file's name as the
  text.

An unlinked `#9` is unfindable to whoever reads the message next — on a phone, in
a transcript, hours later. A pasted raw URL is findable but ugly, and it pushes
the sentence it belongs to off the screen. Link the number; don't spell the URL
out in prose.

Range links are the exception only when the reader already has the context and
the thing is genuinely unbounded (a search, a filter).

## Part 1: Create the PR

### 1. Change Validation

```bash
git status                                    # must be clean
git fetch origin <base-branch>                # get latest base
git diff <base-branch> --name-only            # every file changed
git log --oneline <base-branch>..HEAD         # every commit
```

Never rely on memory — check the actual diff.

### 1b. Stage only your own files

Use `git add <path>` for each path you edited. In a working tree you share with
other sessions, the catch-all forms are hazards:

- **`git add -A` and `git add .`** stage untracked files too, including another
  agent's work in progress, and put it in your PR under your name.
- **`git commit -a`** stages every *tracked* modification — so it sweeps up
  another session's edits to files you never opened, which is harder to notice
  than a new file appearing in the diff.

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

**Never reference issue/PR numbers (`#N`) in the description unless you
mean a real linked ticket.** PR-Agent's ticket-compliance step latches
onto any `#N` in the body and tries to fetch it as an issue — a bare
mention like "see #51" where #51 is a PR (or an issue that can't be
fetched) crashes the review job with `Error extracting tickets` /
`'NoneType' object has no attribute 'get'` (observed 2026-08-08, houses:
a PR body saying "crashed the run on #51" killed pr-agent's review of
that very PR). Say "the earlier dependabot PR" instead of "#51".

### 4. Create PR

```bash
gh pr create \
  --title "type: description" \
  --body-file pr_description.md \
  --base <base-branch> \
  --head <branch-name>
rm pr_description.md
```

**Updating the description later — never `gh pr edit`** (Projects-classic
deprecation GraphQL error on some orgs); PATCH instead:

```bash
gh api -X PATCH repos/<owner>/<repo>/pulls/<number> --input body.json \
  --jq '.body[0:60]'   # verify the patch applied
```
`body.json` is `{"body": "<description>"}` with newlines escaped as `\n`
(raw newlines break the JSON).

**Never append to the tail of an existing body.** PR-Agent appends its own
boilerplate (`### PR Type`, Description, File Walkthrough) to the description
after each review. A body edit that concatenates text at the end lands BELOW
that boilerplate — and the reviewer's compliance check reads only the
description portion, so the addition is invisible to it. To add anything,
rebuild the description: fetch the current body; if the boilerplate marker
(`___` followed by `### **PR Type**`) is absent (no review has run yet),
PATCH the whole body directly — otherwise split just before the marker,
insert the new text into the description half, rejoin, PATCH the whole body.
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

If the AI review is still running after 10+ minutes with no step-level progress for 5+ minutes, something may actually be stuck. Investigate before cancelling.

**Read the logs from the REST endpoint, not the CLI.** `gh run view <run-id>
--log` prints nothing at all for some runs — re-runs, and jobs that failed
inside a step — while the logs exist and are complete. The endpoint that always
serves them returns a zip:

```bash
curl -sL -H "Authorization: token $(gh auth token)" \
  https://api.github.com/repos/<owner>/<repo>/actions/runs/<run-id>/logs -o logs.zip
unzip -o -q logs.zip -d logs && ls logs     # then read the failing step's file
```

An empty `gh` result is not evidence of a missing log, and never a reason to
conclude "no logs, so I cannot tell why". Say what you found, or fetch the zip
and read it.

### 5a. Never resolve someone else's thread

A review thread belongs to the person who opened it. Resolving it is their
statement that the point is settled — not the author's, and not an agent's.

- **Reply, fix, push.** Then leave it open.
- Resolving hides the reply that came after it and removes the judgement from the
  person who made the point. A thread shows as `outstanding` precisely because
  somebody has not yet agreed it is done.
- Clearing a merge gate is not a reason. If a gate wants resolution, that is the
  reviewer's click to make; an agent that "unblocks" a PR this way has removed
  the only human check in the loop.

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

### 5c. Skipping the AI Review (`/skip`) — only on explicit user request

A human posting `/skip` as a PR comment opts that PR out of the AI review
(supported by the house pr-agent setup: `skip_commands` in `.pr_agent.toml`,
and the check-review step passes on a skip instead of failing with "no
comments posted"). This is a **deliberate opt-out only — do NOT use it on
your own initiative**. Use it only when the user explicitly asks to skip
the review on a specific PR (e.g. a trivial mechanical bump where review
adds nothing, and the user says so). The default is that every PR gets
reviewed; a skipped review is a decision the user makes, not the agent.

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

Findings can come from multiple places. Read **all of them** before deciding
what to fix. One command fetches every source at once — inline PR comments,
issue comments, and review threads — with FULL comment bodies:

```bash
fetch-pr-findings.sh <n>
```

`fetch-pr-findings.sh` is on PATH (installed with this skill by `make
install`). If it is not found, run `make install` in the omp-config repo
first. It fetches all three sources: inline file comments, issue/PR
comments, and review thread comments, never truncated, each with the numeric
id a reply needs. Run it before fixing anything — do not hand-roll the
queries: a `reviewThreads` page or the rendered PR view misses findings, and
a missed finding reads to the user as ignored. If you must query directly,
inline comments are `repos/<owner>/<repo>/pulls/<n>/comments` (numeric `id`
per comment) and unresolved threads are GraphQL `reviewThreads` filtered on
`isResolved == false`.

**CRITICAL: Human reviewers (including the user who opened the PR) may leave
inline comments on specific lines of the changed files. The `pulls/<n>/comments`
endpoint is the ONLY place these appear. If you skip them, you miss the user's
feedback entirely.**

### 7b. Reply to every inline comment

After fixing a finding, **reply to the inline comment that raised it** —
one concise line per comment: how it was fixed, or why you disagree. A
silently-resolved comment leaves the reviewer unsure their feedback was
seen. Reply to a thread with:

**Self-verifying replies only.** A reply must let the reviewer confirm the
disposition without re-deriving it. Fixed: name the commit (sha or message)
AND the exact referent — file:line, config key, or doc section — plus the
one check that confirms it. Disagreed (no change): cite the evidence —
source file:line at the pinned version, a config read path, or a command
and its output — that refutes the claim. A bare `Fixed` or `No` is a
non-reply: it carries no referent, so neither bot nor human can verify it,
and the thread reopens the same question it was meant to close.
Pass the reply body as ONE argument — `-f body="…"` from a script, or
`--input` from a file. A body that travels through shell word-splitting
(`set -- $pair`, unquoted expansion) is split into separate arguments and
truncates to its first word — quote the argument, or write the body to a
file and pass it with `--input`.
```bash
gh api repos/<owner>/<repo>/pulls/<n>/comments/<comment-id>/replies \
  -f body="Fixed in <commit-sha> — <file>:<line> now <what changed>; <the one check that confirms it>." 
```

The comment-id is the numeric `id` from `fetch-pr-findings.sh`'s inline
output (`[id:<n>]`) or `pulls/<n>/comments`. A GraphQL node id (`PRRC_…`)
fails there with `404 Parent comment not found`.
For issue comments (not inline), reply with `gh api
repos/<owner>/<repo>/issues/<n>/comments -f body=...`.

**Never resolve the thread yourself.** Replying is the agent's half of the
cycle; resolution is the reviewer's verdict that the fix answers the finding.
Resolving your own thread erases the reviewer's open question instead of
answering it — reply, push, and leave every thread unresolved.

### 8. Parse AI Review Comments Thoroughly

If the repo has an AI code reviewer (PR-Agent or similar), its review comment contains **multiple distinct sections**. Do NOT rely on counting `<details>` elements — you will miss issues.

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

1. **Wait for the review of this head, then ask what still needs an answer.**
   `pr-threads --wait <pr>` blocks until the reviewer has finished for the
   current head, then lists every thread it prints as UNANSWERED — including one
   you replied to earlier that the reviewer followed up on. A push starts a new
   review, so reading the threads before it lands reports a clean PR that is
   about to have findings; and a non-zero exit means the PR is not ready to
   report, however green the checks are.
2. Re-read the review comments — the persistent review will be updated
3. Confirm the specific finding you fixed is no longer reported
4. Check for ANY new findings that may have been uncovered
5. Repeat until `pr-threads` prints nothing and the review reports "No security
   concerns" and "No major issues/detected"

### 12. Know When to Stop

The AI may keep finding new issues on each round (especially compliance nits). Stop iterating when:

- All **security concerns** are resolved
- All **actual bugs** are fixed
- Remaining findings are stylistic preferences, pre-existing issues, or config self-reviews
- A human reviewer would approve the PR as-is

---

## Part 5: Handing the merge to the user

### 13. The PR carries the version bump; merging it is the release

If the repo releases by version (a semver in a version file, a release branch,
a tag), the bump goes in the PR under review, before it merges: one PR with the
change, its tests, its docs and the version. Merging that PR *is* the release.

- Derive the number from the diff with semver: breaking change → major, new
  capability → minor, fixes only → patch.
- Check the bump is **committed** before you ask for approval: `git diff --stat
  origin/main...HEAD -- <version files>` must show it in the PR's commits —
  a working-tree diff would count an uncommitted bump that never reaches the
  PR. `<version files>` is wherever that stack keeps the version, plus its
  lockfile if it has one — `package.json` and `package-lock.json`, `Cargo.toml`,
  `pyproject.toml`.

---

## Common Pitfalls

The sections above are the how-to; these are the one-line reminders.
- **Fetch the REST zip when `gh run view --log` prints nothing** (§5). Concluding
  "no logs" from an empty `gh` call is how a traceable failure becomes an
  unexplained one.
- **Reading only the `<details>` count** — the review comment has findings
  outside the collapsible sections (security table, compliance links);
  read the full body (§8).
- **A pre-commit hook blocked your commit — never `--no-verify`.** A hook
  that modifies files (a formatter) blocks the commit; the safe recovery
  is to re-stage the hook-modified files and commit again WITH the hook —
  but first verify what the re-stage captured: a blocked commit's
  stash/restore cycle can leave the working tree different from your
  intent, and a blind `git add -A` commits the reverted content silently.
  `--no-verify` also skips the secrets and standards checks. The fix for
  a blocked commit is re-stage + verify the staged diff + re-commit with
  the hook (2026-08-06: a formatter-blocked commit silently shipped a
  reverted fix).
- **Cancelling runs prematurely** — checks take minutes and `updatedAt`
  lags; investigate step-level status before cancelling (§5).
- **Updating a PR description** — never `gh pr edit`, and never append at the
  tail (it lands below the bot's boilerplate, invisible to compliance) —
  rebuild the description half and PATCH the whole body (§4).
- **Pushing without local lint/tests** — each CI cycle costs minutes; run
  the suite locally first (§10).
- **Calling a push done without re-reading the threads** — a green check says
  nothing about a comment. Run `pr-threads <pr>` after every push; the reviewer
  adds findings a round at a time, and the unread one is the one that mattered.
- **Pushing while a review is in flight** — wait-read-fix-push, one push
  per pass (§5b).
- **Resolving review threads yourself** — never; resolution is the reviewer's
  verdict. Reply and stop (§7b).
- **Terse thread replies** (`Fixed` / `No`) — every reply names its
  referent: the commit + file:line (or the evidence that refutes the
  claim). A reply with no checkable referent is a non-reply (§7b).
- **Referencing `#N` in a PR description** — PR-Agent's ticket extractor
  fetches any `#N`; a PR number or unfetchable issue crashes the review
  with `Error extracting tickets` (§3).
- **Posting `/skip` on your own initiative** — the review-skip command is
  a user decision, never the agent's; only use it when the user explicitly
  asks (§5c).
- **Assuming all suggestions are from the current run** — stale
  suggestions accumulate; check the latest PR Reviewer Guide (§7).
- **Fixing AI config suggestions** — `.pr_agent.toml`/workflow
  self-reviews are almost never actionable (§9).
- **Leaving the version out of the PR** — derive it with semver and have it
  staged before asking for approval, so the merge is the release (§13).
- **Deleting a branch a workflow references** — never. Before deleting any
  branch, grep `.github/workflows/` for its name. `pr-agent-config`'s role
  and its two false-stale signals are stated in the workflow that pins
  it — read that comment before auditing branches.

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
