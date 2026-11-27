"""A GitHub read bound to one repository and one timeout."""

from __future__ import annotations

from pathlib import Path
import subprocess

from tools.desk.command import run
from tools.desk.errors import SourceUnknown


class Github:
    """One repository's GitHub state, read under one timeout.

    A subclass adds the reads for one concern. Raw payloads stay inside the
    subclass: a caller receives records, never the wire format. A read that
    fails raises ``SourceUnknown`` with the fact it could not read.
    """

    def __init__(self, repo: str, timeout: int = 30) -> None:
        self.repo = repo
        self.timeout = timeout

    def command(
        self, args: list[str], cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        return run(args, self.timeout, cwd)

    def gh(self, args: list[str], reason: str) -> str:
        """The output of one ``gh`` call, or ``SourceUnknown(reason)``."""
        result = self.command(["gh", *args])
        if result.returncode != 0:
            raise SourceUnknown(reason)
        return result.stdout
