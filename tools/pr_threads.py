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

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass

QUERY = """
query($owner: String!, $repo: String!, $pr: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $pr) {
      reviewThreads(first: 100, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          isResolved
          path
          line
          comments(first: 20) {
            pageInfo { hasNextPage }
            nodes { author { login } body }
          }
        }
      }
    }
  }
}
"""

DEFAULT_ME = "omp-harness"


@dataclass(frozen=True)
class Comment:
    author: str
    body: str


@dataclass(frozen=True)
class Thread:
    path: str
    line: int | None
    resolved: bool
    comments: tuple[Comment, ...]

    @classmethod
    def from_json(cls, node: dict) -> "Thread":  # lucidlint: ignore record-shape the GraphQL node is the wire format; converting it is this function's whole job
        comments = tuple(
            Comment(c["author"]["login"], c["body"]) for c in node["comments"]["nodes"]
        )
        return cls(node["path"], node.get("line"), node["isResolved"], comments)


def unanswered(threads: list[Thread], me: str) -> list[Thread]:
    """Unresolved threads whose last comment is not mine."""
    return [
        thread for thread in threads
        if not thread.resolved and thread.comments and thread.comments[-1].author != me
    ]


def _page(pr: int, owner: str, name: str, cursor: str | None) -> dict:
    args = ["gh", "api", "graphql", "-f", "query=" + QUERY,
            "-f", f"owner={owner}", "-f", f"repo={name}", "-F", f"pr={pr}"]
    if cursor:
        args += ["-f", f"cursor={cursor}"]
    out = subprocess.run(args, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("gh graphql failed: " + out.stderr.strip())
    return json.loads(out.stdout)["data"]["repository"]["pullRequest"]["reviewThreads"]


def fetch(pr: int, repo: str) -> list[Thread]:
    """Every review thread on the PR, not the first page of them."""
    owner, name = repo.split("/", 1)
    threads: list[Thread] = []
    cursor = None
    while True:
        page = _page(pr, owner, name, cursor)
        for node in page["nodes"]:
            if node["comments"]["pageInfo"]["hasNextPage"]:
                sys.exit(f"thread on {node['path']} has more comments than one page; raise the 20")
            threads.append(Thread.from_json(node))
        if not page["pageInfo"]["hasNextPage"]:
            return threads
        cursor = page["pageInfo"]["endCursor"]


def repo_slug() -> str:
    out = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit("not in a repo, and no --repo given")
    return out.stdout.strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", type=int)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--me", default=DEFAULT_ME)
    args = ap.parse_args()

    repo = args.repo or repo_slug()
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
