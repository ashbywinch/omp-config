"""The repository a command runs inside, when its name was not given."""

from __future__ import annotations

import json

from tools.desk.command import run
from tools.desk.errors import SourceUnknown


class Repository:
    """Reads this checkout's ``owner/name``."""

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def current(self) -> str:
        """The checkout's ``owner/name``, or ``SourceUnknown`` when there is none."""
        result = run(["gh", "repo", "view", "--json", "nameWithOwner"], self.timeout)
        if result.returncode != 0:
            raise SourceUnknown("not in a checkout, and no owner/name given")
        try:
            name = str(json.loads(result.stdout).get("nameWithOwner") or "")
        except json.JSONDecodeError as exc:
            raise SourceUnknown("cannot read the repo's name") from exc
        if not name:
            raise SourceUnknown("not in a checkout, and no owner/name given")
        return name
