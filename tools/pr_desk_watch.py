#!/usr/bin/env python3
"""Tell the session that owns a PR what needs doing next.

    pr-desk-watch.py <pr> [owner/name] [interval-seconds] [--once]

One recipient, `PR_DESK_AGENT`: the session that owns the PR — this repo's own
agent when the PR is part of its work, or the desk when the work must not
interrupt it. Every message goes there, because that session is also the
person's channel.

Four notices, one per state change, each keyed so a steady state is silent:

    a comment arrived       keyed by the sorted unanswered thread ids
    a required check failed keyed by the head plus the failing names
    the branch is behind    keyed by the head, once
    ready for review        keyed by the head

A key is recorded only after the send succeeds, so a failed send repeats.

Design: `docs/desk-watcher.md`. Procedure: `skill://pr-desk`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

def missing_tools() -> list[str]:
    """The tools this watcher cannot run without, absent from PATH."""
    return [
        tool for tool in ("gh", "pr-threads", "pr-ready", "paseo")
        if shutil.which(tool) is None
    ]


class WatchError(Exception):
    """A setting or an input that cannot be used, reported before any polling."""


def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    """Run one command, bounded, keeping its output whatever its status."""
    try:
        return subprocess.run(
            args, capture_output=True, text=True, check=False, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 1, "", str(exc))


def checks_from_pages(text: str) -> list["Check"]:
    """Every check run in the stream `gh api --paginate` writes.

    The pages arrive as consecutive JSON objects, so the stream is decoded value
    by value rather than split on lines: a pretty-printed page would break a
    line-based reader.
    """
    decoder = json.JSONDecoder()
    checks: list["Check"] = []
    index = 0
    while True:
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            return checks
        try:
            page, index = decoder.raw_decode(text, index)
        except json.JSONDecodeError as exc:
            raise WatchError("GitHub returned unreadable JSON") from exc
        if not isinstance(page, dict):
            continue
        for node in page.get("check_runs") or []:
            if isinstance(node, dict):
                checks.append(Check.from_api(node))


@dataclass(frozen=True)
class Check:
    """One check run on a head, as far as a verdict needs it."""

    name: str
    status: str
    conclusion: str | None
    started: str

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
        return self.status == "completed" and self.conclusion == "success"

    @property
    def failed(self) -> bool:
        """A conclusion that names something to fix."""
        return self.conclusion in {
            "failure", "timed_out", "action_required", "startup_failure"
        }


def latest_by_name(checks: list[Check]) -> list[Check]:
    """One check per name, the newest run.

    `filter=latest` is not reliable — a reusable workflow's job comes back twice
    — so the reduction happens here, ordered by `started_at`, which a run that
    never started leaves empty.
    """
    latest: dict[str, Check] = {}
    for check in checks:
        held = latest.get(check.name)
        if held is None or check.started >= held.started:
            latest[check.name] = check
    return list(latest.values())


@dataclass(frozen=True)
class PullRequest:
    state: str
    head: str
    decision: str
    base: str
    url: str
    merge_state: str

    @classmethod
    def from_api(cls, node: dict) -> "PullRequest":  # lucidlint: ignore record-shape the GitHub payload is the wire format; reading it here is this function's job
        def text(key: str) -> str:
            return str(node.get(key) or "-")

        return cls(
            state=text("state"),
            head=text("headRefOid"),
            decision=text("reviewDecision"),
            base=text("baseRefName"),
            url=text("url"),
            merge_state=text("mergeStateStatus"),
        )

    @property
    def finished(self) -> bool:
        return self.state in ("MERGED", "CLOSED")

    @property
    def behind(self) -> bool:
        return self.merge_state == "BEHIND"


@dataclass(frozen=True)
class CheckReport:
    """What the check list says about readiness, and what is worth sending."""

    blocked: int
    failing: list[str]


@dataclass(frozen=True)
class Verdict:
    """`pr-ready`'s answer: the verdict, and the line that carried it."""

    ready: bool
    line: str


@dataclass(frozen=True)
class Settings:
    pr: int
    repo: str
    agent: str
    interval: int
    timeout: int = 30
    send_timeout: int = 120
    root: Path = Path(".")

    @property
    def slug(self) -> str:
        return f"{self.repo}#{self.pr}"


