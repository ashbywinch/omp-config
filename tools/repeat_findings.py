#!/usr/bin/env python3
"""Show which hunks a PR's reviewer has had to answer more than once.

    repeat_findings.py <pr-number> [--repo owner/name] [--root path]

This is a diagnostic, not a check. A hunk the reviewer returns to is one where
an earlier answer did not settle it. It reports standing, not a pass:

- **SPENT** — the suggested patch matches the text already there, so the reviewer
  was confused about that line. Reply with the diff, and take the comment as
  evidence about the file.
- a count above one — zoom out on the file and see what is actually confusing
  (`skill://pr-workflow` §11c).

It exits 0 whatever it finds. A gate on the count would license the first round,
and one round is already one too many.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

FENCE_RE = re.compile(r"```[a-z]*\n(.*?)```", re.DOTALL)


@dataclass(frozen=True)
class Finding:
    """One inline comment, top-level or reply.

    A reply answers a comment; it does not flag the hunk again, so grouping keeps
    the top-level ones only.
    """

    id: int
    author: str
    path: str
    line: int | None
    body: str
    reply_to: int | None = None

    @classmethod
    def from_api(cls, node: dict) -> "Finding":  # lucidlint: ignore record-shape the GitHub payload is the wire format; reading it into Finding is this function's job
        """Read one comment off the wire, keeping only what standing needs."""
        return cls(
            id=node["id"],
            author=node["user"]["login"],
            path=node["path"],
            line=node.get("line") or node.get("original_line"),
            body=node["body"] or "",
            reply_to=node.get("in_reply_to_id"),
        )

    @property
    def is_reply(self) -> bool:
        """A reply carries the id of the comment it answers."""
        return self.reply_to is not None


def suggested_patch(body: str) -> str | None:
    """The replacement text a finding offers: the last fenced block in its body.

    A suggestion fence and a "Proposed code" block are both fenced, so the last
    block is the code in either form.
    """
    fences = FENCE_RE.findall(body)
    return fences[-1] if fences else None


def normalised(lines: list[str]) -> tuple[str, ...]:
    """Text as the reviewer means it: blank lines and indentation carry no meaning."""
    return tuple(line.strip() for line in lines if line.strip())


def patch_replaces(patch: str, file_lines: list[str], line: int | None) -> bool:
    """True when the patch is the text already in the file.

    GitHub anchors a comment at the last line of its range, so the patch is
    compared against a slice ending at `line`. A file changed since the comment
    will not match, which reports a spent finding as open — the safe direction.
    """
    if line is None:
        return False
    want = normalised(patch.splitlines())
    if not want:
        return False
    start = max(0, line - len(want))
    return want == normalised(file_lines[start:line])


def group_by_hunk(findings: list[Finding]) -> dict[tuple[str, int | None], list[Finding]]:
    """Findings per path and line, in first-seen order."""
    keys = list(dict.fromkeys((f.path, f.line) for f in findings))
    return {key: [f for f in findings if (f.path, f.line) == key] for key in keys}


@dataclass(frozen=True)
class Standing:
    """One hunk's standing: how many findings, and whether the last one is spent."""

    path: str
    line: int | None
    findings: tuple[Finding, ...]
    spent: bool

    @property
    def answered_more_than_once(self) -> bool:
        """A second finding on a hunk says the first answer did not settle it."""
        return len(self.findings) > 1

    @property
    def mark(self) -> str:
        """The one word that changes what a reader does, empty when nothing does."""
        return "SPENT" if self.spent else ""


def lines_from(root: Path) -> Callable[[str], list[str]]:
    """Read a file's lines from the checkout the comments anchor to."""

    def read(path: str) -> list[str]:
        target = root / path
        return target.read_text(encoding="utf-8").splitlines() if target.exists() else []

    return read


def standings(findings: list[Finding], lines_for: Callable[[str], list[str]]) -> list[Standing]:
    """Every hunk's standing, most-answered first.

    `lines_for` supplies the file's current text, so a caller decides where it
    comes from and a test needs no filesystem.
    """
    out: list[Standing] = []
    for (path, line), group in group_by_hunk([f for f in findings if not f.is_reply]).items():
        lines = lines_for(path)
        spent = any(
            patch_replaces(patch, lines, line)
            for patch in (suggested_patch(f.body) for f in group)
            if patch
        )
        out.append(Standing(path=path, line=line, findings=tuple(group), spent=spent))
    return sorted(out, key=lambda s: (-len(s.findings), s.path, s.line or 0))


def fetch(pr: str, repo: str) -> list[Finding]:
    """Every inline comment on the PR, pages included.

    `--jq '.[] | tojson'` prints one object per line, because `--paginate`
    concatenates pages and the result is not one JSON document.
    """
    result = subprocess.run(
        ["gh", "api", "--paginate", f"repos/{repo}/pulls/{pr}/comments", "--jq", ".[] | tojson"],
        capture_output=True, text=True, check=True,
    )
    return [Finding.from_api(json.loads(line)) for line in result.stdout.splitlines() if line.strip()]


def default_repo() -> str:
    """The repo of the current checkout, as `owner/name`."""
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def report(rows: list[Standing]) -> str:
    """The table, then what a reader does about it."""
    lines = [f"{'MARK':6} {'COUNT':5} PATH:LINE"]
    lines += [f"{row.mark or '-':6} {len(row.findings):<5} {row.path}:{row.line}" for row in rows]
    spent = [row for row in rows if row.spent]
    reworded = [row for row in rows if row.answered_more_than_once and not row.spent]
    if not spent and not reworded:
        return "\n".join(lines) + "\nNothing here has been answered twice: fix each finding as written."
    if spent:
        lines.append(
            f"\n{len(spent)} hunk(s) SPENT: the reviewer proposed the text already there. "
            "Reply with the diff, and treat the comment as evidence about the file."
        )
    if reworded:
        lines.append(
            f"\n{len(reworded)} hunk(s) answered more than once. Zoom out on the file and see "
            "what is actually confusing (skill://pr-workflow §11c)."
        )
    return "\n".join(lines)


def main() -> int:
    """Print the standing and the next step. Always exits 0: this is advice, not a gate."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pr", help="pull request number")
    parser.add_argument("--repo", default=None, help="owner/name (default: this checkout)")
    parser.add_argument("--root", default=".", help="checkout the comments anchor to")
    args = parser.parse_args()

    repo = args.repo or default_repo()
    print(report(standings(fetch(args.pr, repo), lines_from(Path(args.root)))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
