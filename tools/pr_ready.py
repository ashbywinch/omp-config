#!/usr/bin/env python3
"""Prove a PR's state and say whether it can be handed over.

    pr_ready.py <pr-number> [--repo owner/name] [--root path] [--no-wait]

Three facts decide it: the head merges into the base, every check-run on the
head is completed and successful, and no review thread is waiting for an answer.
The tool prints each fact with its evidence, then READY or BLOCKED and the next
step. Exit 0 when ready, 1 when blocked.

Absence is not success. Zero check-runs is BLOCKED, and the reason matters: a
conflicted PR cannot build its merge ref, so the `pull_request` event never
starts a run and the PR shows no checks at all. That reads as nothing to report
if nobody counts.

A cancelled check is stale, not failed: a newer run on the same ref replaced it.
The tool names it rather than guessing which run to keep.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Verdict(Enum):
    """The one word a reader acts on."""

    READY = "READY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class Fact:
    """One of the three things a reader needs before the PR is handed over."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class Target:
    """The two coordinates of a merge question: what merges, and into what."""

    sha: str
    base: str


@dataclass(frozen=True)
class Check:
    """One check-run on the head, as far as a verdict needs it.

    `started` orders two runs of the same name: a re-run supersedes the run
    before it, and a cancelled run is the superseded one.
    """

    name: str
    status: str
    conclusion: str | None
    started: str = ""
    required: bool = False

    @classmethod
    def from_api(cls, node: dict) -> "Check":  # lucidlint: ignore record-shape the GitHub payload is the wire format; reading it here is this function's job
        """Read one check-run off the wire."""
        return cls(
            name=str(node.get("name") or "unnamed"),
            status=str(node.get("status") or "unknown"),
            conclusion=node.get("conclusion"),
            started=str(node.get("started_at") or ""),
        )

    @property
    def passed(self) -> bool:
        """Finished, and not reporting a problem.

        GitHub treats `success`, `neutral` and `skipped` as passing for branch
        protection: `neutral` says the run finished without a verdict (the
        reviewer's informational check), `skipped` says its `if:` did not match.
        Only a failure conclusion blocks.
        """
        return self.status == "completed" and self.conclusion in ("success", "neutral", "skipped")


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command and keep its output, whether or not it exits zero."""
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def gh_json(args: list[str]) -> dict:  # lucidlint: ignore record-shape the GitHub payload is the wire format; reading it here is this function's job
    """A `gh api` response, parsed, or an empty record when the call fails."""
    result = run(["gh", *args])
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else {}


def latest_by_name(checks: list[Check]) -> list[Check]:
    """One check per name, the most recent run.

    A re-run supersedes the run before it, so counting every run reports a
    cancelled run as a failure while the run that replaced it is green.
    """
    latest: dict[str, Check] = {}
    for check in checks:
        held = latest.get(check.name)
        if held is None or check.started >= held.started:
            latest[check.name] = check
    return list(latest.values())


def failed(checks: list[Check]) -> list[str]:
    """The REQUIRED checks that did not pass.

    A check the branch does not require cannot block a merge, so reporting it
    as a failure is a wrong verdict that teaches the reader to ignore the
    tool. When the API will not say which contexts are required, every check
    counts — the conservative direction.
    """
    required = [check for check in checks if check.required] or checks
    return [
        f"{check.name} is {check.status.lower()} {check.conclusion or ''}".strip()
        for check in required
        if not check.passed
    ]


@dataclass(frozen=True)
class PullRequest:
    """What a PR is: a repo, a number, and the checkout its diff is proved in."""

    repo: str
    number: str
    root: Path

    def target(self) -> Target:
        """The head sha and base branch, as the PR records them."""
        data = gh_json(["api", f"repos/{self.repo}/pulls/{self.number}"])
        return Target(
            sha=data.get("head", {}).get("sha", ""),
            base=data.get("base", {}).get("ref", "main"),
        )

    def merge(self, target: Target) -> Fact:
        """Whether the head merges into the base, by tree rather than by GitHub's opinion."""
        run(["git", "fetch", "origin", target.base], cwd=self.root)
        if target.sha and run(["git", "cat-file", "-e", f"{target.sha}^{{commit}}"], cwd=self.root).returncode != 0:
            run(["git", "fetch", "origin", target.sha], cwd=self.root)
        result = run(["git", "merge-tree", "--write-tree", f"origin/{target.base}", target.sha], cwd=self.root)
        if result.returncode == 0:
            return Fact(name="merge", ok=True, detail=f"merges cleanly into origin/{target.base}")
        first = (result.stdout.strip().splitlines() or ["no detail"])[0]
        return Fact(name="merge", ok=False, detail=f"conflicts with origin/{target.base}: {first}")

    def _required_names(self, target: Target) -> set[str]:
        """The required check contexts for the base branch, or empty when unreadable."""
        query = (
            "query($o:String!,$n:String!,$b:String!){repository(owner:$o,name:$n){"
            "ref(qualifiedName:$b){branchProtectionRule{requiredStatusCheckContexts}}}}"
        )
        owner, _, name = self.repo.partition("/")
        data = gh_json([
            "api", "graphql",
            "-f", f"query={query}",
            "-f", f"o={owner}", "-f", f"n={name}", "-f", f"b=refs/heads/{target.base}",
        ])
        rule = (data.get("data") or {}).get("repository", {}).get("ref", {}) or {}
        rule = (rule.get("branchProtectionRule") or {})
        return set(rule.get("requiredStatusCheckContexts") or [])

    def checks(self, target: Target) -> Fact:
        """Whether every check on the head passed, with zero checks a failure."""
        if not target.sha:
            return Fact(name="checks", ok=False, detail="no head sha to read checks from")
        nodes = gh_json(["api", f"repos/{self.repo}/commits/{target.sha}/check-runs?per_page=100"])
        checks = [Check.from_api(node) for node in nodes.get("check_runs", [])]
        required = self._required_names(target)
        if required:
            checks = [
                Check(name=c.name, status=c.status, conclusion=c.conclusion,
                      started=c.started, required=c.name in required)
                for c in checks
            ]
        if not checks:
            return Fact(
                name="checks",
                ok=False,
                detail="0 check-runs on this sha. Nothing ran: a conflicted PR cannot build "
                "its merge ref, so no pull_request run starts. Fix the conflict, then re-run.",
            )
        current = latest_by_name(checks)
        broken = failed(current)
        if broken:
            return Fact(name="checks", ok=False, detail="; ".join(broken))
        return Fact(name="checks", ok=True, detail=f"{len(current)} check(s), latest run of each, all successful")

    def threads(self, wait: bool) -> Fact:
        """Whether any review thread is waiting for an answer, asked of pr-threads."""
        tool = shutil.which("pr-threads")
        if not tool:
            return Fact(name="threads", ok=False, detail="pr-threads is not on PATH: run `make install`")
        args = [tool, self.number, "--repo", self.repo] + (["--wait"] if wait else [])
        result = run(args)
        first = (result.stdout.strip().splitlines() or ["no output"])[0]
        return Fact(name="threads", ok=result.returncode == 0, detail=first)

    def facts(self, wait: bool) -> list[Fact]:
        """The three facts, in the order a reader asks them."""
        target = self.target()
        return [self.merge(target), self.checks(target), self.threads(wait=wait)]