def warn(message: str) -> None:
    """One line on stderr: a read that did not answer, or a send that failed."""
    print(f"pr-desk-watch: {message}", file=sys.stderr)


class Github:
    """Every read of GitHub state, each bounded by the timeout.

    A read that fails returns None, never an empty answer: the caller
    decides what unknown means for the notice it is about to send.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def pull(self) -> PullRequest | None:
        result = run(
            [
                "gh", "pr", "view", str(self.settings.pr),
                "--repo", self.settings.repo,
                "--json", "state,headRefOid,reviewDecision,baseRefName,url,mergeStateStatus",
            ],
            self.settings.timeout,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        try:
            return PullRequest.from_api(json.loads(result.stdout))
        except json.JSONDecodeError:
            return None

    def required_contexts(self, base: str) -> list[str] | None:
        """The base's required contexts, or None when GitHub will not say.

        Both sources are read: a partial list would drop a required check, so
        one unreadable source makes the whole answer unknown.
        """
        owner, _, name = self.settings.repo.partition("/")
        classic = run(
            [
                "gh", "api", "graphql",
                "-f", "query=query($o:String!,$n:String!,$b:String!){repository(owner:$o,name:$n){ref(qualifiedName:$b){branchProtectionRule{requiredStatusCheckContexts}}}}",
                "-f", f"o={owner}", "-f", f"n={name}", "-f", f"b=refs/heads/{base}",
            ],
            self.settings.timeout,
        )
        rules = run(
            ["gh", "api", f"repos/{self.settings.repo}/rules/branches/{base}"],
            self.settings.timeout,
        )
        if classic.returncode != 0 or rules.returncode != 0:
            return None
        contexts: set[str] = set()
        try:
            classic_data = json.loads(classic.stdout or "{}")
            rule = (
                classic_data.get("data", {}).get("repository", {}).get("ref") or {}
            ).get("branchProtectionRule") or {}
            contexts.update(rule.get("requiredStatusCheckContexts") or [])
            for entry in json.loads(rules.stdout or "[]"):
                if entry.get("type") != "required_status_checks":
                    continue
                for check in (entry.get("parameters") or {}).get(
                    "required_status_checks", []
                ):
                    contexts.add(check.get("context", ""))
        except json.JSONDecodeError:
            return None
        return sorted(context for context in contexts if context)

    def checks_on(self, head: str) -> list[Check] | None:
        """The check runs on a head, one per name, or None when unknown."""
        if not head or head == "-":
            warn("no head sha to read checks from — holding readiness")
            return None
        result = run(
            [
                "gh", "api", "--paginate",
                f"repos/{self.settings.repo}/commits/{head}/check-runs?per_page=100&filter=latest",
            ],
            self.settings.timeout,
        )
        if result.returncode != 0:
            warn(f"check-runs unreadable on {head[:7]} — holding readiness")
            return None
        try:
            checks = checks_from_pages(result.stdout)
        except WatchError:
            warn(f"check-runs on {head[:7]} are unreadable — holding readiness")
            return None
        if not checks:
            warn(f"no check-runs on {head[:7]} — holding readiness")
            return None
        return latest_by_name(checks)

    def unanswered_threads(self) -> list[str] | None:
        """The unanswered thread ids, or None when pr-threads could not answer.

        Exit 1 is a verdict, not a failure: `pr-threads --ids` prints the ids it
        found and exits 1 because work remains. Anything above 1 is the tool
        failing, which is the only case that leaves the state unknown.
        """
        result = run(
            ["pr-threads", str(self.settings.pr), "--repo", self.settings.repo, "--ids"],
            self.settings.timeout,
        )
        if result.returncode > 1:
            warn("pr-threads did not answer — thread state unknown")
            return None
        return sorted(line.strip() for line in result.stdout.splitlines() if line.strip())

    def ready_verdict(self) -> Verdict:
        """`pr-ready`'s answer, for the ready notice and for the log."""
        result = run(
            [
                "pr-ready", str(self.settings.pr), "--repo", self.settings.repo,
                "--root", str(self.settings.root), "--no-wait",
            ],
            self.settings.timeout,
        )
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        # The verdict is the last line; the facts above it are the evidence.
        verdict = lines[-1] if lines else ""
        return Verdict(
            ready=result.returncode == 0 and verdict.startswith("READY:"),
            line=verdict,
        )

