"""What each desk reader answers, and when it refuses to answer.

Every read runs the real reader against the fake `gh` the watcher's tests use,
so the payload parsed here has the shape GitHub sends. The merge proof runs git
for real against a throwaway origin: its subject is a subprocess round trip, and
a stubbed runner would prove nothing about it.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.desk.checks import Checks, checks_from_pages
from tools.desk.contexts import Contexts
from tools.desk.errors import SourceUnknown
from tools.desk.merge import Merge
from tools.desk.model import Thread
from tools.desk.pulls import PullRequests
from tools.desk.repository import Repository
from tools.desk.threads import Threads, unanswered
from tools.tests.desk_fakes import Fake


class ReaderTest(unittest.TestCase):
    """A test whose readers run against one fake `gh` on PATH."""

    def fake(self, **scenario) -> Fake:
        fake = Fake(**scenario)
        self.addCleanup(fake.close)
        patcher = mock.patch.dict(os.environ, fake.env())
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake


class PullRequestTest(ReaderTest):
    def test_view_returns_the_fields_a_notice_reads(self):
        self.fake(state="OPEN", head="b" * 40, decision="APPROVED", merge_state="BEHIND")
        pull = PullRequests("owner/name", timeout=5).view(1)
        self.assertEqual(pull.number, 1)
        self.assertEqual(pull.repo, "owner/name")
        self.assertEqual(pull.state, "OPEN")
        self.assertEqual(pull.head, "b" * 40)
        self.assertEqual(pull.base, "main")
        self.assertEqual(pull.url, "https://github.com/owner/name/pull/1")
        self.assertEqual(pull.decision, "APPROVED")
        self.assertEqual(pull.merge_state, "BEHIND")
        self.assertTrue(pull.behind)
        self.assertFalse(pull.finished)

    def test_a_failed_view_is_unknown_not_an_empty_record(self):
        self.fake(pull_rc=1)
        with self.assertRaises(SourceUnknown):
            PullRequests("owner/name", timeout=5).view(1)


class ThreadTest(ReaderTest):
    def test_threads_carry_their_last_author(self):
        self.fake(thread_nodes=[
            {"id": "T1", "isResolved": False, "path": "a.py", "line": 3,
             "comments": {"nodes": [{"author": {"login": "reviewer"}}]}},
            {"id": "T2", "isResolved": True, "path": "b.py", "line": None,
             "comments": {"nodes": [{"author": {"login": "omp-harness"}}]}},
        ])
        threads = Threads("owner/name", timeout=5).all(1)
        self.assertEqual(
            threads,
            [
                Thread("T1", "a.py", 3, False, "reviewer"),
                Thread("T2", "b.py", None, True, "omp-harness"),
            ],
        )

    def test_only_an_open_thread_whose_last_voice_is_not_mine_is_unanswered(self):
        threads = [
            Thread("T1", "a.py", 1, False, "reviewer"),
            Thread("T2", "b.py", 1, False, "omp-harness"),
            Thread("T3", "c.py", 1, True, "reviewer"),
            Thread("T4", "d.py", 1, False, None),
        ]
        self.assertEqual([t.id for t in unanswered(threads, "omp-harness")], ["T1"])


class CheckTest(ReaderTest):
    def test_one_run_per_name_is_kept_and_the_newest_wins(self):
        self.fake(checks=[
            {"name": "arm", "status": "completed", "conclusion": "failure",
             "started_at": "2026-01-01T00:00:00Z"},
            {"name": "arm", "status": "completed", "conclusion": "success",
             "started_at": "2026-01-01T00:05:00Z"},
        ])
        checks = Checks("owner/name", timeout=5).on("a" * 40)
        self.assertEqual([(c.name, c.conclusion) for c in checks], [("arm", "success")])
        self.assertTrue(checks[0].passed)

    def test_no_check_runs_is_unknown_not_clean(self):
        self.fake(checks=[])
        with self.assertRaises(SourceUnknown):
            Checks("owner/name", timeout=5).on("a" * 40)

    def test_a_head_that_is_not_a_sha_is_unknown(self):
        self.fake()
        with self.assertRaises(SourceUnknown):
            Checks("owner/name", timeout=5).on("-")

    def test_a_page_that_is_not_an_object_is_unknown_not_no_runs(self):
        with self.assertRaises(SourceUnknown):
            checks_from_pages(json.dumps([{"name": "arm"}]))

    def test_pages_are_decoded_value_by_value(self):
        first = {"check_runs": [{"name": "one", "status": "completed",
                                 "conclusion": "success", "started_at": "x"}]}
        second = {"check_runs": [{"name": "two", "status": "queued",
                                  "conclusion": None, "started_at": ""}]}
        checks = checks_from_pages(json.dumps(first) + "\n" + json.dumps(second))
        self.assertEqual([check.name for check in checks], ["one", "two"])


class ContextTest(ReaderTest):
    def test_classic_and_rules_contexts_are_merged_and_sorted(self):
        self.fake(
            required=["lint", "test"],
            rules=[{
                "type": "required_status_checks",
                "parameters": {"required_status_checks": [
                    {"context": "test"}, {"context": "build"},
                ]},
            }],
        )
        self.assertEqual(
            Contexts("owner/name", timeout=5).required("main"),
            ["build", "lint", "test"],
        )

    def test_an_unreadable_source_makes_the_whole_answer_unknown(self):
        self.fake(contexts_rc=1)
        with self.assertRaises(SourceUnknown):
            Contexts("owner/name", timeout=5).required("main")

    def test_an_unreadable_rules_source_is_unknown_too(self):
        """A 404 from the rules endpoint is a failed read, not "no rules"."""
        self.fake(required=["lint"], rules_rc=1)
        with self.assertRaises(SourceUnknown):
            Contexts("owner/name", timeout=5).required("main")


class RepositoryTest(ReaderTest):
    def test_the_checkout_names_its_repository(self):
        self.fake()
        self.assertEqual(Repository(timeout=5).current(), "owner/name")

    def test_no_checkout_is_unknown(self):
        self.fake(repo_rc=1)
        with self.assertRaises(SourceUnknown):
            Repository(timeout=5).current()


def git(*args: str, cwd: Path) -> str:
    """One git command with a fixed identity, independent of the caller's config."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@example.com",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
        },
    )
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


