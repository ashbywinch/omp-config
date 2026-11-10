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

import contextlib
import io
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_review_posted  # noqa: E402  (sys.path bootstrap must precede the import)


def _covers(comments, sha, head_at):
    return check_review_posted._review_covers(comments, sha, head_at)

SHA = "44d47e01e09a7e4992d2760b0e86d87fc7d48d7c"
HEAD_AT = "2026-08-22T12:41:46Z"
BEFORE_HEAD = "2026-08-22T12:00:00Z"
AFTER_HEAD = "2026-08-22T12:42:27Z"

def comment(body: str, created_at: str = AFTER_HEAD, updated_at: str = "", user_type: str = "Bot"):
    """One issue comment, as the gate models it."""
    return check_review_posted._Comment(body, created_at, updated_at, user_type)
class ApiFailureTest(unittest.TestCase):
    """A failed fetch fails the gate with a message. Only HTTPError was caught
    once, so a proxy's error page reached the user as a traceback; the job-log
    fetch was swallowed, so the user was told the log was mid-run when the
    fetch had simply been refused."""

    def test_a_body_that_is_not_json_is_reported_not_raised(self):
        with mock.patch.object(check_review_posted, "_get", return_value=b"<html>Bad gateway</html>"):
            with mock.patch.dict(os.environ, {
                "SHA": SHA,
                "PR_NUMBER": "1",
                "GITHUB_REPOSITORY": "o/r",
                "GITHUB_TOKEN": "t",
            }):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(check_review_posted.main(), 1)
        self.assertIn("::error::", out.getvalue())
        self.assertIn("is not fetchable", out.getvalue())
        self.assertIn("not JSON", out.getvalue())

    def test_a_transport_failure_is_reported_not_raised(self):
        with mock.patch.object(check_review_posted, "_get",
                               side_effect=urllib.error.URLError("connection refused")):
            with mock.patch.dict(os.environ, {
                "SHA": SHA,
                "PR_NUMBER": "1",
                "GITHUB_REPOSITORY": "o/r",
                "GITHUB_TOKEN": "t",
            }):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(check_review_posted.main(), 1)
        self.assertIn("is not fetchable", out.getvalue())
        self.assertIn("connection refused", out.getvalue())

    def test_an_unreadable_job_log_names_the_failure_it_was(self):
        def refuse_the_log(url, token, accept="application/vnd.github+json"):
            if "/actions/runs/" in url and url.endswith("/jobs"):
                refused = urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
                refused.close()  # an unclosed fake leaks a file handle at GC
                raise refused
            if "/commits/" in url:
                return b"{}"
            if "/actions/runs/" in url:
                return b'{"run_started_at": "' + HEAD_AT.encode() + b'"}'
            return b"[]"  # no comments, so coverage is unproven
        with mock.patch.object(check_review_posted, "_get", side_effect=refuse_the_log):
            with mock.patch.dict(os.environ, {
                "SHA": SHA,
                "PR_NUMBER": "1",
                "GITHUB_REPOSITORY": "o/r",
                "GITHUB_TOKEN": "t",
                "GITHUB_RUN_ID": "7",
            }):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    self.assertEqual(check_review_posted.main(), 1)
        self.assertIn("could not be read", out.getvalue())
        self.assertIn("HTTP 403", out.getvalue())
        self.assertNotIn("not served while the job is still running", out.getvalue())


class ReviewSkippedTest(unittest.TestCase):
    """The markers are parameters. A local tuple shadowed them once, so a caller
    could not change them and the parameter was dead; this fails on that."""

    def test_custom_skip_markers_are_honoured(self):
        self.assertTrue(
            check_review_posted._review_skipped(
                "nothing here it can read",
                failure_markers=(),
                skip_markers=("nothing here it can read",),
            )
        )

    def test_a_traceback_still_means_not_a_clean_skip(self):
        self.assertFalse(
            check_review_posted._review_skipped(
                "skipping review\nTraceback (most recent call last)",
                failure_markers=("Traceback (most recent call last)",),
                skip_markers=("skipping review",),
            )
        )


class ReviewCoversTest(unittest.TestCase):
    def test_regular_guide_after_head_covers(self):
        c = comment("## PR Reviewer Guide 🔍\nHere are some observations")
        self.assertTrue(_covers([c], SHA, HEAD_AT))

    def test_persistent_guide_edited_after_head_covers(self):
        """The guide is edited in place on every run: `created_at` stays at its
        first date, and pr-agent's persistent-state read can fail so the edit
        carries no SHA footer. An edit after the head arrived is coverage."""
        c = comment("## PR Reviewer Guide 🔍\nNo major issues detected",
                    created_at=BEFORE_HEAD, updated_at=AFTER_HEAD)
        self.assertTrue(_covers([c], SHA, HEAD_AT))

    def test_persistent_guide_untouched_since_before_head_does_not_cover(self):
        c = comment("## PR Reviewer Guide 🔍\nSome older review",
                    created_at=BEFORE_HEAD, updated_at=BEFORE_HEAD)
        self.assertFalse(_covers([c], SHA, HEAD_AT))

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
