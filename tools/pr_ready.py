#!/usr/bin/env python3
"""Prove a PR's state before anyone calls it ready.

    pr-ready <pr> [--repo owner/name] [--root path] [--me login]

Exit status follows `grep`: 0 the PR is ready, 1 it is blocked, 2 the read
failed. `readiness.evaluate` decides from records; this file only gathers them
and prints the verdict.

Procedure: `skill://pr-state`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tools.desk.checks import Checks
from tools.desk.contexts import Contexts
from tools.desk.errors import SourceUnknown
from tools.desk.identity import answering_login
from tools.desk.merge import Merge
from tools.desk.model import PullRequest, Verdict
from tools.desk.pulls import PullRequests
from tools.desk.readiness import evaluate
from tools.desk.repository import Repository
from tools.desk.threads import Threads, unanswered

def next_step(verdict: Verdict) -> str:
    fixes = {
        "head": "push the head, or read the PR again",
        "checks": "run the failing check again, or fix what it reports",
        "merge": "merge the base in and resolve the conflict, then push",
        "threads": "answer every thread the reviewer opened, and resolve none of them",
        "draft": "mark the PR ready for review",
    }
    broken = [fixes[fact.name] for fact in verdict.facts if not fact.ok]
    if not broken:
        return "hand it over: the merge is the user's to make"
    return "blocked — " + "; ".join(broken)


def report(pull: PullRequest, verdict: Verdict) -> str:
    lines = [f"PR {pull.number} ({pull.repo}) @ {pull.head[:12] or 'unknown'}"]
    lines += [
        f"  {fact.name:7} {'ok   ' if fact.ok else 'FAIL '} {fact.detail}"
        for fact in verdict.facts
    ]
    verdict_word = "READY" if verdict.ready else "BLOCKED"
    lines += [f"{verdict_word}: {next_step(verdict)}"]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pr", type=int, help="pull request number")
    parser.add_argument("--repo", default=None, help="owner/name (default: this checkout)")
    parser.add_argument("--root", default=".", help="checkout to prove the merge in")
    parser.add_argument("--me", default=None, help="login whose reply answers a thread")
    args = parser.parse_args()

    me = args.me or answering_login()
    try:
        repo = args.repo or Repository().current()
        pull = PullRequests(repo).view(args.pr)
        threads = unanswered(Threads(repo).all(args.pr), me)
        checks = Checks(repo).on(pull.head)
        contexts = Contexts(repo).required(pull.base)
        merge_state = Merge(repo, root=Path(args.root)).state(pull)
    except SourceUnknown as exc:
        print(f"pr-ready: {exc}", file=sys.stderr)
        return 2

    verdict = evaluate(pull, threads, checks, contexts, merge_state)
    print(report(pull, verdict))
    return 0 if verdict.ready else 1


if __name__ == "__main__":
    sys.exit(main())
