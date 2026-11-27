"""The one place that decides whether a PR is ready, from records a caller read."""

from __future__ import annotations

from tools.desk.model import Check, Fact, MergeState, PullRequest, Thread, Verdict


def evaluate(
    pull: PullRequest,
    threads: list[Thread],
    checks: list[Check],
    contexts: list[str],
    merge_state: MergeState,
) -> Verdict:
    """Whether the PR is ready, over the records it is handed.

    ``checks`` are the latest run per name, as ``Checks.on`` returns them.
    ``threads`` are the unanswered ones; answering the definition is
    ``tools.desk.threads.unanswered``, and ``me`` stays the caller's.
    """
    facts = [
        _head(pull),
        _checks(checks, contexts),
        _merge(pull, merge_state),
        _threads(threads),
        _draft(pull),
    ]
    return Verdict(ready=all(fact.ok for fact in facts), facts=facts)


def _head(pull: PullRequest) -> Fact:
    """A head that is not a commit sha cannot be read or merged."""
    if not pull.head or pull.head == "-":
        return Fact(name="head", ok=False, detail="no head sha")
    return Fact(name="head", ok=True, detail=f"head {pull.head[:12]}")


def _checks(checks: list[Check], contexts: list[str]) -> Fact:
    """Required contexts only: a run that never reported verified nothing."""
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


def _merge(pull: PullRequest, merge_state: MergeState) -> Fact:
    """No conflict and not behind; the approval gate is not a merge failure.

    A missing head is `_head`'s fact, not this one's: naming it twice would
    give one cause two lines in the verdict.
    """
    if not pull.base or pull.base == "-":
        return Fact(name="merge", ok=False, detail="no base branch to compare against")
    origin_base = f"origin/{pull.base}"
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
