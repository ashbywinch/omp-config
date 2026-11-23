"""Tests for `tools/pr_ready.py`."""

import subprocess
import unittest
from pathlib import Path

from tools.pr_ready import (
    Check,
    Fact,
    PullRequest,
    Target,
    Verdict,
    failure_lines,
    latest_by_name,
    next_step,
    verdict,
)


def check(name: str = "ci", status: str = "completed", conclusion: str | None = "success") -> Check:
    return Check(name=name, status=status, conclusion=conclusion)


def facts(*oks: bool) -> list[Fact]:
    names = ("merge", "base", "checks", "threads")
    return [Fact(name=name, ok=ok, detail="evidence") for name, ok in zip(names, oks)]


class FakeGit:
    def __init__(
        self,
        *,
        ancestor: int = 0,
        behind: str = "0",
        stderr: str = "",
        head: str = "abc123",
        merge_tree: int = 0,
        merge_stdout: str = "",
        rev_list: int = 0,
    ):
        self.ancestor = ancestor
        self.behind = behind
        self.stderr = stderr
        self.head = head
        self.merge_tree = merge_tree
        self.merge_stdout = merge_stdout
        self.rev_list = rev_list
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if args[1:2] == ["cat-file"]:
            return subprocess.CompletedProcess(args, 0 if args[-1] == f"{self.head}^{{commit}}" else 1)
        if args[1:2] == ["merge-base"]:
            return subprocess.CompletedProcess(args, self.ancestor, "", self.stderr)
        if args[1:2] == ["rev-list"]:
            return subprocess.CompletedProcess(args, self.rev_list, f"{self.behind}\n", self.stderr)
        if args[1:2] == ["merge-tree"]:
            return subprocess.CompletedProcess(args, self.merge_tree, self.merge_stdout, self.stderr)
        return subprocess.CompletedProcess(args, 0)


class BehindBaseTest(unittest.TestCase):
    def base(self, fake: FakeGit, sha: str = "abc123") -> Fact:
        pr = PullRequest(repo="owner/name", number="1", root=Path("."), run=fake)
        return pr.base(Target(sha=sha, base="main"))

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

    def test_the_origin_base_is_built_from_origin(self):
        self.assertEqual(Target(sha="abc123", base="main").origin_base, "origin/main")

    def test_the_base_is_fetched_on_every_call(self):
        fake = FakeGit()
        self.base(fake)
        self.assertIn(["git", "fetch", "origin", "+refs/heads/main:refs/remotes/origin/main"], fake.calls)

    def test_an_unreadable_base_fails_rather_than_passing(self):
        fact = self.base(FakeGit(ancestor=128, stderr="fatal: bad revision 'origin/main'"))
        self.assertFalse(fact.ok)
        self.assertIn("cannot compare", fact.detail)

    def test_a_silent_git_failure_names_the_command_and_exit_code(self):
        fact = self.base(FakeGit(ancestor=128))
        self.assertIn("git merge-base` exited 128", fact.detail)

    def test_a_failed_count_still_blocks_and_names_the_reason(self):
        fact = self.base(FakeGit(ancestor=1, rev_list=3))
        self.assertFalse(fact.ok)
        self.assertIn("git rev-list` exited 3", fact.detail)
        self.assertIn("merge the base first", fact.detail)

    def test_no_head_sha_fails_the_fact(self):
        self.assertFalse(self.base(FakeGit(), sha="").ok)

    def test_an_unfetched_head_fails_the_fact(self):
        self.assertFalse(self.base(FakeGit(head="abc123"), sha="def456").ok)

    def test_behind_blocks_even_when_the_merge_is_clean(self):
        state = facts(True, False, True, True)
        self.assertEqual(verdict(state), Verdict.BLOCKED)
        self.assertIn("behind", next_step(state))


class MergeTest(unittest.TestCase):
    def merge(self, fake: FakeGit, sha: str = "abc123") -> Fact:
        pr = PullRequest(repo="owner/name", number="1", root=Path("."), run=fake)
        return pr.merge(Target(sha=sha, base="main"))

    def test_a_clean_merge_passes(self):
        self.assertTrue(self.merge(FakeGit()).ok)

    def test_a_conflict_reads_the_tree_output(self):
        fact = self.merge(FakeGit(merge_tree=1, merge_stdout="CONFLICT (content): letter.txt"))
        self.assertIn("conflicts with origin/main", fact.detail)
        self.assertIn("CONFLICT", fact.detail)

    def test_a_merge_that_is_not_a_conflict_names_the_error(self):
        fact = self.merge(FakeGit(merge_tree=2, stderr="fatal: not a valid object name"))
        self.assertIn("cannot merge against origin/main", fact.detail)
        self.assertIn("not a valid object name", fact.detail)

    def test_a_head_that_is_not_present_fails_the_merge_fact(self):
        self.assertIn("no head sha to merge", self.merge(FakeGit(head="abc123"), sha="def456").detail)


class ChecksTest(unittest.TestCase):
    def test_a_completed_success_passes(self):
        self.assertEqual(failure_lines([check()], None), [])

    def test_neutral_and_skipped_pass(self):
        self.assertEqual(failure_lines([check(conclusion="neutral"), check(name="docs", conclusion="skipped")], None), [])

    def test_a_running_check_does_not_pass(self):
        self.assertEqual(len(failure_lines([check(status="in_progress", conclusion=None)], None)), 1)

    def test_a_cancelled_check_does_not_pass(self):
        self.assertEqual(len(failure_lines([check(conclusion="cancelled")], None)), 1)

    def test_a_failure_is_named(self):
        self.assertIn("ci", failure_lines([check(conclusion="failure")], None)[0])


