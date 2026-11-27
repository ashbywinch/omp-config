"""The review threads on a pull request, and the ones still unanswered."""

from __future__ import annotations

import json
from dataclasses import dataclass

from tools.desk.errors import SourceUnknown
from tools.desk.github import Github
from tools.desk.model import Thread


@dataclass(frozen=True)
class _ThreadPage:
    """One page of review threads, and the cursor to the next page."""

    threads: list[Thread]
    next_cursor: str | None


def unanswered(threads: list[Thread], me: str) -> list[Thread]:
    """Threads still open whose last comment is not mine.

    A thread with no comments has nothing to answer. GraphQL reports a bot's
    login without the ``[bot]`` suffix the REST surface shows, so the comparison
    drops it: ``omp-harness`` and ``omp-harness[bot]`` are one account.
    """
    mine = me.removesuffix("[bot]")
    return [
        thread for thread in threads
        if not thread.resolved
        and thread.last_author is not None
        and thread.last_author.removesuffix("[bot]") != mine
    ]


class Threads(Github):
    """Reads every review thread on one pull request."""

    _THREADS = """
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
          comments(last: 1) {
            nodes { author { login } }
          }
        }
      }
    }
  }
}
"""

    def all(self, number: int) -> list[Thread]:
        """Every thread, with its last author; ``SourceUnknown`` when the list
        cannot be read whole."""
        threads: list[Thread] = []
        cursor: str | None = None
        while True:
            page = self._page(number, cursor)
            threads += page.threads
            if page.next_cursor is None:
                return threads
            cursor = page.next_cursor

    def _page(self, number: int, cursor: str | None) -> _ThreadPage:
        owner, _, name = self.repo.partition("/")
        variables = ["-f", f"owner={owner}", "-f", f"repo={name}", "-F", f"pr={number}"]
        if cursor:
            variables += ["-f", f"cursor={cursor}"]
        out = self.gh(
            ["api", "graphql", "-f", f"query={self._THREADS}", *variables],
            f"cannot read the review threads on {self.repo}#{number}",
        )
        try:
            payload = json.loads(out or "{}")
        except json.JSONDecodeError as exc:
            raise SourceUnknown(
                f"GitHub returned unreadable JSON for {self.repo}#{number}"
            ) from exc
        if not isinstance(payload, dict):
            raise SourceUnknown(
                f"GitHub returned no review threads for {self.repo}#{number}"
            )
        # GraphQL reports refusals in a 200 response: without this, a missing
        # permission reads as a missing thread.
        errors = payload.get("errors")
        if errors:
            messages = "; ".join(
                str(error.get("message", "?")) if isinstance(error, dict) else str(error)
                for error in errors
            )
            raise SourceUnknown(f"the GitHub API refused the query: {messages}")
        try:
            page = payload["data"]["repository"]["pullRequest"]["reviewThreads"]
        except (KeyError, TypeError) as exc:
            raise SourceUnknown(
                f"cannot read PR {number} in {self.repo}: it does not exist, "
                "or this token cannot see it"
            ) from exc
        nodes = page.get("nodes") if isinstance(page, dict) else None
        info = page.get("pageInfo") if isinstance(page, dict) else None
        if not isinstance(nodes, list) or not isinstance(info, dict):
            # A null array is "this token cannot see them", not "there are none".
            raise SourceUnknown(
                f"cannot see every review thread on {self.repo}#{number}"
            )
        threads = [self._thread(number, node) for node in nodes]
        has_next = info.get("hasNextPage")
        if has_next is None:
            raise SourceUnknown(f"cannot page the review threads on {self.repo}#{number}")
        if not has_next:
            return _ThreadPage(threads, None)
        next_cursor = info.get("endCursor")
        if not next_cursor:
            raise SourceUnknown(f"cannot page the review threads on {self.repo}#{number}")
        return _ThreadPage(threads, str(next_cursor))

    def _thread(self, number: int, node: dict) -> Thread:  # lucidlint: ignore record-shape the GraphQL node is the wire format; converting it is this function's job
        """One thread off the wire. A comment the token cannot see is not a
        thread with no comments, so a missing field refuses the page."""
        try:
            comments = node["comments"]
            if comments is None:
                raise KeyError("comments")
            nodes = comments.get("nodes")
            if nodes is None:
                raise KeyError("comments.nodes")
            last_author = (
                str((nodes[-1].get("author") or {}).get("login") or "")
                if nodes else None
            )
            return Thread(
                id=str(node["id"]),
                path=str(node.get("path") or ""),
                line=node.get("line"),
                resolved=bool(node["isResolved"]),
                last_author=last_author,
            )
        except (KeyError, TypeError, IndexError) as exc:
            raise SourceUnknown(
                f"cannot read every review thread on {self.repo}#{number} "
                f"({exc}) — refusing a partial list"
            ) from exc
