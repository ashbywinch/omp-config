"""The records a notice or a verdict reads.

Raw GitHub payloads never reach these types: a reader converts the wire format
at its own boundary, and everything downstream sees only these fields.
"""

from __future__ import annotations

from dataclasses import dataclass

def absent(value: str) -> bool:
    """Whether a text field is missing.

    A reader writes ``-`` for a field GitHub did not answer with, so this is
    the one place that spelling is interpreted.
    """
    return not value or value == "-"


@dataclass(frozen=True)
class PullRequest:
    """One pull request, as far as a notice or a verdict needs it."""

    number: int
    repo: str
    state: str
    head: str
    base: str
    url: str
    decision: str
    merge_state: str
    draft: bool

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

    # The merge gate's own failing list: a conclusion here is a check to fix.
    _FAILING = frozenset({
        "failure", "timed_out", "cancelled", "action_required", "startup_failure"
    })

    @property
    def passed(self) -> bool:
        """Completed, and not one of the conclusions that name a fault."""
        return self.status == "completed" and self.conclusion not in self._FAILING

    @property
    def failed(self) -> bool:
        """A conclusion that names something to fix."""
        return self.conclusion in self._FAILING


@dataclass(frozen=True)
class MergeState:
    """Whether a head merges into its base, which base, and whether it is behind."""

    base: str
    merges: bool
    behind: bool

    def __post_init__(self) -> None:
        if absent(self.base):
            raise ValueError("a merge state names the base it was proved against")


@dataclass(frozen=True)
class Reading:
    """Everything a verdict is decided on, as one set.

    The fields are not optional: a read that could not answer raises
    `SourceUnknown`, so a caller either has a complete set of records or has
    nothing to hand `readiness.evaluate`. This is the type that says so.
    """

    pull: PullRequest
    threads: list[Thread]
    checks: list[Check]
    contexts: list[str]
    merge: MergeState

    def __post_init__(self) -> None:
        if None in (
            self.pull,
            self.threads,
            self.checks,
            self.contexts,
            self.merge,
        ):
            raise ValueError("a reading is all five records or it is not one")


@dataclass(frozen=True)
class Fact:
    """One claim readiness makes, with the evidence for it."""

    name: str
    ok: bool
    detail: str

    def __post_init__(self) -> None:
        if not self.detail.strip():
            raise ValueError(f"fact {self.name!r} carries no evidence")


@dataclass(frozen=True)
class Verdict:
    """Readiness, and the facts it was decided on."""

    ready: bool
    facts: list[Fact]
