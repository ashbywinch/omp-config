# The desk watcher

`tools/pr_desk_watch.py` and `tools/desk/` are read alongside this file. Every
apparent defect below is a decision, and the reason is stated so a reader does
not have to infer it.

## It reports, it never acts

The watcher sends messages. It never approves, resolves a thread, pushes, or
merges. The approval is the person's, and resolving is the reviewer's.

## One recipient

`PR_DESK_AGENT` names the session that owns the PR: this repo's own agent when
the PR is part of its work, or the desk when the work must not interrupt it.
Every message goes there, because that session is also the person's channel.

`PASEO_AGENT_ID` is never used as a default. A spawned session inherits its
parent's value, so a default would post a worker's notices to whatever spawned
it.

## Every read is a reader

The GitHub reads live in `tools/desk/`, one class per concern: `PullRequests`,
`Threads`, `Checks`, `Contexts`, `Merge`, and `Repository` for the checkout's
name. A reader raises `SourceUnknown` when it has no answer; an empty list is an
answer ("no threads", "no check runs", "nothing required"). The watcher warns on
stderr and holds that notice for the pass, so a failed read never reads as
clean:

| Read | When it cannot answer |
|---|---|
| the pull | nothing is announced this pass |
| required contexts | every check counts for the check notice; readiness is held |
| check runs | the check notice and readiness are held |
| review threads | the thread notice and readiness are held |
| the merge | `UNKNOWN` is proved with `git fetch` and `git merge-tree`; when that cannot answer, readiness is held |

## Four notices, each with a key

| Notice | Key | Cleared when |
|---|---|---|
| a comment arrived | the sorted unanswered thread ids | no thread is unanswered |
| a required check failed | the head plus the failing names | no required check has failed |
| the branch is behind its base | the head | the head is not behind |
| ready for review | the head | the PR stops being ready |

Approval is a fact, not a mute. The three attention notices fire whether or not
the PR is approved. The ready notice fires for a clean PR either way: unapproved
says "ready for the person's review, relay it"; approved says "approved and
clean, nothing outstanding".

A key is recorded only after the send succeeds, so a failed send repeats next
pass instead of being recorded as delivered. The send is `paseo send --no-wait`:
without the flag it waits for the recipient's turn, and a slow turn reads as a
failed send.

## The state file

`NoticeLog` owns `$XDG_STATE_HOME/omp-config/watch/<owner>/<repo>/<pr>.json`,
falling back to `~/.local/state/`. Nothing else touches it.

- Keys are stored exactly — the head, the sorted thread ids, the head plus the
  failing names — never digested, so a person can read why nothing was sent.
- An empty string means "owed".
- The file is written atomically: a temporary file, then a rename.
- The pass that sees the PR merged or closed deletes it.
- Files older than seven days are pruned at startup.

The file records what was said, never what is true. GitHub wins every
disagreement, and the file is rewritten to match: a stale key that suppresses a
notice costs more than a repeat.

## Readiness is a pure function

`readiness.evaluate(pull, threads, checks, contexts, merge_state)` reads
nothing. The watcher and `pr-ready` call it over the records they read, so they
cannot disagree and no pass reads the same fact twice. A PR is ready when:

1. The head is a commit sha.
2. Every required context is completed and passing. A required context with no
   run blocks; an empty required list passes.
3. The head merges into its base: no conflict, and not behind it. `BLOCKED` is
   accepted, because the gate it reports is the approval being asked for.
4. No thread is unanswered — `threads.unanswered(threads, me)`, where `me` is
   `PR_THREADS_ME` or the `omp-harness[bot]` default. GraphQL reports the bot's
   login without the `[bot]` suffix, and the comparison treats the two as one
   account.
5. The PR is not a draft.

A passing check is completed and not one of `failure`, `timed_out`,
`cancelled`, `action_required`, `startup_failure` — the merge gate's own list,
so the notice and the merger agree.

## The tools exit like grep

`pr-ready` and `pr-threads` are displays over the library. Exit 0 means the
condition holds (READY, no unanswered thread), 1 means it does not (BLOCKED,
threads to answer), and 2 or above means the tool failed. The watcher calls the
library's functions, never these tools' exit codes.

## Why the check list is reduced in the reader

`filter=latest` on the check-runs endpoint does not reliably return one run per
name — a reusable workflow's job appears twice in practice. `Checks.on` keeps
the newest run per name itself (`latest_by_name`), so a superseded or in-flight
duplicate cannot be judged as the check.

## Why both send streams are captured

`paseo send` writes "agent not found" to whichever stream it chooses. The
watcher captures both and reports them together, so that failure stays visible;
a failed send leaves its key unwritten and repeats.
