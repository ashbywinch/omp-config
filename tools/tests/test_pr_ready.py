"""`pr-ready` as a display over the library: the verdict, and the exit code."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from tools.tests.desk_fakes import Fake

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "tools" / "pr_ready.py"


class ReadyTest(unittest.TestCase):
    def fake(self, **scenario) -> Fake:
        fake = Fake(**scenario)
        self.addCleanup(fake.close)
        patcher = mock.patch.dict(os.environ, fake.env())
        patcher.start()
        self.addCleanup(patcher.stop)
        return fake

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "1", *args],
            env=os.environ,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_a_clean_pr_exits_zero_and_says_ready(self):
        self.fake(required=["self-check"])
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("READY:", result.stdout)
        self.assertIn("no unanswered threads", result.stdout)

    def test_a_finished_pr_is_named_instead_of_judged(self):
        """A merged head is behind main by definition; that is not a defect."""
        self.fake(state="MERGED", required=["self-check"])
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("is MERGED — nothing to ready", result.stdout)
        self.assertNotIn("BLOCKED", result.stdout)

    def test_a_failing_required_check_blocks_with_the_check_named(self):
        self.fake(
            required=["self-check"],
            checks=[{"name": "self-check", "status": "completed",
                     "conclusion": "failure", "started_at": "2026-01-01T00:00:00Z"}],
        )
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("BLOCKED:", result.stdout)
        self.assertIn("self-check did not pass (failure)", result.stdout)

    def test_a_required_context_with_no_run_blocks(self):
        self.fake(required=["missing"])
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing has no run on this head", result.stdout)

    def test_an_unanswered_thread_blocks(self):
        self.fake(threads=["PRRC_1", "PRRC_2"])
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("2 unanswered thread(s)", result.stdout)

    def test_a_head_behind_its_base_blocks(self):
        self.fake(merge_state="BEHIND")
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("behind origin/main", result.stdout)

    def test_a_draft_blocks(self):
        self.fake(draft=True)
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertIn("the PR is a draft", result.stdout)

    def test_an_unreadable_read_exits_two(self):
        self.fake(checks_rc=1)
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("pr-ready:", result.stderr)

    def test_me_from_the_environment_answers_a_thread(self):
        nodes = [{"id": "T1", "isResolved": False, "path": "a.py", "line": 1,
                  "comments": {"nodes": [{"author": {"login": "omp-harness[bot]"}}]}}]
        self.fake(required=["self-check"], thread_nodes=nodes)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_me_from_the_flag_overrides_the_environment(self):
        nodes = [{"id": "T1", "isResolved": False, "path": "a.py", "line": 1,
                  "comments": {"nodes": [{"author": {"login": "someone"}}]}}]
        self.fake(required=["self-check"], thread_nodes=nodes)
        self.assertEqual(self.run_cli("--me", "someone").returncode, 0)
        self.assertEqual(self.run_cli().returncode, 1)


if __name__ == "__main__":
    unittest.main()
