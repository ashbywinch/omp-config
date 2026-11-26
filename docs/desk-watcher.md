# The desk watcher

`tools/pr_desk_watch.py` is read alongside this file. Every apparent defect below
is a decision, and the reason is stated so a reader does not have to infer it.

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

## Four notices, each with a key

| Notice | Key | Cleared when |
|---|---|---|
| a comment arrived | the sorted unanswered thread ids | no threads are unanswered |
| a required check failed | the head plus the failing names | no required check has failed |
| the branch is behind its base | the head, once | the head is no longer behind |
| ready for review | the head | the PR stops being ready |

A key is set only after the send succeeds. A failed send therefore repeats next
pass instead of being recorded as delivered.

## "Unknown" is not "clean"

A read that fails is reported on stderr and treated as unknown:

- required contexts unreadable → every check counts, not none;
- check runs unreadable, absent, or not a commit sha → readiness is held;
- `pr-ready` giving no verdict → its last line is printed, not read as "not
  ready yet".

The cheap gate is never more permissive than `pr-ready`, which repeats the
checks as the authority.

## Why the check list is reduced here

`filter=latest` on the check-runs endpoint does not reliably return one run per
name — a reusable workflow's job appears twice in practice. The watcher keeps
the newest run per name itself (`group_by(.name)` then `sort_by(.started_at)`),
so a superseded or in-flight duplicate cannot be judged as the check.

## Why both send streams are captured

`paseo send` writes "agent not found" to whichever stream it chooses. Capturing
both and reporting them together is what keeps that failure visible; `pipefail`
keeps the sender's exit status.