class GitFixture:
    """A bare origin and a clone of it, under one temporary directory."""

    def __init__(self, testcase: unittest.TestCase) -> None:
        self.dir = tempfile.TemporaryDirectory()
        testcase.addCleanup(self.dir.cleanup)
        self.root = Path(self.dir.name) / "repos"
        self.root.mkdir()
        self.origin = self.root / "origin.git"
        git("init", "--bare", "-b", "main", str(self.origin), cwd=self.root)
        seed = self.clone("seed")
        (seed / "f.txt").write_text("one\n", encoding="utf-8")
        git("add", "f.txt", cwd=seed)
        git("commit", "-m", "base", cwd=seed)
        git("push", "origin", "main", cwd=seed)

    def clone(self, name: str) -> Path:
        path = self.root / name
        git("clone", str(self.origin), str(path), cwd=self.root)
        return path


class MergeTest(ReaderTest):
    def test_the_status_answers_without_git(self):
        for status, merges, behind in (
            ("CLEAN", True, False),
            ("BLOCKED", True, False),
            ("BEHIND", True, True),
            ("DIRTY", False, False),
        ):
            with self.subTest(status=status):
                self.fake(merge_state=status)
                state = Merge("owner/name", timeout=5).state(1)
                self.assertEqual((state.merges, state.behind), (merges, behind))

    # lucidlint: ignore fakefs the subject is git's own merge-tree round trip through subprocess; a fake filesystem cannot host a real git origin.
    def test_a_clean_head_is_proved_locally_when_github_says_unknown(self):
        repos = GitFixture(self)
        feature = repos.clone("feature")
        (feature / "g.txt").write_text("new\n", encoding="utf-8")
        git("add", "g.txt", cwd=feature)
        git("commit", "-m", "feature", cwd=feature)
        head = git("rev-parse", "HEAD", cwd=feature)
        self.fake(merge_state="UNKNOWN", head=head)
        state = Merge("owner/name", timeout=5, root=feature).state(1)
        self.assertEqual((state.merges, state.behind), (True, False))

    # lucidlint: ignore fakefs the subject is git's own merge-tree round trip through subprocess; a fake filesystem cannot host a real git origin.
    def test_a_conflict_is_proved_locally_when_github_says_unknown(self):
        repos = GitFixture(self)
        feature = repos.clone("feature")
        base = repos.clone("base")
        (base / "f.txt").write_text("two\n", encoding="utf-8")
        git("commit", "-am", "base edit", cwd=base)
        git("push", "origin", "main", cwd=base)
        (feature / "f.txt").write_text("three\n", encoding="utf-8")
        git("commit", "-am", "feature edit", cwd=feature)
        head = git("rev-parse", "HEAD", cwd=feature)
        self.fake(merge_state="UNKNOWN", head=head)
        state = Merge("owner/name", timeout=5, root=feature).state(1)
        self.assertFalse(state.merges)
        self.assertTrue(state.behind)

    # lucidlint: ignore fakefs the subject is git's own merge-tree round trip through subprocess; a fake filesystem cannot host a real git origin.
    def test_a_head_the_origin_does_not_have_is_named_as_the_fetch_failure(self):
        repos = GitFixture(self)
        feature = repos.clone("feature")
        self.fake(merge_state="UNKNOWN", head="a" * 40)
        with self.assertRaises(SourceUnknown) as caught:
            Merge("owner/name", timeout=5, root=feature).state(1)
        self.assertIn("cannot fetch", str(caught.exception))

    def test_when_git_cannot_prove_it_either_the_read_raises(self):
        repos = GitFixture(self)
        self.fake(merge_state="UNKNOWN", head="a" * 40)
        with self.assertRaises(SourceUnknown):
            Merge("owner/name", timeout=5, root=repos.root / "absent").state(1)


if __name__ == "__main__":
    unittest.main()
