---
name: pr-state
description: |
  Decide whether a pull request is ready to report — clean merge, checks green on
  the head, every thread answered — and say blocked when one fails. Load this
  before saying "ready for approval" or "blocked".
---

# A PR's state

Report a PR's state only after the reviewer has finished: it is a claim about
someone else's next action.

## Always use the script

Run `pr-ready <pr>` and report what it printed. Do not summarise an earlier run:
the user's last message can have changed the answer.

## What the script cannot decide

- **Reply to every thread and resolve none.** Only the reviewer resolves. Quote
  the line at the pushed sha — `git show <sha>:<path> | grep -n` — because a
  bullet added in that push moves every anchor below it.
