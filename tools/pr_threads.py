#!/usr/bin/env python3
"""List the review threads on a PR that still need an answer.

    pr-threads <pr> [--repo owner/name] [--me login] [--ids] [--wait]

A thread is answered when its **last** comment is authored by `--me` — not
"the first, plus a reply": a thread I opened has nothing left to answer.
`--me` defaults to `PR_THREADS_ME`, then to `omp-harness[bot]`.

Exit status follows `grep`: 0 no thread is unanswered, 1 some are, 2 the read
failed. `--wait` blocks until the checks on the head have finished, so the
listing is the reviewer's answer rather than a snapshot mid-review. `--ids`
prints only each unanswered thread's id — a debugging view of the key a
watcher de-duplicates on.
"""

from __future__ import annotations

import argparse
import sys
import time

from tools.desk.checks import Checks
from tools.desk.errors import SourceUnknown
from tools.desk.identity import answering_login
from tools.desk.pulls import PullRequests
from tools.desk.repository import Repository
from tools.desk.threads import Threads, unanswered


class _ReviewWait:
    """Block until the checks on the PR's current head have finished."""

    _TIMEOUT_SECONDS = 900
    _POLL_SECONDS = 15
    _GRACE_SECONDS = 90

    def __init__(self, pulls: PullRequests, checks: Checks, number: int) -> None:
        self.pulls = pulls
        self.checks = checks
        self.number = number

    def run(self) -> None:
        started = time.monotonic()
        while time.monotonic() < started + self._TIMEOUT_SECONDS:
            try:
                pull = self.pulls.view(self.number)
                runs = self.checks.on(pull.head)
            except SourceUnknown as exc:
                print(f"pr-threads: {exc} — retrying", file=sys.stderr)
                time.sleep(self._POLL_SECONDS)
                continue
            if not runs:
                # A push creates the check runs a moment later. Waiting a short
                # while is the difference between "no checks configured" and
                # "not here yet".
                if time.monotonic() < started + self._GRACE_SECONDS:
                    time.sleep(self._POLL_SECONDS)
                    continue
                print("warning: no checks reported; listing what has posted", file=sys.stderr)
                return
            if all(run.status == "completed" for run in runs):
                return
            time.sleep(self._POLL_SECONDS)
        print("warning: the review had not finished; listing what has posted", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pr", type=int)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--me", default=None, help="login whose reply answers a thread")
    parser.add_argument(
        "--wait", action="store_true",
        help="wait for the checks on this head before listing",
    )
    parser.add_argument(
        "--ids", action="store_true",
        help="print only each unanswered thread's id, one per line — a debugging "
             "view of the de-duplication key",
    )
    args = parser.parse_args()

    me = args.me or answering_login()
    try:
        repo = args.repo or Repository().current()
        pulls = PullRequests(repo)
        if args.wait:
            pulls.view(args.pr)
            _ReviewWait(pulls, Checks(repo), args.pr).run()
        threads = Threads(repo).all(args.pr)
    except SourceUnknown as exc:
        print(f"pr-threads: {exc}", file=sys.stderr)
        return 2

    pending = unanswered(threads, me)
    if args.ids:
        for thread_id in sorted(thread.id for thread in pending):
            print(thread_id)
        return 1 if pending else 0

    print(f"PR {args.pr} ({repo}): {len(threads)} threads, {len(pending)} unanswered")
    for thread in pending:
        print(f"  UNANSWERED  {thread.path}:{thread.line}  @{thread.last_author}")
    return 1 if pending else 0


if __name__ == "__main__":
    sys.exit(main())
