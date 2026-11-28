"""The check runs on a head, reduced to the run that counts for each name."""

from __future__ import annotations

import json

from tools.desk.errors import SourceUnknown
from tools.desk.github import Github
from tools.desk.model import Check, absent


def checks_from_pages(text: str) -> list[Check]:
    """Every check run in the stream ``gh api --paginate`` writes.

    The pages arrive as consecutive JSON objects, so the stream is decoded
    value by value rather than split on lines: a pretty-printed page would
    break a line-based reader.
    """
    decoder = json.JSONDecoder()
    checks: list[Check] = []
    index = 0
    while True:
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            return checks
        try:
            page, index = decoder.raw_decode(text, index)
        except json.JSONDecodeError as exc:
            raise SourceUnknown("GitHub returned unreadable JSON") from exc
        if not isinstance(page, dict):
            # A page that is not an object is unreadable, not an empty answer:
            # skipping it would report "no check runs" for a payload we cannot read.
            raise SourceUnknown("GitHub returned a check-runs page that is not an object")
        for node in page.get("check_runs") or []:
            if isinstance(node, dict):
                checks.append(_check(node))


def _check(node: dict) -> Check:  # lucidlint: ignore record-shape the GitHub payload is the wire format; reading it here is this function's job
    return Check(
        name=str(node.get("name") or "unnamed"),
        status=str(node.get("status") or "unknown"),
        conclusion=node.get("conclusion"),
        started=str(node.get("started_at") or ""),
    )


def latest_by_name(checks: list[Check]) -> list[Check]:
    """One check per name, the newest run.

    ``filter=latest`` is not reliable — a reusable workflow's job comes back
    twice — so the reduction happens here. A queued run has no ``started_at``
    and is the one that supersedes the run before it, so it orders newest;
    keeping the older, finished run would report a re-run as already passed.
    """
    latest: dict[str, Check] = {}
    for check in checks:
        held = latest.get(check.name)
        if held is None or _newer(check, held):
            latest[check.name] = check
    return list(latest.values())


def _newer(check: Check, held: Check) -> bool:
    """Whether ``check`` supersedes ``held``: a queued run, or a later start."""
    return (not check.started, check.started) >= (not held.started, held.started)


class Checks(Github):
    """Reads the check runs on one head."""

    _LATEST = "repos/{repo}/commits/{head}/check-runs?per_page=100&filter=latest"

    def on(self, head: str) -> list[Check]:
        """The newest run of every check on ``head``.

        An empty list is an answer: no run reported. ``SourceUnknown`` when the
        head is not a sha, or the read fails.
        """
        if absent(head):
            raise SourceUnknown("no head sha to read checks from")
        short = head[:7]
        out = self.gh(
            ["api", "--paginate", self._LATEST.format(repo=self.repo, head=head)],
            f"check-runs unreadable on {short}",
        )
        try:
            checks = checks_from_pages(out)
        except SourceUnknown as exc:
            raise SourceUnknown(f"check-runs on {short} are unreadable") from exc
        return latest_by_name(checks)
