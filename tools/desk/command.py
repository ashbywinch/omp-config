"""One bounded command, keeping its output whatever its exit status."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run(
    args: list[str], timeout: int, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run one command, bounded, keeping its output whatever its status.

    A missing tool and a timeout are answers too: they come back as a failed
    result carrying the reason, so every caller reports them the same way.
    """
    try:
        return subprocess.run(
            args, cwd=cwd, capture_output=True, text=True, check=False, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 1, "", str(exc))
