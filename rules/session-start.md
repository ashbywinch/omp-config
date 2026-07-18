---
description: Check git state at session start — dirty tree, branch safety, never commit to main
---

# Session-Start Git Hygiene

Run this checklist when a new session begins, before taking any user instructions.

## 1. Check for Dirty Working Tree

```bash
git status --porcelain
```

If output is non-empty, inspect what changed:

- **Matches the user's request**: If dirty files are what the user is about to work on (e.g. same module, same feature area), tell the user what was found and that it looks like in-progress work, then ask whether to continue.
- **Unrelated or abandoned**: If dirty files don't relate to the user's request — stale timestamps, temp files, lock files, experiments, or changes in a different area — flag them explicitly and ask the user whether to continue or handle them first.

If the user says continue, proceed. If they say handle, do what they ask — stash, commit, or discard as instructed.

## 2. Branch Safety (main branch)

If the current branch IS `main`/`master`:

- **Dirty tree with content**: Move the changes to a new branch named `wip/<timestamp>` or `work/<topic>` (try to infer a topic from the changed files). `git switch -c <name>` carries uncommitted changes.
- **Clean tree**: Ask the user if they want to create a feature branch, or confirm they really intend to work on `main`.
- Never commit directly to `main`.
