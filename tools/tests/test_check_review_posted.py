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


class ReviewSkippedTest(unittest.TestCase):
    """The bot reviews nothing when it has nothing it can analyse — a lone CSV
    diff. It says so in its log and posts no comment; that is a verdict."""

    def test_clean_skip_passes(self):
        log = (
            '{"text":"PR has no analyzable files: o/r/12, skipping describe"}\n'
            '{"text":"PR has no analyzable files: o/r/12, skipping review"}\n'
        )
        self.assertTrue(check_review_posted._review_skipped(log))

    def test_skip_with_traceback_fails(self):
        log = (
            '{"text":"PR has no analyzable files: o/r/12, skipping review"}\n'
            '{"text":"Failed to process the command."}\n'
        )
        self.assertFalse(check_review_posted._review_skipped(log))

    def test_skip_with_token_cap_fails(self):
        log = (
            '{"text":"PR has no analyzable files: o/r/12, skipping review"}\n'
            '{"text":"Tokens: 91000, total tokens over limit: 80000"}\n'
        )
        self.assertFalse(check_review_posted._review_skipped(log))

    def test_no_log_does_not_pass(self):
        # no log means no evidence of a skip: the gate stays closed
        self.assertFalse(check_review_posted._review_skipped(None))
        self.assertFalse(check_review_posted._review_skipped(""))

    def test_ordinary_log_does_not_pass(self):
        log = '{"text":"Reviewing PR: https://api.github.com/repos/o/r/pulls/12 ..."}\n'
        self.assertFalse(check_review_posted._review_skipped(log))


class JobNameMatchesTest(unittest.TestCase):
    """A reusable workflow prefixes its job names with the workflow: the job
    called pr-review is listed as "review / pr-review". The log fetcher has to
    find it, or every failure falls back to a generic message."""

    def test_bare_name_matches(self):
        self.assertTrue(check_review_posted._job_name_matches("pr-review", "pr-review"))

    def test_prefixed_name_matches(self):
        self.assertTrue(check_review_posted._job_name_matches("review / pr-review", "pr-review"))

    def test_other_job_does_not_match(self):
        self.assertFalse(check_review_posted._job_name_matches("review / verify", "pr-review"))

    def test_prefix_is_not_a_wildcard(self):
        self.assertFalse(check_review_posted._job_name_matches("pr-review / extra", "pr-review"))


if __name__ == "__main__":
    unittest.main()