class RequiredTest(unittest.TestCase):
    def test_a_check_the_branch_does_not_require_cannot_block(self):
        checks = [check(name="ci"), check(name="lint", conclusion="failure")]
        self.assertEqual(failure_lines(checks, {"ci"}), [])

    def test_a_required_context_that_did_not_pass_is_named(self):
        self.assertIn("ci is completed failure", failure_lines([check(conclusion="failure")], {"ci"})[0])

    def test_a_required_context_with_no_run_fails(self):
        self.assertIn("ci has no run on this sha", failure_lines([check(name="lint")], {"ci"})[0])

    def test_an_unreadable_required_list_makes_every_check_count(self):
        self.assertEqual(len(failure_lines([check(conclusion="failure")], None)), 1)

    def test_an_empty_required_set_makes_every_check_count(self):
        self.assertEqual(len(failure_lines([check(conclusion="failure")], set())), 1)


class SupersededTest(unittest.TestCase):
    def test_a_later_success_supersedes_an_earlier_cancelled_run(self):
        runs = [check(conclusion="cancelled"), check(conclusion="success")]
        self.assertEqual(failure_lines(latest_by_name(runs), None), [])

    def test_a_run_cancelled_after_a_success_still_reports_the_latest(self):
        runs = [
            Check(name="arm", status="completed", conclusion="cancelled", started="13:26:45"),
            Check(name="arm", status="completed", conclusion="success", started="13:26:49"),
            Check(name="arm", status="completed", conclusion="cancelled", started="13:26:58"),
            Check(name="arm", status="completed", conclusion="success", started="13:27:03"),
        ]
        self.assertEqual(failure_lines(latest_by_name(runs), None), [])

    def test_a_cancelled_run_with_no_successor_fails(self):
        runs = [check(name="arm", conclusion="success"), check(name="arm", conclusion="cancelled")]
        self.assertEqual(len(failure_lines(latest_by_name(runs), None)), 1)

    def test_one_entry_per_name(self):
        runs = [check(name="arm", conclusion="success"), check(name="arm", conclusion="success")]
        self.assertEqual(len(latest_by_name(runs)), 1)


class ZeroChecksTest(unittest.TestCase):
    def report(
        self,
        check_runs: list[dict],
        sha: str = "abc123",
        rule: tuple[str, ...] = (),
        graphql_fails: bool = False,
    ) -> Fact:
        graphql: dict = {} if graphql_fails else {
            "data": {"repository": {"ref": {"branchProtectionRule": {"requiredStatusCheckContexts": list(rule)}}}}
        }
        api = lambda args: graphql if "graphql" in args else {"check_runs": check_runs}
        pr = PullRequest(repo="owner/name", number="1", root=Path("."), api=api)
        return pr.checks(Target(sha=sha, base="main"))

    def test_no_check_runs_fails_the_fact(self):
        fact = self.report([])
        self.assertFalse(fact.ok)
        self.assertIn("0 check-runs", fact.detail)

    def test_no_head_sha_fails_the_fact(self):
        self.assertFalse(self.report([], sha="").ok)

    def test_all_successful_passes(self):
        fact = self.report([{"name": "ci", "status": "completed", "conclusion": "success"}])
        self.assertTrue(fact.ok)

    def test_a_non_required_failure_does_not_block(self):
        runs = [
            {"name": "ci", "status": "completed", "conclusion": "success"},
            {"name": "lint", "status": "completed", "conclusion": "failure"},
        ]
        self.assertTrue(self.report(runs, rule=("ci",)).ok)

    def test_a_required_context_with_no_run_fails_the_fact(self):
        runs = [{"name": "lint", "status": "completed", "conclusion": "success"}]
        fact = self.report(runs, rule=("ci",))
        self.assertFalse(fact.ok)
        self.assertIn("ci has no run", fact.detail)

    def test_an_unreadable_required_list_is_named_in_the_fact(self):
        runs = [{"name": "ci", "status": "completed", "conclusion": "success"}]
        fact = self.report(runs, graphql_fails=True)
        self.assertTrue(fact.ok)
        self.assertIn("required contexts unreadable", fact.detail)


class WireTest(unittest.TestCase):
    def required(self, envelope: dict) -> set[str] | None:
        pr = PullRequest(repo="owner/name", number="1", root=Path("."), api=lambda args: envelope)
        return pr._required_contexts(Target(sha="abc123", base="main"))

    def test_a_null_repository_reads_as_no_required_contexts(self):
        self.assertEqual(self.required({"data": {"repository": None}}), set())

    def test_a_null_ref_reads_as_no_required_contexts(self):
        self.assertEqual(self.required({"data": {"repository": {"ref": None}}}), set())

    def test_a_null_rule_reads_as_no_required_contexts(self):
        self.assertEqual(self.required({"data": {"repository": {"ref": {"branchProtectionRule": None}}}}), set())

    def test_a_failed_call_is_not_an_empty_rule(self):
        self.assertIsNone(self.required({}))


class EvidenceTest(unittest.TestCase):
    def test_a_fact_without_evidence_is_refused(self):
        with self.assertRaises(ValueError):
            Fact(name="merge", ok=True, detail="   ")


class VerdictTest(unittest.TestCase):
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
