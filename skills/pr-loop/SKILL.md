---
name: pr-loop
description: |
  Drive a PR through review rounds until it is clean: land the code, answer every
  thread on the current head, push once, wait for the next review. Load when a PR
  has findings to answer, or before deciding whether to push again.
---

# The review loop

A reviewer reviews every push, so a reply-push-reply loop stays one batch behind.
Work in one pass per review.

1. Land every code change before you answer. A change you accepted in a reply
   and then deferred is an open finding.
2. Run `pr-threads <pr>`. Answer every thread on the current head, linking
   each PR or issue as `skill://pr-workflow` §4 requires.
3. Push once.
4. Run `pr-threads --wait <pr>`. Answer the batch it lists.
5. Push again only when an answer needed a code change.

`pr-threads` is the authority on "answered". Neither a hand-rolled query nor a
login comparison is. Run it fresh on the head you describe.

`watch-pr.sh` reports whether the checks are finished and green, and whether the
head is settled. It is not a thread authority.

The watcher exits with `NEW THREADS` when a thread needs an answer. Answer it as
the next action, not a wait: it never waits for a thread to be resolved, because
only the reviewer resolves.

Work in the branch's own worktree. A claim about the code comes from the branch
under review, never the default checkout.
