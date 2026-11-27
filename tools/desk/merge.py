"""Whether a head merges into its base, and whether it is behind it."""

from __future__ import annotations

from pathlib import Path

from tools.desk.errors import SourceUnknown
from tools.desk.github import Github
from tools.desk.model import MergeState, PullRequest


class Merge(Github):
    """Reads a pull request's merge state, proving it locally when GitHub cannot.

    ``mergeStateStatus`` answers cheaply. ``UNKNOWN`` is GitHub saying it has
    not worked it out yet, so the answer is proved against the checkout with
    ``git fetch`` and ``git merge-tree``. When neither can answer, the read
    raises: a merge nobody verified is not a merge.
    """

    _CONFLICT = "DIRTY"
    _BEHIND = "BEHIND"
    _UNKNOWN = "UNKNOWN"

    def __init__(self, repo: str, timeout: int = 30, root: Path = Path(".")) -> None:
        super().__init__(repo, timeout)
        self.root = Path(root).resolve()

    def state(self, pull: PullRequest) -> MergeState:
        """The pull's merge state, or ``SourceUnknown`` when it cannot be proved.

        It takes the record the caller already read, so the pull is not read
        twice for the same pass.
        """
        if pull.merge_state not in (self._UNKNOWN, "-"):
            return MergeState(
                merges=pull.merge_state != self._CONFLICT,
                behind=pull.merge_state == self._BEHIND,
            )
        return self._prove_locally(pull)

    def _prove_locally(self, pull: PullRequest) -> MergeState:
        """Prove the merge in the checkout, refusing what git cannot answer."""
        origin_base = f"origin/{pull.base}"
        if not pull.head or pull.head == "-":
            raise SourceUnknown(
                f"no head sha to merge {pull.slug} against {origin_base}"
            )
        self._fetch(pull)
        merged = self._ask(
            ["merge-tree", "--write-tree", origin_base, pull.head],
            f"cannot merge {pull.slug} against {origin_base}",
        )
        ancestor = self._ask(
            ["merge-base", "--is-ancestor", origin_base, pull.head],
            f"cannot compare {pull.slug} with {origin_base}",
        )
        return MergeState(merges=merged == 0, behind=ancestor == 1)

    def _fetch(self, pull: PullRequest) -> None:
        """Make ``origin/<base>`` and the head available, or refuse.

        Guarantees both commits are present when it returns: a fetch that exits
        zero but leaves the head absent is still an unknown, not a missing head.
        """
        refspec = f"+refs/heads/{pull.base}:refs/remotes/origin/{pull.base}"
        fetched = self.command(["git", "fetch", "origin", refspec], cwd=self.root)
        if fetched.returncode != 0:
            raise SourceUnknown(
                f"cannot fetch origin/{pull.base} to prove {pull.slug}: "
                f"{_first_line(fetched.stderr, f'`git fetch` exited {fetched.returncode}')}"
            )
        if self._has_commit(pull.head):
            return
        fetched_head = self.command(["git", "fetch", "origin", pull.head], cwd=self.root)
        if fetched_head.returncode != 0:
            raise SourceUnknown(
                f"cannot fetch {pull.head[:7]} to prove {pull.slug}: "
                f"{_first_line(fetched_head.stderr, f'`git fetch` exited {fetched_head.returncode}')}"
            )
        if not self._has_commit(pull.head):
            raise SourceUnknown(
                f"git fetch did not deliver {pull.head[:7]} to prove {pull.slug}"
            )

    def _ask(self, args: list[str], reason: str) -> int:
        """A git question whose 0 and 1 are answers; anything else refuses."""
        result = self.command(["git", *args], cwd=self.root)
        if result.returncode not in (0, 1):
            first = _first_line(
                result.stderr, f"`git {args[0]}` exited {result.returncode}"
            )
            raise SourceUnknown(f"{reason}: {first}")
        return result.returncode

    def _has_commit(self, sha: str) -> bool:
        return self.command(
            ["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=self.root
        ).returncode == 0


def _first_line(text: str, fallback: str) -> str:
    return (text.strip().splitlines() or [fallback])[0]
