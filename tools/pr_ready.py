#!/usr/bin/env python3
"""Prove a PR's state before anyone calls it ready.

    pr_ready.py <pr-number> [--repo owner/name] [--root path] [--no-wait]

Procedure: `skill://pr-state`.
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

PASSING_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})


class Verdict(Enum):
    READY = "READY"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class Fact:
    name: str
    ok: bool
    detail: str

    def __post_init__(self) -> None:
        if not self.detail.strip():
            raise ValueError(f"fact {self.name!r} carries no evidence")


@dataclass(frozen=True)
class Target:
    sha: str
    base: str

    @property
    def origin_base(self) -> str:
        return f"origin/{self.base}"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    conclusion: str | None
    started: str = ""

    @classmethod
    def from_api(cls, node: dict) -> "Check":  # lucidlint: ignore record-shape the GitHub payload is the wire format; reading it here is this function's job
        return cls(
            name=str(node.get("name") or "unnamed"),
            status=str(node.get("status") or "unknown"),
            conclusion=node.get("conclusion"),
            started=str(node.get("started_at") or ""),
        )

    @property
    def passed(self) -> bool:
        return self.status == "completed" and self.conclusion in PASSING_CONCLUSIONS


def run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)


def gh_json(args: list[str]) -> dict:  # lucidlint: ignore record-shape the GitHub payload is the wire format; reading it here is this function's job
    result = run(["gh", *args])
    return json.loads(result.stdout) if result.returncode == 0 and result.stdout.strip() else {}


def latest_by_name(checks: list[Check]) -> list[Check]:
    latest: dict[str, Check] = {}
    for check in checks:
        held = latest.get(check.name)
        if held is None or check.started >= held.started:
            latest[check.name] = check
    return list(latest.values())


def describe_failure(check: Check) -> str:
    return f"{check.name} is {check.status.lower()} {check.conclusion or ''}".strip()


def failure_lines(checks: list[Check], required: set[str] | None) -> list[str]:
    latest = latest_by_name(checks)
    if not required:
        return [describe_failure(check) for check in latest if not check.passed]
    by_name = {check.name: check for check in latest}
    broken = []
    for name in sorted(required):
        check = by_name.get(name)
        if check is None:
            broken.append(f"{name} has no run on this sha")
        elif not check.passed:
            broken.append(describe_failure(check))
    return broken


@dataclass(frozen=True)
class PullRequest:
    repo: str
    number: str
    root: Path

    def target(self) -> Target:
        data = gh_json(["api", f"repos/{self.repo}/pulls/{self.number}"])
        return Target(
            sha=data.get("head", {}).get("sha", ""),
            base=data.get("base", {}).get("ref", "main"),
        )

    def _has_commit(self, sha: str) -> bool:
        return bool(sha) and run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=self.root).returncode == 0

    def _fetch(self, target: Target) -> None:
        refspec = f"+refs/heads/{target.base}:refs/remotes/origin/{target.base}"
        run(["git", "fetch", "origin", refspec], cwd=self.root)
        if not self._has_commit(target.sha):
            run(["git", "fetch", "origin", target.sha], cwd=self.root)

    def merge(self, target: Target) -> Fact:
        self._fetch(target)
        if not self._has_commit(target.sha):
            return Fact(name="merge", ok=False, detail="no head sha to merge")
        result = run(["git", "merge-tree", "--write-tree", target.origin_base, target.sha], cwd=self.root)
        if result.returncode == 0:
            return Fact(name="merge", ok=True, detail=f"merges cleanly into {target.origin_base}")
        if result.returncode == 1:
            first = (result.stdout.strip().splitlines() or ["no detail"])[0]
            return Fact(name="merge", ok=False, detail=f"conflicts with {target.origin_base}: {first}")
        first = (result.stderr.strip().splitlines() or [f"`git merge-tree` exited {result.returncode}"])[0]
        return Fact(name="merge", ok=False, detail=f"cannot merge against {target.origin_base}: {first}")

    def base(self, target: Target) -> Fact:
        self._fetch(target)
        if not self._has_commit(target.sha):
            return Fact(name="base", ok=False, detail="no head sha to compare with the base")
        contains = run(["git", "merge-base", "--is-ancestor", target.origin_base, target.sha], cwd=self.root)
        if contains.returncode == 0:
            return Fact(name="base", ok=True, detail=f"contains {target.origin_base}")
        if contains.returncode != 1:
            first = (contains.stderr.strip().splitlines() or [f"`git merge-base` exited {contains.returncode}"])[0]
            return Fact(name="base", ok=False, detail=f"cannot compare with {target.origin_base}: {first}")
        behind = run(["git", "rev-list", "--count", f"{target.sha}..{target.origin_base}"], cwd=self.root)
        if behind.returncode != 0:
            return Fact(
                name="base",
                ok=False,
                detail=f"behind {target.origin_base} — merge the base first "
                f"(`git rev-list` exited {behind.returncode})",
            )
        count = behind.stdout.strip()
        commits = f"{count} commit" if count == "1" else f"{count} commits"
        return Fact(name="base", ok=False, detail=f"behind {target.origin_base} by {commits} — merge the base first")

    def _required_contexts(self, target: Target) -> set[str] | None:
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
        if not data:
            return None
        repository = (data.get("data") or {}).get("repository") or {}
        ref = repository.get("ref") or {}
        rule = ref.get("branchProtectionRule") or {}
        return set(rule.get("requiredStatusCheckContexts") or [])

    def checks(self, target: Target) -> Fact:
        if not target.sha:
            return Fact(name="checks", ok=False, detail="no head sha to read checks from")
        nodes = gh_json(["api", f"repos/{self.repo}/commits/{target.sha}/check-runs?per_page=100"])
        checks = [Check.from_api(node) for node in nodes.get("check_runs", [])]
        if not checks:
            return Fact(
                name="checks",
                ok=False,
                detail="0 check-runs on this sha. Nothing ran: a conflicted PR cannot build "
                "its merge ref, so no pull_request run starts. Fix the conflict, then re-run.",
            )
        required = self._required_contexts(target)
        current = latest_by_name(checks)
        broken = failure_lines(current, required)
        if broken:
            return Fact(name="checks", ok=False, detail="; ".join(broken))
        if required is None:
            judged = "required contexts unreadable, every run counted"
        elif required:
            judged = f"{len(required)} required context(s) passing"
        else:
            judged = "no required contexts, every run counted"
        return Fact(name="checks", ok=True, detail=f"{len(current)} check(s), latest run of each, all successful; {judged}")

    def threads(self, wait: bool) -> Fact:
        tool = shutil.which("pr-threads")
        if not tool:
            return Fact(name="threads", ok=False, detail="pr-threads is not on PATH: run `make install`")
        args = [tool, self.number, "--repo", self.repo] + (["--wait"] if wait else [])
        result = run(args)
        first = (result.stdout.strip().splitlines() or ["no output"])[0]
        return Fact(name="threads", ok=result.returncode == 0, detail=first)

    def facts(self, wait: bool) -> list[Fact]:
        target = self.target()
        return [self.merge(target), self.base(target), self.checks(target), self.threads(wait=wait)]


def verdict(facts: list[Fact]) -> Verdict:
    return Verdict.READY if all(fact.ok for fact in facts) else Verdict.BLOCKED


def next_step(facts: list[Fact]) -> str:
    fixes = {
        "merge": "resolve the conflict against the base and push",
        "base": "merge the base branch into this one and push — a PR behind its base is not ready",
        "checks": "run the failing check again, or fix what it reports",
        "threads": "answer every thread the reviewer opened, and resolve none of them",
    }
    broken = [fixes[fact.name] for fact in facts if not fact.ok]
    if not broken:
        return "hand it over: the merge is the user's to make"
    return "blocked — " + "; ".join(broken)


def report(pr: PullRequest, target: Target, facts: list[Fact]) -> str:
    lines = [f"PR {pr.number} ({pr.repo}) @ {target.sha[:12] or 'unknown'}"]
    lines += [f"  {fact.name:7} {'ok   ' if fact.ok else 'FAIL '} {fact.detail}" for fact in facts]
    lines += [f"{verdict(facts).value}: {next_step(facts)}"]
    return "\n".join(lines)


def main() -> int:
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
