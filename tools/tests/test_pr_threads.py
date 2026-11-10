"""Tests for tools/pr_threads.py — which threads still need an answer.

The load-bearing rule: a thread is answered only when the *last* comment is mine.
An earlier reply followed by a follow-up question is still open work, which is
the mistake this tool exists to catch.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pr_threads import Comment, Thread, unanswered  # noqa: E402


def thread(*authors, resolved=False):
    return Thread(
        id="t1",
        path="a.md",
        line=1,
        resolved=resolved,
        comments=tuple(Comment(author=a, body=f"from {a}") for a in authors),
    )


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
