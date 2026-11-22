"""Tests for tools/pr_ready.py — the three facts, and absence is not success.

The load-bearing rules: zero check-runs is blocked (a conflicted PR starts no
run), a cancelled check is blocked and named, and one failed fact blocks the
other two however green they are.
"""

import unittest
from pathlib import Path

import tools.pr_ready as pr_ready
from tools.pr_ready import Check, Fact, PullRequest, Target, Verdict, failed, next_step, verdict


def check(name: str = "ci", status: str = "completed", conclusion: str | None = "success") -> Check:
    return Check(name=name, status=status, conclusion=conclusion)


def facts(*oks: bool) -> list[Fact]:
    names = ("merge", "checks", "threads")
    return [Fact(name=name, ok=ok, detail="") for name, ok in zip(names, oks)]


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
    """READY needs all three; one failure blocks the rest."""

    def test_all_three_hold_is_ready(self):
        self.assertEqual(verdict(facts(True, True, True)), Verdict.READY)

    def test_one_failure_blocks_whatever_the_others_say(self):
        self.assertEqual(verdict(facts(True, False, True)), Verdict.BLOCKED)

    def test_the_next_step_names_each_broken_fact(self):
        step = next_step(facts(False, True, False))
        self.assertIn("conflict", step)
        self.assertIn("thread", step)
        self.assertNotIn("failing check", step)

    def test_ready_says_the_merge_is_the_users(self):
        self.assertIn("user", next_step(facts(True, True, True)))
