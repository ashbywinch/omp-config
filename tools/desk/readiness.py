"""The one place that decides whether a PR is ready, from records a caller read."""

from __future__ import annotations

from tools.desk.model import (
    Check,
    Fact,
    MergeState,
    PullRequest,
    Reading,
    Thread,
    Verdict,
)


def evaluate(reading: Reading) -> Verdict:
    """Whether the PR is ready, over the one set of records it is handed.

    ``checks`` are the latest run per name, as ``Checks.on`` returns them.
    ``threads`` are the unanswered ones; answering the definition is
    ``tools.desk.threads.unanswered``, and ``me`` stays the caller's.
    """
    pull = reading.pull
    facts = [
        _head(pull),
        _checks(reading.contexts, reading.checks),
        _merge(reading.merge),
        _threads(reading.threads),
        _draft(pull),
    ]
    return Verdict(ready=all(fact.ok for fact in facts), facts=facts)


def _head(pull: PullRequest) -> Fact:
    """A head that is not a commit sha cannot be read or merged."""
    if not pull.head or pull.head == "-":
        return Fact(name="head", ok=False, detail="no head sha")
    return Fact(name="head", ok=True, detail=f"head {pull.head[:12]}")


def _checks(contexts: list[str], checks: list[Check]) -> Fact:
    """Required contexts only: a run that never reported verified nothing.

    ``contexts`` is what the base branch requires and ``checks`` is the newest
    run per name; a check nobody required cannot block.
    """
    required = sorted(set(contexts))
    if not required:
        return Fact(name="checks", ok=True, detail="no required contexts")
    runs = {check.name: check for check in checks}
    broken: list[str] = []
    for name in required:
        run = runs.get(name)
        if run is None:
            broken.append(f"{name} has no run on this head")
        elif not run.passed:
            broken.append(f"{name} is {run.status.lower()} {run.conclusion or ''}".strip())
    if broken:
        return Fact(name="checks", ok=False, detail="; ".join(broken))
    return Fact(
        name="checks",
        ok=True,
        detail=f"{len(required)} required context(s) completed and passing",
    )


def _merge(merge_state: MergeState) -> Fact:
    """No conflict and not behind; the approval gate is not a merge failure.

    The base is on the record because `Merge.state` refuses to produce one
    without it, so this fact never has to name a missing base or head.
    """
    origin_base = f"origin/{merge_state.base}"
    if not merge_state.merges:
        return Fact(name="merge", ok=False, detail=f"conflicts with {origin_base}")
    if merge_state.behind:
        return Fact(name="merge", ok=False, detail=f"behind {origin_base}")
    return Fact(name="merge", ok=True, detail=f"merges cleanly into {origin_base}")


def _threads(threads: list[Thread]) -> Fact:
    """A thread whose last voice is not mine is open work."""
    if threads:
        return Fact(
            name="threads", ok=False, detail=f"{len(threads)} unanswered thread(s)"
        )
    return Fact(name="threads", ok=True, detail="no unanswered threads")


def _draft(pull: PullRequest) -> Fact:
    """A draft is not yet asking for review."""
    if pull.draft:
        return Fact(name="draft", ok=False, detail="the PR is a draft")
    return Fact(name="draft", ok=True, detail="not a draft")