@dataclass
class Keys:
    """The last state each notice reported. Unset means "owed"."""

    threads: str = ""
    checks: str = ""
    behind: str = ""
    ready: str = ""


@dataclass
class Watcher:
    """The notices, their keys, and the one session that receives them."""

    settings: Settings
    gh: Github
    keys: Keys = field(default_factory=Keys)
    required: list[str] = field(default_factory=list)
    required_for: str = ""

    # ---- sending ---------------------------------------------------------

    def notify(self, body: str) -> bool:
        """Send one notice; a failure leaves the caller's key unset.

        A send gets its own, longer bound: `paseo send` waits on the relay, and a
        message that took longer than a read timeout was being killed after the
        person had already received it — so the key stayed unset and every pass
        sent it again.
        """
        result = run(
            ["paseo", "send", self.settings.agent, body], self.settings.send_timeout
        )
        if result.returncode == 0:
            return True
        said = (result.stderr or result.stdout or "no message").strip().replace("\n", " ")
        warn(f"send to {self.settings.agent} failed — {said} — retrying next pass")
        return False

    def rearm(self, kind: str) -> None:
        """Forget the last notice of this kind.

        Only the thread key needs it: thread ids are stable, so a thread answered
        and then re-raised carries the same key and clearing is what lets it
        notify again. Every other key holds the head, so a new head differs by
        itself — and clearing on a transient state repeated the notice.
        """
        setattr(self.keys, kind, "")

    def announce(self, kind: str, key: str, body: str) -> None:
        if getattr(self.keys, kind) == key:
            return
        if self.notify(body):
            setattr(self.keys, kind, key)

    # ---- one pass --------------------------------------------------------

    def pass_once(self) -> bool:
        """One poll. Returns False when the PR is finished."""
        pull = self.gh.pull()
        if pull is None:
            warn(f"cannot read {self.settings.slug} — still watching")
            return True
        if pull.finished:
            print(f"PR {self.settings.slug} is {pull.state} — watcher done")
            return False

        if pull.base != self.required_for:
            contexts = self.gh.required_contexts(pull.base)
            if contexts is None:
                warn(
                    f"required contexts unreadable for origin/{pull.base} — every check counts"
                )
                contexts = []
            self.required, self.required_for = contexts, pull.base

        self.report_threads(pull)
        check_report = self.report_checks(pull)
        self.report_behind(pull)
        self.report_ready(pull, check_report)
        return True

    def report_threads(self, pull: PullRequest) -> None:
        threads = self.gh.unanswered_threads()
        if not threads:
            self.rearm("threads")
            return
        count = len(threads)
        self.announce(
            "threads",
            "\n".join(threads),
            f"PR {self.settings.slug}: {count} unanswered review thread(s) on "
            f"{pull.head[:7]}. Run: pr-threads {self.settings.pr} --repo "
            f"{self.settings.repo} — answer each with evidence, fix what is real, "
            "push once.",
        )

    def report_checks(self, pull: PullRequest) -> CheckReport:
        """Report failing required checks, and say how many are not green.

        Unknown is reported as blocked: readiness needs zero, and a list that
        could not be read has verified nothing.
        """
        checks = self.gh.checks_on(pull.head)
        if checks is None:
            return CheckReport(blocked=1, failing=[])
        wanted = set(self.required)
        considered = [check for check in checks if not wanted or check.name in wanted]
        # Two ways a required check is not green: it ran and did not pass, or it
        # never reported at all — GitHub's "expected", which nothing verified.
        not_green = {check.name for check in considered if not check.passed}
        never_ran = wanted - {check.name for check in checks}
        blocked = len(not_green | never_ran)
        failing = sorted({check.name for check in considered if check.failed})
        if not failing:
            return CheckReport(blocked=blocked, failing=[])
        self.announce(
            "checks",
            f"{pull.head} {', '.join(failing)}",
            f"PR {self.settings.slug}: failing required check(s) on "
            f"{pull.head[:7]}: {', '.join(failing)}. Read the failing step, fix the "
            "cause, push once.",
        )
        return CheckReport(blocked=blocked, failing=failing)

    def report_behind(self, pull: PullRequest) -> None:
        if not pull.behind:
            return
        self.announce(
            "behind",
            f"{pull.head} behind",
            f"PR {self.settings.slug} is behind origin/{pull.base} on "
            f"{pull.head[:7]}. Update the branch (merge origin/{pull.base} into the "
            "head), then let the checks run.",
        )

    def report_ready(self, pull: PullRequest, check_report: CheckReport) -> None:
        # No rearming: the key is the head, so a new head notifies again by
        # itself. Clearing on a transient not-ready — a check run in flight, a
        # pr-ready timeout — sent the same notice on every pass.
        if check_report.blocked or pull.decision == "APPROVED" or pull.behind:
            return
        verdict = self.gh.ready_verdict()
        if not verdict.ready:
            if not verdict.line.startswith("BLOCKED:"):
                warn(f"pr-ready gave no verdict — {verdict.line}".rstrip(" —"))
            return
        self.announce(
            "ready",
            pull.head,
            f"PR {self.settings.slug} is ready for the person's review — "
            f"{pull.url} (head {pull.head[:7]}: merges cleanly into "
            f"origin/{pull.base}, required checks green, no unanswered threads). "
            "Relay it: the review is the only step left, and this watcher will "
            "not approve, resolve or merge.",
        )


