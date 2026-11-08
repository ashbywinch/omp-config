#!/usr/bin/env python3
"""List the review threads on a PR that still need an answer.

    pr_threads.py <pr-number> [--repo owner/name] [--me login]

A thread is answered when its **last** comment is authored by `--me` — not "the
first, plus a reply": a thread I opened has nothing left to answer. Everything
unresolved and last-authored by anyone else prints as UNANSWERED, and the exit
status is 1, so a caller can gate on it.

Run it after every push, not before reporting the PR as ready: a reviewer adds
findings one round at a time, a green check says nothing about a thread, and the
one comment you did not read is the one that mattered.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, replace

THREADS_QUERY = """
query($owner: String!, $repo: String!, $pr: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          path
          line
          comments(first: 100) {
            pageInfo { hasNextPage endCursor }
            nodes { author { login } body }
          }
        }
      }
    }
  }
}
"""

COMMENTS_QUERY = """
query($id: ID!, $cursor: String) {
  node(id: $id) {
    ... on PullRequestReviewThread {
      comments(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes { author { login } body }
      }
    }
  }
}
"""

DEFAULT_ME = "omp-harness"


@dataclass(frozen=True)
class ThreadPage:
    threads: list[Thread]
    next_cursor: str | None


@dataclass(frozen=True)
class Comment:
    author: str
    body: str


@dataclass(frozen=True)
class Thread:
    id: str
    path: str
    line: int | None
    resolved: bool
    comments: tuple[Comment, ...]

    @classmethod
    def from_json(cls, node: dict) -> "Thread":  # lucidlint: ignore record-shape the GraphQL node is the wire format; converting it is this function's whole job
        comments = tuple(
            Comment(c["author"]["login"], c["body"]) for c in node["comments"]["nodes"]
        )
        return cls(node["id"], node["path"], node.get("line"), node["isResolved"], comments)


def _gh(*args: str) -> subprocess.CompletedProcess:
    """Run gh, and say so plainly when there is no gh to run."""
    try:
        return subprocess.run(["gh", *args], capture_output=True, text=True)
    except OSError as exc:  # missing, not executable, or blocked
        sys.exit("cannot run gh (%s): this needs the GitHub CLI installed and on PATH" % exc)


def _graphql(query: str, variables: list[str]) -> dict:  # lucidlint: ignore record-shape the response is the wire format; callers convert it straight away
    out = _gh("api", "graphql", "-f", "query=" + query, *variables)
    if out.returncode != 0:
        sys.exit("gh graphql failed: " + out.stderr.strip())
    try:
        payload = json.loads(out.stdout or "{}")
    except json.JSONDecodeError as exc:
        sys.exit("gh returned something that is not JSON: " + str(exc))
    # GraphQL reports refusals in a 200 response: without this, a missing
    # permission reads as a KeyError further down.
    if payload.get("errors"):
        messages = "; ".join(e.get("message", "?") for e in payload["errors"])
        sys.exit("the GitHub API refused the query: " + messages)
    return payload


def _thread_page(pr: int, owner: str, name: str, cursor: str | None) -> "ThreadPage":
    variables = ["-f", f"owner={owner}", "-f", f"repo={name}", "-F", f"pr={pr}"]
    if cursor:
        variables += ["-f", f"cursor={cursor}"]
    data = _graphql(THREADS_QUERY, variables)
    try:
        payload = data["data"]["repository"]["pullRequest"]["reviewThreads"]
        nodes, page_info = payload["nodes"], payload["pageInfo"]
    except (KeyError, TypeError):
        sys.exit(f"cannot read PR {pr} in {owner}/{name}: it does not exist, or this token cannot see it")

    threads: list[Thread] = []
    for node in nodes:
        if not node or "id" not in node:
            # GraphQL returns null for a node the viewer cannot see. Reporting the
            # threads we can see would understate what is open, so stop instead.
            sys.exit(f"cannot see every review thread on PR {pr} — refusing to report a partial list")
        thread = Thread.from_json(node)
        comments_page = (node.get("comments") or {}).get("pageInfo", {})
        if comments_page.get("hasNextPage"):
            later = _later_comments(thread.id, comments_page["endCursor"])
            thread = replace(thread, comments=thread.comments + tuple(later))
        threads.append(thread)
    return ThreadPage(threads, page_info["endCursor"] if page_info["hasNextPage"] else None)


def _later_comments(thread_id: str, cursor: str) -> list[Comment]:
    """Comments after the first page of a long thread — the last one decides."""
    extra: list[Comment] = []
    while cursor:
        data = _graphql(COMMENTS_QUERY, ["-f", f"id={thread_id}", "-f", f"cursor={cursor}"])
        node = data["data"].get("node")
        if not node:
            sys.exit(f"cannot read the rest of thread {thread_id} — refusing a partial answer")
        page = node["comments"]
        extra += [Comment(c["author"]["login"], c["body"]) for c in page["nodes"]]
        cursor = page["pageInfo"]["endCursor"] if page["pageInfo"]["hasNextPage"] else None
    return extra


def fetch(pr: int, repo: str) -> list[Thread]:
    """Every review thread on the PR, with every comment on each."""
    owner, name = repo.split("/", 1)
    threads: list[Thread] = []
    cursor: str | None = None
    while True:
        page = _thread_page(pr, owner, name, cursor)
        threads += page.threads
        if page.next_cursor is None:
            return threads
        cursor = page.next_cursor


def wait_for_review(pr: int, repo: str, timeout: int = 900) -> None:
    """Block until the reviewer has finished on the current head.

    A push starts a review, and it posts minutes later. Reading the threads
    before it finishes reports a clean PR that is about to have findings.
    """
    started = time.monotonic()
    deadline = started + timeout
    # How long to wait for the check runs to appear at all, before deciding there
    # are none configured for this repo.
    grace = 90
    while time.monotonic() < deadline:
        out = _gh("pr", "checks", str(pr), "--repo", repo, "--json", "name,state")
        try:
            checks = json.loads(out.stdout or "[]")
        except json.JSONDecodeError as exc:
            print("warning: could not read the checks (%s); listing what has posted" % exc,
                  file=sys.stderr)
            return
        if not checks:
            if out.returncode != 0:
                print("warning: `gh pr checks` failed (%s); listing what has posted"
                      % (out.stderr.strip() or out.returncode), file=sys.stderr)
                return
            # A push creates the check runs a moment later. Waiting a short while
            # is the difference between "no checks configured" and "not here yet".
            if time.monotonic() < started + grace:
                time.sleep(15)
                continue
            print("warning: no checks reported; listing what has posted", file=sys.stderr)
            return
        # Name the finished states rather than testing for PENDING: QUEUED and
        # IN_PROGRESS are both "not yet", and neither says PENDING.
        finished = {"SUCCESS", "FAILURE", "SKIPPED", "CANCELLED", "NEUTRAL"}
        if all(c["state"] in finished for c in checks):
            return
        time.sleep(15)
    print("warning: the review had not finished; listing what has posted", file=sys.stderr)


def unanswered(threads: list[Thread], me: str) -> list[Thread]:
    """Unresolved threads whose last comment is not mine."""
    return [
        thread for thread in threads
        if not thread.resolved and thread.comments and thread.comments[-1].author != me
    ]


def repo_slug() -> str:
    out = _gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    if out.returncode != 0:
        sys.exit("not in a repo, and no --repo given")
    return out.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", type=int)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--me", default=DEFAULT_ME)
    ap.add_argument("--wait", action="store_true",
                    help="wait for the reviewer to finish on this head before listing")
    args = ap.parse_args()

    repo = args.repo or repo_slug()
    if args.wait:
        wait_for_review(args.pr, repo)
    threads = fetch(args.pr, repo)
    pending = unanswered(threads, args.me)

    print(f"PR {args.pr} ({repo}): {len(threads)} threads, {len(pending)} unanswered")
    for thread in pending:
        first = thread.comments[0]
        body = " ".join(first.body.split())[:100]
        print(f"  UNANSWERED  {thread.path}:{thread.line}  @{first.author}  {body}")
    return 1 if pending else 0


if __name__ == "__main__":
    sys.exit(main())
