"""The file that remembers what the watcher already said."""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path


class NoticeLog:
    """One PR's notice keys, stored exactly and written atomically.

    The file records what was said, never what is true: GitHub wins every
    disagreement, and a stale key that suppresses a notice costs more than a
    repeat. An empty string means "owed".
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
        """Delete notice files older than seven days; return what was removed."""
        base = root or cls.root()
        if not base.is_dir():
            return []
        cutoff = (now if now is not None else time.time()) - cls._MAX_AGE_SECONDS
        removed: list[Path] = []
        for path in sorted(base.rglob("*.json")):
            try:
                stale = path.stat().st_mtime < cutoff
            except FileNotFoundError:
                continue
            if stale:
                path.unlink(missing_ok=True)
                removed.append(path)
        return removed

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
        except (OSError, json.JSONDecodeError):
            # A log we cannot read is no record at all: a repeat costs less
            # than a notice suppressed by a file we could not trust.
            return {}
        if not isinstance(data, dict):
            return {}
        return {kind: str(data.get(kind) or "") for kind in self._KINDS}

    def _write(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            {kind: self._keys.get(kind, "") for kind in self._KINDS}, sort_keys=True
        )
        handle, temporary = tempfile.mkstemp(
            dir=self.path.parent, prefix=f".{self.path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(payload)
            os.replace(temporary, self.path)
        except OSError:
            Path(temporary).unlink(missing_ok=True)
            raise