def env_seconds(name: str, default: int) -> int:
    """A positive whole number of seconds, from the environment or the default."""
    raw = os.environ.get(name) or str(default)  # empty is unset, not invalid
    if not raw.isdigit() or int(raw) < 1:
        raise WatchError(
            f"{name} must be a positive whole number of seconds, got {raw!r}"
        )
    return int(raw)


def settings_from(pr_arg: str, repo_arg: str | None, interval_arg: str) -> Settings:
    if not pr_arg.isdigit():
        raise WatchError(f"<pr> must be a pull request number, got {pr_arg!r}")
    if not interval_arg.isdigit() or int(interval_arg) < 1:
        raise WatchError(
            f"interval-seconds must be a positive whole number, got {interval_arg!r}"
        )
    agent = os.environ.get("PR_DESK_AGENT", "")
    if not agent:
        raise WatchError("PR_DESK_AGENT is not set — name the session that owns this PR")
    timeout = env_seconds("PR_DESK_WATCH_TIMEOUT", Settings.timeout)
    send_timeout = env_seconds("PR_DESK_WATCH_SEND_TIMEOUT", Settings.send_timeout)
    repo = repo_arg or ""
    if not repo:
        result = run(["gh", "repo", "view", "--json", "nameWithOwner"], timeout)
        if result.returncode != 0:
            raise WatchError("not in a checkout, and no owner/name given")
        try:
            repo = str(json.loads(result.stdout).get("nameWithOwner") or "")
        except json.JSONDecodeError as exc:
            raise WatchError("cannot read the repo's name") from exc
        if not repo:
            raise WatchError("not in a checkout, and no owner/name given")
    return Settings(
        pr=int(pr_arg),
        repo=repo,
        agent=agent,
        interval=int(interval_arg),
        timeout=timeout,
        send_timeout=send_timeout,
        root=Path(os.environ.get("PR_READY_ROOT", ".")).resolve(),
    )


def watch(settings: Settings, once: bool) -> int:
    watcher = Watcher(settings=settings, gh=Github(settings))
    while True:
        if not watcher.pass_once():
            return 0
        if once:
            return 0
        time.sleep(settings.interval)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pr")
    parser.add_argument("repo", nargs="?")
    parser.add_argument("interval", nargs="?", default="60")
    parser.add_argument(
        "--once", action="store_true", help="run one pass and exit (tests, cron)"
    )
    args = parser.parse_args(argv)
    try:
        settings = settings_from(args.pr, args.repo, args.interval)
    except WatchError as exc:
        print(f"pr-desk-watch: {exc}", file=sys.stderr)
        return 2
    return watch(settings, args.once)


if __name__ == "__main__":
    sys.exit(main())
