#!/usr/bin/env python3
"""List the review threads on a PR that still need an answer.

    pr_threads.py <pr-number> [--repo owner/name] [--me login]

A thread is answered when a comment after the first is authored by `--me`.
Everything unresolved and last-authored by anyone else prints as UNANSWERED, and
the exit status is 1, so a caller can gate on it.

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
    except FileNotFoundError:
        sys.exit("gh is not installed, or not on PATH: this needs the GitHub CLI")


def _graphql(query: str, variables: list[str]) -> dict:  # lucidlint: ignore record-shape the response is the wire format; callers convert it straight away
    out = _gh("api", "graphql", "-f", "query=" + query, *variables)
    if out.returncode != 0:
        sys.exit("gh graphql failed: " + out.stderr.strip())
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError as exc:
        sys.exit("gh returned something that is not JSON: " + str(exc))


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
        thread = Thread.from_json(node)
        if node["comments"]["pageInfo"]["hasNextPage"]:
            later = _later_comments(thread.id, node["comments"]["pageInfo"]["endCursor"])
            thread = replace(thread, comments=thread.comments + tuple(later))
        threads.append(thread)
    return ThreadPage(threads, page_info["endCursor"] if page_info["hasNextPage"] else None)


def _later_comments(thread_id: str, cursor: str) -> list[Comment]:
    """Comments after the first page of a long thread — the last one decides."""
    extra: list[Comment] = []
    while cursor:
        data = _graphql(COMMENTS_QUERY, ["-f", f"id={thread_id}", "-f", f"cursor={cursor}"])
        page = data["data"]["node"]["comments"]
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
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        out = _gh("pr", "checks", str(pr), "--repo", repo, "--json", "name,state")
        try:
            checks = json.loads(out.stdout or "[]")
        except json.JSONDecodeError:
            return
        reviewing = [c for c in checks if "review" in c["name"].lower()]
        if reviewing and all(c["state"] != "PENDING" for c in reviewing):
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
