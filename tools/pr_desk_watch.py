#!/usr/bin/env python3
"""Tell the session that owns a PR what needs doing next.

    pr-desk-watch <pr> [owner/name] [interval-seconds] [--once]

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

Every GitHub read goes through `tools/desk/`; this file decides what to say.

Design: `docs/desk-watcher.md`. Procedure: `skill://pr-desk`.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from tools.desk.checks import Checks
from tools.desk.command import run
from tools.desk.contexts import Contexts
from tools.desk.errors import SourceUnknown
from tools.desk.model import PullRequest
from tools.desk.pulls import PullRequests
from tools.desk.repository import Repository
from tools.desk.threads import Threads, unanswered


class WatchError(Exception):
    """A setting or an input that cannot be used, reported before any polling."""


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


@dataclass
class Notices:
    """The four notice keys, and the send that records one only on success.

    A key is the last state its notice reported; unset means "owed".
    """

    agent: str
    send_timeout: int
    threads: str = ""
    checks: str = ""
    behind: str = ""
    ready: str = ""

    def notify(self, body: str) -> bool:
        """Send one notice; a failure leaves the caller's key unset.

        A send gets its own, longer bound: `paseo send` waits on the relay, and a
        message that took longer than a read timeout was being killed after the
        person had already received it — so the key stayed unset and every pass
        sent it again.
        """
        result = run(["paseo", "send", self.agent, body], self.send_timeout)
        if result.returncode == 0:
            return True
        said = (result.stderr or result.stdout or "no message").strip().replace("\n", " ")
        warn(f"send to {self.agent} failed — {said} — retrying next pass")
        return False

    def rearm(self, kind: str) -> None:
        """Forget the last notice of this kind.

        Only the thread key needs it: thread ids are stable, so a thread answered
        and then re-raised carries the same key and clearing is what lets it
        notify again. Every other key holds the head, so a new head differs by
        itself — and clearing on a transient state repeated the notice.
        """
        setattr(self, kind, "")

    def announce(self, kind: str, key: str, body: str) -> None:
        if getattr(self, kind) == key:
            return
        if self.notify(body):
            setattr(self, kind, key)


@dataclass
class Watcher:
    """The notices, their keys, and the one session that receives them."""

    settings: Settings
    required: list[str] = field(default_factory=list)
    required_for: str = ""
    # The login `pr-threads` counts as mine; this watcher reads the threads
    # itself and must judge them the same way.
    me: str = "omp-harness"
    notices: Notices = field(init=False)
    pulls: PullRequests = field(init=False)
    review_threads: Threads = field(init=False)
    check_runs: Checks = field(init=False)
    required_contexts: Contexts = field(init=False)

    def __post_init__(self) -> None:
        repo, timeout = self.settings.repo, self.settings.timeout
        self.notices = Notices(self.settings.agent, self.settings.send_timeout)
        self.pulls = PullRequests(repo, timeout)
        self.review_threads = Threads(repo, timeout)
        self.check_runs = Checks(repo, timeout)
        self.required_contexts = Contexts(repo, timeout)

    # ---- one pass --------------------------------------------------------

    def pass_once(self) -> bool:
        """One poll. Returns False when the PR is finished."""
        try:
            pull = self.pulls.view(self.settings.pr)
        except SourceUnknown:
            warn(f"cannot read {self.settings.slug} — still watching")
            return True
        if pull.finished:
            print(f"PR {self.settings.slug} is {pull.state} — watcher done")
            return False

        if pull.base != self.required_for:
            try:
                contexts = self.required_contexts.required(pull.base)
            except SourceUnknown:  # lucidlint: ignore swallow when the required list cannot be read the pass continues with every check counted, which is the conservative answer the notice needs; the warn is the surface.
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
        try:
            threads = self.review_threads.all(self.settings.pr)
        except SourceUnknown as exc:
            warn(f"{exc} — thread state unknown")
            self.notices.rearm("threads")
            return
        ids = sorted(thread.id for thread in unanswered(threads, self.me))
        if not ids:
            self.notices.rearm("threads")
            return
        count = len(ids)
        self.notices.announce(
            "threads",
            "\n".join(ids),
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
        try:
            checks = self.check_runs.on(pull.head)
        except SourceUnknown as exc:
            warn(f"{exc} — holding readiness")
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
        self.notices.announce(
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
        self.notices.announce(
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
        verdict = self.ready_verdict()
        if not verdict.ready:
            if not verdict.line.startswith("BLOCKED:"):
                warn(f"pr-ready gave no verdict — {verdict.line}".rstrip(" —"))
            return
        self.notices.announce(
            "ready",
            pull.head,
            f"PR {self.settings.slug} is ready for the person's review — "
            f"{pull.url} (head {pull.head[:7]}: merges cleanly into "
            f"origin/{pull.base}, required checks green, no unanswered threads). "
            "Relay it: the review is the only step left, and this watcher will "
            "not approve, resolve or merge.",
        )

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
        try:
            repo = Repository(timeout).current()
        except SourceUnknown as exc:
            raise WatchError(str(exc)) from exc
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
    watcher = Watcher(settings=settings)
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
