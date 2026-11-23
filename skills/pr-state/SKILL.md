---
name: pr-state
description: |
  Decide whether a pull request is ready to report — clean merge, current with its
  base, checks green on the head, every thread answered — and say blocked when one
  fails. Load this before saying "ready for approval" or "blocked".
---

# A PR's state

Report a PR's state only after the reviewer has finished: it is a claim about
someone else's next action.

## Always use the script

Run `pr-ready <pr>` and report what it printed. Do not summarise an earlier run:
the user's last message can have changed the answer.

## Four facts, each its own failure

A clean merge, a current base, a green head and answered threads are separate
claims. One failing blocks the PR whatever the others say.

**Behind the base is not ready.** The base is `origin/<base>`, never a local
branch of that name. GitHub reports such a PR `MERGEABLE`, and merging it drops
the base's newer commits — so the diff under review was proved against a base
that has since moved. The fix is the branch's: merge the base in, resolve, push,
then ask again.

## What the script cannot decide

- **Reply to every thread and resolve none.** Only the reviewer resolves. Quote
  the line at the pushed sha — `git show <sha>:<path> | grep -n` — because a
  bullet added in that push moves every anchor below it.
