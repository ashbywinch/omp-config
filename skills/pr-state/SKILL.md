---
name: pr-state
description: |
  Never say a PR is "ready for approval" or "blocked" without running
  `pr-ready` first and reporting what it printed.
---

# A PR's state

Report a PR's state only after the reviewer has finished: it is a claim about
someone else's next action.

## Always use the script

Run `pr-threads --wait <pr>` first: it blocks until the reviewer has finished
the current head, so the state is a settled one. Then run `pr-ready <pr>` and
report what it printed. Do not summarise an earlier run: the user's last
message can have changed the answer.

Both tools exit like `grep`: 0 the condition holds (no unanswered thread;
READY), 1 it does not (threads to answer; BLOCKED), 2 the read failed, 3 the PR
is merged or closed. Treat a 2 as a retry — never report it as blocked or clean.

A merged or closed PR is named in one line and exits 3, because it is finished
rather than blocked: its head is behind its base by definition, so printing the
five facts would report a defect that is not one, and a caller reading the code
alone must be able to tell the two apart.

## Five facts, each its own failure

A head that is a commit, required checks green, a merge that is clean and
current, answered threads and a non-draft PR are separate claims. One failing
blocks the PR whatever the others say. An empty required-check list passes: no
check was asked for.

**Behind the base is not ready.** The base is `origin/<base>`, never a local
branch of that name. A PR behind its base is not ready: merging it drops the
base's newer commits. The fix is the branch's: merge the base in, resolve, push,
then ask again.

## What the script cannot decide

- **Reply to every thread and resolve none.** Only the reviewer resolves. Quote
  the line at the pushed sha — `git show <sha>:<path> | grep -n` — because a
  bullet added in that push moves every anchor below it.
