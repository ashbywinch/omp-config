"""What the watcher said, per PR.

The file records what was said, never what is true: GitHub wins every
disagreement, and a stale key that suppresses a notice costs more than a repeat.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path


class NoticeLog:
    """One PR's notice keys, stored exactly and written atomically.

    An empty string means "owed".
    """

    _KINDS = ("threads", "checks", "behind", "ready")
    _MAX_AGE_SECONDS = 7 * 24 * 60 * 60

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._keys = self._read()

    @classmethod
    def for_pr(cls, repo: str, number: int, root: Path | None = None) -> "NoticeLog":
        """The log for one PR, under the state directory."""
        owner, _, name = repo.partition("/")
        return cls((root or cls.root()) / owner / name / f"{number}.json")

    @classmethod
    def root(cls) -> Path:
        """`$XDG_STATE_HOME/omp-config/watch`, falling back to `~/.local/state`."""
        state = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
        return Path(state) / "omp-config" / "watch"

    @classmethod
    def prune(cls, root: Path | None = None, now: float | None = None) -> list[Path]:
        """Delete stale files; return what was removed.

        A stamp ahead of now is stale too: a restored or copied tree must not
        keep a key that suppresses a notice for ever.
        """
        base = root or cls.root()
        if not base.is_dir():
            return []
        moment = now if now is not None else time.time()
        cutoff = moment - cls._MAX_AGE_SECONDS
        removed: list[Path] = []
        # A temporary file is always an abandoned write: only a live `_write`
        # in this process makes one, and a live write renames it. Age is not
        # the test, because a crashed write leaves one that no key needs.
        for path in sorted(base.rglob(".*.tmp")):
            if cls._unlink(path):
                removed.append(path)
        for path in sorted(base.rglob("*.json")):
            try:
                stamp = path.stat().st_mtime
            except OSError:
                continue
            stale = stamp < cutoff or stamp > moment
            if stale and cls._unlink(path):
                removed.append(path)
        return removed

    @staticmethod
    def _unlink(path: Path) -> bool:
        """Delete one file and say whether it went.

        A cleanup pass that meets a directory, or a file it may not remove,
        skips it: the next pass tries again, and one odd entry is not worth
        the watcher.
        """
        try:
            path.unlink()
        except OSError:
            return False
        return True

    def get(self, kind: str) -> str:
        """The last key recorded for this notice; empty means owed."""
        return self._keys.get(kind, "")

    def set(self, kind: str, key: str) -> None:
        """Record (or clear) one notice's key, and write the file."""
        if self._keys.get(kind, "") == key:
            return
        self._keys[kind] = key
        self._write()

    def delete(self) -> None:
        """Forget every key: the PR is merged or closed."""
        self._keys = {}
        self.path.unlink(missing_ok=True)

    def _read(self) -> dict[str, str]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            # A file we cannot trust is no record at all: a repeat costs less
            # than a notice suppressed by a file that may be lying. Any other
            # read failure is a real problem and propagates.
            return {}
        if not isinstance(data, dict):
            return {}
        return {kind: str(data.get(kind) or "") for kind in self._KINDS}

    def _write(self) -> None:
        # The directory first, then the temp file in it: `mkstemp` does not
        # create the directory, and the rename is atomic only within one.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp"
        )
        payload = json.dumps(
            {kind: self._keys.get(kind, "") for kind in self._KINDS}, sort_keys=True
        )
        try:
            # Written through the descriptor `mkstemp` returned: closing it and
            # reopening the path would give another process a window to swap it.
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(payload)
            os.replace(temporary, self.path)
        except OSError:
            Path(temporary).unlink(missing_ok=True)
            raise

