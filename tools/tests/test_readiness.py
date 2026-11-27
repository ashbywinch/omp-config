"""The readiness predicate: what makes a PR ready, over records handed to it.

The subject is the decision, not a read: every input here is a record.
"""

from __future__ import annotations

import unittest

from tools.desk.model import Check, MergeState, PullRequest, Reading, Thread
from tools.desk.readiness import evaluate

SHA = "a" * 40


def pull(**overrides) -> PullRequest:
    fields = {
        "number": 1,
        "repo": "owner/name",
        "state": "OPEN",
        "head": SHA,
        "base": "main",
        "url": "https://github.com/owner/name/pull/1",
        "decision": "",
        "merge_state": "CLEAN",
        "draft": False,
    }
    fields.update(overrides)
    return PullRequest(**fields)


def check(name="ci", status="completed", conclusion="success") -> Check:
    return Check(name=name, status=status, conclusion=conclusion, started="")


def thread(thread_id="T1") -> Thread:
    return Thread(id=thread_id, path="a.py", line=1, resolved=False, last_author="reviewer")


def verdict(
    *,
    the_pull: PullRequest | None = None,
    threads: list[Thread] | None = None,
    checks: list[Check] | None = None,
    contexts: list[str] | None = None,
    merge_state: MergeState | None = None,
):
    return evaluate(
        Reading(
            pull=the_pull or pull(),
            threads=threads if threads is not None else [],
            checks=checks if checks is not None else [check()],
            contexts=contexts if contexts is not None else ["ci"],
            merge=merge_state or MergeState(base="main", merges=True, behind=False),
        )
    )


def fact(result, name: str):
    return next(f for f in result.facts if f.name == name)


class ReadyTest(unittest.TestCase):
    def test_a_clean_pr_is_ready(self):
        self.assertTrue(verdict().ready)

    def test_every_fact_is_reported(self):
        self.assertEqual(
            [f.name for f in verdict().facts],
            ["head", "checks", "merge", "threads", "draft"],
        )

    def test_one_failed_fact_blocks_whatever_the_others_say(self):
        self.assertFalse(verdict(threads=[thread()]).ready)
        self.assertFalse(verdict(the_pull=pull(draft=True)).ready)


class RecordTest(unittest.TestCase):
    """A record either carries what a verdict needs or is not built."""

    def test_a_reading_holds_all_five_records(self):
        with self.assertRaises(ValueError):
            Reading(
                pull=pull(),
                threads=[],
                checks=[check()],
                contexts=None,  # type: ignore[arg-type]  # the hole is what the record must refuse
                merge=MergeState(base="main", merges=True, behind=False),
            )

    def test_a_merge_state_names_its_base(self):
        with self.assertRaises(ValueError):
            MergeState(base="-", merges=True, behind=False)


class HeadTest(unittest.TestCase):
    def test_a_missing_head_blocks(self):
        result = verdict(the_pull=pull(head="-"))
        self.assertFalse(fact(result, "head").ok)
        self.assertFalse(result.ready)


class ChecksTest(unittest.TestCase):
    def test_a_failing_required_check_blocks_and_is_named(self):
        result = verdict(checks=[check(conclusion="failure")])
        self.assertFalse(result.ready)
        self.assertIn("ci did not pass (failure)", fact(result, "checks").detail)

    def test_a_required_context_with_no_run_blocks(self):
        result = verdict(checks=[check(name="lint")], contexts=["ci"])
        self.assertIn("ci has no run on this head", fact(result, "checks").detail)
        self.assertFalse(result.ready)

    def test_an_empty_required_list_passes(self):
        result = verdict(checks=[check(conclusion="failure")], contexts=[])
        self.assertTrue(fact(result, "checks").ok)
        self.assertTrue(result.ready)

    def test_a_non_required_failure_cannot_block(self):
        checks = [check(name="ci"), check(name="lint", conclusion="failure")]
        self.assertTrue(verdict(checks=checks, contexts=["ci"]).ready)

    def test_a_running_required_check_blocks(self):
        result = verdict(checks=[check(status="in_progress", conclusion=None)])
        self.assertFalse(fact(result, "checks").ok)

    def test_neutral_and_skipped_pass(self):
        checks = [check(conclusion="neutral"), check(name="docs", conclusion="skipped")]
        self.assertTrue(verdict(checks=checks, contexts=["ci", "docs"]).ready)

    def test_a_cancelled_check_blocks(self):
        result = verdict(checks=[check(conclusion="cancelled")])
        self.assertFalse(fact(result, "checks").ok)

    def test_a_check_that_failed_to_start_blocks(self):
        """`startup_failure` is in the merge gate's list, so the predicate must see it."""
        result = verdict(checks=[check(conclusion="startup_failure")])
        self.assertFalse(fact(result, "checks").ok)
        self.assertIn("startup_failure", fact(result, "checks").detail)


class MergeTest(unittest.TestCase):
    def test_a_conflict_blocks(self):
        result = verdict(merge_state=MergeState(base="main", merges=False, behind=False))
        self.assertIn("conflicts with origin/main", fact(result, "merge").detail)

    def test_a_head_behind_its_base_blocks(self):
        result = verdict(merge_state=MergeState(base="main", merges=True, behind=True))
        self.assertIn("behind origin/main", fact(result, "merge").detail)
        self.assertFalse(result.ready)

    def test_a_blocked_approval_gate_is_not_a_merge_failure(self):
        # MergeState says what GitHub's BLOCKED already means: the merge is fine.
        self.assertTrue(verdict(merge_state=MergeState(base="main", merges=True, behind=False)).ready)


class ThreadTest(unittest.TestCase):
    def test_an_unanswered_thread_blocks_and_is_counted(self):
        result = verdict(threads=[thread("T1"), thread("T2")])
        self.assertIn("2 unanswered thread(s)", fact(result, "threads").detail)
        self.assertFalse(result.ready)


class DraftTest(unittest.TestCase):
    def test_a_draft_blocks(self):
        result = verdict(the_pull=pull(draft=True))
        self.assertIn("draft", fact(result, "draft").detail)
        self.assertFalse(result.ready)


if __name__ == "__main__":
    unittest.main()
