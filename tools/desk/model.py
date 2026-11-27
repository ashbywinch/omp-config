"""The records a notice or a verdict reads.

Raw GitHub payloads never reach these types: a reader converts the wire format
at its own boundary, and everything downstream sees only these fields.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PullRequest:  # lucidlint: ignore class-module the desk architecture names model.py for the notice and verdict records; they are one record set with one reason to change.
    """One pull request, as far as a notice or a verdict needs it."""

    number: int
    repo: str
    state: str
    head: str
    base: str
    url: str
    decision: str
    merge_state: str

    @property
    def slug(self) -> str:
        return f"{self.repo}#{self.number}"

    @property
    def finished(self) -> bool:
        return self.state in ("MERGED", "CLOSED")

    @property
    def behind(self) -> bool:
        return self.merge_state == "BEHIND"


@dataclass(frozen=True)
class Thread:
    """One review thread, as far as "is it answered" needs it.

    ``last_author`` is ``None`` for a thread with no comments: nothing was
    said, so there is nothing to answer.
    """

    id: str
    path: str
    line: int | None
    resolved: bool
    last_author: str | None


@dataclass(frozen=True)
class Check:
    """One check run on a head, as far as a verdict needs it."""

    name: str
    status: str
    conclusion: str | None
    started: str

    @property
    def passed(self) -> bool:
        return self.status == "completed" and self.conclusion == "success"

    @property
    def failed(self) -> bool:
        """A conclusion that names something to fix."""
        return self.conclusion in {
            "failure", "timed_out", "action_required", "startup_failure"
        }


@dataclass(frozen=True)
class MergeState:
    """Whether a head merges into its base, and whether it is behind it."""

    merges: bool
    behind: bool
