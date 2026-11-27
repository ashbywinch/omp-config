# The desk's review state

`tools/pr_desk_watch.py` polls one PR and tells its owner what needs doing. This
document states the architecture it follows and the invariants a change keeps.

## Records

Four readers, one concern each. Each holds the repo and the read timeout, and
each returns records.

| Reader | Returns |
|---|---|
| `PullRequests.view(pr)` | `PullRequest`: state, head, base, url, decision, merge_state |
| `Threads.unanswered(pr)` | `Thread` records: id, path, line |
| `Checks.on(head)` | `Check` records: name, status, conclusion, started |
| `Contexts.required(base)` | the required context names of the base |

A reader that cannot get an answer raises `SourceUnknown` with the reason. No
reader returns an empty list or `None` to mean "I could not tell".

## Readiness

`readiness.evaluate(pr, threads, checks, contexts, root)` takes records and
returns a verdict. It reads nothing.

The watcher and `pr-ready` both call it with the records they already hold. They
cannot disagree, and nothing is fetched twice.

## Notices

The watcher emits four notices, each keyed so a steady state sends nothing.

| Notice | Key | Cleared when |
|---|---|---|
| a comment arrived | digest of the unanswered thread ids | no thread is unanswered |
| a required check failed | digest of the head and the failing names | no required check has failed |
| the branch is behind | the head | the head moves |
| ready for review | the head | the head moves |

A key is recorded only after the send succeeds, so a failed send repeats.

## The state file

Keys live at `$XDG_STATE_HOME/omp-config/watch/<owner>/<repo>/<pr>.json`, falling
back to `~/.local/state/`. Each key is a short digest, so the file holds four
strings whatever the PR's size.

- Delete the file when the PR merges or closes.
- Prune files older than seven days at startup.
- Write atomically: a temporary file, then a rename.

**The file records what was said, never what is true.** GitHub wins every
disagreement, and the file is rewritten to match. A stale key that suppresses a
notice costs more than a repeat.

## The command-line tools

`pr-threads`, `pr-ready` and `pr-desk-watch` are displays over the library. Their
text serves the reader and is not an interface.

Exit 0 means the tool answered; non-zero means it failed. "There are unanswered
threads" is an answer and exits 0. Ask `pr-ready` for a gate on readiness.

## What this design refuses

- A client that models GitHub. Each reader takes the fields a notice needs and
  drops the rest.
- A reader that degrades. Unknown is an exception, never an empty list.
- Stored PR facts. The file holds what was said, and nothing else.
