---
name: pr-loop
description: |
  Drive a PR through review rounds until it is clean: land the code, answer every
  thread on the current head, push once, wait for the next review. Load when a PR
  has findings to answer, or before deciding whether to push again.
---

# The review loop

The reviewer reviews every push. One pass per review, in this order:

1. Land every code change first. A deferred acceptance is an open finding.
2. Run `pr-threads <pr>`. Answer every thread on the current head.
3. Push once.
4. Run `pr-threads --wait <pr>`. Answer the batch it lists.
5. Push again only when an answer needed a code change.

`make install` puts `pr-threads`, `pr-ready` and `watch-pr.sh` on PATH.

## Which tool answers which question

- `pr-threads` decides whether a thread is answered. A hand-rolled query or a
  login comparison does not.
- `pr-ready` decides whether the PR is ready (`skill://pr-state`).
- `watch-pr.sh` reports the checks and whether the head is settled. It never
  reports on threads.

`watch-pr.sh` exits with `NEW THREADS` when an answer is owed. Answer it now; it
never waits for a thread to be resolved.

## Where the other rules live

- Answering a finding: refactor, never argue — `skill://pr-workflow` §11b.
- Linking a PR or issue: `skill://pr-workflow` §4.
- Working tree: use the branch's own worktree. A claim about the code comes from
  the branch under review, never the default checkout.
