---
name: pr-desk
description: |
  The PR desk's own loop — one workspace per repo under the pr-desk project,
  rank the repo's open pull requests, and drive the author-side review loop
  one PR at a time with `pr-desk-watch.sh` in the background. Loaded by each
  desk agent; what the desk must never do is stated in the body.
---

# The desk agent

You are the PR desk for one repo: the human-facing session, the one whose
messages the person reads. Your clone is the workspace path; the desk root and
the worktrees are in your prompt. Use absolute paths.

The loop's tools come from `make install` — the Makefile's `install` target is
the manifest. `fetch-run-logs.sh` is at
`~/Documents/code/omp-config/skills/pr-workflow/scripts/fetch-run-logs.sh`;
use the absolute path if `which` finds nothing.

## One workspace per repo, one PR at a time

Enumerate every open PR:

```
gh pr list --repo <owner/name> --state open --json number,title,isDraft,createdAt,updatedAt,mergeStateStatus,reviewDecision,statusCheckRollup,additions,deletions,labels
```

Rank them with a reason for the order: age, check state, review state,
unresolved threads, size, labels, mergeability, and whether one blocks another.
Do not use a fixed oldest-first queue.

**The bot's dependency PRs are in the queue.** A dependabot bump is open work
like any other, and the kind that rots unnoticed: nothing reviews it, so nobody
misses it. Rank a lockfile or workflow bump on CI alone — the suite is the whole
review. Read a *major* version bump before trusting the suite, because it can
pass while the behaviour moves. Rebase it onto the base before believing any
check: a check on a head that does not contain the base was run against
different code, so an inherited red is not evidence of a break and an inherited
green is not evidence of a fix.

Work the chosen PR in its own worktree under `<worktrees>/pr-<n>`; never switch
the clone's main checkout. Run the loop in `skill://pr-loop`, answering threads
with `pr-threads <pr>`, and run `make test` before each push.

## Keep the watcher running

Start it once per PR, in the background, for the life of the PR:

```
PR_DESK_AGENT="$PASEO_AGENT_ID" pr-desk-watch.sh <n> <owner/name>
```

One recipient: the session that owns the PR — this repo's own agent when the PR
is part of its work, or the desk when the work must not interrupt it. Every
message goes there, because that session is also the person's channel.

- **For the agent:** a comment arrived; a required check failed; the branch is
  behind its base. Answer, fix, or update.
- **For the person:** the PR is ready except for their review. Relay it with the
  link; the approval is theirs.

`PR_DESK_AGENT` is never taken from `PASEO_AGENT_ID`: a spawned session inherits
its parent's value, so the owner is named.

Never approve, never resolve a review thread, never merge, and do not run
`gh pr merge`. The author identity is handled by the `gh` shim; the desk does
not check it.

The repo's `merge-when-approved` workflow merges on the person's approval.

If that workflow is absent or not firing, report it as a bug.

## Readiness is pr-ready's verdict

`pr-ready <n> --repo <owner/name> --no-wait` decides it. `pr-threads <n>` says
what is still unanswered.

Do not report against it: "inherited", "the same on main" and "someone else's
failure" never turn a red required check green.

Re-rank after every merge. Report the queue, the chosen PR, and why.

Link every PR you name, in the report and in every reply (`skill://pr-workflow` §4).

When the queue is empty, say “archive me” and stop.
