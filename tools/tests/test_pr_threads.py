"""Tests for tools/pr_threads.py — which threads still need an answer.

The load-bearing rule: a thread is answered only when the *last* comment is mine.
An earlier reply followed by a follow-up question is still open work, which is
the mistake this tool exists to catch.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pr_threads import Check, Comment, Thread, unanswered  # noqa: E402


def thread(*authors, resolved=False):
    return Thread(
        id="t1",
        path="a.md",
        line=1,
        resolved=resolved,
        comments=tuple(Comment(author=a, body=f"from {a}") for a in authors),
    )


class FinishedTest(unittest.TestCase):
    """A check run carries `status`; a status context carries `state`. Reading
    one field for both made the wait loop wait for a value that never appears."""

    def check(self, **node):
        return Check.from_json(node).finished

    def test_a_completed_check_run_is_finished(self):
        self.assertTrue(self.check(__typename="CheckRun", status="COMPLETED", conclusion="SUCCESS"))

    def test_a_running_check_run_is_not_finished(self):
        self.assertFalse(self.check(__typename="CheckRun", status="IN_PROGRESS", conclusion=None))

    def test_a_status_context_is_finished_once_it_is_not_pending(self):
        self.assertTrue(self.check(__typename="StatusContext", state="SUCCESS"))
        self.assertFalse(self.check(__typename="StatusContext", state="PENDING"))


class ThreadShapeTest(unittest.TestCase):
    def test_a_thread_missing_its_comments_is_refused_not_crashed(self):
        with self.assertRaises(ValueError):
            Thread.from_json({"id": "t1", "path": "a.md", "isResolved": False})


class CommentTest(unittest.TestCase):
    def test_a_deleted_author_is_nobody(self):
        # GraphQL returns null for a comment whose account was deleted; reading
        # it must not crash the whole listing.
        self.assertEqual(Comment.from_json({"author": None, "body": "gone"}).author, "")

    def test_a_deleted_author_does_not_answer_for_me(self):
        threads = [Thread(id="t1", path="a.md", line=1, resolved=False,
                          comments=(Comment.from_json({"author": None, "body": "gone"}),))]
        self.assertEqual(len(unanswered(threads, "omp-harness")), 1)


class UnansweredTest(unittest.TestCase):
    def test_unanswered_when_the_reviewer_spoke_last(self):
        self.assertEqual(len(unanswered([thread("github-actions")], "omp-harness")), 1)

    def test_answered_when_i_spoke_last(self):
        self.assertEqual(unanswered([thread("github-actions", "omp-harness")], "omp-harness"), [])

    def test_a_follow_up_question_reopens_the_thread(self):
        threads = [thread("github-actions", "omp-harness", "ashbywinch")]
        self.assertEqual(len(unanswered(threads, "omp-harness")), 1)

    def test_resolved_threads_are_ignored(self):
        self.assertEqual(unanswered([thread("github-actions", resolved=True)], "omp-harness"), [])

    def test_a_thread_only_i_have_spoken_in_is_answered(self):
        # Nothing to answer in a thread I opened myself.
        self.assertEqual(unanswered([thread("omp-harness")], "omp-harness"), [])

    def test_a_thread_with_no_comments_is_ignored(self):
        empty = Thread(id="t1", path="a.md", line=1, resolved=False, comments=())
        self.assertEqual(unanswered([empty], "omp-harness"), [])


if __name__ == "__main__":
    unittest.main()