def verdict(facts: list[Fact]) -> Verdict:
    """READY only when all three hold. One failure is blocked, whatever the rest say."""
    return Verdict.READY if all(fact.ok for fact in facts) else Verdict.BLOCKED


def next_step(facts: list[Fact]) -> str:
    """What to do about the facts that failed."""
    fixes = {
        "merge": "resolve the conflict against the base and push",
        "checks": "run the failing check again, or fix what it reports",
        "threads": "answer every thread the reviewer opened, and resolve none of them",
    }
    broken = [fixes[fact.name] for fact in facts if not fact.ok]
    if not broken:
        return "hand it over: the merge is the user's to make"
    return "blocked — " + "; ".join(broken)


def report(pr: PullRequest, target: Target, facts: list[Fact]) -> str:
    """Each fact with its evidence, then the verdict and the next step."""
    lines = [f"PR {pr.number} ({pr.repo}) @ {target.sha[:12] or 'unknown'}"]
    lines += [f"  {fact.name:7} {'ok   ' if fact.ok else 'FAIL '} {fact.detail}" for fact in facts]
    lines += [f"{verdict(facts).value}: {next_step(facts)}"]
    return "\n".join(lines)


def main() -> int:
    """Print the three facts and the verdict; exit non-zero when blocked."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pr", help="pull request number")
    parser.add_argument("--repo", default=None, help="owner/name (default: this checkout)")
    parser.add_argument("--root", default=".", help="checkout to prove the merge in")
    parser.add_argument("--no-wait", action="store_true", help="do not wait for the reviewer")
    args = parser.parse_args()

    repo = args.repo or run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]).stdout.strip()
    pr = PullRequest(repo=repo, number=args.pr, root=Path(args.root))
    target = pr.target()
    facts = pr.facts(wait=not args.no_wait)
    print(report(pr, target, facts))
    return 0 if verdict(facts) == Verdict.READY else 1


if __name__ == "__main__":
    sys.exit(main())
