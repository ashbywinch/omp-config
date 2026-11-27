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

Every GitHub read goes through `tools/desk/`, and readiness is the pure
`readiness.evaluate` over the records read here. This file decides what to say.

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
from tools.desk.identity import answering_login
from tools.desk.merge import Merge
from tools.desk.model import Check, MergeState, PullRequest, Thread
from tools.desk.noticelog import NoticeLog
from tools.desk.pulls import PullRequests
from tools.desk.readiness import evaluate
from tools.desk.repository import Repository
from tools.desk.threads import Threads, unanswered


class WatchError(Exception):
    """A setting or an input that cannot be used, reported before any polling."""


@dataclass(frozen=True)
class Settings:
    pr: int
    repo: str
    agent: str
    interval: int
    timeout: int = 30
    send_timeout: int = 120
    root: Path = Path(".")
    me: str = "omp-harness[bot]"

    @property
    def slug(self) -> str:
        return f"{self.repo}#{self.pr}"


def warn(message: str) -> None:
    """One line on stderr: a read that did not answer, or a send that failed."""
    print(f"pr-desk-watch: {message}", file=sys.stderr)


@dataclass
class Notices:
    """The send, and the keys the log records only when it succeeds."""

    agent: str
    send_timeout: int
    log: NoticeLog

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
        """Forget the last notice of this kind: its condition no longer holds.

        The next pass that finds the condition again owes a notice.
        """
        self.log.set(kind, "")

    def announce(self, kind: str, key: str, body: str) -> None:
        if self.log.get(kind) == key:
            return
        if self.notify(body):
            self.log.set(kind, key)

    def delete(self) -> None:
        """Forget every key: the PR is merged or closed."""
        self.log.delete()


@dataclass
class Watcher:
    """The notices, their keys, and the one session that receives them."""

    settings: Settings
    required: list[str] = field(default_factory=list)
    required_for: str = ""
    notices: Notices = field(init=False)
    pulls: PullRequests = field(init=False)
    review_threads: Threads = field(init=False)
    check_runs: Checks = field(init=False)
    required_contexts: Contexts = field(init=False)
    merges: Merge = field(init=False)

    def __post_init__(self) -> None:
        repo, timeout = self.settings.repo, self.settings.timeout
        self.notices = Notices(
            self.settings.agent,
            self.settings.send_timeout,
            NoticeLog.for_pr(repo, self.settings.pr),
        )
        self.pulls = PullRequests(repo, timeout)
        self.review_threads = Threads(repo, timeout)
        self.check_runs = Checks(repo, timeout)
        self.required_contexts = Contexts(repo, timeout)
        self.merges = Merge(repo, timeout, self.settings.root)

    # ---- one pass --------------------------------------------------------

    def pass_once(self) -> bool:
        """One poll. Returns False when the PR is finished."""
        try:
            pull = self.pulls.view(self.settings.pr)
        except SourceUnknown:
            warn(f"cannot read {self.settings.slug} — still watching")
            return True
        if pull.finished:
            self.notices.delete()
            print(f"PR {self.settings.slug} is {pull.state} — watcher done")
            return False

        contexts = self._required_contexts(pull)
        threads = self._unanswered()
        checks = self._checks(pull.head)
        merge_state = self._merge_state(pull)

        self.report_threads(pull, threads)
        self.report_checks(pull, checks, contexts)
        self.report_behind(pull, merge_state)
        self.report_ready(pull, threads, checks, contexts, merge_state)
        return True

    # ---- the reads that hold a notice when they cannot answer -------------

    def _required_contexts(self, pull: PullRequest) -> list[str] | None:
        if pull.base == self.required_for:
            return self.required
        try:
            contexts = self.required_contexts.required(pull.base)
        except SourceUnknown as exc:
            warn(f"{exc} — every check counts")
            return None
        self.required, self.required_for = contexts, pull.base
        return contexts

    def _unanswered(self) -> list[Thread] | None:
        try:
            threads = self.review_threads.all(self.settings.pr)
        except SourceUnknown as exc:
            warn(f"{exc} — thread state unknown")
            return None
        return unanswered(threads, self.settings.me)

    def _checks(self, head: str) -> list[Check] | None:
        try:
            return self.check_runs.on(head)
        except SourceUnknown as exc:
            warn(f"{exc} — holding readiness")
            return None

    def _merge_state(self, pull: PullRequest) -> MergeState | None:
        try:
            return self.merges.state(pull)
        except SourceUnknown as exc:
            warn(f"{exc} — holding readiness")
            return None

    # ---- the four notices ------------------------------------------------

    def report_threads(self, pull: PullRequest, threads: list[Thread] | None) -> None:
        if threads is None:
            return
        ids = sorted(thread.id for thread in threads)
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

    def report_checks(
        self, pull: PullRequest, checks: list[Check] | None, contexts: list[str] | None
    ) -> None:
        """Report failing required checks.

        While the required list is unknown, every check counts: a notice that
        names a check that did not need to pass is corrected by the next pass,
        and one that misses a required failure is the miss this notice exists to
        prevent.
        """
        if checks is None:
            return
        if contexts is None:
            considered = checks
        else:
            wanted = set(contexts)
            considered = [check for check in checks if check.name in wanted]
        failing = sorted({check.name for check in considered if check.failed})
        if not failing:
            self.notices.rearm("checks")
            return
        self.notices.announce(
            "checks",
            f"{pull.head} {', '.join(failing)}",
            f"PR {self.settings.slug}: failing required check(s) on "
            f"{pull.head[:7]}: {', '.join(failing)}. Read the failing step, fix the "
            "cause, push once.",
        )

    def report_behind(self, pull: PullRequest, merge_state: MergeState | None) -> None:
        behind = merge_state.behind if merge_state is not None else pull.behind
        if not behind:
            self.notices.rearm("behind")
            return
        self.notices.announce(
            "behind",
            pull.head,
            f"PR {self.settings.slug} is behind origin/{pull.base} on "
            f"{pull.head[:7]}. Update the branch (merge origin/{pull.base} into the "
            "head), then let the checks run.",
        )

    def report_ready(
        self,
        pull: PullRequest,
        threads: list[Thread] | None,
        checks: list[Check] | None,
        contexts: list[str] | None,
        merge_state: MergeState | None,
    ) -> None:
        if None in (threads, checks, contexts, merge_state):
            return
        verdict = evaluate(pull, threads, checks, contexts, merge_state)
        if not verdict.ready:
            self.notices.rearm("ready")
            return
        self.notices.announce("ready", pull.head, self._ready_notice(pull))

    def _ready_notice(self, pull: PullRequest) -> str:
        """The ready notice; approval changes what is left to say, not whether."""
        if pull.decision == "APPROVED":
            return (
                f"PR {self.settings.slug} is approved and clean — {pull.url} "
                f"(head {pull.head[:7]}: merges cleanly into origin/{pull.base}, "
                "required checks green, no unanswered threads). Nothing "
                "outstanding; the merge is the person's."
            )
        return (
            f"PR {self.settings.slug} is ready for the person's review — "
            f"{pull.url} (head {pull.head[:7]}: merges cleanly into "
            f"origin/{pull.base}, required checks green, no unanswered threads). "
            "Relay it: the review is the only step left, and this watcher will "
            "not approve, resolve or merge."
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
        me=answering_login(),
    )


def watch(settings: Settings, once: bool) -> int:
    NoticeLog.prune()
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
