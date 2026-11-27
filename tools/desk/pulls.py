"""One pull request's fields, read from GitHub."""

from __future__ import annotations

import json

from tools.desk.errors import SourceUnknown
from tools.desk.github import Github
from tools.desk.model import PullRequest

def _text(node: dict, key: str) -> str:  # lucidlint: ignore record-shape the GitHub payload is the wire format; reading it here is this function's job
    return str(node.get(key) or "-")


class PullRequests(Github):
    """Reads one pull request at a time."""

    _FIELDS = "state,headRefOid,reviewDecision,baseRefName,url,mergeStateStatus"

    def view(self, number: int) -> PullRequest:
        """The pull request's fields, or ``SourceUnknown`` when it cannot be read."""
        out = self.gh(
            ["pr", "view", str(number), "--repo", self.repo, "--json", self._FIELDS],
            f"cannot read {self.repo}#{number}",
        )
        if not out.strip():
            raise SourceUnknown(f"GitHub returned nothing for {self.repo}#{number}")
        try:
            node = json.loads(out)
        except json.JSONDecodeError as exc:
            raise SourceUnknown(
                f"GitHub returned unreadable JSON for {self.repo}#{number}"
            ) from exc
        if not isinstance(node, dict):
            raise SourceUnknown(f"GitHub returned no pull request for {self.repo}#{number}")
        return PullRequest(
            number=number,
            repo=self.repo,
            state=_text(node, "state"),
            head=_text(node, "headRefOid"),
            base=_text(node, "baseRefName"),
            url=_text(node, "url"),
            decision=_text(node, "reviewDecision"),
            merge_state=_text(node, "mergeStateStatus"),
        )
