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

@dataclass(frozen=True)
class ThreadPage:
    threads: list[Thread]
    next_cursor: str | None


@dataclass(frozen=True)
class Comment:
    author: str
    body: str

    @classmethod
    def from_json(cls, node: dict) -> "Comment":  # lucidlint: ignore record-shape the GraphQL node is the wire format; converting it is this function's whole job
        """Read one comment off the wire. `author` is null when the account was
        deleted; nobody's login, so it answers to no one — not to me either."""
        author = (node.get("author") or {}).get("login") or ""
        return cls(author, node.get("body") or "")


@dataclass(frozen=True)
class Check:
    """One entry in a PR's statusCheckRollup: a check run, or an older status
    context. They report completion in different fields."""

    kind: str
    status: str | None
    state: str | None

    @classmethod
    def from_json(cls, node: dict) -> "Check":  # lucidlint: ignore record-shape the rollup node is the wire format; converting it is this function's whole job
        return cls(node.get("__typename") or "", node.get("status"), node.get("state"))

    @property
    def finished(self) -> bool:
        if self.kind == "StatusContext":
            return self.state not in (None, "PENDING", "EXPECTED")
        return self.status == "COMPLETED"


@dataclass(frozen=True)
class Thread:
    id: str
    path: str
    line: int | None
    resolved: bool
    comments: tuple[Comment, ...]

    @classmethod
    def from_json(cls, node: dict) -> "Thread":  # lucidlint: ignore record-shape the GraphQL node is the wire format; converting it is this function's whole job
        """Read one thread off the wire. Every field the listing needs is
        required: a thread missing one cannot be reported at all."""
        try:
            comments = tuple(Comment.from_json(c) for c in node["comments"]["nodes"])
            return cls(node["id"], node["path"], node.get("line"), node["isResolved"], comments)
        except (KeyError, TypeError) as exc:
            raise ValueError(f"the thread node is missing {exc}") from exc


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


class _ReviewThreads:
    """The review threads on one repository's PR: the GraphQL documents, and
    the paging over both levels — the threads, then each thread's comments."""

    THREADS = """
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
    COMMENTS = """
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
    ME = "omp-harness"

    def __init__(self, repo: str):
        self.repo = repo
        self.owner, self.name = repo.split("/", 1)

    def fetch(self, pr: int) -> list[Thread]:
        """Every review thread on the PR, with every comment on each."""
        threads: list[Thread] = []
        cursor: str | None = None
        while True:
            page = self._page(pr, cursor)
            threads += page.threads
            if page.next_cursor is None:
                return threads
            cursor = page.next_cursor

    def _page(self, pr: int, cursor: str | None) -> "ThreadPage":
        variables = ["-f", f"owner={self.owner}", "-f", f"repo={self.name}", "-F", f"pr={pr}"]
        if cursor:
            variables += ["-f", f"cursor={cursor}"]
        data = _graphql(self.THREADS, variables)
        try:
            payload = data["data"]["repository"]["pullRequest"]["reviewThreads"]
            nodes, page_info = payload["nodes"], payload["pageInfo"]
        except (KeyError, TypeError):
            sys.exit(f"cannot read PR {pr} in {self.repo}: it does not exist, or this token cannot see it")

        threads: list[Thread] = []
        for node in nodes:
            if not node or "id" not in node:
                # GraphQL returns null for a node the viewer cannot see. Reporting the
                # threads we can see would understate what is open, so stop instead.
                sys.exit(f"cannot see every review thread on PR {pr} — refusing to report a partial list")
            try:
                thread = Thread.from_json(node)
            except ValueError as exc:
                sys.exit(f"cannot read every review thread on PR {pr} ({exc}) — refusing a partial list")
            comments_page = (node.get("comments") or {}).get("pageInfo")
            if comments_page is None:
                # No pageInfo means the comments were not readable; the first page
                # would look like the whole thread, and the last comment decides.
                sys.exit(f"cannot read the comments on thread {thread.id} — refusing a partial answer")
            if comments_page.get("hasNextPage"):
                thread_cursor = comments_page.get("endCursor")
                if not thread_cursor:
                    # More comments exist and the cursor to them is gone: the first
                    # page would stand in for the thread, and the last comment decides.
                    sys.exit(f"cannot page the comments on thread {thread.id} — refusing a partial answer")
                later = self._later_comments(thread.id, thread_cursor)
                thread = replace(thread, comments=thread.comments + tuple(later))
            threads.append(thread)
        if page_info["hasNextPage"]:
            next_cursor = page_info.get("endCursor")
            if not next_cursor:
                sys.exit(f"cannot page the review threads on PR {pr} — refusing a partial answer")
            return ThreadPage(threads, next_cursor)
        return ThreadPage(threads, None)

    def _later_comments(self, thread_id: str, cursor: str) -> list[Comment]:
        """Comments after the first page of a long thread — the last one decides."""
        extra: list[Comment] = []
        while cursor:
            data = _graphql(self.COMMENTS, ["-f", f"id={thread_id}", "-f", f"cursor={cursor}"])
            node = data["data"].get("node")
            if not node:
                sys.exit(f"cannot read the rest of thread {thread_id} — refusing a partial answer")
            page = node.get("comments") or {}
            nodes = page.get("nodes")
            if nodes is None:
                sys.exit(f"cannot read the rest of thread {thread_id} — refusing a partial answer")
            extra += [Comment.from_json(c) for c in nodes]
            page_info = page.get("pageInfo") or {}
            cursor = None
            if page_info.get("hasNextPage"):
                cursor = page_info.get("endCursor")
                if not cursor:
                    sys.exit(f"cannot page thread {thread_id} — refusing a partial answer")
        return extra


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
        # `gh pr checks` has no --json in the gh this runs against (2.46); the
        # rollup on the PR is the same data in a shape every gh 2.x serves.
        out = _gh("pr", "view", str(pr), "--repo", repo, "--json", "statusCheckRollup")
        if out.returncode != 0:
            # A warning then listing anyway would report a state the tool could
            # not observe — the failure this option exists to prevent.
            sys.exit("`gh pr view` failed (%s); cannot wait for the review"
                     % (out.stderr.strip() or out.returncode))
        try:
            rollup = json.loads(out.stdout or "{}").get("statusCheckRollup") or []
        except json.JSONDecodeError as exc:
            sys.exit("`gh pr view` returned something that is not JSON (%s); cannot wait for the review" % exc)
        checks = [Check.from_json(node) for node in rollup]
        if not checks:
            # A push creates the check runs a moment later. Waiting a short while
            # is the difference between "no checks configured" and "not here yet".
            if time.monotonic() < started + grace:
                time.sleep(15)
                continue
            print("warning: no checks reported; listing what has posted", file=sys.stderr)
            return
        if all(check.finished for check in checks):
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
    ap.add_argument("--me", default=_ReviewThreads.ME)
    ap.add_argument("--wait", action="store_true",
                    help="wait for the reviewer to finish on this head before listing")
    args = ap.parse_args()

    repo = args.repo or repo_slug()
    if args.wait:
        wait_for_review(args.pr, repo)
    threads = _ReviewThreads(repo).fetch(args.pr)
    pending = unanswered(threads, args.me)

    print(f"PR {args.pr} ({repo}): {len(threads)} threads, {len(pending)} unanswered")
    for thread in pending:
        first = thread.comments[0]
        body = " ".join(first.body.split())[:100]
        print(f"  UNANSWERED  {thread.path}:{thread.line}  @{first.author}  {body}")
    return 1 if pending else 0


if __name__ == "__main__":
    sys.exit(main())
