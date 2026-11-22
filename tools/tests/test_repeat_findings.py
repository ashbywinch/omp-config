"""Tests for tools/repeat_findings.py — which hunks were answered more than once.

The load-bearing rules: a reply is not a new finding, a second finding on a hunk
means the first fix reworded it, and a patch identical to the line means the
reviewer has nothing left there. The tool is advice, so it never gates.
"""

import unittest

from tools.repeat_findings import (
    Finding,
    Standing,
    group_by_hunk,
    normalised,
    patch_replaces,
    report,
    standings,
    suggested_patch,
)

BODY = """**Suggestion:** Split it.
```suggestion
one claim per sentence
```
"""


def finding(id: int, line: int = 3, body: str = "**Suggestion:** nope", reply_to=None) -> Finding:
    return Finding(id=id, author="github-actions[bot]", path="a.md", line=line, body=body, reply_to=reply_to)


def no_lines(path: str) -> list[str]:
    """No file on disk: the standing is then decided by the findings alone."""
    return []


def standing(*findings: Finding, spent: bool = False) -> Standing:
    return Standing(path="a.md", line=3, findings=findings, spent=spent)


class GroupingTest(unittest.TestCase):
    """A reply answers a comment; counting it as a finding counts one objection twice."""

    def test_two_findings_on_one_hunk_group_together(self):
        self.assertEqual(len(group_by_hunk([finding(1), finding(2)])[("a.md", 3)]), 2)

    def test_two_hunks_stay_apart(self):
        self.assertEqual(len(group_by_hunk([finding(1, line=3), finding(2, line=9)])), 2)

    def test_a_reply_is_not_a_finding_on_the_hunk(self):
        self.assertEqual(len(standings([finding(1), finding(2, reply_to=1)], no_lines)[0].findings), 1)


class PatchTest(unittest.TestCase):
    """The suggestion fence is the patch; the last fence is the code either way."""

    def test_the_suggestion_fence_is_read(self):
        self.assertEqual(suggested_patch(BODY), "one claim per sentence\n")

    def test_no_fence_offers_no_patch(self):
        self.assertIsNone(suggested_patch("**Suggestion:** just words"))

    def test_indentation_and_blanks_do_not_change_the_patch(self):
        self.assertEqual(normalised(["  a  ", "", "b"]), ("a", "b"))

    def test_a_patch_already_in_the_file_is_spent(self):
        self.assertTrue(patch_replaces("one claim per sentence\n", ["x", "one claim per sentence"], line=2))

    def test_a_patch_that_changes_the_line_is_not_spent(self):
        self.assertFalse(patch_replaces("one claim per sentence\n", ["x", "something else"], line=2))

    def test_an_unknown_line_is_not_spent(self):
        self.assertFalse(patch_replaces("one claim per sentence\n", ["x"], line=None))


class StandingTest(unittest.TestCase):
    """Two findings on one hunk is the signal; there is no count below which it is fine."""

    def test_a_second_finding_means_the_first_answer_did_not_settle_it(self):
        self.assertTrue(standings([finding(1), finding(2)], no_lines)[0].answered_more_than_once)

    def test_one_finding_is_answerable_as_written(self):
        self.assertFalse(standings([finding(1)], no_lines)[0].answered_more_than_once)

    def test_a_spent_patch_is_marked(self):
        lines = ["x", "one claim per sentence"]
        row = standings([finding(9, line=2, body=BODY)], lambda path: lines)[0]
        self.assertEqual(row.mark, "SPENT")

    def test_the_most_answered_hunk_sorts_first(self):
        rows = standings([finding(1, line=3), finding(2, line=9), finding(3, line=9)], no_lines)
        self.assertEqual(rows[0].line, 9)


class ReportTest(unittest.TestCase):
    """The report names the next step, or says there is none."""

    def test_no_repeat_says_to_fix_what_is_written(self):
        self.assertIn("Nothing here has been answered twice", report([standing(finding(1))]))

    def test_a_repeat_points_at_the_rule(self):
        self.assertIn("skill://pr-workflow", report([standing(finding(1), finding(2))]))

    def test_a_spent_hunk_says_to_reply_once(self):
        self.assertIn("SPENT", report([standing(finding(1), spent=True)]))
