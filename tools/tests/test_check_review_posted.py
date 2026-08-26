"""Tests for tools/check_review_posted.py (stdlib unittest — no deps in this
repo).

The coverage contract is the load-bearing part of the gate: a comment covers
the head commit when it is a posted review guide (regular or incremental,
referencing the SHA or created after the head commit), a human /skip opt-out,
or the bot's OWN incremental-skip verdict — an incremental review with no
files changed since the previous review posts "Incremental Review Skipped"
instead of a guide, and that skip IS the review (the diff was examined and
found empty). The last case is the regression this suite pins: a merge of
the base branch into the PR (which changes nothing in the PR's diff) used to
fail the gate because the skip comment was not counted as coverage.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_review_posted  # noqa: E402  (sys.path bootstrap must precede the import)


def _covers(comments, sha, head_at):
    return check_review_posted._review_covers(comments, sha, head_at)

SHA = "44d47e01e09a7e4992d2760b0e86d87fc7d48d7c"
HEAD_AT = "2026-08-22T12:41:46Z"
BEFORE_HEAD = "2026-08-22T12:00:00Z"
AFTER_HEAD = "2026-08-22T12:42:27Z"

def comment(body: str, created_at: str = AFTER_HEAD, user_type: str = "Bot"):
    """One issue comment in the wire shape the gate reads."""
    # lucidlint: ignore record-shape the one-shot test-fixture wire shape — a class is ceremony
    return {"body": body, "created_at": created_at, "user": {"type": user_type}}
class ReviewCoversTest(unittest.TestCase):
    def test_regular_guide_after_head_covers(self):
        c = comment("## PR Reviewer Guide 🔍\nHere are some observations")
        self.assertTrue(_covers([c], SHA, HEAD_AT))

    def test_incremental_guide_with_sha_covers(self):
        c = comment(f"## Incremental PR Reviewer Guide 🔍\nStarting from commit https://github.com/o/r/commit/{SHA}")
        self.assertTrue(_covers([c], SHA, HEAD_AT))

    def test_incremental_guide_before_head_does_not_cover(self):
        # a review for an OLDER commit must not cover the new head
        c = comment("## Incremental PR Reviewer Guide 🔍\nold review", created_at=BEFORE_HEAD)
        self.assertFalse(_covers([c], SHA, HEAD_AT))

    def test_bot_skip_after_head_covers(self):
        # the regression: an incremental review with no files changed posts a
        # skip instead of a guide — that skip is the reviewed verdict
        c = comment("Incremental Review Skipped\nNo files were changed since the previous PR Review")
        self.assertTrue(_covers([c], SHA, HEAD_AT))

    def test_bot_skip_before_head_does_not_cover(self):
        # a stale skip for an older commit must not cover a newer head
        c = comment("Incremental Review Skipped", created_at=BEFORE_HEAD)
        self.assertFalse(_covers([c], SHA, HEAD_AT))

    def test_non_bot_skip_does_not_cover(self):
        # only the bot's own skip verdict counts — a human comment with the
        # same prefix must not satisfy the gate
        c = comment("Incremental Review Skipped", user_type="User")
        self.assertFalse(_covers([c], SHA, HEAD_AT))

    def test_human_skip_covers(self):
        self.assertTrue(_covers([comment("/skip", user_type="User")], SHA, HEAD_AT))

    def test_no_comments_does_not_cover(self):
        self.assertFalse(_covers([], SHA, HEAD_AT))

    def test_unrelated_comment_does_not_cover(self):
        c = comment("![Code Coverage](https://img.shields.io/badge/78%25-success)")
        self.assertFalse(_covers([c], SHA, HEAD_AT))


if __name__ == "__main__":
    unittest.main()
