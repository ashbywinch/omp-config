"""Tests for tools/pr_ready.py — the four facts, and absence is not success.

The load-bearing rules: zero check-runs is blocked (a conflicted PR starts no
run), a cancelled check is blocked and named, a head behind its base is blocked
even when it merges cleanly, and one failed fact blocks the others however green
they are.
"""

import subprocess
import unittest
from pathlib import Path

import tools.pr_ready as pr_ready
from tools.pr_ready import (
    Check,
    Fact,
    PullRequest,
    Target,
    Verdict,
    failed,
    latest_by_name,
    next_step,
    verdict,
)


def check(name: str = "ci", status: str = "completed", conclusion: str | None = "success") -> Check:
    return Check(name=name, status=status, conclusion=conclusion)


def facts(*oks: bool) -> list[Fact]:
    names = ("merge", "base", "checks", "threads")
    return [Fact(name=name, ok=ok, detail="") for name, ok in zip(names, oks)]


class Completed:
    """The slice of CompletedProcess the tool reads."""

    def __init__(self, args: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""):
        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeGit:
    """Answer git like a checkout would, and keep every command it was asked."""

    def __init__(self, *, ancestor: int = 0, behind: str = "0", stderr: str = ""):
        self.ancestor = ancestor
        self.behind = behind
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], cwd: Path | None = None) -> Completed:
        self.calls.append(args)
        if args[1:2] == ["merge-base"]:
            return Completed(args, self.ancestor, "", self.stderr)
        if args[1:2] == ["rev-list"]:
            return Completed(args, 0, f"{self.behind}\n")
        return Completed(args, 0)


class BaseTest(unittest.TestCase):
    """A PR behind its base is blocked, and the base is origin/<ref>."""

    def base(self, fake: FakeGit, sha: str = "abc123") -> Fact:
        original = pr_ready.run
        pr_ready.run = fake
        try:
            return PullRequest(repo="owner/name", number="1", root=Path(".")).base(Target(sha=sha, base="main"))
        finally:
            pr_ready.run = original

    def test_a_head_containing_the_base_tip_passes(self):
        fact = self.base(FakeGit(ancestor=0))
        self.assertTrue(fact.ok)
        self.assertIn("origin/main", fact.detail)

    def test_a_head_behind_the_base_fails_with_the_count(self):
        fact = self.base(FakeGit(ancestor=1, behind="3"))
        self.assertFalse(fact.ok)
        self.assertIn("behind origin/main by 3 commits", fact.detail)
        self.assertIn("merge the base first", fact.detail)

    def test_one_commit_behind_is_named_in_the_singular(self):
        self.assertIn("by 1 commit ", self.base(FakeGit(ancestor=1, behind="1")).detail)

    def test_the_comparison_names_origin_never_a_local_branch(self):
        fake = FakeGit(ancestor=1, behind="2")
        self.base(fake)
        self.assertIn(["git", "merge-base", "--is-ancestor", "origin/main", "abc123"], fake.calls)
        self.assertIn(["git", "rev-list", "--count", "abc123..origin/main"], fake.calls)

    def test_an_unreadable_base_fails_rather_than_passing(self):
        fact = self.base(FakeGit(ancestor=128, stderr="fatal: bad revision 'origin/main'"))
        self.assertFalse(fact.ok)
        self.assertIn("cannot compare", fact.detail)

    def test_no_head_sha_fails_the_fact(self):
        self.assertFalse(self.base(FakeGit(), sha="").ok)

    def test_behind_blocks_even_when_the_merge_is_clean(self):
        """The reported bug: clean merge, green checks, no threads — and behind."""
        state = facts(True, False, True, True)
        self.assertEqual(verdict(state), Verdict.BLOCKED)
        self.assertIn("behind", next_step(state))


class ChecksTest(unittest.TestCase):
    """A check passes only when it is completed and successful."""

    def test_a_completed_success_passes(self):
        self.assertEqual(failed([check()]), [])

    def test_a_running_check_does_not_pass(self):
        self.assertEqual(len(failed([check(status="in_progress", conclusion=None)])), 1)

    def test_a_cancelled_check_does_not_pass(self):
        self.assertEqual(len(failed([check(conclusion="cancelled")])), 1)

    def test_a_failure_is_named(self):
        self.assertIn("ci", failed([check(conclusion="failure")])[0])


class SupersededTest(unittest.TestCase):
    """A re-run replaces the run before it; a cancelled run is the replaced one."""

    def test_a_later_success_supersedes_an_earlier_cancelled_run(self):
        runs = [check(conclusion="cancelled"), check(conclusion="success")]
        self.assertEqual(failed(latest_by_name(runs)), [])

    def test_a_run_cancelled_after_a_success_still_reports_the_latest(self):
        """The PR head that ran arm six times: cancelled, success, cancelled, success."""
        runs = [
            Check(name="arm", status="completed", conclusion="cancelled", started="13:26:45"),
            Check(name="arm", status="completed", conclusion="success", started="13:26:49"),
            Check(name="arm", status="completed", conclusion="cancelled", started="13:26:58"),
            Check(name="arm", status="completed", conclusion="success", started="13:27:03"),
        ]
        self.assertEqual(failed(latest_by_name(runs)), [])

    def test_a_cancelled_run_with_no_successor_fails(self):
        runs = [check(name="arm", conclusion="success"), check(name="arm", conclusion="cancelled")]
        self.assertEqual(len(failed(latest_by_name(runs))), 1)

    def test_one_entry_per_name(self):
        runs = [check(name="arm", conclusion="success"), check(name="arm", conclusion="success")]
        self.assertEqual(len(latest_by_name(runs)), 1)


class ZeroChecksTest(unittest.TestCase):
    """Nothing ran is not the same as everything passed, and the cause matters."""

    def report(self, check_runs: list[dict], sha: str = "abc123") -> Fact:
        original = pr_ready.gh_json
        pr_ready.gh_json = lambda args: {"check_runs": check_runs}
        try:
            pr = PullRequest(repo="owner/name", number="1", root=Path("."))
            return pr.checks(Target(sha=sha, base="main"))
        finally:
            pr_ready.gh_json = original

    def test_no_check_runs_fails_the_fact(self):
        fact = self.report([])
        self.assertFalse(fact.ok)
        self.assertIn("0 check-runs", fact.detail)

    def test_no_head_sha_fails_the_fact(self):
        self.assertFalse(self.report([], sha="").ok)

    def test_all_successful_passes(self):
        fact = self.report([{"name": "ci", "status": "completed", "conclusion": "success"}])
        self.assertTrue(fact.ok)


class VerdictTest(unittest.TestCase):
    """READY needs every fact; one failure blocks the rest."""

    def test_all_four_hold_is_ready(self):
        self.assertEqual(verdict(facts(True, True, True, True)), Verdict.READY)

    def test_one_failure_blocks_whatever_the_others_say(self):
        self.assertEqual(verdict(facts(True, True, False, True)), Verdict.BLOCKED)

    def test_the_next_step_names_each_broken_fact(self):
        step = next_step(facts(False, True, True, False))
        self.assertIn("conflict", step)
        self.assertIn("thread", step)
        self.assertNotIn("failing check", step)

    def test_ready_says_the_merge_is_the_users(self):
        self.assertIn("user", next_step(facts(True, True, True, True)))
