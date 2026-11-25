---
name: pr-loop
description: |
  Drive a PR through review rounds until it is clean: land the code, answer every
  thread on the current head, push once, wait for the next review. Load when a PR
  has findings to answer, or before deciding whether to push again.
---

# The review loop

The reviewer reviews every push. One pass per review, in this order:

1. Land every code change first.
2. Run `pr-threads <pr>`. Answer every thread on the current head.
3. Push once.
4. Run `pr-threads --wait <pr>`. Answer the batch it lists.
5. Push again only when an answer needed a code change.

## Answering a finding

An answer is a change to the code, not an argument about it. A comment that is
right means the code confused its author, and one that is wrong means it
confused the reviewer. Either way the code did not carry the fact. Make it carry
the fact, so the question cannot come back.

- Make it structural first: a name, a type, a branch, one decision function.
- Use a doc line, comment or test only when the code cannot express the fact.

Work in the branch's own worktree. The default checkout may sit on another
branch, so a claim about the code would describe something the PR does not
contain.

A watcher that exits with `NEW THREADS` has work for you now. It never waits for
a thread to be resolved.
